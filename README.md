# TriCore AI Interview Agent

## 🚨 Problem
Traditional interviews are static and fail to evaluate real understanding or adapt to candidate responses.

## 💡 Solution
An AI-powered adaptive interview system that:
- Dynamically adjusts question difficulty
- Evaluates answers in real-time
- Identifies knowledge gaps
- Provides feedback signals

## ⚙️ Features
- Adaptive question generation
- Real-time evaluation (confidence, clarity, depth)
- Knowledge gap detection
- Role-based interviews (AI Engineer, etc.)
- Follow-up questioning logic

## 🧠 Tech Stack
- Frontend: React
- Backend: Python (FastAPI/Flask)
- AI: LLM-based evaluation engine

## 🎥 Live Demo
[PUT YOUR LINK HERE]

## 🛠️ Run Locally

### Backend
cd interview-agent
pip install -r requirements.txt
python app.py

### Frontend
cd interview-frontend
npm install
npm run dev

## 🤖 AI Usage
See AI_USAGE_LOG.md

## 📌 Architecture
- Frontend → sends answer
- Backend → evaluates via LLM
- Engine → generates next adaptive question
