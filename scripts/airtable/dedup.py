"""
UnoSnake — Déduplication Airtable.

Vérifie si un produit existe déjà dans la base avant création.

Clés de déduplication (par priorité) :
1. ASIN (clé primaire)
2. URL Amazon normalisée (fallback si ASIN absent)
3. Combinaison titre + URL (dernier recours)
"""

import logging

logger = logging.getLogger("unosnake")


def is_duplicate(
    asin: str | None,
    normalized_url: str | None,
    title: str | None,
    existing_asins: set,
    existing_urls: set,
) -> tuple[bool, str]:
    """
    Vérifie si un candidat est un doublon.

    Args:
        asin: ASIN du candidat (peut être None).
        normalized_url: URL Amazon normalisée (peut être None).
        title: Titre du produit (peut être None).
        existing_asins: Set d'ASINs déjà dans Airtable.
        existing_urls: Set d'URLs normalisées déjà dans Airtable.

    Returns:
        Tuple (is_dup: bool, reason: str).
        reason est vide si pas de doublon.
    """
    # 1. Check ASIN (clé primaire)
    if asin and asin in existing_asins:
        return True, f"ASIN {asin} already exists"

    # 2. Check URL normalisée
    if normalized_url and normalized_url in existing_urls:
        return True, f"URL {normalized_url} already exists"

    return False, ""


def build_existing_index(records: list[dict], extract_asin_fn, normalize_url_fn) -> tuple[set, set]:
    """
    Construit les index de déduplication à partir des records Airtable existants.

    Args:
        records: Liste de records Airtable (chaque record a "fields").
        extract_asin_fn: Fonction extract_asin(url) -> str | None.
        normalize_url_fn: Fonction normalize_amazon_url(url) -> str | None.

    Returns:
        Tuple (existing_asins: set, existing_urls: set).
    """
    existing_asins = set()
    existing_urls = set()

    for record in records:
        fields = record.get("fields", {})
        amazon_url = fields.get("Amazon URL", "")

        if not amazon_url:
            continue

        # Index ASIN
        asin = extract_asin_fn(amazon_url)
        if asin:
            existing_asins.add(asin)

        # Index URL normalisée
        norm = normalize_url_fn(amazon_url)
        if norm:
            existing_urls.add(norm)

    return existing_asins, existing_urls


def check_candidate_batch(
    candidates: list[dict],
    existing_asins: set,
    existing_urls: set,
    extract_asin_fn,
    normalize_url_fn,
) -> tuple[list[dict], list[dict]]:
    """
    Filtre un batch de candidats en séparant nouveaux et doublons.

    Args:
        candidates: Liste de candidats (chacun a "url", "asin", "title").
        existing_asins: Set d'ASINs existants.
        existing_urls: Set d'URLs normalisées existantes.
        extract_asin_fn: Fonction extract_asin.
        normalize_url_fn: Fonction normalize_amazon_url.

    Returns:
        Tuple (new_candidates, duplicates).
        Chaque doublon a un champ "duplicate_reason" ajouté.
    """
    new = []
    duplicates = []

    # Aussi tracker les ASINs/URLs dans ce batch pour éviter les doublons intra-batch
    batch_asins = set()
    batch_urls = set()

    for candidate in candidates:
        asin = candidate.get("asin") or extract_asin_fn(candidate.get("url", ""))
        normalized_url = normalize_url_fn(candidate.get("url", ""))
        title = candidate.get("title", "")

        # Check contre Airtable existant
        dup, reason = is_duplicate(asin, normalized_url, title, existing_asins, existing_urls)

        if dup:
            candidate["duplicate_reason"] = reason
            duplicates.append(candidate)
            logger.info(f"  DUPLICATE → SKIP: {reason}")
            continue

        # Check intra-batch
        if asin and asin in batch_asins:
            candidate["duplicate_reason"] = f"ASIN {asin} already in this batch"
            duplicates.append(candidate)
            logger.info(f"  DUPLICATE → SKIP (intra-batch): ASIN {asin}")
            continue

        if normalized_url and normalized_url in batch_urls:
            candidate["duplicate_reason"] = f"URL {normalized_url} already in this batch"
            duplicates.append(candidate)
            logger.info(f"  DUPLICATE → SKIP (intra-batch): URL {normalized_url}")
            continue

        # Nouveau produit
        new.append(candidate)
        if asin:
            batch_asins.add(asin)
        if normalized_url:
            batch_urls.add(normalized_url)

    return new, duplicates
