"""
UnoSnake — Remplacement des visuels placeholder par de vraies photos (Pexels).

Pourquoi ce script : la recherche Unsplash/Pexels est bloquée sans clé API (pages 401/403),
mais l'API Pexels est gratuite. Ce script conserve EXACTEMENT les noms, ratios et dimensions
attendus par build.py / style.css, écrit WebP + JPG et un fichier de crédits.

Usage :
    set PEXELS_API_KEY=...                    (clé lue depuis l'environnement, jamais dans le code)
    python scripts/site/fetch_photos.py --list hero          # voir 10 candidats (id, dimensions, auteur, alt)
    python scripts/site/fetch_photos.py --dry-run             # vérifier les choix sans écrire
    python scripts/site/fetch_photos.py                       # télécharger + recadrer + écrire assets/img/*
    python scripts/site/fetch_photos.py --pick hero=1571460   # imposer une photo précise pour un visuel

Licence : toutes les photos Pexels sont sous licence Pexels (usage commercial libre, attribution
non requise) — https://www.pexels.com/license/ . Les crédits sont écrits dans assets/img/CREDITS.md.
"""
import argparse, io, json, os, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
IMG_DIR = os.path.join(ROOT, "assets", "img")
API = "https://api.pexels.com/v1/search"

# nom de fichier -> (largeur, hauteur, requête, orientation Pexels)
SPECS = {
    "hero":             (1000, 1250, "scandinavian living room warm minimal", "portrait"),
    "style-scandinave": (900,  600,  "scandinavian interior light wood",     "landscape"),
    "style-japandi":    (900,  600,  "japandi interior neutral",             "landscape"),
    "style-warm":       (900,  600,  "warm minimalist interior beige",       "landscape"),
    "style-boheme":     (900,  600,  "boho interior rattan natural",         "landscape"),
    "prod-etagere":     (800,  1000, "wooden wall shelf minimalist decor",   "portrait"),
    "prod-lampe":       (800,  1000, "table lamp wood linen minimalist",     "portrait"),
    "prod-vase":        (800,  1000, "ceramic vase beige minimalist",        "portrait"),
    "prod-panier":      (800,  1000, "rattan basket natural interior",       "portrait"),
    "prod-miroir":      (800,  1000, "round mirror wood wall minimalist",    "portrait"),
    "prod-coussin":     (800,  1000, "linen cushion beige natural",          "portrait"),
    "art-japandi":      (1000, 625,  "japandi living room calm wood",        "landscape"),
    "art-lampe":        (1000, 625,  "cozy lamp light scandinavian interior evening", "landscape"),
    "art-chaleur":      (1000, 625,  "warm cozy interior textures wood linen candle", "landscape"),
    "art-hero-japandi": (1400, 600,  "japandi interior wide wood neutral",   "landscape"),
    # Visuels des articles du Journal (série 2)
    "art-bois-scandinave":     (1000, 625, "scandinavian interior oak wood furniture light", "landscape"),
    "art-coin-lecture":        (1000, 625, "reading nook armchair lamp blanket cozy corner", "landscape"),
    "art-rangement-japandi":   (1000, 625, "japandi shelves storage minimal ceramics wood",  "landscape"),
    "art-rotin":               (1000, 625, "rattan armchair boho living room plants",       "landscape"),
    "art-lumiere-equilibre":   (1000, 625, "living room large window natural light curtains linen", "landscape"),
    "art-erreurs-minimalisme": (1000, 625, "minimalist living room beige sofa warm",        "landscape"),
}

SHEET_DIR = os.path.join(os.environ.get("TEMP") or os.environ.get("TMPDIR") or "/tmp", "unosnake_photo_sheets")


