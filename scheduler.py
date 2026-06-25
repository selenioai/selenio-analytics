from apscheduler.schedulers.background import BackgroundScheduler
import db, datetime

_scheduler = None

def _sincronizar_keywords_gsc():
    """Sincroniza keywords via GSC para todos os projetos configurados."""
    import json, requests as req_lib
    from datetime import datetime, timedelta

    print(f"[Scheduler] Iniciando sync GSC keywords — {datetime.now().strftime('%H:%M:%S')}")

    # Buscar todos os projetos com GSC configurado e ativo
    configs = db.query(
        """SELECT kfc.*, p.tenant_id, p.nome as projeto_nome
           FROM keyword_fonte_config kfc
           JOIN projetos p ON p.id = kfc.projeto_id
           WHERE kfc.fonte = 'gsc'
             AND kfc.gsc_property_url IS NOT NULL
             AND p.ativo = 1 AND p.D_E_L_E_T = 0"""
    )

    for cfg in configs:
        tid = cfg["tenant_id"]
        pid = cfg["projeto_id"]
        try:
            # Buscar token GSC do projeto
            integracao = db.query_one(
                """SELECT * FROM api_integracoes
                   WHERE tenant_id=%s AND projeto_id=%s
                     AND provedor='google_gsc' AND ativo=1 AND d_e_l_e_t=0
                   ORDER BY datestamp_insert DESC LIMIT 1""",
                (tid, pid)
            )
            if not integracao:
                print(f"[Scheduler] GSC t{tid}/p{pid}: sem token")
                continue

            # Renovar token se necessário
            from modules.keywords.gsc import _refresh_token_se_necessario
            access_token = _refresh_token_se_necessario(integracao)

            # Buscar keywords do projeto
            keywords = db.query(
                "SELECT * FROM keywords WHERE projeto_id=%s AND d_e_l_e_t=0 AND ativo=1",
                (pid,)
            )
            if not keywords:
                continue

            property_url = cfg["gsc_property_url"]
            end_date     = datetime.utcnow().strftime("%Y-%m-%d")
            start_date   = (datetime.utcnow() - timedelta(days=28)).strftime("%Y-%m-%d")
            GSC_API_BASE = "https://www.googleapis.com/webmasters/v3"

            total_sync = 0
            for kw in keywords:
                try:
                    body = {
                        "startDate":  start_date,
                        "endDate":    end_date,
                        "dimensions": ["query"],
                        "dimensionFilterGroups": [{"filters": [{
                            "dimension":  "query",
                            "operator":   "equals",
                            "expression": kw["termo"]
                        }]}],
                        "rowLimit": 1
                    }
                    resp = req_lib.post(
                        f"{GSC_API_BASE}/sites/{req_lib.utils.quote(property_url, safe='')}/searchAnalytics/query",
                        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                        json=body, timeout=20
                    )
                    posicao  = None
                    raw_data = {}
                    if resp.status_code == 200:
                        rows = resp.json().get("rows", [])
                        if rows:
                            posicao  = round(rows[0].get("position", 0))
                            raw_data = rows[0]

                    # Buscar posição anterior para alerta
                    pos_ant = db.query_one(
                        "SELECT posicao FROM keyword_posicoes WHERE keyword_id=%s ORDER BY rastreado_em DESC LIMIT 1",
                        (kw["id"],)
                    )
                    pos_anterior = pos_ant["posicao"] if pos_ant else None

                    db.execute(
                        """INSERT INTO keyword_posicoes
                           (keyword_id, projeto_id, posicao, volume_busca, fonte, raw_data)
                           VALUES (%s,%s,%s,%s,'gsc',%s)""",
                        (kw["id"], pid, posicao,
                         int(raw_data.get("impressions", 0)) if raw_data else None,
                         json.dumps(raw_data))
                    )

                    # Alerta de variação >= 5 posições
                    if posicao and pos_anterior:
                        variacao = pos_anterior - posicao
                        if abs(variacao) >= 5:
                            tipo = "subida" if variacao > 0 else "queda"
                            if pos_anterior > 10 and posicao <= 10: tipo = "entrada_top10"
                            elif pos_anterior <= 10 and posicao > 10: tipo = "saiu_top10"
                            db.execute(
                                """INSERT INTO keyword_alertas
                                   (keyword_id, projeto_id, tipo, posicao_anterior, posicao_atual, variacao)
                                   VALUES (%s,%s,%s,%s,%s,%s)""",
                                (kw["id"], pid, tipo, pos_anterior, posicao, variacao)
                            )
                    total_sync += 1
                except Exception as e:
                    print(f"[Scheduler] GSC keyword '{kw['termo']}' t{tid}/p{pid}: {e}")

            # Atualizar ultimo_sync
            db.execute("UPDATE api_integracoes SET ultimo_sync=NOW() WHERE id=%s", (integracao["id"],))
            print(f"[Scheduler] GSC t{tid}/p{pid} '{cfg['projeto_nome']}': {total_sync} keywords sincronizadas")

        except Exception as e:
            print(f"[Scheduler] GSC erro t{tid}/p{pid}: {e}")

