from flask import Blueprint, render_template, redirect, url_for, request, flash, g
from flask_login import login_required, current_user
import db

bp = Blueprint("dashboard", __name__)

@bp.route("/")
@login_required
def index():
    tid      = current_user.tenant_id
    projetos = db.query_t(tid,
        "SELECT * FROM projetos WHERE tenant_id=%s AND D_E_L_E_T=0 ORDER BY nome")
    if not projetos:
        return render_template("dashboard/sem_projeto.html")
    if len(projetos) == 1:
        return redirect(url_for("seo.painel", projeto_id=projetos[0]["id"]))
    return render_template("dashboard/index.html", projetos=projetos)

@bp.route("/projetos/novo", methods=["GET","POST"])
@login_required
def novo_projeto():
    tid = current_user.tenant_id
    if not db.dentro_do_limite(tid, "projetos"):
        flash("Limite de projetos do plano atingido. Faça upgrade.", "danger")
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        d = request.form
        row = db.execute("""
            INSERT INTO projetos
                (tenant_id, usuario_id, nome, dominio, gsc_site_url,
                 ga4_property_id, meta_page_id, linkedin_org_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (
            tid,
            current_user.id,
            d.get("nome"), d.get("dominio"), d.get("gsc_site_url"),
            d.get("ga4_property_id"), d.get("meta_page_id"), d.get("linkedin_org_id"),
        ))
        flash("Projeto criado!", "success")
        return redirect(url_for("seo.painel", projeto_id=row["id"]))
    return render_template("dashboard/novo_projeto.html")
