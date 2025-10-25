import json
import os
from uagents import Agent, Context
from ..shared.models import MoodSignal, TopItem, TopPicks
from ..shared.chroma_client import query_menus, rerank_with_prefs
from ..shared.settings import LAST_RECO_PATH, USER_ID
from ..shared.groq_client import explain_choice

reco_agent = Agent(name="reco_agent")

@reco_agent.on_message(MoodSignal)
async def recommend(ctx: Context, m: MoodSignal):
    # Step 1: vector search menus
    candidates = query_menus(m.query, k=12)
    # Step 2: filter by budget and simple spice keyword if present
    filtered = [c for c in candidates if float(c["price"]) <= m.budget]
    filtered = filtered[:6] if filtered else candidates[:6]
    # Step 3: re-rank with prefs
    ranked = rerank_with_prefs(filtered, user_id=USER_ID)
    # Step 4: choose top 3 and generate short reasons via Groq
    top3 = []
    for it in ranked[:3]:
        try:
            reason = explain_choice(m.model_dump(), it["name"])[:140]
        except Exception:
            reason = "Matches your mood and constraints."
        top3.append(TopItem(
            id=it["id"], name=it["name"], price=float(it["price"]),
            reason=reason, eta=int(it["eta"]), dietary=it.get("dietary", []), restaurant=it["restaurant"]
        ))
    picks = TopPicks(items=top3)

    # Persist last recommendations for the HTTP gateway
    os.makedirs(os.path.dirname(LAST_RECO_PATH), exist_ok=True)
    with open(LAST_RECO_PATH, "w", encoding="utf-8") as f:
        json.dump(picks.model_dump(), f, ensure_ascii=False, indent=2)

    ctx.logger.info(f"RecoAgent: wrote {len(top3)} picks → {LAST_RECO_PATH}")