#!/usr/bin/env python3
"""
kie_music.py — Generare muzică via Suno (prin KIE.ai) pentru NOVA Video agent.

Apelează API-ul KIE.ai pentru generare muzicală folosind Suno V5.5.
Endpoint diferit față de video/voice: POST /api/v1/generate

Usage:
  python kie_music.py "<prompt>" <output_path> [opțiuni]
  python kie_music.py --health

Opțiuni:
  --duration SECONDS  Durata muzicii în secunde (default: 30)
  --health            Verifică conexiunea API
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path

BASE_URL = "https://api.kie.ai/api/v1"
POLL_INTERVAL = 5
POLL_TIMEOUT = 300  # 5 minute pentru generare muzicală


def get_api_key():
    key = os.environ.get("KIE_API_KEY", "")
    if not key:
        print(json.dumps({"error": "KIE_API_KEY lipsă din environment"}))
        sys.exit(1)
    return key


def headers(key):
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def health_check(key):
    try:
        resp = requests.get(
            f"{BASE_URL}/user/info",
            headers=headers(key),
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            credits = data.get("data", {}).get("credits", "necunoscut")
            print(json.dumps({"status": "ok", "credits": credits}))
        elif resp.status_code == 401:
            print(json.dumps({"status": "error", "error": "Cheie API invalidă (401)"}))
            sys.exit(1)
        else:
            print(json.dumps({"status": "ok", "note": f"HTTP {resp.status_code}"}))
    except requests.exceptions.RequestException as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)


def create_music_task(key, prompt, duration):
    # Suno folosește endpoint /generate, nu /jobs/createTask
    payload = {
        "prompt": prompt,
        "duration": duration,
        "model": "V5.5",
        "instrumental": True,
    }

    resp = requests.post(
        f"{BASE_URL}/generate",
        headers=headers(key),
        json=payload,
        timeout=30,
    )

    if resp.status_code != 200:
        err = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        print(json.dumps({"error": f"generate muzică eșuat HTTP {resp.status_code}", "detail": err}))
        sys.exit(1)

    data = resp.json()
    # Suno poate returna task_id direct sau poate returna URL sincron
    task_id = (data.get("data", {}).get("taskId")
               or data.get("taskId")
               or data.get("id"))

    # Dacă răspunsul conține deja URL-ul audio (răspuns sincron)
    audio_url = (data.get("data", {}).get("audioUrl")
                 or data.get("audioUrl")
                 or data.get("audio_url"))

    if audio_url:
        return None, audio_url  # răspuns sincron

    if not task_id:
        print(json.dumps({"error": "taskId/audioUrl lipsă din răspuns Suno", "raw": data}))
        sys.exit(1)

    return task_id, None


def poll_until_done(key, task_id):
    start = time.time()
    while True:
        if time.time() - start > POLL_TIMEOUT:
            print(json.dumps({"error": f"Timeout muzică după {POLL_TIMEOUT}s. task_id={task_id}"}))
            sys.exit(1)

        try:
            # Suno poate folosi /generate/recordInfo sau /jobs/recordInfo
            resp = requests.get(
                f"{BASE_URL}/generate/recordInfo",
                headers=headers(key),
                params={"taskId": task_id},
                timeout=15,
            )
            if resp.status_code == 404:
                # Fallback la endpoint-ul de jobs
                resp = requests.get(
                    f"{BASE_URL}/jobs/recordInfo",
                    headers=headers(key),
                    params={"taskId": task_id},
                    timeout=15,
                )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(json.dumps({"error": f"Polling muzică eșuat: {e}"}))
            sys.exit(1)

        data = resp.json().get("data", {})
        state = data.get("state") or data.get("status", "")

        if state == "success":
            return data
        elif state in ("failed", "error"):
            fail_msg = data.get("failMsg") or data.get("message", "motiv necunoscut")
            print(json.dumps({"error": f"Generare muzică eșuată: {fail_msg}", "task_id": task_id}))
            sys.exit(1)

        time.sleep(POLL_INTERVAL)


def download_file(url, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def generate_music(prompt, output_path, duration):
    key = get_api_key()
    start_time = time.time()

    task_id, audio_url = create_music_task(key, prompt, duration)

    if audio_url:
        # Răspuns sincron — descarcă direct
        record = {"audioUrl": audio_url, "credits": 0}
    else:
        record = poll_until_done(key, task_id)
        audio_url = (record.get("audioUrl")
                     or record.get("audio_url")
                     or (record.get("resultUrls") or [""])[0])

    if not audio_url:
        print(json.dumps({"error": "Niciun URL audio în răspuns Suno", "record": record}))
        sys.exit(1)

    try:
        download_file(audio_url, output_path)
    except Exception as e:
        print(json.dumps({"error": f"Descărcare muzică eșuată: {e}"}))
        sys.exit(1)

    elapsed = round(time.time() - start_time, 1)
    credits = record.get("credits") or record.get("cost", 0)
    size_bytes = Path(output_path).stat().st_size

    print(json.dumps({
        "task_id": task_id,
        "output_path": str(output_path),
        "audio_url": audio_url,
        "cost_time_s": elapsed,
        "credits": credits,
        "size_bytes": size_bytes,
    }))


def main():
    parser = argparse.ArgumentParser(description="Generare muzică Suno via kie.ai")
    parser.add_argument("prompt", nargs="?", help="Descrierea stilului muzical")
    parser.add_argument("output_path", nargs="?", help="Calea fișierului output .mp3")
    parser.add_argument("--duration", type=int, default=30, help="Durata în secunde (default: 30)")
    parser.add_argument("--health", action="store_true", help="Verifică conexiunea API")

    args = parser.parse_args()

    if args.health:
        health_check(get_api_key())
        return

    if not args.prompt or not args.output_path:
        parser.print_help()
        sys.exit(1)

    generate_music(
        prompt=args.prompt,
        output_path=args.output_path,
        duration=args.duration,
    )


if __name__ == "__main__":
    main()
