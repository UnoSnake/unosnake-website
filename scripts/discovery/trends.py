"""
UnoSnake — Google Trends France.

Récupère les tendances Google France via RSS et filtre
celles pertinentes pour la décoration intérieure.
"""

import xml.etree.ElementTree as ET
import requests


def fetch_trends_rss(url: str, timeout: int = 10) -> str:
    """
    Télécharge le RSS Google Trends France.

    Returns:
        Contenu XML en string.

    Raises:
        requests.RequestException si le téléchargement échoue.
    """
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 UnoSnake/1.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.text


def parse_trends_xml(xml_content: str) -> list[str]:
    """
    Parse le XML RSS Google Trends et extrait les titres.

    Returns:
        Liste de titres de tendances (strings).
    """
    if not xml_content:
        return []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return []

    trends = []
    for item in root.findall("./channel/item"):
        title = item.findtext("title", "").strip()
        if title:
            trends.append(title)

    return trends


def filter_deco_trends(trends: list[str], keywords: list[str]) -> list[str]:
    """
    Filtre les tendances pertinentes pour la décoration.

    Args:
        trends: Liste de tendances brutes.
        keywords: Liste de mots-clés déco à matcher.

    Returns:
        Liste de tendances filtrées.
    """
    filtered = []
    for trend in trends:
        normalized = trend.lower()
        if any(keyword in normalized for keyword in keywords):
            filtered.append(trend)
    return filtered


def get_deco_trends(url: str, keywords: list[str], timeout: int = 10) -> list[str]:
    """
    Pipeline complet : fetch + parse + filter.

    Returns:
        Liste de tendances déco. Peut être vide.

    Raises:
        Ne lève pas d'exception — retourne une liste vide en cas d'erreur.
    """
    try:
        xml_content = fetch_trends_rss(url, timeout)
        all_trends = parse_trends_xml(xml_content)
        return filter_deco_trends(all_trends, keywords)
    except Exception:
        return []
