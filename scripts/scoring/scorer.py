"""
UnoSnake — Scoring produit (0–100).

Score chaque candidat selon son adéquation avec la marque UnoSnake.
Ne fabrique JAMAIS de données absentes — utilise un score neutre.

Échelle :
  0–40   → rejeté (MIN_PRODUCT_SCORE par défaut 65)
  40–64  → faible
  65–79  → acceptable
  80–100 → excellent

Composantes (total = 100) :
  Style match       : 25 pts
  Category match    : 20 pts
  Position          : 15 pts
  Title quality     : 15 pts
  Rating            : 15 pts
  Review count      : 10 pts
"""

import re

# ── Mots-clés UnoSnake par style ──
STYLE_KEYWORDS: dict[str, list[str]] = {
    "Scandinavian": [
        "scandinave", "scandinavian", "nordique", "nordic", "hygge",
        "bois clair", "blanc", "épuré",
    ],
    "Japandi": [
        "japandi", "japonais", "japan", "zen", "wabi-sabi", "wabi sabi",
    ],
    "Warm Minimalism": [
        "minimaliste", "minimalism", "minimalist", "warm", "chaleureux",
        "neutre", "beige", "naturel", "organique",
    ],
    "Bohemian": [
        "bohème", "bohemian", "boho", "macramé", "rotin", "rattan",
        "tressé", "ethnique", "artisanal",
    ],
    "Natural": [
        "naturel", "natural", "bois", "wood", "bambou", "bamboo",
        "plante", "végétal", "osier", "lin", "jute",
    ],
    "Modern": [
        "design", "moderne", "modern", "contemporain", "géométrique",
        "métal", "élégant", "aesthetic",
    ],
}

# ── Catégories déco ──
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Décoration": ["décoration", "déco", "deco", "decor", "ornement", "decoration"],
    "Mobilier": ["meuble", "table", "chaise", "bureau", "étagère", "shelf", "console"],
    "Éclairage": ["lampe", "lamp", "luminaire", "bougeoir", "guirlande", "led", "applique"],
    "Accessoires": ["miroir", "cadre", "horloge", "porte-", "crochet", "patère"],
    "Rangement": ["rangement", "panier", "boîte", "organisateur", "organizer", "étagère"],
    "Textile": ["coussin", "tapis", "rideau", "plaid", "housse", "nappe", "linge"],
    "Objets déco": ["vase", "figurine", "statuette", "bougie", "pot", "plateau", "photophore"],
}

# ── Mots-clés de pertinence déco (bonus) ──
DECO_RELEVANCE_KEYWORDS = [
    "décoration", "déco", "deco", "decor", "maison", "intérieur", "interior",
    "home", "salon", "chambre", "bedroom", "living", "cuisine", "kitchen",
    "salle de bain", "bathroom", "entrée", "bureau",
]


def score_candidate(
    candidate: dict,
    existing_asins: set | None = None,
    recently_published_categories: list[str] | None = None,
) -> dict:
    """
    Calcule le score UnoSnake d'un candidat (0–100).

    Args:
        candidate: dict avec "url", "title", "snippet", "position", etc.
        existing_asins: ASINs déjà connus (duplicate → score 0).
        recently_published_categories: catégories récemment publiées (diversité).

    Returns:
        dict enrichi avec "score" (int 0–100), "score_reasons" (list[str]),
        "style_detected", "category_detected", "is_duplicate".
    """
    title = (candidate.get("title") or "").lower()
    snippet = (candidate.get("snippet") or "").lower()
    text = f"{title} {snippet}"
    position = candidate.get("position", 10)
    rating = candidate.get("rating")
    rating_count = candidate.get("rating_count")

    reasons: list[str] = []
    components: dict[str, float] = {}

    # ── 1. Style match (0–25 pts) ──
    style, style_pts = _score_style(text)
    components["style"] = style_pts
    if style_pts >= 20:
        reasons.append(f"Strong {style} style match (+{style_pts:.0f})")
    elif style_pts >= 10:
        reasons.append(f"Moderate {style} style (+{style_pts:.0f})")
    else:
        reasons.append(f"Weak style signal (+{style_pts:.0f})")

    # ── 2. Category match (0–20 pts) ──
    category, cat_pts = _score_category(text)
    components["category"] = cat_pts
    if cat_pts >= 15:
        reasons.append(f"Clear {category} category (+{cat_pts:.0f})")
    elif cat_pts > 0:
        reasons.append(f"Possible {category} category (+{cat_pts:.0f})")

    # ── 3. Position (0–15 pts) ──
    pos_pts = _score_position(position)
    components["position"] = pos_pts
    if pos_pts >= 12:
        reasons.append(f"Top position #{position} (+{pos_pts:.0f})")

    # ── 4. Title quality (0–15 pts) ──
    title_pts = _score_title_quality(candidate.get("title", ""))
    components["title_quality"] = title_pts
    if title_pts <= 5:
        reasons.append(f"Poor title quality (+{title_pts:.0f})")

    # ── 5. Rating (0–15 pts) — neutre 7.5 si absent ──
    rating_pts = _score_rating(rating)
    components["rating"] = rating_pts
    if rating is not None:
        reasons.append(f"Rating {rating}/5 (+{rating_pts:.0f})")
    else:
        reasons.append(f"No rating data (neutral +{rating_pts:.0f})")

    # ── 6. Review count (0–10 pts) — neutre 5 si absent ──
    review_pts = _score_reviews(rating_count)
    components["reviews"] = review_pts
    if rating_count is not None and rating_count >= 50:
        reasons.append(f"{rating_count} reviews (+{review_pts:.0f})")

    # ── Total brut ──
    raw_score = sum(components.values())

    # ── Bonus diversité (-5 si catégorie surreprésentée) ──
    diversity_adj = 0.0
    if recently_published_categories and category:
        cat_count = recently_published_categories.count(category)
        if cat_count >= 3:
            diversity_adj = -5.0
            reasons.append(f"Category {category} overrepresented ({cat_count}× recent) (-5)")
        elif cat_count == 0:
            diversity_adj = 3.0
            reasons.append(f"New category {category} (diversity bonus +3)")

    final_score = max(0, min(100, round(raw_score + diversity_adj)))

    # ── Duplicate check ──
    is_duplicate = False
    if existing_asins:
        asin = candidate.get("asin")
        if not asin:
            # Fallback extract
            from scripts.amazon.asin import extract_asin
            asin = extract_asin(candidate.get("url", ""))
        if asin and asin in existing_asins:
            is_duplicate = True
            final_score = 0
            reasons = [f"DUPLICATE: ASIN {asin} already exists"]

    result = dict(candidate)
    result.update({
        "score": final_score,
        "score_reasons": reasons,
        "score_components": components,
        "style_detected": style,
        "category_detected": category,
        "is_duplicate": is_duplicate,
    })
    return result


