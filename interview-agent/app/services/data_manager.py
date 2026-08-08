import json
import logging
from typing import Dict, Any, List, Optional
import numpy as np
import faiss
from openai import OpenAI
from groq import Groq

from app import config

logger = logging.getLogger(__name__)

# ── Singletons ────────────────────────────────────────────────────────────────
_index:            Optional[faiss.IndexFlatIP] = None
_metadata:         Optional[List[Dict[str, Any]]] = None
_openai_client:    Optional[OpenAI] = None
_groq_client:      Optional[Groq]   = None
_curriculum_cache: Optional[Dict[str, Any]] = None


def get_openai_client() -> OpenAI:
    """OpenAI client — used only for embeddings."""
    global _openai_client
    if _openai_client is None:
        api_key = config.OPENAI_API_KEY
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Required for FAISS embedding generation."
            )
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def get_groq_client() -> Groq:
    """Groq client — used for all LLM chat completions."""
    global _groq_client
    if _groq_client is None:
        api_key = config.GROQ_API_KEY
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set. "
                "Please configure it in your .env file."
            )
        _groq_client = Groq(api_key=api_key)
    return _groq_client

def create_day_chunk(day_data: Dict[str, Any]) -> str:
    """
    Create a rich text representation of a curriculum day.
    """
    day = day_data.get("day", 0)
    title = day_data.get("title", "Untitled Day")
    day_type = day_data.get("type", "UNKNOWN")
    tools = ", ".join(day_data.get("tools", []))
    objectives_list = day_data.get("objectives", [])
    objectives = "\n".join(f"- {obj}" for obj in objectives_list)
    
    return f"""Day {day}: {title}
Type: {day_type}
Tools: {tools}
Objectives:
{objectives}"""

