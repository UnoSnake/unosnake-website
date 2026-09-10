"""
UnoSnake — Pinterest Publisher.

Orchestre la publication d'un Pin :
1. Vérifie le feature flag PINTEREST_ENABLED
2. Construit le payload
3. Valide le payload
4. Publie via l'API Pinterest v5
5. Confirme le succès
6. Met à jour Airtable (Published=true, Status=Published) UNIQUEMENT après confirmation

Règles :
- PINTEREST_ENABLED=false → prépare le payload mais ne publie PAS
- En cas d'échec Pinterest : Airtable reste en Selected / Published=False
- Un produit déjà Published ne doit JAMAIS être republié
- Le lien du Pin pointe vers l'Affiliate URL Amazon (pas de redirect UnoSnake)
"""

import logging

from scripts.pinterest.client import PinterestClient
from scripts.pinterest.payload import (
    build_pin_from_candidate,
    validate_pin_payload,
)

logger = logging.getLogger("unosnake")


class PublishResult:
    """Résultat d'une tentative de publication."""

    def __init__(
        self,
        success: bool,
        pin_id: str = "",
        pin_url: str = "",
        error: str = "",
        skipped: bool = False,
        skip_reason: str = "",
        payload: dict | None = None,
    ):
        self.success = success
        self.pin_id = pin_id
        self.pin_url = pin_url
        self.error = error
        self.skipped = skipped
        self.skip_reason = skip_reason
        self.payload = payload

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "pin_id": self.pin_id,
            "pin_url": self.pin_url,
            "error": self.error,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


def publish_pin(
    candidate: dict,
    content: dict,
    affiliate_url: str,
    board_id: str,
    access_token: str,
    pinterest_enabled: bool = False,
    sandbox: bool = True,
    dry_run: bool = False,
) -> PublishResult:
    """
    Tente de publier un Pin Pinterest.

    Args:
        candidate: dict du candidat scoré.
        content: dict retourné par generate_content().
        affiliate_url: URL affiliée validée Phase 5.
        board_id: ID du board Pinterest cible.
        access_token: Token Pinterest (secret — jamais loggé).
        pinterest_enabled: Feature flag. False → payload préparé mais non envoyé.
        sandbox: True = API sandbox Pinterest.
        dry_run: True = aucune action (log only).

    Returns:
        PublishResult.
    """
    # ── Construire le payload ──
    try:
        payload = build_pin_from_candidate(
            candidate=candidate,
            content=content,
            board_id=board_id,
            affiliate_url=affiliate_url,
        )
    except ValueError as e:
        return PublishResult(success=False, error=f"Payload build error: {e}")

    # ── Valider le payload ──
    valid, reason = validate_pin_payload(payload)
    if not valid:
        return PublishResult(success=False, error=f"Payload validation failed: {reason}", payload=payload)

    # ── Dry run → stop ──
    if dry_run:
        logger.info(f"  [DRY] Pinterest payload ready: {payload.get('title', '')[:60]}")
        return PublishResult(
            success=False,
            skipped=True,
            skip_reason="dry_run",
            payload=payload,
        )

    # ── Feature flag off → stop ──
    if not pinterest_enabled:
        logger.info("  Pinterest disabled (PINTEREST_ENABLED=false) — payload prepared but not sent")
        return PublishResult(
            success=False,
            skipped=True,
            skip_reason="pinterest_disabled",
            payload=payload,
        )

    # ── Token manquant → stop ──
    if not access_token:
        return PublishResult(
            success=False,
            skipped=True,
            skip_reason="no_access_token",
            payload=payload,
        )

    # ── Publier ──
    try:
        client = PinterestClient(
            access_token=access_token,
            sandbox=sandbox,
        )

        logger.info(f"  Publishing to Pinterest ({'sandbox' if sandbox else 'production'})...")
        response = client.create_pin(payload)

        pin_id = response.get("id", "")
        if not pin_id:
            return PublishResult(
                success=False,
                error="Pinterest returned no pin ID",
                payload=payload,
            )

        pin_url = f"https://www.pinterest.com/pin/{pin_id}/"
        logger.info(f"  ✅ Pin created: {pin_id}")

        return PublishResult(
            success=True,
            pin_id=pin_id,
            pin_url=pin_url,
            payload=payload,
        )

    except Exception as e:
        logger.error(f"  Pinterest API error: {e}")
        return PublishResult(
            success=False,
            error=str(e),
            payload=payload,
        )
