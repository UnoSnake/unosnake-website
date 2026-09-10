"""
UnoSnake — Export des produits publiés (Airtable → products.json public).

Chaîne : Airtable (table Products, Published = true) → products.json (racine du dépôt)
→ build.py génère les cartes produits du site.

Sécurité :
- AIRTABLE_TOKEN / AIRTABLE_BASE_ID sont lus depuis l'environnement (GitHub Secrets côté Actions).
  Rien n'est écrit côté navigateur : products.json ne contient QUE des données publiques.
- Champs exportés par produit, et rien d'autre : name, asin, category, style, image_url, affiliate_url.
- L'URL affiliée est TOUJOURS reconstruite au format officiel
  https://www.amazon.fr/dp/{ASIN}/ref=nosim?tag=unosnake09-21 (jamais recopiée telle quelle).

Usage :
    python scripts/site/export_products.py            # écrit products.json si son contenu change
    python scripts/site/export_products.py --dry-run  # affiche le JSON, n'écrit rien

Sortie déterministe (tri stable, JSON trié) → un run sans nouveauté ne produit aucun diff git.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from scripts.amazon.asin import extract_asin, build_affiliate_url, validate_affiliate_url, is_valid_asin  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PRODUCTS_FILE = os.path.join(ROOT, "products.json")

# Noms de colonnes Airtable EXACTS (voir schéma table Products)
FIELDS = ["Product Name", "Amazon URL", "Affiliate URL", "Image URL", "Category", "Style", "Published", "Date Added"]
PUBLISHED_FORMULA = "{Published}=TRUE()"

# Whitelist stricte des clés publiques
PUBLIC_KEYS = ("name", "asin", "category", "style", "image_url", "affiliate_url")
MAX_NAME_LEN = 120
MAX_LABEL_LEN = 40


def _clean(value, max_len: int) -> str:
    """Texte public : chaîne, espaces normalisés, longueur bornée."""
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:max_len].rstrip()


def _clean_image_url(value) -> str:
    """Seules les URLs https:// absolues sont conservées (CSP img-src https:)."""
    url = _clean(value, 2000)
    if not url.lower().startswith("https://") or any(c in url for c in ' "<>'):
        return ""
    return url


def normalize_record(fields: dict, partner_tag: str) -> dict | None:
    """
    Transforme les champs d'un record Airtable en produit public, ou None si inexploitable.

    Un produit est exploitable s'il a un nom et un ASIN valide (extrait de l'URL Amazon,
    sinon de l'URL affiliée). L'URL affiliée est reconstruite au format officiel.
    """
    if not fields or not fields.get("Published"):
        return None
    name = _clean(fields.get("Product Name"), MAX_NAME_LEN)
    asin = extract_asin(fields.get("Amazon URL") or "") or extract_asin(fields.get("Affiliate URL") or "")
    if not name or not is_valid_asin(asin or ""):
        return None
    affiliate_url = build_affiliate_url(asin, partner_tag)
    valid, _reason = validate_affiliate_url(affiliate_url, asin, partner_tag)
    if not valid:
        return None
    return {
        "name": name,
        "asin": asin,
        "category": _clean(fields.get("Category"), MAX_LABEL_LEN),
        "style": _clean(fields.get("Style"), MAX_LABEL_LEN),
        "image_url": _clean_image_url(fields.get("Image URL")),
        "affiliate_url": affiliate_url,
    }


def build_products(records: list[dict], partner_tag: str) -> list[dict]:
    """
    Records Airtable → liste de produits publics, du plus récent au plus ancien
    (Date Added décroissante, puis nom), sans doublon d'ASIN.
    """
    def sort_key(rec):
        f = rec.get("fields", {}) or {}
        return (str(f.get("Date Added") or ""), _clean(f.get("Product Name"), MAX_NAME_LEN))

    products, seen = [], set()
    for rec in sorted(records, key=sort_key, reverse=True):
        p = normalize_record(rec.get("fields", {}) or {}, partner_tag)
        if not p or p["asin"] in seen:
            continue
        seen.add(p["asin"])
        products.append({k: p[k] for k in PUBLIC_KEYS})
    return products


def render_json(products: list[dict]) -> str:
    """Sérialisation déterministe (clés triées, UTF-8 lisible, fin de ligne)."""
    return json.dumps({"products": products}, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def export(records: list[dict], partner_tag: str, path: str = PRODUCTS_FILE) -> tuple[bool, int]:
    """Écrit products.json uniquement si son contenu change. Retourne (changed, count)."""
    products = build_products(records, partner_tag)
    content = render_json(products)
    try:
        with open(path, encoding="utf-8") as f:
            unchanged = f.read() == content
    except OSError:
        unchanged = False
    if unchanged:
        return False, len(products)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return True, len(products)


def fetch_published_records():
    """Lit Airtable (Published = true) avec les credentials d'environnement. Ne loggue jamais le token."""
    from scripts import config
    from scripts.airtable.client import AirtableClient

    if not config.AIRTABLE_BASE_ID or not config.AIRTABLE_TOKEN:
        raise RuntimeError("AIRTABLE_BASE_ID / AIRTABLE_TOKEN manquants dans l'environnement")
    client = AirtableClient(config.AIRTABLE_BASE_ID, config.AIRTABLE_TABLE_ID, config.AIRTABLE_TOKEN, config.AIRTABLE_API_URL)
    return client.list_records(fields=FIELDS, filter_formula=PUBLISHED_FORMULA)


def main(argv=None) -> int:
    from scripts import config

    dry_run = "--dry-run" in (argv if argv is not None else sys.argv[1:])
    try:
        records = fetch_published_records()
    except Exception as e:  # message sans secret (le client ne loggue pas le token)
        print(f"✗ Airtable indisponible : {type(e).__name__}: {e}")
        return 1
    partner_tag = config.AMAZON_PARTNER_TAG
    if dry_run:
        print(render_json(build_products(records, partner_tag)), end="")
        return 0
    changed, count = export(records, partner_tag)
    print(f"✓ {count} produit(s) publié(s) → products.json {'mis à jour' if changed else 'inchangé'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
