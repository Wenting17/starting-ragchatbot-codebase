# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Dependencies are managed with `uv` and require Python 3.13+. **Always use `uv` — never `pip` — to install deps or run the server.** An `ANTHROPIC_API_KEY` must be set in a `.env` file at the repo root.

- Install deps: `uv sync`
- Run app (from repo root): `./run.sh` — equivalent to `cd backend && uv run uvicorn app:app --reload --port 8000`
- Web UI: `http://localhost:8000`  •  API docs: `http://localhost:8000/docs`
- On Windows, run shell commands via Git Bash.

There is no test suite or linter configured in this repo.

## Architecture

A tool-using RAG system over course transcripts. FastAPI backend + static HTML/JS frontend, ChromaDB for vectors, Claude (Anthropic) for generation.

**Request flow** (`backend/app.py` → `rag_system.py` → `ai_generator.py`):
1. `POST /api/query` creates/uses a session and calls `RAGSystem.query()`.
2. `RAGSystem` does **not** retrieve context up front. Instead it passes `ToolManager`'s tool definitions to Claude and lets the model decide whether to call `search_course_content`.
3. When Claude invokes the tool, `CourseSearchTool` (in `search_tools.py`) queries `VectorStore`, stores sources on `self.last_sources`, and returns text to the model. `RAGSystem` then drains and resets sources via the `ToolManager` after the final response.
4. `SessionManager` keeps the last `MAX_HISTORY` exchanges per session and injects them into the next prompt.

**Vector store** (`vector_store.py`): two Chroma collections — one for course metadata (used for fuzzy course-name matching) and one for chunked content. Embeddings via `sentence-transformers` (`all-MiniLM-L6-v2`). Persisted at `backend/chroma_db/` (created on first run).

**Ingestion** (`document_processor.py`): on FastAPI startup, `app.py` calls `add_course_folder("../docs")` with `clear_existing=False`. It parses each file in `docs/` into a `Course` + `Lesson`s + sentence-based `CourseChunk`s (`CHUNK_SIZE=800`, `CHUNK_OVERLAP=100`). Courses are deduped by title — **edits to an already-ingested course won't take effect** unless you delete `backend/chroma_db/` or call `add_course_folder(..., clear_existing=True)`.

**Frontend** (`frontend/`): plain `index.html` + `script.js` + `style.css`, served as static files from `/` by `app.py` with no-cache headers (`DevStaticFiles`).

**Config** (`backend/config.py`): single `Config` dataclass holds the model name (`claude-sonnet-4-20250514`), embedding model, chunk sizes, `MAX_RESULTS`, `MAX_HISTORY`, and `CHROMA_PATH`. Change behavior here rather than threading parameters through call sites.

## Adding capabilities

To add a new tool the LLM can call: subclass `Tool` in `search_tools.py` (implement `get_tool_definition` returning an Anthropic tool schema, and `execute`), then register it in `RAGSystem.__init__` via `self.tool_manager.register_tool(...)`. If it produces citations, follow `CourseSearchTool`'s pattern of populating `self.last_sources` so they flow back through `ToolManager.get_last_sources()`.
