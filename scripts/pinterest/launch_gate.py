"""
UnoSnake — Pinterest Launch Gate.

Responsabilité unique : déterminer si UnoSnake est autorisé à publier
en PRODUCTION sur Pinterest.

Principe de sécurité :
- Par défaut, tout est BLOCKED.
- READY uniquement si TOUS les checks critiques passent.
- Un seul check critique en échec → ready = false.
- Ne jamais déduire "production ready" du seul fait que le token existe.
- Ne jamais exposer le token dans les logs ou le rapport.

Le Launch Gate NE PUBLIE PAS. Il répond seulement : READY / BLOCKED.
"""

import logging

logger = logging.getLogger("unosnake")


class LaunchGateResult:
    """Résultat de l'évaluation du Launch Gate."""

    def __init__(self, ready: bool, reasons: list[str], checks: dict[str, bool]):
        self.ready = ready
        self.reasons = reasons
        self.checks = checks

    def to_dict(self) -> dict:
        return {
            "ready": self.ready,
            "reasons": self.reasons,
            "checks": self.checks,
        }

    def __repr__(self) -> str:
        return f"LaunchGateResult(ready={self.ready}, checks={sum(self.checks.values())}/{len(self.checks)})"


# ══════════════════════════════════════════════════════════
#  Checks critiques : TOUS doivent passer pour READY
# ══════════════════════════════════════════════════════════
CRITICAL_CHECKS = [
    "pinterest_enabled",
    "production_mode",       # not sandbox
    "access_token_present",
    "token_verifiable",
    "board_id_present",
    "board_accessible",
    "payload_validation_available",
    "affiliate_validation_available",
    "state_machine_available",
    "dry_run_disabled",
    "live_pilot_disabled",
    "test_mode_disabled",
]


def evaluate_launch_gate(
    *,
    pinterest_enabled: bool,
    pinterest_sandbox: bool,
    access_token: str,
    board_id: str,
    test_mode: bool,
    live_pilot: bool,
    dry_run: bool,
    client_factory=None,
    verify_token_fn=None,
    list_boards_fn=None,
    skip_network: bool = False,
) -> LaunchGateResult:
    """
    Évalue si la publication production Pinterest est autorisée.

    Args:
        pinterest_enabled: PINTEREST_ENABLED.
        pinterest_sandbox: PINTEREST_SANDBOX (True = sandbox → BLOCKED prod).
        access_token: Token Pinterest (jamais logué).
        board_id: PINTEREST_BOARD_ID.
        test_mode: TEST_MODE.
        live_pilot: LIVE_PILOT.
        dry_run: DRY_RUN effectif.
        client_factory: callable(access_token, sandbox) -> client, optionnel.
                        Utilisé pour vérifier token + board via l'API réelle.
        verify_token_fn: override pour tests — callable() -> dict {"ok": bool}.
        list_boards_fn: override pour tests — callable() -> list[dict].
        skip_network: si True, ne fait aucun appel réseau (token_verifiable
                      et board_accessible seront False sauf si fn fournies).

    Returns:
        LaunchGateResult.
    """
    checks: dict[str, bool] = {}
    reasons: list[str] = []

    # ── 1. Pinterest enabled ──
    checks["pinterest_enabled"] = bool(pinterest_enabled)
    if not pinterest_enabled:
        reasons.append("PINTEREST_ENABLED is false")

    # ── 2. Production mode (not sandbox) ──
    checks["production_mode"] = not pinterest_sandbox
    if pinterest_sandbox:
        reasons.append("PINTEREST_SANDBOX is true (production requires sandbox=false)")

    # ── 3. Access token present ──
    checks["access_token_present"] = bool(access_token and access_token.strip())
    if not checks["access_token_present"]:
        reasons.append("Pinterest access token is missing")

    # ── 4. Test mode disabled ──
    checks["test_mode_disabled"] = not test_mode
    if test_mode:
        reasons.append("TEST_MODE is true (must be false for production)")

    # ── 5. Live pilot disabled ──
    checks["live_pilot_disabled"] = not live_pilot
    if live_pilot:
        reasons.append("LIVE_PILOT is true (must be false for production)")

    # ── 6. Dry run disabled ──
    checks["dry_run_disabled"] = not dry_run
    if dry_run:
        reasons.append("DRY_RUN is true (must be false for production)")

    # ── 7. Board ID present ──
    checks["board_id_present"] = bool(board_id and board_id.strip())
    if not checks["board_id_present"]:
        reasons.append("PINTEREST_BOARD_ID is missing")

    # ── 8. Payload validation available ──
    checks["payload_validation_available"] = _check_payload_validation()
    if not checks["payload_validation_available"]:
        reasons.append("Pinterest payload validation unavailable")

    # ── 9. Affiliate URL validation available ──
    checks["affiliate_validation_available"] = _check_affiliate_validation()
    if not checks["affiliate_validation_available"]:
        reasons.append("Affiliate URL validation unavailable")

    # ── 10. State machine available ──
    checks["state_machine_available"] = _check_state_machine()
    if not checks["state_machine_available"]:
        reasons.append("Airtable state machine unavailable")

    # ── 11 & 12. Token verifiable + board accessible (network) ──
    # Only attempt if token present, not sandbox, and network allowed.
    token_verifiable = False
    board_accessible = False

    can_check_network = (
        checks["access_token_present"]
        and not skip_network
        and (client_factory is not None or verify_token_fn is not None or list_boards_fn is not None)
    )

    if can_check_network:
        # Verify token
        try:
            if verify_token_fn is not None:
                result = verify_token_fn()
            else:
                client = client_factory(access_token, pinterest_sandbox)
                result = client.verify_token()

            if isinstance(result, dict) and result.get("ok"):
                token_verifiable = True
            else:
                status = result.get("status") if isinstance(result, dict) else None
                if status in (401, 403):
                    reasons.append("Pinterest authentication/access unavailable")
                else:
                    reasons.append("Pinterest token verification failed")
        except Exception:
            reasons.append("Pinterest token verification error")

        # Verify board (only if token OK)
        if token_verifiable and checks["board_id_present"]:
            try:
                if list_boards_fn is not None:
                    boards = list_boards_fn()
                else:
                    client = client_factory(access_token, pinterest_sandbox)
                    boards = client.list_boards()

                board_ids = {b.get("id", "") for b in boards} if boards else set()
                if board_id in board_ids:
                    board_accessible = True
                else:
                    reasons.append(f"Configured board not accessible/found")
            except Exception:
                reasons.append("Pinterest board verification error")
    else:
        if not skip_network and checks["access_token_present"]:
            reasons.append("Pinterest API not reachable (no client provided)")

    checks["token_verifiable"] = token_verifiable
    checks["board_accessible"] = board_accessible

    # ── Verdict : tous les checks critiques doivent passer ──
    all_critical_pass = all(checks.get(c, False) for c in CRITICAL_CHECKS)
    ready = all_critical_pass

    if ready:
        reasons = ["All critical checks passed — production publication authorized"]

    return LaunchGateResult(ready=ready, reasons=reasons, checks=checks)


