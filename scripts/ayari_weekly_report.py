import os
import json
import time
import requests
from datetime import datetime, timedelta, timezone
import anthropic

IG_ACCESS_TOKEN = os.environ["IG_ACCESS_TOKEN"]
IG_USER_ID = os.environ["IG_USER_ID_AYARI"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID_AYARI_REPORTS"]


def _parse_ts(ts: str) -> datetime:
    ts = ts.replace("Z", "+00:00")
    if ts[-3] != ":" and (ts[-5] == "+" or ts[-5] == "-"):
        ts = ts[:-2] + ":" + ts[-2:]
    return datetime.fromisoformat(ts)


def get_recent_posts(days: int = 7) -> list[dict]:
    url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media"
    params = {
        "fields": "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count",
        "access_token": IG_ACCESS_TOKEN,
        "limit": 30,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    posts = resp.json().get("data", [])
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [p for p in posts if _parse_ts(p["timestamp"]) >= cutoff]


def get_post_insights(media_id: str, media_product_type: str = "") -> dict:
    url = f"https://graph.facebook.com/v21.0/{media_id}/insights"
    is_reel = media_product_type.upper() == "REELS"

    metric_sets = [
        "reach,impressions,saved,shares,total_interactions,profile_visits,follows,plays" if is_reel else
        "reach,impressions,saved,shares,total_interactions,profile_visits,follows",
        "reach,saved,shares,total_interactions,profile_visits,follows",
        "reach,saved,shares,total_interactions",
    ]
    for metrics in metric_sets:
        params = {"metric": metrics, "period": "lifetime", "access_token": IG_ACCESS_TOKEN}
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            result = {}
            for item in resp.json().get("data", []):
                value = item.get("values", [{}])[0].get("value", 0) if item.get("values") else item.get("value", 0)
                result[item["name"]] = value
            return result
    print(f"  Insights error {media_id}")
    return {}


def build_report_with_claude(posts_data: list[dict]) -> str:
    client = anthropic.Anthropic()
    posts_json = json.dumps(posts_data, indent=2, ensure_ascii=False)
    today = datetime.now().strftime("%d. %B %Y")

    prompt = f"""Du bist der Instagram-Analyst für @ayari — Jasmins persönliche Brand mit 144K Followern.

@ayari ist KEINE Supplement-Seite. Es geht um:
- Persönliche Transformation und Identität
- Nervensystem, Energie, innere Freiheit
- "Funktionieren vs. wirklich Leben"
- Founder-Story und Jasmins authentische Perspektive

Heute ist {today}. Hier sind die Posts der letzten 7 Tage:

{posts_json}

Erstelle einen scharfen Wochenbericht. Struktur:

*@AYARI WOCHENBERICHT — {today}*

*ÜBERBLICK*
- Posts: X
- Gesamtreichweite: X
- Bester Post: [Caption-Anfang] — [warum er funktioniert hat]
- Schwächster Post: [Caption-Anfang] — [warum nicht]

*KEY METRIKEN*
- Ø Save Rate: X% (Benchmark: >1% = stark)
- Ø Share Rate: X% (Benchmark: >0.5% = stark)
- Ø Engagement Rate: X%
- Neue Follower diese Woche: X

*WAS FUNKTIONIERT HAT*
[2-3 Punkte: welche Themen, Hooks oder Formate haben überperformt]

*WAS NICHT FUNKTIONIERT HAT*
[1-2 Punkte: was unterperformt hat und warum]

*3 CONTENT-IDEEN NÄCHSTE WOCHE*
1. [Konkreter Hook + Thema basierend auf den Daten]
2. [Konkreter Hook + Thema]
3. [Konkreter Hook + Thema]

*HOOK FÜR SOFORT*
[Ein fertiger Hook für den stärksten Content-Ansatz nächste Woche]

Regeln: brutal ehrlich, keine Floskeln, nur Daten und Muster. Niemals Supplement- oder Produktthemen erwähnen — das ist die persönliche Brand. Format für Telegram mit *bold* für Überschriften."""

    models = ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"]
    for attempt in range(5):
        model = models[min(attempt // 2, len(models) - 1)]
        try:
            print(f"  Claude ({model}, Versuch {attempt + 1})...")
            msg = client.messages.create(
                model=model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < 4:
                wait = 15 * (attempt + 1)
                print(f"  Überlastet, warte {wait}s...")
                time.sleep(wait)
            else:
                raise


def send_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = [text[i: i + 4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        resp = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "Markdown"},
            timeout=30,
        )
        if resp.status_code == 400:
            resp = requests.post(
                url,
                json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk},
                timeout=30,
            )
        resp.raise_for_status()
        time.sleep(0.5)


def main() -> None:
    print("Fetching posts von @ayari...")
    posts = get_recent_posts(days=7)

    if not posts:
        send_telegram("*@ayari Wochenbericht*\n\nKeine Posts in den letzten 7 Tagen.")
        return

    print(f"  {len(posts)} Posts gefunden. Insights werden geladen...")
    enriched = []
    for post in posts:
        mpt = (post.get("media_product_type") or post.get("media_type") or "")
        insights = get_post_insights(post["id"], mpt)
        time.sleep(0.3)

        reach = insights.get("reach", 0)
        likes = post.get("like_count", 0)
        comments = post.get("comments_count", 0)
        saves = insights.get("saved", 0)
        shares = insights.get("shares", 0)
        interactions = insights.get("total_interactions", likes + comments)
        follows = insights.get("follows", 0)

        enriched.append({
            "date": post["timestamp"][:10],
            "format": mpt.upper(),
            "caption_preview": (post.get("caption") or "")[:150],
            "permalink": post.get("permalink", ""),
            "reach": reach,
            "impressions": insights.get("impressions", 0),
            "likes": likes,
            "comments": comments,
            "saves": saves,
            "shares": shares,
            "follows": follows,
            "save_rate_pct": round(saves / reach * 100, 2) if reach > 0 else 0,
            "share_rate_pct": round(shares / reach * 100, 2) if reach > 0 else 0,
            "engagement_rate_pct": round(interactions / reach * 100, 2) if reach > 0 else 0,
            "plays": insights.get("plays"),
        })

    print("  Claude analysiert...")
    report = build_report_with_claude(enriched)

    label = datetime.now().strftime("%d. %B %Y")
    send_telegram(f"*@ayari Wochenbericht — {label}*\n\n{report}")
    print("  Fertig.")


if __name__ == "__main__":
    main()
