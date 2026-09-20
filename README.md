# Document Intake Assistant

A conversational assistant that interviews a user through multi-turn chat,
extracts structured information with an LLM (with an offline rule-based
fallback), validates it, keeps a running structured state, handles
corrections/ambiguity, and renders a live "Personal Wishes Document" draft
preview.

## 1. Project Overview
The user chats with an AI assistant. Each message is passed to an
extraction layer that returns structured JSON, which is validated against
a Pydantic schema and merged into a single, explicit application state
(never inferred ad-hoc from raw chat history). The backend then asks
whatever question is still needed, and a live document preview is
regenerated from state on every turn.

## 2. Features
- Multi-turn conversational intake with follow-up questions for missing
  fields only (never re-asks something already captured).
- Structured, explicit state (Pydantic schema) as the single source of
  truth — not the chat transcript.
- Corrections: restating a field ("Actually, my full name is...") 
  overwrites the old value.
- Multi-field extraction in a single message (e.g. name + children in
  one sentence).
- Validation before state is ever touched; malformed/garbled LLM output
  is safely rejected without corrupting state or crashing.
- Works fully offline: if `OPENAI_API_KEY` is not set, a deterministic
  rule-based extractor is used automatically.
- Live document preview, clearly labelled as fictional / not legal advice.
- Automated tests (extraction, corrections, malformed input, API flow).

## 3. Architecture
```
User message
     v
Extraction layer (LLM if configured, else rule-based fallback)
     v
Raw JSON
     v
Pydantic validation (ExtractionResult)
     v
State merge (state.py)  <-- single in-memory WishesState
     v
Conversation logic decides next missing field / question
     v
Document generator renders draft from state
     v
Response { reply, state, document, is_complete } -> React UI
```
Key separation: the LLM **never** writes to state directly. It only
proposes structured JSON, which is validated first.

## 4. Tech Stack
- Backend: Python, FastAPI, Pydantic, pytest
- LLM: OpenAI API (`gpt-4o-mini`) with an offline regex-based fallback
- Frontend: React + Vite
- Tests: pytest + FastAPI TestClient

## 5. Folder Structure
```
document-intake-assistant/
├── backend/
│   ├── main.py          FastAPI app & routes
│   ├── models.py        Pydantic schema (WishesState, ExtractionResult)
│   ├── state.py          In-memory state store + merge logic
│   ├── conversation.py    Missing-field detection & next question
│   ├── llm.py            LLM extraction + offline fallback extractor
│   ├── document.py        Renders WishesState -> document text
│   ├── tests/
│   │   ├── test_state.py  Extraction / state / document unit tests
│   │   └── test_api.py    End-to-end API tests
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── frontend/
│   ├── src/
│   │   ├── App.jsx        Chat + state + document UI
│   │   ├── App.css
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── .gitignore
├── AI_LOG.md
└── README.md
```

## 6. Environment Variables
Copy `backend/.env.example` to `backend/.env`:
```
OPENAI_API_KEY=          # optional — leave blank to use the offline fallback extractor
```

## 7. Installation
```bash
git clone <your-repo-url>
cd document-intake-assistant

# Backend
cd backend
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Frontend
cd ../frontend
npm install
```

## 8. Running the Backend
```bash
cd backend
uvicorn main:app --reload
```
API: http://127.0.0.1:8000  |  Docs: http://127.0.0.1:8000/docs

## 9. Running the Frontend
```bash
cd frontend
npm run dev
```
Open http://localhost:5173

## 10. Running Tests
```bash
cd backend
pytest -q
```
Covers: normal extraction, multi-field extraction, corrections, "unknown"
input (no invented data), malformed/invalid extraction results, state
merge behaviour, document generation, and full API request/response flow.

## 11. LLM Design
`llm.extract_information()` sends the user's message plus the list of
still-missing fields to the model with a strict system prompt requesting
raw JSON only. The response is validated with Pydantic
(`ExtractionResult`) before ever touching `WishesState`. If no API key is
configured, or the API call fails for any reason, the same function
transparently falls back to `extract_information_fallback()`, a
deterministic regex-based extractor covering the same field set — so the
app is fully demoable and testable without network access or an API key.

## 12. Error Handling
- **LLM/API unavailable or errors** → caught in `_call_openai`, silently
  falls back to the rule-based extractor; user never sees a crash.
- **Malformed/invalid extraction JSON** → Pydantic validation fails →
  state is left untouched → user gets a safe "please rephrase" reply.
- **Missing API key** → app still runs correctly via the fallback
  extractor (documented behaviour, not a hard failure).
- **Network errors on the frontend** → caught and shown as a banner
  ("having trouble reaching the server"), chat remains usable.

## 13. AI Development Log
See `AI_LOG.md` for the prompts used, what was accepted from the AI's
suggestions, and what was changed/corrected and why.

## 14. Production Improvements (not implemented here, out of scope for
this timed test)
- Per-session state (session ID / auth) instead of a single global
  in-memory state, backed by a real database (e.g. Postgres or Redis).
- Streaming LLM responses to the frontend.
- Stronger ambiguity handling: ask the LLM to explicitly flag
  contradictions (e.g. two different names in the same conversation)
  rather than silently taking the latest value.
- Rate limiting / retries with backoff on the LLM call.
- Proper document export (PDF) rather than a plain-text preview.
- Authentication so multiple users can each have their own intake
  session concurrently.
- CI pipeline running `pytest` and a frontend lint/build on every push.
