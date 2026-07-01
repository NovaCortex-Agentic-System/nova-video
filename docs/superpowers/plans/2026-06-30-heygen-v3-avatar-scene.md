# HeyGen v3 Avatar în Scenă — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adaugă la agentul NOVA Video capacitatea de a crea avatare persistente din fotografie și de a genera video-uri cu avatarul plasat într-o scenă reală (fundal imagine/video + mișcare naturală + voce română), migrând pe API-ul HeyGen v3 corect.

**Architecture:** Un script Python centralizat (`heygen_v3.py`) înlocuiește `heygen_video.py` și expune toate operațiile v3 (creare avatar, listare voci cu filtru limbă, generare video cu scenă). Două skill-uri consumă scriptul: skill-ul existent `vid-avatar-heygen` (updatat) și un skill nou `vid-avatar-heygen-create` pentru onboarding avatar.

**Tech Stack:** Python 3, `requests`, HeyGen REST API v3 (`https://api.heygen.com`), variabilă `HEYGEN_API_KEY` din `.env` agent.

---

## File Structure

```
nova-video/.claude/skills/
├── vid-avatar-heygen/
│   ├── SKILL.md                        MODIFY — adaugă scenă, voce română, referință heygen_v3.py
│   └── scripts/
│       ├── heygen_video.py             KEEP — nu șterge, rămâne pentru compatibilitate
│       └── heygen_v3.py               CREATE — wrapper complet pe API v3
├── vid-avatar-heygen-create/          CREATE — skill nou pentru creare avatar persistent
│   └── SKILL.md
```

---

## Task 1: Creează `heygen_v3.py` — wrapper API v3

**Files:**
- Create: `.claude/skills/vid-avatar-heygen/scripts/heygen_v3.py`

- [ ] **Step 1: Scrie scriptul complet**

Creează fișierul `.claude/skills/vid-avatar-heygen/scripts/heygen_v3.py` cu conținutul de mai jos:

