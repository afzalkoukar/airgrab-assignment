"""Rule-based mock of an LLM query parser.

Implements the QueryParser protocol (app.llm.base) so a real LLM provider
can be swapped in later without changing the rest of the application.
Extraction logic lives in app.llm.utils.
"""

from app.llm.utils import (
    extract_category,
    extract_diet,
    extract_keywords,
    extract_location,
    extract_price,
)
from app.schemas import ParsedQuery
from base import QueryParser


class MockQueryParser(QueryParser):
    """Parses natural-language food queries using rules instead of an LLM."""

    def parse(self, query: str) -> ParsedQuery:
        text = query.lower().strip()

        max_price, text = extract_price(text)
        veg_only = extract_diet(text)
        location, text = extract_location(text)
        category = extract_category(text)
        keywords = extract_keywords(text)

        return ParsedQuery(
            max_price=max_price,
            veg_only=veg_only,
            location=location,
            category=category,
            keywords=keywords,
        )
