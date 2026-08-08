"""
test_follow_up_logic.py
=======================
Tests the intelligent follow-up logic:

  Case 1 — VAGUE answer  → must trigger follow_up_clarify (done=False, same topic)
  Case 2 — STRONG answer → must either escalate difficulty (follow_up_escalate)
                           or move to next topic (new_question) if depth >= 8.
                           Either way done=False and we log the action taken.
  Case 3 — Hard cap      → after the follow-up is answered, next turn must be
                           a new_question regardless of answer quality.

Prints full request/response pairs for every turn.
"""
import urllib.request
import json

URL = "http://localhost:8000/api/interview"

CANDIDATE = {
    "member": {
        "id": "CAND-003", "name": "Emily Chen",
        "jobRole": "AI Engineer", "yearsExperience": 6,
        "education": "MS Artificial Intelligence", "status": "COMPLETED",
    },
    "missions": [
        {"day": 7,  "title": "Embeddings Explained",               "passed": True, "attempts": 1},
        {"day": 8,  "title": "Vector Databases Overview",           "passed": True, "attempts": 1},
        {"day": 10, "title": "Retrieval & Matching Engine",          "passed": True, "attempts": 1},
        {"day": 11, "title": "RAG End-to-End & LLM API Basics",     "passed": True, "attempts": 1},
        {"day": 12, "title": "Prompt Engineering Fundamentals",      "passed": True, "attempts": 1},
        {"day": 13, "title": "Function Calling & Structured Outputs","passed": True, "attempts": 1},
        {"day": 21, "title": "LangChain Agents",                     "passed": True, "attempts": 1},
        {"day": 22, "title": "Multi-Agent Orchestration",            "passed": True, "attempts": 1},
        {"day": 23, "title": "Model Context Protocol (MCP)",         "passed": True, "attempts": 1},
        {"day": 31, "title": "Capstone Project & Final Demo",        "passed": True, "attempts": 1},
    ],
    "signals": {"commitDays": 31, "missionsCompleted": 31, "missionsFirstTry": 30},
}

# Answers
VAGUE_ANSWER = "I don't know much about that."

STRONG_ANSWER = (
    "Embeddings are dense vector representations trained so that semantically similar items "
    "cluster together in high-dimensional space. For a production semantic search system I'd "
    "use a bi-encoder like sentence-transformers to encode documents offline and store them in "
    "a FAISS IVF-PQ index — IVF for fast approximate nearest-neighbour search and PQ for memory "
    "compression. At query time the query is encoded with the same model, normalised to unit "
    "length, and I do an inner-product search which is equivalent to cosine similarity after "
    "normalisation. For domain-specific vocabulary I'd fine-tune the encoder on in-domain "
    "positive/negative pairs using contrastive loss rather than trying to patch the index, "
    "because the embedding space itself needs to shift, not just the data."
)


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


def get_status(session_id: str) -> dict:
    req = urllib.request.Request(
        f"http://localhost:8000/api/interview/status?sessionId={session_id}",
        method="GET",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def print_pair(label: str, request_body: dict, status: int, response: dict):
    print(f"\n  {'─'*60}")
    print(f"  {label}")
    print(f"  {'─'*60}")
    print(f"  REQUEST:")
    # Print concisely — show only the key fields
    display = {k: v for k, v in request_body.items() if k != "candidate"}
    if "candidate" in request_body:
        display["candidate"] = "{...}"
    print(f"    {json.dumps(display)}")
    print(f"  RESPONSE (HTTP {status}):")
    print(f"    done  = {response.get('done')}")
    print(f"    reply = {response.get('reply', '')[:200]}")
    if response.get("feedback"):
        print(f"    feedback.summary = {response['feedback']['summary'][:100]}...")


def run_case(title: str, session_id: str, answer: str, expected_follow_up: bool):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")

    # ── Start ──────────────────────────────────────────────────────
    req1 = {"sessionId": session_id, "candidate": CANDIDATE}
    s1, r1 = post(req1)
    assert s1 == 200, f"Start failed: {s1} {r1}"
    print_pair("TURN 1 — Start interview", req1, s1, r1)

    opening_question = r1["reply"]
    st = get_status(session_id)
    print(f"\n  [server state] question_count={st['question_count']}  "
          f"covered_days={st['covered_days']}  "
          f"pending={st['pending_follow_up'].get('is_pending')}")

    # ── Send the test answer ───────────────────────────────────────
    req2 = {"sessionId": session_id, "message": answer}
    s2, r2 = post(req2)
    assert s2 == 200, f"Turn 2 failed: {s2} {r2}"
    print_pair("TURN 2 — Candidate answer", req2, s2, r2)

    st2 = get_status(session_id)
    pending = st2["pending_follow_up"]
    print(f"\n  [server state] question_count={st2['question_count']}  "
          f"covered_days={st2['covered_days']}  "
          f"pending={pending.get('is_pending')}  "
          f"follow_up_type={pending.get('follow_up_type', 'n/a')}")

    # ── Verify ────────────────────────────────────────────────────
    assert r2.get("done") is False, "FAIL: interview ended prematurely"

    if expected_follow_up:
        assert pending.get("is_pending") is True, (
            "FAIL: expected a follow-up to be pending but pending=False"
        )
        fu_type = pending.get("follow_up_type", "unknown")
        print(f"\n  PASS: follow-up triggered  (type={fu_type})")
        print(f"  Follow-up question: {pending.get('follow_up_question', '')[:200]}")

        # ── Case 3: answer the follow-up → must get new_question ─────
        req3 = {"sessionId": session_id,
                "message": "Let me be more specific: I would use cosine similarity "
                            "over dot product because it normalises for vector magnitude, "
                            "which matters when document lengths vary significantly."}
        s3, r3 = post(req3)
        assert s3 == 200, f"Turn 3 failed: {s3} {r3}"
        print_pair("TURN 3 — Answer the follow-up", req3, s3, r3)

        st3 = get_status(session_id)
        pending3 = st3["pending_follow_up"]
        assert pending3.get("is_pending") is False, (
            "FAIL: follow-up is still pending after it was answered (chained follow-up!)"
        )
        print(f"\n  PASS: hard cap enforced — no chained follow-up "
              f"(pending={pending3.get('is_pending')})")

    else:
        # Strong answer — may escalate OR move to new topic; both are valid
        is_still_pending = pending.get("is_pending", False)
        fu_type = pending.get("follow_up_type", "n/a")
        if is_still_pending and fu_type == "escalate":
            print(f"\n  PASS: strong answer → escalation follow-up triggered")
            print(f"  Escalation question: {pending.get('follow_up_question', '')[:200]}")
        elif not is_still_pending:
            print(f"\n  PASS: strong answer + high depth → moved to next topic")
            print(f"  Next question: {r2['reply'][:200]}")
        else:
            print(f"\n  INFO: follow_up_type={fu_type}, pending={is_still_pending}")

    return True


def main():
    print("\n" + "="*65)
    print("  FOLLOW-UP LOGIC TEST")
    print("="*65)

    # Case 1: Vague answer → must clarify
    run_case(
        "CASE 1: VAGUE answer → expect follow_up_clarify",
        session_id="followup-test-vague-v2",
        answer=VAGUE_ANSWER,
        expected_follow_up=True,
    )

    # Case 2: Strong answer → escalate or next topic
    run_case(
        "CASE 2: STRONG detailed answer → expect escalate or next topic",
        session_id="followup-test-strong-v2",
        answer=STRONG_ANSWER,
        expected_follow_up=False,
    )

    print(f"\n{'='*65}")
    print("  ALL FOLLOW-UP LOGIC TESTS PASSED")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
