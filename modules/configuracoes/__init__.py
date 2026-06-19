"""
Módulo de Configurações
- Configurações Gerais
- APIs de Redes Sociais (Meta, LinkedIn, etc.)
- Permissões (futuro)
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, g, jsonify, session)
from flask_login import login_required, current_user
import os, json, secrets, requests as req_lib
from datetime import datetime, timedelta
import db
from permissions import requer_permissao, tem_permissao

bp = Blueprint("configuracoes", __name__)

# ── Helpers ───────────────────────────────────────────────────────
def _log(tenant_id, integracao_id, tipo, status, mensagem, registros=0):
    db.execute("""
        INSERT INTO api_logs (tenant_id, integracao_id, tipo, status, mensagem, registros_coletados)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (tenant_id, integracao_id, tipo, status, mensagem, registros))

# ════════════════════════════════════════════════════════════════
#  CONFIGURAÇÕES GERAIS
# ════════════════════════════════════════════════════════════════
@bp.route("/geral")
@login_required
@requer_permissao("config.geral", "ver")
def geral():
    tid = current_user.tenant_id
    config = db.query_one(
        "SELECT * FROM configuracoes WHERE tenant_id=%s", (tid,))
    if not config:
        db.execute(
            "INSERT INTO configuracoes (tenant_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (tid,))
        config = db.query_one(
            "SELECT * FROM configuracoes WHERE tenant_id=%s", (tid,))
    return render_template("configuracoes/geral.html", config=config)

@bp.route("/geral/salvar", methods=["POST"])
@login_required
@requer_permissao("config.geral", "editar")
def geral_salvar():
    tid = current_user.tenant_id
    d   = request.form
    db.execute("""
        INSERT INTO configuracoes (tenant_id, timezone, idioma, notif_email, notif_alertas, coleta_hora)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT (tenant_id) DO UPDATE SET
            timezone=%s, idioma=%s, notif_email=%s, notif_alertas=%s,
            coleta_hora=%s, datestamp_update=NOW()
    """, (
        tid, d.get("timezone","America/Sao_Paulo"), d.get("idioma","pt-BR"),
        1 if d.get("notif_email") else 0,
        1 if d.get("notif_alertas") else 0,
        int(d.get("coleta_hora", 6)),
        d.get("timezone","America/Sao_Paulo"), d.get("idioma","pt-BR"),
        1 if d.get("notif_email") else 0,
        1 if d.get("notif_alertas") else 0,
        int(d.get("coleta_hora", 6)),
    ))
    flash("Configurações salvas com sucesso.", "success")
    return redirect(url_for("configuracoes.geral"))

# ════════════════════════════════════════════════════════════════
#  APIs DE REDES SOCIAIS
# ════════════════════════════════════════════════════════════════
PROVEDORES = {
    "meta": {
        "nome":        "Meta (Instagram + Facebook)",
        "icones":      ["📸", "👍"],
        "cor":         "#1877F2",
        "descricao":   "Conecta Instagram Business e Facebook Page via Meta Graph API",
        "doc_url":     "https://developers.facebook.com/docs/graph-api",
        "oauth_implementado": True,
        "requer_app":  True,
        "campos": [
            {"key": "app_id",     "label": "App ID",     "tipo": "text", "ajuda": "ID do App no Meta for Developers"},
            {"key": "app_secret", "label": "App Secret", "tipo": "password", "ajuda": "Secret do App no Meta for Developers"},
        ],
    },
    "linkedin": {
        "nome":        "LinkedIn",
        "icones":      ["💼"],
        "cor":         "#0A66C2",
        "descricao":   "Conecta LinkedIn Company Page via LinkedIn Marketing API",
        "doc_url":     "https://learn.microsoft.com/en-us/linkedin/marketing/",
        "oauth_implementado": True,
        "requer_app":  True,
        "campos": [
            {"key": "client_id",     "label": "Client ID",     "tipo": "text",     "ajuda": "Client ID do app no LinkedIn Developers"},
            {"key": "client_secret", "label": "Client Secret", "tipo": "password", "ajuda": "Client Secret do app no LinkedIn Developers"},
        ],
    },
    "google": {
        "nome":        "Google (Search Console + Analytics)",
        "icones":      ["🔍", "📈"],
        "cor":         "#4285F4",
        "descricao":   "Conecta Google Search Console e Google Analytics 4",
        "doc_url":     "https://developers.google.com/webmaster-tools",
        "em_breve": True,
        "requer_app":  True,
        "campos": [
            {"key": "client_id",     "label": "Client ID",     "tipo": "text",     "ajuda": "Client ID do projeto no Google Cloud Console"},
            {"key": "client_secret", "label": "Client Secret", "tipo": "password", "ajuda": "Client Secret do projeto no Google Cloud Console"},
        ],
    },
    "tiktok": {
        "nome":        "TikTok",
        "icones":      ["🎵"],
        "cor":         "#010101",
        "descricao":   "Conecta TikTok Business Account via TikTok for Business API",
        "doc_url":     "https://business-api.tiktok.com/",
        "em_breve": True,
        "requer_app":  True,
        "campos": [
            {"key": "app_id",     "label": "App ID",     "tipo": "text",     "ajuda": "App ID no TikTok for Developers"},
            {"key": "app_secret", "label": "App Secret", "tipo": "password", "ajuda": "App Secret no TikTok for Developers"},
        ],
    },
    "twitter": {
        "nome":        "X (Twitter)",
        "icones":      ["🐦"],
        "cor":         "#000000",
        "descricao":   "Conecta conta X/Twitter via Twitter API v2",
        "doc_url":     "https://developer.twitter.com/en/docs",
        "em_breve": True,
        "requer_app":  True,
        "campos": [
            {"key": "api_key",        "label": "API Key",        "tipo": "text",     "ajuda": "API Key do projeto no Twitter Developer Portal"},
            {"key": "api_secret",     "label": "API Secret",     "tipo": "password", "ajuda": "API Secret do projeto"},
            {"key": "bearer_token",   "label": "Bearer Token",   "tipo": "password", "ajuda": "Bearer Token para leitura de dados"},
        ],
    },
}

@bp.route("/apis-sociais")
@login_required
@requer_permissao("config.apis_sociais", "ver")
def apis_sociais():
    tid  = current_user.tenant_id
    integracoes = db.query_t(tid,
        "SELECT * FROM api_integracoes WHERE tenant_id=%s AND D_E_L_E_T=0 ORDER BY provedor, datestamp_insert DESC")
    projetos = db.query_t(tid,
        "SELECT * FROM projetos WHERE tenant_id=%s AND ativo=1 AND D_E_L_E_T=0 ORDER BY nome")

    # Agrupa integrações por provedor
    por_provedor = {}
    for integ in integracoes:
        p = integ["provedor"]
        if p not in por_provedor:
            por_provedor[p] = []
        por_provedor[p].append(integ)

    return render_template("configuracoes/apis_sociais.html",
        provedores=PROVEDORES,
        por_provedor=por_provedor,
        projetos=projetos,
        tem_permissao=tem_permissao,
    )

@bp.route("/apis-sociais/credenciais/<provedor>", methods=["POST"])
@login_required
@requer_permissao("config.apis_sociais", "editar")
def salvar_credenciais(provedor):
    """Salva App ID / Client ID e secrets do provedor nas configurações do tenant."""
    if provedor not in PROVEDORES:
        flash("Provedor inválido.", "danger")
        return redirect(url_for("configuracoes.apis_sociais"))

    tid = current_user.tenant_id
    d   = request.form
    info_provedor = PROVEDORES[provedor]

    # Monta meta_dados com as credenciais do app
    creds = {}
    for campo in info_provedor["campos"]:
        val = d.get(campo["key"], "").strip()
        if val:
            creds[campo["key"]] = val

    if not creds:
        flash("Preencha pelo menos um campo de credencial.", "warning")
        return redirect(url_for("configuracoes.apis_sociais"))

    # Verifica se já existe config para este provedor (sem projeto específico = config global)
    existente = db.query_one("""
        SELECT id FROM api_integracoes
        WHERE tenant_id=%s AND provedor=%s AND projeto_id IS NULL AND D_E_L_E_T=0
    """, (tid, provedor))

    meta = json.dumps({"app_credentials": creds}, ensure_ascii=False)

    if existente:
        db.execute("""
            UPDATE api_integracoes
            SET meta_dados=%s, status='pendente', datestamp_update=NOW()
            WHERE id=%s
        """, (meta, existente["id"]))
        flash(f"Credenciais do {info_provedor['nome']} atualizadas.", "success")
    else:
        db.execute("""
            INSERT INTO api_integracoes
                (tenant_id, provedor, nome_exibicao, status, meta_dados, criado_por)
            VALUES (%s,%s,%s,'pendente',%s,%s)
        """, (tid, provedor, info_provedor["nome"], meta, current_user.id))
        flash(f"Credenciais do {info_provedor['nome']} salvas. Agora conecte uma conta.", "success")

    return redirect(url_for("configuracoes.apis_sociais"))

# ── OAuth Meta ────────────────────────────────────────────────────
@bp.route("/apis-sociais/meta/conectar/<int:projeto_id>")
@login_required
@requer_permissao("config.apis_sociais", "editar")
def meta_conectar(projeto_id):
    """Inicia fluxo OAuth do Meta."""
    tid = current_user.tenant_id

    # Busca credenciais do app salvas
    config_meta = db.query_one("""
        SELECT meta_dados FROM api_integracoes
        WHERE tenant_id=%s AND provedor='meta' AND projeto_id IS NULL AND D_E_L_E_T=0
    """, (tid,))

    if not config_meta or not config_meta["meta_dados"]:
        flash("Configure as credenciais do Meta App primeiro.", "warning")
        return redirect(url_for("configuracoes.apis_sociais"))

    creds   = json.loads(config_meta["meta_dados"]).get("app_credentials", {})
    app_id  = creds.get("app_id") or os.getenv("META_APP_ID", "")

    if not app_id:
        flash("App ID do Meta não configurado.", "danger")
        return redirect(url_for("configuracoes.apis_sociais"))

    state = secrets.token_urlsafe(16)
    session["oauth_state"]      = state
    session["oauth_projeto_id"] = projeto_id
    session["oauth_provedor"]   = "meta"

    redirect_uri = url_for("configuracoes.meta_callback", _external=True)
    scope = "pages_show_list,pages_read_engagement,instagram_basic,instagram_manage_insights,read_insights"

    auth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth"
        f"?client_id={app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope}"
        f"&state={state}"
        f"&response_type=code"
    )
    return redirect(auth_url)

