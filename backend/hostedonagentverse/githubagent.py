# agent_github_collector.py
import os
import re
from typing import Optional, Tuple, List
import httpx
from uagents import Agent, Context, Protocol, Model

class CommitData(Model):
    commits: List[str]  # simple list of commit messages

class Chat(Model):
    text: str  # plain text input (GitHub URL or owner/repo)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
proto = Protocol(name="github-collector", version="1.0.0")

def parse_repo_text(s: str) -> Tuple[str, str, Optional[str], Optional[str]]:
    s = s.strip()
    kv = {k: v for k, v in (p.split("=", 1) for p in s.split() if "=" in p)}
    branch = kv.get("branch")
    since_iso = kv.get("since") or kv.get("since_iso")

    m = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", s, flags=re.I)
    if m:
        owner, repo = m.group(1), m.group(2)
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo, branch, since_iso

    m = re.match(r"^\s*([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)\s*$", s)
    if m:
        return m.group(1), m.group(2), branch, since_iso

    if "owner" in kv and "repo" in kv:
        return kv["owner"], kv["repo"], branch, since_iso

    raise ValueError("Could not parse repository. Use a GitHub URL like "
                     "'https://github.com/<owner>/<repo>' or 'owner/repo'.")

async def fetch_commits(owner: str, repo: str,
                        branch: Optional[str],
                        since_iso: Optional[str]) -> List[str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "uagents-github-collector",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    params = {}
    if since_iso:
        params["since"] = since_iso
    if branch:
        params["sha"] = branch

    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers, params=params)
        r.raise_for_status()
        commits: List[str] = []
        for c in r.json():
            commits.append(c["commit"]["message"])
        return commits

@proto.on_message(Chat, replies=CommitData)
async def handle_chat(ctx: Context, sender: str, msg: Chat):
    try:
        owner, repo, branch, since_iso = parse_repo_text(msg.text)
        commits = await fetch_commits(owner, repo, branch, since_iso)
        await ctx.send(sender, CommitData(commits=commits))
    except Exception as e:
        ctx.logger.error(f"chat parse/fetch error: {e}")
        await ctx.send(sender, CommitData(commits=[]))

agent = Agent(name="github_collector", seed=os.getenv("SEED", "github-collector-seed"))
agent.include(proto)

if __name__ == "__main__":
    agent.run()
