from fastapi import FastAPI
from app.schemas import InterviewRequest, InterviewResponse
from app import session_store

app = FastAPI(title="AI Interview Agent")

@app.post("/api/interview", response_model=InterviewResponse)
async def interview_endpoint(req: InterviewRequest):
    session = session_store.get_session(req.sessionId)
    if not session:
        session_store.create_or_update_session(req.sessionId, {"candidate": req.candidate, "history": []})
    
    return InterviewResponse(
        reply="Ready",
        done=False
    )
