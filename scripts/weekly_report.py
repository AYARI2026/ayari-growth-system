import os
import json
import requests
from datetime import datetime, timedelta, timezone
import anthropic

IG_ACCESS_TOKEN = os.environ["IG_ACCESS_TOKEN"]
IG_USER_ID = os.environ["IG_USER_ID"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
# ANTHROPIC_API_KEY is picked up automatically by the anthropic library


def get_ig_account_info() -> tuple[str, str]:
    """Returns (ig_user_id, page_access_token)"""
    url = "https://graph.facebook.com/v21.0/me/accounts"
    params = {"fields": "access_token,instagram_business_account", "access_token": IG_ACCESS_TOKEN}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    for page in resp.json().get("data", []):
        ig = page.get("instagram_business_account")
        if ig:
            return ig["id"], page.get("access_token", IG_ACCESS_TOKEN)
    return IG_USER_ID, IG_ACCESS_TOKEN


def get_recent_posts(days: int = 7) -> tuple[list[dict], str]:
    user_id, page_token = get_ig_account_info()
    url = f"https://graph.facebook.com/v21.0/{user_id}/media"
    params = {
        "fields": "id,caption,media_type,timestamp,permalink,like_count,comments_count",
        "access_token": page_token,
        "limit": 30,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    posts = resp.json().get("data", [])

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = [p for p in posts if datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00")) >= cutoff]
    return recent, page_token


def get_post_insights(media_id: str, media_type: str, page_token: str) -> dict:
    url = f"https://graph.facebook.com/v21.0/{media_id}/insights"

    if media_type in ("VIDEO", "REEL"):
        metrics = "impressions,reach,shares,saved,video_views,total_interactions"
    else:
        metrics = "impressions,reach,shares,saved,total_interactions"

    params = {"metric": metrics, "access_token": page_token}
    resp = requests.get(url, params=params, timeout=30)

    if resp.status_code != 200:
        print(f"Insights warning for {media_id}: {resp.status_code} — {resp.text[:200]}")
        return {}

    insights = {}
    for item in resp.json().get("data", []):
        value = item.get("values", [{}])[0].get("value", 0) if item.get("values") else item.get("value", 0)
        insights[item["name"]] = value
    return insights


def build_report_with_claude(posts_data: list[dict]) -> str:
    client = anthropic.Anthropic()

    posts_json = json.dumps(posts_data, indent=2, ensure_ascii=False)
    today = datetime.now().strftime("%d. %B %Y")

    prompt = f"""You are AYARI's Instagram growth analyst. AYARI is a premium longevity brand for ambitious German-speaking women and men. Tone: premium, sharp, credible, direct.

Today is {today}. Here is the Instagram performance data for the last 7 days:

{posts_json}

Write a sharp weekly report. Structure it exactly like this:

*WEEKLY SUMMARY*
- Posts published: X
- Total reach: X
- Total impressions: X
- Best post: [caption start] — [one sentence on why it worked]
- Weakest post: [caption start] — [one sentence on what went wrong]

*KEY METRICS*
- Avg save rate: X% (benchmark: >1% is strong)
- Avg share rate: X% (benchmark: >0.5% is strong)
- Avg engagement rate: X%

*WHAT WORKED THIS WEEK*
[2-3 bullet points: hook types, topics, or formats that performed above average]

*WHAT TO STOP OR FIX*
[1-2 bullet points: what underperformed and why]

*3 CONTENT IDEAS FOR NEXT WEEK*
1. [Specific hook + topic based on what worked]
2. [Specific hook + topic]
3. [Specific hook + topic]

*HOOK TO USE NOW*
[One ready-to-use hook for next week's strongest content idea]

Rules: no fluff, no vague advice, no motivation speech. Be brutally honest and specific. Format for Telegram using *bold* for section headers."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def send_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "Markdown"}
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()


def main() -> None:
    print("Fetching recent posts from @ayari.longevity...")
    posts, page_token = get_recent_posts(days=7)

    if not posts:
        send_telegram("*AYARI Weekly Report*\n\nNo posts published in the last 7 days.")
        print("No posts found. Sent notice to Telegram.")
        return

    print(f"Found {len(posts)} posts. Fetching insights...")
    enriched = []
    for post in posts:
        insights = get_post_insights(post["id"], post.get("media_type", "IMAGE"), page_token)
        enriched.append(
            {
                "caption_preview": (post.get("caption") or "")[:200],
                "media_type": post.get("media_type"),
                "timestamp": post.get("timestamp"),
                "permalink": post.get("permalink"),
                "insights": insights,
            }
        )

    print("Analyzing with Claude...")
    report_body = build_report_with_claude(enriched)

    week_label = datetime.now().strftime("%d. %B %Y")
    full_message = f"*AYARI Instagram Report — {week_label}*\n\n{report_body}"

    print("Sending to Telegram...")
    send_telegram(full_message)
    print("Done. Report delivered.")


if __name__ == "__main__":
    main()
