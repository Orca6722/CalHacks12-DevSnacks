from uagents import Bureau
from .agents.commit_agent import commit_agent
from .agents.mood_agent import mood_agent
from .agents.reco_agent import reco_agent
from .agents.order_agent import order_agent
from .shared.settings import COMMIT_POLL_SECONDS

# Wire addresses for message routing via agent storage
@commit_agent.on_startup
async def _wire_commit(ctx):
    ctx.storage.set("mood_addr", mood_agent.address)

@mood_agent.on_startup
async def _wire_mood(ctx):
    ctx.storage.set("reco_addr", reco_agent.address)

# Adjust commit polling interval dynamically (optional)
commit_agent._intervals.clear()
commit_agent.interval(COMMIT_POLL_SECONDS)(lambda ctx: None)  # hack to set interval value

if __name__ == "__main__":
    bureau = Bureau()
    bureau.add(commit_agent)
    bureau.add(mood_agent)
    bureau.add(reco_agent)
    bureau.add(order_agent)
    print("Running uAgents Bureau...\n",
          f"commit_agent: {commit_agent.address}\n",
          f"mood_agent:   {mood_agent.address}\n",
          f"reco_agent:   {reco_agent.address}\n",
          f"order_agent:  {order_agent.address}")
    bureau.run()