"""
full_demo.py — End-to-end interview simulation for one candidate.

Usage (from the interview-agent/ directory):
    python scripts/full_demo.py [CAND-ID]

    CAND-ID defaults to CAND-003 (Emily Chen — strong first-try candidate).

What it does:
    1. Loads the candidate record from data/candidates.json.
    2. Starts a fresh interview session via dialogue_manager.start_interview.
    3. Drives simulated turns using a response bank keyed to the detected topic.
    4. Prints every request/response in a readable format.
    5. Prints the final feedback object in full when done=True.

The script is self-contained: it talks directly to the dialogue_manager
(no HTTP server needed), so it works with just OPENAI_API_KEY in your .env.
"""

import json
import sys
import textwrap
import uuid
from pathlib import Path
from typing import Any, Dict, List

# ── Path bootstrap ────────────────────────────────────────────────────────────
AGENT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT_ROOT))

from app.services import data_manager, dialogue_manager  # noqa: E402
from app.schemas import InterviewResponse  # noqa: E402

# ── ANSI colours (graceful fallback on Windows without ANSI support) ──────────
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
except Exception:
    pass

BOLD   = "\033[1m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
RESET  = "\033[0m"
DIM    = "\033[2m"
BLUE   = "\033[34m"


# ── Simulated answer bank ─────────────────────────────────────────────────────
# Maps lower-case topic keywords to (first_answer, follow_up_answer) pairs.
# first_answer is sent on the first turn for a topic.
# follow_up_answer is sent when a follow-up question is detected.

