import json
import asyncio
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from tavily import AsyncTavilyClient
from app.core.config import settings
from app.graph.state import AgentState, ParsedCriteria

logger = logging.getLogger("agent.nodes")

def extract_text(content) -> str:
    """Safely extract plain text from an LLM response content that may be a string or a list of blocks."""
    if isinstance(content, list):
        return " ".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)

# Key rotation pool
current_key_idx = 0

def get_gemini_keys() -> list[str]:
    keys = []
    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
        keys.append(settings.GEMINI_API_KEY.strip())
    if getattr(settings, "GEMINI_API_KEY_BACKUP", None) and settings.GEMINI_API_KEY_BACKUP.strip():
        backup = settings.GEMINI_API_KEY_BACKUP.strip()
        if backup not in keys:
            keys.append(backup)
    return keys

def create_llm(api_key: str):
    return ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        google_api_key=api_key,
        temperature=0.0,
        max_retries=1,
        request_timeout=35
    )

async def invoke_llm_resilient(prompt: str, structured_schema=None):
    global current_key_idx
    keys = get_gemini_keys()
    if not keys:
        raise ValueError("No GEMINI_API_KEY configured in .env")

    last_err = None
    for attempt in range(len(keys)):
        idx = (current_key_idx + attempt) % len(keys)
        key = keys[idx]
        masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"

        try:
            llm_inst = create_llm(key)
            if structured_schema:
                res = await llm_inst.with_structured_output(structured_schema).ainvoke(prompt)
            else:
                res = await llm_inst.ainvoke(prompt)
            current_key_idx = idx
            return res
        except Exception as e:
            err_msg = str(e).lower()
            last_err = e
            is_rate_limit = "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg or "rate limit" in err_msg
            is_timeout = "504" in err_msg or "deadline" in err_msg or "timeout" in err_msg

            if is_rate_limit:
                logger.warning("[LLM] Key %s hit rate limit/quota. Rotating to backup API key...", masked)
                if len(keys) > 1:
                    continue
                else:
                    logger.warning("[LLM] Only 1 key configured. Pausing 5s before retry...")
                    await asyncio.sleep(5)
                    try:
                        llm_inst = create_llm(key)
                        if structured_schema:
                            return await llm_inst.with_structured_output(structured_schema).ainvoke(prompt)
                        return await llm_inst.ainvoke(prompt)
                    except Exception as retry_err:
                        last_err = retry_err
            elif is_timeout:
                logger.warning("[LLM] Key %s encountered gateway timeout/deadline exceeded: %s", masked, e)
                if len(keys) > 1:
                    continue
                else:
                    await asyncio.sleep(2)
                    try:
                        llm_inst = create_llm(key)
                        if structured_schema:
                            return await llm_inst.with_structured_output(structured_schema).ainvoke(prompt)
                        return await llm_inst.ainvoke(prompt)
                    except Exception as retry_err:
                        last_err = retry_err
            else:
                logger.warning("[LLM] Key %s error: %s. Trying backup if available...", masked, e)
                if len(keys) > 1:
                    continue
                raise e

    raise last_err

tavily = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)

async def parser_node(state: AgentState) -> dict:
    logger.info("[parser_node] Starting — prompt: %s", state['raw_prompt'])
    prompt = f"""
    Current Reference Date: {state['current_date']}
    User Prompt: "{state['raw_prompt']}"

    Extract:
    - topics: list of subject areas (e.g. hackathons, tech events, AI, etc.)
    - location: city/location mentioned (e.g. "Hyderabad", or null if none)
    - target_days: requested days of the week
    - target_dates: concrete target dates (YYYY-MM-DD) relative to reference date
    - is_online_only: False if physical/city events are requested, True if online only
    - delay_minutes: if the user specifies a delay, wait time, or duration to work/wait before delivering results (e.g., 'work for 15 minutes', 'deliver after 10 mins', 'send in 5 minutes'), extract the integer number of minutes (e.g. 15). Default is 0.
    """
    parsed: ParsedCriteria = await invoke_llm_resilient(prompt, structured_schema=ParsedCriteria)
    logger.info("[parser_node] Done — criteria: %s", parsed.model_dump())
    return {"criteria": parsed.model_dump()}

