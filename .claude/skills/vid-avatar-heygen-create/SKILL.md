---
name: vid-avatar-heygen-create
description: "Creează un avatar persistent din fotografie via HeyGen API. Rulează o singură dată per persoană/brand. Avatarul rezultat (look_id) se salvează în knowledge/brand-video.md și se reutilizează la orice video ulterior via vid-avatar-heygen."
triggers:
  - "creează avatar heygen"
  - "avatar din poză"
  - "avatar persistent"
  - "înregistrează avatar"
  - "photo avatar heygen"
  - "avatar nou heygen"
secrets_required:
  - HEYGEN_API_KEY
context_loads:
  - knowledge/brand-video.md
outputs:
  - look_id salvat în knowledge/brand-video.md
runtime_dependencies:
  - python3
  - requests (pip install requests)
---

# Skill: Creare Avatar Persistent HeyGen

Creează un Photo Avatar persistent din fotografie și îl salvează în catalogul de branduri pentru reutilizare la toate video-urile viitoare.

## Pas 0: Verifică dacă avatarul există deja

Citește `knowledge/brand-video.md`. Dacă brandul menționat are deja un câmp `heygen_look_id` completat, NU crea un avatar nou.

Mesaj utilizator:
> "Brandul [NUME] are deja avatarul configurat (look_id: [ID]). Îl folosim pe acesta sau vrei să creezi unul nou cu o altă fotografie?"

Dacă vrea să continue cu cel existent → handoff la `vid-avatar-heygen`.
Dacă vrea unul nou → continuă la Pas 1.

## Pas 1: Primește fotografia

Cere utilizatorului:
> "Trimite fotografia pentru avatar. Cerințe HeyGen:
> - Format: JPG sau PNG
> - Față vizibilă, față spre cameră, fără ochelari de soare
> - Fundal curat (alb sau uniform preferat)
> - Rezoluție minimă: 512×512 px
>
> Trimite un URL public al fotografiei."

Dacă utilizatorul trimite un fișier local via Telegram → fotografia ajunge cu `local_file:` în mesaj. Uploadează-o pe Zernio via skill-ul `tool-video-upload` pentru a obține un URL public, apoi continuă cu URL-ul.

**ÎNCHEIE TURA** — nu continua fără URL fotografiei.

## Pas 2: Primește denumirea avatarului

Cere:
> "Cum denumim avatarul? (ex: 'Dan Mitruț — Trainer', 'Maria — Sales', 'Avatar Brand X')"

**ÎNCHEIE TURA** — nu continua fără denumire.

## Pas 3: Creează avatarul

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a

python3 .claude/skills/vid-avatar-heygen/scripts/heygen_v3.py \
  --create-avatar \
  --avatar-name "<DENUMIRE>" \
  --avatar-photo-url "<URL_FOTOGRAFIE>"
```

Parsează JSON-ul returnat:
- Dacă conține `"error"` → raportează eroarea completă și oprește.
- Dacă `"status": "ok"` → extrage `look_id` și `group_id` din output.

## Pas 4: Salvează în catalog

```bash
cat >> "${CTX_AGENT_DIR}/knowledge/brand-video.md" << EOF

## Avatar: <DENUMIRE>
- heygen_look_id: <LOOK_ID>
- heygen_group_id: <GROUP_ID>
- creat: $(date -u +%Y-%m-%d)
EOF
```

Raportează utilizatorului:
> "Avatar creat cu succes!
> - Nume: [DENUMIRE]
> - look_id: [LOOK_ID]
>
> Salvat în catalogul de branduri. Poți genera acum un video cu:
> 'video cu avatar [DENUMIRE] care spune [SUBIECT]'"

## Rules

- Nu crea un avatar dacă brandul are deja un look_id valid în catalog
- Fotografia TREBUIE să fie URL public înainte de apelul API
- Salvează ÎNTOTDEAUNA look_id în knowledge/brand-video.md după creare reușită
- Nu continua la Pas 3 fără denumire confirmată
- La eroare API, raportează răspunsul complet — nu interpreta, nu presupune

## Self-Update

Dacă utilizatorul semnalează o problemă, adaugă în Rules:
`- [YYYY-MM-DD] corecție: [descriere scurtă a problemei și soluției]`
