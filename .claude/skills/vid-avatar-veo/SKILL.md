---
name: vid-avatar-veo
description: "Generează video text-to-video via Google Veo (Gemini API). Audio nativ inclus în generare. Ideal pentru scenarii cu narator, reclame cu voiceover integrat sau scene cinematice cu sunet."
triggers:
  - "video veo"
  - "google veo"
  - "veo 3"
  - "video cu audio nativ"
  - "gemini video"
  - "text to video google"
secrets_required:
  - GEMINI_API_KEY
context_loads:
  - knowledge/brand-video.md
note: brand-video.md conține mai multe branduri; citește secțiunea brandului ales la task
outputs:
  - video .mp4 în /tmp/nova-video/{slug}/veo-{N}.mp4
runtime_dependencies:
  - python3
  - requests (pip install requests)
---

# Skill: Generare Video via Google Veo

## Pas 0: Citește contextul și selectează brandul

**Identifică brandul:**
Dacă brief-ul nu specifică un brand, întreabă: "Pentru ce brand generăm video-ul?"

Citește `knowledge/brand-video.md` și găsește secțiunea brandului menționat.

## Pas 1: Selectează modelul și parametrii

| Model | Preț | Calitate | Când |
|-------|------|----------|------|
| `veo-3.1-lite-generate-preview` | $0.05/s | Bun | Default, draft, testare |
| `veo-3.1-fast-generate-preview` | $0.10/s | Mai bun | Livrare, calitate medie |
| `veo-3.1-generate-preview` | $0.40/s | Cel mai bun | Hero shots, livrare finală |

Parametri impliciti:
- Durată: 8 secunde
- Rezoluție: 720p
- Aspect ratio: 9:16 (portrait)

Dacă utilizatorul nu specifică modelul, folosește `veo-3.1-lite-generate-preview` și informează-l.

## Pas 2: Scrie sau primește promptul

Promptul bun pentru Veo descrie:
1. **Scena**: ce vedem în cadru (locație, lumină, atmosferă)
2. **Personajul/subiectul**: ce face, cum arată
3. **Camera**: mișcare cameră dacă e relevantă (slow zoom, tracking shot)
4. **Audio** (opțional): dacă vrei sunet specific (muzică ambientală, vorbire, efecte)

Veo 3 generează audio nativ — dacă promptul menționează vorbire sau muzică, le va include.

Dacă utilizatorul a dat un brief, propune un prompt și cere confirmare:
> "Propun promptul: [prompt]. Confirmi sau ajustăm?"

**Nu continua la Pas 3 fără confirmare explicită pe prompt.**

## Pas 3: Avertizare cost și confirmare

Calculează costul estimat:

```
Cost = durata_secunde × preț_per_secundă
Exemplu lite, 8s: 8 × $0.05 = $0.40
Exemplu fast, 8s: 8 × $0.10 = $0.80
Exemplu standard, 8s: 8 × $0.40 = $3.20
```

Trimite utilizatorului:
> "Generare Veo [MODEL], [N] secunde.
> Cost estimat: ~$[X].
> Confirmi?"

**Nu genera fără confirmare explicită.**

## Pas 4: Execuție

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
OUTPUT_SLUG="veo-$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="/tmp/nova-video/${OUTPUT_SLUG}"
mkdir -p "${OUTPUT_DIR}"

python3 .claude/skills/vid-avatar-veo/scripts/veo_video.py \
  "<prompt>" \
  "${OUTPUT_DIR}/veo-1.mp4" \
  --model veo-3.1-lite-generate-preview \
  --duration 8 \
  --aspect 9:16 \
  --resolution 720p
```

Cu imagine de referință (opțional):
```bash
python3 .claude/skills/vid-avatar-veo/scripts/veo_video.py \
  "<prompt>" \
  "${OUTPUT_DIR}/veo-1.mp4" \
  --reference "/calea/catre/imagine.jpg"
```

Parsează output-ul JSON:
- `output_path` — calea fișierului generat
- `operation_name` — ID-ul operației Gemini (util pentru debug)
- `duration_s` — durată în secunde

Dacă output-ul conține `"error"`, raportează eroarea completă și oprește.

## Pas 5: Self-QA și livrare

```bash
FILE_SIZE=$(du -k "${OUTPUT_DIR}/veo-1.mp4" 2>/dev/null | cut -f1)
echo "Dimensiune fișier: ${FILE_SIZE}KB"
```

Criterii de acceptare:
- Fișierul există: da/nu
- Dimensiune > 500KB: da/nu (sub 500KB = generare eșuată)

Raportează utilizatorului:
- Model folosit
- Durată reală
- Cost estimat bazat pe durată reală
- Calea completă a fișierului
- Dacă a inclus audio nativ (da dacă promptul menționa vorbire/muzică)

Întreabă: "Continui cu subtitruri sau uploadăm direct (handoff la tool-video-upload)?"

## Rules

- Avertizarea cost cu calcul explicit este OBLIGATORIE înainte de orice generare
- Nu genera fără confirmare explicită pe cost
- Promptul trebuie prezentat și confirmat înainte de execuție
- Modelul implicit este `veo-3.1-lite-generate-preview` ($0.05/s)
- Fișierul video trebuie să existe și să fie > 500KB înainte de livrare
- Audio nativ e inclus automat dacă promptul îl menționează

## Self-Update

Dacă utilizatorul semnalează o problemă cu output-ul, adaugă în secțiunea Rules o linie cu formatul:
`- [YYYY-MM-DD] corecție: [descriere scurtă a problemei și soluției]`
Nu șterge reguli existente. Adaugă doar în josul listei.
