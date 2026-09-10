"""
UnoSnake — Discovery Engine.

Orchestrateur principal du pipeline de découverte produit.

Usage:
    python -m scripts.discovery.engine [--test] [--dry-run]
"""

import json
import os
import sys
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.config import (
    TEST_MODE,
    SERPER_API_KEY,
    NICHES_FILE,
    SEARCH_HISTORY_FILE,
    NICHE_COOLDOWN_HOURS,
    MAX_NICHES_PER_RUN,
    MAX_CANDIDATES_PER_SEARCH,
    MIN_PRODUCT_SCORE,
    MAX_ACCEPTED_PER_RUN,
    GOOGLE_TRENDS_RSS_URL,
    TRENDS_DECO_KEYWORDS,
    AIRTABLE_BASE_ID,
    AIRTABLE_TOKEN,
    AIRTABLE_TABLE_ID,
    AIRTABLE_API_URL,
    STATUS_NEW,
    AMAZON_PARTNER_TAG,
    AMAZON_DOMAIN,
)
from scripts.discovery.niche_pool import (
    load_niches, load_search_history, record_search, select_niches,
)
from scripts.discovery.trends import get_deco_trends
from scripts.discovery.serper_search import search_amazon_products
from scripts.amazon.asin import extract_asin, normalize_amazon_url, build_affiliate_url, validate_affiliate_url
from scripts.scoring.scorer import score_candidate, rank_candidates
from scripts.airtable.dedup import build_existing_index, check_candidate_batch
from scripts.content.generator import generate_content

logger = logging.getLogger("unosnake")


def resolve_product_name(candidate: dict) -> str:
    """
    Détermine le Product Name à enregistrer dans Airtable.

    Priorité :
    1. Titre Serper réel (>= 10 caractères)
    2. Snippet tronqué
    3. "Product {ASIN}"

    Ne retourne JAMAIS "Candidat UnoSnake - ...".
    """
    title = (candidate.get("title") or "").strip()

    if title and len(title) >= 10:
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

        if len(title) >= 10:
            return title[:200]

    snippet = (candidate.get("snippet") or "").strip()
    if snippet and len(snippet) >= 10:
        first_sentence = snippet.split(".")[0].strip()
        if len(first_sentence) >= 10:
            return first_sentence[:200]
        return snippet[:200]

    asin = candidate.get("asin", "")
    if asin:
        return f"Product {asin}"

    return "Unknown Product"


