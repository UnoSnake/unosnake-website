#!/usr/bin/env python3
"""
UnoSnake — Tests Pinterest Module (42 tests).

Couvre : client, payload, publisher, state machine, feature flags.
Aucun appel Pinterest réel — tests unitaires purs.

Usage: python tests/test_pinterest.py
"""

import os, sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, PROJECT_ROOT)

from scripts.pinterest.payload import (
    build_pin_payload,
    validate_pin_payload,
    build_pin_from_candidate,
)
from scripts.pinterest.publisher import publish_pin, PublishResult
from scripts.pinterest.client import PinterestClient, PINTEREST_SANDBOX_BASE, PINTEREST_API_BASE
from scripts.airtable.state_machine import (
    can_transition,
    ALLOWED_TRANSITIONS,
)
from scripts.config import PINTEREST_ENABLED, PINTEREST_SANDBOX

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
print("\n🔧 PINTEREST CONFIG")
# ═══════════════════════════════════════════════════════════

@test("PINTEREST_ENABLED defaults false")
def _(): assert PINTEREST_ENABLED is False

@test("PINTEREST_SANDBOX defaults true")
def _(): assert PINTEREST_SANDBOX is True


# ═══════════════════════════════════════════════════════════
print("\n🔌 PINTEREST CLIENT")
# ═══════════════════════════════════════════════════════════

@test("client requires token")
def _():
    try:
        PinterestClient(access_token="")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

@test("client sandbox URL")
def _():
    c = PinterestClient(access_token="test_token", sandbox=True)
    assert c.is_sandbox is True
    assert "sandbox" in c._base_url

@test("client production URL")
def _():
    c = PinterestClient(access_token="test_token", sandbox=False)
    assert c.is_sandbox is False
    assert c._base_url == PINTEREST_API_BASE

@test("client headers have Bearer token")
def _():
    c = PinterestClient(access_token="abc123", sandbox=True)
    assert c._headers["Authorization"] == "Bearer abc123"
    assert c._headers["Content-Type"] == "application/json"


# ═══════════════════════════════════════════════════════════
print("\n📦 PIN PAYLOAD")
# ═══════════════════════════════════════════════════════════

AFF_URL = "https://www.amazon.fr/dp/B0H36L8M6F/ref=nosim?tag=unosnake09-21"

@test("payload: valid build")
def _():
    p = build_pin_payload(
        board_id="123456",
        title="Étagère Scandinave",
        description="Belle étagère en bois",
        link=AFF_URL,
    )
    assert p["board_id"] == "123456"
    assert p["title"] == "Étagère Scandinave"
    assert p["link"] == AFF_URL

@test("payload: title truncated at 100")
def _():
    p = build_pin_payload("123", "A" * 200, "desc", AFF_URL)
    assert len(p["title"]) <= 100

@test("payload: description truncated at 500")
def _():
    p = build_pin_payload("123", "Title", "D" * 600, AFF_URL)
    assert len(p["description"]) <= 500

@test("payload: image_url sets media_source")
def _():
    p = build_pin_payload("123", "Title", "desc", AFF_URL, image_url="https://img.jpg")
    assert p["media_source"]["source_type"] == "image_url"
    assert p["media_source"]["url"] == "https://img.jpg"

@test("payload: no image_url → no media_source")
def _():
    p = build_pin_payload("123", "Title", "desc", AFF_URL)
    assert "media_source" not in p

@test("payload: rejects empty board_id")
def _():
    try:
        build_pin_payload("", "Title", "desc", AFF_URL)
        assert False
    except ValueError as e:
        assert "board_id" in str(e)

@test("payload: rejects empty title")
def _():
    try:
        build_pin_payload("123", "", "desc", AFF_URL)
        assert False
    except ValueError as e:
        assert "title" in str(e)

@test("payload: rejects empty link")
def _():
    try:
        build_pin_payload("123", "Title", "desc", "")
        assert False
    except ValueError as e:
        assert "link" in str(e)

@test("payload: link is affiliate URL (not redirect)")
def _():
    p = build_pin_payload("123", "Title", "desc", AFF_URL)
    assert "/ref=nosim?tag=" in p["link"]
    assert "unosnake09-21" in p["link"]
    assert "amazon.fr" in p["link"]


# ═══════════════════════════════════════════════════════════
print("\n✅ PAYLOAD VALIDATION")
# ═══════════════════════════════════════════════════════════

@test("validate: valid payload passes")
def _():
    p = build_pin_payload("123", "Title", "desc", AFF_URL)
    valid, reason = validate_pin_payload(p)
    assert valid is True and reason == "OK"

@test("validate: missing board_id fails")
def _():
    v, _ = validate_pin_payload({"title": "X", "link": AFF_URL})
    assert v is False

@test("validate: missing title fails")
def _():
    v, _ = validate_pin_payload({"board_id": "123", "link": AFF_URL})
    assert v is False

@test("validate: non-HTTPS link fails")
def _():
    v, _ = validate_pin_payload({"board_id": "123", "title": "X", "link": "http://example.com"})
    assert v is False

