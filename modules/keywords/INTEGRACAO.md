# Módulo Keywords — Selenio Analytics
## Instruções de Integração

---

## 1. Arquivos criados

```
migrations/002_keywords.sql          ← Tabelas + view + índices
modules/keywords/__init__.py         ← Blueprint Flask (todas as rotas)
modules/keywords/providers.py        ← Arquitetura plugável de fontes
templates/keywords/index.html        ← Tela principal (lista + filtros + modais)
templates/keywords/historico.html    ← Gráfico de evolução + tabela histórico
templates/keywords/config.html       ← Configurar fonte de rastreamento
```

---

## 2. Registrar o Blueprint no app.py

```python
# app.py — adicionar junto aos outros blueprints
from modules.keywords import bp as bp_keywords
app.register_blueprint(bp_keywords, url_prefix="/keywords")
```

---

## 3. Rodar a migration

**No Mac (local):**
```bash
cd ~/Documents/selenio-analytics
psql -h localhost -U postgres -d selenio -f migrations/002_keywords.sql
```

**Na VPS (produção) — via psql dentro do container db:**
```bash
docker exec -i solidy-db psql -U postgres -d selenio < /root/analytics/migrations/002_keywords.sql
```

---

## 4. Adicionar link no menu (base.html)

Localizar a seção de navegação SEO e adicionar:

```html
<!-- Após o link do SEO, antes de fechar o grupo -->
<a href="{{ url_for('keywords.index', projeto_id=projeto.id) }}"
   class="nav-item {% if 'keywords' in request.endpoint %}active{% endif %}">
  🔑 Keywords
</a>
```

---

## 5. Adicionar permissões no seed.sql

As permissões são inseridas automaticamente pela migration com `ON CONFLICT DO NOTHING`.
Se precisar adicionar manualmente ao `permissions.py`:

```python
# permissions.py — adicionar nos grupos relevantes
"keywords.index", "keywords.historico", "keywords.config",
```

---

## 6. Registrar no dashboard (opcional)

Para mostrar contagem de keywords no card do projeto:

```python
# No dashboard, junto à query de stats:
keywords_count = db.query_one(
    "SELECT COUNT(*) as total FROM keywords WHERE projeto_id=%s AND D_E_L_E_T=0",
    (projeto_id,)
)
```

---

## 7. Dependências adicionais (requirements.txt)

Nenhuma nova dependência necessária para a versão manual.

**Quando ativar GSC — adicionar:**
```
google-auth==2.29.0
google-auth-oauthlib==1.2.0
google-api-python-client==2.128.0
```

**Quando ativar Scraping — adicionar:**
```
beautifulsoup4==4.12.3
```

---

## 8. Fluxo completo do usuário

```
1. Acessa /keywords/<projeto_id>
2. Clica em "+ Adicionar Keyword"
3. Preenche: termo, URL alvo, grupo, país → Salva
4. Clica em 📍 para registrar posição manualmente
5. Digita a posição → Salva
6. Badge colorido atualiza na tabela:
   🟡 Top 3 | 🟢 Top 10 | 🔵 Top 30 | ⚫ Fora | — Sem dados
7. Clica em 📈 para ver histórico + gráfico
8. Acessa ⚙️ para ver as fontes disponíveis
```

---

## 9. Providers — Como ativar futuramente

### GSC (Google Search Console)
1. Criar projeto no Google Cloud Console
2. Ativar Search Console API
3. Configurar OAuth 2.0
4. Descomentar o bloco `# HOOK` em `providers.py > rastrear_gsc()`
5. Adicionar `google-auth` ao requirements.txt

### DataForSEO
1. Criar conta em dataforseo.com
2. Obter login e senha da API
3. Descomentar o bloco `# HOOK` em `providers.py > rastrear_dataforseo()`
4. Usuário configura credenciais em ⚙️ Fonte

### Scraping Google
1. Configurar proxy rotativo (ex: ScraperAPI, Oxylabs)
2. Instalar `beautifulsoup4`
3. Descomentar e ajustar bloco `# HOOK` em `providers.py > rastrear_scraping()`

---

## 10. Estrutura das tabelas

| Tabela | Função |
|--------|--------|
| `keyword_fonte_config` | 1 registro por projeto — define a fonte ativa |
| `keywords` | Cadastro de termos por projeto |
| `keyword_posicoes` | Histórico de posições (append-only) |
| `keyword_alertas` | Variações >= 5 posições |
| `v_keywords_ultima_posicao` | View — última posição por keyword |

---

## Deploy

```bash
# Mac — commitar e enviar
cd ~/Documents/selenio-analytics
git add .
git commit -m "feat: módulo de keywords com providers plugáveis"
git push origin main
# O webhook faz o deploy automático em ~2 min
```

Após o deploy, rodar a migration na VPS conforme item 3.
