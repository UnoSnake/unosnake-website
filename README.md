# 🐍 UnoSnake — Website & Autopilot

Marque éditoriale de décoration intérieure (scandinave, japandi, minimalisme chaleureux, bohème).
Le dépôt contient **deux parties découplées** :

1. **Le site** (frontend statique, déployé sur Cloudflare)
2. **L'autopilot** (backend Python, orchestré par GitHub Actions) : découverte produits → scoring → contenu → Airtable → Pinterest

---

## 🌐 Site (frontend)

Site statique premium en HTML/CSS/JS vanilla — aucune dépendance lourde.

### Pages
```
index.html              Accueil (hero, sélections, styles, catégories, journal)
styles.html             4 univers (Scandinave, Japandi, Warm Minimalism, Bohème)
inspirations.html       Galerie éditoriale des sélections
journal.html            Le Journal UnoSnake (articles)
article-*.html          3 articles (gabarit éditorial)
about.html              À propos / démarche
privacy.html            Confidentialité (FR)
affiliate.html          Transparence affiliation (FR)
legal.html              Mentions légales (FR)
404.html                Page introuvable
```

### Assets
```
assets/style.css        Design system complet (tokens : couleurs, spacing, typo, ombres…)
assets/main.js          Interactions (header scroll, menu mobile, reveals) — ~2 Ko
assets/logo-mark.png    Logo officiel UnoSnake
assets/favicon*.png     Favicons + apple-touch-icon
assets/og-image.jpg     Image de partage social
assets/img/             Visuels éditoriaux (WebP + JPG fallback)
```

### Design system
- **Couleurs** : ivoire `#F2EBE0`, surface `#FAF6EF`, encre `#2B291F`, noyer `#7D5A3C`, accent `#8A7748`…
- **Typographie** : Cormorant Garamond (display) + Inter (texte)
- **Accessibilité** : HTML sémantique, focus visibles, `prefers-reduced-motion`, contrastes AA
- **SEO** : canonical, Open Graph, Twitter cards, schema.org (Organization/WebSite/Article/BreadcrumbList), `sitemap.xml`, `robots.txt`, `lang="fr"`

### Régénérer le site
Les pages sont générées par `build.py` (source unique de vérité pour header/footer/SEO) :
```bash
python build.py
```

---

## ☁️ Déploiement Cloudflare

Inchangé : le site est servi par un Cloudflare Worker.
```
wrangler.jsonc   Config (assets binding, SPA fallback)
worker.js        Worker (sert les assets + endpoint /api/amazon-test)
```
Le worker lit les credentials Amazon **depuis les variables d'environnement Cloudflare** (`env.AMAZON_CREDENTIAL_ID`, `env.AMAZON_CREDENTIAL_SECRET`). **Aucun secret n'est stocké dans le code.**

```bash
npx wrangler deploy
```
URL : https://unosnake-website.unosnakeshop.workers.dev/

---

## 🤖 Autopilot (backend Python)

Pipeline automatisé — **totalement découplé du site**.

```
scripts/config.py            Configuration centralisée (feature flags, limites)
scripts/discovery/           Google Trends + Serper → candidats Amazon.fr
scripts/scoring/             Scoring produit 0–100 (seuil 65)
scripts/content/             Génération titres/descriptions/hashtags (déterministe)
scripts/amazon/              Extraction ASIN + URL affiliée officielle
scripts/airtable/            CRUD + dédup + machine à états (New→Selected→Published)
scripts/pinterest/           Client API v5 + publisher + Launch Gate
scripts/scheduler/           Autopilot + data quality
scripts/site/                Pont vers le site : export_products.py (Airtable → products.json), fetch_photos.py
```

### Produits affichés sur le site (Airtable → `products.json`)
Le site n'embarque aucun produit codé en dur. `scripts/site/export_products.py` lit la table
Products (filtre `Published = true`, token côté GitHub Actions uniquement) et écrit `products.json`,
un fichier **public et non sensible** : `name, asin, category, style, image_url, affiliate_url`, rien d'autre.
`build.py` génère les cartes à partir de ce fichier ; s'il est vide, le site affiche un état vide propre.
Le workflow `export-products.yml` (manuel + quotidien) régénère `products.json` et les pages, puis
committe le résultat — Cloudflare redéploie automatiquement.

### Flux
```
Discovery → Dedup → Scoring → Content → Affiliate → Airtable (New)
         → Launch Gate → Selected → Pinterest → Published
```

### Format lien affilié (officiel, ne jamais modifier)
```
https://www.amazon.fr/dp/{ASIN}/ref=nosim?tag=unosnake09-21
```

### Launch Gate (Phase 14)
Détermine si la publication production Pinterest est autorisée : **READY / BLOCKED**.
Safe-by-default : 12 checks critiques, un seul échec ⇒ BLOCKED. Aucun token exposé.

### Workflows GitHub Actions
```
.github/workflows/test.yml              CI — 9 suites de tests (push, PR, manuel)
.github/workflows/export-products.yml   Airtable → products.json → site (manuel + cron quotidien)
.github/workflows/discover.yml          Découverte (manuel/cron)
.github/workflows/autopilot.yml         Pipeline complet (cron 4×/jour)
.github/workflows/live-pilot.yml        Pilote données réelles (manuel)
.github/workflows/production-check.yml  Launch Gate READY/BLOCKED (manuel, aucun Pin)
.github/workflows/first-pin.yml         Premier Pin (manuel, confirm=PUBLISH)
```

### Secrets (GitHub Actions — jamais dans le code)
`SERPER_API_KEY`, `AIRTABLE_BASE_ID`, `AIRTABLE_TOKEN`, `AMAZON_PARTNER_TAG`, `PINTEREST_ACCESS_TOKEN`

### Tests
```bash
python tests/run_tests.py                 # 129
python tests/test_content.py              # 24
python tests/test_pinterest.py            # 37
python tests/test_scheduler.py            # 20
python tests/test_production_hardening.py # 36
python tests/test_live_dry_run.py         # 20
python tests/test_real_data_pilot.py      # 20
python tests/test_launch_gate.py          # 22
python tests/test_export_products.py      # 19 (export Airtable → products.json + build.py)
# Total : 327 tests
```

---

## 🔒 Sécurité
- Aucun secret dans le dépôt (tout via env Cloudflare / GitHub Secrets)
- Liens Amazon directs (aucune redirection intermédiaire)
- `.gitignore` exclut credentials, `.env`, `.dev.vars`

## État Pinterest
Production en attente d'approbation de l'app Pinterest. Le Launch Gate reste **BLOCKED** tant que l'app n'est pas approuvée — c'est le comportement attendu.
