"""
modules/keywords/gsc.py

Integração com Google Search Console API.
Usa a tabela api_integracoes (provedor='google_gsc') para armazenar tokens OAuth.

Fluxo OAuth:
1. /keywords/<projeto_id>/gsc/conectar  → redireciona para Google
2. /keywords/<projeto_id>/gsc/callback  → recebe code, troca por tokens, salva
3. /keywords/<projeto_id>/gsc/sincronizar → importa posições do GSC

Escopos necessários:
- https://www.googleapis.com/auth/webmasters.readonly
- openid, email, profile
"""

import json
import secrets
import requests
from datetime import datetime, timedelta
from flask import (Blueprint, redirect, request, url_for,
                   flash, session, render_template, jsonify)
from flask_login import login_required, current_user
import db

bp_gsc = Blueprint("gsc", __name__)

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────

GOOGLE_AUTH_URL    = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL   = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL  = "https://oauth2.googleapis.com/revoke"
GSC_API_BASE       = "https://www.googleapis.com/webmasters/v3"

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/webmasters.readonly",
]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_credenciais_app(tenant_id):
    """Busca client_id e client_secret do Google configurados pelo tenant."""
    row = db.query_one(
        """SELECT meta_dados FROM api_integracoes
           WHERE tenant_id=%s AND provedor='google_app' AND ativo=1 AND d_e_l_e_t=0
           ORDER BY datestamp_insert DESC LIMIT 1""",
        (tenant_id,)
    )
    if not row or not row["meta_dados"]:
        return None, None
    dados = json.loads(row["meta_dados"])
    return dados.get("client_id"), dados.get("client_secret")


def _get_token(tenant_id, projeto_id):
    """Busca token GSC do projeto."""
    return db.query_one(
        """SELECT * FROM api_integracoes
           WHERE tenant_id=%s AND projeto_id=%s
             AND provedor='google_gsc' AND ativo=1 AND d_e_l_e_t=0
           ORDER BY datestamp_insert DESC LIMIT 1""",
        (tenant_id, projeto_id)
    )


def _refresh_token_se_necessario(integracao):
    """Renova o access_token se expirado. Retorna token atualizado."""
    if not integracao["refresh_token"]:
        return integracao["access_token"]

    expires_at = integracao.get("token_expires_at")
    if expires_at and expires_at > datetime.utcnow() + timedelta(minutes=5):
        return integracao["access_token"]  # ainda válido

    # Buscar credenciais do app
    client_id, client_secret = _get_credenciais_app(integracao["tenant_id"])
    if not client_id:
        return integracao["access_token"]

    resp = requests.post(GOOGLE_TOKEN_URL, data={
        "grant_type":    "refresh_token",
        "refresh_token": integracao["refresh_token"],
        "client_id":     client_id,
        "client_secret": client_secret,
    }, timeout=15)

    if resp.status_code == 200:
        data = resp.json()
        novo_token  = data.get("access_token")
        expires_in  = data.get("expires_in", 3600)
        expires_at  = datetime.utcnow() + timedelta(seconds=expires_in)

        db.execute(
            """UPDATE api_integracoes
               SET access_token=%s, token_expires_at=%s, datestamp_update=NOW()
               WHERE id=%s""",
            (novo_token, expires_at, integracao["id"])
        )
        return novo_token

    return integracao["access_token"]


# ─────────────────────────────────────────────
# ROTA 1 — Iniciar OAuth
# ─────────────────────────────────────────────

@bp_gsc.route("/<int:projeto_id>/gsc/conectar")
@login_required
def conectar(projeto_id):
    client_id, _ = _get_credenciais_app(current_user.tenant_id)
    if not client_id:
        flash("Configure o Client ID e Client Secret do Google antes de conectar.", "warning")
        return redirect(url_for("keywords.config", projeto_id=projeto_id))

    state = secrets.token_urlsafe(16)
    session["gsc_state"]      = state
    session["gsc_projeto_id"] = projeto_id

    callback_url = url_for("gsc.callback", _external=True)

    params = {
        "client_id":             client_id,
        "redirect_uri":          callback_url,
        "response_type":         "code",
        "scope":                 " ".join(SCOPES),
        "access_type":           "offline",   # para receber refresh_token
        "prompt":                "consent",   # força exibir tela de consentimento
        "state":                 state,
    }

    url = GOOGLE_AUTH_URL + "?" + "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return redirect(url)


