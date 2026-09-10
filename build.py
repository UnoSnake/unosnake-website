# -*- coding: utf-8 -*-
"""
UnoSnake — Static site generator.
Produit toutes les pages HTML avec header/footer/SEO partagés.
Aucun secret. Liens Amazon au format affilié officiel uniquement.
Exécuter : python build.py  (écrit les .html à la racine du site)
"""
import os, json, html as _html, hashlib, struct

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_URL = "https://unosnake-website.unosnakeshop.workers.dev"
PARTNER_TAG = "unosnake09-21"
MOBILE_BP = 860  # doit rester aligné avec le breakpoint de assets/style.css

# ----------------------------------------------------------------
# Données (statiques, honnêtes — aucun faux avis/chiffre)
# ----------------------------------------------------------------
def affiliate(asin):
    return f"https://www.amazon.fr/dp/{asin}/ref=nosim?tag={PARTNER_TAG}"

# Produit réel validé au pilote Phase 13 + placeholders éditoriaux honnêtes
# (pas de faux prix : price=None → non affiché ; sans ASIN → carte non cliquable "Sélection à venir")
PRODUCTS = [
    {"asin":"B09FQ9RL1X","name":"Étagère flottante en bois massif","cat":"Rangement","style":"Warm Minimalism","img":"prod-etagere","price":None,"real":True},
    {"asin":None,"name":"Lampe de table bois et lin","cat":"Éclairage","style":"Scandinave","img":"prod-lampe","price":None,"real":False},
    {"asin":None,"name":"Vase en céramique mate","cat":"Objets déco","style":"Japandi","img":"prod-vase","price":None,"real":False},
    {"asin":None,"name":"Panier en rotin tressé","cat":"Rangement","style":"Bohème","img":"prod-panier","price":None,"real":False},
    {"asin":None,"name":"Miroir rond en bois clair","cat":"Décoration","style":"Scandinave","img":"prod-miroir","price":None,"real":False},
    {"asin":None,"name":"Coussin en lin lavé","cat":"Textiles","style":"Warm Minimalism","img":"prod-coussin","price":None,"real":False},
]

STYLES = [
    {"slug":"scandinave","name":"Scandinave","img":"style-scandinave",
     "line":"Des lignes simples, du bois clair et une chaleur naturelle.",
     "desc":"Le style scandinave cherche la lumière et la simplicité : des matières claires, des formes douces et une fonctionnalité tranquille qui rend chaque pièce accueillante."},
    {"slug":"japandi","name":"Japandi","img":"style-japandi",
     "line":"Le calme, l'équilibre et la beauté de l'essentiel.",
     "desc":"Le japandi réunit la sobriété japonaise et la chaleur nordique : des palettes apaisées, des matériaux naturels et une recherche d'équilibre dans chaque détail."},
    {"slug":"warm-minimalism","name":"Warm Minimalism","img":"style-warm",
     "line":"Moins, mais mieux — dans un intérieur qui reste vivant.",
     "desc":"Le minimalisme chaleureux garde l'essentiel sans jamais devenir froid : des tons neutres, des textures naturelles et des objets choisis pour durer."},
    {"slug":"boheme","name":"Bohème","img":"style-boheme",
     "line":"Textures, matières et caractère, sans perdre l'équilibre.",
     "desc":"Le bohème assume la matière et le fait-main : fibres naturelles, tissages et pièces au caractère affirmé, réunis avec justesse pour éviter la surcharge."},
]

CATEGORIES = [
    {"name":"Mobilier","icon":"chair"},
    {"name":"Éclairage","icon":"lamp"},
    {"name":"Rangement","icon":"box"},
    {"name":"Décoration","icon":"vase"},
]

ARTICLES = [
    {"slug":"interieur-japandi-chaleureux","title":"7 façons de créer un intérieur Japandi chaleureux","tag":"Japandi","img":"art-japandi","hero_img":"art-hero-japandi",
     "excerpt":"Le japandi n'est pas qu'une affaire de palette neutre. Voici comment garder la chaleur tout en cultivant le calme.",
     "date":"2026-09-02"},
    {"slug":"choisir-lampe-scandinave","title":"Comment choisir une lampe pour un intérieur scandinave","tag":"Éclairage","img":"art-lampe",
     "excerpt":"La lumière fait le style scandinave. Quelques repères simples pour choisir une lampe qui réchauffe la pièce.",
     "date":"2026-08-28"},
    {"slug":"details-piece-chaleureuse","title":"Les détails qui rendent une pièce plus chaleureuse","tag":"Inspiration","img":"art-chaleur",
     "excerpt":"Ce ne sont jamais les gros meubles qui réchauffent une pièce, mais une série de petits choix. Tour d'horizon.",
     "date":"2026-08-20"},
]

