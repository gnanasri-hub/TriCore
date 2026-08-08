from typing import Dict, Any

# In-memory store: sessionId -> session data
sessions: Dict[str, Any] = {}

def get_session(session_id: str) -> Any:
    return sessions.get(session_id)

def create_or_update_session(session_id: str, data: Any):
    sessions[session_id] = data