ANSWER_BANK: List[Dict[str, Any]] = [
    {
        "keywords": ["embedding", "vector", "semantic"],
        "first": (
            "Embeddings are dense numerical representations of text produced by a neural network. "
            "The model maps each token to a high-dimensional vector so that semantically similar "
            "texts end up geometrically close. Models like text-embedding-3-small use contrastive "
            "training to learn this mapping. Sparse embeddings like BM25 count term frequency, "
            "while dense embeddings capture meaning — hybrid search combines both for best recall."
        ),
        "follow_up": (
            "For domain-specific jargon not in general training data I fine-tune a bi-encoder on "
            "in-domain pairs or use late interaction models like ColBERT. Another option is a "
            "hybrid index: BM25 for exact term hits + dense retrieval for semantic matching, then "
            "a re-ranker (cross-encoder) to merge the lists. The trade-off is latency vs. recall."
        ),
    },
    {
        "keywords": ["faiss", "vector database", "index", "hnsw", "ivf", "ann"],
        "first": (
            "FAISS provides IndexFlatIP for exact inner-product search (cosine after L2 normalise) "
            "and approximate indexes like HNSW and IVF-PQ for large-scale use. HNSW builds a "
            "navigable small-world graph; query time is O(log n) vs O(n) for flat. IVF-PQ "
            "clusters vectors and quantises residuals, saving memory at a small accuracy cost. "
            "For production I choose based on dataset size, recall@k target, and memory budget."
        ),
        "follow_up": (
            "When inserting at scale I batch index builds offline and swap the live index with a "
            "read-lock to avoid query interruption. I track recall@10 on a held-out evaluation "
            "set after each rebuild. For Kubernetes deployments I use a shared PV so all replicas "
            "read the same index without rebuilding on every pod restart."
        ),
    },
    {
        "keywords": ["rag", "retrieval", "augmented", "generation", "chunk"],
        "first": (
            "RAG: chunk the corpus, embed each chunk, store in a vector DB. At query time, embed "
            "the question, retrieve top-k chunks, stuff them into the LLM context, and generate. "
            "Good chunking strategy matters: overlapping fixed-size windows work well; "
            "semantic splitting by paragraph boundaries is better for structured docs. "
            "Metadata filters (date, source) prevent stale or irrelevant retrieval."
        ),
        "follow_up": (
            "For contradictory retrieved passages I add a 'reconcile' step in the system prompt: "
            "'if sources conflict, say so and present both views'. I also score each retrieved "
            "chunk with a cross-encoder re-ranker and drop chunks below a confidence threshold "
            "rather than blindly stuffing the context window."
        ),
    },
    {
        "keywords": ["prompt", "engineering", "few-shot", "chain-of-thought", "cot"],
        "first": (
            "Prompt engineering shapes model behaviour without changing weights. Key techniques: "
            "few-shot examples for in-context learning, chain-of-thought (ask the model to "
            "reason step-by-step before answering), role prompting to set persona, and "
            "delimiters to separate context from instruction. For structured outputs I combine "
            "a JSON schema in the prompt with response_format=... in the API call."
        ),
        "follow_up": (
            "Temperature controls randomness; for factual tasks I use 0.0–0.2. "
            "Top-p (nucleus sampling) at 0.9 is a good default for creative tasks. "
            "I always version my prompt templates in Git and A/B test changes against "
            "an eval set before rolling out — even small wording changes can shift accuracy "
            "by several percentage points."
        ),
    },
    {
        "keywords": ["agent", "langchain", "react", "tool", "agentic"],
        "first": (
            "A LangChain ReAct agent follows a Thought → Action → Observation loop. The LLM "
            "emits a thought, calls a tool (action), reads the result (observation), and repeats "
            "until it decides to answer. I prevent infinite loops with a max_iterations cap and "
            "an output parser that detects repeated tool calls. For complex workflows I prefer "
            "LangGraph where each node is a deterministic function — easier to debug."
        ),
        "follow_up": (
            "Multi-agent coordination: agents share state via a typed Pydantic model passed "
            "through graph edges. A supervisor node routes tasks; worker nodes specialise. "
            "To avoid deadlock I use async execution with timeouts and a circuit-breaker that "
            "returns a fallback if any node exceeds its budget. Cost: I cache tool results and "
            "use GPT-4o-mini for intermediate reasoning, reserving GPT-4o for final synthesis."
        ),
    },
    {
        "keywords": ["mcp", "model context protocol", "server", "client"],
        "first": (
            "MCP standardises how LLM clients (editors, agents) connect to external tool servers. "
            "The client sends a JSON-RPC 'tools/call' request; the server executes and returns "
            "results. This decouples the LLM from specific SDK integrations — any MCP-compliant "
            "server works with any client. I've used it to expose a SQL query tool and a file "
            "system reader to Claude Desktop."
        ),
        "follow_up": (
            "For security I scope each tool to the minimum required permissions and validate "
            "all inputs server-side. Large payloads are streamed back in chunks. Token budget: "
            "I truncate tool results to a max_chars limit and summarise with a smaller LLM if "
            "they exceed it, so I don't blow the context window."
        ),
    },
    {
        "keywords": ["docker", "kubernetes", "deploy", "container", "k8s"],
        "first": (
            "I containerise with a multi-stage Dockerfile: build stage installs deps, final "
            "stage copies only the artefact. For a FastAPI service I use uvicorn with multiple "
            "workers behind a Kubernetes Deployment. A ConfigMap holds non-secret env vars; "
            "Secrets hold API keys. HPA scales on CPU; for LLM services I also track a custom "
            "queue-depth metric to scale ahead of latency spikes."
        ),
        "follow_up": (
            "Conversation state must live outside the pod — I use Redis with a TTL so sessions "
            "survive pod restarts. For the FAISS index I mount a ReadOnlyMany PV so all replicas "
            "share the same index without race conditions. Rolling updates use a 25% max-surge "
            "strategy so the old version handles traffic while new pods warm up."
        ),
    },
    {
        "keywords": ["fine-tun", "lora", "qlora", "finetune"],
        "first": (
            "Fine-tuning adapts a base model to domain-specific data. LoRA adds low-rank "
            "adapter matrices (rank 4–16) to attention layers, training only those weights — "
            "typically 0.1–1% of total params. QLoRA quantises the base model to 4-bit NF4 "
            "and trains LoRA adapters at 16-bit, fitting a 70B model on a single A100. "
            "I use fine-tuning when prompt engineering plateaus and I have ≥ 1 000 labelled examples."
        ),
        "follow_up": (
            "Catastrophic forgetting: I mix ~10% general instruction data into the fine-tuning "
            "set. Evaluation: perplexity on a held-out domain set, plus a task-specific metric "
            "(F1, BLEU, or human preference scores). I also run the base model as a reference "
            "to make sure the fine-tuned version doesn't regress on general capabilities."
        ),
    },
    {
        "keywords": ["security", "guardrail", "privacy", "pii", "safety"],
        "first": (
            "Key guardrails: prompt injection detection (flag inputs that try to override system "
            "prompts), output scanning for PII before returning to clients, rate limiting per "
            "user to prevent abuse, and a content moderation layer (OpenAI moderation API or "
            "Llama Guard). For regulated data I enforce data residency by routing to region-locked "
            "endpoints and strip PII before sending to any third-party LLM."
        ),
        "follow_up": (
            "For red-teaming I maintain an adversarial prompt library and run it in CI on every "
            "model or prompt change. OWASP LLM Top 10 is my checklist. For SOC-2 compliance I "
            "log all completions (excluding PII) to an append-only audit store with a 90-day "
            "retention policy."
        ),
    },
]

