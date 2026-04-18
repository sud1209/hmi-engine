import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


@pytest.fixture
def client():
    """Client with DB calls mocked so lifespan completes without a real DB."""
    with patch("mcp_server.main.init_db", new_callable=AsyncMock), \
         patch("mcp_server.main.seed_data", new_callable=AsyncMock), \
         patch("mcp_server.main.fetch_and_store_news", new_callable=AsyncMock), \
         patch("mcp_server.main.fetch_and_store_rates", new_callable=AsyncMock), \
         patch("mcp_server.main.poll_kpi_file", new_callable=AsyncMock):
        from mcp_server.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


def test_health_no_auth(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_history_no_auth(client):
    response = client.get("/history/National")
    assert response.status_code != 401


def test_msa_no_auth(client):
    response = client.get("/msa/rankings?metric=median_sale_price")
    assert response.status_code != 401


def test_query_no_auth(client):
    response = client.post("/query", json={"query": "What is the average home price?"})
    assert response.status_code != 401


def test_metrics_no_auth(client):
    response = client.get("/metrics")
    assert response.status_code != 401


def test_tools_call_requires_auth(client):
    response = client.post("/tools/call/search_houses", json={"query": "house"})
    assert response.status_code == 401


def test_ingest_requires_auth(client):
    response = client.post(
        "/ingest/kpis",
        json={"market": "National", "kpis": {}, "as_of_date": "2026-04-17"},
    )
    assert response.status_code == 401
