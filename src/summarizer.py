"""
Extract YouTube transcript and summarize with Claude.
"""
import json
import os
from typing import Optional

import anthropic


def _get_transcript(video_id: str) -> Optional[str]:
    import requests
    api_key = os.environ.get("SUPADATA_API_KEY", "")
    if not api_key:
        raise RuntimeError("SUPADATA_API_KEY not set")
    try:
        resp = requests.get(
            "https://api.supadata.ai/v1/youtube/transcript",
            params={"videoId": video_id, "text": "true"},
            headers={"x-api-key": api_key.strip()},
            timeout=15,
        )
        if not resp.ok:
            print(f"    No transcript for {video_id}: {resp.status_code} {resp.text[:100]}")
            return None
        return resp.json().get("content", "")
    except Exception as e:
        print(f"    No transcript for {video_id}: {e}")
        return None


def summarize_video(video: dict, language: str = "en", api_key: str = None) -> Optional[dict]:
    """Summarize a video. Returns enriched video dict or None if no transcript."""
    transcript = _get_transcript(video["video_id"])
    if not transcript:
        return None

    lang_instruction = "Respond in French." if language == "fr" else "Respond in English."

    client = anthropic.Anthropic(api_key=(api_key or os.environ.get("ANTHROPIC_API_KEY", "")).strip())
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": f"""YouTube video: "{video['title']}" by {video['channel']}

Transcript (excerpt):
{transcript[:6000]}

Write a digest entry for this video. {lang_instruction}

Format:
**[Emoji] Title in one line**
One paragraph of 3-4 sentences: what the video is about, the key insight or takeaway, why it matters.
→ [Watch](URL)

Use this URL: {video['url']}
Be concrete and direct. No fluff."""
        }]
    )

    return {
        **video,
        "summary": message.content[0].text.strip(),
        "has_transcript": True,
    }


def summarize_videos(videos: list[dict], language: str = "en", api_key: str = None) -> list[dict]:
    """Summarize all videos that have transcripts available."""
    results = []
    for video in videos:
        print(f"  Summarizing: {video['title'][:60]}")
        result = summarize_video(video, language=language, api_key=api_key)
        if result:
            results.append(result)
    return results


def generate_meta(summaries: list[dict], language: str = "en", api_key: str = None) -> dict:
    """Generate a meta-summary and thematic categorization of the week's videos."""
    lang_instruction = "Réponds en français." if language == "fr" else "Respond in English."

    videos_text = "\n\n".join(
        f"ID: {v['video_id']}\nChannel: {v['channel']}\nTitle: {v['title']}\nSummary: {v['summary']}"
        for v in summaries
    )

    client = anthropic.Anthropic(api_key=(api_key or os.environ.get("ANTHROPIC_API_KEY", "")).strip())
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""You have {len(summaries)} YouTube video summaries from a weekly digest.

{videos_text}

{lang_instruction}

Tasks:
1. Write a 2-3 sentence meta-summary of the week's themes (what dominated, any notable trends).
2. Group videos into thematic categories based on content (e.g. Business & Sales, Health & Performance, Technology). Only create separate categories if they are clearly distinct — otherwise use a single category.
3. For each category, pick the single most insightful video as "highlight".

Return ONLY valid JSON, no markdown:
{{
  "meta": "...",
  "categories": [
    {{
      "name": "...",
      "highlight_id": "video_id",
      "video_ids": ["id1", "id2"]
    }}
  ]
}}"""
        }]
    )

    text = message.content[0].text.strip()
    if "```" in text:
        # Strip markdown code fences
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)
