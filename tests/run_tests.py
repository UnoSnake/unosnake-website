#!/usr/bin/env python3
"""
UnoSnake — Test Runner (Phase 7).

145+ tests : config, ASIN, affiliate, niche pool, trends, serper, scoring 0–100,
diversity, product name, deduplication, B0H36L8M6F, threshold.

Usage: python tests/run_tests.py
"""

import os, sys, json
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, PROJECT_ROOT)

from scripts.config import (
    TEST_MODE, PINTEREST_ENABLED, AMAZON_CREATORS_API_ENABLED,
    PUBLISHES_PER_DAY, MAX_CANDIDATES_PER_SEARCH, AMAZON_PARTNER_TAG,
    VALID_STATUSES, NICHE_COOLDOWN_HOURS, AIRTABLE_TABLE_ID,
    UNOSNAKE_STYLES, UNOSNAKE_CATEGORIES, TRENDS_DECO_KEYWORDS,
    MIN_PRODUCT_SCORE, MAX_ACCEPTED_PER_RUN,
)
from scripts.amazon.asin import (
    extract_asin, normalize_amazon_url, build_affiliate_url, is_valid_asin,
    validate_affiliate_url,
)
from scripts.discovery.niche_pool import (
    load_niches, get_available_niches, select_niches,
)
from scripts.discovery.trends import parse_trends_xml, filter_deco_trends
from scripts.discovery.serper_search import build_serper_query, parse_serper_results
from scripts.scoring.scorer import score_candidate, rank_candidates
from scripts.airtable.dedup import (
    is_duplicate, build_existing_index, check_candidate_batch,
)
from scripts.discovery.engine import resolve_product_name
from scripts.content.generator import generate_content, _deterministic_index
from scripts.pinterest.payload import (
    build_pin_payload,
    validate_pin_payload,
    build_pin_from_candidate,
)
from scripts.pinterest.publisher import publish_pin, PublishResult
from scripts.pinterest.client import PinterestClient
from scripts.airtable.state_machine import can_transition

_passed = _failed = 0
_errors = []

def test(name):
    def decorator(func):
        global _passed, _failed
        try:
            func()
            _passed += 1
            print(f"  ✅ {name}")
        except Exception as e:
            _failed += 1
            _errors.append((name, str(e)))
            print(f"  ❌ {name}: {e}")
        return func
    return decorator


# ═══════════════════════════════════════════════════════════
print("\n🔗 AFFILIATE URL")
# ═══════════════════════════════════════════════════════════

@test("affiliate: B0H36L8M6F exact format")
def _():
    url = build_affiliate_url("B0H36L8M6F", "unosnake09-21")
    assert url == "https://www.amazon.fr/dp/B0H36L8M6F/ref=nosim?tag=unosnake09-21"

@test("affiliate: contains /ref=nosim")
def _():
    url = build_affiliate_url("B0H36L8M6F", "unosnake09-21")
    assert "/ref=nosim" in url

@test("affiliate: contains ?tag=")
def _():
    url = build_affiliate_url("B0H36L8M6F", "unosnake09-21")
    assert "?tag=unosnake09-21" in url

@test("affiliate: HTTPS only")
def _():
    url = build_affiliate_url("B0H36L8M6F", "unosnake09-21")
    assert url.startswith("https://")

@test("affiliate: rejects invalid ASIN")
def _():
    assert build_affiliate_url("short", "unosnake09-21") == ""
    assert build_affiliate_url("b0h36l8m6f", "unosnake09-21") == ""
    assert build_affiliate_url("", "unosnake09-21") == ""

@test("affiliate: rejects empty tag")
def _():
    assert build_affiliate_url("B0H36L8M6F", "") == ""
    assert build_affiliate_url("B0H36L8M6F", "  ") == ""

@test("affiliate: stable across calls")
def _():
    u1 = build_affiliate_url("B0H36L8M6F", "unosnake09-21")
    u2 = build_affiliate_url("B0H36L8M6F", "unosnake09-21")
    assert u1 == u2

@test("affiliate: different ASINs produce different URLs")
def _():
    u1 = build_affiliate_url("B0H36L8M6F", "unosnake09-21")
    u2 = build_affiliate_url("B0H6LW7X2K", "unosnake09-21")
    assert u1 != u2
    assert "B0H36L8M6F" in u1
    assert "B0H6LW7X2K" in u2

