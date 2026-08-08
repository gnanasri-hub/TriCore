import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the interview-agent app
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env
load_dotenv(BASE_DIR / ".env", override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")

# Data paths
CANDIDATES_JSON_PATH = BASE_DIR / "data" / "candidates.json"
CURRICULUM_JSON_PATH = BASE_DIR / "data" / "curriculum.json"

# FAISS paths
FAISS_INDEX_PATH    = BASE_DIR / "data" / "curriculum.faiss"
FAISS_METADATA_PATH = BASE_DIR / "data" / "metadata.json"

# Embedding settings (still OpenAI — embeddings stay on OpenAI)
EMBEDDING_MODEL     = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

# Groq settings
GROQ_MODEL = "llama-3.3-70b-versatile"
