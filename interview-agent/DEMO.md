# Full Interview Demo

This document shows a complete multi-turn interview session for **Emily Chen (CAND-003)**,
an AI Engineer with 6 years of experience who passed every cohort mission on the first attempt.

Because all her topics are in `strong_topics`, the agent asks design-level, architectural
questions throughout, probes for deeper depth on one topic, and closes with a feedback
object that references her specific answers.

All `curl` commands target a locally running server:

```bash
uvicorn app.main:app --reload   # in one terminal
# then run the curl commands below in a second terminal
```

---

## Turn 0 — Start the interview

**Request**

```bash
curl -s -X POST http://127.0.0.1:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-emily-001",
    "candidate": {
      "member": {
        "id": "CAND-003",
        "name": "Emily Chen",
        "jobRole": "AI Engineer",
        "yearsExperience": 6,
        "education": "MS Artificial Intelligence",
        "status": "COMPLETED"
      },
      "missions": [
        { "day": 7,  "title": "Embeddings Explained",                  "passed": true, "attempts": 1 },
        { "day": 8,  "title": "Vector Databases Overview",             "passed": true, "attempts": 1 },
        { "day": 10, "title": "Retrieval & Matching Engine",           "passed": true, "attempts": 1 },
        { "day": 11, "title": "RAG End-to-End & LLM API Basics",       "passed": true, "attempts": 1 },
        { "day": 12, "title": "Prompt Engineering Fundamentals",       "passed": true, "attempts": 1 },
        { "day": 13, "title": "Function Calling & Structured Outputs", "passed": true, "attempts": 1 },
        { "day": 21, "title": "LangChain Agents",                      "passed": true, "attempts": 1 },
        { "day": 22, "title": "Multi-Agent Orchestration",             "passed": true, "attempts": 1 },
        { "day": 23, "title": "Model Context Protocol (MCP)",          "passed": true, "attempts": 1 },
        { "day": 31, "title": "Capstone Project & Final Demo",         "passed": true, "attempts": 1 }
      ],
      "signals": { "commitDays": 31, "missionsCompleted": 31, "missionsFirstTry": 30 }
    }
  }'
```

**Response**

```json
{
  "reply": "Hi Emily, great to meet you — and congratulations on completing the cohort. Let's jump straight in. You've clearly worked extensively with embeddings, so I'd love to go a level deeper right away. When you're deploying a semantic search system and the general-purpose embedding model doesn't represent your domain's vocabulary well — say, highly specialised legal or biomedical terminology — how do you diagnose that gap, and what's your preferred strategy for closing it?",
  "done": false
}
```

---

## Turn 1 — Emily answers the embeddings question

**Request**

```bash
curl -s -X POST http://127.0.0.1:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-emily-001",
    "message": "I usually start by running a qualitative retrieval audit — I pull a sample of domain queries and manually inspect the top-k results to see where the embeddings are clearly conflating unrelated terms or missing domain synonyms. If the gaps are significant, I evaluate two paths: fine-tuning a bi-encoder on in-domain pairs using contrastive loss, which gives the best semantic quality but requires labelled data and retraining overhead; or a hybrid index that pairs BM25 for exact term recall with the dense model for semantic coverage, then a cross-encoder re-ranker to merge the lists. For most production cases I lean on the hybrid approach first because it requires no retraining and the re-ranker can be swapped independently."
  }'
```

**Response**

```json
{
  "reply": "That's a really pragmatic framework — the hybrid-first approach makes a lot of sense when labelled data is scarce. Let's move to vector databases. Given you've worked with FAISS, at what scale does IndexFlatIP stop being the right tool, and how do you decide between HNSW and IVF-PQ when you need to go approximate?",
  "done": false
}
```

---

## Turn 2 — Emily answers the FAISS indexing question

**Request**

```bash
curl -s -X POST http://127.0.0.1:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-emily-001",
    "message": "IndexFlatIP is fine up to a few million vectors if you can afford the memory and latency — it is exact, so recall is perfect. Once you are north of ten million vectors or have strict sub-ten-millisecond latency requirements, you need approximate search. I choose between HNSW and IVF-PQ based on two axes: memory budget and update frequency. HNSW is faster at query time and handles incremental inserts well, but the graph structure is expensive in RAM — roughly 100 bytes per vector for a typical M=32 build. IVF-PQ with product quantisation compresses aggressively, so it wins when you are memory-constrained, but it requires a full rebuild for significant insertions and recall drops more sharply with quantisation error. For a read-heavy system with a fixed corpus I pick IVF-PQ; for a system with frequent updates I pick HNSW."
  }'
```

**Response**

```json
{
  "reply": "Solid — you clearly know the trade-off space well. Let's shift to RAG. A tricky failure mode: your retriever surfaces contextually plausible chunks, two of them contradict each other, and the LLM confidently synthesises a hallucinated answer from both. How do you design the pipeline to catch that before it reaches the user?",
  "done": false
}
```

