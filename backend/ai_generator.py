import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Tool Usage:
- **search_course_content**: Use for questions about specific course content or detailed educational materials
- **get_course_outline**: Use for questions about a course's structure, outline, or lesson list. When returning outline information, always include the course title, course link, and the full lesson list with each lesson's number and title.
- **Up to 2 sequential tool calls per query** — use a second tool only when the first result is needed to form the next search
- Synthesize results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course outline/structure questions**: Use get_course_outline, then present the course title, course link, and all lessons (number and title)
- **Course content questions**: Use search_course_content, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        # auth_token=None prevents conflict when ANTHROPIC_AUTH_TOKEN is set in the
        # environment (e.g. when the server is started from a Claude Code terminal session).
        self.client = anthropic.Anthropic(api_key=api_key, auth_token=None)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._run_tool_loop(response, api_params, tool_manager)
        
        # Return direct response
        text_blocks = [b for b in response.content if hasattr(b, "text")]
        if not text_blocks:
            raise ValueError(f"No text block in response content: {response.content}")
        return text_blocks[0].text
    
    def _run_tool_loop(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Execute up to MAX_TOOL_ROUNDS of tool calls, each in a separate API request.

        Terminates early if Claude stops requesting tools. After hitting the round cap,
        makes a final synthesis call without tools to produce a text answer.
        """
        messages = base_params["messages"].copy()
        current_response = initial_response
        rounds_completed = 0

        while True:
            # Append full assistant turn (text blocks + tool_use blocks)
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute all tool calls in this round
            tool_results = []
            for block in current_response.content:
                if block.type == "tool_use":
                    result = tool_manager.execute_tool(block.name, **block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            rounds_completed += 1

            if rounds_completed >= self.MAX_TOOL_ROUNDS:
                break

            # Next API call with tools — Claude may call another tool or answer directly
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
                "tools": base_params["tools"],
                "tool_choice": {"type": "auto"}
            }
            current_response = self.client.messages.create(**next_params)

            # Claude finished without another tool call — return directly, no synthesis needed
            if current_response.stop_reason != "tool_use":
                text_blocks = [b for b in current_response.content if hasattr(b, "text")]
                if not text_blocks:
                    raise ValueError(f"No text block in response: {current_response.content}")
                return text_blocks[0].text

        # Round cap reached — final synthesis call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        final_response = self.client.messages.create(**final_params)
        text_blocks = [b for b in final_response.content if hasattr(b, "text")]
        if not text_blocks:
            raise ValueError(f"No text block in final response: {final_response.content}")
        return text_blocks[0].text