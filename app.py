from flask import Flask, render_template, redirect, url_for, request, flash, g
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os, json, datetime
import db
import auth as auth_module

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-change-me-in-production")

bcrypt    = Bcrypt(app)
login_mgr = LoginManager(app)
login_mgr.login_view    = "login"
login_mgr.login_message = "Faça login para continuar."

# ── Filtros Jinja2 ────────────────────────────────────────────
@app.template_filter("from_json")
def from_json(s):
    try: return json.loads(s) if s else []
    except: return []

@app.template_filter("format_number")
def format_number(n):
    try: return f"{int(n):,}".replace(",",".")
    except: return "0"

@app.template_filter("format_currency")
def format_currency(n):
    try: return f"R$ {float(n):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except: return "R$ 0,00"

# ── Banco ────────────────────────────────────────────────────
with app.app_context():
    try:
        db.init_db()
        print("[DB] Schema multi-tenant inicializado.")
    except Exception as e:
        print(f"[DB] Aviso: {e}")

# ── Blueprints ────────────────────────────────────────────────
from modules.dashboard      import bp as bp_dash
from modules.seo            import bp as bp_seo
from modules.keywords       import bp as bp_keywords
from modules.billing        import bp as bp_billing
from modules.admin          import bp as bp_admin
from modules.configuracoes  import bp as bp_config

app.register_blueprint(bp_dash,    url_prefix="/dashboard")
app.register_blueprint(bp_seo,     url_prefix="/seo")
app.register_blueprint(bp_keywords, url_prefix="/keywords")
app.register_blueprint(bp_billing, url_prefix="/billing")
app.register_blueprint(bp_admin,   url_prefix="/admin")
app.register_blueprint(bp_config,  url_prefix="/configuracoes")

# ── Middleware de tenant ──────────────────────────────────────
from tenant_middleware import init_tenant_middleware
init_tenant_middleware(app)

# ── Scheduler ─────────────────────────────────────────────────
from scheduler import init_scheduler
init_scheduler(app)

# ── Auth ──────────────────────────────────────────────────────
@login_mgr.user_loader
def load_user(user_id):
    return auth_module.get_user(int(user_id))

@app.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        senha = request.form.get("senha","")
        row   = auth_module.get_user_by_email(email)
        if row and bcrypt.check_password_hash(row["senha_hash"], senha):
            db.execute("UPDATE usuarios SET ultimo_login=NOW() WHERE id=%s", (row["id"],))
            login_user(auth_module.Usuario(row), remember=True)
            return redirect(request.args.get("next") or url_for("dashboard.index"))
        flash("E-mail ou senha incorretos.", "danger")
    return render_template("auth/login.html")

@app.route("/registro", methods=["GET","POST"])
def registro():
    """Self-service: cria tenant + owner em trial de 14 dias."""
    planos = db.query("SELECT * FROM planos WHERE ativo=1 ORDER BY preco_por_assento")
    if request.method == "POST":
        d     = request.form
        slug  = d.get("empresa","").lower().strip().replace(" ","-")
        email = d.get("email","").strip().lower()

        # Verifica duplicidade
        if db.query_one("SELECT id FROM tenants WHERE slug=%s OR email_admin=%s", (slug, email)):
            flash("Empresa ou e-mail já cadastrado.", "danger")
            return render_template("auth/registro.html", planos=planos)

        plano_id = int(d.get("plano_id", 1))

        # Cria tenant em trial
        t = db.execute("""
            INSERT INTO tenants (slug, nome, email_admin, plano_id, status, assentos_contratados)
            VALUES (%s,%s,%s,%s,'trial',1) RETURNING id
        """, (slug, d.get("empresa"), email, plano_id))

        # Cria owner
        senha_hash = bcrypt.generate_password_hash(d.get("senha","")).decode("utf-8")
        db.execute("""
            INSERT INTO usuarios (tenant_id, nome, email, senha_hash, role)
            VALUES (%s,%s,%s,%s,'owner')
        """, (t["id"], d.get("nome"), email, senha_hash))

        flash("Conta criada! Você tem 14 dias de trial gratuito.", "success")
        return redirect(url_for("login"))
    return render_template("auth/registro.html", planos=planos)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
def root():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("login"))

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

@app.context_processor
def inject_projeto():
    from flask_login import current_user
    if current_user.is_authenticated:
        projeto = db.query_one(
            "SELECT * FROM projetos WHERE tenant_id=%s AND D_E_L_E_T=0 ORDER BY nome LIMIT 1",
            (current_user.tenant_id,)
        )
        return {"projeto": projeto}
    return {"projeto": None}
