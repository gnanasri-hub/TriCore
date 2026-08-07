import os
from openai import OpenAI
from app.schemas import SessionState, Feedback

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def generate_feedback(session: SessionState) -> dict:
    """
    Generates a final overall feedback based on the session state.
    Matches the exact schema in technical-spec.md using GPT-4o.
    """
    candidate_profile = session.candidate_profile
    qa_records = session.qa_records
    
    # Summarize QA records for the prompt context
    qa_summary_parts = []
    for idx, record in enumerate(qa_records):
        question = record.get("question", "")
        answer = record.get("answer", "")
        eval_dict = record.get("evaluation", {})
        
        accuracy = eval_dict.get('technical_accuracy', 'N/A')
        depth = eval_dict.get('depth', 'N/A')
        strengths = eval_dict.get('strengths', [])
        gaps = eval_dict.get('missing_points', [])
        
        qa_summary_parts.append(
            f"Q{idx+1}: {question}\n"
            f"A{idx+1}: {answer}\n"
            f"Eval: Accuracy={accuracy}/10, Depth={depth}/10.\n"
            f"Strengths: {strengths}\n"
            f"Gaps: {gaps}"
        )
    
    qa_summary = "\n\n".join(qa_summary_parts)
    
    # Summarize missions performance
    missions = candidate_profile.get("missions", [])
    missions_summary = []
    for m in missions:
        status = "Passed" if m.get("passed") else ("Skipped" if m.get("skipped") else "Failed")
        attempts = m.get("attempts", 0)
        missions_summary.append(f"- {m.get('title', 'Unknown')}: {status} ({attempts} attempts)")
    
    missions_str = "\n".join(missions_summary)
    
    system_prompt = f"""You are a senior technical interviewer writing final structured feedback after an interview with a candidate who completed a 31-day AI engineering cohort.

You will receive:
- The candidate’s original profile (missions completed, skipped, failed, attempts, job role, experience)
- The full list of questions asked and their answers + evaluations during this interview

Produce feedback that is balanced, specific, constructive, and professional.

Guidelines:
- Reference concrete topics from the curriculum when possible.
- Strengths should highlight what the candidate demonstrated well.
- Gaps should focus on areas that were weak, skipped, or poorly explained.
- “next” should contain practical, actionable next steps.
- Keep every bullet concise (one clear sentence each).
- Tone: professional, encouraging, and honest.

--- 
Candidate Profile:
Name: {candidate_profile.get('name', 'Unknown')}
Role: {candidate_profile.get('jobRole', 'Unknown')}
Experience: {candidate_profile.get('yearsExperience', '0')} years

Mission Performance:
{missions_str}

Interview Q&A Records:
{qa_summary}"""

    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the final feedback."}
        ],
        response_format=Feedback,
    )
    
    return response.choices[0].message.parsed.model_dump()