def format_readiness_report(result: LaunchGateResult, extra: dict | None = None) -> str:
    """
    Génère un rapport lisible READY/BLOCKED.
    Ne révèle JAMAIS de token.
    """
    c = result.checks
    lines = []
    lines.append("UNOSNAKE PRODUCTION READINESS")
    lines.append("=" * 29)
    lines.append("")
    lines.append("Pipeline:")
    lines.append(f"  Payload validation:  {'PASS' if c.get('payload_validation_available') else 'FAIL'}")
    lines.append(f"  Affiliate validation: {'PASS' if c.get('affiliate_validation_available') else 'FAIL'}")
    lines.append(f"  State machine:       {'PASS' if c.get('state_machine_available') else 'FAIL'}")
    lines.append("")
    lines.append("Pinterest:")
    lines.append(f"  Token present:       {'PASS' if c.get('access_token_present') else 'FAIL'}")
    lines.append(f"  Token verifiable:    {'PASS' if c.get('token_verifiable') else 'FAIL'}")
    lines.append(f"  Board present:       {'PASS' if c.get('board_id_present') else 'FAIL'}")
    lines.append(f"  Board accessible:    {'PASS' if c.get('board_accessible') else 'FAIL'}")
    lines.append(f"  Production endpoint: {'PASS' if c.get('production_mode') else 'FAIL'}")
    lines.append("")
    lines.append("Safety:")
    lines.append(f"  Pinterest enabled:   {'PASS' if c.get('pinterest_enabled') else 'FAIL'}")
    lines.append(f"  Dry run disabled:    {'PASS' if c.get('dry_run_disabled') else 'FAIL'}")
    lines.append(f"  Live pilot disabled: {'PASS' if c.get('live_pilot_disabled') else 'FAIL'}")
    lines.append(f"  Test mode disabled:  {'PASS' if c.get('test_mode_disabled') else 'FAIL'}")
    lines.append("")
    lines.append("Launch Gate:")
    lines.append(f"  {'READY' if result.ready else 'BLOCKED'}")
    lines.append("")
    lines.append("Reasons:")
    for r in result.reasons:
        lines.append(f"  - {r}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════
#  Availability checks (imports, no network)
# ══════════════════════════════════════════════════════════

def _check_payload_validation() -> bool:
    try:
        from scripts.pinterest.payload import validate_pin_payload
        return callable(validate_pin_payload)
    except Exception:
        return False


def _check_affiliate_validation() -> bool:
    try:
        from scripts.amazon.asin import validate_affiliate_url, build_affiliate_url
        return callable(validate_affiliate_url) and callable(build_affiliate_url)
    except Exception:
        return False


def _check_state_machine() -> bool:
    try:
        from scripts.airtable.state_machine import can_transition, mark_published
        return callable(can_transition) and callable(mark_published)
    except Exception:
        return False