def fit_cover(size, target):
    """Boîte de recadrage centrée (l, t, r, b) couvrant `target` (w, h) depuis une image `size` (w, h),
    sans déformation : même logique que CSS object-fit: cover."""
    sw, sh = size
    tw, th = target
    scale = max(tw / sw, th / sh)
    cw, ch = tw / scale, th / scale
    left = (sw - cw) / 2
    top = (sh - ch) / 2
    return (round(left), round(top), round(left + cw), round(top + ch))


def _api(url, key):
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "unosnake-site/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "unosnake-site/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def search(key, query, orientation, per_page=10):
    q = urllib.parse.urlencode({"query": query, "orientation": orientation, "per_page": per_page, "size": "large"})
    return _api(f"{API}?{q}", key).get("photos", [])


def photo_by_id(key, photo_id):
    """Métadonnées d'une photo précise (pour --pick avec un id absent des premiers résultats)."""
    return _api(f"https://api.pexels.com/v1/photos/{photo_id}", key)


def choose(photos, target, pick_id=None, key=None):
    """Première photo assez grande (aucun agrandissement) ; ou celle imposée par --pick."""
    tw, th = target
    if pick_id is not None:
        match = next((p for p in photos if p["id"] == pick_id), None)
        if match is None and key:
            try:
                match = photo_by_id(key, pick_id)
            except Exception:
                match = None
        return match if match and match["width"] >= tw and match["height"] >= th else None
    for p in photos:
        if p["width"] >= tw and p["height"] >= th:
            return p
    return None


def source_url(photo, target):
    """URL CDN de l'original redimensionné à ~2x la cible (qualité) au lieu du fichier brut (souvent > 20 Mo)."""
    tw, th = target
    scale = max(tw / photo["width"], th / photo["height"])
    want_w = min(photo["width"], int(photo["width"] * scale * 2))
    return f"{photo['src']['original']}?auto=compress&cs=tinysrgb&w={want_w}"


def process(name, photo, target, dry_run=False):
    from PIL import Image  # import local : Pillow n'est requis que pour l'écriture
    try:
        raw = _download(source_url(photo, target))
    except Exception:
        raw = _download(photo["src"]["original"])
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    if im.width < target[0] or im.height < target[1]:
        raw = _download(photo["src"]["original"])
        im = Image.open(io.BytesIO(raw)).convert("RGB")
    im = im.crop(fit_cover(im.size, target)).resize(target, Image.LANCZOS)
    if dry_run:
        return
    im.save(os.path.join(IMG_DIR, f"{name}.jpg"), "JPEG", quality=82, optimize=True, progressive=True)
    im.save(os.path.join(IMG_DIR, f"{name}.webp"), "WEBP", quality=80, method=6)


def contact_sheet(key, names, per_page=8):
    """Planche contact (hors dépôt, dans %TEMP%) : jusqu'à `per_page` candidats par visuel, recadrés au ratio cible,
    avec id / dimensions / auteur — pour choisir à l'œil puis imposer via --pick."""
    from PIL import Image, ImageDraw
    os.makedirs(SHEET_DIR, exist_ok=True)
    cell_w, pad, label_h = 240, 8, 30
    rows = []
    for name in names:
        w, h, query, orient = SPECS[name]
        photos = [p for p in search(key, query, orient, per_page=per_page + 4) if p["width"] >= w and p["height"] >= h][:per_page]
        thumbs = []
        for p in photos:
            try:
                im = Image.open(io.BytesIO(_download(p["src"]["medium"]))).convert("RGB")
                im = im.crop(fit_cover(im.size, (w, h)))
                im = im.resize((cell_w, round(cell_w * h / w)), Image.LANCZOS)
            except Exception:
                im = Image.new("RGB", (cell_w, round(cell_w * h / w)), "#cccccc")
            thumbs.append((p, im))
        rows.append((name, thumbs))
    cell_h = max((t.height for _, th in rows for _, t in th), default=160) + label_h
    sheet = Image.new("RGB", (pad + per_page * (cell_w + pad), pad + len(rows) * (cell_h + 26 + pad)), "#FAF6EF")
    d = ImageDraw.Draw(sheet)
    y = pad
    for name, thumbs in rows:
        d.text((pad, y), f"{name}  —  {SPECS[name][2]}", fill="#2B291F")
        y += 20
        for i, (p, im) in enumerate(thumbs):
            x = pad + i * (cell_w + pad)
            sheet.paste(im, (x, y))
            d.text((x, y + im.height + 2), f"#{i+1} id={p['id']}", fill="#2B291F")
            d.text((x, y + im.height + 15), (p["photographer"] or "")[:30], fill="#5F5947")
        y += cell_h + 6 + pad
    out = os.path.join(SHEET_DIR, "_".join(names)[:80] + ".png")
    sheet.save(out)
    return out


