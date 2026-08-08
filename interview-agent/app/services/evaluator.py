import os
from typing import Any, Literal, List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI

# Lazy singleton — instantiated on first use so tests can import without a key.
_client: Optional[OpenAI] = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _client

# Answers shorter than this (stripped) are always treated as vague regardless of LLM verdict.
MIN_ANSWER_LENGTH = 15


class Evaluation(BaseModel):
    technical_accuracy: int = Field(ge=0, le=10, description="Technical accuracy score 0-10")
    depth: int = Field(ge=0, le=10, description="Depth of answer 0-10")
    clarity: int = Field(ge=0, le=10, description="Clarity of answer 0-10")
    is_vague: bool = Field(description="Answer is vague or too short to be useful")
    is_strong: bool = Field(description="Answer is detailed, well-reasoned, and technically accurate")
    is_incomplete: bool = Field(description="Answer misses key concepts or parts of the question")
    strengths: List[str] = Field(description="Concrete strengths demonstrated in the answer")
    missing_points: List[str] = Field(description="Important concepts or details that were missing")
    overall_comment: str = Field(description="One-sentence summary of the answer quality")

    @property
    def is_correct(self) -> bool:
        """Derived: accuracy >= 6 and not incomplete."""
        return self.technical_accuracy >= 6 and not self.is_incomplete

    @property
    def evaluation_notes(self) -> str:
        """Derived: overall_comment used as the human-readable note in qa_records."""
        return self.overall_comment


def evaluate_answer(question: str, answer: str, curriculum_context: Any) -> Evaluation:
    """
    Evaluate the candidate's answer synchronously using GPT-4o structured output.

    A hard min-length guard short-circuits the LLM call for trivially short answers,
    saving tokens and latency.
    """
    # ── Hard min-length guard ─────────────────────────────────────────────────
    if len(answer.strip()) < MIN_ANSWER_LENGTH:
        return Evaluation(
            technical_accuracy=0,
            depth=0,
            clarity=0,
            is_vague=True,
            is_strong=False,
            is_incomplete=True,
            strengths=[],
            missing_points=["The answer was too short to assess — no substantive content provided."],
            overall_comment="Answer was too brief to evaluate meaningfully.",
        )

    # ── Serialise curriculum context ──────────────────────────────────────────
    if isinstance(curriculum_context, dict):
        context_str = (
            f"Day {curriculum_context.get('day', '?')}: "
            f"{curriculum_context.get('title', 'Unknown topic')}\n"
            f"Learning objectives: {', '.join(curriculum_context.get('objectives', []))}\n"
            f"Key tools / concepts: {', '.join(curriculum_context.get('tools', []))}"
        )
    else:
        context_str = str(curriculum_context)

    system_prompt = """\
You are a senior AI engineering interviewer evaluating a candidate's answer during a \
technical interview. Your evaluation feeds directly into the candidate's final feedback \
report, so accuracy and fairness matter.

Evaluation principles:
- Judge the answer against the curriculum context provided — that is the source of truth \
  for what a correct, complete answer looks like.
- Reward genuine understanding: concrete examples, correct use of terminology, awareness \
  of trade-offs, and practical implementation knowledge all indicate depth.
- Penalise vagueness fairly: "it depends" with no elaboration, restating the question, \
  or generic platitudes without specifics should lower scores.
- A strong answer doesn't need to be perfect — it needs to demonstrate that the candidate \
  actually knows this topic, not just that they've heard of it.
- Be calibrated: reserve scores of 9–10 for truly excellent answers that cover edge cases \
  and nuance. Most solid answers sit in the 6–8 range.
- overall_comment: write one honest, constructive sentence as if you were telling a colleague \
  how the candidate did on this question.\
"""

    user_prompt = (
        f"Curriculum context for this question:\n{context_str}\n\n"
        f"Question asked:\n{question}\n\n"
        f"Candidate's answer:\n{answer}"
    )

    response = _get_client().beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        response_format=Evaluation,
    )

    return response.choices[0].message.parsed


def decide_next_action(
    evaluation: Evaluation, session: Any
) -> Literal["follow_up", "new_question", "end"]:
    """
    Decide what to do after evaluating an answer.

    Priority order:
      1. Already on a follow-up  → new_question  (hard cap: never chain follow-ups)
      2. Vague OR incomplete     → follow_up     (always probe once)
      3. Strong + depth >= 8     → new_question  (candidate earned the move)
      4. Strong + depth < 8      → follow_up     (push for more depth)
      5. Default                 → new_question
    """
    if isinstance(session, dict):
        pending = session.get("pending_follow_up", {})
    else:
        pending = getattr(session, "pending_follow_up", {})

    if pending.get("is_pending", False):
        return "new_question"

    if evaluation.is_vague or evaluation.is_incomplete:
        return "follow_up"

    if evaluation.is_strong:
        return "new_question" if evaluation.depth >= 8 else "follow_up"

    return "new_question"


def generate_follow_up(evaluation: Evaluation, question: str, answer: str) -> str:
    """
    Generate a targeted follow-up question based on the evaluation.
    (Retained for completeness — question_generator.generate_follow_up is
    the one used by the dialogue manager in production.)
    """
    missing = ", ".join(evaluation.missing_points) if evaluation.missing_points else "none identified"
    strengths = ", ".join(evaluation.strengths) if evaluation.strengths else "none identified"

    system_prompt = """\
You are a senior technical interviewer. The candidate's last answer was evaluated and \
warrants a follow-up question. Your follow-up should feel like a natural continuation \
of the conversation — warm, precise, and intellectually curious.\
"""

    user_prompt = (
        f"Original question: {question}\n"
        f"Candidate's answer: {answer}\n\n"
        f"Evaluation summary:\n"
        f"  - Vague: {evaluation.is_vague}\n"
        f"  - Incomplete: {evaluation.is_incomplete}\n"
        f"  - Strong: {evaluation.is_strong}\n"
        f"  - Strengths in the answer: {strengths}\n"
        f"  - What was missing: {missing}\n\n"
        "Write one follow-up question (1–2 sentences) that:\n"
        "- If vague/incomplete: asks the candidate to be concrete — give an example, "
        "name a tool, or walk through a specific step.\n"
        "- If strong but shallow: escalates slightly — a trade-off, an edge case, "
        "or a production consideration.\n"
        "Do not introduce a new topic. Output only the question text."
    )

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()
