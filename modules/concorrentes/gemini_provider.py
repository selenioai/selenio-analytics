"""
modules/concorrentes/gemini_provider.py

Provider de rastreamento de posições usando Gemini API
com Google Search Grounding.

O Gemini pesquisa no Google real e retorna as posições
de domínios para uma keyword específica.

Custo: Nível gratuito — 15 RPM, 1M tokens/dia (Gemini 2.0 Flash)
"""

import os
import json
import re
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def rastrear_com_gemini(keyword: str, meu_dominio: str, dominios_concorrentes: list, pais: str = "br") -> dict:
    """
    Usa Gemini com Google Search Grounding para rastrear
    posições de domínios para uma keyword.

    Returns:
    {
        "ok": True,
        "keyword": "contabilidade digital",
        "meu_site": {"posicao": 7, "url": "https://..."},
        "concorrentes": {
            "agilize.com.br": {"posicao": 3, "url": "https://..."},
        },
        "fonte": "gemini"
    }
    """
    if not GEMINI_API_KEY:
        return {
            "ok": False,
            "erro": "GEMINI_API_KEY não configurada no .env",
            "keyword": keyword,
            "meu_site": {"posicao": None, "url": None},
            "concorrentes": {d: {"posicao": None, "url": None} for d in dominios_concorrentes}
        }

    todos_dominios = [meu_dominio] + dominios_concorrentes
    dominios_str   = "\n".join([f"- {d}" for d in todos_dominios])

    prompt = f"""Pesquise no Google Brasil a keyword exata: "{keyword}"

Analise os resultados orgânicos (não anúncios) e identifique a posição exata de cada domínio abaixo:

{dominios_str}

Retorne APENAS um JSON válido, sem texto adicional, sem markdown, sem explicações:

{{
  "keyword": "{keyword}",
  "resultados": [
    {{"dominio": "exemplo.com.br", "posicao": 1, "url": "https://exemplo.com.br/pagina"}},
    {{"dominio": "outro.com.br", "posicao": 5, "url": "https://outro.com.br/pagina"}}
  ]
}}

Se um domínio não aparecer no top 50, não o inclua na lista.
Conte apenas resultados orgânicos, ignore anúncios.
"""

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature":     0.1,
            "maxOutputTokens": 500,
        }
    }

    resultado = {
        "ok":           False,
        "keyword":      keyword,
        "fonte":        "gemini",
        "meu_site":     {"posicao": None, "url": None},
        "concorrentes": {d: {"posicao": None, "url": None} for d in dominios_concorrentes},
        "erro":         None
    }

    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
            timeout=30
        )

        if resp.status_code == 429:
            resultado["erro"] = "Rate limit atingido. Aguarde alguns minutos."
            return resultado

        if resp.status_code != 200:
            resultado["erro"] = f"Gemini retornou status {resp.status_code}: {resp.text[:200]}"
            return resultado

        data = resp.json()

        # Extrair texto da resposta
        texto = ""
        for candidate in data.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if "text" in part:
                    texto += part["text"]

        if not texto:
            resultado["erro"] = "Gemini não retornou texto"
            return resultado

        # Limpar e parsear JSON
        texto = texto.strip()
        # Remover blocos markdown se houver
        texto = re.sub(r"```json\s*", "", texto)
        texto = re.sub(r"```\s*", "", texto)
        texto = texto.strip()

        # Encontrar JSON no texto
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if not match:
            resultado["erro"] = f"JSON não encontrado na resposta: {texto[:200]}"
            return resultado

        dados = json.loads(match.group())
        resultados_gemini = dados.get("resultados", [])

        resultado["ok"] = True

        # Processar resultados
        for item in resultados_gemini:
            dominio = item.get("dominio", "").lower().replace("www.", "")
            posicao = item.get("posicao")
            url     = item.get("url")

            # Verificar meu site
            meu_dom_limpo = meu_dominio.lower().replace("www.", "")
            if dominio == meu_dom_limpo or dominio.endswith("." + meu_dom_limpo):
                resultado["meu_site"] = {"posicao": posicao, "url": url}

            # Verificar concorrentes
            for conc_dom in dominios_concorrentes:
                conc_limpo = conc_dom.lower().replace("www.", "")
                if dominio == conc_limpo or dominio.endswith("." + conc_limpo):
                    resultado["concorrentes"][conc_dom] = {"posicao": posicao, "url": url}

        print(f"[Gemini] '{keyword}' — meu_site: {resultado['meu_site']['posicao']}, "
              f"concorrentes: {resultado['concorrentes']}")

    except json.JSONDecodeError as e:
        resultado["erro"] = f"Erro ao parsear JSON: {e} — texto: {texto[:200]}"
    except Exception as e:
        resultado["erro"] = f"Erro: {str(e)}"

    return resultado


def rastrear_projeto_gemini(keywords: list, meu_dominio: str, dominios_concorrentes: list, delay: float = 5.0) -> list:
    """
    Rastreia todas as keywords de um projeto via Gemini.
    Delay entre requisições para respeitar rate limits.
    """
    resultados = []
    total      = len(keywords)

    for i, kw in enumerate(keywords):
        print(f"[Gemini] {i+1}/{total} — rastreando: {kw}")

        resultado = rastrear_com_gemini(
            keyword=kw,
            meu_dominio=meu_dominio,
            dominios_concorrentes=dominios_concorrentes
        )
        resultados.append(resultado)

        # Rate limit: 15 RPM no plano gratuito = 4s entre requisições
        if i < total - 1:
            time.sleep(delay)

    return resultados


# ─────────────────────────────────────────────
# TESTE RÁPIDO
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Teste Gemini Provider ===")
    r = rastrear_com_gemini(
        keyword="contabilidade digital",
        meu_dominio="solidycontabilidade.com.br",
        dominios_concorrentes=["agilize.com.br", "contabilizei.com.br"]
    )
    print(json.dumps(r, indent=2, ensure_ascii=False))
