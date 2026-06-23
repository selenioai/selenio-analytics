-- Módulo SEO: tabela de análises
CREATE TABLE IF NOT EXISTS seo_analises (
    id          SERIAL PRIMARY KEY,
    tenant_id   INTEGER NOT NULL,
    projeto_id  INTEGER,
    url         VARCHAR(2000) NOT NULL,
    score       INTEGER DEFAULT 0,
    dados_json  TEXT,
    criado_por  INTEGER,
    criado_em   TIMESTAMP DEFAULT NOW(),
    D_E_L_E_T   SMALLINT DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_seo_analises_tenant ON seo_analises(tenant_id);
