"""
UnoSnake Autopilot — Configuration centralisée.

Toutes les constantes, feature flags et limites.
Les valeurs sont lues depuis les variables d'environnement
avec des valeurs par défaut sécurisées (mode test).
"""

import os

# ============================================================
# FEATURE FLAGS
# ============================================================

TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
PINTEREST_ENABLED = os.getenv("PINTEREST_ENABLED", "false").lower() == "true"
AMAZON_CREATORS_API_ENABLED = os.getenv("AMAZON_CREATORS_API_ENABLED", "false").lower() == "true"

# ============================================================
# LIMITES OPÉRATIONNELLES
# ============================================================

PUBLISHES_PER_DAY = int(os.getenv("PUBLISHES_PER_DAY", "4"))
MAX_CANDIDATES_PER_SEARCH = int(os.getenv("MAX_CANDIDATES_PER_SEARCH", "10"))
MAX_SERPER_REQUESTS_PER_DAY = int(os.getenv("MAX_SERPER_REQUESTS_PER_DAY", "5"))
MAX_RETRY_COUNT = int(os.getenv("MAX_RETRY_COUNT", "3"))
RETRY_BACKOFF_BASE = float(os.getenv("RETRY_BACKOFF_BASE", "2.0"))

# Scoring
MIN_PRODUCT_SCORE = int(os.getenv("MIN_PRODUCT_SCORE", "65"))
MAX_ACCEPTED_PER_RUN = int(os.getenv("MAX_ACCEPTED_PER_RUN", "10"))
MAX_PUBLISH_PER_RUN = int(os.getenv("MAX_PUBLISH_PER_RUN", "1"))

# Live Pilot mode
LIVE_PILOT = os.getenv("LIVE_PILOT", "false").lower() == "true"
MAX_PILOT_AIRTABLE_WRITES = int(os.getenv("MAX_PILOT_AIRTABLE_WRITES", "1"))

# First Pin mode — ultra-controlled first real Pin (max 1, no batch)
FIRST_PIN_MODE = os.getenv("FIRST_PIN_MODE", "false").lower() == "true"

# ============================================================
# AIRTABLE
# ============================================================

AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN", "")
AIRTABLE_TABLE_ID = "tbl2RQvsmpBm3yAdW"
AIRTABLE_API_URL = "https://api.airtable.com/v0"

# Statuts Airtable (machine à états)
STATUS_NEW = "New"
STATUS_SELECTED = "Selected"
STATUS_PUBLISHED = "Published"
STATUS_REJECTED = "Rejected"

VALID_STATUSES = [STATUS_NEW, STATUS_SELECTED, STATUS_PUBLISHED, STATUS_REJECTED]

# ============================================================
# AMAZON
# ============================================================

AMAZON_PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG", "unosnake09-21")
AMAZON_MARKETPLACE = "www.amazon.fr"
AMAZON_DOMAIN = "amazon.fr"

# ============================================================
# SERPER
# ============================================================

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SERPER_API_URL = "https://google.serper.dev/search"
SERPER_COUNTRY = "fr"
SERPER_LANGUAGE = "fr"

# ============================================================
# PINTEREST
# ============================================================

PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN", "")
PINTEREST_BOARD_ID = os.getenv("PINTEREST_BOARD_ID", "")
PINTEREST_SANDBOX = os.getenv("PINTEREST_SANDBOX", "true").lower() == "true"
# API base URLs
PINTEREST_API_URL = "https://api.pinterest.com/v5"
PINTEREST_SANDBOX_URL = "https://api-sandbox.pinterest.com/v5"

# ============================================================
# DISCOVERY
# ============================================================

NICHES_FILE = os.path.join(os.path.dirname(__file__), "..", "niches.json")
SEARCH_HISTORY_FILE = os.getenv(
    "SEARCH_HISTORY_FILE",
    os.path.join(os.path.dirname(__file__), "..", "search_history.json"),
)

# Nombre minimum d'heures entre deux utilisations de la même niche
NICHE_COOLDOWN_HOURS = int(os.getenv("NICHE_COOLDOWN_HOURS", "24"))

# Nombre max de niches à interroger par run
MAX_NICHES_PER_RUN = int(os.getenv("MAX_NICHES_PER_RUN", "3"))

# ============================================================
# GOOGLE TRENDS
# ============================================================

GOOGLE_TRENDS_RSS_URL = "https://trends.google.com/trending/rss?geo=FR"

# Mots-clés de filtrage des tendances déco
TRENDS_DECO_KEYWORDS = [
    "déco", "decoration", "décoration", "maison", "interieur", "intérieur",
    "salon", "chambre", "cuisine", "meuble", "mobilier", "design",
    "scandinave", "japandi", "bohème", "boheme", "minimaliste",
    "lampe", "lumière", "luminaire", "vase", "miroir", "tapis",
    "étagère", "etagere", "table", "chaise", "canapé", "canape",
    "rangement", "plante", "bougie", "coussin", "rideau", "cadre",
]

# ============================================================
# UNOSNAKE STYLES & CATÉGORIES
# ============================================================

UNOSNAKE_STYLES = [
    "Scandinavian",
    "Japandi",
    "Warm Minimalism",
    "Bohemian",
    "Natural",
    "Modern",
]

UNOSNAKE_CATEGORIES = [
    "Décoration",
    "Mobilier",
    "Éclairage",
    "Accessoires",
    "Rangement",
    "Textile",
    "Objets déco",
]