def init_index(force_rebuild: bool = False):
    """
    Initialize the FAISS index and metadata.
    Loads from disk if available, otherwise builds and saves them.
    """
    global _index, _metadata
    
    if not force_rebuild and config.FAISS_INDEX_PATH.exists() and config.FAISS_METADATA_PATH.exists():
        try:
            logger.info("Loading FAISS index and metadata from disk...")
            _index = faiss.read_index(str(config.FAISS_INDEX_PATH))
            with open(config.FAISS_METADATA_PATH, "r", encoding="utf-8") as f:
                _metadata = json.load(f)
            logger.info("Successfully loaded FAISS index and metadata from disk.")
            return
        except Exception as e:
            logger.error(f"Failed to load FAISS index from disk: {e}. Rebuilding index...")
            
    # Rebuild index
    logger.info("Building FAISS index...")
    if not config.CURRICULUM_JSON_PATH.exists():
        raise FileNotFoundError(f"Curriculum JSON file not found at {config.CURRICULUM_JSON_PATH}")
        
    with open(config.CURRICULUM_JSON_PATH, "r", encoding="utf-8") as f:
        curriculum_data = json.load(f)
        
    days = curriculum_data.get("days", [])
    if not days:
        raise ValueError("No days found in curriculum.json")
        
    chunks = []
    metadata = []
    
    for d in days:
        chunk = create_day_chunk(d)
        chunks.append(chunk)
        metadata.append({
            "day": d.get("day"),
            "title": d.get("title"),
            "type": d.get("type"),
            "tools": d.get("tools", []),
            "objectives": d.get("objectives", []),
            "chunk_text": chunk
        })
        
    # Generate embeddings via OpenAI
    client = get_openai_client()
    logger.info(f"Generating embeddings using model {config.EMBEDDING_MODEL}...")
    
    response = client.embeddings.create(
        input=chunks,
        model=config.EMBEDDING_MODEL
    )
    
    embeddings = [item.embedding for item in response.data]
    embeddings_np = np.array(embeddings, dtype=np.float32)
    
    # Normalize vectors to L2 norm for inner product (cosine similarity)
    faiss.normalize_L2(embeddings_np)
    
    dimension = config.EMBEDDING_DIMENSION
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_np)
    
    # Save to disk
    logger.info("Saving FAISS index and metadata to disk...")
    config.FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(config.FAISS_INDEX_PATH))
    with open(config.FAISS_METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
        
    _index = index
    _metadata = metadata
    logger.info("Successfully built and saved FAISS index.")

def ensure_index_loaded():
    """
    Ensures index and metadata are loaded.
    """
    global _index, _metadata
    if _index is None or _metadata is None:
        init_index()

def _load_curriculum_cache() -> Dict[str, Any]:
    """
    Loads curriculum structure details once to speed up candidate profiling.
    """
    global _curriculum_cache
    if _curriculum_cache is not None:
        return _curriculum_cache
        
    if not config.CURRICULUM_JSON_PATH.exists():
        logger.warning(f"Curriculum JSON file not found at {config.CURRICULUM_JSON_PATH}")
        return {}
        
    try:
        with open(config.CURRICULUM_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading curriculum.json: {e}")
        return {}
        
    day_to_module = {}
    day_to_title = {}
    
    # Build mapping from modules
    modules = data.get("modules", [])
    for mod in modules:
        mod_title = mod.get("title", "")
        day_range = mod.get("days", [])
        if len(day_range) == 2:
            for d in range(day_range[0], day_range[1] + 1):
                day_to_module[d] = mod_title
                
    # Build mapping from days list
    days = data.get("days", [])
    for d in days:
        d_num = d.get("day")
        d_title = d.get("title", "")
        if d_num:
            day_to_title[d_num] = d_title
            
    _curriculum_cache = {
        "day_to_module": day_to_module,
        "day_to_title": day_to_title
    }
    return _curriculum_cache

def get_candidate_profile(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a candidate's record and return a structured profile dictionary.
    
    The structured dictionary contains:
      - id: str
      - name: str
      - job_role: str
      - experience_level: str ("Junior", "Mid-level", "Senior")
      - years_experience: int
      - completed_days: List[int]
      - skipped_days: List[int]
      - failed_days: List[int]
      - strong_topics: List[str]
      - weak_topics: List[str]
      - signals: Dict[str, Any]
    """
    member = candidate.get("member", {})
    missions = candidate.get("missions", [])
    signals = candidate.get("signals", {})
    
    cache = _load_curriculum_cache()
    day_to_title = cache.get("day_to_title", {})
    
    completed_days = []
    skipped_days = []
    failed_days = []

    strong_topics = []
    weak_topics = []
    attempts_by_day: Dict[int, int] = {}   # day_num → attempts (0 if skipped/no attempts)

    for mission in missions:
        day_num = mission.get("day")
        title = mission.get("title") or day_to_title.get(day_num, f"Day {day_num}")
        passed = mission.get("passed")
        skipped = mission.get("skipped", False)
        attempts = mission.get("attempts", 0)

        attempts_by_day[day_num] = attempts

        if skipped:
            skipped_days.append(day_num)
            weak_topics.append(title)
        elif passed is True:
            completed_days.append(day_num)
            # Define "strong" as passed in <= 2 attempts
            if attempts <= 2:
                strong_topics.append(title)
            else:
                weak_topics.append(title)
        elif passed is False:
            failed_days.append(day_num)
            weak_topics.append(title)
            
    # Categorize experience level
    years_exp = member.get("yearsExperience", 0)
    if years_exp < 3:
        exp_level = "Junior"
    elif years_exp <= 5:
        exp_level = "Mid-level"
    else:
        exp_level = "Senior"
        
    return {
        "id": member.get("id"),
        "name": member.get("name"),
        "job_role": member.get("jobRole"),
        "experience_level": exp_level,
        "years_experience": years_exp,
        "completed_days": sorted(completed_days),
        "skipped_days": sorted(skipped_days),
        "failed_days": sorted(failed_days),
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "attempts_by_day": attempts_by_day,
        "signals": signals
    }

def retrieve_relevant_days(
    query: str,
    top_k: int = 5,
    preferred_days: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Search the FAISS index for the top_k most similar curriculum days.

    Parameters:
      - query: Semantic text query
      - top_k: Maximum number of records to return
      - preferred_days: Optional filter list of day numbers

    Returns:
      A list of day metadata dictionaries with a "similarity" float score.
      Returns an empty list (graceful degradation) if the embedding API is
      unavailable — callers must handle this case.
    """
    ensure_index_loaded()

    # Generate query embedding via OpenAI
    try:
        client = get_openai_client()
        response = client.embeddings.create(
            input=[query],
            model=config.EMBEDDING_MODEL
        )
    except Exception as exc:
        logger.warning(
            "Embedding API unavailable (%s). Skipping semantic retrieval — "
            "falling back to title/tier-based day selection.",
            exc,
        )
        return []

    query_emb = response.data[0].embedding
    query_emb_np = np.array([query_emb], dtype=np.float32)
    faiss.normalize_L2(query_emb_np)

    # Search the full index
    total_days = len(_metadata)
    scores, indices = _index.search(query_emb_np, total_days)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(_metadata):
            continue
        day_meta = _metadata[idx].copy()
        day_meta["similarity"] = float(score)

        # Apply preferred_days hard filter if provided
        if preferred_days is not None:
            if day_meta["day"] not in preferred_days:
                continue

        results.append(day_meta)
        if len(results) == top_k:
            break

    return results

def get_all_days_metadata() -> List[Dict[str, Any]]:
    """
    Retrieve metadata for all 31 curriculum days.
    """
    ensure_index_loaded()
    return _metadata

def get_day_metadata(day_num: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve metadata for a specific curriculum day number.
    """
    ensure_index_loaded()
    for d in _metadata:
        if d.get("day") == day_num:
            return d
    return None
