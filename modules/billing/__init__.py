"""
Billing & Gestão de Assentos — modelo por usuário (seat-based).
Permite ao owner do tenant adicionar/remover usuários e ver o custo.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from flask_login import login_required, current_user
from functools import wraps
import secrets
import db

bp = Blueprint("billing", __name__)

def owner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_owner:
            flash("Apenas o proprietário pode acessar esta área.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated

# ── Painel de assinaturas / assentos ────────────────────────
@bp.route("/")
@login_required
@owner_required
def index():
    tid = current_user.tenant_id
    tenant    = g.tenant
    assinatura = db.query_one(
        "SELECT * FROM assinaturas WHERE tenant_id=%s AND status='active' ORDER BY id DESC LIMIT 1",
        (tid,)
    )
    usuarios = db.query_t(tid,
        "SELECT * FROM usuarios WHERE tenant_id=%s AND D_E_L_E_T=0 ORDER BY nome")
    convites = db.query_t(tid,
        "SELECT * FROM convites WHERE tenant_id=%s AND aceito=0 AND expira_em > NOW() ORDER BY datestamp_insert DESC")
    plano    = db.plano_do_tenant(tid)

    assentos_usados   = len([u for u in usuarios if u["ativo"] == 1])
    assentos_total    = tenant["assentos_contratados"]
    custo_atual       = assentos_usados * (plano["preco_por_assento"] if plano else 0)

    return render_template("billing/index.html",
        tenant=tenant,
        assinatura=assinatura,
        usuarios=usuarios,
        convites=convites,
        plano=plano,
        assentos_usados=assentos_usados,
        assentos_total=assentos_total,
        custo_atual=custo_atual,
    )

# ── Convidar usuário ─────────────────────────────────────────
@bp.route("/convidar", methods=["POST"])
@login_required
@owner_required
def convidar():
    tid   = current_user.tenant_id
    email = request.form.get("email","").strip().lower()
    role  = request.form.get("role","member")

    if not db.dentro_do_limite(tid, "usuarios"):
        flash("Limite de usuários do plano atingido. Faça upgrade para adicionar mais assentos.", "danger")
        return redirect(url_for("billing.index"))

    # Verifica se já existe
    existente = db.query_one("SELECT id FROM usuarios WHERE email=%s", (email,))
    if existente:
        flash("Este e-mail já possui uma conta.", "warning")
        return redirect(url_for("billing.index"))

    token = secrets.token_urlsafe(32)
    db.execute("""
        INSERT INTO convites (tenant_id, email, role, token, convidado_por)
        VALUES (%s,%s,%s,%s,%s)
    """, (tid, email, role, token, current_user.id))

    # Em produção: enviar e-mail com link de convite
    # Por ora, mostra o link na tela
    link = url_for("billing.aceitar_convite", token=token, _external=True)
    flash(f"Convite gerado! Link: {link}", "success")
    return redirect(url_for("billing.index"))

# ── Aceitar convite ──────────────────────────────────────────
@bp.route("/convite/<token>", methods=["GET","POST"])
def aceitar_convite(token):
    from flask_bcrypt import Bcrypt
    bcrypt = Bcrypt()

    convite = db.query_one(
        "SELECT * FROM convites WHERE token=%s AND aceito=0 AND expira_em > NOW()",
        (token,)
    )
    if not convite:
        flash("Convite inválido ou expirado.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        nome  = request.form.get("nome","").strip()
        senha = request.form.get("senha","")
        if len(senha) < 8:
            flash("A senha deve ter pelo menos 8 caracteres.", "danger")
            return render_template("billing/aceitar_convite.html", convite=convite)

        senha_hash = bcrypt.generate_password_hash(senha).decode("utf-8")
        db.execute("""
            INSERT INTO usuarios (tenant_id, nome, email, senha_hash, role)
            VALUES (%s,%s,%s,%s,%s)
        """, (convite["tenant_id"], nome, convite["email"], senha_hash, convite["role"]))

        db.execute("UPDATE convites SET aceito=1 WHERE id=%s", (convite["id"],))
        flash("Conta criada! Faça login.", "success")
        return redirect(url_for("login"))

    return render_template("billing/aceitar_convite.html", convite=convite)

# ── Remover usuário (desativa assento) ───────────────────────
@bp.route("/usuarios/<int:user_id>/remover")
@login_required
@owner_required
def remover_usuario(user_id):
    tid = current_user.tenant_id
    if user_id == current_user.id:
        flash("Você não pode remover sua própria conta.", "danger")
        return redirect(url_for("billing.index"))
    db.execute_t(tid,
        "UPDATE usuarios SET ativo=0, D_E_L_E_T=1 WHERE id=%s AND tenant_id=%s",
        (user_id,)
    )
    flash("Usuário removido. Assento liberado.", "success")
    return redirect(url_for("billing.index"))

# ── Alterar role ─────────────────────────────────────────────
@bp.route("/usuarios/<int:user_id>/role", methods=["POST"])
@login_required
@owner_required
def alterar_role(user_id):
    tid  = current_user.tenant_id
    role = request.form.get("role","member")
    if role not in ("admin","member","viewer"):
        flash("Role inválido.", "danger")
        return redirect(url_for("billing.index"))
    db.execute_t(tid,
        "UPDATE usuarios SET role=%s WHERE id=%s AND tenant_id=%s",
        (role, user_id)
    )
    flash("Permissão atualizada.", "success")
    return redirect(url_for("billing.index"))

# ── Planos disponíveis ───────────────────────────────────────
@bp.route("/planos")
def planos():
    planos = db.query("SELECT * FROM planos WHERE ativo=1 ORDER BY preco_por_assento")
    return render_template("billing/planos.html", planos=planos)
