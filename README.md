# douyin-mcp-py

MCP server for **抖音 (Douyin / TikTok China)** — lets Claude and other AI assistants search videos, download content, and transcribe audio via the Model Context Protocol.

**No browser required.** Uses [F2](https://github.com/Johnserf-Seed/f2) for pure-Python A-Bogus token generation — no CAPTCHA, no Chromium overhead.

Douyin data is locked behind apps and anti-bot systems. Scraping it manually is fragile and slow. This exposes Douyin as clean MCP tools — search, download, transcribe — directly in Claude Code, no browser required.

## Tools (12)

| Tool | What it does |
|---|---|
| `check_login_status` | Check cookie validity |
| `get_login_qrcode` | QR login (stub — F2 mode uses cookies) |
| `delete_cookies` | Reset session |
| `list_feeds` | Get homepage/recommend feed |
| `search_feeds` | Search videos by keyword, sort, date |
| `get_feed_detail` | Get video detail + comments |
| `user_profile` | Get user info and recent videos |
| `parse_douyin_video_info` | Parse share link → video metadata |
| `get_douyin_download_link` | Get watermark-free download URL |
| `extract_douyin_text` | Transcribe video audio (Dashscope ASR) |
| `recognize_audio_url` | Transcribe audio from URL |
| `recognize_audio_file` | Transcribe local audio file |

## Quick Start

```bash
git clone https://github.com/nardovibecoding/douyin-mcp-py
cd douyin-mcp-py
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py --port 18070
```

Then add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "douyin": { "url": "http://localhost:18070/mcp" }
  }
}
```

## Audio Transcription

Set `DASHSCOPE_API_KEY` in your environment for `extract_douyin_text` and `recognize_audio_*` tools (uses Alibaba Cloud ASR).

## Hot-reload

Reset the auth token without restarting:

```bash
# Via HTTP
curl -X POST http://localhost:18070/api/v1/reload

# Via signal
kill -HUP $(pgrep -f "server.py --port 18070")
```

## Requirements

- Python 3.11+
- F2 (`pip install f2`)

## License

AGPL-3.0 — see [LICENSE](LICENSE)
