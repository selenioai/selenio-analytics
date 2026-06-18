"""
tenant_middleware.py
Injeta g.tenant_id e g.tenant em todo request autenticado.
Também verifica se o tenant está ativo e o plano não expirou.
"""
from flask import g, redirect, url_for, flash
from flask_login import current_user
import auth as auth_module
import db

def init_tenant_middleware(app):

    @app.before_request
    def load_tenant():
        g.tenant_id = None
        g.tenant    = None
        g.plano     = None

        if current_user.is_authenticated:
            g.tenant_id = current_user.tenant_id
            g.tenant    = auth_module.get_tenant(current_user.tenant_id)
            g.plano     = g.tenant  # plano já vem junto no JOIN

    @app.before_request
    def check_tenant_active():
        """Bloqueia acesso se tenant suspenso (exceto superadmin)."""
        from flask import request
        if not current_user.is_authenticated:
            return
        if current_user.is_superadmin:
            return
        if request.endpoint in ("login", "logout", "static", "billing.planos",
                                 "billing.sucesso", "billing.cancelado"):
            return
        if g.tenant and g.tenant["status"] == "suspended":
            flash("Conta suspensa. Entre em contato com o suporte.", "danger")
            return redirect(url_for("billing.planos"))

    @app.context_processor
    def inject_tenant_globals():
        total_alertas = 0
        if current_user.is_authenticated and g.tenant_id:
            row = db.query_one_t(g.tenant_id,
                "SELECT COUNT(*) AS n FROM alertas WHERE lido=0 AND tenant_id=%s")
            total_alertas = row["n"] if row else 0
        return {
            "total_alertas": total_alertas,
            "tenant":        g.tenant,
            "plano":         g.plano,
        }