```python
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
    try:
        resp = requests.get(f"{BASE_URL}/v1/user/remaining.quota", headers=hdrs(key), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(json.dumps({"status": "ok", "quota": data.get("data", data)}))
        elif resp.status_code == 401:
            print(json.dumps({"status": "error", "error": "Cheie API invalidă (401)"}))
            sys.exit(1)
        else:
            print(json.dumps({"status": "ok", "note": f"HTTP {resp.status_code}"}))
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
            {"id": a.get("avatar_id") or a.get("id", ""), "name": a.get("avatar_name") or a.get("name", "")}
            for a in raw
        ]
        print(json.dumps({"status": "ok", "count": len(avatars), "avatars": avatars}))
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def list_voices(key, language=None):
    """Listează vocile, opțional filtrate după limbă (ex: 'Romanian')."""
    params = {}
    if language:
        params["language"] = language
    try:
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
        print(json.dumps({"status": "ok", "count": len(voices), "voices": voices}))
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Avatar creation
# ---------------------------------------------------------------------------

def create_photo_avatar(key, name, photo_url):
    """
    Creează un avatar persistent din fotografie.
    Returnează group_id și look_id (avatar_id pentru generare video).
    """
    payload = {
        "type": "photo",
        "name": name,
        "file": {"type": "url", "url": photo_url},
    }
    try:
        resp = requests.post(f"{BASE_URL}/v3/avatars", headers=hdrs(key), json=payload, timeout=30)
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
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Video generation
# ---------------------------------------------------------------------------

def build_background(color=None, image_url=None):
    """Construiește obiectul background pentru payload."""
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
        resp = requests.post(f"{BASE_URL}/v3/videos", headers=hdrs(key), json=payload, timeout=30)
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
            resp = requests.get(f"{BASE_URL}/v3/videos/{video_id}", headers=hdrs(key), timeout=15)
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

    parser.add_argument("--health", action="store_true")
    parser.add_argument("--list-avatars", action="store_true")
    parser.add_argument("--list-voices", action="store_true")
    parser.add_argument("--language", default=None, help="Filtru limbă voci (ex: Romanian)")
    parser.add_argument("--create-avatar", action="store_true")
    parser.add_argument("--avatar-name", default=None)
    parser.add_argument("--avatar-photo-url", default=None)

    subparsers = parser.add_subparsers(dest="command")
    gen = subparsers.add_parser("generate")
    gen.add_argument("script_text")
    gen.add_argument("output_path")
    gen.add_argument("--avatar", dest="avatar_id", required=True)
    gen.add_argument("--voice", dest="voice_id", required=True)
    gen.add_argument("--aspect", default="9:16", choices=["9:16", "16:9", "1:1", "4:5", "5:4"])
    gen.add_argument("--resolution", default="1080p", choices=["1080p", "720p", "4k"])
    gen.add_argument("--background-color", default=None, help="Hex color ex: #1a1a2e")
    gen.add_argument("--background-image", default=None, help="URL imagine fundal")
    gen.add_argument("--motion-prompt", default=None)
    gen.add_argument("--expressiveness", default=None, choices=["high", "medium", "low"])
    gen.add_argument("--locale", default=None, help="BCP-47 ex: ro-RO")

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

    parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verifică sintaxa Python**

```bash
cd "/Users/danmitrut/Desktop/CURS AGENȚI/biblioteca-agenti/nova-video"
python3 -m py_compile .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py && echo "OK"
```

Expected: `OK`

- [ ] **Step 3: Test --health**

```bash
cd "/Users/danmitrut/Desktop/CURS AGENȚI/biblioteca-agenti/nova-video"
set -a; source .env; set +a
python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py --health
```

Expected: JSON cu `"status": "ok"` și informații quota. Dacă returnează 401 → cheia API lipsește sau e invalidă în `.env`.

- [ ] **Step 4: Test --list-voices Romanian**

```bash
python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py --list-voices --language Romanian
```

Expected: JSON cu `"status": "ok"`, `"voices": [...]`. Lista poate fi goală dacă HeyGen nu are voci RO specifice — în acest caz `"count": 0` e valid, agentul va folosi voce EN cu `locale: "ro-RO"`.

- [ ] **Step 5: Test --list-avatars**

```bash
python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py --list-avatars
```

Expected: JSON cu `"status": "ok"`, `"avatars": [...]` cu cel puțin 1 avatar.

---

## Task 2: Creează skill `vid-avatar-heygen-create`

**Files:**
- Create: `.claude/skills/vid-avatar-heygen-create/SKILL.md`

- [ ] **Step 1: Creează directorul și SKILL.md**

Creează fișierul `.claude/skills/vid-avatar-heygen-create/SKILL.md`:

```markdown
---
name: vid-avatar-heygen-create
description: "Creează un avatar persistent din fotografie via HeyGen API. Rulează o singură dată per persoană. Avatarul rezultat (look_id) se salvează în knowledge/brand-video.md și se reutilizează la orice video ulterior."
triggers:
  - "creează avatar"
  - "avatar din poză"
  - "avatar persistent"
  - "înregistrează avatar"
  - "photo avatar heygen"
secrets_required:
  - HEYGEN_API_KEY
context_loads:
  - knowledge/brand-video.md
outputs:
  - look_id salvat în knowledge/brand-video.md
runtime_dependencies:
  - python3
  - requests (pip install requests)
---

# Skill: Creare Avatar Persistent HeyGen

Acest skill creează un avatar persistent (Photo Avatar) din o fotografie și îl salvează în catalogul de branduri pentru reutilizare la toate video-urile viitoare.

## Pas 0: Verifică dacă avatarul există deja

Citește `knowledge/brand-video.md`. Dacă brandul menționat are deja un câmp `heygen_look_id` completat, NU crea un avatar nou.

Mesaj utilizator:
> "Brandul [NUME] are deja avatarul [ID]. Îl folosim pe acesta sau vrei să creezi unul nou cu o altă fotografie?"

Dacă vrea să creeze unul nou, continuă la Pas 1.

## Pas 1: Primește fotografia

