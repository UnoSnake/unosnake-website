"""
UnoSnake — Data Quality Report.

Évalue la qualité des candidats découverts.
Ne modifie rien — lecture seule.
"""

import re


def validate_candidate(candidate: dict, content: dict | None = None, affiliate_url: str = "") -> dict:
    """
    Vérifie la qualité d'un candidat unique.

    Returns:
        dict avec checks individuels et score global.
    """
    checks = {}

    # ASIN
    asin = candidate.get("asin", "")
    checks["valid_asin"] = bool(asin) and bool(re.fullmatch(r"[A-Z0-9]{10}", asin or ""))

    # Amazon URL
    url = candidate.get("url", "")
    checks["valid_amazon_url"] = url.startswith("https://") and "amazon" in url.lower()

    # ASIN matches URL
    checks["asin_url_match"] = bool(asin) and asin in url if url else False

    # Affiliate URL
    checks["valid_affiliate_url"] = (
        affiliate_url.startswith("https://")
        and "/ref=nosim?tag=" in affiliate_url
        and bool(asin) and asin in affiliate_url
    ) if affiliate_url else False

    # Title
    title = candidate.get("title", "")
    checks["valid_title"] = bool(title) and len(title) >= 10

    # Score
    score = candidate.get("score", 0)
    checks["score_above_threshold"] = score >= 65

    # Content (if provided)
    if content:
        pt = content.get("pinterest_title", "")
        checks["pinterest_title_ok"] = bool(pt) and len(pt) <= 100 and "#" not in pt

        pd = content.get("pinterest_description", "")
        checks["pinterest_desc_ok"] = bool(pd) and len(pd) <= 500

        ht = content.get("hashtags", [])
        checks["hashtags_ok"] = 5 <= len(ht) <= 10 and all(h.startswith("#") for h in ht)
    else:
        checks["pinterest_title_ok"] = None
        checks["pinterest_desc_ok"] = None
        checks["hashtags_ok"] = None

    # Image (if present)
    img = candidate.get("image_url", "")
    checks["valid_image"] = img.startswith("https://") if img else None

    # Calculate quality score
    scored_checks = {k: v for k, v in checks.items() if v is not None}
    passed = sum(1 for v in scored_checks.values() if v)
    total = len(scored_checks)
    quality_pct = round(100 * passed / total) if total > 0 else 0

    return {
        "checks": checks,
        "passed": passed,
        "total": total,
        "quality_pct": quality_pct,
    }


def generate_quality_report(candidates: list[dict], contents: list[dict] | None = None) -> dict:
    """
    Génère un rapport de qualité pour un batch de candidats.

    Returns:
        dict avec métriques agrégées.
    """
    if not candidates:
        return {"count": 0, "quality_pct": 0, "details": []}

    details = []
    total_quality = 0

    for i, cand in enumerate(candidates):
        content = contents[i] if contents and i < len(contents) else None
        asin = cand.get("asin", "")
        aff = ""
        if asin and re.fullmatch(r"[A-Z0-9]{10}", asin):
            aff = f"https://www.amazon.fr/dp/{asin}/ref=nosim?tag=unosnake09-21"

        result = validate_candidate(cand, content, aff)
        result["asin"] = asin
        result["title"] = (cand.get("title") or "")[:80]
        result["score"] = cand.get("score", 0)
        details.append(result)
        total_quality += result["quality_pct"]

    avg_quality = round(total_quality / len(candidates)) if candidates else 0

    # Aggregate check pass rates
    all_checks = {}
    for d in details:
        for k, v in d["checks"].items():
            if v is not None:
                if k not in all_checks:
                    all_checks[k] = {"passed": 0, "total": 0}
                all_checks[k]["total"] += 1
                if v:
                    all_checks[k]["passed"] += 1

    check_rates = {}
    for k, v in all_checks.items():
        check_rates[k] = f"{v['passed']}/{v['total']}"

    return {
        "count": len(candidates),
        "quality_pct": avg_quality,
        "check_rates": check_rates,
        "details": details,
    }
