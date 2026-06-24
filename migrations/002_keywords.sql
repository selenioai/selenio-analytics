-- ============================================================
-- Módulo Keywords — Selenio Analytics
-- Migration 002
-- ============================================================

-- Configuração de fonte de dados por projeto
CREATE TABLE IF NOT EXISTS keyword_fonte_config (
    id                  SERIAL PRIMARY KEY,
    projeto_id          INTEGER NOT NULL REFERENCES projetos(id),
    fonte               VARCHAR(30) NOT NULL DEFAULT 'manual',
    -- 'manual' | 'gsc' | 'scraping' | 'dataforseo'

    -- GSC
    gsc_property_url    TEXT,
    gsc_token_json      TEXT,          -- JSON do OAuth token

    -- DataForSEO
    dataforseo_login    VARCHAR(200),
    dataforseo_password VARCHAR(200),

    -- Scraping
    scraping_pais       VARCHAR(5) DEFAULT 'br',
    scraping_lingua     VARCHAR(5) DEFAULT 'pt',

    ativo               SMALLINT DEFAULT 1,
    datestamp_insert    TIMESTAMP DEFAULT NOW(),
    datestamp_update    TIMESTAMP,
    UNIQUE(projeto_id)
);

-- Keywords cadastradas por projeto
CREATE TABLE IF NOT EXISTS keywords (
    id                  SERIAL PRIMARY KEY,
    projeto_id          INTEGER NOT NULL REFERENCES projetos(id),
    termo               VARCHAR(500) NOT NULL,
    url_alvo            TEXT,          -- URL que deve ranquear
    grupo               VARCHAR(100),  -- cluster/tema
    pais                VARCHAR(5) DEFAULT 'br',
    lingua              VARCHAR(5) DEFAULT 'pt',
    ativo               SMALLINT DEFAULT 1,
    D_E_L_E_T           SMALLINT DEFAULT 0,
    usuario_insert      INTEGER,
    usuario_update      INTEGER,
    datestamp_insert    TIMESTAMP DEFAULT NOW(),
    datestamp_update    TIMESTAMP,
    UNIQUE(projeto_id, termo, D_E_L_E_T)
);

-- Histórico de posições (cada rastreamento gera um registro)
CREATE TABLE IF NOT EXISTS keyword_posicoes (
    id                  SERIAL PRIMARY KEY,
    keyword_id          INTEGER NOT NULL REFERENCES keywords(id),
    projeto_id          INTEGER NOT NULL REFERENCES projetos(id),
    posicao             INTEGER,       -- NULL = não encontrado no top 100
    url_encontrada      TEXT,          -- URL que apareceu no resultado
    volume_busca        INTEGER,       -- volume mensal (quando disponível)
    dificuldade         SMALLINT,      -- KD 0-100 (quando disponível)
    cpc                 NUMERIC(10,2), -- custo por clique (quando disponível)
    fonte               VARCHAR(30) NOT NULL DEFAULT 'manual',
    rastreado_em        TIMESTAMP DEFAULT NOW(),
    -- Dados brutos da API (para debug e reprocessamento)
    raw_data            JSONB
);

-- Alertas de variação de posição
CREATE TABLE IF NOT EXISTS keyword_alertas (
    id                  SERIAL PRIMARY KEY,
    keyword_id          INTEGER NOT NULL REFERENCES keywords(id),
    projeto_id          INTEGER NOT NULL REFERENCES projetos(id),
    tipo                VARCHAR(30),   -- 'subida' | 'queda' | 'entrada_top10' | 'saiu_top10'
    posicao_anterior    INTEGER,
    posicao_atual       INTEGER,
    variacao            INTEGER,       -- positivo = subiu, negativo = caiu
    lido                SMALLINT DEFAULT 0,
    datestamp_insert    TIMESTAMP DEFAULT NOW()
);

-- View auxiliar: última posição de cada keyword
CREATE OR REPLACE VIEW v_keywords_ultima_posicao AS
SELECT DISTINCT ON (kp.keyword_id)
    k.id,
    k.projeto_id,
    k.termo,
    k.url_alvo,
    k.grupo,
    k.pais,
    kp.posicao,
    kp.url_encontrada,
    kp.volume_busca,
    kp.dificuldade,
    kp.cpc,
    kp.fonte,
    kp.rastreado_em,
    -- Posição anterior para calcular variação
    LAG(kp.posicao) OVER (
        PARTITION BY kp.keyword_id ORDER BY kp.rastreado_em
    ) AS posicao_anterior
FROM keywords k
LEFT JOIN keyword_posicoes kp ON kp.keyword_id = k.id
WHERE k.D_E_L_E_T = 0 AND k.ativo = 1
ORDER BY kp.keyword_id, kp.rastreado_em DESC;

-- Índices de performance
CREATE INDEX IF NOT EXISTS idx_keywords_projeto     ON keywords(projeto_id) WHERE D_E_L_E_T=0;
CREATE INDEX IF NOT EXISTS idx_kposicoes_keyword    ON keyword_posicoes(keyword_id);
CREATE INDEX IF NOT EXISTS idx_kposicoes_projeto    ON keyword_posicoes(projeto_id);
CREATE INDEX IF NOT EXISTS idx_kposicoes_rastreado  ON keyword_posicoes(rastreado_em DESC);
CREATE INDEX IF NOT EXISTS idx_kalertas_projeto     ON keyword_alertas(projeto_id) WHERE lido=0;

-- Permissões do módulo (inserir se não existir)
INSERT INTO permissoes (codigo, nome, descricao, modulo, icone, ordem)
VALUES
    ('keywords.index',     'Keywords',          'Lista de keywords rastreadas',      'keywords', '🔑', 20),
    ('keywords.historico', 'Histórico Keywords', 'Histórico de posições',            'keywords', '📈', 21),
    ('keywords.config',    'Config Keywords',   'Configurar fonte de rastreamento',  'keywords', '⚙️', 22)
ON CONFLICT (codigo) DO NOTHING;
