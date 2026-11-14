from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class ParsedCriteria(BaseModel):
    topics: List[str] = Field(description="List of target topics like AI, Web3, ML, Hackathons, Tech Events")
    location: Optional[str] = Field(default=None, description="City or location mentioned by user, e.g. Hyderabad, or None if online/unspecified")
    target_days: List[str] = Field(description="Days of the week mentioned by the user")
    target_dates: List[str] = Field(description="Calculated concrete target dates in YYYY-MM-DD")
    is_online_only: bool = Field(default=True)
    delay_minutes: int = Field(
        default=0, 
        description="Number of minutes to wait before discovering and dispatching, if requested (e.g. 'send in 1 min' -> 1)"
    )
class EventCandidate(BaseModel):
    title: str
    url: str
    platform: str
    date: str
    organizer: str
    summary: str
    priority: Optional[str] = "MEDIUM"

class AgentState(TypedDict):
    task_id: str
    raw_prompt: str
    current_date: str
    criteria: Dict[str, Any]
    scraped_events: List[Dict[str, Any]]
    verified_events: List[Dict[str, Any]]
    ranked_events: List[Dict[str, Any]]
