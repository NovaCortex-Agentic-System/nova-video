#!/usr/bin/env python3
"""
heygen_avatar.py — Generare video talking head via HeyGen pentru NOVA Video agent.

Primește un audio_url public (generat de kie_voice.py) și avatar_id, produce MP4.

Usage:
  python heygen_avatar.py <audio_url> <avatar_id> <output_path> [opțiuni]
  python heygen_avatar.py --health
  python heygen_avatar.py --list-avatars
  python heygen_avatar.py --check-credits

Opțiuni:
  --width INT           Lățime video (default: 1080)
  --height INT          Înălțime video (default: 1920 — portret pentru reels)
  --background-url URL  URL imagine fundal (opțional)
  --avatar-style STYLE  Stilul avatarului: normal, circle, closeup (default: normal)
  --health              Verifică conexiunea API
  --list-avatars        Listează avatarele din cont cu preview URL-uri
  --check-credits       Verifică soldul de credite HeyGen
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path

BASE_URL = "https://api.heygen.com"
POLL_INTERVAL = 5
POLL_TIMEOUT = 300  # 5 minute pentru randare video


def get_api_key():
    key = os.environ.get("HEYGEN_API_KEY", "")
    if not key:
        print(json.dumps({"error": "HEYGEN_API_KEY lipsă din environment"}))
        sys.exit(1)
    return key


def headers(key):
    return {
        "X-Api-Key": key,
        "Content-Type": "application/json",
    }


def health_check(key):
    try:
        resp = requests.get(
            f"{BASE_URL}/v2/avatars",
            headers=headers(key),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            count = len(data.get("data", {}).get("avatars", []))
            print(json.dumps({"status": "ok", "avatars_available": count}))
        else:
            print(json.dumps({"status": "error", "http": resp.status_code}))
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)


def check_credits(key):
    try:
        resp = requests.get(
            f"{BASE_URL}/v1/credit.get",
            headers=headers(key),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            remaining = data.get("remaining_quota") or data.get("credits") or data.get("remaining", 0)
            print(json.dumps({"credits_remaining": remaining}))
        else:
            # Endpoint alternativ
            resp2 = requests.get(f"{BASE_URL}/v2/user/remaining_quota", headers=headers(key), timeout=10)
            if resp2.status_code == 200:
                data = resp2.json().get("data", {})
                remaining = data.get("remaining_quota", 0)
                print(json.dumps({"credits_remaining": remaining}))
            else:
                print(json.dumps({"credits_remaining": "necunoscut", "note": f"HTTP {resp.status_code}"}))
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def list_avatars(key):
    import re
    resp = requests.get(f"{BASE_URL}/v2/avatars", headers=headers(key), timeout=15)
    resp.raise_for_status()
    avatars = resp.json().get("data", {}).get("avatars", [])
    # Avatarele custom au ID hex de 32 caractere fără underscore
    custom = [a for a in avatars if re.match(r'^[a-f0-9]{32}$', a.get("avatar_id", ""))]
    result = custom if custom else avatars[:10]
    return [
        {
            "avatar_id": a.get("avatar_id"),
            "name": a.get("avatar_name"),
            "preview_image_url": a.get("preview_image_url"),
            "preview_video_url": a.get("preview_video_url"),
        }
        for a in result
    ]


def generate_video(key, audio_url, avatar_id, width, height, background_url=None, avatar_style="normal"):
    voice_block = {
        "type": "audio",
        "audio_url": audio_url,
    }

    character_block = {
        "type": "avatar",
        "avatar_id": avatar_id,
        "avatar_style": avatar_style,
    }

    video_input = {
        "character": character_block,
        "voice": voice_block,
    }

    if background_url:
        video_input["background"] = {
            "type": "image",
            "url": background_url,
        }

    payload = {
        "video_inputs": [video_input],
        "dimension": {"width": width, "height": height},
    }

    resp = requests.post(
        f"{BASE_URL}/v2/video/generate",
        headers=headers(key),
        json=payload,
        timeout=30,
    )

    if resp.status_code != 200:
        err = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        print(json.dumps({"error": f"generate eșuat HTTP {resp.status_code}", "detail": err}))
        sys.exit(1)

    data = resp.json()
    video_id = data.get("data", {}).get("video_id")
    if not video_id:
        print(json.dumps({"error": "video_id lipsă din răspuns", "raw": data}))
        sys.exit(1)

    return video_id


def poll_until_done(key, video_id):
    start = time.time()
    while True:
        if time.time() - start > POLL_TIMEOUT:
            print(json.dumps({"error": f"Timeout după {POLL_TIMEOUT}s. video_id={video_id}"}))
            sys.exit(1)

        try:
            resp = requests.get(
                f"{BASE_URL}/v1/video_status.get",
                headers=headers(key),
                params={"video_id": video_id},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(json.dumps({"error": f"Polling eșuat: {e}"}))
            sys.exit(1)

        data = resp.json().get("data", {})
        status = data.get("status", "")

        if status == "completed":
            return data
        elif status == "failed":
            err = data.get("error", {})
            print(json.dumps({"error": f"Randare eșuată: {err}", "video_id": video_id}))
            sys.exit(1)

        time.sleep(POLL_INTERVAL)


def download_file(url, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def main():
    parser = argparse.ArgumentParser(description="Generare video talking head HeyGen")
    parser.add_argument("audio_url", nargs="?", help="URL public audio (de la kie_voice.py)")
    parser.add_argument("avatar_id", nargs="?", help="ID avatar HeyGen")
    parser.add_argument("output_path", nargs="?", help="Cale MP4 output")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--background-url", help="URL imagine fundal (opțional)")
    parser.add_argument("--avatar-style", default="normal", choices=["normal", "circle", "closeup"])
    parser.add_argument("--list-avatars", action="store_true", help="Listează avatarele din cont cu preview URL-uri")
    parser.add_argument("--check-credits", action="store_true", help="Verifică soldul de credite HeyGen")
    parser.add_argument("--health", action="store_true", help="Verifică conexiunea API")

    args = parser.parse_args()
    key = get_api_key()

    if args.health:
        health_check(key)
        return

    if args.check_credits:
        check_credits(key)
        return

    if args.list_avatars:
        avatars = list_avatars(key)
        print(json.dumps({"avatars": avatars}, ensure_ascii=False))
        return

    if not args.audio_url or not args.avatar_id or not args.output_path:
        parser.print_help()
        sys.exit(1)

    start_time = time.time()

    video_id = generate_video(
        key=key,
        audio_url=args.audio_url,
        avatar_id=args.avatar_id,
        width=args.width,
        height=args.height,
        background_url=args.background_url,
        avatar_style=args.avatar_style,
    )

    record = poll_until_done(key, video_id)

    video_url = record.get("video_url", "")
    duration = record.get("duration", 0)

    try:
        download_file(video_url, args.output_path)
    except Exception as e:
        print(json.dumps({"error": f"Descărcare MP4 eșuată: {e}", "video_id": video_id, "video_url": video_url}))
        sys.exit(1)

    elapsed = round(time.time() - start_time, 1)
    size_bytes = Path(args.output_path).stat().st_size

    print(json.dumps({
        "video_id": video_id,
        "output_path": str(args.output_path),
        "video_url": video_url,
        "duration_s": duration,
        "cost_time_s": elapsed,
        "size_bytes": size_bytes,
    }))


if __name__ == "__main__":
    main()
