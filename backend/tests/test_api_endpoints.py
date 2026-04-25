"""
Tests for FastAPI API endpoints (/api/query, /api/courses).

Uses the test-only app from conftest._build_test_app so no frontend/
directory or ChromaDB initialisation is needed.
"""
import pytest


# ── POST /api/query ───────────────────────────────────────────────────────────

class TestQueryEndpoint:

    def test_returns_200_on_valid_request(self, api_client):
        response = api_client.post("/api/query", json={"query": "What is Python?"})

        assert response.status_code == 200

    def test_response_contains_answer(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("Python is a language.", [])

        response = api_client.post("/api/query", json={"query": "What is Python?"})

        assert response.json()["answer"] == "Python is a language."

    def test_response_contains_sources_list(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = (
            "Answer.",
            [{"name": "Python Basics - Lesson 1", "link": "https://example.com/1"}],
        )

        response = api_client.post("/api/query", json={"query": "functions"})
        sources = response.json()["sources"]

        assert isinstance(sources, list)
        assert sources[0]["name"] == "Python Basics - Lesson 1"

    def test_response_contains_session_id(self, api_client):
        response = api_client.post("/api/query", json={"query": "test"})

        assert "session_id" in response.json()
        assert response.json()["session_id"]

    def test_auto_creates_session_when_not_provided(self, api_client, mock_rag_system):
        mock_rag_system.session_manager.create_session.return_value = "new-session-abc"

        response = api_client.post("/api/query", json={"query": "test"})

        mock_rag_system.session_manager.create_session.assert_called_once()
        assert response.json()["session_id"] == "new-session-abc"

    def test_uses_provided_session_id(self, api_client, mock_rag_system):
        response = api_client.post(
            "/api/query",
            json={"query": "follow-up", "session_id": "existing-session-xyz"},
        )

        mock_rag_system.session_manager.create_session.assert_not_called()
        assert response.json()["session_id"] == "existing-session-xyz"

    def test_passes_query_to_rag_system(self, api_client, mock_rag_system):
        api_client.post("/api/query", json={"query": "explain embeddings"})

        call_args = mock_rag_system.query.call_args
        assert call_args.args[0] == "explain embeddings"

    def test_passes_session_id_to_rag_system(self, api_client, mock_rag_system):
        api_client.post(
            "/api/query",
            json={"query": "test", "session_id": "my-session"},
        )

        call_args = mock_rag_system.query.call_args
        assert call_args.args[1] == "my-session"

    def test_returns_500_when_rag_system_raises(self, api_client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("Internal failure")

        response = api_client.post("/api/query", json={"query": "test"})

        assert response.status_code == 500
        assert "Internal failure" in response.json()["detail"]

    def test_returns_422_when_query_field_missing(self, api_client):
        response = api_client.post("/api/query", json={"session_id": "only-session"})

        assert response.status_code == 422

    def test_returns_422_on_empty_body(self, api_client):
        response = api_client.post("/api/query", json={})

        assert response.status_code == 422

    def test_empty_sources_list_serialises_correctly(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("No sources answer.", [])

        response = api_client.post("/api/query", json={"query": "general question"})

        assert response.json()["sources"] == []


# ── GET /api/courses ──────────────────────────────────────────────────────────

class TestCoursesEndpoint:

    def test_returns_200(self, api_client):
        response = api_client.get("/api/courses")

        assert response.status_code == 200

    def test_returns_total_courses_count(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 5,
            "course_titles": ["A", "B", "C", "D", "E"],
        }

        response = api_client.get("/api/courses")

        assert response.json()["total_courses"] == 5

    def test_returns_course_titles_list(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Python Basics", "RAG Chatbot"],
        }

        response = api_client.get("/api/courses")

        assert response.json()["course_titles"] == ["Python Basics", "RAG Chatbot"]

    def test_total_courses_matches_titles_length(self, api_client, mock_rag_system):
        titles = ["Course X", "Course Y", "Course Z"]
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": len(titles),
            "course_titles": titles,
        }

        data = api_client.get("/api/courses").json()

        assert data["total_courses"] == len(data["course_titles"])

    def test_empty_course_catalog(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        response = api_client.get("/api/courses")

        assert response.status_code == 200
        assert response.json()["total_courses"] == 0
        assert response.json()["course_titles"] == []

    def test_returns_500_when_analytics_raises(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("DB unavailable")

        response = api_client.get("/api/courses")

        assert response.status_code == 500
        assert "DB unavailable" in response.json()["detail"]