# ----------------------------------------------------------------
# Icônes SVG inline (catégories) — traits fins, cohérents
# ----------------------------------------------------------------
ICONS = {
 "chair":'<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M6 10V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v5M5 10h14v4H5zM7 14v6M17 14v6"/></svg>',
 "lamp":'<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M8 3h8l3 8H5zM12 11v7M8 21h8"/></svg>',
 "box":'<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M3 8l9-5 9 5v8l-9 5-9-5zM3 8l9 5 9-5M12 13v8"/></svg>',
 "vase":'<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M9 3h6M8 7c0 6-3 6-3 11a3 3 0 0 0 3 3h8a3 3 0 0 0 3-3c0-5-3-5-3-11M8 7h8"/></svg>',
}
ARROW = '<svg class="arrow" viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M2 8h11M9 4l4 4-4 4"/></svg>'
NEW_WINDOW = '<span class="sr-only"> (s\'ouvre dans une nouvelle fenêtre)</span>'

NAV = [("inspirations.html","Inspirations"),("styles.html","Styles"),("journal.html","Journal"),("about.html","À propos")]

FONTS_URL = "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Inter:wght@400;500;600&display=swap"

# ----------------------------------------------------------------
# Utilitaires
# ----------------------------------------------------------------
def esc(s):
    """Échappe texte/attributs HTML (indispensable pour toute donnée externe)."""
    return _html.escape(str(s), quote=True)

def image_size(path):
    """Dimensions (w, h) d'un PNG ou JPEG, en stdlib. None si illisible."""
    try:
        with open(path, "rb") as f:
            head = f.read(26)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                w, h = struct.unpack(">II", head[16:24]); return w, h
            if head[:2] != b"\xff\xd8":
                return None
            f.seek(2)
            while True:
                b = f.read(1)
                while b and b != b"\xff": b = f.read(1)
                while b == b"\xff": b = f.read(1)
                if not b: return None
                m = b[0]
                if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                    f.read(3); h, w = struct.unpack(">HH", f.read(4)); return w, h
                (ln,) = struct.unpack(">H", f.read(2)); f.seek(ln - 2, 1)
    except (OSError, struct.error):
        return None

_asset_hash = {}
def asset_url(rel):
    """URL versionnée (?v=hash du contenu) → cache long côté navigateur sans risque de contenu périmé."""
    if rel not in _asset_hash:
        try:
            with open(os.path.join(HERE, rel), "rb") as f:
                _asset_hash[rel] = hashlib.sha1(f.read()).hexdigest()[:8]
        except OSError:
            _asset_hash[rel] = None
    v = _asset_hash[rel]
    return f"/{rel}?v={v}" if v else f"/{rel}"

# ----------------------------------------------------------------
# Fragments partagés
# ----------------------------------------------------------------
def head(title, desc, path, og_type="website"):
    canon = f"{SITE_URL}/{path}" if path != "index.html" else f"{SITE_URL}/"
    t, d = esc(title), esc(desc)
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{canon}">
<meta name="theme-color" content="#F2EBE0">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="UnoSnake">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE_URL}/assets/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="UnoSnake — inspirations déco scandinave, japandi et minimalisme chaleureux">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{SITE_URL}/assets/og-image.jpg">
<link rel="icon" href="/assets/favicon.ico" sizes="any">
<link rel="icon" type="image/png" href="/assets/favicon-32.png" sizes="32x32">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{asset_url('assets/style.css')}">
<link rel="stylesheet" href="{FONTS_URL}">
<noscript><style>.reveal{{opacity:1;transform:none}}</style></noscript>
</head>
<body>"""

def header(active="", current=True):
    """active = page mise en avant dans la nav ; current=False pour une sous-page (article) :
    le lien est visuellement actif mais sans aria-current, réservé à la page exacte."""
    def link(href, label):
        if href != active:
            return f'<a href="/{href}">{label}</a>'
        attr = ' aria-current="page"' if current else ' class="is-active"'
        return f'<a href="/{href}"{attr}>{label}</a>'
    links = "".join(link(h, l) for h, l in NAV)
    mlinks = "".join(f'<a href="/{href}">{label}</a>' for href,label in NAV)
    logo = asset_url("assets/logo-mark-128.png")
    return f"""<a class="skip-link" href="#main">Aller au contenu</a>
<header class="site-header">
  <div class="container header-inner">
    <a class="brand" href="/" aria-label="UnoSnake — accueil">
      <img class="brand-logo" src="{logo}" width="42" height="42" alt="">
      <span class="brand-name">UnoSnake</span>
    </a>
    <nav class="nav-desktop" aria-label="Navigation principale">{links}</nav>
    <div class="header-actions">
      <a class="btn btn-secondary nav-desktop-cta" href="/inspirations.html">Découvrir</a>
      <button class="burger" type="button" aria-label="Ouvrir le menu" aria-expanded="false" aria-controls="mobile-nav">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
