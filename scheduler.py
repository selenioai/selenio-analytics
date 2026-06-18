from apscheduler.schedulers.background import BackgroundScheduler
import db, datetime

_scheduler = None

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
    _scheduler.add_job(_coletar_todos_tenants, "cron", hour=6,  minute=0,  id="coleta_diaria")
    _scheduler.add_job(_registrar_uso_mensal,  "cron", hour=23, minute=55, id="uso_mensal")
    _scheduler.start()
    print("[Scheduler] Iniciado — coleta às 06h, uso às 23:55 BRT")
