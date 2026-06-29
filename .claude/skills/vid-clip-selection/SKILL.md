---
name: vid-clip-selection
description: "Analizează un transcript video long-form și identifică cele mai bune momente pentru clip-uri short-form. Scorează pe 5 categorii: Hook, Value, Clarity, Shareability, Completeness."
triggers:
  - "selectează clipuri"
  - "găsește cele mai bune momente"
  - "extrage shorts din transcript"
  - "analizează transcriptul"
  - "clip selection"
  - "ce clipuri să extrag"
  - "momente bune din video"
  - "find best clips"
negative_triggers:
  - "generează video"
  - "editează video"
  - "adaugă subtitruri"
inputs:
  - transcript (obligatoriu: cale fișier SRT sau text plain)
  - count (opțional: număr clipuri dorite, default 5)
  - duration_range (opțional: "min-max" secunde, default "30-90")
  - focus (opțional: topici prioritare)
outputs:
  - listă ordonată de clipuri cu timestamps, scoruri și motivare
---

# Skill: Selecție Clipuri Short-Form

## Pas 0: Validare input

Citește fișierul transcript furnizat. Dacă e SRT, parsează timestamp-urile și textul. Dacă e text plain, tratează fiecare paragraf ca un segment.

Dacă transcriptul are sub 500 cuvinte:
> "Transcriptul e scurt (sub 500 cuvinte). Pot analiza, dar rezultatele vor fi limitate. Continui?"

Dacă utilizatorul nu a furnizat un transcript, cere:
> "Furnizează fișierul transcript (SRT sau text) sau lipește conținutul direct în chat."

## Pas 1: Scanare pentru momente potențiale

Citește transcriptul complet. Identifică segmentele care conțin:
- Afirmații contradictorii sau surprinzătoare
- Momentele cu cel mai mult emoție sau intensitate
- Explicații clare ale unui concept valoros
- Răspunsuri directe la întrebări frecvente
- Anecdote sau exemple concrete
- Concluzii sau insight-uri cheie

Notează timestamp-ul de start al fiecărui moment potențial. Dacă transcriptul e text plain fără timestamps, estimează poziția procentuală (ex: "30% din text").

## Pas 2: Scorare pe 5 categorii

Pentru fiecare moment potențial, scorează de la 1 la 10:

**1. Hook Strength (primele 3-5 secunde)**
- 9-10: Afirmație contrariană, întrebare retorică puternică, statistică surprinzătoare
- 7-8: Promisiune clară de valoare, preview al unui insight
- 5-6: Context util dar nu spectaculos
- 1-4: Introducere plată, fără tensiune sau curiozitate

**2. Value Delivery (payoff-ul clipului)**
- 9-10: Insight acționabil, schimbă perspectiva, rezolvă o problemă reală
- 7-8: Informație utilă, bine structurată
- 5-6: Conținut informativ dar general
- 1-4: Filler, repetă ce știe audiența deja

**3. Clarity (standalone, fără context)**
- 9-10: Complet de sine stătător, nu necesită context anterior
- 7-8: Minor context necesar, ușor de înțeles
- 5-6: Necesită unele explicații suplimentare
- 1-4: De neînțeles fără context

**4. Shareability (potențial viral)**
- 9-10: Surprinzător, emoționant sau puternic contradictoriu față de opinia comună
- 7-8: Relatable, util pentru un segment larg
- 5-6: Interesant pentru nișă specifică
- 1-4: Puțin probabil să fie distribuit

**5. Completeness (clipul are început și sfârșit natural)**
- 9-10: Pornim dintr-un punct natural, terminăm cu o concluzie clară
- 7-8: Ușor tăiat la margini dar acceptabil
- 5-6: Tăiat la mijlocul unui gând, necesită rework
- 1-4: Fragment incomprehensibil ca clip independent

**Scor total:** suma celor 5 categorii (max 50).

## Pas 3: Filtrare și selecție finală

Elimină clipurile cu:
- Scor total sub 25
- Durata în afara range-ului specificat (default 30-90 secunde)
- Scor Completeness sub 6

Sortează descrescător după scor total. Selectează primele `count` clipuri (default 5).

Dacă după filtrare rămân mai puțin de `count` clipuri, raportează câte ai găsit și de ce celelalte au fost eliminate.

Dacă după filtrare nu rămâne niciun clip: "Niciun segment nu îndeplinește criteriile (scor≥25, Completeness≥6, durată 30-90s). Vrei să relaxez criteriile? (ex: coboară scorul minim la 20 sau extinzi durata la 120s)"

## Pas 4: Output

Timestamps: folosește formatul `HH:MM:SS` (ex: `00:02:34 → 00:03:12`). Dacă transcriptul SRT are milisecunde, rotunjește la secunde întregi.

Prezintă rezultatele:

```
## Clipurile recomandate

### Clip 1 — [scor total]/50
- **Timestamps:** [start] → [end] ([durata]s)
- **Platformă recomandată:** [TikTok/Reels/Shorts]
- **Scor:** Hook [X] | Value [X] | Clarity [X] | Share [X] | Complete [X]
- **De ce:** [1-2 propoziții despre ce face clipul bun]
- **Textul:** "[primele și ultimele 10-15 cuvinte din clip]"

[repetă pentru fiecare clip]
```

Platformă recomandată: TikTok = 45-60s, Reels = 30-90s, Shorts = 15-60s. Dacă durata clipului se potrivește la mai multe platforme, listează-le pe toate.

La final: "Vrei să extrag clipurile din video cu FFmpeg (vid-ffmpeg-edit) sau le editez cu subtitruri direct?"

## Rules

- Nu selecta clipuri sub 30 secunde sau peste 90 secunde fără aprobare explicită (limita default a range-ului)
- Scorul Completeness sub 6 = respins automat
- Nu selecta mai mult de `count` clipuri fără aprobare
- Dacă focusul e specificat (ex: "doar despre marketing"), prioritizează segmentele pe acel topic chiar dacă scorul lor e mai mic decât altele
- Dacă transcriptul nu are timestamps (text plain), menționează explicit că timestamps-urile din output sunt estimative

## Self-Update

Dacă utilizatorul semnalează că selecția nu reflectă calitatea reală, adaugă în Rules:
`- [YYYY-MM-DD] corecție: [descriere scurtă]`
