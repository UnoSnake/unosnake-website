"""
UnoSnake — Site: export produits (Airtable → products.json → build.py).

Couvre :
- filtre Published, extraction ASIN, format affilié officiel, whitelist des champs publics
- nettoyage (espaces, longueur, image https uniquement), tri, dédoublonnage
- écriture déterministe et idempotente de products.json, aucun secret dans la sortie
- build.py : lecture de products.json, carte produit, état vide, libellés de style

Aucun appel réseau : records Airtable simulés.
"""

import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.site.export_products import (  # noqa: E402
    normalize_record, build_products, render_json, export, PUBLIC_KEYS, MAX_NAME_LEN,
)
import build  # noqa: E402  (générateur du site, à la racine du dépôt)

TAG = "unosnake09-21"
AFF_RE = re.compile(r"^https://www\.amazon\.fr/dp/([A-Z0-9]{10})/ref=nosim\?tag=unosnake09-21$")

# ── Minimal test framework (identique aux autres suites) ──
TESTS = []
PASSED = 0
FAILED = 0


def test(name):
    def decorator(fn):
        TESTS.append((name, fn))
        return fn
    return decorator


def run_all():
    global PASSED, FAILED
    print(f"\n{'='*60}")
    print("UnoSnake — Site: Export Products Tests")
    print(f"{'='*60}\n")
    for name, fn in TESTS:
        try:
            fn()
            PASSED += 1
            print(f"  ✅ {name}")
        except AssertionError as e:
            FAILED += 1
            print(f"  ❌ {name}: {e}")
        except Exception as e:
            FAILED += 1
            print(f"  ❌ {name}: EXCEPTION: {type(e).__name__}: {e}")
    print(f"\n{'─'*40}")
    print(f"  Total: {len(TESTS)} | Passed: {PASSED} | Failed: {FAILED}")
    print(f"{'='*60}\n")
    return FAILED == 0


def rec(**fields):
    """Record Airtable simulé (Published par défaut)."""
    base = {
        "Product Name": "Étagère flottante en bois massif",
        "Amazon URL": "https://www.amazon.fr/dp/B09FQ9RL1X/ref=sr_1_3?keywords=etagere",
        "Affiliate URL": "https://www.amazon.fr/dp/B09FQ9RL1X/ref=nosim?tag=unosnake09-21",
        "Image URL": "https://m.media-amazon.com/images/I/71abc.jpg",
        "Category": "Rangement",
        "Style": "Warm Minimalism",
        "Published": True,
        "Date Added": "2026-09-01",
        "Description": "Texte long interne",
        "Pinterest Title": "Titre Pinterest interne",
        "Price": "29,90 €",
    }
    base.update(fields)
    return {"id": "recuGeVeBVGl8ThDR", "createdTime": "2026-09-01T10:00:00.000Z", "fields": base}


# ══════════════════════════════════════════════════════════
# export_products
# ══════════════════════════════════════════════════════════

@test("1. Published record → exporté avec exactement les 6 clés publiques")
def _():
    p = normalize_record(rec()["fields"], TAG)
    assert p is not None
    assert tuple(sorted(p.keys())) == tuple(sorted(PUBLIC_KEYS)), p.keys()
    assert p["asin"] == "B09FQ9RL1X" and p["name"] == "Étagère flottante en bois massif"


@test("2. Record non publié → exclu")
def _():
    assert normalize_record(rec(Published=False)["fields"], TAG) is None
    assert normalize_record(rec(Published=None)["fields"], TAG) is None


@test("3. Sans ASIN extractible → exclu")
def _():
    f = rec(**{"Amazon URL": "https://www.amazon.fr/s?k=etagere", "Affiliate URL": ""})["fields"]
    assert normalize_record(f, TAG) is None


@test("4. affiliate_url toujours reconstruite au format officiel (URL Airtable ignorée)")
def _():
    f = rec(**{"Affiliate URL": "https://amzn.to/xyz?tag=autre-21"})["fields"]
    p = normalize_record(f, TAG)
    assert p and AFF_RE.match(p["affiliate_url"]), p and p["affiliate_url"]
    assert p["affiliate_url"] == "https://www.amazon.fr/dp/B09FQ9RL1X/ref=nosim?tag=unosnake09-21"


@test("5. ASIN pris dans l'URL affiliée si l'URL Amazon manque")
def _():
    f = rec(**{"Amazon URL": ""})["fields"]
    p = normalize_record(f, TAG)
    assert p and p["asin"] == "B09FQ9RL1X"


@test("6. image_url : https conservée, http/relative/injection → vide")
def _():
    assert normalize_record(rec()["fields"], TAG)["image_url"].startswith("https://")
    for bad in ("http://m.media-amazon.com/x.jpg", "/images/x.jpg", 'https://x.com/a.jpg" onerror="alert(1)', ""):
        assert normalize_record(rec(**{"Image URL": bad})["fields"], TAG)["image_url"] == "", bad


@test("7. Aucune fuite : description, prix, Pinterest, id de record absents de la sortie")
def _():
    out = render_json(build_products([rec()], TAG))
    for forbidden in ("Texte long interne", "Titre Pinterest interne", "29,90", "recuGeVeBVGl8ThDR", "Date Added", "Published"):
        assert forbidden not in out, forbidden


