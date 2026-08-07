from fastapi import FastAPI, HTTPException
from app.schemas import InterviewRequest, InterviewResponse
from app.services import dialogue_manager

app = FastAPI(title="AI Interview Agent")

@app.post("/api/interview", response_model=InterviewResponse)
async def interview_endpoint(req: InterviewRequest):
    # Determine if this is starting a new interview or sending a turn message
    if req.candidate is not None:
        try:
            reply = dialogue_manager.start_interview(req.sessionId, req.candidate)
            return InterviewResponse(
                reply=reply,
                done=False
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start interview: {e}")
            
    elif req.message is not None:
        try:
            return dialogue_manager.process_message(req.sessionId, req.message)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process message: {e}")
            
    else:
        raise HTTPException(
            status_code=400, 
            detail="Invalid request. Must provide either 'candidate' to start or 'message' for a turn."
        )
