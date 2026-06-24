from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
import requests, re, json, time, db
from urllib.parse import urlparse, urljoin
from datetime import datetime

bp = Blueprint("seo", __name__)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SelenioBot/2.0; +https://selenio.ai)", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"}

def _fetch(url, timeout=15):
    try: return requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    except: return None

def _score_label(s):
    return "bom" if s>=80 else ("medio" if s>=50 else "ruim")

def _parse_html(html):
    from html.parser import HTMLParser
    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.title=""; self.meta={}; self.links=[]; self.images=[]; self.schema_blocks=[]; self.canonical=""; self._in_title=False; self._in_body=False; self.text_content=[]; self._in_script=False; self._in_style=False; self.scripts=[]; self.styles=[]; self.inline_scripts=[]; self.inline_styles=[]
        def handle_starttag(self, tag, attrs):
            a=dict(attrs); tag=tag.lower()
            if tag=="title": self._in_title=True
            elif tag=="body": self._in_body=True
            elif tag=="script":
                src=a.get("src","")
                if src: self.scripts.append(src)
                elif "application/ld+json" in a.get("type",""): self._in_script="schema"
                else: self._in_script="inline"
            elif tag=="style": self._in_style=True
            elif tag=="link":
                rel=a.get("rel","").lower()
                if rel=="canonical": self.canonical=a.get("href","")
                elif rel=="stylesheet" and a.get("href"): self.styles.append(a["href"])
            elif tag=="meta":
                name=(a.get("name") or a.get("property") or a.get("http-equiv") or "").lower()
                if name: self.meta[name]=a.get("content","")
            elif tag=="a":
                href=a.get("href","")
                if href: self.links.append({"href":href,"rel":a.get("rel","")})
            elif tag=="img": self.images.append({"src":a.get("src",""),"alt":a.get("alt",""),"width":a.get("width",""),"height":a.get("height",""),"loading":a.get("loading","")})
        def handle_endtag(self, tag):
            tag=tag.lower()
            if tag=="title": self._in_title=False
            elif tag=="script": self._in_script=False
            elif tag=="style": self._in_style=False
        def handle_data(self, data):
            if self._in_title: self.title+=data
            elif self._in_script=="schema": self.schema_blocks.append(data.strip())
            elif self._in_script=="inline": self.inline_scripts.append(data[:200])
            elif self._in_style: self.inline_styles.append(data[:200])
            elif not self._in_script and not self._in_style and self._in_body:
                t=data.strip()
                if t: self.text_content.append(t)
    p=P()
    try: p.feed(html)
    except: pass
    return p

