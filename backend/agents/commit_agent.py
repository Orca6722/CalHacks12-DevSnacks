from uagents import Agent, Context
from ..shared.models import CommitBatch
from ..shared.git_utils import read_local_commits

commit_agent = Agent(name="commit_agent")

@commit_agent.on_interval(period=60.0)
async def poll_repo(ctx: Context):
    commits = read_local_commits()
    batch = CommitBatch(repo="local", commits=commits)
    # Send to MoodAgent (address injected by run_agents)
    target = ctx.storage.get("mood_addr")
    if target:
        await ctx.send(target, batch)
        ctx.logger.info(f"CommitAgent: sent {len(commits)} commits → MoodAgent")