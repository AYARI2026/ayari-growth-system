"""
AYARI Longevity — Weekly Content Planner
Called by n8n every Sunday to generate next week's content plan.
Outputs structured JSON that n8n uses to schedule and post.

Environment variables required:
- ANTHROPIC_API_KEY
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
import anthropic

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_CONTENT_BOT_TOKEN") or os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CONTENT_CHAT_ID") or os.environ["TELEGRAM_CHAT_ID"]

# Read brand data files (n8n runs from repo root)
def read_brand_files():
    files = {
        "products": "data/brand/ayari-products.md",
        "master_brand": "data/brand/ayari-master-brand.md",
        "channel_info": "data/instagram/channel-info.md",
    }
    content = {}
    for key, path in files.items():
        try:
            with open(path, "r", encoding="utf-8") as f:
                content[key] = f.read()
        except FileNotFoundError:
            content[key] = ""
    return content


WEEKLY_PLAN_PROMPT = """
Du bist der Content-Stratege für @ayari.longevity — AYARIs Supplement- und Educations-Kanal.

BRAND DATA:
{brand_data}

Erstelle einen vollständigen 7-Tage-Content-Plan für @ayari.longevity für die Woche starting {week_start}.

WOCHENFORMAT (PFLICHT):
- Montag: Facts Reel (Spickzettel) — Growth
- Dienstag: UGC/Social Proof Post
- Mittwoch: Expert/Education Reel + Newsletter-Thema
- Donnerstag: Karussell — Education + Saves
- Freitag: Facts Reel (Spickzettel) — Growth
- Samstag: Conversion Reel + Newsletter-Thema
- Sonntag: Brand/Lifestyle Single Post

Für jeden Post liefere EXAKT dieses JSON-Format:

{{
  "week_theme": "...",
  "week_theme_reason": "...",
  "posts": [
    {{
      "day": "Montag",
      "date": "YYYY-MM-DD",
      "format": "facts_reel|ugc|expert_reel|karussell|conversion_reel|single_post",
      "product_focus": "Produktname oder null",
      "content_type": "image|video|carousel",
      "hook_text": "Max 8 Wörter — für Video-Text-Overlay",
      "hook_caption": "Erste Zeile der Caption — macht neugierig",
      "caption": "Vollständige Caption (150-300 Zeichen, kurze Absätze, kein Fließtext)",
      "hashtags": ["#longevity", "#ayari", "..."],
      "manychat_keyword": "KEYWORD oder null",
      "script_lines": ["Zeile 1 für Jasmin falls Video", "..."] oder null,
      "thumbnail_prompt": "Higgsfield/AI Bildprompt falls image-post benötigt",
      "needs_jasmin_video": true/false,
      "newsletter_topic": "Newsletter-Betreff falls Mittwoch oder Samstag, sonst null",
      "posting_time": "HH:MM",
      "priority": "high|medium|low"
    }}
  ],
  "newsletter_subjects": {{
    "wednesday": "...",
    "saturday": "..."
  }},
  "strategic_recommendation": "Eine klare Empfehlung für diese Woche"
}}

REGELN:
- Alle Captions auf Deutsch
- EFSA-konforme Sprache: "beiträgt zu", "unterstützt", "kann dazu beitragen"
- Niemals: "heilt", "behandelt", "verhindert Krankheiten"
- ManyChat Keywords IMMER bei: Mittwoch, Donnerstag, Samstag
- Hashtags: 5-8, mix aus brand (#ayari, #ayarilongevity) + topic + niche
- Facts Reel hooks: provokant, neugierig, direkt
- Karussell: letzter Slide immer Produktbild + ManyChat Keyword

Antworte NUR mit dem JSON. Kein zusätzlicher Text.
"""


def generate_weekly_plan(week_start_date: str) -> dict:
    brand = read_brand_files()
    brand_summary = f"""
PRODUKTE: {brand['products'][:3000]}
BRAND: {brand['master_brand'][:1000]}
CHANNEL: {brand['channel_info'][:500]}
"""

    client = anthropic.Anthropic()
    prompt = WEEKLY_PLAN_PROMPT.format(
        brand_data=brand_summary,
        week_start=week_start_date
    )

    models = ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"]
    for attempt in range(5):
        model = models[min(attempt // 2, len(models) - 1)]
        try:
            print(f"Generating weekly plan ({model}, attempt {attempt + 1})...")
            message = client.messages.create(
                model=model,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            # Strip markdown code blocks if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < 4:
                wait = 15 * (attempt + 1)
                print(f"Overloaded, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
        except json.JSONDecodeError as e:
            print(f"JSON parse error attempt {attempt + 1}: {e}")
            if attempt == 4:
                raise


def format_telegram_plan(plan: dict) -> str:
    lines = [
        f"*📅 AYARI Longevity — Wochenplan*",
        f"*Thema:* {plan['week_theme']}",
        f"_{plan['week_theme_reason']}_",
        "",
    ]
    for post in plan["posts"]:
        needs_video = "🎬 Jasmin Video" if post.get("needs_jasmin_video") else "🤖 AI generiert"
        keyword = f" | 🔑 {post['manychat_keyword']}" if post.get("manychat_keyword") else ""
        lines.append(
            f"*{post['day']} {post.get('date','')}* — {post['format'].upper()}{keyword}"
        )
        lines.append(f"Hook: _{post['hook_text']}_")
        lines.append(f"→ {needs_video} | ⏰ {post.get('posting_time','08:00')}")
        if post.get("newsletter_topic"):
            lines.append(f"📧 Newsletter: {post['newsletter_topic']}")
        lines.append("")

    lines.append(f"*💡 Strategie:* {plan.get('strategic_recommendation','')}")
    lines.append("")
    lines.append("Soll ich mit diesem Plan fortfahren? ✅ /approve oder ❌ /reject")
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = [text[i: i + 4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        resp = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk},
            timeout=30
        )
        resp.raise_for_status()


def save_plan(plan: dict, week_start: str) -> str:
    os.makedirs("reports/weekly", exist_ok=True)
    path = f"reports/weekly/plan_{week_start}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    print(f"Plan saved to {path}")
    return path


def main():
    # Next Monday
    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7 or 7
    next_monday = today + timedelta(days=days_until_monday)
    week_start = next_monday.strftime("%Y-%m-%d")

    print(f"Generating content plan for week of {week_start}...")
    plan = generate_weekly_plan(week_start)
    path = save_plan(plan, week_start)

    message = format_telegram_plan(plan)
    send_telegram(message)
    send_telegram(f"📁 Plan gespeichert: `{path}`\n\nAntworte mit `/approve` um zu starten oder `/reject` um neu zu generieren.")
    print("Weekly plan sent to Telegram.")


if __name__ == "__main__":
    main()