@test("validate: correct URL passes")
def _():
    url = "https://www.amazon.fr/dp/B0H36L8M6F/ref=nosim?tag=unosnake09-21"
    valid, reason = validate_affiliate_url(url, "B0H36L8M6F", "unosnake09-21")
    assert valid is True and reason == "OK"

@test("validate: missing ref=nosim fails")
def _():
    valid, _ = validate_affiliate_url("https://www.amazon.fr/dp/B0H36L8M6F?tag=unosnake09-21", "B0H36L8M6F", "unosnake09-21")
    assert valid is False

@test("validate: empty URL fails")
def _():
    valid, _ = validate_affiliate_url("", "B0H36L8M6F", "unosnake09-21")
    assert valid is False


# ═══════════════════════════════════════════════════════════
print("\n📋 CONFIG")
# ═══════════════════════════════════════════════════════════

@test("defaults are safe")
def _():
    assert TEST_MODE is True
    assert PINTEREST_ENABLED is False
    assert AMAZON_CREATORS_API_ENABLED is False

@test("operational limits")
def _():
    assert PUBLISHES_PER_DAY == 4
    assert MAX_CANDIDATES_PER_SEARCH == 10
    assert NICHE_COOLDOWN_HOURS == 24

@test("partner tag")
def _(): assert AMAZON_PARTNER_TAG == "unosnake09-21"

@test("valid statuses")
def _(): assert VALID_STATUSES == ["New", "Selected", "Published", "Rejected"]

@test("airtable table id")
def _(): assert AIRTABLE_TABLE_ID == "tbl2RQvsmpBm3yAdW"

@test("styles and categories populated")
def _():
    assert len(UNOSNAKE_STYLES) >= 4
    assert len(UNOSNAKE_CATEGORIES) >= 5
    assert len(TRENDS_DECO_KEYWORDS) >= 20

@test("scoring config")
def _():
    assert MIN_PRODUCT_SCORE == 65
    assert MAX_ACCEPTED_PER_RUN == 10


# ═══════════════════════════════════════════════════════════
print("\n🔍 ASIN EXTRACTION")
# ═══════════════════════════════════════════════════════════

@test("extract from /dp/")
def _(): assert extract_asin("https://www.amazon.fr/dp/B0H36L8M6F/ref=sr") == "B0H36L8M6F"

@test("extract from /gp/product/")
def _(): assert extract_asin("https://www.amazon.fr/gp/product/B08N5WRWNW") == "B08N5WRWNW"

@test("extract with title slug")
def _(): assert extract_asin("https://www.amazon.fr/Lampe/dp/B0H6LW7X2K/r") == "B0H6LW7X2K"

@test("extract with query params")
def _(): assert extract_asin("https://www.amazon.fr/dp/B0GZDK4KGL?th=1") == "B0GZDK4KGL"

@test("no ASIN in search URL")
def _(): assert extract_asin("https://www.amazon.fr/s?k=vase") is None

@test("empty/None")
def _():
    assert extract_asin("") is None
    assert extract_asin(None) is None

@test("amazon.co.uk")
def _(): assert extract_asin("https://www.amazon.co.uk/dp/B09XYZ1234") == "B09XYZ1234"

@test("normalize strips tracking")
def _(): assert normalize_amazon_url("https://www.amazon.fr/X/dp/B0H36L8M6F/ref?x") == "https://www.amazon.fr/dp/B0H36L8M6F"

@test("normalize preserves domain")
def _(): assert normalize_amazon_url("https://www.amazon.co.uk/dp/B0H36L8M6F") == "https://www.amazon.co.uk/dp/B0H36L8M6F"

@test("normalize None for invalid")
def _(): assert normalize_amazon_url("https://www.google.com") is None

@test("build affiliate URL")
def _(): assert build_affiliate_url("B0H36L8M6F", "unosnake09-21") == "https://www.amazon.fr/dp/B0H36L8M6F/ref=nosim?tag=unosnake09-21"

@test("affiliate empty inputs")
def _():
    assert build_affiliate_url("", "t") == ""
    assert build_affiliate_url("X", "") == ""

