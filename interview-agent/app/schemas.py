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
