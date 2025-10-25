# shared/schemas.py
from pydantic import BaseModel
from typing import List, Optional

class CollectCommitsRequest(BaseModel):
    owner: str
    repo: str
    branch: Optional[str] = None
    since_iso: Optional[str] = None  # e.g. 2025-10-01T00:00:00Z

class CommitRecord(BaseModel):
    sha: str
    author: Optional[str]
    message: str
    date_iso: str

class CollectCommitsResponse(BaseModel):
    commits: List[CommitRecord]

class EmbedCommitRequest(BaseModel):
    commit: CommitRecord

class EmbedCommitResponse(BaseModel):
    id: str
    mood_label: str
    vector_dim: int

class FindFoodRequest(BaseModel):
    mood_label: str

class FindFoodResponse(BaseModel):
    cuisine: str
    confidence: float

class OrderFoodRequest(BaseModel):
    cuisine: str
    dropoff_address: str
    contact_name: str
    contact_phone: str
    # add any DoorDash Drive fields you need

class OrderFoodResponse(BaseModel):
    doordash_delivery_id: str
    status: str

# --- Food recommender (Groq agent) ---
class RecommendFoodRequest(BaseModel):
    commits: List[str]  # list of raw commit messages (newest-first recommended)

class RecommendFoodResponse(BaseModel):
    mood: str           # one of: focused, energized, meh, stressed, celebratory, calm
    food: str           # a single, concrete dish name
    reasoning: Optional[str] = None