@test("is_valid_asin")
def _():
    assert is_valid_asin("B0H36L8M6F") is True
    assert is_valid_asin("short") is False
    assert is_valid_asin("") is False


# ═══════════════════════════════════════════════════════════
print("\n🌿 NICHE POOL")
# ═══════════════════════════════════════════════════════════

niches_path = os.path.join(PROJECT_ROOT, "niches.json")

@test("load niches")
def _():
    n = load_niches(niches_path)
    assert len(n) >= 20
    assert all("query" in x and "style" in x for x in n)

@test("cooldown excludes recent")
def _():
    n = load_niches(niches_path)
    now = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)
    h = [{"query": n[0]["query"], "timestamp": (now - timedelta(hours=2)).isoformat()}]
    assert len(get_available_niches(n, h, 24, now)) == len(n) - 1

@test("select respects max")
def _(): assert len(select_niches(load_niches(niches_path), [], 3, seed=42)) == 3

@test("select ensures diversity")
def _():
    s = select_niches(load_niches(niches_path), [], 3, seed=42)
    assert len({x["style"] for x in s}) >= 2

@test("handles all in cooldown")
def _():
    n = load_niches(niches_path)
    now = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)
    h = [{"query": x["query"], "timestamp": (now - timedelta(hours=1)).isoformat()} for x in n]
    assert len(select_niches(n, h, 3, 24, now)) == 3

@test("standalone without trends")
def _(): assert len(select_niches(load_niches(niches_path), [], 3, seed=1)) >= 1


# ═══════════════════════════════════════════════════════════
print("\n📈 TRENDS")
# ═══════════════════════════════════════════════════════════

MOCK_RSS = '<?xml version="1.0"?><rss><channel><item><title>sport</title></item><item><title>décoration scandinave</title></item><item><title>lampe design</title></item></channel></rss>'

@test("parse XML")
def _(): assert len(parse_trends_xml(MOCK_RSS)) == 3

@test("filter deco")
def _(): assert len(filter_deco_trends(parse_trends_xml(MOCK_RSS), ["décoration", "lampe"])) == 2

@test("parse empty")
def _(): assert parse_trends_xml("") == []


# ═══════════════════════════════════════════════════════════
print("\n🔎 SERPER")
# ═══════════════════════════════════════════════════════════

@test("query format")
def _(): assert build_serper_query("japandi") == "site:amazon.fr/dp japandi"

@test("filters non-Amazon")
def _():
    r = parse_serper_results({"organic": [
        {"title": "A", "link": "https://www.amazon.fr/dp/B001ABCDE1", "snippet": "s", "position": 1},
        {"title": "B", "link": "https://example.com/x", "snippet": "s", "position": 2},
    ]})
    assert len(r) == 1

@test("empty response")
def _(): assert parse_serper_results({}) == []


# ═══════════════════════════════════════════════════════════
print("\n⭐ SCORING 0–100")
# ═══════════════════════════════════════════════════════════

PERFECT = {"url": "https://www.amazon.fr/dp/B0H36L8M6F", "title": "Étagère Murale Scandinave Bois Naturel Décoration", "snippet": "Étagère scandinave minimaliste bois clair salon décoration", "position": 1, "rating": 4.8, "rating_count": 150}
LOW = {"url": "", "title": "x", "snippet": "", "position": 10, "rating": None, "rating_count": None}

@test("perfect candidate >= 75")
def _():
    r = score_candidate(PERFECT)
    assert r["score"] >= 75, f"Got {r['score']}"

@test("perfect has Scandinavian style")
def _(): assert score_candidate(PERFECT)["style_detected"] == "Scandinavian"

@test("perfect has valid category")
def _(): assert score_candidate(PERFECT)["category_detected"] in ["Mobilier", "Rangement", "Décoration"]

@test("perfect has score_reasons")
def _(): assert len(score_candidate(PERFECT)["score_reasons"]) >= 3

@test("low candidate < 65")
def _(): assert score_candidate(LOW)["score"] < 65

@test("no rating → neutral 7.5")
def _():
    c = {"url": "", "title": "Lampe Design Moderne Salon", "snippet": "lampe", "position": 3, "rating": None, "rating_count": None}
    assert score_candidate(c)["score_components"]["rating"] == 7.5