@bp.route("/apis-sociais/meta/callback")
@login_required
def meta_callback():
    """Callback OAuth do Meta — troca code por access_token."""
    tid   = current_user.tenant_id
    code  = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        flash(f"Autorização negada: {request.args.get('error_description', error)}", "danger")
        return redirect(url_for("configuracoes.apis_sociais"))

    if state != session.get("oauth_state"):
        flash("Estado OAuth inválido. Tente novamente.", "danger")
        return redirect(url_for("configuracoes.apis_sociais"))

    projeto_id = session.get("oauth_projeto_id")

    # Busca credenciais
    config_meta = db.query_one("""
        SELECT meta_dados FROM api_integracoes
        WHERE tenant_id=%s AND provedor='meta' AND projeto_id IS NULL AND D_E_L_E_T=0
    """, (tid,))
    creds      = json.loads(config_meta["meta_dados"]).get("app_credentials", {})
    app_id     = creds.get("app_id")
    app_secret = creds.get("app_secret")

    redirect_uri = url_for("configuracoes.meta_callback", _external=True)

    try:
        # Troca code por token
        resp = req_lib.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
            "client_id":     app_id,
            "client_secret": app_secret,
            "redirect_uri":  redirect_uri,
            "code":          code,
        }, timeout=15)
        resp.raise_for_status()
        token_data = resp.json()
        short_token = token_data.get("access_token")

        # Converte para long-lived token
        resp2 = req_lib.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
            "grant_type":        "fb_exchange_token",
            "client_id":         app_id,
            "client_secret":     app_secret,
            "fb_exchange_token": short_token,
        }, timeout=15)
        resp2.raise_for_status()
        long_data    = resp2.json()
        long_token   = long_data.get("access_token")
        expires_in   = long_data.get("expires_in", 5184000)  # 60 dias padrão
        expires_at   = datetime.now() + timedelta(seconds=expires_in)

        # Busca páginas do usuário
        resp3 = req_lib.get("https://graph.facebook.com/v19.0/me/accounts", params={
            "access_token": long_token,
            "fields":       "id,name,picture,access_token",
        }, timeout=15)
        resp3.raise_for_status()
        pages = resp3.json().get("data", [])

        if not pages:
            flash("Nenhuma página do Facebook encontrada na conta.", "warning")
            return redirect(url_for("configuracoes.apis_sociais"))

        # Salva cada página como uma integração separada
        for page in pages:
            page_token  = page.get("access_token", long_token)
            page_id     = page["id"]
            page_name   = page["name"]
            avatar_url  = page.get("picture", {}).get("data", {}).get("url", "") if isinstance(page.get("picture"), dict) else ""

            # Verifica se já existe
            existente = db.query_one("""
                SELECT id FROM api_integracoes
                WHERE tenant_id=%s AND provedor='meta' AND account_id=%s AND D_E_L_E_T=0
            """, (tid, page_id))

            if existente:
                db.execute("""
                    UPDATE api_integracoes SET
                        access_token=%s, token_expires_at=%s, account_name=%s,
                        status='ativo', ultimo_sync=NOW(), erro_mensagem=NULL,
                        datestamp_update=NOW()
                    WHERE id=%s
                """, (page_token, expires_at, page_name, existente["id"]))
            else:
                db.execute("""
                    INSERT INTO api_integracoes
                        (tenant_id, projeto_id, provedor, nome_exibicao, status,
                         access_token, token_expires_at, account_id, account_name,
                         account_avatar_url, criado_por)
                    VALUES (%s,%s,'meta',%s,'ativo',%s,%s,%s,%s,%s,%s)
                """, (
                    tid, projeto_id,
                    f"Meta — {page_name}",
                    page_token, expires_at,
                    page_id, page_name, avatar_url,
                    current_user.id
                ))

            _log(tid, None, "auth", "ok", f"Página '{page_name}' conectada com sucesso")

        flash(f"{len(pages)} página(s) do Facebook/Instagram conectada(s) com sucesso.", "success")

    except Exception as e:
        flash(f"Erro ao conectar Meta: {str(e)}", "danger")
        _log(tid, None, "auth", "erro", str(e))

    return redirect(url_for("configuracoes.apis_sociais"))

