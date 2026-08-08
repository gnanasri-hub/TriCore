"""
test_personalization.py
=======================
Tests personalization for CAND-003, CAND-010, CAND-011 by running
3 turns per candidate and printing the questions + which tier/depth
drove the selection.
"""
import urllib.request
import json

URL = "http://localhost:8000/api/interview"

# ── Candidate payloads ────────────────────────────────────────────────────────

CANDIDATES = {
    "CAND-003": {
        "desc": "Emily Chen — AI Engineer, 6 yrs, ALL first-try passes → expect DEEP questions",
        "payload": {
            "member": {
                "id": "CAND-003", "name": "Emily Chen",
                "jobRole": "AI Engineer", "yearsExperience": 6,
                "education": "MS Artificial Intelligence", "status": "COMPLETED",
            },
            "missions": [
                {"day": 7,  "title": "Embeddings Explained",              "passed": True, "attempts": 1},
                {"day": 8,  "title": "Vector Databases Overview",          "passed": True, "attempts": 1},
                {"day": 10, "title": "Retrieval & Matching Engine",         "passed": True, "attempts": 1},
                {"day": 11, "title": "RAG End-to-End & LLM API Basics",    "passed": True, "attempts": 1},
                {"day": 12, "title": "Prompt Engineering Fundamentals",     "passed": True, "attempts": 1},
                {"day": 13, "title": "Function Calling & Structured Outputs","passed": True, "attempts": 1},
                {"day": 21, "title": "LangChain Agents",                    "passed": True, "attempts": 1},
                {"day": 22, "title": "Multi-Agent Orchestration",           "passed": True, "attempts": 1},
                {"day": 23, "title": "Model Context Protocol (MCP)",        "passed": True, "attempts": 1},
                {"day": 31, "title": "Capstone Project & Final Demo",       "passed": True, "attempts": 1},
            ],
            "signals": {"commitDays": 31, "missionsCompleted": 31, "missionsFirstTry": 30},
        },
    },
    "CAND-011": {
        "desc": "Mia Alvarez — UX Researcher, 6 yrs, 5 SKIPPED AI topics → expect FOUNDATIONAL questions on skipped days",
        "payload": {
            "member": {
                "id": "CAND-011", "name": "Mia Alvarez",
                "jobRole": "UX Researcher", "yearsExperience": 6,
                "education": "MA Human-Computer Interaction", "status": "COMPLETED",
            },
            "missions": [
                {"day": 1,  "title": "VS Code & Python Environment Setup",    "passed": True, "attempts": 2},
                {"day": 2,  "title": "Local LLM & AI Coding Assistant Setup", "passed": True, "attempts": 1},
                {"day": 3,  "title": "First AI Project, React Frontend & GitHub","passed": True, "attempts": 3},
                {"day": 4,  "title": "Reading & Processing Structured Data",  "passed": True, "attempts": 2},
                {"day": 7,  "title": "Embeddings Explained",                  "skipped": True},
                {"day": 8,  "title": "Vector Databases Overview",             "skipped": True},
                {"day": 12, "title": "Prompt Engineering Fundamentals",       "skipped": True},
                {"day": 16, "title": "Chatbot Backend & API Integration",     "skipped": True},
                {"day": 22, "title": "Multi-Agent Orchestration",             "skipped": True},
                {"day": 31, "title": "Capstone Project & Final Demo",         "passed": True, "attempts": 4},
            ],
            "signals": {"commitDays": 9, "missionsCompleted": 14, "missionsFirstTry": 5},
        },
    },
    "CAND-010": {
        "desc": "Gerald Combs — IT Support Specialist, 20 yrs, 3 FAILED + 2 SKIPPED → expect probing on failed/skipped days",
        "payload": {
            "member": {
                "id": "CAND-010", "name": "Gerald Combs",
                "jobRole": "IT Support Specialist", "yearsExperience": 20,
                "education": "AAS Information Technology", "status": "COMPLETED",
            },
            "missions": [
                {"day": 1,  "title": "VS Code & Python Environment Setup",  "passed": True,  "attempts": 2},
                {"day": 7,  "title": "Embeddings Explained",                "passed": True,  "attempts": 5},
                {"day": 8,  "title": "Vector Databases Overview",           "passed": False, "attempts": 4},
                {"day": 10, "title": "Retrieval & Matching Engine",          "passed": False, "attempts": 3},
                {"day": 12, "title": "Prompt Engineering Fundamentals",      "passed": True,  "attempts": 5},
                {"day": 16, "title": "Chatbot Backend & API Integration",    "passed": True,  "attempts": 4},
                {"day": 22, "title": "Multi-Agent Orchestration",            "passed": False, "attempts": 3},
                {"day": 27, "title": "Security, Privacy & Guardrails",       "skipped": True},
                {"day": 28, "title": "Docker & Kubernetes Deployment",       "skipped": True},
                {"day": 31, "title": "Capstone Project & Final Demo",        "passed": True,  "attempts": 3},
            ],
            "signals": {"commitDays": 22, "missionsCompleted": 23, "missionsFirstTry": 1},
        },
    },
}

