import json
import logging
from typing import List, Dict, Any

from app.services import data_manager
from app.schemas import Feedback
from app import config

logger = logging.getLogger(__name__)

# ── Validation thresholds ─────────────────────────────────────────────────────
MIN_STRENGTHS = 3
MIN_GAPS      = 2
MIN_NEXT      = 3
MIN_SUMMARY_WORDS = 15   # summary must be at least this many words


def _validate_feedback(data: dict, qa_records: List[Dict[str, Any]]) -> List[str]:
    """
    Return a list of validation failure reasons.
    Empty list = feedback is acceptable.

    Checks:
    - All required arrays are present and meet minimums
    - summary is at least MIN_SUMMARY_WORDS words
    - strengths / gaps / next items reference real curriculum topics or
      contain specific technical terminology (not just generic praise)
    """
    failures = []

    summary = data.get("summary", "")
    if len(summary.split()) < MIN_SUMMARY_WORDS:
        failures.append(f"summary too short ({len(summary.split())} words, need {MIN_SUMMARY_WORDS})")

    strengths = data.get("strengths", [])
    if not isinstance(strengths, list) or len(strengths) < MIN_STRENGTHS:
        failures.append(f"strengths has {len(strengths)} items, need >= {MIN_STRENGTHS}")

    gaps = data.get("gaps", [])
    if not isinstance(gaps, list) or len(gaps) < MIN_GAPS:
        failures.append(f"gaps has {len(gaps)} items, need >= {MIN_GAPS}")

    next_steps = data.get("next", [])
    if not isinstance(next_steps, list) or len(next_steps) < MIN_NEXT:
        failures.append(f"next has {len(next_steps)} items, need >= {MIN_NEXT}")

    # Check for generic filler in strengths — items must be > 5 words
    for i, s in enumerate(strengths):
        if len(str(s).split()) < 5:
            failures.append(f"strengths[{i}] is too generic: '{s}'")

    for i, g in enumerate(gaps):
        if len(str(g).split()) < 5:
            failures.append(f"gaps[{i}] is too generic: '{g}'")

    for i, n in enumerate(next_steps):
        if len(str(n).split()) < 6:
            failures.append(f"next[{i}] is too generic: '{n}'")

    return failures


def _build_system_prompt(
    name: str, role: str, years: int, level: str,
    cohort_summary: str, qa_narrative: str,
) -> str:
    return f"""\
You are a senior AI engineering interviewer writing the final performance review for \
{name} after a structured technical interview. This feedback will be read by the candidate \
and their hiring manager — it MUST be specific to this interview, honest, and actionable.

About {name}:
  Role: {role}
  Experience: {years} years ({level})

Cohort history (31-day AI engineering programme):
{cohort_summary}

Interview Q&A with per-question evaluations:
{qa_narrative}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT REQUIREMENTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You MUST respond with valid JSON only — no markdown, no explanation, no code fences.
Use EXACTLY this structure:
{{
  "summary": "<string>",
  "strengths": ["<string>", "<string>", "<string>"],
  "gaps": ["<string>", "<string>"],
  "next": ["<string>", "<string>", "<string>"]
}}

RULES — read carefully, every rule is enforced:

summary:
  - 2 sentences MINIMUM.
  - Sentence 1: name {name}'s role, their STRONGEST demonstrated topic from the Q&A above.
  - Sentence 2: name their MOST IMPORTANT gap — a real topic from the Q&A or cohort history.
  - FORBIDDEN: "overall a good candidate", "showed strong fundamentals", "great potential"
    — these are generic filler. Be specific about THIS interview.

strengths (3–5 items):
  - Each item MUST name a specific curriculum topic, tool, or concept from the Q&A above.
  - Each item MUST start with an action verb: Articulated, Demonstrated, Explained,
    Applied, Showed command of, Correctly identified, etc.
  - Each item MUST be at least 8 words.
  - Reference the actual question or answer where possible.
  - FORBIDDEN: "Good communication", "Completed the interview", "Strong background"

gaps (2–4 items):
  - Each item MUST name a specific topic, concept, or day from the cohort history or Q&A.
  - Frame as "Did not demonstrate X" or "Struggled to explain Y" — not "Bad at Z."
  - If the candidate skipped or failed days in the cohort, name them explicitly.
  - Each item MUST be at least 8 words.

next (3–4 items):
  - Concrete, prioritised learning actions. Highest-priority gap FIRST.
  - Name a SPECIFIC resource type, concept, or hands-on exercise.
  - GOOD: "Build a RAG pipeline from scratch using LangChain and a FAISS vector store"
  - BAD:  "Study more about RAG" or "Practice coding"
  - Each item MUST be at least 8 words.\
"""


