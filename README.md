# AI-First CRM — HCP Module: Log Interaction Screen

A working reference implementation of the Log Interaction screen: React + Redux
frontend, FastAPI backend, and a LangGraph agent (Groq `gemma2-9b-it` /
`llama-3.3-70b-versatile`) powering the conversational logging path.

## Structure

```
hcp-crm/
  backend/
    app/
      main.py            # FastAPI app entrypoint
      config.py           # env-driven settings
      database.py          # SQLAlchemy engine/session
      models.py            # ORM models (HCP, Interaction, FollowUpTask, etc.)
      schemas.py            # Pydantic request/response schemas
      agent/
        llm.py               # Groq LLM wrappers (fast + reasoning model)
        state.py              # LangGraph AgentState
        tools.py               # The 5(+1) tools: log, edit, fetch_history,
                                # schedule_follow_up, compliance_check, next_best_action
        graph.py                # LangGraph StateGraph wiring router -> tools
      routers/
        interactions.py    # REST CRUD for the structured-form path
        hcp.py               # HCP search / history / next-best-action
        chat.py               # Chat endpoint wired to the LangGraph agent
    requirements.txt
    seed.py               # populates demo reps/HCPs/products
    .env.example
  frontend/
    src/
      store/              # Redux Toolkit slices (interaction, chat)
      api/client.js        # axios API client
      components/
        LogInteractionScreen.jsx  # form/chat mode toggle
        StructuredForm.jsx
        ChatInterface.jsx
    package.json
```

## Running the backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY and DATABASE_URL
python seed.py          # optional demo data
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`, docs at `/docs`.

## Running the frontend

```bash
cd frontend
npm install
echo "REACT_APP_API_BASE_URL=http://localhost:8000" > .env
npm start
```

App available at `http://localhost:3000`.

## Notes on the AI agent design

- **Two entry points, one backend**: both the structured form and the chat
  interface ultimately call the same tools (`log_interaction_tool`,
  `edit_interaction_tool`), so records are consistent regardless of how they
  were captured.
- **Human-in-the-loop**: nothing from a chat message is written to the
  database until the rep explicitly confirms — the agent always returns a
  preview/diff first (`/api/chat/message` → `/api/chat/confirm`).
- **Model split**: `gemma2-9b-it` handles low-latency routing/extraction;
  `llama-3.3-70b-versatile` is reserved for compliance screening and
  next-best-action suggestions where a bit more reasoning depth is worth the
  extra latency.
- **Audit trail**: every edit snapshots the prior state into
  `interaction_history` before mutating, and the original raw chat/form input
  is retained on the interaction record.

This is a reference implementation intended to demonstrate architecture and
working code paths end-to-end; before production use you'd want: real auth,
Alembic migrations instead of `create_all`, a persistent (Postgres) LangGraph
checkpointer instead of `MemorySaver`, and more robust HCP name resolution
(fuzzy matching / dedup) than the simple `ILIKE` lookup used here.
