import logging
from typing import List, Dict, Any, Optional
from app.schemas import SessionState
from app.services import data_manager
from app import config

logger = logging.getLogger(__name__)

# ── High-quality fallback questions ──────────────────────────────────────────
# Used when the LLM call fails. Keyed by curriculum day number.
# Each entry has a "strong" variant (candidate passed the topic first-try)
# and a "weak" variant (candidate skipped or failed it).

FALLBACK_QUESTIONS: Dict[int, Dict[str, str]] = {
    # Day 7 — Embeddings
    7: {
        "strong": (
            "You've clearly worked with embeddings before, so let's go a level deeper. "
            "When you're building a semantic search system and the general-purpose embedding model "
            "doesn't represent your domain's vocabulary well — say, highly specialised medical or "
            "legal terminology — how do you approach that gap? Walk me through whether you'd "
            "fine-tune the encoder, lean on a hybrid BM25 + dense retrieval setup, or something "
            "else entirely, and what factors drive that choice."
        ),
        "weak": (
            "Let's start with the foundations here. In your own words, what does a vector "
            "embedding actually represent — what information is being captured when a model "
            "converts a sentence into a list of numbers? And practically speaking, what's the "
            "key difference between a dense embedding and a sparse one like BM25?"
        ),
    },
    # Day 8 — Vector Databases
    8: {
        "strong": (
            "Given your experience with vector databases, I'd like to dig into the indexing "
            "trade-offs. When you're scaling from a few thousand vectors to hundreds of millions, "
            "at what point does FAISS IndexFlatIP become the wrong choice, and how do you decide "
            "between HNSW and IVF-PQ? What recall, latency, and memory targets are you "
            "optimising for in that decision?"
        ),
        "weak": (
            "Let's talk about why vector databases exist as a category. A traditional SQL database "
            "is excellent at exact lookups — so what's the fundamental limitation that makes it "
            "unsuitable for similarity search over embeddings? And why do indexes like HNSW matter "
            "for making that search fast at scale?"
        ),
    },
    # Day 9 — Building the Vector DB
    9: {
        "strong": (
            "When you're populating a vector database at scale — say, indexing millions of "
            "documents in a batch pipeline — how do you architect the process to avoid query "
            "latency spikes on the live index while the build is happening? And what does your "
            "data consistency strategy look like when index updates need to stay in sync with "
            "your source-of-truth store?"
        ),
        "weak": (
            "Walk me through the mechanics of getting embeddings into a vector database. "
            "Once you've generated your embedding vectors, what are the steps to index them "
            "so they're searchable, and how does metadata filtering — like restricting results "
            "to a specific date range or category — work alongside the vector search?"
        ),
    },
    # Day 10 — Retrieval & Matching
    10: {
        "strong": (
            "In a production retrieval system, pure vector similarity often isn't enough on its "
            "own. How do you combine dense retrieval with metadata filters or keyword signals to "
            "improve precision, and how do you handle the re-ranking step to surface the most "
            "relevant chunks before they hit the LLM context window?"
        ),
        "weak": (
            "When a user submits a query, how does the retrieval engine actually find the most "
            "relevant documents from your vector store? Can you walk me through the journey from "
            "raw query text to the final ranked list of matching chunks?"
        ),
    },
    # Day 11 — RAG End-to-End
    11: {
        "strong": (
            "Let's talk about a tricky RAG failure mode: your retriever surfaces contextually "
            "plausible chunks, but two of them contradict each other, and the LLM confidently "
            "synthesises a hallucinated answer from both. How do you design the pipeline — "
            "chunking strategy, retrieval scoring, and prompt construction — to catch that "
            "before it reaches the user?"
        ),
        "weak": (
            "Could you walk me through the complete flow of a RAG system, from the moment a "
            "user types a question to the moment they see an answer? I'm particularly interested "
            "in why we bother retrieving external documents at all, rather than just relying on "
            "what the LLM already knows."
        ),
    },
    # Day 12 — Prompt Engineering
    12: {
        "strong": (
            "Prompt engineering can feel more like art than science, so let's get concrete. "
            "You're building a customer-facing chatbot and a small prompt change in staging "
            "looks better qualitatively, but you can't tell if it's actually an improvement. "
            "How do you set up a rigorous evaluation process to make that call confidently, "
            "and how do you version and roll out prompt changes safely in production?"
        ),
        "weak": (
            "Take me through the core techniques you'd reach for when crafting a system prompt "
            "for an LLM. What's the difference between zero-shot, few-shot, and chain-of-thought "
            "prompting, and when does each one earn its place in your toolkit?"
        ),
    },
    # Day 13 — Function Calling
    13: {
        "strong": (
            "Function calling lets the model drive external actions, which creates a reliability "
            "problem: the model might call the wrong function, pass malformed arguments, or call "
            "the same function repeatedly in a loop. How do you harden a function-calling "
            "workflow against those failure modes in a production system?"
        ),
        "weak": (
            "What does OpenAI function calling actually enable that wasn't possible with plain "
            "text generation? Walk me through a concrete example of a function definition, how "
            "the model decides to invoke it, and what happens with the result."
        ),
    },
    # Day 21 — LangChain Agents
    21: {
        "strong": (
            "ReAct agents are powerful but notoriously hard to make reliable — they can loop, "
            "hallucinate tool names, or fail silently on malformed outputs. When you're "
            "productionising a ReAct agent, what guardrails do you put in place, and at what "
            "point would you abandon the single-agent pattern in favour of a LangGraph "
            "multi-node approach?"
        ),
        "weak": (
            "Help me understand what makes an AI agent fundamentally different from a regular "
            "LLM call. What is the agent actually doing between receiving a task and producing "
            "a final answer, and how do tools fit into that loop?"
        ),
    },
    # Day 22 — Multi-Agent Orchestration
    22: {
        "strong": (
            "In a multi-agent system built with something like CrewAI or LangGraph, coordination "
            "overhead can silently eat your latency and token budget. How do you design the "
            "inter-agent communication protocol and shared state model to keep things efficient, "
            "and how do you debug a coordination failure when the system produces a wrong answer "
            "without any individual agent erroring out?"
        ),
        "weak": (
            "What's the value of having multiple specialised agents instead of one general-purpose "
            "agent? Walk me through a scenario where a router agent decides which specialist to "
            "hand a task to, and explain what that delegation actually looks like in practice."
        ),
    },
    # Day 23 — MCP
    23: {
        "strong": (
            "When you're exposing tools to an LLM client via MCP, token budget and security "
            "become real constraints fast. How do you prevent a tool from returning a payload "
            "that blows the context window, and what's your approach to scoping permissions "
            "so a compromised tool server can't escalate privileges within the client session?"
        ),
        "weak": (
            "The Model Context Protocol is solving a specific integration problem — what is it? "
            "Before MCP existed, what was the friction point when trying to connect an LLM-powered "
            "editor like Cursor or Claude Desktop to external data sources and tools?"
        ),
    },
    # Day 27 — Security & Guardrails
    27: {
        "strong": (
            "Prompt injection is one of the OWASP LLM Top 10 risks — an attacker embeds "
            "instructions in user-supplied content that override your system prompt. What's your "
            "defence-in-depth strategy against that, and how do you balance security strictness "
            "with not making the system so paranoid it refuses legitimate requests?"
        ),
        "weak": (
            "When you deploy an LLM-powered application, what are the top two or three security "
            "concerns that are unique to LLMs — risks you wouldn't face with a traditional REST "
            "API — and what's your first line of defence against each?"
        ),
    },
    # Day 28 — Docker & Kubernetes
    28: {
        "strong": (
            "A stateful LLM service is trickier to run on Kubernetes than a typical stateless "
            "microservice — conversation memory, FAISS indexes, and long-running inference all "
            "create challenges. How do you handle state persistence and index sharing across "
            "pod replicas, and what metrics do you use for HPA when the load driver is LLM "
            "throughput rather than plain CPU?"
        ),
        "weak": (
            "Why do we containerise Python applications with Docker before deploying them, and "
            "what specific problems does Kubernetes solve once you have more than a handful of "
            "those containers to manage?"
        ),
    },
}


