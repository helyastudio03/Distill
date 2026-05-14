# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Distill is a weekly automated newsletter that fetches recent YouTube videos from a curated list of channels, transcribes and summarizes them with Claude Haiku, and sends a structured HTML digest via email. It runs on GitHub Actions every Sunday at 07:00 UTC.

## Running the pipeline

```bash
pip install -r requirements.txt

# All users defined in users.yml
python main.py

# Single user, custom lookback window
python main.py --user helyastudio03@gmail.com --days 14

# Custom config file
python main.py --config path/to/users.yml
```

Required environment variables: `ANTHROPIC_API_KEY`, `YOUTUBE_API_KEY`, `RESEND_API_KEY`, `SUPADATA_API_KEY`.

## Architecture

The pipeline is linear and runs per-user:

```
main.py
  └── youtube_fetcher.py   → YouTube Data API v3 → list of video dicts
  └── summarizer.py        → Supadata (transcripts) + Claude Haiku (summaries + meta)
  └── email_sender.py      → Resend API (HTML email)
```

**`youtube_fetcher.py`** resolves `@handles` to channel IDs, fetches the uploads playlist, and filters by `published_at >= now - days`. Returns up to 3 videos per channel.

**`summarizer.py`** has two responsibilities:
- `summarize_video()` — fetches transcript via Supadata (`api.supadata.ai/v1/youtube/transcript`), then prompts Claude Haiku for a 3-4 sentence digest entry with emoji title and watch link.
- `generate_meta()` — takes all summaries, prompts Claude Haiku for a JSON structure: a 2-3 sentence week overview + thematic categories, each with a `highlight_id` and list of `video_ids`. Returns parsed dict, falls back to `None` on failure.

**`email_sender.py`** builds HTML from the meta structure (highlight card per category + "Voir aussi" list for the rest). Falls back to simple channel grouping if `generate_meta` failed. Sends via Resend with `from: onboarding@resend.dev` (test sender — can only deliver to the verified address `helyastudio03@gmail.com`).

**`users.yml`** is the subscriber list. Each user has `name`, `email`, `language` (`fr`/`en`), and `channels` (list of `@handles`).

## Key constraints

- **Supadata** is used instead of the YouTube Transcript API because cloud IPs are blocked by YouTube.
- **Resend sandbox** (`onboarding@resend.dev`) only delivers to the verified owner address. To send to arbitrary recipients, a custom domain must be configured in Resend.
- The `generate_meta` JSON response from Claude is parsed directly; if it is wrapped in markdown fences, the code strips them before `json.loads`.