# ─────────────────────────────────────────────
# ROTA 2 — Callback OAuth
# ─────────────────────────────────────────────

@bp_gsc.route("/gsc/callback")
@login_required
def callback():
    error      = request.args.get("error")
    code       = request.args.get("code")
    state      = request.args.get("state")
    projeto_id = session.get("gsc_projeto_id")

    if error:
        flash(f"Erro ao conectar Google: {error}", "error")
        return redirect(url_for("keywords.config", projeto_id=projeto_id or 1))

    if state != session.get("gsc_state"):
        flash("Estado OAuth inválido. Tente novamente.", "error")
        return redirect(url_for("keywords.config", projeto_id=projeto_id or 1))

    client_id, client_secret = _get_credenciais_app(current_user.tenant_id)
    callback_url = url_for("gsc.callback", _external=True)

    # Trocar code por tokens
    resp = requests.post(GOOGLE_TOKEN_URL, data={
        "code":          code,
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  callback_url,
        "grant_type":    "authorization_code",
    }, timeout=15)

    if resp.status_code != 200:
        flash(f"Erro ao obter token Google: {resp.text}", "error")
        return redirect(url_for("keywords.config", projeto_id=projeto_id))

    token_data   = resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in   = token_data.get("expires_in", 3600)
    expires_at   = datetime.utcnow() + timedelta(seconds=expires_in)

    # Buscar info do usuário Google
    user_resp = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )
    user_info = user_resp.json() if user_resp.status_code == 200 else {}

    # Buscar propriedades do GSC disponíveis
    sites_resp = requests.get(
        f"{GSC_API_BASE}/sites",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )
    sites = []
    if sites_resp.status_code == 200:
        sites = sites_resp.json().get("siteEntry", [])

    # Salvar token na api_integracoes
    existente = _get_token(current_user.tenant_id, projeto_id)
    meta_dados = json.dumps({"sites": sites})

    if existente:
        db.execute(
            """UPDATE api_integracoes
               SET access_token=%s, refresh_token=%s, token_expires_at=%s,
                   account_name=%s, account_avatar_url=%s, meta_dados=%s,
                   status='ativo', erro_mensagem=NULL, datestamp_update=NOW()
               WHERE id=%s""",
            (
                access_token, refresh_token or existente["refresh_token"],
                expires_at,
                user_info.get("name", ""),
                user_info.get("picture", ""),
                meta_dados,
                existente["id"]
            )
        )
    else:
        db.execute(
            """INSERT INTO api_integracoes
               (tenant_id, projeto_id, provedor, nome_exibicao, status,
                access_token, refresh_token, token_expires_at,
                account_name, account_avatar_url, meta_dados, criado_por)
               VALUES (%s,%s,'google_gsc',%s,'ativo',%s,%s,%s,%s,%s,%s,%s)""",
            (
                current_user.tenant_id, projeto_id,
                f"GSC — {user_info.get('email', '')}",
                access_token, refresh_token, expires_at,
                user_info.get("name", ""),
                user_info.get("picture", ""),
                meta_dados,
                current_user.id
            )
        )

    # Salvar property selecionada na keyword_fonte_config
    # (usuário vai selecionar depois na tela de config)
    db.execute(
        """UPDATE keyword_fonte_config SET fonte='gsc', datestamp_update=NOW()
           WHERE projeto_id=%s""",
        (projeto_id,)
    )

    flash("✅ Google Search Console conectado com sucesso!", "success")
    return redirect(url_for("gsc.selecionar_property", projeto_id=projeto_id))