</header>
<nav class="nav-mobile" id="mobile-nav" aria-label="Navigation mobile">
  {mlinks}
  <a class="btn btn-primary" href="/inspirations.html">Découvrir les inspirations</a>
</nav>"""

def footer():
    style_links = "".join(f'<a href="/styles.html#{s["slug"]}">{s["name"]}</a>' for s in STYLES)
    logo = asset_url("assets/logo-mark-128.png")
    return f"""<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand-col">
        <div class="footer-brand">
          <img src="{logo}" width="40" height="40" alt="">
          <span>UnoSnake</span>
        </div>
        <p class="footer-about">Inspirations et sélections déco autour des styles scandinave, japandi et minimalisme chaleureux.</p>
      </div>
      <nav class="footer-col" aria-labelledby="f-explore">
        <h2 class="footer-heading" id="f-explore">Explorer</h2>
        <a href="/inspirations.html">Inspirations</a>
        <a href="/styles.html">Styles</a>
        <a href="/journal.html">Journal</a>
        <a href="/about.html">À propos</a>
      </nav>
      <nav class="footer-col" aria-labelledby="f-styles">
        <h2 class="footer-heading" id="f-styles">Styles</h2>
        {style_links}
      </nav>
      <nav class="footer-col" aria-labelledby="f-info">
        <h2 class="footer-heading" id="f-info">Informations</h2>
        <a href="/affiliate.html">Transparence</a>
        <a href="/privacy.html">Confidentialité</a>
        <a href="/legal.html">Mentions légales</a>
      </nav>
    </div>
    <div class="footer-bottom">
      <span>© <span data-year>2026</span> UnoSnake. Tous droits réservés.</span>
      <span>Fait avec soin pour des intérieurs plus chaleureux.</span>
    </div>
  </div>
</footer>
<script src="{asset_url('assets/main.js')}" defer></script>
</body>
</html>"""

def picture(name, alt, lazy=True, priority=False, decorative=False):
    """<picture> WebP + repli JPG, width/height explicites (anti-CLS), lazy par défaut.
    decorative=True → alt vide (image dans un lien dont le texte porte déjà le sens)."""
    jpg = f"assets/img/{name}.jpg"
    size = image_size(os.path.join(HERE, jpg))
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
    loading = 'loading="lazy" decoding="async"' if lazy else 'decoding="async"'
    if priority: loading += ' fetchpriority="high"'
    a = "" if decorative else esc(alt)
    return (f'<picture><source type="image/webp" srcset="{asset_url(f"assets/img/{name}.webp")}">'
            f'<img src="{asset_url(jpg)}"{dims} alt="{a}" {loading}></picture>')

def product_card(p, lazy=True, hlevel=3):
    h = f"h{hlevel}"
    name = esc(p["name"])
    badge = f'<span class="badge">{esc(p["style"])}</span>'
    price = f'<span class="product-price">{esc(p["price"])}</span>' if p.get("price") else '<span class="product-price muted">Sélection</span>'
    media = f'<div class="product-media">{picture(p["img"], p["name"], lazy=lazy, decorative=True)}{badge}</div>'
    if p.get("asin"):
        cta = f'<span class="product-cta">Voir sur Amazon{NEW_WINDOW} {ARROW}</span>'
        return f"""<a class="product-card reveal" href="{affiliate(p["asin"])}" rel="sponsored nofollow noopener" target="_blank">
  {media}
  <div class="product-body">
    <span class="product-cat">{esc(p["cat"])}</span>
    <{h} class="product-name">{name}</{h}>
    <div class="product-meta">{price}<span class="product-cta">Voir sur Amazon{NEW_WINDOW} {ARROW}</span></div>
  </div>
</a>"""
    # Pas encore de produit réel derrière cette carte : aucun lien trompeur.
    return f"""<article class="product-card is-placeholder reveal">
  {media}
  <div class="product-body">
    <span class="product-cat">{esc(p["cat"])}</span>
    <{h} class="product-name">{name}</{h}>
    <div class="product-meta">{price}<span class="product-cta">Sélection à venir</span></div>
  </div>
</article>"""

def style_card(s, hlevel=3):
    h = f"h{hlevel}"
    return f"""<a class="style-card reveal" href="/styles.html#{s['slug']}">
  {picture(s['img'], f"Ambiance {s['name']}", decorative=True)}
  <div class="style-card-body">
    <{h}>{esc(s['name'])}</{h}>
    <p>{esc(s['line'])}</p>
  </div>
