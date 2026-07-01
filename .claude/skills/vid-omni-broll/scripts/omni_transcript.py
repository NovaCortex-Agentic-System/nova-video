#!/usr/bin/env python3
"""
omni_transcript.py — Extrage transcript cu timestamps din audio via Gemini Flash.

Uploadează fișierul audio la Gemini File API, trimite cerere de transcriere
cu timestamps la nivel de frază, returnează JSON structurat.

Usage:
  python3 omni_transcript.py <audio.mp3> <output.json>
  python3 omni_transcript.py --health

Output JSON:
  {
    "segments": [
      {"start": 0.0, "end": 3.2, "text": "Salut, azi vorbim despre AI."},
      ...
    ],
    "duration_total": 45.1,
    "language": "ro"
  }
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
MODEL = "gemini-2.0-flash"


def get_api_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print(json.dumps({"error": "GEMINI_API_KEY lipsă din environment"}))
        sys.exit(1)
    return key


def health_check(key):
    try:
        resp = requests.get(
            f"{BASE_URL}/models",
            params={"key": key},
            timeout=10,
        )
        if resp.status_code == 200:
            print(json.dumps({"status": "ok", "model": MODEL}))
        else:
            print(json.dumps({"status": "error", "http": resp.status_code}))
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)


def upload_audio(key, audio_path):
    audio_path = Path(audio_path)
    if not audio_path.exists():
        print(json.dumps({"error": f"Fișier audio negăsit: {audio_path}"}))
        sys.exit(1)

    suffix = audio_path.suffix.lower()
    mime_map = {".mp3": "audio/mpeg", ".mp4": "audio/mp4", ".wav": "audio/wav", ".m4a": "audio/mp4", ".ogg": "audio/ogg"}
    mime_type = mime_map.get(suffix, "audio/mpeg")

    file_size = audio_path.stat().st_size
    init_headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(file_size),
        "X-Goog-Upload-Header-Content-Type": mime_type,
        "Content-Type": "application/json",
    }
    init_payload = {"file": {"display_name": audio_path.name}}

    try:
        init_resp = requests.post(
            f"{BASE_URL}/upload/files",
            params={"key": key},
            headers=init_headers,
            json=init_payload,
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"Upload init eșuat: {e}"}))
        sys.exit(1)

    if init_resp.status_code not in (200, 201):
        print(json.dumps({"error": f"Upload init HTTP {init_resp.status_code}", "detail": init_resp.text}))
        sys.exit(1)

    upload_url = init_resp.headers.get("X-Goog-Upload-URL")
    if not upload_url:
        print(json.dumps({"error": "Upload URL lipsă din răspuns"}))
        sys.exit(1)

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    try:
        upload_resp = requests.post(
            upload_url,
            headers={
                "X-Goog-Upload-Command": "upload, finalize",
                "X-Goog-Upload-Offset": "0",
                "Content-Type": mime_type,
            },
            data=audio_bytes,
            timeout=120,
        )
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"Upload bytes eșuat: {e}"}))
        sys.exit(1)

    if upload_resp.status_code not in (200, 201):
        print(json.dumps({"error": f"Upload HTTP {upload_resp.status_code}", "detail": upload_resp.text}))
        sys.exit(1)

    file_data = upload_resp.json().get("file", {})
    file_uri = file_data.get("uri")
    file_name = file_data.get("name")

    if not file_uri:
        print(json.dumps({"error": "URI lipsă din răspuns upload", "raw": upload_resp.json()}))
        sys.exit(1)

    # Așteptăm procesarea fișierului
    max_wait = 60
    waited = 0
    while waited < max_wait:
        state_resp = requests.get(
            f"{BASE_URL}/{file_name}",
            params={"key": key},
            timeout=15,
        )
        state = state_resp.json().get("state", "")
        if state == "ACTIVE":
            break
        if state == "FAILED":
            print(json.dumps({"error": "Fișierul audio a eșuat la procesare pe Gemini"}))
            sys.exit(1)
        time.sleep(5)
        waited += 5

    return file_uri, mime_type


def transcribe(key, file_uri, mime_type):
    prompt = """Transcrie înregistrarea audio cu timestamps precise la nivel de frază/propoziție.
Returnează STRICT un JSON valid (fără text extra, fără markdown) în formatul:
{
  "segments": [
    {"start": 0.0, "end": 3.2, "text": "textul exact vorbit"},
    {"start": 3.2, "end": 6.8, "text": "continuare"},
    ...
  ],
  "duration_total": 45.1,
  "language": "ro"
}
Reguli:
- start/end sunt în secunde (număr zecimal)
- Nu combina propoziții lungi — max 10 cuvinte per segment
- Timestamps exacte, nu rotunjite
- Fără punctuație la final de segment dacă nu există în original
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"file_data": {"mime_type": mime_type, "file_uri": file_uri}},
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096},
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/models/{MODEL}:generateContent",
            params={"key": key},
            json=payload,
            timeout=120,
        )
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"Transcriere eșuată (rețea): {e}"}))
        sys.exit(1)

    if resp.status_code != 200:
        print(json.dumps({"error": f"Transcriere HTTP {resp.status_code}", "detail": resp.text[:500]}))
        sys.exit(1)

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        print(json.dumps({"error": "Niciun candidat în răspuns Gemini", "raw": data}))
        sys.exit(1)

    raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")

    # Curăță markdown dacă Gemini a adăugat ```json
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:])
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"JSON invalid în răspunsul Gemini: {e}", "raw": raw_text[:500]}))
        sys.exit(1)

    segments = parsed.get("segments", [])
    if not segments:
        print(json.dumps({"error": "Niciun segment în transcriere — audio fără voce?"}))
        sys.exit(1)

    return parsed


def main():
    parser = argparse.ArgumentParser(description="Transcriere audio cu timestamps via Gemini Flash")
    parser.add_argument("audio_path", nargs="?", help="Calea fișierului audio")
    parser.add_argument("output_json", nargs="?", help="Calea fișierului JSON output")
    parser.add_argument("--health", action="store_true", help="Verifică conexiunea API")

    args = parser.parse_args()
    key = get_api_key()

    if args.health:
        health_check(key)
        return

    if not args.audio_path or not args.output_json:
        parser.print_help()
        sys.exit(1)

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    file_uri, mime_type = upload_audio(key, args.audio_path)
    result = transcribe(key, file_uri, mime_type)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    seg_count = len(result.get("segments", []))
    duration = result.get("duration_total", 0)
    print(json.dumps({
        "status": "ok",
        "output_path": str(output_path),
        "segments": seg_count,
        "duration_total": duration,
        "language": result.get("language", "?"),
    }))


if __name__ == "__main__":
    main()
