---
name: vid-hyperframes
description: "Montaj avansat short-form via Hyperframes: compune clipuri generate sau footage real într-un HTML cu animații GSAP, tranziții și captions sincronizate, apoi randează MP4."
triggers:
  - "montaj avansat"
  - "hyperframes"
  - "compoziție video"
  - "animații pe video"
  - "tranziții stilizate"
  - "captions sincronizate"
  - "short-form avansat"
  - "reclame stilizate"
negative_triggers:
  - "generează video din zero"
  - "avatar"
  - "lip sync"
  - "UGC"
inputs:
  - clips (obligatoriu: list de căi MP4 sau URL-uri)
  - brief (obligatoriu: ce trebuie să comunice video-ul)
  - brand (opțional: calea spre frame.md sau design.md cu identitate vizuală)
  - transcript (opțional: text sau SRT pentru captions sincronizate)
outputs:
  - MP4 final randat la ./output/final.mp4
runtime_dependencies:
  - npx hyperframes (instalat global sau local via npm)
  - Chrome/Chromium (pentru render headless)
---

# Skill: Montaj Avansat cu Hyperframes

## Când folosești acest skill vs ffmpeg

| Situație | Alege |
|----------|-------|
| Subtitruri simple pe un clip | ffmpeg (vid-ffmpeg-edit) |
| Concatenare scenă cu scenă, fără animații | ffmpeg |
| Reclame short-form cu text animat, tranziții, brand | Hyperframes |
| Prezentare produs cu mai multe clipuri + overlays | Hyperframes |
| Captions karaoke sincronizate la voiceover | Hyperframes |
| Orice video unde brandingul și mișcarea contează | Hyperframes |

## Pas 0: Verifică Hyperframes

```bash
npx hyperframes --version 2>/dev/null || echo "LIPSĂ"
```

Dacă lipsește:
```bash
npm install -g hyperframes
```

## Pas 1: Citește identitatea vizuală

Caută în ordine:
1. `knowledge/brand-video.md` — secțiunea brandului activ
2. `frame.md` sau `design.md` în folderul proiectului
3. Dacă nimic nu există, întreabă: "Ce culori și font vrei pe video?"

Extrage:
- `CULOARE_PRIMARA` (hex)
- `CULOARE_TEXT` (hex)
- `FONT` (ex: Arial, Inter, Montserrat)

**Nu inventa culori. Nu folosi #333 sau #3b82f6 ca default.**

## Pas 2: Creează folderul de compoziție

```bash
mkdir -p ./hyperframes-output
cd ./hyperframes-output
```

Copiază clipurile sursă sau referențiază căile absolute.

## Pas 3: Scrie index.html

Structura de bază pentru o compoziție cu clipuri multiple:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
</head>
<body>
  <div data-composition-id="root" data-width="1080" data-height="1920">

    <!-- Clip 1 -->
    <video
      id="clip-1"
      data-start="0"
      data-duration="5"
      data-track-index="0"
      src="../CALE_CLIP_1.mp4"
      muted playsinline>
    </video>

    <!-- Clip 2 -->
    <video
      id="clip-2"
      data-start="5"
      data-duration="5"
      data-track-index="0"
      src="../CALE_CLIP_2.mp4"
      muted playsinline>
    </video>

    <!-- Text overlay -->
    <div id="titlu"
      class="clip"
      data-start="0.5"
      data-duration="4"
      data-track-index="1"
      style="
        position: absolute;
        bottom: 200px;
        left: 0; right: 0;
        text-align: center;
        font-family: FONT;
        font-size: 80px;
        font-weight: 900;
        color: CULOARE_TEXT;
      ">
      TEXT TITLU
    </div>

    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <script>
      window.__timelines = window.__timelines || {};
      const tl = gsap.timeline({ paused: true });

      // Entrance animații — întotdeauna gsap.from()
      tl.from("#titlu", { y: 60, opacity: 0, duration: 0.6, ease: "power3.out" }, 0.5);

      window.__timelines["root"] = tl;
    </script>
  </div>
</body>
</html>
```

**Reguli obligatorii:**
- Video-ul întotdeauna `muted playsinline`
- Audio separat ca `<audio>` element dacă e necesar
- `gsap.from()` pentru intrări, niciodată `gsap.to()` cu opacity 0 înainte de tranziție (excepție: ultima scenă)
- `window.__timelines["root"] = tl` obligatoriu

## Pas 4: Adaugă captions (dacă există transcript)

Citește `references/captions.md` din skill-ul global Hyperframes pentru sintaxa exactă.

Pattern de bază pentru captions sincronizate la voiceover:

```js
// În script, după timeline-ul principal
const captions = [
  { start: 0.5, end: 2.0, text: "Prima frază" },
  { start: 2.2, end: 4.0, text: "A doua frază" },
];

captions.forEach(({ start, end, text }) => {
  const el = document.createElement("div");
  el.className = "caption clip";
  el.dataset.start = start;
  el.dataset.duration = end - start;
  el.dataset.trackIndex = "2";
  el.textContent = text;
  document.querySelector("[data-composition-id='root']").appendChild(el);
  tl.from(el, { opacity: 0, y: 20, duration: 0.2 }, start);
});
```

## Pas 5: Validează și previzualizează

```bash
cd ./hyperframes-output

# Verifică sintaxa
npx hyperframes lint

# Validează timing și contrast
npx hyperframes validate

# Previzualizare în browser
npx hyperframes preview
```

Rezolvă toate erorile de la `lint` și `validate` înainte să continui.

## Pas 6: Randează MP4

```bash
npx hyperframes render --output ../output/final.mp4
```

Verifică output:
```bash
SIZE_KB=$(du -k "../output/final.mp4" | cut -f1)
echo "Output: ${SIZE_KB}KB"
[ "$SIZE_KB" -lt 500 ] && echo "AVERTISMENT: fișier suspect de mic"
```

## Pas 7: Raportează

Trimite utilizatorului:
- Calea fișierului: `./output/final.mp4`
- Dimensiunea
- Durata totală (din metadata)
- "Gata de publicat sau vrei ajustări?"

## Tranziții între scene

Citește `references/transitions.md` din skill-ul global Hyperframes.

Shortcut pentru crossfade simplu între două scene la timestamp `T`:

```js
// Overlay negru pentru crossfade
tl.to("#overlay", { opacity: 1, duration: 0.4, ease: "power2.in" }, T - 0.4);
tl.to("#overlay", { opacity: 0, duration: 0.4, ease: "power2.out" }, T);
```

## Rules

- Niciodată `ffmpeg` și `Hyperframes` pe același clip în serie — alege unul
- `lint` și `validate` trec înainte de render, fără excepții
- Culorile vin din `knowledge/brand-video.md`, nu inventate
- Output > 500KB înainte de a raporta succes
- Dacă render durează >5 min, verifică că Chrome e instalat și că nu lipsesc clipuri

## Self-Update

Adaugă în Rules orice eroare nouă întâlnită și soluția ei.
