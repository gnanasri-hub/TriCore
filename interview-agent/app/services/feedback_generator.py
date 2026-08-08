import json
import logging
from typing import List, Dict, Any

from app.services import data_manager
from app.schemas import Feedback
from app import config

logger = logging.getLogger(__name__)


def generate_feedback(profile: Dict[str, Any], qa_records: List[Dict[str, Any]]) -> dict:
    """
    Generate final structured feedback using Groq (llama-3.3-70b-versatile).

    Args:
        profile:    Structured profile from data_manager.get_candidate_profile().
        qa_records: Flat Q&A records accumulated during the interview.

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

    # ── Build per-question narrative ──────────────────────────────────────────
    qa_parts = []
    for i, rec in enumerate(qa_records, start=1):
        acc     = rec.get("technical_accuracy", "?")
        depth   = rec.get("depth", "?")
        note    = rec.get("evaluation_notes", "")
        correct = "correct" if rec.get("is_correct") else "incomplete/incorrect"
        vague   = " (vague)" if rec.get("is_vague") else ""
        s_list  = rec.get("strengths", [])
        g_list  = rec.get("missing_points", [])

        qa_parts.append(
            f"Q{i} - Day {rec.get('day','?')} ({rec.get('day_title','Unknown')})\n"
            f"  Question: {rec.get('question','')}\n"
            f"  Answer: {rec.get('answer','')}\n"
            f"  Result: {correct}{vague} | accuracy {acc}/10, depth {depth}/10\n"
            f"  Comment: {note}\n"
            f"  Demonstrated: {', '.join(s_list) if s_list else 'nothing notable'}\n"
            f"  Missed: {', '.join(g_list) if g_list else 'nothing significant'}"
        )

    qa_narrative = "\n\n".join(qa_parts) if qa_parts else "No interview questions on record."

    cohort_lines = [
        f"Completed curriculum days: {completed_days}",
        f"Skipped days: {skipped_days}" if skipped_days else "No skipped days.",
        f"Failed days: {failed_days}"   if failed_days  else "No failed days.",
        f"Strong topics (first-try): {strong_topics}" if strong_topics else "No first-try passes.",
        f"Weak/struggled topics: {weak_topics}"       if weak_topics  else "No weak topics.",
    ]
    cohort_summary = "\n".join(cohort_lines)

    system_prompt = f"""\
You are a senior AI engineering interviewer writing the final performance review for \
{name} after a structured technical interview. This feedback will be read by the candidate \
and their hiring manager — it must be specific, honest, and actionable.

About {name}:
  Role: {role}
  Experience: {years} years ({level})

Cohort history (31-day AI engineering programme):
{cohort_summary}

Interview Q&A:
{qa_narrative}

You MUST respond with valid JSON only — no markdown, no explanation, no code fences.
Use exactly this structure:
{{
  "summary": "<1-2 sentence candid overall assessment — mention role, strongest area, main gap>",
  "strengths": ["<action-verb bullet — specific skill/topic demonstrated>", ...],
  "gaps": ["<specific topic or concept that was weak, skipped, or missing>", ...],
  "next": ["<concrete prioritised learning action — specific, not vague>", ...]
}}

Rules:
- summary: 1-2 sentences, specific, no filler like "overall a good candidate"
- strengths: 3-5 items, start each with action verb (Articulated, Demonstrated, Showed...)
- gaps: 2-4 items, frame as "Did not demonstrate X" not "Bad at X"
- next: 3-4 items, specific resources or exercises, highest-priority gap first
- Tone: professional, encouraging, specific\
"""

    client = data_manager.get_groq_client()
    try:
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": "Generate the final structured feedback now."},
            ],
            temperature=0.5,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        return Feedback(**data).model_dump()

    except Exception as exc:
        logger.error("Feedback generation failed: %s", exc)
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
