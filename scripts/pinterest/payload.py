"""
UnoSnake — Pinterest Pin Payload Builder.

Construit le payload conforme à l'API Pinterest v5 POST /pins.
Le lien du Pin pointe directement vers l'Affiliate URL Amazon.
Aucun redirect UnoSnake.

API docs : https://developers.pinterest.com/docs/api/v5/#operation/pins/create
"""

import logging

logger = logging.getLogger("unosnake")


def build_pin_payload(
    board_id: str,
    title: str,
    description: str,
    link: str,
    image_url: str | None = None,
    alt_text: str = "",
) -> dict:
    """
    Construit le payload pour POST /pins (Pinterest v5).

    Args:
        board_id: ID du board Pinterest cible.
        title: Titre du Pin (Pinterest Title).
        description: Description du Pin (Pinterest Description + hashtags).
        link: URL de destination (= Affiliate URL Amazon). PAS de redirect.
        image_url: URL de l'image source (optionnel).
        alt_text: Texte alternatif pour l'image.

    Returns:
        dict payload conforme à l'API Pinterest v5.

    Raises:
        ValueError si board_id, title ou link manquent.
    """
    if not board_id:
        raise ValueError("board_id is required")
    if not title:
        raise ValueError("title is required")
    if not link:
        raise ValueError("link (affiliate URL) is required")

    payload = {
        "board_id": board_id,
        "title": title[:100],  # Pinterest max 100 chars
        "description": description[:500] if description else "",
        "link": link,
    }

    # Image source (Pinterest v5 media_source)
    if image_url:
        payload["media_source"] = {
            "source_type": "image_url",
            "url": image_url,
        }

    if alt_text:
        payload["alt_text"] = alt_text[:500]

    return payload


def validate_pin_payload(payload: dict) -> tuple[bool, str]:
    """
    Valide le format d'un payload Pin avant envoi.

    Vérifie :
    1. board_id présent
    2. title présent et ≤ 100 chars
    3. link présent et HTTPS
    4. link contient /ref=nosim?tag= (affiliate)
    5. description ≤ 500 chars

    Returns:
        (is_valid, reason)
    """
    if not payload.get("board_id"):
        return False, "Missing board_id"

    title = payload.get("title", "")
    if not title:
        return False, "Missing title"
    if len(title) > 100:
        return False, f"Title too long ({len(title)} > 100)"

    link = payload.get("link", "")
    if not link:
        return False, "Missing link (affiliate URL)"
    if not link.startswith("https://"):
        return False, "Link must use HTTPS"
    if "/ref=nosim?tag=" not in link:
        return False, "Link must be a valid affiliate URL (/ref=nosim?tag=)"

    desc = payload.get("description", "")
    if len(desc) > 500:
        return False, f"Description too long ({len(desc)} > 500)"

    return True, "OK"


def build_pin_from_candidate(
    candidate: dict,
    content: dict,
    board_id: str,
    affiliate_url: str,
) -> dict:
    """
    Raccourci : construit un payload Pin depuis un candidat scoré + contenu généré.

    Args:
        candidate: dict du candidat (title, asin, etc.)
        content: dict retourné par generate_content()
        board_id: ID du board Pinterest
        affiliate_url: URL affiliée validée (Phase 5)

    Returns:
        dict payload Pin.
    """
    # Combiner description + hashtags
    desc = content.get("pinterest_description", "")
    hashtags = content.get("hashtags", [])
    if hashtags:
        desc = desc + "\n\n" + " ".join(hashtags)

    return build_pin_payload(
        board_id=board_id,
        title=content.get("pinterest_title", candidate.get("title", "")[:100]),
        description=desc,
        link=affiliate_url,
        image_url=candidate.get("image_url"),
        alt_text=content.get("pinterest_title", ""),
    )
