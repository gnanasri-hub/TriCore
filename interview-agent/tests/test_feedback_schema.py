"""
Tests for feedback_generator.generate_feedback — validates that the output
always matches the exact Feedback schema regardless of input shape.

No OpenAI calls are made; GPT-4o is mocked to return a canned Feedback.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.schemas import Feedback
from app.services import feedback_generator


# ── Shared mock factory ───────────────────────────────────────────────────────

def _mock_gpt_feedback(**overrides):
    """Build a Feedback-shaped mock that _get_client().beta.chat.completions.parse returns."""
    defaults = dict(
        summary="Candidate demonstrated solid understanding of core AI topics.",
        strengths=["Good grasp of embeddings", "Clear explanation of RAG"],
        gaps=["Missed trade-offs in vector DB selection"],
        next=["Review FAISS indexing strategies", "Practice prompt engineering exercises"],
    )
    defaults.update(overrides)
    feedback_obj = Feedback(**defaults)
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed = feedback_obj
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.return_value = mock_response
    return mock_client


def _minimal_profile() -> dict:
    return {
        "id": "CAND-003",
        "name": "Emily Chen",
        "job_role": "AI Engineer",
        "experience_level": "Mid-level",
        "years_experience": 6,
        "completed_days": [7, 8, 10, 11],
        "skipped_days": [],
        "failed_days": [],
        "strong_topics": ["Embeddings Explained", "RAG End-to-End & LLM API Basics"],
        "weak_topics": [],
        "signals": {"commitDays": 31},
    }


def _qa_records(n: int = 3) -> list:
    return [
        {
            "day": i + 7,
            "day_title": f"Day {i + 7} Title",
            "question": f"Question {i}",
            "answer": f"Answer {i} with sufficient detail",
            "is_vague": False,
            "is_correct": True,
            "evaluation_notes": "Good answer.",
            "technical_accuracy": 8,
            "depth": 7,
            "strengths": ["clear explanation"],
            "missing_points": [],
        }
        for i in range(n)
    ]


# ── Schema compliance ─────────────────────────────────────────────────────────

class TestFeedbackSchema:
    def test_returns_dict_with_all_required_keys(self):
        with patch("app.services.feedback_generator._get_client", return_value=_mock_gpt_feedback()):
            result = feedback_generator.generate_feedback(_minimal_profile(), _qa_records())

        assert isinstance(result, dict)
        for key in ("summary", "strengths", "gaps", "next"):
            assert key in result, f"Missing key: {key}"

    def test_summary_is_non_empty_string(self):
        with patch("app.services.feedback_generator._get_client", return_value=_mock_gpt_feedback()):
            result = feedback_generator.generate_feedback(_minimal_profile(), _qa_records())

        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_array_fields_are_lists(self):
        with patch("app.services.feedback_generator._get_client", return_value=_mock_gpt_feedback()):
            result = feedback_generator.generate_feedback(_minimal_profile(), _qa_records())

        assert isinstance(result["strengths"], list)
        assert isinstance(result["gaps"], list)
        assert isinstance(result["next"], list)

    def test_array_fields_contain_strings(self):
        with patch("app.services.feedback_generator._get_client", return_value=_mock_gpt_feedback()):
            result = feedback_generator.generate_feedback(_minimal_profile(), _qa_records())

        for field in ("strengths", "gaps", "next"):
            for item in result[field]:
                assert isinstance(item, str), f"{field} contains non-string: {item!r}"

    def test_result_validates_as_feedback_model(self):
        """The returned dict must be accepted by the Feedback Pydantic model."""
        with patch("app.services.feedback_generator._get_client", return_value=_mock_gpt_feedback()):
            result = feedback_generator.generate_feedback(_minimal_profile(), _qa_records())

        # Should not raise
        fb = Feedback(**result)
        assert fb.summary == result["summary"]

    def test_empty_qa_records_still_returns_valid_schema(self):
        with patch("app.services.feedback_generator._get_client", return_value=_mock_gpt_feedback()):
            result = feedback_generator.generate_feedback(_minimal_profile(), [])

        assert set(result.keys()) >= {"summary", "strengths", "gaps", "next"}

    def test_graceful_fallback_on_llm_error(self):
        """When GPT-4o raises, fallback must still return a valid Feedback dict."""
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.side_effect = Exception("API timeout")
        with patch("app.services.feedback_generator._get_client", return_value=mock_client):
            result = feedback_generator.generate_feedback(_minimal_profile(), _qa_records())

        assert isinstance(result, dict)
        fb = Feedback(**result)
        assert fb.summary  # non-empty

    def test_skipped_candidate_profile_accepted(self):
        """CAND-011 archetype (many skipped) must not break the prompt builder."""
        import json
        from pathlib import Path
        from app.services.data_manager import get_candidate_profile

        candidates_path = Path(__file__).resolve().parent.parent / "data" / "candidates.json"
        with open(candidates_path) as fh:
            all_cands = json.load(fh)["candidates"]
        cand_011 = next(c for c in all_cands if c["member"]["id"] == "CAND-011")

        with patch("app.services.data_manager.get_openai_client", return_value=MagicMock()):
            profile = get_candidate_profile(cand_011)

        with patch("app.services.feedback_generator._get_client", return_value=_mock_gpt_feedback()):
            result = feedback_generator.generate_feedback(profile, _qa_records())

        Feedback(**result)  # must not raise
