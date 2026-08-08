import os
from typing import Any, Literal, List
from pydantic import BaseModel, Field
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


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
        """Derived: answer is considered correct when accuracy >= 6 and not incomplete."""
        return self.technical_accuracy >= 6 and not self.is_incomplete

    @property
    def evaluation_notes(self) -> str:
        """Derived: human-readable evaluation note for qa_record storage."""
        return self.overall_comment


def evaluate_answer(question: str, answer: str, curriculum_context: Any) -> Evaluation:
    """
    Evaluate the candidate's answer synchronously using GPT-4o structured output.

    curriculum_context may be a dict (day metadata) or a plain string.
    """
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

    response = client.beta.chat.completions.parse(
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
    Decide whether to ask a follow-up, move to a new question, or end the interview.
    Limits to a maximum of 1 follow-up per main question.
    """
    if isinstance(session, dict):
        pending = session.get("pending_follow_up", {})
        question_count = session.get("question_count", 0)
    else:
        pending = getattr(session, "pending_follow_up", {})
        question_count = getattr(session, "question_count", 0)

    # Use "is_pending" — the key used throughout the rest of the codebase
    is_answering_follow_up = pending.get("is_pending", False)

    if is_answering_follow_up:
        # Already on a follow-up: never chain another one
        return "new_question"

    if evaluation.is_vague or evaluation.is_incomplete:
        return "follow_up"

    if evaluation.is_strong:
        # Perfect depth → move on; otherwise probe a bit deeper
        if evaluation.depth >= 9:
            return "new_question"
        return "follow_up"

    return "new_question"


def generate_follow_up(evaluation: Evaluation, question: str, answer: str) -> str:
    """
    Generate a targeted follow-up question based on the evaluation result.
    (This version is kept for completeness; question_generator.generate_follow_up
    is the one currently called by the dialogue manager.)
    """
    system_prompt = (
        "You are a senior technical interviewer. The candidate just gave an answer "
        "that warrants a follow-up.\n\n"
        f"Original Question: {question}\n"
        f"Candidate's Answer: {answer}\n\n"
        f"Evaluation context:\n"
        f"- Vague: {evaluation.is_vague}\n"
        f"- Incomplete: {evaluation.is_incomplete}\n"
        f"- Strong: {evaluation.is_strong}\n"
        f"- Strengths: {', '.join(evaluation.strengths) if evaluation.strengths else 'None'}\n"
        f"- Missing points: {', '.join(evaluation.missing_points) if evaluation.missing_points else 'None'}\n\n"
        "Rules:\n"
        "- Vague/incomplete → ask them to clarify, elaborate, or give a concrete example.\n"
        "- Strong → escalate slightly (edge cases, trade-offs, improvement ideas).\n"
        "- Keep the follow-up concise (1-2 sentences). Do not introduce a new topic.\n"
        "Return ONLY the follow-up question text."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the follow-up question."},
        ],
    )

    return response.choices[0].message.content.strip()
