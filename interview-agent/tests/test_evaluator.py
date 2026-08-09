"""
Tests for evaluator.evaluate_answer (min-length guard) and
decide_next_action (all six branches).

No OpenAI calls are made — every LLM interaction is mocked or short-circuited
by the min-length guard.
"""
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.evaluator import (
    Evaluation,
    evaluate_answer,
    decide_next_action,
    MIN_ANSWER_LENGTH,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _eval(
    *,
    is_vague=False,
    is_incomplete=False,
    is_strong=False,
    depth=5,
    technical_accuracy=7,
    clarity=7,
) -> Evaluation:
    return Evaluation(
        technical_accuracy=technical_accuracy,
        depth=depth,
        clarity=clarity,
        is_vague=is_vague,
        is_strong=is_strong,
        is_incomplete=is_incomplete,
        strengths=["good point"] if is_strong else [],
        missing_points=["missing detail"] if (is_vague or is_incomplete) else [],
        overall_comment="test comment",
    )


def _pending_session(is_pending: bool) -> dict:
    return {
        "pending_follow_up": {
            "is_pending": is_pending,
            "follow_up_question": "elaborate?",
            "original_question": "q",
            "vague_answer": "idk",
        },
        "question_count": 3,
    }


# ── evaluate_answer: min-length guard ────────────────────────────────────────

class TestMinLengthGuard:
    """Answers under MIN_ANSWER_LENGTH must be flagged vague without LLM calls."""

    def test_empty_string_is_vague(self):
        result = evaluate_answer("What is an embedding?", "", {})
        assert result.is_vague is True
        assert result.technical_accuracy == 0

    def test_single_word_is_vague(self):
        result = evaluate_answer("What is an embedding?", "Yes", {})
        assert result.is_vague is True

    def test_short_answer_below_threshold(self):
        short = "I don't know"   # 13 chars — below MIN_ANSWER_LENGTH=15
        result = evaluate_answer("Explain RAG", short, {})
        assert result.is_vague is True
        assert result.is_incomplete is True

    def test_answer_at_threshold_calls_llm(self):
        """An answer at exactly MIN_ANSWER_LENGTH should attempt the LLM call."""
        answer = "x" * MIN_ANSWER_LENGTH
        mock_eval = _eval(is_vague=False)
        mock_response = MagicMock()
        mock_response.choices[0].message.content = mock_eval.model_dump_json()

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        with patch("app.services.evaluator._get_client", return_value=mock_client):
            result = evaluate_answer("Q", answer, {"day": 7, "title": "T",
                                                    "objectives": [], "tools": []})
        mock_client.chat.completions.create.assert_called_once()
        assert result.is_vague is False

    def test_dict_context_serialised(self):
        """Dict curriculum_context must be accepted without error."""
        answer = "x" * MIN_ANSWER_LENGTH
        mock_eval = _eval()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = mock_eval.model_dump_json()

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        with patch("app.services.evaluator._get_client", return_value=mock_client):
            result = evaluate_answer(
                "Q", answer,
                {"day": 7, "title": "Embeddings", "objectives": ["obj1"], "tools": ["FAISS"]},
            )
        assert result is not None



# ── Evaluation derived properties ─────────────────────────────────────────────

class TestDerivedProperties:
    def test_is_correct_true_when_accuracy_gte_6_and_not_incomplete(self):
        e = _eval(technical_accuracy=7, is_incomplete=False)
        assert e.is_correct is True

    def test_is_correct_false_when_accuracy_lt_6(self):
        e = _eval(technical_accuracy=4, is_incomplete=False)
        assert e.is_correct is False

    def test_is_correct_false_when_incomplete(self):
        e = _eval(technical_accuracy=9, is_incomplete=True)
        assert e.is_correct is False

    def test_evaluation_notes_equals_overall_comment(self):
        e = _eval()
        assert e.evaluation_notes == e.overall_comment


# ── decide_next_action: all six branches ────────────────────────────────────

class TestDecideNextAction:
    # Rule 1: already in follow-up → always new_question
    def test_already_in_followup_returns_new_question(self):
        session = _pending_session(is_pending=True)
        for ev in [_eval(is_vague=True), _eval(is_incomplete=True), _eval(is_strong=True, depth=10)]:
            assert decide_next_action(ev, session) == "new_question"

    # Rule 2: vague → follow_up_clarify
    def test_vague_triggers_followup(self):
        session = _pending_session(is_pending=False)
        ev = _eval(is_vague=True)
        assert decide_next_action(ev, session) == "follow_up_clarify"

    # Rule 2: incomplete → follow_up_clarify
    def test_incomplete_triggers_followup(self):
        session = _pending_session(is_pending=False)
        ev = _eval(is_incomplete=True)
        assert decide_next_action(ev, session) == "follow_up_clarify"

    # Rule 2: vague AND incomplete → follow_up_clarify
    def test_vague_and_incomplete_triggers_followup(self):
        session = _pending_session(is_pending=False)
        ev = _eval(is_vague=True, is_incomplete=True)
        assert decide_next_action(ev, session) == "follow_up_clarify"

    # Rule 3: strong + depth >= 8 → new_question
    def test_strong_high_depth_moves_on(self):
        session = _pending_session(is_pending=False)
        for depth in [8, 9, 10]:
            ev = _eval(is_strong=True, depth=depth)
            assert decide_next_action(ev, session) == "new_question", f"depth={depth}"

    # Rule 4: strong + depth < 8 → follow_up_escalate
    def test_strong_low_depth_probes_deeper(self):
        session = _pending_session(is_pending=False)
        for depth in [0, 4, 7]:
            ev = _eval(is_strong=True, depth=depth)
            assert decide_next_action(ev, session) == "follow_up_escalate", f"depth={depth}"

    # Rule 5: default (average answer, not vague/strong/incomplete) → new_question
    def test_average_answer_moves_on(self):
        session = _pending_session(is_pending=False)
        ev = _eval(is_vague=False, is_incomplete=False, is_strong=False, depth=5)
        assert decide_next_action(ev, session) == "new_question"

    # SessionState object (not dict) also works
    def test_works_with_session_state_object(self):
        from app.schemas import SessionState
        state = SessionState(
            session_id="test",
            candidate_profile={},
            history=[],
            qa_records=[],
            covered_days=[1],
            current_day=1,
            question_count=2,
            pending_follow_up={
                "is_pending": False,
                "follow_up_question": "",
                "original_question": "",
                "vague_answer": "",
            },
            interview_stage="INTERVIEWING",
        )
        ev = _eval(is_vague=True)
        assert decide_next_action(ev, state) == "follow_up_clarify"
