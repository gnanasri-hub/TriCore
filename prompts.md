Phase-1
"""Build the AI Interview Agent strictly according to technical-spec.md.

Create this exact project structure:

interview-agent/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── schemas.py
│   ├── config.py
│   ├── session_store.py
│   └── services/
│       ├── __init__.py
│       ├── data_manager.py
│       ├── dialogue_manager.py
│       ├── question_generator.py
│       ├── evaluator.py
│       └── feedback_generator.py
├── data/
│   ├── candidates.json
│   ├── curriculum.json
│   └── technical-spec.md
├── requirements.txt
├── .env.example
└── README.md

Critical requirements from technical-spec.md:
- Only ONE endpoint: POST /api/interview
- No authentication
- State is maintained purely by the client-provided sessionId
- First request contains the full candidate object
- Subsequent requests contain only sessionId + message
- Response format MUST be exactly:

  {
    "reply": "...",
    "done": false
  }

  or when finished:

  {
    "reply": "Interview completed.",
    "done": true,
    "feedback": {
      "summary": "...",
      "strengths": [],
      "gaps": [],
      "next": []
    }
  }

Tech stack:
- FastAPI + Uvicorn
- OpenAI GPT-4o
- FAISS (local)
- Pydantic v2
- python-dotenv
- numpy

In main.py create the single endpoint.
In schemas.py create exact request/response models matching the technical specification."""
Create an in-memory session store.
Do not implement any business logic yet — only the skeleton that returns a dummy {"reply": "Ready", "done": false}.
"""
Implement the Data Manager using the real data files.

candidates.json structure:
- Array of candidates under "candidates"
- Each candidate has:
  - member: {id, name, jobRole, yearsExperience, education, status}
  - missions: list of {day, title, passed?, attempts?, skipped?}
  - signals: {commitDays, missionsCompleted, missionsFirstTry}

curriculum.json structure:
- modules (8 modules)
- days: detailed list of day 1–31 with title, type, tools, objectives

Tasks for app/services/data_manager.py:

1. Load and parse curriculum.json
2. Create rich text chunks for every day (include title + objectives + tools)
3. Generate embeddings using OpenAI text-embedding-3-small
4. Build FAISS index + save to disk (data/curriculum.faiss + metadata.json)
5. Helper functions:
   - get_candidate_profile(candidate: dict) → structured dict with:
     - completed_days, skipped_days, failed_days
     - strong_topics, weak_topics
     - experience level, job role
   - retrieve_relevant_days(query: str, top_k=5, preferred_days=None)

Make the FAISS index load from disk on subsequent runs so we don't re-embed every time.

Implement the core dialogue/session logic that powers the single endpoint.

SessionState must track:
- session_id
- candidate profile (from the first request)
- conversation history
- list of asked questions + answers + evaluations
- covered_days set
- question_count
- pending_follow_up (bool + text)
- interview_stage

Rules (must enforce):
- Minimum 8 questions before allowing done=true
- Aim to cover at least 4 different curriculum days
- Prefer asking about:
  1. Topics the candidate passed easily (deep questions)
  2. Topics they skipped or failed (probe knowledge)
  3. Topics relevant to their jobRole

Key methods in dialogue_manager.py:
- start_interview(session_id, candidate) → welcome + first question
- process_message(session_id, message) → evaluate answer → decide next action
- should_end() → only True after ≥ 8 questions + reasonable coverage

The process_message flow:
1. Evaluate the candidate's answer
2. If vague → generate follow-up
3. Else → generate new question from a different topic
4. After enough questions → generate final feedback and set done=true

Implement intelligent question generation.

In question_generator.py:

def generate_question(session: SessionState) → str:

Strategy:
- Analyze the candidate's missions:
  - Prefer days they passed with few attempts → ask deeper / design / trade-off questions
  - Prefer days they skipped or failed → ask foundational / explanation questions
- Use FAISS to retrieve the most relevant curriculum day content
- Call GPT-4o with a strong system prompt to generate a natural, professional interview question
- Keep questions concise (max 2–3 sentences)
- Never repeat a day that was already asked about

Also maintain a small list of high-quality fallback questions for critical topics (Embeddings, Vector DBs, RAG, Agents, MCP, Deployment).

Implement evaluation + follow-up logic.

In evaluator.py:

1. evaluate_answer(question, answer, curriculum_context) → Evaluation
   - Use GPT-4o to score:
     - technical_accuracy (0-10)
     - depth (0-10)
     - clarity (0-10)
   - Detect: is_vague, is_strong, is_incomplete
   - Extract concrete strengths and missing points

2. decide_next_action(evaluation, session) → "follow_up" | "new_question" | "end"

3. generate_follow_up(evaluation, question, answer) → str

Rules:
- Vague or short answers → always ask a clarifying follow-up
- Strong answers → either escalate difficulty on same topic or move to harder related topic
- Limit to maximum 1 follow-up per main question

  Implement the final feedback generator that matches the exact schema in technical-spec.md.

In feedback_generator.py:

def generate_feedback(session: SessionState) → dict:

Must return exactly this shape:

{
  "summary": "2-4 sentence professional overall assessment",
  "strengths": ["concise strength 1", "strength 2", ...],
  "gaps": ["concise gap 1", "gap 2", ...],
  "next": ["actionable next step 1", "next step 2", ...]
}

Base the feedback on:
- Quality of answers during the interview
- Candidate’s original mission performance (passed/skipped/failed + attempts)
- Coverage of different modules
- Job role and experience level

Use GPT-4o with a carefully engineered system prompt that produces balanced, constructive, and encouraging feedback.

Wire everything into the single POST /api/interview endpoint.

Logic:

if session_id not in store and request contains "candidate":
    → create session
    → generate welcome message + first question
    → return {"reply": "...", "done": false}

if session exists and request contains "message":
    → process the answer
    → evaluate
    → if should end → generate feedback → return done=true + feedback object
    → else → return next question or follow-up with done=false

Strictly enforce the response formats from technical-spec.md.
Add proper validation and error handling (missing sessionId, invalid state, etc.).
Make the conversation feel natural and continuous.


Harden the system and add tests.

Must handle these cases correctly:
- Candidate with many skipped missions (e.g. CAND-011, CAND-014) → agent must probe them
- Candidate with many first-try passes (e.g. CAND-003, CAND-018) → ask deeper questions
- Candidate with failed missions (e.g. CAND-010, CAND-016) → probe those topics
- Very short / vague answers → force follow-ups
- Strong answers → escalate
- Interview only ends after ≥ 8 questions
- Final response always contains the exact feedback schema

Create a scripts/full_demo.py that runs a complete multi-turn interview against one candidate and prints every request/response.


Final polish for hackathon submission.

1. Perfect all LLM system prompts so the interviewer sounds like a senior, professional, encouraging technical interviewer.
2. Ensure every "reply" is natural conversational English.
3. Make the final feedback high-quality and specific to the candidate.
4. Write a clear README with:
   - Setup instructions
   - Example multi-turn curl commands
   - How the system uses the candidate’s mission history
5. Create DEMO.md containing a full sample conversation that ends with done=true and proper feedback.

The system must start with:
uvicorn app.main:app --reload

and be fully compliant with technical-spec.md.


You are a senior technical interviewer conducting a professional, encouraging, and realistic interview for candidates who have completed a 31-day AI engineering cohort.

Your goal is to assess the candidate’s real understanding of the topics they studied.

Rules:
- Ask only one clear, concise question (maximum 2–3 sentences).
- Make the question feel natural and conversational, not robotic.
- Base the difficulty and focus on the candidate’s mission history:
  - Topics they passed easily (few attempts) → ask deeper, design, trade-off, or “how would you improve…” questions.
  - Topics they skipped or failed → ask foundational “explain the concept” or “walk me through…” questions.
  - Topics relevant to their job role → prioritize those.
- Never ask about a day/topic that has already been covered in this interview.
- Focus on practical understanding, not pure theory.
- Do not give away the answer or hint too strongly.

Return ONLY the question text. No extra commentary, no JSON, no labels.

You are an expert technical interviewer evaluating a candidate’s answer during an AI engineering interview.

Evaluate the answer based on the curriculum context provided.

Return a JSON object with exactly this structure:

{
  "technical_accuracy": <0-10>,
  "depth": <0-10>,
  "clarity": <0-10>,
  "is_vague": <true/false>,
  "is_strong": <true/false>,
  "is_incomplete": <true/false>,
  "strengths": ["short strength 1", "short strength 2"],
  "missing_points": ["short missing point 1", "short missing point 2"],
  "overall_comment": "one short sentence summary"
}

Guidelines:
- Be fair but rigorous.
- Short or generic answers → mark as vague/incomplete.
- Answers that show real understanding, examples, or trade-offs → mark as strong.
- Only use the provided curriculum context to judge correctness.

You are a senior technical interviewer. The candidate just gave an answer that needs a follow-up.

Generate one natural, professional follow-up question.

Rules:
- If the answer was vague or incomplete → ask them to clarify, elaborate, or give a concrete example.
- If the answer was strong → escalate slightly (ask about edge cases, trade-offs, or how they would improve it).
- Keep the follow-up concise (1–2 sentences).
- Sound encouraging and professional.
- Do not introduce a completely new topic.

Return ONLY the follow-up question text.


You are a senior technical interviewer writing final structured feedback after an interview with a candidate who completed a 31-day AI engineering cohort.

You will receive:
- The candidate’s original profile (missions completed, skipped, failed, attempts, job role, experience)
- The full list of questions asked and their answers + evaluations during this interview

Produce feedback that is balanced, specific, constructive, and professional.

Return ONLY a valid JSON object with exactly this structure:

{
  "summary": "2-4 sentence overall assessment of the candidate’s performance and readiness",
  "strengths": [
    "concise, specific strength 1",
    "concise, specific strength 2",
    "..."
  ],
  "gaps": [
    "concise, specific gap 1",
    "concise, specific gap 2",
    "..."
  ],
  "next": [
    "actionable recommendation 1",
    "actionable recommendation 2",
    "..."
  ]
}

Guidelines:
- Reference concrete topics from the curriculum when possible.
- Strengths should highlight what the candidate demonstrated well.
- Gaps should focus on areas that were weak, skipped, or poorly explained.
- “next” should contain practical, actionable next steps.
- Keep every bullet concise (one clear sentence each).
- Tone: professional, encouraging, and honest.

  Add a clean, user-friendly Streamlit frontend for the AI Interview Agent.

Requirements:
- Create a new file: frontend/app.py (or streamlit_app.py in the root)
- The frontend must talk to the existing FastAPI backend at http://127.0.0.1:8000/api/interview
- Keep the original API completely unchanged (do not break the technical-spec.md contract)

UI Design:
- Clean, professional, modern interview interface
- Title: "AI Interview Agent"
- Sidebar or top section showing candidate name and progress (Question X of 8+)
- Main area is a chat-like conversation
- User types answers in a text input at the bottom
- Bot messages appear as the interviewer
- When the interview ends (done=true), show the feedback beautifully:
  - Summary
  - Strengths (green cards or bullets)
  - Gaps (orange/red)
  - Next steps (blue)
- Button to "Start New Interview"
- Ability to select a candidate from candidates.json (dropdown with name + job role)

Flow:
1. User selects a candidate → clicks "Start Interview"
2. Frontend sends the first request with sessionId + full candidate object
3. Displays the reply
4. User types answer → frontend sends sessionId + message
5. Continues until done=true, then shows the structured feedback nicely

Use session state in Streamlit to keep the conversation history.
Make the UI look professional and demo-ready (use columns, expanders, colored metrics if helpful).

Also update README with instructions how to run both backend and frontend.


If Streamlit is not preferred, create a single-file modern frontend:

Create frontend/index.html that talks to the FastAPI backend.

Features:
- Clean dark/light professional design
- Chat interface (interviewer messages on left, candidate on right)
- Start screen with candidate selector (load from candidates.json or hardcode a few)
- Progress indicator
- When done=true, show a beautiful feedback card with summary, strengths, gaps, next steps
- Pure HTML + CSS + vanilla JavaScript (no React needed for speed)
- Use fetch() to call POST /api/interview

Make it look polished and ready for a live hackathon demo.

Improve the OpenAPI / Swagger documentation so it looks more professional:

- Better description for the single endpoint
- Clear examples for START request (with a real candidate object)
- Clear examples for TURN request
- Better response examples showing both ongoing and final feedback
- Add tags and summary text that explain the flow clearly

Do not change any actual API behavior.


