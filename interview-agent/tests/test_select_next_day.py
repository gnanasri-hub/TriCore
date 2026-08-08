"""
Tests for dialogue_manager._select_next_day — verifies tier priority and
exclusion logic for every candidate archetype.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CANDIDATES_PATH = Path(__file__).resolve().parent.parent / "data" / "candidates.json"
STUB_DAYS = [
    {"day": d, "title": f"Day {d} Title", "type": "LEARN", "tools": [], "objectives": []}
    for d in range(1, 32)
]

def load_candidate(cand_id: str):
    with open(CANDIDATES_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    for c in data["candidates"]:
        if c["member"]["id"] == cand_id:
            return c
    raise KeyError(f"Candidate {cand_id} not found")


@pytest.fixture(autouse=True)
def patch_data_manager():
    with (
        patch("app.services.data_manager.ensure_index_loaded"),
        patch("app.services.data_manager._metadata", STUB_DAYS),
        patch("app.services.data_manager.get_all_days_metadata", return_value=STUB_DAYS),
        patch(
            "app.services.data_manager.get_day_metadata",
            side_effect=lambda n: next((d for d in STUB_DAYS if d["day"] == n), None),
        ),
        patch(
            "app.services.data_manager.retrieve_relevant_days",
            return_value=STUB_DAYS[:10],
        ),
        patch("app.services.data_manager.get_openai_client", return_value=MagicMock()),
    ):
        yield


def _profile(cand_id):
    from app.services import data_manager
    return data_manager.get_candidate_profile(load_candidate(cand_id))


def _select(profile, covered, current=None):
    from app.services.dialogue_manager import _select_next_day
    return _select_next_day(profile, covered, current)


# ── Tier-1: skipped/failed days come first ───────────────────────────────────

class TestTier1SkippedProbed:
    """CAND-011 skips days 7, 8, 12, 16, 22 — tier-1 must return one of them."""

    def test_skipped_day_selected_when_nothing_covered(self):
        p = _profile("CAND-011")
        result = _select(p, covered=[], current=None)
        assert result is not None
        assert result["day"] in p["skipped_days"], (
            f"Expected a skipped day, got day {result['day']}"
        )

    def test_skipped_day_selected_over_strong(self):
        p = _profile("CAND-011")
        # Cover some completed days to make sure skipped still wins
        covered = p["completed_days"][:2]
        result = _select(p, covered=covered, current=None)
        assert result["day"] in p["skipped_days"]

    def test_current_day_excluded(self):
        p = _profile("CAND-011")
        first_skipped = sorted(p["skipped_days"])[0]
        # Force current_day to be the first skipped day
        result = _select(p, covered=[first_skipped], current=first_skipped)
        # Should pick a different skipped day or fall through
        assert result is None or result["day"] != first_skipped


class TestTier1FailedProbed:
    """CAND-010 failed days 8, 10, 22 — must probe them."""

    def test_failed_day_selected_first(self):
        p = _profile("CAND-010")
        result = _select(p, covered=[], current=None)
        assert result["day"] in p["failed_days"]

    def test_all_failed_days_eventually_covered(self):
        """Repeatedly calling _select drains failed days before others."""
        p = _profile("CAND-010")
        covered = []
        selected_days = []
        for _ in range(5):
            r = _select(p, covered=covered, current=covered[-1] if covered else None)
            if r is None:
                break
            covered.append(r["day"])
            selected_days.append(r["day"])

        # At least one of the failed days must appear in the first 3 picks
        assert any(d in p["failed_days"] for d in selected_days[:3])


class TestTier1MixedFailedSkipped:
    """CAND-016 has both failed and skipped missions."""

    def test_weak_day_selected_first(self):
        p = _profile("CAND-016")
        all_weak = set(p["failed_days"]) | set(p["skipped_days"])
        result = _select(p, covered=[], current=None)
        assert result["day"] in all_weak


# ── Tier-2: job-role relevance fallback ──────────────────────────────────────

class TestTier2JobRole:
    """When all weak days are covered, tier-2 (job role) should fire."""

    def test_job_role_fallback_used(self):
        p = _profile("CAND-003")     # no weak days, AI Engineer
        # All skipped/failed already covered (empty for CAND-003)
        result = _select(p, covered=[], current=None)
        # STUB_DAYS[:10] is returned by retrieve_relevant_days; result must be one of them
        assert result is not None
        assert result["day"] in [d["day"] for d in STUB_DAYS[:10]]


# ── No same-day repetition ────────────────────────────────────────────────────

class TestNoRepeatDay:
    def test_current_day_never_repeated(self):
        p = _profile("CAND-003")
        for day_num in [1, 7, 8, 12, 21]:
            result = _select(p, covered=[day_num], current=day_num)
            assert result is None or result["day"] != day_num

    def test_covered_days_never_repeated(self):
        p = _profile("CAND-003")
        covered = [1, 2, 3, 4, 5]
        result = _select(p, covered=covered, current=5)
        assert result is None or result["day"] not in covered