def get_fallback_question(day_num: int, is_strong: bool) -> Optional[str]:
    """Return a pre-written fallback question for the given day, or None if not available."""
    entry = FALLBACK_QUESTIONS.get(day_num)
    if not entry:
        # Adjacent-day aliasing for days without their own entry
        if day_num in (9, 10):
            entry = FALLBACK_QUESTIONS.get(day_num)  # already keyed
        elif day_num in (24,):
            entry = FALLBACK_QUESTIONS.get(23)
        elif day_num in (14, 15):
            entry = None  # fine-tuning — no fallback, use generic
    if entry:
        return entry.get("strong" if is_strong else "weak")
    return None


# ── System prompt shared across both question-generation calls ────────────────
_INTERVIEWER_SYSTEM = """\
You are a senior AI engineering interviewer conducting a technical interview on behalf of \
a 31-day AI engineering cohort. Your style is warm, encouraging, and intellectually rigorous \
— you want candidates to do well, but you don't lower the bar.

Tone guidelines:
- Speak in natural, conversational English. Avoid bullet-point questions or numbered lists.
- Never sound robotic or form-letter. Each question should feel hand-crafted.
- Acknowledge the conversation so far naturally when transitioning topics — \
  a brief connector like "Let's shift gears a bit" or "Building on that..." keeps the flow human.
- Keep questions to 2–4 sentences maximum. One sharp question beats a wall of sub-questions.
- Never repeat a question or topic already covered in the conversation history.\
"""


