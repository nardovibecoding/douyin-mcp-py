# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Cookie management — bidirectional conversion between go-rod CDP format and Playwright format."""

import json
import os
from pathlib import Path

# Default cookie path — can be overridden via COOKIES_PATH env var
DEFAULT_COOKIE_PATH = os.path.join(os.path.dirname(__file__), "cookies.json")


def get_cookie_path() -> str:
    return os.environ.get("COOKIES_PATH", DEFAULT_COOKIE_PATH)


def _cdp_to_playwright(cookie: dict) -> dict:
    """Convert a go-rod/CDP cookie dict to Playwright cookie format."""
    pw = {
        "name": cookie["name"],
        "value": cookie["value"],
        "domain": cookie.get("domain", ""),
        "path": cookie.get("path", "/"),
    }
    if cookie.get("expires") and cookie["expires"] > 0:
        pw["expires"] = cookie["expires"]
    if cookie.get("httpOnly"):
        pw["httpOnly"] = True
    if cookie.get("secure"):
        pw["secure"] = True
    same_site = cookie.get("sameSite", "")
    if same_site and same_site != "None":
        pw["sameSite"] = same_site
    return pw


def _playwright_to_cdp(cookie: dict) -> dict:
    """Convert a Playwright cookie dict back to go-rod/CDP format for saving."""
    cdp = {
        "name": cookie["name"],
        "value": cookie["value"],
        "domain": cookie.get("domain", ""),
        "path": cookie.get("path", "/"),
        "expires": cookie.get("expires", -1),
        "size": len(cookie["name"]) + len(cookie["value"]),
        "httpOnly": cookie.get("httpOnly", False),
        "secure": cookie.get("secure", False),
        "session": cookie.get("expires", -1) <= 0,
        "priority": "Medium",
        "sameParty": False,
        "sourceScheme": "Secure",
        "sourcePort": 443,
    }
    return cdp


def load_cookies() -> list[dict]:
    """Load cookies from file, converting from CDP to Playwright format."""
    path = get_cookie_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            cdp_cookies = json.load(f)
        return [_cdp_to_playwright(c) for c in cdp_cookies]
    except (json.JSONDecodeError, KeyError):
        return []


def save_cookies(pw_cookies: list[dict]) -> None:
    """Save cookies to file in CDP format (compatible with go-rod)."""
    path = get_cookie_path()
    cdp_cookies = [_playwright_to_cdp(c) for c in pw_cookies]
    with open(path, "w") as f:
        json.dump(cdp_cookies, f, indent=2)


def delete_cookies() -> str:
    """Delete the cookies file. Returns the path that was deleted."""
    path = get_cookie_path()
    if os.path.exists(path):
        os.remove(path)
    return path
