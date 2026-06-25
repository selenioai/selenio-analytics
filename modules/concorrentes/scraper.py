"""
modules/concorrentes/scraper.py

Scraper do Google Search para rastrear posições de domínios.

Arquitetura:
- Sem proxy: uso pessoal/interno, risco de bloqueio após muitas requisições
- Com proxy: produção, uso comercial (ScraperAPI, BrightData, Oxylabs)

Configuração via .env:
    SCRAPING_MODO=direto|scraperapi|brightdata
    SCRAPERAPI_KEY=sua_chave          (se modo=scraperapi)
    BRIGHTDATA_USER=user              (se modo=brightdata)
    BRIGHTDATA_PASS=pass
    BRIGHTDATA_HOST=brd.superproxy.io
    BRIGHTDATA_PORT=22225

Retorno padrão por keyword:
{
    "keyword": "contabilidade digital",
    "resultados": [
        {"posicao": 1, "dominio": "site.com.br", "url": "https://...", "titulo": "..."},
        ...
    ],
    "meu_site": {"posicao": 7, "url": "https://..."},
    "concorrentes": {
        "agilize.com.br": {"posicao": 3, "url": "https://..."},
        ...
    }
}
"""

import os
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# USER AGENTS rotativos
# ─────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _extrair_dominio(url: str) -> str:
    """Extrai domínio limpo de uma URL."""
    try:
        parsed = urlparse(url)
        dominio = parsed.netloc.lower()
        dominio = dominio.replace("www.", "")
        return dominio
    except Exception:
        return ""


def _dominio_match(url: str, dominio_alvo: str) -> bool:
    """Verifica se a URL pertence ao domínio alvo."""
    dom = _extrair_dominio(url)
    alvo = dominio_alvo.lower().replace("www.", "")
    return dom == alvo or dom.endswith("." + alvo)


def _headers_aleatorios() -> dict:
    """Gera headers aleatórios para parecer um browser real."""
    return {
        "User-Agent":      random.choice(USER_AGENTS),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT":             "1",
        "Connection":      "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest":  "document",
        "Sec-Fetch-Mode":  "navigate",
        "Sec-Fetch-Site":  "none",
        "Cache-Control":   "max-age=0",
    }


# ─────────────────────────────────────────────
# MODO 1 — SCRAPING DIRETO (sem proxy)
# ─────────────────────────────────────────────

def _buscar_direto(keyword: str, pais: str = "br", num: int = 50) -> str:
    """
    Faz busca direta no Google. 
    Risco de bloqueio em uso intensivo.
    Para uso pessoal/interno ou baixo volume.
    """
    url = f"https://www.google.com.br/search?q={quote_plus(keyword)}&num={num}&gl={pais}&hl=pt-BR"
    
    session = requests.Session()
    resp = session.get(
        url,
        headers=_headers_aleatorios(),
        timeout=15,
        allow_redirects=True
    )
    
    if resp.status_code != 200:
        raise Exception(f"Google retornou status {resp.status_code}")
    
    # Verificar se foi bloqueado (CAPTCHA)
    if "captcha" in resp.text.lower() or "unusual traffic" in resp.text.lower():
        raise Exception("Google bloqueou a requisição (CAPTCHA). Use modo proxy.")
    
    return resp.text


# ─────────────────────────────────────────────
# MODO 2 — SCRAPERAPI (proxy pago)
# https://www.scraperapi.com — $49/mês 100k requisições
# ─────────────────────────────────────────────

def _buscar_scraperapi(keyword: str, pais: str = "br", num: int = 50) -> str:
    """
    Busca via ScraperAPI — resolve CAPTCHAs automaticamente.
    Configure SCRAPERAPI_KEY no .env
    """
    api_key = os.getenv("SCRAPERAPI_KEY")
    if not api_key:
        raise Exception("SCRAPERAPI_KEY não configurada no .env")
    
    google_url = f"https://www.google.com.br/search?q={quote_plus(keyword)}&num={num}&gl={pais}&hl=pt-BR"
    
    resp = requests.get(
        "http://api.scraperapi.com",
        params={
            "api_key":    api_key,
            "url":        google_url,
            "country_code": pais,
            "render":     "false"
        },
        timeout=30
    )
    
    if resp.status_code != 200:
        raise Exception(f"ScraperAPI retornou status {resp.status_code}: {resp.text}")
    
    return resp.text


