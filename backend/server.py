import os
import asyncio
import threading
from typing import List, Optional, Tuple
from concurrent.futures import Future

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uagents import Agent, Context, Model

# ====== CONFIG ======
REMOTE_ADDR = "agent1qgj6hulwjjkmmu7dr6jwh0drwuayjehcmtuhg8lf2v9ttsw6lu4w6j77v88"

# Disable any env that might force an HTTP endpoint/port
for k in ("PORT", "UAGENTS_PORT", "ENDPOINT", "UAGENTS_ENDPOINT", "UVICORN_PORT"):
    os.environ.pop(k, None)
os.environ.setdefault("UAGENTS_REGISTER", "false")
os.environ.setdefault("UAGENTS_NO_HTTP", "true")
os.environ.setdefault("UAGENTS_DISABLE_INSPECTOR", "true")

# ====== uAgents models (must match remote) ======
class CommitData(Model):
    commits: List[str]

class UserCommitsQuery(Model):
    username: str
    token: str
    since_iso: Optional[str] = None
    per_page: Optional[int] = 20

# ====== FastAPI DTOs ======
class RunRequest(BaseModel):
    username: str
    token: str

class RunResponse(BaseModel):
    commits: List[str]

app = FastAPI(title="User Commits API")

# CORS (dev-friendly; restrict later to your extension ID)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== Background client agent infrastructure ======
# We run ONE client agent in its own thread/loop and push requests via an asyncio.Queue inside that loop.
AGENT_THREAD: Optional[threading.Thread] = None
AGENT_LOOP: Optional[asyncio.AbstractEventLoop] = None
REQ_Q: Optional[asyncio.Queue] = None           # queue of (username, token, since_iso, future)
STARTED = threading.Event()

def agent_thread_main():
    """Runs in a dedicated thread with its own event loop."""
    global AGENT_LOOP, REQ_Q
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    AGENT_LOOP = loop
    REQ_Q = asyncio.Queue()

    # Mailbox-only client; no HTTP server or advertised endpoint; port=0 avoids collisions if server starts internally.
    try:
        client = Agent(
            name="github_commits_client",
            seed="client-seed",                  # keep stable if you've created a mailbox for this address
            mailbox="https://mailbox.fetch.ai",
            loop=loop,
            register=False,
            port=0,
        )
    except TypeError:
        client = Agent(
            name="github_commits_client",
            seed="client-seed",
            mailbox="https://mailbox.fetch.ai",
            loop=loop,
            port=0,
        )
        # Best-effort: ensure no endpoints are advertised / no HTTP is forced
        for attr in ("endpoints", "_endpoints"):
            if hasattr(client, attr):
                try:
                    getattr(client, attr).clear()
                except Exception:
                    setattr(client, attr, [])
        for attr in ("serve_http", "_serve_http"):
            if hasattr(client, attr):
                try:
                    setattr(client, attr, False)
                except Exception:
                    pass

    async def worker(ctx: Context):
        """Consumes requests from REQ_Q and resolves their futures."""
        STARTED.set()
        while True:
            item: Tuple[str, str, Optional[str], Future] = await REQ_Q.get()
            if item is None:
                break
            username, token, since_iso, fut = item
            try:
                resp, _ = await ctx.send_and_receive(
                    REMOTE_ADDR,
                    UserCommitsQuery(
                        username=username, token=token, since_iso=since_iso, per_page=20
                    ),
                    CommitData,
                    timeout=75.0,
                )
                commits = resp.commits if isinstance(resp, CommitData) else []
                fut.set_result(commits or [])
            except Exception as e:
                fut.set_result([])  # never bubble errors to the API; return empty list
            finally:
                REQ_Q.task_done()

    @client.on_event("startup")
    async def on_start(ctx: Context):
        # Give mailbox a moment to fully establish
        await asyncio.sleep(1.0)
        loop.create_task(worker(ctx))

    @client.on_event("shutdown")
    async def on_stop(ctx: Context):
        # drain queue if needed
        pass

    # Block this thread in the agent run loop
    try:
        client.run()
    finally:
        # Clean loop on exit
        pending = asyncio.all_tasks(loop=loop)
        for t in pending:
            t.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()


# FastAPI lifespan: start/stop the client thread
@app.on_event("startup")
async def _startup():
    global AGENT_THREAD
    if AGENT_THREAD is None or not AGENT_THREAD.is_alive():
        AGENT_THREAD = threading.Thread(target=agent_thread_main, daemon=True)
        AGENT_THREAD.start()
    # Wait for the agent to signal readiness (mailbox connected, worker running)
    await asyncio.get_running_loop().run_in_executor(None, STARTED.wait)

@app.on_event("shutdown")
async def _shutdown():
    # Ask worker to stop and ask agent to exit (if server exists)
    if AGENT_LOOP and REQ_Q:
        try:
            # Stop worker
            asyncio.run_coroutine_threadsafe(REQ_Q.put(None), AGENT_LOOP).result(5)
        except Exception:
            pass
        # Try to stop agent internal server if present
        # (We can't access ctx here; client.run() will exit when process ends since it's daemon thread.)

# ====== Public endpoint (unchanged shape) ======
async def call_agent_once(username: str, token: str, since_iso: Optional[str]) -> List[str]:
    """
    Enqueue a request to the background agent and await the result.
    """
    if not (AGENT_LOOP and REQ_Q and STARTED.is_set()):
        # Background agent not ready (shouldn't happen after startup)
        return []

    # Use a thread-safe Future; await via asyncio.wrap_future in this loop
    fut: Future = Future()
    try:
        # Put work item into the agent loop's queue
        put_f = asyncio.run_coroutine_threadsafe(REQ_Q.put((username, token, since_iso, fut)), AGENT_LOOP)
        put_f.result(timeout=5)
        # Await the result with a timeout from FastAPI's loop
        return await asyncio.wait_for(asyncio.wrap_future(fut), timeout=80.0)
    except asyncio.TimeoutError:
        return []
    except Exception:
        return []

@app.post("/api/run", response_model=RunResponse)
async def run(req: RunRequest) -> RunResponse:
    commits = await call_agent_once(req.username, req.token, None)
    return RunResponse(commits=commits)
