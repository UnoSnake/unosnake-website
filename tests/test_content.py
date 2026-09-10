#!/usr/bin/env python3
"""
UnoSnake — Tests Content Generator (25 tests).

Usage: python tests/test_content.py
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.content.generator import generate_content, _deterministic_index

_p = _f = 0
_e = []

def test(name):
    def decorator(func):
        global _p, _f
        try:
            func()
            _p += 1
            print(f"  ✅ {name}")
        except Exception as e:
            _f += 1
            _e.append((name, str(e)))
            print(f"  ❌ {name}: {e}")
        return func
    return decorator


# ── Test fixtures ──

FULL_CANDIDATE = {
    "title": "Étagère Murale Scandinave en Bois Naturel",
    "asin": "B0H6LW7X2K",
    "url": "https://www.amazon.fr/dp/B0H6LW7X2K",
    "snippet": "Étagère murale en bois naturel style nordique pour salon",
    "style_detected": "Scandinavian",
    "category_detected": "Mobilier",
    "niche_style": "Scandinavian",
    "niche_category": "Mobilier",
    "score": 82,
}

NO_STYLE = {
    "title": "Boîte de Rangement Élégante",
    "asin": "B0TESTNO01",
    "url": "https://www.amazon.fr/dp/B0TESTNO01",
    "snippet": "Rangement pratique pour la maison",
    "style_detected": "Unknown",
    "category_detected": "Rangement",
    "score": 68,
}

EMPTY_CANDIDATE = {
    "title": "",
    "asin": "",
    "url": "",
    "snippet": "",
    "style_detected": "",
    "category_detected": "",
    "score": 0,
}

SALON_CANDIDATE = {
    "title": "Lampe Design pour Salon Scandinave",
    "asin": "B0TESTSALON",
    "snippet": "Lampe de salon moderne style scandinave",
    "style_detected": "Scandinavian",
    "category_detected": "Éclairage",
    "score": 75,
}


# ═══════════════════════════════════════════════
print("\n✍️  PINTEREST TITLE")
# ═══════════════════════════════════════════════

@test("title generated for full candidate")
def _():
    c = generate_content(FULL_CANDIDATE)
    assert len(c["pinterest_title"]) > 0

@test("title length 20–100")
def _():
    c = generate_content(FULL_CANDIDATE)
    t = c["pinterest_title"]
    assert 20 <= len(t) <= 100, f"Length {len(t)}: {t}"

@test("title contains no hashtags")
def _():
    c = generate_content(FULL_CANDIDATE)
    assert "#" not in c["pinterest_title"]

@test("title mentions product")
def _():
    c = generate_content(FULL_CANDIDATE)
    # Some part of product name should appear
    assert "tagère" in c["pinterest_title"] or "Bois" in c["pinterest_title"] or "déco" in c["pinterest_title"].lower()

@test("title with style mentions scandinave")
def _():
    c = generate_content(FULL_CANDIDATE)
    assert "scandinave" in c["pinterest_title"].lower()

@test("title without style still works")
def _():
    c = generate_content(NO_STYLE)
    assert len(c["pinterest_title"]) >= 20
    assert "scandinave" not in c["pinterest_title"].lower()


# ═══════════════════════════════════════════════
print("\n📝 PINTEREST DESCRIPTION")
# ═══════════════════════════════════════════════

@test("description generated")
def _():
    c = generate_content(FULL_CANDIDATE)
    assert len(c["pinterest_description"]) > 0

@test("description length 80–300")
def _():
    c = generate_content(FULL_CANDIDATE)
    d = c["pinterest_description"]
    assert 80 <= len(d) <= 300, f"Length {len(d)}: {d}"

@test("description mentions UnoSnake or inspiration")
def _():
    c = generate_content(FULL_CANDIDATE)
    d = c["pinterest_description"].lower()
    assert "unosnake" in d or "inspir" in d or "décor" in d

@test("description without style still works")
def _():
    c = generate_content(NO_STYLE)
    assert len(c["pinterest_description"]) >= 80


# ═══════════════════════════════════════════════
print("\n🏷️  HASHTAGS")
# ═══════════════════════════════════════════════

@test("hashtags 5–10 count")
def _():
    c = generate_content(FULL_CANDIDATE)
    h = c["hashtags"]
    assert 5 <= len(h) <= 10, f"Got {len(h)} hashtags: {h}"

@test("all hashtags start with #")
def _():
    c = generate_content(FULL_CANDIDATE)
    for h in c["hashtags"]:
        assert h.startswith("#"), f"Bad hashtag: {h}"

@test("no duplicate hashtags")
def _():
    c = generate_content(FULL_CANDIDATE)
    lower = [h.lower() for h in c["hashtags"]]
    assert len(lower) == len(set(lower)), f"Duplicates in: {c['hashtags']}"

@test("no spaces in hashtags")
def _():
    c = generate_content(FULL_CANDIDATE)
    for h in c["hashtags"]:
        assert " " not in h, f"Space in hashtag: {h}"

@test("style hashtag present when style known")
def _():
    c = generate_content(FULL_CANDIDATE)
    lower = [h.lower() for h in c["hashtags"]]
    assert any("scandinave" in h or "nordic" in h for h in lower), f"No style tag in: {c['hashtags']}"

@test("hashtags generated without style")
def _():
    c = generate_content(NO_STYLE)
    assert 5 <= len(c["hashtags"]) <= 10

@test("hashtags generated with empty candidate")
def _():
    c = generate_content(EMPTY_CANDIDATE)
    assert len(c["hashtags"]) >= 5  # generics fill in


# ═══════════════════════════════════════════════
print("\n📄 EDITORIAL DESCRIPTION")
# ═══════════════════════════════════════════════

@test("editorial description generated")
def _():
    c = generate_content(FULL_CANDIDATE)
    assert len(c["description"]) > 0
    assert "UnoSnake" in c["description"]

@test("editorial description with empty inputs")
def _():
    c = generate_content(EMPTY_CANDIDATE)
    assert "UnoSnake" in c["description"]


# ═══════════════════════════════════════════════
print("\n🔁 STABILITY & VARIATION")
# ═══════════════════════════════════════════════

@test("same ASIN produces same content")
def _():
    c1 = generate_content(FULL_CANDIDATE)
    c2 = generate_content(FULL_CANDIDATE)
    assert c1["pinterest_title"] == c2["pinterest_title"]
    assert c1["pinterest_description"] == c2["pinterest_description"]
    assert c1["hashtags"] == c2["hashtags"]

@test("different ASINs produce different content")
def _():
    alt = dict(FULL_CANDIDATE, asin="B0DIFFERENT")
    c1 = generate_content(FULL_CANDIDATE)
    c2 = generate_content(alt)
    # At least title OR description should differ (different rotation)
    differs = (c1["pinterest_title"] != c2["pinterest_title"]) or \
              (c1["pinterest_description"] != c2["pinterest_description"])
    assert differs, "Identical content for different ASINs"

@test("deterministic index varies per ASIN")
def _():
    i1 = _deterministic_index("B0H6LW7X2K")
    i2 = _deterministic_index("B0DIFFERENT")
    i3 = _deterministic_index("B0ANOTHER99")
    assert len({i1, i2, i3}) == 3, "Collisions"


# ═══════════════════════════════════════════════
print("\n🛡️  EDGE CASES")
# ═══════════════════════════════════════════════

@test("empty title still generates content")
def _():
    c = generate_content(EMPTY_CANDIDATE)
    assert len(c["pinterest_title"]) > 0
    assert len(c["pinterest_description"]) > 0

@test("room detection in salon candidate")
def _():
    c = generate_content(SALON_CANDIDATE)
    meta = c["content_metadata"]
    assert "salon" in meta["room_detected"].lower(), f"Room: {meta['room_detected']}"


# ═══════════════════════════════════════════════
print(f"\n{'=' * 55}")
total = _p + _f
if _f == 0:
    print(f"✅ ALL {total} CONTENT TESTS PASSED")
else:
    print(f"❌ {_f}/{total} FAILED:")
    for n, e in _e:
        print(f"   - {n}: {e}")
print(f"{'=' * 55}")
sys.exit(0 if _f == 0 else 1)
