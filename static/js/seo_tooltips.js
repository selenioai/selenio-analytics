// Dados de explicação para cada check SEO
const SEO_EXPLICACOES = {
  "Title tag presente": {
    o_que: "A tag <title> define o título que aparece na aba do navegador e nos resultados do Google (SERP).",
    problema: "Sem title tag, o Google não sabe qual é o tema principal da página.",
    porque: "O title é o fator on-page mais importante para SEO — influencia diretamente o ranqueamento e o CTR.",
    sugestao: "Crie um title único com a keyword principal no início, entre 50-60 caracteres."
  },
  "Tamanho do title (50-60)": {
    o_que: "O Google exibe entre 50-60 caracteres do title na SERP. Títulos maiores são cortados.",
    problema: "Title longo é cortado na SERP. Title curto desperdiça espaço valioso.",
    porque: "Um title bem dimensionado maximiza o CTR e transmite a proposta de valor completa.",
    sugestao: "Ajuste para 50-60 caracteres com keyword principal + diferencial."
  },
  "Meta description presente": {
    o_que: "A meta description é o resumo exibido abaixo do título nos resultados do Google.",
    problema: "Sem description, o Google escolhe aleatoriamente um trecho do conteúdo — geralmente inadequado.",
    porque: "Embora não influencie ranking diretamente, uma boa description aumenta o CTR em 5-15%.",
    sugestao: "Escreva 120-160 chars com keyword + benefício + CTA. Ex: 'Contabilidade online a partir de R$159/mês. Abra sua empresa grátis. Sem fidelidade.'"
  },
  "Tamanho da description (120-160)": {
    o_que: "O Google exibe entre 120-160 caracteres da meta description na SERP.",
    problema: "Descriptions muito longas são cortadas. Muito curtas desperdiçam espaço persuasivo.",
    porque: "O tamanho ideal garante que a mensagem completa apareça na SERP, maximizando o CTR.",
    sugestao: "Ajuste para 120-160 caracteres incluindo keyword, benefício e chamada para ação."
  },
  "Charset definido": {
    o_que: "O charset define a codificação de caracteres da página (UTF-8 é o padrão internacional).",
    problema: "Sem charset, caracteres especiais (ã, ç, é) podem aparecer incorretamente.",
    porque: "UTF-8 garante que acentos e caracteres do português sejam exibidos corretamente em todos os browsers.",
    sugestao: "Adicione <meta charset='UTF-8'> no início do <head>."
  },
  "Sem meta refresh": {
    o_que: "A meta refresh redireciona automaticamente o usuário para outra página após X segundos.",
    problema: "Redirecionamentos via meta refresh são má prática e podem prejudicar a indexação.",
    porque: "O Google prefere redirecionamentos 301 no servidor. Meta refresh pode ser interpretado como cloaking.",
    sugestao: "Use redirecionamento 301 no servidor (.htaccess ou nginx) em vez de meta refresh."
  },
  "H1 único": {
    o_que: "O H1 é o título principal da página — deve haver exatamente um por página.",
    problema: "Múltiplos H1 confundem o Google sobre o tema principal. H1 ausente elimina sinal importante de relevância.",
    porque: "O H1 é o segundo fator on-page mais importante após o title. Sinaliza ao Google o tema central da página.",
    sugestao: "Crie um único H1 com a keyword principal. Ex: 'Contabilidade Digital para PJ e Autônomos em São Paulo'"
  },
  "H2s presentes": {
    o_que: "Os H2s são subtítulos que organizam o conteúdo em seções temáticas.",
    problema: "Sem H2s, o conteúdo parece um bloco único sem estrutura — dificulta leitura e indexação.",
    porque: "H2s com keywords secundárias aumentam a relevância temática e ajudam o Google a entender o conteúdo.",
    sugestao: "Use H2s para cada seção principal com variações da keyword. Ex: 'Planos de Contabilidade Online para MEI'"
  },
  "H3s presentes": {
    o_que: "H3s são subtítulos de segundo nível que organizam subseções dentro de cada H2.",
    problema: "Ausência de H3s indica conteúdo pouco estruturado.",
    porque: "Hierarquia completa de headings melhora experiência do usuário e entendimento semântico do Google.",
    sugestao: "Use H3s para subseções dentro de cada H2, especialmente em FAQs e listas de características."
  },
  "HTTPS ativo": {
    o_que: "HTTPS criptografa a conexão entre o servidor e o usuário via certificado SSL/TLS.",
    problema: "Sites sem HTTPS são marcados como 'Não seguro' pelo Chrome — afasta visitantes.",
    porque: "Google usa HTTPS como fator de ranking desde 2014. Obrigatório para LGPD e proteção de dados.",
    sugestao: "Instale certificado SSL gratuito via Let's Encrypt e force HTTPS via redirect 301."
  },
  "Viewport mobile": {
    o_que: "A meta viewport controla como a página é exibida em dispositivos móveis.",
    problema: "Sem viewport, o site aparece em tamanho desktop no celular — impossível de usar.",
    porque: "Mais de 60% das buscas são em mobile. Google usa Mobile-First Indexing.",
    sugestao: "Adicione <meta name='viewport' content='width=device-width, initial-scale=1'> no <head>."
  },
  "Canonical tag": {
    o_que: "A canonical tag indica ao Google qual é a versão oficial de uma página quando há duplicatas.",
    problema: "Sem canonical, o Google pode indexar múltiplas versões da mesma página, diluindo autoridade.",
    porque: "Conteúdo duplicado pode resultar em penalidade. A canonical concentra os sinais de SEO.",
    sugestao: "Adicione <link rel='canonical' href='URL-oficial'> apontando para a versão principal."
  },
  "URL sem parâmetros": {
    o_que: "URLs com parâmetros (?utm=, &page=2) podem ser interpretadas como páginas diferentes pelo Google.",
    problema: "Parâmetros na URL podem gerar conteúdo duplicado e confundir o Googlebot.",
    porque: "URLs limpas e semânticas são mais fáceis de indexar, compartilhar e ranquear.",
    sugestao: "Use URLs limpas e descritivas. Configure o Google Search Console para ignorar parâmetros."
  },
  "URL não bloqueada": {
    o_que: "O arquivo robots.txt pode bloquear o acesso do Google a páginas com a diretiva Disallow.",
    problema: "Se a URL está bloqueada no robots.txt, o Google não pode indexá-la.",
    porque: "Páginas bloqueadas no robots.txt não aparecem no Google, independentemente do conteúdo.",
    sugestao: "Remova a regra Disallow do robots.txt para esta URL ou verifique se o bloqueio é intencional."
  },
  "robots.txt presente": {
    o_que: "O robots.txt instrui os robôs de busca sobre quais páginas podem ser rastreadas.",
    problema: "Sem robots.txt, o Google rastreia tudo — incluindo páginas de admin e conteúdo privado.",
    porque: "Um robots.txt bem configurado otimiza o crawl budget e protege áreas sensíveis do site.",
    sugestao: "Crie /robots.txt com User-agent: * e Disallow para áreas privadas. Inclua link do sitemap."
  },
  "sitemap.xml presente": {
    o_que: "O sitemap.xml lista todas as URLs do site para facilitar o rastreamento pelo Google.",
    problema: "Sem sitemap, o Google pode demorar para descobrir novas páginas ou não indexá-las.",
    porque: "O sitemap acelera a indexação de páginas novas e garante que o Google conheça toda a estrutura.",
    sugestao: "Gere um sitemap.xml e envie no Google Search Console. Em WordPress use Yoast SEO ou RankMath."
  },
  "Schema markup presente": {
    o_que: "Schema markup é código JSON-LD que adiciona contexto semântico às páginas para os buscadores.",
    problema: "Sem schema, o Google não exibe rich snippets (estrelas, FAQ, preço) nos resultados.",
    porque: "Rich snippets aumentam o CTR em 20-30% e melhoram visibilidade nos SERPs.",
    sugestao: "Implemente Schema do tipo Organization, LocalBusiness e FAQPage usando JSON-LD no <head>."
  },
  "FAQ Schema": {
    o_que: "FAQPage schema marca perguntas e respostas para que o Google as exiba como rich snippets.",
    problema: "Sem FAQ schema, as perguntas do site não aparecem como rich snippets nos resultados.",
    porque: "FAQ rich snippets ocupam mais espaço na SERP e aumentam visibilidade sem mudar posição.",
    sugestao: "Adicione JSON-LD com @type FAQPage para cada pergunta e resposta existente na página."
  },
  "Organization Schema": {
    o_que: "Organization/LocalBusiness schema fornece informações estruturadas sobre a empresa para o Google.",
    problema: "Sem schema de organização, o Google tem menos dados para Knowledge Panel e resultados locais.",
    porque: "Melhora o E-E-A-T — fator crucial de ranking do Google desde 2022.",
    sugestao: "Implemente Organization schema com nome, endereço, telefone, CNPJ, horários e URL do logo."
  },
  "Conteúdo mínimo 300 palavras": {
    o_que: "O volume de conteúdo é sinal de profundidade e relevância temática para o Google.",
    problema: "Menos de 300 palavras é considerado thin content — conteúdo raso que não rankeia bem.",
    porque: "O Google prefere conteúdo aprofundado que responda completamente à intenção de busca.",
    sugestao: "Adicione conteúdo relevante: descrição de serviços, FAQs, diferenciais — mínimo 600 palavras."
  },
  "Alt text em imagens": {
    o_que: "O atributo alt descreve o conteúdo das imagens para o Google e usuários com deficiência visual.",
    problema: "Imagens sem alt são ignoradas pelo Google — perda de ranking em Google Images.",
    porque: "Alt text é fundamental para acessibilidade (WCAG) e Google Images — fonte adicional de tráfego.",
    sugestao: "Adicione alt descritivo em todas imagens. Ex: alt='Logo Solidy Contabilidade Digital São Paulo'"
  },
  "Imagens com dimensões": {
    o_que: "Os atributos width e height nas imagens reservam espaço no layout antes do carregamento.",
    problema: "Sem dimensões, as imagens causam CLS (layout shift) — o conteúdo 'pula' ao carregar.",
    porque: "CLS é um Core Web Vital do Google. Alto CLS prejudica experiência e ranking.",
    sugestao: "Adicione width e height em todas as tags <img>. Ex: <img width='200' height='80' ...>"
  },
  "Links internos": {
    o_que: "Links internos conectam páginas do mesmo site, distribuindo autoridade e guiando o usuário.",
    problema: "Sem links internos, a página fica isolada — o Google não descobre outras páginas.",
    porque: "Links internos são essenciais para crawlability, distribuição de PageRank e tempo no site.",
    sugestao: "Adicione 3-5 links para outras páginas: blog, serviços, contato, cases de sucesso."
  },
  "Open Graph completo": {
    o_que: "Open Graph controla como a página aparece quando compartilhada no Facebook e WhatsApp.",
    problema: "Sem OG tags, o WhatsApp escolhe aleatoriamente título e imagem — resultado feio.",
    porque: "Compartilhamentos com preview profissional geram mais cliques. Crítico para tráfego social.",
    sugestao: "Adicione og:title, og:description, og:image (1200x630px) e og:url no <head>."
  },
  "Twitter Card": {
    o_que: "Twitter Cards controlam a aparência dos links quando compartilhados no X (Twitter).",
    problema: "Sem Twitter Card, links no X aparecem como texto simples sem preview visual.",
    porque: "Cards visuais têm CTR significativamente maior que links de texto no X.",
    sugestao: "Adicione twitter:card='summary_large_image', twitter:title, twitter:description e twitter:image."
  },
  "HSTS header": {
    o_que: "HSTS força o browser a sempre usar HTTPS, mesmo se o usuário digitar HTTP.",
    problema: "Sem HSTS, usuários podem ser redirecionados via HTTP antes do HTTPS — vulnerabilidade.",
    porque: "HSTS protege contra ataques man-in-the-middle e é sinal de segurança para o Google.",
    sugestao: "Configure: Strict-Transport-Security: max-age=31536000; includeSubDomains no servidor."
  },
  "X-Frame-Options": {
    o_que: "X-Frame-Options impede que a página seja carregada dentro de um iframe em outros sites.",
    problema: "Sem este header, o site fica vulnerável a ataques de clickjacking.",
    porque: "Clickjacking pode roubar dados de usuários. Google valoriza sites seguros.",
    sugestao: "Configure: X-Frame-Options: SAMEORIGIN no nginx ou apache."
  },
  "Sem mixed content": {
    o_que: "Mixed content ocorre quando uma página HTTPS carrega recursos via HTTP.",
    problema: "Browsers bloqueiam recursos HTTP em páginas HTTPS — imagens podem não aparecer.",
    porque: "Mixed content quebra a segurança do HTTPS e o Chrome exibe aviso 'Não seguro'.",
    sugestao: "Atualize todas as URLs de recursos para HTTPS. Use //exemplo.com/img.jpg (protocol-relative)."
  },
  "Velocidade < 2s": {
    o_que: "O tempo de resposta do servidor é o tempo até o primeiro byte chegar ao browser (TTFB).",
    problema: "Servidor lento aumenta o LCP — Core Web Vital negativo para SEO.",
    porque: "53% dos usuários abandonam sites que demoram mais de 3s. Google penaliza sites lentos.",
    sugestao: "Use cache de servidor, CDN (Cloudflare), otimize queries de banco e reduza plugins."
  },
  "Compressão gzip/brotli": {
    o_que: "Compressão reduz o tamanho dos arquivos transferidos entre servidor e browser.",
    problema: "Sem compressão, HTML/CSS/JS são transferidos no tamanho original — carregamento lento.",
    porque: "Gzip reduz o tamanho em 60-80%. Impacto direto no LCP e tempo de carregamento.",
    sugestao: "Ative gzip no nginx: gzip on; gzip_types text/html text/css application/javascript;"
  },
  "Menos de 40 requests": {
    o_que: "Cada arquivo (JS, CSS, imagem, fonte) gera uma requisição HTTP separada ao servidor.",
    problema: "Muitas requisições aumentam o tempo de carregamento, especialmente em mobile.",
    porque: "Cada request adiciona latência. Mais de 40 requests indica código inchado.",
    sugestao: "Combine CSS/JS, use sprites de imagem, elimine plugins desnecessários e use HTTP/2."
  },
  "Lazy loading de imagens": {
    o_que: "Lazy loading carrega imagens apenas quando entram na área visível do usuário.",
    problema: "Sem lazy loading, todas as imagens carregam imediatamente — mesmo as invisíveis.",
    porque: "Lazy loading reduz o peso inicial e melhora o LCP — Core Web Vital de ranking.",
    sugestao: "Adicione loading='lazy' em imagens abaixo do fold. Ex: <img src='foto.jpg' loading='lazy'>"
  },
  "GTM ou Google Analytics": {
    o_que: "GTM e GA4 são ferramentas de rastreamento de comportamento e conversões.",
    problema: "Sem rastreamento, você não sabe quantas pessoas visitam, de onde vêm ou o que fazem.",
    porque: "Dados de comportamento são essenciais para otimizar SEO, CRO e campanhas. Não se melhora o que não se mede.",
    sugestao: "Instale GTM e configure GA4 com eventos de conversão (cliques em WhatsApp, formulários)."
  },
  "font-display:swap": {
    o_que: "font-display:swap mostra texto com fonte fallback enquanto a fonte customizada carrega.",
    problema: "Sem swap, o browser pode esconder o texto até a fonte carregar — FOIT.",
    porque: "Texto invisível durante carregamento prejudica o LCP e experiência em conexões lentas.",
    sugestao: "Adicione font-display: swap no CSS das @font-face ou nas URLs do Google Fonts (&display=swap)."
  }
};

