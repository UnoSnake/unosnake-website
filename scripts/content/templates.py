"""
UnoSnake — Templates de contenu Pinterest.

Templates déterministes pour titres, descriptions et hashtags.
Ton : esthétique, inspiration maison, élégant, naturel.
Langue : français.
"""

# ============================================================
# PINTEREST TITLE TEMPLATES  (≈40–100 chars)
# ============================================================
# Placeholders :
#   {product}  — nom court du produit
#   {style}    — style UnoSnake (Scandinavian → scandinave, etc.)
#   {category} — catégorie (Éclairage, Rangement…)
#   {room}     — pièce déduite si possible

TITLE_TEMPLATES: list[str] = [
    "{product} — inspiration déco {style}",
    "{product} — une touche {style} pour la maison",
    "{product} — idée déco pour un intérieur {style}",
    "{product} — décoration {style} élégante",
    "{product} — coup de cœur déco {style}",
    "{product} — ambiance {style} à la maison",
    "{product} — notre sélection déco {style}",
    "{product} — pour un intérieur inspirant",
]

# Variantes quand le style est inconnu / absent
TITLE_TEMPLATES_NO_STYLE: list[str] = [
    "{product} — inspiration décoration maison",
    "{product} — idée déco pour la maison",
    "{product} — coup de cœur décoration intérieure",
    "{product} — pour un intérieur qui vous ressemble",
    "{product} — trouvaille déco du moment",
]


# ============================================================
# PINTEREST DESCRIPTION TEMPLATES  (≈100–300 chars)
# ============================================================

DESCRIPTION_TEMPLATES: list[str] = [
    "Apportez une touche {style_adj} à votre intérieur avec {product_lower}. "
    "Une pièce pensée pour les amateurs de décoration {style_adj} et d'espaces harmonieux.",

    "Découvrez {product_lower}, une idée déco {style_adj} pour transformer votre espace. "
    "Parfait pour créer une ambiance chaleureuse et inspirante.",

    "{product} : un choix {style_adj} pour sublimer votre décoration intérieure. "
    "Laissez-vous inspirer par cette sélection UnoSnake.",

    "Envie d'un intérieur {style_adj} ? {product} apporte cette touche d'élégance "
    "qui fait toute la différence dans un espace de vie.",

    "Une sélection UnoSnake pour les amoureux du {style_adj}. "
    "{product} s'intègre naturellement dans un intérieur soigné et inspirant.",
]

DESCRIPTION_TEMPLATES_NO_STYLE: list[str] = [
    "Découvrez {product_lower}, une idée déco pour transformer votre intérieur. "
    "Parfait pour créer une ambiance chaleureuse et inspirante.",

    "{product} : un choix élégant pour sublimer votre décoration intérieure. "
    "Laissez-vous inspirer par cette sélection UnoSnake.",

    "Envie de renouveler votre décoration ? {product} apporte cette touche "
    "qui fait toute la différence dans un espace de vie.",

    "Une sélection UnoSnake pour votre intérieur. "
    "{product} s'intègre naturellement dans un espace soigné et inspirant.",
]


# ============================================================
# HASHTAG POOLS
# ============================================================

HASHTAGS_BY_STYLE: dict[str, list[str]] = {
    "Scandinavian": ["#Scandinave", "#DecoScandinave", "#StyleNordique", "#Hygge", "#NordicHome"],
    "Japandi": ["#Japandi", "#DecoJapandi", "#ZenDecor", "#WabiSabi", "#JapandiStyle"],
    "Warm Minimalism": ["#Minimaliste", "#WarmMinimalism", "#DecoMinimaliste", "#LessIsMore", "#SimpleDecor"],
    "Bohemian": ["#Boheme", "#BohoDecor", "#DecoBoho", "#BohemianHome", "#BohoChic"],
    "Natural": ["#DecoNaturelle", "#NaturalHome", "#BoisNaturel", "#OrganicDecor", "#EcoDecor"],
    "Modern": ["#DecoModerne", "#ModernHome", "#DesignInterior", "#ContemporaryDecor", "#ModernDecor"],
}

HASHTAGS_BY_CATEGORY: dict[str, list[str]] = {
    "Décoration": ["#Decoration", "#DecoMaison", "#HomeDecor"],
    "Mobilier": ["#Mobilier", "#Furniture", "#MeubleDesign"],
    "Éclairage": ["#Eclairage", "#LampeDesign", "#Luminaire"],
    "Accessoires": ["#Accessoires", "#HomAccessories", "#DecoDetail"],
    "Rangement": ["#Rangement", "#Organisation", "#HomeOrganization"],
    "Textile": ["#TextileMaison", "#Coussin", "#HomeTextile"],
    "Objets déco": ["#ObjetDeco", "#VaseDeco", "#BougieDeco"],
}

HASHTAGS_GENERIC: list[str] = [
    "#DecoInterieur",
    "#InspirationDeco",
    "#Interieur",
    "#HomeSweetHome",
    "#DecorationInterieure",
    "#InteriorDesign",
    "#UnoSnake",
]


# ============================================================
# STYLE → FRENCH ADJECTIVE MAPPING
# ============================================================

STYLE_ADJECTIVES: dict[str, str] = {
    "Scandinavian": "scandinave",
    "Japandi": "japandi",
    "Warm Minimalism": "minimaliste",
    "Bohemian": "bohème",
    "Natural": "naturel",
    "Modern": "moderne",
    "General Deco": "élégant",
    "Unknown": "",
}


# ============================================================
# ROOM DETECTION KEYWORDS
# ============================================================

ROOM_KEYWORDS: dict[str, str] = {
    "salon": "le salon",
    "living": "le salon",
    "chambre": "la chambre",
    "bedroom": "la chambre",
    "cuisine": "la cuisine",
    "kitchen": "la cuisine",
    "salle de bain": "la salle de bain",
    "bathroom": "la salle de bain",
    "bureau": "le bureau",
    "office": "le bureau",
    "entrée": "l'entrée",
    "entryway": "l'entrée",
}
