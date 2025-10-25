import os, httpx, asyncio

AGENT_GH=os.getenv("AGENT_GH_URL")
AGENT_EMB=os.getenv("AGENT_EMB_URL")
AGENT_FOOD=os.getenv("AGENT_FOOD_URL")

async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        gh = await client.post(AGENT_GH, json={"owner":"vercel","repo":"next.js","since_iso":"2025-10-01T00:00:00Z"})
        commits = gh.json()["commits"][:10]
        moods=set()
        for c in commits:
            e = await client.post(AGENT_EMB, json={"commit": c})
            moods.add(e.json()["mood_label"])
        target = next(iter(moods), "meh")
        ff = await client.post(AGENT_FOOD, json={"mood_label": target})
        cuisine = ff.json()["cuisine"]
        order = await client.post(AGENT_FOOD, json={
            "cuisine": cuisine,
            "dropoff_address": "1 Hacker Way, Menlo Park, CA",
            "contact_name": "Demo User",
            "contact_phone": "4155551234"
        })
        print(target, cuisine, order.json())

asyncio.run(main())