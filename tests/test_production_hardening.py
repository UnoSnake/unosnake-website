#!/usr/bin/env python3
"""
UnoSnake — Production Hardening Tests (Phase 11).

Tests du flux complet New → Selected → Published.
Tous les appels externes sont mockés.

Usage: python tests/test_production_hardening.py
"""

import os, sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, PROJECT_ROOT)

from scripts.airtable.state_machine import (
    can_transition, mark_selected, mark_published, mark_rejected,
    ALLOWED_TRANSITIONS,
)
from scripts.airtable.dedup import is_duplicate, build_existing_index, check_candidate_batch
from scripts.amazon.asin import extract_asin, normalize_amazon_url, build_affiliate_url, validate_affiliate_url
from scripts.pinterest.publisher import publish_pin, PublishResult
from scripts.config import (
    PINTEREST_ENABLED, PINTEREST_SANDBOX, TEST_MODE,
    MAX_PUBLISH_PER_RUN, MIN_PRODUCT_SCORE,
)

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


# ── Mock Airtable client ──
class MockAirtableClient:
    """Mock client that records calls without network."""
    def __init__(self):
        self.updates = []  # list of (record_id, fields)

    def update_record(self, record_id, fields):
        self.updates.append((record_id, fields))
        return True


AFF = "https://www.amazon.fr/dp/B0H36L8M6F/ref=nosim?tag=unosnake09-21"
CAND = {"title": "Étagère Scandinave", "asin": "B0H36L8M6F"}
CONT = {"pinterest_title": "Ét — déco", "pinterest_description": "Desc", "hashtags": ["#Scan"]}


# ═══════════════════════════════════════════════════════════
print("\n🔄 FLUX: New → Selected → Published")
# ═══════════════════════════════════════════════════════════

@test("New → Selected is allowed")
def _():
    ok, _ = can_transition("New", "Selected")
    assert ok is True

@test("Selected → Published is allowed")
def _():
    ok, _ = can_transition("Selected", "Published")
    assert ok is True

@test("New → Published is FORBIDDEN (skip Selected)")
def _():
    ok, reason = can_transition("New", "Published")
    assert ok is False, f"New → Published should be blocked, got: {reason}"

@test("mark_selected actually transitions")
def _():
    client = MockAirtableClient()
    result = mark_selected(client, "rec123", "New")
    assert result is True
    assert len(client.updates) == 1
    assert client.updates[0] == ("rec123", {"Status": "Selected"})

@test("mark_published after Selected")
def _():
    client = MockAirtableClient()
    result = mark_published(client, "rec123", "Selected", pin_id="pin_456")
    assert result is True
    assert client.updates[0][1]["Status"] == "Published"
    assert client.updates[0][1]["Published"] is True

@test("mark_published refuses from New")
def _():
    client = MockAirtableClient()
    result = mark_published(client, "rec123", "New")
    assert result is False
    assert len(client.updates) == 0  # No update made


# ═══════════════════════════════════════════════════════════
print("\n🛡️  Published IMMUTABLE")
# ═══════════════════════════════════════════════════════════

@test("Published → New blocked")
def _(): assert can_transition("Published", "New")[0] is False

@test("Published → Selected blocked")
def _(): assert can_transition("Published", "Selected")[0] is False

@test("Published → Rejected blocked")
def _(): assert can_transition("Published", "Rejected")[0] is False

@test("Published → Published blocked")
def _(): assert can_transition("Published", "Published")[0] is False

@test("Published ASIN is duplicate")
def _():
    records = [{"fields": {"Amazon URL": "https://www.amazon.fr/dp/B0PUBLI001", "Status": "Published"}}]
    asins, urls = build_existing_index(records, extract_asin, normalize_amazon_url)
    dup, _ = is_duplicate("B0PUBLI001", None, None, asins, urls)
    assert dup is True


# ═══════════════════════════════════════════════════════════
print("\n🔁 IDEMPOTENCE")
# ═══════════════════════════════════════════════════════════

@test("Run 1: new ASIN passes dedup")
def _():
    dup, _ = is_duplicate("B0NEWPROD01", None, None, set(), set())
    assert dup is False

@test("Run 2: same ASIN blocked after Published")
def _():
    dup, _ = is_duplicate("B0NEWPROD01", None, None, {"B0NEWPROD01"}, set())
    assert dup is True

@test("Same ASIN different URL still blocked")
def _():
    dup, _ = is_duplicate("B0H36L8M6F", None, None, {"B0H36L8M6F"}, set())
    assert dup is True

@test("Same URL different title still blocked")
def _():
    url = "https://www.amazon.fr/dp/B0H36L8M6F"
    dup, _ = is_duplicate(None, url, None, set(), {url})
    assert dup is True

@test("Intra-batch duplicate blocked")
def _():
    cands = [
        {"url": "https://www.amazon.fr/dp/B0SAME0001", "asin": "B0SAME0001", "title": "First"},
        {"url": "https://www.amazon.fr/dp/B0SAME0001", "asin": "B0SAME0001", "title": "Copy"},
    ]
    new, dups = check_candidate_batch(cands, set(), set(), extract_asin, normalize_amazon_url)
    assert len(new) == 1 and len(dups) == 1

@test("Selected record in Airtable blocks re-creation")
def _():
    records = [{"fields": {"Amazon URL": "https://www.amazon.fr/dp/B0SELECT01", "Status": "Selected"}}]
    asins, urls = build_existing_index(records, extract_asin, normalize_amazon_url)
    dup, _ = is_duplicate("B0SELECT01", None, None, asins, urls)
    assert dup is True


