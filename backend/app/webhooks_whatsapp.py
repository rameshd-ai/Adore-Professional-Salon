"""WhatsApp Cloud API webhooks: subscription verify (GET) and inbound messages (POST)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import PlainTextResponse

from app.database import get_db
from app.models import ApiSettings, Customer, WhatsAppInboxMessage
from app.whatsapp_meta import normalize_whatsapp_recipient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


def _verify_meta_signature(body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    got = signature_header[7:]
    return hmac.compare_digest(expected, got)


def _message_body_and_type(msg: dict[str, Any]) -> tuple[str, str]:
    mtype = (msg.get("type") or "unknown").strip() or "unknown"
    if mtype == "text":
        body = ((msg.get("text") or {}).get("body") or "").strip()
        return body, mtype
    if mtype == "image":
        cap = ((msg.get("image") or {}).get("caption") or "").strip()
        return (cap or "[image]"), mtype
    if mtype == "video":
        cap = ((msg.get("video") or {}).get("caption") or "").strip()
        return (cap or "[video]"), mtype
    if mtype == "document":
        cap = ((msg.get("document") or {}).get("caption") or "").strip()
        fn = ((msg.get("document") or {}).get("filename") or "").strip()
        return (cap or fn or "[document]"), mtype
    if mtype == "audio":
        return "[audio]", mtype
    if mtype == "sticker":
        return "[sticker]", mtype
    if mtype == "location":
        loc = msg.get("location") or {}
        lat, lng = loc.get("latitude"), loc.get("longitude")
        return (f"[location] {lat}, {lng}" if lat is not None else "[location]"), mtype
    if mtype == "button":
        body = ((msg.get("button") or {}).get("text") or "").strip()
        return body or "[button]", mtype
    if mtype == "interactive":
        inter = msg.get("interactive") or {}
        itype = inter.get("type")
        if itype == "button_reply":
            body = ((inter.get("button_reply") or {}).get("title") or "").strip()
            return body or "[button reply]", mtype
        if itype == "list_reply":
            body = ((inter.get("list_reply") or {}).get("title") or "").strip()
            return body or "[list reply]", mtype
        return f"[interactive:{itype or '?'}]", mtype
    return f"[{mtype}]", mtype


def _parse_inbound_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if payload.get("object") != "whatsapp_business_account":
        return out
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            messages = value.get("messages") or []
            if not messages:
                continue
            contacts: dict[str, str] = {}
            for c in value.get("contacts") or []:
                wid = (c.get("wa_id") or "").strip()
                name = ((c.get("profile") or {}).get("name") or "").strip()
                if wid:
                    contacts[wid] = name
            for msg in messages:
                from_id = (msg.get("from") or "").strip()
                mid = (msg.get("id") or "").strip()
                if not from_id or not mid:
                    continue
                ts_raw = msg.get("timestamp")
                created_at: datetime | None = None
                if ts_raw is not None:
                    try:
                        created_at = datetime.fromtimestamp(int(ts_raw), tz=timezone.utc)
                    except (TypeError, ValueError, OSError):
                        created_at = None
                body, mtype = _message_body_and_type(msg)
                out.append(
                    {
                        "wa_message_id": mid,
                        "from_wa_id": from_id,
                        "profile_name": contacts.get(from_id, ""),
                        "message_type": mtype,
                        "body": body,
                        "created_at": created_at,
                        "raw": msg,
                    }
                )
    return out


def _match_customer_id(db: Session, from_wa_id: str) -> int | None:
    normalized = normalize_whatsapp_recipient(from_wa_id)
    if not normalized:
        return None
    rows = db.scalars(select(Customer).where(Customer.is_active.is_(True))).all()
    for c in rows:
        n = normalize_whatsapp_recipient(c.phone or "")
        if n and n == normalized:
            return c.id
    return None


def store_inbound_whatsapp_messages(db: Session, payload: dict[str, Any]) -> int:
    items = _parse_inbound_messages(payload)
    n = 0
    for item in items:
        mid = item["wa_message_id"]
        existing = db.scalar(
            select(WhatsAppInboxMessage.id).where(WhatsAppInboxMessage.wa_message_id == mid).limit(1)
        )
        if existing is not None:
            continue
        cid = _match_customer_id(db, item["from_wa_id"])
        try:
            raw = json.dumps(item.get("raw") or {}, ensure_ascii=False)
        except (TypeError, ValueError):
            raw = "{}"
        if len(raw) > 12000:
            raw = raw[:12000] + "…"
        row = WhatsAppInboxMessage(
            wa_message_id=mid,
            from_wa_id=item["from_wa_id"][:32],
            profile_name=(item.get("profile_name") or "")[:160],
            message_type=(item.get("message_type") or "unknown")[:40],
            body_text=(item.get("body") or "")[:16000],
            raw_payload=raw,
            customer_id=cid,
        )
        if item.get("created_at") is not None:
            row.created_at = item["created_at"]
        db.add(row)
        n += 1
    if n:
        db.commit()
    return n


@router.get("/whatsapp", include_in_schema=False)
def whatsapp_webhook_verify(request: Request, db: Session = Depends(get_db)) -> PlainTextResponse:
    """Meta sends hub.mode, hub.verify_token, hub.challenge when you subscribe the webhook."""
    qp = request.query_params
    if qp.get("hub.mode") != "subscribe":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid hub.mode")
    challenge = qp.get("hub.challenge") or ""
    token = qp.get("hub.verify_token") or ""
    row = db.query(ApiSettings).filter(ApiSettings.id == 1).first()
    expected = (row.whatsapp_webhook_verify_token or "").strip() if row else ""
    if not expected or token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verify token mismatch")
    return PlainTextResponse(content=challenge, status_code=200)


@router.post("/whatsapp", include_in_schema=False)
async def whatsapp_webhook_receive(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    body = await request.body()
    row = db.query(ApiSettings).filter(ApiSettings.id == 1).first()
    secret = (row.whatsapp_app_secret or "").strip() if row else ""
    if secret:
        sig = request.headers.get("x-hub-signature-256")
        if not _verify_meta_signature(body, sig, secret):
            logger.warning("WhatsApp webhook rejected: bad X-Hub-Signature-256")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {"status": "ok"}

    if not isinstance(payload, dict):
        return {"status": "ok"}

    try:
        stored = store_inbound_whatsapp_messages(db, payload)
    except Exception:
        logger.exception("WhatsApp webhook store failed")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Store failed")

    return {"status": "ok", "stored": stored}
