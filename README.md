# Airgrab Food Search

A small backend service that accepts a natural-language food query, interprets it with an
AI/LLM component (mocked, behind a swappable interface), and returns relevant food items
from a sample dataset.

Built with FastAPI. Python 3.12+.

## How to run

```bash
git clone <repo-url>
cd airgrab

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

- Interactive API docs (Swagger UI): http://localhost:8000/docs
- Health check: `curl localhost:8000/health`
- Run the test suite: `pytest -v`

No configuration is required: the parser defaults to the mock provider
(`LLM_PROVIDER=mock`). To configure explicitly, `cp .env.example .env` — the app
loads `.env` at startup via `python-dotenv`.

## API usage

### `POST /search`

Request body: `{"query": "<natural-language query>"}`

Response: the original query, the structured `ParsedQuery` the LLM component extracted,
the result count, and up to 10 ranked food items.

#### Example 1 — assignment headline query

```bash
curl -X POST localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "I want spicy chicken biryani under ₹300 near Koramangala"}'
```

```json
{
    "query": "I want spicy chicken biryani under ₹300 near Koramangala",
    "parsed": {
        "max_price": 300.0,
        "veg_only": false,
        "location": "Koramangala",
        "category": "biryani",
        "keywords": ["spicy", "chicken", "biryani"]
    },
    "count": 2,
    "results": [
        {
            "id": 1,
            "name": "Chicken Dum Biryani",
            "restaurant": "Paradise Biryani",
            "price": 280.0,
            "location": "Koramangala",
            "veg": false,
            "category": "biryani",
            "rating": 4.5,
            "tags": ["spicy", "chicken", "rice"]
        },
        {
            "id": 2,
            "name": "Chicken Tikka Biryani",
            "restaurant": "Nawab's Kitchen",
            "price": 300.0,
            "location": "Koramangala",
            "veg": false,
            "category": "biryani",
            "rating": 4.4,
            "tags": ["spicy", "chicken", "rice"]
        }
    ]
}
```

#### Example 2 — no explicit filters, intent-based query

```bash
curl -X POST localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "Something healthy for breakfast"}'
```

```json
{
    "query": "Something healthy for breakfast",
    "parsed": {
        "max_price": null,
        "veg_only": false,
        "location": null,
        "category": "breakfast",
        "keywords": ["healthy", "breakfast"]
    },
    "count": 8,
    "results": [
        {
            "id": 11,
            "name": "Idli Vada Combo",
            "restaurant": "Udupi Upahar",
            "price": 80.0,
            "location": "Indiranagar",
            "veg": true,
            "category": "breakfast",
            "rating": 4.3,
            "tags": ["healthy", "breakfast", "south_indian"]
        }
    ]
}
```

*(7 more items omitted for brevity — full response has `"count": 8`.)*

#### Example 3 — constraint-only query (no keywords)

```bash
curl -X POST localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "Veg food under ₹200"}'
```

```json
{
    "query": "Veg food under ₹200",
    "parsed": {
        "max_price": 200.0,
        "veg_only": true,
        "location": null,
        "category": null,
        "keywords": []
    },
    "count": 10,
    "results": [
        {
            "id": 19,
            "name": "Chocolate Brownie",
            "restaurant": "The Dessert Room",
            "price": 160.0,
            "location": "BTM",
            "veg": true,
            "category": "desserts",
            "rating": 4.5,
            "tags": ["sweet", "chocolate", "dessert"]
        }
    ]
}
```

*(9 more items omitted for brevity — full response has `"count": 10`. Note that with no
keywords extracted, all correctly-filtered items are kept and ranked purely by rating.)*

#### Invalid request

```bash
curl -X POST localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query": ""}'
```

HTTP 422:

```json
{"detail":[{"type":"string_too_short","loc":["body","query"],"msg":"String should have at least 1 character","input":"","ctx":{"min_length":1}}]}
```

If the query-understanding component itself fails, the API returns
`502 {"detail": "Query understanding failed"}` without leaking internals.

## Architecture

```
POST /search {"query": "..."}
        │
        ▼
app/main.py            FastAPI transport layer. Pydantic validates the request
                       (SearchRequest) and the response (SearchResponse). No logic here.
        │
        ▼
app/llm/               QueryParser protocol (base.py) + MockQueryParser (mock.py).
parse(query)           Rule-based extraction (utils.py): price, diet, location,
        │              category, keywords → ParsedQuery. Selected by factory.py
        │              via LLM_PROVIDER; a real LLM client slots in behind the
        │              same protocol with zero changes to the rest of the app.
        ▼
