import os
import json
import time
import requests
from datetime import datetime, timedelta, timezone
import anthropic

IG_ACCESS_TOKEN = os.environ["IG_ACCESS_TOKEN"]
IG_USER_ID = os.environ["IG_USER_ID"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID_LONGEVITY_REPORTS"]

WEEKS = 6


def _parse_ts(ts: str) -> datetime:
    ts = ts.replace("Z", "+00:00")
    if ts[-3] != ":" and (ts[-5] == "+" or ts[-5] == "-"):
        ts = ts[:-2] + ":" + ts[-2:]
    return datetime.fromisoformat(ts)


def get_posts(weeks: int) -> list[dict]:
    url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media"
    params = {
        "fields": "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count",
        "access_token": IG_ACCESS_TOKEN,
        "limit": 50,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    posts = resp.json().get("data", [])
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    return [p for p in posts if _parse_ts(p["timestamp"]) >= cutoff]


def get_insights(media_id: str, media_product_type: str = "") -> dict:
    url = f"https://graph.facebook.com/v21.0/{media_id}/insights"
    is_reel = media_product_type.upper() == "REELS"

    # Try progressively simpler metric sets until one succeeds
    if is_reel:
        metric_sets = [
            "reach,impressions,saved,shares,total_interactions,profile_visits,follows,plays,ig_reels_avg_watch_time,ig_reels_video_view_total_time",
            "reach,impressions,saved,shares,total_interactions,profile_visits,follows,plays",
            "reach,impressions,saved,shares,total_interactions,profile_visits,follows",
            "reach,saved,shares,total_interactions",
        ]
    else:
        metric_sets = [
            "reach,impressions,saved,shares,total_interactions,profile_visits,follows",
            "reach,saved,shares,total_interactions,profile_visits,follows",
            "reach,saved,shares,total_interactions",
        ]

    last_resp = None
    for metrics in metric_sets:
        params = {"metric": metrics, "period": "lifetime", "access_token": IG_ACCESS_TOKEN}
        resp = requests.get(url, params=params, timeout=30)
        last_resp = resp
        if resp.status_code == 200:
            result = {}
            for item in resp.json().get("data", []):
                value = item.get("values", [{}])[0].get("value", 0) if item.get("values") else item.get("value", 0)
                result[item["name"]] = value
            return result

    print(f"  Insights error {media_id}: {last_resp.status_code if last_resp else '?'}")
    return {}


def get_follower_growth(weeks: int) -> dict:
    url = f"https://graph.facebook.com/v21.0/{IG_USER_ID}/insights"
    since = int((datetime.now(timezone.utc) - timedelta(weeks=weeks)).timestamp())
    until = int(datetime.now(timezone.utc).timestamp())
    params = {
        "metric": "follower_count",
        "period": "day",
        "since": since,
        "until": until,
        "access_token": IG_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"  Follower data unavailable: {resp.status_code}")
        return {}
    data = resp.json().get("data", [])
    if not data:
        return {}
    values = data[0].get("values", [])
    if len(values) < 2:
        return {}
    start = values[0].get("value", 0)
    end = values[-1].get("value", 0)
    # Daily changes to find peak gain/loss days
    daily = [(v.get("end_time", "")[:10], v.get("value", 0)) for v in values]
    daily_changes = [(daily[i][0], daily[i][1] - daily[i - 1][1]) for i in range(1, len(daily))]
    best_day = max(daily_changes, key=lambda x: x[1]) if daily_changes else ("?", 0)
    worst_day = min(daily_changes, key=lambda x: x[1]) if daily_changes else ("?", 0)
    return {
        "start_followers": start,
        "end_followers": end,
        "net_change": end - start,
        "best_day": best_day[0],
        "best_day_gain": best_day[1],
        "worst_day": worst_day[0],
        "worst_day_loss": worst_day[1],
        "avg_daily_change": round((end - start) / len(daily_changes), 1) if daily_changes else 0,
    }


def build_enriched_posts(posts: list[dict]) -> list[dict]:
    enriched = []
    for i, post in enumerate(posts):
        mpt = (post.get("media_product_type") or post.get("media_type") or "").upper()
        print(f"  [{i+1}/{len(posts)}] {post['id']} — {mpt}")
        insights = get_insights(post["id"], mpt)
        time.sleep(0.3)

        caption = (post.get("caption") or "")[:150]
        reach = insights.get("reach", 0)
        impressions = insights.get("impressions", 0)
        saves = insights.get("saved", 0)
        shares = insights.get("shares", 0)
        likes = post.get("like_count", 0)
        comments = post.get("comments_count", 0)
        interactions = insights.get("total_interactions", likes + comments)
        profile_visits = insights.get("profile_visits", 0)
        follows = insights.get("follows", 0)
        plays = insights.get("plays", None)
        avg_watch_sec = insights.get("ig_reels_avg_watch_time", None)
        total_watch_sec = insights.get("ig_reels_video_view_total_time", None)

        save_rate = round(saves / reach * 100, 2) if reach > 0 else 0
        share_rate = round(shares / reach * 100, 2) if reach > 0 else 0
        engagement_rate = round(interactions / reach * 100, 2) if reach > 0 else 0
        follow_rate = round(follows / reach * 100, 3) if reach > 0 else 0
        profile_visit_rate = round(profile_visits / reach * 100, 2) if reach > 0 else 0
        repeat_view_rate = round((impressions - reach) / reach * 100, 1) if reach > 0 and impressions > reach else 0

        entry = {
            "id": post["id"],
            "date": post["timestamp"][:10],
            "format": mpt,
            "caption_preview": caption,
            "permalink": post.get("permalink", ""),
            "reach": reach,
            "impressions": impressions,
            "likes": likes,
            "comments": comments,
            "saves": saves,
            "shares": shares,
            "interactions": interactions,
            "profile_visits": profile_visits,
            "follows": follows,
            "save_rate_pct": save_rate,
            "share_rate_pct": share_rate,
            "engagement_rate_pct": engagement_rate,
            "follow_rate_pct": follow_rate,
            "profile_visit_rate_pct": profile_visit_rate,
            "repeat_view_rate_pct": repeat_view_rate,
        }
        if plays is not None:
            entry["plays"] = plays
            entry["play_rate_pct"] = round(plays / impressions * 100, 1) if impressions > 0 else 0
        if avg_watch_sec is not None:
            entry["avg_watch_sec"] = avg_watch_sec
        if total_watch_sec is not None:
            entry["total_watch_min"] = round(total_watch_sec / 60, 0)

        enriched.append(entry)
    return enriched


def analyze_with_claude(posts: list[dict], follower_growth: dict) -> str:
    client = anthropic.Anthropic()
    posts_json = json.dumps(posts, indent=2, ensure_ascii=False)
    today = datetime.now().strftime("%d. %B %Y")

    follower_context = ""
    if follower_growth:
        follower_context = f"""
*Account-Entwicklung ({WEEKS} Wochen):*
- Follower Start: {follower_growth.get('start_followers', '?')} → Ende: {follower_growth.get('end_followers', '?')}
- Netto-Veränderung: {follower_growth.get('net_change', '?'):+}
- Ø täglich: {follower_growth.get('avg_daily_change', '?'):+}
- Bester Tag: {follower_growth.get('best_day', '?')} (+{follower_growth.get('best_day_gain', '?')})
- Schlechtester Tag: {follower_growth.get('worst_day', '?')} ({follower_growth.get('worst_day_loss', '?'):+})
"""

    prompt = f"""Du bist AYARI's Instagram-Analyst. AYARI ist eine Premium-Longevity-Brand für deutschsprachige Frauen und Männer (@ayari.longevity, 7.3K Follower).

Heute ist {today}. Hier sind alle Posts der letzten {WEEKS} Wochen mit vollständigen Metriken:

{posts_json}

{follower_context}

METRIK-ERKLÄRUNGEN:
- reach = Unique Accounts die den Post gesehen haben
- impressions = Gesamtaufrufe inkl. Wiederholungen
- plays = Video-Aufrufe (Reels)
- avg_watch_sec = Durchschnittliche Watch Time in Sekunden
- save_rate_pct = Saves/Reach × 100 (Benchmark: >1% = stark)
- share_rate_pct = Shares/Reach × 100 (Benchmark: >0.5% = stark)
- engagement_rate_pct = Interactions/Reach × 100 (Benchmark: >3% = stark)
- follow_rate_pct = New Follows/Reach × 100 (Benchmark: >0.1% = gut)
- profile_visit_rate_pct = Profilbesuche/Reach × 100
- repeat_view_rate_pct = Wie viele haben den Post mehrfach gesehen

---

*POST-BY-POST ANALYSE — Letzte {WEEKS} Wochen*

Für jeden Post:
[Datum] [Format] — [Caption-Anfang, max 40 Zeichen]
→ Reach: X | Views/Plays: X | Saves: X (X%) | Shares: X (X%) | Follows: +X | ER: X%
→ LABEL: 🏆 WINNER / ✅ OKAY / ❌ KILL — [Ein Satz Begründung]

---

*FORMAT-PERFORMANCE*

Tabelle: Format | Ø Reach | Ø Saves% | Ø ER% | Ø Follows | Anzahl Posts
Welches Format performt am stärksten?

---

*FOLLOWER-WACHSTUM ANALYSE*

Netto-Follower der letzten {WEEKS} Wochen.
An welchen Tagen kamen die meisten Follower? Korreliert das mit Posts?
Hinweis: Per-Post-Unfollows sind von Instagram API nicht verfügbar — nur Netto-Wachstum ist messbar.

---

*MUSTER-ANALYSE*

Welche Hooks bringen Saves?
Welche Themen bringen Shares?
Welche Posts bringen Profilbesuche + Follows?
Welche Watch Times / Wiederholungsraten fallen auf?

---

*WACHSTUMS-KPIs GESAMT*

- Gesamtreichweite {WEEKS} Wochen: X
- Ø Reach pro Post: X
- Ø Save Rate: X%
- Ø Engagement Rate: X%
- Ø Follow Rate: X%
- Bester Post (Reach): [Name]
- Bester Post (Saves): [Name]
- Bester Post (Follows): [Name]

---

*3 SCHLÜSSEL-ERKENNTNISSE*

Konkret, datenbasiert, keine Floskeln.

---

*4-WOCHEN-TEST EMPFEHLUNG*

Welche 3 Content-Säulen sollen die nächsten 4 Wochen getestet werden?
Aus: Schlaf/Nervensystem · Energy/Fokus · Beauty/Gut Aging · Wissenschaft/Longevity · Produkt-Education
Begründung: direkt aus den Daten.

---

*TOP 3 HOOKS FÜR NÄCHSTE WOCHE*

Fertige, konkrete Hooks basierend auf den Mustern die funktioniert haben.
Format, Länge, Thema angeben.

Regeln: brutal ehrlich, nur Zahlen und Muster, kein Wellness-Geschwätz. Format für Telegram mit *bold* für Überschriften."""

    models = ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"]
    for attempt in range(5):
        model = models[min(attempt // 2, len(models) - 1)]
        try:
            print(f"  Claude ({model}, Versuch {attempt + 1})...")
            msg = client.messages.create(
                model=model,
                max_tokens=3500,
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
            # Markdown parse error — retry as plain text
            resp = requests.post(
                url,
                json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk},
                timeout=30,
            )
        resp.raise_for_status()
        time.sleep(0.5)


def save_data(posts: list[dict], follower_growth: dict) -> None:
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "instagram")
    os.makedirs(out_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = os.path.join(out_dir, f"post_analysis_{date_str}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"posts": posts, "follower_growth": follower_growth}, f, indent=2, ensure_ascii=False)
    print(f"  Daten gespeichert: {filename}")


def main() -> None:
    print(f"Fetching posts der letzten {WEEKS} Wochen von @ayari.longevity...")
    posts = get_posts(WEEKS)
    print(f"  {len(posts)} Posts gefunden.")

    if not posts:
        send_telegram("*AYARI Post-Analyse*\n\nKeine Posts in den letzten 6 Wochen gefunden.")
        return

    print("Insights werden geladen...")
    enriched = build_enriched_posts(posts)

    print("Follower-Wachstum wird geladen...")
    follower_growth = get_follower_growth(WEEKS)
    if follower_growth:
        print(f"  Follower-Netto: {follower_growth.get('net_change', '?'):+}")

    print("Daten werden gespeichert...")
    save_data(enriched, follower_growth)

    print("Claude analysiert...")
    analysis = analyze_with_claude(enriched, follower_growth)

    label = datetime.now().strftime("%d. %B %Y")
    full_message = f"*AYARI Post-Analyse — {label}*\n\n{analysis}"

    print("Sende an Telegram...")
    send_telegram(full_message)
    print("Fertig.")


if __name__ == "__main__":
    main()
