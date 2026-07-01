#!/usr/bin/env python3
"""
omni_combine.py — Combină footage original cu B-roll via FFmpeg.

Suportă trei moduri:
  split-screen  — footage pe dreapta (50%), B-roll pe stânga (50%)
  overlay       — B-roll peste footage cu opacitate redusă
  alternare     — footage și B-roll alternează la timestamps din transcript

Usage:
  python3 omni_combine.py <footage.mp4> <broll.mp4> <transcript.json> <output.mp4> [opțiuni]

Opțiuni:
  --mode MODE         split-screen, overlay sau alternare (default: split-screen)
  --opacity FLOAT     Opacitate B-roll la modul overlay (0.1-1.0, default: 0.5)
  --resolution RES    Rezoluție output: 1080x1920, 720x1280 (default: 1080x1920)
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
from pathlib import Path


def get_video_info(path):
    """Returnează (duration_s, width, height) via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, None, None

    try:
        data = json.loads(result.stdout)
        streams = data.get("streams", [{}])
        fmt = data.get("format", {})
        w = streams[0].get("width") if streams else None
        h = streams[0].get("height") if streams else None
        dur = float(fmt.get("duration", 0))
        return dur, w, h
    except (json.JSONDecodeError, IndexError, ValueError):
        return None, None, None


def split_screen(footage_path, broll_path, output_path, resolution, duration):
    """Footage dreapta, B-roll stânga, 50/50."""
    w_str, h_str = resolution.split("x")
    w, h = int(w_str), int(h_str)
    half_w = w // 2

    filter_complex = (
        f"[0:v]scale={half_w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={half_w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1[right];"
        f"[1:v]scale={half_w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={half_w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1[left];"
        f"[left][right]hstack=inputs=2[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(footage_path),
        "-i", str(broll_path),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        str(output_path),
    ]

    return subprocess.run(cmd, capture_output=True, text=True)


def overlay_mode(footage_path, broll_path, output_path, resolution, duration, opacity):
    """B-roll overlay peste footage cu transparență."""
    w_str, h_str = resolution.split("x")
    w, h = int(w_str), int(h_str)

    filter_complex = (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1[base];"
        f"[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black[overlay_raw];"
        f"[overlay_raw]format=rgba,colorchannelmixer=aa={opacity}[overlay];"
        f"[base][overlay]overlay=0:0:format=yuv420[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(footage_path),
        "-i", str(broll_path),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        str(output_path),
    ]

    return subprocess.run(cmd, capture_output=True, text=True)


def alternare_mode(footage_path, broll_path, output_path, resolution, duration, transcript_path):
    """Alternare footage/broll la timestamps din transcript, voce continuă."""
    w_str, h_str = resolution.split("x")
    w, h = int(w_str), int(h_str)

    try:
        with open(transcript_path, encoding="utf-8") as f:
            transcript = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return None, f"Transcript invalid: {e}"

    segments = transcript.get("segments", [])
    if not segments:
        return None, "Transcript fără segmente"

    # Strategie simplă: primele 2 segmente footage, segmentele 3+ alternează cu B-roll
    # Logica exactă: dacă segmentul e "pair" → B-roll, "impar" → footage
    # Implementare via FFmpeg concat cu trim per segment

    tmp_dir = Path(output_path).parent / "alternare_tmp"
    tmp_dir.mkdir(exist_ok=True)

    clip_files = []

    for i, seg in enumerate(segments):
        start = seg.get("start", 0.0)
        end = seg.get("end", start + 2.0)
        seg_dur = end - start
        clip_path = tmp_dir / f"seg_{i:03d}.mp4"

        if i % 2 == 0:
            # Footage real
            source = str(footage_path)
        else:
            # B-roll (trimmit din broll la aceeași poziție relativă)
            source = str(broll_path)

        scale_filter = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
        )

        cmd_seg = [
            "ffmpeg", "-y",
            "-i", str(footage_path),  # audio track mereu din footage
            "-i", source,             # video track alternat
            "-filter_complex",
            f"[1:v]{scale_filter}[v]",
            "-map", "[v]",
            "-map", "0:a",
            "-ss", str(start), "-t", str(seg_dur),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            str(clip_path),
        ]

        r = subprocess.run(cmd_seg, capture_output=True, text=True)
        if r.returncode != 0:
            continue

        clip_files.append(str(clip_path))

    if not clip_files:
        return None, "Niciun segment procesat"

    # Concatenare
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as list_file:
        for cf in clip_files:
            list_file.write(f"file '{cf}'\n")
        list_path = list_file.name

    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        "-t", str(duration),
        str(output_path),
    ]

    r = subprocess.run(cmd_concat, capture_output=True, text=True)
    os.unlink(list_path)

    return r, None


def main():
    parser = argparse.ArgumentParser(description="Combină footage cu B-roll via FFmpeg")
    parser.add_argument("footage_mp4", nargs="?", help="Footage original")
    parser.add_argument("broll_mp4", nargs="?", help="B-roll generat")
    parser.add_argument("transcript_json", nargs="?", help="Transcript cu timestamps (necesar pt. alternare)")
    parser.add_argument("output_mp4", nargs="?", help="Video output")
    parser.add_argument("--mode", default="split-screen",
                        choices=["split-screen", "overlay", "alternare"],
                        help="Modul de combinare (default: split-screen)")
    parser.add_argument("--opacity", type=float, default=0.5,
                        help="Opacitate B-roll la overlay (0.1-1.0, default: 0.5)")
    parser.add_argument("--resolution", default="1080x1920",
                        help="Rezoluție output WxH (default: 1080x1920)")

    args = parser.parse_args()

    if not all([args.footage_mp4, args.broll_mp4, args.transcript_json, args.output_mp4]):
        parser.print_help()
        sys.exit(1)

    footage_path = Path(args.footage_mp4)
    broll_path = Path(args.broll_mp4)
    output_path = Path(args.output_mp4)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not footage_path.exists():
        print(json.dumps({"error": f"Footage negăsit: {footage_path}"}))
        sys.exit(1)

    if not broll_path.exists():
        print(json.dumps({"error": f"B-roll negăsit: {broll_path}"}))
        sys.exit(1)

    duration, _, _ = get_video_info(footage_path)
    if not duration:
        print(json.dumps({"error": "Nu pot citi durata footage-ului via ffprobe"}))
        sys.exit(1)

    if args.mode == "split-screen":
        result = split_screen(footage_path, broll_path, output_path, args.resolution, duration)
        err_src = None
    elif args.mode == "overlay":
        result = overlay_mode(footage_path, broll_path, output_path, args.resolution, duration, args.opacity)
        err_src = None
    else:  # alternare
        result, err_src = alternare_mode(footage_path, broll_path, output_path, args.resolution, duration, args.transcript_json)

    if err_src:
        print(json.dumps({"error": err_src}))
        sys.exit(1)

    if result and result.returncode != 0:
        print(json.dumps({"error": f"FFmpeg eșuat", "stderr": result.stderr[-400:]}))
        sys.exit(1)

    if not output_path.exists():
        print(json.dumps({"error": "Output negăsit după execuție FFmpeg"}))
        sys.exit(1)

    size_bytes = output_path.stat().st_size
    print(json.dumps({
        "status": "ok",
        "output_path": str(output_path),
        "mode": args.mode,
        "resolution": args.resolution,
        "duration_s": round(duration, 1),
        "size_bytes": size_bytes,
    }))


if __name__ == "__main__":
    main()