def _coletar_todos_tenants():
    from integrations import serpapi, gsc
    tenants = db.query("SELECT * FROM tenants WHERE status='active' AND ativo=1")
    for t in tenants:
        tid      = t["id"]
        projetos = db.query_t(tid,
            "SELECT * FROM projetos WHERE tenant_id=%s AND ativo=1 AND D_E_L_E_T=0")
        for p in projetos:
            pid = p["id"]
            try: serpapi.coletar_rankings(tid, pid)
            except Exception as e: print(f"[Scheduler] SERPApi t{tid}/p{pid}: {e}")
            if p.get("gsc_site_url"):
                try: gsc.coletar_queries(tid, pid, p["gsc_site_url"])
                except Exception as e: print(f"[Scheduler] GSC t{tid}/p{pid}: {e}")

def _registrar_uso_mensal():
    """Snapshot mensal de uso por tenant para billing."""
    hoje     = datetime.date.today().replace(day=1)
    tenants  = db.query("SELECT id FROM tenants WHERE status='active' AND ativo=1")
    for t in tenants:
        tid = t["id"]
        usuarios  = db.query_one_t(tid, "SELECT COUNT(*) AS n FROM usuarios WHERE tenant_id=%s AND ativo=1 AND D_E_L_E_T=0")
        projetos  = db.query_one_t(tid, "SELECT COUNT(*) AS n FROM projetos WHERE tenant_id=%s AND D_E_L_E_T=0")
        keywords  = db.query_one_t(tid, "SELECT COUNT(*) AS n FROM keywords WHERE tenant_id=%s AND D_E_L_E_T=0")
        db.execute("""
            INSERT INTO uso_mensal (tenant_id, mes_ref, assentos_ativos, projetos_ativos, keywords_total)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (tenant_id, mes_ref) DO UPDATE
            SET assentos_ativos=%s, projetos_ativos=%s, keywords_total=%s, datestamp_update=NOW()
        """, (tid, hoje,
              usuarios["n"], projetos["n"], keywords["n"],
              usuarios["n"], projetos["n"], keywords["n"]))

def init_scheduler(app):
    global _scheduler
    if _scheduler: return
    _scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    _scheduler.add_job(_sincronizar_keywords_gsc, "cron", hour=6, minute=30, id="sync_keywords_gsc")
    _scheduler.add_job(_coletar_todos_tenants, "cron", hour=6,  minute=0,  id="coleta_diaria")
    _scheduler.add_job(_registrar_uso_mensal,  "cron", hour=23, minute=55, id="uso_mensal")
    _scheduler.start()
    print("[Scheduler] Iniciado — keywords GSC às 06:30h, coleta às 06h, uso às 23:55 BRT")
