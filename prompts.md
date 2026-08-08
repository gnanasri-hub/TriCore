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