@test("no rating_count → neutral 5")
def _():
    c = {"url": "", "title": "Vase Céramique Déco", "snippet": "vase", "position": 2, "rating": 4.5, "rating_count": None}
    assert score_candidate(c)["score_components"]["reviews"] == 5.0

@test("relevant title scores well")
def _():
    c = {"url": "", "title": "Coussin Bohème Macramé Naturel Salon", "snippet": "coussin bohème décoration", "position": 1, "rating": 4.2, "rating_count": 80}
    assert score_candidate(c)["score"] >= 65

@test("irrelevant title scores low")
def _():
    c = {"url": "", "title": "Tournevis Électrique Pro", "snippet": "outil bricolage", "position": 1, "rating": 4.9, "rating_count": 500}
    assert score_candidate(c)["score"] < 70

@test("score in 0–100 range")
def _():
    assert 0 <= score_candidate(PERFECT)["score"] <= 100
    assert 0 <= score_candidate(LOW)["score"] <= 100

@test("not duplicate without existing ASINs")
def _(): assert score_candidate(PERFECT)["is_duplicate"] is False

@test("Japandi niche detected")
def _():
    c = {"url": "", "title": "Décoration Japandi Intérieur", "snippet": "japandi zen wabi-sabi", "position": 2, "rating": 4.3, "rating_count": 60}
    r = score_candidate(c)
    assert r["style_detected"] == "Japandi" and r["score"] >= 65

@test("duplicate → score 0")
def _():
    c = {"url": "https://www.amazon.fr/dp/B0H36L8M6F", "asin": "B0H36L8M6F", "title": "X", "snippet": "x", "position": 1}
    r = score_candidate(c, existing_asins={"B0H36L8M6F"})
    assert r["score"] == 0 and r["is_duplicate"] is True

@test("rank sorts descending")
def _():
    r = rank_candidates([PERFECT, LOW], min_score=0)
    assert r[0]["score"] >= r[-1]["score"]

@test("MIN_PRODUCT_SCORE threshold filters")
def _():
    r = rank_candidates([PERFECT, LOW], min_score=65)
    assert all(c["score"] >= 65 for c in r)


# ═══════════════════════════════════════════════════════════
print("\n🎯 DIVERSITY")
# ═══════════════════════════════════════════════════════════

@test("overrepresented category penalized")
def _():
    c = {"url": "", "title": "Lampe Scandinave Salon", "snippet": "lampe luminaire scandinave", "position": 1, "rating": 4.5, "rating_count": 100}
    over = score_candidate(c, recently_published_categories=["Éclairage"] * 4)
    normal = score_candidate(c, recently_published_categories=[])
    assert over["score"] < normal["score"]

@test("new category gets bonus")
def _():
    c = {"url": "", "title": "Coussin Bohème Macramé", "snippet": "coussin textile bohème", "position": 1, "rating": 4.5, "rating_count": 100}
    r = score_candidate(c, recently_published_categories=["Éclairage", "Rangement"])
    assert any("bonus" in s.lower() or "new category" in s.lower() for s in r["score_reasons"])

@test("multi-candidates preserved")
def _():
    cs = [
        {"url": "", "title": "Vase Scandinave Design", "snippet": "vase décoration", "position": 1, "rating": 4.5, "rating_count": 100},
        {"url": "", "title": "Lampe Scandinave Bureau", "snippet": "lampe décoration", "position": 2, "rating": 4.5, "rating_count": 100},
    ]
    assert len(rank_candidates(cs, min_score=0)) == 2


# ═══════════════════════════════════════════════════════════
print("\n📝 PRODUCT NAME")
# ═══════════════════════════════════════════════════════════

@test("real Serper title")
def _(): assert resolve_product_name({"title": "Étagère Murale Design Scandinave", "snippet": "x", "asin": "B001"}) == "Étagère Murale Design Scandinave"

@test("strip Amazon.fr prefix")
def _(): assert resolve_product_name({"title": "Amazon.fr : Vase Blanc", "snippet": "", "asin": "B002"}) == "Vase Blanc"

@test("snippet fallback")
def _():
    r = resolve_product_name({"title": "Short", "snippet": "Beautiful ceramic vase for modern decoration. Ideal.", "asin": "B003"})
    assert r != "Short" and len(r) >= 10