def analisar_url(url):
    inicio=time.time()
    r={"url":url,"timestamp":datetime.now().strftime("%d/%m/%Y %H:%M"),"tempo_analise":0,"score_geral":0,"status_http":None,"redirect_chain":[],"meta":{},"headings":{},"conteudo":{},"imagens":{},"links":{},"performance":{},"schema":{},"open_graph":{},"twitter_card":{},"canonical":{},"robots":{},"sitemap":{},"seguranca":{},"mobile":{},"avancado":{},"url_analise":{},"checklist":[],"problemas":[],"avisos":[],"positivos":[],"analise_ia":""}
    resp=_fetch(url)
    if resp is None:
        r["problemas"].append({"item":"Acesso","desc":"Não foi possível acessar a URL.","categoria":"critico"})
        return r
    r["status_http"]=resp.status_code
    if len(resp.history)>0: r["redirect_chain"]=[h.url for h in resp.history]+[resp.url]
    tempo_resposta=resp.elapsed.total_seconds() if resp.elapsed else 0
    html=resp.text
    headers_resp={k.lower():v for k,v in resp.headers.items()}
    parsed_base=urlparse(url); base_domain=parsed_base.netloc; path=parsed_base.path
    p=_parse_html(html)
    headings={}
    for i in range(1,7):
        m=re.findall(rf"<h{i}[^>]*>(.*?)</h{i}>",html,re.I|re.S)
        headings[f"h{i}"]=[re.sub(r"<[^>]+>","",x).strip() for x in m if x.strip()]
    title=p.title.strip(); meta=p.meta; description=meta.get("description",""); viewport=meta.get("viewport","")
    charset_m=re.search(r'<meta[^>]+charset=["\']?([^"\'>\s]+)',html,re.I); charset=charset_m.group(1) if charset_m else ""
    title_len=len(title); desc_len=len(description)
    r["meta"]={"title":title,"title_len":title_len,"title_status":"bom" if 50<=title_len<=60 else("curto" if title_len<50 else "longo"),"description":description,"desc_len":desc_len,"desc_status":"bom" if 120<=desc_len<=160 else("curto" if desc_len<120 else "longo"),"keywords":meta.get("keywords",""),"robots":meta.get("robots",""),"viewport":viewport,"charset":charset,"author":meta.get("author",""),"refresh":meta.get("refresh","")}
    h1c=len(headings.get("h1",[]))
    r["headings"]={**{f"h{i}":headings.get(f"h{i}",[]) for i in range(1,7)},"h1_count":h1c,"h1_status":"bom" if h1c==1 else("ausente" if h1c==0 else "multiplos")}
    texto=" ".join(p.text_content); n_palavras=len(texto.split()); ratio_txt=(len(texto)/max(len(html),1))*100
    r["conteudo"]={"n_palavras":n_palavras,"palavras_status":"bom" if n_palavras>=300 else "curto","ratio_texto_html":round(ratio_txt,1),"tem_faq":bool(re.search(r'faq|perguntas frequentes',html,re.I)),"tem_tabela":bool(re.search(r'<table',html,re.I)),"tem_video":bool(re.search(r'<video|youtube\.com|vimeo\.com',html,re.I))}
    imgs=p.images; sem_alt=[i for i in imgs if not i.get("alt")]; sem_dim=[i for i in imgs if not i.get("width") or not i.get("height")]; com_lazy=[i for i in imgs if i.get("loading")=="lazy"]
    r["imagens"]={"total":len(imgs),"sem_alt":len(sem_alt),"sem_alt_lista":[i["src"] for i in sem_alt[:5]],"sem_dimensoes":len(sem_dim),"com_lazy":len(com_lazy),"status":"bom" if not sem_alt else("aviso" if len(sem_alt)<=3 else "ruim")}
    internos=[]; externos=[]; nofollow=[]
    for lk in p.links:
        href=lk["href"]
        if not href or href.startswith("#") or href.startswith("javascript"): continue
        if href.startswith("http"):
            if base_domain in href: internos.append(href)
            else:
                externos.append(href)
                if "nofollow" in lk.get("rel",""): nofollow.append(href)
        elif not href.startswith("mailto") and not href.startswith("tel"): internos.append(urljoin(url,href))
    r["links"]={"total":len(p.links),"internos":len(internos),"externos":len(externos),"nofollow":len(nofollow)}
    tamanho_html=len(html.encode("utf-8"))/1024; n_scripts=len(p.scripts); n_styles=len(p.styles); n_total_requests=n_scripts+n_styles+len(imgs)
    tem_gzip="gzip" in headers_resp.get("content-encoding","").lower() or "br" in headers_resp.get("content-encoding","").lower()
    tem_expires=bool(headers_resp.get("expires") or headers_resp.get("cache-control"))
    css_min=any(".min.css" in s or "-min.css" in s for s in p.styles); js_min=any(".min.js" in s or "-min.js" in s for s in p.scripts)
    head_html=html[:html.lower().find("</head>")] if "</head>" in html.lower() else html[:3000]
    render_blocking=len(re.findall(r'<script(?![^>]*(async|defer))[^>]*src=',head_html,re.I))
    tem_gtm=bool(re.search(r'GTM-[A-Z0-9]+|googletagmanager\.com',html,re.I)); gtm_id_m=re.search(r'GTM-([A-Z0-9]+)',html,re.I)
    tem_ga=bool(re.search(r'UA-\d+|G-[A-Z0-9]+|gtag\(|google-analytics',html,re.I))
    tem_font_display=bool(re.search(r'font-display\s*:\s*swap',html,re.I))
    tem_lazy=bool(re.search(r'loading=["\']lazy["\']|lazyload|lazy-load',html,re.I))
    r["performance"]={"tempo_resposta":round(tempo_resposta,2),"tempo_status":"bom" if tempo_resposta<1 else("aviso" if tempo_resposta<3 else "ruim"),"tamanho_html_kb":round(tamanho_html,1),"tamanho_status":"bom" if tamanho_html<100 else("aviso" if tamanho_html<500 else "ruim"),"https":url.startswith("https://"),"gzip":tem_gzip,"n_scripts":n_scripts,"n_styles":n_styles,"n_total_requests":n_total_requests,"requests_status":"bom" if n_total_requests<20 else("aviso" if n_total_requests<40 else "ruim"),"render_blocking":render_blocking,"css_minificado":css_min,"js_minificado":js_min,"tem_expires":tem_expires,"tem_gtm":tem_gtm,"gtm_id":gtm_id_m.group(0) if gtm_id_m else "","tem_ga":tem_ga,"tem_font_display":tem_font_display,"tem_lazy":tem_lazy}
    schemas=[]; schema_det={}
    for blk in p.schema_blocks:
        try:
            s=json.loads(blk); t=s.get("@type",""); tipos=[t] if isinstance(t,str) else t; schemas.extend(tipos)
            for tp in tipos: schema_det[tp]=s
        except: pass
    if not schemas: schemas=list(set(re.findall(r'"@type"\s*:\s*"([^"]+)"',html)))
    tem_faq_schema="FAQPage" in schemas; tem_org_schema=any(x in schemas for x in ["Organization","LocalBusiness"]); tem_breadcrumb_schema="BreadcrumbList" in schemas
    r["schema"]={"tipos":schemas,"tem_schema":bool(schemas),"tem_faq":tem_faq_schema,"tem_organization":tem_org_schema,"tem_breadcrumb":tem_breadcrumb_schema,"status":"bom" if schemas else "ruim"}
    og={k:meta.get(f"og:{k}","") for k in ["title","description","image","url","type"]}; og_completo=all([og["title"],og["description"],og["image"]])
    r["open_graph"]={**og,"completo":og_completo,"status":"bom" if og_completo else "ruim"}
    tc={k:meta.get(f"twitter:{k}","") for k in ["card","title","description","image"]}
    r["twitter_card"]={**tc,"tem":bool(tc.get("card")),"status":"bom" if tc.get("card") else "aviso"}
    canonical=p.canonical
    r["canonical"]={"url":canonical,"tem":bool(canonical),"status":"bom" if canonical else "aviso"}
    url_tem_keyword=len(path)>1 and path not in ["/","/lp/","/home/"]; url_limpa=not bool(re.search(r'[?#&=%]',path)) and "-" in path
    r["url_analise"]={"path":path,"tem_keyword":url_tem_keyword,"limpa":url_limpa,"tem_parametros":"?" in url,"status":"bom" if(url_tem_keyword and url_limpa) else "aviso"}
    robots_url=f"{parsed_base.scheme}://{parsed_base.netloc}/robots.txt"; r_robots=_fetch(robots_url)
    tem_robots=r_robots is not None and r_robots.status_code==200; robots_content=r_robots.text[:1000] if tem_robots else ""
    url_bloqueada=bool(re.search(rf'Disallow:\s*{re.escape(path)}',robots_content)) if robots_content else False
    r["robots"]={"tem":tem_robots,"url":robots_url,"conteudo":robots_content,"url_bloqueada":url_bloqueada,"status":"bom" if(tem_robots and not url_bloqueada) else "ruim"}
    sitemap_url=f"{parsed_base.scheme}://{parsed_base.netloc}/sitemap.xml"; r_sitemap=_fetch(sitemap_url)
    tem_sitemap=r_sitemap is not None and r_sitemap.status_code==200
    r["sitemap"]={"tem":tem_sitemap,"url":sitemap_url,"em_robots":"sitemap" in robots_content.lower() if robots_content else False,"status":"bom" if tem_sitemap else "ruim"}
    hsts="strict-transport-security" in headers_resp; csp="content-security-policy" in headers_resp; x_frame="x-frame-options" in headers_resp; x_content="x-content-type-options" in headers_resp
    tem_mixed=bool(re.search(r'src=["\']http://',html)) and url.startswith("https://")
    r["seguranca"]={"https":url.startswith("https://"),"hsts":hsts,"csp":csp,"x_frame_options":x_frame,"x_content_type":x_content,"mixed_content":tem_mixed,"status":"bom" if(url.startswith("https://") and hsts) else("aviso" if url.startswith("https://") else "ruim")}
    viewport_ok="width=device-width" in viewport if viewport else False
    r["mobile"]={"tem_viewport":bool(viewport),"viewport_ok":viewport_ok,"viewport_valor":viewport,"status":"bom" if viewport_ok else "ruim"}
    r["avancado"]={"tem_breadcrumb_html":bool(re.search(r'breadcrumb',html,re.I)),"tem_paginacao":bool(re.search(r'rel=["\']next["\']|rel=["\']prev["\']',html,re.I)),"tem_hreflang":bool(re.search(r'hreflang',html,re.I)),"tem_gtm":tem_gtm,"tem_ga":tem_ga,"tem_font_display":tem_font_display,"render_blocking":render_blocking}
    checks=[]; pontos=0; total=0
    def ck(nome,ok,peso,ok_msg,fail_msg,cat="geral"):
        checks.append({"nome":nome,"ok":ok,"peso":peso,"desc":ok_msg if ok else fail_msg,"categoria":cat})
        return peso if ok else 0
    pontos+=ck("Title tag presente",bool(title),8,f"Title: {title[:50]}","Title tag ausente","meta"); total+=8
    pontos+=ck("Tamanho do title (50-60)",50<=title_len<=60,4,f"{title_len} chars — ideal",f"{title_len} chars — {'curto' if title_len<50 else 'longo'}","meta"); total+=4
    pontos+=ck("Meta description presente",bool(description),7,f"Description: {desc_len} chars","Meta description ausente","meta"); total+=7
    pontos+=ck("Tamanho da description (120-160)",120<=desc_len<=160,3,f"{desc_len} chars — ideal",f"{desc_len} chars — {'curto' if desc_len<120 else 'longo'}","meta"); total+=3
    pontos+=ck("Charset definido",bool(charset),2,f"Charset: {charset}","Charset não declarado","meta"); total+=2
    pontos+=ck("Sem meta refresh",not bool(meta.get("refresh","")),1,"Sem meta refresh","Meta refresh detectado","meta"); total+=1
    pontos+=ck("H1 único",h1c==1,8,f"H1: {headings.get('h1',[''])[0][:50]}",f"{'H1 ausente' if h1c==0 else f'{h1c} H1s (deve ter apenas 1)'}","headings"); total+=8
    pontos+=ck("H2s presentes",len(headings.get("h2",[]))>0,3,f"{len(headings.get('h2',[]))} H2(s)","Sem H2 — estrutura fraca","headings"); total+=3
    pontos+=ck("H3s presentes",len(headings.get("h3",[]))>0,1,f"{len(headings.get('h3',[]))} H3(s)","Sem H3","headings"); total+=1
    pontos+=ck("HTTPS ativo",url.startswith("https://"),10,"Site usa HTTPS — seguro","Site sem HTTPS — crítico","tecnico"); total+=10
    pontos+=ck("Viewport mobile",viewport_ok,7,f"Viewport: {viewport[:40]}","Viewport ausente — não mobile friendly","tecnico"); total+=7
    pontos+=ck("Canonical tag",bool(canonical),5,f"Canonical: {canonical[:50]}","Canonical ausente — risco conteúdo duplicado","tecnico"); total+=5
    pontos+=ck("URL sem parâmetros",not bool("?" in url),2,"URL limpa","URL com parâmetros","tecnico"); total+=2
    pontos+=ck("URL não bloqueada",not url_bloqueada,1,"URL não bloqueada no robots.txt","URL BLOQUEADA no robots.txt!","tecnico"); total+=1
    pontos+=ck("robots.txt presente",tem_robots,5,f"robots.txt em {robots_url}","robots.txt não encontrado","arquivos"); total+=5
    pontos+=ck("sitemap.xml presente",tem_sitemap,5,f"sitemap.xml em {sitemap_url}","sitemap.xml não encontrado","arquivos"); total+=5
    pontos+=ck("Schema markup presente",bool(schemas),6,f"Schemas: {', '.join(schemas[:3])}","Sem schema — perde rich snippets","schema"); total+=6
    pontos+=ck("FAQ Schema",tem_faq_schema,3,"FAQPage schema — rich snippets ativos","Sem FAQ schema — oportunidade perdida","schema"); total+=3
    pontos+=ck("Organization Schema",tem_org_schema,3,"Organization schema — melhora E-E-A-T","Sem Organization schema","schema"); total+=3
    pontos+=ck("Conteúdo mínimo 300 palavras",n_palavras>=300,5,f"{n_palavras} palavras",f"Apenas {n_palavras} palavras","conteudo"); total+=5
    pontos+=ck("Alt text em imagens",not sem_alt,5,"Todas imagens com alt text",f"{len(sem_alt)} imagem(ns) sem alt text","conteudo"); total+=5
    pontos+=ck("Imagens com dimensões",len(sem_dim)==0,3,"Imagens com width/height",f"{len(sem_dim)} imagem(ns) sem dimensões — risco CLS","conteudo"); total+=3
    pontos+=ck("Links internos",len(internos)>0,2,f"{len(internos)} links internos","Sem links internos — silo isolado","conteudo"); total+=2
    pontos+=ck("Open Graph completo",og_completo,5,"og:title, og:description e og:image OK","Open Graph incompleto — preview ruim no WhatsApp","social"); total+=5
    pontos+=ck("Twitter Card",bool(tc.get("card")),2,f"Twitter Card: {tc.get('card')}","Twitter Card ausente","social"); total+=2
    pontos+=ck("HSTS header",hsts,3,"HSTS configurado","HSTS ausente","seguranca"); total+=3
    pontos+=ck("X-Frame-Options",x_frame,2,"X-Frame-Options presente","X-Frame-Options ausente","seguranca"); total+=2
    pontos+=ck("Sem mixed content",not tem_mixed,3,"Sem mixed content","Mixed content HTTP em página HTTPS","seguranca"); total+=3
    pontos+=ck("Velocidade < 2s",tempo_resposta<2,5,f"Resposta em {tempo_resposta}s",f"Resposta em {tempo_resposta}s — lento","performance"); total+=5
    pontos+=ck("Compressão gzip/brotli",tem_gzip,3,"Compressão ativa","Sem compressão — aumenta carregamento","performance"); total+=3
    pontos+=ck("Menos de 40 requests",n_total_requests<40,2,f"{n_total_requests} requests",f"{n_total_requests} requests — reduzir","performance"); total+=2
    pontos+=ck("Lazy loading de imagens",tem_lazy,1,"Lazy loading ativo","Sem lazy loading","performance"); total+=1
    pontos+=ck("GTM ou Google Analytics",tem_gtm or tem_ga,3,f"{'GTM: '+r['performance']['gtm_id'] if tem_gtm else 'GA detectado'}","Sem GTM/GA — rastreamento ausente","analytics"); total+=3
    pontos+=ck("font-display:swap",tem_font_display,2,"font-display:swap ativo","Sem font-display:swap","analytics"); total+=2
    score=round((pontos/total)*100) if total>0 else 0
    r["score_geral"]=score; r["score_label"]=_score_label(score); r["checklist"]=checks; r["tempo_analise"]=round(time.time()-inicio,1)
    for c in checks:
        if not c["ok"]: (r["problemas"] if c["peso"]>=7 else r["avisos"]).append({"item":c["nome"],"desc":c["desc"],"categoria":c["categoria"]})
        else: r["positivos"].append({"item":c["nome"],"desc":c["desc"]})
    return r

