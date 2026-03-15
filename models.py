"""Pydantic models for Douyin MCP server."""

from typing import Optional
from pydantic import BaseModel, Field


class VideoCard(BaseModel):
    video_id: str = ""
    title: str = ""
    description: str = ""
    cover_url: str = ""
    play_count: str = ""
    like_count: str = ""
    comment_count: str = ""
    share_count: str = ""
    duration: str = ""
    author_id: str = ""
    author_name: str = ""
    author_avatar: str = ""
    url: str = ""


class FeedListResponse(BaseModel):
    feeds: list[VideoCard] = []
    count: int = 0


class VideoDetailResponse(BaseModel):
    video_id: str = ""
    title: str = ""
    description: str = ""
    cover_url: str = ""
    play_count: str = ""
    like_count: str = ""
    comment_count: str = ""
    share_count: str = ""
    collect_count: str = ""
    duration: str = ""
    publish_time: str = ""
    author_id: str = ""
    author_name: str = ""
    author_avatar: str = ""
    author_follower_count: str = ""
    tags: list[str] = []
    video_url: str = ""
    comments: list[dict] = []
    comment_loaded_count: int = 0


class LoginStatusResponse(BaseModel):
    is_logged_in: bool = False
    username: str = ""


class QrcodeResponse(BaseModel):
    timeout: str = "0s"
    is_logged_in: bool = False
    img: str = ""


class DeleteCookiesResponse(BaseModel):
    cookie_path: str = ""
    message: str = ""


class SearchFeedsArgs(BaseModel):
    keyword: str
    sort_by: str = Field(default="综合排序", description="综合排序|最新发布|最多点赞")
    publish_time: str = Field(default="不限", description="不限|一天内|一周内|半年内")


class FeedDetailArgs(BaseModel):
    video_id: str
    load_comments: bool = False
    comment_limit: int = 20


class UserProfileArgs(BaseModel):
    user_id: str
