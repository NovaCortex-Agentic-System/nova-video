---
name: vid-avatar-heygen
description: "Generează video cu avatar realist via HeyGen CLI. Avatarul vorbește un script în română, plasat într-o scenă reală (fundal imagine sau culoare, mișcare naturală). Nu pentru reclame cinematice fără voce — acelea merg pe vid-scene-cinematic."
triggers:
  - "video heygen"
  - "avatar realist"
  - "talking head"
  - "prezentare video"
  - "avatar vorbitor"
  - "lip sync"
  - "avatar în scenă"
  - "video cu avatar"
  - "avatar care vorbește"
secrets_required:
  - HEYGEN_API_KEY
context_loads:
  - knowledge/brand-video.md
  - knowledge/produse.md
note: brand-video.md conține mai multe branduri; citește secțiunea brandului ales la task
outputs:
  - video .mp4 în /tmp/nova-video/{slug}/heygen-{N}.mp4
runtime_dependencies:
  - heygen CLI (curl -fsSL https://static.heygen.ai/cli/install.sh | bash)
---

# Skill: Generare Video Avatar HeyGen

## Pas 0: Identifică brandul și avatarul

Citește `knowledge/brand-video.md`. Găsește secțiunea brandului menționat. Extrage:
- `heygen_look_id` — ID-ul avatarului persistent (dacă există)
- `aspect_ratio`, culori, format preferat

Dacă brandul **nu are `heygen_look_id`**:
> "Brandul [NUME] nu are un avatar HeyGen configurat. Opțiuni:
> 1. Creăm un avatar persistent din fotografie (recomandat) → handoff la vid-avatar-heygen-create
> 2. Folosim un avatar din biblioteca HeyGen (fără fotografie proprie)"

Dacă alege 1 → transferă la `vid-avatar-heygen-create`, revino după ce look_id e salvat în catalog.
Dacă alege 2 → continuă la Pas 1.
Dacă brandul are look_id → sari direct la Pas 2.

## Pas 1: Selectează avatarul din biblioteca HeyGen

Rulează numai dacă brandul nu are look_id și utilizatorul a ales opțiunea 2.

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
heygen avatar looks list --ownership public --limit 20
```

Parsează JSON, extrage `id` și `name` din `data.looks`. Prezintă primele 10. Cere alegerea.

**ÎNCHEIE TURA** — nu continua fără confirmare avatar.

## Pas 2: Selectează vocea în română

```bash
heygen voice list --language Romanian --limit 100
```

Fallback hardcodat dacă comanda returnează 0 voci:
- `dfea36b07588437d93e9f73c828fec5a` — Hushed Horatiu (masculin, discret)
- `00631519159a402ab5d8f719e51532bb` — Jora Slobod (masculin)
- `ec218e50cc9c4991894676a31e4804c5` — Emil - Natural (masculin)
- `19e93c4e7713495894a42b80fcff866c` — Alina - Natural (feminin)

Prezintă lista și întreabă preferința utilizatorului.

**ÎNCHEIE TURA** — nu continua fără confirmare voce.

## Pas 3: Alege scena

> "Ce fundal vrei pentru scenă?
> 1. Culoare solidă (alb, negru, bleumarin #1a1a2e, gri #f0f0f0)
> 2. Imagine de fundal — trimite un URL public
> 3. Fără fundal specificat — HeyGen decide automat"

**ÎNCHEIE TURA** — nu continua fără decizie scenă.

## Pas 4: Scrie sau primește scriptul

Dacă utilizatorul a dat un script complet → folosește-l direct, sari la Pas 5.

Dacă a dat un brief, scrie scriptul respectând:
- Max 200 cuvinte (~90 secunde vorbire)
- Ton conversațional, primele 5 cuvinte = hook direct
- Fără "Bună ziua, mă numesc..."

Prezintă scriptul și cere confirmare. **Nu continua fără confirmare explicită pe script.**

## Pas 5: Avertizare cost și confirmare

```
Secunde video ≈ (cuvinte ÷ 150) × 60
Avatar IV (default): secunde × $0.043
Avatar V:            secunde × $0.067
Avatar III:          secunde × $0.017
```

> "Script de [N] cuvinte = ~[M] secunde. Cost estimat: ~$[X] cu Avatar IV. Continui?"

**Nu genera fără confirmare explicită.**

## Pas 6: Execuție

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
OUTPUT_DIR="/tmp/nova-video/heygen-$(date +%Y%m%d-%H%M%S)"
mkdir -p "${OUTPUT_DIR}"

PAYLOAD='{
  "type": "avatar",
  "avatar_id": "<LOOK_ID>",
  "voice_id": "<VOICE_ID>",
  "script": "<SCRIPTUL_COMPLET>",
  "aspect_ratio": "<9:16 SAU 16:9>",
  "resolution": "1080p",
  "locale": "ro-RO",
  "expressiveness": 1.5,
  "motion_prompt": "looking at camera, speaking naturally with hand gestures"
}'

# Cu fundal imagine: adaugă "background": {"type": "image", "url": "<URL>"}
# Cu fundal culoare: adaugă "background": {"type": "color", "value": "#1a1a2e"}

RESULT=$(heygen video create -d "${PAYLOAD}" --wait)
VIDEO_ID=$(echo "${RESULT}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['video_id'])")
heygen video download "${VIDEO_ID}" --output-path "${OUTPUT_DIR}/heygen-1.mp4"
```

## Pas 7: Self-QA și livrare

```bash
FILE_SIZE=$(du -k "${OUTPUT_DIR}/heygen-1.mp4" 2>/dev/null | cut -f1)
echo "Dimensiune: ${FILE_SIZE}KB"
```

Criterii de acceptare: fișierul există și > 100KB.

Raportează: look_id folosit, voce, calea fișierului.

Întreabă: "Continui cu subtitruri (vid-ffmpeg-edit) sau uploadăm direct (tool-video-upload)?"

## Rules

- Avertizarea cost este OBLIGATORIE înainte de generare
- Nu genera fără confirmare pe cost și script
- `"expressiveness": 1.5` și `"motion_prompt"` sunt ÎNTOTDEAUNA incluse
- `"locale": "ro-RO"` este ÎNTOTDEAUNA inclus
- Dacă `heygen voice list --language Romanian` returnează 0, folosește lista hardcodată
- Fișierul trebuie să fie > 100KB înainte de livrare

## Self-Update

Dacă utilizatorul semnalează o problemă, adaugă în Rules:
`- [YYYY-MM-DD] corecție: [descriere scurtă]`
