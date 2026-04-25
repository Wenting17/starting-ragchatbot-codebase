Refactor @backend/ai_generator.py to support sequential tool calling where Claude can make up to 2 tool calls in separate API rounds.

# 1. 清晰定义现状

Current behavior:

- Claude makes 1 tool call → tools are removed from API params → final response
- If Claude wants another tool call after seeing results, it can't (gets empty response)

# 2. 清晰定义目标

Desired behavior:

- Each tool call should be a separate API request where Claude can reason about previous results
- Support for complex queries requiring multiple searches...

# 3. 提供具体示例

Example flow:

1. User: "Search for a course that discusses the same topic as lesson 4 of course X"
2. Claude: get course outline for course X - gets title of lesson 4
3. Claude: uses the title to search for a course that discusses the same topic → returns course information
4. Claude: provides complete answer

# 4. 给出明确的技术约束

Requirements:

- Maximum 2 sequential rounds per user query
- Terminate when: (a) 2 rounds completed, (b) Claude's response has no tool_use blocks, or (c) tool call fails
- ...

# 5. 提出元指令：派出子智能体

Use two parallel subagents to brainstorm possible plans. Do not implement any code.
