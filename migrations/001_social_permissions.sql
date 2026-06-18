-- ═══════════════════════════════════════════════════════════════
--  Migration: Sistema de Permissões + Configurações + APIs Sociais
--  Versão: 1.1.0
--  Aplica: ALTER TABLE IF NOT EXISTS / CREATE TABLE IF NOT EXISTS
-- ═══════════════════════════════════════════════════════════════

-- ── Telas / Recursos do sistema (para permissionamento) ─────────
CREATE TABLE IF NOT EXISTS telas (
    id                  SERIAL PRIMARY KEY,
    codigo              VARCHAR(100)  NOT NULL UNIQUE,  -- ex: config.apis_sociais
    nome                VARCHAR(200)  NOT NULL,
    descricao           TEXT,
    modulo              VARCHAR(100),                   -- config | seo | social | admin
    icone               VARCHAR(50)   DEFAULT '📄',
    ativo               SMALLINT      DEFAULT 1,
    ordem               SMALLINT      DEFAULT 0,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

-- ── Permissões por role + tela ───────────────────────────────────
CREATE TABLE IF NOT EXISTS permissoes (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    role                VARCHAR(20)   NOT NULL,          -- owner | admin | member | viewer
    tela_codigo         VARCHAR(100)  NOT NULL,
    pode_ver            SMALLINT      DEFAULT 0,
    pode_editar         SMALLINT      DEFAULT 0,
    pode_criar          SMALLINT      DEFAULT 0,
    pode_deletar        SMALLINT      DEFAULT 0,
    datestamp_insert    TIMESTAMP     DEFAULT NOW(),
    datestamp_update    TIMESTAMP,
    UNIQUE(tenant_id, role, tela_codigo)
);

CREATE INDEX IF NOT EXISTS idx_permissoes_tenant_role
    ON permissoes(tenant_id, role);

-- ── Configurações gerais por tenant ──────────────────────────────
CREATE TABLE IF NOT EXISTS configuracoes (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL UNIQUE,
    timezone            VARCHAR(50)   DEFAULT 'America/Sao_Paulo',
    idioma              VARCHAR(10)   DEFAULT 'pt-BR',
    notif_email         SMALLINT      DEFAULT 1,
    notif_alertas       SMALLINT      DEFAULT 1,
    coleta_hora         SMALLINT      DEFAULT 6,         -- hora do dia para coleta automática
    datestamp_insert    TIMESTAMP     DEFAULT NOW(),
    datestamp_update    TIMESTAMP
);

-- ── Integrações de APIs por projeto ──────────────────────────────
CREATE TABLE IF NOT EXISTS api_integracoes (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    projeto_id          INTEGER       REFERENCES projetos(id),
    provedor            VARCHAR(50)   NOT NULL,  -- meta | linkedin | google | tiktok | twitter
    nome_exibicao       VARCHAR(200),            -- ex: "Página Solidy Contabilidade"
    status              VARCHAR(20)   DEFAULT 'pendente', -- pendente | ativo | erro | expirado
    -- OAuth tokens
    access_token        TEXT,
    refresh_token       TEXT,
    token_expires_at    TIMESTAMP,
    token_scope         TEXT,
    -- IDs das contas conectadas
    account_id          VARCHAR(200),            -- page_id, org_id, etc.
    account_name        VARCHAR(200),
    account_avatar_url  VARCHAR(500),
    -- Metadados específicos por provedor (JSON)
    meta_dados          TEXT,                    -- JSON com dados extras
    -- Controle
    ultimo_sync         TIMESTAMP,
    erro_mensagem       TEXT,
    ativo               SMALLINT      DEFAULT 1,
    D_E_L_E_T           SMALLINT      DEFAULT 0,
    criado_por          INTEGER       REFERENCES usuarios(id),
    datestamp_insert    TIMESTAMP     DEFAULT NOW(),
    datestamp_update    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_integracoes_tenant
    ON api_integracoes(tenant_id, provedor);

CREATE INDEX IF NOT EXISTS idx_api_integracoes_projeto
    ON api_integracoes(projeto_id, provedor);

-- ── Logs de coleta por integração ────────────────────────────────
CREATE TABLE IF NOT EXISTS api_logs (
    id                  SERIAL PRIMARY KEY,
    tenant_id           INTEGER       REFERENCES tenants(id) NOT NULL,
    integracao_id       INTEGER       REFERENCES api_integracoes(id),
    tipo                VARCHAR(50),             -- coleta | auth | erro | refresh
    status              VARCHAR(20),             -- ok | erro | aviso
    mensagem            TEXT,
    registros_coletados INTEGER       DEFAULT 0,
    duracao_ms          INTEGER,
    datestamp_insert    TIMESTAMP     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_logs_integracao
    ON api_logs(integracao_id, datestamp_insert DESC);

-- ── Seed: telas do sistema ────────────────────────────────────────
INSERT INTO telas (codigo, nome, descricao, modulo, icone, ordem) VALUES
-- SEO
('seo.painel',           'Painel SEO',            'Visão geral das métricas de SEO',          'seo',    '📊', 10),
('seo.keywords',         'Keywords',              'Gerenciar keywords monitoradas',            'seo',    '🔑', 11),
('seo.auditoria',        'Auditoria On-Page',     'Auditar URLs e score SEO',                 'seo',    '🔍', 12),
('seo.concorrentes',     'Concorrentes',          'Análise de gaps e concorrentes',           'seo',    '⚡', 13),
-- Social
('social.painel',        'Painel Social',         'Visão geral das métricas sociais',         'social', '📱', 20),
('social.instagram',     'Instagram',             'Métricas do Instagram',                    'social', '📸', 21),
('social.facebook',      'Facebook',              'Métricas do Facebook',                     'social', '👍', 22),
('social.linkedin',      'LinkedIn',              'Métricas do LinkedIn',                     'social', '💼', 23),
-- Configurações
('config.geral',         'Configurações Gerais',  'Configurações gerais do sistema',          'config', '⚙️', 30),
('config.apis_sociais',  'APIs Redes Sociais',    'Conectar e configurar APIs de redes sociais', 'config', '🔗', 31),
('config.usuarios',      'Usuários e Plano',      'Gerenciar usuários e assentos',            'config', '👥', 32),
-- Admin
('admin.painel',         'Painel Admin',          'Administração geral do SaaS',              'admin',  '🛡', 40),
('admin.tenants',        'Clientes',              'Gerenciar clientes do SaaS',               'admin',  '🏢', 41)
ON CONFLICT (codigo) DO NOTHING;

-- ── Seed: permissões padrão por role ─────────────────────────────
-- Função para criar permissões padrão para um tenant
-- (Chamada pelo Python após criar um tenant)
-- Padrões:
--   owner  → acesso total a tudo exceto admin
--   admin  → acesso total exceto admin e billing
--   member → ver e editar SEO e social
--   viewer → apenas ver SEO e social
