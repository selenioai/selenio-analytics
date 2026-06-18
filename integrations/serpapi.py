import os, requests, datetime
import db

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
BASE_URL    = "https://serpapi.com/search"

def _buscar_posicao(keyword, domain, location="Brazil"):
    if not SERPAPI_KEY:
        return None, None
    params = {
        "engine": "google", "q": keyword,
        "location": location, "hl": "pt", "gl": "br",
        "num": 100, "api_key": SERPAPI_KEY,
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        for i, r in enumerate(resp.json().get("organic_results", []), 1):
            link = r.get("link","")
            d = domain.replace("https://","").replace("http://","").replace("www.","")
            if d in link.replace("https://","").replace("http://","").replace("www.",""):
                return i, link
        return None, None
    except Exception as e:
        print(f"[SERPApi] {keyword}: {e}")
        return None, None

def coletar_rankings(tenant_id, projeto_id):
    projeto  = db.query_one("SELECT * FROM projetos WHERE id=%s", (projeto_id,))
    if not projeto:
        return {"status": "erro"}
    keywords = db.query_t(tenant_id,
        "SELECT * FROM keywords WHERE projeto_id=%s AND tenant_id=%s AND ativo=1 AND D_E_L_E_T=0",
        (projeto_id,)
    )
    hoje = datetime.date.today()
    for kw in keywords:
        pos, url = _buscar_posicao(kw["termo"], projeto["dominio"],
                                   projeto.get("serpapi_location","Brazil"))
        db.execute("""
            INSERT INTO rankings (tenant_id, keyword_id, projeto_id, posicao, url_ranqueada, data_coleta)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (tenant_id, kw["id"], projeto_id, pos, url, hoje))
    return {"status": "ok", "keywords_coletadas": len(keywords)}

def ranking_atual(tenant_id, projeto_id):
    return db.query("""
        SELECT DISTINCT ON (k.id)
            k.id, k.termo, r.posicao, r.url_ranqueada, r.data_coleta
        FROM keywords k
        LEFT JOIN rankings r ON r.keyword_id = k.id AND r.tenant_id = %s
        WHERE k.projeto_id=%s AND k.tenant_id=%s AND k.ativo=1 AND k.D_E_L_E_T=0
        ORDER BY k.id, r.data_coleta DESC NULLS LAST
    """, (tenant_id, projeto_id, tenant_id))

def gaps_concorrentes(tenant_id, projeto_id):
    return db.query("""
        SELECT k.termo,
               c.nome  AS concorrente,
               cr.posicao AS pos_concorrente,
               r.posicao  AS nossa_posicao
        FROM concorrente_rankings cr
        JOIN keywords     k ON k.id = cr.keyword_id AND k.tenant_id = %s
        JOIN concorrentes c ON c.id = cr.concorrente_id AND c.tenant_id = %s
        LEFT JOIN (
            SELECT DISTINCT ON (keyword_id) keyword_id, posicao
            FROM rankings
            WHERE projeto_id=%s AND tenant_id=%s
            ORDER BY keyword_id, data_coleta DESC
        ) r ON r.keyword_id = k.id
        WHERE c.projeto_id=%s AND cr.data_coleta = CURRENT_DATE
          AND cr.posicao <= 20
          AND (r.posicao IS NULL OR r.posicao > 20)
        ORDER BY cr.posicao
    """, (tenant_id, tenant_id, projeto_id, tenant_id, projeto_id))