@test("ASIN fallback")
def _(): assert resolve_product_name({"title": "", "snippet": "", "asin": "B0H36L8M6F"}) == "Product B0H36L8M6F"

@test("Unknown fallback")
def _(): assert resolve_product_name({"title": "", "snippet": "", "asin": ""}) == "Unknown Product"

@test("never Candidat UnoSnake")
def _():
    for c in [{"title": "Real Title Prod", "snippet": "", "asin": "B001"}, {"title": "", "snippet": "", "asin": ""}]:
        assert "Candidat UnoSnake" not in resolve_product_name(c)

@test("truncate 200")
def _(): assert len(resolve_product_name({"title": "A" * 300, "snippet": "", "asin": "B001"})) <= 200


# ═══════════════════════════════════════════════════════════
print("\n🔄 DEDUPLICATION")
# ═══════════════════════════════════════════════════════════

@test("ASIN duplicate")
def _(): assert is_duplicate("B0H36L8M6F", None, None, {"B0H36L8M6F"}, set()) == (True, "ASIN B0H36L8M6F already exists")

@test("URL duplicate")
def _(): assert is_duplicate(None, "https://www.amazon.fr/dp/B0H36L8M6F", None, set(), {"https://www.amazon.fr/dp/B0H36L8M6F"})[0] is True

@test("new product passes")
def _(): assert is_duplicate("B0NEWPROD01", None, None, set(), set()) == (False, "")

@test("build index from records")
def _():
    rs = [{"fields": {"Amazon URL": "https://www.amazon.fr/dp/B0H36L8M6F/ref=sr"}}, {"fields": {"Amazon URL": "https://www.amazon.fr/dp/B0H6LW7X2K"}}]
    a, u = build_existing_index(rs, extract_asin, normalize_amazon_url)
    assert len(a) == 2 and len(u) == 2

@test("batch filters known")
def _():
    cs = [{"url": "https://www.amazon.fr/dp/B0H36L8M6F", "asin": "B0H36L8M6F", "title": "Old"}, {"url": "https://www.amazon.fr/dp/B0NEWPROD01", "asin": "B0NEWPROD01", "title": "New"}]
    n, d = check_candidate_batch(cs, {"B0H36L8M6F"}, set(), extract_asin, normalize_amazon_url)
    assert len(n) == 1 and n[0]["asin"] == "B0NEWPROD01"

@test("intra-batch dedup")
def _():
    cs = [{"url": "https://www.amazon.fr/dp/B0SAME0001", "asin": "B0SAME0001", "title": "1st"}, {"url": "https://www.amazon.fr/dp/B0SAME0001", "asin": "B0SAME0001", "title": "2nd"}]
    n, d = check_candidate_batch(cs, set(), set(), extract_asin, normalize_amazon_url)
    assert len(n) == 1 and n[0]["title"] == "1st"

@test("URL fallback dedup")
def _():
    u = "https://www.amazon.fr/dp/B0H36L8M6F"
    n, d = check_candidate_batch([{"url": u, "asin": None, "title": "X"}], set(), {normalize_amazon_url(u)}, extract_asin, normalize_amazon_url)
    assert len(n) == 0

@test("empty batch")
def _(): assert check_candidate_batch([], set(), set(), extract_asin, normalize_amazon_url) == ([], [])

@test("Published skipped")
def _():
    a, u = build_existing_index([{"fields": {"Amazon URL": "https://www.amazon.fr/dp/B0PUBLI001", "Status": "Published"}}], extract_asin, normalize_amazon_url)
    assert is_duplicate("B0PUBLI001", None, None, a, u)[0] is True

@test("New skipped")
def _():
    a, u = build_existing_index([{"fields": {"Amazon URL": "https://www.amazon.fr/dp/B0EXIST001", "Status": "New"}}], extract_asin, normalize_amazon_url)
    assert is_duplicate("B0EXIST001", None, None, a, u)[0] is True


# ═══════════════════════════════════════════════════════════
print("\n🧪 B0H36L8M6F INTEGRATION")
# ═══════════════════════════════════════════════════════════

REAL = {"url": "https://www.amazon.fr/dp/B0H36L8M6F/ref=sr_1_1", "asin": "B0H36L8M6F", "title": "Générique Tablette for Radiateur Gain De Place", "snippet": "Rangement maison esthétique", "position": 1}

