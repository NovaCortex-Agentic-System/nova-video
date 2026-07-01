---
name: vid-omni-broll
description: "Primește footage real al utilizatorului vorbind, extrage transcript cu timestamps via Gemini Flash, generează B-roll animat sincronizat via Veo 3.1 (Google Gemini API), combină în split-screen sau overlay via FFmpeg. Footage real + B-roll AI = reel gata."
triggers:
  - "omni broll"
  - "b-roll din footage"
  - "animație pe voce"
  - "sincronizat cu vorbirea"
  - "google omni"
  - "footage cu b-roll"
  - "split screen din footage"
  - "tipografie kinetică"
  - "gemini omni flash"
secrets_required:
  - GEMINI_API_KEY
context_loads:
  - knowledge/brand-video.md
outputs:
  - video .mp4 în /tmp/nova-video/{slug}/omni-broll-{N}.mp4
runtime_dependencies:
  - python3
  - requests (pip install requests)
  - ffmpeg (brew install ffmpeg)
---

# Skill: B-roll Animat Sincronizat cu Vorbirea (Gemini + Veo 3.1)

Fluxul inspirat din tehnica @neuro_ver / @alhimik_ai de pe Instagram:
persoana se filmează singură vorbind → Gemini Flash extrage transcript cu timestamps → Veo 3.1 generează B-roll animat per segment → se combină în split-screen sau overlay via FFmpeg.

**Despre "Google Omni":** Gemini Omni Flash (`gemini-omni-flash-preview`) este modelul oficial Google pentru text-to-video cu audio nativ, lansat 30 iunie 2026, cu `video_config.task`. B-roll-ul curent se generează via Veo 3.1 (API stabil și documentat). Upgrade la `gemini-omni-flash-preview` e TODO când endpoint-ul devine GA.

## Pas 0: Primește footage-ul

Cere utilizatorului:
> "Trimite videoul în care vorbești. Cerințe:
> - Format: MP4, MOV, orice format video standard
> - Durată: max 90 secunde pentru rezultate bune
> - Sunet clar, fără zgomot de fundal
> - Poate fi filmat cu telefonul, nu e nevoie de echipament profesional
>
> Trimite fișierul via Telegram sau un URL public."

Dacă utilizatorul trimite fișier local via Telegram → calea e în `local_file:` din mesaj.
Dacă trimite URL → descarcă local:
```bash
curl -L "<URL>" -o "/tmp/nova-video/omni-input/footage.mp4"
```

**ÎNCHEIE TURA** — nu continua fără footage confirmat.

## Pas 1: Alege stilul vizual pentru B-roll

Prezintă opțiunile de stil:
> "Ce stil vizual vrei pentru B-roll?
> 1. **Kinetic Typography** — text bold animat care apare sincronizat cu vorbele tale, fundal negru sau culoare solidă (stilul @neuro_ver)
> 2. **Paper Scrapbook** — text pe textură hârtie, decupaje ziar, halftone dots, culori acide
> 3. **Clean Minimal** — text alb pe negru, animații simple, profesional
> 4. **Custom** — descrie stilul tău"

Dacă alege Custom → cere descrierea stilului.

**ÎNCHEIE TURA** — nu continua fără stil confirmat.

## Pas 2: Alege formatul de combinare

> "Cum vrei să combini footage-ul cu B-roll-ul?
> 1. **Split-screen** — tu pe dreapta (50%), B-roll pe stânga (50%) — stilul clasic din reels
> 2. **Overlay** — B-roll apare peste footage-ul tău ca layer transparent (30-50% opacity)
> 3. **Alternare** — tu apari câteva secunde, apoi B-roll înlocuiește imaginea, vocea continuă"

## Pas 3: Extrage transcript cu timestamps

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
OUTPUT_DIR="/tmp/nova-video/omni-broll-$(date +%Y%m%d-%H%M%S)"
mkdir -p "${OUTPUT_DIR}"
INPUT_VIDEO="<CALEA_FOOTAGE>"