Cere utilizatorului:
> "Trimite fotografia pentru avatar. Cerințe HeyGen:
> - Format: JPG sau PNG
> - Față vizibilă, față spre cameră, fără ochelari de soare
> - Fundal curat (alb sau uniform)
> - Rezoluție minimă: 512×512 px
>
> Poți trimite un URL public sau poți face upload la fișier prin Telegram."

Dacă utilizatorul trimite un URL → continuă cu URL-ul.
Dacă utilizatorul trimite un fișier local via Telegram → fotografia ajunge la `local_file:` în mesaj. Uploadează-o pe Zernio via `tool-video-upload` pentru a obține un URL public, apoi continuă.

## Pas 2: Confirmă și cere denumirea

Cere:
> "Cum denumim avatarul? (ex: 'Dan Mitruț — Trainer', 'Maria — Sales')"

**ÎNCHEIE TURA** — nu continua fără răspuns.

## Pas 3: Creează avatarul

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a

python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py \
  --create-avatar \
  --avatar-name "<DENUMIRE>" \
  --avatar-photo-url "<URL_FOTOGRAFIE>"
```

Parsează JSON-ul returnat:
- Dacă conține `"error"` → raportează eroarea și oprește.
- Dacă `"status": "ok"` → extrage `look_id` și `group_id`.

## Pas 4: Salvează în catalog

```bash
cat >> "${CTX_AGENT_DIR}/knowledge/brand-video.md" << EOF

### Avatar: <DENUMIRE>
- heygen_look_id: <LOOK_ID>
- heygen_group_id: <GROUP_ID>
- creat: $(date -u +%Y-%m-%d)
EOF
```

Raportează utilizatorului:
> "Avatar creat cu succes!
> - Nume: [DENUMIRE]
> - look_id: [LOOK_ID]
> - Salvat în catalogul de branduri.
>
> Poți folosi acest avatar în orice video cu comanda 'video cu avatar [DENUMIRE] în scenă'."

## Rules

- Nu crea un avatar dacă brandul are deja un look_id în catalog
- Fotografia trebuie să fie un URL public înainte de a apela API-ul
- Salvează ÎNTOTDEAUNA look_id în knowledge/brand-video.md după creare reușită
- Nu continua la Pas 3 fără denumire confirmată de utilizator
```

- [ ] **Step 2: Verifică că fișierul e valid Markdown cu frontmatter**

```bash
head -10 "/Users/danmitrut/Desktop/CURS AGENȚI/biblioteca-agenti/nova-video/.claude/skills/vid-avatar-heygen-create/SKILL.md"
```

Expected: primele linii sunt `---`, `name: vid-avatar-heygen-create`, etc.

---

## Task 3: Actualizează `vid-avatar-heygen/SKILL.md` cu suport scenă și voce română

**Files:**
- Modify: `.claude/skills/vid-avatar-heygen/SKILL.md`

- [ ] **Step 1: Rescrie SKILL.md cu v3, scenă și română**

Înlocuiește conținutul complet al fișierului `.claude/skills/vid-avatar-heygen/SKILL.md`:

```markdown
---
name: vid-avatar-heygen
description: "Generează video cu avatar realist via HeyGen API v3. Avatarul vorbește un script text cu lip sync precis, plasat într-o scenă reală (fundal imagine sau culoare, mișcare naturală). Suport voce română."
triggers:
  - "video heygen"
  - "avatar realist"
  - "talking head"
  - "prezentare video"
  - "avatar vorbitor"
  - "lip sync"
  - "avatar în scenă"
  - "video cu avatar"
secrets_required:
  - HEYGEN_API_KEY
context_loads:
  - knowledge/brand-video.md
  - knowledge/produse.md
note: brand-video.md conține mai multe branduri; citește secțiunea brandului ales la task
outputs:
  - video .mp4 în /tmp/nova-video/{slug}/heygen-{N}.mp4
runtime_dependencies:
  - python3
  - requests (pip install requests)
---

# Skill: Generare Video Avatar HeyGen v3

## Pas 0: Identifică brandul și avatarul

Citește `knowledge/brand-video.md`.

Găsește secțiunea brandului menționat în brief. Extrage:
- `heygen_look_id` — ID-ul avatarului persistent (dacă există)
- `aspect_ratio`, `resolution`, culoarea subtitlurilor etc.

Dacă brandul **nu are `heygen_look_id`**:
> "Brandul [NUME] nu are un avatar configurat. Vrei să creăm acum un avatar persistent din fotografie? (handoff la vid-avatar-heygen-create) sau continui cu un avatar din biblioteca HeyGen?"

Dacă utilizatorul vrea un avatar din bibliotecă (nu foto proprie), continuă la Pas 1.
Dacă vrea avatar propriu, transferă la `vid-avatar-heygen-create` și revino după ce look_id e salvat.

## Pas 1: Selectează avatarul (dacă nu e din catalog)

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py --list-avatars
```