app/search.py          Pure functions: hard filters (price / veg / location) first,
search(items, parsed)  then relevance scoring on keywords + category, then
                       sort by (score, rating) descending, top 10.
        │
        ▼
app/data/foods.json    25-item dataset, loaded and validated against the FoodItem
                       schema once at startup (bad data fails loudly at boot,
                       not silently at request time).
```

```
app/
├── main.py          # FastAPI app: /search, /health
├── schemas.py       # SearchRequest, ParsedQuery, FoodItem, SearchResponse
├── search.py        # filter-then-rank search
├── llm/
│   ├── base.py      # QueryParser protocol
│   ├── mock.py      # rule-based mock parser
│   ├── utils.py     # extraction helpers (price/diet/location/category/keywords)
│   └── factory.py   # selects parser via LLM_PROVIDER env var
└── data/foods.json  # sample dataset
tests/test_api.py    # endpoints, filters, ranking, error handling, dataset validity
```

## Design decisions

- **FastAPI** — request/response validation and Swagger docs come for free from the
  Pydantic schemas; invalid input is rejected with a useful 422 before any of my code runs.
- **`Protocol`-based parser (`QueryParser`)** — the LLM component is mocked today
  (deterministic, no API key, tests are hermetic), but `app/main.py` only knows the
  `parse(query) -> ParsedQuery` contract. Integrating a real provider means adding one
  class behind `factory.py` and setting `LLM_PROVIDER` — nothing else changes. The
  `ParsedQuery` schema also caps the blast radius of a flaky or adversarial LLM:
  whatever it returns must conform to typed fields.
- **JSON file dataset** — right-sized for 25 items; it's validated into typed `FoodItem`
  objects at startup, so the rest of the app never touches raw dicts. The next step
  (repository interface → Postgres) is a drop-in for the loader in `main.py`.
- **`tags` field on each item** — the key decision that lets a *rule-based* mock
  understand adjectives. A rule can't infer that oats are "healthy", but real catalogues
  (Swiggy/Zomato) are tagged with exactly these attributes, so matching query words
  against tags makes queries like "something healthy" work with zero ML.
- **Filter-then-rank, not filter-only** — hard constraints (price, veg, location) are
  exact: an item over budget is simply gone. Keywords are a *soft* signal used for
  scoring and ranking, with rating as tie-breaker. If a query produced no keywords
  (e.g. "veg food under ₹200"), the zero-relevance drop is skipped so correctly-filtered
  items still surface.

## Assumptions

- **"near me" is ignored** — there is no geolocation input, so it yields no location
  filter. Only named areas match (Koramangala, HSR Layout, Indiranagar, Whitefield, BTM,
  with a few aliases like "hsr").
- Prices are in INR; "under ₹300" means `price <= 300` (inclusive).
- Single-city dataset; queries are in English.
- A query mentioning meat words ("chicken", "mutton", ...) is treated as *not* veg-only,
  so the veg filter isn't applied to it; explicit "veg" sets the veg filter. "non veg"
  is checked before "veg" so it never triggers the veg filter.

## Limitations

Left out due to time constraints:

- **Brittle keyword parsing** — the mock has no typo tolerance, stemming, or synonym
  handling ("biriyani" won't match; "paneer" as a craving vs an ingredient isn't
  distinguished). This is exactly the gap a real LLM provider closes.
- **No semantic search** — "comfort food for a rainy day" has no keyword to match.
  Production would use hybrid retrieval (keyword/BM25 + vector embeddings), possibly
  with the LLM re-ranking.
- **Strict filters can return zero results** — there is no fallback (e.g. retry without
  location, then without price); `[]` is returned as-is.
- **No pagination** — responses are capped at top 10.
- Location list is hardcoded; unknown place names silently produce no location filter.

## Production considerations

- **Authentication & rate limiting** — API keys or JWT per client; per-token rate limits
  to protect the (expensive) LLM call.
- **Caching** — cache `query → ParsedQuery`; the LLM call is the latency/cost hotspot and
  queries repeat heavily in search workloads.
- **Database** — move the dataset to Postgres; full-text + pgvector for hybrid retrieval
  instead of in-memory filtering.
- **LLM reliability** — timeouts, retries with backoff, and a fallback (e.g. this same
  rule-based parser) when the provider is down; validate every LLM response against
  `ParsedQuery` before trusting it.
- **Prompt-injection guard** — the query is untrusted user input; the system prompt must
  constrain the LLM to output only the `ParsedQuery` shape, and schema validation
  enforces it.
- **Observability** — structured logs with request IDs, metrics on parse failures /
  zero-result rate / LLM latency, and tracing across the parse → search pipeline.