---

## Turn 3 — Emily answers the RAG contradictions question

**Request**

```bash
curl -s -X POST http://127.0.0.1:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-emily-001",
    "message": "A few layers. First, at retrieval time I use a cross-encoder re-ranker that scores each chunk against the query independently — contradictory chunks usually score similarly and both make the cut, but I can add a pairwise consistency check that flags chunk pairs with high semantic similarity but opposing sentiment or factual claims. Second, in the prompt I instruct the model explicitly: if retrieved sources conflict, surface both positions rather than synthesising a single answer, and cite the source metadata. Third, I maintain a post-generation guardrail that compares the output against each retrieved chunk using an NLI model — if any chunk strongly contradicts the output I flag it for human review rather than returning it directly."
  }'
```

**Response**

```json
{
  "reply": "That NLI post-generation check is a nice touch — I don't hear that approach often. Let's talk about agents. You passed the LangChain and multi-agent days on the first attempt, so I want to push into the hard parts: when a ReAct agent is in production and it starts looping — calling the same tool repeatedly — what does your debugging and guardrail strategy look like?",
  "done": false
}
```

---

## Turn 4 — Emily answers the ReAct agent looping question

**Request**

```bash
curl -s -X POST http://127.0.0.1:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-emily-001",
    "message": "Loops usually come from one of three root causes: the tool returns an unhelpful result and the agent keeps retrying, the output parser fails silently so the agent never sees the observation, or the stop condition in the prompt is ambiguous. My guardrail stack is: a max_iterations cap at the executor level that forces an early termination with a structured error, a tool-call deduplication check that raises if the same tool is called with identical arguments twice in a row, and structured logging of every thought-action-observation triple so I can replay the loop in a notebook. For the longer-term fix I move the workflow to LangGraph where each node is deterministic — you can add explicit loop-detection edges and return a fallback node rather than letting the agent spin."
  }'
```

**Response**

```json
{
  "reply": "Good — the structured logging point is often underrated. Moving on to multi-agent coordination: in a LangGraph graph where you have a supervisor routing tasks to specialised worker agents, how do you handle the case where a worker times out or returns a malformed result mid-graph without failing the entire workflow?",
  "done": false
}
```

---

## Turn 5 — Emily answers the multi-agent fault tolerance question

**Request**

```bash
curl -s -X POST http://127.0.0.1:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-emily-001",
    "message": "Each worker node is wrapped in a try-except that catches both timeout and validation errors and writes a structured error object into the shared state rather than raising. The supervisor node checks for the error key on every incoming edge — if it finds one it routes to a recovery node that either retries with a simplified prompt or substitutes a cached fallback result if one exists. I set per-node async timeouts using asyncio.wait_for so a slow worker cannot block the entire graph. For observability I emit a span for every node execution into an OpenTelemetry collector, which gives me a flame graph of the execution trace when something goes wrong."
  }'
```

**Response**

```json
{
  "reply": "The OpenTelemetry span-per-node pattern is excellent for exactly that reason. Let's cover MCP. When you're exposing a database query tool to an LLM client via Model Context Protocol, what's your approach to preventing a large query result from blowing the client's context window, and how do you scope permissions so the tool can't be misused?",
  "done": false
}
```

---

## Turn 6 — Emily answers the MCP question

**Request**

```bash
curl -s -X POST http://127.0.0.1:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-emily-001",
    "message": "On the payload side I enforce a max_rows and max_chars limit server-side before returning results — if the result exceeds it I truncate and append a note saying results were truncated, so the model knows it did not see everything. For very large result sets I add a summarise flag: the tool first calls a lighter model to summarise the results, then returns the summary instead of the raw rows. For permissions I use a capability manifest: each MCP server declares exactly which resources and operations it can access, and the client validates the manifest against an allowlist before establishing the session. Individual tool calls are also signed with the session token so the server can verify they originate from an authorised client."
  }'
```

**Response**

```json
{
  "reply": "That capability manifest approach aligns well with the principle of least privilege. Final topic — prompt engineering. You aced that day on the first attempt, so let me ask about the evaluation side: you've shipped a prompt change to production and a week later your support queue spikes. How do you retrospectively diagnose whether the prompt change caused the regression, and what does your rollback and forward-fix process look like?",
  "done": false
}
```

---

## Turn 7 — Emily answers the prompt regression question

**Request**

