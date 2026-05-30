# AYARI Automation System — Setup Guide
# n8n + Telegram + Instagram + TikTok + Facebook + YouTube

---

## OVERVIEW

```
[Sunday 8pm] n8n trigger
→ content_planner_longevity.py generates 7-day plan
→ Telegram: "Here's next week's plan — approve?"
→ You approve → plan is locked

[Daily, 8am] n8n trigger
→ reads today's post from plan
→ if AI image needed → calls Higgsfield API
→ Telegram: preview of post with [✅ POST] [⏭ SKIP] buttons
→ You tap ✅ → post_publisher.py posts to all platforms
→ ManyChat handles all DM responses automatically
```

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

**Trigger:** Schedule — runs Mon-Sun at 7:30am CET
**Logic:**
1. Read today's plan from latest `reports/weekly/plan_*.json`
2. Find today's post (by date)
3. If `needs_jasmin_video = true` → check Google Drive for uploaded video
   - If no video found → skip and send Telegram reminder
4. If AI image needed → call Higgsfield API with `thumbnail_prompt`
5. Send Telegram preview:
   ```
   📸 @ayari.longevity post heute (Dienstag)
   Format: Facts Reel
   Hook: "Das wissen die wenigsten über Magnesium"
   Caption: [preview...]
   Bild: [attached image]

   [✅ JETZT POSTEN] [⏭ ÜBERSPRINGEN] [✏️ CAPTION ÄNDERN]
   ```
6. Wait for Telegram button response
7. On ✅ → call post_publisher.py → post to Instagram (+Facebook)
8. Confirm: "✅ Gepostet! Instagram ID: 123456"

**n8n Nodes needed:**
- Schedule Trigger
- Read Binary File (read plan JSON)
- Code Node (JavaScript to find today's post)
- HTTP Request (Higgsfield API for image)
- Telegram Send Message
- Telegram Trigger (wait for button click)
- HTTP Request / Execute Command (call post_publisher.py)
- Telegram Send Message (confirmation)

---

### Workflow B: Video Upload Handler

**Trigger:** Google Drive — New file in "AYARI Ready to Post" folder
**Logic:**
1. New video file detected in Google Drive
2. Read filename convention: `YYYY-MM-DD_platform_caption-key.mp4`
3. Look up caption from weekly plan
4. Send Telegram preview with video thumbnail
5. Wait for approval
6. On approve → download video → post to:
   - Instagram Reels
   - TikTok (if TIKTOK_ACCESS_TOKEN set)
   - Facebook (same video)
   - YouTube Shorts (Phase 2)

**File naming convention for videos:**
```
2026-06-02_longevity_magnesium-reel.mp4
YYYY-MM-DD_channel_description.mp4
```

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
