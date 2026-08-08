import os
import logging
from typing import List, Dict, Any

from openai import OpenAI
from app.schemas import Feedback

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def generate_feedback(profile: Dict[str, Any], qa_records: List[Dict[str, Any]]) -> dict:
    """
    Generate final structured feedback from the candidate profile and Q&A records.

    Args:
        profile:    The structured candidate profile produced by data_manager.get_candidate_profile().
                    Keys: id, name, job_role, experience_level, years_experience,
                          completed_days, skipped_days, failed_days,
                          strong_topics, weak_topics, signals.
        qa_records: List of Q&A records accumulated during the interview.
                    Each record has: day, day_title, question, answer,
                                     is_vague, is_correct, evaluation_notes,
                                     technical_accuracy, depth, strengths, missing_points.

    Returns:
        A dict matching the Feedback schema: summary, strengths[], gaps[], next[].
    """
    # ── Build Q&A summary ──────────────────────────────────────────────────────
    qa_summary_parts = []
    for idx, record in enumerate(qa_records, start=1):
        accuracy = record.get("technical_accuracy", "N/A")
        depth = record.get("depth", "N/A")
        strengths = record.get("strengths", [])
        gaps = record.get("missing_points", [])
        note = record.get("evaluation_notes", "")

        qa_summary_parts.append(
            f"Q{idx} (Day {record.get('day', '?')} – {record.get('day_title', '')}): "
            f"{record.get('question', '')}\n"
            f"Answer: {record.get('answer', '')}\n"
            f"Eval: Accuracy={accuracy}/10, Depth={depth}/10. {note}\n"
            f"Strengths: {strengths}\n"
            f"Gaps: {gaps}"
        )

    qa_summary = "\n\n".join(qa_summary_parts) if qa_summary_parts else "No Q&A records available."

    # ── Build performance summary from profile ────────────────────────────────
    completed = profile.get("completed_days", [])
    skipped = profile.get("skipped_days", [])
    failed = profile.get("failed_days", [])
    strong_topics = profile.get("strong_topics", [])
    weak_topics = profile.get("weak_topics", [])

    performance_lines = [
        f"- Completed days: {completed}",
        f"- Skipped days:   {skipped}",
        f"- Failed days:    {failed}",
        f"- Strong topics:  {strong_topics}",
        f"- Weak topics:    {weak_topics}",
    ]
    performance_str = "\n".join(performance_lines)

    # ── Compose system prompt ─────────────────────────────────────────────────
    system_prompt = (
        "You are a senior technical interviewer writing final structured feedback "
        "after an interview with a candidate who completed a 31-day AI engineering cohort.\n\n"
        "You will receive:\n"
        "- The candidate's profile (mission history, job role, experience level)\n"
        "- The full list of questions, answers, and per-answer evaluations\n\n"
        "Produce feedback that is balanced, specific, constructive, and professional.\n\n"
        "Guidelines:\n"
        "- Reference concrete topics from the curriculum when possible.\n"
        "- strengths: highlight what the candidate demonstrated well (one clear sentence each).\n"
        "- gaps: focus on areas that were weak, skipped, or poorly explained.\n"
        "- next: practical, actionable next steps the candidate should take.\n"
        "- Keep every bullet concise (one sentence each).\n"
        "- Tone: professional, encouraging, and honest.\n\n"
        "---\n"
        f"Candidate Profile:\n"
        f"Name: {profile.get('name', 'Unknown')}\n"
        f"Role: {profile.get('job_role', 'Unknown')}\n"
        f"Experience: {profile.get('years_experience', 0)} years "
        f"({profile.get('experience_level', 'Unknown')})\n\n"
        f"Cohort Performance:\n{performance_str}\n\n"
        f"Interview Q&A Records:\n{qa_summary}"
    )

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate the final structured feedback."},
            ],
            response_format=Feedback,
        )
        return response.choices[0].message.parsed.model_dump()

    except Exception as e:
        logger.error(f"Failed to generate feedback via GPT-4o: {e}")
        # Graceful fallback so the interview still completes
        return Feedback(
            summary="The interview has been completed. Detailed feedback could not be generated at this time.",
            strengths=["Completed the interview session."],
            gaps=["Detailed analysis unavailable due to a generation error."],
            next=["Review the AI engineering curriculum topics covered during this interview."],
        ).model_dump()
