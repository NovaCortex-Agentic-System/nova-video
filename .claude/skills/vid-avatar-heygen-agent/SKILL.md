---
name: vid-avatar-heygen-agent
description: "Generează video complet via HeyGen Video Agent: talking head + B-roll automat, compoziție scenă, subtitruri — dintr-un singur prompt. HeyGen scrie scriptul, decide când apare avatarul și când apare B-roll-ul. Voce română. Ideal pentru video-uri de tip prezentare, explainer, update."
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
  - python3
  - requests (pip install requests)
---

# Skill: Video Agent HeyGen — Talking Head + B-roll Automat

HeyGen Video Agent primește un brief text și generează singur: scrie scriptul, decide când apare avatarul (talking head) și când apare B-roll, compune scenele, randează video-ul final.

**Diferența față de vid-avatar-heygen:** aici dai un brief, nu un script. HeyGen face restul.

## Pas 0: Identifică brandul și avatarul

Citește `knowledge/brand-video.md`. Extrage `heygen_look_id` și `heygen_voice_id` (dacă există) pentru brandul menționat.

Dacă brandul nu are `heygen_look_id`:
> "Brandul [NUME] nu are avatar configurat. Creăm unul din fotografie? (handoff la vid-avatar-heygen-create)"

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

Cere utilizatorului:
> "Descrie video-ul în detaliu:
> - Subiectul și mesajul principal
> - Durata aproximativă (recomandat: 45-90 secunde)
> - Tonul (educativ, inspirațional, direct, etc.)
> - Ce scene sau momente vrei să evidențiezi (HeyGen va decide B-roll-ul automat pe baza asta)
> - Limba: română"

**Important pentru utilizator:** Nu dai script — dai context. Cu cât brief-ul e mai detaliat despre momentele cheie, cu atât scena va fi mai apropiată de ce vrei.

**ÎNCHEIE TURA** — nu continua fără brief confirmat.

## Pas 3: Referințe B-roll (opțional)

Întreabă:
> "Ai imagini sau documente (PDF, imagini) care să servească drept referință vizuală pentru B-roll? Poți trimite URL-uri publice.
> (Opțional — dacă nu trimiți nimic, HeyGen alege B-roll-ul singur)"

Dacă da → colectează URL-urile (max 20).
Dacă nu → continuă fără `--file`.

## Pas 4: Construiește prompt-ul pentru Video Agent

Din brief-ul primit, construiește un prompt clar pentru HeyGen. Structura recomandată:

```
[Descriere subiect și context]
[Mesaj principal]
[Momente cheie pe care să le evidențieze cu B-roll]
[Ton și stil]
[Limbă: Romanian]
[Durată aproximativă: X secunde]
```

Exemplu pentru brief-ul "Data Drift AI, 50 secunde, revoluția industrială, job disruption, AI agents":
```
Create a 50-second video in Romanian about AI's impact on work and jobs for Data Drift AI.
The avatar presents directly to camera. Include B-roll footage showing: industrial revolution imagery
when discussing historical parallels (around the 8-18 second mark), people in office environments
when discussing job disruption (around 28-35 seconds), and futuristic AI/technology visuals when
discussing AI agents (around 40-47 seconds). The tone is educational and direct. Language: Romanian.
```

Prezintă prompt-ul utilizatorului și cere confirmare:
> "Iată prompt-ul pe care îl trimit la Video Agent. Confirmi sau ajustăm?"

**Nu continua fără confirmare.**

## Pas 5: Avertizare cost și confirmare

Video Agent costă mai mult decât talking head simplu (include scene composition + B-roll):

```
Estimare cost Video Agent HeyGen: $0.10 - $0.30 per video (50-90 secunde)
(variază în funcție de complexitate și planul de cont)
```

> "Generarea via Video Agent costă estimativ $0.10-$0.30 pentru un video de ~50 secunde.
> Confirmi?"

**Nu genera fără confirmare explicită.**

## Pas 6: Execuție

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
OUTPUT_SLUG="heygen-agent-$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="/tmp/nova-video/${OUTPUT_SLUG}"
mkdir -p "${OUTPUT_DIR}"

python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py agent \
  "<PROMPT_TEXT>" \
  "${OUTPUT_DIR}/heygen-agent-1.mp4" \
  --avatar <LOOK_ID> \
  --voice <VOICE_ID> \
  --orientation landscape \
  [--file "URL1"] \
  [--file "URL2"]
```

Parsează JSON returnat. Extrage `output_path`, `video_id`, `duration_s`.
Dacă conține `"error"` → raportează eroarea completă și oprește.

## Pas 7: Self-QA și livrare

```bash
FILE_SIZE=$(du -k "${OUTPUT_DIR}/heygen-agent-1.mp4" 2>/dev/null | cut -f1)
echo "Dimensiune: ${FILE_SIZE}KB"
```

Criterii de acceptare:
- Fișierul există și este > 500KB (video-urile Video Agent sunt mai grele)
- `duration_s` este în intervalul rezonabil față de brief

Raportează:
- Durata reală a video-ului generat
- Calea fișierului
- Video_id HeyGen (pentru referință)

Întreabă: "Adăugăm subtitruri (vid-ffmpeg-edit) sau uploadăm direct (tool-video-upload)?"

## Rules

- Brief-ul trebuie să menționeze explicit limba română (sau "Language: Romanian" în prompt)
- Prompt-ul se prezintă utilizatorului înainte de execuție — nu se trimite nesupravegheate
- Confirmarea cost este obligatorie înainte de generare
- Dacă nu ai look_id → handoff obligatoriu la vid-avatar-heygen-create
- Referințele B-roll sunt opționale — nu bloca fluxul dacă utilizatorul nu le trimite

## Self-Update

Dacă utilizatorul semnalează o problemă, adaugă în Rules:
`- [YYYY-MM-DD] corecție: [descriere scurtă a problemei și soluției]`
