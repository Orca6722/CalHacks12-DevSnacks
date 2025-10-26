import asyncio
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, constr

from uagents import Agent, Context, Model

# ========= Hosted agent address (replace if needed) =========
REMOTE_ADDR = "agent1qgj6hulwjjkmmu7dr6jwh0drwuayjehcmtuhg8lf2v9ttsw6lu4w6j77v88"

# ========= uAgents models (MUST match hosted agent) =========
class CommitData(Model):
    commits: List[str]

class UserCommitsQuery(Model):
    username: str
    token: str
    since_iso: Optional[str] = None
    per_page: Optional[int] = 20

# ========= FastAPI DTOs =========
class RunRequest(BaseModel):
    username: str
    token: str

class RunResponse(BaseModel):
    commits: List[str]

app = FastAPI(title="User Commits API")

async def call_agent_once(username: str, token: str, since_iso: Optional[str]) -> List[str]:
    """
    Spin up a fresh uAgents client (configured like your working script),
    wait briefly for the ephemeral mailbox to bind, send the query, capture the response,
    and shut the client down.
    """
    result_fut: asyncio.Future[List[str]] = asyncio.get_event_loop().create_future()

    # EXACTLY like your working client:
    client = Agent(
        name="github_commits_client",
        seed="client-seed",
        mailbox="https://mailbox.fetch.ai",   # ephemeral relay that doesn't require inspector clicks
        port=8011,                             # avoid FastAPI's 8000
    )

    @client.on_event("startup")
    async def go(ctx: Context):
        # Give the relay a moment to bind (matches your working example)
        await asyncio.sleep(1.5)
        resp, rest = await ctx.send_and_receive(
            REMOTE_ADDR,
            UserCommitsQuery(username=username, token=token, since_iso=since_iso, per_page=20),
            CommitData,
            timeout=45.0,
        )
        if isinstance(resp, CommitData):
            if not result_fut.done():
                result_fut.set_result(resp.commits or [])
        else:
            # Return empty list on failure; you can push error info here if desired
            if not result_fut.done():
                result_fut.set_result([])

    # Run the agent in a thread (non-blocking), await result, then stop
    task = asyncio.create_task(asyncio.to_thread(client.run))
    try:
        commits: List[str] = await asyncio.wait_for(result_fut, timeout=60.0)
    finally:
        if not task.done():
            task.cancel()
    return commits

@app.post("/api/run", response_model=RunResponse)
async def run(req: RunRequest) -> RunResponse:
    commits = await call_agent_once(req.username, req.token, None)
    return RunResponse(commits=commits)