# ─────────────────────────────────────────────
# MODO 3 — BRIGHTDATA (proxy pago premium)
# https://brightdata.com — mais robusto e caro
# ─────────────────────────────────────────────

def _buscar_brightdata(keyword: str, pais: str = "br", num: int = 50) -> str:
    """
    Busca via BrightData residential proxy.
    Configure BRIGHTDATA_USER, BRIGHTDATA_PASS no .env
    """
    user = os.getenv("BRIGHTDATA_USER")
    pwd  = os.getenv("BRIGHTDATA_PASS")
    host = os.getenv("BRIGHTDATA_HOST", "brd.superproxy.io")
    port = os.getenv("BRIGHTDATA_PORT", "22225")
    
    if not user or not pwd:
        raise Exception("Credenciais BrightData não configuradas no .env")
    
    proxy_url = f"http://{user}:{pwd}@{host}:{port}"
    proxies   = {"http": proxy_url, "https": proxy_url}
    
    google_url = f"https://www.google.com.br/search?q={quote_plus(keyword)}&num={num}&gl={pais}&hl=pt-BR"
    
    resp = requests.get(
        google_url,
        headers=_headers_aleatorios(),
        proxies=proxies,
        timeout=30,
        verify=False  # BrightData usa SSL próprio
    )
    
    return resp.text


# ─────────────────────────────────────────────
# PARSER — Extrai resultados do HTML do Google
# ─────────────────────────────────────────────

def _parsear_resultados(html: str, num_resultados: int = 50) -> list:
    """
    Extrai lista de resultados orgânicos do HTML do Google.
    Retorna lista de dicts: {posicao, url, dominio, titulo, descricao}
    """
    soup = BeautifulSoup(html, "lxml")
    resultados = []
    posicao = 1

    # Seletores do Google (podem mudar com atualizações)
    # Tentamos múltiplos seletores para robustez
    blocos = (
        soup.select("div.g") or
        soup.select("div[data-hveid]") or
        soup.select("div.tF2Cxc")
    )

    for bloco in blocos:
        if posicao > num_resultados:
            break

        # Tentar encontrar o link
        link = bloco.select_one("a[href]")
        if not link:
            continue

        url = link.get("href", "")
        if not url.startswith("http"):
            continue

        # Ignorar resultados que não são orgânicos
        if any(x in url for x in ["google.com", "youtube.com", "maps.google"]):
            continue

        # Título
        titulo_el = bloco.select_one("h3")
        titulo    = titulo_el.get_text(strip=True) if titulo_el else ""

        # Descrição
        desc_el  = bloco.select_one("div.VwiC3b, span.aCOpRe, div[data-sncf]")
        descricao = desc_el.get_text(strip=True) if desc_el else ""

        dominio = _extrair_dominio(url)
        if not dominio:
            continue

        resultados.append({
            "posicao":   posicao,
            "url":       url,
            "dominio":   dominio,
            "titulo":    titulo[:200],
            "descricao": descricao[:300],
        })
        posicao += 1

    return resultados


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────

