"""Extraction helpers for the rule-based query parser.

Each function extracts one filter from the (lowercased) query text.
Price and location also return the text with the match removed, so later
stages see less noise.
"""

import re

# --- Price: "under ₹300" / "below 200" / "less than Rs. 150" ---
PRICE_RE = re.compile(
    r"(?:under|below|less than|within|max)\s*(?:₹|rs\.?|inr)?\s*(\d+)",
    re.IGNORECASE,
)

# --- Location: alias (lowercase) -> canonical name as stored in foods.json ---
# Longest aliases first so "hsr layout" wins over "hsr".
LOCATIONS = {
    "koramangala": "Koramangala",
    "hsr layout": "HSR Layout",
    "indiranagar": "Indiranagar",
    "whitefield": "Whitefield",
    "hsr": "HSR Layout",
    "btm": "BTM",
}

# --- Diet ---
# "non veg" contains "veg" -> check the non-veg phrase FIRST.
NON_VEG_PHRASE_RE = re.compile(r"\bnon[-\s]?veg\b")
VEG_WORDS = ["pure veg", "vegetarian", "vegan", "veg"]
NON_VEG_WORDS = ["chicken", "mutton", "fish", "prawn", "egg"]

# --- Category: canonical value (as stored in foods.json) -> trigger words ---
CATEGORY_MAP = {
    "breakfast": ["breakfast", "morning"],
    "healthy": ["healthy", "diet", "light", "salad"],
    "desserts": ["dessert", "sweets", "sweet", "cake", "ice cream"],
    "biryani": ["biryani", "pulao"],
    "snacks": ["snacks", "snack", "chaat"],
    "south_indian": ["south indian", "dosa", "idli"],
    "north_indian": ["north indian", "thali", "chole"],
}

STOPWORDS = {
    "i", "me", "my", "want", "need", "get", "give", "some", "something",
    "food", "eat", "eating", "near", "in", "at", "a", "an", "the", "for",
    "please", "good", "nice", "best", "under", "below", "within", "than",
    "less", "max", "and", "or", "with", "of",
}
# Pure diet markers are noise for keyword ranking; meat words like "chicken"
# are NOT removed — they carry ranking signal.
DIET_NOISE = {"veg", "vegetarian", "vegan", "pure", "non"}


def extract_price(text: str) -> tuple[float | None, str]:
    matches = PRICE_RE.findall(text)
    if not matches:
        return None, text
    price = float(min(int(m) for m in matches))  # most restrictive wins
    return price, PRICE_RE.sub(" ", text)


def extract_diet(text: str) -> bool:
    if NON_VEG_PHRASE_RE.search(text):
        return False  # explicit non-veg request -> no veg filter
    if any(re.search(rf"\b{w}\b", text) for w in NON_VEG_WORDS):
        return False  # mentions meat -> don't restrict to veg
    if any(re.search(rf"\b{re.escape(w)}\b", text) for w in VEG_WORDS):
        return True
    return False


def extract_location(text: str) -> tuple[str | None, str]:
    for alias, canonical in LOCATIONS.items():
        if alias in text:
            return canonical, text.replace(alias, " ")
    return None, text  # "near me" and unknown places -> no location filter


def extract_category(text: str) -> str | None:
    for category, triggers in CATEGORY_MAP.items():
        if any(re.search(rf"\b{re.escape(t)}\b", text) for t in triggers):
            return category
    return None


def extract_keywords(text: str) -> list[str]:
    text = re.sub(r"[^\w\s]", " ", text)  # strip punctuation (₹, commas, etc.)
    return [
        token
        for token in text.split()
        if token not in STOPWORDS
        and token not in DIET_NOISE
        and not token.isdigit()
    ]
