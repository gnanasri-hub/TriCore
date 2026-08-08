"""
test_full_interview.py
======================
Runs a complete interview end-to-end and verifies the hard minimums:
  - >= 8 questions asked
  - >= 4 distinct curriculum days covered

Prints a turn-by-turn trace plus final counts.
"""
import urllib.request
import json

URL = "http://localhost:8000/api/interview"
SESSION_ID = "full-interview-test-002"

CANDIDATE = {
    "member": {
        "id": "CAND-001",
        "name": "Sarah Johnson",
        "jobRole": "Senior Data Engineer",
        "yearsExperience": 9,
        "education": "MS Computer Science",
        "status": "COMPLETED",
    },
    "missions": [
        {"day": 7,  "title": "Embeddings Explained",              "passed": True,  "attempts": 1},
        {"day": 8,  "title": "Vector Databases Overview",          "passed": True,  "attempts": 1},
        {"day": 10, "title": "Retrieval and Matching Engine",       "passed": True,  "attempts": 2},
        {"day": 12, "title": "Prompt Engineering Fundamentals",     "passed": True,  "attempts": 4},
        {"day": 16, "title": "Chatbot Backend API Integration",     "passed": True,  "attempts": 1},
        {"day": 22, "title": "Multi-Agent Orchestration",           "passed": True,  "attempts": 2},
        {"day": 23, "title": "Model Context Protocol MCP",          "passed": True,  "attempts": 2},
        {"day": 28, "title": "Docker and Kubernetes Deployment",    "passed": True,  "attempts": 3},
        {"day": 29, "title": "Monitoring Logging Observability",    "skipped": True},
        {"day": 31, "title": "Capstone Project Final Demo",         "passed": True,  "attempts": 1},
    ],
    "signals": {"commitDays": 28, "missionsCompleted": 30, "missionsFirstTry": 20},
}

# Realistic answers — varied quality so we hit both follow-up and new-question paths
ANSWERS = [
    # Substantive — should move to next topic
    "I use Python's logging module with structured JSON output. Each service emits logs "
    "with a correlation ID so we can trace a request across microservices in Grafana. "
    "Prometheus scrapes metrics endpoints and we set up alerts on p99 latency and error rate.",

    # Somewhat vague — may trigger a follow-up
    "Embeddings capture the meaning of text as numbers.",

    # Follow-up answer — more detail
    "Specifically, a sentence embedding maps the whole sentence to a fixed-length vector "
    "in a high-dimensional space, where semantically similar sentences cluster together. "
    "We use cosine similarity to find nearest neighbours in that space.",

    # Solid answer
    "HNSW gives sub-linear search time with high recall by building a hierarchical graph. "
    "The trade-off is memory — each vector keeps edges to its neighbours. For a million "
    "vectors I'd choose HNSW over IVF-PQ when recall matters more than memory budget.",

    # Vague — triggers follow-up
    "RAG retrieves relevant documents and feeds them to the LLM.",

    # Follow-up answer
    "The retrieval step embeds the query, searches the FAISS index for top-k chunks, "
    "then we prepend those chunks to the prompt. The LLM answers grounded in the retrieved "
    "context rather than parametric knowledge, which cuts hallucinations significantly.",

    # Solid answer
    "Prompt engineering involves crafting the system and user messages to steer the model. "
    "Few-shot examples help with structured output tasks. Chain-of-thought prompting improves "
    "reasoning accuracy by asking the model to show its work step by step.",

    # Solid answer
    "Multi-agent orchestration lets you decompose a complex task into specialised agents. "
    "A router decides which agent handles each subtask. CrewAI and LangGraph both support "
    "this — LangGraph gives you explicit state machines while CrewAI is more declarative.",

    # Solid answer for safety net
    "Docker packages the app with all its dependencies into an image so it runs identically "
    "everywhere. Kubernetes then manages scaling, self-healing, and rolling updates across "
    "a cluster of those containers.",

    # Solid answer for safety net
    "Function calling lets the LLM emit a structured JSON tool invocation instead of plain "
    "text. The host application parses the call, executes the real function, and returns the "
    "result back to the model for the final answer.",
]


def post(payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        URL, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main():
    print("=" * 65)
    print("FULL INTERVIEW TEST — minimum 8 questions, 4 curriculum days")
    print("=" * 65)

    # ── Start ──────────────────────────────────────────────────────────────
    status, resp = post({"sessionId": SESSION_ID, "candidate": CANDIDATE})
    assert status == 200, f"Start failed: {status} {resp}"

    turn = 1
    question_count = 1          # opening question counts
    covered_days = []           # track from server state embedded in turns

    print(f"\nTURN {turn:02d} [Q{question_count}] ASSISTANT:")
    print(f"  {resp['reply']}")
    assert resp["done"] is False

    answer_idx = 0
    MAX_TURNS = 40   # safety cap — prevents infinite loop if logic is broken

    # ── Conversation loop ──────────────────────────────────────────────────
    while not resp.get("done", False) and turn < MAX_TURNS:
        answer = ANSWERS[answer_idx % len(ANSWERS)]
        answer_idx += 1
        turn += 1

        status, resp = post({"sessionId": SESSION_ID, "message": answer})
        assert status == 200, f"Turn {turn} failed: {status} {resp}"

        if not resp.get("done"):
            question_count += 1
            print(f"\nTURN {turn:02d} [Q{question_count}] ASSISTANT:")
        else:
            print(f"\nTURN {turn:02d} [FINAL] ASSISTANT:")

        print(f"  {resp['reply']}")

        if resp.get("done"):
            break

    # ── Results ────────────────────────────────────────────────────────────
    assert resp.get("done") is True, "Interview never ended!"
    fb = resp.get("feedback")
    assert fb is not None, "done=true but feedback is missing!"

    # Fetch exact server-side counts via the status endpoint
    status_req = urllib.request.Request(
        f"http://localhost:8000/api/interview/status?sessionId={SESSION_ID}",
        method="GET",
    )
    with urllib.request.urlopen(status_req) as r:
        status_data = json.loads(r.read())

    actual_q_count   = status_data["question_count"]
    actual_days      = status_data["covered_days"]
    actual_day_count = len(actual_days)

    print("\n" + "=" * 65)
    print("RESULTS")
    print("=" * 65)
    print(f"  Total questions asked : {actual_q_count}")
    print(f"  Distinct days covered : {actual_day_count}  → {actual_days}")
    print(f"  Feedback summary      : {fb['summary'][:120]}...")
    print()

    passed = True
    if actual_q_count < 8:
        print(f"  FAIL: expected >= 8 questions, got {actual_q_count}")
        passed = False
    else:
        print(f"  PASS: >= 8 questions  ({actual_q_count})")

    if actual_day_count < 4:
        print(f"  FAIL: expected >= 4 days covered, got {actual_day_count}")
        passed = False
    else:
        print(f"  PASS: >= 4 days covered ({actual_day_count})")

    print()
    if passed:
        print("ALL MINIMUM REQUIREMENTS MET")
    else:
        print("MINIMUM REQUIREMENTS NOT MET — fix required")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
