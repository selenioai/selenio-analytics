"""
modules/keywords/providers.py

Arquitetura plugável de fontes de rastreamento.
Cada provider implementa o mesmo contrato:
    rastrear(keyword: dict, config: dict) -> dict

Retorno padrão:
{
    "posicao": int | None,
    "url_encontrada": str | None,
    "volume_busca": int | None,
    "dificuldade": int | None,
    "cpc": float | None,
    "fonte": str,
    "raw_data": dict
}

Para adicionar novo provider:
1. Crie a função rastrear_<nome>(keyword, config)
2. Registre em PROVIDERS dict abaixo
"""

import requests
import time
import random
import json
from datetime import datetime


# ─────────────────────────────────────────────
# CONTRATO BASE
# ─────────────────────────────────────────────

RESULTADO_VAZIO = {
    "posicao": None,
    "url_encontrada": None,
    "volume_busca": None,
    "dificuldade": None,
    "cpc": None,
    "fonte": "manual",
    "raw_data": {}
}


# ─────────────────────────────────────────────
# PROVIDER 1 — MANUAL
# O usuário insere a posição diretamente.
# Nenhuma chamada externa.
# ─────────────────────────────────────────────

def rastrear_manual(keyword: dict, config: dict, posicao_manual: int = None) -> dict:
    """Registra posição informada manualmente pelo usuário."""
    resultado = RESULTADO_VAZIO.copy()
    resultado["fonte"] = "manual"
    resultado["posicao"] = posicao_manual
    resultado["raw_data"] = {
        "input": "manual",
        "registrado_em": datetime.utcnow().isoformat()
    }
    return resultado


# ─────────────────────────────────────────────
# PROVIDER 2 — GOOGLE SEARCH CONSOLE
# Usa a API oficial do GSC para obter
# impressões, cliques e posição média.
# Hook pronto — requer credenciais OAuth.
# ─────────────────────────────────────────────

def rastrear_gsc(keyword: dict, config: dict) -> dict:
    """
    Rastreia via Google Search Console API.
    Requer: config['gsc_property_url'] e config['gsc_token_json']
    
    Documentação: https://developers.google.com/webmaster-tools/v1/api_reference_index
    """
    resultado = RESULTADO_VAZIO.copy()
    resultado["fonte"] = "gsc"

    # ── HOOK: implementar quando GSC OAuth estiver configurado ──
    # from google.oauth2.credentials import Credentials
    # from googleapiclient.discovery import build
    #
    # creds = Credentials.from_authorized_user_info(
    #     json.loads(config["gsc_token_json"])
    # )
    # service = build("webmasters", "v3", credentials=creds)
    #
    # body = {
    #     "startDate": "30daysAgo",
    #     "endDate": "today",
    #     "dimensions": ["query"],
    #     "dimensionFilterGroups": [{
    #         "filters": [{
    #             "dimension": "query",
    #             "operator": "equals",
    #             "expression": keyword["termo"]
    #         }]
    #     }]
    # }
    # response = service.searchanalytics().query(
    #     siteUrl=config["gsc_property_url"],
    #     body=body
    # ).execute()
    #
    # if response.get("rows"):
    #     row = response["rows"][0]
    #     resultado["posicao"] = round(row["position"])
    #     resultado["raw_data"] = row
    # ────────────────────────────────────────────────────────────

    resultado["raw_data"] = {
        "status": "hook_pendente",
        "mensagem": "GSC OAuth ainda não configurado para este projeto"
    }
    return resultado


# ─────────────────────────────────────────────
# PROVIDER 3 — SCRAPING GOOGLE
# Busca no Google e extrai posição.
# ATENÇÃO: uso pessoal/interno apenas.
# Em produção use proxies rotativos.
# ─────────────────────────────────────────────

def rastrear_scraping(keyword: dict, config: dict) -> dict:
    """
    Rastreia via scraping do Google Search.
    Retorna posição do domínio do projeto nos resultados.
    
    Config esperada:
        config['dominio']       — domínio a buscar (ex: solidy.com.br)
        config['scraping_pais'] — código do país (default: br)
    """
    resultado = RESULTADO_VAZIO.copy()
    resultado["fonte"] = "scraping"

    # ── HOOK: implementar scraping com BeautifulSoup ──
    # IMPORTANTE: Em produção, usar proxies e user-agents rotativos
    # para evitar bloqueio. Opções: ScraperAPI, BrightData, Oxylabs.
    #
    # import re
    # from bs4 import BeautifulSoup
    #
    # dominio = config.get("dominio", "")
    # pais = config.get("scraping_pais", "br")
    # termo = keyword["termo"]
    #
    # headers = {
    #     "User-Agent": random.choice(USER_AGENTS),
    #     "Accept-Language": "pt-BR,pt;q=0.9"
    # }
    #
    # url = f"https://www.google.com.br/search?q={requests.utils.quote(termo)}&num=100&gl={pais}"
    # resp = requests.get(url, headers=headers, timeout=15)
    # soup = BeautifulSoup(resp.text, "html.parser")
    #
    # resultados = soup.select("div.g")
    # for i, r in enumerate(resultados, 1):
    #     link = r.select_one("a")
    #     if link and dominio in link.get("href", ""):
    #         resultado["posicao"] = i
    #         resultado["url_encontrada"] = link["href"]
    #         break
    #
    # time.sleep(random.uniform(2, 5))  # evitar bloqueio
    # ─────────────────────────────────────────────────────

    resultado["raw_data"] = {
        "status": "hook_pendente",
        "mensagem": "Scraping não ativado — configure proxies antes de usar"
    }
    return resultado