def rank_candidates(
    candidates: list[dict],
    existing_asins: set | None = None,
    min_score: int = 65,
    recently_published_categories: list[str] | None = None,
) -> list[dict]:
    """
    Score, filtre et trie les candidats.

    Returns:
        Liste triée par score décroissant.
        Doublons exclus. Scores < min_score exclus.
    """
    scored = [
        score_candidate(c, existing_asins, recently_published_categories)
        for c in candidates
    ]

    filtered = [
        c for c in scored
        if not c["is_duplicate"] and c["score"] >= min_score
    ]
    filtered.sort(key=lambda c: c["score"], reverse=True)

    return filtered


# ════════════════════════════════════════════
#  Composantes de score (fonctions pures)
# ════════════════════════════════════════════

def _score_style(text: str) -> tuple[str, float]:
    """Détecte le style UnoSnake (0–25 pts)."""
    best_style = "Unknown"
    best_pts = 0.0

    for style, keywords in STYLE_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text)
        if matches > 0:
            # 1 match = 12.5, 2+ = 25
            pts = min(25.0, matches * 12.5)
            if pts > best_pts:
                best_pts = pts
                best_style = style

    # Bonus si mots-clés déco génériques présents
    deco_matches = sum(1 for kw in DECO_RELEVANCE_KEYWORDS if kw in text)
    if deco_matches > 0 and best_pts == 0:
        best_pts = min(8.0, deco_matches * 4.0)
        best_style = "General Deco"

    return best_style, round(best_pts, 1)


def _score_category(text: str) -> tuple[str, float]:
    """Détecte la catégorie UnoSnake (0–20 pts)."""
    best_cat = "Autre"
    best_pts = 0.0

    for category, keywords in CATEGORY_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text)
        if matches > 0:
            pts = min(20.0, matches * 10.0)
            if pts > best_pts:
                best_pts = pts
                best_cat = category

    return best_cat, round(best_pts, 1)


def _score_position(position: int) -> float:
    """Score de position dans les résultats (0–15 pts)."""
    if position <= 0:
        return 7.5  # neutre
    if position == 1:
        return 15.0
    if position == 2:
        return 13.0
    if position == 3:
        return 11.0
    if position <= 5:
        return 9.0
    if position <= 10:
        return max(2.0, 15.0 - position * 1.3)
    return 2.0


def _score_title_quality(title: str) -> float:
    """Score la qualité du titre (0–15 pts)."""
    if not title:
        return 0.0
    length = len(title)
    if length < 10:
        return 3.0
    if length <= 80:
        return 15.0
    if length <= 120:
        return 11.0
    if length <= 150:
        return 8.0
    return 5.0


def _score_rating(rating: float | None) -> float:
    """Score du rating (0–15 pts). Neutre 7.5 si absent."""
    if rating is None:
        return 7.5
    if rating >= 4.5:
        return 15.0
    if rating >= 4.0:
        return 12.0
    if rating >= 3.5:
        return 9.0
    if rating >= 3.0:
        return 6.0
    return 3.0


def _score_reviews(rating_count: int | None) -> float:
    """Score du nombre d'avis (0–10 pts). Neutre 5 si absent."""
    if rating_count is None:
        return 5.0
    if rating_count >= 200:
        return 10.0
    if rating_count >= 100:
        return 8.0
    if rating_count >= 50:
        return 7.0
    if rating_count >= 20:
        return 5.0
    if rating_count >= 5:
        return 3.0
    return 1.0
