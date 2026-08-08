"""
Tests for data_manager.get_candidate_profile — covers every candidate archetype.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CANDIDATES_PATH = Path(__file__).resolve().parent.parent / "data" / "candidates.json"

def load_candidate(cand_id: str):
    with open(CANDIDATES_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    for c in data["candidates"]:
        if c["member"]["id"] == cand_id:
            return c
    raise KeyError(f"Candidate {cand_id} not found")


# Patch the OpenAI client and FAISS so importing data_manager doesn't crash.
@pytest.fixture(autouse=True)
def no_openai():
    with patch("app.services.data_manager.get_openai_client", return_value=MagicMock()):
        yield


def _profile(cand_id: str):
    from app.services import data_manager
    return data_manager.get_candidate_profile(load_candidate(cand_id))


# ── CAND-003: Emily Chen — almost all first-try passes ───────────────────────
class TestStrongCandidate:
    def test_strong_topics_populated(self):
        p = _profile("CAND-003")
        assert len(p["strong_topics"]) >= 8, "Expected many strong topics for CAND-003"

    def test_no_failed_days(self):
        p = _profile("CAND-003")
        assert p["failed_days"] == []

    def test_no_skipped_days(self):
        p = _profile("CAND-003")
        assert p["skipped_days"] == []

    def test_experience_level_senior(self):
        p = _profile("CAND-003")  # 6 years → Senior (> 5 years threshold)
        assert p["experience_level"] == "Senior"

    def test_profile_keys_present(self):
        p = _profile("CAND-003")
        for key in ("id", "name", "job_role", "experience_level", "years_experience",
                    "completed_days", "skipped_days", "failed_days",
                    "strong_topics", "weak_topics", "signals"):
            assert key in p, f"Missing key: {key}"


# ── CAND-018: Diane Foster — 100% first-try ──────────────────────────────────
class TestPerfectFirstTry:
    def test_all_strong_topics(self):
        p = _profile("CAND-018")
        # Every mission was passed on first attempt
        assert len(p["strong_topics"]) == len(p["completed_days"])

    def test_weak_topics_empty(self):
        p = _profile("CAND-018")
        assert p["weak_topics"] == []


# ── CAND-011: Mia Alvarez — many skipped missions ────────────────────────────
class TestManySkipped:
    def test_skipped_days_detected(self):
        p = _profile("CAND-011")
        # CAND-011 skips days 7, 8, 12, 16, 22
        assert len(p["skipped_days"]) >= 5

    def test_skipped_are_weak_topics(self):
        p = _profile("CAND-011")
        weak_lower = [t.lower() for t in p["weak_topics"]]
        # "Embeddings Explained" was skipped
        assert any("embedding" in t for t in weak_lower)

    def test_completed_days_not_skipped(self):
        p = _profile("CAND-011")
        overlap = set(p["completed_days"]) & set(p["skipped_days"])
        assert overlap == set()


# ── CAND-014: Bethany Cole — four skipped missions ───────────────────────────
class TestSkippedHRCandidate:
    def test_skipped_days_present(self):
        p = _profile("CAND-014")
        # days 8, 22, 27, 28 are skipped
        assert set([8, 22, 27, 28]).issubset(set(p["skipped_days"]))

    def test_no_failed_days(self):
        p = _profile("CAND-014")
        assert p["failed_days"] == []

    def test_experience_level_senior(self):
        p = _profile("CAND-014")   # 10 years
        assert p["experience_level"] == "Senior"


# ── CAND-010: Gerald Combs — failed days 8, 10, 22 ───────────────────────────
class TestFailedMissions:
    def test_failed_days_detected(self):
        p = _profile("CAND-010")
        assert set([8, 10, 22]).issubset(set(p["failed_days"]))

    def test_failed_are_weak_topics(self):
        p = _profile("CAND-010")
        weak_lower = [t.lower() for t in p["weak_topics"]]
        assert any("vector" in t for t in weak_lower)

    def test_failed_not_in_completed(self):
        p = _profile("CAND-010")
        overlap = set(p["failed_days"]) & set(p["completed_days"])
        assert overlap == set()


# ── CAND-016: Isabella Rossi — failed days 7, 12, 22 + two skipped ───────────
class TestMixedFailedSkipped:
    def test_failed_days(self):
        p = _profile("CAND-016")
        assert set([7, 12, 22]).issubset(set(p["failed_days"]))

    def test_skipped_days(self):
        p = _profile("CAND-016")
        assert set([27, 28]).issubset(set(p["skipped_days"]))

    def test_failed_and_skipped_are_all_weak(self):
        p = _profile("CAND-016")
        all_weak_days = set(p["failed_days"]) | set(p["skipped_days"])
        # All weak days must appear in weak_topics list (via title lookup)
        assert len(p["weak_topics"]) >= len(all_weak_days)
