# shared/schemas.py
from pydantic import BaseModel
from typing import List, Optional

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