def gerar_analise_ia(dados):
    score=dados.get("score_geral",0); problemas=dados.get("problemas",[]); avisos=dados.get("avisos",[]); meta=dados.get("meta",{}); schema=dados.get("schema",{}); perf=dados.get("performance",{})
    prompt=f"""Você é um analista sênior de SEO. Analise os dados abaixo e forneça análise estratégica concisa em português.

URL: {dados.get('url')}
Score: {score}/100 | Problemas: {len(problemas)} | Avisos: {len(avisos)}

DADOS:
- Title: {meta.get('title','(ausente)')} ({meta.get('title_len',0)} chars)
- Description: {meta.get('desc_len',0)} chars {'(ausente)' if not meta.get('description') else '(presente)'}
- H1: {dados.get('headings',{}).get('h1_count',0)} | Palavras: {dados.get('conteudo',{}).get('n_palavras',0)}
- Schema: {', '.join(schema.get('tipos',[])) or 'Nenhum'}
- HTTPS: {'Sim' if dados.get('seguranca',{}).get('https') else 'Não'}
- Tempo: {perf.get('tempo_resposta',0)}s | Gzip: {'Sim' if perf.get('gzip') else 'Não'}
- Open Graph: {'Completo' if dados.get('open_graph',{}).get('completo') else 'Incompleto'}
- robots.txt: {'OK' if dados.get('robots',{}).get('tem') else 'Ausente'} | sitemap.xml: {'OK' if dados.get('sitemap',{}).get('tem') else 'Ausente'}
- GTM: {'Sim' if perf.get('tem_gtm') else 'Não'} | Gzip: {'Sim' if perf.get('gzip') else 'Não'}
- Render blocking: {perf.get('render_blocking',0)} scripts

PROBLEMAS: {', '.join([p['item'] for p in problemas[:5]]) if problemas else 'Nenhum'}
AVISOS: {', '.join([a['item'] for a in avisos[:5]]) if avisos else 'Nenhum'}

Forneça em markdown:
## 🔍 Diagnóstico Geral
(2-3 linhas sobre estado do SEO)

## 🎯 Top 3 Prioridades
1. (ação mais impactante)
2. (segunda ação)
3. (terceira ação)

## ⚡ Quick Win
(1 ação que pode ser feita hoje com alto impacto)

## 📌 Conclusão
(1 linha estratégica)

Máximo 250 palavras. Seja técnico e acionável."""
    try:
        import requests as req
        resp=req.post("https://api.anthropic.com/v1/messages",headers={"Content-Type":"application/json","anthropic-version":"2023-06-01"},json={"model":"claude-sonnet-4-6","max_tokens":600,"messages":[{"role":"user","content":prompt}]},timeout=30)
        data=resp.json()
        if "content" in data and data["content"]: return data["content"][0].get("text","")
    except Exception as e: print(f"[SEO IA] Erro: {e}")
    return ""

