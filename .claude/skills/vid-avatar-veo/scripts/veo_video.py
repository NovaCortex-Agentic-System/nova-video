#!/usr/bin/env python3
"""
veo_video.py — Generare video via Google Veo (Gemini API) pentru NOVA Video agent.

Apelează REST API direct (nu SDK google-genai). Returnează video cu audio nativ
dacă promptul menționează vorbire sau muzică.

Usage:
  python3 veo_video.py "<prompt>" <output_path> [opțiuni]
  python3 veo_video.py --health

Opțiuni:
  --model MODEL       Model Veo (default: veo-3.1-lite-generate-preview)
  --duration SECONDS  Durata video: 4, 6 sau 8 (default: 8)
  --aspect RATIO      Aspect ratio: 9:16 sau 16:9 (default: 9:16)
  --resolution RES    Rezoluție: 720p sau 1080p (default: 720p)
  --reference PATH    Imagine de referință locală (opțional, activează image-to-video)
  --health            Verifică conexiunea API
"""

import os
import sys
import json
import time
import base64
import argparse
import requests
from pathlib import Path

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
POLL_INTERVAL = 10
POLL_TIMEOUT = 600  # 10 minute


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
            models = resp.json().get("models", [])
            veo_models = [m["name"] for m in models if "veo" in m.get("name", "").lower()]
            print(json.dumps({"status": "ok", "veo_models_available": veo_models}))
        elif resp.status_code == 400:
            print(json.dumps({"status": "error", "error": "Cheie API invalidă (400)"}))
            sys.exit(1)
        else:
            print(json.dumps({"status": "ok", "note": f"API accesibil, HTTP {resp.status_code}"}))
    except requests.exceptions.RequestException as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)


def submit_generation(key, prompt, model, duration, aspect_ratio, resolution, reference_path=None):
    instances = [{"prompt": prompt}]

    if reference_path:
        try:
            with open(reference_path, "rb") as f:
                img_bytes = f.read()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            suffix = Path(reference_path).suffix.lower()
            mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
            instances[0]["image"] = {"bytesBase64Encoded": img_b64, "mimeType": mime}
        except FileNotFoundError:
            print(json.dumps({"error": f"Fișier referință negăsit: {reference_path}"}))
            sys.exit(1)

    payload = {
        "instances": instances,
        "parameters": {
            "durationSeconds": duration,
            "aspectRatio": aspect_ratio,
            "outputMimeType": "video/mp4",
            "resolution": resolution,
        },
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/models/{model}:predictLongRunning",
            params={"key": key},
            json=payload,
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": f"submit_generation eșuat (rețea): {e}"}))
        sys.exit(1)

    if resp.status_code not in (200, 201):
        try:
            err = resp.json()
        except Exception:
            err = resp.text
        print(json.dumps({"error": f"Generare respinsă HTTP {resp.status_code}", "detail": err}))
        sys.exit(1)

    data = resp.json()
    operation_name = data.get("name")
    if not operation_name:
        print(json.dumps({"error": "operation name lipsă din răspuns", "raw": data}))
        sys.exit(1)

    return operation_name


def poll_operation(key, operation_name):
    # operation_name e de forma "operations/xxx" sau full path
    op_id = operation_name.split("/")[-1] if "/" in operation_name else operation_name
    start = time.time()

    while True:
        if time.time() - start > POLL_TIMEOUT:
            print(json.dumps({"error": f"Timeout după {POLL_TIMEOUT}s. operation={operation_name}"}))
            sys.exit(1)

        try:
            resp = requests.get(
                f"{BASE_URL}/operations/{op_id}",
                params={"key": key},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(json.dumps({"error": f"Polling eșuat: {e}", "operation": operation_name}))
            sys.exit(1)

        data = resp.json()

        if data.get("error"):
            err = data["error"]
            print(json.dumps({"error": f"Operație eșuată: {err.get('message', err)}", "operation": operation_name}))
            sys.exit(1)

        if data.get("done"):
            return data.get("response", {})

        time.sleep(POLL_INTERVAL)


def download_video_from_response(response, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    videos = response.get("videos") or response.get("predictions", [])
    if not videos:
        print(json.dumps({"error": "Niciun video în răspunsul final", "response": response}))
        sys.exit(1)

    video = videos[0]

    # Cazul 1: video e stocat ca bytes base64
    if video.get("bytesBase64Encoded"):
        video_bytes = base64.b64decode(video["bytesBase64Encoded"])
        with open(output_path, "wb") as f:
            f.write(video_bytes)
        return

    # Cazul 2: video e disponibil la un URI (GCS sau URL public)
    uri = video.get("uri") or video.get("url")
    if uri:
        try:
            resp = requests.get(uri, stream=True, timeout=120)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return
        except requests.exceptions.RequestException as e:
            print(json.dumps({"error": f"Descărcare video de la URI eșuată: {e}", "uri": uri}))
            sys.exit(1)

    print(json.dumps({"error": "Video fără bytesBase64Encoded și fără URI", "video_keys": list(video.keys())}))
    sys.exit(1)


def generate(prompt, output_path, model, duration, aspect_ratio, resolution, reference_path=None):
    key = get_api_key()
    start_time = time.time()

    operation_name = submit_generation(key, prompt, model, duration, aspect_ratio, resolution, reference_path)
    response = poll_operation(key, operation_name)
    download_video_from_response(response, output_path)

    elapsed = round(time.time() - start_time, 1)
    size_bytes = Path(output_path).stat().st_size

    print(json.dumps({
        "status": "ok",
        "output_path": str(output_path),
        "operation_name": operation_name,
        "duration_s": elapsed,
        "size_bytes": size_bytes,
    }))


def main():
    parser = argparse.ArgumentParser(description="Generare video via Google Veo (Gemini API)")
    parser.add_argument("prompt", nargs="?", help="Promptul video")
    parser.add_argument("output_path", nargs="?", help="Calea fișierului output .mp4")
    parser.add_argument("--model", default="veo-3.1-lite-generate-preview",
                        help="Model Veo (default: veo-3.1-lite-generate-preview)")
    parser.add_argument("--duration", type=int, default=8, choices=[4, 6, 8],
                        help="Durată în secunde: 4, 6 sau 8 (default: 8)")
    parser.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"],
                        help="Aspect ratio (default: 9:16)")
    parser.add_argument("--resolution", default="720p", choices=["720p", "1080p"],
                        help="Rezoluție (default: 720p)")
    parser.add_argument("--reference", help="Cale locală imagine de referință (activează image-to-video)")
    parser.add_argument("--health", action="store_true", help="Verifică conexiunea API")

    args = parser.parse_args()

    if args.health:
        health_check(get_api_key())
        return

    if not args.prompt or not args.output_path:
        parser.print_help()
        sys.exit(1)

    generate(
        prompt=args.prompt,
        output_path=args.output_path,
        model=args.model,
        duration=args.duration,
        aspect_ratio=args.aspect,
        resolution=args.resolution,
        reference_path=args.reference,
    )


if __name__ == "__main__":
    main()
