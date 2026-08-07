import logging
from typing import List, Dict, Any
from app.schemas import Feedback
from app.services.data_manager import get_openai_client

logger = logging.getLogger(__name__)

def generate_feedback(candidate_profile: Dict[str, Any], qa_records: List[Dict[str, Any]]) -> Feedback:
    """
    Generate final interview evaluation feedback using GPT-4o.
    Outputs a structured Feedback schema.
    """
    client = get_openai_client()
    
    # Format the QA records into a readable string for the prompt
    qa_summary_list = []
    for record in qa_records:
        qa_summary_list.append(
            f"Topic (Day {record.get('day')}): {record.get('day_title')}\n"
            f"- Question: {record.get('question')}\n"
            f"- Answer: {record.get('answer')}\n"
            f"- Evaluation: Vague={record.get('is_vague')}, Correct={record.get('is_correct')}\n"
            f"- Evaluator Notes: {record.get('evaluation_notes')}\n"
        )
    qa_history_text = "\n".join(qa_summary_list)
    
    prompt = f"""You are an expert technical evaluator. Analyze the candidate's interview performance and generate a final evaluation report.

Candidate Profile:
- Name: {candidate_profile.get('name')}
- Job Role: {candidate_profile.get('job_role')}
- Experience Level: {candidate_profile.get('experience_level')}

Interview QA Record:
{qa_history_text}

Instructions:
1. Provide a comprehensive summary of their performance (2-4 sentences). It should assess their general level of readiness and technical communication.
2. Identify a list of specific strengths demonstrated in their correct answers. (Provide 2-4 points).
3. Identify a list of gaps/areas of improvement based on vague or incorrect answers. (Provide 2-4 points).
4. Recommend concrete next steps / learning paths based on gaps. (Provide 2-4 points).

Output in the specified structured schema.
"""

    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional technical evaluator who compiles structured interview feedback."},
                {"role": "user", "content": prompt}
            ],
            response_format=Feedback,
            temperature=0.0
        )
        return response.choices[0].message.parsed
    except Exception as e:
        logger.error(f"Error generating feedback: {e}")
        # Graceful fallback: return a default report to not crash
        return Feedback(
            summary=f"Interview completed. Technical evaluation fallback due to generation error: {e}",
            strengths=["Demonstrated engagement in technical discussion."],
            gaps=["Needs deeper technical validation."],
            next=["Review standard interview materials."]
        )
