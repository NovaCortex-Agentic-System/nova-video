---
name: vid-ugc-higgsfield
description: "Generează reclamă UGC (user-generated content style) via Higgsfield MCP. Selfie-style autentic, produs în acțiune sau testimonial fără avatar realist. Opțional: adaugă voiceover ElevenLabs via vid-voice."
triggers:
  - "reclamă UGC"
  - "video autentic"
  - "selfie style"
  - "produs în acțiune"
  - "video Higgsfield"
  - "UGC ad"
  - "video social media rapid"
negative_triggers:
  - "avatar"
  - "lip sync"
  - "mai multe scene"
  - "multi-scenă"
  - "cinematic"
inputs:
  - brief (obligatoriu: produs, mesaj cheie, publicul țintă)
  - brand (opțional: din knowledge/brand-video.md)
outputs:
  - video .mp4 la /tmp/nova-video/{slug}/ugc-{N}.mp4
runtime_dependencies:
  - Higgsfield MCP (mcp__higgsfield__generate_video disponibil)
secrets_required: []
context_loads:
  - knowledge/brand-video.md
  - knowledge/produse.md
---

# Skill: Reclamă UGC via Higgsfield

## Pas 0: Citește contextul

Citește `knowledge/brand-video.md` și identifică brandul. Dacă brandul nu e în catalog, folosește default-uri: 9:16, fără restricții de culoare.

Citește `knowledge/produse.md` pentru detalii despre produs dacă e menționat în brief.

## Pas 1: Construiește prompt-ul UGC

Stilul UGC pentru Higgsfield are câteva reguli fixe:

**Structura promptului:**
```
A person [acțiune autentică: holds, shows, tries, demonstrates].
[Descriere produs: ce face, cum arată, beneficiul principal].
[Context vizual: locație, lumină naturală, telefon la mână sau nu].
[Ton: candid, real, imperfect — nu studio, nu comercial].
```

**Exemple de prompts bune:**
- "A young woman sits on her couch, holds up a small skincare bottle, looks at camera with a relaxed expression, natural window light, candid home setting"
- "A man in a kitchen demonstrates a kitchen gadget, casual t-shirt, genuine surprised expression when it works, handheld camera feel"

**Cuvinte interzise în prompt:** professional, studio, cinematic, commercial, perfect, stunning, 8k, advertisement

**Format:** 9:16 pentru TikTok/Reels, 16:9 dacă utilizatorul cere YouTube.

## Pas 2: Avertizare cost și confirmare

Higgsfield are plan propriu (nu credite kie.ai). Înainte de generare, confirmă:

> "Generez via Higgsfield MCP (conform planului tău Higgsfield). Durată: [durată]s, format: [format].
> Prompt: [prompt construit]
> Confirmi?"

Nu genera fără confirmare.

## Pas 3: Generează via Higgsfield MCP

Apelează tool-ul MCP `mcp__higgsfield__generate_video` cu parametrii:
- `prompt`: promptul construit la Pas 1
- `aspect_ratio`: "9:16" sau "16:9"
- `duration`: durata în secunde (default: 8)

Salvează URL-ul video-ului returnat.

Descarcă local:
```bash
OUTPUT_DIR="/tmp/nova-video/$(date +%Y%m%d-%H%M%S)"
mkdir -p "${OUTPUT_DIR}"
OUTPUT_PATH="${OUTPUT_DIR}/ugc-1.mp4"
curl -L -o "${OUTPUT_PATH}" "${VIDEO_URL}"
```

## Pas 4: Self-QA

```bash
FILE_SIZE=$(du -k "${OUTPUT_PATH}" 2>/dev/null | cut -f1)
echo "Dimensiune: ${FILE_SIZE}KB"
```

Sub 100KB = probabil eroare. Raportează și nu livra.

## Pas 5: Voiceover (opțional)

Întreabă utilizatorul:
> "Adăugăm voiceover? (ElevenLabs via kie.ai, ~$0.075 pentru 30s) — sau livrăm clipul fără sunet?"

Dacă da: activează skill-ul `vid-voice` și transmite calea clipului și textul de citit.
Dacă nu: treci la Pas 6.

## Pas 6: Livrare

Trimite utilizatorului:
- Calea fișierului local
- Dimensiunea fișierului
- "Mai adăugăm subtitruri (vid-ffmpeg-edit) sau e gata de publicat?"

## Rules

- Nu genera niciodată fără confirmare explicită
- Cuvintele interzise sunt blocante, nu advisory
- Descarcă întotdeauna local înainte de livrare — nu trimite doar URL-ul Higgsfield
- Fișierul trebuie să fie > 100KB înainte de a raporta succes
- Higgsfield generează max ~8 secunde per apel. Dacă durata cerută > 8s, fă mai multe apeluri (ex: 20s = 3 clipuri), variind vizual promptul (unghi cameră, acțiune, expresie) și transmite lista de clipuri la vid-reel pentru concatenare. Nu anunța utilizatorul despre limita tehnică — gestioneaz-o transparent.

## Self-Update

Adaugă în Rules soluțiile pentru orice eroare nouă întâlnită cu formatul:
`- [YYYY-MM-DD] corecție: [descriere problemă și soluție]`
