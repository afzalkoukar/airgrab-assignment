import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.schemas import FoodItem

DATA_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "foods.json"


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_empty_query_rejected(client):
    assert client.post("/search", json={"query": ""}).status_code == 422


def test_whitespace_query_rejected(client):
    assert client.post("/search", json={"query": "   "}).status_code == 422


def test_oversized_query_rejected(client):
    assert client.post("/search", json={"query": "x" * 501}).status_code == 422


def test_search_response_shape(client):
    r = client.post("/search", json={"query": "spicy chicken biryani"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"query", "parsed", "count", "results"}
    assert body["query"] == "spicy chicken biryani"
    assert body["count"] == len(body["results"])
    assert body["count"] <= 10


def test_veg_only_filter(client):
    r = client.post("/search", json={"query": "veg food under 200"})
    assert r.status_code == 200
    for item in r.json()["results"]:
        assert item["veg"] is True
        assert item["price"] <= 200


def test_location_and_category_filter(client):
    r = client.post("/search", json={"query": "biryani in koramangala"})
    assert r.status_code == 200
    for item in r.json()["results"]:
        assert item["location"] == "Koramangala"
        assert item["category"] == "biryani"


def test_keywords_drop_zero_relevance(client):
    r = client.post("/search", json={"query": "chicken"})
    assert r.status_code == 200
    for item in r.json()["results"]:
        haystack = " ".join([item["name"], item["category"], *item["tags"]]).lower()
        assert "chicken" in haystack


def test_no_keywords_keeps_filtered_items(client):
    r = client.post("/search", json={"query": "veg food under ₹500"})
    assert r.status_code == 200
    body = r.json()
    assert body["parsed"]["keywords"] == []
    assert body["count"] > 0
    for item in body["results"]:
        assert item["veg"] is True


def test_ranking_score_then_rating(client):
    r = client.post("/search", json={"query": "spicy chicken rice"})
    assert r.status_code == 200
    items = r.json()["results"]

    def score(item):
        hay = " ".join([item["name"], item["category"], *item["tags"]]).lower()
        return sum(2 for kw in ("spicy", "chicken", "rice") if kw in hay)

    scored = [(score(i), i["rating"]) for i in items]
    assert scored == sorted(scored, key=lambda t: (t[0], t[1]), reverse=True)


def test_parser_failure_returns_502_no_leak(client):
    with patch("app.main.parser.parse", side_effect=RuntimeError("boom")):
        r = client.post("/search", json={"query": "anything"})
    assert r.status_code == 502
    assert r.json()["detail"] == "Query understanding failed"


def test_foods_json_dataset_is_valid():
    raw = json.loads(DATA_PATH.read_text())
    items = [FoodItem(**entry) for entry in raw]
    assert len(items) == len(raw)
    assert len(items) > 0
    for it in items:
        assert 0 <= it.rating <= 5
        assert it.price >= 0