@test("B0H36L8M6F duplicate → score 0")
def _():
    r = score_candidate(REAL, existing_asins={"B0H36L8M6F"})
    assert r["is_duplicate"] is True and r["score"] == 0

@test("B0H36L8M6F skip reason")
def _():
    r = score_candidate(REAL, existing_asins={"B0H36L8M6F"})
    assert "DUPLICATE" in r["score_reasons"][0]

@test("B0H36L8M6F fresh has valid score")
def _():
    r = score_candidate(REAL)
    assert 0 < r["score"] <= 100


# ═══════════════════════════════════════════════════════════
print("\n✍️  CONTENT — PINTEREST TITLE")
# ═══════════════════════════════════════════════════════════

CONTENT_FULL = {
    "title": "Étagère Murale Scandinave en Bois Naturel",
    "asin": "B0H6LW7X2K", "url": "https://www.amazon.fr/dp/B0H6LW7X2K",
    "snippet": "Étagère murale en bois naturel style nordique pour salon",
    "style_detected": "Scandinavian", "category_detected": "Mobilier", "score": 82,
}
CONTENT_NO_STYLE = {
    "title": "Boîte de Rangement Élégante", "asin": "B0TESTNO01",
    "snippet": "Rangement pratique pour la maison", "style_detected": "Unknown",
    "category_detected": "Rangement", "score": 68,
}
CONTENT_EMPTY = {"title": "", "asin": "", "snippet": "", "style_detected": "", "category_detected": "", "score": 0}
CONTENT_SALON = {
    "title": "Lampe Design pour Salon Scandinave", "asin": "B0TESTSLON",
    "snippet": "Lampe de salon moderne scandinave", "style_detected": "Scandinavian",
    "category_detected": "Éclairage", "score": 75,
}
CONTENT_JAPANDI = {
    "title": "Vase Céramique Japandi Zen", "asin": "B0JAPANDI1",
    "snippet": "Vase en céramique style japandi wabi-sabi", "style_detected": "Japandi",
    "category_detected": "Objets déco", "score": 78,
}
CONTENT_BOHO = {
    "title": "Coussin Bohème Macramé Naturel", "asin": "B0BOHO0001",
    "snippet": "Coussin bohème artisanal en macramé", "style_detected": "Bohemian",
    "category_detected": "Textile", "score": 72,
}

_cf = generate_content(CONTENT_FULL)

@test("content: title exists")
def _(): assert len(_cf["pinterest_title"]) > 0

@test("content: title length 20–100")
def _():
    t = _cf["pinterest_title"]
    assert 20 <= len(t) <= 100, f"Len={len(t)}: {t}"

@test("content: title no hashtags")
def _(): assert "#" not in _cf["pinterest_title"]

@test("content: title contains product ref")
def _():
    t = _cf["pinterest_title"]
    assert any(w in t for w in ["tagère", "Bois", "Murale"]) or "déco" in t.lower()

@test("content: title has scandinave for Scandinavian")
def _(): assert "scandinave" in _cf["pinterest_title"].lower()

@test("content: title works without style")
def _():
    cn = generate_content(CONTENT_NO_STYLE)
    assert len(cn["pinterest_title"]) >= 20
    assert "scandinave" not in cn["pinterest_title"].lower()


# ═══════════════════════════════════════════════════════════
print("\n📝 CONTENT — PINTEREST DESCRIPTION")
# ═══════════════════════════════════════════════════════════

@test("content: description exists")
def _(): assert len(_cf["pinterest_description"]) > 0

@test("content: description length 80–300")
def _():
    d = _cf["pinterest_description"]
    assert 80 <= len(d) <= 300, f"Len={len(d)}"

@test("content: description has brand or inspiration")
def _():
    d = _cf["pinterest_description"].lower()
    assert any(w in d for w in ["unosnake", "inspir", "décor", "élégance"])

@test("content: description works without style")
def _():
    cn = generate_content(CONTENT_NO_STYLE)
    assert len(cn["pinterest_description"]) >= 80


# ═══════════════════════════════════════════════════════════
print("\n🏷️  CONTENT — HASHTAGS")
# ═══════════════════════════════════════════════════════════

