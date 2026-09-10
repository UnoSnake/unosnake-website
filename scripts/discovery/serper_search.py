"""
UnoSnake — Serper Search : recherche Amazon.fr via Serper API.

Construit des requêtes site:amazon.fr/dp, parse les résultats,
et retourne des candidats structurés.
"""

import json
import requests
from datetime import datetime, timezone


def build_serper_query(niche_query: str, site_prefix: str = "site:amazon.fr/dp") -> str:
    """
    Construit la requête Serper pour chercher des produits Amazon.

    Returns:
        Requête formatée : "site:amazon.fr/dp {niche_query}"
    """
    return f"{site_prefix} {niche_query}"


def search_serper(
    query: str,
    api_key: str,
    api_url: str = "https://google.serper.dev/search",
    country: str = "fr",
    language: str = "fr",
    num_results: int = 10,
    timeout: int = 15,
) -> dict:
    """
    Exécute une recherche Serper.

    Returns:
        Réponse JSON complète de Serper.

    Raises:
        requests.RequestException en cas d'erreur réseau.
        ValueError si la clé API est vide.
    """
    if not api_key:
        raise ValueError("SERPER_API_KEY is empty")

    payload = {
        "q": query,
        "gl": country,
        "hl": language,
        "num": num_results,
    }

    response = requests.post(
        api_url,
        headers={
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def parse_serper_results(serper_response: dict, source_query: str = "") -> list[dict]:
    """
    Parse les résultats Serper en candidats produit.

    Filtre uniquement les résultats Amazon.
    Extrait : URL, titre, snippet, position, rating/ratingCount si présents.

    Args:
        serper_response: Réponse JSON Serper.
        source_query: La requête utilisée (pour traçabilité).

    Returns:
        Liste de candidats structurés.
    """
    candidates = []
    organic = serper_response.get("organic", [])
    now = datetime.now(timezone.utc).isoformat()

    for i, result in enumerate(organic):
        link = result.get("link", "")

        # Ne garder que les résultats Amazon
        if "amazon" not in link.lower():
            continue

        candidate = {
            "url": link,
            "title": result.get("title", ""),
            "snippet": result.get("snippet", ""),
            "position": result.get("position", i + 1),
            "rating": result.get("rating", None),
            "rating_count": result.get("ratingCount", None),
            "source_query": source_query,
            "discovered_at": now,
        }
        candidates.append(candidate)

    return candidates


def search_amazon_products(
    niche_query: str,
    api_key: str,
    api_url: str = "https://google.serper.dev/search",
    num_results: int = 10,
) -> list[dict]:
    """
    Pipeline complet : construit la requête, interroge Serper,
    parse les résultats Amazon.

    Returns:
        Liste de candidats Amazon. Vide si erreur.
    """
    query = build_serper_query(niche_query)

    try:
        response = search_serper(
            query=query,
            api_key=api_key,
            api_url=api_url,
            num_results=num_results,
        )
    except Exception:
        return []

    return parse_serper_results(response, source_query=niche_query)
