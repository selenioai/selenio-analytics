-- ═══════════════════════════════════════════════════════════════
--  Solidy SEO Analytics — Schema Multi-Tenant
--  Modelo: por assento (seat-based pricing)
--  Regra de ouro: todo dado tem tenant_id
-- ═══════════════════════════════════════════════════════════════

-- ── Planos disponíveis ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS planos (
    id                  SERIAL PRIMARY KEY,
    nome                VARCHAR(50)   NOT NULL UNIQUE,  -- starter | pro | enterprise
    preco_por_assento   NUMERIC(8,2)  NOT NULL DEFAULT 0,
    max_projetos        SMALLINT      DEFAULT 1,
    max_keywords        SMALLINT      DEFAULT 20,
    max_usuarios        SMALLINT      DEFAULT 1,
    social_enabled      SMALLINT      DEFAULT 0,
    competitors_enabled SMALLINT      DEFAULT 0,
    relatorio_auto      SMALLINT      DEFAULT 0,
    api_access          SMALLINT      DEFAULT 0,
    ativo               SMALLINT      DEFAULT 1,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

-- ── Tenants (clientes do SaaS) ───────────────────────────────
CREATE TABLE IF NOT EXISTS tenants (
    id                  SERIAL PRIMARY KEY,
    slug                VARCHAR(100)  NOT NULL UNIQUE,  -- ex: solidy, agencia-xyz
    nome                VARCHAR(200)  NOT NULL,
    email_admin         VARCHAR(200)  NOT NULL,
    plano_id            INTEGER       REFERENCES planos(id) DEFAULT 1,
    status              VARCHAR(20)   DEFAULT 'trial',  -- trial | active | suspended | cancelled
    trial_expira        TIMESTAMP     DEFAULT (NOW() + INTERVAL '14 days'),
    assentos_contratados SMALLINT     DEFAULT 1,
    ativo               SMALLINT      DEFAULT 1,
    D_E_L_E_T           SMALLINT      DEFAULT 0,
    datestamp_insert    TIMESTAMP     DEFAULT NOW(),
    datestamp_update    TIMESTAMP
);

-- ── Assinaturas / faturamento ────────────────────────────────
CREATE TABLE IF NOT EXISTS assinaturas (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id),
    plano_id            INTEGER       REFERENCES planos(id),
    assentos            SMALLINT      DEFAULT 1,
    valor_mensal        NUMERIC(8,2)  DEFAULT 0,
    status              VARCHAR(20)   DEFAULT 'active',  -- active | past_due | cancelled
    periodo_inicio      DATE          DEFAULT CURRENT_DATE,
    periodo_fim         DATE,
    gateway_sub_id      VARCHAR(200),  -- ID no Stripe/Hotmart/etc.
    datestamp_insert    TIMESTAMP     DEFAULT NOW(),
    datestamp_update    TIMESTAMP
);