# Short answers that keep the conversation going without triggering done=true too soon
SHORT_ANSWER = (
    "I have some familiarity with this area but I'd appreciate going deeper. "
    "Could you give me a bit more context on what aspect you're most interested in?"
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


def run_candidate(cand_id: str, info: dict, num_questions: int = 4):
    print("\n" + "=" * 70)
    print(f"  {cand_id}: {info['desc']}")
    print("=" * 70)

    session_id = f"personalization-test-{cand_id.lower()}-v2"

    # Start
    status, resp = post({"sessionId": session_id, "candidate": info["payload"]})
    if status != 200:
        print(f"  ERROR starting session: {status} {resp}")
        return

    questions = []
    day_sequence = []

    # Collect questions over num_questions turns
    q_text = resp["reply"]
    questions.append(q_text)

    # Check status for day info
    s = get_status(session_id)
    day_sequence.append(s["covered_days"][:])

    print(f"\n  Q1 → Day {s['covered_days'][-1] if s['covered_days'] else '?'}")
    print(f"       {q_text}")

    for i in range(2, num_questions + 1):
        if resp.get("done"):
            break
        status, resp = post({"sessionId": session_id, "message": SHORT_ANSWER})
        if status != 200:
            print(f"  ERROR on turn {i}: {status} {resp}")
            break
        if resp.get("done"):
            break
        q_text = resp["reply"]
        questions.append(q_text)
        s = get_status(session_id)
        day_sequence.append(s["covered_days"][:])
        covered = s["covered_days"]
        print(f"\n  Q{i} → Day {covered[-1] if covered else '?'}")
        print(f"       {q_text}")

    return questions, day_sequence


def main():
    print("\n" + "=" * 70)
    print("  PERSONALIZATION TEST")
    print("  Verifying questions match candidate strength/weakness profiles")
    print("=" * 70)

    # Extract profiles for analysis
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    from app.services.data_manager import get_candidate_profile

    for cand_id, info in CANDIDATES.items():
        profile = get_candidate_profile(info["payload"])
        print(f"\n{'─'*70}")
        print(f"  Profile for {cand_id} ({profile['name']})")
        print(f"{'─'*70}")
        print(f"  Role:          {profile['job_role']} ({profile['experience_level']}, {profile['years_experience']} yrs)")
        print(f"  Strong topics: {profile['strong_topics'] or 'none'}")
        print(f"  Weak topics:   {profile['weak_topics'] or 'none'}")
        print(f"  Skipped days:  {profile['skipped_days'] or 'none'}")
        print(f"  Failed days:   {profile['failed_days'] or 'none'}")
        attempts = profile.get("attempts_by_day", {})
        if attempts:
            print(f"  Attempts/day:  { {k: v for k,v in sorted(attempts.items())} }")

        result = run_candidate(cand_id, info, num_questions=4)

    print("\n\n" + "=" * 70)
    print("  ANALYSIS — why questions were chosen")
    print("=" * 70)

    print("""
CAND-003 (Emily Chen — AI Engineer, all first-try passes):
  • No skipped/failed days → Tier-1 skipped entirely
  • Tier-2: job role "AI Engineer" semantic match → AI/ML-heavy days prioritised
  • All days are strong (≤2 attempts) → depth_instruction = ADVANCED
  • LLM instructed: "do NOT ask what something is — ask how to design/debug/choose"
  • Expected: design-level, architectural, trade-off questions

CAND-011 (Mia Alvarez — UX Researcher, 5 skipped AI days):
  • Tier-1 fires immediately: skipped_days = [7, 8, 12, 16, 22]
  • All selected days are skipped → depth_instruction = FOUNDATIONAL + encouraging
  • LLM instructed: "clear foundational question — what is it, why does it matter"
  • Expected: "what is X" / "explain how X works" style questions

CAND-010 (Gerald Combs — IT Support Specialist, 3 failed + 2 skipped):
  • Tier-1 fires immediately: failed_days = [8, 10, 22], skipped_days = [27, 28]
  • Failed days get: "attempted N times and did not pass — foundational question"
  • Skipped days get: "skipped entirely — foundational + encouraging"
  • Expected: explanation questions on Vector DBs, Retrieval, Multi-Agent, Security, Docker
""")


if __name__ == "__main__":
    main()
