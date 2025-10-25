from uagents import Model
from typing import List, Dict, Optional

class CommitBatch(Model):
    repo: str
    commits: List[str]

class MoodSignal(Model):
    mood: str
    energy: str
    valence: str
    budget: float
    diet: str
    spice: str
    time: str
    query: str  # NL query for retrieval

class TopItem(Model):
    id: str
    name: str
    price: float
    reason: str
    eta: int
    dietary: List[str]
    restaurant: str

class TopPicks(Model):
    items: List[TopItem]

class Feedback(Model):
    user_id: str
    item_id: str
    liked: bool
    notes: Optional[str] = None

# --- DoorDash order models ---
class PlaceOrder(Model):
    # Generate external_delivery_id internally if not provided
    item_id: str
    item_name: str
    dropoff_address: str
    dropoff_phone_number: str  # E.164 (+1...)
    dropoff_contact_given_name: Optional[str] = None
    dropoff_contact_family_name: Optional[str] = None
    tip_cents: Optional[int] = 0
    pickup_address: str = "1 Palace of Fine Arts, San Francisco, CA 94123"  # demo default
    pickup_business_name: str = "DevSnacks Kitchen"
    pickup_phone_number: str = "+14155550100"
    pickup_instructions: Optional[str] = "Show order code at counter"

class DeliveryResponse(Model):
    external_delivery_id: str
    status: str
    eta: Optional[int] = None
    tracking_url: Optional[str] = None
    raw: Dict | None = None