# doordash_client.py
# Prod-ready DoorDash Drive v2 integration using DD-JWT-V1 and base64url-decoded signing_secret.
# Works with sandbox or prod depending on the base_url + creds you pass.
#
# Typical use:
#   client = DoorDashClient(base_url="https://openapi.doordash.com/drive/v2", creds=creds_dict)
#   summary = client.order_food_from_recommendation(
#       food_name=reco["food"],  # from your Groq agent
#       pickup_address=...,
#       pickup_business_name=...,
#       pickup_phone_number=...,
#       dropoff_address=...,
#       contact_name=...,
#       contact_phone=...,
#       poll=True,
#   )

from __future__ import annotations
import math
import time
import uuid
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

import jwt
import jwt.utils
import requests


@dataclass(frozen=True)
class DoorDashCreds:
    developer_id: str
    key_id: str
    signing_secret: str  # BASE64URL-encoded string exactly as portal shows


class DoorDashClient:
    def __init__(
        self,
        *,
        base_url: str,           # e.g. "https://openapi.doordash.com/drive/v2"
        creds: DoorDashCreds,
        timeout_s: int = 30
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self.base_url = base_url.rstrip("/")
        self.creds = creds
        self.timeout_s = timeout_s

    # ---------- Auth ----------
    def _token(self) -> str:
        now = math.floor(time.time())
        payload = {
            "aud": "doordash",
            "iss": self.creds.developer_id,
            "kid": self.creds.key_id,
            "exp": str(now + 300),  # 5 minutes
            "iat": str(now),
        }
        signing_key = jwt.utils.base64url_decode(self.creds.signing_secret)
        tok = jwt.encode(payload, signing_key, algorithm="HS256", headers={"dd-ver": "DD-JWT-V1"})
        return tok if isinstance(tok, str) else tok.decode("utf-8")

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept-Encoding": "application/json",
            "Authorization": f"Bearer {self._token()}",
            "Content-Type": "application/json",
        }

    # ---------- API ----------
    def create_delivery(
        self,
        *,
        external_delivery_id: Optional[str],
        pickup_address: str,
        pickup_business_name: str,
        pickup_phone_number: str,
        dropoff_address: str,
        dropoff_business_name: str,
        dropoff_phone_number: str,
        items: List[Dict[str, Any]],
        order_value_cents: Optional[int] = None,
        pickup_instructions: Optional[str] = None,
        dropoff_instructions: Optional[str] = None,
        additional_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "external_delivery_id": external_delivery_id or str(uuid.uuid4()),
            "pickup_address": pickup_address,
            "pickup_business_name": pickup_business_name,
            "pickup_phone_number": pickup_phone_number,
            "dropoff_address": dropoff_address,
            "dropoff_business_name": dropoff_business_name,
            "dropoff_phone_number": dropoff_phone_number,
            "items": items,
        }
        if order_value_cents is not None:
            body["order_value"] = order_value_cents
        if pickup_instructions:
            body["pickup_instructions"] = pickup_instructions
        if dropoff_instructions:
            body["dropoff_instructions"] = dropoff_instructions
        if additional_fields:
            body.update(additional_fields)

        url = f"{self.base_url}/deliveries/"
        resp = requests.post(url, headers=self._headers(), json=body, timeout=self.timeout_s)
        if not resp.ok:
            raise RuntimeError(f"create_delivery failed: {resp.status_code} {resp.text}")
        return resp.json()

    def get_delivery(self, delivery_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/deliveries/{delivery_id}"
        resp = requests.get(url, headers=self._headers(), timeout=self.timeout_s)
        if not resp.ok:
            raise RuntimeError(f"get_delivery failed: {resp.status_code} {resp.text}")
        return resp.json()

    def poll_until_terminal(
        self,
        delivery_id: str,
        *,
        interval_sec: int = 5,
        timeout_sec: int = 180
    ) -> Dict[str, Any]:
        start = time.time()
        while True:
            data = self.get_delivery(delivery_id)
            status = data.get("status")
            print(f"[DoorDash] status={status}")
            if status in {"delivered", "cancelled"}:
                return data
            if time.time() - start > timeout_sec:
                raise TimeoutError("DoorDash polling timed out")
            time.sleep(interval_sec)

    # ---------- High-level helper for your recommender output ----------
    def order_food_from_recommendation(
        self,
        *,
        food_name: str,                 # from your Groq agent's RecommendFoodResponse.food
        dropoff_address: str,
        contact_name: str,
        contact_phone: str,
        pickup_address: str,
        pickup_business_name: str,
        pickup_phone_number: str,
        order_value_cents: Optional[int] = None,   # if you have a price
        pickup_instructions: Optional[str] = None,
        dropoff_instructions: Optional[str] = None,
        poll: bool = True,
        interval_sec: int = 5,
        timeout_sec: int = 180,
        external_delivery_id: Optional[str] = None,
        additional_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Build a minimal item list; a single dish from the recommender.
        items = [{
            "name": food_name,
            "quantity": 1,
            "description": f"Mood-based recommendation: {food_name}",
        }]

        created = self.create_delivery(
            external_delivery_id=external_delivery_id,
            pickup_address=pickup_address,
            pickup_business_name=pickup_business_name,
            pickup_phone_number=pickup_phone_number,
            dropoff_address=dropoff_address,
            dropoff_business_name=contact_name,
            dropoff_phone_number=contact_phone,
            items=items,
            order_value_cents=order_value_cents,
            pickup_instructions=pickup_instructions,
            dropoff_instructions=dropoff_instructions,
            additional_fields=additional_fields,
        )

        # Delivery ID can be "id" or "external_delivery_id"
        delivery_id = created.get("id") or created.get("external_delivery_id")
        if not delivery_id:
            # Fallback to the external id we would have sent/generated
            delivery_id = external_delivery_id or items[0]["name"] + "-" + str(uuid.uuid4())

        final = self.poll_until_terminal(delivery_id, interval_sec=interval_sec, timeout_sec=timeout_sec) if poll else self.get_delivery(delivery_id)

        # Front-end–ready summary
        return {
            "delivery_id": delivery_id,
            "food": {"name": food_name, "quantity": 1},
            "pickup": {
                "business_name": final.get("pickup_business_name") or created.get("pickup_business_name"),
                "address":       final.get("pickup_address") or created.get("pickup_address"),
                "phone":         final.get("pickup_phone_number") or created.get("pickup_phone_number"),
            },
            "dropoff": {
                "address":       final.get("dropoff_address") or dropoff_address,
                "contact_name":  final.get("dropoff_business_name") or contact_name,
                "contact_phone": final.get("dropoff_phone_number") or contact_phone,
                "eta":           final.get("dropoff_eta"),
            },
            "status": final.get("status"),
            "driver": {
                "name":  final.get("dasher_name"),
                "phone": final.get("dasher_dropoff_phone_number"),
            },
            "raw": final,  # keep everything for UI/debug
        }
