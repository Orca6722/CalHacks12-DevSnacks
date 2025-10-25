import time
import math
import uuid
import jwt
import requests
from typing import Dict
from .settings import (
    DOORDASH_DEVELOPER_ID,
    DOORDASH_KEY_ID,
    DOORDASH_SIGNING_SECRET,
    DOORDASH_BASE,
)

HEADERS_VER = {"dd-ver": "DD-JWT-V1"}


def _jwt() -> str:
    if not (DOORDASH_DEVELOPER_ID and DOORDASH_KEY_ID and DOORDASH_SIGNING_SECRET):
        raise RuntimeError("DoorDash credentials missing. Set DOORDASH_* in .env")
    payload = {
        "aud": "doordash",
        "iss": DOORDASH_DEVELOPER_ID,
        "kid": DOORDASH_KEY_ID,
        "exp": str(math.floor(time.time() + 300)),
        "iat": str(math.floor(time.time())),
    }
    token = jwt.encode(
        payload,
        jwt.utils.base64url_decode(DOORDASH_SIGNING_SECRET),
        algorithm="HS256",
        headers=HEADERS_VER,
    )
    return token


def create_delivery(body: Dict) -> Dict:
    url = f"{DOORDASH_BASE}/drive/v2/deliveries"
    headers = {"Authorization": f"Bearer {_jwt()}", "Content-Type": "application/json"}
    resp = requests.post(url, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_delivery(external_delivery_id: str) -> Dict:
    url = f"{DOORDASH_BASE}/drive/v2/deliveries/{external_delivery_id}"
    headers = {"Authorization": f"Bearer {_jwt()}"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_body_from_place_order(po: Dict) -> Dict:
    external_id = f"DSNACK-{uuid.uuid4().hex[:10]}"
    body = {
        "external_delivery_id": external_id,
        "order_fulfillment_method": "standard",
        "pickup_address": po.get("pickup_address"),
        "pickup_business_name": po.get("pickup_business_name"),
        "pickup_phone_number": po.get("pickup_phone_number"),
        "pickup_instructions": po.get("pickup_instructions", ""),
        "dropoff_address": po["dropoff_address"],
        "dropoff_phone_number": po["dropoff_phone_number"],
        "dropoff_contact_given_name": po.get("dropoff_contact_given_name") or "Dev",
        "dropoff_contact_family_name": po.get("dropoff_contact_family_name") or "Snacker",
        "dropoff_instructions": "Leave at front desk if no answer",
        "contactless_dropoff": True,
        "items": [
            {
                "name": po.get("item_name", "Recommended Item"),
                "quantity": 1,
            }
        ],
        "tip": int(po.get("tip_cents") or 0),
    }
    return body