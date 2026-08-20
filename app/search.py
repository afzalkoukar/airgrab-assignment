"""Filter-then-rank search over the food dataset.

Pure functions, no FastAPI imports — unit-testable without HTTP.
Hard filters apply first; a missing filter (None/False) means no constraint.
"""

from app.schemas import FoodItem, ParsedQuery

TOP_N = 10


def _score(item: FoodItem, parsed: ParsedQuery) -> int:
    """+2 per keyword hit in name/tags/category, +1 for a category match."""
    haystack = " ".join([item.name, item.category, *item.tags]).lower()
    score = sum(2 for kw in parsed.keywords if kw in haystack)
    if parsed.category and item.category == parsed.category:
        score += 1
    return score


def search(items: list[FoodItem], parsed: ParsedQuery) -> list[FoodItem]:
    # 1. Hard filters
    filtered = [
        i for i in items
        if (parsed.max_price is None or i.price <= parsed.max_price)
        and (not parsed.veg_only or i.veg)
        and (parsed.location is None or i.location.lower() == parsed.location.lower())
    ]

    # 2. Score each survivor
    scored = [(i, _score(i, parsed)) for i in filtered]

    # 3. If keywords exist, drop items with zero relevance signal.
    #    Skipped when no keywords were extracted (e.g. "veg food under ₹200")
    #    — otherwise every correctly-filtered item would be discarded.
    if parsed.keywords:
        scored = [(i, s) for i, s in scored if s > 0]

    # 4. Sort: score desc, then rating desc
    scored.sort(key=lambda pair: (pair[1], pair[0].rating), reverse=True)

    # 5. Return top N
    return [item for item, _ in scored[:TOP_N]]