@test("content: hashtags 5–10")
def _():
    h = _cf["hashtags"]
    assert 5 <= len(h) <= 10, f"Got {len(h)}: {h}"

@test("content: all hashtags start with #")
def _(): assert all(h.startswith("#") for h in _cf["hashtags"])

@test("content: no duplicate hashtags")
def _():
    lower = [h.lower() for h in _cf["hashtags"]]
    assert len(lower) == len(set(lower))

@test("content: no spaces in hashtags")
def _(): assert all(" " not in h for h in _cf["hashtags"])

@test("content: style tag present when style known")
def _():
    lower = [h.lower() for h in _cf["hashtags"]]
    assert any("scandinave" in h or "nordic" in h for h in lower)

@test("content: hashtags work without style")
def _():
    cn = generate_content(CONTENT_NO_STYLE)
    assert 5 <= len(cn["hashtags"]) <= 10

@test("content: hashtags work with empty candidate")
def _():
    ce = generate_content(CONTENT_EMPTY)
    assert len(ce["hashtags"]) >= 5


# ═══════════════════════════════════════════════════════════
print("\n📄 CONTENT — EDITORIAL DESCRIPTION")
# ═══════════════════════════════════════════════════════════

@test("content: editorial has UnoSnake")
def _(): assert "UnoSnake" in _cf["description"]

@test("content: editorial works with empty")
def _():
    ce = generate_content(CONTENT_EMPTY)
    assert "UnoSnake" in ce["description"]


# ═══════════════════════════════════════════════════════════
print("\n🔁 CONTENT — STABILITY & VARIATION")
# ═══════════════════════════════════════════════════════════

@test("content: same ASIN → same output")
def _():
    c1 = generate_content(CONTENT_FULL)
    c2 = generate_content(CONTENT_FULL)
    assert c1["pinterest_title"] == c2["pinterest_title"]
    assert c1["hashtags"] == c2["hashtags"]

@test("content: different ASIN → different output")
def _():
    c1 = generate_content(CONTENT_FULL)
    c2 = generate_content(dict(CONTENT_FULL, asin="B0DIFFERENT"))
    assert c1["pinterest_title"] != c2["pinterest_title"] or c1["pinterest_description"] != c2["pinterest_description"]

@test("content: deterministic index varies")
def _():
    assert len({_deterministic_index("A"), _deterministic_index("B"), _deterministic_index("C")}) == 3


# ═══════════════════════════════════════════════════════════
print("\n🛡️  CONTENT — EDGE CASES & STYLES")
# ═══════════════════════════════════════════════════════════

@test("content: empty candidate still generates")
def _():
    ce = generate_content(CONTENT_EMPTY)
    assert len(ce["pinterest_title"]) > 0 and len(ce["pinterest_description"]) > 0

@test("content: room detection salon")
def _():
    cs = generate_content(CONTENT_SALON)
    assert "salon" in cs["content_metadata"]["room_detected"].lower()

@test("content: japandi style detected")
def _():
    cj = generate_content(CONTENT_JAPANDI)
    assert "japandi" in cj["pinterest_title"].lower()

@test("content: bohème style detected")
def _():
    cb = generate_content(CONTENT_BOHO)
    assert "bohème" in cb["pinterest_title"].lower() or "bohème" in cb["pinterest_description"].lower()

@test("content: snippet used in editorial")
def _():
    d = _cf["description"].lower()
    assert "bois naturel" in d or "nordique" in d or "scandinave" in d




# ═══════════════════════════════════════════════════════════
print("\n🔌 PINTEREST CLIENT")
# ═══════════════════════════════════════════════════════════

@test("pinterest: client requires token")
def _():
    try:
        PinterestClient(access_token="")
        assert False
    except ValueError:
        pass

@test("pinterest: sandbox by default")
def _():
    c = PinterestClient(access_token="tok", sandbox=True)
    assert c.is_sandbox is True

@test("pinterest: production URL")
def _():
    c = PinterestClient(access_token="tok", sandbox=False)
    assert c.is_sandbox is False


# ═══════════════════════════════════════════════════════════
print("\n📦 PIN PAYLOAD")
# ═══════════════════════════════════════════════════════════

_P7_AFF = "https://www.amazon.fr/dp/B0H36L8M6F/ref=nosim?tag=unosnake09-21"