# Extrage audio din footage
ffmpeg -i "${INPUT_VIDEO}" -q:a 0 -map a "${OUTPUT_DIR}/audio.mp3" -y

# Transcript cu timestamps via Gemini Flash (multimodal audio)
python3 .claude/skills/vid-omni-broll/scripts/omni_transcript.py \
  "${OUTPUT_DIR}/audio.mp3" \
  "${OUTPUT_DIR}/transcript.json"
```

Parsează output JSON. Dacă `"status": "ok"` → extrage `segments` și `duration_total`.
Dacă `"error"` → raportează și oprește.

## Pas 4: Generează B-roll animat sincronizat (Veo 3.1)

```bash
python3 .claude/skills/vid-omni-broll/scripts/omni_broll.py \
  "${OUTPUT_DIR}/transcript.json" \
  "${OUTPUT_DIR}/broll.mp4" \
  --style "<STILUL_ALES: kinetic-typography | paper-scrapbook | clean-minimal | custom>" \
  --model veo-3.1-lite-generate-preview \
  --duration 6 \
  --aspect 9:16
```

Parsează output JSON. Dacă `"status": "ok"` → verifică `clips_generated > 0`.
Dacă `estimated_cost_usd` e > $1.00 → raportează costul utilizatorului și cere confirmare înainte de a continua.

**Atenție cost:** fiecare clip Veo 3.1 Lite costă $0.05/s × 6s = $0.30. Un footage de 60s → ~10 clipuri → ~$3.00.
Raportează estimarea ÎNAINTE de execuție:
> "Footage de [N]s → ~[M] clipuri × $0.30 = ~$[X] total. Confirmi?"

## Pas 5: Combină footage + B-roll

```bash
python3 .claude/skills/vid-omni-broll/scripts/omni_combine.py \
  "${INPUT_VIDEO}" \
  "${OUTPUT_DIR}/broll.mp4" \
  "${OUTPUT_DIR}/transcript.json" \
  "${OUTPUT_DIR}/omni-broll-1.mp4" \
  --mode <split-screen | overlay | alternare> \
  --resolution 1080x1920
```

Parsează output JSON. Dacă `"status": "ok"` → verifică `size_bytes > 1000000`.

## Pas 6: Self-QA și livrare

```bash
FILE_SIZE=$(du -k "${OUTPUT_DIR}/omni-broll-1.mp4" 2>/dev/null | cut -f1)
echo "Dimensiune: ${FILE_SIZE}KB"
```

Criterii de acceptare:
- Fișierul există și e > 1MB
- Durata output ≈ durata footage input

Raportează:
- Durata video final
- Stilul aplicat
- Calea fișierului

Întreabă: "Adăugăm subtitruri (vid-ffmpeg-edit) sau uploadăm direct (tool-video-upload)?"

## Rules

- Nu continua la Pas 3 fără footage, stil și format confirmate
- Footage-ul rămâne local — nu se uploadează nicăieri fără aprobare explicită
- Dacă transcript-ul returnează 0 segmente, oprește și raportează eroarea de audio
- Split-screen e formatul default dacă utilizatorul nu specifică
- Estimarea cost Veo se prezintă ÎNAINTE de execuția `omni_broll.py`, nu după
- Nu genera B-roll fără confirmare cost explicită pentru footages > 30 secunde

## Status implementare

- [x] `omni_transcript.py` — Gemini Flash multimodal, transcript cu timestamps
- [x] `omni_broll.py` — Veo 3.1 (`veo-3.1-lite-generate-preview`), grupare segmente, generare clipuri
- [x] `omni_combine.py` — FFmpeg: split-screen, overlay, alternare
- [ ] Upgrade `omni_broll.py` la `gemini-omni-flash-preview` (`video_config.task: text_to_video`) când API devine GA și endpoint-ul e confirmat în documentație (ai.google.dev/gemini-api/docs/omni)

## Self-Update

Dacă utilizatorul semnalează o problemă, adaugă în Rules:
`- [YYYY-MM-DD] corecție: [descriere scurtă a problemei și soluției]`
