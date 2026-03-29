# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Monkey-patches for F2 library to handle transient API failures.

Must be imported BEFORE any f2.apps.douyin.model or f2.apps.douyin.crawler imports.

Fixes:
1. BaseRequestModel.msToken fails at import time when msToken API is down
   (F2's model.py has a try/except that retries the same failing call)
2. Suppresses noisy F2 error logs during initialization
"""

import logging

logger = logging.getLogger("douyin.f2_patch")


def apply_patches():
    """Apply all F2 monkey-patches. Call before importing f2.apps.douyin.model."""

    # Import F2 utils -- this triggers f2.log.logger setup
    from f2.apps.douyin import utils as dy_utils

    # Suppress the F2 logger during model import (prevents QA doc spam)
    f2_logger = logging.getLogger("f2")
    saved_level = f2_logger.level
    f2_logger.setLevel(logging.CRITICAL)

    # Patch TokenManager.gen_real_msToken to silently fall back on failure.
    # We replace it entirely to avoid the original raising APIResponseError
    # (whose __init__ logs an ERROR before we can catch it).
    try:
        @classmethod
        def _safe_gen_real_msToken(cls) -> str:
            """Generate msToken, falling back to random token on any failure."""
            try:
                import httpx

                token_conf = dy_utils.ClientConfManager.msToken()
                payload = {
                    "magic": token_conf.get("magic", 538969122),
                    "version": token_conf.get("version", 1),
                    "dataType": token_conf.get("dataType", 8),
                    "strData": token_conf.get("strData", ""),
                }
                headers = {
                    "Content-Type": "application/json; charset=utf-8",
                    "User-Agent": dy_utils.ClientConfManager.user_agent(),
                }
                proxies = dy_utils.ClientConfManager.proxies()

                with httpx.Client(
                    headers=headers,
                    proxies=proxies,
                    timeout=5,
                ) as client:
                    response = client.post(
                        token_conf.get("url", "https://mssdk.bytedance.com/web/report"),
                        json=payload,
                    )
                    response.raise_for_status()
                    msToken = str(response.json().get("data", ""))
                    if len(msToken) not in (120, 128):
                        raise ValueError(f"Invalid msToken length: {len(msToken)}")
                    return msToken
            except Exception:
                # Silently fall back to fake token
                return cls.gen_false_msToken()

        dy_utils.TokenManager.gen_real_msToken = _safe_gen_real_msToken
    except Exception as e:
        logger.warning(f"Failed to patch TokenManager: {e}")

    # Restore F2 log level after patching (model.py will import cleanly now)
    f2_logger.setLevel(logging.WARNING)


# Auto-apply on import
apply_patches()
