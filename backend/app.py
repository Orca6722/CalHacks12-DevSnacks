# app.py (your orchestrator)
import os, httpx
from fastapi import FastAPI
from pydantic import BaseModel

AGENT_GH = os.getenv("AGENT_GH_URL")
AGENT_EMB = os.getenv("AGENT_EMB_URL")
AGENT_FOOD = os.getenv("AGENT_FOOD_URL")

app = FastAPI()

class OrchestrateBody(BaseModel):
    owner: str
    repo: str
    branch: str | None = None
    since_iso: str | None = None
    dropoff_address: str
    contact_name: str
    contact_phone: str

@app.post("/mood-food")
async def mood_food(body: OrchestrateBody):
    async with httpx.AsyncClient(timeout=60) as client:
        # 1) collect commits
        r = await client.post(AGENT_GH, json=body.model_dump(include={"owner","repo","branch","since_iso"}))
        commits = r.json()["commits"]

        # 2) embed + mood label all commits (fan-out)
        moods = set()
        for c in commits:
            rr = await client.post(AGENT_EMB, json={"commit": c})
            moods.add(rr.json()["mood_label"])

        # 3) pick dominant mood, map to cuisine + order
        # Alternatively, call FindFood first for the chosen mood and display cuisine/confidence
        target_mood = list(moods)[0] if moods else "meh"
        fr = await client.post(AGENT_FOOD, json={"mood_label": target_mood})
        cuisine = fr.json()["cuisine"]
        order = await client.post(AGENT_FOOD, json={
            "cuisine": cuisine,
            "dropoff_address": body.dropoff_address,
            "contact_name": body.contact_name,
            "contact_phone": body.contact_phone
        })
        return {
          "dominant_mood": target_mood,
          "cuisine": cuisine,
          "delivery": order.json()
        }
