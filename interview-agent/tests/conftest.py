"""
Shared fixtures and helpers for the interview-agent test suite.

All tests run WITHOUT hitting the OpenAI API or the FAISS index.
Every external call is patched at the module level where it is imported.
"""
import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# ── Make sure the interview-agent package is importable ──────────────────────
AGENT_ROOT = Path(__file__).resolve().parent.parent
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

# ── Candidate fixtures loaded straight from the real data file ───────────────
CANDIDATES_PATH = AGENT_ROOT / "data" / "candidates.json"


def load_candidate(cand_id: str) -> Dict[str, Any]:
    with open(CANDIDATES_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    for c in data["candidates"]:
        if c["member"]["id"] == cand_id:
            return c
    raise KeyError(f"Candidate {cand_id} not found in candidates.json")


# ── Minimal metadata stubs ────────────────────────────────────────────────────
STUB_DAYS: List[Dict[str, Any]] = [
    {"day": d, "title": f"Day {d} Title", "type": "LEARN", "tools": [], "objectives": []}
    for d in range(1, 32)
]


@pytest.fixture()
def stub_metadata():
    """Patch data_manager so no FAISS index is needed."""
    with (
        patch("app.services.data_manager.ensure_index_loaded"),
        patch("app.services.data_manager._metadata", STUB_DAYS),
        patch("app.services.data_manager._index", MagicMock()),
        patch(
            "app.services.data_manager.get_all_days_metadata",
            return_value=STUB_DAYS,
        ),
        patch(
            "app.services.data_manager.get_day_metadata",
            side_effect=lambda n: next((d for d in STUB_DAYS if d["day"] == n), None),
        ),
        patch(
            "app.services.data_manager.retrieve_relevant_days",
            return_value=STUB_DAYS[:10],
        ),
    ):
        yield