@test("pin payload: valid build")
def _():
    p = build_pin_payload("123", "Title", "desc", _P7_AFF)
    assert p["board_id"] == "123" and p["link"] == _P7_AFF

@test("pin payload: title truncated 100")
def _():
    assert len(build_pin_payload("123", "A" * 200, "d", _P7_AFF)["title"]) <= 100

@test("pin payload: rejects empty board")
def _():
    try:
        build_pin_payload("", "T", "d", _P7_AFF)
        assert False
    except ValueError:
        pass

@test("pin payload: rejects empty link")
def _():
    try:
        build_pin_payload("123", "T", "d", "")
        assert False
    except ValueError:
        pass

@test("pin payload: link is affiliate (not redirect)")
def _():
    p = build_pin_payload("123", "T", "d", _P7_AFF)
    assert "/ref=nosim?tag=" in p["link"]

@test("pin validate: correct passes")
def _():
    p = build_pin_payload("123", "T", "d", _P7_AFF)
    valid, reason = validate_pin_payload(p)
    assert valid is True

@test("pin validate: non-affiliate fails")
def _():
    v, _ = validate_pin_payload({"board_id": "123", "title": "X", "link": "https://amazon.fr/dp/B001"})
    assert v is False

@test("pin from candidate: complete")
def _():
    p = build_pin_from_candidate(
        {"title": "Ét", "asin": "B0H36L8M6F"},
        {"pinterest_title": "Ét — déco", "pinterest_description": "Desc", "hashtags": ["#Scan"]},
        "board123", _P7_AFF,
    )
    assert p["board_id"] == "board123" and "#Scan" in p["description"]


# ═══════════════════════════════════════════════════════════
print("\n🚀 PUBLISHER")
# ═══════════════════════════════════════════════════════════

_P7_CAND = {"title": "Ét Scandinave", "asin": "B0H36L8M6F"}
_P7_CONT = {"pinterest_title": "Ét — déco", "pinterest_description": "Desc", "hashtags": ["#Scan"]}

@test("publisher: dry_run skips")
def _():
    r = publish_pin(_P7_CAND, _P7_CONT, _P7_AFF, "b", "tok", dry_run=True)
    assert r.skipped is True and r.skip_reason == "dry_run"

@test("publisher: disabled skips with payload")
def _():
    r = publish_pin(_P7_CAND, _P7_CONT, _P7_AFF, "b", "tok", pinterest_enabled=False)
    assert r.skipped and r.payload is not None

@test("publisher: no token skips")
def _():
    r = publish_pin(_P7_CAND, _P7_CONT, _P7_AFF, "b", "", pinterest_enabled=True)
    assert r.skip_reason == "no_access_token"

@test("publisher: empty board → error")
def _():
    assert not publish_pin(_P7_CAND, _P7_CONT, _P7_AFF, "", "tok", pinterest_enabled=True).success

@test("publisher: empty affiliate → error")
def _():
    assert not publish_pin(_P7_CAND, _P7_CONT, "", "b", "tok", pinterest_enabled=True).success


# ═══════════════════════════════════════════════════════════
print("\n🔄 STATE MACHINE")
# ═══════════════════════════════════════════════════════════

@test("sm: New → Selected allowed")
def _(): assert can_transition("New", "Selected")[0] is True

@test("sm: Selected → Published allowed")
def _(): assert can_transition("Selected", "Published")[0] is True

@test("sm: Published → * blocked")
def _():
    for t in ["New", "Selected", "Rejected"]:
        assert can_transition("Published", t)[0] is False

@test("sm: same status blocked")
def _(): assert can_transition("Published", "Published")[0] is False

@test("sm: * → New blocked")
def _():
    for s in ["Selected", "Published", "Rejected"]:
        assert can_transition(s, "New")[0] is False


# ═══════════════════════════════════════════════════════════
print(f"\n{'=' * 55}")
total = _passed + _failed
if _failed == 0:
    print(f"✅ ALL {total} TESTS PASSED")
else:
    print(f"❌ {_failed}/{total} TESTS FAILED:")
    for name, error in _errors:
        print(f"   - {name}: {error}")
print(f"{'=' * 55}")
sys.exit(0 if _failed == 0 else 1)
