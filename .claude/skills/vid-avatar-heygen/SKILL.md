---
name: vid-avatar-heygen
description: "Generează video cu avatar realist via HeyGen API v3. Avatarul vorbește un script în română, plasat într-o scenă reală (fundal imagine sau culoare, mișcare naturală). Nu pentru reclame cinematice fără voce — acelea merg pe vid-scene-cinematic."
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
  - python3
  - requests (pip install requests)
---

# Skill: Generare Video Avatar HeyGen v3

## Pas 0: Identifică brandul și avatarul

Citește `knowledge/brand-video.md`.

Găsește secțiunea brandului menționat. Extrage:
- `heygen_look_id` — ID-ul avatarului persistent (dacă există)
- `aspect_ratio`, `resolution`, culori, format preferat

Dacă brandul **nu are `heygen_look_id`**:
> "Brandul [NUME] nu are un avatar HeyGen configurat. Opțiuni:
> 1. Creăm un avatar persistent din fotografie (recomandat) — handoff la vid-avatar-heygen-create
> 2. Folosim un avatar din biblioteca HeyGen (fără fotografie proprie)"

Dacă alege 1 → transferă la `vid-avatar-heygen-create`, revino după ce look_id e salvat în catalog.
Dacă alege 2 → continuă la Pas 1.
Dacă brandul are look_id → sari direct la Pas 2.

## Pas 1: Selectează avatarul din biblioteca HeyGen

Rulează numai dacă brandul nu are look_id și utilizatorul a ales opțiunea 2.

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py --list-avatars
```

Prezintă primele 10 avatare (ID, nume). Cere alegerea.

**ÎNCHEIE TURA** — nu continua fără confirmare avatar.

## Pas 2: Selectează vocea în română

```bash
python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py --list-voices --language Romanian
```

Voci române confirmate disponibile:
- `dfea36b07588437d93e9f73c828fec5a` — Hushed Horatiu (masculin, discret)
- `00631519159a402ab5d8f719e51532bb` — Jora Slobod (masculin)
- `ec218e50cc9c4991894676a31e4804c5` — Emil - Natural (masculin, natural)
- `19e93c4e7713495894a42b80fcff866c` — Alina - Natural (feminin, natural)

Prezintă lista și întreabă:
> "Ce voce preferi pentru acest video? (sau îmi dai tu preferința — ex: masculin/feminin, ton calm/energic)"

**ÎNCHEIE TURA** — nu continua fără confirmare voce.

## Pas 3: Alege scena

Întreabă utilizatorul:
> "Ce fundal vrei pentru scenă?
> 1. Culoare solidă (alb, negru, bleumarin #1a1a2e, gri #f0f0f0)
> 2. Imagine de fundal — trimite un URL (birou, studio, exterior, etc.)
> 3. Fără fundal specificat — HeyGen decide automat"

Dacă alege 1 → cere codul hex sau sugerează variantele de mai sus.
Dacă alege 2 → cere URL-ul imaginii (trebuie să fie public, accesibil fără autentificare).
Dacă alege 3 → nu adăuga `--background-*` la comandă.

**ÎNCHEIE TURA** — nu continua fără decizie scenă.

## Pas 4: Scrie sau primește scriptul

Dacă utilizatorul a dat un script complet → folosește-l direct, sari la Pas 5.

Dacă a dat un brief, scrie scriptul respectând:
- Max 200 cuvinte (~90 secunde vorbire)
- Ton conversațional, nu formal sau marketing agresiv
- Primele 5 cuvinte = hook direct, fără "Bună ziua, mă numesc..."
- Dacă brief-ul menționează un produs din `knowledge/produse.md`, include beneficiul principal

Prezintă scriptul și cere confirmare:
> "Iată scriptul ([N] cuvinte, ~[M] secunde). Confirmi sau ajustăm?"

**Nu continua la Pas 5 fără confirmare explicită pe script.**

## Pas 5: Avertizare cost și confirmare

Calculează costul estimat:

```
Secunde video ≈ (număr cuvinte ÷ 150) × 60
Cost Avatar IV (default) = secunde × $0.043
Cost Avatar V            = secunde × $0.067
Cost Avatar III          = secunde × $0.017  ← cel mai ieftin
```

Trimite calculul:
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
  --aspect <RATIO_DIN_BRAND_SAU_9:16> \
  --resolution 1080p \
  --locale ro-RO \
  --expressiveness high \
  --motion-prompt "looking at camera, speaking naturally with hand gestures" \
  [--background-color "#HEX"] \
  [--background-image "URL"]
```

Parsează JSON returnat. Extrage `output_path`, `video_id`, `duration_s`.
Dacă conține `"error"` → raportează eroarea completă și oprește.

## Pas 7: Self-QA și livrare

```bash
FILE_SIZE=$(du -k "${OUTPUT_DIR}/heygen-1.mp4" 2>/dev/null | cut -f1)
echo "Dimensiune: ${FILE_SIZE}KB"
```

Criterii de acceptare:
- Fișierul există și este > 100KB
- `duration_s` din JSON corespunde estimării din Pas 5

Raportează utilizatorului:
- Avatar folosit (ID)
- Voce folosită (ID + nume)
- Durată reală
- Cost estimat pe durata reală (recalculat)
- Calea completă a fișierului

Întreabă: "Continui cu subtitruri (vid-ffmpeg-edit) sau uploadăm direct (tool-video-upload)?"

## Rules

- Avertizarea cost cu calcul explicit este OBLIGATORIE înainte de orice generare
- Nu genera fără confirmare pe cost și script
- `--expressiveness high` și `--motion-prompt` sunt ÎNTOTDEAUNA incluse pentru a evita stilul "poza de pașaport"
- `--locale ro-RO` este ÎNTOTDEAUNA inclus indiferent de vocea aleasă
- Fișierul trebuie să existe și să fie > 100KB înainte de livrare
- Dacă `--list-voices --language Romanian` returnează 0 voci, folosește Emil sau Alina din lista hardcodată de mai sus la Pas 2

## Self-Update

Dacă utilizatorul semnalează o problemă, adaugă în Rules:
`- [YYYY-MM-DD] corecție: [descriere scurtă a problemei și soluției]`