def write_credits(rows):
    lines = ["# Crédits photos", "",
             "Photos issues de [Pexels](https://www.pexels.com) — [licence Pexels](https://www.pexels.com/license/)",
             "(usage commercial libre, modification autorisée, attribution non requise mais fournie ici).", "",
             "| Fichier | Photographe | Photo |", "|---|---|---|"]
    for name, p in rows:
        lines.append(f"| `{name}.jpg` / `{name}.webp` | [{p['photographer']}]({p['photographer_url']}) | {p['url']} |")
    with open(os.path.join(IMG_DIR, "CREDITS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", metavar="NAME", help="afficher les candidats pour un visuel et quitter")
    ap.add_argument("--sheet", action="append", default=[], metavar="NAME", help="planche contact PNG (dans %%TEMP%%) pour ces visuels, puis quitter")
    ap.add_argument("--pick", action="append", default=[], metavar="NAME=ID", help="imposer une photo Pexels")
    ap.add_argument("--only", action="append", default=[], metavar="NAME", help="ne traiter que ces visuels")
    ap.add_argument("--dry-run", action="store_true", help="tout faire sauf écrire les fichiers")
    args = ap.parse_args(argv)

    key = os.getenv("PEXELS_API_KEY", "")
    if not key:
        print("PEXELS_API_KEY manquante (variable d'environnement). Clé gratuite : https://www.pexels.com/api/")
        return 2

    picks = {}
    for item in args.pick:
        n, _, i = item.partition("=")
        if n not in SPECS or not i.isdigit():
            print(f"--pick invalide : {item}"); return 2
        picks[n] = int(i)

    if args.sheet:
        names = list(SPECS) if args.sheet == ["all"] else args.sheet
        bad = [n for n in names if n not in SPECS]
        if bad:
            print("visuels inconnus :", ", ".join(bad)); return 2
        for i in range(0, len(names), 3):
            print("  ✓", contact_sheet(key, names[i:i + 3]))
        return 0

    if args.list:
        w, h, query, orient = SPECS[args.list]
        for p in search(key, query, orient):
            ok = "ok " if p["width"] >= w and p["height"] >= h else "小 "
            print(f"{ok}{p['id']:>9} {p['width']}x{p['height']} {p['photographer'][:24]:24} {p.get('alt','')[:70]}")
        return 0

    names = args.only or list(SPECS)
    credits, failed = [], []
    for name in names:
        w, h, query, orient = SPECS[name]
        photos = search(key, query, orient)
        photo = choose(photos, (w, h), picks.get(name), key)
        if not photo:
            failed.append(name); print(f"  ✗ {name}: aucun candidat assez grand ({w}x{h})"); continue
        process(name, photo, (w, h), dry_run=args.dry_run)
        credits.append((name, photo))
        print(f"  ✓ {name}: #{photo['id']} par {photo['photographer']} → {w}x{h}{' (dry-run)' if args.dry_run else ''}")
    if credits and not args.dry_run:
        write_credits(credits)
        print("  ✓ assets/img/CREDITS.md")
    if failed:
        print("Échecs :", ", ".join(failed)); return 1
    print("Pensez à relancer `python build.py` (les URLs versionnées changent avec le contenu).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
