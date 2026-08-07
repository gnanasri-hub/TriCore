import os
from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field
from openai import AsyncOpenAI

# Use the API key from environment variable
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class Evaluation(BaseModel):
    technical_accuracy: int = Field(ge=0, le=10, description="Technical accuracy score from 0 to 10")
    depth: int = Field(ge=0, le=10, description="Depth of the answer from 0 to 10")
    clarity: int = Field(ge=0, le=10, description="Clarity of the answer from 0 to 10")
    is_vague: bool = Field(description="Whether the answer is vague or too short")
    is_strong: bool = Field(description="Whether the answer is particularly strong and detailed")
    is_incomplete: bool = Field(description="Whether the answer misses key parts of the question")
    strengths: List[str] = Field(description="Concrete strengths of the answer")
    missing_points: List[str] = Field(description="Important missing points or inaccuracies")

async def evaluate_answer(question: str, answer: str, curriculum_context: str) -> Evaluation:
    """
    Evaluates the candidate's answer using GPT-4o based on the question and curriculum context.
    Returns an Evaluation object.
    """
    system_prompt = f"""You are an expert technical interviewer evaluating a candidate's answer.
Question asked: {question}
Expected curriculum context: {curriculum_context}

Evaluate the candidate's answer based on technical accuracy, depth, and clarity.
Determine if the answer is vague, strong, or incomplete.
Extract concrete strengths and missing points."""
    
    response = await client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Candidate's answer: {answer}"}
        ],
        response_format=Evaluation,
    )
    
    return response.choices[0].message.parsed

def decide_next_action(evaluation: Evaluation, session: Any) -> Literal["follow_up", "new_question", "end"]:
    """
    Decides the next action based on the evaluation and session state.
    Limits to maximum 1 follow-up per main question.
    """
    # session can be a SessionState object or dictionary depending on the store implementation
    if isinstance(session, dict):
        pending = session.get("pending_follow_up", {})
        question_count = session.get("question_count", 0)
    else:
        # Assuming SessionState model
        pending = getattr(session, "pending_follow_up", {})
        question_count = getattr(session, "question_count", 0)
        
    # Check if the current answer is already a response to a follow-up
    # We assume 'is_active' is set to True when a follow-up is pending
    is_answering_follow_up = pending.get("is_active", False)
    
    # If we've reached a max question limit (e.g. 5 or 10), we could return 'end'.
    # We don't have the max count here, so this is just a placeholder logic for 'end'
    # if question_count >= 10 and not is_answering_follow_up:
    #     return "end"

    if is_answering_follow_up:
        # Limit to 1 follow-up per main question
        return "new_question"
        
    if evaluation.is_vague or evaluation.is_incomplete:
        # Vague or short/incomplete answers -> always ask a clarifying follow-up
        return "follow_up"
        
    if evaluation.is_strong:
        # Strong answers -> either escalate difficulty on same topic (follow_up) 
        # or move to harder related topic (new_question)
        # Let's use a heuristic: if depth is perfect, move on. Otherwise, escalate.
        if evaluation.depth < 10:
            return "follow_up"
        return "new_question"
        
    # Default fallback
    return "new_question"

async def generate_follow_up(evaluation: Evaluation, question: str, answer: str) -> str:
    """
    Generates a follow-up question based on the evaluation of the candidate's answer.
    """
    system_prompt = f"""You are a technical interviewer. 
The original question was: {question}
The candidate's answer was: {answer}

The evaluation of this answer found:
Vague: {evaluation.is_vague}
Strong: {evaluation.is_strong}
Incomplete: {evaluation.is_incomplete}
Strengths: {', '.join(evaluation.strengths) if evaluation.strengths else 'None'}
Missing points: {', '.join(evaluation.missing_points) if evaluation.missing_points else 'None'}

Your task is to generate ONE follow-up question. 
- If the answer was vague or incomplete, ask them to clarify or fill in the missing points.
- If the answer was strong, ask a challenging follow-up question to probe their depth of knowledge on the same topic.
Keep the question concise and conversational."""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the follow-up question."}
        ]
    )
    
    return response.choices[0].message.content.strip()
