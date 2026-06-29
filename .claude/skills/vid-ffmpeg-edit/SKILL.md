---
name: vid-ffmpeg-edit
description: "Adaugă subtitruri ASS stilizate pe un clip video folosind FFmpeg single-pass. Phrase grouping 3-5 cuvinte, culoare și font din catalogul de branduri. Opțional: concatenare clipuri multiple."
triggers:
  - "adaugă subtitruri"
  - "editează clipul"
  - "burn captions"
  - "pune text pe video"
  - "editează cu FFmpeg"
  - "add subtitles"
  - "procesează video"
negative_triggers:
  - "generează video"
  - "clip selection"
  - "uploadează"
inputs:
  - clip_path (obligatoriu: cale MP4)
  - transcript (obligatoriu: textul dialogului sau cale fișier SRT)
  - clips_to_concat (opțional: listă de MP4-uri de concatenat înainte de subtitruri)
outputs:
  - MP4 cu subtitruri arse, la {clip_path}_subtitled.mp4
runtime_dependencies:
  - ffmpeg (instalat în PATH)
---

# Skill: Editare Video cu FFmpeg

## Pas 0: Citește preferințele de brand

Identifică brandul din context (menționat în brief sau în task-ul curent). Dacă nu e clar, întreabă: "Subtitruri cu stilul căror brand?"

Citește `knowledge/brand-video.md` și găsește secțiunea brandului.

Extrage:
- `CULOARE_SUBTITRURI` (default: #FFD700 dacă brandul nu e în catalog)
- `FONT_SUBTITRURI` (default: Arial Bold dacă brandul nu e în catalog)

## Pas 1: Verifică FFmpeg

```bash
ffmpeg -version 2>&1 | head -1
```

Dacă nu e instalat:
> "FFmpeg nu e instalat. Instalare:
> - macOS: `brew install ffmpeg`
> - Ubuntu/Debian: `sudo apt install ffmpeg`
> - Windows: descarcă de la ffmpeg.org"

Oprește-te până e instalat.

Verifică că fișierul de intrare există:
```bash
[ -f "{CLIP_PATH}" ] || { echo "EROARE: fișierul clip nu există la ${CLIP_PATH}"; exit 1; }
```

Obține durata clipului (necesar pentru timing în Pas 3 dacă transcriptul nu are timestamps):
```bash
CLIP_DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "{CLIP_PATH}")
echo "Durată clip: ${CLIP_DURATION}s"
```

## Pas 2: (Opțional) Concatenare clipuri

Dacă `clips_to_concat` e furnizat (mai multe clipuri de asamblat):

```bash
# Agentul substituie {LISTA_CLIPURI} cu căile reale separate prin spații
# Exemplu: CLIPS=("/tmp/clip1.mp4" "/tmp/clip2.mp4")
CONCAT_FILE="/tmp/concat_list.txt"
> "${CONCAT_FILE}"
for clip in "${CLIPS[@]}"; do
  echo "file '${clip}'" >> "${CONCAT_FILE}"
done

# Concatenează fără re-encodare
ffmpeg -f concat -safe 0 -i "${CONCAT_FILE}" -c copy /tmp/concatenated.mp4
CLIP_PATH="/tmp/concatenated.mp4"
```

## Pas 3: Generează fișierul ASS de subtitruri

Parsează transcriptul: grupează câte 3-5 cuvinte per frază, calculează timing-ul proporțional cu durata totală a clipului.

Creează fișierul ASS la `/tmp/subtitles.ass`:

```
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT_SUBTITRURI},80,&H00{HEX_BGR_CULOARE},&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,1,2,10,10,150,1

[Events]
Format: Layer, Start, End, Style, Text
```

**Conversia culorii hex → BGR pentru ASS:**
- HTML hex: #RRGGBB → ASS BGR: &H00BBGGRR
- Ex: #FFD700 (auriu) → &H0000D7FF

**Format timestamp ASS:** `H:MM:SS.cc` (centisecunde)

**Timing:** împarte durata clipului proporțional la numărul de fraze. Dacă ai SRT cu timecode-uri exacte, folosește-le direct.

**Phrase grouping:** maxim 5 cuvinte per rând, preferabil la punctuație sau pauze naturale.

## Pas 4: FFmpeg single-pass cu subtitruri

```bash
OUTPUT_PATH="${CLIP_PATH%.*}_subtitled.mp4"

ffmpeg -i "{CLIP_PATH}" \
  -vf "ass=/tmp/subtitles.ass" \
  -c:a copy \
  -y \
  "{OUTPUT_PATH}"
```

**Nu folosi cascade de filtre sau două pasuri FFmpeg.**

Verifică output:
```bash
if [ -f "${OUTPUT_PATH}" ]; then
  SIZE_KB=$(du -k "${OUTPUT_PATH}" | cut -f1)
  if [ "${SIZE_KB}" -lt 100 ]; then
    echo "AVERTISMENT: fișier output sub 100KB (${SIZE_KB}KB) — posibil corupt sau generare eșuată"
  else
    echo "Output OK: ${SIZE_KB}KB la ${OUTPUT_PATH}"
  fi
else
  echo "EROARE: output lipsă la ${OUTPUT_PATH}"
fi
```

Dacă output lipsește sau e sub 100KB, raportează eroarea FFmpeg.

## Pas 5: Raportează

Trimite utilizatorului:
- Calea fișierului output
- Dimensiunea fișierului
- "Mai ai modificări sau e gata de publicat?"

## Rules

- Single-pass FFmpeg întotdeauna — niciodată cascade sau două comenzi separate
- Culoarea din knowledge/brand-video.md, nu hardcodată
- Phrase grouping: strict 3-5 cuvinte, nu mai mult
- Safe-zone: MarginV minim 100px de la marginea de jos (PlayResY=1920 → MarginV=150)
- Fișierul output să fie > 100KB înainte de a raporta succes

## Troubleshooting

**"Fontul nu e găsit":** Înlocuiește cu `Arial` (universal) sau specifică calea absolută a fontului.

**"ASS subtitles invisible":** Verifică conversia hex→BGR. Greșeală frecventă: #FFD700 devine &H0000D7FF, nu &H00FFD700.

**"Render lent" (>2 minute pentru clip <1 minut):** Adaugă `-preset fast` la opțiunile de encoding. Sau folosește `-c:v copy` dacă video-ul nu necesită re-encodare (subtitruri hardcodate cer re-encodare).

**"concat: file not found":** Verifică că toate căile din fișierul de concatenare sunt absolute, nu relative.

## Self-Update

Adaugă în Rules soluțiile pentru orice eroare nouă întâlnită.
