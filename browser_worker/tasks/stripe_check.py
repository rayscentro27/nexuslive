"""
Stripe check — uses Stripe API (not browser) to report recent webhook events.
"""
import os
import json
import urllib.request
from datetime import datetime, timezone


async def run(page, payload: dict) -> dict:
    """Check recent Stripe webhook deliveries and subscription events."""
    api_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not api_key:
        return {"status": "error", "message": "STRIPE_SECRET_KEY not set"}

    def stripe_get(path: str) -> dict:
        req = urllib.request.Request(
            f"https://api.stripe.com/v1/{path}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    # Recent events
    events_data = stripe_get("events?limit=10&types[]=checkout.session.completed"
                              "&types[]=customer.subscription.updated"
                              "&types[]=customer.subscription.deleted")
    events = events_data.get("data", [])

    lines = [f"Stripe Recent Events ({len(events)} found):"]
    for evt in events[:5]:
        ts = datetime.fromtimestamp(evt["created"], tz=timezone.utc).strftime("%m/%d %H:%M")
        lines.append(f"  [{ts}] {evt['type']} — {evt.get('id','?')[:20]}")

    # Webhook endpoint status
    try:
        webhooks = stripe_get("webhook_endpoints?limit=5")
        for wh in webhooks.get("data", []):
            lines.append(f"\nWebhook: {wh.get('url','?')[:60]}")
            lines.append(f"  Status: {wh.get('status','?')} | Events: {len(wh.get('enabled_events',[]))}")
    except Exception as e:
        lines.append(f"\nWebhook fetch failed: {e}")

    return {
        "status": "ok",
        "summary": "\n".join(lines),
        "event_count": len(events),
    }