def generate_question(session: SessionState) -> str:
    """
    Generate a natural, on-topic interview question fully personalised to
    the candidate's cohort history, role, and performance on this specific
    curriculum day.

    Personalization rules:
      - is_strong  (day passed in ≤ 2 attempts) → design/architectural/trade-off question
      - is_weak    (day skipped or failed)       → foundational/explanation question,
                                                   encouraging tone
      - is_medium  (passed in 3+ attempts)       → mid-level conceptual + implementation
    """
    day_num = session.current_day
    if not day_num:
        logger.warning("No current_day set in SessionState.")
        return (
            "Great — let's get started. To kick things off, could you give me a quick overview "
            "of your background and what drew you to AI engineering?"
        )

    profile      = session.candidate_profile
    day_meta     = data_manager.get_day_metadata(day_num)
    day_title    = day_meta.get("title", f"Day {day_num}") if day_meta else f"Day {day_num}"

    # ── Classify this topic using day NUMBER (not title string) ──────────────
    strong_days  = set(profile.get("completed_days", [])) - set(
        profile.get("skipped_days", []) + profile.get("failed_days", [])
    )
    attempts_by_day = profile.get("attempts_by_day", {})
    # Strong = completed AND <= 2 attempts
    is_strong = (
        day_num in strong_days
        and attempts_by_day.get(day_num, 99) <= 2
    )
    is_weak = (
        day_num in profile.get("skipped_days", [])
        or day_num in profile.get("failed_days", [])
    )
    attempts = attempts_by_day.get(day_num, 0)
    was_skipped = day_num in profile.get("skipped_days", [])
    was_failed  = day_num in profile.get("failed_days", [])

    # Retrieve the day's curriculum content via FAISS for grounding
    try:
        results = data_manager.retrieve_relevant_days(
            query=day_title, top_k=1, preferred_days=[day_num]
        )
        day_content = results[0] if results else (day_meta or {})
    except Exception as exc:
        logger.error("FAISS retrieval failed for day %s: %s", day_num, exc)
        day_content = day_meta or {}

    objectives_str = ", ".join(day_content.get("objectives", [])) or "not specified"
    tools_str      = ", ".join(day_content.get("tools", []))      or "not specified"

    # ── Build rich depth instruction from real candidate data ────────────────
    job_role = profile.get("job_role", "Software Engineer")

    if is_strong:
        depth_instruction = (
            f"DEPTH: ADVANCED — This candidate passed this topic in {attempts} attempt(s), "
            f"demonstrating strong mastery. As a {job_role}, they should handle production-level "
            f"complexity. Ask a design, architecture, or trade-off question that assumes solid "
            f"fundamentals and probes edge cases, scaling concerns, or real-world failure modes. "
            f"Do NOT ask what something is — they know. Ask how they'd design, debug, or choose."
        )
    elif was_skipped:
        depth_instruction = (
            f"DEPTH: FOUNDATIONAL — This candidate skipped this topic entirely in the cohort. "
            f"As a {job_role}, this may be an area they haven't worked with yet. "
            f"Ask a clear, foundational question — what is it, why does it matter, how does it "
            f"work at a basic level. Use an encouraging tone: this is their chance to show what "
            f"they do know, not a test designed to expose a gap."
        )
    elif was_failed:
        depth_instruction = (
            f"DEPTH: FOUNDATIONAL — This candidate attempted this topic {attempts} time(s) "
            f"in the cohort and did not pass. As a {job_role}, they may have struggled here. "
            f"Ask a foundational explanation question — give them a genuine chance to demonstrate "
            f"their current understanding. Encouraging tone. Focus on core concepts, not edge cases."
        )
    else:
        # Completed but took 3+ attempts — medium depth
        depth_instruction = (
            f"DEPTH: INTERMEDIATE — This candidate eventually passed this topic after "
            f"{attempts} attempt(s). They understand the basics but may have gaps in depth. "
            f"Ask a solid mid-level question: conceptual understanding plus one concrete "
            f"application or implementation detail relevant to their role as a {job_role}."
        )

    # ── Build candidate context summary for the LLM ──────────────────────────
    strong_topics  = profile.get("strong_topics", [])
    weak_topics    = profile.get("weak_topics", [])
    skipped_days   = profile.get("skipped_days", [])
    failed_days    = profile.get("failed_days", [])
    signals        = profile.get("signals", {})

    candidate_context = (
        f"Strong areas (passed 1st or 2nd try): {', '.join(strong_topics) if strong_topics else 'none'}\n"
        f"  Weak/struggled areas: {', '.join(weak_topics) if weak_topics else 'none'}\n"
        f"  Skipped cohort days: {skipped_days if skipped_days else 'none'}\n"
        f"  Failed cohort days:  {failed_days if failed_days else 'none'}\n"
        f"  Commit streak: {signals.get('commitDays', '?')} days | "
        f"Missions completed: {signals.get('missionsCompleted', '?')} | "
        f"First-try passes: {signals.get('missionsFirstTry', '?')}"
    )

    # Build recent history string (last 4 turns) for context continuity
    recent = session.history[-4:] if len(session.history) > 4 else session.history
    history_str = (
        "\n".join(f"  {m['role'].upper()}: {m['content']}" for m in recent)
        if recent else "  (This is the opening question — include a brief warm welcome.)"
    )

    user_prompt = f"""\
Candidate profile:
  Name:             {profile.get('name', 'the candidate')}
  Role:             {profile.get('job_role', 'Software Engineer')}
  Experience:       {profile.get('years_experience', '?')} years ({profile.get('experience_level', 'Mid-level')})
  {candidate_context}

Current topic (curriculum Day {day_num} — "{day_title}"):
  Learning objectives: {objectives_str}
  Key tools/concepts:  {tools_str}

{depth_instruction}

Recent conversation:
{history_str}

Generate exactly one interview question tailored to this specific candidate's background, \
role, and performance history. The question must reflect the depth level above. \
Output the question text only — no labels, no preamble, no quotation marks."""

    client = data_manager.get_groq_client()
    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": _INTERVIEWER_SYSTEM},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("LLM question generation failed: %s. Using fallback.", exc)
        fallback = get_fallback_question(day_num, is_strong)
        if fallback:
            return fallback
        tools_list = ", ".join(day_content.get("tools", [])) or "the core tools"
        return (
            f"Let's talk about {day_title}. "
            f"How would you approach building a solution using {tools_list}, "
            f"and what are the key trade-offs you'd need to navigate?"
        )


