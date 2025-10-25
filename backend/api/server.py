from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import os
from ..shared.settings import LAST_RECO_PATH, USER_ID
from ..shared.chroma_client import add_feedback
from ..shared.doordash import build_body_from_place_order, create_delivery, get_delivery

app = FastAPI(title="DevSnacksAI API")

@app.get("/api/recommendations")
async def get_recommendations():
    if not os.path.exists(LAST_RECO_PATH):
        return {"items": []}
    with open(LAST_RECO_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

class FeedbackIn(BaseModel):
    item_id: str
    liked: bool
    notes: str | None = None

@app.post("/api/feedback")
async def post_feedback(body: FeedbackIn):
    add_feedback(user_id=USER_ID, item_id=body.item_id, liked=body.liked, notes=body.notes)
    return {"ok": True}

class OrderIn(BaseModel):
    item_id: str
    item_name: str
    dropoff_address: str
    dropoff_phone_number: str
    dropoff_contact_given_name: str | None = None
    dropoff_contact_family_name: str | None = None
    tip_cents: int | None = 0

@app.post("/api/order")
async def post_order(body: OrderIn):
    try:
        dd_body = build_body_from_place_order(body.model_dump())
        res = create_delivery(dd_body)
        return {"ok": True, "external_delivery_id": res.get("external_delivery_id"), "raw": res}
    except Exception as e:
        raise HTTPException(400, f"DoorDash error: {e}")

@app.get("/api/order/{external_delivery_id}")
async def order_status(external_delivery_id: str):
    try:
        res = get_delivery(external_delivery_id)
        return res
    except Exception as e:
        raise HTTPException(400, f"DoorDash error: {e}")