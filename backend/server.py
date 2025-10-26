import os
import asyncio
import threading
from typing import List, Optional, Tuple, Dict
from concurrent.futures import Future

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uagents import Agent, Context, Model

# ---- explicit local imports (no heuristics) ---------------------------------
from agentverse.agents.food_decider.main import recommend_food_from_commits
from doordash import DoorDashClient, DoorDashCreds

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
    # optional delivery fields (backend has sane defaults if omitted)
    dropoff_address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    pickup_address: Optional[str] = None
    pickup_business_name: Optional[str] = None
    pickup_phone_number: Optional[str] = None
    poll: bool = True  # poll DoorDash to terminal status by default

class RunResponse(BaseModel):
    commits: List[str]
    recommendation: Dict | None = None
    order_response: Dict | None = None
    order_url: str | None = None
    note: str | None = None

app = FastAPI(title="User Commits API")

# CORS (dev-friendly; restrict later to your extension ID)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- sane defaults + creds sourcing ------------------------------------------
SAMPLE_PICKUP = {
    "pickup_address": "901 Market St, San Francisco, CA 94103",
    "pickup_business_name": "Demo Restaurant",
    "pickup_phone_number": "+14155550123",  # E.164
}
SAMPLE_DROPOFF = {
    "dropoff_address": "1355 Market St, San Francisco, CA 94103",
    "contact_name": "Demo Customer",
    "contact_phone": "+14155550124",  # E.164
}

def _dd_creds_from_env_or_defaults() -> Optional[DoorDashCreds]:
    dev = "a4128903-af33-4ee0-9b6f-2beacca10227"
    kid = "607ba3b5-e79f-446d-8af8-6a883a3626ec"
    sec = "lPHMRmf6_nXBMf-P-Y_rLMfqaH4_PWu2ntAG3GsA8Tk"
    if not (dev and kid and sec):
        return None
    return DoorDashCreds(developer_id=dev, key_id=kid, signing_secret=sec)

def _dd_base_url() -> str:
    return os.getenv("DOORDASH_BASE_URL", "https://openapi.doordash.com/drive/v2").rstrip("/")

def _extract_order_url(order_resp: Optional[Dict]) -> Optional[str]:
    if not order_resp:
        return None
    raw = order_resp.get("raw") or {}
    return (
        raw.get("tracking_url")
        or raw.get("external_tracking_url")
        or raw.get("order_tracking_url")
        or raw.get("order_url")
        or None
    )

# ====== Background client agent infrastructure ===============================
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
            seed="client-seed",
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
                    UserCommitsQuery(username=username, token=token, since_iso=since_iso, per_page=20),
                    CommitData,
                    timeout=75.0,
                )
                commits = resp.commits if isinstance(resp, CommitData) else []
                fut.set_result(commits or [])
            except Exception:
                fut.set_result([])  # never bubble errors to the API; return empty list
            finally:
                REQ_Q.task_done()

    @client.on_event("startup")
    async def on_start(ctx: Context):
        await asyncio.sleep(1.0)
        loop.create_task(worker(ctx))

    @client.on_event("shutdown")
    async def on_stop(ctx: Context):
        pass

    try:
        client.run()
    finally:
        pending = asyncio.all_tasks(loop=loop)
        for t in pending:
            t.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

@app.on_event("startup")
async def _startup():
    global AGENT_THREAD
    if AGENT_THREAD is None or not AGENT_THREAD.is_alive():
        AGENT_THREAD = threading.Thread(target=agent_thread_main, daemon=True)
        AGENT_THREAD.start()
    await asyncio.get_running_loop().run_in_executor(None, STARTED.wait)

@app.on_event("shutdown")
async def _shutdown():
    if AGENT_LOOP and REQ_Q:
        try:
            asyncio.run_coroutine_threadsafe(REQ_Q.put(None), AGENT_LOOP).result(5)
        except Exception:
            pass

# ====== Helper to call the agent once ========================================
async def call_agent_once(username: str, token: str, since_iso: Optional[str]) -> List[str]:
    if not (AGENT_LOOP and REQ_Q and STARTED.is_set()):
        return []
    fut: Future = Future()
    try:
        put_f = asyncio.run_coroutine_threadsafe(REQ_Q.put((username, token, since_iso, fut)), AGENT_LOOP)
        put_f.result(timeout=5)
        return await asyncio.wait_for(asyncio.wrap_future(fut), timeout=80.0)
    except asyncio.TimeoutError:
        return []
    except Exception:
        return []

# ====== Public endpoint: run full pipeline after call_agent_once =============
@app.post("/api/run", response_model=RunResponse)
async def run(req: RunRequest) -> RunResponse:
    # 1) existing agent pipeline (unchanged)
    commits = await call_agent_once(req.username, req.token, None)

    out = RunResponse(
        commits=commits or [],
        recommendation=None,
        order_response=None,
        order_url=None,
        note=None,
    )

    # 2) use commit history -> recommend a food (explicit import from main.py)
    try:
        recommendation = recommend_food_from_commits(out.commits)
        out.recommendation = recommendation
    except Exception as e:
        out.note = f"Recommender error: {e}"
        return out

    # 3) order via DoorDash (explicit import from doordash.py)
    creds = _dd_creds_from_env_or_defaults()
    if not creds:
        out.note = "DoorDash creds missing; skipped ordering."
        return out

    # Merge pickup/dropoff with defaults if fields are missing
    pickup_address        = (req.pickup_address or SAMPLE_PICKUP["pickup_address"]).strip()
    pickup_business_name  = (req.pickup_business_name or SAMPLE_PICKUP["pickup_business_name"]).strip()
    pickup_phone_number   = (req.pickup_phone_number or SAMPLE_PICKUP["pickup_phone_number"]).strip()
    dropoff_address       = (req.dropoff_address or SAMPLE_DROPOFF["dropoff_address"]).strip()
    contact_name          = (req.contact_name or SAMPLE_DROPOFF["contact_name"]).strip()
    contact_phone         = (req.contact_phone or SAMPLE_DROPOFF["contact_phone"]).strip()

    dd = DoorDashClient(base_url=_dd_base_url(), creds=creds)

    try:
        # Build a minimal item list like app.py would
        food_name = (out.recommendation or {}).get("food") or "margherita pizza"
        items = [{
            "name": food_name,
            "quantity": 1,
            "description": f"Mood-based recommendation: {food_name}",
        }]

        # >>> IMPORTANT: call create_delivery directly (no polling) <<<
        created = dd.create_delivery(
            external_delivery_id=None,
            pickup_address=pickup_address,
            pickup_business_name=pickup_business_name,
            pickup_phone_number=contact_phone if pickup_phone_number == "" else pickup_phone_number,
            dropoff_address=dropoff_address,
            dropoff_business_name=contact_name,
            dropoff_phone_number=contact_phone,
            items=items,
            # add optional fields if you want:
            # order_value_cents=1999,
            # pickup_instructions="Ask for to-go packaging",
            # dropoff_instructions="Leave at the front desk",
            # additional_fields={...},
        )

        # Return EXACTLY the JSON DoorDash returned from create_delivery
        out.order_response = created

        # Best-effort link extraction (may not be present immediately)
        # If your _extract_order_url expects {"raw": ...}, wrap it:
        out.order_url = _extract_order_url({"raw": created})

        out.note = "DoorDash create_delivery called (no polling)."
    except Exception as e:
        out.note = f"DoorDash error: {e}"

    return out