```bash
curl -s -X POST http://127.0.0.1:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "demo-emily-001",
    "message": "First I diff the prompt versions in version control and pull the completion logs for a 48-hour window before and after the deploy, then run both prompt versions against the failing inputs from the support queue offline to see if the old prompt handles them correctly. If it does, the prompt is the likely cause. Rollback is a one-line config change since prompts are versioned in a feature flag store decoupled from the application deploy. For the forward fix I build a regression test set from the failing inputs, run it in CI against every future prompt change, and set an alert threshold on my eval metrics — currently a combination of LLM-as-a-judge scores and task-specific accuracy on a golden dataset — so this class of regression is caught before it reaches production next time."
  }'
```

**Response**

```json
{
  "reply": "Thank you — that wraps up our interview. I'll share your feedback below.",
  "done": true,
  "feedback": {
    "summary": "Emily demonstrated the depth and breadth you would expect from a strong mid-to-senior AI Engineer: she moved comfortably from foundational retrieval theory into production-grade architecture across embeddings, RAG, agentic systems, and MCP, with the most impressive moments being her NLI-based post-generation consistency check and her OpenTelemetry tracing strategy for multi-agent graphs. The one area to develop further is the formal evaluation infrastructure around prompt changes, where her answer was solid but leaned more on reactive diagnosis than proactive CI-gated eval pipelines.",
    "strengths": [
      "Articulated a clear hybrid retrieval strategy (BM25 + dense + cross-encoder re-ranker) and explained the decision criteria for choosing fine-tuning versus hybrid search based on data availability.",
      "Demonstrated precise command of FAISS index trade-offs — correctly contrasted HNSW memory overhead against IVF-PQ compression and tied the choice to read-vs-update workload patterns.",
      "Showed a multi-layer approach to RAG contradiction handling, including a pairwise consistency check at retrieval and an NLI post-generation guardrail — a pattern rarely seen at this level of detail.",
      "Described a production-grade ReAct agent guardrail stack (iteration cap, deduplication, structured logging) and articulated when to migrate to LangGraph for deterministic control flow.",
      "Explained MCP permission scoping via a capability manifest and demonstrated awareness of context-window constraints through server-side truncation and summarisation strategies."
    ],
    "gaps": [
      "Did not describe a proactive, CI-integrated evaluation pipeline for prompt changes — the answer focused on retrospective diagnosis rather than preventing regressions from reaching production in the first place.",
      "Function calling and structured outputs (Day 13) were not covered during the interview — no signal on whether she can harden function-calling workflows against malformed arguments or tool-loop failures.",
      "The answer on prompt regression touched on LLM-as-a-judge scoring but did not specify how the golden dataset is maintained or how the alert threshold is calibrated over time."
    ],
    "next": [
      "Build a CI-integrated prompt evaluation pipeline: define a golden dataset of at least 50 labelled inputs, wire it into GitHub Actions, and set an LLM-as-a-judge pass-rate gate that blocks merges below a threshold.",
      "Implement a production function-calling workflow end-to-end — specifically practice hardening against malformed tool arguments, schema validation on the server side, and graceful degradation when the model calls a non-existent function.",
      "Read the RAGAS framework documentation and run it against your next RAG project to get quantitative faithfulness and answer-relevance scores, not just qualitative inspection.",
      "Set up an OpenTelemetry + Langfuse (or LangSmith) tracing integration on a personal LangGraph project to practise reading execution traces and identifying latency bottlenecks at the node level."
    ]
  }
}
```

---

## Session lifecycle summary

| Turn | Sent | `done` | Notes |
|------|------|--------|-------|
| 0 | `candidate` object | `false` | Session created, first question asked (Embeddings — strong topic) |
| 1 | Answer on hybrid retrieval | `false` | Solid answer → moved to FAISS (strong topic) |
| 2 | Answer on FAISS trade-offs | `false` | Strong answer → moved to RAG |
| 3 | Answer on RAG contradictions | `false` | Strong answer → moved to Agents |
| 4 | Answer on ReAct loops | `false` | Strong answer → moved to Multi-agent |
| 5 | Answer on fault tolerance | `false` | Strong answer → moved to MCP |
| 6 | Answer on MCP | `false` | Strong answer → moved to Prompt Engineering |
| 7 | Answer on prompt regression | `true` | 8 questions asked across 6 curriculum days → interview ends, feedback generated |

---

## Key behaviours demonstrated

- **No skipped/failed days** for CAND-003, so the agent went straight to job-role semantic matching (Tier 2), covering Embeddings → Vector DBs → RAG → Agents → Multi-agent → MCP → Prompt Engineering.
- **Depth escalation**: every question was design/architectural level, not foundational, because all topics were in `strong_topics`.
- **Natural transitions**: replies acknowledge the previous answer before pivoting ("That NLI post-generation check is a nice touch", "The OpenTelemetry span-per-node pattern is excellent").
- **Ending gate enforced**: the interview did not end until `question_count >= 8` AND `len(covered_days) >= 4`.
- **Feedback is candidate-specific**: the summary, strengths, and gaps all reference Emily's actual answers and her specific cohort day performance — not generic boilerplate.
