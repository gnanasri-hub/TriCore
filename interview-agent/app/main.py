import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import InterviewRequest, InterviewResponse
from app.services import data_manager, dialogue_manager
from app import session_store

logger = logging.getLogger(__name__)


# ── Startup ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        data_manager.init_index()
        logger.info("FAISS index ready.")
    except Exception as exc:
        logger.error("Failed to initialise FAISS index on startup: %s", exc)
    yield


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Interview Agent",
    description="Personalised technical interview agent for the TriCore AI cohort.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    # Check if sessionId is completely missing from the request
    is_session_id_missing = any(
        err.get("loc") == ("body", "sessionId") and err.get("type") == "missing"
        for err in errors
    )
    if is_session_id_missing:
        return JSONResponse(
            status_code=422,
            content={"detail": errors}
        )

    # Map other request validation errors to 400 Bad Request
    error_messages = []
    for err in errors:
        msg = err.get("msg", "")
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        
        loc = err.get("loc", [])
        if len(loc) > 1:
            field_name = ".".join(str(l) for l in loc[1:])
            error_messages.append(f"'{field_name}': {msg}")
        else:
            error_messages.append(msg)

    detail_msg = "; ".join(error_messages) if error_messages else "Request validation failed."
    return JSONResponse(
        status_code=400,
        content={"detail": detail_msg}
    )


# ── POST /api/interview ───────────────────────────────────────────────────────

@app.post(
    "/api/interview",
    response_model=None,
    summary="Drive the interview lifecycle",
    responses={
        400: {"description": "Bad request — missing or conflicting fields"},
        404: {"description": "Session not found"},
        409: {"description": "Session already exists"},
        410: {"description": "Session already completed"},
    },
)
def interview_endpoint(req: InterviewRequest) -> InterviewResponse:
    """
    Single endpoint for the entire interview lifecycle.

    **START a new interview**
    ```json
    { "sessionId": "abc-123", "candidate": { "id": "...", "name": "...", "role": "..." } }
    ```
    Returns `{ "reply": "...", "done": false }`

    **Advance a turn**
    ```json
    { "sessionId": "abc-123", "message": "My answer here..." }
    ```
    Returns `{ "reply": "...", "done": false }` or the final
    `{ "reply": "Interview completed.", "done": true, "feedback": {...} }`

    Pydantic validates all fields before this function is called:
    - `sessionId` must be non-empty
    - Exactly one of `candidate` or `message` must be present
    - `message` must be non-empty when provided
    """
    session_id = req.sessionId  # already stripped by the validator

    # ── START ─────────────────────────────────────────────────────────────────
    if req.candidate is not None:
        # Pass the candidate as a plain dict so data_manager can process it.
        # model_dump() produces the flat format; data_manager accepts both flat
        # and legacy-wrapped formats.
        candidate_dict = req.candidate.model_dump(by_alias=False)

        try:
            reply = dialogue_manager.start_interview(session_id, candidate_dict)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except Exception as exc:
            logger.exception("Error starting interview for session '%s'", session_id)
            raise HTTPException(status_code=500, detail=f"Failed to start interview: {exc}")

        return {"reply": reply, "done": False}

    # ── TURN ──────────────────────────────────────────────────────────────────
    message = req.message.strip()  # guaranteed non-empty by schema validator

    try:
        return dialogue_manager.process_message(session_id, message)

        if result.get("done"):
        return {
            "reply": result["reply"],
            "done": True,
            "feedback": result["feedback"]
        }
    else:
        return {
            "reply": result["reply"],
            "done": False
        }
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Session '{session_id}' not found. "
                "Start the interview first by sending a 'candidate' payload."
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=410, detail=str(exc))
    except Exception as exc:
        logger.exception("Error processing message for session '%s'", session_id)
        raise HTTPException(status_code=500, detail=f"Failed to process message: {exc}")


# ── GET /api/interview/status ─────────────────────────────────────────────────

@app.get(
    "/api/interview/status",
    summary="Session debug counters",
    responses={404: {"description": "Session not found"}},
)
def session_status(sessionId: str):
    """
    Return live session counters for testing and debugging.
    Not required by the spec — useful for test scripts.
    """
    raw = session_store.get_session(sessionId.strip())
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Session '{sessionId}' not found.")
    return {
        "sessionId":        sessionId,
        "question_count":   raw.get("question_count", 0),
        "covered_days":     sorted(set(raw.get("covered_days", []))),
        "interview_stage":  raw.get("interview_stage", "UNKNOWN"),
        "pending_follow_up": raw.get("pending_follow_up", {}),
    }
