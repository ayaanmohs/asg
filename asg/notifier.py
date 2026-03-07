"""
Notification backends for ASG (Aldertech Storage Governor).

Supports Discord, NTFY, and Gotify — all optional. If no backends are
configured, notifications are silently skipped (log-only mode).
"""

import json
import urllib.request
from datetime import datetime

from . import config


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] notify: {message}")


def _send_discord(webhook_url: str, title: str, body: str, color: int = 0x3498DB) -> None:
    """Send a Discord embed notification."""
    payload = {
        "embeds": [{
            "title": title,
            "description": body,
            "color": color,
            "footer": {"text": "ASG (Aldertech Storage Governor)"},
            "timestamp": datetime.utcnow().isoformat(),
        }]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "ASG-Governor"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except Exception as exc:
        _log(f"Discord notification failed: {exc}")


def _send_ntfy(url: str, token: str, title: str, body: str) -> None:
    """Send an NTFY notification."""
    data = body.encode("utf-8")
    headers = {
        "Title": title,
        "User-Agent": "ASG-Governor",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except Exception as exc:
        _log(f"NTFY notification failed: {exc}")


def _send_gotify(url: str, token: str, title: str, body: str) -> None:
    """Send a Gotify notification."""
    endpoint = f"{url.rstrip('/')}/message?token={token}"
    payload = json.dumps({
        "title": title,
        "message": body,
        "priority": 5,
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "ASG-Governor"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except Exception as exc:
        _log(f"Gotify notification failed: {exc}")


def send(title: str, body: str, color: int = 0x3498DB) -> None:
    """
    Send a notification to all configured backends.

    Parameters
    ----------
    title : str
        Notification title / subject.
    body : str
        Notification body (Markdown for Discord, plain text for others).
    color : int
        Embed colour for Discord (hex integer).
    """
    try:
        cfg = config.get()
    except RuntimeError:
        return

    notif = cfg.get("notifications") or {}

    discord = notif.get("discord") or {}
    if discord.get("webhook_url"):
        _send_discord(discord["webhook_url"], title, body, color)

    ntfy = notif.get("ntfy") or {}
    if ntfy.get("url"):
        _send_ntfy(ntfy["url"], ntfy.get("token", ""), title, body)

    gotify = notif.get("gotify") or {}
    if gotify.get("url") and gotify.get("token"):
        _send_gotify(gotify["url"], gotify["token"], title, body)
