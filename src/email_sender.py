"""
Compose and send the weekly digest email via Resend.
"""
import os
from datetime import datetime


def _build_html(user: dict, summaries: list[dict], meta: dict = None) -> str:
    date_str = datetime.now().strftime("%B %d, %Y")
    lang = user.get("language", "en")

    title = "Votre digest YouTube de la semaine" if lang == "fr" else "Your weekly YouTube digest"
    no_reply = "Ne répondez pas à cet email." if lang == "fr" else "Do not reply to this email."
    highlight_label = "✦ À la une" if lang == "fr" else "✦ Highlight"
    also_label = "Voir aussi" if lang == "fr" else "Also this week"

    if meta:
        video_by_id = {v["video_id"]: v for v in summaries}
        meta_html = f"<p style='color:#444;font-size:15px;line-height:1.6;background:#fafafa;padding:16px;border-radius:8px;margin-bottom:8px'>{meta['meta']}</p>"

        sections = ""
        for cat in meta.get("categories", []):
            highlight = video_by_id.get(cat.get("highlight_id", ""))
            others = [
                video_by_id[vid]
                for vid in cat.get("video_ids", [])
                if vid != cat.get("highlight_id") and vid in video_by_id
            ]
            count = len(cat.get("video_ids", []))
            count_label = (
                f'{count} vidéo{"s" if count > 1 else ""}'
                if lang == "fr"
                else f'{count} video{"s" if count > 1 else ""}'
            )

            sections += f"""
<h2 style='color:#1a1a1a;margin-top:32px;font-size:18px;border-bottom:1px solid #eee;padding-bottom:6px'>
  {cat['name']} <span style='font-size:13px;font-weight:normal;color:#999'>({count_label})</span>
</h2>
"""
            if highlight:
                summary_html = highlight["summary"].replace("\n", "<br>")
                sections += f"""
<div style='margin:12px 0 16px;padding:16px;background:#f0f4ff;border-radius:8px;border-left:3px solid #4a6fa5'>
  <div style='font-size:11px;font-weight:bold;color:#4a6fa5;margin-bottom:10px;text-transform:uppercase;letter-spacing:0.5px'>{highlight_label}</div>
  {summary_html}
</div>
"""
            if others:
                items = "".join(
                    f"<li style='margin-bottom:5px'><a href='{v['url']}' style='color:#333;text-decoration:none'>{v['title']}</a>"
                    f" <span style='color:#aaa;font-size:12px'>— {v['channel']}</span></li>"
                    for v in others
                )
                sections += f"""
<div style='margin-bottom:20px'>
  <p style='font-size:12px;color:#888;margin:0 0 6px;text-transform:uppercase;letter-spacing:0.4px'>{also_label}</p>
  <ul style='margin:0;padding-left:18px;font-size:14px;line-height:1.8'>{items}</ul>
</div>
"""
    else:
        # Fallback: simple channel grouping
        channel_groups: dict[str, list] = {}
        for s in summaries:
            channel_groups.setdefault(s["channel"], []).append(s)
        meta_html = (
            f"<p style='color:#555'>Voici les nouvelles vidéos de cette semaine.</p>"
            if lang == "fr"
            else f"<p style='color:#555'>Here are the new videos from this week.</p>"
        )
        sections = ""
        for channel, videos in channel_groups.items():
            sections += f"<h2 style='color:#1a1a1a;margin-top:32px'>{channel}</h2>\n"
            for v in videos:
                summary_html = v["summary"].replace("\n", "<br>")
                sections += f"""
<div style='margin-bottom:24px;padding:16px;background:#f9f9f9;border-radius:8px'>
  {summary_html}
</div>
"""

    return f"""
<!DOCTYPE html>
<html>
<body style='font-family:Georgia,serif;max-width:640px;margin:0 auto;padding:24px;color:#1a1a1a'>
  <h1 style='font-size:22px;border-bottom:2px solid #1a1a1a;padding-bottom:8px'>
    📺 {title} — {date_str}
  </h1>
  {meta_html}
  {sections}
  <hr style='margin-top:40px;border:none;border-top:1px solid #ddd'>
  <p style='font-size:12px;color:#999'>{no_reply}</p>
</body>
</html>
"""


def send_digest(user: dict, summaries: list[dict], api_key: str = None) -> bool:
    """Send the weekly digest to one user via Resend."""
    import requests
    from summarizer import generate_meta

    resend_key = api_key or os.environ.get("RESEND_API_KEY", "")
    if not resend_key:
        raise RuntimeError("RESEND_API_KEY not set")

    lang = user.get("language", "en")
    subject = (
        f"📺 Votre digest YouTube — {datetime.now().strftime('%d %B %Y')}"
        if lang == "fr"
        else f"📺 Your weekly YouTube digest — {datetime.now().strftime('%B %d, %Y')}"
    )

    print("  Generating digest structure...")
    try:
        meta = generate_meta(summaries, language=lang)
    except Exception as e:
        print(f"  Warning: meta generation failed ({e}), using fallback layout")
        meta = None

    html = _build_html(user, summaries, meta=meta)

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
        json={
            "from": "Subbrief <onboarding@resend.dev>",
            "to": [user["email"]],
            "subject": subject,
            "html": html,
        },
        timeout=15,
    )

    if resp.ok:
        print(f"  ✓ Email sent to {user['email']}")
        return True
    else:
        print(f"  ✗ Email failed for {user['email']}: {resp.text}")
        return False
