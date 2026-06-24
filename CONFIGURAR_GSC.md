# Guia de Configuração — Google Search Console
## Selenio Analytics

---

## Visão Geral

Para o Selenio importar posições reais do Google, você precisa:

1. Criar um projeto no **Google Cloud Console**
2. Ativar a **Search Console API**
3. Criar as **credenciais OAuth 2.0**
4. Configurar a **tela de consentimento**
5. Adicionar o **Client ID e Secret** no Selenio
6. Clicar em **Conectar com Google**
7. Selecionar a **property do seu site**

---

## PASSO 1 — Criar projeto no Google Cloud Console

1. Acesse: https://console.cloud.google.com
2. Clique no seletor de projetos (topo da página) → **Novo Projeto**
3. Nome: `Selenio Analytics` (ou qualquer nome)
4. Clique em **Criar**
5. Aguarde criar e selecione o projeto

---

## PASSO 2 — Ativar a Search Console API

1. No menu lateral: **APIs e Serviços → Biblioteca**
2. Busque: `Google Search Console API`
3. Clique no resultado → **Ativar**
4. Aguarde a ativação (pode levar alguns segundos)

---

## PASSO 3 — Configurar tela de consentimento OAuth

1. Menu lateral: **APIs e Serviços → Tela de consentimento OAuth**
2. Tipo de usuário: **Externo** → Criar
3. Preencha:
   - **Nome do app:** Selenio Analytics
   - **E-mail de suporte:** seu email
   - **E-mail do desenvolvedor:** seu email
4. Clique em **Salvar e continuar**
5. Em **Escopos** → clique em **Adicionar ou remover escopos**
   - Busque e adicione: `webmasters.readonly`
   - Adicione também: `openid`, `email`, `profile`
6. Salvar e continuar
7. Em **Usuários de teste** → **Adicionar usuários**
   - Adicione os emails que vão usar o Selenio
   - ⚠️ Enquanto o app estiver em modo "Teste", só esses emails conseguem conectar
8. Salvar e continuar → **Voltar ao painel**

---

## PASSO 4 — Criar credenciais OAuth 2.0

1. Menu lateral: **APIs e Serviços → Credenciais**
2. Clique em **Criar credenciais → ID do cliente OAuth**
3. Tipo de aplicativo: **Aplicativo da Web**
4. Nome: `Selenio Analytics OAuth`
5. Em **URIs de redirecionamento autorizados** → adicione:
   ```
   https://analytics.selenio.ai/gsc/callback
   ```
6. Clique em **Criar**
7. Uma janela aparece com:
   - **ID do cliente** (Client ID) — começa com números e termina em `.apps.googleusercontent.com`
   - **Chave secreta do cliente** (Client Secret) — começa com `GOCSPX-`
8. **Copie e guarde os dois valores**

---

## PASSO 5 — Salvar credenciais no app (banco de dados)

As credenciais do Google ficam salvas na tabela `api_integracoes` com `provedor='google_app'`.

**Rodar na VPS para salvar:**
```bash
docker exec -i solidy-db psql -U solidy -d solidy_saas << 'EOF'
INSERT INTO api_integracoes (tenant_id, provedor, nome_exibicao, status, meta_dados, criado_por)
VALUES (
    1,                          -- substitua pelo tenant_id correto
    'google_app',
    'Google Cloud App',
    'ativo',
    '{"client_id": "SEU_CLIENT_ID_AQUI", "client_secret": "SEU_CLIENT_SECRET_AQUI"}',
    1                           -- substitua pelo usuario_id do admin
)
ON CONFLICT DO NOTHING;
EOF
```

**Ou via interface (quando implementado):**
- Configurações → APIs Redes Sociais → Google → preencher Client ID e Secret

---

## PASSO 6 — Verificar o site no Search Console

Se ainda não fez isso:

1. Acesse: https://search.google.com/search-console
2. Clique em **Adicionar property**
3. Escolha **Domain** (recomendado) ou **URL prefix**
   - **Domain:** cobre http, https, www e subdomínios
   - **URL prefix:** cobre apenas a URL exata
4. Para domínio: adicione o registro TXT no DNS
5. Para URL prefix: faça upload do arquivo HTML ou adicione meta tag
6. Aguarde a verificação (pode levar minutos a horas)

---

## PASSO 7 — Conectar no Selenio

1. Acesse: **Keywords → ⚙️ Fonte → Google Search Console**
2. Preencha Client ID e Client Secret
3. Clique em **Conectar com Google**
4. Faça login com sua conta Google
5. Autorize os escopos solicitados
6. Selecione a property do seu site
7. Clique em **Confirmar Property**
8. Pronto! Clique em **🔄 Sincronizar agora**

---

## Como funciona a sincronização

Ao clicar em **Sincronizar agora**, o Selenio:

1. Busca todas as keywords cadastradas no projeto
2. Para cada keyword, consulta o GSC com filtro de query exata
3. Obtém: **posição média**, **impressões**, **cliques** dos últimos 28 dias
4. Salva na tabela `keyword_posicoes`
5. Gera alertas para variações >= 5 posições
6. Atualiza o gráfico de evolução

---

## Limitações do GSC

| Limitação | Detalhe |
|---|---|
| Delay de dados | GSC tem ~2-3 dias de atraso |
| Threshold de privacidade | Keywords com poucos cliques podem não aparecer |
| Máximo 25.000 rows por query | Suficiente para qualquer projeto |
| Dados históricos | Disponível por até 16 meses |
| Posição média | É a média das posições em que apareceu — pode ser decimal |

---

## Troubleshooting

**"Erro ao obter token"**
→ Verifique se o URI de redirecionamento está exato: `https://analytics.selenio.ai/gsc/callback`

**"Nenhuma property encontrada"**
→ O email Google usado não tem acesso ao Search Console. Adicione como usuário na property.

**"Keyword não encontrada nos dados do GSC"**
→ A keyword ainda não gerou impressões suficientes no Google. Normal para termos novos.

**Token expirado**
→ O sistema renova automaticamente via refresh_token. Se falhar, desconecte e reconecte.

---

## Estrutura de dados salvos

```json
{
  "keyword": "contabilidade digital",
  "posicao": 7,
  "impressoes": 1240,
  "cliques": 48,
  "ctr": 0.0387,
  "periodo": "2026-05-27 → 2026-06-24"
}
```

---

## Próximos passos após configurar

1. ✅ Conectar GSC
2. ✅ Selecionar property
3. ✅ Sincronizar manualmente
4. 🔜 Configurar sync automático diário (cron job)
5. 🔜 Importar keywords diretamente do GSC (top queries)
