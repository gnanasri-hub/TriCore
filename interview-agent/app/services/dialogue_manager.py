import logging
from typing import Dict, Any, List, Optional

from app import session_store
from app.schemas import InterviewResponse, Feedback, SessionState
from app.services import data_manager, evaluator, question_generator, feedback_generator

logger = logging.getLogger(__name__)

# ── Ending criteria ────────────────────────────────────────────────────────────
MIN_QUESTIONS = 8
MIN_DAYS = 4

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
    candidate_profile: Dict[str, Any], covered_days: List[int]
) -> Optional[Dict[str, Any]]:
    """
    Pick the next curriculum day using a four-tier priority:
      1. Skipped or failed days not yet covered.
      2. Job-role-relevant days via FAISS semantic search.
      3. Strong-topic days (completed in ≤ 2 attempts) not yet covered.
      4. Any remaining uncovered day.
    """
    all_days = data_manager.get_all_days_metadata()
    if not all_days:
        logger.warning("No curriculum days metadata available.")
        return None

    covered_set = set(covered_days)

    # 1. Probe weak/skipped days first
    weak_nums = set(
        candidate_profile.get("skipped_days", [])
        + candidate_profile.get("failed_days", [])
    )
    available_weak = [d for d in all_days if d["day"] in weak_nums and d["day"] not in covered_set]
    if available_weak:
        return available_weak[0]

    # 2. Job-role semantic match
    job_role = candidate_profile.get("job_role", "")
    if job_role:
        relevant = data_manager.retrieve_relevant_days(job_role, top_k=10)
        available_relevant = [d for d in relevant if d["day"] not in covered_set]
        if available_relevant:
            day_num = available_relevant[0]["day"]
            return data_manager.get_day_metadata(day_num)

    # 3. Strong topics
    completed_set = set(candidate_profile.get("completed_days", []))
    strong_nums = completed_set - weak_nums
    available_strong = [d for d in all_days if d["day"] in strong_nums and d["day"] not in covered_set]
    if available_strong:
        return available_strong[0]

    # 4. Fallback: any uncovered day
    available_fallback = [d for d in all_days if d["day"] not in covered_set]
    if available_fallback:
        return available_fallback[0]

    return None


# ── Interview lifecycle ────────────────────────────────────────────────────────

def start_interview(session_id: str, candidate_data: Dict[str, Any]) -> str:
    """
    Initialise a new session: profile the candidate, select the first topic,
    generate the welcome + opening question, persist state and return the reply.

    Raises ValueError if called on a session that already exists.
    """
    if session_store.get_session(session_id) is not None:
        raise ValueError(f"Session '{session_id}' already exists.")

    # 1. Build structured profile
    profile = data_manager.get_candidate_profile(candidate_data)

    # 2. Select first curriculum day
    first_day_meta = _select_next_day(profile, [])
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
        question_count=0,           # incremented by generate_question below
        pending_follow_up={
            "is_pending": False,
            "follow_up_question": "",
            "original_question": "",
            "vague_answer": "",
        },
        interview_stage="INTERVIEWING",
    )

    # 4. Generate opening question (includes welcome preamble from GPT)
    opening = question_generator.generate_question(state)
    state.history.append({"role": "assistant", "content": opening})
    state.question_count += 1

    # 5. Persist and return
    _save_state(session_id, state)
    return opening


def should_end(state: SessionState) -> bool:
    """
    End the interview once both minimum thresholds are met:
      - At least MIN_QUESTIONS questions have been asked.
      - At least MIN_DAYS distinct curriculum days have been covered.
    """
    return state.question_count >= MIN_QUESTIONS and len(state.covered_days) >= MIN_DAYS


