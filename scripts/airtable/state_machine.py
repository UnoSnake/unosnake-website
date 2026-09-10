"""
UnoSnake — Airtable State Machine.

Transitions autorisées :
  New → Selected
  Selected → Published  (uniquement après confirmation Pinterest)
  Selected → Rejected   (en cas d'erreur critique)
  New → Rejected

Transitions INTERDITES :
  Published → quoi que ce soit (un produit publié est final)
  * → New (pas de retour en arrière)
"""

import logging

logger = logging.getLogger("unosnake")

# Transitions autorisées : (from, to)
ALLOWED_TRANSITIONS = {
    ("New", "Selected"),
    ("New", "Rejected"),
    ("Selected", "Published"),
    ("Selected", "Rejected"),
}


def can_transition(current_status: str, target_status: str) -> tuple[bool, str]:
    """
    Vérifie si une transition de statut est autorisée.

    Returns:
        (allowed, reason)
    """
    if current_status == target_status:
        return False, f"Already in status {current_status}"

    if (current_status, target_status) in ALLOWED_TRANSITIONS:
        return True, "OK"

    return False, f"Transition {current_status} → {target_status} is not allowed"


def mark_selected(client, record_id: str, current_status: str) -> bool:
    """Marque un record comme Selected."""
    allowed, reason = can_transition(current_status, "Selected")
    if not allowed:
        logger.warning(f"Cannot mark {record_id} as Selected: {reason}")
        return False

    client.update_record(record_id, {"Status": "Selected"})
    logger.info(f"  {record_id}: {current_status} → Selected")
    return True


def mark_published(client, record_id: str, current_status: str, pin_id: str = "") -> bool:
    """
    Marque un record comme Published.

    UNIQUEMENT après confirmation réussie de la publication Pinterest.
    """
    allowed, reason = can_transition(current_status, "Published")
    if not allowed:
        logger.warning(f"Cannot mark {record_id} as Published: {reason}")
        return False

    fields = {
        "Status": "Published",
        "Published": True,
    }
    # Stocker le Pin ID si disponible (pas de nouveau champ — utiliser Description si nécessaire)

    client.update_record(record_id, fields)
    logger.info(f"  {record_id}: {current_status} → Published (Pin: {pin_id})")
    return True


def mark_rejected(client, record_id: str, current_status: str, reason: str = "") -> bool:
    """Marque un record comme Rejected."""
    allowed, transition_reason = can_transition(current_status, "Rejected")
    if not allowed:
        logger.warning(f"Cannot mark {record_id} as Rejected: {transition_reason}")
        return False

    client.update_record(record_id, {"Status": "Rejected"})
    logger.info(f"  {record_id}: {current_status} → Rejected ({reason})")
    return True
