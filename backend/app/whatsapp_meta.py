"""WhatsApp Cloud API (Meta) helpers — used from the admin broadcast page only."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


def normalize_whatsapp_recipient(raw: str) -> str | None:
    """Digits only, country code, no leading +. Assumes India (91) for 10-digit local numbers."""
    if not raw:
        return None
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) < 10:
        return None
    if len(digits) == 10:
        return "91" + digits
    return digits


def _graph_url(api_version: str, phone_number_id: str) -> str:
    v = (api_version or "v22.0").strip().lstrip("/")
    pid = (phone_number_id or "").strip()
    return f"https://graph.facebook.com/{v}/{pid}/messages"


@dataclass
class SendResult:
    ok: bool
    status_code: int
    detail: str
    raw: dict[str, Any] | None = None


def _post_json(url: str, token: str, payload: dict[str, Any]) -> SendResult:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw_txt = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw_txt) if raw_txt else {}
            except json.JSONDecodeError:
                data = {"_raw": raw_txt}
            return SendResult(True, resp.status, "sent", data if isinstance(data, dict) else {"_raw": data})
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("error", {}).get("message", err_body[:500])
        except (json.JSONDecodeError, AttributeError, TypeError):
            msg = err_body[:500] or str(e.reason)
        return SendResult(False, e.code, msg, None)
    except Exception as e:
        return SendResult(False, 0, str(e)[:500], None)


def send_text_message(
    *,
    access_token: str,
    phone_number_id: str,
    api_version: str,
    to_digits: str,
    body: str,
    preview_url: bool = True,
) -> SendResult:
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_digits,
        "type": "text",
        "text": {"preview_url": preview_url, "body": body[:4096]},
    }
    return _post_json(_graph_url(api_version, phone_number_id), access_token, payload)


def send_image_message(
    *,
    access_token: str,
    phone_number_id: str,
    api_version: str,
    to_digits: str,
    image_https_url: str,
    caption: str = "",
) -> SendResult:
    link = (image_https_url or "").strip()
    if not re.match(r"^https://", link, re.I):
        return SendResult(False, 0, "Image must be a public https:// URL (WhatsApp fetches it from your link).", None)
    img_block: dict[str, Any] = {"link": link}
    cap = (caption or "").strip()
    if cap:
        img_block["caption"] = cap[:1024]
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_digits,
        "type": "image",
        "image": img_block,
    }
    return _post_json(_graph_url(api_version, phone_number_id), access_token, payload)
