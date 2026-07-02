---
name: vid-avatar-heygen-agent
description: "Generează video complet via HeyGen Video Agent CLI: talking head + B-roll automat, compoziție scenă, subtitruri — dintr-un singur prompt. HeyGen scrie scriptul, decide când apare avatarul și când apare B-roll-ul. Voce română. Ideal pentru video-uri de tip prezentare, explainer, update."
triggers:
  - "video agent heygen"
  - "video complet heygen"
  - "heygen cu b-roll"
  - "video cu scene heygen"
  - "video agent"
  - "prezentare cu b-roll"
secrets_required:
  - HEYGEN_API_KEY
context_loads:
  - knowledge/brand-video.md
  - knowledge/produse.md
outputs:
  - video .mp4 în /tmp/nova-video/{slug}/heygen-agent-{N}.mp4
runtime_dependencies:
  - heygen CLI (curl -fsSL https://static.heygen.ai/cli/install.sh | bash)
---

# Skill: Video Agent HeyGen — Talking Head + B-roll Automat

HeyGen Video Agent primește un brief text și generează singur: scrie scriptul, decide când apare avatarul (talking head) și când apare B-roll, compune scenele, randează video-ul final.

**Diferența față de vid-avatar-heygen:** aici dai un brief, nu un script. HeyGen face restul.

## Pas 0: Identifică brandul și avatarul

Citește `knowledge/brand-video.md`. Extrage `heygen_look_id` și `heygen_voice_id` (dacă există).

Dacă brandul nu are `heygen_look_id`:
> "Brandul [NUME] nu are avatar configurat. Creăm unul? (handoff la vid-avatar-heygen-create)"

Dacă are look_id → continuă.

## Pas 1: Selectează vocea română

Dacă brandul are `heygen_voice_id` salvat → folosește-l direct, sari la Pas 2.

Altfel, prezintă vocile române confirmate:
- `ec218e50cc9c4991894676a31e4804c5` — Emil - Natural (masculin)
- `19e93c4e7713495894a42b80fcff866c` — Alina - Natural (feminin)
- `dfea36b07588437d93e9f73c828fec5a` — Hushed Horatiu (masculin, discret)
- `00631519159a402ab5d8f719e51532bb` — Jora Slobod (masculin)

**ÎNCHEIE TURA** — nu continua fără confirmare voce.

## Pas 2: Primește brief-ul video

> "Descrie video-ul:
> - Subiectul și mesajul principal
> - Durata aproximativă (recomandat: 45-90 secunde)
> - Tonul (educativ, inspirațional, direct, etc.)
> - Momente cheie de evidențiat (HeyGen decide B-roll-ul automat)
> - Limbă: română"

**ÎNCHEIE TURA** — nu continua fără brief confirmat.

## Pas 3: Referințe B-roll (opțional)

> "Ai URL-uri publice de imagini/documente ca referință vizuală pentru B-roll? (opțional)"

Dacă da → colectează URL-urile (max 20, pentru `heygen asset create` înainte dacă sunt fișiere locale).
Dacă nu → continuă fără referințe.

## Pas 4: Construiește și confirmă promptul

Din brief, construiește promptul pentru Video Agent. Structură recomandată:
```
[Subiect și context]
[Mesaj principal]
[Momente cheie cu B-roll la timestamps aproximative]
[Ton și stil]
Language: Romanian
Duration: ~[X] seconds
```

Prezintă promptul și cere confirmare. **Nu trimite fără confirmare.**

## Pas 5: Avertizare cost și confirmare

> "Video Agent costă estimativ $0.10-$0.30 pentru un video de ~50 secunde. Confirmi?"

**Nu genera fără confirmare explicită.**

## Pas 6: Execuție

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
OUTPUT_DIR="/tmp/nova-video/heygen-agent-$(date +%Y%m%d-%H%M%S)"
mkdir -p "${OUTPUT_DIR}"

RESULT=$(heygen video-agent create \
  --prompt "<PROMPTUL_CONSTRUIT>" \
  --avatar-id "<LOOK_ID>" \
  --voice-id "<VOICE_ID>" \
  --orientation portrait \
  --wait)

SESSION_ID=$(echo "${RESULT}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['session_id'])")
VIDEO_ID=$(heygen video-agent videos list "${SESSION_ID}" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['videos'][0]['video_id'])")
heygen video download "${VIDEO_ID}" --output-path "${OUTPUT_DIR}/heygen-agent-1.mp4"
```

## Pas 7: Self-QA și livrare

```bash
FILE_SIZE=$(du -k "${OUTPUT_DIR}/heygen-agent-1.mp4" 2>/dev/null | cut -f1)
echo "Dimensiune: ${FILE_SIZE}KB"
```

Criterii: fișierul există și > 500KB.

Raportează: durata, session_id, video_id, calea fișierului.

Întreabă: "Adăugăm subtitruri (vid-ffmpeg-edit) sau uploadăm direct (tool-video-upload)?"

## Rules

- Promptul se prezintă utilizatorului înainte de execuție — nu se trimite nesupravegheate
- Confirmarea cost este obligatorie înainte de generare
- Brief-ul trebuie să menționeze explicit limba română în prompt
- Dacă nu ai look_id → handoff obligatoriu la vid-avatar-heygen-create
- Referințele B-roll sunt opționale — nu bloca fluxul fără ele

## Self-Update

Dacă utilizatorul semnalează o problemă, adaugă în Rules:
`- [YYYY-MM-DD] corecție: [descriere scurtă]`
