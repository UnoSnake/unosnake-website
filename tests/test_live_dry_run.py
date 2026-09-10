#!/usr/bin/env python3
"""
UnoSnake — Live Dry Run Tests (20 tests).

Vérifie que dry-run bloque Pinterest/Published tout en permettant
la discovery réelle. Tous les tests sont mockés — pas d'appel API.

Usage: python tests/test_live_dry_run.py
"""

import os, sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, PROJECT_ROOT)

from scripts.pinterest.publisher import publish_pin, PublishResult
from scripts.pinterest.client import PinterestClient
from scripts.airtable.state_machine import can_transition
from scripts.airtable.dedup import is_duplicate
from scripts.amazon.asin import build_affiliate_url, validate_affiliate_url, is_valid_asin
from scripts.config import PINTEREST_ENABLED, PINTEREST_SANDBOX, MIN_PRODUCT_SCORE
from scripts.scheduler.quality import validate_candidate, generate_quality_report

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


AFF = "https://www.amazon.fr/dp/B0H36L8M6F/ref=nosim?tag=unosnake09-21"
CAND = {"title": "Étagère Scandinave", "asin": "B0H36L8M6F"}
CONT = {"pinterest_title": "Ét — déco", "pinterest_description": "Desc", "hashtags": ["#Scan"]}


# ═══════════════════════════════════════════════════════════
print("\n🛡️  PINTEREST HARD BLOCK")
# ═══════════════════════════════════════════════════════════

@test("dry_run blocks Pinterest")
def _():
    r = publish_pin(CAND, CONT, AFF, "board", "token", pinterest_enabled=True, dry_run=True)
    assert r.skipped is True
    assert r.skip_reason == "dry_run"
    assert r.success is False

@test("dry_run never produces Published")
def _():
    r = publish_pin(CAND, CONT, AFF, "board", "token", dry_run=True)
    assert r.success is False

@test("PINTEREST_ENABLED=false blocks")
def _():
    r = publish_pin(CAND, CONT, AFF, "board", "token", pinterest_enabled=False)
    assert r.skipped is True

@test("Pinterest disabled is safe")
def _():
    assert PINTEREST_ENABLED is False

@test("Pinterest dry_run is safe")
def _():
    assert PINTEREST_SANDBOX is True


# ═══════════════════════════════════════════════════════════
print("\n📊 DATA QUALITY")
# ═══════════════════════════════════════════════════════════

GOOD_CAND = {
    "title": "Étagère Murale Scandinave en Bois Naturel",
    "asin": "B0H6LW7X2K",
    "url": "https://www.amazon.fr/dp/B0H6LW7X2K",
    "score": 82,
}
GOOD_CONTENT = {
    "pinterest_title": "Étagère — déco scandinave",
    "pinterest_description": "Description naturelle UnoSnake",
    "hashtags": ["#Scandinave", "#DecoMaison", "#HomeDecor", "#Interieur", "#UnoSnake"],
}

@test("valid candidate passes all checks")
def _():
    r = validate_candidate(GOOD_CAND, GOOD_CONTENT, AFF)
    assert r["quality_pct"] >= 80, f"Quality {r['quality_pct']}%"
    assert r["checks"]["valid_asin"] is True
    assert r["checks"]["valid_amazon_url"] is True

@test("invalid ASIN fails check")
def _():
    c = dict(GOOD_CAND, asin="short")
    r = validate_candidate(c)
    assert r["checks"]["valid_asin"] is False

@test("missing affiliate fails check")
def _():
    r = validate_candidate(GOOD_CAND, GOOD_CONTENT, "")
    assert r["checks"]["valid_affiliate_url"] is False

@test("affiliate without nosim fails")
def _():
    r = validate_candidate(GOOD_CAND, GOOD_CONTENT, "https://www.amazon.fr/dp/B0H6LW7X2K?tag=x")
    assert r["checks"]["valid_affiliate_url"] is False

@test("score below threshold detected")
def _():
    c = dict(GOOD_CAND, score=40)
    r = validate_candidate(c)
    assert r["checks"]["score_above_threshold"] is False

@test("score above threshold passes")
def _():
    r = validate_candidate(GOOD_CAND)
    assert r["checks"]["score_above_threshold"] is True

@test("Pinterest title validation")
def _():
    r = validate_candidate(GOOD_CAND, GOOD_CONTENT)
    assert r["checks"]["pinterest_title_ok"] is True

@test("image HTTPS validated")
def _():
    c = dict(GOOD_CAND, image_url="https://images.amazon.com/img.jpg")
    r = validate_candidate(c)
    assert r["checks"]["valid_image"] is True

@test("image non-HTTPS detected")
def _():
    c = dict(GOOD_CAND, image_url="http://insecure.com/img.jpg")
    r = validate_candidate(c)
    assert r["checks"]["valid_image"] is False


# ═══════════════════════════════════════════════════════════
print("\n📋 QUALITY REPORT")
# ═══════════════════════════════════════════════════════════

@test("quality report for batch")
def _():
    report = generate_quality_report([GOOD_CAND], [GOOD_CONTENT])
    assert report["count"] == 1
    assert report["quality_pct"] >= 50

@test("empty batch report")
def _():
    report = generate_quality_report([])
    assert report["count"] == 0
    assert report["quality_pct"] == 0

@test("report aggregate check rates")
def _():
    report = generate_quality_report([GOOD_CAND, dict(GOOD_CAND, asin="short")])
    assert "valid_asin" in report["check_rates"]


# ═══════════════════════════════════════════════════════════
print("\n🔄 IDEMPOTENCE IN DRY RUN")
# ═══════════════════════════════════════════════════════════

@test("duplicate ASIN blocked")
def _():
    dup, _ = is_duplicate("B0H36L8M6F", None, None, {"B0H36L8M6F"}, set())
    assert dup is True

@test("Published never modified in dry-run")
def _():
    ok, _ = can_transition("Published", "Selected")
    assert ok is False

@test("zero candidates → no error")
def _():
    report = generate_quality_report([])
    assert report["count"] == 0


# ═══════════════════════════════════════════════════════════
print(f"\n{'=' * 55}")
total = _passed + _failed
if _failed == 0:
    print(f"✅ ALL {total} LIVE DRY RUN TESTS PASSED")
else:
    print(f"❌ {_failed}/{total} FAILED:")
    for n, e in _errors:
        print(f"   - {n}: {e}")
print(f"{'=' * 55}")
sys.exit(0 if _failed == 0 else 1)
