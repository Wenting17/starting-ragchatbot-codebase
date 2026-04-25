import sys
import os
import pytest
from unittest.mock import MagicMock

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ── SearchResults helpers ────────────────────────────────────────────────────

from vector_store import SearchResults


def make_search_results(docs, metadata, distances=None, error=None):
    if error:
        return SearchResults.empty(error)
    return SearchResults(
        documents=docs,
        metadata=metadata,
        distances=distances or [0.1] * len(docs),
        error=None,
    )


# ── Anthropic response helpers (MagicMock-based, version-agnostic) ───────────

def make_text_message(text: str):
    msg = MagicMock()
    msg.stop_reason = "end_turn"
    block = MagicMock()
    block.type = "text"
    block.text = text
    msg.content = [block]
    return msg


def make_tool_use_message(tool_name: str, tool_id: str, tool_input: dict):
    msg = MagicMock()
    msg.stop_reason = "tool_use"
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = tool_name
    block.input = tool_input
    msg.content = [block]
    return msg


def make_empty_content_message():
    msg = MagicMock()
    msg.stop_reason = "end_turn"
    msg.content = []
    return msg


# ── Shared fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.get_lesson_link.return_value = "https://example.com/lesson/1"
    store.get_course_link.return_value = "https://example.com/course"
    return store


@pytest.fixture
def mock_anthropic_client():
    return MagicMock()
