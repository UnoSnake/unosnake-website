"""
UnoSnake — Extraction ASIN et normalisation URL Amazon.

Fonctions pures, sans appel réseau. Testables unitairement.

Format officiel lien affilié Amazon Associates France :
  https://www.amazon.fr/dp/{ASIN}/ref=nosim?tag={PARTNER_TAG}

Source : https://partenaires.amazon.fr/help/node/topic/GP38PJ6EUR6PFBEC
"""

import re
from urllib.parse import urlparse

# Pattern ASIN : exactement 10 caractères alphanumériques majuscules/chiffres
# Présent dans /dp/ASIN ou /gp/product/ASIN
ASIN_PATTERN = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?#]|$)")


def extract_asin(url: str) -> str | None:
    """
    Extrait l'ASIN d'une URL Amazon.

    Cherche d'abord dans le path (/dp/XXXX ou /gp/product/XXXX),
    puis en fallback dans les segments du path.

    Returns:
        ASIN (str) ou None si introuvable.
    """
    if not url:
        return None

    # Tentative primaire : pattern structuré dans le path
    match = ASIN_PATTERN.search(url)
    if match:
        return match.group(1)

    # Fallback : chercher un segment ASIN dans le path
    # uniquement si l'URL contient amazon
    if "amazon" in url.lower():
        parsed = urlparse(url)
        path_parts = parsed.path.split("/")
        for part in path_parts:
            if re.fullmatch(r"[A-Z0-9]{10}", part):
                return part

    return None


def normalize_amazon_url(url: str) -> str | None:
    """
    Normalise une URL Amazon en forme canonique.

    Résultat : https://www.amazon.fr/dp/{ASIN}
    Supprime les query strings, fragments et paramètres de tracking.

    Returns:
        URL normalisée ou None si l'ASIN n'est pas extractible.
    """
    asin = extract_asin(url)
    if not asin:
        return None

    domain = _extract_amazon_domain(url)
    return f"https://www.{domain}/dp/{asin}"


def build_affiliate_url(asin: str, partner_tag: str, domain: str = "amazon.fr") -> str:
    """
    Construit une URL affiliée Amazon Associates.

    Format officiel Amazon Associates France :
      https://www.amazon.fr/dp/{ASIN}/ref=nosim?tag={PARTNER_TAG}

    Source : https://partenaires.amazon.fr/help/node/topic/GP38PJ6EUR6PFBEC
    Citation : "voici le format lien que vous nécessitez :
               http://www.amazon.fr/dp/ASIN/ref=nosim?tag=VOTREIDPARTENAIRE"

    IMPORTANT : ce format a été vérifié dans la documentation officielle.
    Cependant, il est recommandé de vérifier régulièrement les mises à jour
    de la documentation Amazon Associates et d'utiliser l'outil de vérification
    de liens du Club Partenaires (partenaires.amazon.fr → Outils → Vérificateur
    de liens) pour confirmer le bon fonctionnement.

    Args:
        asin: ASIN Amazon (10 caractères, A-Z0-9).
        partner_tag: Identifiant partenaire (ex: "unosnake09-21").
        domain: Domaine Amazon (défaut: "amazon.fr").

    Returns:
        URL affiliée complète, ou "" si ASIN ou tag invalide.
    """
    if not is_valid_asin(asin):
        return ""
    if not partner_tag or not partner_tag.strip():
        return ""

    return f"https://www.{domain}/dp/{asin}/ref=nosim?tag={partner_tag}"


def validate_affiliate_url(url: str, expected_asin: str, expected_tag: str) -> tuple[bool, str]:
    """
    Valide le format d'une URL affiliée Amazon.

    Vérifie :
    1. Présence de l'ASIN attendu
    2. Présence du partner tag attendu
    3. Présence de /ref=nosim
    4. Format HTTPS

    IMPORTANT : cette validation vérifie le FORMAT, pas que le lien
    est fonctionnel chez Amazon. Pour vérifier le fonctionnement réel,
    utiliser le Vérificateur de liens du Club Partenaires Amazon.

    Returns:
        Tuple (is_valid: bool, reason: str).
    """
    if not url:
        return False, "Affiliate URL is empty"

    if not url.startswith("https://"):
        return False, "Affiliate URL must use HTTPS"

    if expected_asin and expected_asin not in url:
        return False, f"ASIN {expected_asin} not found in URL"

    if expected_tag and expected_tag not in url:
        return False, f"Partner tag {expected_tag} not found in URL"

    if "/ref=nosim" not in url:
        return False, "Missing /ref=nosim (required by Amazon Associates)"

    if "?tag=" not in url:
        return False, "Missing ?tag= parameter"

    return True, "OK"


def is_valid_asin(asin: str) -> bool:
    """
    Vérifie si une chaîne est un ASIN Amazon valide.

    Un ASIN est exactement 10 caractères : lettres majuscules et chiffres.
    """
    if not asin:
        return False
    return bool(re.fullmatch(r"[A-Z0-9]{10}", asin))


def _extract_amazon_domain(url: str) -> str:
    """
    Extrait le domaine Amazon depuis une URL.
    Fallback : amazon.fr
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        match = re.search(r"(amazon\.\w+(?:\.\w+)?)", hostname)
        if match:
            return match.group(1)
    except Exception:
        pass
    return "amazon.fr"
