"""
Tests for AIGenerator.

All Anthropic API calls are intercepted via patch('ai_generator.anthropic.Anthropic').

Includes two "bug detector" test classes:
  - TestAPIKeyValidation  : Bug 1 — placeholder key raises AuthenticationError
  - TestUnsafeContentAccess : Bug 2 — content[0].text raises IndexError when content=[]
"""
import pytest
import anthropic
from unittest.mock import MagicMock, patch

from conftest import (
    make_text_message,
    make_tool_use_message,
    make_empty_content_message,
)
from ai_generator import AIGenerator


MODEL = "claude-sonnet-4-20250514"
VALID_FAKE_KEY = "sk-ant-test-validlookingkeyformat123456"
PLACEHOLDER_KEY = "your-api-key-here"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_client(mock_anthropic_client):
    with patch("ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client):
        yield mock_anthropic_client


@pytest.fixture
def generator(mock_client):
    return AIGenerator(api_key=VALID_FAKE_KEY, model=MODEL)


@pytest.fixture
def mock_tool_manager():
    tm = MagicMock()
    tm.execute_tool.return_value = "Tool result: Python uses indentation for blocks."
    return tm


# ── Direct text response (no tool use) ───────────────────────────────────────

class TestGenerateResponseDirect:

    def test_returns_text_from_direct_response(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_message(
            "Python was created by Guido van Rossum."
        )

        result = generator.generate_response(query="Who created Python?")

        assert result == "Python was created by Guido van Rossum."

    def test_direct_response_calls_api_once(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_message("Direct answer.")

        generator.generate_response(query="What is 2+2?")

        assert mock_client.messages.create.call_count == 1

    def test_direct_response_includes_query_in_messages(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_message("answer")

        generator.generate_response(query="Explain gradient descent")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "user"
        assert "Explain gradient descent" in messages[0]["content"]

    def test_direct_response_includes_system_prompt(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_message("answer")

        generator.generate_response(query="test")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "system" in call_kwargs
        assert len(call_kwargs["system"]) > 0

    def test_tools_added_to_api_params_when_provided(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_message("answer")
        fake_tools = [{"name": "search_course_content", "description": "...", "input_schema": {}}]

        generator.generate_response(query="test", tools=fake_tools)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "tools" in call_kwargs
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    def test_no_tools_param_when_tools_not_provided(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_message("answer")

        generator.generate_response(query="test", tools=None)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "tools" not in call_kwargs

    def test_conversation_history_appended_to_system_prompt(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_message("answer")

        generator.generate_response(
            query="follow-up question",
            conversation_history="User: hello\nAssistant: hi",
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "Previous conversation" in call_kwargs["system"]
        assert "User: hello" in call_kwargs["system"]


# ── Tool-use branch → _handle_tool_execution ─────────────────────────────────

class TestHandleToolExecution:

    def test_tool_use_stop_reason_triggers_second_api_call(
        self, generator, mock_client, mock_tool_manager
    ):
        mock_client.messages.create.side_effect = [
            make_tool_use_message("search_course_content", "toolu_abc", {"query": "python basics"}),
            make_text_message("Python is a programming language."),
        ]

        result = generator.generate_response(
            query="What is Python?",
            tools=[{"name": "search_course_content", "description": "", "input_schema": {}}],
            tool_manager=mock_tool_manager,
        )

        assert result == "Python is a programming language."
        assert mock_client.messages.create.call_count == 2

    def test_execute_tool_called_with_correct_name_and_input(
        self, generator, mock_client, mock_tool_manager
    ):
        mock_client.messages.create.side_effect = [
            make_tool_use_message(
                "search_course_content", "toolu_xyz",
                {"query": "chromadb collections", "course_name": "RAG Course"},
            ),
            make_text_message("ChromaDB answer."),
        ]

        generator.generate_response(query="ChromaDB?", tools=[{}], tool_manager=mock_tool_manager)

        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="chromadb collections",
            course_name="RAG Course",
        )

    def test_final_api_call_has_no_tools_param(
        self, generator, mock_client, mock_tool_manager
    ):
        """
        The final call after tool execution MUST NOT include 'tools' or 'tool_choice'.
        Sending tools in the final call causes an Anthropic API error.
        """
        mock_client.messages.create.side_effect = [
            make_tool_use_message("search_course_content", "toolu_01", {"query": "test"}),
            make_text_message("Final answer."),
        ]

        generator.generate_response(query="test", tools=[{}], tool_manager=mock_tool_manager)

        final_call_kwargs = mock_client.messages.create.call_args_list[1].kwargs
        assert "tools" not in final_call_kwargs, (
            "Final API call must not include 'tools'"
        )
        assert "tool_choice" not in final_call_kwargs

    def test_multi_turn_message_structure_is_correct(
        self, generator, mock_client, mock_tool_manager
    ):
        """
        After tool execution, messages sent to the final API call must be:
          [user_query, assistant_tool_use, user_tool_result]
        """
        tool_response = make_tool_use_message(
            "search_course_content", "toolu_seq01", {"query": "lesson content"},
        )
        mock_client.messages.create.side_effect = [
            tool_response,
            make_text_message("Synthesised answer."),
        ]
        mock_tool_manager.execute_tool.return_value = "Lesson content about RAG."

        generator.generate_response(
            query="lesson content?", tools=[{}], tool_manager=mock_tool_manager
        )

        final_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
        assert len(final_messages) == 3, f"Expected 3 messages, got {len(final_messages)}"

        assert final_messages[0]["role"] == "user"
        assert "lesson content?" in final_messages[0]["content"]

        assert final_messages[1]["role"] == "assistant"
        assert final_messages[1]["content"] == tool_response.content

        assert final_messages[2]["role"] == "user"
        tool_result_block = final_messages[2]["content"][0]
        assert tool_result_block["type"] == "tool_result"
        assert tool_result_block["tool_use_id"] == "toolu_seq01"
        assert tool_result_block["content"] == "Lesson content about RAG."

    def test_tool_result_content_is_string_from_execute_tool(
        self, generator, mock_client, mock_tool_manager
    ):
        mock_tool_manager.execute_tool.return_value = "Specific tool output string."
        mock_client.messages.create.side_effect = [
            make_tool_use_message("search_course_content", "toolu_c", {"query": "x"}),
            make_text_message("ok"),
        ]

        generator.generate_response(query="x", tools=[{}], tool_manager=mock_tool_manager)

        final_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
        tool_result = final_messages[2]["content"][0]
        assert tool_result["content"] == "Specific tool output string."


# ── Bug 1 — Invalid API key causes AuthenticationError ───────────────────────

class TestAPIKeyValidation:

    def test_placeholder_key_raises_authentication_error_on_api_call(self):
        """
        BUG 1 DETECTOR — ROOT CAUSE of 'Query failed'.

        The .env contains ANTHROPIC_API_KEY=your-api-key-here (36 bytes, placeholder).
        Any real Anthropic API call with this key raises AuthenticationError (HTTP 401).

        Flow in production:
          config.py → ANTHROPIC_API_KEY = 'your-api-key-here'
          AIGenerator.__init__ → anthropic.Anthropic(api_key='your-api-key-here')
          generate_response → client.messages.create() → AuthenticationError
          app.py:73-74 → except Exception → HTTP 500
          script.js:78 → 'Query failed'

        FIX: Replace 'your-api-key-here' in .env with a real sk-ant-... key.
        """
        real_generator = AIGenerator(api_key=PLACEHOLDER_KEY, model=MODEL)

        with pytest.raises(anthropic.AuthenticationError) as exc_info:
            real_generator.generate_response(query="What is Python?")

        assert exc_info.value.status_code == 401

    def test_authentication_error_propagates_out_of_generate_response(self):
        """
        AuthenticationError must NOT be swallowed inside generate_response.
        It must propagate to app.py's exception handler.
        """
        import httpx
        mock_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        mock_response = httpx.Response(401, request=mock_request, text="Unauthorized")
        auth_error = anthropic.AuthenticationError(
            message="Invalid API key",
            response=mock_response,
            body=None,
        )

        mock_client_instance = MagicMock()
        mock_client_instance.messages.create.side_effect = auth_error

        with patch("ai_generator.anthropic.Anthropic", return_value=mock_client_instance):
            gen = AIGenerator(api_key="bad-key", model=MODEL)
            with pytest.raises(anthropic.AuthenticationError):
                gen.generate_response(query="anything")


# ── Bug 2 — Unsafe content[0].text access ────────────────────────────────────

class TestUnsafeContentAccess:

    def test_empty_content_list_raises_value_error_in_direct_path(
        self, generator, mock_client
    ):
        """
        BUG 2 FIX VERIFIED — ai_generator.py direct path.

        After the fix, empty content raises ValueError with a descriptive message
        instead of a silent IndexError.
        """
        mock_client.messages.create.return_value = make_empty_content_message()

        with pytest.raises(ValueError, match="No text block in response content"):
            generator.generate_response(query="What is Python?")

    def test_empty_content_list_raises_value_error_in_tool_execution_path(
        self, generator, mock_client, mock_tool_manager
    ):
        """
        BUG 2 FIX VERIFIED — ai_generator.py tool execution path.

        After the fix, empty final response content raises ValueError.
        """
        mock_client.messages.create.side_effect = [
            make_tool_use_message("search_course_content", "toolu_bug2", {"query": "test"}),
            make_empty_content_message(),
        ]

        with pytest.raises(ValueError, match="No text block in final response"):
            generator.generate_response(
                query="test", tools=[{}], tool_manager=mock_tool_manager
            )