</a>"""

def article_card(a, hlevel=3):
    h = f"h{hlevel}"
    return f"""<a class="article-card reveal" href="/article-{a['slug']}.html">
  <div class="article-media">{picture(a['img'], a['title'], decorative=True)}</div>
  <span class="article-tag">{esc(a['tag'])}</span>
  <{h}>{esc(a['title'])}</{h}>
  <p>{esc(a['excerpt'])}</p>
</a>"""

DISCLOSURE = """<div class="disclosure reveal">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v4h1"/></svg>
  <p>Certains liens présents sur UnoSnake sont des liens affiliés. Si vous effectuez un achat via ces liens, nous pouvons percevoir une commission, sans coût supplémentaire pour vous. Cela n'influence pas nos sélections.</p>
</div>"""

FR_MONTHS = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]
def fr_date(iso):
    y, m, d = iso.split("-")
    return f"{int(d)} {FR_MONTHS[int(m)-1]} {y}"

def write(path, content):
    with open(os.path.join(HERE, path), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ {path}")

# ----------------------------------------------------------------
# PAGES
# ----------------------------------------------------------------
def build_index():
    # Sur toutes les largeurs, la grille produits est sous le hero : lazy partout.
    prods = "".join(product_card(p) for p in PRODUCTS[:4])
    styles = "".join(style_card(s) for s in STYLES)
    cats = "".join(f'<a class="cat-card reveal" href="/inspirations.html">{ICONS[c["icon"]]}<span>{c["name"]}</span></a>' for c in CATEGORIES)
    arts = "".join(article_card(a) for a in ARTICLES)
    schema = json.dumps({
        "@context":"https://schema.org","@type":"WebSite","name":"UnoSnake",
        "url":SITE_URL+"/","inLanguage":"fr",
        "description":"Inspirations et sélections déco — scandinave, japandi, minimalisme chaleureux."
    }, ensure_ascii=False)
    org = json.dumps({
        "@context":"https://schema.org","@type":"Organization","name":"UnoSnake",
        "url":SITE_URL+"/","logo":SITE_URL+"/assets/logo-mark.png"
    }, ensure_ascii=False)
    page = head(
        "UnoSnake — Inspirations déco scandinave, japandi & minimalisme chaleureux",
        "UnoSnake sélectionne des inspirations et des pièces déco autour des styles scandinave, japandi et minimalisme chaleureux. Des intérieurs qui donnent envie de rester.",
        "index.html")
    page += f'<script type="application/ld+json">{schema}</script>'
    page += f'<script type="application/ld+json">{org}</script>'
    page += header("")
    # Le hero est le contenu principal (LCP) : il s'affiche immédiatement, sans animation d'apparition.
    page += f"""<main id="main">
  <section class="hero">
    <div class="container hero-grid">
      <div class="hero-copy">
        <span class="eyebrow">Scandinave · Japandi · Minimalisme chaleureux</span>
        <h1 class="display">Des intérieurs qui donnent envie de rester.</h1>
        <p class="lead">UnoSnake sélectionne des inspirations et des pièces déco choisies avec soin, pour des espaces naturels, calmes et intemporels.</p>
        <div class="hero-actions">
          <a class="btn btn-primary" href="/inspirations.html">Découvrir les inspirations</a>
          <a class="btn btn-secondary" href="/styles.html">Explorer les styles</a>
        </div>
      </div>
      <div class="hero-visual">
        {picture("hero","Intérieur chaleureux minimaliste avec arche et vase", lazy=False, priority=True)}
        <span class="hero-tag">Sélection UnoSnake</span>
      </div>
    </div>
  </section>

  <section class="section" aria-labelledby="sel-h">
    <div class="container">
      <div class="section-head reveal">
        <span class="eyebrow">Les sélections UnoSnake</span>
        <h2 id="sel-h">La sélection du moment</h2>
        <p>Des pièces repérées pour leur justesse — matières naturelles, formes sobres, présence discrète.</p>
      </div>
      <div class="grid-products">{prods}</div>
      <div class="section-more reveal"><a class="btn btn-ghost" href="/inspirations.html">Voir toutes les inspirations {ARROW}</a></div>
    </div>
  </section>

  <section class="section section-alt" aria-labelledby="sty-h">
    <div class="container">
      <div class="section-head reveal">
        <span class="eyebrow">Univers</span>
        <h2 id="sty-h">Explorer par style</h2>
        <p>Quatre sensibilités pour composer un intérieur qui vous ressemble.</p>
      </div>
      <div class="grid-styles">{styles}</div>
    </div>
  </section>

  <section class="section" aria-labelledby="cat-h">
    <div class="container">
      <div class="section-head reveal">
        <span class="eyebrow">Catégories</span>
        <h2 id="cat-h">Explorer par catégorie</h2>
      </div>
      <div class="grid-cats">{cats}</div>
    </div>
  </section>

  <section class="section band">
    <div class="container quote">
      <p class="reveal">« Rendre les espaces du quotidien un peu plus beaux. »</p>
    </div>
  </section>

  <section class="section" aria-labelledby="jour-h">
    <div class="container">
      <div class="section-head reveal">
        <span class="eyebrow">Le Journal UnoSnake</span>
        <h2 id="jour-h">Inspirations & conseils</h2>
        <p>Des idées concrètes pour composer, choisir et réchauffer vos intérieurs.</p>
      </div>
      <div class="grid-3">{arts}</div>
    </div>
  </section>

  <section class="section-sm">
    <div class="container">{DISCLOSURE}</div>
  </section>
