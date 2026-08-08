# AI Interview Agent

A GPT-4o–powered technical interview agent for the TriCore 31-day AI engineering cohort.
It reads a candidate's mission history, dynamically selects curriculum topics to probe,
conducts a natural multi-turn conversation, and produces a structured feedback report.

---

## How it works

The agent exposes a single `POST /api/interview` endpoint.
Each request either **starts** a new interview session or **advances** an existing one.

```
POST /api/interview

Start  →  { sessionId, candidate: {...} }  →  { reply, done: false }
Turn   →  { sessionId, message: "..." }    →  { reply, done: false }
End    →  { sessionId, message: "..." }    →  { reply, done: true, feedback: {...} }
```

State is kept in memory, keyed by the `sessionId` you provide.
The session persists until the server restarts — it is your responsibility to send
the same `sessionId` on every turn.

### How the candidate's mission history is used

When you send a candidate object, the agent builds a **structured profile**:

| Profile field | How it is built | How it is used |
|---|---|---|
| `strong_topics` | Days passed in ≤ 2 attempts | Agent asks design-level, trade-off questions |
| `weak_topics` | Days failed or skipped | Agent probes these first (Tier-1 topic selection) |
| `skipped_days` / `failed_days` | Missions with `skipped: true` or `passed: false` | Guaranteed to be asked before any other topic |
| `job_role` | `member.jobRole` | Used for FAISS semantic matching when no weak days remain |
| `experience_level` | Derived from `yearsExperience` (< 3 → Junior, ≤ 5 → Mid-level, > 5 → Senior) | Calibrates question difficulty |

Topic selection priority (Tier 1 → 4):

1. **Skipped + failed days** — the agent always probes these first, giving the candidate a chance to redeem them
2. **Job-role semantic match** — FAISS finds the most relevant curriculum days for the candidate's role
3. **Strong topics** — deep architectural questions on areas the candidate aced
4. **Fallback** — any remaining uncovered curriculum day

The interview ends after **at least 8 questions** have been asked across **at least 4 distinct curriculum days**.

---

## Setup

### Prerequisites

- Python 3.10+
- An OpenAI API key with access to `gpt-4o` and `text-embedding-3-small`

### 1. Install dependencies

```bash
cd interview-agent
pip install -r requirements.txt
```

### 2. Configure the environment

```bash
cp .env.example .env
```

Open `.env` and set your key:

```
OPENAI_API_KEY=sk-...
```

### 3. Start the server

```bash
uvicorn app.main:app --reload
```

The server starts on `http://127.0.0.1:8000`.
On first boot, the FAISS curriculum index is loaded from `data/curriculum.faiss`.
If the index file is missing it will be rebuilt automatically (requires an OpenAI API call
to embed the 31-day curriculum — takes ~5 seconds).

Interactive API docs are available at `http://127.0.0.1:8000/docs`.

---

## API reference

### `POST /api/interview`

**Start a new interview**

```json
{
  "sessionId": "abc-123",
  "candidate": {
    "member": {
      "id": "CAND-003",
      "name": "Emily Chen",
      "jobRole": "AI Engineer",
      "yearsExperience": 6
    },
    "missions": [
      { "day": 7,  "title": "Embeddings Explained",          "passed": true, "attempts": 1 },
      { "day": 8,  "title": "Vector Databases Overview",     "passed": true, "attempts": 1 },
      { "day": 22, "title": "Multi-Agent Orchestration",     "passed": true, "attempts": 1 },
      { "day": 28, "title": "Docker & Kubernetes Deployment","skipped": true }
    ],
    "signals": { "commitDays": 31, "missionsCompleted": 28, "missionsFirstTry": 22 }
  }
}
```

Response:

```json
{ "reply": "Welcome, Emily! ...", "done": false }
```

**Send a message (conversation turn)**

```json
{ "sessionId": "abc-123", "message": "Embeddings map text into high-dimensional vectors..." }
```

Response:

```json
{ "reply": "That's a solid foundation — let's go a level deeper...", "done": false }
```

**Final response (when done)**

```json
{
  "reply": "Thank you — that wraps up our interview...",
  "done": true,
  "feedback": {
    "summary": "...",
    "strengths": ["...", "..."],
    "gaps":      ["...", "..."],
    "next":      ["...", "..."]
  }
}
```

### Error codes

| Status | Meaning |
|--------|---------|
| `400`  | Missing/conflicting fields, empty `sessionId` or `message`, `candidate` missing `member` key |
| `404`  | `sessionId` not found — send `candidate` first to start |
| `409`  | Session already exists with this `sessionId` |
| `410`  | Session is already completed |
| `422`  | Pydantic validation error (e.g. `sessionId` field missing entirely) |
| `500`  | Unexpected server error |

---

## Multi-turn curl walkthrough

