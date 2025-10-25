# github_commits_client.py
import asyncio
import json
from uagents import Agent, Context, Model
from typing import List

class Chat(Model):
    text: str

class CommitData(Model):
    commits: List[str]

REMOTE_ADDR = "agent1qgj6hulwjjkmmu7dr6jwh0drwuayjehcmtuhg8lf2v9ttsw6lu4w6j77v88"

CLIENT = Agent(
    name="github_commits_client",
    seed="client-seed",
    mailbox="https://mailbox.fetch.ai",  # temporary mailbox relay
)
def print_commits(commits: List[str], label: str = "Recent commit messages"):
    if not commits:
        print("No commits found.")
        return
    print(f"\n{label}:")
    print("------------------------")
    for i, m in enumerate(commits[:20], 1):
        print(f"{i:02d}. {m.splitlines()[0]}")

async def query_once(ctx: Context, github_url: str):
    resp, msgstatus = await ctx.send_and_receive(
        REMOTE_ADDR, Chat(text=github_url), CommitData, timeout=45.0
    )

    if isinstance(resp, CommitData):
        print(resp)
        return resp

    ctx.logger.error(f"Received unexpected response: {resp}")
    print("Request failed; see logs above.")

@CLIENT.on_event("startup")
async def interactive(ctx: Context):
    await asyncio.sleep(1.5)  # let the mailbox register
    print("Client is running. Paste GitHub repo URLs (blank line to quit).")
    while True:
        url = await asyncio.to_thread(input, "GitHub URL: ")
        url = (url or "").strip()
        if not url:
            print("Goodbye.")
            break
        await query_once(ctx, url)

if __name__ == "__main__":
    CLIENT.run()
