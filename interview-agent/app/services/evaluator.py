import json
import logging
from typing import Any, Literal, List, Optional
from pydantic import BaseModel, Field

from app.services import data_manager
from app import config

logger = logging.getLogger(__name__)

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
    Evaluate the candidate's answer using Groq (llama-3.3-70b-versatile).
    Returns a structured Evaluation parsed from the JSON response.
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
- Judge the answer against the curriculum context provided.
- Reward genuine understanding: concrete examples, correct terminology, awareness of trade-offs.
- Penalise vagueness: "it depends" with no elaboration or generic platitudes should lower scores.
- A strong answer demonstrates the candidate knows the topic, not just heard of it.
- Reserve scores of 9-10 for truly excellent answers. Most solid answers sit in the 6-8 range.

You MUST respond with valid JSON only — no markdown, no explanation, no code fences.
Use exactly this structure:
{
  "technical_accuracy": <int 0-10>,
  "depth": <int 0-10>,
  "clarity": <int 0-10>,
  "is_vague": <bool>,
  "is_strong": <bool>,
  "is_incomplete": <bool>,
  "strengths": [<string>, ...],
  "missing_points": [<string>, ...],
  "overall_comment": "<one sentence>"
}"""

    user_prompt = (
        f"Curriculum context for this question:\n{context_str}\n\n"
        f"Question asked:\n{question}\n\n"
        f"Candidate's answer:\n{answer}"
    )

    client = data_manager.get_groq_client()
    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        return Evaluation(**data)
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc)
        # Safe fallback — interview continues even if evaluation errors
        return Evaluation(
            technical_accuracy=5,
            depth=5,
            clarity=5,
            is_vague=False,
            is_strong=False,
            is_incomplete=False,
            strengths=["Provided a response to the question."],
            missing_points=[],
            overall_comment="Evaluation could not be completed; default scores assigned.",
        )


def decide_next_action(
    evaluation: Evaluation, session: Any
) -> Literal["follow_up_clarify", "follow_up_escalate", "new_question", "end"]:
    """
    Decide what to do after evaluating an answer.

    Return values
    ─────────────
    follow_up_clarify   Vague, too short, or missing key concepts
                        → probe for concrete detail / elaboration
    follow_up_escalate  Strong answer, depth < 8
                        → push harder on the same topic (harder variant)
    new_question        Strong + depth >= 8, OR already on a follow-up (hard cap)
                        → move to the next curriculum day
    end                 (reserved for future use — not returned by this function)

    Hard cap: never chain follow-ups. If pending_follow_up.is_pending is True
    the answer is always new_question regardless of quality.
    """
    if isinstance(session, dict):
        pending = session.get("pending_follow_up", {})
    else:
        pending = getattr(session, "pending_follow_up", {})

    # Hard cap — already asked one follow-up, must move on
    if pending.get("is_pending", False):
        return "new_question"

    # Vague, too short, or incomplete → ask for clarification/elaboration
    if evaluation.is_vague or evaluation.is_incomplete:
        return "follow_up_clarify"

    # Strong answer — escalate if depth is shallow, else reward with next topic
    if evaluation.is_strong:
        return "new_question" if evaluation.depth >= 8 else "follow_up_escalate"

    # Average answer (not strong, not vague) → move on
    return "new_question"


def generate_follow_up(evaluation: Evaluation, question: str, answer: str,
                       mode: str = "clarify") -> str:
    """
    Generate a targeted follow-up question based on the evaluation and mode.

    mode="clarify"   — answer was vague/incomplete: probe for concrete detail
    mode="escalate"  — answer was strong but shallow: push to harder territory

    (Retained for completeness — question_generator.generate_follow_up is
    the one used by the dialogue manager in production.)
    """
    missing   = ", ".join(evaluation.missing_points) if evaluation.missing_points else "none identified"
    strengths = ", ".join(evaluation.strengths)       if evaluation.strengths       else "none identified"

    if mode == "escalate":
        follow_up_instruction = (
            "The candidate gave a solid answer. Now escalate: ask a harder question "
            "on the same topic — a production edge case, a trade-off they haven't addressed, "
            "or a deeper architectural decision. DO NOT ask them to repeat or elaborate on "
            "what they already said well. Push them to the next level."
        )
    else:
        follow_up_instruction = (
            "The candidate's answer was vague or incomplete. Ask them to be more concrete: "
            "request a specific example, name a tool they'd actually use, or walk through "
            "one implementation step in detail. Keep the tone encouraging, not interrogative."
        )

    system_prompt = """\
You are a senior technical interviewer. Generate one follow-up question (1-2 sentences). \
Output only the question text — no preamble, no labels."""

    user_prompt = (
        f"Original question: {question}\n"
        f"Candidate's answer: {answer}\n\n"
        f"Evaluation:\n"
        f"  - Vague: {evaluation.is_vague} | Incomplete: {evaluation.is_incomplete} | Strong: {evaluation.is_strong}\n"
        f"  - Depth: {evaluation.depth}/10 | Accuracy: {evaluation.technical_accuracy}/10\n"
        f"  - Strengths: {strengths}\n"
        f"  - Missing: {missing}\n\n"
        f"Instruction: {follow_up_instruction}"
    )

    client = data_manager.get_groq_client()
    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
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