// Cria tooltip elemento
function criarTooltip() {
  const el = document.createElement('div');
  el.id = 'seo-tooltip';
  el.innerHTML = `
    <div class="tt-header">
      <span class="tt-icon" id="tt-icon"></span>
      <strong id="tt-nome"></strong>
    </div>
    <div class="tt-body">
      <div class="tt-row"><span class="tt-lbl">📌 O que é</span><p id="tt-oque"></p></div>
      <div class="tt-row"><span class="tt-lbl">⚠️ Problema</span><p id="tt-prob"></p></div>
      <div class="tt-row"><span class="tt-lbl">🎯 Por que melhorar</span><p id="tt-porque"></p></div>
      <div class="tt-row tt-sug"><span class="tt-lbl">💡 Sugestão</span><p id="tt-sug"></p></div>
    </div>`;
  document.body.appendChild(el);
  return el;
}

let ttEl = null;
let ttTimer = null;

function mostrarTooltip(e, nome, ok) {
  const info = SEO_EXPLICACOES[nome];
  if (!info) return;
  if (!ttEl) ttEl = criarTooltip();
  clearTimeout(ttTimer);
  document.getElementById('tt-icon').textContent = ok ? '✅' : '❌';
  document.getElementById('tt-nome').textContent = nome;
  document.getElementById('tt-oque').textContent = info.o_que;
  document.getElementById('tt-prob').textContent = info.problema;
  document.getElementById('tt-porque').textContent = info.porque;
  document.getElementById('tt-sug').textContent = info.sugestao;
  ttEl.style.display = 'block';
  posicionarTooltip(e);
}