def run_discovery(
    test_mode: bool = None,
    dry_run: bool = False,
    max_accepted_override: int | None = None,
) -> dict:
    """
    Exécute le pipeline complet de découverte.

    Returns:
        dict résumé.
    """
    if test_mode is None:
        test_mode = TEST_MODE

    effective_max_accepted = max_accepted_override if max_accepted_override is not None else MAX_ACCEPTED_PER_RUN

    logger.info("=" * 60)
    logger.info("UNOSNAKE — DISCOVERY ENGINE v3")
    logger.info(f"Mode: {'TEST' if test_mode else 'PRODUCTION'}")
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Min score: {MIN_PRODUCT_SCORE}/100")
    logger.info(f"Max accepted/run: {MAX_ACCEPTED_PER_RUN}")
    if max_accepted_override is not None:
        logger.info(f"Max accepted OVERRIDE (pilot): {effective_max_accepted}")
    logger.info("=" * 60)

    summary = {
        "queries": [],
        "total_candidates": 0,
        "duplicates_skipped": 0,
        "below_threshold": 0,
        "accepted": 0,
        "records_created": 0,
        "errors": [],
        "selected_candidates": [],
    }

    # ── 1. Charger les niches ──
    niches = load_niches(NICHES_FILE)
    history = load_search_history(SEARCH_HISTORY_FILE)
    if not niches:
        logger.error(f"No niches found in {NICHES_FILE}")
        summary["errors"].append("No niches file")
        return summary
    logger.info(f"Loaded {len(niches)} niches, {len(history)} history entries")

    # ── 2. Tendances déco (optionnel) ──
    deco_trends = []
    try:
        deco_trends = get_deco_trends(GOOGLE_TRENDS_RSS_URL, TRENDS_DECO_KEYWORDS)
        if deco_trends:
            logger.info(f"Deco trends found: {deco_trends[:3]}")
        else:
            logger.info("No deco trends — using niche pool only (normal)")
    except Exception as e:
        logger.warning(f"Google Trends unavailable: {e}")

    # ── 3. Sélectionner les niches ──
    selected = select_niches(
        niches, history, max_niches=MAX_NICHES_PER_RUN,
        cooldown_hours=NICHE_COOLDOWN_HOURS,
    )
    if not selected:
        selected = [niches[0]]
        logger.warning("No niches available — forced first niche")

    if deco_trends:
        selected.insert(0, {"query": deco_trends[0], "style": "Unknown", "category": "Décoration"})
        logger.info(f"Added trend niche: {deco_trends[0]}")

    logger.info(f"Selected {len(selected)} niches for this run")
    for n in selected:
        logger.info(f"  • {n['query']} [{n.get('style', '?')}]")

    # ── 4. Charger l'index de dédup Airtable ──
    existing_asins = set()
    existing_urls = set()
    recently_published_categories: list[str] = []

    if AIRTABLE_TOKEN and AIRTABLE_BASE_ID:
        try:
            existing_asins, existing_urls, recently_published_categories = _fetch_dedup_index()
            logger.info(f"Dedup index: {len(existing_asins)} ASINs, {len(existing_urls)} URLs")
            if recently_published_categories:
                logger.info(f"Recent categories: {recently_published_categories[:10]}")
        except Exception as e:
            logger.warning(f"Could not fetch dedup index: {e}")

    # ── 5. Rechercher pour chaque niche (multi-candidats) ──
    all_candidates = []

    for niche in selected:
        query = niche["query"]
        logger.info(f"Searching: {query}")

        if not SERPER_API_KEY:
            logger.error("SERPER_API_KEY is empty")
            summary["errors"].append("Missing SERPER_API_KEY")
            break

        candidates = search_amazon_products(
            niche_query=query,
            api_key=SERPER_API_KEY,
            num_results=MAX_CANDIDATES_PER_SEARCH,
        )

        logger.info(f"  → {len(candidates)} Amazon results")
        summary["queries"].append({"query": query, "results": len(candidates)})
        record_search(SEARCH_HISTORY_FILE, query, len(candidates))

        for c in candidates:
            c["niche_style"] = niche.get("style", "")
            c["niche_category"] = niche.get("category", "")
            c["niche_query"] = query
            asin = extract_asin(c.get("url", ""))
            c["asin"] = asin

        all_candidates.extend(candidates)

    summary["total_candidates"] = len(all_candidates)
    logger.info(f"Total candidates found: {len(all_candidates)}")

    # ── 6. Scorer tous les candidats ──
    scored = []
    for c in all_candidates:
        result = score_candidate(c, existing_asins, recently_published_categories)
        scored.append(result)

    # Trier par score décroissant
    scored.sort(key=lambda c: c["score"], reverse=True)

    # ── 7. Classer : doublons, sous-seuil, acceptés ──
    duplicates = [c for c in scored if c["is_duplicate"]]
    below_threshold = [c for c in scored if not c["is_duplicate"] and c["score"] < MIN_PRODUCT_SCORE]
    above_threshold = [c for c in scored if not c["is_duplicate"] and c["score"] >= MIN_PRODUCT_SCORE]

    summary["duplicates_skipped"] = len(duplicates)
    summary["below_threshold"] = len(below_threshold)

    # ── Log des résultats scoring ──
    logger.info("=" * 60)
    logger.info("SCORING RESULTS")
    logger.info(f"  Candidates found:        {len(all_candidates)}")
    logger.info(f"  Duplicates skipped:      {len(duplicates)}")
    logger.info(f"  Below score threshold:   {len(below_threshold)} (< {MIN_PRODUCT_SCORE})")
    logger.info(f"  Above threshold:         {len(above_threshold)}")

    for d in duplicates[:5]:
        logger.info(f"    DUPLICATE → SKIP: {d.get('asin', '?')} — {d.get('score_reasons', [''])[0]}")
    for b in below_threshold[:5]:
        logger.info(f"    LOW SCORE → SKIP: [{b['score']}] {(b.get('title','') or '')[:50]}")

    # ── 8. Dédup intra-batch sur les acceptés ──
    new_candidates, batch_dups = check_candidate_batch(
        above_threshold, existing_asins, existing_urls, extract_asin, normalize_amazon_url,
    )
    summary["duplicates_skipped"] += len(batch_dups)

    # Limiter au max accepté par run
    accepted = new_candidates[:effective_max_accepted]
    summary["accepted"] = len(accepted)

    # ── Log des candidats acceptés ──
    logger.info("=" * 60)
    logger.info(f"ACCEPTED CANDIDATES: {len(accepted)}")
    for c in accepted:
        name = resolve_product_name(c)
        logger.info(f"  Selected candidate:")
        logger.info(f"    Title: {name[:80]}")
        logger.info(f"    ASIN:  {c.get('asin', '?')}")
        logger.info(f"    Score: {c['score']}/100")
        logger.info(f"    Reasons: {'; '.join(c.get('score_reasons', []))}")
        summary["selected_candidates"].append({
            "title": name[:100],
            "asin": c.get("asin"),
            "score": c["score"],
        })

    # ── 9. Créer les records Airtable ──
    if dry_run:
        logger.info("DRY RUN — skipping Airtable creation")
        for c in accepted:
            content = generate_content(c)
            logger.info(f"  [DRY] Would create:")
            logger.info(f"    Product:          {resolve_product_name(c)[:80]}")
            logger.info(f"    Score:            {c['score']}/100")
            logger.info(f"    Pinterest Title:  {content['pinterest_title']}")
            logger.info(f"    Pinterest Desc:   {content['pinterest_description'][:120]}…")
            logger.info(f"    Hashtags:         {' '.join(content['hashtags'])}")
            logger.info(f"    Description:      {content['description'][:120]}…")
            summary["selected_candidates"][-len(accepted) + accepted.index(c)].update({
                "pinterest_title": content["pinterest_title"],
                "hashtags": content["hashtags"],
            })
    else:
        for candidate in accepted:
            try:
                # Generate content BEFORE creating the record
                content = generate_content(candidate)
                record_id = _create_airtable_record(candidate, content)
                if record_id:
                    summary["records_created"] += 1
                    logger.info(f"  Created record {record_id}: ASIN {candidate.get('asin', '?')}")
            except Exception as e:
                logger.error(f"  Airtable error: {e}")
                summary["errors"].append(str(e))

    # ── Résumé final ──
    logger.info("=" * 60)
    logger.info("DISCOVERY SUMMARY")
    logger.info(f"  Queries:            {len(summary['queries'])}")
    logger.info(f"  Candidates found:   {summary['total_candidates']}")
    logger.info(f"  Duplicates skipped: {summary['duplicates_skipped']}")
    logger.info(f"  Below threshold:    {summary['below_threshold']}")
    logger.info(f"  Accepted:           {summary['accepted']}")
    logger.info(f"  Records created:    {summary['records_created']}")
    logger.info(f"  Errors:             {len(summary['errors'])}")
    logger.info("=" * 60)

    return summary


