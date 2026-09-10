"""
UnoSnake — Content Generator (déterministe, gratuit).

Transforme un candidat produit en contenu Pinterest prêt à publier.
Rotation basée sur l'ASIN → même produit = même contenu (stable).
Aucune donnée inventée. Aucun fournisseur IA externe.
"""

import hashlib
import re


def _safe_format(template: str, **kwargs) -> str:
    """String formatting via replace — sandbox-safe."""
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result


from scripts.content.templates import (
    TITLE_TEMPLATES,
    TITLE_TEMPLATES_NO_STYLE,
    DESCRIPTION_TEMPLATES,
    DESCRIPTION_TEMPLATES_NO_STYLE,
    HASHTAGS_BY_STYLE,
    HASHTAGS_BY_CATEGORY,
    HASHTAGS_GENERIC,
    STYLE_ADJECTIVES,
    ROOM_KEYWORDS,
)


def generate_content(candidate: dict) -> dict:
    """
    Génère tout le contenu pour un candidat produit.

    Returns:
        dict : pinterest_title, pinterest_description, hashtags,
               description, content_metadata
    """
    product_name = _clean_product_name(candidate.get("title", ""))
    asin = candidate.get("asin", "") or ""
    snippet = candidate.get("snippet", "") or ""
    style = (
        candidate.get("style_detected")
        or candidate.get("niche_style")
        or ""
    )
    category = (
        candidate.get("category_detected")
        or candidate.get("niche_category")
        or ""
    )

    rotation_idx = _deterministic_index(asin)
    room = _detect_room(product_name + " " + snippet)
    style_adj = STYLE_ADJECTIVES.get(style, "")
    has_style = bool(style_adj) and style not in ("Unknown", "")

    product_short = _truncate(product_name, 60) if product_name else "cette pièce déco"
    product_lower = product_short[0].lower() + product_short[1:] if len(product_short) > 1 else product_short

    pinterest_title = _generate_title(product_short, style_adj, has_style, room, rotation_idx)
    pinterest_description = _generate_description(product_short, product_lower, style_adj, has_style, room, rotation_idx)
    hashtags = _generate_hashtags(style, category, room, rotation_idx)
    description = _generate_editorial_description(product_name, snippet, style_adj, has_style)

    return {
        "pinterest_title": pinterest_title,
        "pinterest_description": pinterest_description,
        "hashtags": hashtags,
        "description": description,
        "content_metadata": {
            "rotation_index": rotation_idx,
            "style_used": style,
            "style_adj": style_adj,
            "category_used": category,
            "room_detected": room,
            "product_name_used": product_short,
        },
    }


def _generate_title(product, style_adj, has_style, room, idx):
    """Pinterest Title (40–100 chars)."""
    templates = TITLE_TEMPLATES if has_style else TITLE_TEMPLATES_NO_STYLE
    template = templates[idx % len(templates)]
    title = _safe_format(template, product=product, style=style_adj, category="", room=room or "la maison")
    title = re.sub(r"\s{2,}", " ", title).strip()
    return _truncate(title, 100)


def _generate_description(product, product_lower, style_adj, has_style, room, idx):
    """Pinterest Description (100–300 chars)."""
    templates = DESCRIPTION_TEMPLATES if has_style else DESCRIPTION_TEMPLATES_NO_STYLE
    template = templates[idx % len(templates)]
    desc = _safe_format(template, product=product, product_lower=product_lower, style_adj=style_adj or "élégant", room=room or "la maison")
    desc = re.sub(r"\s{2,}", " ", desc).strip()
    return _truncate(desc, 300)


def _generate_hashtags(style, category, room, idx):
    """5–10 hashtags uniques."""
    tags = []

    style_tags = HASHTAGS_BY_STYLE.get(style, [])
    if style_tags:
        start = idx % len(style_tags)
        for i in range(min(3, len(style_tags))):
            tags.append(style_tags[(start + i) % len(style_tags)])

    cat_tags = HASHTAGS_BY_CATEGORY.get(category, [])
    if cat_tags:
        start = idx % len(cat_tags)
        for i in range(min(2, len(cat_tags))):
            tags.append(cat_tags[(start + i) % len(cat_tags)])

    remaining = max(0, 7 - len(tags))
    start = idx % len(HASHTAGS_GENERIC)
    for i in range(remaining):
        tag = HASHTAGS_GENERIC[(start + i) % len(HASHTAGS_GENERIC)]
        if tag not in tags:
            tags.append(tag)

    seen = set()
    unique = []
    for tag in tags:
        nl = tag.lower()
        if nl not in seen:
            seen.add(nl)
            unique.append(tag)

    return unique[:10]


def _generate_editorial_description(product_name, snippet, style_adj, has_style):
    """Description Airtable : factuelle, pas de spam."""
    parts = []
    if product_name:
        parts.append(product_name + ".")
    if snippet and snippet.lower() != (product_name or "").lower():
        clean = snippet.strip().rstrip(".")
        if len(clean) > 10:
            parts.append(clean + ".")
    if has_style:
        parts.append("Style " + style_adj + ".")
    parts.append("Sélection UnoSnake.")
    return " ".join(parts)[:500]


def _clean_product_name(title):
    if not title:
        return ""
    title = title.strip()
    for prefix in ["Amazon.fr :", "Amazon.fr:", "Amazon.fr -", "Amazon.co.uk :"]:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()

    # Strip Amazon category suffix (e.g. ": Amazon.fr: Cuisine et Maison")
    amazon_suffix_patterns = [
        ": Amazon.fr:", " : Amazon.fr:", "- Amazon.fr:",
        ": Amazon.co.uk:", " : Amazon.co.uk:",
    ]
    for suffix in amazon_suffix_patterns:
        if suffix in title:
            title = title[:title.index(suffix)].strip()
    return title


def _detect_room(text):
    text_lower = text.lower()
    for keyword, room_name in ROOM_KEYWORDS.items():
        if keyword in text_lower:
            return room_name
    return ""


def _deterministic_index(asin):
    if not asin:
        return 0
    digest = hashlib.md5(asin.encode()).hexdigest()
    return int(digest[:8], 16)


def _truncate(text, max_len):
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rsplit(" ", 1)[0] + "…"