@test("8. Nom : espaces normalisés et longueur bornée")
def _():
    p = normalize_record(rec(**{"Product Name": "  Vase   en\n céramique  "})["fields"], TAG)
    assert p["name"] == "Vase en céramique"
    p2 = normalize_record(rec(**{"Product Name": "A" * 500})["fields"], TAG)
    assert len(p2["name"]) == MAX_NAME_LEN


@test("9. Tri : du plus récent au plus ancien (Date Added)")
def _():
    old = rec(**{"Date Added": "2026-08-01", "Amazon URL": "https://www.amazon.fr/dp/B0OLD00001", "Product Name": "Ancien"})
    new = rec(**{"Date Added": "2026-09-05", "Amazon URL": "https://www.amazon.fr/dp/B0NEW00001", "Product Name": "Récent"})
    names = [p["name"] for p in build_products([old, new], TAG)]
    assert names == ["Récent", "Ancien"], names


@test("10. Doublon d'ASIN → une seule carte")
def _():
    prods = build_products([rec(), rec(**{"Product Name": "Copie", "Date Added": "2026-08-01"})], TAG)
    assert len(prods) == 1 and prods[0]["name"] == "Étagère flottante en bois massif"


@test("11. render_json déterministe, clés triées, JSON valide, fin de ligne")
def _():
    a = render_json(build_products([rec()], TAG))
    b = render_json(build_products([rec()], TAG))
    assert a == b and a.endswith("\n")
    data = json.loads(a)
    assert list(data["products"][0].keys()) == sorted(PUBLIC_KEYS)


@test("12. export : écrit une fois, puis inchangé (idempotent)")
def _():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "products.json")
        changed, count = export([rec()], TAG, path)
        assert changed is True and count == 1
        changed2, count2 = export([rec()], TAG, path)
        assert changed2 is False and count2 == 1
        assert json.load(open(path, encoding="utf-8"))["products"][0]["asin"] == "B09FQ9RL1X"


@test("13. export sans produit → {\"products\": []}")
def _():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "products.json")
        export([rec(Published=False)], TAG, path)
        assert json.load(open(path, encoding="utf-8")) == {"products": []}


@test("14. Le token n'apparaît jamais dans la sortie")
def _():
    sentinel = "patFAKE1234567890.deadbeefdeadbeefdeadbeef"
    os.environ["AIRTABLE_TOKEN"] = sentinel
    try:
        out = render_json(build_products([rec()], TAG))
        assert sentinel not in out and "deadbeef" not in out
    finally:
        os.environ.pop("AIRTABLE_TOKEN", None)


# ══════════════════════════════════════════════════════════
# build.py
# ══════════════════════════════════════════════════════════

@test("15. build.load_products : filtre ASIN invalide et image non https")
def _():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "products.json")
        json.dump({"products": [
            {"name": "OK", "asin": "B09FQ9RL1X", "category": "Rangement", "style": "Scandinavian", "image_url": "http://x/y.jpg", "affiliate_url": ""},
            {"name": "Bad", "asin": "not-an-asin", "category": "", "style": "", "image_url": "", "affiliate_url": ""},
            {"name": "", "asin": "B0EMPTY000", "category": "", "style": "", "image_url": "", "affiliate_url": ""},
        ]}, open(path, "w", encoding="utf-8"))
        prods = build.load_products(path)
        assert len(prods) == 1 and prods[0]["asin"] == "B09FQ9RL1X"
        assert prods[0]["image_url"] == ""            # http rejeté
        assert prods[0]["style"] == "Scandinave"      # libellé FR
    assert build.load_products(os.path.join(d, "absent.json")) == []


@test("16. product_card : lien affilié officiel, rel sponsored, image distante décorative")
def _():
    p = {"asin": "B09FQ9RL1X", "name": "Étagère <test> & co", "cat": "Rangement", "style": "Japandi",
         "image_url": "https://m.media-amazon.com/images/I/71abc.jpg"}
    html = build.product_card(p)
    m = re.search(r'href="([^"]+)"', html)
    assert m and AFF_RE.match(m.group(1)), m and m.group(1)
    assert 'rel="sponsored nofollow noopener"' in html and 'target="_blank"' in html
    assert 'src="https://m.media-amazon.com/images/I/71abc.jpg"' in html and 'alt=""' in html
    assert 'referrerpolicy="no-referrer"' in html
    assert "Étagère &lt;test&gt; &amp; co" in html and "<test>" not in html   # échappement
    assert "nouvelle fenêtre" in html


@test("17. Produit sans photo → visuel neutre, jamais la photo d'un autre produit")
def _():
    html = build.product_card({"asin": "B09FQ9RL1X", "name": "Vase", "cat": "", "style": "", "image_url": ""})
    assert "product-media--empty" in html
    assert 'src="https://' not in html
    assert "prod-" not in html


@test("18. products_grid vide → état vide sans aucun lien Amazon")
def _():
    html = build.products_grid([])
    assert "empty-state" in html and "amazon.fr" not in html
    assert 'href="/styles.html"' in html and 'href="/journal.html"' in html


@test("19. products_grid non vide → grille de cartes, titres au niveau demandé")
def _():
    prods = [{"asin": "B09FQ9RL1X", "name": "A", "cat": "", "style": "", "image_url": ""},
             {"asin": "B0GZDK4KGL", "name": "B", "cat": "", "style": "", "image_url": ""}]
    html = build.products_grid(prods, hlevel=2)
    assert html.count('class="product-card') == 2 and "<h2" in html and "<h3" not in html
    assert "empty-state" not in html


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
