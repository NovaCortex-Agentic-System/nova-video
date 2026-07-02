---
name: vid-avatar-heygen-create
description: "Creează un avatar persistent din fotografie via HeyGen CLI. Rulează o singură dată per persoană/brand. Avatarul rezultat (look_id) se salvează în knowledge/brand-video.md și se reutilizează la orice video ulterior via vid-avatar-heygen."
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
  - heygen CLI (curl -fsSL https://static.heygen.ai/cli/install.sh | bash)
---

# Skill: Creare Avatar Persistent HeyGen

## Pas 0: Verifică dacă avatarul există deja

Citește `knowledge/brand-video.md`. Dacă brandul are deja `heygen_look_id`:
> "Brandul [NUME] are deja avatarul configurat (look_id: [ID]). Folosim acesta sau creăm unul nou?"

Dacă vrea cel existent → handoff la `vid-avatar-heygen`.
Dacă vrea unul nou → continuă la Pas 1.

## Pas 1: Primește fotografia

> "Trimite fotografia pentru avatar. Cerințe HeyGen:
> - Format: JPG sau PNG
> - Față vizibilă, față spre cameră, fără ochelari de soare
> - Fundal curat (alb sau uniform preferat)
> - Rezoluție minimă: 512×512 px
>
> Trimite un URL public al fotografiei."

Dacă utilizatorul trimite fișier local via Telegram → uploadează pe Zernio via `tool-video-upload` pentru URL public, apoi continuă.

**ÎNCHEIE TURA** — nu continua fără URL confirmat.

## Pas 2: Primește denumirea avatarului

> "Cum denumim avatarul? (ex: 'Dan Mitruț — Trainer', 'Maria — Sales')"

**ÎNCHEIE TURA** — nu continua fără denumire.

## Pas 3: Uploadează fotografia ca asset și creează avatarul

```bash
cd "${CTX_AGENT_DIR}"
set -a; source .env; set +a

# Pasul 3a: Creează avatarul (photo_avatar din URL public)
RESULT=$(heygen avatar create -d '{
  "name": "<DENUMIRE>",
  "type": "photo",
  "image": {"type": "url", "url": "<URL_FOTOGRAFIE>"}
}')
```

Dacă CLI-ul `avatar create` nu suportă `-d` (verifică cu `heygen avatar create --help`), folosește schema:
```bash
heygen avatar create --request-schema
```
și adaptează comanda conform schemei returnate.

Parsează răspunsul JSON:
- Dacă conține `"error"` → raportează eroarea completă și oprește
- Dacă `"status": "ok"` sau similar → extrage `look_id` și `group_id`

## Pas 4: Salvează în catalog

```bash
cat >> "${CTX_AGENT_DIR}/knowledge/brand-video.md" << EOF

## Avatar: <DENUMIRE>
- heygen_look_id: <LOOK_ID>
- heygen_group_id: <GROUP_ID>
- creat: $(date -u +%Y-%m-%d)
EOF
```

Raportează:
> "Avatar creat cu succes!
> - Nume: [DENUMIRE]
> - look_id: [LOOK_ID]
>
> Salvat în catalog. Poți genera acum un video cu:
> 'video cu avatar [DENUMIRE] care spune [SUBIECT]'"

## Rules

- Nu crea un avatar dacă brandul are deja un look_id valid în catalog
- Fotografia TREBUIE să fie URL public înainte de apelul API
- Salvează ÎNTOTDEAUNA look_id în knowledge/brand-video.md după creare reușită
- Nu continua la Pas 3 fără denumire confirmată
- La eroare API, raportează răspunsul complet — nu interpreta, nu presupune
- Dacă `heygen avatar create` nu suportă `--type photo` direct, rulează `--request-schema` și adaptează

## Self-Update

Dacă utilizatorul semnalează o problemă, adaugă în Rules:
`- [YYYY-MM-DD] corecție: [descriere scurtă]`