</main>"""
    page += footer()
    write("index.html", page)

def build_styles():
    page = head("Styles — Scandinave, Japandi, Minimalisme chaleureux, Bohème | UnoSnake",
                "Découvrez les univers UnoSnake : scandinave, japandi, minimalisme chaleureux et bohème. Palettes, philosophie et sélections pour chaque style.",
                "styles.html")
    page += header("styles.html")
    blocks = ""
    for i, s in enumerate(STYLES):
        flipped = " is-flipped" if i % 2 else ""      # alternance image gauche / droite sur desktop
        alt_bg = " section-alt" if i % 2 else ""
        blocks += f"""<section class="section{alt_bg}" id="{s['slug']}" aria-labelledby="{s['slug']}-h">
      <div class="container style-detail">
        <figure class="style-figure reveal{flipped}">{picture(s['img'], f"Ambiance {s['name']}", lazy=(i > 0))}</figure>
        <div class="style-copy reveal">
          <span class="eyebrow">Univers</span>
          <h2 id="{s['slug']}-h">{esc(s['name'])}</h2>
          <p class="lead italic">{esc(s['line'])}</p>
          <p class="text-2">{esc(s['desc'])}</p>
          <div class="section-more"><a class="btn btn-ghost" href="/inspirations.html">Voir les sélections {ARROW}</a></div>
        </div>
      </div>
    </section>"""
    page += f"""<main id="main">
  <section class="section page-head">
    <div class="container section-head">
      <span class="eyebrow">Univers UnoSnake</span>
      <h1>Explorer par style</h1>
      <p>Quatre sensibilités qui partagent la même idée : des intérieurs naturels, calmes et durables.</p>
    </div>
  </section>
  {blocks}
  <section class="section-sm"><div class="container">{DISCLOSURE}</div></section>
</main>"""
    page += footer()
    write("styles.html", page)

def build_inspirations():
    # Les deux premières cartes sont visibles au chargement (desktop) : chargement immédiat.
    prods = "".join(product_card(p, lazy=(i > 1), hlevel=2) for i, p in enumerate(PRODUCTS))
    page = head("Inspirations déco — Sélections UnoSnake",
                "La galerie des sélections UnoSnake : mobilier, éclairage, rangement et décoration choisis autour des styles scandinave, japandi et minimalisme chaleureux.",
                "inspirations.html")
    page += header("inspirations.html")
    page += f"""<main id="main">
  <section class="section page-head">
    <div class="container section-head">
      <span class="eyebrow">Les sélections UnoSnake</span>
      <h1>Inspirations</h1>
      <p>Chaque pièce est repérée pour sa justesse et sa cohérence avec un intérieur pensé dans la durée — jamais pour accumuler.</p>
    </div>
  </section>
  <section class="section page-body" aria-label="Sélections">
    <div class="container">
      <div class="grid-products">{prods}</div>
    </div>
  </section>
  <section class="section-sm"><div class="container">{DISCLOSURE}</div></section>
</main>"""
    page += footer()
    write("inspirations.html", page)

def build_journal():
    arts = "".join(article_card(a, hlevel=2) for a in ARTICLES)
    page = head("Le Journal UnoSnake — Inspirations & conseils déco",
                "Le Journal UnoSnake : idées et conseils pour composer des intérieurs scandinaves, japandi et chaleureux. Des articles pensés comme de vraies lectures déco.",
                "journal.html")
    page += header("journal.html")
    page += f"""<main id="main">
  <section class="section page-head">
    <div class="container section-head">
      <span class="eyebrow">Le Journal UnoSnake</span>
      <h1>Inspirations & conseils</h1>
      <p>Des idées concrètes pour composer, choisir et réchauffer vos intérieurs — sans jargon, sans surenchère.</p>
    </div>
  </section>
  <section class="section page-body" aria-label="Articles">
    <div class="container"><div class="grid-3">{arts}</div></div>
  </section>
