from typing import Protocol
from app.schemas import ParsedQuery

class QueryParser(Protocol):
    def parse(self, query: str) -> ParsedQuery:
        ...