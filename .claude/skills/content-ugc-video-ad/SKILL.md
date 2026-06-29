---
name: content-ugc-video-ad
description: "Orchestrează producția completă a unui video UGC sau ad: brief → selectare engine → generare → subtitruri → upload. Skill orchestrator care combină alte skill-uri în funcție de cerință."
triggers:
  - "fă o reclamă video"
  - "video ad"
  - "ugc video"
  - "video complet"
  - "produ un clip"
  - "video de vânzare"
secrets_required:
  - KIE_API_KEY sau HEYGEN_API_KEY sau GEMINI_API_KEY
context_loads:
  - knowledge/brand-video.md
  - knowledge/produse.md
outputs:
  - video .mp4 final în /tmp/nova-video/{slug}/final.mp4
  - URL public Zernio (dacă se uploadează)
---

# Skill: Producție Video Reclamă / UGC (Orchestrator)

Acest skill nu face generare directă — orchestrează alte skill-uri în secvență logică.

## Pas 0: Brief și decizie engine

Colectează brief-ul complet dacă nu l-ai primit:
- Produsul sau serviciul
- Audiența țintă
- Tonul dorit (UGC autentic / cinematic / prezentare formală)
- Format (9:16 portrait / 16:9 landscape)
- Durată dorită (15s / 30s / 60s)

Selectează engine-ul de generare după logica:

| Dacă brief-ul cere | Engine recomandat | Skill apelat |
|-------------------|-------------------|--------------|
| Avatar realist cu lip sync, prezentare vorbită | HeyGen | vid-avatar-heygen |
| Sunet nativ în clip, narator integrat, Google Veo | Veo | vid-avatar-veo |
| UGC autentic, selfie-style, fără avatar realist | Higgsfield | vid-ugc-higgsfield |
| Produs animat dintr-o imagine existentă | Seedance | vid-avatar-seedance |
| Scenă cinematică cu efecte vizuale | Kling | vid-scene-cinematic |
| Mai multe scene rapid, fără calitate cinematică | Higgsfield | vid-scene-rapid |

Prezintă decizia utilizatorului:
> "Pe baza brief-ului, recomand [engine] pentru că [motiv]. Confirmi sau preferi altceva?"

**ÎNCHEIE TURA** — nu continua fără confirmare pe engine.

## Pas 1: Generare video

Handoff la skill-ul ales. Urmează integral pașii acelui skill (brief, cost, confirmare, execuție).

La finalizarea generării, ai calea `output_video_path`.

## Pas 2: Post-producție (opțional)

Întreabă după generare:

> "Clipul e gata. Ce adăugăm?
> 1. Subtitruri stilizate (vid-ffmpeg-edit)
> 2. Voiceover (vid-voice)
> 3. Muzică de fundal (vid-music)
> 4. Montaj avansat cu tranziții (vid-hyperframes)
> 5. Nimic, livrăm ca atare"

Poți combina opțiunile 1+2, 1+3, 2+3 etc. Execută skill-urile în ordinea aleasă.

Ordinea recomandată dacă se combină: voiceover → muzică → subtitruri (subtitrurile merg ultimele).

## Pas 3: Upload și livrare

Dacă utilizatorul vrea URL public, handoff la `tool-video-upload`.

Dacă nu, livrează calea locală a fișierului final.

Raport final către utilizator:
- Engine folosit
- Durată finală a clipului
- Post-producție aplicată
- URL public (dacă s-a uploadat) sau cale locală

## Rules

- Nu sări peste confirmarea engine-ului — utilizatorul trebuie să știe ce engine folosim și de ce
- Nu combina engine-uri fără aprobare (ex: nu genera cu HeyGen și Veo în același task fără să fi cerut)
- Post-producția este opțională — nu o aplica automat fără întrebare
- Upload-ul este opțional — nu uploada fără confirmare
