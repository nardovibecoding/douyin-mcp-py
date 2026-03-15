"""HTTP-based Douyin share link parser — no browser needed.

Ported from the existing douyin-mcp-server.
"""

import os
import re
import json
import logging
import requests
from typing import Optional

logger = logging.getLogger("douyin.video_parse")

# Mobile user-agent for share link resolution
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) '
                  'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                  'EdgiOS/121.0.2277.107 Version/17.0 Mobile/15E148 Safari/604.1'
}


def parse_share_url(share_text: str) -> dict:
    """Parse a Douyin share link/text to extract video info.

    Returns dict with keys: video_id, title, url (download link).
    """
    # Extract URL from share text
    urls = re.findall(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        share_text,
    )
    if not urls:
        raise ValueError("未找到有效的分享链接")

    share_url = urls[0]
    share_response = requests.get(share_url, headers=HEADERS)
    video_id = share_response.url.split("?")[0].strip("/").split("/")[-1]
    share_url = f'https://www.iesdouyin.com/share/video/{video_id}'

    # Fetch the video page
    response = requests.get(share_url, headers=HEADERS)
    response.raise_for_status()

    pattern = re.compile(
        pattern=r"window\._ROUTER_DATA\s*=\s*(.*?)</script>",
        flags=re.DOTALL,
    )
    find_res = pattern.search(response.text)

    if not find_res or not find_res.group(1):
        raise ValueError("从HTML中解析视频信息失败")

    json_data = json.loads(find_res.group(1).strip())
    VIDEO_ID_PAGE_KEY = "video_(id)/page"
    NOTE_ID_PAGE_KEY = "note_(id)/page"

    if VIDEO_ID_PAGE_KEY in json_data["loaderData"]:
        original_video_info = json_data["loaderData"][VIDEO_ID_PAGE_KEY]["videoInfoRes"]
    elif NOTE_ID_PAGE_KEY in json_data["loaderData"]:
        original_video_info = json_data["loaderData"][NOTE_ID_PAGE_KEY]["videoInfoRes"]
    else:
        raise Exception("无法从JSON中解析视频或图集信息")

    data = original_video_info["item_list"][0]

    video_url = data["video"]["play_addr"]["url_list"][0].replace("playwm", "play")
    desc = data.get("desc", "").strip() or f"douyin_{video_id}"
    desc = re.sub(r'[\\/:*?"<>|]', '_', desc)

    return {
        "video_id": video_id,
        "title": desc,
        "url": video_url,
    }


def get_download_link(share_link: str) -> dict:
    """Get watermark-free download link from a Douyin share link."""
    try:
        video_info = parse_share_url(share_link)
        return {
            "status": "success",
            "video_id": video_info["video_id"],
            "title": video_info["title"],
            "download_url": video_info["url"],
            "description": f"视频标题: {video_info['title']}",
            "usage_tip": "可以直接使用此链接下载无水印视频",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"获取下载链接失败: {str(e)}",
        }


def parse_video_info(share_link: str) -> dict:
    """Parse a Douyin share link and return basic video info."""
    try:
        video_info = parse_share_url(share_link)
        return {
            "status": "success",
            "video_id": video_info["video_id"],
            "title": video_info["title"],
            "download_url": video_info["url"],
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def extract_text_from_share_link(share_link: str, model: Optional[str] = None) -> dict:
    """Extract text from Douyin video via speech recognition.

    Requires API_KEY env var for Alibaba Cloud Dashscope.
    """
    api_key = os.getenv('API_KEY')
    if not api_key:
        return {
            "status": "error",
            "error": "未设置环境变量 API_KEY，请在配置中添加阿里云百炼API密钥",
        }

    try:
        import dashscope
        from urllib import request as url_request
        from http import HTTPStatus

        dashscope.api_key = api_key
        video_info = parse_share_url(share_link)
        model_name = model or "paraformer-v2"

        task_response = dashscope.audio.asr.Transcription.async_call(
            model=model_name,
            file_urls=[video_info["url"]],
            language_hints=['zh', 'en'],
        )
        transcription_response = dashscope.audio.asr.Transcription.wait(
            task=task_response.output.task_id,
        )

        if transcription_response.status_code == HTTPStatus.OK:
            for transcription in transcription_response.output['results']:
                result_url = transcription['transcription_url']
                result = json.loads(url_request.urlopen(result_url).read().decode('utf8'))
                if 'transcripts' in result and len(result['transcripts']) > 0:
                    return {
                        "status": "success",
                        "text": result['transcripts'][0]['text'],
                        "title": video_info["title"],
                    }
                else:
                    return {"status": "success", "text": "未识别到文本内容", "title": video_info["title"]}
        else:
            return {"status": "error", "error": f"转录失败: {transcription_response.output.message}"}
    except ImportError:
        return {"status": "error", "error": "dashscope package not installed. Run: pip install dashscope"}
    except Exception as e:
        return {"status": "error", "error": f"提取文字失败: {str(e)}"}


def recognize_audio_from_url(url: str, model: Optional[str] = None) -> dict:
    """Recognize speech from an audio URL (placeholder, uses Dashscope)."""
    api_key = os.getenv('API_KEY')
    if not api_key:
        return {"status": "error", "error": "未设置环境变量 API_KEY"}

    try:
        import dashscope
        from urllib import request as url_request
        from http import HTTPStatus

        dashscope.api_key = api_key
        model_name = model or "paraformer-v2"

        task_response = dashscope.audio.asr.Transcription.async_call(
            model=model_name,
            file_urls=[url],
            language_hints=['zh', 'en'],
        )
        transcription_response = dashscope.audio.asr.Transcription.wait(
            task=task_response.output.task_id,
        )

        if transcription_response.status_code == HTTPStatus.OK:
            for transcription in transcription_response.output['results']:
                result_url = transcription['transcription_url']
                result = json.loads(url_request.urlopen(result_url).read().decode('utf8'))
                if 'transcripts' in result and len(result['transcripts']) > 0:
                    return {"status": "success", "text": result['transcripts'][0]['text']}
                else:
                    return {"status": "success", "text": "未识别到文本内容"}
        else:
            return {"status": "error", "error": f"转录失败: {transcription_response.output.message}"}
    except ImportError:
        return {"status": "error", "error": "dashscope package not installed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def recognize_audio_from_file(file_path: str, model: Optional[str] = None) -> dict:
    """Recognize speech from a local audio file (placeholder)."""
    if not os.path.exists(file_path):
        return {"status": "error", "error": f"文件不存在: {file_path}"}

    api_key = os.getenv('API_KEY')
    if not api_key:
        return {"status": "error", "error": "未设置环境变量 API_KEY"}

    # Dashscope only supports URL-based recognition
    # For local files, you would need to upload first
    return {
        "status": "error",
        "error": "本地文件识别暂不支持，请使用 recognize_audio_url 传入音频URL",
    }
