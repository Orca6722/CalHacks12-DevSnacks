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
    "You read recent developer commit messages and infer the developer’s current mood "
    "as a short, lowercase phrase (2–5 words), e.g., 'quietly focused', 'time-crunched and stressed', "
    "'excited and celebratory', or 'calm and steady'. "
    "Then choose exactly ONE concrete, orderable dish (a common menu item) that best fits that mood for quick delivery. "
    "Important:\n"
    "- Do NOT restrict choices to any example foods or mood that may appear in the prompt; examples are illustrative only.\n"
    "- Use your broad, general food knowledge. Prefer widely available, delivery-friendly dishes.\n"
    "- The dish must be a specific item (e.g., 'bibimbap', 'ramen', 'chicken burrito', 'greek salad'), not a cuisine or restaurant.\n"
    "- Keep the name natural and concise (no emojis, no extra descriptors).\n\n"
    "Heuristics examples:\n"
    "- stressed / time-crunched → warm, comforting, or hearty food (e.g., noodles, burrito, curry + rice)\n"
    "- celebratory / excited → festive or treat-like items (e.g., tacos, sushi rolls, cake, wings)\n"
    "- focused / calm → light or steady-energy items (e.g., grain bowls, salads, poke, soba)\n"
    "- tired / low-energy → simple, satisfying classics (e.g., pizza, sandwich, fried rice)\n\n"
    "Return STRICT JSON with keys: mood, food, reasoning. No extra text."
)

USER_TEMPLATE = (
    "Commit messages (newest first):\n"
    "{bulleted}\n\n"
    "Rules:\n"
    "- Infer a concise, lowercase mood phrase (2–5 words).\n"
    "- Pick exactly ONE dish name that best matches the mood.\n"
    "- Do NOT limit yourself to any examples mentioned in the prompt; use general food knowledge.\n"
    "- The dish must be a concrete menu item (not a cuisine or restaurant).\n"
    "- Keep reasoning to 1–2 short sentences.\n"
    "Output JSON only with keys: mood, food, reasoning."
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