The commands below run a full mini-interview against CAND-011 (Mia Alvarez),
who skipped Days 7, 8, 12, 16, and 22. Notice the agent probes those skipped topics first.

> **Windows users:** replace `'` with `"` and escape inner quotes, or use PowerShell's
> `Invoke-RestMethod` / a tool like Postman.

### Turn 0 — Start

```bash
curl -s -X POST http://127.0.0.1:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-mia-001",
    "candidate": {
      "member": {
        "id": "CAND-011",
        "name": "Mia Alvarez",
        "jobRole": "UX Researcher",
        "yearsExperience": 6
      },
      "missions": [
        { "day": 1,  "title": "VS Code & Python Setup",          "passed": true,  "attempts": 2 },
        { "day": 4,  "title": "Reading Structured Data",          "passed": true,  "attempts": 2 },
        { "day": 7,  "title": "Embeddings Explained",             "skipped": true },
        { "day": 8,  "title": "Vector Databases Overview",        "skipped": true },
        { "day": 12, "title": "Prompt Engineering Fundamentals",  "skipped": true },
        { "day": 16, "title": "Chatbot Backend & API Integration","skipped": true },
        { "day": 22, "title": "Multi-Agent Orchestration",        "skipped": true },
        { "day": 31, "title": "Capstone Project & Final Demo",    "passed": true,  "attempts": 4 }
      ],
      "signals": { "commitDays": 9, "missionsCompleted": 14, "missionsFirstTry": 5 }
    }
  }'
```

Expected response shape:
```json
{ "reply": "Hi Mia! ... embeddings ...", "done": false }
```

### Turn 1 — Answer the first question

```bash
curl -s -X POST http://127.0.0.1:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-mia-001",
    "message": "An embedding is a way to represent text as numbers so a computer can compare meaning, not just exact words."
  }'
```

### Turn 2 — Answer the follow-up (or next question)

```bash
curl -s -X POST http://127.0.0.1:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-mia-001",
    "message": "I think dense embeddings capture semantic meaning while sparse ones like BM25 focus on keyword frequency."
  }'
```

### Subsequent turns

Continue sending `{ "sessionId": "demo-mia-001", "message": "..." }` until `done: true`.
The response will include a `feedback` object when the interview is complete.

---

## Running the test suite

All 77 tests run offline — no OpenAI API key required.

```bash
cd interview-agent
python -m pytest tests/ -v
```

Expected output:

```
77 passed in ~4s
```

Individual test files and what they cover:

| File | Coverage |
|------|----------|
| `test_profile_parsing.py` | Candidate archetype parsing (strong / skipped / failed / mixed) |
| `test_select_next_day.py` | Topic selection tier priority and no-repeat invariants |
| `test_evaluator.py` | Min-length guard, derived properties, all 6 `decide_next_action` branches |
| `test_should_end.py` | Ending gate (≥ 8 questions AND ≥ 4 days, duplicate dedup) |
| `test_feedback_schema.py` | Feedback schema compliance and graceful fallback |
| `test_api_validation.py` | HTTP 400 / 404 / 409 / 410 / 422 / 200 + response shapes |

---

## Project structure

```
interview-agent/
├── app/
│   ├── main.py               # FastAPI app + POST /api/interview endpoint
│   ├── schemas.py            # Pydantic models (InterviewRequest, InterviewResponse, Feedback, SessionState)
│   ├── config.py             # Environment config and file paths
│   ├── session_store.py      # In-memory session store
│   └── services/
│       ├── data_manager.py       # FAISS index lifecycle + candidate profile builder
│       ├── dialogue_manager.py   # Interview orchestration (start, process, end)
│       ├── evaluator.py          # GPT-4o answer evaluation + next-action decision
│       ├── feedback_generator.py # Final structured feedback generation
│       └── question_generator.py # Calibrated question + follow-up generation
├── data/
│   ├── candidates.json       # 20 sample candidate records
│   ├── curriculum.json       # 31-day AI engineering curriculum
│   ├── curriculum.faiss      # Pre-built FAISS index (rebuilt automatically if missing)
│   └── metadata.json         # FAISS index metadata
├── scripts/
│   └── full_demo.py          # End-to-end CLI demo (no server required)
├── tests/                    # 77 offline unit tests
├── .env.example
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Running the demo script

The demo script drives a complete interview directly against the dialogue manager,
without needing a running server. Requires a valid `OPENAI_API_KEY` in `.env`.

```bash
cd interview-agent
python scripts/full_demo.py           # uses CAND-003 (Emily Chen — all first-try)
python scripts/full_demo.py CAND-011  # Mia Alvarez — many skipped topics
python scripts/full_demo.py CAND-010  # Gerald Combs — failed missions
python scripts/full_demo.py CAND-016  # Isabella Rossi — mixed failed + skipped
```