# ─────────────────────────────────────────────
# ROTA 3 — Selecionar property do GSC
# ─────────────────────────────────────────────

@bp_gsc.route("/<int:projeto_id>/gsc/property", methods=["GET", "POST"])
@login_required
def selecionar_property(projeto_id):
    integracao = _get_token(current_user.tenant_id, projeto_id)
    if not integracao:
        flash("GSC não conectado.", "error")
        return redirect(url_for("keywords.config", projeto_id=projeto_id))

    meta = json.loads(integracao["meta_dados"] or "{}")
    sites = meta.get("sites", [])

    if request.method == "POST":
        property_url = request.form.get("property_url")
        if property_url:
            # Atualizar config com a property selecionada
            db.execute(
                """UPDATE keyword_fonte_config
                   SET gsc_property_url=%s, datestamp_update=NOW()
                   WHERE projeto_id=%s""",
                (property_url, projeto_id)
            )
            # Atualizar meta_dados da integração
            meta["property_selecionada"] = property_url
            db.execute(
                "UPDATE api_integracoes SET meta_dados=%s WHERE id=%s",
                (json.dumps(meta), integracao["id"])
            )
            flash(f"Property {property_url} selecionada!", "success")
            return redirect(url_for("keywords.config", projeto_id=projeto_id))

    projeto = db.query_one(
        "SELECT * FROM projetos WHERE id=%s AND tenant_id=%s",
        (projeto_id, current_user.tenant_id)
    )
    return render_template(
        "keywords/gsc_property.html",
        projeto=projeto,
        sites=sites,
        integracao=integracao
    )


# ─────────────────────────────────────────────
# ROTA 4 — Sincronizar posições do GSC
# ─────────────────────────────────────────────

@bp_gsc.route("/<int:projeto_id>/gsc/sincronizar", methods=["POST"])
@login_required
def sincronizar(projeto_id):
    integracao = _get_token(current_user.tenant_id, projeto_id)
    if not integracao:
        return jsonify({"ok": False, "erro": "GSC não conectado"}), 400

    config = db.query_one(
        "SELECT * FROM keyword_fonte_config WHERE projeto_id=%s",
        (projeto_id,)
    )
    property_url = config.get("gsc_property_url") if config else None
    if not property_url:
        return jsonify({"ok": False, "erro": "Nenhuma property GSC selecionada"}), 400

    # Renovar token se necessário
    access_token = _refresh_token_se_necessario(integracao)

    # Buscar keywords do projeto
    keywords = db.query(
        "SELECT * FROM keywords WHERE projeto_id=%s AND d_e_l_e_t=0 AND ativo=1",
        (projeto_id,)
    )

    if not keywords:
        return jsonify({"ok": False, "erro": "Nenhuma keyword cadastrada"}), 400

    # Definir período (últimos 28 dias)
    end_date   = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=28)).strftime("%Y-%m-%d")

    resultados = []
    erros      = []

    for kw in keywords:
        try:
            body = {
                "startDate":  start_date,
                "endDate":    end_date,
                "dimensions": ["query"],
                "dimensionFilterGroups": [{
                    "filters": [{
                        "dimension":  "query",
                        "operator":   "equals",
                        "expression": kw["termo"]
                    }]
                }],
                "rowLimit": 1
            }

            resp = requests.post(
                f"{GSC_API_BASE}/sites/{requests.utils.quote(property_url, safe='')}/searchAnalytics/query",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type":  "application/json"
                },
                json=body,
                timeout=20
            )

            posicao         = None
            url_encontrada  = None
            raw_data        = {}

            if resp.status_code == 200:
                data = resp.json()
                rows = data.get("rows", [])
                if rows:
                    row     = rows[0]
                    posicao = round(row.get("position", 0))
                    raw_data = row
            else:
                erros.append(f"{kw['termo']}: {resp.text}")

            # Salvar posição
            pos_anterior_row = db.query_one(
                "SELECT posicao FROM keyword_posicoes WHERE keyword_id=%s ORDER BY rastreado_em DESC LIMIT 1",
                (kw["id"],)
            )
            pos_anterior = pos_anterior_row["posicao"] if pos_anterior_row else None

            db.execute(
                """INSERT INTO keyword_posicoes
                   (keyword_id, projeto_id, posicao, url_encontrada,
                    volume_busca, fonte, raw_data)
                   VALUES (%s,%s,%s,%s,%s,'gsc',%s)""",
                (
                    kw["id"], projeto_id, posicao, url_encontrada,
                    int(raw_data.get("impressions", 0)) if raw_data else None,
                    json.dumps(raw_data)
                )
            )

            # Alerta de variação
            if posicao and pos_anterior:
                variacao = pos_anterior - posicao
                if abs(variacao) >= 5:
                    tipo = "subida" if variacao > 0 else "queda"
                    if pos_anterior > 10 and posicao <= 10:
                        tipo = "entrada_top10"
                    elif pos_anterior <= 10 and posicao > 10:
                        tipo = "saiu_top10"
                    db.execute(
                        """INSERT INTO keyword_alertas
                           (keyword_id, projeto_id, tipo, posicao_anterior, posicao_atual, variacao)
                           VALUES (%s,%s,%s,%s,%s,%s)""",
                        (kw["id"], projeto_id, tipo, pos_anterior, posicao, variacao)
                    )

            resultados.append({
                "keyword": kw["termo"],
                "posicao": posicao,
                "impressoes": raw_data.get("impressions"),
                "cliques": raw_data.get("clicks"),
                "ctr": raw_data.get("ctr"),
            })

        except Exception as e:
            erros.append(f"{kw['termo']}: {str(e)}")

    # Atualizar último sync
    db.execute(
        "UPDATE api_integracoes SET ultimo_sync=NOW() WHERE id=%s",
        (integracao["id"],)
    )

    return jsonify({
        "ok":        True,
        "total":     len(resultados),
        "erros":     erros,
        "resultados": resultados,
        "periodo":   f"{start_date} → {end_date}"
    })