async def search_node(state: AgentState) -> dict:
    topics = " ".join(state["criteria"].get("topics", []))
    days   = " ".join(state["criteria"].get("target_days", []))
    location = state["criteria"].get("location")
    
    candidates = []
    seen_urls = set()
    queries = []

    if location:
        queries.append(f"hackathons tech events workshops meetups {location} 2026")
        queries.append(f"{topics} events {location} Devfolio Unstop Meetup")
    else:
        queries.append(f"online hackathon workshop webinar {topics} {days} Devpost Unstop Devfolio")

    for query in queries:
        logger.info("[search_node] Starting — query: %s", query)
        search_results = await tavily.search(query=query, max_results=7)
        for res in search_results.get("results", []):
            url = res.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                candidates.append({
                    "title":    res.get("title", ""),
                    "url":      url,
                    "snippet":  (res.get("content", "") or "")[:250],
                    "platform": "Web"
                })
    logger.info("[search_node] Done — %d candidates found", len(candidates))
    return {"scraped_events": candidates}

async def verifier_node(state: AgentState) -> dict:
    candidates = state.get("scraped_events", [])
    criteria   = state.get("criteria", {})
    logger.info("[verifier_node] Starting — %d candidates to verify", len(candidates))

    if not candidates:
        return {"verified_events": []}

    compact_candidates = [
        {
            "title": c.get("title", ""),
            "url": c.get("url", ""),
            "snippet": (c.get("snippet", "") or "")[:200]
        }
        for c in candidates[:10]
    ]

    verification_prompt = f"""
    User Topics: {json.dumps(criteria.get('topics', []))}
    Location: {json.dumps(criteria.get('location'))}
    Reference Date: {criteria.get('target_dates', ['today'])[0] if criteria.get('target_dates') else 'today'}
    Candidates: {json.dumps(compact_candidates)}

    Task: Keep every item that is a real upcoming or ongoing tech event.
    Return ONLY a valid JSON array:
    [{{"title": "...", "url": "...", "date": "...", "organizer": "...", "summary": "..."}}]
    """
    try:
        response   = await invoke_llm_resilient(verification_prompt)
        clean_text = extract_text(response.content).replace("```json", "").replace("```", "").strip()
        verified = json.loads(clean_text)
    except Exception as e:
        logger.warning("[verifier_node] Verification LLM error (%s). Using candidate fallback.", e)
        verified = [
            {
                "title": c.get("title", "Tech Event"),
                "url": c.get("url", ""),
                "date": "Upcoming",
                "organizer": c.get("platform", "Web"),
                "summary": c.get("snippet", "")
            }
            for c in candidates[:8]
        ]

    logger.info("[verifier_node] Done — %d events verified", len(verified))
    return {"verified_events": verified}

async def ranker_node(state: AgentState) -> dict:
    verified = state.get("verified_events", [])
    logger.info("[ranker_node] Starting — %d events to rank", len(verified))
    if not verified:
        return {"ranked_events": []}

    ranking_prompt = f"""
    Events: {json.dumps(verified)}

    Assign a priority ("HIGH", "MEDIUM", "LOW") to each event:
    - HIGH: Tier-1 tech giants, large global prize pools, or major hackathons.
    - MEDIUM: Reputable startups, developer communities.
    - LOW: Local college clubs, student meetups.

    Also determine for each event:
    - "is_online": true if virtual/online/remote, false if in-person/offline
    - "is_free": true if free registration or no ticket fee, false if paid

    Return the updated JSON list with the "priority", "is_online", and "is_free" fields populated.
    """
    try:
        response   = await invoke_llm_resilient(ranking_prompt)
        clean_text = extract_text(response.content).replace("```json", "").replace("```", "").strip()
        ranked = json.loads(clean_text)
    except Exception as e:
        logger.warning("[ranker_node] Ranking LLM error (%s). Assigning default priorities.", e)
        ranked = [
            {
                **v,
                "priority": "HIGH" if idx < 3 else ("MEDIUM" if idx < 6 else "LOW"),
                "is_online": True,
                "is_free": True
            }
            for idx, v in enumerate(verified)
        ]

    logger.info("[ranker_node] Done — %d events ranked", len(ranked))
    return {"ranked_events": ranked}
    return {"ranked_events": ranked}