Prezintă primele 10 avatare (ID, nume) și cere alegerea.

## Pas 2: Selectează vocea română

```bash
python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py --list-voices --language Romanian
```

Dacă lista are voci → prezintă-le și cere alegerea.
Dacă lista e goală (HeyGen nu returnează voci RO native) → folosește vocea multilinguală ElevenLabs din skill-ul `vid-voice` sau alege o voce EN cu `locale: ro-RO` setat implicit.

Notifică utilizatorul:
> "Am găsit [N] voci în română. [Lista] — care preferi?"

**ÎNCHEIE TURA** — nu continua fără confirmare avatar + voce.

## Pas 3: Alege scena (fundalul)

Întreabă utilizatorul:
> "Ce fundal vrei pentru scena avatarului?
> 1. Culoare solidă (ex: alb, negru, gradient) — cel mai rapid
> 2. Imagine de fundal — URL imagine (birou, studio, exterior)
> 3. Fără fundal specificat — HeyGen alege automat"

Dacă alege 1: cere codul hex al culorii (sau sugerează `#FFFFFF` alb, `#1a1a2e` bleumarin, `#f0f0f0` gri deschis).
Dacă alege 2: cere URL-ul imaginii. URL-ul trebuie să fie public și accesibil.
Dacă alege 3: nu adăuga câmpul `background` în request.

**ÎNCHEIE TURA** — nu continua fără decizie scenă.

## Pas 4: Scrie sau primește scriptul

Dacă utilizatorul a dat un script complet → folosește-l direct (sari la Pas 5).

Dacă a dat un brief, scrie scriptul:
- Max 200 cuvinte (~90 secunde)
- Ton conversațional, nu formal
- Primele 5 cuvinte = hook direct, fără "Bună ziua, mă numesc..."
- Dacă brief-ul menționează un produs din `knowledge/produse.md`, include beneficiul principal

Prezintă scriptul:
> "Iată scriptul ([N] cuvinte, ~[M] secunde). Confirmi sau ajustăm?"

**Nu continua la Pas 5 fără confirmare explicită pe script.**

## Pas 5: Avertizare cost și confirmare

```
Minute video = număr cuvinte ÷ 150
Cost Avatar III = secunde × $0.017
Cost Avatar IV  = secunde × $0.043  ← default recomandat
Cost Avatar V   = secunde × $0.067  ← calitate maximă
```

Mesaj utilizator:
> "Script de [N] cuvinte = ~[M] secunde video.
> Cost estimat: ~$[X] cu Avatar IV (recomandat).
> Continui?"

**Nu genera fără confirmare explicită.**

## Pas 6: Execuție

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
OUTPUT_SLUG="heygen-$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="/tmp/nova-video/${OUTPUT_SLUG}"
mkdir -p "${OUTPUT_DIR}"

python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py generate \
  "<SCRIPT_TEXT>" \
  "${OUTPUT_DIR}/heygen-1.mp4" \
  --avatar <LOOK_ID> \
  --voice <VOICE_ID> \
  --aspect <RATIO> \
  --resolution 1080p \
  --locale ro-RO \
  --expressiveness high \
  --motion-prompt "gesturing naturally while speaking, looking at camera" \
  [--background-color "#HEX"] \
  [--background-image "URL"]
