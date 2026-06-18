from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g
from flask_login import login_required, current_user
import db

bp = Blueprint("seo", __name__)

def _projeto_do_tenant(projeto_id):
    """Garante que o projeto pertence ao tenant do usuário logado."""
    return db.query_one_t(
        current_user.tenant_id,
        "SELECT * FROM projetos WHERE id=%s AND tenant_id=%s AND D_E_L_E_T=0",
        (projeto_id,)
    )

# ── Painel SEO ────────────────────────────────────────────────
@bp.route("/<int:projeto_id>")
@login_required
def painel(projeto_id):
    from integrations import gsc, serpapi, audit
    tid     = current_user.tenant_id
    projeto = _projeto_do_tenant(projeto_id)
    if not projeto:
        flash("Projeto não encontrado.", "danger")
        return redirect(url_for("dashboard.index"))

    keywords  = serpapi.ranking_atual(tid, projeto_id)
    resumo    = gsc.resumo_gsc(tid, projeto_id)
    top_q     = gsc.top_queries(tid, projeto_id, limite=10)
    audits    = audit.ultimas_auditorias(tid, projeto_id, limite=8)
    alertas   = db.query_t(tid,
        "SELECT * FROM alertas WHERE tenant_id=%s AND projeto_id=%s AND lido=0 ORDER BY datestamp_insert DESC LIMIT 5",
        (projeto_id,)
    )
    tend      = gsc.tendencia_cliques(tid, projeto_id)
    tend_labels  = [str(r["data_ref"]) for r in tend]
    tend_cliques = [r["cliques"] for r in tend]

    return render_template("seo/painel.html",
        projeto=projeto,
        keywords=keywords,
        resumo=resumo,
        top_queries=top_q,
        audits=audits,
        alertas=alertas,
        tend_labels=tend_labels,
        tend_cliques=tend_cliques,
    )

# ── Keywords ──────────────────────────────────────────────────
@bp.route("/<int:projeto_id>/keywords")
@login_required
def keywords(projeto_id):
    from integrations import serpapi
    tid     = current_user.tenant_id
    projeto = _projeto_do_tenant(projeto_id)
    if not projeto:
        return redirect(url_for("dashboard.index"))
    kws = serpapi.ranking_atual(tid, projeto_id)
    return render_template("seo/keywords.html", projeto=projeto, keywords=kws)

@bp.route("/<int:projeto_id>/keywords/adicionar", methods=["POST"])
@login_required
def adicionar_keyword(projeto_id):
    tid   = current_user.tenant_id
    termo = request.form.get("termo","").strip().lower()
    if termo:
        if not db.dentro_do_limite(tid, "keywords"):
            flash("Limite de keywords do plano atingido. Faça upgrade.", "danger")
            return redirect(url_for("seo.keywords", projeto_id=projeto_id))
        db.execute_t(tid,
            "INSERT INTO keywords (tenant_id, projeto_id, termo) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            (projeto_id, termo)
        )
        flash(f"Keyword '{termo}' adicionada.", "success")
    return redirect(url_for("seo.keywords", projeto_id=projeto_id))

@bp.route("/<int:projeto_id>/keywords/<int:kw_id>/remover")
@login_required
def remover_keyword(projeto_id, kw_id):
    tid = current_user.tenant_id
    db.execute_t(tid,
        "UPDATE keywords SET D_E_L_E_T=1 WHERE id=%s AND projeto_id=%s AND tenant_id=%s",
        (kw_id, projeto_id)
    )
    flash("Keyword removida.", "success")
    return redirect(url_for("seo.keywords", projeto_id=projeto_id))

# ── Auditoria ─────────────────────────────────────────────────
@bp.route("/<int:projeto_id>/auditoria")
@login_required
def auditoria(projeto_id):
    from integrations import audit
    tid     = current_user.tenant_id
    projeto = _projeto_do_tenant(projeto_id)
    if not projeto:
        return redirect(url_for("dashboard.index"))
    audits = audit.ultimas_auditorias(tid, projeto_id, limite=20)
    return render_template("seo/auditoria.html", projeto=projeto, audits=audits)

@bp.route("/<int:projeto_id>/auditoria/rodar", methods=["POST"])
@login_required
def rodar_auditoria(projeto_id):
    from integrations import audit
    tid = current_user.tenant_id
    url = request.form.get("url","").strip()
    if url:
        r = audit.auditar_url(url, projeto_id, tid)
        flash(f"Auditoria concluída — Score: {r['score']}/100", "success")
    return redirect(url_for("seo.auditoria", projeto_id=projeto_id))

# ── Gaps de concorrentes ──────────────────────────────────────
@bp.route("/<int:projeto_id>/gaps")
@login_required
def gaps(projeto_id):
    from integrations import serpapi
    tid     = current_user.tenant_id
    projeto = _projeto_do_tenant(projeto_id)
    if not projeto:
        return redirect(url_for("dashboard.index"))
    gaps    = serpapi.gaps_concorrentes(tid, projeto_id)
    concs   = db.query_t(tid,
        "SELECT * FROM concorrentes WHERE tenant_id=%s AND projeto_id=%s AND D_E_L_E_T=0",
        (projeto_id,)
    )
    return render_template("seo/gaps.html",
        projeto=projeto, gaps=gaps, concorrentes=concs)

@bp.route("/<int:projeto_id>/concorrentes/adicionar", methods=["POST"])
@login_required
def adicionar_concorrente(projeto_id):
    tid    = current_user.tenant_id
    nome   = request.form.get("nome","").strip()
    domain = request.form.get("dominio","").strip()
    if nome and domain:
        db.execute_t(tid,
            "INSERT INTO concorrentes (tenant_id, projeto_id, nome, dominio) VALUES (%s,%s,%s,%s)",
            (projeto_id, nome, domain)
        )
        flash(f"Concorrente '{nome}' adicionado.", "success")
    return redirect(url_for("seo.gaps", projeto_id=projeto_id))

@bp.route("/<int:projeto_id>/coletar", methods=["POST"])
@login_required
def coletar_agora(projeto_id):
    from integrations import serpapi
    tid = current_user.tenant_id
    r   = serpapi.coletar_rankings(tid, projeto_id)
    flash(f"Coleta concluída: {r.get('keywords_coletadas',0)} keywords.", "success")
    return redirect(url_for("seo.painel", projeto_id=projeto_id))
