"""
Tests for CourseSearchTool.execute() and ToolManager.

All tests are pure unit tests — no ChromaDB, no network.
Every test in this file should PASS when the codebase is correct.
"""
import pytest
from unittest.mock import MagicMock

from conftest import make_search_results
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def search_tool(mock_vector_store):
    return CourseSearchTool(vector_store=mock_vector_store)


@pytest.fixture
def tool_manager(search_tool):
    tm = ToolManager()
    tm.register_tool(search_tool)
    return tm


# ── Happy path ────────────────────────────────────────────────────────────────

class TestCourseSearchToolExecute:

    def test_returns_formatted_string_when_results_exist(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["Python is a high-level language."],
            metadata=[{"course_title": "Python Basics", "lesson_number": 1}],
        )

        result = search_tool.execute(query="what is python")

        assert isinstance(result, str)
        assert "Python Basics" in result
        assert "Lesson 1" in result
        assert "Python is a high-level language." in result

    def test_passes_query_to_vector_store(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["content"], metadata=[{"course_title": "Test", "lesson_number": 1}]
        )

        search_tool.execute(query="RAG architecture explained")

        mock_vector_store.search.assert_called_once_with(
            query="RAG architecture explained",
            course_name=None,
            lesson_number=None,
        )

    def test_passes_course_name_filter_to_store(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["content"], metadata=[{"course_title": "MCP Course", "lesson_number": 2}]
        )

        search_tool.execute(query="tool use", course_name="MCP")

        mock_vector_store.search.assert_called_once_with(
            query="tool use",
            course_name="MCP",
            lesson_number=None,
        )

    def test_passes_lesson_number_filter_to_store(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["content"], metadata=[{"course_title": "RAG Course", "lesson_number": 3}]
        )

        search_tool.execute(query="embeddings", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="embeddings",
            course_name=None,
            lesson_number=3,
        )

    def test_passes_both_filters_to_store(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["content"], metadata=[{"course_title": "Deep Learning", "lesson_number": 5}]
        )

        search_tool.execute(query="backprop", course_name="Deep Learning", lesson_number=5)

        mock_vector_store.search.assert_called_once_with(
            query="backprop",
            course_name="Deep Learning",
            lesson_number=5,
        )


