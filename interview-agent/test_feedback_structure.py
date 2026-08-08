"""
test_feedback_structure.py
==========================
Runs a complete interview and validates the final response against the
technical-spec.md contract:

  {
    "reply":    "Interview completed.",
    "done":     true,
    "feedback": {
      "summary":   "...",
      "strengths": [...],
      "gaps":      [...],
      "next":      [...]
    }
  }

Also checks that feedback is specific (not generic filler).
"""
import urllib.request
import json
import sys

URL = "http://localhost:8000/api/interview"
SESSION_ID = "feedback-structure-test-v1"

CANDIDATE = {
    "member": {
        "id": "CAND-001", "name": "Sarah Johnson",
        "jobRole": "Senior Data Engineer", "yearsExperience": 9,
        "education": "MS Computer Science", "status": "COMPLETED",
    },
    "missions": [
        {"day": 7,  "title": "Embeddings Explained",           "passed": True, "attempts": 1},
        {"day": 8,  "title": "Vector Databases Overview",       "passed": True, "attempts": 1},
        {"day": 10, "title": "Retrieval & Matching Engine",      "passed": True, "attempts": 2},
        {"day": 12, "title": "Prompt Engineering Fundamentals",  "passed": True, "attempts": 4},
        {"day": 16, "title": "Chatbot Backend & API Integration","passed": True, "attempts": 1},
        {"day": 22, "title": "Multi-Agent Orchestration",        "passed": True, "attempts": 2},
        {"day": 23, "title": "Model Context Protocol (MCP)",     "passed": True, "attempts": 2},
        {"day": 28, "title": "Docker & Kubernetes Deployment",   "passed": True, "attempts": 3},
        {"day": 29, "title": "Monitoring, Logging & Observability","skipped": True},
        {"day": 31, "title": "Capstone Project & Final Demo",    "passed": True, "attempts": 1},
    ],
    "signals": {"commitDays": 28, "missionsCompleted": 30, "missionsFirstTry": 20},
}

# Varied-quality answers to ensure we get real Q&A records for feedback
ANSWERS = [
    # Solid answer
    "I use Python's structured logging module with JSON output. Each log entry carries "
    "a correlation ID, service name, log level, and timestamp. We ship logs to a central "
    "aggregator — typically Loki or Elasticsearch — and build Grafana dashboards on top. "
    "For metrics, Prometheus scrapes the /metrics endpoint and we alert on p99 latency "
    "and error rate thresholds.",

    # Vague — will trigger follow-up
    "Embeddings are vectors that represent meaning.",

    # Follow-up answer — more detail
    "Specifically, a sentence embedding maps the entire sequence to a fixed-length vector "
    "in a high-dimensional space where semantically similar sentences are closer together. "
    "We use cosine similarity to find nearest neighbours — dot product after L2 normalisation. "
    "In practice I use sentence-transformers with FAISS for the index.",

    # Solid answer
    "HNSW builds a hierarchical graph of approximate nearest neighbours. At query time it "
    "traverses from the top level down to progressively denser layers, giving sub-linear "
    "search with high recall. The trade-off vs IVF-PQ is memory: HNSW keeps edges for each "
    "vector. For under 10M vectors where memory isn't a constraint, HNSW is my default.",

    # Average answer
    "Prompt engineering is writing good instructions for the LLM. You can use few-shot "
    "examples to show the format you want, or chain-of-thought to make the model reason step by step.",

    # Solid answer
    "MCP decouples the LLM client from tool implementations. Instead of hardcoding function "
    "schemas per provider, you define tools as MCP servers and any compatible client can "
    "discover and call them. The protocol handles capability negotiation, so adding a new "
    "tool doesn't require changing the client code.",

    # Solid answer
    "For Docker, each service gets its own image so it runs identically in dev, staging, "
    "and prod. Kubernetes adds orchestration: it handles rolling deploys, self-heals crashed "
    "pods, and scales replicas based on HPA metrics. For LLM services I set HPA on custom "
    "metrics like queue depth rather than CPU, since inference is GPU-bound.",

    # Solid answer
    "Multi-agent orchestration splits complex tasks across specialised agents. A router "
    "determines which agent handles a subtask, and shared state is passed between them. "
    "LangGraph gives you explicit state machines with typed edges, which makes debugging "
    "coordination failures much easier than CrewAI's implicit execution flow.",
]


