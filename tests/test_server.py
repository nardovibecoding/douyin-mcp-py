# Copyright (c) 2026 Nardo. AGPL-3.0 — see LICENSE
"""Tests for server.py: health endpoint and lifespan context manager."""
import sys
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Stub out f2 and mcp_tools before server.py is imported
sys.modules.setdefault("f2_patch", MagicMock())
sys.modules.setdefault("f2", MagicMock())
sys.modules.setdefault("f2.apps", MagicMock())
sys.modules.setdefault("f2.apps.douyin", MagicMock())
sys.modules.setdefault("f2.apps.douyin.utils", MagicMock())

_mock_mcp = MagicMock()
_mock_mcp.streamable_http_app.return_value = MagicMock()
_mock_mcp.session_manager = MagicMock()
sys.modules.setdefault("mcp_tools", MagicMock(mcp=_mock_mcp))

# Stub all api_routes handlers
import types
_api_routes = types.ModuleType("api_routes")
for _name in [
    "login_status_handler", "login_qrcode_handler", "delete_cookies_handler",
    "list_feeds_handler", "search_feeds_handler", "feed_detail_handler",
    "user_profile_handler", "parse_video_info_handler", "download_link_handler",
    "extract_text_handler", "recognize_audio_url_handler", "recognize_audio_file_handler",
]:
    setattr(_api_routes, _name, MagicMock())
sys.modules["api_routes"] = _api_routes


class TestHealthEndpoint(unittest.IsolatedAsyncioTestCase):
    async def test_health_returns_ok(self):
        from server import health
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route

        app = Starlette(routes=[Route("/health", health)])
        client = TestClient(app)
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["backend"], "f2")


class TestLifespan(unittest.IsolatedAsyncioTestCase):
    async def test_lifespan_starts_and_stops(self):
        """Lifespan should log start/stop and start MCP session manager."""
        from server import lifespan
        from starlette.applications import Starlette

        mock_app = MagicMock(spec=Starlette)

        # Mock _session_manager.run() as async context manager
        mock_run_ctx = MagicMock()
        mock_run_ctx.__aenter__ = AsyncMock(return_value=None)
        mock_run_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("server._session_manager") as mock_sm, \
             patch("server.get_f2_kwargs", return_value={}, create=True):
            mock_sm.run.return_value = mock_run_ctx

            async with lifespan(mock_app):
                pass  # yield point — server is "running" here

            mock_sm.run.assert_called_once()
            mock_run_ctx.__aenter__.assert_called_once()
            mock_run_ctx.__aexit__.assert_called_once()

    async def test_lifespan_f2_init_warning_does_not_crash(self):
        """If F2 client init raises, lifespan should still proceed."""
        from server import lifespan
        from starlette.applications import Starlette

        mock_app = MagicMock(spec=Starlette)
        mock_run_ctx = MagicMock()
        mock_run_ctx.__aenter__ = AsyncMock(return_value=None)
        mock_run_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("server._session_manager") as mock_sm, \
             patch("dy_actions.f2_client.get_f2_kwargs",
                   side_effect=Exception("init error"), create=True):
            mock_sm.run.return_value = mock_run_ctx

            # Should not raise even if F2 init fails
            try:
                async with lifespan(mock_app):
                    pass
            except Exception as e:
                # Only acceptable if it's not the F2 init error
                self.fail(f"lifespan raised unexpectedly: {e}")


if __name__ == "__main__":
    unittest.main()
