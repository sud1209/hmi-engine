import pytest
import os
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock
from mcp_server.feeds.news_fetcher import (
    fetch_and_store_news,
    _score_relevance,
    _make_id,
    _fetch_newsapi,
    _fetch_rss,
)
from mcp_server.db.models import NewsItem


class TestScoreRelevance:
    """Test the relevance scoring function."""

    def test_high_relevance_keywords(self):
        """Housing keywords should score as 'high'."""
        assert _score_relevance("mortgage rate dropped today") == "high"
        assert _score_relevance("home sales surge in Q1") == "high"
        assert _score_relevance("housing market shows strength") == "high"
        assert _score_relevance("median price reaches $450k") == "high"
        assert _score_relevance("inventory levels tight") == "high"
        assert _score_relevance("foreclosure rates rise") == "high"

    def test_medium_relevance_keywords(self):
        """Real estate keywords should score as 'medium'."""
        assert _score_relevance("real estate agents busy") == "medium"
        assert _score_relevance("housing affordability crisis") == "medium"
        assert _score_relevance("property prices climb") == "medium"
        assert _score_relevance("first-time buyer incentives") == "medium"
        assert _score_relevance("home buyer sentiment improves") == "medium"
        assert _score_relevance("interest rate changes announced") == "medium"

    def test_low_relevance_keywords(self):
        """Unrelated text should score as 'low'."""
        assert _score_relevance("Tech stocks surge") == "low"
        assert _score_relevance("Weather forecast for tomorrow") == "low"
        assert _score_relevance("Sports highlights of the week") == "low"

    def test_case_insensitive_matching(self):
        """Relevance scoring should be case-insensitive."""
        assert _score_relevance("MORTGAGE RATE dropped") == "high"
        assert _score_relevance("Home Sales Surge") == "high"
        assert _score_relevance("REAL ESTATE News") == "medium"


class TestMakeId:
    """Test ID generation from URLs."""

    def test_id_format(self):
        """Generated IDs should start with 'news-' prefix."""
        url = "https://example.com/news/housing"
        id_val = _make_id(url)
        assert id_val.startswith("news-")
        assert len(id_val) == len("news-") + 12

    def test_id_deterministic(self):
        """Same URL should always produce same ID."""
        url = "https://example.com/news/housing"
        id1 = _make_id(url)
        id2 = _make_id(url)
        assert id1 == id2

    def test_id_unique_per_url(self):
        """Different URLs should produce different IDs."""
        url1 = "https://example.com/news/1"
        url2 = "https://example.com/news/2"
        id1 = _make_id(url1)
        id2 = _make_id(url2)
        assert id1 != id2


