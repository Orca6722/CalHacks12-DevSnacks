# agents/github_collector/main.py
import os, httpx
from uagents import Agent, Context, Protocol
from shared.schemas import CollectCommitsRequest, CollectCommitsResponse, CommitRecord

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

proto = Protocol("github-collector", version="1.0.0")

@proto.on_message(CollectCommitsRequest, replies=CollectCommitsResponse)
async def handle_collect(ctx: Context, msg: CollectCommitsRequest):
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    params = {}
    if msg.since_iso: params["since"] = msg.since_iso
    if msg.branch: params["sha"] = msg.branch

    url = f"https://api.github.com/repos/{msg.owner}/{msg.repo}/commits"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers, params=params)
        r.raise_for_status()
        commits = []
        for c in r.json():
            commit = c["commit"]
            commits.append(CommitRecord(
                sha=c["sha"],
                author=(commit.get("author") or {}).get("name"),
                message=commit["message"],
                date_iso=(commit.get("author") or {}).get("date") or ""
            ))
    await ctx.send(ctx.sender, CollectCommitsResponse(commits=commits))

agent = Agent(name="github_collector", seed=os.getenv("SEED", "github-collector-seed"))
agent.include(proto)

if __name__ == "__main__":
    agent.run()