# ─────────────────────────────────────────────
# PROVIDER 4 — DATAFORSEO
# API profissional com dados precisos.
# Cobrança por requisição (~$0.003/keyword).
# ─────────────────────────────────────────────

def rastrear_dataforseo(keyword: dict, config: dict) -> dict:
    """
    Rastreia via DataForSEO API.
    Retorna posição + volume + KD + CPC.
    
    Docs: https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/
    Config esperada:
        config['dataforseo_login']    — email da conta DataForSEO
        config['dataforseo_password'] — senha da API DataForSEO
    """
    resultado = RESULTADO_VAZIO.copy()
    resultado["fonte"] = "dataforseo"

    login    = config.get("dataforseo_login")
    password = config.get("dataforseo_password")

    if not login or not password:
        resultado["raw_data"] = {
            "status": "erro",
            "mensagem": "Credenciais DataForSEO não configuradas"
        }
        return resultado

    # ── HOOK: implementar quando DataForSEO estiver contratado ──
    # import base64
    #
    # auth = base64.b64encode(f"{login}:{password}".encode()).decode()
    # headers = {
    #     "Authorization": f"Basic {auth}",
    #     "Content-Type": "application/json"
    # }
    #
    # payload = [{
    #     "keyword": keyword["termo"],
    #     "location_code": 2076,        # Brasil
    #     "language_code": "pt",
    #     "device": "desktop",
    #     "depth": 100
    # }]
    #
    # resp = requests.post(
    #     "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
    #     headers=headers,
    #     json=payload,
    #     timeout=30
    # )
    # data = resp.json()
    #
    # if data["status_code"] == 20000:
    #     items = data["tasks"][0]["result"][0]["items"]
    #     dominio = config.get("dominio", "")
    #     for item in items:
    #         if dominio in item.get("url", ""):
    #             resultado["posicao"]       = item["rank_absolute"]
    #             resultado["url_encontrada"] = item["url"]
    #             resultado["raw_data"]      = item
    #             break
    #
    # # Volume e KD (endpoint separado — Keywords Data)
    # # resp_kd = requests.post(
    # #     "https://api.dataforseo.com/v3/keywords_data/google/search_volume/live",
    # #     headers=headers,
    # #     json=[{"keywords": [keyword["termo"]], "location_code": 2076}],
    # #     timeout=30
    # # )
    # ─────────────────────────────────────────────────────────────

    resultado["raw_data"] = {
        "status": "hook_pendente",
        "mensagem": "DataForSEO não ativado — configure login/password nas configurações"
    }
    return resultado


# ─────────────────────────────────────────────
# REGISTRY — mapa de providers disponíveis
# ─────────────────────────────────────────────

PROVIDERS = {
    "manual":      rastrear_manual,
    "gsc":         rastrear_gsc,
    "scraping":    rastrear_scraping,
    "dataforseo":  rastrear_dataforseo,
}

PROVIDERS_INFO = {
    "manual": {
        "nome":      "Manual",
        "descricao": "Você insere a posição diretamente",
        "icone":     "✏️",
        "gratuito":  True,
        "status":    "ativo"
    },
    "gsc": {
        "nome":      "Google Search Console",
        "descricao": "Dados reais do Google via OAuth",
        "icone":     "🔍",
        "gratuito":  True,
        "status":    "em_breve"
    },
    "scraping": {
        "nome":      "Scraping Google",
        "descricao": "Rastreamento automático via busca",
        "icone":     "🤖",
        "gratuito":  True,
        "status":    "em_breve"
    },
    "dataforseo": {
        "nome":      "DataForSEO",
        "descricao": "Dados profissionais com volume e KD",
        "icone":     "📊",
        "gratuito":  False,
        "status":    "em_breve"
    }
}


def executar_rastreamento(keyword: dict, config: dict, posicao_manual: int = None) -> dict:
    """
    Ponto de entrada único para rastreamento.
    Seleciona o provider correto baseado em config['fonte'].
    """
    fonte = config.get("fonte", "manual")
    provider_fn = PROVIDERS.get(fonte, rastrear_manual)

    if fonte == "manual":
        return provider_fn(keyword, config, posicao_manual)
    return provider_fn(keyword, config)
