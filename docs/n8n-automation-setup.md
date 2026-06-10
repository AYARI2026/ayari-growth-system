# AYARI Automation System — Setup Guide
# n8n + Telegram + Instagram + TikTok + Facebook + YouTube

---

## OVERVIEW

```
[Sunday 8pm] n8n trigger
→ content_planner_longevity.py generates 7-day plan
→ Telegram: "Here's next week's plan — approve?"
→ You approve → plan is locked

[Daily, 30 min before target time] n8n trigger
→ Random wait: 0–60 min (for organic timing)
→ Reads today's post from plan
→ Generates content based on type:
     Jasmin Reel    → waits for video sent to Telegram bot
     Facts Reel     → Higgsfield generates image
     Karussell      → Higgsfield generates carousel slides
     UGC            → Higgsfield Marketing Studio UGC mode
     Single Post    → Higgsfield generates lifestyle image
→ ALL content types: Telegram preview sent to you
→ You tap ✅ → posts to Instagram
→ You tap ✏️ → edit caption, then post
→ You tap ⏭  → skip today
→ ManyChat handles all DM responses automatically
```

**Rule: Nothing posts without your ✅. No exceptions.**

---

## STEP 1 — Accounts & API Keys to Set Up

### 1.1 n8n (the brain)
- Go to: https://n8n.io
- Sign up for **n8n Cloud Starter** (~€20/month)
- Or self-host on any VPS (Hetzner €5/month works fine)

### 1.2 Telegram Bot (your approval interface)
Already have bot token + chat ID from weekly report.
Same credentials work for this system.

### 1.3 Instagram
Already configured: IG_ACCESS_TOKEN, IG_USER_ID in GitHub Secrets.
Same token works for posting.

### 1.4 TikTok for Business API
1. Go to: https://developers.tiktok.com
2. Create a developer account
3. Create an app → request "Content Posting API" access
4. Set scopes: `video.publish`
5. Get access token → save as TIKTOK_ACCESS_TOKEN
⚠️ TikTok API approval takes 1-2 weeks. Apply now.

### 1.5 Facebook Pages
Same access token as Instagram (Meta Graph API).
No extra setup needed — page token is fetched automatically.

### 1.6 YouTube Data API
1. Go to: https://console.cloud.google.com
2. Create project "AYARI Automation"
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials
5. Download client_secret.json → save to scripts/
6. YouTube posting requires separate implementation (complex OAuth)
⚠️ YouTube automation: set up in Phase 2 after Instagram/TikTok work

### 1.7 Google Drive (for video uploads)
1. Create folder: "AYARI Ready to Post"
2. Share folder with n8n (via Google Drive node)
3. When Jasmin's video is edited → drop it in this folder
4. n8n detects new file → triggers posting workflow

---

## STEP 2 — GitHub Actions Update

Add new secrets to GitHub repository:
```
TIKTOK_ACCESS_TOKEN=...
FACEBOOK_PAGE_ID=...    (optional, auto-detected)
```

Add new scheduled workflow:

```yaml
# .github/workflows/weekly-content-plan.yml
name: AYARI Weekly Content Plan
on:
  schedule:
    - cron: "0 18 * * 0"  # Sunday 6pm UTC (8pm CET)
  workflow_dispatch:
jobs:
  generate-plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r scripts/requirements.txt
      - run: python scripts/content_planner_longevity.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
```

---

## STEP 3 — n8n Workflows to Build

### Workflow A: Daily Post with Telegram Approval

**Trigger:** Schedule — runs 60 min before target posting time (from plan JSON)
**First node after trigger:** Wait node — `{{ Math.floor(Math.random() * 121) }}` minutes
This creates natural ±60 min variation so posting times never look automated to Meta.
Example: target time 11:00 → trigger fires at 10:00 → random wait 0–120 min → actual post lands anywhere between 10:00 and 12:00.

**Logic:**
1. Read today's plan from latest `reports/weekly/plan_*.json`
2. Find today's post (by date)
3. Branch by `content_type` + `needs_jasmin_video`:

```
needs_jasmin_video = true  →  Check Telegram bot inbox for today's video
                               If found: use it
                               If not found: send reminder → wait 2h → if still missing: skip + notify

content_type = "image"     →  Call Higgsfield API (gpt_image_2) with thumbnail_prompt
content_type = "carousel"  →  Call Higgsfield API (gpt_image_2) for each slide
content_type = "ugc"       →  Call Higgsfield Marketing Studio (ugc mode) → see UGC templates
```

