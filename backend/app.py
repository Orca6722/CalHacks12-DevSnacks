"""
Orchestrator API: fetch commits via the uAgents client (re-uses server.call_agent_once),
pass commits to food_decider.recommend_food_from_commits, then (optionally) place an order
via the DoorDash client.

If DoorDash credentials are not present in env, the endpoint will return the recommender
result and indicate the order was skipped.

POST /api/order -> accepts username/token and pickup/dropoff details and returns:
{ commits, recommendation, order_response }
"""
from typing import Optional
import os
import asyncio
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
import json
import logging

# re-use helper from server module to obtain commits
# Intentionally do NOT import or call the hosted uAgents client here.
# The app will use hard-coded sample commits for now so the endpoint is
# stable and doesn't fail when the agent or network is unavailable.
# from server import call_agent_once

# The agentverse agents are in a folder with a dash in the name ("agentverse-agents"),
# so normal dotted imports will fail. Load the modules by file path using importlib.
import importlib.util
import types
from pathlib import Path

BASE = Path(__file__).resolve().parent
AV_AGENTS = BASE / "agentverse-agents"


def load_module_from_path(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    # Ensure the module is available in sys.modules before executing it.
    # Some decorators (e.g. dataclasses) expect the module to be present there
    # when they inspect class __module__ during decoration.
    import sys
    sys.modules[name] = mod
    loader = spec.loader
    assert loader is not None
    loader.exec_module(mod)
    return mod


# recommender from food_decider (file: agentverse-agents/agents/food_decider/main.py)
food_decider_path = AV_AGENTS / "agents" / "food_decider" / "main.py"
food_decider = load_module_from_path("food_decider_main", food_decider_path)

# DoorDash client (file: agentverse-agents/doordash.py)
doordash_mod = load_module_from_path("doordash_client", AV_AGENTS / "doordash.py")
DoorDashClient = doordash_mod.DoorDashClient
DoorDashCreds = doordash_mod.DoorDashCreds

app = FastAPI(title="Orchestrator API")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

class OrderRequest(BaseModel):
    username: str
    token: str
    # dropoff / contact details (required to place a DoorDash order)
    dropoff_address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    # pickup info
    pickup_address: Optional[str] = None
    pickup_business_name: Optional[str] = None
    pickup_phone_number: Optional[str] = None
    # ordering behavior
    poll: Optional[bool] = True

class OrderResponse(BaseModel):
    commits: list
    recommendation: dict
    order_response: Optional[dict] = None
    note: Optional[str] = None


# Fallback sample commits used when the uAgents client fails to fetch commits
SAMPLE_COMMITS = [
    "fix: resolve flaky connection issue",
    "feat: add user preferences endpoint",
    "chore: update CI to include unit tests",
]

# --- Hard-coded DoorDash credentials and sample pickup/dropoff (replace with real values) ---
# You said you'll hardcode the creds here; these placeholders should be replaced with
# your sandbox credentials. Keep the format as strings.
HARDCODE_DOORDASH = {
    "base_url": os.getenv("DOORDASH_BASE_URL") or "https://openapi.doordash.com/drive/v2",
    "developer_id": os.getenv("DOORDASH_DEVELOPER_ID") or "a4128903-af33-4ee0-9b6f-2beacca10227",
    "key_id": os.getenv("DOORDASH_KEY_ID") or "607ba3b5-e79f-446d-8af8-6a883a3626ec",
    "signing_secret": os.getenv("DOORDASH_SIGNING_SECRET") or "lPHMRmf6_nXBMf-P-Y_rLMfqaH4_PWu2ntAG3GsA8Tk",
}

# If the request omits pickup/dropoff fields, use these sane defaults so ordering still runs.
SAMPLE_PICKUP = {
    "pickup_address": "100 Sample Pickup St, FoodCity, FC 12345",
    "pickup_business_name": "Sample Restaurant",
    "pickup_phone_number": "+15550001111",
}

SAMPLE_DROPOFF = {
    "dropoff_address": "200 Sample Dropoff Ave, HomeTown, HT 54321",
    "contact_name": "Sample Customer",
    "contact_phone": "+15550002222",
}


@app.post("/api/order", response_model=OrderResponse)
async def order(req: OrderRequest):
    # 1) Get commits via the hosted agent client (uAgents)
    # Use hard-coded sample commits for now (no RPC calls to hosted agent).
    commits = SAMPLE_COMMITS
    note_messages = ["using hard-coded sample commits (agent calls disabled)"]

    # 2) Get recommendation from food_decider
    try:
        recommendation = food_decider.recommend_food_from_commits(commits)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommender error: {e}")

    # 3) Place DoorDash order using hard-coded creds (user asked to force this path).
    base_url = HARDCODE_DOORDASH["base_url"]
    developer_id = HARDCODE_DOORDASH["developer_id"]
    key_id = HARDCODE_DOORDASH["key_id"]
    signing_secret = HARDCODE_DOORDASH["signing_secret"]

    # Use request values when provided; otherwise, fall back to sample pickup/dropoff.
    pickup_address = req.pickup_address or SAMPLE_PICKUP["pickup_address"]
    pickup_business_name = req.pickup_business_name or SAMPLE_PICKUP["pickup_business_name"]
    pickup_phone_number = req.pickup_phone_number or SAMPLE_PICKUP["pickup_phone_number"]

    dropoff_address = req.dropoff_address or SAMPLE_DROPOFF["dropoff_address"]
    contact_name = req.contact_name or SAMPLE_DROPOFF["contact_name"]
    contact_phone = req.contact_phone or SAMPLE_DROPOFF["contact_phone"]

    creds = DoorDashCreds(developer_id=developer_id, key_id=key_id, signing_secret=signing_secret)
    dd = DoorDashClient(base_url=base_url, creds=creds)
    try:
        order_resp = dd.order_food_from_recommendation(
            food_name=recommendation.get("food"),
            dropoff_address=dropoff_address,
            contact_name=contact_name,
            contact_phone=contact_phone,
            pickup_address=pickup_address,
            pickup_business_name=pickup_business_name,
            pickup_phone_number=pickup_phone_number,
            poll=req.poll,
        )
    except Exception as e:
        # Surface DoorDash errors back to client for debugging.
        raise HTTPException(status_code=500, detail=f"DoorDash error: {e}")

    # Print DoorDash raw response to terminal/log so you can see it immediately.
    try:
        logging.info("DoorDash response:\n%s", json.dumps(order_resp, indent=2, default=str))
    except Exception:
        # Fallback to simple logging if json.dumps fails
        logging.info("DoorDash response: %s", str(order_resp))

    return OrderResponse(commits=commits, recommendation=recommendation, order_response=order_resp, note="DoorDash called with hard-coded creds")


if __name__ == "__main__":
    # By default, running `python app.py` will perform a one-shot demo using
    # the hard-coded SAMPLE_COMMITS and print the recommendation, then exit.
    # To start the HTTP server, pass --serve on the command line.
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Orchestrator demo / server")
    parser.add_argument("--serve", action="store_true", help="Start the FastAPI server (use uvicorn recommended)")
    parser.add_argument("--port", type=int, default=8001, help="Port to serve on when --serve is used")
    parser.add_argument("--order-demo", action="store_true", help="In demo mode, also place a DoorDash order and print the response")
    args = parser.parse_args()

    if args.serve:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        # One-shot demo: run recommender on SAMPLE_COMMITS and print JSON result.
        try:
            recommendation = food_decider.recommend_food_from_commits(SAMPLE_COMMITS)
        except Exception as e:
            print(f"Recommender error: {e}")
            raise

        out = {
            "commits": SAMPLE_COMMITS,
            "recommendation": recommendation,
            "note": "one-shot demo (use --serve to run HTTP server)",
        }
        print(json.dumps(out, indent=2))

        if args.order_demo:
            # Perform a DoorDash ordering demo using the same hard-coded creds and
            # sample pickup/dropoff values so you can see the order response in the terminal.
            try:
                creds = DoorDashCreds(developer_id=HARDCODE_DOORDASH["developer_id"], key_id=HARDCODE_DOORDASH["key_id"], signing_secret=HARDCODE_DOORDASH["signing_secret"])
                dd = DoorDashClient(base_url=HARDCODE_DOORDASH["base_url"], creds=creds)

                order_resp = dd.order_food_from_recommendation(
                    food_name=recommendation.get("food"),
                    dropoff_address=SAMPLE_DROPOFF["dropoff_address"],
                    contact_name=SAMPLE_DROPOFF["contact_name"],
                    contact_phone=SAMPLE_DROPOFF["contact_phone"],
                    pickup_address=SAMPLE_PICKUP["pickup_address"],
                    pickup_business_name=SAMPLE_PICKUP["pickup_business_name"],
                    pickup_phone_number=SAMPLE_PICKUP["pickup_phone_number"],
                    poll=False,
                )

                # Print result to terminal
                try:
                    print("\nDoorDash order response:")
                    print(json.dumps(order_resp, indent=2, default=str))
                except Exception:
                    print("DoorDash order response:", order_resp)

            except Exception as e:
                print(f"DoorDash demo error: {e}")