# ── OAuth LinkedIn ────────────────────────────────────────────────
@bp.route("/apis-sociais/linkedin/conectar/<int:projeto_id>")
@login_required
@requer_permissao("config.apis_sociais", "editar")
def linkedin_conectar(projeto_id):
    """Inicia fluxo OAuth do LinkedIn."""
    tid = current_user.tenant_id

    config_li = db.query_one("""
        SELECT meta_dados FROM api_integracoes
        WHERE tenant_id=%s AND provedor='linkedin' AND projeto_id IS NULL AND D_E_L_E_T=0
    """, (tid,))

    if not config_li:
        flash("Configure as credenciais do LinkedIn App primeiro.", "warning")
        return redirect(url_for("configuracoes.apis_sociais"))

    creds     = json.loads(config_li["meta_dados"]).get("app_credentials", {})
    client_id = creds.get("client_id") or os.getenv("LINKEDIN_CLIENT_ID", "")

    if not client_id:
        flash("Client ID do LinkedIn não configurado.", "danger")
        return redirect(url_for("configuracoes.apis_sociais"))

    state = secrets.token_urlsafe(16)
    session["oauth_state"]      = state
    session["oauth_projeto_id"] = projeto_id
    session["oauth_provedor"]   = "linkedin"

    redirect_uri = url_for("configuracoes.linkedin_callback", _external=True)
    scope        = "r_liteprofile,openid,profile"

    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope}"
        f"&state={state}"
    )
    return redirect(auth_url)

