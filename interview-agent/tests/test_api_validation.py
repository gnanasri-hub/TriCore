"""
Tests for POST /api/interview HTTP validation and error mapping.

The FastAPI app is tested via TestClient.
All LLM / FAISS calls are mocked so these tests stay offline and fast.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Shared candidate payload ──────────────────────────────────────────────────

CANDIDATE_PAYLOAD = {
    "member": {
        "id": "CAND-003",
        "name": "Emily Chen",
        "jobRole": "AI Engineer",
        "yearsExperience": 6,
        "education": "MS Artificial Intelligence",
        "status": "COMPLETED",
    },
    "missions": [
        {"day": 7, "title": "Embeddings Explained", "passed": True, "attempts": 1},
        {"day": 8, "title": "Vector Databases Overview", "passed": True, "attempts": 1},
        {"day": 10, "title": "Retrieval & Matching Engine", "passed": True, "attempts": 1},
        {"day": 11, "title": "RAG End-to-End & LLM API Basics", "passed": True, "attempts": 1},
        {"day": 21, "title": "LangChain Agents", "passed": True, "attempts": 1},
        {"day": 22, "title": "Multi-Agent Orchestration", "passed": True, "attempts": 1},
    ],
    "signals": {"commitDays": 31, "missionsCompleted": 31, "missionsFirstTry": 30},
}


@pytest.fixture()
def client():
    """
    TestClient with all external dependencies patched so no network or disk
    access occurs during request handling.
    """
    with (
        patch("app.services.data_manager.init_index"),
        patch("app.services.data_manager.ensure_index_loaded"),
        patch("app.services.data_manager.get_openai_client", return_value=MagicMock()),
        patch(
            "app.services.data_manager.get_all_days_metadata",
            return_value=[
                {"day": d, "title": f"Day {d}", "type": "LEARN", "tools": [], "objectives": []}
                for d in range(1, 32)
            ],
        ),
        patch(
            "app.services.data_manager.get_day_metadata",
            return_value={"day": 7, "title": "Embeddings Explained", "tools": [], "objectives": []},
        ),
        patch(
            "app.services.data_manager.retrieve_relevant_days",
            return_value=[
                {"day": d, "title": f"Day {d}", "similarity": 0.9}
                for d in range(1, 11)
            ],
        ),
        patch(
            "app.services.question_generator.generate_question",
            return_value="Tell me about embeddings.",
        ),
        patch(
            "app.services.question_generator.generate_follow_up",
            return_value="Can you elaborate on that?",
        ),
    ):
        # Import app *after* patches are active
        from app.main import app
        from app import session_store
        session_store.sessions.clear()   # fresh store per test
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ── 400: missing / conflicting fields ────────────────────────────────────────

class TestBadRequest:
    def test_no_candidate_no_message(self, client):
        resp = client.post("/api/interview", json={"sessionId": "s1"})
        assert resp.status_code == 400

    def test_both_candidate_and_message(self, client):
        resp = client.post("/api/interview", json={
            "sessionId": "s1",
            "candidate": CANDIDATE_PAYLOAD,
            "message": "hello",
        })
        assert resp.status_code == 400

    def test_empty_session_id(self, client):
        resp = client.post("/api/interview", json={
            "sessionId": "",
            "candidate": CANDIDATE_PAYLOAD,
        })
        assert resp.status_code == 400

    def test_whitespace_session_id(self, client):
        resp = client.post("/api/interview", json={
            "sessionId": "   ",
            "candidate": CANDIDATE_PAYLOAD,
        })
        assert resp.status_code == 400

    def test_empty_message(self, client):
        # First start a session so the 400 is from empty message, not 404
        client.post("/api/interview", json={
            "sessionId": "s-empty-msg",
            "candidate": CANDIDATE_PAYLOAD,
        })
        resp = client.post("/api/interview", json={
            "sessionId": "s-empty-msg",
            "message": "",
        })
        assert resp.status_code == 400

    def test_candidate_missing_required_fields(self, client):
        resp = client.post("/api/interview", json={
            "sessionId": "s-missing-fields",
            "candidate": {"missions": []},   # no id, name, role
        })
        assert resp.status_code == 400

    def test_flat_candidate_format_success(self, client):
        resp = client.post("/api/interview", json={
            "sessionId": "s-flat-success",
            "candidate": {
                "id": "CAND-999",
                "name": "Alex flat",
                "role": "DevOps Engineer",
            },
        })
        assert resp.status_code == 200


    def test_missing_session_id_field(self, client):
        resp = client.post("/api/interview", json={"candidate": CANDIDATE_PAYLOAD})
        assert resp.status_code == 422   # Pydantic required field


# ── 409: duplicate session ────────────────────────────────────────────────────

class TestConflict:
    def test_starting_same_session_twice_returns_409(self, client):
        payload = {"sessionId": "dup-session", "candidate": CANDIDATE_PAYLOAD}
        r1 = client.post("/api/interview", json=payload)
        assert r1.status_code == 200
        r2 = client.post("/api/interview", json=payload)
        assert r2.status_code == 409


# ── 404: session not found ────────────────────────────────────────────────────

class TestNotFound:
    def test_message_without_prior_start_returns_404(self, client):
        resp = client.post("/api/interview", json={
            "sessionId": "ghost-session",
            "message": "Hello there",
        })
        assert resp.status_code == 404


# ── 410: session already completed ───────────────────────────────────────────

class TestGone:
    def test_message_to_completed_session_returns_410(self, client):
        from app import session_store
        from app.schemas import SessionState

        # Inject a completed session directly
        state = SessionState(
            session_id="done-session",
            candidate_profile={},
            history=[{"role": "assistant", "content": "Q1"}],
            qa_records=[],
            covered_days=[1, 2, 3, 4],
            current_day=4,
            question_count=10,
            pending_follow_up={
                "is_pending": False,
                "follow_up_question": "",
                "original_question": "",
                "vague_answer": "",
            },
            interview_stage="COMPLETED",
        )
        session_store.create_or_update_session("done-session", state.model_dump())

        resp = client.post("/api/interview", json={
            "sessionId": "done-session",
            "message": "One more answer",
        })
        assert resp.status_code == 410


# ── 200: happy-path response shapes ──────────────────────────────────────────

class TestHappyPath:
    def test_start_returns_reply_and_done_false(self, client):
        resp = client.post("/api/interview", json={
            "sessionId": "happy-start",
            "candidate": CANDIDATE_PAYLOAD,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "reply" in body
        assert body["done"] is False
        assert body.get("feedback") is None

    def test_start_reply_is_non_empty_string(self, client):
        resp = client.post("/api/interview", json={
            "sessionId": "happy-reply",
            "candidate": CANDIDATE_PAYLOAD,
        })
        assert isinstance(resp.json()["reply"], str)
        assert len(resp.json()["reply"]) > 0

    def test_turn_returns_reply_and_done_false(self, client):
        from app.services.evaluator import Evaluation

        # Start session
        client.post("/api/interview", json={
            "sessionId": "happy-turn",
            "candidate": CANDIDATE_PAYLOAD,
        })

        # Mock evaluation to avoid LLM call
        mock_eval = Evaluation(
            technical_accuracy=7, depth=6, clarity=7,
            is_vague=False, is_strong=False, is_incomplete=False,
            strengths=["good"], missing_points=[],
            overall_comment="Fine answer.",
        )
        with patch("app.services.evaluator.evaluate_answer", return_value=mock_eval):
            resp = client.post("/api/interview", json={
                "sessionId": "happy-turn",
                "message": "A sufficiently detailed answer about the topic.",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert "reply" in body
        assert "done" in body

    def test_end_turn_contains_feedback_schema(self, client):
        """When should_end fires, the response must include the full feedback object."""
        from app.services.evaluator import Evaluation
        from app.schemas import Feedback

        # Start session
        client.post("/api/interview", json={
            "sessionId": "happy-end",
            "candidate": CANDIDATE_PAYLOAD,
        })

        mock_eval = Evaluation(
            technical_accuracy=8, depth=9, clarity=8,
            is_vague=False, is_strong=True, is_incomplete=False,
            strengths=["excellent"], missing_points=[],
            overall_comment="Great answer.",
        )
        mock_fb = Feedback(
            summary="Strong overall performance.",
            strengths=["Embeddings knowledge", "RAG pipeline understanding"],
            gaps=["Could improve on fine-tuning"],
            next=["Study LoRA", "Practice deployment"],
        )

        with (
            patch("app.services.evaluator.evaluate_answer", return_value=mock_eval),
            patch("app.services.dialogue_manager.should_end", return_value=True),
            patch(
                "app.services.feedback_generator.generate_feedback",
                return_value=mock_fb.model_dump(),
            ),
        ):
            resp = client.post("/api/interview", json={
                "sessionId": "happy-end",
                "message": "An excellent, detailed technical answer here.",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body["done"] is True
        fb = body.get("feedback")
        assert fb is not None
        assert "summary" in fb
        assert isinstance(fb["strengths"], list)
        assert isinstance(fb["gaps"], list)
        assert isinstance(fb["next"], list)
