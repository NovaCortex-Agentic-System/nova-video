---
name: vid-scene-cinematic
description: "Generează video multi-scenă cinematic: script → scene breakdown → imagine cheie per scenă (Higgsfield) → animație image-to-video (Kling via kie.ai) → concatenare ffmpeg → voiceover → muzică → montaj final."
triggers:
  - "multi-scenă cinematic"
  - "video cinematic"
  - "Kling"
  - "calitate înaltă scene"
  - "scurt metraj calitate"
  - "scene cinematice"
  - "imagine cheie"
  - "keyframe"
negative_triggers:
  - "avatar"
  - "UGC"
  - "rapid"
  - "Higgsfield UGC"
inputs:
  - script sau lista de scene (obligatoriu)
  - brand (opțional)
  - voiceover da/nu (opțional, default: nu)
  - muzică da/nu (opțional, default: nu)
outputs:
  - video final .mp4 la /tmp/nova-video/{slug}/final.mp4
  - scene individuale la /tmp/nova-video/{slug}/scene-{N}.mp4
  - imagini cheie la /tmp/nova-video/{slug}/keyframe-{N}.jpg
runtime_dependencies:
  - python3
  - requests (pip install requests)
  - ffmpeg (instalat în PATH)
secrets_required:
  - KIE_API_KEY
context_loads:
  - knowledge/brand-video.md
  - knowledge/produse.md
---

# Skill: Video multi-scenă cinematic (keyframe → Kling i2v)

## Pas 0: Citește contextul

