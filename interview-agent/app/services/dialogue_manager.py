import logging
from typing import Dict, Any, List, Optional

from app import session_store
from app.schemas import InterviewResponse, Feedback
from app.services import data_manager, evaluator, question_generator, feedback_generator

logger = logging.getLogger(__name__)

def select_next_day(candidate_profile: Dict[str, Any], covered_days: List[int]) -> Optional[Dict[str, Any]]:
    """
    Select the next curriculum day topic based on candidate profile prioritization:
      1. Probing skipped or failed days.
      2. Job role relevance (via semantic search).
      3. Deep questions on topics passed easily (strong topics).
      4. General fallback.
    """
    all_days = data_manager.get_all_days_metadata()
    if not all_days:
        logger.warning("No curriculum days metadata available.")
        return None
        
    covered_set = set(covered_days)
    
    # 1. Probing: skipped/failed days
    weak_day_nums = set(candidate_profile.get("skipped_days", []) + candidate_profile.get("failed_days", []))
    available_weak = [d for d in all_days if d["day"] in weak_day_nums and d["day"] not in covered_set]
    if available_weak:
        return available_weak[0]
        
    # 2. Job Role Relevance: semantic match to candidate's job role
    job_role = candidate_profile.get("job_role", "")
    if job_role:
        relevant_days = data_manager.retrieve_relevant_days(job_role, top_k=10)
        available_relevant = [d for d in relevant_days if d["day"] not in covered_set]
        if available_relevant:
            day_num = available_relevant[0]["day"]
            return data_manager.get_day_metadata(day_num)
            
    # 3. Deep probing: topics passed easily (strong topics)
    # Strong topics are completed days that are not failed or skipped
    completed_set = set(candidate_profile.get("completed_days", []))
    strong_day_nums = completed_set - weak_day_nums
    available_strong = [d for d in all_days if d["day"] in strong_day_nums and d["day"] not in covered_set]
    if available_strong:
        return available_strong[0]
        
    # 4. General fallback: any remaining uncovered days
    available_fallback = [d for d in all_days if d["day"] not in covered_set]
    if available_fallback:
        return available_fallback[0]
        
    # If everything is covered, return any day not covered or just None
    return None

def start_interview(session_id: str, candidate_data: Dict[str, Any]) -> str:
    """
    Initialize session state, profile candidate, select first topic,
    generate welcome + initial question, and save state.
    """
    # 1. Profile candidate using the Data Manager
    profile = data_manager.get_candidate_profile(candidate_data)
    
    # 2. Select the first curriculum day
    covered_days = []
    first_day_meta = select_next_day(profile, covered_days)
    if not first_day_meta:
        raise ValueError("Could not select a curriculum day to begin the interview.")
        
    day_num = first_day_meta["day"]
    covered_days.append(day_num)
    
    # 3. Generate initial question
    welcome_question = question_generator.generate_initial_question(profile, first_day_meta)
    
    # 4. Create Session State
    session_state = {
        "session_id": session_id,
        "candidate_profile": profile,
        "history": [
            {"role": "assistant", "content": welcome_question}
        ],
        "qa_records": [],
        "covered_days": covered_days,
        "current_day": day_num,
        "question_count": 1,
        "pending_follow_up": {
            "is_pending": False,
            "follow_up_question": "",
            "original_question": "",
            "vague_answer": ""
        },
        "interview_stage": "INTERVIEWING"
    }
    
    # 5. Save State
    session_store.create_or_update_session(session_id, session_state)
    return welcome_question

def should_end(state: Dict[str, Any]) -> bool:
    """
    Enforce ending rules:
      - At least 8 questions asked.
      - Covered at least 4 distinct curriculum days.
    """
    question_count = state.get("question_count", 0)
    covered_days = state.get("covered_days", [])
    
    return question_count >= 8 and len(covered_days) >= 4

