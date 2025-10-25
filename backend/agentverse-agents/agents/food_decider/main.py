import os
import json
from typing import List, Optional
from uagents import Agent, Context, Protocol
from groq import Groq
from shared.schemas import RecommendFoodRequest, RecommendFoodResponse

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is required")

groq_client = Groq(api_key=GROQ_API_KEY)

proto = Protocol(name="food-decider", version="1.0.0")

SYS = (
    "You are a decisive assistant that reads recent developer commit messages and "
    "infers the developer's current mood. Pick ONE lowercase mood token from: "
    "[focused, energized, meh, stressed, celebratory, calm]. "
    "Then choose exactly ONE concrete food item that matches that mood for quick delivery. "
    "Prefer universal dishes (e.g., 'margherita pizza', 'chicken burrito', 'poke bowl', "
    "'ramen', 'sushi roll', 'greek salad', 'falafel wrap', 'pad thai', 'butter chicken', 'bibimbap'). "
    "Return STRICT JSON with keys: mood, food, reasoning. No extra text."
)

USER_TEMPLATE = (
    "Commit messages (newest first):\n"
    "{bulleted}\n\n"
    "Rules:\n"
    "- mood must be one token from the set.\n"
    "- food must be a concrete, orderable dish (not a cuisine or restaurant).\n"
    "- Keep reasoning 1–2 short sentences.\n"
    "Output JSON only."
)

def _to_bulleted(commits: List[str]) -> str:
    return "\n".join(f"- {m.strip()}" for m in commits if m and m.strip())

@proto.on_message(RecommendFoodRequest, replies=RecommendFoodResponse)
async def handle_food(ctx: Context, msg: RecommendFoodRequest):
    bulleted = _to_bulleted(msg.commits) if msg.commits else "- (no commits provided)"
    user = USER_TEMPLATE.format(bulleted=bulleted)

    comp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": SYS},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=200,
        response_format={"type": "json_object"},
    )

    raw = comp.choices[0].message.content
    try:
        data = json.loads(raw)
        mood = str(data.get("mood", "")).strip().lower()
        food = str(data.get("food", "")).strip()
        reasoning: Optional[str] = str(data.get("reasoning", "")).strip() or None
    except Exception:
        mood, food, reasoning = "meh", "margherita pizza", "Fallback due to parse error."

    allowed = {"focused", "energized", "meh", "stressed", "celebratory", "calm"}
    if mood not in allowed:
        mood = "meh"
    if not food:
        food = "margherita pizza"

    await ctx.send(ctx.sender, RecommendFoodResponse(mood=mood, food=food, reasoning=reasoning))

agent = Agent(name="food_decider", seed=os.getenv("SEED", "food-decider-seed"))
agent.include(proto)

# --- Local CLI demo (no agent network needed) ---
def _demo(commits: List[str]):
    bulleted = _to_bulleted(commits)
    user = USER_TEMPLATE.format(bulleted=bulleted)
    comp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": SYS}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=200,
        response_format={"type": "json_object"},
    )
    print(comp.choices[0].message.content)

if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--demo"]
        _demo(args or [
            "fix: flaky websocket reconnect",
            "feat: add retry with exponential backoff",
            "chore: update deployment docs",
        ])
    else:
        agent.run()