Citește `knowledge/brand-video.md` și identifică brandul. Extrage:
- `FORMAT` (default: 9:16)
- `CULOARE_SUBTITRURI` (default: #FFD700)
- `FONT_SUBTITRURI` (default: Arial Bold)

Citește `knowledge/produse.md` dacă produsul e menționat în brief.

## Pas 1: Breakdown pe scene

Sparge scriptul în scene. Maxim 8 scene (fiecare scenă = imagine + animație Kling = cost dublu față de rapid).

Pentru fiecare scenă definește două prompturi separate:

**Prompt imagine cheie** (cadrul de start):
```
[Subiect clar în prim plan]. [Compoziție: unghi cameră, distanță]. [Lumină și atmosferă]. [Culori dominante]. Fără text, fără logouri, fără watermark.
```

**Prompt animație Kling** (mișcarea din acel cadru):
```
[Mișcare cameră: pan left/right, zoom in/out, tilt, static]. [Acțiune subiect]. [Atmosferă]. Smooth motion, natural lighting.
```

Prezintă breakdown-ul complet și cere confirmare înainte de orice generare.

## Pas 2: Avertizare cost și confirmare

> "Flux cinematic pentru [N] scene:
>
> 1. Generare [N] imagini cheie via Higgsfield
> 2. Animație [N] scene via Kling 3.0 (~$[N × 0.20])
> [Dacă voiceover: + ~$0.075 ElevenLabs]
> [Dacă muzică: + ~$0.10 Suno]
>
> Total estimat: ~$[sumă]. Confirmăm?"

Nu genera fără confirmare.

## Pas 3: Pregătește folderul de lucru

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a

SLUG=$(date +%Y%m%d-%H%M%S)
OUTPUT_DIR="/tmp/nova-video/${SLUG}"
mkdir -p "${OUTPUT_DIR}"
```

## Pas 4: Generează imaginile cheie per scenă

Pentru fiecare scenă, generează imaginea de start via **Higgsfield MCP**:

```
Apelează: mcp__higgsfield__generate_image
Parametri:
  prompt: "{PROMPT_IMAGINE_SCENA_N}"
  aspect_ratio: "9:16"   (sau "16:9" după format)
```

Descarcă imaginea returnată și salvează la `${OUTPUT_DIR}/keyframe-N.jpg`.
Verifică fiecare keyframe > 20KB înainte de a continua.

**Dacă Higgsfield nu e disponibil:** oprește și informează:
> "Fluxul cinematic necesită Higgsfield MCP pentru imagini cheie. Alternativa este `vid-scene-rapid` (text-to-video direct, fără keyframe-uri)."

## Pas 5: Animează fiecare scenă cu Kling image-to-video

Secvențial, pentru fiecare scenă:

```bash
python3 .claude/skills/vid-scene-cinematic/scripts/kie_video.py \
  "{PROMPT_ANIMATIE_SCENA_N}" \
  "${OUTPUT_DIR}/scene-N.mp4" \
  --model kling-3.0 \
  --duration {DURATA} \
  --aspect {FORMAT} \
  --reference "${OUTPUT_DIR}/keyframe-N.jpg"
```

Parsează output JSON. Dacă conține `"error"`, raportează și oprește.
Verifică fiecare scenă > 100KB înainte de a continua cu următoarea.

## Pas 6: Concatenează scenele

```bash
CONCAT_FILE="${OUTPUT_DIR}/concat.txt"
> "${CONCAT_FILE}"
for i in $(seq 1 N_SCENE); do
  echo "file '${OUTPUT_DIR}/scene-${i}.mp4'" >> "${CONCAT_FILE}"
done

ffmpeg -f concat -safe 0 -i "${CONCAT_FILE}" -c copy "${OUTPUT_DIR}/final-raw.mp4"
```

Verifică: `final-raw.mp4` > 500KB.

## Pas 7: Voiceover (opțional)

Dacă utilizatorul a cerut voiceover: activează `vid-voice`.

```bash
ffmpeg -i "${OUTPUT_DIR}/final-raw.mp4" \
  -i "${OUTPUT_DIR}/voiceover.mp3" \
  -c:v copy -c:a aac \
  -map 0:v:0 -map 1:a:0 \
  -shortest \
  "${OUTPUT_DIR}/final-voice.mp4"
```

## Pas 8: Muzică (opțional)

Dacă utilizatorul a cerut muzică: activează `vid-music`.

```bash
# Cu voiceover: muzica la 20%
ffmpeg -i "${OUTPUT_DIR}/final-voice.mp4" \
  -i "${OUTPUT_DIR}/muzica.mp3" \
  -filter_complex "[1:a]volume=0.2[music];[0:a][music]amix=inputs=2:duration=first" \
  -c:v copy "${OUTPUT_DIR}/final.mp4"

# Fără voiceover: muzica la 50%
ffmpeg -i "${OUTPUT_DIR}/final-raw.mp4" \
  -i "${OUTPUT_DIR}/muzica.mp3" \
  -filter_complex "[1:a]volume=0.5[music];[0:a][music]amix=inputs=2:duration=first" \
  -c:v copy "${OUTPUT_DIR}/final.mp4"
```

## Pas 9: Subtitruri (opțional)

Dacă utilizatorul vrea subtitruri: activează `vid-ffmpeg-edit` cu video-ul final și scriptul.

## Pas 10: Self-QA

```bash
FILE_SIZE=$(du -k "${OUTPUT_DIR}/final.mp4" 2>/dev/null | cut -f1)
DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${OUTPUT_DIR}/final.mp4" 2>/dev/null)
echo "Dimensiune: ${FILE_SIZE}KB, Durată: ${DURATION}s"
```

## Pas 11: Livrare

- Calea video-ului final: `${OUTPUT_DIR}/final.mp4`
- Dimensiunea și durata totală
- Credite Kling cheltuite (suma `credits` din JSON-urile generate)
- Imagini cheie la: `${OUTPUT_DIR}/keyframe-*.jpg`
- Scene individuale la: `${OUTPUT_DIR}/scene-*.mp4`

## Rules

- Kling 3.0 e singurul model acceptat — nu schimba fără confirmare
- Secvențial per scenă: keyframe → video → verificare → scenă următoare
- Verifică fiecare keyframe > 20KB și fiecare scenă > 100KB înainte de a continua
- Dacă Higgsfield nu e disponibil, redirectează spre `vid-scene-rapid`
- Nu livra fără self-QA (Pas 10)
- Cuvinte interzise în prompturi: cinematic, professional, stunning, 8k, perfect, beautiful

## Self-Update

Adaugă în Rules soluțiile pentru orice eroare nouă:
`- [YYYY-MM-DD] corecție: [descriere]`
