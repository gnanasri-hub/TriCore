import urllib.request, json, sys

URL = "http://localhost:8000/api/interview"

def post(payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        URL, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

SESSION_ID = "verify-groq-001"

# ── REQUIREMENT 1: Only one endpoint exists ───────────────────────────────────
print("=" * 60)
print("REQUIREMENT 1: Single endpoint check")
print("=" * 60)
r = urllib.request.urlopen("http://localhost:8000/openapi.json")
spec = json.loads(r.read())
paths = list(spec.get("paths", {}).keys())
print(f"Registered paths: {paths}")
assert paths == ["/api/interview"], f"FAIL: unexpected paths {paths}"
print("PASS: exactly ONE endpoint -> POST /api/interview\n")

# ── REQUIREMENT 2: Start Interview ───────────────────────────────────────────
print("=" * 60)
print(f"REQUIREMENT 2: Start Interview (sessionId={SESSION_ID})")
print("=" * 60)

req1 = {
    "sessionId": SESSION_ID,
    "candidate": {
        "member": {
            "id": "CAND-001",
            "name": "Sarah Johnson",
            "jobRole": "Senior Data Engineer",
            "yearsExperience": 9,
            "education": "MS Computer Science",
            "status": "COMPLETED"
        },
        "missions": [
            {"day": 7,  "title": "Embeddings Explained",           "passed": True, "attempts": 1},
            {"day": 8,  "title": "Vector Databases Overview",       "passed": True, "attempts": 1},
            {"day": 10, "title": "Retrieval and Matching Engine",    "passed": True, "attempts": 2},
            {"day": 12, "title": "Prompt Engineering Fundamentals",  "passed": True, "attempts": 4},
            {"day": 16, "title": "Chatbot Backend API Integration",  "passed": True, "attempts": 1},
            {"day": 22, "title": "Multi-Agent Orchestration",        "passed": True, "attempts": 2},
            {"day": 23, "title": "Model Context Protocol MCP",       "passed": True, "attempts": 2},
            {"day": 28, "title": "Docker and Kubernetes Deployment", "passed": True, "attempts": 3},
            {"day": 29, "title": "Monitoring Logging Observability", "skipped": True},
            {"day": 31, "title": "Capstone Project Final Demo",      "passed": True, "attempts": 1},
        ],
        "signals": {"commitDays": 28, "missionsCompleted": 30, "missionsFirstTry": 20}
    }
}

print("REQUEST:")
print(json.dumps(req1, indent=2))
print()

status1, resp1 = post(req1)
print(f"HTTP {status1}")
print("RESPONSE:")
print(json.dumps(resp1, indent=2))
print()

assert status1 == 200, f"FAIL: expected 200, got {status1}"
assert resp1.get("done") is False, f"FAIL: done should be False, got {resp1.get('done')}"
assert resp1.get("reply"), "FAIL: reply is empty"
assert resp1.get("feedback") is None, "FAIL: feedback should not be present"
print("PASS: HTTP 200, done=false, reply present, no feedback\n")

# ── REQUIREMENT 3: Conversation Turn ─────────────────────────────────────────
print("=" * 60)
print(f"REQUIREMENT 3: Conversation Turn (same sessionId={SESSION_ID})")
print("=" * 60)

req2 = {
    "sessionId": SESSION_ID,
    "message": "Embeddings are numerical vector representations of data that capture semantic meaning. They allow models to understand similarity between concepts by measuring distance in vector space."
}

print("REQUEST:")
print(json.dumps(req2, indent=2))
print()

status2, resp2 = post(req2)
print(f"HTTP {status2}")
print("RESPONSE:")
print(json.dumps(resp2, indent=2))
print()

assert status2 == 200, f"FAIL: expected 200, got {status2}"
assert resp2.get("done") is False, f"FAIL: expected done=false for turn 2, got {resp2.get('done')}"
assert resp2.get("reply"), "FAIL: reply is empty"
print("PASS: HTTP 200, done=false, next question returned\n")

# ── REQUIREMENT 4: State is keyed only by sessionId ──────────────────────────
print("=" * 60)
print("REQUIREMENT 4: State isolation by sessionId")
print("=" * 60)

# Try a different session — should get 404
req_unknown = {"sessionId": "unknown-session-xyz", "message": "test"}
status_u, resp_u = post(req_unknown)
print(f"Unknown session response: HTTP {status_u} -> {resp_u}")
assert status_u == 404, f"FAIL: expected 404 for unknown session, got {status_u}"
print("PASS: unknown sessionId returns 404 (state isolated per sessionId)\n")

print("=" * 60)
print("ALL REQUIREMENTS VERIFIED")
print("=" * 60)
