---
name: vid-scene-rapid
description: "Generează video multi-scenă rapid via Higgsfield MCP: fiecare scenă din prompt text, concatenare ffmpeg, voiceover și muzică opționale. Varianta rapidă a MULTI-SCENĂ — viteză în detrimentul calității cinematice."
triggers:
  - "multi-scenă rapid"
  - "mai multe scene rapide"
  - "video din scene"
  - "scurt metraj rapid"
  - "5 scene"
  - "3 scene"
  - "video narativ rapid"
negative_triggers:
  - "avatar"
  - "UGC"
  - "cinematic"
  - "Kling"
  - "calitate înaltă"
inputs:
  - script sau lista de scene (obligatoriu)
  - brand (opțional)
  - voiceover da/nu (opțional, default: nu)
  - muzică da/nu (opțional, default: nu)
outputs:
  - video final concatenat .mp4 la /tmp/nova-video/{slug}/final.mp4
  - scene individuale păstrate la /tmp/nova-video/{slug}/scene-{N}.mp4
runtime_dependencies:
  - Higgsfield MCP (mcp__higgsfield__generate_video disponibil)
  - ffmpeg (instalat în PATH)
secrets_required:
  - KIE_API_KEY (doar dacă se adaugă voiceover sau muzică)
context_loads:
  - knowledge/brand-video.md
  - knowledge/produse.md
---

# Skill: Video multi-scenă rapid via Higgsfield

## Pas 0: Citește contextul

Citește `knowledge/brand-video.md` pentru stilul brandului (culoare subtitruri, format).

## Pas 1: Breakdown pe scene

Dacă utilizatorul a dat un script narativ, sparge-l în scene:
- Maxim 10 scene per video
- Fiecare scenă = 5-8 secunde de acțiune vizuală
- Fiecare scenă trebuie să poată fi descrisă independent (fără referințe la "scena anterioară")

Format scene:
```
Scena 1: [ce se vede, cine/ce, acțiune, context]
Scena 2: [...]
...
```

Prezintă breakdown-ul utilizatorului și cere confirmare înainte de generare.

## Pas 2: Avertizare cost și confirmare

> "Generez [N] scene via Higgsfield (plan propriu Higgsfield), format [9:16/16:9].
>
> Scene:
> 1. [rezumat 10 cuvinte]
> 2. [rezumat 10 cuvinte]
> ...
>
> [Dacă voiceover: + ~$0.075 ElevenLabs]
> [Dacă muzică: + ~$0.10 Suno]
>
> Confirmăm?"

Nu genera fără confirmare.

## Pas 3: Generează fiecare scenă via Higgsfield MCP

Pentru fiecare scenă, apelează `mcp__higgsfield__generate_video`:
- `prompt`: descrierea scenei (fără "scena N" în prompt)
- `aspect_ratio`: format ales
- `duration`: 5-8 secunde per scenă

**Generează scenele secvențial, nu în paralel** — descarcă și verifică fiecare înainte de următoarea.

```bash
OUTPUT_DIR="/tmp/nova-video/$(date +%Y%m%d-%H%M%S)"
mkdir -p "${OUTPUT_DIR}"
```

Descarcă fiecare scenă:
```bash
curl -L -o "${OUTPUT_DIR}/scene-1.mp4" "${URL_SCENA_1}"
# ... pentru fiecare scenă
```

Verifică fiecare scenă (> 100KB) înainte de a continua.

## Pas 4: Concatenare cu ffmpeg

Creează fișierul de concatenare:
```bash
CONCAT_FILE="${OUTPUT_DIR}/concat.txt"
for i in $(seq 1 N_SCENE); do
  echo "file '${OUTPUT_DIR}/scene-${i}.mp4'" >> "${CONCAT_FILE}"
done

ffmpeg -f concat -safe 0 -i "${CONCAT_FILE}" -c copy "${OUTPUT_DIR}/final-raw.mp4"
```

Verifică output (> 500KB pentru video multi-scenă).

## Pas 5: Voiceover (opțional)

Dacă utilizatorul a cerut voiceover: activează skill-ul `vid-voice` cu:
- `text`: scriptul narativ complet
- `output_path`: `${OUTPUT_DIR}/voiceover.mp3`

Lipește voiceover-ul pe video-ul concatenat:
```bash
ffmpeg -i "${OUTPUT_DIR}/final-raw.mp4" \
  -i "${OUTPUT_DIR}/voiceover.mp3" \
  -c:v copy -c:a aac \
  -map 0:v:0 -map 1:a:0 \
  -shortest \
  "${OUTPUT_DIR}/final-with-voice.mp4"
```

## Pas 6: Muzică (opțional)

Dacă utilizatorul a cerut muzică de fundal: activează skill-ul `vid-music`.
Mixează muzica la -20dB față de voiceover (sau la -10dB dacă nu există voiceover):

```bash
# Cu voiceover
ffmpeg -i "${OUTPUT_DIR}/final-with-voice.mp4" \
  -i "${OUTPUT_DIR}/muzica.mp3" \
  -filter_complex "[1:a]volume=0.2[music];[0:a][music]amix=inputs=2:duration=first" \
  -c:v copy \
  "${OUTPUT_DIR}/final.mp4"

# Fără voiceover (muzică singură)
ffmpeg -i "${OUTPUT_DIR}/final-raw.mp4" \
  -i "${OUTPUT_DIR}/muzica.mp3" \
  -filter_complex "[1:a]volume=0.5[music]" \
  -map 0:v -map "[music]" \
  -c:v copy -c:a aac \
  -shortest \
  "${OUTPUT_DIR}/final.mp4"
```

## Pas 7: Subtitruri (opțional)

Dacă utilizatorul vrea subtitruri: activează skill-ul `vid-ffmpeg-edit` cu calea video-ului final și scriptul narativ ca transcript.

## Pas 8: Livrare

Trimite utilizatorului:
- Calea video-ului final
- Dimensiunea totală
- Lista scenelor individuale (dacă vrea să le folosească separat)
- "Video gata de publicat sau mai modificăm ceva?"

## Rules

- Nu genera fără confirmarea breakdown-ului de scene
- Scene secvențial, nu în paralel (evită supraîncărcarea MCP)
- Verifică fiecare scenă > 100KB înainte de concatenare
- Final concatenat trebuie să fie > 500KB înainte de livrare
- Scenele individuale rămân pe disc, nu le șterge

## Self-Update

Adaugă în Rules soluțiile pentru orice eroare nouă întâlnită cu formatul:
`- [YYYY-MM-DD] corecție: [descriere problemă și soluție]`