def generate_follow_up(
    question: str,
    vague_answer: str,
    history: List[Dict[str, str]],
    mode: str = "clarify",
) -> str:
    """
    Generate a natural follow-up question.

    mode="clarify"   — answer was vague/incomplete: ask for concrete detail,
                       a specific example, or a step-by-step walk-through.
    mode="escalate"  — answer was strong but shallow: push to a harder variant
                       of the same topic — a trade-off, edge case, or production
                       concern they haven't addressed yet.

    Hard rule: stay on the same topic. Never introduce a new curriculum day.
    """
    client = data_manager.get_groq_client()

    recent = history[-4:] if len(history) > 4 else history
    history_str = "\n".join(
        f"  {m['role'].upper()}: {m['content']}" for m in recent
    ) if recent else "  (No prior turns.)"

    if mode == "escalate":
        follow_up_instruction = """\
The candidate gave a solid answer. Your job is to escalate difficulty on the SAME topic.
- Acknowledge what they got right briefly (one clause at most), then immediately push deeper.
- Ask about a production edge case, a scaling trade-off, a failure mode, or an architectural
  decision embedded in what they said that they haven't addressed yet.
- DO NOT ask them to repeat or elaborate on what they already explained well.
- Sound intellectually curious and rigorous, not adversarial."""
    else:
        follow_up_instruction = """\
The candidate's answer was vague, too short, or incomplete. Your job is to probe for depth.
- Ask them to be concrete: a specific tool they'd use, a real example, or one step
  of implementation they'd actually take.
- Keep the tone encouraging and collaborative — "That's a start, could you walk me through..."
  works better than a blunt "Explain X."
- Stay anchored to exactly what they said. Do not switch topics."""

    user_prompt = f"""\
{follow_up_instruction}

Original question you asked:
  {question}

Candidate's response:
  {vague_answer}

Recent conversation:
{history_str}

Output only the follow-up question text — no labels, no preamble."""

    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": _INTERVIEWER_SYSTEM},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Follow-up generation failed: %s", exc)
        if mode == "escalate":
            return (
                "That's a solid foundation — now let's push deeper. "
                "Can you walk me through how that would hold up under production load, "
                "or describe a trade-off you'd have to navigate at scale?"
            )
        return (
            "That's a good start — could you give me a concrete example of how you'd "
            "apply that in practice, or walk me through a specific implementation detail?"
        )
