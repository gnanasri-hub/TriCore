import logging
from typing import Dict, Any, List, Optional

from app import session_store
from app.schemas import InterviewResponse, Feedback, SessionState
from app.services import data_manager, evaluator, question_generator, feedback_generator

logger = logging.getLogger(__name__)

# ── Ending criteria ────────────────────────────────────────────────────────────
MIN_QUESTIONS = 8   # minimum total questions asked (including follow-ups) before ending
MIN_DAYS = 4        # minimum distinct curriculum days covered before ending


# ── Session helpers ────────────────────────────────────────────────────────────

def _load_state(session_id: str) -> Optional[SessionState]:
    """Return a SessionState for the given session_id, or None if not found."""
    raw = session_store.get_session(session_id)
    if raw is None:
        return None
    return SessionState(**raw)


def _save_state(session_id: str, state: SessionState) -> None:
    session_store.create_or_update_session(session_id, state.model_dump())


# ── Topic selection ────────────────────────────────────────────────────────────

def _select_next_day(
    candidate_profile: Dict[str, Any],
    covered_days: List[int],
    current_day: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Pick the next curriculum day using a strict four-tier priority:

      1. Skipped or failed days not yet covered  ← guaranteed probing
      2. Job-role-relevant days via FAISS semantic search
      3. Strong-topic days (completed in ≤ 2 attempts) not yet covered
      4. Any remaining uncovered day

    The current_day is always excluded from selection so the same topic
    is never repeated back-to-back.
    """
    all_days = data_manager.get_all_days_metadata()
    if not all_days:
        logger.warning("No curriculum days metadata available.")
        return None

    # Build exclusion set: already covered + the day we just finished
    excluded = set(covered_days)
    if current_day is not None:
        excluded.add(current_day)

    # ── Tier 1: probe skipped and failed days first ───────────────────────────
    weak_nums = set(
        candidate_profile.get("skipped_days", [])
        + candidate_profile.get("failed_days", [])
    )
    available_weak = [d for d in all_days if d["day"] in weak_nums and d["day"] not in excluded]
    if available_weak:
        logger.debug("Tier-1 (weak/skipped) day selected: %s", available_weak[0]["day"])
        return available_weak[0]

    # ── Tier 2: job-role semantic match ──────────────────────────────────────
    job_role = candidate_profile.get("job_role", "")
    if job_role:
        relevant = data_manager.retrieve_relevant_days(job_role, top_k=10)
        available_relevant = [d for d in relevant if d["day"] not in excluded]
        if available_relevant:
            day_num = available_relevant[0]["day"]
            meta = data_manager.get_day_metadata(day_num)
            logger.debug("Tier-2 (job-role) day selected: %s", day_num)
            return meta

    # ── Tier 3: strong topics (probe depth) ──────────────────────────────────
    completed_set = set(candidate_profile.get("completed_days", []))
    strong_nums = completed_set - weak_nums
    available_strong = [d for d in all_days if d["day"] in strong_nums and d["day"] not in excluded]
    if available_strong:
        logger.debug("Tier-3 (strong topics) day selected: %s", available_strong[0]["day"])
        return available_strong[0]

    # ── Tier 4: fallback ──────────────────────────────────────────────────────
    available_fallback = [d for d in all_days if d["day"] not in excluded]
    if available_fallback:
        logger.debug("Tier-4 (fallback) day selected: %s", available_fallback[0]["day"])
        return available_fallback[0]

    return None


# ── Interview lifecycle ────────────────────────────────────────────────────────

def start_interview(session_id: str, candidate_data: Dict[str, Any]) -> str:
    """
    Initialise a new session: profile the candidate, select the first topic,
    generate the opening question, persist state, and return the reply string.

    Raises ValueError if a session with session_id already exists.
    """
    if session_store.get_session(session_id) is not None:
        raise ValueError(f"Session '{session_id}' already exists.")

    # 1. Build structured profile
    profile = data_manager.get_candidate_profile(candidate_data)

    # 2. Select first curriculum day (pass empty covered list + no current day)
    first_day_meta = _select_next_day(profile, covered_days=[], current_day=None)
    if not first_day_meta:
        raise ValueError("No curriculum day available to start the interview.")

    day_num = first_day_meta["day"]

    # 3. Initialise SessionState
    state = SessionState(
        session_id=session_id,
        candidate_profile=profile,
        history=[],
        qa_records=[],
        covered_days=[day_num],
        current_day=day_num,
        question_count=0,           # incremented after generating first question
        pending_follow_up={
            "is_pending": False,
            "follow_up_question": "",
            "original_question": "",
            "vague_answer": "",
        },
        interview_stage="INTERVIEWING",
    )

    # 4. Generate opening question
    opening = question_generator.generate_question(state)
    state.history.append({"role": "assistant", "content": opening})
    state.question_count += 1

    # 5. Persist and return
    _save_state(session_id, state)
    return opening


def should_end(state: SessionState) -> bool:
    """
    End ONLY when BOTH hard minimums are satisfied:
      - At least MIN_QUESTIONS total questions asked (includes follow-ups)
      - At least MIN_DAYS distinct curriculum days covered

    Both conditions must be true simultaneously. This is the single source of
    truth for ending — no other code path may end the interview without calling
    this guard first.
    """
    questions_ok = state.question_count >= MIN_QUESTIONS
    days_ok      = len(set(state.covered_days)) >= MIN_DAYS
    return questions_ok and days_ok


def _build_qa_record(
    day_num: int,
    day_meta: Optional[Dict[str, Any]],
    question: str,
    answer: str,
    eval_result: evaluator.Evaluation,
) -> Dict[str, Any]:
    """
    Build a flat Q&A record consumed by feedback_generator.generate_feedback.
    Stores both derived flags and raw evaluation scores.
    """
    return {
        "day": day_num,
        "day_title": day_meta.get("title", "") if day_meta else "",
        "question": question,
        "answer": answer,
        # Derived flags
        "is_vague": eval_result.is_vague,
        "is_correct": eval_result.is_correct,
        "evaluation_notes": eval_result.evaluation_notes,
        # Raw scores for richer feedback summaries
        "technical_accuracy": eval_result.technical_accuracy,
        "depth": eval_result.depth,
        "strengths": eval_result.strengths,
        "missing_points": eval_result.missing_points,
    }


def _end_interview(
    session_id: str,
    state: SessionState,
    closing_line: str,
) -> InterviewResponse:
    """Generate feedback, mark session completed, persist, return final response."""
    fb = feedback_generator.generate_feedback(state.candidate_profile, state.qa_records)
    state.interview_stage = "COMPLETED"
    _save_state(session_id, state)
    return InterviewResponse(
        reply=closing_line,
        done=True,
        feedback=Feedback(**fb),
    )


def process_message(session_id: str, message: str) -> InterviewResponse:
    """
    Handle one conversation turn.

    Flow:
      1. Load and validate session state.
      2. Evaluate the candidate's answer against the last asked question.
      3. decide_next_action → follow_up | new_question | end
         - follow_up  → generate follow-up, return done=False
         - end / thresholds met → generate feedback, return done=True
         - new_question → select next day, generate question, return done=False

    Raises:
        KeyError  – session_id not found in store
        ValueError – session is already completed
    """
    state = _load_state(session_id)
    if state is None:
        raise KeyError(f"Session '{session_id}' not found.")
    if state.interview_stage == "COMPLETED":
        raise ValueError(f"Session '{session_id}' is already completed.")

    profile = state.candidate_profile
    current_day = state.current_day
    current_day_meta = data_manager.get_day_metadata(current_day) if current_day else None
    pending = state.pending_follow_up

    # ── Identify the question that prompted this answer ───────────────────────
    if pending.get("is_pending"):
        last_question = pending["follow_up_question"]
    else:
        last_question = next(
            (m["content"] for m in reversed(state.history) if m["role"] == "assistant"),
            "",
        )

    # ── 1. Evaluate ───────────────────────────────────────────────────────────
    eval_result = evaluator.evaluate_answer(
        question=last_question,
        answer=message,
        curriculum_context=current_day_meta or {},
    )
    state.history.append({"role": "user", "content": message})

    # ── 2. Decide ─────────────────────────────────────────────────────────────
    action = evaluator.decide_next_action(eval_result, state)

    # ── 3a. Follow-up ─────────────────────────────────────────────────────────
    if action == "follow_up":
        logger.info(
            "Session %s: follow-up triggered on day %s (vague=%s incomplete=%s strong=%s depth=%d)",
            session_id, current_day,
            eval_result.is_vague, eval_result.is_incomplete,
            eval_result.is_strong, eval_result.depth,
        )
        follow_up_text = question_generator.generate_follow_up(
            last_question, message, state.history
        )
        state.pending_follow_up = {
            "is_pending": True,
            "follow_up_question": follow_up_text,
            "original_question": last_question,
            "vague_answer": message,
        }
        state.history.append({"role": "assistant", "content": follow_up_text})
        state.question_count += 1
        _save_state(session_id, state)
        return InterviewResponse(reply=follow_up_text, done=False)

    # ── Commit Q&A record (shared by new_question and end paths) ─────────────
    if pending.get("is_pending"):
        combined_answer = (
            f"Initial: {pending['vague_answer']} | Follow-up: {message}"
        )
        qa_rec = _build_qa_record(
            current_day, current_day_meta,
            pending["original_question"], combined_answer, eval_result,
        )
        # Reset pending follow-up
        state.pending_follow_up = {
            "is_pending": False,
            "follow_up_question": "",
            "original_question": "",
            "vague_answer": "",
        }
    else:
        qa_rec = _build_qa_record(
            current_day, current_day_meta,
            last_question, message, eval_result,
        )

    state.qa_records.append(qa_rec)

    # ── 3b. End interview — only if BOTH hard minimums are met ──────────────
    if should_end(state):
        logger.info(
            "Session %s ending: question_count=%d covered_days=%d",
            session_id, state.question_count, len(set(state.covered_days)),
        )
        return _end_interview(
            session_id, state,
            "Thank you — that wraps up our interview. I'll share your feedback below.",
        )

    # ── 3c. Next question ─────────────────────────────────────────────────────
    next_day_meta = _select_next_day(profile, state.covered_days, state.current_day)
    if next_day_meta is None:
        # No uncovered days left — but we still must respect the hard minimums.
        # Re-open already-covered days (excluding current) so we can keep asking.
        logger.info(
            "Session %s: all days exhausted (q=%d days=%d) — recycling covered days.",
            session_id, state.question_count, len(set(state.covered_days)),
        )
        all_days = data_manager.get_all_days_metadata()
        # Pick any day that is not the current one
        recycled = [d for d in all_days if d["day"] != state.current_day]
        next_day_meta = recycled[0] if recycled else None

    if next_day_meta is None:
        # Truly nothing left (single-day curriculum edge case) — end regardless.
        logger.warning("Session %s: no days available at all, ending.", session_id)
        return _end_interview(
            session_id, state,
            "We've covered everything on our agenda. Let me share your feedback.",
        )

    next_day_num = next_day_meta["day"]
    state.covered_days.append(next_day_num)
    state.current_day = next_day_num

    next_question = question_generator.generate_question(state)
    state.history.append({"role": "assistant", "content": next_question})
    state.question_count += 1

    _save_state(session_id, state)
    return InterviewResponse(reply=next_question, done=False)