-- ── Usuários ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuarios (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    nome                VARCHAR(200)  NOT NULL,
    email               VARCHAR(200)  NOT NULL UNIQUE,
    senha_hash          VARCHAR(300)  NOT NULL,
    role                VARCHAR(20)   DEFAULT 'member',  -- owner | admin | member | viewer
    ativo               SMALLINT      DEFAULT 1,
    D_E_L_E_T           SMALLINT      DEFAULT 0,
    ultimo_login        TIMESTAMP,
    datestamp_insert    TIMESTAMP     DEFAULT NOW(),
    datestamp_update    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usuarios_tenant ON usuarios(tenant_id);

-- ── Convites de usuário ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS convites (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id),
    email               VARCHAR(200)  NOT NULL,
    role                VARCHAR(20)   DEFAULT 'member',
    token               VARCHAR(100)  NOT NULL UNIQUE,
    aceito              SMALLINT      DEFAULT 0,
    expira_em           TIMESTAMP     DEFAULT (NOW() + INTERVAL '48 hours'),
    convidado_por       INTEGER       REFERENCES usuarios(id),
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

-- ── Projetos (sites monitorados) ─────────────────────────────
CREATE TABLE IF NOT EXISTS projetos (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    usuario_id          INTEGER       REFERENCES usuarios(id),
    nome                VARCHAR(200)  NOT NULL,
    dominio             VARCHAR(300)  NOT NULL,
    gsc_site_url        VARCHAR(300),
    ga4_property_id     VARCHAR(50),
    meta_page_id        VARCHAR(100),
    linkedin_org_id     VARCHAR(100),
    serpapi_location    VARCHAR(100)  DEFAULT 'Brazil',
    ativo               SMALLINT      DEFAULT 1,
    D_E_L_E_T           SMALLINT      DEFAULT 0,
    datestamp_insert    TIMESTAMP     DEFAULT NOW(),
    datestamp_update    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_projetos_tenant ON projetos(tenant_id);

-- ── Keywords ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS keywords (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    projeto_id          INTEGER       REFERENCES projetos(id),
    termo               VARCHAR(500)  NOT NULL,
    ativo               SMALLINT      DEFAULT 1,
    D_E_L_E_T           SMALLINT      DEFAULT 0,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_keywords_tenant ON keywords(tenant_id);

-- ── Rankings diários ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rankings (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    keyword_id          INTEGER       REFERENCES keywords(id),
    projeto_id          INTEGER       REFERENCES projetos(id),
    posicao             SMALLINT,
    url_ranqueada       VARCHAR(500),
    data_coleta         DATE          DEFAULT CURRENT_DATE,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rankings_tenant_data
    ON rankings(tenant_id, data_coleta DESC);

-- ── Google Search Console ────────────────────────────────────
CREATE TABLE IF NOT EXISTS gsc_metricas (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    projeto_id          INTEGER       REFERENCES projetos(id),
    data_ref            DATE          NOT NULL,
    query               VARCHAR(500),
    pagina              VARCHAR(500),
    cliques             INTEGER       DEFAULT 0,
    impressoes          INTEGER       DEFAULT 0,
    ctr                 NUMERIC(6,4)  DEFAULT 0,
    posicao_media       NUMERIC(6,2)  DEFAULT 0,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gsc_tenant_data
    ON gsc_metricas(tenant_id, data_ref DESC);

-- ── GA4 ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ga4_metricas (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    projeto_id          INTEGER       REFERENCES projetos(id),
    data_ref            DATE          NOT NULL,
    sessoes             INTEGER       DEFAULT 0,
    usuarios            INTEGER       DEFAULT 0,
    novos_usuarios      INTEGER       DEFAULT 0,
    bounce_rate         NUMERIC(6,4)  DEFAULT 0,
    duracao_media       NUMERIC(10,2) DEFAULT 0,
    conversoes          INTEGER       DEFAULT 0,
    canal               VARCHAR(100),
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ga4_tenant_data
    ON ga4_metricas(tenant_id, data_ref DESC);

-- ── Meta (Instagram + Facebook) ─────────────────────────────
CREATE TABLE IF NOT EXISTS meta_metricas (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    projeto_id          INTEGER       REFERENCES projetos(id),
    plataforma          VARCHAR(20)   NOT NULL,
    data_ref            DATE          NOT NULL,
    seguidores          INTEGER       DEFAULT 0,
    alcance             INTEGER       DEFAULT 0,
    impressoes          INTEGER       DEFAULT 0,
    engajamentos        INTEGER       DEFAULT 0,
    posts_publicados    SMALLINT      DEFAULT 0,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meta_tenant ON meta_metricas(tenant_id, data_ref DESC);

-- ── LinkedIn ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS linkedin_metricas (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    projeto_id          INTEGER       REFERENCES projetos(id),
    data_ref            DATE          NOT NULL,
    seguidores          INTEGER       DEFAULT 0,
    impressoes          INTEGER       DEFAULT 0,
    cliques             INTEGER       DEFAULT 0,
    engajamentos        INTEGER       DEFAULT 0,
    novos_seguidores    INTEGER       DEFAULT 0,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

-- ── Auditorias SEO on-page ───────────────────────────────────
CREATE TABLE IF NOT EXISTS auditorias (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    projeto_id          INTEGER       REFERENCES projetos(id),
    url                 VARCHAR(500)  NOT NULL,
    score               SMALLINT,
    title_tag           VARCHAR(300),
    meta_desc           VARCHAR(300),
    h1                  VARCHAR(300),
    status_code         SMALLINT,
    tem_schema          SMALLINT      DEFAULT 0,
    tem_og              SMALLINT      DEFAULT 0,
    canonical           VARCHAR(500),
    issues_json         TEXT,
    data_auditoria      DATE          DEFAULT CURRENT_DATE,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant ON auditorias(tenant_id, data_auditoria DESC);

-- ── Concorrentes ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS concorrentes (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    projeto_id          INTEGER       REFERENCES projetos(id),
    nome                VARCHAR(200)  NOT NULL,
    dominio             VARCHAR(300)  NOT NULL,
    ativo               SMALLINT      DEFAULT 1,
    D_E_L_E_T           SMALLINT      DEFAULT 0,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

-- ── Rankings de concorrentes ─────────────────────────────────
CREATE TABLE IF NOT EXISTS concorrente_rankings (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    concorrente_id      INTEGER       REFERENCES concorrentes(id),
    keyword_id          INTEGER       REFERENCES keywords(id),
    posicao             SMALLINT,
    url_ranqueada       VARCHAR(500),
    data_coleta         DATE          DEFAULT CURRENT_DATE,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

-- ── Alertas ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alertas (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    projeto_id          INTEGER       REFERENCES projetos(id),
    tipo                VARCHAR(50),
    mensagem            TEXT,
    lido                SMALLINT      DEFAULT 0,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

-- ── Tokens OAuth por tenant ──────────────────────────────────
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    projeto_id          INTEGER       REFERENCES projetos(id),
    provedor            VARCHAR(50)   NOT NULL,
    access_token        TEXT,
    refresh_token       TEXT,
    expires_at          TIMESTAMP,
    scope               TEXT,
    datestamp_insert    TIMESTAMP     DEFAULT NOW(),
    datestamp_update    TIMESTAMP
);

-- ── Log de uso por assento (billing) ─────────────────────────
CREATE TABLE IF NOT EXISTS uso_mensal (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    mes_ref             DATE          NOT NULL,             -- primeiro dia do mês
    assentos_ativos     SMALLINT      DEFAULT 0,
    projetos_ativos     SMALLINT      DEFAULT 0,
    keywords_total      SMALLINT      DEFAULT 0,
    coletas_realizadas  INTEGER       DEFAULT 0,
    datestamp_insert    TIMESTAMP     DEFAULT NOW(),
    datestamp_update    TIMESTAMP,
    UNIQUE(tenant_id, mes_ref)
);
