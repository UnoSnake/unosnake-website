"""Tests — extraction ASIN et normalisation URL Amazon."""

import os
import sys

# Ajout du chemin projet
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.amazon.asin import (
    extract_asin,
    normalize_amazon_url,
    build_affiliate_url,
    is_valid_asin,
    validate_affiliate_url,
)


# ============================================================
# extract_asin
# ============================================================

def test_extract_asin_standard_dp():
    url = "https://www.amazon.fr/dp/B0H36L8M6F/ref=sr_1_1"
    assert extract_asin(url) == "B0H36L8M6F"


def test_extract_asin_gp_product():
    url = "https://www.amazon.fr/gp/product/B08N5WRWNW"
    assert extract_asin(url) == "B08N5WRWNW"


def test_extract_asin_with_title_slug():
    url = "https://www.amazon.fr/Lampe-Design-Scandinave/dp/B0H6LW7X2K/ref=sr_1_3"
    assert extract_asin(url) == "B0H6LW7X2K"


def test_extract_asin_with_query_params():
    url = "https://www.amazon.fr/dp/B0GZDK4KGL?th=1&psc=1"
    assert extract_asin(url) == "B0GZDK4KGL"


def test_extract_asin_no_asin():
    url = "https://www.amazon.fr/s?k=vase+ceramique"
    assert extract_asin(url) is None


def test_extract_asin_empty():
    assert extract_asin("") is None
    assert extract_asin(None) is None


def test_extract_asin_non_amazon():
    url = "https://www.example.com/dp/B0H36L8M6F"
    # /dp/ pattern should still match even on non-amazon domains
    assert extract_asin(url) == "B0H36L8M6F"


def test_extract_asin_amazon_co_uk():
    url = "https://www.amazon.co.uk/dp/B09XYZ1234"
    assert extract_asin(url) == "B09XYZ1234"


# ============================================================
# normalize_amazon_url
# ============================================================

def test_normalize_strips_tracking():
    url = "https://www.amazon.fr/Rangement-Esthetique/dp/B0H36L8M6F/ref=sr_1_1?dib=abc123&keywords=rangement"
    result = normalize_amazon_url(url)
    assert result == "https://www.amazon.fr/dp/B0H36L8M6F"


def test_normalize_preserves_domain():
    url = "https://www.amazon.co.uk/dp/B0H36L8M6F"
    result = normalize_amazon_url(url)
    assert result == "https://www.amazon.co.uk/dp/B0H36L8M6F"


def test_normalize_returns_none_for_invalid():
    assert normalize_amazon_url("https://www.google.com") is None
    assert normalize_amazon_url("") is None


# ============================================================
# build_affiliate_url
# ============================================================

def test_build_affiliate_url():
    result = build_affiliate_url("B0H36L8M6F", "unosnake09-21")
    assert result == "https://www.amazon.fr/dp/B0H36L8M6F/ref=nosim?tag=unosnake09-21"


def test_build_affiliate_url_custom_domain():
    result = build_affiliate_url("B0H36L8M6F", "unosnake09-21", "amazon.co.uk")
    assert result == "https://www.amazon.co.uk/dp/B0H36L8M6F/ref=nosim?tag=unosnake09-21"


def test_build_affiliate_url_empty():
    assert build_affiliate_url("", "unosnake09-21") == ""
    assert build_affiliate_url("B0H36L8M6F", "") == ""

def test_build_affiliate_invalid_asin():
    assert build_affiliate_url("short", "unosnake09-21") == ""
    assert build_affiliate_url("b0h36l8m6f", "unosnake09-21") == ""  # lowercase


# ============================================================
# is_valid_asin
# ============================================================

def test_valid_asin():
    assert is_valid_asin("B0H36L8M6F") is True
    assert is_valid_asin("0123456789") is True


def test_invalid_asin():
    assert is_valid_asin("") is False
    assert is_valid_asin(None) is False
    assert is_valid_asin("B0H36") is False  # trop court
    assert is_valid_asin("b0h36l8m6f") is False  # minuscules
    assert is_valid_asin("B0H36L8M6F!") is False  # caractère spécial


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  ✅ {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  ❌ {test.__name__}: {e}")
    print(f"\n{'✅' if failed == 0 else '❌'} {passed}/{passed+failed} tests passed")
