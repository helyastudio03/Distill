"""
Fetch new videos published in the last 7 days for a list of YouTube channels.
Uses YouTube Data API v3.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _api_key() -> str:
    key = os.environ.get("YOUTUBE_API_KEY", "")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY environment variable not set")
    return key


def _resolve_channel_id(handle_or_url: str) -> Optional[str]:
    """Resolve a @handle or channel URL to a channel ID."""
    handle = handle_or_url.strip().lstrip("@")
    if handle_or_url.startswith("https://"):
        parts = handle_or_url.rstrip("/").split("/")
        handle = parts[-1].lstrip("@")

    resp = requests.get(
        f"{YOUTUBE_API_BASE}/channels",
        params={
            "key": _api_key(),
            "forHandle": handle,
            "part": "id,snippet",
        },
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        print(f"  Warning: channel not found for '{handle_or_url}'")
        return None
    return items[0]["id"]


def _get_uploads_playlist_id(channel_id: str) -> Optional[str]:
    resp = requests.get(
        f"{YOUTUBE_API_BASE}/channels",
        params={
            "key": _api_key(),
            "id": channel_id,
            "part": "contentDetails",
        },
        timeout=10,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def _get_recent_videos(playlist_id: str, since: datetime) -> list[dict]:
    """Get videos from uploads playlist published after `since`."""
    videos = []
    page_token = None

    while True:
        params = {
            "key": _api_key(),
            "playlistId": playlist_id,
            "part": "snippet",
            "maxResults": 50,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(
            f"{YOUTUBE_API_BASE}/playlistItems",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("items", []):
            snippet = item["snippet"]
            published = datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            )
            if published < since:
                return videos  # playlist is chronological desc, stop early
            videos.append({
                "video_id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "published_at": published.isoformat(),
                "url": f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}",
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return videos


def fetch_new_videos(channels: list[str], days: int = 7, max_per_channel: int = 3) -> list[dict]:
    """Return up to `max_per_channel` recent videos per channel published in the last `days` days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    all_videos = []

    for channel_handle in channels:
        print(f"  Fetching: {channel_handle}")
        channel_id = _resolve_channel_id(channel_handle)
        if not channel_id:
            continue
        playlist_id = _get_uploads_playlist_id(channel_id)
        if not playlist_id:
            continue
        videos = _get_recent_videos(playlist_id, since)[:max_per_channel]
        print(f"    → {len(videos)} new video(s)")
        all_videos.extend(videos)

    return all_videos
