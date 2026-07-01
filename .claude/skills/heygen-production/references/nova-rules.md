# NOVA Video Rules For HeyGen

These rules override generic HeyGen docs for this org.

## Romanian Lip-Sync Gate

Dan explicitly marked HeyGen/Higgsfield lip-sync in Romanian as failed/unvalidated.

Do not:

- propose HeyGen as final validated Romanian talking-head production;
- generate a full Romanian lip-sync clip;
- spend credits on long avatar/lip-sync tests;
- call a local path or dashboard URL "delivered".

Required sample protocol:

1. One avatar/look.
2. One Romanian sentence.
3. 5-8 seconds.
4. One voice or one external audio file.
5. Cost estimate and Dan confirmation before generation.
6. Deliver the sample as Telegram attachment.
7. Wait for Dan PASS/FAIL on:
   - lip-sync accuracy;
   - Romanian pronunciation;
   - realism/expressiveness;
   - Telegram delivery.

Only after PASS can a full Romanian talking-head task proceed.

## Cost Gate

Before any paid HeyGen call:

- state route and endpoint/tool;
- state duration or expected units;
- state known pricing if available, or say pricing is account/plan dependent;
- state that credits may be consumed;
- ask for explicit Dan confirmation.

No silent proceeding.

## Delivery Gate

Final user-visible deliverables must go through Telegram:

```bash
set -a; source .env; set +a
curl -sS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendVideo" \
  -F "chat_id=${CHAT_ID}" \
  -F "video=@/absolute/path/final.mp4" \
  -F "width=720" \
  -F "height=1280" \
  -F "caption=..."
```

For files that Telegram may not preview correctly, use `sendDocument`.

## Preferred NOVA Routes

For "wow" demos:

- Prefer cinematic scenes, KIE/Kling, local edit, external voiceover, subtitles, music.
- Use HeyGen Cinematic Avatar only for short prompt-driven character shots.
- Avoid making talking-head lip-sync the centerpiece until Romanian PASS exists.

For controlled avatar demos:

- Direct Video with explicit avatar look, voice/audio, aspect, and script.
- Keep sample short.

For fast exploration:

- Video Agent in chat mode, with storyboard/revision review.

For localization:

- Video Translation precision + proofread flow when subtitles/terms matter.

## Deletions And State Changes

Deleting or rotating any of these requires explicit approval:

- videos;
- avatars/groups/looks;
- voices;
- lipsync jobs;
- translations;
- assets;
- webhooks;
- webhook signing secrets.

Creating webhook endpoints also requires approval unless Dan already authorized that production workflow.

## Required Task Artifacts

When generating with HeyGen, save in the task output directory:

- request JSON;
- response JSON;
- polling log or webhook event;
- downloaded MP4/audio/subtitles;
- ffprobe output;
- Telegram delivery confirmation.

## Memory Updates

After every meaningful HeyGen run, update `MEMORY.md` with:

- endpoint/tool used;
- request shape;
- model/engine;
- avatar/voice IDs;
- actual status/result;
- any error/failure code;
- Dan quality feedback.
