---
name: vid-voice
description: "Generează voiceover via ElevenLabs (prin kie.ai API). Suportă română și alte limbi. Returnează fișier MP3 local, gata de lipit pe video cu ffmpeg."
triggers:
  - "adaugă voiceover"
  - "voiceover în română"
  - "voce pentru video"
  - "narare"
  - "text to speech"
  - "TTS"
  - "citește textul"
negative_triggers:
  - "muzică"
  - "subtitruri"
  - "generează video"
inputs:
  - text (obligatoriu: textul de citit, max ~500 cuvinte per apel)
  - language_code (opțional, default: "ro" pentru română)
  - voice_id (opțional: ID voce ElevenLabs — dacă lipsește, se folosește vocea default)
  - output_path (opțional: cale MP3 output — default: /tmp/nova-video/{slug}/voiceover.mp3)
outputs:
  - fișier .mp3 la output_path
runtime_dependencies:
  - python3
  - requests (pip install requests)
secrets_required:
  - KIE_API_KEY
---

# Skill: Voiceover ElevenLabs via kie.ai

## Pas 0: Verifică textul

Numără cuvintele. Dacă textul depășește 500 cuvinte, propune împărțirea în segmente sau confirmă că utilizatorul vrea un singur fișier lung.

## Pas 1: Avertizare cost și confirmare

Estimează costul: ~$0.0025 per 100 caractere (aproximativ $0.075 pentru 30s de vorbire normală).

> "Generez voiceover în [limbă] via ElevenLabs (kie.ai).
> Text: [N] cuvinte, durată estimată: ~[N/150]s.
> Cost estimat: ~$[cost].
> Confirmi?"

Nu genera fără confirmare.

## Pas 2: Generează voiceover cu kie_voice.py

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a

OUTPUT_DIR="/tmp/nova-video/$(date +%Y%m%d-%H%M%S)"
mkdir -p "${OUTPUT_DIR}"
OUTPUT_PATH="${output_path:-${OUTPUT_DIR}/voiceover.mp3}"

python3 .claude/skills/vid-voice/scripts/kie_voice.py \
  "{TEXT}" \
  "${OUTPUT_PATH}" \
  --language ro \
  [--voice-id {VOICE_ID} dacă e specificat]
```

Parsează output-ul JSON. Dacă conține `"error"`, raportează eroarea și oprește.

## Pas 3: Self-QA

```bash
FILE_SIZE=$(du -k "${OUTPUT_PATH}" 2>/dev/null | cut -f1)
echo "Dimensiune voiceover: ${FILE_SIZE}KB"
```

Sub 10KB = probabil eroare sau text prea scurt/gol.

## Pas 4: Livrare

Trimite utilizatorului:
- Calea fișierului MP3
- Dimensiunea fișierului
- "Lipim voiceover-ul pe video cu ffmpeg (vid-ffmpeg-edit / vid-scene-rapid / vid-scene-cinematic)?"

## Voci recomandate ElevenLabs (via kie.ai)

Dacă utilizatorul nu specifică o voce, folosește vocea default multilingual. Dacă întreabă de opțiuni, menționează că kie.ai oferă accesul la voicele ElevenLabs — poate testa pe kie.ai dashboard.

Modele disponibile:
- `elevenlabs/text-to-speech-multilingual-v2` — calitate înaltă, suportă română
- `elevenlabs/text-to-speech-turbo-2-5` — mai rapid, cost puțin mai mic

## Rules

- Nu genera fără confirmare cost
- Verifică dimensiunea fișierului MP3 înainte de livrare
- Maximum 500 cuvinte per apel pentru rezultate optime
- Limba default: română ("ro")

## Self-Update

`- [YYYY-MM-DD] corecție: [descriere]`
