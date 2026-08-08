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

# Answers shorter than this (stripped) are always treated as vague regardless of LLM verdict
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

    Applies a hard min-length guard before calling the LLM: answers under
    MIN_ANSWER_LENGTH characters are immediately flagged as vague without an API call.
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
            missing_points=["Answer was too short to evaluate."],
            overall_comment="Answer was too short — no substantive content to assess.",
        )

    # ── Serialise curriculum context ──────────────────────────────────────────
    if isinstance(curriculum_context, dict):
        context_str = (
            f"Day {curriculum_context.get('day', '?')}: {curriculum_context.get('title', '')}\n"
            f"Objectives: {', '.join(curriculum_context.get('objectives', []))}\n"
            f"Tools: {', '.join(curriculum_context.get('tools', []))}"
        )
    else:
        context_str = str(curriculum_context)

    system_prompt = (
        "You are an expert technical interviewer evaluating a candidate's answer "
        "during an AI engineering interview.\n\n"
        f"Question asked: {question}\n"
        f"Curriculum context:\n{context_str}\n\n"
        "Guidelines:\n"
        "- Be fair but rigorous.\n"
        "- Short or generic answers → mark as vague/incomplete.\n"
        "- Answers that show real understanding, examples, or trade-offs → mark as strong.\n"
        "- Only use the provided curriculum context to judge correctness."
    )

    response = _get_client().beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Candidate's answer: {answer}"},
        ],
        response_format=Evaluation,
    )

    return response.choices[0].message.parsed


def decide_next_action(
    evaluation: Evaluation, session: Any
) -> Literal["follow_up", "new_question", "end"]:
    """
    Decide what to do after evaluating an answer.

    Rules (in priority order):
      1. Already answering a follow-up → always move to new_question (no chaining).
      2. Answer is vague OR incomplete → always ask a follow-up.
      3. Answer is strong with depth >= 8 → move to new_question (earned it).
      4. Answer is strong but depth < 8 → follow_up to probe deeper.
      5. Default → new_question.
    """
    if isinstance(session, dict):
        pending = session.get("pending_follow_up", {})
    else:
        pending = getattr(session, "pending_follow_up", {})

    # Rule 1: hard cap — never chain follow-ups
    if pending.get("is_pending", False):
        return "new_question"

    # Rule 2: vague or incomplete → always probe
    if evaluation.is_vague or evaluation.is_incomplete:
        return "follow_up"

    # Rules 3 & 4: strong answers
    if evaluation.is_strong:
        return "new_question" if evaluation.depth >= 8 else "follow_up"

    # Rule 5: default
    return "new_question"


def generate_follow_up(evaluation: Evaluation, question: str, answer: str) -> str:
    """
    Generate a targeted follow-up question.  Kept for completeness; the dialogue
    manager uses question_generator.generate_follow_up in practice.
    """
    system_prompt = (
        "You are a senior technical interviewer. The candidate gave an answer that "
        "warrants a follow-up.\n\n"
        f"Original Question: {question}\n"
        f"Candidate's Answer: {answer}\n\n"
        "Evaluation context:\n"
        f"- Vague: {evaluation.is_vague}\n"
        f"- Incomplete: {evaluation.is_incomplete}\n"
        f"- Strong: {evaluation.is_strong}\n"
        f"- Strengths: {', '.join(evaluation.strengths) if evaluation.strengths else 'None'}\n"
        f"- Missing points: {', '.join(evaluation.missing_points) if evaluation.missing_points else 'None'}\n\n"
        "Rules:\n"
        "- Vague/incomplete → ask to clarify, elaborate, or give a concrete example.\n"
        "- Strong → escalate slightly (edge cases, trade-offs, improvement ideas).\n"
        "- Keep it concise (1-2 sentences). Do not introduce a new topic.\n"
        "Return ONLY the follow-up question text."
    )

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the follow-up question."},
        ],
    )
    return response.choices[0].message.content.strip()
