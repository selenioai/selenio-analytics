"""
permissions.py
Sistema de permissões por role e tela.
Uso: @requer_permissao('config.apis_sociais', 'ver')
"""
from functools import wraps
from flask import redirect, url_for, flash, g
from flask_login import current_user
import db

# ── Permissões padrão por role ────────────────────────────────────
PERMISSOES_PADRAO = {
    "owner": {
        "pode_ver": 1, "pode_editar": 1, "pode_criar": 1, "pode_deletar": 1,
        "telas": [
            "seo.painel", "seo.keywords", "seo.auditoria", "seo.concorrentes",
            "social.painel", "social.instagram", "social.facebook", "social.linkedin",
            "config.geral", "config.apis_sociais", "config.usuarios",
        ]
    },
    "admin": {
        "pode_ver": 1, "pode_editar": 1, "pode_criar": 1, "pode_deletar": 0,
        "telas": [
            "seo.painel", "seo.keywords", "seo.auditoria", "seo.concorrentes",
            "social.painel", "social.instagram", "social.facebook", "social.linkedin",
            "config.geral", "config.apis_sociais",
        ]
    },
    "member": {
        "pode_ver": 1, "pode_editar": 1, "pode_criar": 1, "pode_deletar": 0,
        "telas": [
            "seo.painel", "seo.keywords", "seo.auditoria", "seo.concorrentes",
            "social.painel", "social.instagram", "social.facebook", "social.linkedin",
        ]
    },
    "viewer": {
        "pode_ver": 1, "pode_editar": 0, "pode_criar": 0, "pode_deletar": 0,
        "telas": [
            "seo.painel", "seo.keywords", "seo.auditoria",
            "social.painel", "social.instagram", "social.facebook", "social.linkedin",
        ]
    },
}

def criar_permissoes_tenant(tenant_id):
    """
    Cria as permissões padrão para um tenant recém-criado.
    Chamada após criação de novo tenant.
    """
    for role, config in PERMISSOES_PADRAO.items():
        for tela in config["telas"]:
            db.execute("""
                INSERT INTO permissoes
                    (tenant_id, role, tela_codigo,
                     pode_ver, pode_editar, pode_criar, pode_deletar)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, role, tela_codigo) DO NOTHING
            """, (
                tenant_id, role, tela,
                config["pode_ver"], config["pode_editar"],
                config["pode_criar"], config["pode_deletar"],
            ))

def tem_permissao(tela_codigo, acao="ver"):
    """
    Verifica se o usuário atual tem permissão para a tela/ação.
    acao: 'ver' | 'editar' | 'criar' | 'deletar'
    """
    if not current_user.is_authenticated:
        return False
    if current_user.is_superadmin:
        return True

    col_map = {
        "ver":     "pode_ver",
        "editar":  "pode_editar",
        "criar":   "pode_criar",
        "deletar": "pode_deletar",
    }
    col = col_map.get(acao, "pode_ver")

    row = db.query_one(f"""
        SELECT {col} AS permitido
        FROM permissoes
        WHERE tenant_id=%s AND role=%s AND tela_codigo=%s
    """, (current_user.tenant_id, current_user.role, tela_codigo))

    return bool(row and row["permitido"])

def requer_permissao(tela_codigo, acao="ver"):
    """
    Decorator que bloqueia acesso se não tiver permissão.
    Uso: @requer_permissao('config.apis_sociais', 'editar')
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not tem_permissao(tela_codigo, acao):
                flash("Você não tem permissão para acessar esta área.", "danger")
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)
        return decorated
    return decorator

def get_menu_permissoes(tenant_id, role):
    """
    Retorna lista de telas que o usuário pode ver,
    agrupadas por módulo — para montar o menu dinâmico.
    """
    if role == "superadmin":
        return db.query("""
            SELECT t.codigo, t.nome, t.modulo, t.icone, t.ordem
            FROM telas t
            WHERE t.ativo = 1
            ORDER BY t.ordem, t.nome
        """)

    return db.query("""
        SELECT t.codigo, t.nome, t.modulo, t.icone, t.ordem
        FROM telas t
        JOIN permissoes p ON p.tela_codigo = t.codigo
        WHERE p.tenant_id = %s
          AND p.role = %s
          AND p.pode_ver = 1
          AND t.ativo = 1
        ORDER BY t.ordem, t.nome
    """, (tenant_id, role))