```

Parsează JSON returnat. Extrage `output_path`, `video_id`, `duration_s`.
Dacă conține `"error"` → raportează și oprește.

## Pas 7: Self-QA și livrare

```bash
FILE_SIZE=$(du -k "${OUTPUT_DIR}/heygen-1.mp4" 2>/dev/null | cut -f1)
echo "Dimensiune: ${FILE_SIZE}KB"
```

Criterii de acceptare:
- Fișierul există și e > 100KB
- `duration_s` din JSON corespunde estimării

Raportează:
- Avatar folosit (ID)
- Durată reală
- Cost estimat pe durata reală
- Calea fișierului

Întreabă: "Continui cu subtitruri (vid-ffmpeg-edit) sau uploadăm direct (tool-video-upload)?"

## Rules

- Avertizarea cost cu calcul explicit este OBLIGATORIE înaintea oricărei generări
- Nu genera fără confirmare pe cost și script
- Dacă `--list-voices --language Romanian` returnează 0 voci, setează `--locale ro-RO` la generare și informează utilizatorul
- `--motion-prompt` și `--expressiveness high` sunt ÎNTOTDEAUNA incluse pentru a evita stilul "poza de pașaport"
- Fișierul trebuie să existe și fie > 100KB înainte de livrare

## Self-Update

Dacă utilizatorul semnalează o problemă, adaugă în Rules:
`- [YYYY-MM-DD] corecție: [descriere scurtă]`
```

- [ ] **Step 2: Verifică frontmatter**

```bash
head -5 "/Users/danmitrut/Desktop/CURS AGENȚI/biblioteca-agenti/nova-video/.claude/skills/vid-avatar-heygen/SKILL.md"
```

Expected: `---` pe prima linie, `name: vid-avatar-heygen` pe a doua.

---

## Task 4: Test end-to-end (manual, cu API real)

- [ ] **Step 1: Verifică că heygen_v3.py e prezent și sintaxa e corectă**

```bash
cd "/Users/danmitrut/Desktop/CURS AGENȚI/biblioteca-agenti/nova-video"
python3 -m py_compile .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py && echo "SINTAXĂ OK"
ls -la .claude/skills/vid-avatar-heygen/scripts/
ls -la .claude/skills/vid-avatar-heygen-create/
```

Expected:
- `SINTAXĂ OK`
- `heygen_v3.py` și `heygen_video.py` ambele prezente
- directorul `vid-avatar-heygen-create/` cu `SKILL.md`

- [ ] **Step 2: Verifică că agentul vede skill-urile noi**

```bash
cortextos bus list-skills --format text 2>/dev/null | grep heygen || ls .claude/skills/ | grep heygen
```

Expected: `vid-avatar-heygen`, `vid-avatar-heygen-create` ambele vizibile.

- [ ] **Step 3: Test generate cu avatar existent din bibliotecă**

Alege un avatar ID din lista returnată la Task 1 Step 5 și o voce ID din lista română (sau EN dacă lista RO e goală):

```bash
cd "/Users/danmitrut/Desktop/CURS AGENȚI/biblioteca-agenti/nova-video"
set -a; source .env; set +a

python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py generate \
  "Bună! Acesta este un test al noului sistem de generare video cu avatar plasat în scenă." \
  "/tmp/nova-video/test-v3/test-heygen-v3.mp4" \
  --avatar <AVATAR_ID_DIN_LISTA> \
  --voice <VOICE_ID_DIN_LISTA> \
  --aspect 16:9 \
  --resolution 1080p \
  --locale ro-RO \
  --expressiveness high \
  --motion-prompt "looking at camera, speaking naturally with hand gestures" \
  --background-color "#1a1a2e"
```

Expected:
```json
{
  "status": "ok",
  "output_path": "/tmp/nova-video/test-v3/test-heygen-v3.mp4",
  "video_id": "...",
  "duration_s": ...,
  "size_bytes": ...
}
```

Verifică fișierul:
```bash
ls -lh /tmp/nova-video/test-v3/test-heygen-v3.mp4
```

Expected: fișier > 500KB (un clip de câteva secunde).
