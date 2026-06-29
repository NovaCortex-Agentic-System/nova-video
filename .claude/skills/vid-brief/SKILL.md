---
name: vid-brief
description: "Intake brief video și selectează produsul potrivit din cele 3 disponibile: AVATAR (HeyGen), UGC (Higgsfield), MULTI-SCENĂ (Higgsfield rapid sau Kling cinematic). Propune și confirmă cu utilizatorul înainte de execuție."
triggers:
  - "vreau un video"
  - "fă un video"
  - "am nevoie de un video"
  - "video pentru"
  - "reclamă video"
  - "brief video"
  - "ce video facem"
negative_triggers:
  - "generează scena"
  - "adaugă subtitruri"
  - "voiceover"
  - "muzică"
inputs:
  - brief (obligatoriu: descriere produs/obiectiv, sau raw text de la utilizator)
outputs:
  - decizie produs (AVATAR / UGC / MULTI-SCENĂ rapid / MULTI-SCENĂ cinematic)
  - parametri inițiali: brand, format, ton
context_loads:
  - knowledge/brand-video.md
  - knowledge/produse.md
---

# Skill: Brief și selecție produs video

## Pas 0: Citește cunoașterea disponibilă

Citește `knowledge/produse.md` și `knowledge/brand-video.md` pentru context.

Dacă catalogul de produse e gol, continuă fără el — utilizatorul va da detaliile în brief.

## Pas 1: Înțelege brief-ul

Dacă utilizatorul a trimis deja un brief detaliat (produs, obiectiv, format dorit): extrage informațiile și sari la Pas 2.

Dacă brief-ul e vag (ex: "vreau un video pentru cursul meu"), pune o singură întrebare care acoperă tot:

> "Pentru ce anume facem video-ul? Spune-mi: ce promovezi, cui se adresează, ce vrei să simtă omul după ce îl vede, și dacă ai preferință de format (reclamă autentică UGC, avatar vorbitor, sau mini-film cu mai multe cadre)."

Așteaptă răspunsul. Nu pune mai mult de o întrebare per tură.

## Pas 2: Selectează produsul potrivit

Folosește tabelul de mai jos:

| Semnal din brief | Produs recomandat |
|------------------|-------------------|
| "avatar", "eu să vorbesc", "lip sync", "prezentare cu față" | AVATAR (HeyGen) |
| "autentic", "UGC", "selfie style", "produs în mână", "social media rapid" | UGC (Higgsfield) |
| "mai multe scene", "poveste", "narativ", "cinematic", "calitate înaltă" | MULTI-SCENĂ cinematic (Kling) |
| "repede", "rapid", "simplu", "5 scene", fără preferință de calitate | MULTI-SCENĂ rapid (Higgsfield) |

Dacă nu e clar: propune UGC ca default pentru reclame simple, MULTI-SCENĂ rapid pentru conținut mai lung.

## Pas 3: Identifică brandul

Verifică `knowledge/brand-video.md`:
- Dacă brandul e menționat în brief și există în catalog: extrage culoare, font, format
- Dacă nu există în catalog sau catalogul e gol: folosește default-uri (9:16, Arial Bold, #FFD700)
- Dacă utilizatorul nu a menționat brandul: întreabă scurt "Pentru ce brand?"

## Pas 4: Propune și confirmă

Trimite utilizatorului un singur mesaj de confirmare:

> "Pe baza brief-ului, propun:
>
> Produs: [AVATAR / UGC / MULTI-SCENĂ rapid / MULTI-SCENĂ cinematic]
> Brand: [Nume brand sau 'default']
> Format: [9:16 / 16:9]
> Ton: [din brief]
>
> Cost estimat: [estimare pe baza produsului ales]
>
> Confirmăm și trecem la generare?"

Tabel estimări cost:
- AVATAR 30s: ~$1.50 HeyGen
- UGC 15s: conform plan Higgsfield
- MULTI-SCENĂ rapid 5 scene x 5s: conform plan Higgsfield
- MULTI-SCENĂ cinematic 5 scene x 5s Kling: ~$1.00 kie.ai
- Voiceover ElevenLabs 30s: +~$0.075
- Muzică Suno 30s: +~$0.10

Dacă utilizatorul confirmă: activează skill-ul corespunzător și transmite parametrii.
Dacă utilizatorul vrea altceva: ajustează propunerea și retrimite.

## Rules

- O singură întrebare per tură, niciodată mai multe
- Nu propune un produs fără estimare de cost
- Confirmarea utilizatorului e obligatorie înainte de orice generare
- Dacă brief-ul e suficient de clar, sari direct la Pas 2 fără să mai pui întrebări