def process_message(session_id: str, message: str) -> InterviewResponse:
    """
    Process candidate message:
      1. Evaluate answer.
      2. If vague (and not already in follow-up), ask a follow-up.
      3. Else, save Q&A evaluation, decide to end or generate new topic question.
    """
    state = session_store.get_session(session_id)
    if not state:
        # Fallback initialization if session wasn't started explicitly with candidate
        # We start with empty candidate data
        logger.warning(f"Session {session_id} not initialized. Starting default interview.")
        default_candidate = {
            "member": {"id": "CAND-DEFAULT", "name": "Candidate", "jobRole": "AI Engineer", "yearsExperience": 2},
            "missions": [],
            "signals": {}
        }
        reply = start_interview(session_id, default_candidate)
        return InterviewResponse(reply=reply, done=False)
        
    profile = state["candidate_profile"]
    current_day = state["current_day"]
    current_day_meta = data_manager.get_day_metadata(current_day)
    
    # Determine the question that candidate is responding to
    pending_follow_up = state["pending_follow_up"]
    if pending_follow_up["is_pending"]:
        last_question = pending_follow_up["follow_up_question"]
    else:
        # The last assistant message in history
        last_question = ""
        for msg in reversed(state["history"]):
            if msg["role"] == "assistant":
                last_question = msg["content"]
                break
                
    # 1. Evaluate answer
    evaluation = evaluator.evaluate_answer(last_question, message, current_day_meta)
    
    # Append user response to history
    state["history"].append({"role": "user", "content": message})
    
    # 2. Trigger follow-up if response is vague and we aren't already in a follow-up
    if evaluation.is_vague and not pending_follow_up["is_pending"]:
        logger.info(f"Vague response detected on Day {current_day}. Generating follow-up.")
        
        # Generate follow-up
        follow_up_text = question_generator.generate_follow_up(last_question, message, state["history"])
        
        # Update follow-up status
        state["pending_follow_up"] = {
            "is_pending": True,
            "follow_up_question": follow_up_text,
            "original_question": last_question,
            "vague_answer": message
        }
        
        # Log the follow-up question to history
        state["history"].append({"role": "assistant", "content": follow_up_text})
        
        # Increment total question count
        state["question_count"] += 1
        
        # Save state and return follow-up question
        session_store.create_or_update_session(session_id, state)
        return InterviewResponse(reply=follow_up_text, done=False)
        
    # 3. Handle non-vague response or resolved follow-up response
    # Register QA record
    if pending_follow_up["is_pending"]:
        combined_answer = f"Initial (Vague): {pending_follow_up['vague_answer']} | Follow-up: {message}"
        original_q = pending_follow_up["original_question"]
        qa_rec = {
            "day": current_day,
            "day_title": current_day_meta.get("title", ""),
            "question": original_q,
            "answer": combined_answer,
            "is_vague": evaluation.is_vague,
            "is_correct": evaluation.is_correct,
            "evaluation_notes": evaluation.evaluation_notes
        }
        # Clear follow-up state
        state["pending_follow_up"] = {
            "is_pending": False,
            "follow_up_question": "",
            "original_question": "",
            "vague_answer": ""
        }
    else:
        qa_rec = {
            "day": current_day,
            "day_title": current_day_meta.get("title", ""),
            "question": last_question,
            "answer": message,
            "is_vague": False,
            "is_correct": evaluation.is_correct,
            "evaluation_notes": evaluation.evaluation_notes
        }
        
    state["qa_records"].append(qa_rec)
    
    # 4. Check if interview should end
    if should_end(state):
        logger.info(f"Ending interview for session {session_id}. Generating final feedback.")
        feedback = feedback_generator.generate_feedback(profile, state["qa_records"])
        state["interview_stage"] = "COMPLETED"
        session_store.create_or_update_session(session_id, state)
        
        return InterviewResponse(
            reply="Thank you! We have completed the interview and evaluated your responses.",
            done=True,
            feedback=feedback
        )
        
    # 5. Transition to next topic
    next_day_meta = select_next_day(profile, state["covered_days"])
    if not next_day_meta:
        # Fallback if somehow we run out of days (highly unlikely with 31 days)
        # We end early in this case to avoid crashing
        logger.warning("No more curriculum days available. Ending early.")
        feedback = feedback_generator.generate_feedback(profile, state["qa_records"])
        state["interview_stage"] = "COMPLETED"
        session_store.create_or_update_session(session_id, state)
        return InterviewResponse(
            reply="Thank you! The interview is complete.",
            done=True,
            feedback=feedback
        )
        
    next_day_num = next_day_meta["day"]
    state["covered_days"].append(next_day_num)
    state["current_day"] = next_day_num
    
    # Generate new topic question
    next_question = question_generator.generate_next_question(profile, next_day_meta, state["history"])
    state["history"].append({"role": "assistant", "content": next_question})
    
    # Increment question count for the new topic question
    state["question_count"] += 1
    
    # Save State
    session_store.create_or_update_session(session_id, state)
    return InterviewResponse(reply=next_question, done=False)
