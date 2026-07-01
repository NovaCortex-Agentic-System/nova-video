#!/usr/bin/env python3
"""
omni_broll.py — Generează B-roll animat din transcript via Google Veo 3.1.

Citește transcript cu timestamps, grupează segmentele în blocuri de ~6s,
generează câte un clip Veo per bloc cu stil vizual definit, concatenează
clipurile într-un singur fișier broll.mp4.

Usage:
  python3 omni_broll.py <transcript.json> <broll.mp4> [opțiuni]

Opțiuni:
  --style STYLE           Stil vizual: kinetic-typography, paper-scrapbook,
                          clean-minimal, custom (default: kinetic-typography)
  --custom-style TEXT     Descrierea stilului custom (când --style custom)
  --duration SECONDS      Durata fiecărui clip Veo: 6 sau 8 (default: 6)
  --model MODEL           Model Veo (default: veo-3.1-lite-generate-preview)
  --aspect RATIO          Aspect ratio: 9:16 sau 16:9 (default: 9:16)
"""

import os
import sys
import json
import time
import base64
import argparse
import subprocess
import requests
import tempfile
from pathlib import Path

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
POLL_INTERVAL = 10
POLL_TIMEOUT = 600

STYLE_PROMPTS = {
    "kinetic-typography": (
        "Bold kinetic typography animation on solid black background. "
        "Massive white text appears word by word, each word punches in with scale animation. "
        "The text reads: \"{text}\". "
        "High contrast, no decorations, professional typographic style. "
        "Duration matches the spoken phrase timing."
    ),
    "paper-scrapbook": (
        "Paper scrapbook collage animation. The text \"{text}\" appears on torn paper texture, "
        "newspaper cutout aesthetic with halftone dots, acid yellow and black color palette. "
        "Rough textures, vintage print style, words appear as if cut and pasted. "
        "Kinetic, energetic movement."
    ),
    "clean-minimal": (
        "Clean minimal animation on white background. The text \"{text}\" fades in with "
        "elegant typography, dark charcoal color. Simple and professional. "
        "Subtle scale or slide-in animation. No decorations."
    ),
}


def get_api_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print(json.dumps({"error": "GEMINI_API_KEY lipsă din environment"}))
        sys.exit(1)
    return key


def load_transcript(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"Transcript invalid: {e}"}))
        sys.exit(1)

    segments = data.get("segments", [])
    if not segments:
        print(json.dumps({"error": "Transcript fără segmente"}))
        sys.exit(1)

    return segments, data.get("duration_total", 0)


def group_segments(segments, target_duration=6.0):
    """Grupează segmentele în blocuri de ~target_duration secunde."""
    groups = []
    current_group = []
    current_start = None
    current_end = 0.0

    for seg in segments:
        start = seg.get("start", 0.0)
        end = seg.get("end", start + 1.0)
        text = seg.get("text", "").strip()

        if not text:
            continue

        if current_start is None:
            current_start = start

        current_group.append(text)
        current_end = end

        if current_end - current_start >= target_duration:
            groups.append({
                "start": current_start,
                "end": current_end,
                "text": " ".join(current_group),
            })
            current_group = []
            current_start = None
            current_end = 0.0

    # Ultimul grup rămas
    if current_group and current_start is not None:
        groups.append({
            "start": current_start,
            "end": current_end,
            "text": " ".join(current_group),
        })

    return groups


def build_prompt(text, style, custom_style=None):
    if style == "custom" and custom_style:
        return custom_style.format(text=text)

    template = STYLE_PROMPTS.get(style, STYLE_PROMPTS["kinetic-typography"])
    return template.format(text=text)


def submit_veo(key, prompt, model, duration, aspect_ratio):
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "durationSeconds": duration,
            "aspectRatio": aspect_ratio,
            "outputMimeType": "video/mp4",
            "resolution": "720p",
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
        return None, f"Request eșuat: {e}"

    if resp.status_code not in (200, 201):
        return None, f"HTTP {resp.status_code}: {resp.text[:200]}"

    operation_name = resp.json().get("name")
    if not operation_name:
        return None, "operation name lipsă"

    return operation_name, None


