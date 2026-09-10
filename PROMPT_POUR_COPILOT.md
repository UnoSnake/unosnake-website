# PROMPT À DONNER À GITHUB COPILOT

> Copie tout le bloc ci-dessous et donne-le à GitHub Copilot (coding agent),
> en lui donnant accès au dépôt `UnoSnake/unosnake-website` et au dossier local
> `GitHub UnoSnake` (fourni). Copilot doit committer et pousser à ta place.

---

## MISSION

Tu dois mettre à jour le dépôt GitHub `UnoSnake/unosnake-website` (branche `main`)
avec le contenu complet du dossier local fourni **`GitHub UnoSnake`**.

Ce dossier est la **version finale et validée** du projet : un site web premium
entièrement refondu (frontend) + un pipeline d'automatisation Python complet
(backend « Autopilot »), avec 308 tests unitaires qui passent tous.

Le dépôt actuel ne contient qu'une ancienne version minimale (dernier commit
`223882d`). Tu dois le faire évoluer vers la version fournie, **sans rien casser**.

## RÈGLES ABSOLUES

1. **Ne jamais committer de secret.** Aucune clé API, token, mot de passe ou
   credential ne doit apparaître dans le code. Les secrets vivent uniquement
   dans les GitHub Secrets et les variables d'environnement Cloudflare.
   Si tu détectes un secret dans un fichier, ARRÊTE et signale-le.
2. **Ne pas modifier le format des liens affiliés Amazon** :
   `https://www.amazon.fr/dp/{ASIN}/ref=nosim?tag=unosnake09-21`
3. **Ne pas casser le déploiement Cloudflare.** Conserver `worker.js` et
   `wrangler.jsonc` tels quels (ils sont dans le dossier fourni, identiques à
   l'actuel — le worker lit les credentials depuis `env`, ne rien y coder en dur).
4. **Préserver l'arborescence exacte** du dossier fourni (sous-dossiers
   `scripts/`, `tests/`, `.github/workflows/`, `assets/img/`, etc.).
5. Le fichier `.gitignore` fourni doit être respecté (exclut `__pycache__`,
   `*credentials*.csv`, `.env`, `.dev.vars`, `node_modules`, `.wrangler`).
6. Ne PAS committer de fichier `*credentials*.csv` ni aucun `.env`.

## CE QU'IL FAUT FAIRE

1. Remplacer / ajouter tous les fichiers du dépôt par ceux du dossier fourni.
   - L'ancien `index.html` / `style.css` (site en anglais) est remplacé par la
     nouvelle version française premium.
   - Ajouter toutes les nouvelles pages : `styles.html`, `inspirations.html`,
     `journal.html`, `article-*.html`, `about.html`, `legal.html`, `404.html`.
   - Ajouter tout le backend Python : `scripts/**`, `tests/**`.
   - Ajouter les workflows : `.github/workflows/*.yml`.
   - Ajouter `assets/**` (logo, css, js, favicons, og-image, img/).
   - Ajouter `README.md`, `.gitignore`, `robots.txt`, `sitemap.xml`,
     `manifest.webmanifest`, `build.py`, `niches.json`, `requirements.txt`.
   - L'ancien `articles.html` peut être supprimé (remplacé par `journal.html`).

2. Faire des **commits propres et séparés par thème** (pas un seul commit géant) :
   ```
   feat: add UnoSnake autopilot backend (discovery, scoring, content, airtable)
   feat: add Pinterest module + Launch Gate (production readiness)
   feat: add GitHub Actions workflows (test, autopilot, live-pilot, production-check, first-pin)
   test: add full test suite (308 tests across 8 suites)
   feat: redesign website — premium editorial UnoSnake (FR, design system, SEO)
   feat: add brand assets (logo, favicons, og-image, editorial visuals)
   docs: update README with site + autopilot architecture
   chore: add .gitignore
   ```

3. Pousser sur `main`.

## VÉRIFICATIONS APRÈS PUSH

1. Le workflow `.github/workflows/test.yml` doit passer au vert (8 suites, 308 tests).
2. Vérifier qu'aucun secret n'a été poussé (`git log -p` / GitHub secret scanning).
3. Vérifier que le déploiement Cloudflare fonctionne toujours :
   https://unosnake-website.unosnakeshop.workers.dev/
   doit afficher le nouveau site.
4. Un seul `<h1>` par page, `lang="fr"`, liens internes valides.

## CONTEXTE TECHNIQUE (pour comprendre le projet)

- **Frontend** : HTML/CSS/JS vanilla, zéro framework. `build.py` (Python) régénère
  les pages HTML avec header/footer/SEO partagés.
- **Backend** : pipeline « Autopilot » — Google Trends + Serper → scoring 0–100
  (seuil 65) → génération de contenu → Airtable (machine à états
  New→Selected→Published) → Pinterest (protégé par un « Launch Gate »
  safe-by-default). Orchestré par GitHub Actions.
- **Déploiement** : Cloudflare Worker (`worker.js` + `wrangler.jsonc`).
- **Tests** : 308 tests, tous verts. Ne pas les casser.

## À LA FIN, RÉPONDS-MOI AVEC :
- Nombre de fichiers ajoutés / modifiés / supprimés
- Liste des commits créés
- Statut du workflow de tests (vert/rouge)
- Confirmation qu'aucun secret n'a été poussé
- Confirmation que le site est en ligne sur l'URL Cloudflare
