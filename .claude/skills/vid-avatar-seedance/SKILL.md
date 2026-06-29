---
name: vid-avatar-seedance
description: "Generează video cinematic cu imagine de referință via Seedance 1.5 Pro (KIE.ai). Animează o imagine statică cu mișcare naturală. Ideal pentru product shots, portrete animate și scenarii cu un personaj central."
triggers:
  - "video seedance"
  - "animează imaginea"
  - "imagine animată"
  - "product animation"
  - "seedance"
  - "kie video"
secrets_required:
  - KIE_API_KEY
context_loads:
  - knowledge/brand-video.md
  - knowledge/produse.md
note: brand-video.md conține mai multe branduri; citește secțiunea brandului ales la task
outputs:
  - video .mp4 în /tmp/nova-video/{slug}/seedance-{N}.mp4
runtime_dependencies:
  - python3
  - requests (pip install requests)
---

# Skill: Generare Video Seedance via KIE.ai

## Pas 0: Citește contextul și selectează brandul

**Identifică brandul:**
Dacă brief-ul nu specifică un brand, întreabă: "Pentru ce brand generăm video-ul?"

Citește `knowledge/brand-video.md` și găsește secțiunea brandului menționat.

Dacă brandul nu e în catalog (sau catalogul e gol):
> "Brandul [NUME] nu are configurație salvată. Cum procedăm?
> 1. Configurăm acum: format (9:16/16:9), watermark
> 2. Folosesc default-uri: 9:16, fără watermark"

## Pas 1: Primește sau generează imaginea de referință

Seedance animează o imagine existentă. Verifică dacă utilizatorul a furnizat o imagine.

Dacă **nu** a furnizat imagine:
> "Seedance are nevoie de o imagine de referință pentru a o anima. Opțiuni:
> 1. Trimiți tu o imagine (JPG/PNG)
> 2. Generăm o imagine cu KIE.ai Flux mai întâi (handoff la skill img-product-photo)
> 3. Folosesc un URL de imagine publicăe"

**ÎNCHEIE TURA** — nu continua fără o imagine de referință confirmată.

## Pas 2: Scrie promptul de animație

Promptul descrie MIȘCAREA dorită, nu subiectul (subiectul e în imagine).

Bune practici:
- Descrie camera: "slow dolly in", "gentle pan left", "camera rotates 30 degrees"
- Descrie mișcarea subiectului: "hair flows gently", "steam rises slowly", "product rotates on axis"
- Evită schimbări dramatice de scenă sau personaje noi
- Max 150 cuvinte

Dacă utilizatorul a dat un brief, propune un prompt de animație și cere confirmare:
> "Propun promptul de animație: [prompt]. Confirmi sau ajustăm?"

## Pas 3: Avertizare cost și confirmare

Calculează costul estimat:

```
Model implicit: seedance-1.5-pro
Durată default: 5 secunde
Cost: 5s × 3.6 credite/s = 18 credite = $0.09
Credite KIE.ai: 1 credit = $0.005
```

Trimite utilizatorului:
> "Generare Seedance 1.5 Pro, 5 secunde.
> Cost estimat: ~18 credite ($0.09).
> Confirmi?"

**Nu genera fără confirmare explicită.**

## Pas 4: Execuție

Identifică sursa imaginii de referință (fișier local sau URL):

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
OUTPUT_SLUG="seedance-$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="/tmp/nova-video/${OUTPUT_SLUG}"
mkdir -p "${OUTPUT_DIR}"

# Cu fișier local (dacă utilizatorul a trimis o imagine):
python3 .claude/skills/vid-avatar-seedance/scripts/kie_video.py \
  "<prompt_animatie>" \
  "${OUTPUT_DIR}/seedance-1.mp4" \
  --reference "/calea/catre/imagine.jpg"

# Cu URL public:
python3 .claude/skills/vid-avatar-seedance/scripts/kie_video.py \
  "<prompt_animatie>" \
  "${OUTPUT_DIR}/seedance-1.mp4" \
  --reference-url "https://url-imagine.com/image.jpg"
```

Parsează output-ul JSON:
- `output_path` — calea fișierului generat
- `task_id` — ID-ul task-ului KIE.ai (util pentru debug)
- `credits` — credite consumate
- `cost_time_s` — timp de generare în secunde

Dacă output-ul conține `"error"`, raportează eroarea completă și oprește.

## Pas 5: Self-QA și livrare

```bash
FILE_SIZE=$(du -k "${OUTPUT_DIR}/seedance-1.mp4" 2>/dev/null | cut -f1)
echo "Dimensiune fișier: ${FILE_SIZE}KB"
```

Criterii de acceptare:
- Fișierul există: da/nu
- Dimensiune > 200KB: da/nu (sub 200KB = generare eșuată sau clip gol)

Raportează utilizatorului:
- Model folosit (seedance-1.5-pro)
- Durată reală (din `cost_time_s`)
- Credite consumate (din `credits`)
- Calea completă a fișierului

Întreabă: "Continui cu subtitruri/muzică sau uploadăm direct (handoff la tool-video-upload)?"

## Alternativă: kie-mcp

Dacă MCP-ul kie-mcp e disponibil în sesiune (`mcp__kie__*`), poți folosi tool-urile MCP direct în loc de scriptul Python. Avantaj: mai simplu, fără subprocess. Dezavantaj: mai puțin control pe polling și download.

## Rules

- Avertizarea cost cu calcul explicit este OBLIGATORIE înainte de orice generare
- Nu genera fără confirmare explicită pe cost
- Promptul de animație trebuie prezentat și confirmat înainte de execuție
- Imaginea de referință este OBLIGATORIE — Seedance nu generează din prompt pur
- Fișierul video trebuie să existe și să fie > 200KB înainte de livrare
- La Pas 1, încheie tura dacă nu există imagine — nu improviza

## Self-Update

Dacă utilizatorul semnalează o problemă cu output-ul, adaugă în secțiunea Rules o linie cu formatul:
`- [YYYY-MM-DD] corecție: [descriere scurtă a problemei și soluției]`
Nu șterge reguli existente. Adaugă doar în josul listei.