def poll_operation(key, operation_name):
    op_id = operation_name.split("/")[-1]
    start = time.time()

    while True:
        if time.time() - start > POLL_TIMEOUT:
            return None, f"Timeout {POLL_TIMEOUT}s"

        try:
            resp = requests.get(
                f"{BASE_URL}/operations/{op_id}",
                params={"key": key},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            return None, f"Polling eșuat: {e}"

        data = resp.json()
        if data.get("error"):
            return None, f"Operație eșuată: {data['error'].get('message', '')}"

        if data.get("done"):
            return data.get("response", {}), None

        time.sleep(POLL_INTERVAL)


def save_video_from_response(response, output_path):
    videos = response.get("videos") or response.get("predictions", [])
    if not videos:
        return f"Niciun video în răspuns: {list(response.keys())}"

    video = videos[0]

    if video.get("bytesBase64Encoded"):
        video_bytes = base64.b64decode(video["bytesBase64Encoded"])
        with open(output_path, "wb") as f:
            f.write(video_bytes)
        return None

    uri = video.get("uri") or video.get("url")
    if uri:
        try:
            r = requests.get(uri, stream=True, timeout=120)
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return None
        except Exception as e:
            return f"Descărcare URI eșuată: {e}"

    return f"Video fără bytes și fără URI. Chei: {list(video.keys())}"


def concatenate_clips(clip_paths, output_path, aspect_ratio):
    """Concatenează clipurile video cu FFmpeg."""
    if not clip_paths:
        return "Nicio cale clip furnizată"

    if len(clip_paths) == 1:
        import shutil
        shutil.copy(clip_paths[0], output_path)
        return None

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as list_file:
        for cp in clip_paths:
            list_file.write(f"file '{cp}'\n")
        list_path = list_file.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(list_path)

    if result.returncode != 0:
        return f"FFmpeg concat eșuat: {result.stderr[-300:]}"

    return None


def main():
    parser = argparse.ArgumentParser(description="Generare B-roll din transcript via Veo 3.1")
    parser.add_argument("transcript_json", nargs="?", help="Calea transcript.json")
    parser.add_argument("output_mp4", nargs="?", help="Calea broll.mp4 output")
    parser.add_argument("--style", default="kinetic-typography",
                        choices=["kinetic-typography", "paper-scrapbook", "clean-minimal", "custom"],
                        help="Stilul vizual (default: kinetic-typography)")
    parser.add_argument("--custom-style", help="Prompt custom pentru stil (când --style custom)")
    parser.add_argument("--duration", type=int, default=6, choices=[4, 6, 8],
                        help="Durată clip Veo în secunde (default: 6)")
    parser.add_argument("--model", default="veo-3.1-lite-generate-preview",
                        help="Model Veo (default: veo-3.1-lite-generate-preview)")
    parser.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"],
                        help="Aspect ratio (default: 9:16)")

    args = parser.parse_args()

    if not args.transcript_json or not args.output_mp4:
        parser.print_help()
        sys.exit(1)

    key = get_api_key()
    segments, total_duration = load_transcript(args.transcript_json)
    groups = group_segments(segments, target_duration=args.duration)

    output_path = Path(args.output_mp4)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_dir = output_path.parent / "broll_clips"
    tmp_dir.mkdir(exist_ok=True)

    clip_paths = []
    errors = []
    total_cost = 0.0

    cost_per_sec = {"veo-3.1-lite-generate-preview": 0.05, "veo-3.1-fast-generate-preview": 0.10, "veo-3.1-generate-preview": 0.40}
    cps = cost_per_sec.get(args.model, 0.05)

    for i, group in enumerate(groups):
        prompt = build_prompt(group["text"], args.style, args.custom_style)
        clip_path = str(tmp_dir / f"clip_{i:03d}.mp4")

        op_name, err = submit_veo(key, prompt, args.model, args.duration, args.aspect)
        if err:
            errors.append(f"Clip {i}: {err}")
            continue

        response, err = poll_operation(key, op_name)
        if err:
            errors.append(f"Clip {i} poll: {err}")
            continue

        err = save_video_from_response(response, clip_path)
        if err:
            errors.append(f"Clip {i} save: {err}")
            continue

        clip_paths.append(clip_path)
        total_cost += args.duration * cps

    if not clip_paths:
        print(json.dumps({"error": "Niciun clip generat", "errors": errors}))
        sys.exit(1)

    concat_err = concatenate_clips(clip_paths, output_path, args.aspect)
    if concat_err:
        print(json.dumps({"error": f"Concatenare eșuată: {concat_err}"}))
        sys.exit(1)

    size_bytes = output_path.stat().st_size
    print(json.dumps({
        "status": "ok",
        "output_path": str(output_path),
        "clips_generated": len(clip_paths),
        "clips_failed": len(errors),
        "estimated_cost_usd": round(total_cost, 3),
        "size_bytes": size_bytes,
        "errors": errors if errors else None,
    }))


if __name__ == "__main__":
    main()
