from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class Feedback(BaseModel):
    summary: str
    strengths: List[str]
    gaps: List[str]
    next: List[str]

class InterviewRequest(BaseModel):
    sessionId: str
    message: Optional[str] = None
    candidate: Optional[Dict[str, Any]] = None

class InterviewResponse(BaseModel):
    reply: str
    done: bool
    feedback: Optional[Feedback] = None

class SessionState(BaseModel):
    session_id: str
    candidate_profile: Dict[str, Any]
    history: List[Dict[str, str]]
    qa_records: List[Dict[str, Any]]
    covered_days: List[int]
    current_day: Optional[int] = None
    question_count: int
    pending_follow_up: Dict[str, Any]
    interview_stage: str
