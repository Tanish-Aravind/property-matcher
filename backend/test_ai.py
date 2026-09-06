"""Basic tests for ai.py with mocked API responses (no real API calls)."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import ai


@pytest.mark.asyncio
async def test_generate_summary_gemini(monkeypatch):
    monkeypatch.setattr(ai, "AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    fake_response = MagicMock()
    fake_response.text = "A spacious 3BHK apartment in Koramangala priced at 1.2 crore."

    with patch("google.generativeai.configure"), \
         patch("google.generativeai.GenerativeModel") as mock_model_cls:
        mock_model_cls.return_value.generate_content.return_value = fake_response
        result = await ai.generate_summary("raw brochure text here")

    assert "Koramangala" in result


@pytest.mark.asyncio
async def test_generate_embedding_gemini(monkeypatch):
    monkeypatch.setattr(ai, "AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with patch("google.generativeai.configure"), \
         patch("google.generativeai.embed_content") as mock_embed:
        mock_embed.return_value = {"embedding": [0.1, 0.2, 0.3]}
        result = await ai.generate_embedding("some summary text")

    assert result == [0.1, 0.2, 0.3]
    mock_embed.assert_called_once_with(
        model="models/gemini-embedding-001",
        content="some summary text",
        output_dimensionality=768,
    )


@pytest.mark.asyncio
async def test_extract_search_filters_gemini(monkeypatch):
    monkeypatch.setattr(ai, "AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    fake_response = MagicMock()
    fake_response.text = json.dumps({
        "bedrooms": 3,
        "min_price": None,
        "max_price": 40000000,
        "location": None,
        "property_type": None,
    })

    with patch("google.generativeai.configure"), \
         patch("google.generativeai.GenerativeModel") as mock_model_cls:
        mock_model_cls.return_value.generate_content.return_value = fake_response
        result = await ai.extract_search_filters("3bhk under 4cr")

    assert result["bedrooms"] == 3
    assert result["max_price"] == 40000000


@pytest.mark.asyncio
async def test_rerank_candidates_gemini(monkeypatch):
    monkeypatch.setattr(ai, "AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    fake_response = MagicMock()
    fake_response.text = json.dumps([
        {"id": "abc123", "reason": "Matches budget and location closely."},
        {"id": "def456", "reason": "Right bedroom count but pricier."},
    ])

    with patch("google.generativeai.configure"), \
         patch("google.generativeai.GenerativeModel") as mock_model_cls:
        mock_model_cls.return_value.generate_content.return_value = fake_response
        result = await ai.rerank_candidates(
            "3BHK under 1.5cr in Koramangala",
            [{"id": "abc123", "summary": "..."}, {"id": "def456", "summary": "..."}],
        )

    assert result[0]["id"] == "abc123"
    assert "reason" in result[0]
