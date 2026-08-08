import os
import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI
from app.schemas import Feedback

logger = logging.getLogger(__name__)

# Lazy singleton — instantiated on first use so tests can import without a key.
_client: Optional[OpenAI] = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _client


def generate_feedback(profile: Dict[str, Any], qa_records: List[Dict[str, Any]]) -> dict:
    """
    Generate final structured feedback that is specific to this candidate's
    mission history, interview performance, and role.

    Args:
        profile:    Structured profile from data_manager.get_candidate_profile().
        qa_records: Flat Q&A records accumulated during the interview, each containing
                    day, day_title, question, answer, is_vague, is_correct,
                    evaluation_notes, technical_accuracy, depth, strengths, missing_points.

    Returns:
        Dict matching the Feedback schema: summary, strengths[], gaps[], next[].
    """
    name           = profile.get("name", "the candidate")
    role           = profile.get("job_role", "Unknown role")
    years          = profile.get("years_experience", 0)
    level          = profile.get("experience_level", "Mid-level")
    strong_topics  = profile.get("strong_topics", [])
    weak_topics    = profile.get("weak_topics", [])
    skipped_days   = profile.get("skipped_days", [])
    failed_days    = profile.get("failed_days", [])
    completed_days = profile.get("completed_days", [])

    # ── Build a rich per-question narrative ───────────────────────────────────
    qa_narrative_parts = []
    for i, rec in enumerate(qa_records, start=1):
        acc     = rec.get("technical_accuracy", "?")
        depth   = rec.get("depth", "?")
        note    = rec.get("evaluation_notes", "")
        correct = "✓ correct" if rec.get("is_correct") else "✗ incomplete/incorrect"
        vague   = " (answer was vague)" if rec.get("is_vague") else ""
        s_list  = rec.get("strengths", [])
        g_list  = rec.get("missing_points", [])

        qa_narrative_parts.append(
            f"Q{i} — Day {rec.get('day', '?')} ({rec.get('day_title', 'Unknown topic')})\n"
            f"  Question: {rec.get('question', '')}\n"
            f"  Answer:   {rec.get('answer', '')}\n"
            f"  Result:   {correct}{vague} | accuracy {acc}/10, depth {depth}/10\n"
            f"  Comment:  {note}\n"
            f"  Demonstrated: {', '.join(s_list) if s_list else 'nothing notable'}\n"
            f"  Missed:       {', '.join(g_list) if g_list else 'nothing significant'}"
        )

    qa_narrative = "\n\n".join(qa_narrative_parts) if qa_narrative_parts else "No interview questions on record."

    # ── Cohort history summary ────────────────────────────────────────────────
    cohort_lines = [
        f"Completed curriculum days: {completed_days}",
        f"Skipped days:             {skipped_days}" if skipped_days else "No skipped days.",
        f"Failed days:              {failed_days}"   if failed_days  else "No failed days.",
        f"Strong topics (passed first-try): {strong_topics}" if strong_topics else "No first-try passes recorded.",
        f"Weak/struggled topics:    {weak_topics}"   if weak_topics  else "No weak topics recorded.",
    ]
    cohort_summary = "\n".join(cohort_lines)

    # ── System prompt ─────────────────────────────────────────────────────────
    system_prompt = f"""\
You are a senior AI engineering interviewer writing the final performance review for \
{name} after a structured technical interview. This feedback will be read by the candidate \
and their hiring manager, so it must be specific, honest, and actionable.

About {name}:
  Role:       {role}
  Experience: {years} years ({level})

Their cohort history (31-day AI engineering programme):
{cohort_summary}

Interview Q&A with per-question evaluations:
{qa_narrative}

Your task is to produce four fields:

summary (1–2 sentences):
  A candid, specific opening statement about how {name} performed overall. \
  Mention their role, their strongest demonstrated area, and the most important gap. \
  Do not use filler phrases like "overall a good candidate."

strengths (3–5 bullet points):
  Each bullet must name a specific topic or skill {name} demonstrated well, \
  ideally referencing a question or answer from the interview. \
  Start each with an action verb (e.g. "Articulated...", "Demonstrated...", "Showed clear command of...").

gaps (2–4 bullet points):
  Each bullet must name a specific topic or concept that was weak, skipped, or missing. \
  Reference the cohort history (skipped/failed days) or a specific weak answer where relevant. \
  Be honest but constructive — frame as "Did not demonstrate X" rather than "Bad at X."

next (3–4 bullet points):
  Concrete, prioritised learning actions. Each should name a specific resource type, \
  concept, or practice exercise. Start with the highest-priority gap. \
  Avoid vague advice like "study more" — be specific: \
  "Implement a RAG pipeline with metadata filtering from scratch" is good; \
  "Learn about RAG" is not.

Tone: professional, encouraging, and specific. Write as if you respect this candidate \
and want them to succeed.\
"""

    try:
        response = _get_client().beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": "Generate the final structured feedback now."},
            ],
            response_format=Feedback,
        )
        return response.choices[0].message.parsed.model_dump()

    except Exception as exc:
        logger.error("Feedback generation failed: %s", exc)
        # Graceful fallback — interview must still complete even if feedback LLM call fails
        return Feedback(
            summary=(
                f"The interview with {name} has been completed. "
                "Detailed AI-generated feedback could not be produced at this time."
            ),
            strengths=["Completed the full interview session."],
            gaps=["Detailed topic-by-topic analysis is unavailable due to a generation error."],
            next=[
                "Review the curriculum days covered during this interview.",
                "Revisit any topics that felt uncertain and build a small project around each one.",
            ],
        ).model_dump()
