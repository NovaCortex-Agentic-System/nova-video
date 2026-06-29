#!/usr/bin/env python3
"""
kie_video.py — Generare video cu Seedance via KIE.ai pentru NOVA Video agent.

Seedance animează o imagine de referință (image-to-video). Funcționează și
ca text-to-video pur, dar calitatea e semnificativ mai bună cu o imagine de referință.

Usage:
  python3 kie_video.py "<prompt>" <output_path> [opțiuni]
  python3 kie_video.py --health

Opțiuni:
  --model MODEL           Model KIE.ai (default: seedance-1.5-pro)
  --duration SECONDS      Durata video în secunde (default: 5)
  --aspect RATIO          Aspect ratio: 9:16 sau 16:9 (default: 9:16)
  --reference PATH        Imagine de referință locală pentru image-to-video
  --reference-url URL     URL public al imaginii de referință
  --health                Verifică conexiunea API și returnează credite
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path

BASE_URL = "https://api.kie.ai/api/v1"
POLL_INTERVAL = 6
POLL_TIMEOUT = 600  # 10 minute


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
            print(json.dumps({"status": "ok", "credits": "indisponibil", "note": f"HTTP {resp.status_code}"}))
    except requests.exceptions.RequestException as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)


def upload_reference(key, image_path):
    upload_url = "https://kieai.redpandaai.co/api/file-stream-upload"
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                upload_url,
                headers={"Authorization": f"Bearer {key}"},
                files={"file": (Path(image_path).name, f)},
                timeout=60,
            )
        resp.raise_for_status()
        data = resp.json()
        url = data.get("url") or data.get("data", {}).get("url")
        if not url:
            print(json.dumps({"error": "URL lipsă din răspunsul de upload", "raw": data}))
            sys.exit(1)
        return url
    except FileNotFoundError:
        print(json.dumps({"error": f"Fișier referință negăsit: {image_path}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Upload referință eșuat: {e}"}))
        sys.exit(1)


def create_task(key, prompt, model, duration, aspect_ratio, reference_url=None):
    payload = {
        "model": model,
        "input": {
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        },
    }
    if reference_url:
        payload["input"]["image_url"] = reference_url

    resp = requests.post(
        f"{BASE_URL}/jobs/createTask",
        headers=headers(key),
        json=payload,
        timeout=30,
    )

    if resp.status_code != 200:
        err = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
        print(json.dumps({"error": f"createTask eșuat HTTP {resp.status_code}", "detail": err}))
        sys.exit(1)

    data = resp.json()
    task_id = data.get("data", {}).get("taskId") or data.get("taskId")
    if not task_id:
        print(json.dumps({"error": "taskId lipsă din răspuns", "raw": data}))
        sys.exit(1)

    return task_id


def poll_until_done(key, task_id):
    start = time.time()
    while True:
        if time.time() - start > POLL_TIMEOUT:
            print(json.dumps({"error": f"Timeout după {POLL_TIMEOUT}s. task_id={task_id}"}))
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
            print(json.dumps({"error": f"Polling eșuat: {e}", "task_id": task_id}))
            sys.exit(1)

        data = resp.json().get("data", {})
        state = data.get("state") or data.get("status", "")

        if state == "success":
            return data
        elif state in ("failed", "error"):
            fail_msg = data.get("failMsg") or data.get("message", "motiv necunoscut")
            print(json.dumps({"error": f"Generare eșuată: {fail_msg}", "task_id": task_id}))
            sys.exit(1)

        time.sleep(POLL_INTERVAL)


def download_file(url, output_path):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def generate(prompt, output_path, model, duration, aspect_ratio, reference_path=None, reference_url=None):
    key = get_api_key()
    start_time = time.time()

    if reference_path and not reference_url:
        reference_url = upload_reference(key, reference_path)

    task_id = create_task(key, prompt, model, duration, aspect_ratio, reference_url)
    record = poll_until_done(key, task_id)

    result_urls = record.get("resultUrls") or record.get("result_urls", [])
    if not result_urls:
        print(json.dumps({"error": "Niciun URL de descărcare în răspuns", "record": record}))
        sys.exit(1)

    try:
        download_file(result_urls[0], output_path)
    except Exception as e:
        print(json.dumps({"error": f"Descărcare eșuată: {e}", "task_id": task_id}))
        sys.exit(1)

    elapsed = round(time.time() - start_time, 1)
    credits = record.get("credits") or record.get("cost", 0)
    size_bytes = Path(output_path).stat().st_size

    print(json.dumps({
        "task_id": task_id,
        "output_path": str(output_path),
        "video_url": result_urls[0],
        "cost_time_s": elapsed,
        "credits": credits,
        "size_bytes": size_bytes,
    }))


def main():
    parser = argparse.ArgumentParser(description="Generare video Seedance via kie.ai")
    parser.add_argument("prompt", nargs="?", help="Promptul de animație")
    parser.add_argument("output_path", nargs="?", help="Calea fișierului output .mp4")
    parser.add_argument("--model", default="seedance-1.5-pro", help="Model KIE.ai (default: seedance-1.5-pro)")
    parser.add_argument("--duration", type=int, default=5, help="Durată în secunde (default: 5)")
    parser.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"], help="Aspect ratio")
    parser.add_argument("--reference", help="Cale locală imagine de referință")
    parser.add_argument("--reference-url", dest="reference_url", help="URL public imagine de referință")
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
        reference_path=args.reference,
        reference_url=args.reference_url,
    )


if __name__ == "__main__":
    main()