</main>"""
    page += footer()
    write("journal.html", page)

def build_article(a):
    bc = f'<a href="/">Accueil</a><span class="sep" aria-hidden="true">/</span><a href="/journal.html">Journal</a><span class="sep" aria-hidden="true">/</span><span aria-current="page">{esc(a["tag"])}</span>'
    reco = "".join(product_card(p) for p in PRODUCTS[:3])
    related = "".join(article_card(x) for x in ARTICLES if x["slug"] != a["slug"])
    hero_name = a.get("hero_img", a["img"])
    hero_cls = "article-hero article-hero--wide" if a.get("hero_img") else "article-hero"
    schema = json.dumps({
        "@context":"https://schema.org","@type":"Article","headline":a["title"],
        "description":a["excerpt"],
        "datePublished":a["date"],"dateModified":a.get("updated", a["date"]),"inLanguage":"fr",
        "image":f"{SITE_URL}/assets/img/{hero_name}.jpg",
        "mainEntityOfPage":f"{SITE_URL}/article-{a['slug']}.html",
        "author":{"@type":"Organization","name":"UnoSnake","url":SITE_URL+"/"},
        "publisher":{"@type":"Organization","name":"UnoSnake","logo":{"@type":"ImageObject","url":f"{SITE_URL}/assets/logo-mark.png"}}
    }, ensure_ascii=False)
    breadcrumb = json.dumps({
        "@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
            {"@type":"ListItem","position":1,"name":"Accueil","item":SITE_URL+"/"},
            {"@type":"ListItem","position":2,"name":"Journal","item":SITE_URL+"/journal.html"},
            {"@type":"ListItem","position":3,"name":a["title"]},
        ]}, ensure_ascii=False)

    BODIES = {
      "interieur-japandi-chaleureux": """
        <p>Le japandi est souvent réduit à une palette de beiges et à quelques branches dans un vase. C'est réducteur. Ce qui fait la chaleur d'un intérieur japandi, c'est un équilibre — entre le vide et le plein, le clair et le foncé, le lisse et le brut.</p>
        <h2>1. Garder du vide, volontairement</h2>
        <p>Le calme naît de l'espace négatif. Laissez respirer les surfaces : une étagère à moitié vide raconte plus qu'une étagère saturée.</p>
        <h2>2. Mélanger deux bois</h2>
        <p>Un bois clair nordique et un bois plus sombre, presque noyer, créent la profondeur qui empêche la pièce de paraître fade.</p>
        <blockquote>La chaleur ne vient pas d'un objet, mais de la relation entre les matières.</blockquote>
        <h2>3. Choisir la lumière basse et douce</h2>
        <p>Une lampe à intensité chaude, posée bas, transforme l'ambiance d'une pièce dès la tombée du jour.</p>
        <div class="pull-tip"><strong>Le détail qui compte —</strong> une seule matière naturelle vivante (lin froissé, céramique mate, rotin) suffit à réchauffer tout un mur neutre.</div>
        <h2>4. Assumer l'artisanat</h2>
        <p>Une pièce légèrement irrégulière, faite main, apporte l'imperfection qui rend un intérieur habité plutôt que décoré.</p>
      """,
    }
    body = BODIES.get(a["slug"], f"""
        <p>{esc(a['excerpt'])}</p>
        <h2>Une approche simple</h2>
        <p>Chez UnoSnake, nous partons toujours d'une idée : un intérieur réussi n'est pas le plus rempli, c'est le plus juste. Quelques repères suffisent pour transformer une pièce.</p>
        <blockquote>Moins d'objets, mais mieux choisis.</blockquote>
        <h2>Par où commencer</h2>
        <p>Observez d'abord la lumière, puis les matières, enfin les proportions. C'est dans cet ordre que se construit une ambiance cohérente et chaleureuse.</p>
        <div class="pull-tip"><strong>À retenir —</strong> une pièce se réchauffe par petites touches : une matière naturelle, une lumière basse, une asymétrie assumée.</div>
    """)

    page = head(f"{a['title']} | Le Journal UnoSnake", a["excerpt"], f"article-{a['slug']}.html", og_type="article")
    page += f'<script type="application/ld+json">{schema}</script>'
    page += f'<script type="application/ld+json">{breadcrumb}</script>'
    page += header("journal.html", current=False)
    page += f"""<main id="main">
  <article>
    <header class="container container-narrow article-head">
      <nav class="breadcrumb" aria-label="Fil d'Ariane">{bc}</nav>
      <span class="article-tag">{esc(a['tag'])}</span>
      <h1>{esc(a['title'])}</h1>
      <p class="lead">{esc(a['excerpt'])}</p>
      <p class="article-meta">Publié le <time datetime="{a['date']}">{fr_date(a['date'])}</time> · Par UnoSnake</p>
    </header>
    <div class="container">
      <div class="{hero_cls}">{picture(hero_name, a['title'], lazy=False, priority=True, decorative=True)}</div>
    </div>
    <div class="container">
      <div class="prose">{body}</div>
    </div>
  </article>
  <aside class="container section-gap" aria-labelledby="reco-h">
    <div class="section-head reveal"><span class="eyebrow">Sélection associée</span><h2 id="reco-h">Des pièces qui vont avec</h2></div>
    <div class="grid-3">{reco}</div>
  </aside>
  <div class="container-narrow container section-gap-sm">{DISCLOSURE}</div>
  <aside class="container section-gap" aria-labelledby="rel-h">
    <div class="section-head reveal"><span class="eyebrow">À lire ensuite</span><h2 id="rel-h">Articles similaires</h2></div>
    <div class="grid-2">{related}</div>
  </aside>
