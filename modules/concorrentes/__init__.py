"""
modules/concorrentes/__init__.py

Módulo de análise de concorrentes — Selenio Analytics
Rotas:
    GET  /concorrentes/<projeto_id>                → index (tabela comparativa)
    POST /concorrentes/<projeto_id>/salvar         → criar/editar concorrente
    POST /concorrentes/<projeto_id>/deletar/<id>   → soft delete
    POST /concorrentes/<projeto_id>/rastrear/<id>  → registrar posição manual
    GET  /concorrentes/<projeto_id>/api/comparativo → JSON da tabela comparativa
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
import json
import db

bp = Blueprint("concorrentes", __name__)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_projeto(projeto_id):
    return db.query_one(
        """SELECT p.* FROM projetos p
           WHERE p.id = %s AND p.tenant_id = %s AND p.D_E_L_E_T = 0""",
        (projeto_id, current_user.tenant_id)
    )


def _get_concorrentes(projeto_id):
    return db.query(
        """SELECT * FROM concorrentes
           WHERE projeto_id=%s AND tenant_id=%s AND d_e_l_e_t=0 AND ativo=1
           ORDER BY nome""",
        (projeto_id, current_user.tenant_id)
    )


def _get_keywords(projeto_id):
    return db.query(
        """SELECT k.*, kp.posicao as minha_posicao, kp.rastreado_em
           FROM keywords k
           LEFT JOIN LATERAL (
               SELECT posicao, rastreado_em FROM keyword_posicoes
               WHERE keyword_id = k.id ORDER BY rastreado_em DESC LIMIT 1
           ) kp ON true
           WHERE k.projeto_id=%s AND k.d_e_l_e_t=0 AND k.ativo=1
           ORDER BY k.termo""",
        (projeto_id,)
    )


def _get_ultima_posicao_concorrente(concorrente_id, keyword_id):
    row = db.query_one(
        """SELECT posicao, url_ranqueada, data_coleta FROM concorrente_rankings
           WHERE concorrente_id=%s AND keyword_id=%s
           ORDER BY data_coleta DESC, datestamp_insert DESC LIMIT 1""",
        (concorrente_id, keyword_id)
    )
    return row


# ─────────────────────────────────────────────
# INDEX — Tabela comparativa
# ─────────────────────────────────────────────

@bp.route("/<int:projeto_id>")
@login_required
def index(projeto_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        flash("Projeto não encontrado.", "error")
        return redirect(url_for("dashboard.index"))

    concorrentes = _get_concorrentes(projeto_id)
    keywords     = _get_keywords(projeto_id)

    # Montar matriz comparativa
    # { keyword_id: { concorrente_id: { posicao, url } } }
    matriz = {}
    for kw in keywords:
        matriz[kw["id"]] = {}
        for c in concorrentes:
            pos = _get_ultima_posicao_concorrente(c["id"], kw["id"])
            matriz[kw["id"]][c["id"]] = pos

    # Stats
    total_keywords    = len(keywords)
    total_concorrentes = len(concorrentes)

    # Visibilidade — média de posições (quanto menor melhor)
    def calcular_visibilidade(posicoes):
        vals = [p for p in posicoes if p is not None and p <= 100]
        if not vals:
            return None
        # Score: 100 - média normalizada
        return round(100 - (sum(vals) / len(vals)), 1)

    minha_posicoes = [kw["minha_posicao"] for kw in keywords]
    minha_vis = calcular_visibilidade(minha_posicoes)

    vis_concorrentes = {}
    for c in concorrentes:
        posicoes = []
        for kw in keywords:
            pos_row = matriz.get(kw["id"], {}).get(c["id"])
            if pos_row:
                posicoes.append(pos_row["posicao"])
        vis_concorrentes[c["id"]] = calcular_visibilidade(posicoes)

    return render_template(
        "concorrentes/index.html",
        projeto=projeto,
        concorrentes=concorrentes,
        keywords=keywords,
        matriz=matriz,
        minha_vis=minha_vis,
        vis_concorrentes=vis_concorrentes,
        stats={
            "total_keywords":     total_keywords,
            "total_concorrentes": total_concorrentes,
        }
    )


# ─────────────────────────────────────────────
# SALVAR — Criar / Editar concorrente
# ─────────────────────────────────────────────

@bp.route("/<int:projeto_id>/salvar", methods=["POST"])
@login_required
def salvar(projeto_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        return jsonify({"ok": False}), 403

    d      = request.form
    c_id   = d.get("id")
    nome   = d.get("nome", "").strip()
    dominio = d.get("dominio", "").strip().lower()

    # Limpar domínio
    dominio = dominio.replace("https://", "").replace("http://", "").split("/")[0]

    if not dominio:
        flash("Informe o domínio do concorrente.", "error")
        return redirect(url_for("concorrentes.index", projeto_id=projeto_id))

    if not nome:
        nome = dominio

    if c_id:
        db.execute(
            """UPDATE concorrentes SET nome=%s, dominio=%s WHERE id=%s AND tenant_id=%s""",
            (nome, dominio, c_id, current_user.tenant_id)
        )
        flash(f'Concorrente "{nome}" atualizado.', "success")
    else:
        existe = db.query_one(
            "SELECT id FROM concorrentes WHERE projeto_id=%s AND dominio=%s AND d_e_l_e_t=0",
            (projeto_id, dominio)
        )
        if existe:
            flash(f'Domínio "{dominio}" já cadastrado.', "warning")
        else:
            db.execute(
                """INSERT INTO concorrentes (tenant_id, projeto_id, nome, dominio)
                   VALUES (%s,%s,%s,%s)""",
                (current_user.tenant_id, projeto_id, nome, dominio)
            )
            flash(f'Concorrente "{nome}" adicionado.', "success")

    return redirect(url_for("concorrentes.index", projeto_id=projeto_id))


# ─────────────────────────────────────────────
# DELETAR
# ─────────────────────────────────────────────

@bp.route("/<int:projeto_id>/deletar/<int:c_id>", methods=["POST"])
@login_required
def deletar(projeto_id, c_id):
    db.execute(
        "UPDATE concorrentes SET d_e_l_e_t=1 WHERE id=%s AND tenant_id=%s",
        (c_id, current_user.tenant_id)
    )
    return jsonify({"ok": True})


# ─────────────────────────────────────────────
# RASTREAR — Registrar posição manual
# ─────────────────────────────────────────────

@bp.route("/<int:projeto_id>/rastrear", methods=["POST"])
@login_required
def rastrear(projeto_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        return jsonify({"ok": False}), 403

    concorrente_id = request.form.get("concorrente_id")
    keyword_id     = request.form.get("keyword_id")
    posicao        = request.form.get("posicao")
    url_ranqueada  = request.form.get("url_ranqueada", "").strip() or None

    if not concorrente_id or not keyword_id:
        return jsonify({"ok": False, "erro": "Dados incompletos"}), 400

    posicao = int(posicao) if posicao and str(posicao).isdigit() else None

    db.execute(
        """INSERT INTO concorrente_rankings
           (tenant_id, concorrente_id, keyword_id, posicao, url_ranqueada, data_coleta)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (
            current_user.tenant_id,
            concorrente_id, keyword_id,
            posicao, url_ranqueada,
            date.today()
        )
    )

    return jsonify({
        "ok":     True,
        "posicao": posicao,
        "data":    date.today().strftime("%d/%m/%Y")
    })


