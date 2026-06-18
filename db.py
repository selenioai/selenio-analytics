"""
db.py — Camada de banco de dados com suporte multi-tenant nativo.

REGRA DE OURO: Nunca chame query() ou execute() sem tenant_id
quando os dados pertencem a um tenant. Use sempre:
  - query_t()    → SELECT com AND tenant_id = %s automático
  - execute_t()  → INSERT/UPDATE com tenant_id injetado
  - query()      → apenas para tabelas globais (planos, tenants)
"""
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "solidy_saas"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        cursor_factory=psycopg2.extras.RealDictCursor
    )

@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ── Queries globais (sem tenant) ─────────────────────────────
def query(sql, params=None):
    with db() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        return cur.fetchall()

def query_one(sql, params=None):
    with db() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        return cur.fetchone()

def execute(sql, params=None):
    with db() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        try:
            return cur.fetchone()
        except Exception:
            return None

# ── Queries com tenant_id automático ─────────────────────────
def query_t(tenant_id, sql, params=None):
    """
    Executa SQL injetando tenant_id como último parâmetro.
    Use {tenant} no SQL onde quiser o placeholder.

    Exemplo:
        query_t(tid, "SELECT * FROM keywords WHERE projeto_id=%s AND tenant_id=%s", (pid,))
    O tenant_id é sempre o ÚLTIMO parâmetro.
    """
    full_params = list(params or []) + [tenant_id]
    with db() as conn:
        cur = conn.cursor()
        cur.execute(sql, full_params)
        return cur.fetchall()

def query_one_t(tenant_id, sql, params=None):
    full_params = list(params or []) + [tenant_id]
    with db() as conn:
        cur = conn.cursor()
        cur.execute(sql, full_params)
        return cur.fetchone()

def execute_t(tenant_id, sql, params=None):
    full_params = list(params or []) + [tenant_id]
    with db() as conn:
        cur = conn.cursor()
        cur.execute(sql, full_params)
        try:
            return cur.fetchone()
        except Exception:
            return None

# ── Helpers de limite por plano ──────────────────────────────
def contar_t(tenant_id, tabela, coluna_extra=None, valor_extra=None):
    """Conta registros ativos de um tenant em qualquer tabela."""
    if coluna_extra:
        return query_one_t(tenant_id,
            f"SELECT COUNT(*) AS n FROM {tabela} WHERE {coluna_extra}=%s AND tenant_id=%s AND D_E_L_E_T=0",
            (valor_extra,)
        )["n"]
    return query_one_t(tenant_id,
        f"SELECT COUNT(*) AS n FROM {tabela} WHERE tenant_id=%s AND D_E_L_E_T=0",
    )["n"]

def plano_do_tenant(tenant_id):
    """Retorna o plano atual com todos os limites."""
    return query_one("""
        SELECT p.* FROM planos p
        JOIN tenants t ON t.plano_id = p.id
        WHERE t.id = %s
    """, (tenant_id,))

def dentro_do_limite(tenant_id, recurso):
    """
    Verifica se tenant ainda está dentro dos limites do plano.
    recurso: 'usuarios' | 'projetos' | 'keywords'
    """
    plano = plano_do_tenant(tenant_id)
    if not plano:
        return False

    limites = {
        "usuarios":  ("usuarios",  plano["max_usuarios"],  None, None),
        "projetos":  ("projetos",  plano["max_projetos"],  None, None),
        "keywords":  ("keywords",  plano["max_keywords"],  None, None),
    }
    if recurso not in limites:
        return True

    tabela, limite, col, val = limites[recurso]
    if limite >= 9999:
        return True
    atual = contar_t(tenant_id, tabela)
    return atual < limite

# ── Inicialização ─────────────────────────────────────────────
def init_db():
    base = os.path.dirname(os.path.abspath(__file__))
    with db() as conn:
        cur = conn.cursor()
        with open(os.path.join(base, "schema.sql"), encoding="utf-8") as f:
            cur.execute(f.read())
    try:
        with db() as conn:
            cur = conn.cursor()
            with open(os.path.join(base, "seed.sql"), encoding="utf-8") as f:
                cur.execute(f.read())
    except Exception as e:
        print(f"[DB] Seed ignorado (ja aplicado): {e}")
