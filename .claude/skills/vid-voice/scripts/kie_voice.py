#!/usr/bin/env python3
"""
kie_voice.py — Generare voiceover via ElevenLabs (prin KIE.ai) pentru NOVA Video agent.

Apelează API-ul KIE.ai pentru text-to-speech folosind modelele ElevenLabs.

Usage:
  python kie_voice.py "<text>" <output_path> [opțiuni]
  python kie_voice.py --health

Opțiuni:
  --model MODEL       Model TTS (default: elevenlabs/text-to-speech-multilingual-v2)
  --language CODE     Codul limbii (default: ro)
  --voice-id ID       ID voce ElevenLabs (opțional, default: vocea default a modelului)
  --speed FLOAT       Viteza vorbirii: 0.5-2.0 (default: 1.0)
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
POLL_INTERVAL = 3
POLL_TIMEOUT = 180  # 3 minute pentru TTS


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


def create_tts_task(key, text, model, language, voice_id=None, speed=1.0):
    payload = {
        "model": model,
        "input": {
            "text": text,
            "language_code": language,
            "speed": speed,
        },
    }
    if voice_id:
        payload["input"]["voice_id"] = voice_id

    resp = requests.post(
        f"{BASE_URL}/jobs/createTask",
        headers=headers(key),
        json=payload,
        timeout=30,
    )

    if resp.status_code != 200:
        err = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        print(json.dumps({"error": f"createTask TTS eșuat HTTP {resp.status_code}", "detail": err}))
        sys.exit(1)

    data = resp.json()
    task_id = data.get("data", {}).get("taskId") or data.get("taskId")
    if not task_id:
        print(json.dumps({"error": "taskId lipsă din răspuns TTS", "raw": data}))
        sys.exit(1)

    return task_id


def poll_until_done(key, task_id):
    start = time.time()
    while True:
        if time.time() - start > POLL_TIMEOUT:
            print(json.dumps({"error": f"Timeout TTS după {POLL_TIMEOUT}s. task_id={task_id}"}))
            sys.exit(1)

        try:
            resp = requests.get(
                f"{BASE_URL}/jobs/recordInfo",
                headers=headers(key),
                params={"taskId": task_id},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(json.dumps({"error": f"Polling TTS eșuat: {e}"}))
            sys.exit(1)

        data = resp.json().get("data", {})
        state = data.get("state") or data.get("status", "")

        if state == "success":
            return data
        elif state in ("failed", "error"):
            fail_msg = data.get("failMsg") or data.get("message", "motiv necunoscut")
            print(json.dumps({"error": f"TTS eșuat: {fail_msg}", "task_id": task_id}))
            sys.exit(1)

        time.sleep(POLL_INTERVAL)


def download_file(url, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def generate_voice(text, output_path, model, language, voice_id=None, speed=1.0):
    key = get_api_key()
    start_time = time.time()

    task_id = create_tts_task(key, text, model, language, voice_id, speed)
    record = poll_until_done(key, task_id)

    result_urls = record.get("resultUrls") or record.get("result_urls", [])
    if not result_urls:
        # Unele modele TTS returnează URL direct în câmpul "audioUrl" sau "url"
        audio_url = record.get("audioUrl") or record.get("url") or record.get("audio_url")
        if not audio_url:
            print(json.dumps({"error": "Niciun URL audio în răspuns", "record": record}))
            sys.exit(1)
        result_urls = [audio_url]

    try:
        download_file(result_urls[0], output_path)
    except Exception as e:
        print(json.dumps({"error": f"Descărcare audio eșuată: {e}", "task_id": task_id}))
        sys.exit(1)

    elapsed = round(time.time() - start_time, 1)
    credits = record.get("credits") or record.get("cost", 0)
    size_bytes = Path(output_path).stat().st_size

    print(json.dumps({
        "task_id": task_id,
        "output_path": str(output_path),
        "audio_url": result_urls[0],
        "cost_time_s": elapsed,
        "credits": credits,
        "size_bytes": size_bytes,
    }))


def main():
    parser = argparse.ArgumentParser(description="Generare voiceover ElevenLabs via kie.ai")
    parser.add_argument("text", nargs="?", help="Textul de citit")
    parser.add_argument("output_path", nargs="?", help="Calea fișierului output .mp3")
    parser.add_argument("--model", default="elevenlabs/text-to-speech-multilingual-v2",
                        help="Model TTS (default: elevenlabs/text-to-speech-multilingual-v2)")
    parser.add_argument("--language", default="ro", help="Codul limbii (default: ro)")
    parser.add_argument("--voice-id", help="ID voce ElevenLabs (opțional)")
    parser.add_argument("--speed", type=float, default=1.0, help="Viteza vorbirii 0.5-2.0 (default: 1.0)")
    parser.add_argument("--health", action="store_true", help="Verifică conexiunea API")

    args = parser.parse_args()

    if args.health:
        health_check(get_api_key())
        return

    if not args.text or not args.output_path:
        parser.print_help()
        sys.exit(1)

    generate_voice(
        text=args.text,
        output_path=args.output_path,
        model=args.model,
        language=args.language,
        voice_id=args.voice_id,
        speed=args.speed,
    )


if __name__ == "__main__":
    main()
