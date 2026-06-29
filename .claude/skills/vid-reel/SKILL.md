---
name: vid-reel
description: "Unește clipuri video existente într-un reel final: concatenare ffmpeg, subtitruri opționale din transcript sau audio (Whisper), voiceover opțional. Clipurile pot veni din orice sursă — HeyGen, Higgsfield, footage local."
triggers:
  - "fă un reel"
  - "unește clipurile"
  - "montaj din clipuri"
  - "concatenează scene"
  - "reel din videouri"
  - "încleie clipurile"
  - "asamblează video"
negative_triggers:
  - "generează video"
  - "avatar"
  - "UGC"
inputs:
  - clips (obligatoriu: listă de căi locale .mp4, în ordinea dorită)
  - transcript (opțional: text sau .srt pentru subtitruri)
  - brand (opțional: pentru stilul subtitrurilor)
outputs:
  - reel final la /tmp/nova-video/{slug}/reel-final.mp4
  - scenele individuale rămân intacte la căile originale
runtime_dependencies:
  - ffmpeg (instalat în PATH)
  - mlx-whisper sau faster-whisper (doar dacă transcript lipsește și se cer subtitruri)
secrets_required: []
context_loads:
  - knowledge/brand-video.md
---

# Skill: Reel din clipuri existente

## Pas 0: Inventariază clipurile

Cere utilizatorului (dacă nu sunt deja specificate):
- Căile complete ale clipurilor, în ordinea finală
- Dacă vrea subtitruri (da/nu)
- Dacă vrea voiceover adăugat (da/nu)

Verifică că fiecare fișier există și e > 100KB:
```bash
for clip in {LISTA_CLIPURI}; do
  [ -f "$clip" ] || echo "LIPSĂ: $clip"
  SIZE=$(du -k "$clip" | cut -f1)
  [ "$SIZE" -lt 100 ] && echo "SUSPECT: $clip (${SIZE}KB)"
done
```

Oprește dacă vreun fișier lipsește.

## Pas 1: Verifică format compatibil

```bash
for clip in {LISTA_CLIPURI}; do
  ffprobe -v quiet -show_entries stream=codec_name,width,height \
    -of csv=p=0 "$clip"
done
```

Dacă clipurile au codecuri sau rezoluții diferite, re-encodează înainte de concatenare:
```bash
ffmpeg -i "$clip" \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" \
  -c:v libx264 -c:a aac "/tmp/nova-video/${SLUG}/normalized-N.mp4"
```

## Pas 2: Concatenează

```bash
SLUG=$(date +%Y%m%d-%H%M%S)
OUTPUT_DIR="/tmp/nova-video/${SLUG}"
mkdir -p "${OUTPUT_DIR}"

CONCAT_FILE="${OUTPUT_DIR}/concat.txt"
> "${CONCAT_FILE}"
for clip in {LISTA_CLIPURI_IN_ORDINE}; do
  echo "file '$clip'" >> "${CONCAT_FILE}"
done

ffmpeg -f concat -safe 0 -i "${CONCAT_FILE}" -c copy "${OUTPUT_DIR}/reel-raw.mp4"
```

Verifică: `reel-raw.mp4` > 500KB.

## Pas 3: Subtitruri (opțional)

**Dacă transcript există** (text sau .srt): activează `vid-ffmpeg-edit` direct.

**Dacă transcript lipsește și utilizatorul vrea subtitruri**: transcrie cu Whisper:
```bash
mlx_whisper "${OUTPUT_DIR}/reel-raw.mp4" \
  --model mlx-community/whisper-large-v3-mlx \
  --output-format srt \
  --output-dir "${OUTPUT_DIR}"
```
Fallback:
```bash
faster-whisper "${OUTPUT_DIR}/reel-raw.mp4" \
  --model large-v3 --output_format srt \
  --output_dir "${OUTPUT_DIR}"
```
Apoi activează `vid-ffmpeg-edit` cu SRT-ul generat.

## Pas 4: Voiceover (opțional)

Dacă utilizatorul vrea voiceover: activează `vid-voice`, apoi lipește:
```bash
ffmpeg -i "${OUTPUT_DIR}/reel-raw.mp4" \
  -i "${OUTPUT_DIR}/voiceover.mp3" \
  -c:v copy -c:a aac \
  -map 0:v:0 -map 1:a:0 \
  -shortest \
  "${OUTPUT_DIR}/reel-voice.mp4"
```

## Pas 5: Self-QA

```bash
FILE_SIZE=$(du -k "${OUTPUT_DIR}/reel-final.mp4" 2>/dev/null | cut -f1)
DURATION=$(ffprobe -v quiet -show_entries format=duration \
  -of csv=p=0 "${OUTPUT_DIR}/reel-final.mp4" 2>/dev/null)
echo "Dimensiune: ${FILE_SIZE}KB, Durată: ${DURATION}s"
```

## Pas 6: Livrare

- Calea reelului final: `${OUTPUT_DIR}/reel-final.mp4`
- Dimensiunea și durata totală
- Clipurile originale sunt intacte la căile lor originale

## Rules

- Verifică existența fiecărui clip înainte de a începe
- Re-encodează dacă codecurile sau rezoluțiile sunt diferite
- Clipurile originale nu se modifică niciodată
- Subtitrurile sunt opționale — nu le adăuga fără confirmare
- Output > 500KB înainte de a raporta succes

## Self-Update

Adaugă în Rules soluțiile pentru orice eroare nouă:
`- [YYYY-MM-DD] corecție: [descriere]`
