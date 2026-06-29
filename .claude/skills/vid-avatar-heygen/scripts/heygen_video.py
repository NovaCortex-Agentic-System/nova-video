#!/usr/bin/env python3
"""
heygen_video.py — Generare video cu avatar via HeyGen REST API v3 pentru NOVA Video agent.

Apelează direct API-ul HeyGen fără SDK extern, doar requests.

Usage:
  python3 heygen_video.py "<script_text>" <output_path> [opțiuni]
  python3 heygen_video.py --health
  python3 heygen_video.py --list-avatars
  python3 heygen_video.py --list-voices

Opțiuni:
  --avatar AVATAR_ID   ID-ul avatarului (obligatoriu pentru generare)
  --voice VOICE_ID     ID-ul vocii (obligatoriu pentru generare)
  --aspect RATIO       Aspect ratio: 9:16 sau 16:9 (default: 9:16)
  --health             Verifică conexiunea API și returnează wallet balance
  --list-avatars       Listează avatarele disponibile
  --list-voices        Listează vocile disponibile
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path

BASE_URL = "https://api.heygen.com"
POLL_INTERVAL = 10
POLL_TIMEOUT = 600  # 10 minute


def get_api_key():
    key = os.environ.get("HEYGEN_API_KEY", "")
    if not key:
        # Caută în .env relativ la locația scriptului
        env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
        if env_path.exists():
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("HEYGEN_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass
    if not key:
        print(json.dumps({"error": "HEYGEN_API_KEY lipsă din environment sau .env"}))
        sys.exit(1)
    return key


def headers(key):
    return {
        "x-api-key": key,
        "Content-Type": "application/json",
    }


def health_check(key):
    """Verifică conexiunea și returnează wallet balance."""
    try:
        resp = requests.get(
            f"{BASE_URL}/v3/users/me",
            headers=headers(key),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            balance = (
                data.get("data", {}).get("wallet_balance")
                or data.get("wallet_balance")
                or "necunoscut"
            )
            print(json.dumps({"status": "ok", "wallet_balance": balance}))
        elif resp.status_code == 401:
            print(json.dumps({"status": "error", "error": "Cheie API invalidă (401)"}))
            sys.exit(1)
        else:
            print(json.dumps({
                "status": "ok",
                "wallet_balance": "indisponibil",
                "note": f"HTTP {resp.status_code}",
            }))
    except requests.exceptions.RequestException as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)


def list_avatars(key):
    """Returnează lista de avatare disponibile (id + name)."""
    try:
        resp = requests.get(
            f"{BASE_URL}/v2/avatars",
            headers=headers(key),
            timeout=15,
        )
        if resp.status_code == 401:
            print(json.dumps({"error": "Cheie API invalidă (401)"}))
            sys.exit(1)
        resp.raise_for_status()
        data = resp.json()
        avatars_raw = (
            data.get("data", {}).get("avatars")
            or data.get("avatars")
            or data.get("data", [])
        )
        avatars = [
            {
                "id": a.get("avatar_id") or a.get("id", ""),
                "name": a.get("avatar_name") or a.get("name", ""),
            }
            for a in avatars_raw
        ]
        print(json.dumps({"status": "ok", "avatars": avatars}))
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"list_avatars eșuat (rețea): {e}"}))
        sys.exit(1)


def list_voices(key):
    """Returnează lista de voci disponibile (id + name + language)."""
    try:
        resp = requests.get(
            f"{BASE_URL}/v2/voices",
            headers=headers(key),
            timeout=15,
        )
        if resp.status_code == 401:
            print(json.dumps({"error": "Cheie API invalidă (401)"}))
            sys.exit(1)
        resp.raise_for_status()
        data = resp.json()
        voices_raw = (
            data.get("data", {}).get("voices")
            or data.get("voices")
            or data.get("data", [])
        )
        voices = [
            {
                "id": v.get("voice_id") or v.get("id", ""),
                "name": v.get("name", ""),
                "language": v.get("language") or v.get("locale", ""),
            }
            for v in voices_raw
        ]
        print(json.dumps({"status": "ok", "voices": voices}))
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"list_voices eșuat (rețea): {e}"}))
        sys.exit(1)


def create_video(key, script_text, avatar_id, voice_id, aspect):
    """Trimite cerere de generare video și returnează video_id."""
    if aspect == "16:9":
        width, height = 1920, 1080
    else:
        # Default 9:16 (portrait)
        width, height = 1080, 1920

    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "input_text": script_text,
                    "voice_id": voice_id,
                },
            }
        ],
        "dimension": {
            "width": width,
            "height": height,
        },
        "test": False,
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/v3/video/generate",
            headers=headers(key),
            json=payload,
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"create_video eșuat (rețea): {e}"}))
        sys.exit(1)

    if resp.status_code == 401:
        print(json.dumps({"error": "Cheie API invalidă (401)"}))
        sys.exit(1)

    if resp.status_code not in (200, 201):
        err = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        print(json.dumps({"error": f"create_video eșuat HTTP {resp.status_code}", "detail": err}))
        sys.exit(1)

    data = resp.json()
    video_id = (
        data.get("data", {}).get("video_id")
        or data.get("video_id")
    )
    if not video_id:
        print(json.dumps({"error": "video_id lipsă din răspuns", "raw": data}))
        sys.exit(1)

    return video_id


def poll_until_done(key, video_id):
    """Polls statusul la fiecare 10s până la completed/failed. Returnează datele video."""
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > POLL_TIMEOUT:
            print(json.dumps({"error": f"Timeout după {POLL_TIMEOUT}s. video_id={video_id}"}))
            sys.exit(1)

        try:
            resp = requests.get(
                f"{BASE_URL}/v3/video/{video_id}",
                headers=headers(key),
                timeout=15,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(json.dumps({"error": f"Polling eșuat (rețea): {e}", "video_id": video_id}))
            sys.exit(1)

        data = resp.json()
        video_data = data.get("data", {}) or data
        status = video_data.get("status", "")

        if status == "completed":
            return video_data
        elif status in ("failed", "error"):
            fail_msg = video_data.get("error") or video_data.get("message", "motiv necunoscut")
            print(json.dumps({"error": f"Generare eșuată: {fail_msg}", "video_id": video_id}))
            sys.exit(1)

        # Încă în procesare (processing, pending, waiting etc.)
        time.sleep(POLL_INTERVAL)


def download_video(video_url, output_path):
    """Descarcă MP4-ul cu streaming la output_path."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(video_url, stream=True, timeout=120)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except FileNotFoundError:
        print(json.dumps({"error": f"Directorul output nu poate fi creat: {output_path}"}))
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"Descărcare video eșuată (rețea): {e}", "video_url": video_url}))
        sys.exit(1)


