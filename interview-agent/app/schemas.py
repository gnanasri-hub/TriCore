from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Candidate payload ─────────────────────────────────────────────────────────

class MissionRecord(BaseModel):
    """One completed / skipped / failed cohort mission."""
    day: int
    title: Optional[str] = None
    passed: Optional[bool] = None
    skipped: Optional[bool] = False
    attempts: Optional[int] = 0


class CandidatePayload(BaseModel):
    """
    Flat candidate format accepted by POST /api/interview.

    Both of these are equivalent and accepted:

      Flat (new, canonical):
        { "id": "CAND-001", "name": "Sarah Johnson", "role": "Senior Data Engineer",
          "yearsExperience": 9, "missions": [...], "signals": {...} }

      Wrapped (legacy, for compatibility with candidates.json):
        { "member": { "id": "CAND-001", "name": "Sarah Johnson",
                      "jobRole": "Senior Data Engineer", "yearsExperience": 9 },
          "missions": [...], "signals": {...} }

    The model normalises both into the flat representation internally.
    """

    id:              str                      = Field(..., min_length=1, description="Non-empty candidate ID")
    name:            str                      = Field(..., min_length=1, description="Non-empty candidate name")
    # "jobRole" is the legacy camelCase field name from candidates.json.
    # "role" is the new flat field name. populate_by_name=True accepts both.
    role:            Optional[str]            = Field(default=None, alias="jobRole")
    yearsExperience: Optional[int]            = 0
    education:       Optional[str]            = None
    status:          Optional[str]            = None
    missions:        List[MissionRecord]      = Field(default_factory=list)
    signals:         Dict[str, Any]           = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    @model_validator(mode="before")
    @classmethod
    def unwrap_member(cls, data: Any) -> Any:
        """
        Handles two input shapes:

        1. Legacy wrapped (from candidates.json):
           { "member": { "id": "...", "jobRole": "..." }, "missions": [...] }
           → unwraps member fields to the top level

        2. Flat canonical (new Swagger / demo format):
           { "id": "...", "role": "Senior Data Engineer", "missions": [...] }
           → normalise "role" → "jobRole" so the alias resolves correctly
        """
        if not isinstance(data, dict):
            return data

        # Unwrap legacy "member" envelope
        if "member" in data:
            member = data.pop("member", {}) or {}
            for k, v in member.items():
                data.setdefault(k, v)

        # Normalise "role" → "jobRole" so the Field alias always resolves
        if "role" in data and "jobRole" not in data:
            data["jobRole"] = data.pop("role")

        return data

    @field_validator("id", "name")
    @classmethod
    def validate_non_empty_str(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Field must be a string.")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field must not be empty or blank.")
        return stripped



# ── Request / Response ────────────────────────────────────────────────────────

class InterviewRequest(BaseModel):
    """
    POST /api/interview request body.

    Exactly one of `candidate` (START) or `message` (TURN) must be present.
    """
    sessionId: str = Field(..., min_length=1, description="Non-empty session identifier")
    candidate: Optional[CandidatePayload] = Field(
        default=None,
        description="Send to START a new interview session.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Send to advance an existing session (TURN).",
    )

    @field_validator("sessionId")
    @classmethod
    def session_id_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("'sessionId' must be a non-empty string.")
        return v.strip()

    @model_validator(mode="after")
    def exactly_one_of_candidate_or_message(self) -> InterviewRequest:
        has_candidate = self.candidate is not None
        has_message   = self.message   is not None

        if has_candidate and has_message:
            raise ValueError(
                "Provide either 'candidate' (to start an interview) "
                "or 'message' (for a conversation turn) — not both."
            )
        if not has_candidate and not has_message:
            raise ValueError(
                "One of 'candidate' (to start) or 'message' (for a turn) is required."
            )
        if has_message and not self.message.strip():
            raise ValueError("'message' must not be empty.")

        return self


class Feedback(BaseModel):
    summary:   str
    strengths: List[str]
    gaps:      List[str]
    next:      List[str]


class InterviewResponse(BaseModel):
    reply:    str
    done:     bool
    feedback: Optional[Feedback] = None
    evaluation: Optional[Dict[str, Any]] = None


# ── Session state (internal) ──────────────────────────────────────────────────

class SessionState(BaseModel):
    session_id:        str
    candidate_profile: Dict[str, Any]
    history:           List[Dict[str, str]]
    qa_records:        List[Dict[str, Any]]
    covered_days:      List[int]
    current_day:       Optional[int] = None
    question_count:    int
    pending_follow_up: Dict[str, Any]
    interview_stage:   str