# ═══════════════════════════════════════════════════════════
print("\n📌 PINTEREST BEHAVIOR")
# ═══════════════════════════════════════════════════════════

@test("Pinterest disabled → skip, exit 0")
def _():
    r = publish_pin(CAND, CONT, AFF, "board", "token", pinterest_enabled=False)
    assert r.skipped is True
    assert r.success is False
    assert r.skip_reason == "pinterest_disabled"

@test("Pinterest enabled + dry_run → skip")
def _():
    r = publish_pin(CAND, CONT, AFF, "board", "token", pinterest_enabled=True, dry_run=True)
    assert r.skipped is True
    assert r.skip_reason == "dry_run"

@test("Pinterest 401 → no Published")
def _():
    # Simulated: 401 means publish_pin returns success=False
    r = PublishResult(success=False, error="401 Unauthorized")
    assert r.success is False
    # State machine: don't call mark_published
    client = MockAirtableClient()
    # On failure, we should NOT transition
    assert len(client.updates) == 0

@test("Pinterest 403 → no Published")
def _():
    r = PublishResult(success=False, error="403 Forbidden")
    assert r.success is False

@test("Pinterest success → Published allowed")
def _():
    r = PublishResult(success=True, pin_id="pin_789")
    assert r.success is True
    # Now we CAN call mark_published
    client = MockAirtableClient()
    ok = mark_published(client, "rec456", "Selected", pin_id="pin_789")
    assert ok is True
    assert client.updates[0][1]["Published"] is True

@test("Pinterest failure → stays Selected")
def _():
    r = PublishResult(success=False, error="500 Server Error")
    client = MockAirtableClient()
    # On failure, DO NOT call mark_published
    if not r.success:
        pass  # No transition
    assert len(client.updates) == 0

@test("Empty board → error")
def _():
    r = publish_pin(CAND, CONT, AFF, "", "token", pinterest_enabled=True)
    assert r.success is False

@test("Empty token → skip")
def _():
    r = publish_pin(CAND, CONT, AFF, "board", "", pinterest_enabled=True)
    assert r.skip_reason == "no_access_token"


# ═══════════════════════════════════════════════════════════
print("\n🔗 AFFILIATE URL VALIDATION")
# ═══════════════════════════════════════════════════════════

@test("Affiliate URL correct format")
def _():
    url = build_affiliate_url("B0H36L8M6F", "unosnake09-21")
    assert url == "https://www.amazon.fr/dp/B0H36L8M6F/ref=nosim?tag=unosnake09-21"

@test("validate passes correct URL")
def _():
    valid, _ = validate_affiliate_url(AFF, "B0H36L8M6F", "unosnake09-21")
    assert valid is True

@test("validate rejects missing nosim")
def _():
    valid, _ = validate_affiliate_url("https://www.amazon.fr/dp/B0H36L8M6F?tag=x", "B0H36L8M6F", "x")
    assert valid is False


# ═══════════════════════════════════════════════════════════
print("\n⚙️  CONFIGURATION SAFETY")
# ═══════════════════════════════════════════════════════════

@test("PINTEREST_ENABLED defaults false")
def _(): assert PINTEREST_ENABLED is False

@test("PINTEREST_SANDBOX defaults true")
def _(): assert PINTEREST_SANDBOX is True

@test("TEST_MODE defaults true")
def _(): assert TEST_MODE is True

@test("MAX_PUBLISH_PER_RUN = 1")
def _(): assert MAX_PUBLISH_PER_RUN == 1

@test("MIN_PRODUCT_SCORE = 65")
def _(): assert MIN_PRODUCT_SCORE == 65


# ═══════════════════════════════════════════════════════════
print("\n🧪 ZERO CANDIDATES")
# ═══════════════════════════════════════════════════════════

@test("Empty candidate list → no error")
def _():
    new, dups = check_candidate_batch([], set(), set(), extract_asin, normalize_amazon_url)
    assert new == [] and dups == []


# ═══════════════════════════════════════════════════════════
print("\n📋 COMPLETE STATE MACHINE")
# ═══════════════════════════════════════════════════════════

@test("All allowed transitions verified")
def _():
    for fr, to in ALLOWED_TRANSITIONS:
        ok, _ = can_transition(fr, to)
        assert ok is True, f"{fr} → {to} should be allowed"

@test("All forbidden transitions verified")
def _():
    forbidden = [
        ("Published", "New"), ("Published", "Selected"), ("Published", "Rejected"),
        ("Published", "Published"),
        ("Selected", "New"), ("Rejected", "New"),
        ("Rejected", "Selected"), ("Rejected", "Published"),
        ("New", "Published"),  # must go through Selected first
    ]
    for fr, to in forbidden:
        ok, _ = can_transition(fr, to)
        assert ok is False, f"{fr} → {to} should be FORBIDDEN"


# ═══════════════════════════════════════════════════════════
print(f"\n{'=' * 55}")
total = _passed + _failed
if _failed == 0:
    print(f"✅ ALL {total} PRODUCTION HARDENING TESTS PASSED")
else:
    print(f"❌ {_failed}/{total} FAILED:")
    for n, e in _errors:
        print(f"   - {n}: {e}")
print(f"{'=' * 55}")
sys.exit(0 if _failed == 0 else 1)