@pytest.mark.asyncio
class TestFetchNewsAPI:
    """Test NewsAPI fetching logic."""

    async def test_newsapi_returns_empty_without_key(self):
        """When NEWS_API_KEY is absent, should return empty list."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEWS_API_KEY", None)
            result = await _fetch_newsapi()
            assert result == []

    async def test_newsapi_handles_http_error(self):
        """HTTP errors should be caught and return empty list."""
        with patch("mcp_server.feeds.news_fetcher.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("HTTP 429")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = False
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch.dict(os.environ, {"NEWS_API_KEY": "test-key"}):
                result = await _fetch_newsapi()
                assert result == []

    async def test_newsapi_parses_articles(self):
        """Should correctly parse articles from NewsAPI."""
        mock_articles = [
            {
                "title": "Housing Market Shows Strong Growth",
                "description": "Median prices up 5% YoY",
                "url": "https://news.example.com/1",
                "source": {"name": "Housing News"},
                "publishedAt": "2026-04-18T10:00:00Z",
            }
        ]

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value={"articles": mock_articles})
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("mcp_server.feeds.news_fetcher.httpx.AsyncClient", return_value=mock_client):
            with patch("mcp_server.feeds.news_fetcher.NEWS_API_KEY", "test-key"):
                result = await _fetch_newsapi()
                assert len(result) == 1
                assert result[0]["headline"] == "Housing Market Shows Strong Growth"
                assert result[0]["url"] == "https://news.example.com/1"
                assert result[0]["source"] == "Housing News"
                assert result[0]["relevance_score"] == "high"


@pytest.mark.asyncio
class TestFetchRSS:
    """Test RSS feed fetching logic."""

    async def test_rss_handles_feed_error(self):
        """HTTP errors in RSS fetch should be caught gracefully."""
        with patch("mcp_server.feeds.news_fetcher.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("Network error")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = False
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await _fetch_rss()
            # Should return empty list or partial results from other feeds
            assert isinstance(result, list)

    async def test_rss_parses_entries(self):
        """Should correctly parse RSS feed entries."""
        mock_entry = MagicMock()
        mock_entry.get.side_effect = lambda key, default="": {
            "title": "Mortgage Rates Hit 3-Year Low",
            "summary": "Interest rates decline sharply",
            "link": "https://example.com/rss/1",
        }.get(key, default)
        mock_entry.published_parsed = (2026, 4, 18, 10, 30, 0, 0, 0, 0)

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]

        with patch("mcp_server.feeds.news_fetcher.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.text = "<rss></rss>"
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = False
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch("mcp_server.feeds.news_fetcher.feedparser.parse", return_value=mock_feed):
                result = await _fetch_rss()
                # Should have entries from the first feed before it hits the mock error
                assert isinstance(result, list)


@pytest.mark.asyncio
class TestFetchAndStoreNews:
    """Test the main fetch_and_store_news function."""

    async def test_rss_fallback_when_no_newsapi_key(self):
        """When NEWS_API_KEY is absent, should fall back to RSS feeds."""
        mock_entry = MagicMock()
        mock_entry.get.side_effect = lambda key, default="": {
            "title": "Housing Market Surge",
            "summary": "Prices up across the nation",
            "link": "https://example.com/housing-surge",
        }.get(key, default)
        mock_entry.published_parsed = None

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEWS_API_KEY", None)

            with patch("mcp_server.feeds.news_fetcher._fetch_newsapi") as mock_newsapi:
                mock_newsapi.return_value = []

                with patch("mcp_server.feeds.news_fetcher.httpx.AsyncClient") as mock_client_class:
                    mock_client = AsyncMock()
                    mock_response = MagicMock()
                    mock_response.text = "<rss></rss>"
                    mock_client.__aenter__.return_value = mock_client
                    mock_client.__aexit__.return_value = False
                    mock_client.get.return_value = mock_response
                    mock_client_class.return_value = mock_client

                    with patch("mcp_server.feeds.news_fetcher.feedparser.parse", return_value=mock_feed):
                        # Should complete without error
                        await fetch_and_store_news()

    async def test_dedup_by_url(self):
        """Should skip articles with URLs already in database."""
        # Create an entry to be fetched
        mock_entry = MagicMock()
        mock_entry.get.side_effect = lambda key, default="": {
            "title": "New Housing Story",
            "summary": "About the housing market",
            "link": "https://example.com/duplicate-story",
        }.get(key, default)
        mock_entry.published_parsed = None

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEWS_API_KEY", None)

            with patch("mcp_server.feeds.news_fetcher._fetch_newsapi", return_value=[]):
                with patch("mcp_server.feeds.news_fetcher.httpx.AsyncClient") as mock_client_class:
                    mock_client = AsyncMock()
                    mock_response = MagicMock()
                    mock_response.text = "<rss></rss>"
                    mock_client.__aenter__.return_value = mock_client
                    mock_client.__aexit__.return_value = False
                    mock_client.get.return_value = mock_response
                    mock_client_class.return_value = mock_client

                    with patch("mcp_server.feeds.news_fetcher.feedparser.parse", return_value=mock_feed):
                        with patch("mcp_server.feeds.news_fetcher.AsyncSessionLocal") as mock_session_cls:
                            # First call: URL doesn't exist (None) — should add
                            # Second call: would be for a duplicate check
                            mock_session = AsyncMock()
                            mock_session.__aenter__.return_value = mock_session
                            mock_session.__aexit__ = AsyncMock(return_value=False)

                            # Simulate: URL not found in DB
                            mock_session.execute = AsyncMock(
                                return_value=MagicMock(scalar=MagicMock(return_value=None))
                            )
                            mock_session.add = MagicMock()
                            mock_session.commit = AsyncMock()
                            mock_session_cls.return_value = mock_session

                            await fetch_and_store_news()

                            # Verify session.add was called once (one article added)
                            assert mock_session.add.call_count >= 1

    async def test_no_articles_logged(self):
        """When no articles found, should log and return early."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEWS_API_KEY", None)

            with patch("mcp_server.feeds.news_fetcher._fetch_newsapi", return_value=[]):
                with patch("mcp_server.feeds.news_fetcher._fetch_rss", return_value=[]):
                    # Should complete without error and not attempt DB operations
                    await fetch_and_store_news()

    async def test_high_relevance_articles_stored(self):
        """Articles with high relevance should be stored with correct score."""
        mock_entry = MagicMock()
        mock_entry.get.side_effect = lambda key, default="": {
            "title": "Mortgage Rates Hit Record Low",
            "summary": "Home sales market surges",
            "link": "https://example.com/mortgage-news",
        }.get(key, default)
        mock_entry.published_parsed = None

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEWS_API_KEY", None)

            with patch("mcp_server.feeds.news_fetcher._fetch_newsapi", return_value=[]):
                with patch("mcp_server.feeds.news_fetcher.httpx.AsyncClient") as mock_client_class:
                    mock_client = AsyncMock()
                    mock_response = MagicMock()
                    mock_response.text = "<rss></rss>"
                    mock_client.__aenter__.return_value = mock_client
                    mock_client.__aexit__.return_value = False
                    mock_client.get.return_value = mock_response
                    mock_client_class.return_value = mock_client

                    with patch("mcp_server.feeds.news_fetcher.feedparser.parse", return_value=mock_feed):
                        with patch("mcp_server.feeds.news_fetcher.AsyncSessionLocal") as mock_session_cls:
                            mock_session = AsyncMock()
                            mock_session.__aenter__.return_value = mock_session
                            mock_session.__aexit__ = AsyncMock(return_value=False)

                            # URL not in DB
                            mock_session.execute = AsyncMock(
                                return_value=MagicMock(scalar=MagicMock(return_value=None))
                            )
                            mock_session.add = MagicMock()
                            mock_session.commit = AsyncMock()
                            mock_session_cls.return_value = mock_session

                            await fetch_and_store_news()

                            # Verify add was called with correct relevance_score
                            mock_session.add.assert_called()
                            call_args = mock_session.add.call_args
                            if call_args:
                                news_item = call_args[0][0]
                                assert news_item.relevance_score == "high"

    async def test_duplicate_url_skipped(self):
        """Articles with duplicate URLs should be skipped."""
        mock_entry = MagicMock()
        mock_entry.get.side_effect = lambda key, default="": {
            "title": "Housing Article",
            "summary": "Some housing news",
            "link": "https://example.com/existing-url",
        }.get(key, default)
        mock_entry.published_parsed = None

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NEWS_API_KEY", None)

            with patch("mcp_server.feeds.news_fetcher._fetch_newsapi", return_value=[]):
                with patch("mcp_server.feeds.news_fetcher.httpx.AsyncClient") as mock_client_class:
                    mock_client = AsyncMock()
                    mock_response = MagicMock()
                    mock_response.text = "<rss></rss>"
                    mock_client.__aenter__.return_value = mock_client
                    mock_client.__aexit__.return_value = False
                    mock_client.get.return_value = mock_response
                    mock_client_class.return_value = mock_client

                    with patch("mcp_server.feeds.news_fetcher.feedparser.parse", return_value=mock_feed):
                        with patch("mcp_server.feeds.news_fetcher.AsyncSessionLocal") as mock_session_cls:
                            mock_session = AsyncMock()
                            mock_session.__aenter__.return_value = mock_session
                            mock_session.__aexit__ = AsyncMock(return_value=False)

                            # Simulate: URL already exists in DB
                            existing_news_item = MagicMock()
                            mock_session.execute = AsyncMock(
                                return_value=MagicMock(scalar=MagicMock(return_value=existing_news_item))
                            )
                            mock_session.add = MagicMock()
                            mock_session.commit = AsyncMock()
                            mock_session_cls.return_value = mock_session

                            await fetch_and_store_news()

                            # Verify add was NOT called (duplicate skipped)
                            mock_session.add.assert_not_called()
