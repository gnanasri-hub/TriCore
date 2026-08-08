# AI Interview Agent

A Groq-powered (llama-3.3-70b-versatile) technical interview agent for the TriCore
31-day AI engineering cohort. It reads a candidate's mission history, dynamically
selects curriculum topics to probe, conducts a natural multi-turn conversation, and
produces a structured feedback report.

---

## How it works

The agent exposes a single `POST /api/interview` endpoint.
Each request either **starts** a new interview session or **advances** an existing one.

```
POST /api/interview

Start  →  { sessionId, candidate: {...} }  →  { reply, done: false }
Turn   →  { sessionId, message: "..." }    →  { reply, done: false }
End    →  { sessionId, message: "..." }    →  { reply: "Interview completed.", done: true, feedback: {...} }
```

State is kept in memory, keyed by the `sessionId` you provide.
The session persists until the server restarts.

### How the candidate's mission history is used

When you send a candidate object, the agent builds a **structured profile**:

| Profile field | How it is built | How it is used |
|---|---|---|
| `strong_topics` | Days passed in ≤ 2 attempts | Agent asks design-level, trade-off questions |
| `weak_topics` | Days failed or skipped | Agent probes these first (Tier-1 topic selection) |
| `skipped_days` / `failed_days` | Missions with `skipped: true` or `passed: false` | Guaranteed to be asked before any other topic |
| `job_role` | `member.jobRole` | Used for FAISS semantic matching when no weak days remain |
| `experience_level` | Derived from `yearsExperience` (< 3 → Junior, ≤ 5 → Mid-level, > 5 → Senior) | Calibrates question difficulty |
| `attempts_by_day` | Per-day attempt count | Exact depth calibration in LLM prompt |

Topic selection priority (Tier 1 → 4):

1. **Skipped + failed days** — always probed first; foundational questions, encouraging tone
2. **Job-role semantic match** — FAISS finds the most relevant curriculum days for the candidate's role
3. **Strong topics** — deep architectural questions on areas the candidate aced (≤ 2 attempts)
4. **Fallback** — any remaining uncovered curriculum day

The interview ends after **at least 8 questions** across **at least 4 distinct curriculum days**.

### Intelligent follow-up logic

After each answer the evaluator classifies it and decides the next action:

| Answer quality | Action | What happens |
|---|---|---|
| Vague / too short / incomplete | `follow_up_clarify` | Probe for concrete example, tool, or step |
| Strong but shallow (depth < 8) | `follow_up_escalate` | Push to production edge case or trade-off |
| Strong and deep (depth ≥ 8) | `new_question` | Move to next curriculum topic |
| Average | `new_question` | Move on |
| Already on a follow-up | `new_question` | Hard cap — follow-ups never chain |

---

## Setup

### Prerequisites

