Prompt 1. Initialization Prompt

Build an AI Interview Agent backend strictly following technical-spec.md.

Hard constraints:
- Only ONE API endpoint: POST /api/interview
- No authentication, no user accounts
- Stateless server; all state tied to client-provided sessionId
- First request MUST contain candidate object
- Subsequent requests MUST contain only sessionId + message
- No additional endpoints allowed (except optional debug)

Response format MUST be EXACT:

For ongoing:
{
  "reply": "<string>",
  "done": false
}

For completion:
{
  "reply": "Interview completed.",
  "done": true,
  "feedback": {
    "summary": "<string>",
    "strengths": [<string>],
    "gaps": [<string>],
    "next": [<string>]
  }
}

Tech stack:
- FastAPI + Uvicorn
- Pydantic v2
- python-dotenv

Goal (IMPORTANT):
Return ONLY a minimal working skeleton:
- FastAPI app
- Single endpoint defined
- No business logic
- Always returns: {"reply": "Ready", "done": false}

Do NOT:
- implement AI logic
- implement FAISS
- implement evaluation
- add extra routes




Prompt 2 :Project Structure Prompt

Create the exact project structure for the AI Interview Agent.

Structure MUST match exactly:

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

Rules:
- All files must exist (even if empty)
- Add placeholder classes/functions with docstrings explaining purpose
- No business logic yet
- Ensure imports are valid and project runs without errors

Output:
- Fully compilable skeleton project
- main.py must start FastAPI server successfully




Prompt 3: Data Manager Prompt

Implement app/services/data_manager.py using real data files.

Data assumptions:

candidates.json:
- root key: "candidates"
- each item:
  - member: {id, name, jobRole, yearsExperience, education, status}
  - missions: [{day, title, passed, attempts, skipped}]
  - signals: {commitDays, missionsCompleted, missionsFirstTry}

curriculum.json:
- modules (high-level grouping)
- days (1–31):
  - title
  - type
  - tools
  - objectives

Tasks:

1. Load curriculum.json and normalize it
2. For each day:
   - create a rich text chunk:
     "Day X: <title>\nTools: ...\nObjectives: ..."
3. Generate embeddings using OpenAI model:
   text-embedding-3-small

4. Build FAISS index:
   - store vectors
   - maintain metadata (day number, topic)

5. Persist to disk:
   - data/curriculum.faiss
   - data/metadata.json

6. On restart:
   - load FAISS index instead of recomputing

7. Implement helper functions:

get_candidate_profile(candidate):
- derive:
  - completed_days
  - skipped_days
  - failed_days
  - strong_topics (few attempts)
  - weak_topics (failed/skipped)
  - job role + experience level

retrieve_relevant_days(query, top_k=5, preferred_days=None):
- semantic search using FAISS
- boost preferred_days if provided

Important constraints:
- Do NOT recompute embeddings every request
- Must be efficient
- Must handle missing/dirty data gracefully



Prompt 4: Dialogue / Session Logic Prompt

Implement app/services/dialogue_manager.py.

Define a SessionState object:

Fields:
- session_id
- candidate_profile
- conversation_history (list of messages)
- asked_questions (list)
- evaluations (list)
- covered_days (set)
- question_count (int)
- pending_follow_up (dict or None)
- interview_stage (string)

Core rules (STRICT):

1. Minimum 8 questions before interview can end
2. Must cover at least 4 different curriculum days
3. Question priority:
   - strong topics → deep questions
   - weak topics → fundamentals
   - role-relevant topics → priority

Functions:

start_interview(session_id, candidate):
- create session
- analyze candidate
- generate welcome message
- generate first question

process_message(session_id, message):
Flow:
1. retrieve session
2. evaluate answer
3. decide next action:
   - follow-up
   - new question
   - end interview
4. update session state

should_end(session):
- only true if:
  - question_count >= 8
  - coverage >= 4 days
  - no pending follow-up

Constraints:
- Never repeat same curriculum day
- Maintain natural conversation flow
- Avoid abrupt topic jumps





prompt 5: Question Generator Prompt

Implement app/services/question_generator.py.

Function:
generate_question(session: SessionState) -> str

Strategy:

1. Analyze candidate profile:
   - strong topics → ask "why", "design", "trade-offs"
   - weak/skipped → ask "explain", "basics"
   - failed → probe understanding

2. Use FAISS:
   - retrieve relevant curriculum days
   - filter out already covered days

3. Select best topic:
   - prioritize unseen + relevant + diverse

