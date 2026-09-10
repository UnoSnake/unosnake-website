#!/usr/bin/env python3
"""
UnoSnake — Test d'intégration Airtable (lecture seule).

Vérifie que la déduplication fonctionne contre la vraie base.
Ne crée PAS de nouveau record. Ne modifie PAS les records existants.

Nécessite les variables d'environnement :
  AIRTABLE_BASE_ID
  AIRTABLE_TOKEN

Usage: python tests/test_airtable_integration.py
"""

import os
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, PROJECT_ROOT)

from scripts.config import AIRTABLE_BASE_ID, AIRTABLE_TOKEN, AIRTABLE_TABLE_ID, AIRTABLE_API_URL
from scripts.amazon.asin import extract_asin, normalize_amazon_url
from scripts.airtable.dedup import build_existing_index, is_duplicate, check_candidate_batch


def main():
    print("=" * 60)
    print("UNOSNAKE — AIRTABLE INTEGRATION TEST (READ ONLY)")
    print("=" * 60)

    if not AIRTABLE_TOKEN or not AIRTABLE_BASE_ID:
        print("⚠️  AIRTABLE_TOKEN or AIRTABLE_BASE_ID not set — skipping integration test")
        print("   Set these env vars to run against the real Airtable base.")
        sys.exit(0)  # Pas un échec — juste pas de credentials

    # 1. Charger les records existants
    from scripts.airtable.client import AirtableClient

    client = AirtableClient(
        base_id=AIRTABLE_BASE_ID,
        table_id=AIRTABLE_TABLE_ID,
        token=AIRTABLE_TOKEN,
        api_url=AIRTABLE_API_URL,
    )

    print("\n📋 Fetching existing records...")
    records = client.list_records(fields=["Amazon URL", "Product Name", "Status"])

    print(f"   Found {len(records)} records")

    if not records:
        print("   ⚠️ No records in Airtable — nothing to test dedup against")
        sys.exit(0)

    # 2. Construire l'index de dédup
    existing_asins, existing_urls = build_existing_index(records, extract_asin, normalize_amazon_url)
    print(f"   Indexed: {len(existing_asins)} ASINs, {len(existing_urls)} URLs")

    # 3. Lister les ASINs existants
    print("\n🔑 Existing ASINs:")
    for asin in sorted(existing_asins):
        print(f"   {asin}")

    # 4. Test : chaque ASIN existant doit être détecté comme doublon
    passed = 0
    failed = 0

    print("\n🔄 Dedup verification:")
    for asin in existing_asins:
        dup, reason = is_duplicate(asin, None, None, existing_asins, existing_urls)
        if dup:
            print(f"   ✅ ASIN {asin} → DUPLICATE → SKIP (correct)")
            passed += 1
        else:
            print(f"   ❌ ASIN {asin} → NOT detected as duplicate (BUG)")
            failed += 1

    # 5. Test : un ASIN inventé ne doit PAS être un doublon
    fake_asin = "ZZZZZZZZ99"
    dup_fake, _ = is_duplicate(fake_asin, None, None, existing_asins, existing_urls)
    if not dup_fake:
        print(f"   ✅ ASIN {fake_asin} → NEW (correct)")
        passed += 1
    else:
        print(f"   ❌ ASIN {fake_asin} → false positive duplicate (BUG)")
        failed += 1

    # 6. Test batch : mixer un existant + un nouveau
    if existing_asins:
        known_asin = list(existing_asins)[0]
        candidates = [
            {"url": f"https://www.amazon.fr/dp/{known_asin}", "asin": known_asin, "title": "Known Product"},
            {"url": "https://www.amazon.fr/dp/ZZZZZZZZ99", "asin": "ZZZZZZZZ99", "title": "New Product"},
        ]
        new, dups = check_candidate_batch(candidates, existing_asins, existing_urls, extract_asin, normalize_amazon_url)

        if len(dups) == 1 and len(new) == 1 and new[0]["asin"] == "ZZZZZZZZ99":
            print(f"   ✅ Batch dedup correct: 1 duplicate, 1 new")
            passed += 1
        else:
            print(f"   ❌ Batch dedup incorrect: {len(new)} new, {len(dups)} dups")
            failed += 1

    # Summary
    print(f"\n{'=' * 60}")
    total = passed + failed
    if failed == 0:
        print(f"✅ INTEGRATION TEST PASSED ({total} checks)")
    else:
        print(f"❌ INTEGRATION TEST FAILED: {failed}/{total} checks failed")
    print(f"{'=' * 60}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