</main>"""
    page += footer()
    write(f"article-{a['slug']}.html", page)

def build_about():
    page = head("À propos — Notre démarche | UnoSnake",
                "UnoSnake est un projet éditorial dédié à la décoration intérieure. Notre démarche : le goût, la simplicité, la fonctionnalité et des sélections pensées avec soin.",
                "about.html")
    page += header("about.html")
    page += f"""<main id="main">
  <section class="section">
    <div class="container container-narrow">
      <span class="eyebrow">Notre démarche</span>
      <h1 class="page-title">Pourquoi UnoSnake existe</h1>
      <div class="prose prose-start">
        <p>UnoSnake est né d'une conviction simple : on vit mieux dans un intérieur pensé avec soin. Pas le plus cher, ni le plus rempli — le plus juste.</p>
        <h2>Notre philosophie</h2>
        <p>Nous croyons au goût plus qu'à la tendance, à la simplicité plus qu'à l'accumulation, à la fonctionnalité qui se fait oublier. Chaque pièce que nous mettons en avant doit avoir une raison d'être dans un intérieur cohérent.</p>
        <blockquote>Inspirer, sélectionner, recommander — puis s'effacer.</blockquote>
        <h2>Comment nous sélectionnons</h2>
        <p>Nos sélections s'appuient sur des critères clairs : cohérence avec un style (scandinave, japandi, minimalisme chaleureux, bohème), qualité des matières, sobriété des formes et pertinence dans la durée. Nous préférons montrer moins, mais mieux.</p>
        <h2>Notre modèle</h2>
        <p>UnoSnake est un média d'inspiration. Lorsque vous découvrez une pièce qui vous plaît, nous vous orientons directement vers le marchand. En toute transparence : certains de ces liens sont affiliés.</p>
      </div>
      <div class="section-more reveal">{DISCLOSURE}</div>
    </div>
  </section>
</main>"""
    page += footer()
    write("about.html", page)

def legal_page(path, title, desc, active, h1, blocks, updated="26 août 2026"):
    page = head(title, desc, path)
    page += header(active)
    inner = "".join(f"<h2>{h}</h2>\n<p>{b}</p>" for h, b in blocks)
    page += f"""<main id="main">
  <section class="section">
    <div class="container container-narrow">
      <span class="eyebrow">Informations</span>
      <h1 class="page-title page-title--tight">{h1}</h1>
      <p class="muted page-updated">Dernière mise à jour : {updated}</p>
      <div class="prose prose-start">{inner}</div>
    </div>
  </section>