def post(payload: dict) -> tuple:
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


def validate_structure(resp: dict) -> list:
    """Return list of structural violations."""
    errors = []

    # Top-level fields
    if resp.get("reply") != "Interview completed.":
        errors.append(f"reply must be exactly 'Interview completed.' got: '{resp.get('reply')}'")
    if resp.get("done") is not True:
        errors.append(f"done must be true, got: {resp.get('done')}")

    fb = resp.get("feedback")
    if not isinstance(fb, dict):
        errors.append(f"feedback must be an object, got: {type(fb)}")
        return errors

    for field in ("summary", "strengths", "gaps", "next"):
        if field not in fb:
            errors.append(f"feedback.{field} is missing")

    if not isinstance(fb.get("summary"), str) or not fb.get("summary"):
        errors.append("feedback.summary must be a non-empty string")

    for arr_field in ("strengths", "gaps", "next"):
        arr = fb.get(arr_field, [])
        if not isinstance(arr, list):
            errors.append(f"feedback.{arr_field} must be an array")
        elif len(arr) == 0:
            errors.append(f"feedback.{arr_field} must not be empty")

    return errors


def validate_specificity(fb: dict) -> list:
    """Return list of specificity warnings (not hard failures)."""
    warnings = []
    generic_phrases = [
        "overall a good candidate", "great potential", "strong background",
        "completed the interview", "good communication", "general understanding",
    ]
    all_text = " ".join([
        fb.get("summary", ""),
        *fb.get("strengths", []),
        *fb.get("gaps", []),
        *fb.get("next", []),
    ]).lower()

    for phrase in generic_phrases:
        if phrase in all_text:
            warnings.append(f"contains generic filler: '{phrase}'")

    return warnings


def main():
    print("=" * 65)
    print("  FEEDBACK STRUCTURE TEST")
    print("  Candidate: Sarah Johnson (CAND-001, Senior Data Engineer)")
    print("=" * 65)

    # ── Start ──────────────────────────────────────────────────────────────
    s, r = post({"sessionId": SESSION_ID, "candidate": CANDIDATE})
    assert s == 200, f"Start failed: {s} {r}"
    print(f"\nQ1: {r['reply'][:120]}...")

    final_resp = None
    answer_idx = 0
    turn = 1
    MAX_TURNS = 30

    while not r.get("done") and turn < MAX_TURNS:
        answer = ANSWERS[answer_idx % len(ANSWERS)]
        answer_idx += 1
        turn += 1
        s, r = post({"sessionId": SESSION_ID, "message": answer})
        assert s == 200, f"Turn {turn} failed: {s} {r}"
        if not r.get("done"):
            print(f"Q{turn}: {r['reply'][:120]}...")
        else:
            final_resp = r
            break

    assert final_resp is not None, "Interview never ended within MAX_TURNS"

    # ── Validate structure ─────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  FINAL RESPONSE")
    print("=" * 65)
    print(json.dumps(final_resp, indent=2))

    print("\n" + "=" * 65)
    print("  STRUCTURE VALIDATION")
    print("=" * 65)

    struct_errors = validate_structure(final_resp)
    if struct_errors:
        for e in struct_errors:
            print(f"  FAIL: {e}")
        sys.exit(1)
    else:
        print("  PASS: reply == 'Interview completed.'")
        print("  PASS: done == true")
        print("  PASS: feedback.summary is present")
        print(f"  PASS: feedback.strengths has {len(final_resp['feedback']['strengths'])} items")
        print(f"  PASS: feedback.gaps has {len(final_resp['feedback']['gaps'])} items")
        print(f"  PASS: feedback.next has {len(final_resp['feedback']['next'])} items")

    print("\n" + "=" * 65)
    print("  SPECIFICITY CHECK")
    print("=" * 65)
    warnings = validate_specificity(final_resp["feedback"])
    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")
    else:
        print("  PASS: No generic filler detected")

    print("\n" + "=" * 65)
    print("  ALL CHECKS PASSED")
    print("=" * 65)


if __name__ == "__main__":
    main()
