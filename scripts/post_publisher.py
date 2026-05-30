"""
AYARI Multi-Platform Publisher
Called by n8n when a post is approved via Telegram.
Publishes to: Instagram, Facebook (same API), TikTok, YouTube.

Usage:
  python post_publisher.py --platform instagram --post-id "Montag_2026-06-02"
  python post_publisher.py --platform all --video /path/to/video.mp4 --caption "..."

Environment variables:
  IG_ACCESS_TOKEN, IG_USER_ID
  TIKTOK_ACCESS_TOKEN (optional)
  YOUTUBE_CLIENT_SECRET (optional)
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path

IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_USER_ID = os.environ.get("IG_USER_ID", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TIKTOK_ACCESS_TOKEN = os.environ.get("TIKTOK_ACCESS_TOKEN", "")

GRAPH_API = "https://graph.facebook.com/v21.0"


# ─── INSTAGRAM ────────────────────────────────────────────────────────────────

def get_ig_page_token() -> tuple[str, str]:
    url = f"{GRAPH_API}/me/accounts"
    params = {"fields": "access_token,instagram_business_account", "access_token": IG_ACCESS_TOKEN}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    for page in resp.json().get("data", []):
        ig = page.get("instagram_business_account")
        if ig:
            return ig["id"], page.get("access_token", IG_ACCESS_TOKEN)
    return IG_USER_ID, IG_ACCESS_TOKEN


def post_instagram_image(image_url: str, caption: str) -> str:
    user_id, token = get_ig_page_token()

    # Step 1: Create media container
    create_resp = requests.post(
        f"{GRAPH_API}/{user_id}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": token
        },
        timeout=30
    )
    create_resp.raise_for_status()
    container_id = create_resp.json()["id"]
    print(f"Instagram container created: {container_id}")

    # Step 2: Wait for container to be ready
    time.sleep(3)

    # Step 3: Publish
    publish_resp = requests.post(
        f"{GRAPH_API}/{user_id}/media_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=30
    )
    publish_resp.raise_for_status()
    post_id = publish_resp.json()["id"]
    print(f"Instagram post published: {post_id}")
    return post_id


def post_instagram_reel(video_url: str, caption: str, cover_url: str = None) -> str:
    user_id, token = get_ig_page_token()

    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": token,
        "share_to_feed": "true"
    }
    if cover_url:
        params["cover_url"] = cover_url

    create_resp = requests.post(f"{GRAPH_API}/{user_id}/media", params=params, timeout=30)
    create_resp.raise_for_status()
    container_id = create_resp.json()["id"]
    print(f"Instagram Reel container created: {container_id}")

    # Poll until ready (video processing takes time)
    for _ in range(20):
        time.sleep(10)
        status_resp = requests.get(
            f"{GRAPH_API}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30
        )
        status = status_resp.json().get("status_code")
        print(f"Container status: {status}")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError(f"Instagram container processing error: {status_resp.json()}")

    publish_resp = requests.post(
        f"{GRAPH_API}/{user_id}/media_publish",
        params={"creation_id": container_id, "access_token": token},
        timeout=30
    )
    publish_resp.raise_for_status()
    post_id = publish_resp.json()["id"]
    print(f"Instagram Reel published: {post_id}")
    return post_id


def post_instagram_carousel(image_urls: list[str], caption: str) -> str:
    user_id, token = get_ig_page_token()

    # Step 1: Create container for each image
    child_ids = []
    for url in image_urls:
        r = requests.post(
            f"{GRAPH_API}/{user_id}/media",
            params={"image_url": url, "is_carousel_item": "true", "access_token": token},
            timeout=30
        )
        r.raise_for_status()
        child_ids.append(r.json()["id"])

    # Step 2: Create carousel container
    r = requests.post(
        f"{GRAPH_API}/{user_id}/media",
        params={
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": token
        },
        timeout=30
    )
    r.raise_for_status()
    carousel_id = r.json()["id"]

    time.sleep(3)

    # Step 3: Publish
    r = requests.post(
        f"{GRAPH_API}/{user_id}/media_publish",
        params={"creation_id": carousel_id, "access_token": token},
        timeout=30
    )
    r.raise_for_status()
    post_id = r.json()["id"]
    print(f"Instagram carousel published: {post_id}")
    return post_id


# ─── FACEBOOK ─────────────────────────────────────────────────────────────────

def post_facebook_photo(page_id: str, page_token: str, image_url: str, caption: str) -> str:
    r = requests.post(
        f"{GRAPH_API}/{page_id}/photos",
        params={"url": image_url, "caption": caption, "access_token": page_token},
        timeout=30
    )
    r.raise_for_status()
    post_id = r.json().get("id")
    print(f"Facebook post published: {post_id}")
    return post_id


def get_facebook_page() -> tuple[str, str]:
    url = f"{GRAPH_API}/me/accounts"
    params = {"fields": "id,name,access_token", "access_token": IG_ACCESS_TOKEN}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    pages = resp.json().get("data", [])
    if pages:
        return pages[0]["id"], pages[0]["access_token"]
    raise RuntimeError("No Facebook page found")


# ─── TIKTOK ───────────────────────────────────────────────────────────────────

def post_tiktok_video(video_path: str, caption: str) -> str:
    """
    TikTok Content Posting API v2.
    Requires: TIKTOK_ACCESS_TOKEN with video.publish scope.
    """
    if not TIKTOK_ACCESS_TOKEN:
        print("TikTok: no access token configured, skipping")
        return None

    # Step 1: Initialize upload
    init_resp = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers={"Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}", "Content-Type": "application/json"},
        json={
            "post_info": {
                "title": caption[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {"source": "FILE_UPLOAD", "video_size": Path(video_path).stat().st_size}
        },
        timeout=30
    )
    init_resp.raise_for_status()
    data = init_resp.json().get("data", {})
    publish_id = data.get("publish_id")
    upload_url = data.get("upload_url")

    # Step 2: Upload video file
    with open(video_path, "rb") as f:
        upload_resp = requests.put(upload_url, data=f, timeout=120)
    upload_resp.raise_for_status()
    print(f"TikTok video uploaded, publish_id: {publish_id}")
    return publish_id


# ─── TELEGRAM NOTIFICATION ────────────────────────────────────────────────────

def notify_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=30)


# ─── MAIN PUBLISHER ───────────────────────────────────────────────────────────

def publish_post(post_data: dict, platforms: list[str] = None) -> dict:
    """
    post_data keys:
      - content_type: image | video | carousel
      - media_url: public URL to image/video (from CDN, Higgsfield, or Google Drive)
      - media_urls: list of URLs for carousel
      - caption: full caption text
      - hashtags: list of hashtags
    """
    if platforms is None:
        platforms = ["instagram"]

    caption = post_data["caption"]
    if post_data.get("hashtags"):
        caption += "\n\n" + " ".join(post_data["hashtags"])

    results = {}

    for platform in platforms:
        try:
            if platform == "instagram":
                ct = post_data.get("content_type", "image")
                if ct == "video":
                    pid = post_instagram_reel(post_data["media_url"], caption)
                elif ct == "carousel":
                    pid = post_instagram_carousel(post_data["media_urls"], caption)
                else:
                    pid = post_instagram_image(post_data["media_url"], caption)
                results["instagram"] = pid

            elif platform == "facebook":
                page_id, page_token = get_facebook_page()
                pid = post_facebook_photo(page_id, page_token, post_data["media_url"], caption)
                results["facebook"] = pid

            elif platform == "tiktok":
                if post_data.get("content_type") == "video" and post_data.get("video_path"):
                    pid = post_tiktok_video(post_data["video_path"], caption)
                    results["tiktok"] = pid

        except Exception as e:
            results[platform] = f"ERROR: {e}"
            print(f"{platform} error: {e}")

    return results


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AYARI Post Publisher")
    parser.add_argument("--post-json", help="Path to post JSON file")
    parser.add_argument("--platforms", default="instagram", help="Comma-separated: instagram,facebook,tiktok")
    parser.add_argument("--media-url", help="Direct media URL")
    parser.add_argument("--caption", help="Caption text")
    parser.add_argument("--content-type", default="image", choices=["image", "video", "carousel"])
    args = parser.parse_args()

    platforms = [p.strip() for p in args.platforms.split(",")]

    if args.post_json:
        with open(args.post_json) as f:
            post_data = json.load(f)
    else:
        post_data = {
            "content_type": args.content_type,
            "media_url": args.media_url,
            "caption": args.caption,
        }

    print(f"Publishing to: {platforms}")
    results = publish_post(post_data, platforms)
    print(f"Results: {json.dumps(results, indent=2)}")

    status = "\n".join([f"✅ {p}: {v}" if not str(v).startswith("ERROR") else f"❌ {p}: {v}" for p, v in results.items()])
    notify_telegram(f"*Post published*\n\n{status}")


if __name__ == "__main__":
    main()