@bp.route("/")
@login_required
def index():
    tid=current_user.tenant_id
    projetos=db.query("SELECT id, nome FROM projetos WHERE tenant_id=%s AND D_E_L_E_T=0 ORDER BY nome",(tid,))
    return render_template("seo/index.html",projetos=projetos)

@bp.route("/analisar",methods=["POST"])
@login_required
def analisar():
    url=request.form.get("url","").strip(); projeto_id=request.form.get("projeto_id"); usar_ia=request.form.get("usar_ia","1")=="1"
    if not url: return jsonify({"erro":"URL não informada"}),400
    if not url.startswith("http"): url="https://"+url
    resultado=analisar_url(url)
    if usar_ia: resultado["analise_ia"]=gerar_analise_ia(resultado)
    tid=current_user.tenant_id
    try:
        row=db.execute("INSERT INTO seo_analises (tenant_id,projeto_id,url,score,dados_json,analise_ia,criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",(tid,projeto_id or None,url,resultado["score_geral"],json.dumps(resultado,ensure_ascii=False),resultado.get("analise_ia",""),current_user.id))
        if row: resultado["analise_id"]=row["id"]
    except Exception as e: print(f"[SEO] Erro: {e}")
    return jsonify(resultado)

@bp.route("/historico")
@login_required
def historico():
    tid=current_user.tenant_id; busca=request.args.get("q","").strip(); pagina=int(request.args.get("p",1)); por_pagina=20; offset=(pagina-1)*por_pagina
    where="WHERE s.tenant_id=%s AND s.D_E_L_E_T=0"; params=[tid]
    if busca: where+=" AND (s.url ILIKE %s OR p.nome ILIKE %s)"; params+=[f"%{busca}%",f"%{busca}%"]
    total_row=db.query_one(f"SELECT COUNT(*) as total FROM seo_analises s LEFT JOIN projetos p ON p.id=s.projeto_id {where}",params)
    total=total_row["total"] if total_row else 0
    analises=db.query(f"SELECT s.id,s.url,s.score,s.criado_em,p.nome as projeto_nome FROM seo_analises s LEFT JOIN projetos p ON p.id=s.projeto_id {where} ORDER BY s.criado_em DESC LIMIT %s OFFSET %s",params+[por_pagina,offset])
    return render_template("seo/historico.html",analises=analises,busca=busca,pagina=pagina,total=total,por_pagina=por_pagina,total_paginas=max(1,-(-total//por_pagina)))

@bp.route("/detalhe/<int:id>")
@login_required
def detalhe(id):
    tid=current_user.tenant_id
    analise=db.query_one("SELECT * FROM seo_analises WHERE id=%s AND tenant_id=%s AND D_E_L_E_T=0",(id,tid))
    if not analise:
        from flask import abort; abort(404)
    return jsonify(json.loads(analise["dados_json"]))

@bp.route("/excluir/<int:id>",methods=["POST"])
@login_required
def excluir(id):
    tid=current_user.tenant_id
    db.execute("UPDATE seo_analises SET D_E_L_E_T=1 WHERE id=%s AND tenant_id=%s",(id,tid))
    return jsonify({"ok":True})
