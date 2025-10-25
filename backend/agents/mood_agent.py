from uagents import Agent, Context
from ..shared.models import CommitBatch, MoodSignal
from ..shared.groq_client import extract_mood_json

mood_agent = Agent(name="mood_agent")

@mood_agent.on_message(CommitBatch)
async def to_mood(ctx: Context, msg: CommitBatch):
    try:
        mood = extract_mood_json(msg.commits)
    except Exception as e:
        ctx.logger.error(f"Groq error: {e}")
        mood = {
            "mood": "neutral", "energy": "med", "valence": "neutral",
            "diet": "light", "budget": 12, "spice": "low", "time": "evening",
            "query": "light, quick, under $12"
        }
    signal = MoodSignal(
        mood=mood["mood"], energy=mood["energy"], valence=mood["valence"],
        budget=float(mood["budget"]), diet=mood["diet"], spice=mood["spice"], time=mood["time"],
        query=mood["query"]
    )
    target = ctx.storage.get("reco_addr")
    if target:
        await ctx.send(target, signal)
        ctx.logger.info(f"MoodAgent: sent MoodSignal → RecoAgent :: {signal.query}")