function posicionarTooltip(e) {
  if (!ttEl) return;
  const x = e.clientX + 16;
  const y = e.clientY + 8;
  const maxX = window.innerWidth - ttEl.offsetWidth - 20;
  const maxY = window.innerHeight - ttEl.offsetHeight - 20;
  ttEl.style.left = Math.min(x, maxX) + 'px';
  ttEl.style.top = Math.min(y, maxY) + 'px';
}

function esconderTooltip() {
  ttTimer = setTimeout(() => {
    if (ttEl) ttEl.style.display = 'none';
  }, 150);
}

// Painel expansível com dados encontrados
function togglePainel(id, nome, dados) {
  const existing = document.getElementById('painel-' + id);
  if (existing) { existing.remove(); return; }
  const info = montarPainel(nome, dados);
  if (!info) return;
  const div = document.createElement('div');
  div.id = 'painel-' + id;
  div.className = 'check-painel';
  div.innerHTML = info;
  const item = document.getElementById('check-item-' + id);
  if (item) item.after(div);
}

function montarPainel(nome, dados) {
  const m = dados.meta || {}; const h = dados.headings || {}; const img = dados.imagens || {};
  const lk = dados.links || {}; const perf = dados.performance || {}; const seg = dados.seguranca || {};
  const sch = dados.schema || {}; const og = dados.open_graph || {}; const tc = dados.twitter_card || {};
  const rob = dados.robots || {}; const sit = dados.sitemap || {}; const can = dados.canonical || {};

  const paineis = {
    "Title tag presente": `<strong>Title encontrado:</strong><br><code>${esc(m.title||'(nenhum)')}</code><br><small>Comprimento: ${m.title_len||0} caracteres</small>`,
    "Tamanho do title (50-60)": `<strong>Title atual:</strong> "${esc(m.title||'')}"<br><div class="barra-wrap"><div class="barra-fill" style="width:${Math.min(100,((m.title_len||0)/70)*100)}%;background:${m.title_len>=50&&m.title_len<=60?'#10b981':'#f59e0b'}"></div></div><small>${m.title_len||0} chars — ideal: 50-60</small>`,
    "Meta description presente": `<strong>Description encontrada:</strong><br><code>${esc(m.description||'(nenhuma)')}</code><br><small>Comprimento: ${m.desc_len||0} caracteres</small>`,
    "Tamanho da description (120-160)": `<strong>Description atual:</strong><br>"${esc(m.description||'')}"<br><div class="barra-wrap"><div class="barra-fill" style="width:${Math.min(100,((m.desc_len||0)/180)*100)}%;background:${m.desc_len>=120&&m.desc_len<=160?'#10b981':'#f59e0b'}"></div></div><small>${m.desc_len||0} chars — ideal: 120-160</small>`,
    "Charset definido": `<strong>Charset detectado:</strong> <code>${esc(m.charset||'(não encontrado)')}</code>`,
    "Sem meta refresh": `<strong>Meta refresh:</strong> ${m.refresh ? `<code>${esc(m.refresh)}</code>` : '(não encontrado — OK)'}`,
    "H1 único": `<strong>${(h.h1||[]).length} H1(s) encontrado(s):</strong><br>${(h.h1||[]).map(t=>`<code>${esc(t)}</code>`).join('<br>') || '<em>(nenhum)</em>'}`,
    "H2s presentes": `<strong>${(h.h2||[]).length} H2(s) encontrado(s):</strong><br>${(h.h2||[]).slice(0,8).map(t=>`<code>${esc(t)}</code>`).join('<br>') || '<em>(nenhum)</em>'}`,
    "H3s presentes": `<strong>${(h.h3||[]).length} H3(s) encontrado(s):</strong><br>${(h.h3||[]).slice(0,6).map(t=>`<code>${esc(t)}</code>`).join('<br>') || '<em>(nenhum)</em>'}`,
    "HTTPS ativo": `<strong>Protocolo:</strong> ${seg.https?'<span style="color:#10b981">✅ HTTPS ativo</span>':'<span style="color:#ef4444">❌ HTTP (inseguro)</span>'}`,
    "Viewport mobile": `<strong>Viewport encontrado:</strong><br><code>${esc(m.viewport||'(ausente)')}</code>`,
    "Canonical tag": `<strong>Canonical URL:</strong><br><code>${esc(can.url||'(ausente)')}</code>`,
    "URL sem parâmetros": `<strong>URL analisada:</strong><br><code>${esc(dados.url)}</code><br>${dados.url_analise?.tem_parametros?'<span style="color:#f59e0b">⚠️ Parâmetros detectados</span>':'<span style="color:#10b981">✅ URL limpa</span>'}`,
    "URL não bloqueada": `<strong>robots.txt:</strong><br><code>${esc(rob.conteudo?.split('\n').slice(0,6).join('\n')||'(não encontrado)')}</code>`,
    "robots.txt presente": `<strong>URL:</strong> <code>${esc(rob.url||'')}</code><br><strong>Conteúdo (primeiras linhas):</strong><br><pre style="font-size:.75rem;background:var(--bg);padding:8px;border-radius:6px;overflow:auto;max-height:120px">${esc(rob.conteudo||'(não encontrado)')}</pre>`,
    "sitemap.xml presente": `<strong>URL:</strong> <code>${esc(sit.url||'')}</code><br><strong>Status:</strong> ${sit.tem?'<span style="color:#10b981">✅ Encontrado</span>':'<span style="color:#ef4444">❌ Não encontrado</span>'}<br>${sit.em_robots?'<span style="color:#10b981">✅ Declarado no robots.txt</span>':'<span style="color:#f59e0b">⚠️ Não declarado no robots.txt</span>'}`,
    "Schema markup presente": `<strong>Schemas encontrados:</strong><br>${(sch.tipos||[]).map(t=>`<span class="tag-schema">${esc(t)}</span>`).join(' ') || '<em>(nenhum)</em>'}<br><br>${sch.tem_faq?'✅ FAQPage':'⚠️ FAQPage ausente'} &nbsp; ${sch.tem_organization?'✅ Organization':'⚠️ Organization ausente'} &nbsp; ${sch.tem_breadcrumb?'✅ Breadcrumb':'⚠️ Breadcrumb ausente'}`,
    "FAQ Schema": `<strong>FAQPage Schema:</strong> ${sch.tem_faq?'<span style="color:#10b981">✅ Presente</span>':'<span style="color:#ef4444">❌ Ausente</span>'}<br><small>Rich snippets de FAQ aparecem nos resultados do Google quando este schema está presente e aprovado.</small>`,
    "Organization Schema": `<strong>Organization/LocalBusiness Schema:</strong> ${sch.tem_organization?'<span style="color:#10b981">✅ Presente</span>':'<span style="color:#ef4444">❌ Ausente</span>'}<br><small>Forneça nome, endereço, telefone, CNPJ e logo na implementação.</small>`,
    "Conteúdo mínimo 300 palavras": `<strong>Palavras encontradas:</strong> ${dados.conteudo?.n_palavras||0}<br><div class="barra-wrap"><div class="barra-fill" style="width:${Math.min(100,((dados.conteudo?.n_palavras||0)/800)*100)}%;background:${(dados.conteudo?.n_palavras||0)>=300?'#10b981':'#ef4444'}"></div></div><small>Mínimo recomendado: 300 palavras | Ideal para SEO: 600+</small>`,
    "Alt text em imagens": `<strong>${img.sem_alt||0} de ${img.total||0} imagens sem alt text:</strong><br>${(img.sem_alt_lista||[]).map(s=>`<code style="display:block;margin:2px 0;font-size:.72rem">${esc(s)}</code>`).join('') || '(todas têm alt text ✅)'}`,
    "Imagens com dimensões": `<strong>Imagens sem width/height:</strong> ${img.sem_dimensoes||0} de ${img.total||0}<br><small>Imagens sem dimensões podem causar CLS (layout shift) — Core Web Vital.</small>`,
    "Links internos": `<strong>Links encontrados:</strong><br>🔗 Internos: ${lk.internos||0} &nbsp; 🌐 Externos: ${lk.externos||0} &nbsp; 🚫 Nofollow: ${lk.nofollow||0}`,
    "Open Graph completo": `<strong>Tags Open Graph encontradas:</strong><br><code>og:title:</code> ${esc(og.title||'(ausente)')}<br><code>og:description:</code> ${esc(og.description||'(ausente)')}<br><code>og:image:</code> ${esc(og.image||'(ausente)')}<br><code>og:type:</code> ${esc(og.type||'(ausente)')}`,
    "Twitter Card": `<strong>Twitter Card encontrado:</strong><br><code>twitter:card:</code> ${esc(tc.card||'(ausente)')}<br><code>twitter:title:</code> ${esc(tc.title||'(ausente)')}<br><code>twitter:image:</code> ${esc(tc.image||'(ausente)')}`,
    "HSTS header": `<strong>Header Strict-Transport-Security:</strong> ${seg.hsts?'<span style="color:#10b981">✅ Presente</span>':'<span style="color:#ef4444">❌ Ausente</span>'}`,
    "X-Frame-Options": `<strong>Header X-Frame-Options:</strong> ${seg.x_frame_options?'<span style="color:#10b981">✅ Presente</span>':'<span style="color:#ef4444">❌ Ausente</span>'}`,
    "Sem mixed content": `<strong>Mixed content (HTTP em página HTTPS):</strong> ${seg.mixed_content?'<span style="color:#ef4444">❌ Detectado</span>':'<span style="color:#10b981">✅ Não detectado</span>'}`,
    "Velocidade < 2s": `<strong>Tempo de resposta:</strong> ${perf.tempo_resposta}s<br><div class="barra-wrap"><div class="barra-fill" style="width:${Math.min(100,(perf.tempo_resposta/5)*100)}%;background:${perf.tempo_resposta<1?'#10b981':perf.tempo_resposta<3?'#f59e0b':'#ef4444'}"></div></div><small>Ideal: < 1s | Aceitável: 1-3s | Crítico: > 3s</small>`,
    "Compressão gzip/brotli": `<strong>Compressão:</strong> ${perf.gzip?'<span style="color:#10b981">✅ gzip/brotli ativo</span>':'<span style="color:#ef4444">❌ Sem compressão</span>'}<br><small>Tamanho HTML: ${perf.tamanho_html_kb} KB</small>`,
    "Menos de 40 requests": `<strong>Total de requests:</strong> ${perf.n_total_requests}<br>📜 JavaScript: ${perf.n_scripts} arquivos<br>🎨 CSS: ${perf.n_styles} arquivos<br>🖼️ Imagens: ${perf.n_total_requests - perf.n_scripts - perf.n_styles}<br><div class="barra-wrap"><div class="barra-fill" style="width:${Math.min(100,(perf.n_total_requests/80)*100)}%;background:${perf.n_total_requests<20?'#10b981':perf.n_total_requests<40?'#f59e0b':'#ef4444'}"></div></div>`,
    "Lazy loading de imagens": `<strong>Lazy loading:</strong> ${perf.tem_lazy?'<span style="color:#10b981">✅ Detectado</span>':'<span style="color:#ef4444">❌ Não detectado</span>'}<br><small>Imagens com lazy: ${img.com_lazy||0} de ${img.total||0}</small>`,
    "GTM ou Google Analytics": `<strong>Google Tag Manager:</strong> ${perf.tem_gtm?`<span style="color:#10b981">✅ ${esc(perf.gtm_id)}</span>`:'❌ Não encontrado'}<br><strong>Google Analytics:</strong> ${perf.tem_ga?'<span style="color:#10b981">✅ Detectado</span>':'❌ Não encontrado'}`,
    "font-display:swap": `<strong>font-display:swap:</strong> ${perf.tem_font_display?'<span style="color:#10b981">✅ Detectado</span>':'<span style="color:#ef4444">❌ Não detectado</span>'}<br><small>Evita FOIT (Flash of Invisible Text) durante carregamento de fontes.</small>`
  };
  return paineis[nome] || null;
}

function esc(t) {
  if (!t) return '';
  return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
