# github_commits_client.py
import asyncio
from typing import List, Optional
from uagents import Agent, Context, Model

# ===== Models (must match agent) =====
class CommitData(Model):
    commits: List[str]

class UserCommitsQuery(Model):
    username: str
    token: str
    since_iso: Optional[str] = None
    per_page: Optional[int] = 20

# ===== Config =====
REMOTE_ADDR = "agent1qgj6hulwjjkmmu7dr6jwh0drwuayjehcmtuhg8lf2v9ttsw6lu4w6j77v88"

CLIENT = Agent(
    name="github_commits_client",
    seed="client-seed",
    mailbox="https://mailbox.fetch.ai",  # temporary relay
)

# ===== Logic =====
async def query_once(ctx: Context, username: str, token: str, since_iso: Optional[str] = None):
    resp, msgstatus = await ctx.send_and_receive(
        REMOTE_ADDR,
        UserCommitsQuery(username=username, token=token, since_iso=since_iso, per_page=20),
        CommitData,
        timeout=45.0,
    )

    if isinstance(resp, CommitData):
        print(resp)
        return

    ctx.logger.error(f"Unexpected response: {resp}")

@CLIENT.on_event("startup")
async def interactive(ctx: Context):
    await asyncio.sleep(1.5)  # wait for mailbox registration
    print("GitHub User Commits — enter details (blank username to quit).")
    while True:
        username = await asyncio.to_thread(input, "GitHub username: ")
        username = (username or "").strip()
        if not username:
            print("Goodbye.")
            break

        token = await asyncio.to_thread(input, "GitHub token (PAT) [required]: ")
        token = (token or "").strip()
        if not token:
            print("❌ Token is required.")
            continue

        # since_iso = await asyncio.to_thread(input, "Since (ISO 8601, e.g. 2025-10-01T00:00:00Z) [optional]: ")
        # since_iso = (since_iso or "").strip() or None

        await query_once(ctx, username=username, token=token) # since_iso = since_iso

if __name__ == "__main__":
    CLIENT.run()
