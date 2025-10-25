# agents/food_orchestrator/main.py
import os, httpx
from uagents import Agent, Context, Protocol
from shared.schemas import FindFoodRequest, FindFoodResponse, OrderFoodRequest, OrderFoodResponse
from shared.chroma_client import collection
from shared.cuisine_map import MOOD_TO_CUISINE, DEFAULT_CUISINE

DD_DRIVE_BASE = "https://openapi.doordash.com/drive/v2"     # use sandbox base from docs
DD_KEY = os.getenv("DD_KEY")                                 # refer to Drive docs for headers
DD_SECRET = os.getenv("DD_SECRET")

proto = Protocol("food-orchestrator", version="1.0.0")

@proto.on_message(FindFoodRequest, replies=FindFoodResponse)
async def handle_find(ctx: Context, msg: FindFoodRequest):
    # Search Chroma by short "query_texts" (collection uses same embedding function)
    res = collection.query(query_texts=[msg.mood_label], n_results=5)
    # Heuristic confidence: inverse distance proxy
    confidence = 0.7 if res["ids"] and len(res["ids"][0]) else 0.0
    cuisine = MOOD_TO_CUISINE.get(msg.mood_label, DEFAULT_CUISINE)
    await ctx.send(ctx.sender, FindFoodResponse(cuisine=cuisine, confidence=confidence))

@proto.on_message(OrderFoodRequest, replies=OrderFoodResponse)
async def handle_order(ctx: Context, msg: OrderFoodRequest):
    # Construct a basic Drive create-delivery payload (sandbox)
    payload = {
      "external_delivery_id": f"demo-{os.urandom(3).hex()}",
      "pickup_address": "123 Demo Store St, San Francisco, CA 94107",
      "pickup_business_name": f"{msg.cuisine.capitalize()} Kitchen",
      "pickup_phone_number": "4155550000",
      "dropoff_address": msg.dropoff_address,
      "dropoff_contact_given_name": msg.contact_name,
      "dropoff_contact_phone_number": msg.contact_phone,
      "order_value": 2000,  # in cents; set something reasonable for sandbox
    }
    headers = {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "Authorization": f"Bearer {DD_KEY}:{DD_SECRET}"  # follow Drive auth format from docs/sdk/postman
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{DD_DRIVE_BASE}/deliveries", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
    await ctx.send(ctx.sender, OrderFoodResponse(
        doordash_delivery_id=str(data.get("external_delivery_id", "")),
        status=data.get("status", "created")
    ))

agent = Agent(name="food_orchestrator", seed=os.getenv("SEED", "food-orchestrator-seed"))
agent.include(proto)

if __name__ == "__main__":
    agent.run()
