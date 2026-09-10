"""
UnoSnake — Autopilot Scheduler.

Orchestre le pipeline complet :
  Discovery → Dedup → Scoring → Content → Affiliate → Airtable → Pinterest

Conçu pour être appelé par GitHub Actions cron (4×/jour).
Idempotent : un même ASIN n'est jamais publié deux fois.

Usage:
    python -m scripts.scheduler.autopilot [--dry-run]
    python -m scripts.scheduler.autopilot --live-pilot
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.config import (
    TEST_MODE,
    PINTEREST_ENABLED,
    PINTEREST_ACCESS_TOKEN,
    PINTEREST_BOARD_ID,
    PINTEREST_SANDBOX,
    AIRTABLE_BASE_ID,
    AIRTABLE_TOKEN,
    AIRTABLE_TABLE_ID,
    AIRTABLE_API_URL,
    AMAZON_PARTNER_TAG,
    AMAZON_DOMAIN,
    SERPER_API_KEY,
    MAX_PUBLISH_PER_RUN,
    MIN_PRODUCT_SCORE,
    STATUS_NEW,
    STATUS_SELECTED,
    LIVE_PILOT,
    MAX_PILOT_AIRTABLE_WRITES,
    FIRST_PIN_MODE,
)
from scripts.discovery.engine import run_discovery, resolve_product_name
from scripts.amazon.asin import build_affiliate_url, validate_affiliate_url, extract_asin
from scripts.content.generator import generate_content
from scripts.pinterest.publisher import publish_pin
from scripts.airtable.state_machine import mark_selected, mark_published
from scripts.pinterest.launch_gate import evaluate_launch_gate, format_readiness_report

logger = logging.getLogger("unosnake")


def validate_config(live_pilot: bool = False) -> tuple[bool, list[str]]:
    """
    Vérifie que la configuration minimale est présente.

    Returns:
        (ok, errors) — ok=True si la config est suffisante pour le discovery.
    """
    errors = []
    if not SERPER_API_KEY:
        errors.append("SERPER_API_KEY is missing")
    if not AIRTABLE_BASE_ID:
        errors.append("AIRTABLE_BASE_ID is missing")
    if not AIRTABLE_TOKEN:
        errors.append("AIRTABLE_TOKEN is missing")
    if not AMAZON_PARTNER_TAG:
        errors.append("AMAZON_PARTNER_TAG is missing")

    # In live-pilot mode, Pinterest MUST be disabled
    if live_pilot and PINTEREST_ENABLED:
        errors.append("LIVE PILOT: PINTEREST_ENABLED must be false during pilot")

    if PINTEREST_ENABLED and not live_pilot:
        if not PINTEREST_ACCESS_TOKEN:
            errors.append("PINTEREST_ENABLED=true but PINTEREST_ACCESS_TOKEN is missing")
        if not PINTEREST_BOARD_ID:
            errors.append("PINTEREST_ENABLED=true but PINTEREST_BOARD_ID is missing")

    return (len(errors) == 0, errors)


def run_autopilot(dry_run: bool = False, live_pilot: bool = False) -> dict:
    """
    Pipeline complet UnoSnake Autopilot.

    Args:
        dry_run: No writes to Pinterest/Airtable.
        live_pilot: Real data validation mode — allows Airtable writes
                    (max 1), but Pinterest is HARD DISABLED.
                    Overrides dry_run=False.

    Returns:
        dict résumé de l'exécution.
    """
    start_time = datetime.now(timezone.utc)

    # Live pilot overrides
    effective_dry_run = dry_run
    if live_pilot:
        effective_dry_run = False  # Allow Airtable writes

    mode_label = "LIVE PILOT" if live_pilot else ("DRY RUN" if effective_dry_run else "PRODUCTION")

    logger.info("=" * 60)
    logger.info("UNOSNAKE AUTOPILOT")
    logger.info(f"Time:      {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info(f"Mode:      {mode_label}")
    logger.info(f"Dry run:   {effective_dry_run}")
    logger.info(f"Live pilot: {live_pilot}")
    logger.info(f"Pinterest: {'ENABLED' if PINTEREST_ENABLED else 'DISABLED'}")
    if live_pilot:
        logger.info(f"Pinterest: HARD DISABLED (live pilot)")
        logger.info(f"Max Airtable writes: {MAX_PILOT_AIRTABLE_WRITES}")
    logger.info(f"Sandbox:   {PINTEREST_SANDBOX}")
    logger.info(f"Max publish/run: {MAX_PUBLISH_PER_RUN}")
    logger.info("=" * 60)

    report = {
        "timestamp": start_time.isoformat(),
        "mode": mode_label,
        "dry_run": effective_dry_run,
        "live_pilot": live_pilot,
        "pinterest_enabled": PINTEREST_ENABLED if not live_pilot else False,
        "candidates_discovered": 0,
        "candidates_accepted": 0,
        "duplicates_skipped": 0,
        "below_threshold": 0,
        "airtable_created": 0,
        "pins_published": 0,
        "pins_skipped": 0,
        "errors": [],
    }

    # ── 1. Validate config ──
    config_ok, config_errors = validate_config(live_pilot=live_pilot)
    if not config_ok:
        for err in config_errors:
            logger.error(f"CONFIG ERROR: {err}")
            report["errors"].append(err)
        return report

    logger.info("Configuration validated ✓")

    # ── 2. Run discovery pipeline ──
    logger.info("")
    logger.info("PHASE: DISCOVERY")

    # In live-pilot mode, limit accepted candidates to MAX_PILOT_AIRTABLE_WRITES
    discovery_result = run_discovery(
        test_mode=TEST_MODE,
        dry_run=effective_dry_run,
        max_accepted_override=MAX_PILOT_AIRTABLE_WRITES if live_pilot else None,
    )

    report["candidates_discovered"] = discovery_result.get("total_candidates", 0)
    report["candidates_accepted"] = discovery_result.get("accepted", 0)
    report["duplicates_skipped"] = discovery_result.get("duplicates_skipped", 0)
    report["below_threshold"] = discovery_result.get("below_threshold", 0)
    report["airtable_created"] = discovery_result.get("records_created", 0)
    report["errors"].extend(discovery_result.get("errors", []))

    accepted = discovery_result.get("selected_candidates", [])

    if not accepted:
        logger.info("No candidates accepted — nothing to publish")
        _print_report(report)
        return report

    # ── 3. Pinterest publication phase ──
    logger.info("")
    logger.info("PHASE: PINTEREST PUBLICATION")

    # LIVE PILOT: Pinterest is HARD DISABLED — no exceptions
    if live_pilot:
        logger.info("LIVE PILOT — Pinterest HARD DISABLED. No publication, no selection.")
        logger.info("Records created with Status=New, Published=false.")
        logger.info("This is a data quality validation run only.")
        report["pins_skipped"] = len(accepted)
        report["pinterest_api_calls"] = 0
        _print_report(report)
        return report

    logger.info(f"Pinterest enabled: {PINTEREST_ENABLED}")
    report["selected"] = 0

    if not PINTEREST_ENABLED:
        logger.info("Pinterest DISABLED — skipping publication (this is normal)")
        report["pins_skipped"] = len(accepted)
        _print_report(report)
        return report

    if effective_dry_run:
        logger.info("DRY RUN — skipping Pinterest publication")
        report["pins_skipped"] = len(accepted)
        _print_report(report)
        return report

    # ── LAUNCH GATE — production publication authorization ──
    # This gate MUST pass before ANY real Pin is created.
    # It re-checks token, board, sandbox/production, and all safety flags.
    logger.info("")
    logger.info("PHASE: LAUNCH GATE")

    def _client_factory(token, sandbox):
        from scripts.pinterest.client import PinterestClient
        return PinterestClient(access_token=token, sandbox=sandbox)

    gate = evaluate_launch_gate(
        pinterest_enabled=PINTEREST_ENABLED,
        pinterest_sandbox=PINTEREST_SANDBOX,
        access_token=PINTEREST_ACCESS_TOKEN,
        board_id=PINTEREST_BOARD_ID,
        test_mode=TEST_MODE,
        live_pilot=live_pilot,
        dry_run=effective_dry_run,
        client_factory=_client_factory,
    )
    report["launch_gate_ready"] = gate.ready
    report["launch_gate_reasons"] = gate.reasons

    if not gate.ready:
        logger.warning("LAUNCH GATE = BLOCKED — no publication will occur")
        for r in gate.reasons:
            logger.warning(f"  - {r}")
        report["pins_skipped"] = len(accepted)
        _print_report(report)
        return report

    logger.info("LAUNCH GATE = READY — production publication authorized")

    # ── FIRST PIN MODE — cap at exactly 1 Pin, no batch ──
    effective_max_publish = MAX_PUBLISH_PER_RUN
    if FIRST_PIN_MODE:
        effective_max_publish = 1
        logger.info("FIRST PIN MODE — capped to exactly 1 Pin, no batch")
    report["first_pin_mode"] = FIRST_PIN_MODE

    # ── 4. Publish up to MAX_PUBLISH_PER_RUN pins ──
    # First: transition best New candidates → Selected
    _select_best_new_candidates()
    report["selected"] = effective_max_publish  # attempted

    # Then: fetch Selected candidates for publication
    publish_candidates = _fetch_selected_candidates()

    if not publish_candidates:
        logger.info("No Selected candidates ready for publication")
        _print_report(report)
        return report

    published_count = 0

    for record in publish_candidates[:effective_max_publish]:
        fields = record.get("fields", {})
        record_id = record.get("id", "")
        asin = extract_asin(fields.get("Amazon URL", ""))
        product_name = fields.get("Product Name", "Unknown")

        logger.info(f"Publishing: {product_name[:60]} [ASIN:{asin}]")

        # Build affiliate URL
        affiliate_url = ""
        if asin:
            affiliate_url = build_affiliate_url(asin, AMAZON_PARTNER_TAG, AMAZON_DOMAIN)

        if not affiliate_url:
            logger.error(f"  Cannot build affiliate URL for {asin}")
            report["errors"].append(f"No affiliate URL for {asin}")
            continue

        # Validate affiliate URL
        valid, reason = validate_affiliate_url(affiliate_url, asin, AMAZON_PARTNER_TAG)
        if not valid:
            logger.error(f"  Affiliate URL invalid: {reason}")
            report["errors"].append(f"Invalid affiliate URL: {reason}")
            continue

        # Build content for the Pin
        candidate_data = {
            "title": product_name,
            "asin": asin,
            "snippet": fields.get("Description", ""),
            "style_detected": fields.get("Style", ""),
            "category_detected": fields.get("Category", ""),
        }
        content = generate_content(candidate_data)

        # Publish
        result = publish_pin(
            candidate=candidate_data,
            content=content,
            affiliate_url=affiliate_url,
            board_id=PINTEREST_BOARD_ID,
            access_token=PINTEREST_ACCESS_TOKEN,
            pinterest_enabled=PINTEREST_ENABLED,
            sandbox=PINTEREST_SANDBOX,
            dry_run=False,
        )

        if result.success:
            # Mark Published ONLY after Pinterest confirmation
            from scripts.airtable.client import AirtableClient
            client = AirtableClient(AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID, AIRTABLE_TOKEN, AIRTABLE_API_URL)
            mark_published(client, record_id, STATUS_SELECTED, pin_id=result.pin_id)
            published_count += 1
            report["pins_published"] += 1
            logger.info(f"  ✅ Published — Pin ID: {result.pin_id}")
        elif result.skipped:
            report["pins_skipped"] += 1
            logger.info(f"  ⏭️ Skipped: {result.skip_reason}")
        else:
            report["errors"].append(f"Pinterest error for {asin}: {result.error}")
            logger.error(f"  ❌ Failed: {result.error}")
            # Do NOT mark Published — keep Selected

    _print_report(report)
    return report


def _fetch_selected_candidates() -> list[dict]:
    """Récupère les candidats Selected depuis Airtable (prêts à publier)."""
    try:
        from scripts.airtable.client import AirtableClient
        client = AirtableClient(AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID, AIRTABLE_TOKEN, AIRTABLE_API_URL)
        records = client.find_by_formula(
            '{Status}="Selected"',
            fields=["Product Name", "Amazon URL", "Affiliate URL", "Description",
                    "Style", "Category", "Status", "Published"],
        )
        # Filter out any already Published (safety)
        return [r for r in records if not r.get("fields", {}).get("Published", False)]
    except Exception as e:
        logger.warning(f"Could not fetch Selected candidates: {e}")
        return []


def _select_best_new_candidates() -> int:
    """
    Transitions les meilleurs candidats New → Selected.

    Sélectionne jusqu'à MAX_PUBLISH_PER_RUN produits New
    et les fait passer en Selected (prêts pour publication).

    Returns:
        Nombre de records transitionné.
    """
    try:
        from scripts.airtable.client import AirtableClient
        client = AirtableClient(AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID, AIRTABLE_TOKEN, AIRTABLE_API_URL)

        records = client.find_by_formula(
            '{Status}="New"',
            fields=["Product Name", "Amazon URL", "Status", "Published", "Date Added"],
        )

        # Filter: not already Published (safety)
        candidates = [r for r in records if not r.get("fields", {}).get("Published", False)]

        if not candidates:
            logger.info("  No New candidates available for selection")
            return 0

        selected_count = 0
        for record in candidates[:MAX_PUBLISH_PER_RUN]:
            record_id = record.get("id", "")
            name = record.get("fields", {}).get("Product Name", "?")
            ok = mark_selected(client, record_id, "New")
            if ok:
                selected_count += 1
                logger.info(f"  New → Selected: {name[:60]} [{record_id}]")

        logger.info(f"  Transitioned {selected_count} candidates to Selected")
        return selected_count

    except Exception as e:
        logger.warning(f"Could not select candidates: {e}")
        return 0


def _print_report(report: dict) -> None:
    """Affiche le résumé final (jamais de secrets)."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("UNOSNAKE AUTOPILOT — REPORT")
    logger.info("-" * 40)
    logger.info(f"  Mode:                   {report.get('mode', '?')}")
    logger.info(f"  Candidates discovered:  {report['candidates_discovered']}")
    logger.info(f"  Candidates accepted:    {report['candidates_accepted']}")
    logger.info(f"  Duplicates skipped:     {report['duplicates_skipped']}")
    logger.info(f"  Below score threshold:  {report['below_threshold']}")
    logger.info(f"  Airtable records:       {report['airtable_created']}")
    logger.info(f"  Selected:               {report.get('selected', 0)}")
    logger.info(f"  Pinterest enabled:      {report['pinterest_enabled']}")
    logger.info(f"  Pinterest API calls:    {report.get('pinterest_api_calls', 'N/A')}")
    logger.info(f"  Pins published:         {report['pins_published']}")
    logger.info(f"  Pins skipped:           {report['pins_skipped']}")
    logger.info(f"  Errors:                 {len(report['errors'])}")
    if report["errors"]:
        for e in report["errors"][:5]:
            logger.info(f"    • {e}")
    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="UnoSnake Autopilot")
    parser.add_argument("--dry-run", action="store_true", help="No writes to Pinterest/Airtable Published")
    parser.add_argument(
        "--live-pilot", action="store_true",
        help="Real data validation: Airtable writes (max 1), Pinterest HARD DISABLED",
    )
    args = parser.parse_args()

    if args.live_pilot and args.dry_run:
        print("ERROR: --live-pilot and --dry-run are mutually exclusive")
        sys.exit(1)

    result = run_autopilot(dry_run=args.dry_run, live_pilot=args.live_pilot)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Exit code: 0 if no fatal errors, 1 otherwise
    fatal_errors = [e for e in result["errors"] if "missing" in e.lower() or "config" in e.lower()]
    sys.exit(1 if fatal_errors else 0)
