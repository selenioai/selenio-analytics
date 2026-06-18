-- ── Planos ──────────────────────────────────────────────────
INSERT INTO planos (nome, preco_por_assento, max_projetos, max_keywords,
                    max_usuarios, social_enabled, competitors_enabled,
                    relatorio_auto, api_access)
VALUES
    ('starter',    49.00,  1,  20,   1, 0, 0, 0, 0),
    ('pro',        97.00,  5,  100,  5, 1, 1, 1, 0),
    ('enterprise', 197.00, 99, 9999, 99,1, 1, 1, 1)
ON CONFLICT (nome) DO NOTHING;

-- ── Tenant interno: Solidy ───────────────────────────────────
INSERT INTO tenants (slug, nome, email_admin, plano_id, status,
                     assentos_contratados)
SELECT 'solidy', 'Solidy Consulting', 'admin@solidycontabilidade.com.br',
       p.id, 'active', 5
FROM planos p WHERE p.nome = 'enterprise'
ON CONFLICT (slug) DO NOTHING;

-- ── Admin owner da Solidy ────────────────────────────────────
-- Senha: Admin@2026 (trocar no primeiro login)
INSERT INTO usuarios (tenant_id, nome, email, senha_hash, role)
SELECT t.id,
       'Administrador Solidy',
       'admin@solidycontabilidade.com.br',
       '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaQkCVmfZqnG0YEq2FJmGQhXe',
       'owner'
FROM tenants t WHERE t.slug = 'solidy'
ON CONFLICT (email) DO NOTHING;

-- ── Super admin (acesso a todos os tenants) ──────────────────
-- Senha: SuperAdmin@2026
INSERT INTO usuarios (tenant_id, nome, email, senha_hash, role)
SELECT t.id,
       'Super Admin',
       'superadmin@solidy.internal',
       '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMaQkCVmfZqnG0YEq2FJmGQhXe',
       'superadmin'
FROM tenants t WHERE t.slug = 'solidy'
ON CONFLICT (email) DO NOTHING;

-- ── Seed v1.1.0: telas do sistema ────────────────────────────────
INSERT INTO telas (codigo, nome, descricao, modulo, icone, ordem) VALUES
('seo.painel',           'Painel SEO',            'Visão geral das métricas de SEO',             'seo',    '📊', 10),
('seo.keywords',         'Keywords',              'Gerenciar keywords monitoradas',               'seo',    '🔑', 11),
('seo.auditoria',        'Auditoria On-Page',     'Auditar URLs e score SEO',                    'seo',    '🔍', 12),
('seo.concorrentes',     'Concorrentes',          'Análise de gaps e concorrentes',              'seo',    '⚡', 13),
('social.painel',        'Painel Social',         'Visão geral das métricas sociais',            'social', '📱', 20),
('social.instagram',     'Instagram',             'Métricas do Instagram',                       'social', '📸', 21),
('social.facebook',      'Facebook',              'Métricas do Facebook',                        'social', '👍', 22),
('social.linkedin',      'LinkedIn',              'Métricas do LinkedIn',                        'social', '💼', 23),
('config.geral',         'Configurações Gerais',  'Configurações gerais do sistema',             'config', '⚙️', 30),
('config.apis_sociais',  'APIs Redes Sociais',    'Conectar e configurar APIs de redes sociais', 'config', '🔗', 31),
('config.usuarios',      'Usuários e Plano',      'Gerenciar usuários e assentos',               'config', '👥', 32),
('admin.painel',         'Painel Admin',          'Administração geral do SaaS',                 'admin',  '🛡', 40),
('admin.tenants',        'Clientes',              'Gerenciar clientes do SaaS',                  'admin',  '🏢', 41)
ON CONFLICT (codigo) DO NOTHING;
