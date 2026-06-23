"""
Módulo SEO — Selenio Analytics
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
import requests, re, json, time, db
from urllib.parse import urlparse
from datetime import datetime

bp = Blueprint("seo", __name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SelenioBot/1.0; +https://selenio.ai)"}

def _fetch(url, timeout=15):
    try:
        return requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    except:
        return None

def _score_label(score):
    if score >= 80: return "bom"
    if score >= 50: return "medio"
    return "ruim"

def analisar_url(url):
    from html.parser import HTMLParser
    inicio = time.time()
    resultado = {
        "url": url, "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "tempo_analise": 0, "score_geral": 0, "status_http": None,
        "redirect_url": None, "meta": {}, "headings": {}, "conteudo": {},
        "imagens": {}, "links": {}, "performance": {}, "schema": {},
        "open_graph": {}, "twitter_card": {}, "canonical": {}, "robots": {},
        "sitemap": {}, "seguranca": {}, "mobile": {},
        "checklist": [], "problemas": [], "avisos": [], "positivos": [],
    }

    resp = _fetch(url)
    if resp is None:
        resultado["problemas"].append({"item": "Acesso", "desc": "Não foi possível acessar a URL."})
        return resultado

    resultado["status_http"] = resp.status_code
    resultado["redirect_url"] = resp.url if resp.url != url else None
    tempo_resposta = resp.elapsed.total_seconds() if resp.elapsed else 0
    html = resp.text

    class SEOParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.title = ""; self.meta = {}; self.links = []; self.images = []
            self.schema_blocks = []; self.canonical = ""; self._in_title = False
            self._in_body = False; self.text_content = []; self._in_script = False
            self._in_style = False

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs); tag = tag.lower()
            if tag == "title": self._in_title = True
            elif tag == "body": self._in_body = True
            elif tag == "script":
                self._in_script = "schema" if "application/ld+json" in attrs.get("type","") else True
            elif tag == "style": self._in_style = True
            elif tag == "meta":
                name = (attrs.get("name") or attrs.get("property") or attrs.get("http-equiv") or "").lower()
                if name: self.meta[name] = attrs.get("content","")
            elif tag == "link":
                if attrs.get("rel","").lower() == "canonical": self.canonical = attrs.get("href","")
            elif tag == "a":
                href = attrs.get("href","")
                if href: self.links.append({"href": href, "rel": attrs.get("rel","")})
            elif tag == "img":
                self.images.append({"src": attrs.get("src",""), "alt": attrs.get("alt","")})

        def handle_endtag(self, tag):
            tag = tag.lower()
            if tag == "title": self._in_title = False
            elif tag == "script": self._in_script = False
            elif tag == "style": self._in_style = False

        def handle_data(self, data):
            if self._in_title: self.title += data
            elif self._in_script == "schema": self.schema_blocks.append(data.strip())
            elif not self._in_script and not self._in_style and self._in_body:
                t = data.strip()
                if t: self.text_content.append(t)

    parser = SEOParser()
    try: parser.feed(html)
    except: pass

    headings = {}
    for i in range(1, 7):
        matches = re.findall(rf"<h{i}[^>]*>(.*?)</h{i}>", html, re.I | re.S)
        headings[f"h{i}"] = [re.sub(r"<[^>]+>","",m).strip() for m in matches if m.strip()]

    title = parser.title.strip(); meta = parser.meta
    description = meta.get("description",""); viewport = meta.get("viewport","")
    charset_m = re.search(r'<meta[^>]+charset=["\']?([^"\'>\s]+)', html, re.I)
    charset = charset_m.group(1) if charset_m else ""
    title_len = len(title); desc_len = len(description)

    resultado["meta"] = {
        "title": title, "title_len": title_len,
        "title_status": "bom" if 50<=title_len<=60 else ("curto" if title_len<50 else "longo"),
        "description": description, "desc_len": desc_len,
        "desc_status": "bom" if 120<=desc_len<=160 else ("curto" if desc_len<120 else "longo"),
        "keywords": meta.get("keywords",""), "robots": meta.get("robots",""),
        "viewport": viewport, "charset": charset,
    }

    resultado["headings"] = {
        **{f"h{i}": headings.get(f"h{i}",[]) for i in range(1,7)},
        "h1_count": len(headings.get("h1",[])),
        "h1_status": "bom" if len(headings.get("h1",[]))==1 else ("ausente" if not headings.get("h1") else "multiplos"),
    }

    texto = " ".join(parser.text_content); n_palavras = len(texto.split())
    resultado["conteudo"] = {"n_palavras": n_palavras, "palavras_status": "bom" if n_palavras>=300 else "curto"}

    imgs = parser.images; sem_alt = [i for i in imgs if not i.get("alt")]
    resultado["imagens"] = {
        "total": len(imgs), "sem_alt": len(sem_alt),
        "sem_alt_lista": [i["src"] for i in sem_alt[:5]],
        "status": "bom" if not sem_alt else ("aviso" if len(sem_alt)<=3 else "ruim"),
    }

    parsed_base = urlparse(url); base_domain = parsed_base.netloc
    internos = []; externos = []
    for lk in parser.links:
        href = lk["href"]
        if not href or href.startswith("#") or href.startswith("javascript"): continue
        if href.startswith("http"):
            (internos if base_domain in href else externos).append(href)
        else: internos.append(href)

    resultado["links"] = {"total": len(parser.links), "internos": len(internos), "externos": len(externos), "nofollow": 0}

    tamanho_html = len(html.encode("utf-8")) / 1024
    resultado["performance"] = {
        "tempo_resposta": round(tempo_resposta, 2),
        "tempo_status": "bom" if tempo_resposta<1 else ("aviso" if tempo_resposta<3 else "ruim"),
        "tamanho_html_kb": round(tamanho_html, 1),
        "tamanho_status": "bom" if tamanho_html<100 else ("aviso" if tamanho_html<500 else "ruim"),
        "https": url.startswith("https://"),
    }

    schemas = []
    for blk in parser.schema_blocks:
        try: t = json.loads(blk).get("@type",""); schemas.append(t if isinstance(t,str) else ", ".join(t))
        except: pass
    if not schemas: schemas = list(set(re.findall(r'"@type"\s*:\s*"([^"]+)"', html)))
    resultado["schema"] = {"tipos": schemas, "tem_schema": bool(schemas), "status": "bom" if schemas else "ruim"}

    og = {k.replace("og:",""):meta.get(f"og:{k}","") for k in ["title","description","image","url","type"]}
    og_completo = all([og["title"], og["description"], og["image"]])
    resultado["open_graph"] = {**og, "completo": og_completo, "status": "bom" if og_completo else "ruim"}

    tc = {k.replace("twitter:",""):meta.get(f"twitter:{k}","") for k in ["card","title","description","image"]}
    resultado["twitter_card"] = {**tc, "tem": bool(tc.get("card")), "status": "bom" if tc.get("card") else "aviso"}
    resultado["canonical"] = {"url": parser.canonical, "tem": bool(parser.canonical), "status": "bom" if parser.canonical else "aviso"}

    robots_url = f"{parsed_base.scheme}://{parsed_base.netloc}/robots.txt"
    r_robots = _fetch(robots_url)
    tem_robots = r_robots is not None and r_robots.status_code == 200
    robots_content = r_robots.text[:500] if tem_robots else ""
    resultado["robots"] = {"tem": tem_robots, "url": robots_url, "conteudo": robots_content, "status": "bom" if tem_robots else "ruim"}

    sitemap_url = f"{parsed_base.scheme}://{parsed_base.netloc}/sitemap.xml"
    r_sitemap = _fetch(sitemap_url)
    tem_sitemap = r_sitemap is not None and r_sitemap.status_code == 200
    resultado["sitemap"] = {"tem": tem_sitemap, "url": sitemap_url, "status": "bom" if tem_sitemap else "ruim"}

    headers_resp = {k.lower() for k in resp.headers}
    resultado["seguranca"] = {
        "https": url.startswith("https://"),
        "hsts": "strict-transport-security" in headers_resp,
        "csp": "content-security-policy" in headers_resp,
        "x_frame_options": "x-frame-options" in headers_resp,
        "status": "bom" if url.startswith("https://") else "ruim",
    }

    viewport_ok = "width=device-width" in viewport if viewport else False
    resultado["mobile"] = {"tem_viewport": bool(viewport), "viewport_ok": viewport_ok, "status": "bom" if viewport_ok else "ruim"}

    checks = []
    pontos = 0; total = 0

    def check(nome, ok, peso, desc_ok, desc_fail):
        checks.append({"nome": nome, "ok": ok, "peso": peso, "desc": desc_ok if ok else desc_fail})
        return peso if ok else 0

    pontos += check("Title tag", bool(title), 8, f"Title presente ({title_len} chars)", "Title tag ausente"); total += 8
    pontos += check("Tamanho do title", 50<=title_len<=60, 4, "Tamanho ideal (50-60 chars)", f"Ajustar: {title_len} chars"); total += 4
    pontos += check("Meta description", bool(description), 7, f"Description presente ({desc_len} chars)", "Meta description ausente"); total += 7
    pontos += check("Tamanho da description", 120<=desc_len<=160, 3, "Tamanho ideal (120-160 chars)", f"Ajustar: {desc_len} chars"); total += 3
    h1c = len(headings.get("h1",[]))
    pontos += check("H1 único", h1c==1, 8, "H1 único encontrado", f"{'H1 ausente' if h1c==0 else f'{h1c} H1s encontrados'}"); total += 8
    pontos += check("HTTPS", url.startswith("https://"), 10, "Site usa HTTPS", "Site não usa HTTPS"); total += 10
    pontos += check("Viewport mobile", viewport_ok, 7, "Viewport configurado", "Viewport ausente"); total += 7
    pontos += check("Canonical tag", bool(parser.canonical), 5, "Canonical presente", "Canonical ausente"); total += 5
    pontos += check("robots.txt", tem_robots, 5, "robots.txt encontrado", "robots.txt não encontrado"); total += 5
    pontos += check("sitemap.xml", tem_sitemap, 5, "sitemap.xml encontrado", "sitemap.xml não encontrado"); total += 5
    pontos += check("Schema markup", bool(schemas), 6, f"Schema: {', '.join(schemas[:2])}", "Sem schema markup"); total += 6
    pontos += check("Open Graph", og_completo, 5, "Open Graph completo", "Open Graph incompleto"); total += 5
    pontos += check("Alt em imagens", not sem_alt, 5, "Todas imagens com alt", f"{len(sem_alt)} sem alt text"); total += 5
    pontos += check("Velocidade", tempo_resposta<2, 7, f"Rápido ({tempo_resposta}s)", f"Lento ({tempo_resposta}s)"); total += 7
    pontos += check("Conteúdo mínimo", n_palavras>=300, 5, f"{n_palavras} palavras", f"Pouco conteúdo ({n_palavras} palavras)"); total += 5
    pontos += check("Subtítulos H2", bool(headings.get("h2")), 3, f"{len(headings.get('h2',[]))} H2(s)", "Sem H2"); total += 3
    pontos += check("Twitter Card", bool(tc.get("card")), 2, "Twitter Card configurado", "Twitter Card ausente"); total += 2

    score = round((pontos/total)*100) if total > 0 else 0
    resultado["score_geral"] = score
    resultado["score_label"] = _score_label(score)
    resultado["checklist"] = checks
    resultado["tempo_analise"] = round(time.time()-inicio, 1)

    for c in checks:
        if not c["ok"]:
            (resultado["problemas"] if c["peso"]>=7 else resultado["avisos"]).append({"item": c["nome"], "desc": c["desc"]})
        else:
            resultado["positivos"].append({"item": c["nome"], "desc": c["desc"]})

    return resultado


@bp.route("/")
@login_required
def index():
    tid = current_user.tenant_id
    projetos = db.query("SELECT id, nome, url FROM projetos WHERE tenant_id=%s AND D_E_L_E_T=0 ORDER BY nome", (tid,))
    return render_template("seo/index.html", projetos=projetos)


@bp.route("/analisar", methods=["POST"])
@login_required
def analisar():
    url = request.form.get("url","").strip()
    projeto_id = request.form.get("projeto_id")
    if not url: return jsonify({"erro": "URL não informada"}), 400
    if not url.startswith("http"): url = "https://" + url
    resultado = analisar_url(url)
    tid = current_user.tenant_id
    try:
        db.execute("""
            INSERT INTO seo_analises (tenant_id, projeto_id, url, score, dados_json, criado_por)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (tid, projeto_id or None, url, resultado["score_geral"], json.dumps(resultado, ensure_ascii=False), current_user.id))
    except Exception as e:
        print(f"[SEO] Erro ao salvar: {e}")
    return jsonify(resultado)


@bp.route("/historico")
@login_required
def historico():
    tid = current_user.tenant_id
    analises = db.query("SELECT id, url, score, criado_em FROM seo_analises WHERE tenant_id=%s AND D_E_L_E_T=0 ORDER BY criado_em DESC LIMIT 50", (tid,))
    return render_template("seo/historico.html", analises=analises)
