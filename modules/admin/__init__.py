"""
Painel Super Admin — visível apenas para role='superadmin'.
Gerencia todos os tenants, planos e métricas de uso do SaaS.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from flask_login import login_required, current_user
from functools import wraps
import db

bp = Blueprint("admin", __name__)

def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superadmin:
            flash("Acesso restrito.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated

# ── Visão geral do SaaS ──────────────────────────────────────
@bp.route("/")
@login_required
@superadmin_required
def index():
    tenants = db.query("""
        SELECT t.*, p.nome AS plano_nome,
               (SELECT COUNT(*) FROM usuarios u WHERE u.tenant_id=t.id AND u.ativo=1 AND u.D_E_L_E_T=0) AS total_usuarios,
               (SELECT COUNT(*) FROM projetos pr WHERE pr.tenant_id=t.id AND pr.D_E_L_E_T=0) AS total_projetos
        FROM tenants t
        JOIN planos p ON p.id = t.plano_id
        WHERE t.D_E_L_E_T = 0
        ORDER BY t.datestamp_insert DESC
    """)
    stats = db.query_one("""
        SELECT
            COUNT(DISTINCT t.id)                              AS total_tenants,
            COUNT(DISTINCT u.id)                              AS total_usuarios,
            SUM(t.assentos_contratados * p.preco_por_assento) AS mrr
        FROM tenants t
        JOIN planos p ON p.id = t.plano_id
        JOIN usuarios u ON u.tenant_id = t.id
        WHERE t.status = 'active' AND t.ativo = 1
    """)
    return render_template("admin/index.html", tenants=tenants, stats=stats)

# ── Criar novo tenant (onboarding manual) ───────────────────
@bp.route("/tenants/novo", methods=["GET","POST"])
@login_required
@superadmin_required
def novo_tenant():
    from flask_bcrypt import Bcrypt
    bcrypt = Bcrypt()
    planos = db.query("SELECT * FROM planos WHERE ativo=1 ORDER BY preco_por_assento")

    if request.method == "POST":
        d = request.form
        # Cria tenant
        t = db.execute("""
            INSERT INTO tenants (slug, nome, email_admin, plano_id,
                                 status, assentos_contratados)
            VALUES (%s,%s,%s,%s,'active',%s) RETURNING id
        """, (
            d["slug"].lower().strip(),
            d["nome"], d["email_admin"],
            d["plano_id"], int(d.get("assentos", 1))
        ))
        tenant_id = t["id"]

        # Cria usuário owner
        senha_hash = bcrypt.generate_password_hash(d["senha"]).decode("utf-8")
        db.execute("""
            INSERT INTO usuarios (tenant_id, nome, email, senha_hash, role)
            VALUES (%s,%s,%s,%s,'owner')
        """, (tenant_id, d["nome_admin"], d["email_admin"], senha_hash))

        # Registra assinatura
        db.execute("""
            INSERT INTO assinaturas (tenant_id, plano_id, assentos, valor_mensal, status)
            SELECT %s, %s, %s, (p.preco_por_assento * %s), 'active'
            FROM planos p WHERE p.id = %s
        """, (tenant_id, d["plano_id"], d["assentos"],
              d["assentos"], d["plano_id"]))

        flash(f"Tenant '{d['nome']}' criado com sucesso!", "success")
        return redirect(url_for("admin.index"))

    return render_template("admin/novo_tenant.html", planos=planos)

# ── Detalhe de um tenant ─────────────────────────────────────
@bp.route("/tenants/<int:tenant_id>")
@login_required
@superadmin_required
def detalhe_tenant(tenant_id):
    tenant   = db.query_one("SELECT * FROM tenants WHERE id=%s", (tenant_id,))
    usuarios = db.query_t(tenant_id,
        "SELECT * FROM usuarios WHERE tenant_id=%s AND D_E_L_E_T=0 ORDER BY nome")
    projetos = db.query_t(tenant_id,
        "SELECT * FROM projetos WHERE tenant_id=%s AND D_E_L_E_T=0 ORDER BY nome")
    uso      = db.query(
        "SELECT * FROM uso_mensal WHERE tenant_id=%s ORDER BY mes_ref DESC LIMIT 6",
        (tenant_id,)
    )
    return render_template("admin/detalhe_tenant.html",
        tenant=tenant, usuarios=usuarios, projetos=projetos, uso=uso)

# ── Suspender / reativar tenant ──────────────────────────────
@bp.route("/tenants/<int:tenant_id>/status/<acao>")
@login_required
@superadmin_required
def alterar_status(tenant_id, acao):
    status = "suspended" if acao == "suspender" else "active"
    db.execute("UPDATE tenants SET status=%s WHERE id=%s", (status, tenant_id))
    flash(f"Tenant {'suspenso' if acao=='suspender' else 'reativado'}.", "success")
    return redirect(url_for("admin.detalhe_tenant", tenant_id=tenant_id))
