"""
YouTube Digest — weekly email pipeline.

Usage:
  python main.py                         # run for all users in users.yml
  python main.py --user your@email.com  # run for one user only
  python main.py --days 14              # look back 14 days instead of 7
"""
import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from youtube_fetcher import fetch_new_videos
from summarizer import summarize_videos
from email_sender import send_digest


def load_users(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["users"]


def run_for_user(user: dict, days: int) -> None:
    print(f"\n{'='*50}")
    print(f"User: {user['name']} <{user['email']}>")
    print(f"Channels: {len(user['channels'])}")

    print("\n[1/3] Fetching new videos...")
    videos = fetch_new_videos(user["channels"], days=days)
    if not videos:
        print("  No new videos this week — skipping.")
        return
    print(f"  → {len(videos)} video(s) found")

    print("\n[2/3] Summarizing...")
    summaries = summarize_videos(videos, language=user.get("language", "en"))
    if not summaries:
        print("  No transcripts available — skipping.")
        return
    print(f"  → {len(summaries)} video(s) summarized")

    print("\n[3/3] Sending email...")
    send_digest(user, summaries)


def main():
    parser = argparse.ArgumentParser(description="Send weekly YouTube digest")
    parser.add_argument("--user", default=None, help="Send only to this email address")
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--config", default="users.yml", help="Path to users.yml")
    args = parser.parse_args()

    users = load_users(args.config)

    if args.user:
        users = [u for u in users if u["email"] == args.user]
        if not users:
            print(f"User '{args.user}' not found in {args.config}")
            sys.exit(1)

    for user in users:
        run_for_user(user, days=args.days)


if __name__ == "__main__":
    main()