# Generic fallback answers when no keyword matches
GENERIC_ANSWERS = [
    (
        "I approach this by first understanding the objectives of the day's topic, then "
        "mapping them to concrete implementation patterns. I've worked with these tools "
        "in production and have direct experience with the trade-offs involved."
    ),
    (
        "The key considerations here are scalability, observability, and correctness. "
        "I'd design a solution that separates concerns cleanly, uses well-tested libraries "
        "where possible, and includes evaluation metrics from day one."
    ),
    (
        "From my experience, the hardest part is not the happy path but handling edge cases: "
        "partial failures, latency spikes, and data quality issues. I build with those in "
        "mind from the start rather than retrofitting reliability later."
    ),
    (
        "I would combine retrieval-augmented generation with a structured evaluation harness "
        "to measure answer quality. Continuous improvement loops — collecting failures, "
        "annotating them, and fine-tuning or adjusting prompts — are essential for production."
    ),
]

_generic_idx = 0


def _pick_answer(question: str, is_follow_up: bool) -> str:
    """Return a contextually appropriate simulated answer."""
    global _generic_idx
    q_lower = question.lower()
    for bank_entry in ANSWER_BANK:
        if any(kw in q_lower for kw in bank_entry["keywords"]):
            return bank_entry["follow_up"] if is_follow_up else bank_entry["first"]
    answer = GENERIC_ANSWERS[_generic_idx % len(GENERIC_ANSWERS)]
    _generic_idx += 1
    return answer


# ── Printing helpers ──────────────────────────────────────────────────────────

SEP = "─" * 72


def _banner(text: str, colour: str = CYAN) -> None:
    print(f"\n{colour}{BOLD}{SEP}{RESET}")
    print(f"{colour}{BOLD}  {text}{RESET}")
    print(f"{colour}{BOLD}{SEP}{RESET}")


def _section(label: str, content: str, colour: str = RESET) -> None:
    print(f"\n{BOLD}{label}{RESET}")
    for line in textwrap.wrap(content, width=68):
        print(f"  {colour}{line}{RESET}")


def _print_request(turn: int, session_id: str, payload: Dict[str, Any]) -> None:
    print(f"\n{DIM}{'─'*72}{RESET}")
    print(f"{BOLD}{YELLOW}► REQUEST  turn={turn}  session={session_id}{RESET}")
    if "candidate" in payload:
        member = payload["candidate"].get("member", {})
        print(f"  {DIM}candidate: {member.get('name')} ({member.get('id')}){RESET}")
    if "message" in payload:
        _section("  message:", payload["message"], colour=YELLOW)