def _build_qa_record(
    day_num: int,
    day_meta: Optional[Dict[str, Any]],
    question: str,
    answer: str,
    eval_result: evaluator.Evaluation,
) -> Dict[str, Any]:
    """
    Build a flat Q&A record compatible with feedback_generator's expectations.
    Stores both the raw evaluation scores and the derived fields.
    """
    return {
        "day": day_num,
        "day_title": day_meta.get("title", "") if day_meta else "",
        "question": question,
        "answer": answer,
        # Derived flags
        "is_vague": eval_result.is_vague,
        "is_correct": eval_result.is_correct,          # @property on Evaluation
        "evaluation_notes": eval_result.evaluation_notes,  # @property → overall_comment
        # Raw scores — consumed by feedback_generator for richer summaries
        "technical_accuracy": eval_result.technical_accuracy,
        "depth": eval_result.depth,
        "strengths": eval_result.strengths,
        "missing_points": eval_result.missing_points,
    }


def process_message(session_id: str, message: str) -> InterviewResponse:
    """
    Handle one conversation turn:
      1. Load session state — 404 if missing.
      2. Evaluate the candidate's answer against the last question.
      3. Decide: follow-up | new_question | end.
         - follow_up  → generate & return follow-up question (done=false).
         - end        → generate feedback, return done=true + feedback object.
         - new_question → select next day, generate question, return done=false.
    """
    state = _load_state(session_id)
    if state is None:
        raise KeyError(f"Session '{session_id}' not found.")

    if state.interview_stage == "COMPLETED":
        raise ValueError(f"Session '{session_id}' is already completed.")

    profile = state.candidate_profile
    current_day = state.current_day
    current_day_meta = data_manager.get_day_metadata(current_day) if current_day else None

    # ── Determine the question that prompted this answer ──────────────────────
    pending = state.pending_follow_up
    if pending.get("is_pending"):
        last_question = pending["follow_up_question"]
    else:
        last_question = next(
            (m["content"] for m in reversed(state.history) if m["role"] == "assistant"),
            "",
        )

    # ── 1. Evaluate the answer ────────────────────────────────────────────────
    eval_result = evaluator.evaluate_answer(
        question=last_question,
        answer=message,
        curriculum_context=current_day_meta or {},
    )

    # Append user turn to history
    state.history.append({"role": "user", "content": message})

    # ── 2. Decide next action ────────────────────────────────────────────────
    action = evaluator.decide_next_action(eval_result, state)

    # ── 3a. Follow-up branch ──────────────────────────────────────────────────
    if action == "follow_up":
        logger.info("Generating follow-up for session %s (day %s).", session_id, current_day)
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

    # ── Commit QA record (for both new_question and end paths) ───────────────
    if pending.get("is_pending"):
        # Combine the vague initial answer with the follow-up answer
        combined_answer = (
            f"Initial: {pending['vague_answer']} | Follow-up: {message}"
        )
        qa_rec = _build_qa_record(
            current_day, current_day_meta,
            pending["original_question"], combined_answer, eval_result,
        )
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

    # ── 3b. End interview ─────────────────────────────────────────────────────
    if action == "end" or should_end(state):
        logger.info("Ending interview for session %s.", session_id)
        fb = feedback_generator.generate_feedback(profile, state.qa_records)
        state.interview_stage = "COMPLETED"
        _save_state(session_id, state)
        return InterviewResponse(
            reply="Thank you — that wraps up our interview. I'll share your feedback below.",
            done=True,
            feedback=Feedback(**fb),
        )

    # ── 3c. Next question ─────────────────────────────────────────────────────
    next_day_meta = _select_next_day(profile, state.covered_days)
    if next_day_meta is None:
        # Ran out of curriculum days — wrap up gracefully
        logger.info("No more curriculum days. Ending session %s early.", session_id)
        fb = feedback_generator.generate_feedback(profile, state.qa_records)
        state.interview_stage = "COMPLETED"
        _save_state(session_id, state)
        return InterviewResponse(
            reply="We've covered everything on our agenda. Let me share your feedback.",
            done=True,
            feedback=Feedback(**fb),
        )

    next_day_num = next_day_meta["day"]
    state.covered_days.append(next_day_num)
    state.current_day = next_day_num

    next_question = question_generator.generate_question(state)
    state.history.append({"role": "assistant", "content": next_question})
    state.question_count += 1

    _save_state(session_id, state)
    return InterviewResponse(reply=next_question, done=False)
