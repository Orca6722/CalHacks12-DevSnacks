from uagents import Agent, Context
from ..shared.models import PlaceOrder, DeliveryResponse
from ..shared.doordash import build_body_from_place_order, create_delivery

order_agent = Agent(name="order_agent")

@order_agent.on_message(PlaceOrder)
async def place(ctx: Context, msg: PlaceOrder):
    try:
        body = build_body_from_place_order(msg.model_dump())
        res = create_delivery(body)
        out = DeliveryResponse(
            external_delivery_id=res.get("external_delivery_id", body["external_delivery_id"]),
            status=res.get("status", "created"),
            eta=res.get("dropoff_time_estimated_seconds"),
            tracking_url=res.get("tracking_url"),
            raw=res,
        )
        ctx.logger.info(f"OrderAgent: Created delivery {out.external_delivery_id}")
    except Exception as e:
        ctx.logger.error(f"OrderAgent error: {e}")