@test("validate: non-affiliate link fails")
def _():
    v, _ = validate_pin_payload({"board_id": "123", "title": "X", "link": "https://www.amazon.fr/dp/B0H36L8M6F"})
    assert v is False

@test("validate: title too long fails")
def _():
    v, _ = validate_pin_payload({"board_id": "123", "title": "A" * 101, "link": AFF_URL})
    assert v is False


# ═══════════════════════════════════════════════════════════
print("\n📌 BUILD FROM CANDIDATE")
# ═══════════════════════════════════════════════════════════

@test("build_pin_from_candidate: complete")
def _():
    candidate = {"title": "Étagère", "asin": "B0H36L8M6F"}
    content = {
        "pinterest_title": "Étagère — déco scandinave",
        "pinterest_description": "Description UnoSnake",
        "hashtags": ["#Scandinave", "#DecoMaison"],
    }
    p = build_pin_from_candidate(candidate, content, "board123", AFF_URL)
    assert p["board_id"] == "board123"
    assert p["title"] == "Étagère — déco scandinave"
    assert "#Scandinave" in p["description"]
    assert p["link"] == AFF_URL


# ═══════════════════════════════════════════════════════════
print("\n🚀 PUBLISHER")
# ═══════════════════════════════════════════════════════════

CANDIDATE = {"title": "Étagère Scandinave", "asin": "B0H36L8M6F"}
CONTENT = {
    "pinterest_title": "Étagère — déco scandinave",
    "pinterest_description": "Description UnoSnake",
    "hashtags": ["#Scandinave"],
}

@test("publisher: dry_run skips")
def _():
    r = publish_pin(CANDIDATE, CONTENT, AFF_URL, "board123", "token", dry_run=True)
    assert r.skipped is True
    assert r.skip_reason == "dry_run"
    assert r.success is False
    assert r.payload is not None

@test("publisher: pinterest_disabled skips")
def _():
    r = publish_pin(CANDIDATE, CONTENT, AFF_URL, "board123", "token", pinterest_enabled=False)
    assert r.skipped is True
    assert r.skip_reason == "pinterest_disabled"
    assert r.payload is not None

@test("publisher: no token skips")
def _():
    r = publish_pin(CANDIDATE, CONTENT, AFF_URL, "board123", "", pinterest_enabled=True)
    assert r.skipped is True
    assert r.skip_reason == "no_access_token"

@test("publisher: empty board_id → error")
def _():
    r = publish_pin(CANDIDATE, CONTENT, AFF_URL, "", "token", pinterest_enabled=True)
    assert r.success is False
    assert "board_id" in r.error.lower()

@test("publisher: empty affiliate → error")
def _():
    r = publish_pin(CANDIDATE, CONTENT, "", "board123", "token", pinterest_enabled=True)
    assert r.success is False
    assert "link" in r.error.lower() or "affiliate" in r.error.lower()

@test("publisher: PublishResult to_dict")
def _():
    r = PublishResult(success=True, pin_id="pin_123", pin_url="https://pin.it/123")
    d = r.to_dict()
    assert d["success"] is True
    assert d["pin_id"] == "pin_123"

@test("publisher: payload prepared even when disabled")
def _():
    r = publish_pin(CANDIDATE, CONTENT, AFF_URL, "board123", "token", pinterest_enabled=False)
    assert r.payload is not None
    assert r.payload["board_id"] == "board123"
    assert "/ref=nosim?tag=" in r.payload["link"]


# ═══════════════════════════════════════════════════════════
print("\n🔄 STATE MACHINE")
# ═══════════════════════════════════════════════════════════

@test("sm: New → Selected allowed")
def _():
    ok, _ = can_transition("New", "Selected")
    assert ok is True

@test("sm: Selected → Published allowed")
def _():
    ok, _ = can_transition("Selected", "Published")
    assert ok is True

@test("sm: Selected → Rejected allowed")
def _():
    ok, _ = can_transition("Selected", "Rejected")
    assert ok is True

@test("sm: New → Rejected allowed")
def _():
    ok, _ = can_transition("New", "Rejected")
    assert ok is True

@test("sm: Published → anything blocked")
def _():
    for target in ["New", "Selected", "Rejected"]:
        ok, _ = can_transition("Published", target)
        assert ok is False, f"Published → {target} should be blocked"

@test("sm: same status blocked")
def _():
    ok, reason = can_transition("Published", "Published")
    assert ok is False
    assert "Already" in reason

@test("sm: Rejected → Published blocked")
def _():
    ok, _ = can_transition("Rejected", "Published")
    assert ok is False

@test("sm: arbitrary → New blocked")
def _():
    for source in ["Selected", "Published", "Rejected"]:
        ok, _ = can_transition(source, "New")
        assert ok is False, f"{source} → New should be blocked"


# ═══════════════════════════════════════════════════════════
print(f"\n{'=' * 55}")
total = _passed + _failed
if _failed == 0:
    print(f"✅ ALL {total} PINTEREST TESTS PASSED")
else:
    print(f"❌ {_failed}/{total} FAILED:")
    for n, e in _errors:
        print(f"   - {n}: {e}")
print(f"{'=' * 55}")
sys.exit(0 if _failed == 0 else 1)