- Python 3.10+
- A **Groq API key** (free tier available at [console.groq.com](https://console.groq.com))
- An **OpenAI API key** — used only for FAISS embedding generation at startup
  (the pre-built index in `data/curriculum.faiss` means this is rarely needed)

### 1. Install dependencies

```bash
cd interview-agent
pip install -r requirements.txt
```

### 2. Configure the environment

```bash
cp .env.example .env
```

Open `.env` and set both keys:

```
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...    # only needed if curriculum.faiss is missing
```

### 3. Start the server

```bash
cd interview-agent
uvicorn app.main:app --reload
```

The server starts on `http://127.0.0.1:8000`.
On first boot the FAISS curriculum index loads from `data/curriculum.faiss` (pre-built).
Interactive API docs: `http://127.0.0.1:8000/docs`.

---

## How to Demo

Run the full end-to-end HTTP demo against a live server:

```bash
# 1. Start the server in one terminal
cd interview-agent
uvicorn app.main:app --reload

# 2. In a second terminal, run the demo script
cd interview-agent
python scripts/full_interview_demo.py
```

The demo script (`scripts/full_interview_demo.py`):
- Loads **CAND-001** (Sarah Johnson, Senior Data Engineer)
- Starts the interview via `POST /api/interview`
- Simulates **8–10 turns** with a mix of strong, vague, and follow-up answers
- Prints **every request and response** with clear labels and colour
- Runs until `done=true` and prints the full `feedback` object
- Ends with a **proof summary** confirming all Problem Statement requirements

Example output (abbreviated):

```
══════════════════════════════════════════════════════════════════════
  AI Interview Agent — Full End-to-End HTTP Demo
══════════════════════════════════════════════════════════════════════

  Candidate : Sarah Johnson (CAND-001)
  Role      : Senior Data Engineer  |  9 years experience

  ▶ REQUEST [START]
  ...
  ◀ RESPONSE [done=false]  HTTP 200
  reply: "Welcome to the interview, Sarah..."

  ▶ REQUEST [TURN 1]
  message: "I'm not sure, I think it has something to do with logging."
  ◀ RESPONSE [done=false]  HTTP 200
  reply: "That's a start — could you walk me through..."
  [state] follow_up_pending=True (type=clarify)

  ...

  ◀ RESPONSE [FINAL — done=true]  HTTP 200
  reply: "Interview completed."

  ╔══ FEEDBACK OBJECT ══════════════════════════════════╗
  summary: Sarah Johnson demonstrated strong command of ...
  strengths: ✔ Articulated the FAISS IVF-PQ trade-offs...
  gaps:      ✘ Did not demonstrate understanding of ...
  next:      → Implement a monitoring pipeline using ...
  ╚═════════════════════════════════════════════════════╝

══════════════════════════════════════════════════════════════════════
  PROOF SUMMARY — Problem Statement Requirements
══════════════════════════════════════════════════════════════════════
  ✔  Single endpoint POST /api/interview
  ✔  reply == "Interview completed."
  ✔  done = true
  ✔  Total questions >= 8
  ✔  Distinct curriculum days >= 4
  ✔  Follow-up(s) triggered
  ✔  feedback has all 4 required fields
  ✔  feedback arrays are non-empty and specific
  ✔  State maintained by sessionId (in-memory)

  ALL REQUIREMENTS SATISFIED ✓
```

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

**Final response (when interview is complete)**

```json
{
  "reply": "Interview completed.",
  "done": true,
  "feedback": {
    "summary": "...",
    "strengths": ["...", "..."],
    "gaps":      ["...", "..."],
    "next":      ["...", "..."]
  }
}
```

### `GET /api/interview/status?sessionId=...`

Returns session counters for debugging:

```json
{
  "sessionId": "abc-123",
  "question_count": 8,
  "covered_days": [7, 8, 12, 29],
  "interview_stage": "COMPLETED",
  "pending_follow_up": { "is_pending": false, ... }
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

## Running the test suite

All 77 tests run offline — no API key required.

```bash
cd interview-agent
python -m pytest tests/ -v
```

Expected output: `77 passed`

| File | Coverage |
|------|----------|
| `test_profile_parsing.py` | Candidate profile parsing (strong / skipped / failed / mixed) |
| `test_select_next_day.py` | Topic selection tier priority and no-repeat invariants |
| `test_evaluator.py` | Min-length guard, derived properties, all `decide_next_action` branches |
| `test_should_end.py` | Ending gate (≥ 8 questions AND ≥ 4 days) |
| `test_feedback_schema.py` | Feedback schema compliance and graceful fallback |
| `test_api_validation.py` | HTTP 400 / 404 / 409 / 410 / 422 / 200 + response shapes |

---

## Verification scripts

These scripts require a running server and a valid `GROQ_API_KEY`:

| Script | What it verifies |
|--------|-----------------|
| `python verify_tests.py` | Basic API contract (single endpoint, start, turn, state isolation) |
| `python test_full_interview.py` | Full interview: ≥ 8 questions, ≥ 4 days, `done=true` |
| `python test_personalization.py` | CAND-003/010/011 get depth-appropriate questions |
| `python test_follow_up_logic.py` | Vague → clarify, strong → escalate, hard cap enforced |
| `python test_feedback_structure.py` | `reply="Interview completed."`, feedback specificity |
| `python scripts/full_interview_demo.py` | Full end-to-end HTTP demo with proof summary |

---

## Project structure

```
interview-agent/
├── app/
│   ├── main.py               # FastAPI app — POST /api/interview + GET /api/interview/status
│   ├── schemas.py            # Pydantic models (InterviewRequest, InterviewResponse, Feedback, SessionState)
│   ├── config.py             # Environment config, file paths, GROQ_MODEL
│   ├── session_store.py      # In-memory session store (dict keyed by sessionId)
│   └── services/
│       ├── data_manager.py       # FAISS index lifecycle, candidate profile builder, Groq/OpenAI clients
│       ├── dialogue_manager.py   # Interview orchestration (start, process, end, should_end)
│       ├── evaluator.py          # Answer evaluation + follow-up decision (clarify/escalate/new_question)
│       ├── feedback_generator.py # Final structured feedback with validation + retry
│       └── question_generator.py # Depth-calibrated question and follow-up generation
├── data/
│   ├── candidates.json       # 20 sample candidate records
│   ├── curriculum.json       # 31-day AI engineering curriculum
│   ├── curriculum.faiss      # Pre-built FAISS index
│   └── metadata.json         # FAISS index metadata
├── scripts/
│   ├── full_demo.py              # Direct (no-server) demo via dialogue_manager
│   └── full_interview_demo.py    # HTTP end-to-end demo with proof summary
├── tests/                    # 77 offline unit tests
├── verify_tests.py           # Basic API contract checks
├── test_full_interview.py    # Minimum requirements test
├── test_personalization.py   # Depth calibration per candidate archetype
├── test_follow_up_logic.py   # Follow-up logic (clarify / escalate / hard cap)
├── test_feedback_structure.py# Spec-compliant feedback structure and specificity
├── .env.example
├── pytest.ini
├── requirements.txt
└── README.md
```
