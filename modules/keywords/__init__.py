"""
modules/keywords/__init__.py

Módulo de rastreamento de keywords — Selenio Analytics
Rotas:
    GET  /keywords/<projeto_id>                  → index (lista + última posição)
    GET  /keywords/<projeto_id>/historico/<id>   → histórico de posições de 1 keyword
    POST /keywords/<projeto_id>/salvar           → criar/editar keyword
    POST /keywords/<projeto_id>/rastrear/<id>    → registrar posição (manual ou API)
    POST /keywords/<projeto_id>/rastrear-todas   → rastrear todas as keywords
    POST /keywords/<projeto_id>/deletar/<id>     → soft delete
    GET  /keywords/<projeto_id>/config           → tela de configuração de fonte
    POST /keywords/<projeto_id>/config/salvar    → salvar config de fonte
    GET  /keywords/<projeto_id>/api/grafico/<id> → JSON do gráfico de evolução
    GET  /keywords/<projeto_id>/api/stats        → JSON de estatísticas do painel
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
import db
from .providers import executar_rastreamento, PROVIDERS_INFO
from .gsc import bp_gsc
from .gsc import bp_gsc

bp = Blueprint("keywords", __name__)


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _get_projeto(projeto_id):
    """Retorna projeto verificando acesso do usuário."""
    return db.query_one(
        """SELECT p.* FROM projetos p
           WHERE p.id = %s AND p.tenant_id = %s AND p.D_E_L_E_T = 0""",
        (projeto_id, current_user.tenant_id)
    )


def _get_config(projeto_id):
    """Retorna config de fonte ou cria padrão (manual)."""
    config = db.query_one(
        "SELECT * FROM keyword_fonte_config WHERE projeto_id = %s",
        (projeto_id,)
    )
    if not config:
        db.execute(
            "INSERT INTO keyword_fonte_config (projeto_id, fonte) VALUES (%s, 'manual')",
            (projeto_id,)
        )
        config = db.query_one(
            "SELECT * FROM keyword_fonte_config WHERE projeto_id = %s",
            (projeto_id,)
        )
    return config


def _calcular_variacao(keyword_id):
    """Retorna variação entre as 2 últimas posições."""
    posicoes = db.query(
        """SELECT posicao FROM keyword_posicoes
           WHERE keyword_id = %s
           ORDER BY rastreado_em DESC LIMIT 2""",
        (keyword_id,)
    )
    if len(posicoes) < 2:
        return None
    p_atual    = posicoes[0]["posicao"]
    p_anterior = posicoes[1]["posicao"]
    if p_atual is None or p_anterior is None:
        return None
    return p_anterior - p_atual  # positivo = melhorou (subiu no ranking)


def _registrar_alerta(keyword_id, projeto_id, pos_anterior, pos_atual):
    """Cria alerta se variação for significativa (>= 5 posições)."""
    if pos_anterior is None or pos_atual is None:
        return
    variacao = pos_anterior - pos_atual
    if abs(variacao) < 5:
        return

    if variacao > 0:
        tipo = "entrada_top10" if pos_atual <= 10 and pos_anterior > 10 else "subida"
    else:
        tipo = "saiu_top10" if pos_anterior <= 10 and pos_atual > 10 else "queda"

    db.execute(
        """INSERT INTO keyword_alertas
           (keyword_id, projeto_id, tipo, posicao_anterior, posicao_atual, variacao)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (keyword_id, projeto_id, tipo, pos_anterior, pos_atual, variacao)
    )


# ─────────────────────────────────────────────────────────
# INDEX — Lista de keywords com última posição
# ─────────────────────────────────────────────────────────

