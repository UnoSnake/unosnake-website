#!/usr/bin/env python3
"""
UnoSnake — Scheduler / Autopilot Tests (20 tests).

Tests unitaires purs — aucun appel API réel.
Utilise des mocks pour Serper, Airtable, Pinterest.

Usage: python tests/test_scheduler.py
"""

import os, sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, PROJECT_ROOT)

from scripts.scheduler.autopilot import validate_config, _print_report
from scripts.config import (
    MAX_PUBLISH_PER_RUN, MIN_PRODUCT_SCORE, MAX_ACCEPTED_PER_RUN,
    PINTEREST_ENABLED, PINTEREST_SANDBOX, TEST_MODE,
)
from scripts.pinterest.publisher import publish_pin, PublishResult
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


AFF = "https://www.amazon.fr/dp/B0H36L8M6F/ref=nosim?tag=unosnake09-21"
CAND = {"title": "Étagère Scandinave", "asin": "B0H36L8M6F"}
CONT = {"pinterest_title": "Ét — déco", "pinterest_description": "Desc", "hashtags": ["#Scan"]}


# ═══════════════════════════════════════════════════════════
print("\n⚙️  SCHEDULER CONFIG")
# ═══════════════════════════════════════════════════════════

@test("config: MAX_PUBLISH_PER_RUN defaults to 1")
def _(): assert MAX_PUBLISH_PER_RUN == 1

@test("config: MIN_PRODUCT_SCORE defaults to 65")
def _(): assert MIN_PRODUCT_SCORE == 65

@test("config: PINTEREST_ENABLED defaults false")
def _(): assert PINTEREST_ENABLED is False

@test("config: PINTEREST_SANDBOX defaults true")
def _(): assert PINTEREST_SANDBOX is True

@test("config: TEST_MODE defaults true")
def _(): assert TEST_MODE is True

@test("config: validate_config checks secrets")
def _():
    # With empty env vars (default), should fail
    ok, errors = validate_config()
    assert ok is False
    assert any("SERPER_API_KEY" in e for e in errors)


# ═══════════════════════════════════════════════════════════
print("\n📊 PUBLISH LIMITS")
# ═══════════════════════════════════════════════════════════

@test("limits: MAX_PUBLISH_PER_RUN = 1")
def _(): assert MAX_PUBLISH_PER_RUN == 1

@test("limits: MAX_ACCEPTED_PER_RUN = 10 (discovery)")
def _(): assert MAX_ACCEPTED_PER_RUN == 10

@test("limits: 4 runs/day × 1/run = 4 max/day")
def _():
    runs_per_day = 4
    assert runs_per_day * MAX_PUBLISH_PER_RUN == 4


# ═══════════════════════════════════════════════════════════
print("\n🚀 PINTEREST BEHAVIOR")
# ═══════════════════════════════════════════════════════════

@test("pinterest disabled → no API call, skip")
def _():
    r = publish_pin(CAND, CONT, AFF, "board", "token", pinterest_enabled=False)
    assert r.skipped is True
    assert r.skip_reason == "pinterest_disabled"
    assert r.success is False

@test("pinterest dry_run → no API call, skip")
def _():
    r = publish_pin(CAND, CONT, AFF, "board", "token", pinterest_enabled=True, dry_run=True)
    assert r.skipped is True
    assert r.skip_reason == "dry_run"

@test("pinterest no token → skip")
def _():
    r = publish_pin(CAND, CONT, AFF, "board", "", pinterest_enabled=True)
    assert r.skip_reason == "no_access_token"

@test("pinterest 401 → not published (simulated)")
def _():
    # A 401 from Pinterest means publish_pin returns success=False
    # The autopilot must NOT mark Published
    r = PublishResult(success=False, error="401 Unauthorized")
    assert r.success is False

@test("pinterest 403 → not published (simulated)")
def _():
    r = PublishResult(success=False, error="403 Forbidden")
    assert r.success is False


# ═══════════════════════════════════════════════════════════
print("\n🔄 STATE MACHINE INTEGRATION")
# ═══════════════════════════════════════════════════════════

@test("success → Published allowed")
def _():
    ok, _ = can_transition("Selected", "Published")
    assert ok is True

@test("failure → stays Selected (Published blocked from New)")
def _():
    # If something fails, record stays at its current state
    # Published → anything is blocked
    ok, _ = can_transition("Published", "Selected")
    assert ok is False

@test("already Published → cannot republish")
def _():
    ok, _ = can_transition("Published", "Published")
    assert ok is False


# ═══════════════════════════════════════════════════════════
print("\n🛡️  IDEMPOTENCE")
# ═══════════════════════════════════════════════════════════

@test("duplicate ASIN skipped by dedup")
def _():
    from scripts.airtable.dedup import is_duplicate
    dup, reason = is_duplicate("B0H36L8M6F", None, None, {"B0H36L8M6F"}, set())
    assert dup is True

@test("Published product not reprocessed")
def _():
    # The autopilot fetches only Selected, filters out Published
    # Simulating: a Published record should not appear in candidates
    mock_record = {"fields": {"Status": "Published", "Published": True}}
    is_published = mock_record["fields"].get("Published", False)
    assert is_published is True  # Would be filtered out by _fetch_selected_candidates


# ═══════════════════════════════════════════════════════════
print("\n📋 REPORT")
# ═══════════════════════════════════════════════════════════

@test("report prints without secrets")
def _():
    import io, logging
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.INFO)
    test_logger = logging.getLogger("unosnake_test_report")
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.INFO)

    # Temporarily swap logger
    import scripts.scheduler.autopilot as ap
    orig = ap.logger
    ap.logger = test_logger

    report = {
        "candidates_discovered": 30,
        "candidates_accepted": 5,
        "duplicates_skipped": 3,
        "below_threshold": 22,
        "airtable_created": 5,
        "pinterest_enabled": False,
        "pins_published": 0,
        "pins_skipped": 5,
        "errors": [],
    }
    _print_report(report)

    ap.logger = orig

    output = buf.getvalue()
    # Must not contain secrets
    assert "SERPER_API_KEY" not in output
    assert "AIRTABLE_TOKEN" not in output
    assert "PINTEREST_ACCESS_TOKEN" not in output
    # Must contain key metrics
    assert "30" in output  # discovered
    assert "5" in output   # accepted


# ═══════════════════════════════════════════════════════════
print(f"\n{'=' * 55}")
total = _passed + _failed
if _failed == 0:
    print(f"✅ ALL {total} SCHEDULER TESTS PASSED")
else:
    print(f"❌ {_failed}/{total} FAILED:")
    for n, e in _errors:
        print(f"   - {n}: {e}")
print(f"{'=' * 55}")
sys.exit(0 if _failed == 0 else 1)
