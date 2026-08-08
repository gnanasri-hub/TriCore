import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.schemas import InterviewRequest, InterviewResponse
from app.services import data_manager, dialogue_manager
from app import session_store

logger = logging.getLogger(__name__)


# ── Startup: pre-load FAISS index so the first request isn't slow ─────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        data_manager.init_index()
        logger.info("FAISS index ready.")
    except Exception as exc:
        logger.error("Failed to initialise FAISS index on startup: %s", exc)
    yield


app = FastAPI(title="AI Interview Agent", lifespan=lifespan)


# ── Global exception handlers ─────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception("Unhandled error on %s", request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


# ── POST /api/interview ───────────────────────────────────────────────────────

@app.post("/api/interview", response_model=InterviewResponse)
def interview_endpoint(req: InterviewRequest):
    """
    Single endpoint that drives the entire interview lifecycle.

    ┌─────────────────────────────────────────────────────────────────┐
    │ START   { sessionId, candidate: {...} }                         │
    │   → creates session, returns { reply, done: false }             │
    ├─────────────────────────────────────────────────────────────────┤
    │ TURN    { sessionId, message: "..." }                           │
    │   → evaluates answer, returns { reply, done: false }            │
    │     OR  { reply, done: true, feedback: {...} } when finished    │
    └─────────────────────────────────────────────────────────────────┘

    Error responses
    ───────────────
    400  Missing or conflicting fields (both candidate+message, or neither)
    404  sessionId not found when sending a message turn
    409  Trying to start a session that already exists
    410  Session is already completed
    422  Pydantic validation failure (FastAPI built-in)
    500  Unexpected server error
    """

    # ── Validate: sessionId must be a non-empty string ────────────────────────
    if not req.sessionId or not req.sessionId.strip():
        raise HTTPException(status_code=400, detail="'sessionId' must be a non-empty string.")

    session_id = req.sessionId.strip()

    has_candidate = req.candidate is not None
    has_message   = req.message   is not None

    # ── Validate: exactly one of candidate / message must be present ──────────
    if has_candidate and has_message:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'candidate' (to start) or 'message' (for a turn), not both.",
        )

    if not has_candidate and not has_message:
        raise HTTPException(
            status_code=400,
            detail="One of 'candidate' (to start an interview) or 'message' (for a turn) is required.",
        )

    # ── START: initialise a new session ──────────────────────────────────────
    if has_candidate:
        # Validate candidate payload has at least a 'member' key
        if not isinstance(req.candidate, dict) or "member" not in req.candidate:
            raise HTTPException(
                status_code=400,
                detail="'candidate' must be an object containing at least a 'member' field.",
            )

        try:
            reply = dialogue_manager.start_interview(session_id, req.candidate)
        except ValueError as exc:
            # start_interview raises ValueError when session already exists
            raise HTTPException(status_code=409, detail=str(exc))
        except Exception as exc:
            logger.exception("Error starting interview for session '%s'", session_id)
            raise HTTPException(status_code=500, detail=f"Failed to start interview: {exc}")

        return InterviewResponse(reply=reply, done=False)

    # ── TURN: process the candidate's answer ──────────────────────────────────
    message = req.message.strip() if req.message else ""
    if not message:
        raise HTTPException(status_code=400, detail="'message' must not be empty.")

    try:
        return dialogue_manager.process_message(session_id, message)
    except KeyError as exc:
        # process_message raises KeyError when session_id is not in the store
        raise HTTPException(
            status_code=404,
            detail=f"Session not found. Start the interview first by sending a 'candidate' payload. ({exc})",
        )
    except ValueError as exc:
        # process_message raises ValueError when session is already completed
        raise HTTPException(status_code=410, detail=str(exc))
    except Exception as exc:
        logger.exception("Error processing message for session '%s'", session_id)
        raise HTTPException(status_code=500, detail=f"Failed to process message: {exc}")


# ── GET /api/interview/status ─────────────────────────────────────────────────

@app.get("/api/interview/status")
def session_status(sessionId: str):
    """
    Return session counters for testing/debugging.
    Used by test scripts to read question_count and covered_days
    without needing direct access to the in-process session store.
    """
    raw = session_store.get_session(sessionId.strip())
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Session '{sessionId}' not found.")
    return {
        "sessionId":     sessionId,
        "question_count": raw.get("question_count", 0),
        "covered_days":   sorted(set(raw.get("covered_days", []))),
        "interview_stage": raw.get("interview_stage", "UNKNOWN"),
    }