def _print_response(turn: int, resp: InterviewResponse) -> None:
    colour = GREEN if not resp.done else RED
    status = "DONE ✓" if resp.done else "ongoing"
    print(f"\n{BOLD}{colour}◄ RESPONSE  [{status}]{RESET}")
    _section("  reply:", resp.reply, colour=colour)
    if resp.feedback:
        fb = resp.feedback
        print(f"\n{BOLD}{BLUE}  ╔══ FEEDBACK ══╗{RESET}")
        _section("  summary:", fb.summary, colour=BLUE)
        if fb.strengths:
            print(f"\n  {BOLD}Strengths:{RESET}")
            for s in fb.strengths:
                print(f"    {GREEN}✔ {s}{RESET}")
        if fb.gaps:
            print(f"\n  {BOLD}Gaps:{RESET}")
            for g in fb.gaps:
                print(f"    {RED}✘ {g}{RESET}")
        if fb.next:
            print(f"\n  {BOLD}Next steps:{RESET}")
            for n in fb.next:
                print(f"    {CYAN}→ {n}{RESET}")
        print(f"\n  {BOLD}{BLUE}  ╚══════════════╝{RESET}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_demo(cand_id: str = "CAND-003") -> None:
    _banner(f"AI Interview Agent — Full Demo  ({cand_id})")

    # Load candidate
    candidates_path = AGENT_ROOT / "data" / "candidates.json"
    with open(candidates_path, encoding="utf-8") as fh:
        all_candidates = json.load(fh)["candidates"]

    candidate = next((c for c in all_candidates if c["member"]["id"] == cand_id), None)
    if candidate is None:
        print(f"{RED}Candidate {cand_id} not found in candidates.json{RESET}")
        sys.exit(1)

    member = candidate["member"]
    print(f"\n  Candidate : {BOLD}{member['name']}{RESET}  ({cand_id})")
    print(f"  Role      : {member['jobRole']}")
    print(f"  Experience: {member['yearsExperience']} years")
    print(f"  Missions  : {len(candidate['missions'])} recorded\n")

    # Pre-load FAISS index (reads from disk — no API call needed)
    print(f"{DIM}Initialising FAISS index…{RESET}", end=" ", flush=True)
    data_manager.init_index()
    print(f"{GREEN}ready{RESET}")

    session_id = f"demo-{cand_id}-{uuid.uuid4().hex[:8]}"
    turn = 0
    is_follow_up = False   # tracks whether current question is a follow-up

    # ── Turn 0: start interview ───────────────────────────────────────────────
    turn += 1
    payload: Dict[str, Any] = {"sessionId": session_id, "candidate": candidate}
    _print_request(turn, session_id, payload)

    reply = dialogue_manager.start_interview(session_id, candidate)
    resp = InterviewResponse(reply=reply, done=False)
    _print_response(turn, resp)

    # ── Subsequent turns ──────────────────────────────────────────────────────
    max_turns = 30  # safety ceiling — demo should end well before this

    while not resp.done and turn < max_turns:
        # Simulate candidate typing a relevant answer
        answer = _pick_answer(resp.reply, is_follow_up=is_follow_up)

        turn += 1
        payload = {"sessionId": session_id, "message": answer}
        _print_request(turn, session_id, payload)

        resp = dialogue_manager.process_message(session_id, answer)

        # Detect if the system issued a follow-up (done=False and question_count increment
        # without covered_days growing — proxy: check "elaborate" / "could you" in reply)
        follow_up_markers = ["elaborate", "could you", "can you", "clarify", "explain",
                              "what do you mean", "tell me more", "give an example"]
        is_follow_up = any(m in resp.reply.lower() for m in follow_up_markers)

        _print_response(turn, resp)

    _banner("Demo complete", colour=GREEN)
    print(f"\n  Total turns : {turn}")
    print(f"  Outcome     : {'Completed ✓' if resp.done else 'Max turns reached'}\n")


if __name__ == "__main__":
    cand_id = sys.argv[1] if len(sys.argv) > 1 else "CAND-003"
    run_demo(cand_id)