def generate(script_text, output_path, avatar_id, voice_id, aspect):
    key = get_api_key()
    start_time = time.time()

    video_id = create_video(key, script_text, avatar_id, voice_id, aspect)

    video_data = poll_until_done(key, video_id)

    video_url = (
        video_data.get("video_url")
        or video_data.get("url")
        or video_data.get("download_url")
    )
    if not video_url:
        print(json.dumps({"error": "Niciun URL de descărcare în răspuns", "data": video_data}))
        sys.exit(1)

    download_video(video_url, output_path)

    elapsed = round(time.time() - start_time, 1)
    size_bytes = Path(output_path).stat().st_size

    print(json.dumps({
        "status": "ok",
        "output_path": str(output_path),
        "video_id": video_id,
        "duration_s": elapsed,
        "size_bytes": size_bytes,
    }))


def main():
    parser = argparse.ArgumentParser(description="Generare video cu avatar HeyGen pentru NOVA Video")
    parser.add_argument("script_text", nargs="?", help="Textul scriptului video")
    parser.add_argument("output_path", nargs="?", help="Calea fișierului output .mp4")
    parser.add_argument("--avatar", dest="avatar_id", help="ID-ul avatarului HeyGen")
    parser.add_argument("--voice", dest="voice_id", help="ID-ul vocii HeyGen")
    parser.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"], help="Aspect ratio (default: 9:16)")
    parser.add_argument("--health", action="store_true", help="Verifică conexiunea API și wallet balance")
    parser.add_argument("--list-avatars", action="store_true", help="Listează avatarele disponibile")
    parser.add_argument("--list-voices", action="store_true", help="Listează vocile disponibile")

    args = parser.parse_args()

    key = get_api_key()

    if args.health:
        health_check(key)
        return

    if args.list_avatars:
        list_avatars(key)
        return

    if args.list_voices:
        list_voices(key)
        return

    if not args.script_text or not args.output_path:
        parser.print_help()
        sys.exit(1)

    if not args.avatar_id:
        print(json.dumps({"error": "Parametrul --avatar este obligatoriu pentru generare"}))
        sys.exit(1)

    if not args.voice_id:
        print(json.dumps({"error": "Parametrul --voice este obligatoriu pentru generare"}))
        sys.exit(1)

    generate(
        script_text=args.script_text,
        output_path=args.output_path,
        avatar_id=args.avatar_id,
        voice_id=args.voice_id,
        aspect=args.aspect,
    )


if __name__ == "__main__":
    main()
