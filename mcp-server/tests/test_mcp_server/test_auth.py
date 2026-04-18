import pytest
from fastapi.testclient import TestClient


def get_client():
    # Import app lazily to avoid DB connection at module load
    from mcp_server.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_health_no_auth():
    client = get_client()
    response = client.get("/health")
    assert response.status_code == 200


def test_history_no_auth():
    client = get_client()
    response = client.get("/history/National")
    assert response.status_code != 401


def test_msa_no_auth():
    client = get_client()
    response = client.get("/msa/rankings?metric=median_sale_price")
    assert response.status_code != 401


def test_query_no_auth():
    client = get_client()
    response = client.post("/query", json={"query": "What is the average home price?"})
    assert response.status_code != 401


def test_metrics_no_auth():
    client = get_client()
    response = client.get("/metrics")
    assert response.status_code != 401


def test_tools_call_requires_auth():
    client = get_client()
    response = client.post("/tools/call/search_houses", json={"query": "house"})
    assert response.status_code == 401


def test_ingest_requires_auth():
    client = get_client()
    response = client.post(
        "/ingest/kpis",
        json={"market": "National", "kpis": {}, "as_of_date": "2026-04-17"},
    )
    assert response.status_code == 401