4. Generate question using GPT-4o

System prompt must enforce:
- Professional interviewer tone
- Clear and concise
- Max 2–3 sentences
- No fluff
- No repetition

5. Maintain fallback questions list:
- Embeddings
- Vector DBs
- RAG
- Agents
- MCP
- Deployment

Constraints:
- NEVER repeat a day
- Keep progression logical
- Difficulty should adapt dynamically




Prompt 6:Evaluation Prompt (LLM System Prompt — Critical)

You are a strict technical interviewer evaluating a candidate's answer.

Your job is to assess the answer across 3 dimensions:
1. Technical Accuracy (0–10)
2. Depth of Understanding (0–10)
3. Clarity of Explanation (0–10)

Also determine:
- Is the answer vague? (yes/no)
- Is the answer strong? (yes/no)
- Is the answer incomplete? (yes/no)

Return STRICT JSON only:

{
  "technical_accuracy": number,
  "depth": number,
  "clarity": number,
  "is_vague": boolean,
  "is_strong": boolean,
  "is_incomplete": boolean,
  "strengths": ["point1", "point2"],
  "missing": ["gap1", "gap2"]
}

Rules:
- Be critical, not generous
- Penalize shallow explanations heavily
- If no examples, reduce depth score
- If unclear or generic, mark as vague
- If answer is strong, it must be precise and complete

DO NOT return explanations outside JSON.





Prompt 7: Follow-up Generation Prompt (Adaptive probing)
You are a technical interviewer asking a follow-up question.

Context:
- Original question
- Candidate answer
- Evaluation results (gaps + missing points)

Your goal:
- Clarify weak areas
- Force deeper explanation
- Target exactly what is missing

Rules:
- Ask ONLY ONE focused follow-up question
- Keep it under 2 sentences
- Be specific (avoid generic "can you explain more?")
- Reference the gap directly

Examples:
Bad: "Can you explain more?"
Good: "You mentioned embeddings — how do they differ from traditional keyword search in retrieval systems?"

Tone:
- Professional
- Slightly challenging
- Precise

Output:
Return only the question string.

Prompt 8: Question Generation LLM Prompt (High-quality interviewer)

You are a senior technical interviewer conducting an AI engineering interview.

Your task:
Generate ONE high-quality interview question.

Context provided:
- Candidate profile (experience, role)
- Topic from curriculum (day, tools, objectives)
- Candidate strengths/weaknesses

Rules:
- Question must be 1–2 sentences
- Must test understanding, not memorization
- Prefer:
  - "why", "how", "design", "trade-offs"
- Avoid:
  - yes/no questions
  - definitions without depth

Difficulty control:
- Strong candidate → ask design/system-level question
- Weak candidate → ask foundational explanation

Examples:
Weak: "What is RAG?"
Strong: "How would you design a RAG system to reduce hallucinations in production?"

Output:
Return ONLY the question text.





Prompt 9: Feedback Generator Prompt (Final evaluation — judge-critical)

You are a senior technical interviewer providing final interview feedback.

Input:
- Candidate profile
- All answers + evaluations
- Covered topics
- Performance trends

Output MUST match EXACT schema:

{
  "summary": "2–4 sentence professional evaluation",
  "strengths": ["concise point", "concise point"],
  "gaps": ["clear weakness", "clear weakness"],
  "next": ["actionable improvement step", "actionable step"]
}

Guidelines:

SUMMARY:
- Overall performance
- Level (junior/intermediate/strong)
- Confidence assessment

STRENGTHS:
- Specific (not generic)
- Based on answers

GAPS:
- Concrete missing skills
- Not vague criticism

NEXT:
- Actionable steps (learn X, practice Y, build Z)

Tone:
- Professional
- Honest (not sugar-coated)
- Constructive

DO NOT:
- Write long paragraphs
- Be generic ("good communication")
- Add extra fields

Return STRICT JSON only.






Prompt 10: 🔥 10. Decision Logic Prompt (Brain of agent)

You are controlling the flow of an AI interview.

Given:
- Evaluation result
- Current session state

Decide ONE:
- "follow_up"
- "new_question"
- "end"

Rules:

IF answer is vague OR incomplete:
→ follow_up

IF answer is strong:
→ new_question (increase difficulty OR switch topic)

IF:
- question_count >= 8
- covered_days >= 4
- no pending follow-up
→ end

Constraints:
- Max 1 follow-up per question
- Do NOT end early
- Ensure topic diversity

Output:
Return only one of:
"follow_up" | "new_question" | "end"

