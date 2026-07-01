#!/usr/bin/env python3
"""
heygen_v3.py — HeyGen REST API v3 wrapper pentru NOVA Video agent.

Usage:
  python3 heygen_v3.py --health
  python3 heygen_v3.py --list-avatars
  python3 heygen_v3.py --list-voices [--language Romanian]
  python3 heygen_v3.py --create-avatar --avatar-name "Nume" --avatar-photo-url "https://..."
  python3 heygen_v3.py generate "<script>" <output.mp4> \\
    --avatar LOOK_ID --voice VOICE_ID \\
    [--aspect 9:16|16:9] [--resolution 1080p|720p] \\
    [--background-color "#1a1a2e"] [--background-image "https://..."] \\
    [--motion-prompt "gesturing naturally while speaking"] \\
    [--expressiveness high|medium|low] [--locale ro-RO]
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
        env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("HEYGEN_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        print(json.dumps({"error": "HEYGEN_API_KEY lipsă din environment sau .env"}))
        sys.exit(1)
    return key


def hdrs(key):
    return {"X-Api-Key": key, "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def health_check(key):
    """Verifică conexiunea via GET /v2/voices (endpoint stabil, nu necesită resurse speciale)."""
    try:
        resp = requests.get(f"{BASE_URL}/v2/voices", headers=hdrs(key), params={"limit": 1}, timeout=10)
        if resp.status_code == 200:
            print(json.dumps({"status": "ok", "message": "Cheie API validă, conexiune OK"}))
        elif resp.status_code == 401:
            print(json.dumps({"status": "error", "error": "Cheie API invalidă (401)"}))
            sys.exit(1)
        else:
            print(json.dumps({"status": "error", "error": f"HTTP {resp.status_code}", "body": resp.text[:200]}))
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)


def list_avatars(key):
    try:
        resp = requests.get(f"{BASE_URL}/v2/avatars", headers=hdrs(key), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        raw = (
            data.get("data", {}).get("avatars")
            or data.get("avatars")
            or data.get("data", [])
        )
        avatars = [
            {
                "id": a.get("avatar_id") or a.get("id", ""),
                "name": a.get("avatar_name") or a.get("name", ""),
            }
            for a in raw
        ]
        print(json.dumps({"status": "ok", "count": len(avatars), "avatars": avatars}))
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def list_voices(key, language=None):
    """Listează vocile disponibile, opțional filtrate după limbă (ex: 'Romanian').
    Dacă API-ul nu suportă filtrul server-side, filtrează client-side."""
    try:
        # Încearcă cu param de limbă
        params = {"language": language} if language else {}
        resp = requests.get(f"{BASE_URL}/v2/voices", headers=hdrs(key), params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        raw = (
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
            for v in raw
        ]
        # Filtrare client-side dacă API-ul a returnat toate vocile (ignorând param)
        if language:
            lang_lower = language.lower()
            filtered = [
                v for v in voices
                if lang_lower in (v.get("language") or "").lower()
                or lang_lower in (v.get("name") or "").lower()
            ]
            # Dacă filtrul server-side a funcționat, raw e deja filtrat — returnăm direct
            # Dacă filtered e mai mic decât voices, înseamnă că filtrul e client-side
            result = filtered if filtered else voices
            print(json.dumps({
                "status": "ok",
                "language_filter": language,
                "count": len(result),
                "voices": result,
            }))
        else:
            print(json.dumps({"status": "ok", "count": len(voices), "voices": voices}))
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Avatar creation
# ---------------------------------------------------------------------------

def create_photo_avatar(key, name, photo_url):
    """
    Creează un avatar persistent (Photo Avatar) din fotografie.
    Returnează look_id și group_id pentru reutilizare în generarea video.
    """
    payload = {
        "type": "photo",
        "name": name,
        "file": {"type": "url", "url": photo_url},
    }
    try:
        resp = requests.post(
            f"{BASE_URL}/v3/avatars",
            headers=hdrs(key),
            json=payload,
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"create_photo_avatar eșuat (rețea): {e}"}))
        sys.exit(1)

    if resp.status_code == 401:
        print(json.dumps({"error": "Cheie API invalidă (401)"}))
        sys.exit(1)
    if resp.status_code not in (200, 201):
        err = resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text
        print(json.dumps({"error": f"create_photo_avatar eșuat HTTP {resp.status_code}", "detail": err}))
        sys.exit(1)

    data = resp.json().get("data", {})
    item = data.get("avatar_item", {})
    group = data.get("avatar_group", {})
    look_id = item.get("id", "")
    group_id = group.get("id", "") or item.get("group_id", "")

    if not look_id:
        print(json.dumps({"error": "look_id lipsă din răspuns", "raw": data}))
        sys.exit(1)

    print(json.dumps({
        "status": "ok",
        "look_id": look_id,
        "group_id": group_id,
        "name": name,
        "note": "Salvează look_id în knowledge/brand-video.md pentru reutilizare.",
    }))


# ---------------------------------------------------------------------------
# Video generation
# ---------------------------------------------------------------------------

def build_background(color=None, image_url=None):
    """Construiește obiectul background pentru payload POST /v3/videos."""
    if image_url:
        return {"type": "image", "url": image_url, "fit": "cover"}
    if color:
        return {"type": "color", "value": color}
    return None


def create_video(key, script, avatar_id, voice_id, aspect, resolution,
                 background=None, motion_prompt=None, expressiveness=None, locale=None):
    """Trimite cerere POST /v3/videos și returnează video_id."""
    payload = {
        "type": "avatar",
        "avatar_id": avatar_id,
        "script": script,
        "voice_id": voice_id,
        "aspect_ratio": aspect,
        "resolution": resolution,
    }
    if background:
        payload["background"] = background
    if motion_prompt:
        payload["motion_prompt"] = motion_prompt
    if expressiveness:
        payload["expressiveness"] = expressiveness
    if locale:
        payload["voice_settings"] = {"locale": locale}

    try:
        resp = requests.post(
            f"{BASE_URL}/v3/videos",
            headers=hdrs(key),
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
        err = resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text
        print(json.dumps({"error": f"create_video eșuat HTTP {resp.status_code}", "detail": err}))
        sys.exit(1)

    data = resp.json()
    video_id = data.get("data", {}).get("video_id") or data.get("video_id")
    if not video_id:
        print(json.dumps({"error": "video_id lipsă din răspuns", "raw": data}))
        sys.exit(1)
    return video_id


def poll_until_done(key, video_id):
    """Polling la GET /v3/videos/{video_id} până la completed sau failed."""
    start = time.time()
    while True:
        if time.time() - start > POLL_TIMEOUT:
            print(json.dumps({"error": f"Timeout după {POLL_TIMEOUT}s", "video_id": video_id}))
            sys.exit(1)

        try:
            resp = requests.get(
                f"{BASE_URL}/v3/videos/{video_id}",
                headers=hdrs(key),
                timeout=15,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(json.dumps({"error": f"Polling eșuat: {e}", "video_id": video_id}))
            sys.exit(1)

        vdata = resp.json().get("data", {}) or resp.json()
        status = vdata.get("status", "")

        if status == "completed":
            return vdata
        if status in ("failed", "error"):
            msg = vdata.get("error") or vdata.get("message", "motiv necunoscut")
            print(json.dumps({"error": f"Generare eșuată: {msg}", "video_id": video_id}))
            sys.exit(1)

        time.sleep(POLL_INTERVAL)


def download_video(video_url, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(video_url, stream=True, timeout=120)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"Descărcare eșuată: {e}"}))
        sys.exit(1)


def generate(script, output_path, avatar_id, voice_id, aspect, resolution,
             background, motion_prompt, expressiveness, locale):
    key = get_api_key()
    t0 = time.time()

    video_id = create_video(
        key, script, avatar_id, voice_id, aspect, resolution,
        background=background,
        motion_prompt=motion_prompt,
        expressiveness=expressiveness,
        locale=locale,
    )

    vdata = poll_until_done(key, video_id)

    video_url = vdata.get("video_url") or vdata.get("url") or vdata.get("download_url")
    if not video_url:
        print(json.dumps({"error": "URL de descărcare lipsă din răspuns", "data": vdata}))
        sys.exit(1)

    download_video(video_url, output_path)

    size_bytes = Path(output_path).stat().st_size
    duration = vdata.get("duration") or round(time.time() - t0, 1)

    print(json.dumps({
        "status": "ok",
        "output_path": str(output_path),
        "video_id": video_id,
        "duration_s": duration,
        "size_bytes": size_bytes,
    }))


# ---------------------------------------------------------------------------
# Video Agent (talking head + B-roll automat din prompt)
# ---------------------------------------------------------------------------

def create_video_agent(key, prompt, avatar_id=None, voice_id=None,
                       orientation="landscape", files=None):
    """
    Trimite cerere POST /v3/video-agents.
    Returnează video_id pentru polling.
    files = listă de {"type": "url", "url": "..."} — imagini/PDF-uri ca context B-roll.
    """
    payload = {"prompt": prompt, "orientation": orientation}
    if avatar_id:
        payload["avatar_id"] = avatar_id
    if voice_id:
        payload["voice_id"] = voice_id
    if files:
        payload["files"] = files

    try:
        resp = requests.post(
            f"{BASE_URL}/v3/video-agents",
            headers=hdrs(key),
            json=payload,
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"video_agent eșuat (rețea): {e}"}))
        sys.exit(1)

    if resp.status_code == 401:
        print(json.dumps({"error": "Cheie API invalidă (401)"}))
        sys.exit(1)
    if resp.status_code not in (200, 201):
        err = resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text
        print(json.dumps({"error": f"video_agent eșuat HTTP {resp.status_code}", "detail": err}))
        sys.exit(1)

    data = resp.json()
    video_id = (
        data.get("data", {}).get("video_id")
        or data.get("data", {}).get("session_id")
        or data.get("video_id")
    )
    if not video_id:
        print(json.dumps({"error": "video_id lipsă din răspuns", "raw": data}))
        sys.exit(1)
    return video_id


def generate_agent(prompt, output_path, avatar_id=None, voice_id=None,
                   orientation="landscape", files=None):
    key = get_api_key()
    t0 = time.time()

    video_id = create_video_agent(
        key, prompt,
        avatar_id=avatar_id,
        voice_id=voice_id,
        orientation=orientation,
        files=files,
    )

    vdata = poll_until_done(key, video_id)

    video_url = vdata.get("video_url") or vdata.get("url") or vdata.get("download_url")
    if not video_url:
        print(json.dumps({"error": "URL de descărcare lipsă", "data": vdata}))
        sys.exit(1)

    download_video(video_url, output_path)

    size_bytes = Path(output_path).stat().st_size
    duration = vdata.get("duration") or round(time.time() - t0, 1)

    print(json.dumps({
        "status": "ok",
        "output_path": str(output_path),
        "video_id": video_id,
        "duration_s": duration,
        "size_bytes": size_bytes,
    }))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="HeyGen v3 wrapper pentru NOVA Video")

    parser.add_argument("--health", action="store_true", help="Verifică conexiunea și quota")
    parser.add_argument("--list-avatars", action="store_true", help="Listează avatarele disponibile")
    parser.add_argument("--list-voices", action="store_true", help="Listează vocile disponibile")
    parser.add_argument("--language", default=None, help="Filtru limbă pentru voci (ex: Romanian)")
    parser.add_argument("--create-avatar", action="store_true", help="Creează avatar persistent din fotografie")
    parser.add_argument("--avatar-name", default=None, help="Numele avatarului")
    parser.add_argument("--avatar-photo-url", default=None, help="URL public al fotografiei")

    subparsers = parser.add_subparsers(dest="command")
    gen = subparsers.add_parser("generate", help="Generează video cu avatar")
    gen.add_argument("script_text", help="Textul scriptului video")
    gen.add_argument("output_path", help="Calea fișierului output .mp4")
    gen.add_argument("--avatar", dest="avatar_id", required=True, help="look_id avatarului")
    gen.add_argument("--voice", dest="voice_id", required=True, help="voice_id")
    gen.add_argument("--aspect", default="9:16",
                     choices=["9:16", "16:9", "1:1", "4:5", "5:4"],
                     help="Aspect ratio (default: 9:16)")
    gen.add_argument("--resolution", default="1080p",
                     choices=["1080p", "720p", "4k"],
                     help="Rezoluție (default: 1080p)")
    gen.add_argument("--background-color", default=None,
                     help="Culoare fundal hex (ex: #1a1a2e)")
    gen.add_argument("--background-image", default=None,
                     help="URL imagine fundal scenă")
    gen.add_argument("--motion-prompt", default=None,
                     help="Prompt mișcare corp avatar")
    gen.add_argument("--expressiveness", default=None,
                     choices=["high", "medium", "low"],
                     help="Expresivitate facială")
    gen.add_argument("--locale", default=None,
                     help="BCP-47 locale pentru voce (ex: ro-RO)")

    ag = subparsers.add_parser("agent", help="Video Agent: talking head + B-roll automat din prompt")
    ag.add_argument("prompt_text", help="Prompt care descrie întregul video")
    ag.add_argument("output_path", help="Calea fișierului output .mp4")
    ag.add_argument("--avatar", dest="avatar_id", default=None, help="look_id avatarului (opțional)")
    ag.add_argument("--voice", dest="voice_id", default=None, help="voice_id (opțional)")
    ag.add_argument("--orientation", default="landscape", choices=["landscape", "portrait"],
                     help="Orientare video (default: landscape)")
    ag.add_argument("--file", dest="files", action="append", default=None,
                     metavar="URL", help="URL imagine/PDF ca context B-roll (repetabil)")

    args = parser.parse_args()
    key = get_api_key()

    if args.health:
        health_check(key)
        return

    if args.list_avatars:
        list_avatars(key)
        return

    if args.list_voices:
        list_voices(key, language=args.language)
        return

    if args.create_avatar:
        if not args.avatar_name or not args.avatar_photo_url:
            print(json.dumps({"error": "--avatar-name și --avatar-photo-url sunt obligatorii"}))
            sys.exit(1)
        create_photo_avatar(key, args.avatar_name, args.avatar_photo_url)
        return

    if args.command == "generate":
        bg = build_background(color=args.background_color, image_url=args.background_image)
        generate(
            script=args.script_text,
            output_path=args.output_path,
            avatar_id=args.avatar_id,
            voice_id=args.voice_id,
            aspect=args.aspect,
            resolution=args.resolution,
            background=bg,
            motion_prompt=args.motion_prompt,
            expressiveness=args.expressiveness,
            locale=args.locale,
        )
        return

    if args.command == "agent":
        files = [{"type": "url", "url": u} for u in args.files] if args.files else None
        generate_agent(
            prompt=args.prompt_text,
            output_path=args.output_path,
            avatar_id=args.avatar_id,
            voice_id=args.voice_id,
            orientation=args.orientation,
            files=files,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
