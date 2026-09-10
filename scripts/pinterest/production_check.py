"""
UnoSnake — Production Readiness Check (read-only).

Runs the Launch Gate and prints a READY/BLOCKED report.
NEVER creates a Pin. NEVER modifies Airtable.

Usage:
    python -m scripts.pinterest.production_check
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.config import (
    PINTEREST_ENABLED,
    PINTEREST_SANDBOX,
    PINTEREST_ACCESS_TOKEN,
    PINTEREST_BOARD_ID,
    TEST_MODE,
    LIVE_PILOT,
)
from scripts.pinterest.launch_gate import evaluate_launch_gate, format_readiness_report

logger = logging.getLogger("unosnake")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    def _client_factory(token, sandbox):
        from scripts.pinterest.client import PinterestClient
        return PinterestClient(access_token=token, sandbox=sandbox)

    gate = evaluate_launch_gate(
        pinterest_enabled=PINTEREST_ENABLED,
        pinterest_sandbox=PINTEREST_SANDBOX,
        access_token=PINTEREST_ACCESS_TOKEN,
        board_id=PINTEREST_BOARD_ID,
        test_mode=TEST_MODE,
        live_pilot=LIVE_PILOT,
        dry_run=False,
        client_factory=_client_factory,
    )

    report = format_readiness_report(gate)
    print(report)

    print()
    print("=" * 40)
    print(f"LAUNCH GATE: {'READY' if gate.ready else 'BLOCKED'}")
    print("=" * 40)

    # This check NEVER creates a Pin — it only reports.
    # Exit 0 always (BLOCKED is a valid, expected answer, not a failure).
    return 0


if __name__ == "__main__":
    sys.exit(main())
