"""Legacy approval routes for backward compatibility with dashboard."""
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import contacts, db
from app.dashboard import require_auth
from app.memory import add_assistant_message

router = APIRouter()
AUTH = [Depends(require_auth)]


class SendRequest(BaseModel):
    text: str | None = Field(default=None, max_length=4000)


@router.get("/api/held", dependencies=AUTH)
def list_held():
    items = []
    for r in db.pending():
        name = contacts.name_for(r["chat_id"], r.get("number"))
        items.append({
            "id": r["id"],
            "name": name,
            "from": name or r["chat_id"].split("@")[0],
            "incoming": r["incoming"],
            "reply": r["reply"],
            "reason": r.get("reason") or "",
        })
    return {"items": items}


@router.post("/api/held/{item_id}/send", dependencies=AUTH)
def send_held(item_id: int, body: SendRequest):
    item = db.get(item_id)
    if not item:
        raise HTTPException(404, "No such item.")
    text = (body.text if body.text is not None else item["reply"]).strip()
    if not text:
        raise HTTPException(400, "The reply is empty.")
    if not db.transition(item_id, "pending", "sending"):
        raise HTTPException(409, "Already handled.")

    bridge_url = os.getenv("BRIDGE_API_URL", "http://127.0.0.1:3001")
    try:
        r = httpx.post(
            f"{bridge_url}/send-reply",
            json={"chat_id": item["chat_id"], "text": text},
            headers={"x-bridge-token": os.getenv("BRIDGE_API_TOKEN", "")},
            timeout=30,
        )
        r.raise_for_status()
    except httpx.HTTPError:
        db.transition(item_id, "sending", "pending")
        err = "Couldn't send through the bridge. Is it running?"
        raise HTTPException(502, err)

    db.transition(item_id, "sending", "approved")
    add_assistant_message(item["chat_id"], text)
    return {"status": "sent", "text": text}


@router.post("/api/held/{item_id}/reject", dependencies=AUTH)
def reject_held(item_id: int):
    if not db.transition(item_id, "pending", "rejected"):
        raise HTTPException(409, "Already handled.")
    return {"status": "rejected"}