def _fetch_dedup_index() -> tuple[set, set, list[str]]:
    """Récupère index de dédup + catégories récentes depuis Airtable."""
    from scripts.airtable.client import AirtableClient

    client = AirtableClient(
        base_id=AIRTABLE_BASE_ID, table_id=AIRTABLE_TABLE_ID,
        token=AIRTABLE_TOKEN, api_url=AIRTABLE_API_URL,
    )
    records = client.list_records(fields=["Amazon URL", "Status", "Category"])
    existing_asins, existing_urls = build_existing_index(records, extract_asin, normalize_amazon_url)

    # Extraire les catégories récentes (tous statuts sauf Rejected)
    recent_cats = []
    for r in records:
        f = r.get("fields", {})
        if f.get("Status") != "Rejected":
            cat = f.get("Category", "")
            if cat:
                recent_cats.append(cat)

    return existing_asins, existing_urls, recent_cats


def _create_airtable_record(candidate: dict, content: dict | None = None) -> str | None:
    """Crée un record Airtable pour un candidat validé."""
    from scripts.airtable.client import AirtableClient

    client = AirtableClient(
        base_id=AIRTABLE_BASE_ID, table_id=AIRTABLE_TABLE_ID,
        token=AIRTABLE_TOKEN, api_url=AIRTABLE_API_URL,
    )

    asin = candidate.get("asin", "")
    amazon_url = candidate.get("url", "")
    normalized_url = normalize_amazon_url(amazon_url) or amazon_url

    affiliate_url = ""
    if asin and AMAZON_PARTNER_TAG:
        affiliate_url = build_affiliate_url(asin, AMAZON_PARTNER_TAG, AMAZON_DOMAIN)

    # Validate affiliate URL format
    if affiliate_url:
        valid, reason = validate_affiliate_url(affiliate_url, asin, AMAZON_PARTNER_TAG)
        if not valid:
            logger.error(f"Affiliate URL validation failed: {reason}")
            affiliate_url = ""  # Don't store an invalid affiliate URL

    product_name = resolve_product_name(candidate)

    fields = {
        "Product Name": product_name,
        "Amazon URL": normalized_url,
        "Affiliate URL": affiliate_url,
        "Status": STATUS_NEW,
        "Published": False,
        "Category": candidate.get("category_detected", candidate.get("niche_category", "")),
        "Style": candidate.get("style_detected", candidate.get("niche_style", "")),
        "Date Added": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    if candidate.get("snippet"):
        fields["Description"] = candidate["snippet"][:500]

    # Champs content (Phase 4)
    if content:
        fields["Description"] = content.get("description", fields.get("Description", ""))
        fields["Pinterest Title"] = content.get("pinterest_title", "")
        fields["Pinterest Description"] = content.get("pinterest_description", "")
        hashtags = content.get("hashtags", [])
        if hashtags:
            fields["Pinterest Description"] += "\n\n" + " ".join(hashtags)

    return client.create_record(fields)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="UnoSnake Discovery Engine")
    parser.add_argument("--test", action="store_true", help="Force test mode")
    parser.add_argument("--dry-run", action="store_true", help="Don't create Airtable records")
    args = parser.parse_args()

    result = run_discovery(test_mode=args.test, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
