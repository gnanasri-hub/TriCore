"""
Tests for dialogue_manager.should_end — verifies the ≥8 questions AND ≥4 days gate.
"""
import pytest
from app.schemas import SessionState
from app.services.dialogue_manager import should_end, MIN_QUESTIONS, MIN_DAYS


def _state(question_count: int, covered_days: list) -> SessionState:
    return SessionState(
        session_id="test",
        candidate_profile={},
        history=[],
        qa_records=[],
        covered_days=covered_days,
        current_day=covered_days[-1] if covered_days else None,
        question_count=question_count,
        pending_follow_up={
            "is_pending": False,
            "follow_up_question": "",
            "original_question": "",
            "vague_answer": "",
        },
        interview_stage="INTERVIEWING",
    )


class TestShouldEnd:
    def test_both_thresholds_met_returns_true(self):
        state = _state(MIN_QUESTIONS, list(range(1, MIN_DAYS + 1)))
        assert should_end(state) is True

    def test_questions_not_met_returns_false(self):
        state = _state(MIN_QUESTIONS - 1, list(range(1, MIN_DAYS + 1)))
        assert should_end(state) is False

    def test_days_not_met_returns_false(self):
        state = _state(MIN_QUESTIONS, list(range(1, MIN_DAYS)))  # one day short
        assert should_end(state) is False

    def test_both_thresholds_not_met_returns_false(self):
        state = _state(0, [])
        assert should_end(state) is False

    def test_duplicate_covered_days_deduped(self):
        """Follow-ups push the same day into covered_days twice — must not trick the gate."""
        # 4 unique days but listed 8 times (duplicates from follow-ups)
        covered = [1, 1, 2, 2, 3, 3, 4, 4]
        state = _state(MIN_QUESTIONS, covered)
        # set(covered) has 4 unique days — exactly MIN_DAYS, so should_end must be True
        assert should_end(state) is True

    def test_just_above_both_thresholds(self):
        state = _state(MIN_QUESTIONS + 5, list(range(1, MIN_DAYS + 5)))
        assert should_end(state) is True

    def test_many_questions_but_only_one_day(self):
        state = _state(50, [7, 7, 7, 7])   # 50 questions but only day 7
        assert should_end(state) is False

    def test_many_days_but_zero_questions(self):
        state = _state(0, [1, 2, 3, 4, 5, 6])
        assert should_end(state) is False

    def test_exact_minimum_questions_and_extra_days(self):
        state = _state(MIN_QUESTIONS, list(range(1, 10)))
        assert should_end(state) is True

    def test_interview_must_not_end_before_8_questions(self):
        """Regression: follow-up questions must count, but the gate stays at MIN_QUESTIONS."""
        for q in range(0, MIN_QUESTIONS):
            state = _state(q, [1, 2, 3, 4, 5])
            assert should_end(state) is False, f"Ended too early at question_count={q}"