def rastrear_posicoes(
    keyword:     str,
    meu_dominio: str,
    dominios_concorrentes: list,
    pais:        str = "br",
    delay:       float = None
) -> dict:
    """
    Rastreia posições no Google para uma keyword.
    
    Args:
        keyword: termo a buscar
        meu_dominio: domínio do projeto (ex: solidycontabilidade.com.br)
        dominios_concorrentes: lista de domínios concorrentes
        pais: código do país (br, us, pt...)
        delay: segundos de espera antes da busca (None = aleatório 2-5s)
    
    Returns:
        {
            "keyword": str,
            "ok": bool,
            "erro": str | None,
            "resultados": [...],
            "meu_site": {"posicao": int|None, "url": str|None},
            "concorrentes": {dominio: {"posicao": int|None, "url": str|None}}
        }
    """
    modo = os.getenv("SCRAPING_MODO", "direto")

    # Delay para evitar bloqueio
    if delay is None:
        delay = random.uniform(2.0, 5.0)
    if delay > 0:
        time.sleep(delay)

    resultado = {
        "keyword":      keyword,
        "ok":           False,
        "erro":         None,
        "modo":         modo,
        "resultados":   [],
        "meu_site":     {"posicao": None, "url": None},
        "concorrentes": {d: {"posicao": None, "url": None} for d in dominios_concorrentes}
    }

    try:
        # Buscar HTML conforme modo configurado
        if modo == "scraperapi":
            html = _buscar_scraperapi(keyword, pais)
        elif modo == "brightdata":
            html = _buscar_brightdata(keyword, pais)
        else:
            html = _buscar_direto(keyword, pais)

        # Parsear resultados
        resultados = _parsear_resultados(html)
        resultado["resultados"] = resultados
        resultado["ok"]         = True

        # Encontrar meu site
        for r in resultados:
            if _dominio_match(r["url"], meu_dominio):
                resultado["meu_site"] = {
                    "posicao": r["posicao"],
                    "url":     r["url"]
                }
                break

        # Encontrar cada concorrente
        for dominio in dominios_concorrentes:
            for r in resultados:
                if _dominio_match(r["url"], dominio):
                    resultado["concorrentes"][dominio] = {
                        "posicao": r["posicao"],
                        "url":     r["url"]
                    }
                    break

    except Exception as e:
        resultado["erro"] = str(e)
        print(f"[Scraper] Erro ao rastrear '{keyword}': {e}")

    return resultado


# ─────────────────────────────────────────────
# RASTREAMENTO EM LOTE
# ─────────────────────────────────────────────

def rastrear_projeto(
    keywords:              list,
    meu_dominio:           str,
    dominios_concorrentes: list,
    pais:                  str = "br",
    delay_entre_buscas:    float = None
) -> list:
    """
    Rastreia todas as keywords de um projeto.
    Adiciona delay entre buscas para evitar bloqueio.
    
    Returns: lista de resultados por keyword
    """
    resultados = []
    total      = len(keywords)

    for i, kw in enumerate(keywords):
        print(f"[Scraper] {i+1}/{total} — rastreando: {kw}")

        # Delay maior entre buscas em modo direto
        modo = os.getenv("SCRAPING_MODO", "direto")
        if delay_entre_buscas is None:
            delay = random.uniform(3.0, 7.0) if modo == "direto" else random.uniform(0.5, 1.5)
        else:
            delay = delay_entre_buscas

        resultado = rastrear_posicoes(
            keyword=kw,
            meu_dominio=meu_dominio,
            dominios_concorrentes=dominios_concorrentes,
            pais=pais,
            delay=delay
        )
        resultados.append(resultado)

        # Pausa extra a cada 10 buscas (modo direto)
        if modo == "direto" and (i + 1) % 10 == 0 and i < total - 1:
            pausa = random.uniform(15.0, 30.0)
            print(f"[Scraper] Pausa de {pausa:.0f}s após 10 buscas...")
            time.sleep(pausa)

    return resultados


# ─────────────────────────────────────────────
# TESTE RÁPIDO (rodar direto: python scraper.py)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Teste de Scraping ===")
    resultado = rastrear_posicoes(
        keyword="contabilidade digital",
        meu_dominio="solidycontabilidade.com.br",
        dominios_concorrentes=["agilize.com.br", "contabilizei.com.br"],
        pais="br"
    )
    print(f"OK: {resultado['ok']}")
    print(f"Meu site: {resultado['meu_site']}")
    print(f"Concorrentes: {resultado['concorrentes']}")
    print(f"Total resultados: {len(resultado['resultados'])}")
    if resultado['erro']:
        print(f"Erro: {resultado['erro']}")