# ─────────────────────────────────────────────
# API — Dados do comparativo (JSON)
# ─────────────────────────────────────────────

@bp.route("/<int:projeto_id>/api/comparativo")
@login_required
def api_comparativo(projeto_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        return jsonify({}), 403

    concorrentes = _get_concorrentes(projeto_id)
    keywords     = _get_keywords(projeto_id)

    resultado = []
    for kw in keywords:
        item = {
            "keyword":     kw["termo"],
            "grupo":       kw["grupo"],
            "minha_pos":   kw["minha_posicao"],
            "concorrentes": {}
        }
        for c in concorrentes:
            pos = _get_ultima_posicao_concorrente(c["id"], kw["id"])
            item["concorrentes"][c["dominio"]] = {
                "posicao": pos["posicao"] if pos else None,
                "url":     pos["url_ranqueada"] if pos else None,
            }
        resultado.append(item)

    return jsonify({
        "keywords":     resultado,
        "concorrentes": [{"id": c["id"], "nome": c["nome"], "dominio": c["dominio"]} for c in concorrentes]
    })


# ─────────────────────────────────────────────
# HISTÓRICO — Evolução de 1 concorrente
# ─────────────────────────────────────────────

@bp.route("/<int:projeto_id>/historico/<int:c_id>")
@login_required
def historico(projeto_id, c_id):
    projeto = _get_projeto(projeto_id)
    if not projeto:
        flash("Projeto não encontrado.", "error")
        return redirect(url_for("dashboard.index"))

    concorrente = db.query_one(
        "SELECT * FROM concorrentes WHERE id=%s AND tenant_id=%s AND d_e_l_e_t=0",
        (c_id, current_user.tenant_id)
    )
    if not concorrente:
        flash("Concorrente não encontrado.", "error")
        return redirect(url_for("concorrentes.index", projeto_id=projeto_id))

    rankings = db.query(
        """SELECT cr.*, k.termo FROM concorrente_rankings cr
           JOIN keywords k ON k.id = cr.keyword_id
           WHERE cr.concorrente_id=%s
           ORDER BY cr.data_coleta DESC, k.termo""",
        (c_id,)
    )

    return render_template(
        "concorrentes/historico.html",
        projeto=projeto,
        concorrente=concorrente,
        rankings=rankings
    )

# ─── SCRAPING ROUTES ───────────────────────────────────────────

@bp.route("/<int:projeto_id>/scraping/status")
@login_required
def scraping_status(projeto_id):
    import os
    modo = os.getenv("SCRAPING_MODO", "direto")
    return jsonify({
        "modo": modo,
        "modos": {
            "direto":     {"configurado": True,                          "custo": "Grátis"},
            "scraperapi": {"configurado": bool(os.getenv("SCRAPERAPI_KEY")), "custo": "$0.001/req"},
            "brightdata": {"configurado": bool(os.getenv("BRIGHTDATA_USER")), "custo": "Variável"}
        }
    })


@bp.route("/<int:projeto_id>/scraping/rastrear-keyword", methods=["POST"])
@login_required
def scraping_rastrear_keyword(projeto_id):
    from .scraper import rastrear_posicoes
    projeto = _get_projeto(projeto_id)
    if not projeto:
        return jsonify({"ok": False}), 403

    keyword_id = request.form.get("keyword_id")
    keyword = db.query_one(
        "SELECT * FROM keywords WHERE id=%s AND projeto_id=%s AND d_e_l_e_t=0",
        (keyword_id, projeto_id)
    )
    if not keyword:
        return jsonify({"ok": False, "erro": "Keyword não encontrada"}), 404

    concorrentes = _get_concorrentes(projeto_id)
    meu_dominio  = projeto.get("dominio", "").replace("https://","").replace("http://","").replace("www.","").split("/")[0].strip()
    dominios     = [c["dominio"] for c in concorrentes]

    resultado = rastrear_posicoes(
        keyword=keyword["termo"],
        meu_dominio=meu_dominio,
        dominios_concorrentes=dominios,
        pais=keyword.get("pais", "br")
    )

    if not resultado["ok"]:
        return jsonify({"ok": False, "erro": resultado["erro"]}), 500

    if resultado["meu_site"]["posicao"]:
        db.execute(
            """INSERT INTO keyword_posicoes
               (keyword_id, projeto_id, posicao, url_encontrada, fonte, raw_data)
               VALUES (%s,%s,%s,%s,'scraping','{}')""",
            (keyword["id"], projeto_id, resultado["meu_site"]["posicao"], resultado["meu_site"]["url"])
        )

    salvos = {}
    for c in concorrentes:
        pos_data = resultado["concorrentes"].get(c["dominio"], {})
        db.execute(
            """INSERT INTO concorrente_rankings
               (tenant_id, concorrente_id, keyword_id, posicao, url_ranqueada, data_coleta)
               VALUES (%s,%s,%s,%s,%s,CURRENT_DATE)""",
            (current_user.tenant_id, c["id"], keyword["id"], pos_data.get("posicao"), pos_data.get("url"))
        )
        salvos[c["dominio"]] = pos_data

    return jsonify({
        "ok": True, "keyword": keyword["termo"],
        "meu_site": resultado["meu_site"],
        "concorrentes": salvos,
        "total": len(resultado["resultados"])
    })


@bp.route("/<int:projeto_id>/scraping/rastrear-todas", methods=["POST"])
@login_required
def scraping_rastrear_todas(projeto_id):
    from .scraper import rastrear_projeto
    projeto      = _get_projeto(projeto_id)
    keywords     = _get_keywords(projeto_id)
    concorrentes = _get_concorrentes(projeto_id)

    if not projeto or not keywords or not concorrentes:
        return jsonify({"ok": False, "erro": "Projeto, keywords ou concorrentes não encontrados"}), 400

    meu_dominio = projeto.get("dominio", "").replace("https://","").replace("http://","").replace("www.","").split("/")[0].strip()
    termos  = [kw["termo"] for kw in keywords]
    dominios = [c["dominio"] for c in concorrentes]
    kw_map  = {kw["termo"]: kw["id"] for kw in keywords}
    c_map   = {c["dominio"]: c["id"] for c in concorrentes}

    resultados  = rastrear_projeto(keywords=termos, meu_dominio=meu_dominio, dominios_concorrentes=dominios)
    total_ok = 0

    for res in resultados:
        if not res["ok"]:
            continue
        kw_id = kw_map.get(res["keyword"])
        if kw_id and res["meu_site"]["posicao"]:
            db.execute(
                """INSERT INTO keyword_posicoes
                   (keyword_id, projeto_id, posicao, url_encontrada, fonte, raw_data)
                   VALUES (%s,%s,%s,%s,'scraping','{}')""",
                (kw_id, projeto_id, res["meu_site"]["posicao"], res["meu_site"]["url"])
            )
        for dom, pos_data in res["concorrentes"].items():
            c_id = c_map.get(dom)
            if c_id and kw_id:
                db.execute(
                    """INSERT INTO concorrente_rankings
                       (tenant_id, concorrente_id, keyword_id, posicao, url_ranqueada, data_coleta)
                       VALUES (%s,%s,%s,%s,%s,CURRENT_DATE)""",
                    (current_user.tenant_id, c_id, kw_id, pos_data.get("posicao"), pos_data.get("url"))
                )
        total_ok += 1

    return jsonify({"ok": True, "total": len(resultados), "sucesso": total_ok})


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
        """SELECT COUNT(*) as total FROM concorrente_rankings cr
           JOIN concorrentes c ON c.id = cr.concorrente_id
           WHERE c.projeto_id=%s AND c.tenant_id=%s""",
        (projeto_id, current_user.tenant_id)
    )
    total = total_row["total"] if total_row else 0

    logs = db.query(
        """SELECT cr.*, c.nome as conc_nome, c.dominio, k.termo
           FROM concorrente_rankings cr
           JOIN concorrentes c ON c.id = cr.concorrente_id
           JOIN keywords k ON k.id = cr.keyword_id
           WHERE c.projeto_id=%s AND c.tenant_id=%s
           ORDER BY cr.datestamp_insert DESC
           LIMIT %s OFFSET %s""",
        (projeto_id, current_user.tenant_id, per_page, offset)
    )

    return render_template(
        "concorrentes/logs.html",
        projeto=projeto,
        logs=logs,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=max(1, -(-total // per_page))
    )


@bp.route("/<int:projeto_id>/gemini/rastrear-todas", methods=["POST"])
@login_required
def gemini_rastrear_todas(projeto_id):
    """Rastreia todas as keywords via Gemini + Google Search."""
    from .gemini_provider import rastrear_projeto_gemini
    import json as _json

    projeto      = _get_projeto(projeto_id)
    keywords     = _get_keywords(projeto_id)
    concorrentes = _get_concorrentes(projeto_id)

    if not projeto or not keywords or not concorrentes:
        return jsonify({"ok": False, "erro": "Projeto, keywords ou concorrentes não encontrados"}), 400

    meu_dominio = projeto.get("dominio", "").replace("https://","").replace("http://","").replace("www.","").split("/")[0].strip()
    termos      = [kw["termo"] for kw in keywords]
    dominios    = [c["dominio"] for c in concorrentes]
    kw_map      = {kw["termo"]: kw["id"] for kw in keywords}
    c_map       = {c["dominio"]: c["id"] for c in concorrentes}

    resultados  = rastrear_projeto_gemini(
        keywords=termos,
        meu_dominio=meu_dominio,
        dominios_concorrentes=dominios,
        delay=5.0
    )

    total_ok = 0
    erros    = []

    for res in resultados:
        if not res["ok"]:
            erros.append(f"{res['keyword']}: {res.get('erro','')}")
            continue

        kw_id = kw_map.get(res["keyword"])

        # Salvar meu site
        if kw_id and res["meu_site"]["posicao"]:
            db.execute(
                """INSERT INTO keyword_posicoes
                   (keyword_id, projeto_id, posicao, url_encontrada, fonte, raw_data)
                   VALUES (%s,%s,%s,%s,'gemini','{}')""",
                (kw_id, projeto_id, res["meu_site"]["posicao"], res["meu_site"]["url"])
            )

        # Salvar concorrentes
        for dom, pos_data in res["concorrentes"].items():
            c_id = c_map.get(dom)
            if c_id and kw_id:
                db.execute(
                    """INSERT INTO concorrente_rankings
                       (tenant_id, concorrente_id, keyword_id, posicao, url_ranqueada, data_coleta)
                       VALUES (%s,%s,%s,%s,%s,CURRENT_DATE)""",
                    (current_user.tenant_id, c_id, kw_id, pos_data.get("posicao"), pos_data.get("url"))
                )

        total_ok += 1

    return jsonify({
        "ok":      True,
        "total":   len(resultados),
        "sucesso": total_ok,
        "erros":   erros
    })