# ── Empty / error paths ───────────────────────────────────────────────────────

    def test_returns_no_content_found_when_results_empty(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(docs=[], metadata=[])

        result = search_tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_empty_message_includes_course_name_filter(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(docs=[], metadata=[])

        result = search_tool.execute(query="something", course_name="Obscure Course")

        assert "Obscure Course" in result

    def test_empty_message_includes_lesson_number_filter(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(docs=[], metadata=[])

        result = search_tool.execute(query="something", lesson_number=7)

        assert "7" in result

    def test_returns_error_string_from_search_results(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults.empty(
            "No course found matching 'fake-course'"
        )

        result = search_tool.execute(query="test", course_name="fake-course")

        assert result == "No course found matching 'fake-course'"

    def test_search_error_takes_precedence_over_empty_check(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error="Search error: timeout"
        )

        result = search_tool.execute(query="anything")

        assert result == "Search error: timeout"


# ── Source dict format ────────────────────────────────────────────────────────

class TestCourseSearchToolSources:

    def test_last_sources_is_list_of_dicts_with_name_and_link(self, search_tool, mock_vector_store):
        """Pins the new List[dict] source format — not the old List[str]."""
        mock_vector_store.search.return_value = make_search_results(
            docs=["content"],
            metadata=[{"course_title": "Python Basics", "lesson_number": 2}],
        )
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson/2"

        search_tool.execute(query="functions")

        assert len(search_tool.last_sources) == 1
        source = search_tool.last_sources[0]
        assert isinstance(source, dict), "Source must be a dict, not a string"
        assert "name" in source
        assert "link" in source

    def test_source_name_includes_lesson_number(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["doc"],
            metadata=[{"course_title": "RAG Chatbot", "lesson_number": 3}],
        )

        search_tool.execute(query="vector search")

        assert search_tool.last_sources[0]["name"] == "RAG Chatbot - Lesson 3"

    def test_source_name_is_course_title_when_no_lesson(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["doc"],
            metadata=[{"course_title": "Intro to AI"}],
        )

        search_tool.execute(query="neural nets")

        assert search_tool.last_sources[0]["name"] == "Intro to AI"

    def test_source_link_uses_lesson_link_when_available(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["doc"],
            metadata=[{"course_title": "MCP Course", "lesson_number": 1}],
        )
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson/1"

        search_tool.execute(query="MCP tools")

        assert search_tool.last_sources[0]["link"] == "https://example.com/lesson/1"
        mock_vector_store.get_lesson_link.assert_called_once_with("MCP Course", 1)

    def test_source_link_falls_back_to_course_link(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["doc"],
            metadata=[{"course_title": "MCP Course", "lesson_number": 1}],
        )
        mock_vector_store.get_lesson_link.return_value = None
        mock_vector_store.get_course_link.return_value = "https://example.com/course"

        search_tool.execute(query="MCP tools")

        assert search_tool.last_sources[0]["link"] == "https://example.com/course"

    def test_multiple_results_produce_multiple_sources(self, search_tool, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["doc1", "doc2"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
        )
        mock_vector_store.get_lesson_link.side_effect = [
            "https://example.com/a/1",
            "https://example.com/b/2",
        ]

        search_tool.execute(query="broad topic")

        assert len(search_tool.last_sources) == 2
        assert search_tool.last_sources[0]["name"] == "Course A - Lesson 1"
        assert search_tool.last_sources[1]["name"] == "Course B - Lesson 2"


# ── ToolManager ───────────────────────────────────────────────────────────────

class TestToolManager:

    def test_register_and_execute_known_tool(self, tool_manager, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["result"], metadata=[{"course_title": "C", "lesson_number": 1}]
        )

        result = tool_manager.execute_tool("search_course_content", query="test query")

        assert "result" in result

    def test_execute_unknown_tool_returns_error_string(self, tool_manager):
        result = tool_manager.execute_tool("nonexistent_tool", query="x")

        assert "nonexistent_tool" in result
        assert "not found" in result.lower()

    def test_get_tool_definitions_returns_list(self, tool_manager):
        definitions = tool_manager.get_tool_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) >= 1
        assert all(isinstance(d, dict) for d in definitions)

    def test_get_tool_definitions_contains_search_tool(self, tool_manager):
        names = [d["name"] for d in tool_manager.get_tool_definitions()]

        assert "search_course_content" in names

    def test_get_last_sources_returns_populated_sources(self, tool_manager):
        tool_manager.tools["search_course_content"].last_sources = [
            {"name": "Course X - Lesson 1", "link": "https://example.com/x/1"}
        ]

        sources = tool_manager.get_last_sources()

        assert sources == [{"name": "Course X - Lesson 1", "link": "https://example.com/x/1"}]

    def test_get_last_sources_returns_empty_when_none(self, tool_manager):
        tool_manager.reset_sources()

        assert tool_manager.get_last_sources() == []

    def test_reset_sources_clears_all_tools(self, tool_manager):
        tool_manager.tools["search_course_content"].last_sources = [
            {"name": "Stale", "link": None}
        ]

        tool_manager.reset_sources()

        assert tool_manager.tools["search_course_content"].last_sources == []
        assert tool_manager.get_last_sources() == []

    def test_execute_tool_passes_kwargs_through(self, tool_manager, mock_vector_store):
        mock_vector_store.search.return_value = make_search_results(
            docs=["doc"], metadata=[{"course_title": "C", "lesson_number": 2}]
        )

        tool_manager.execute_tool(
            "search_course_content",
            query="embeddings",
            course_name="RAG Course",
            lesson_number=2,
        )

        mock_vector_store.search.assert_called_once_with(
            query="embeddings",
            course_name="RAG Course",
            lesson_number=2,
        )
