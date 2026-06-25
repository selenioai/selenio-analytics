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