</main>"""
    page += footer()
    write(path, page)

def build_legal():
    legal_page("affiliate.html","Transparence & affiliation | UnoSnake",
        "Transparence UnoSnake sur les liens affiliés : comment ils fonctionnent et pourquoi ils n'influencent pas nos sélections.",
        "", "Transparence",
        [("Nos liens affiliés","Certains liens présents sur UnoSnake sont des liens affiliés. Si vous effectuez un achat via l'un de ces liens, nous pouvons percevoir une commission, sans aucun coût supplémentaire pour vous."),
         ("Notre approche éditoriale","L'affiliation ne change rien à l'objectif de nos contenus : partager des idées déco utiles et des pièces cohérentes avec l'esthétique UnoSnake. Une commission potentielle n'influence pas nos sélections."),
         ("Amazon","UnoSnake participe au Programme Partenaires d'Amazon. Les liens produits pointent directement vers Amazon.fr. Les produits sont présentés comme des inspirations et des recommandations, pas comme une garantie qu'ils conviennent à chaque intérieur."),
         ("Une question ?","Pour toute question sur une recommandation ou une relation d'affiliation, contactez-nous via la plateforme sur laquelle vous avez découvert nos contenus.")])
    legal_page("privacy.html","Politique de confidentialité | UnoSnake",
        "Politique de confidentialité d'UnoSnake : quelles données sont collectées (ou non) et comment vos informations sont traitées.",
        "", "Politique de confidentialité",
        [("1. À propos de ce site","UnoSnake est un projet d'inspiration déco dédié aux intérieurs scandinaves, japandi et minimalistes chaleureux."),
         ("2. Données collectées","Ce site est conçu comme un site informatif simple. Nous ne collectons pas volontairement de données personnelles via des formulaires, comptes ou inscriptions sur ce site."),
         ("3. Cookies et mesure d'audience","À ce jour, ce site n'utilise pas volontairement de cookies publicitaires ni d'outils d'analyse tiers. Si cela change, cette politique sera mise à jour au préalable."),
         ("4. Services et liens tiers","UnoSnake peut renvoyer vers des sites tiers, des marketplaces et des réseaux sociaux, qui disposent de leurs propres politiques de confidentialité. Nous ne sommes pas responsables de leurs pratiques."),
         ("5. Pinterest et réseaux sociaux","UnoSnake peut publier du contenu sur des plateformes comme Pinterest. Les interactions avec ces plateformes relèvent de leurs politiques respectives. Ce site ne demande ni ne stocke de mots de passe de réseaux sociaux."),
         ("6. Modifications","Cette politique pourra être mise à jour lorsque le site ou ses services évoluent. La date en haut de page sera actualisée en conséquence."),
         ("7. Contact","Pour toute question relative à la confidentialité de ce site, contactez-nous via la plateforme sur laquelle vous avez découvert nos contenus.")])
    legal_page("legal.html","Mentions légales | UnoSnake",
        "Mentions légales du site UnoSnake.",
        "", "Mentions légales",
        [("Éditeur du site","Le site UnoSnake est édité dans le cadre d'un projet éditorial dédié à la décoration intérieure."),
         ("Hébergement","Le site est hébergé sur l'infrastructure Cloudflare."),
         ("Propriété intellectuelle","Le nom, le logo et l'identité visuelle UnoSnake, ainsi que les contenus éditoriaux du site, sont protégés. Toute reproduction sans autorisation est interdite."),
         ("Liens externes","Le site contient des liens vers des sites tiers, notamment Amazon.fr. UnoSnake n'est pas responsable du contenu de ces sites externes."),
         ("Contact","Pour toute demande, contactez-nous via la plateforme sur laquelle vous avez découvert nos contenus.")])

def build_404():
    page = head("Page introuvable | UnoSnake", "Cette page n'existe pas ou plus.", "404.html")
    page += header("")
    page += f"""<main id="main">
  <section class="center-screen container">
    <span class="eyebrow">Erreur 404</span>
    <h1 class="display">Cette pièce n'existe plus.</h1>
    <p class="lead center-lead">La page que vous cherchez a peut-être été déplacée ou n'existe pas. Reprenons l'exploration.</p>
    <div class="hero-actions hero-actions--center">
      <a class="btn btn-primary" href="/">Retour à l'accueil</a>
      <a class="btn btn-secondary" href="/inspirations.html">Voir les inspirations</a>
    </div>
  </section>
</main>"""
    page += footer()
    write("404.html", page)

def build_seo_files():
    pages = ["","styles.html","inspirations.html","journal.html","about.html",
             "affiliate.html","privacy.html","legal.html"]
    urls = ""
    for p in pages:
        loc = f"{SITE_URL}/" if p == "" else f"{SITE_URL}/{p}"
        pr = "1.0" if p == "" else "0.7"
        urls += f"  <url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>{pr}</priority></url>\n"
    for a in ARTICLES:
        urls += (f"  <url><loc>{SITE_URL}/article-{a['slug']}.html</loc><lastmod>{a.get('updated', a['date'])}</lastmod>"
                 f"<changefreq>monthly</changefreq><priority>0.7</priority></url>\n")
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}</urlset>"""
    write("sitemap.xml", sitemap)
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    # PWA manifest
    manifest = json.dumps({
        "name":"UnoSnake","short_name":"UnoSnake","lang":"fr",
        "start_url":"/","display":"standalone",
        "background_color":"#F2EBE0","theme_color":"#F2EBE0",
        "icons":[{"src":"/assets/apple-touch-icon.png","sizes":"180x180","type":"image/png"},
                 {"src":"/assets/logo-mark.png","sizes":"512x512","type":"image/png"}]
    }, ensure_ascii=False, indent=2)
    write("manifest.webmanifest", manifest)

def build_all():
    build_index()
    build_styles()
    build_inspirations()
    build_journal()
    for a in ARTICLES: build_article(a)
    build_about()
    build_legal()
    build_404()
    build_seo_files()

if __name__ == "__main__":
    print("Building UnoSnake site…")
    build_all()
    print("Done.")