def generate_feedback(profile: Dict[str, Any], qa_records: List[Dict[str, Any]]) -> dict:
    """
    Generate final structured feedback using Groq (llama-3.3-70b-versatile).
    Validates output and retries once if validation fails.

    Returns dict matching Feedback schema: summary, strengths[], gaps[], next[].
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

    # ── Build detailed Q&A narrative ─────────────────────────────────────────
    qa_parts = []
    for i, rec in enumerate(qa_records, start=1):
        acc     = rec.get("technical_accuracy", "?")
        depth   = rec.get("depth", "?")
        note    = rec.get("evaluation_notes", "")
        correct = "CORRECT" if rec.get("is_correct") else "INCOMPLETE/INCORRECT"
        vague   = " [VAGUE ANSWER]" if rec.get("is_vague") else ""
        s_list  = rec.get("strengths", [])
        g_list  = rec.get("missing_points", [])

        qa_parts.append(
            f"Q{i} — Day {rec.get('day','?')}: {rec.get('day_title','Unknown topic')}\n"
            f"  Question asked: {rec.get('question','')}\n"
            f"  Candidate answer: {rec.get('answer','')}\n"
            f"  Result: {correct}{vague} | technical_accuracy={acc}/10, depth={depth}/10\n"
            f"  Evaluator comment: {note}\n"
            f"  What they demonstrated: {', '.join(s_list) if s_list else 'nothing notable'}\n"
            f"  What was missing: {', '.join(g_list) if g_list else 'nothing significant'}"
        )

    qa_narrative = "\n\n".join(qa_parts) if qa_parts else "No Q&A records — interview data unavailable."

    # ── Cohort history summary ────────────────────────────────────────────────
    cohort_lines = [
        f"Completed days:            {completed_days if completed_days else 'none'}",
        f"Skipped days:              {skipped_days if skipped_days else 'none'}",
        f"Failed days:               {failed_days if failed_days else 'none'}",
        f"Strong topics (≤2 tries):  {', '.join(strong_topics) if strong_topics else 'none'}",
        f"Weak/struggled topics:     {', '.join(weak_topics) if weak_topics else 'none'}",
    ]
    cohort_summary = "\n".join(cohort_lines)

    system_prompt = _build_system_prompt(name, role, years, level, cohort_summary, qa_narrative)
    client = data_manager.get_groq_client()

    def _call_llm(extra_instruction: str = "") -> dict:
        user_msg = "Generate the final structured feedback now."
        if extra_instruction:
            user_msg += f"\n\nIMPORTANT correction needed: {extra_instruction}"
        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)

    # ── First attempt ─────────────────────────────────────────────────────────
    try:
        data = _call_llm()
        failures = _validate_feedback(data, qa_records)

        if failures:
            logger.warning(
                "Feedback validation failed (%d issues): %s — retrying.",
                len(failures), "; ".join(failures),
            )
            # ── Retry with explicit correction instruction ─────────────────
            correction = (
                f"Your previous response had these problems: {'; '.join(failures)}. "
                "Fix ALL of them. Every strength/gap/next item must be specific to the "
                "curriculum topics and Q&A above, at least 8 words, and reference real "
                "technical concepts from the interview."
            )
            data = _call_llm(extra_instruction=correction)
            failures2 = _validate_feedback(data, qa_records)
            if failures2:
                logger.error(
                    "Feedback still invalid after retry (%s). Using best-effort result.",
                    "; ".join(failures2),
                )

        return Feedback(**data).model_dump()

    except Exception as exc:
        logger.error("Feedback generation failed: %s", exc)
        # Graceful fallback — always returns spec-compliant structure
        # Build it from available qa_records so it's as specific as possible
        topic_names = [r.get("day_title", "Unknown") for r in qa_records]
        correct_topics = [
            r.get("day_title", "Unknown")
            for r in qa_records if r.get("is_correct")
        ]
        weak_qa = [
            r.get("day_title", "Unknown")
            for r in qa_records if not r.get("is_correct") or r.get("is_vague")
        ]

        return Feedback(
            summary=(
                f"{name} completed a {len(qa_records)}-question interview covering "
                f"{', '.join(topic_names) if topic_names else 'multiple curriculum topics'}. "
                f"Automated feedback generation encountered an error; a manual review is recommended."
            ),
            strengths=(
                [f"Completed interview questions on {t}" for t in correct_topics[:3]]
                or ["Completed the full interview session without technical errors."]
            ),
            gaps=(
                [f"Did not demonstrate strong understanding of {t}" for t in weak_qa[:3]]
                or ["Detailed gap analysis unavailable due to a generation error."]
            ),
            next=[
                f"Review and practice the topics covered: {', '.join(topic_names[:4])}",
                "Build a small end-to-end project combining the weakest topics from this session.",
                "Re-attempt any cohort missions that were skipped or failed.",
            ],
        ).model_dump()
