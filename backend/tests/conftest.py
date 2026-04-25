import sys
import os
import pytest
from unittest.mock import MagicMock
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

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


# ── API test-app factory ─────────────────────────────────────────────────────
# Mirrors app.py routes without the StaticFiles mount or startup ingestion,
# so tests can run without a frontend/ directory or ChromaDB.

def _build_test_app(rag_system) -> FastAPI:
    """Return a FastAPI app wired to rag_system (any MagicMock or real instance)."""

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[dict]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    _app = FastAPI()

    @_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return _app


@pytest.fixture
def mock_rag_system():
    rag = MagicMock()
    rag.session_manager.create_session.return_value = "auto-session-id"
    rag.query.return_value = ("Default answer.", [])
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course A", "Course B"],
    }
    return rag


@pytest.fixture
def api_client(mock_rag_system):
    """TestClient for the API-only test app (no static files)."""
    return TestClient(_build_test_app(mock_rag_system))
