import logging
from pydantic import BaseModel
from app import config
from app.services.data_manager import get_openai_client

logger = logging.getLogger(__name__)

class EvaluationResult(BaseModel):
    is_vague: bool
    is_correct: bool
    evaluation_notes: str

def evaluate_answer(question: str, answer: str, day_metadata: dict) -> EvaluationResult:
    """
    Evaluate candidate's answer using GPT-4o with structured outputs.
    Checks if the answer is vague/evasive and if the technical content is correct.
    """
    client = get_openai_client()
    
    prompt = f"""You are an expert technical interviewer for an AI engineering cohort.
Evaluate the candidate's response to the interview question based on the curriculum topic.

Curriculum Day Context:
- Day: {day_metadata.get('day')}
- Title: {day_metadata.get('title')}
- Objectives: {", ".join(day_metadata.get('objectives', []))}
- Tools: {", ".join(day_metadata.get('tools', []))}

Interview Context:
- Question Asked: {question}
- Candidate's Response: {answer}

Your job is to determine:
1. is_vague: Set to true if the response is evasive, overly generic, too brief (e.g. just repeating the question), or fails to actually answer the specific question asked. Set to false if they gave a clear, direct answer.
2. is_correct: Set to true if their response demonstrates correct technical understanding of the topic and tools, or false if they make incorrect statements or display severe misunderstandings.
3. evaluation_notes: A concise note (1-2 sentences) explaining your reasoning (what they answered well, what they missed, or why it was vague).
"""

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise technical evaluator."},
                {"role": "user", "content": prompt}
            ],
            response_format=EvaluationResult,
            temperature=0.0
        )
        return response.choices[0].message.parsed
    except Exception as e:
        logger.error(f"Error evaluating answer with LLM: {e}")
        # Graceful fallback: treat as correct and not vague to not block the conversation
        return EvaluationResult(
            is_vague=False,
            is_correct=True,
            evaluation_notes=f"Fallback evaluation due to API error: {e}"
        )
