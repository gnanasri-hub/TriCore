import logging
from typing import List, Dict, Any, Optional
from app.schemas import SessionState
from app.services import data_manager

logger = logging.getLogger(__name__)

# Fallback questions for critical topics
FALLBACK_QUESTIONS = {
    # Embeddings
    7: {
        "strong": "When designing a production semantic search system, how do you handle domain-specific terminology that may not be well-represented in a general-purpose embedding model like text-embedding-3-small? What are the trade-offs of fine-tuning the model versus hybrid search?",
        "weak": "Can you explain in simple terms what a vector embedding represents and how a model converts unstructured text into a high-dimensional vector? What is the main difference between dense and sparse embeddings?"
    },
    # Vector DBs
    8: {
        "strong": "As database size scales, how do you choose between IndexFlatIP (exact search) and HNSW or IVF (approximate nearest neighbor) in FAISS? What impact does this choice have on query latency, recall accuracy, and memory consumption?",
        "weak": "What is the purpose of a vector database compared to a traditional relational database (like SQLite), and why do we need specialized indexes like HNSW to search vector embeddings efficiently?"
    },
    9: {
        "strong": "When inserting millions of vectors into a database, how do you design batch indexing pipelines to prevent query latency spikes? How do you ensure index updates are synchronized without data loss?",
        "weak": "Can you explain how embeddings are loaded and indexed in a vector database, and how metadata filtering is applied to restrict search results?"
    },
    # RAG
    11: {
        "strong": "To prevent hallucinations and retrieve high-fidelity source context, how do you design a document chunking and metadata-filtering strategy in a RAG pipeline? How do you handle cases where the retrieved context contains contradictory information?",
        "weak": "Could you walk me through the step-by-step flow of a Retrieval-Augmented Generation (RAG) system, starting from a user's query to the final LLM response? Why is retrieving external context useful?"
    },
    # Agents
    21: {
        "strong": "When building a ReAct-based agent, how do you prevent loops and handle scenarios where the agent selects incorrect tools or fails to parse tool arguments? What trade-offs do you consider when deciding between a single complex reasoning agent and a multi-agent orchestrated graph?",
        "weak": "What is an AI agent, and how does it differ from a standard LLM chatbot that only generates responses? How does the agent use tools to interact with external environments?"
    },
    22: {
        "strong": "In a multi-agent architecture like CrewAI or LangGraph, how do you design agent communication protocols and shared memory state to prevent coordination deadlock and minimize API costs?",
        "weak": "What are specialized agents, and how does a router agent decide which specialist to delegate a healthcare question or task to?"
    },
    # MCP
    23: {
        "strong": "When exposing database tools via the Model Context Protocol (MCP), how do you secure user contexts and manage token limits when multiple tools report large payloads back to the LLM? How does MCP standardise client-server communication?",
        "weak": "What is the Model Context Protocol (MCP), and what problem does it solve when connecting local development editors (like VS Code or Claude Desktop) to external tools and data sources?"
    },
    # Deployment
    28: {
        "strong": "When containerizing and deploying a FastAPI + React chatbot on Kubernetes, how do you handle state persistence for conversation memory across multiple scaled pod replicas? What horizontal pod autoscaling metrics are most appropriate for LLM-backed services?",
        "weak": "Why do we containerize python applications with Docker, and what are the main benefits of using Kubernetes to orchestrate these containers in a production deployment?"
    }
}

def get_fallback_question(day_num: int, is_strong: bool) -> Optional[str]:
    """
    Retrieve prebuilt high-quality fallback questions for critical curriculum topics.
    """
    topic_fallbacks = FALLBACK_QUESTIONS.get(day_num)
    if not topic_fallbacks:
        # Fallback to key category lookup if day_num doesn't match directly
        # E.g. search adjacent day mappings
        if day_num in [8, 9, 10]:
            topic_fallbacks = FALLBACK_QUESTIONS.get(8)
        elif day_num in [21, 22, 24]:
            topic_fallbacks = FALLBACK_QUESTIONS.get(21)
            
    if topic_fallbacks:
        return topic_fallbacks.get("strong" if is_strong else "weak")
    return None

def generate_question(session: SessionState) -> str:
    """
    Generate a natural, professional interview question tailored to the candidate's strength
    on the current day's curriculum topic. Uses FAISS semantic search for context.
    """
    day_num = session.current_day
    if not day_num:
        logger.warning("No current_day set in SessionState.")
        return "Let's begin the interview. Could you describe your background and experience?"
        
    profile = session.candidate_profile
    day_meta = data_manager.get_day_metadata(day_num)
    day_title = day_meta.get("title", f"Day {day_num}") if day_meta else f"Day {day_num}"
    
    # 1. Analyze candidate's strength on this day
    is_strong = day_title in profile.get("strong_topics", [])
    
    # 2. Use FAISS to retrieve the most relevant curriculum day content
    try:
        # Query FAISS using the day title as query, restricted to this day number
        search_results = data_manager.retrieve_relevant_days(
            query=day_title,
            top_k=1,
            preferred_days=[day_num]
        )
        if search_results:
            day_content = search_results[0]
        else:
            day_content = day_meta or {}
    except Exception as e:
        logger.error(f"Error using FAISS to retrieve day {day_num}: {e}")
        day_content = day_meta or {}
        
    # Define difficulty prefix
    difficulty_pref = (
        "deep application, design, or architectural question (design trade-offs, scalability, edge cases)"
        if is_strong else
        "foundational, concept-probing question (explanation of how it works, purpose, basic implementation details)"
    )
    
    # 3. Call GPT-4o with strong prompt
    client = data_manager.get_openai_client()
    
    prompt = f"""You are an expert technical interviewer for an AI engineering cohort.
Generate a concise, professional interview question for the candidate based on the curriculum context.

Candidate Context:
- Name: {profile.get('name', 'Candidate')}
- Job Role: {profile.get('job_role', 'Software Engineer')}
- Experience Level: {profile.get('experience_level', 'Mid-level')}
- Topic Area: This is a {"strong" if is_strong else "weak/skipped"} area for the candidate.

Curriculum Day Context:
- Day: {day_num}
- Title: {day_title}
- Objectives: {", ".join(day_content.get('objectives', []))}
- Tools: {", ".join(day_content.get('tools', []))}

Question Strategy:
- Ask a {difficulty_pref}.
- The question must focus on the objectives and tools of this day.
- Keep the question natural, conversational, and highly technical.
- DO NOT repeat introductions or welcome messages if conversation history already has exchanges.

Conversation History (recent turns):
{session.history[-4:] if len(session.history) > 4 else session.history}

Instructions:
1. Generate the question directly. Keep it to a maximum of 2-3 sentences.
2. Ensure the tone is professional, technical, and precise.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional technical interviewer who asks concise, targeted technical questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Failed to generate question with LLM: {e}. Using fallback question.")
        # Retrieve high quality fallback
        fallback_q = get_fallback_question(day_num, is_strong)
        if fallback_q:
            return fallback_q
        # Backup backup
        tools_str = ", ".join(day_content.get('tools', []))
        return f"Regarding Day {day_num} ({day_title}), how would you design a solution using {tools_str or 'the curriculum tools'} and what key trade-offs would you consider?"

def generate_follow_up(question: str, vague_answer: str, history: List[Dict[str, str]]) -> str:
    """
    Generate a follow-up question probing the candidate's vague or brief response.
    """
    client = data_manager.get_openai_client()
    
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
