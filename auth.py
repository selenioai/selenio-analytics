from flask_login import UserMixin
import db

class Usuario(UserMixin):
    def __init__(self, row):
        self.id         = row["id"]
        self.tenant_id  = row["tenant_id"]
        self.nome       = row["nome"]
        self.email      = row["email"]
        self.role       = row["role"]

    @property
    def is_owner(self):
        return self.role in ("owner", "superadmin")

    @property
    def is_admin(self):
        return self.role in ("owner", "admin", "superadmin")

    @property
    def is_superadmin(self):
        return self.role == "superadmin"

    @property
    def can_write(self):
        return self.role in ("owner", "admin", "member", "superadmin")

def get_user(user_id):
    row = db.query_one(
        "SELECT * FROM usuarios WHERE id=%s AND ativo=1 AND D_E_L_E_T=0",
        (user_id,)
    )
    return Usuario(row) if row else None

def get_user_by_email(email):
    return db.query_one(
        "SELECT * FROM usuarios WHERE email=%s AND ativo=1 AND D_E_L_E_T=0",
        (email,)
    )

def get_tenant(tenant_id):
    return db.query_one("""
        SELECT t.*, p.nome AS plano_nome, p.max_projetos, p.max_keywords,
               p.max_usuarios, p.social_enabled, p.competitors_enabled,
               p.relatorio_auto, p.api_access, p.preco_por_assento
        FROM tenants t
        JOIN planos p ON p.id = t.plano_id
        WHERE t.id = %s AND t.ativo = 1
    """, (tenant_id,))