@bp.route("/<int:projeto_id>")
@login_required
def index(projeto_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        flash("Projeto não encontrado.", "error")
        return redirect(url_for("dashboard.index"))

    config = _get_config(projeto_id)

    # Keywords com última posição
    keywords = db.query(
        """SELECT
               k.id, k.termo, k.url_alvo, k.grupo, k.pais,
               k.datestamp_insert,
               kp.posicao,
               kp.url_encontrada,
               kp.volume_busca,
               kp.dificuldade,
               kp.cpc,
               kp.fonte,
               kp.rastreado_em
           FROM keywords k
           LEFT JOIN LATERAL (
               SELECT posicao, url_encontrada, volume_busca, dificuldade, cpc, fonte, rastreado_em
               FROM keyword_posicoes
               WHERE keyword_id = k.id
               ORDER BY rastreado_em DESC
               LIMIT 1
           ) kp ON true
           WHERE k.projeto_id = %s AND k.D_E_L_E_T = 0 AND k.ativo = 1
           ORDER BY
               CASE WHEN kp.posicao IS NULL THEN 1 ELSE 0 END,
               kp.posicao ASC NULLS LAST,
               k.termo ASC""",
        (projeto_id,)
    )

    # Enriquecer com variação
    for kw in keywords:
        kw["variacao"] = _calcular_variacao(kw["id"])

    # Stats resumidas
    total        = len(keywords)
    top3         = sum(1 for k in keywords if k["posicao"] and k["posicao"] <= 3)
    top10        = sum(1 for k in keywords if k["posicao"] and k["posicao"] <= 10)
    sem_posicao  = sum(1 for k in keywords if k["posicao"] is None)

    # Grupos disponíveis
    grupos = sorted(set(k["grupo"] for k in keywords if k["grupo"]))

    # Alertas não lidos
    alertas = db.query(
        """SELECT ka.*, kw.termo FROM keyword_alertas ka
           JOIN keywords kw ON kw.id = ka.keyword_id
           WHERE ka.projeto_id = %s AND ka.lido = 0
           ORDER BY ka.datestamp_insert DESC LIMIT 10""",
        (projeto_id,)
    )

    return render_template(
        "keywords/index.html",
        projeto=projeto,
        keywords=keywords,
        config=config,
        providers_info=PROVIDERS_INFO,
        stats={
            "total": total,
            "top3": top3,
            "top10": top10,
            "sem_posicao": sem_posicao
        },
        grupos=grupos,
        alertas=alertas
    )


# ─────────────────────────────────────────────────────────
# SALVAR — Criar / Editar keyword
# ─────────────────────────────────────────────────────────

@bp.route("/<int:projeto_id>/salvar", methods=["POST"])
@login_required
def salvar(projeto_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        return jsonify({"ok": False, "erro": "Projeto não encontrado"}), 403

    d        = request.form
    kw_id    = d.get("id")
    termo    = d.get("termo", "").strip().lower()
    url_alvo = d.get("url_alvo", "").strip() or None
    grupo    = d.get("grupo", "").strip() or None
    pais     = d.get("pais", "br")

    if not termo:
        flash("Informe o termo da keyword.", "error")
        return redirect(url_for("keywords.index", projeto_id=projeto_id))

    if kw_id:
        db.execute(
            """UPDATE keywords
               SET termo=%s, url_alvo=%s, grupo=%s, pais=%s,
                   usuario_update=%s, datestamp_update=NOW()
               WHERE id=%s AND projeto_id=%s""",
            (termo, url_alvo, grupo, pais, current_user.id, kw_id, projeto_id)
        )
        flash(f'Keyword "{termo}" atualizada.', "success")
    else:
        # Verificar duplicata
        existe = db.query_one(
            "SELECT id FROM keywords WHERE projeto_id=%s AND termo=%s AND D_E_L_E_T=0",
            (projeto_id, termo)
        )
        if existe:
            flash(f'Keyword "{termo}" já cadastrada.', "warning")
        else:
            db.execute(
                """INSERT INTO keywords (tenant_id, projeto_id, termo, url_alvo, grupo, pais, usuario_insert)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (current_user.tenant_id, projeto_id, termo, url_alvo, grupo, pais, current_user.id)
            )
            flash(f'Keyword "{termo}" adicionada.', "success")

    return redirect(url_for("keywords.index", projeto_id=projeto_id))


# ─────────────────────────────────────────────────────────
# RASTREAR — Registrar posição de 1 keyword
# ─────────────────────────────────────────────────────────

@bp.route("/<int:projeto_id>/rastrear/<int:kw_id>", methods=["POST"])
@login_required
def rastrear(projeto_id, kw_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        return jsonify({"ok": False}), 403

    keyword = db.query_one(
        "SELECT * FROM keywords WHERE id=%s AND projeto_id=%s AND D_E_L_E_T=0",
        (kw_id, projeto_id)
    )
    if not keyword:
        return jsonify({"ok": False, "erro": "Keyword não encontrada"}), 404

    config        = _get_config(projeto_id)
    posicao_manual = request.form.get("posicao")
    posicao_manual = int(posicao_manual) if posicao_manual and posicao_manual.isdigit() else None

    # Adicionar domínio do projeto na config
    config_dict = dict(config)
    config_dict["dominio"] = projeto.get("url", "").replace("https://", "").replace("http://", "").split("/")[0]

    # Executar rastreamento
    resultado = executar_rastreamento(dict(keyword), config_dict, posicao_manual)

    # Buscar posição anterior para alerta
    pos_anterior_row = db.query_one(
        "SELECT posicao FROM keyword_posicoes WHERE keyword_id=%s ORDER BY rastreado_em DESC LIMIT 1",
        (kw_id,)
    )
    pos_anterior = pos_anterior_row["posicao"] if pos_anterior_row else None

    # Salvar resultado
    db.execute(
        """INSERT INTO keyword_posicoes
           (keyword_id, projeto_id, posicao, url_encontrada, volume_busca,
            dificuldade, cpc, fonte, raw_data)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            kw_id, projeto_id,
            resultado["posicao"],
            resultado["url_encontrada"],
            resultado["volume_busca"],
            resultado["dificuldade"],
            resultado["cpc"],
            resultado["fonte"],
            json.dumps(resultado["raw_data"])
        )
    )

    # Checar e registrar alerta
    if resultado["posicao"] is not None:
        _registrar_alerta(kw_id, projeto_id, pos_anterior, resultado["posicao"])

    return jsonify({
        "ok": True,
        "posicao": resultado["posicao"],
        "fonte": resultado["fonte"],
        "variacao": (_calcular_variacao(kw_id))
    })


# ─────────────────────────────────────────────────────────
# RASTREAR TODAS
# ─────────────────────────────────────────────────────────

@bp.route("/<int:projeto_id>/rastrear-todas", methods=["POST"])
@login_required
def rastrear_todas(projeto_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        return jsonify({"ok": False}), 403

    config = _get_config(projeto_id)
    if config["fonte"] == "manual":
        return jsonify({
            "ok": False,
            "erro": "Rastreamento em lote não disponível para fonte Manual. Use DataForSEO ou GSC."
        }), 400

    keywords = db.query(
        "SELECT * FROM keywords WHERE projeto_id=%s AND D_E_L_E_T=0 AND ativo=1",
        (projeto_id,)
    )

    config_dict = dict(config)
    config_dict["dominio"] = projeto.get("url", "").replace("https://", "").replace("http://", "").split("/")[0]

    resultados = []
    for kw in keywords:
        resultado = executar_rastreamento(dict(kw), config_dict)
        pos_anterior_row = db.query_one(
            "SELECT posicao FROM keyword_posicoes WHERE keyword_id=%s ORDER BY rastreado_em DESC LIMIT 1",
            (kw["id"],)
        )
        pos_anterior = pos_anterior_row["posicao"] if pos_anterior_row else None

        db.execute(
            """INSERT INTO keyword_posicoes
               (keyword_id, projeto_id, posicao, url_encontrada, volume_busca,
                dificuldade, cpc, fonte, raw_data)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                kw["id"], projeto_id,
                resultado["posicao"], resultado["url_encontrada"],
                resultado["volume_busca"], resultado["dificuldade"],
                resultado["cpc"], resultado["fonte"],
                json.dumps(resultado["raw_data"])
            )
        )
        if resultado["posicao"] is not None:
            _registrar_alerta(kw["id"], projeto_id, pos_anterior, resultado["posicao"])

        resultados.append({
            "keyword": kw["termo"],
            "posicao": resultado["posicao"],
            "fonte": resultado["fonte"]
        })

    return jsonify({"ok": True, "total": len(resultados), "resultados": resultados})


# ─────────────────────────────────────────────────────────
# DELETAR
# ─────────────────────────────────────────────────────────

@bp.route("/<int:projeto_id>/deletar/<int:kw_id>", methods=["POST"])
@login_required
def deletar(projeto_id, kw_id):
    db.execute(
        """UPDATE keywords SET D_E_L_E_T=1, usuario_update=%s, datestamp_update=NOW()
           WHERE id=%s AND projeto_id=%s""",
        (current_user.id, kw_id, projeto_id)
    )
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────
# HISTÓRICO — Evolução de 1 keyword
# ─────────────────────────────────────────────────────────

@bp.route("/<int:projeto_id>/historico/<int:kw_id>")
@login_required
def historico(projeto_id, kw_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        flash("Projeto não encontrado.", "error")
        return redirect(url_for("dashboard.index"))

    keyword = db.query_one(
        "SELECT * FROM keywords WHERE id=%s AND projeto_id=%s AND D_E_L_E_T=0",
        (kw_id, projeto_id)
    )
    if not keyword:
        flash("Keyword não encontrada.", "error")
        return redirect(url_for("keywords.index", projeto_id=projeto_id))

    posicoes = db.query(
        """SELECT posicao, url_encontrada, volume_busca, dificuldade, cpc, fonte, rastreado_em
           FROM keyword_posicoes
           WHERE keyword_id=%s
           ORDER BY rastreado_em ASC""",
        (kw_id,)
    )

    return render_template(
        "keywords/historico.html",
        projeto=projeto,
        keyword=keyword,
        posicoes=posicoes
    )


# ─────────────────────────────────────────────────────────
# API — Dados do gráfico (JSON)
# ─────────────────────────────────────────────────────────

@bp.route("/<int:projeto_id>/api/grafico/<int:kw_id>")
@login_required
def api_grafico(projeto_id, kw_id):
    dias = int(request.args.get("dias", 30))
    desde = datetime.utcnow() - timedelta(days=dias)

    posicoes = db.query(
        """SELECT posicao, rastreado_em
           FROM keyword_posicoes
           WHERE keyword_id=%s AND rastreado_em >= %s
           ORDER BY rastreado_em ASC""",
        (kw_id, desde)
    )

    labels    = [p["rastreado_em"].strftime("%d/%m") for p in posicoes]
    valores   = [p["posicao"] for p in posicoes]

    return jsonify({"labels": labels, "valores": valores})


# ─────────────────────────────────────────────────────────
# API — Estatísticas do painel (JSON)
# ─────────────────────────────────────────────────────────

@bp.route("/<int:projeto_id>/api/stats")
@login_required
def api_stats(projeto_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        return jsonify({}), 403

    keywords = db.query(
        """SELECT k.id, kp.posicao FROM keywords k
           LEFT JOIN LATERAL (
               SELECT posicao FROM keyword_posicoes
               WHERE keyword_id = k.id ORDER BY rastreado_em DESC LIMIT 1
           ) kp ON true
           WHERE k.projeto_id=%s AND k.D_E_L_E_T=0 AND k.ativo=1""",
        (projeto_id,)
    )

    total       = len(keywords)
    top3        = sum(1 for k in keywords if k["posicao"] and k["posicao"] <= 3)
    top10       = sum(1 for k in keywords if k["posicao"] and k["posicao"] <= 10)
    top30       = sum(1 for k in keywords if k["posicao"] and k["posicao"] <= 30)
    sem_posicao = sum(1 for k in keywords if k["posicao"] is None)

    return jsonify({
        "total": total,
        "top3": top3,
        "top10": top10,
        "top30": top30,
        "sem_posicao": sem_posicao
    })


# ─────────────────────────────────────────────────────────
# CONFIGURAÇÃO DE FONTE
# ─────────────────────────────────────────────────────────

@bp.route("/<int:projeto_id>/config")
@login_required
def config(projeto_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        flash("Projeto não encontrado.", "error")
        return redirect(url_for("dashboard.index"))

    cfg = _get_config(projeto_id)
    gsc_integracao = db.query_one(
        """SELECT * FROM api_integracoes
           WHERE tenant_id=%s AND projeto_id=%s
             AND provedor='google_gsc' AND ativo=1 AND d_e_l_e_t=0
           ORDER BY datestamp_insert DESC LIMIT 1""",
        (current_user.tenant_id, projeto_id)
    )
    return render_template(
        "keywords/config.html",
        projeto=projeto,
        config=cfg,
        providers_info=PROVIDERS_INFO,
        gsc_integracao=gsc_integracao
    )


@bp.route("/<int:projeto_id>/config/salvar", methods=["POST"])
@login_required
def config_salvar(projeto_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        return jsonify({"ok": False}), 403

    d = request.form
    gsc_url = d.get("gsc_property_url") or None
    if not gsc_url:
        cfg_atual = db.query_one("SELECT gsc_property_url FROM keyword_fonte_config WHERE projeto_id=%s", (projeto_id,))
        if cfg_atual:
            gsc_url = cfg_atual["gsc_property_url"]
    db.execute(
        """UPDATE keyword_fonte_config
           SET fonte=%s,
               gsc_property_url=%s,
               dataforseo_login=%s,
               dataforseo_password=%s,
               scraping_pais=%s,
               datestamp_update=NOW()
           WHERE projeto_id=%s""",
        (
            d.get("fonte", "manual"),
            gsc_url,
            d.get("dataforseo_login") or None,
            d.get("dataforseo_password") or None,
            d.get("scraping_pais", "br"),
            projeto_id
        )
    )
    flash("Configuração salva com sucesso.", "success")
    return redirect(url_for("keywords.config", projeto_id=projeto_id))


# ─────────────────────────────────────────────────────────
# MARCAR ALERTA COMO LIDO
# ─────────────────────────────────────────────────────────

@bp.route("/<int:projeto_id>/alertas/ler/<int:alerta_id>", methods=["POST"])
@login_required
def ler_alerta(projeto_id, alerta_id):
    db.execute(
        "UPDATE keyword_alertas SET lido=1 WHERE id=%s AND projeto_id=%s",
        (alerta_id, projeto_id)
    )
    return jsonify({"ok": True})

@bp.route("/<int:projeto_id>/logs")
@login_required
def logs(projeto_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        flash("Projeto não encontrado.", "error")
        return redirect(url_for("dashboard.index"))

    page     = int(request.args.get("p", 1))
    per_page = 50
    offset   = (page - 1) * per_page

    total_row = db.query_one(
        "SELECT COUNT(*) as total FROM keyword_posicoes WHERE projeto_id=%s",
        (projeto_id,)
    )
    total = total_row["total"] if total_row else 0

    logs = db.query(
        """SELECT kp.*, k.termo, k.grupo
           FROM keyword_posicoes kp
           JOIN keywords k ON k.id = kp.keyword_id
           WHERE kp.projeto_id=%s
           ORDER BY kp.rastreado_em DESC
           LIMIT %s OFFSET %s""",
        (projeto_id, per_page, offset)
    )

    return render_template(
        "keywords/logs.html",
        projeto=projeto,
        logs=logs,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=max(1, -(-total // per_page))
    )
