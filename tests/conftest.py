"""Pytest configuration and automatic fixtures for offline unit tests."""

from unittest.mock import patch

import pytest

from linkedin_intelligence.tools.retrieval_service import LinkedInRetrievalService


@pytest.fixture(autouse=True)
def mock_retrieval_unless_live(request):
    """Automatically mock external Apify calls during normal unit tests."""
    if "live" in request.keywords:
        yield
        return

    # In normal tests, force retrieval to use the local fixture
    async def mocked_search(self, plan):
        return self._load_fixture_data(plan.queries)

    with patch.object(LinkedInRetrievalService, "search", new=mocked_search):
        yield
