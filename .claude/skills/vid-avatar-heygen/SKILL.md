---
name: vid-avatar-heygen
description: "Generează video talking head cu avatar realist via HeyGen API. Avatarul vorbește un script text cu lip sync precis. Ideal pentru prezentări, tutoriale și explicații — nu pentru reclame cinematice (acelea merg pe vid-scene-cinematic)."
triggers:
  - "video heygen"
  - "avatar realist"
  - "talking head"
  - "prezentare video"
  - "avatar vorbitor"
  - "lip sync"
secrets_required:
  - HEYGEN_API_KEY
context_loads:
  - knowledge/brand-video.md
  - knowledge/produse.md
note: brand-video.md conține mai multe branduri; citește secțiunea brandului ales la task
outputs:
  - video .mp4 în /tmp/nova-video/{slug}/heygen-{N}.mp4
runtime_dependencies:
  - python3
  - requests (pip install requests)
---

# Skill: Generare Video Avatar HeyGen

## Pas 0: Citește contextul și selectează brandul

**Identifică brandul:**
Dacă brief-ul nu specifică un brand, întreabă: "Pentru ce brand generăm video-ul?"

Citește `knowledge/brand-video.md` și găsește secțiunea brandului menționat.

Dacă brandul nu e în catalog (sau catalogul e gol):
> "Brandul [NUME] nu are configurație salvată. Cum procedăm?
> 1. Configurăm acum: culoare subtitruri, font, format (9:16/16:9), watermark
> 2. Folosesc default-uri: 16:9, Arial Bold, #FFD700, fără watermark"

Dacă alege 1, cere toate 4 preferințele într-un singur mesaj și adaugă brandul în catalog:
```bash
cat >> "${CTX_AGENT_DIR}/knowledge/brand-video.md" << EOF

## [BRAND_NAME]
- Culoare subtitruri: [CULOARE]
- Font: [FONT]
- Aspect ratio: [RATIO]
- Rezoluție: [REZOLUTIE]
- Watermark: [WATERMARK]
EOF
```

**Citește produsul dacă e menționat în brief:**
Dacă brief-ul menționează un produs specific care NU apare în `knowledge/produse.md`, întreabă: "Produsul [NUME] nu e în catalogul meu. Îl adăugăm acum sau continui cu o descriere generică?"

## Pas 1: Selectează avatarul și vocea

Verifică dacă utilizatorul a specificat deja un avatar și o voce. Dacă le-a specificat, sari direct la Pas 2.

Dacă nu, listează avatarele disponibile:

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
python3 .claude/skills/vid-avatar-heygen/scripts/heygen_video.py --list-avatars
```

Prezintă primele 10 avatare (ID, nume, stil) și întreabă utilizatorul să aleagă.

Apoi listează vocile:

```bash
python3 .claude/skills/vid-avatar-heygen/scripts/heygen_video.py --list-voices
```

Filtrează vocile în română dacă există în listă. Dacă nu există voci în română, prezintă top 10 voci în engleză cu accent neutru.

**ÎNCHEIE TURA** — nu continua cu Pas 2 fără confirmare avatar + voce din partea utilizatorului.

## Pas 2: Scrie sau primește scriptul

Dacă utilizatorul a dat un script complet, folosește-l direct (sari la Pas 3).

Dacă a dat un brief sau o idee, scrie scriptul respectând:
- Max 200 cuvinte (corespunde la ~90 secunde vorbire)
- Ton conversațional, nu formal sau marketing agresiv
- Primele 5 cuvinte = hook care captează atenția imediat
- Fără fraze de umplutură de tipul "Bună ziua, mă numesc..."
- Dacă brief-ul menționează un produs din `knowledge/produse.md`, include beneficiul principal al produsului

Prezintă scriptul și cere confirmare:
> "Iată scriptul propus ([N] cuvinte, ~[M] secunde). Confirmi sau îl ajustăm?"

**Nu continua la Pas 3 fără confirmare explicită pe script.**

## Pas 3: Avertizare cost și confirmare

Calculează costul estimat înainte de generare:

```
Minute video = număr cuvinte ÷ 150
Secunde video = minute × 60
Cost Avatar III Photo  = secunde × $0.043  ← default recomandat
Cost Avatar III Twin   = secunde × $0.017  ← cel mai ieftin
Cost Avatar IV Photo   = secunde × $0.05   ← calitate mai bună
Cost Avatar IV Twin    = secunde × $0.067  ← calitate maximă
```

Trimite utilizatorului calculul explicit:
> "Script de [N] cuvinte = ~[M] secunde video.
> Cost estimat: ~$[X] cu Avatar III Photo (recomandat) sau ~$[Y] cu Avatar IV.
> Continui cu [avatar ales]?"

Așteaptă confirmarea. **Nu genera fără confirmare explicită.**

Dacă utilizatorul răspunde "nu": întreabă "Vrei să scurtăm scriptul, alegem un avatar mai ieftin sau oprim?" Nu continua cu generarea.

## Pas 4: Execuție

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a
OUTPUT_SLUG="heygen-$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="/tmp/nova-video/${OUTPUT_SLUG}"
mkdir -p "${OUTPUT_DIR}"

python3 .claude/skills/vid-avatar-heygen/scripts/heygen_video.py \
  "<script_text>" \
  "${OUTPUT_DIR}/heygen-1.mp4" \
  --avatar <avatar_id> \
  --voice <voice_id> \
  --aspect <ratio_din_brand_catalog>
```

Parsează output-ul JSON returnat de script. Extrage:
- `output_path` — calea fișierului generat
- `video_id` — ID-ul sesiunii HeyGen (util pentru debug)
- `duration_s` — durata reală a clipului în secunde

Dacă output-ul conține `"error"`, raportează eroarea completă și oprește.

## Pas 5: Self-QA și livrare

Verifică fișierul generat:

```bash
FILE_SIZE=$(du -k "${OUTPUT_DIR}/heygen-1.mp4" 2>/dev/null | cut -f1)
echo "Dimensiune fișier: ${FILE_SIZE}KB"
```

Criterii de acceptare:
- Fișierul există: da/nu
- Dimensiune > 100KB: da/nu (sub 100KB = generare eșuată sau clip gol)
- `duration_s` din JSON corespunde cu estimarea din Pas 3: da/nu

Raportează utilizatorului:
- Avatar folosit (ID + nume)
- Durată reală (din `duration_s`)
- Cost estimat pe baza duratei reale
- Calea completă a fișierului

Întreabă: "Continui cu subtitruri (handoff la vid-ffmpeg-edit) sau uploadăm direct (handoff la tool-video-upload)?"

## Rules

- Avertizarea cost cu calcul explicit este OBLIGATORIE înainte de orice generare
- Nu genera fără confirmare explicită pe cost
- Scriptul trebuie prezentat și confirmat înainte de trimitere la API
- Aspect ratio din `knowledge/brand-video.md`, nu inventat
- Fișierul video trebuie să existe și să fie > 100KB înainte de livrare
- La Pas 1, încheie tura după prezentarea avatarelor și vocilor — nu continua fără răspuns

## Self-Update

Dacă utilizatorul semnalează o problemă cu output-ul, adaugă în secțiunea Rules o linie cu formatul:
`- [YYYY-MM-DD] corecție: [descriere scurtă a problemei și soluției]`
Nu șterge reguli existente. Adaugă doar în josul listei.