4. Send Telegram preview for **every** content type:
   ```
   📸 @ayari.longevity — Mittwoch (Expert Reel)
   Hook: "Das einzige NMN das in Menschen getestet wurde"
   Caption: NAD+ kann man nicht direkt supplementieren...
   [Video / Image attached]
   Keyword: LONGEVITY
   ──────────────────────
   [✅ POSTEN]  [✏️ CAPTION]  [⏭ SKIP]
   ```
5. Wait for Telegram button response (timeout: 4h → auto-skip + notify)
6. On ✅ → call post_publisher.py → post to Instagram (+Facebook)
7. Confirm: "✅ Gepostet um 11:23 Uhr — Instagram ID: 123456"

**n8n Nodes needed:**
- Schedule Trigger
- Wait Node (random delay expression)
- Read Binary File (plan JSON)
- Code Node (JavaScript: find today's post, determine content type)
- Switch Node (branch by content_type)
- HTTP Request (Higgsfield API — image / UGC)
- Telegram Send Message (preview with inline buttons)
- Telegram Trigger (wait for button click)
- IF Node (which button was tapped)
- HTTP Request / Execute Command (post_publisher.py)
- Telegram Send Message (confirmation)

---

### Workflow B: Jasmin Video Upload via Telegram

**How it works:**
Jasmin films a reel → opens Telegram → sends the video directly to the AYARI bot with a date label.

**Message format Jasmin uses:**
```
[sends video file]
Caption: 2026-06-10
```
That's it. Just the date. n8n matches it to that day's post in the plan.

**n8n Logic:**
1. Telegram Trigger fires when bot receives a video message
2. Code node: extract date from caption → find matching post in plan JSON
3. Store video with metadata: `{ date, file_id, matched_post }`
4. Reply to Jasmin: "✅ Video für Mittwoch 10.6. gespeichert"
5. Video is ready for Workflow A to pick up at posting time

**Important:** Jasmin sends the video anytime before the posting time — the night before is ideal.
If no video arrives by 1h before scheduled time → Workflow A sends a reminder to Telegram.

---

### Workflow C: ManyChat Keyword Handler
This runs INSIDE ManyChat — not in n8n.
Set it up once in ManyChat UI:

| Keyword trigger | Response |
|---|---|
| CODE | Send AYARI Code info + link |
| LONGEVITY | Send NMN+ product link |
| SLEEP / STRESS | Send Magnesium product link |
| OMEGA | Send Omega-3 product link |
| GLOW | Send Kollagen product link |
| ENERGY | Send Kreatin product link |
| VITAMIN | Send Vitamin D3/K2 link |
| FOCUS | Send B-Komplex link |
| IMMUNITY | Send Vitamin C+ link |
| SPICKZETTEL | Send link to latest Spickzettel post |
| ROUTINE | Send morning routine guide |

After setup: zero ongoing effort. ManyChat handles everything 24/7.

---

## STEP 4 — Higgsfield API Integration

Higgsfield has a CLI but also REST API. For n8n HTTP Request nodes:

```
POST https://api.higgsfield.ai/v1/generate
Authorization: Bearer YOUR_HIGGSFIELD_TOKEN
{
  "model": "gpt_image_2",
  "prompt": "...",
  "aspect_ratio": "4:5",
  "resolution": "2k"
}
```

To get your API token: `higgsfield auth token` in terminal.

For Facts Reels (Spickzettel): use GPT Image 2 with brand colors:
```
Premium editorial infographic on cream white background (#F5F0E8).
Clean sans-serif typography. AYARI brand aesthetic.
Hook text at top, 6-8 bullet points below.
No decorative elements. Minimal. Elegant.
Text: [hook and bullet points from content plan]
```

---

## STEP 5 — Thumbnail Generation for Facts Reels

Facts Reels are images not videos. The AI can generate these fully:

1. Content plan provides: hook text + bullet points
2. n8n passes to Higgsfield with brand prompt
3. Image generated, saved to CDN
4. Posted via Instagram Image API

For product posts: use existing AYARI product images (already in Shopify CDN).

---

## SAFETY — Anti-Ban & Anti-Penalty Rules

This section protects @ayari.longevity from Instagram action blocks, shadowbans, and domain penalties.
Every rule here is non-negotiable. n8n must enforce these automatically.

---

### POSTING TIMING RULES

| Rule | Why |
|---|---|
| Never post at exact same time two days in a row | Looks like a bot to Meta's detection systems |
| Random wait: ±60 min from target time | `{{ Math.floor(Math.random() * 121) }}` min after trigger |
| Never post between 01:00–06:00 CET | Low engagement hour + unusual bot behavior window |
| Max 1 post per day per account | More than 1/day raises API abuse flags |
| Minimum 18h between posts | Even with random timing, enforce this as a hard floor |

**n8n enforcement:** Add an IF node before posting that checks: "Was a post published in the last 18 hours?" If yes → skip + send Telegram warning.

---

### HASHTAG RULES

| Rule | Why |
|---|---|
| Never use the same exact hashtag set twice in a row | Instagram spam filter flags repeated hashtag blocks |
| Max 5–8 hashtags per post (not 30) | Mass hashtag use is a shadowban signal since 2023 |
| Never use banned hashtags | Meta silently reduces reach without notifying you |
| Rotate hashtag groups — at least 3 different pools | Pool A / Pool B / Pool C — rotate weekly |

**n8n enforcement:** Content plan JSON already generates hashtags per post. Code node should verify no two consecutive posts share more than 3 identical hashtags.

---

### CAPTION RULES

| Rule | Why |
|---|---|
| Never post identical captions | Duplicate content = spam signal |
| Never start a caption with a # or @ | Reduces reach algorithmically |
| No external URLs in captions | Meta suppresses posts with links — use "link in bio" only |

---

### API & TOKEN RULES

| Rule | Why |
|---|---|
| Instagram access token must be refreshed every 45 days | Tokens expire at 60 days — stale token = posting failure |
| Build a token expiry check + Telegram alert | Silent expiry = days without posts, no warning |
| Use only official Meta Graph API v18+ | Unofficial or scraping tools = instant permanent ban |
| Never share IG_ACCESS_TOKEN outside GitHub Secrets | Token theft = account takeover |

**Automated token refresh reminder:**
Add a monthly cron in n8n:
- Fires on the 1st of every month
- Sends Telegram message: "⚠️ Token-Check: IG Access Token läuft in 15 Tagen ab. Jetzt erneuern."

---

### CONTENT QUALITY RULES

| Rule | Why |
|---|---|
| Every AI-generated image must pass your Telegram review | Low-quality AI content gets flagged by Meta's classifiers |
| No watermarks from other tools in images | Copyright flags + quality penalty |
| Video aspect ratio must be 9:16 for Reels | Wrong ratio = format rejection or poor distribution |
| Video length: 7–90 seconds for Reels | Outside this window = not eligible for Reels feed |
| Image resolution: minimum 1080×1080px | Low resolution reduces distribution quality |

---

### DOMAIN RULES (ayari-longevity.de)

| Rule | Why |
|---|---|
| Never link to a page that returns 404 | Google penalizes dead links from social traffic |
| Never publish AI blog content without human review | Google's Helpful Content Update penalizes thin AI text |
| Instagram bio link must always point to a live page | Meta checks bio links — dead links reduce account trust |

---

### TELEGRAM WARNING TRIGGERS

n8n should send you an automatic Telegram warning when any of these occur:

```
⚠️ WARNUNG: Posting in den letzten 18h bereits erfolgt — kein Post heute.
⚠️ WARNUNG: IG Access Token läuft in 15 Tagen ab.
⚠️ WARNUNG: Letzter Post hatte 0 Saves und 0 Shares — Überprüfe den Content.
⚠️ WARNUNG: Gleiche Hashtag-Gruppe wie gestern — rotiere zu Pool B/C.
⚠️ WARNUNG: Kein Video von Jasmin empfangen — Expert Reel heute nicht möglich.
⚠️ FEHLER: Instagram API returned 400/401 — Token prüfen oder Post fehlgeschlagen.
```

---

## PHASE PLAN

### Phase 1 (this week): Foundation
- [ ] Set up n8n Cloud account
- [ ] Apply for TikTok API access
- [ ] Build Workflow A (daily post + Telegram approval)
- [ ] Build Workflow B (video upload handler)
- [ ] Add GitHub Action for weekly content plan
- [ ] Test with one Facts Reel post

### Phase 2 (week 2): Full pipeline
- [ ] ManyChat keywords fully configured
- [ ] TikTok posting active
- [ ] Facebook posting active
- [ ] Higgsfield thumbnail generation automated

### Phase 3 (week 3+): YouTube + optimization
- [ ] YouTube Shorts posting
- [ ] A/B testing hooks via performance data
- [ ] Auto-report: what performed best this week

---

## COSTS (monthly estimate)

| Tool | Cost |
|---|---|
| n8n Cloud Starter | €20/mo |
| Higgsfield Plus | €39/mo |
| ManyChat Pro | €15/mo |
| n8n total API calls | included |
| Instagram/TikTok/FB API | free |
| **Total** | **~€74/mo** |

---

## WHAT YOU STILL DO (15 min/week)
1. Sunday evening: read weekly plan in Telegram → tap ✅ approve
2. Daily: tap ✅ on post preview in Telegram (30 sec per post)
3. When Jasmin records a video: drop it in Google Drive folder → done

Everything else: AI does it.