@bp.route("/apis-sociais/linkedin/callback")
@login_required
def linkedin_callback():
    """Callback OAuth do LinkedIn."""
    tid   = current_user.tenant_id
    code  = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        flash(f"Autorização negada: {request.args.get('error_description', error)}", "danger")
        return redirect(url_for("configuracoes.apis_sociais"))

    if state != session.get("oauth_state"):
        flash("Estado OAuth inválido.", "danger")
        return redirect(url_for("configuracoes.apis_sociais"))

    projeto_id = session.get("oauth_projeto_id")

    config_li    = db.query_one("""
        SELECT meta_dados FROM api_integracoes
        WHERE tenant_id=%s AND provedor='linkedin' AND projeto_id IS NULL AND D_E_L_E_T=0
    """, (tid,))
    creds        = json.loads(config_li["meta_dados"]).get("app_credentials", {})
    client_id    = creds.get("client_id")
    client_secret= creds.get("client_secret")
    redirect_uri = url_for("configuracoes.linkedin_callback", _external=True)

    try:
        # Troca code por token
        resp = req_lib.post("https://www.linkedin.com/oauth/v2/accessToken", data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  redirect_uri,
            "client_id":     client_id,
            "client_secret": client_secret,
        }, timeout=15)
        resp.raise_for_status()
        token_data   = resp.json()
        access_token = token_data.get("access_token")
        expires_in   = token_data.get("expires_in", 5184000)
        expires_at   = datetime.now() + timedelta(seconds=expires_in)

        # Busca organizações administradas
        resp2 = req_lib.get(
            "https://api.linkedin.com/v2/organizationAcls",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            params={"q": "roleAssignee", "role": "ADMINISTRATOR"},
            timeout=15
        )
        resp2.raise_for_status()
        orgs = resp2.json().get("elements", [])

        if not orgs:
            flash("Nenhuma organização encontrada no LinkedIn.", "warning")
            return redirect(url_for("configuracoes.apis_sociais"))

        for org in orgs:
            org_urn  = org.get("organization", "")
            org_id   = org_urn.split(":")[-1] if org_urn else ""

            # Busca nome da organização
            resp3 = req_lib.get(
                f"https://api.linkedin.com/v2/organizations/{org_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15
            )
            org_name = resp3.json().get("localizedName", org_id) if resp3.ok else org_id

            existente = db.query_one("""
                SELECT id FROM api_integracoes
                WHERE tenant_id=%s AND provedor='linkedin' AND account_id=%s AND D_E_L_E_T=0
            """, (tid, org_id))

            if existente:
                db.execute("""
                    UPDATE api_integracoes SET
                        access_token=%s, token_expires_at=%s, account_name=%s,
                        status='ativo', ultimo_sync=NOW(), datestamp_update=NOW()
                    WHERE id=%s
                """, (access_token, expires_at, org_name, existente["id"]))
            else:
                db.execute("""
                    INSERT INTO api_integracoes
                        (tenant_id, projeto_id, provedor, nome_exibicao, status,
                         access_token, token_expires_at, account_id, account_name, criado_por)
                    VALUES (%s,%s,'linkedin',%s,'ativo',%s,%s,%s,%s,%s)
                """, (
                    tid, projeto_id,
                    f"LinkedIn — {org_name}",
                    access_token, expires_at,
                    org_id, org_name, current_user.id
                ))

            _log(tid, None, "auth", "ok", f"LinkedIn '{org_name}' conectado")

        flash(f"{len(orgs)} organização(ões) do LinkedIn conectada(s).", "success")

    except Exception as e:
        flash(f"Erro ao conectar LinkedIn: {str(e)}", "danger")
        _log(tid, None, "auth", "erro", str(e))

    return redirect(url_for("configuracoes.apis_sociais"))

