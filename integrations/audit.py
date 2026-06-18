import requests, datetime, json, re
import db

HEADERS = {"User-Agent": "SolidySEOBot/1.0"}

def _check_url(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        return r.status_code, r.text, r.url
    except:
        return 0, "", url

def _extract(html, tag):
    m = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', html, re.IGNORECASE|re.DOTALL)
    return m.group(1).strip() if m else None

def auditar_url(url, projeto_id, tenant_id):
    issues = []; score = 100
    pen = {"critical":20,"high":10,"medium":5,"low":2}

    status, html, final_url = _check_url(url)

    if status == 0:
        return {"score":0,"issues":[{"tipo":"critical","msg":"URL inacessivel"}]}
    if status >= 400:
        issues.append({"tipo":"critical","msg":f"HTTP {status}"}); score -= pen["critical"]

    title = _extract(html,"title")
    if not title:
        issues.append({"tipo":"critical","msg":"Title tag ausente"}); score -= pen["critical"]
    elif len(title) < 30:
        issues.append({"tipo":"high","msg":f"Title curto ({len(title)} chars)"}); score -= pen["high"]
    elif len(title) > 65:
        issues.append({"tipo":"medium","msg":f"Title longo ({len(title)} chars)"}); score -= pen["medium"]

    meta_desc = None
    m = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.IGNORECASE)
    if m: meta_desc = m.group(1).strip()
    if not meta_desc:
        issues.append({"tipo":"critical","msg":"Meta description ausente"}); score -= pen["critical"]

    h1 = _extract(html,"h1")
    if not h1:
        issues.append({"tipo":"high","msg":"H1 ausente"}); score -= pen["high"]

    tem_schema = 1 if "application/ld+json" in html else 0
    if not tem_schema:
        issues.append({"tipo":"high","msg":"Schema markup ausente"}); score -= pen["high"]

    tem_og = 1 if 'property="og:title"' in html else 0
    if not tem_og:
        issues.append({"tipo":"medium","msg":"Open Graph ausente"}); score -= pen["medium"]

    canonical = None
    m = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', html, re.IGNORECASE)
    if m: canonical = m.group(1).strip()
    else:
        issues.append({"tipo":"medium","msg":"Tag canonical ausente"}); score -= pen["medium"]

    imgs_sem_alt = len(re.findall(r'<img(?![^>]*\balt=["\'][^"\'][^>]*>)[^>]*>', html, re.IGNORECASE))
    if imgs_sem_alt > 0:
        issues.append({"tipo":"medium","msg":f"{imgs_sem_alt} imagem(ns) sem alt"}); score -= pen["medium"]

    if not final_url.startswith("https://"):
        issues.append({"tipo":"critical","msg":"Sem HTTPS"}); score -= pen["critical"]

    score = max(0, score)
    db.execute("""
        INSERT INTO auditorias
            (tenant_id, projeto_id, url, score, title_tag, meta_desc, h1,
             status_code, tem_schema, tem_og, canonical, issues_json, data_auditoria)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (tenant_id, projeto_id, url, score, title, meta_desc, h1,
          status, tem_schema, tem_og, canonical,
          json.dumps(issues, ensure_ascii=False), datetime.date.today()))

    return {"url":url,"score":score,"issues":issues,
            "tem_schema":bool(tem_schema),"tem_og":bool(tem_og)}

def ultimas_auditorias(tenant_id, projeto_id, limite=20):
    return db.query("""
        SELECT DISTINCT ON (url)
            url, score, issues_json, data_auditoria, tem_schema, tem_og
        FROM auditorias
        WHERE tenant_id=%s AND projeto_id=%s
        ORDER BY url, data_auditoria DESC
        LIMIT %s
    """, (tenant_id, projeto_id, limite))
