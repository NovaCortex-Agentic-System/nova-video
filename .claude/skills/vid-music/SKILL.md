---
name: vid-music
description: "Generează muzică de fundal via Suno V5.5 (prin kie.ai API). Returnează fișier MP3 local. Folosește în combinație cu vid-scene-rapid sau vid-scene-cinematic pentru muzică de fundal."
triggers:
  - "adaugă muzică"
  - "muzică de fundal"
  - "background music"
  - "generează muzică"
  - "Suno"
  - "coloană sonoră"
negative_triggers:
  - "voiceover"
  - "narare"
  - "text to speech"
  - "generează video"
inputs:
  - prompt (obligatoriu: descriere stil muzical — ton, tempo, instrumente, mood)
  - duration (opțional: durata în secunde, default: 30)
  - output_path (opțional, default: /tmp/nova-video/{slug}/muzica.mp3)
outputs:
  - fișier .mp3 la output_path
runtime_dependencies:
  - python3
  - requests (pip install requests)
secrets_required:
  - KIE_API_KEY
---

# Skill: Muzică de fundal via Suno (kie.ai)

## Pas 0: Construiește prompt-ul muzical

Dacă utilizatorul a dat o descriere vagă, completează-o:
- Ce emoție trebuie să transmită? (motivațional, relaxant, energic, melancolic)
- Ce instrumente? (pian, chitară, sintetizator, percuție electronică)
- Ce tempo? (lent, mediu, rapid)
- Să fie instrumental sau cu voce? (pentru fundal video — recomandat: instrumental)

Prompt ideal pentru Suno:
```
[Stil muzical], [tempo], [instrumente principale], [mood/emoție], instrumental, no lyrics
```

Exemple:
- "Uplifting corporate background music, medium tempo, piano and strings, motivational, instrumental, no lyrics"
- "Lo-fi chill beats, slow tempo, acoustic guitar, relaxed atmosphere, instrumental, no lyrics"

## Pas 1: Avertizare cost și confirmare

> "Generez muzică de fundal [durata]s via Suno V5.5 (kie.ai).
> Stil: [prompt construit]
> Cost estimat: ~$0.10 pentru 30s.
> Confirmi?"

Nu genera fără confirmare.

## Pas 2: Generează cu kie_music.py

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a

OUTPUT_DIR="/tmp/nova-video/$(date +%Y%m%d-%H%M%S)"
mkdir -p "${OUTPUT_DIR}"
OUTPUT_PATH="${output_path:-${OUTPUT_DIR}/muzica.mp3}"

python3 .claude/skills/vid-music/scripts/kie_music.py \
  "{PROMPT_MUZICA}" \
  "${OUTPUT_PATH}" \
  --duration {DURATA}
```

Parsează output-ul JSON. Dacă conține `"error"`, raportează și oprește.

## Pas 3: Self-QA

```bash
FILE_SIZE=$(du -k "${OUTPUT_PATH}" 2>/dev/null | cut -f1)
echo "Dimensiune muzică: ${FILE_SIZE}KB"
```

Sub 50KB = probabil eroare de generare.

## Pas 4: Livrare

Trimite utilizatorului:
- Calea fișierului MP3
- Dimensiunea fișierului
- "Mixăm muzica pe video? (recomand volum 20% când există și voiceover, 50% dacă e singură)"

## Rules

- Muzica pentru fundal video = întotdeauna instrumental, fără versuri
- Nu genera fără confirmare cost
- Verifică > 50KB înainte de livrare
- Durata muzicii trebuie să fie mai mare sau egală cu durata video-ului

## Self-Update

`- [YYYY-MM-DD] corecție: [descriere]`