# ─────────────────────────────────────────────
# ROTA 5 — Desconectar GSC
# ─────────────────────────────────────────────

@bp_gsc.route("/<int:projeto_id>/gsc/desconectar", methods=["POST"])
@login_required
def desconectar(projeto_id):
    integracao = _get_token(current_user.tenant_id, projeto_id)
    if integracao:
        # Revogar token no Google
        try:
            requests.post(
                GOOGLE_REVOKE_URL,
                params={"token": integracao["access_token"]},
                timeout=10
            )
        except Exception:
            pass

        db.execute(
            "UPDATE api_integracoes SET d_e_l_e_t=1, ativo=0 WHERE id=%s",
            (integracao["id"],)
        )
        db.execute(
            "UPDATE keyword_fonte_config SET fonte='manual', gsc_property_url=NULL WHERE projeto_id=%s",
            (projeto_id,)
        )

    flash("Google Search Console desconectado.", "success")
    return redirect(url_for("keywords.config", projeto_id=projeto_id))


# ─────────────────────────────────────────────
# ROTA 6 — Status da conexão (JSON)
# ─────────────────────────────────────────────

@bp_gsc.route("/<int:projeto_id>/gsc/status")
@login_required
def status(projeto_id):
    integracao = _get_token(current_user.tenant_id, projeto_id)
    if not integracao:
        return jsonify({"conectado": False})

    meta = json.loads(integracao["meta_dados"] or "{}")
    return jsonify({
        "conectado":          True,
        "account_name":       integracao["account_name"],
        "account_avatar":     integracao["account_avatar_url"],
        "property":           meta.get("property_selecionada"),
        "ultimo_sync":        integracao["ultimo_sync"].isoformat() if integracao["ultimo_sync"] else None,
        "sites_disponiveis":  len(meta.get("sites", []))
    })
