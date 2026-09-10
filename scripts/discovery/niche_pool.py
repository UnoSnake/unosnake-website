"""
UnoSnake — Niche Pool : rotation, historique et diversité.

Gère le pool de niches depuis niches.json, assure la rotation
pour éviter les recherches identiques trop rapprochées,
et favorise la diversité des styles/catégories.
"""

import json
import os
import random
from datetime import datetime, timedelta, timezone


def load_niches(niches_file: str) -> list[dict]:
    """
    Charge les niches depuis un fichier JSON.

    Returns:
        Liste de dicts : {"query": str, "style": str, "category": str}
    """
    if not os.path.exists(niches_file):
        return []

    with open(niches_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("niches", [])


def load_search_history(history_file: str) -> list[dict]:
    """
    Charge l'historique des recherches.

    Returns:
        Liste de dicts : {"query": str, "timestamp": str, "results_count": int}
    """
    if not os.path.exists(history_file):
        return []

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_search_history(history_file: str, history: list[dict]) -> None:
    """Sauvegarde l'historique des recherches."""
    # Garder seulement les 500 dernières entrées pour ne pas exploser
    history = history[-500:]

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def record_search(history_file: str, query: str, results_count: int = 0) -> None:
    """Enregistre une recherche dans l'historique."""
    history = load_search_history(history_file)
    history.append({
        "query": query,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results_count": results_count,
    })
    save_search_history(history_file, history)


def get_available_niches(
    niches: list[dict],
    history: list[dict],
    cooldown_hours: int = 24,
    now: datetime | None = None,
) -> list[dict]:
    """
    Filtre les niches disponibles en excluant celles utilisées récemment.

    Args:
        niches: Pool complet de niches.
        history: Historique des recherches.
        cooldown_hours: Heures minimum entre deux utilisations d'une même niche.
        now: Datetime courant (pour les tests).

    Returns:
        Liste de niches disponibles (pas en cooldown).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    cutoff = now - timedelta(hours=cooldown_hours)

    # Trouver les queries utilisées après le cutoff
    recent_queries = set()
    for entry in history:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts > cutoff:
                recent_queries.add(entry["query"])
        except (KeyError, ValueError):
            continue

    # Filtrer les niches en cooldown
    return [n for n in niches if n["query"] not in recent_queries]


def select_niches(
    niches: list[dict],
    history: list[dict],
    max_niches: int = 3,
    cooldown_hours: int = 24,
    now: datetime | None = None,
    seed: int | None = None,
) -> list[dict]:
    """
    Sélectionne les niches à interroger pour ce run.

    Algorithme :
    1. Exclure les niches en cooldown
    2. Favoriser la diversité des styles et catégories
    3. Sélectionner max_niches parmi les candidats

    Args:
        niches: Pool complet.
        history: Historique des recherches.
        max_niches: Nombre max de niches à retourner.
        cooldown_hours: Heures de cooldown.
        now: Datetime courant (pour les tests).
        seed: Seed random (pour les tests).

    Returns:
        Liste de niches sélectionnées (max max_niches).
    """
    available = get_available_niches(niches, history, cooldown_hours, now)

    if not available:
        # Toutes en cooldown → prendre les plus anciennes
        available = _get_least_recent_niches(niches, history, max_niches)

    if len(available) <= max_niches:
        return available

    # Diversifier par style et catégorie
    return _diverse_selection(available, max_niches, seed)


def _get_least_recent_niches(
    niches: list[dict], history: list[dict], count: int
) -> list[dict]:
    """Retourne les niches les moins récemment utilisées."""
    last_used = {}
    for entry in history:
        query = entry.get("query", "")
        ts = entry.get("timestamp", "")
        if query and ts:
            last_used[query] = ts  # La dernière entrée gagne

    # Trier par date d'utilisation (les plus anciennes d'abord)
    niche_queries = {n["query"] for n in niches}
    sorted_niches = sorted(
        niches,
        key=lambda n: last_used.get(n["query"], "1970-01-01T00:00:00"),
    )

    return sorted_niches[:count]


def _diverse_selection(
    available: list[dict], count: int, seed: int | None = None
) -> list[dict]:
    """
    Sélectionne des niches en favorisant la diversité.

    Essaie de couvrir un maximum de styles et catégories différents.
    """
    rng = random.Random(seed)

    selected = []
    used_styles = set()
    used_categories = set()

    # Premier passage : un par style/catégorie unique
    shuffled = list(available)
    rng.shuffle(shuffled)

    for niche in shuffled:
        if len(selected) >= count:
            break
        style = niche.get("style", "")
        category = niche.get("category", "")

        # Privilégier les styles/catégories pas encore couverts
        if style not in used_styles or category not in used_categories:
            selected.append(niche)
            used_styles.add(style)
            used_categories.add(category)

    # Compléter si pas assez
    remaining = [n for n in shuffled if n not in selected]
    for niche in remaining:
        if len(selected) >= count:
            break
        selected.append(niche)

    return selected
