import logging
from typing import List, Dict, Any
from app.services.data_manager import get_openai_client

logger = logging.getLogger(__name__)

def generate_initial_question(candidate_profile: Dict[str, Any], day_metadata: Dict[str, Any]) -> str:
    """
    Generate a welcome message and the very first interview question.
    """
    client = get_openai_client()
    
    prompt = f"""You are an expert technical interviewer for an AI engineering cohort.
Generate a professional, warm welcome message and the first question for the candidate.

Candidate Profile:
- Name: {candidate_profile.get('name')}
- Job Role: {candidate_profile.get('job_role')}
- Experience Level: {candidate_profile.get('experience_level')}

Target First Topic:
- Day: {day_metadata.get('day')}
- Title: {day_metadata.get('title')}
- Objectives: {", ".join(day_metadata.get('objectives', []))}
- Tools: {", ".join(day_metadata.get('tools', []))}

Instructions:
1. Greet the candidate by name, mention their job role/experience, and welcome them.
2. Introduce the first topic of the interview based on the Curriculum Day details.
3. Formulate a clear, direct technical question targeting the objectives/tools.
4. Keep the question conversational but technically rigorous.
5. If the first day is a topic they passed (completed), ask a deeper application or architectural question. If it's skipped or failed, ask a foundational question to probe their understanding.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional technical interviewer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating initial question: {e}")
        return f"Welcome {candidate_profile.get('name')}. Let's start with Day {day_metadata.get('day')}: {day_metadata.get('title')}. Could you explain your experience with {', '.join(day_metadata.get('tools', []))}?"

def generate_next_question(candidate_profile: Dict[str, Any], day_metadata: Dict[str, Any], history: List[Dict[str, str]]) -> str:
    """
    Generate the next question on a new topic, maintaining conversation flow.
    """
    client = get_openai_client()
    
    # Check if the target topic is strong or weak for the candidate
    day_title = day_metadata.get('title')
    is_strong = day_title in candidate_profile.get('strong_topics', [])
    difficulty_pref = "deep application, design, or architectural question" if is_strong else "probing, foundational technical question to test their understanding"
    
    prompt = f"""You are an expert technical interviewer. Transition the candidate to the next topic and ask a new question.

Candidate Profile:
- Job Role: {candidate_profile.get('job_role')}
- Experience Level: {candidate_profile.get('experience_level')}

Next Curriculum Day Context:
- Day: {day_metadata.get('day')}
- Title: {day_title}
- Objectives: {", ".join(day_metadata.get('objectives', []))}
- Tools: {", ".join(day_metadata.get('tools', []))}
- Difficulty Strategy: This topic is a { 'strong' if is_strong else 'weak/skipped' } area for the candidate. Ask a {difficulty_pref}.

Conversation History:
{history[-4:] if len(history) > 4 else history}

Instructions:
1. Provide a brief transition (e.g. "Let's move on to...", "Great. Now let's talk about...") based on the conversation history.
2. Ask a clear, high-quality technical question targeting the new day's objectives and tools.
3. Keep it concise (2-4 sentences max).
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional technical interviewer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating next question: {e}")
        return f"Let's move on to Day {day_metadata.get('day')}: {day_metadata.get('title')}. Can you explain how you work with {', '.join(day_metadata.get('tools', []))}?"

def generate_follow_up(question: str, vague_answer: str, history: List[Dict[str, str]]) -> str:
    """
    Generate a follow-up question probing the candidate's vague or brief response.
    """
    client = get_openai_client()
    
    prompt = f"""You are an expert technical interviewer. The candidate gave a vague, brief, or evasive response to your last question. Probing is required.

Last Question Asked: {question}
Candidate's Vague Response: {vague_answer}

Conversation Context (recent history):
{history[-4:] if len(history) > 4 else history}

Instructions:
1. Formulate a polite but targeted follow-up question.
2. Ask them to elaborate on specific details, explain the 'why', or clarify what they meant.
3. Keep it brief (1-2 sentences). Do not transition to a new topic.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional technical interviewer probing for depth."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating follow-up: {e}")
        return f"Could you elaborate more on that? Please specify the tools or methods you used in this context."
