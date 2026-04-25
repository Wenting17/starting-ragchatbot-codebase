"""
Tests for RAGSystem.query().

All heavy collaborators (AIGenerator, VectorStore, SessionManager, ToolManager,
DocumentProcessor) are mocked out. Tests cover orchestration logic only.
All tests in this file should PASS.
"""
import pytest
from unittest.mock import MagicMock, patch

from rag_system import RAGSystem


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.ANTHROPIC_API_KEY = "sk-ant-test-fake"
    cfg.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    cfg.CHROMA_PATH = ":memory:"
    cfg.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    cfg.MAX_RESULTS = 5
    cfg.CHUNK_SIZE = 800
    cfg.CHUNK_OVERLAP = 100
    cfg.MAX_HISTORY = 2
    return cfg


@pytest.fixture
def rag(mock_config):
    with patch("rag_system.DocumentProcessor"), \
         patch("rag_system.VectorStore"), \
         patch("rag_system.AIGenerator") as MockAIGen, \
         patch("rag_system.SessionManager") as MockSession, \
         patch("rag_system.ToolManager") as MockTM, \
         patch("rag_system.CourseSearchTool"), \
         patch("rag_system.CourseOutlineTool"):

        system = RAGSystem(mock_config)

        system._mock_ai = MockAIGen.return_value
        system._mock_session = MockSession.return_value
        system._mock_tm = MockTM.return_value

        system._mock_ai.generate_response.return_value = "AI generated answer."
        system._mock_session.get_conversation_history.return_value = None
        system._mock_tm.get_tool_definitions.return_value = [
            {"name": "search_course_content", "description": "", "input_schema": {}}
        ]
        system._mock_tm.get_last_sources.return_value = [
            {"name": "Python Basics - Lesson 1", "link": "https://example.com/1"}
        ]

        yield system


# ── Return type contract ──────────────────────────────────────────────────────

class TestRAGSystemQueryContract:

    def test_query_returns_tuple(self, rag):
        result = rag.query("What is Python?")

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_query_first_element_is_string(self, rag):
        answer, _ = rag.query("What is Python?")

        assert isinstance(answer, str)
        assert answer == "AI generated answer."

    def test_query_second_element_is_list(self, rag):
        _, sources = rag.query("What is Python?")

        assert isinstance(sources, list)

    def test_query_returns_sources_from_tool_manager(self, rag):
        rag._mock_tm.get_last_sources.return_value = [
            {"name": "Course A - Lesson 3", "link": "https://example.com/a/3"}
        ]

        _, sources = rag.query("something")

        assert sources == [{"name": "Course A - Lesson 3", "link": "https://example.com/a/3"}]

    def test_query_returns_empty_sources_when_no_tool_called(self, rag):
        rag._mock_tm.get_last_sources.return_value = []

        _, sources = rag.query("general knowledge question")

        assert sources == []


# ── generate_response call contract ──────────────────────────────────────────

class TestGenerateResponseCallContract:

    def test_prompt_wraps_user_query(self, rag):
        rag.query("explain embeddings")

        call_kwargs = rag._mock_ai.generate_response.call_args.kwargs
        assert "explain embeddings" in call_kwargs["query"]
        assert "Answer this question about course materials" in call_kwargs["query"]

    def test_tool_definitions_forwarded_to_generate_response(self, rag):
        expected_tools = [{"name": "search_course_content", "description": "", "input_schema": {}}]
        rag._mock_tm.get_tool_definitions.return_value = expected_tools

        rag.query("test query")

        call_kwargs = rag._mock_ai.generate_response.call_args.kwargs
        assert call_kwargs["tools"] == expected_tools

    def test_tool_manager_forwarded_to_generate_response(self, rag):
        rag.query("test query")

        call_kwargs = rag._mock_ai.generate_response.call_args.kwargs
        assert call_kwargs["tool_manager"] is rag.tool_manager

    def test_no_history_when_no_session(self, rag):
        rag.query("standalone question")

        call_kwargs = rag._mock_ai.generate_response.call_args.kwargs
        assert call_kwargs.get("conversation_history") is None

    def test_history_forwarded_when_session_exists(self, rag):
        rag._mock_session.get_conversation_history.return_value = (
            "User: hello\nAssistant: hi there"
        )

        rag.query("follow up", session_id="session_1")

        call_kwargs = rag._mock_ai.generate_response.call_args.kwargs
        assert call_kwargs["conversation_history"] == "User: hello\nAssistant: hi there"

    def test_history_not_fetched_without_session_id(self, rag):
        rag.query("question with no session")

        rag._mock_session.get_conversation_history.assert_not_called()


# ── Source lifecycle ──────────────────────────────────────────────────────────

class TestSourceLifecycle:

    def test_get_last_sources_called_after_generate_response(self, rag):
        rag.query("test")

        rag._mock_tm.get_last_sources.assert_called_once()

    def test_reset_sources_called_after_collecting(self, rag):
        rag.query("test")

        rag._mock_tm.reset_sources.assert_called_once()

    def test_reset_called_even_when_sources_empty(self, rag):
        rag._mock_tm.get_last_sources.return_value = []

        rag.query("test")

        rag._mock_tm.reset_sources.assert_called_once()


# ── Session management ────────────────────────────────────────────────────────

class TestSessionManagement:

    def test_add_exchange_called_with_original_query_and_response(self, rag):
        rag._mock_ai.generate_response.return_value = "The answer is X."

        rag.query("What is X?", session_id="session_1")

        rag._mock_session.add_exchange.assert_called_once_with(
            "session_1", "What is X?", "The answer is X."
        )

    def test_add_exchange_not_called_without_session_id(self, rag):
        rag.query("ephemeral question")

        rag._mock_session.add_exchange.assert_not_called()

    def test_get_conversation_history_called_with_correct_session_id(self, rag):
        rag.query("continuation", session_id="my_session")

        rag._mock_session.get_conversation_history.assert_called_once_with("my_session")
