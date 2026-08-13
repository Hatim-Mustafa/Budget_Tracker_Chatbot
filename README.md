# Insight Chat — Data-aware conversational assistant

Insight Chat is a self-hosted chat application that lets users ask natural
language questions about datasets and receive AI-generated answers with
interactive visualizations. The frontend uses a chat UI and the backend runs
an agent pipeline that can plan visualizations and return executable specs.

Key features
- Natural-language chat interface with conversation history and multiple chats.
- Authentication (signup/login) and per-user conversation persistence.
- Agent pipeline on the backend that can summarize long histories and plan
	visualizations via a `VisualizationPlanner` tool.
- Visualizations rendered in the UI using ECharts; multiple chart types
	(line, bar, pie, scatter, heatmap, treemap, etc.).
- Clean, responsive UI built with MUI and MUI X Chat components.

Architecture overview
- Backend (Python / FastAPI): implements API endpoints (`/conversations`,
	`/chat`, auth), conversation storage, and an agent orchestration layer that
	runs models and tools to produce text answers and visualization specs.
- Frontend (Next.js + React): chat UI powered by `@mui/x-chat`, charts via
	ECharts, and an adapter that streams assistant replies and attaches
	visualization parts to messages.

Repo layout
- `src/` — Python backend: API server, agent code, DB layer, visualization
	planner, and supporting utilities.
- `my-chat-app/` — Next.js frontend: chat UI, auth pages, theme, and chart
	renderer (`ChartRenderer.tsx`).
- `scripts/` — helper utilities (example: `rag_doc_upload.py`).

Requirements
- Python >= 3.11 (see `pyproject.toml` for backend dependencies).
- Node.js and npm for the frontend (see `my-chat-app/package.json`).

Quickstart — Backend (development)
1. Create and activate a virtual environment:

```powershell
python -m venv .venv
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .venv\Scripts\Activate.ps1)
```

2. Install Python dependencies (recommended):

```powershell
pip install -U pip
pip install -r requirements.txt
# If you prefer Hatch/PyProject: use your build workflow (pyproject.toml)
```

3. Start the API server (development):

```powershell
uv run uvicorn src.fastapi_server:app --reload --port 5000
```

The backend listens on `http://localhost:5000` by default and exposes the
chat API used by the frontend.

Quickstart — Frontend (development)
1. Install and run the frontend:

```bash
cd my-chat-app
npm install
npm run dev
```

2. Open the app at `http://localhost:3000`. The frontend calls the backend at
	 `http://localhost:5000` (see `my-chat-app/app/lib/auth.ts` to change the base URL).

Useful commands
- Upload documents for RAG example:

```bash
python scripts/rag_doc_upload.py
```

- Lint Python with Ruff (assuming virtualenv active):

```powershell
.venv\Scripts\python.exe -m ruff check src
```

- Frontend build and lint:

```bash
cd my-chat-app
npm run lint
npm run build
```

Important files
- `src/fastapi_server.py` — backend entrypoint (routes for chat and auth).
- `src/agent.py` — agent orchestration and tool registration.
- `src/visualization_planner.py` — planner that emits visualization specs.
- `src/db.py`, `src/db_backend.py` — DB session and persistence layer.
- `my-chat-app/app/page.tsx` — main chat UI wiring to `@mui/x-chat`.
- `my-chat-app/app/components/ChartRenderer.tsx` — converts planner specs to
	ECharts options.

Development notes
- Visualization flow: the agent can append `VisualizationSpec` objects to a
	shared `AgentState`; the API response includes these specs and the frontend
	renders them below assistant messages using the `data-visualization` part.
- UI theming and tweaks live in `my-chat-app/app/theme.ts` and
	`my-chat-app/app/globals.css`.

Troubleshooting & tips
- If the frontend can't reach the backend, verify the backend is running and
	`API_BASE` in `my-chat-app/app/lib/auth.ts` points to the correct host/port.
- For database issues, review `src/db.py` and ensure your DB is reachable and
	migrations (if any) have been applied.

Extending the project
- Add new tools to the agent by registering them in `src/agent.py` and
	implementing the supporting logic in `src/`.
- To add chart types, extend `ChartRenderer.tsx` and the planner's output
	format in `src/visualization_planner.py`.

License
Add a `LICENSE` file if you plan to publish or redistribute this project.

---
If you'd like, I can now:
- add a minimal `requirements.txt` generated from the project dependencies,
- add a `Makefile` with common dev commands, or
- create a short troubleshooting checklist for common startup errors.
Tell me which you'd like next.