# ── Desconectar integração ────────────────────────────────────────
@bp.route("/apis-sociais/desconectar/<int:integracao_id>")
@login_required
@requer_permissao("config.apis_sociais", "deletar")
def desconectar(integracao_id):
    tid = current_user.tenant_id
    db.execute_t(tid,
        "UPDATE api_integracoes SET D_E_L_E_T=1, ativo=0, datestamp_update=NOW() WHERE id=%s AND tenant_id=%s",
        (integracao_id,)
    )
    flash("Integração desconectada.", "success")
    return redirect(url_for("configuracoes.apis_sociais"))

# ── API: status das integrações (JSON) ───────────────────────────
@bp.route("/apis-sociais/status")
@login_required
def status_integracoes():
    tid = current_user.tenant_id
    integracoes = db.query_t(tid,
        """SELECT provedor, account_name, status, ultimo_sync, token_expires_at
           FROM api_integracoes
           WHERE tenant_id=%s AND D_E_L_E_T=0 AND ativo=1
           ORDER BY provedor""")
    return jsonify([dict(r) for r in integracoes])

@bp.route("/apis-sociais/meta/webhook-verify", methods=["GET"])
def meta_webhook_verify():
    import os
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == os.getenv("META_VERIFY_TOKEN", "selenio2026"):
        return challenge, 200
    return "Forbidden", 403
