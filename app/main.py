"""FastAPI wiring — thin transport layer only.

All logic lives in app.llm (parsing) and app.search (filtering/ranking).
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

from app.llm.factory import get_parser
from app.schemas import FoodItem, SearchRequest, SearchResponse
from app.search import search

app = FastAPI(title="Airgrab Food Search")

parser = get_parser()

# Load + validate the dataset at startup: a malformed item fails loudly here,
# not silently at request time.
DATA_PATH = Path(__file__).parent / "data" / "foods.json"
items = [FoodItem(**raw) for raw in json.loads(DATA_PATH.read_text())]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
def search_food(req: SearchRequest):
    try:
        parsed = parser.parse(req.query.strip())
    except Exception:
        # Simulates the real-LLM failure mode; don't leak internals.
        raise HTTPException(status_code=502, detail="Query understanding failed")

    results = search(items, parsed)
    return SearchResponse(
        query=req.query, parsed=parsed, count=len(results), results=results
    )
