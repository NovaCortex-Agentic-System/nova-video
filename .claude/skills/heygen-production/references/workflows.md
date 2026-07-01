# HeyGen Workflows For NOVA Video

Sources: Quick Start, Choosing the Right Video API, Video Agent Overview, Interactive Sessions, CLI docs, Cookbook, Changelog.

## 1. Video Agent: Prompt To Finished Video

Use when Dan gives a broad brief and wants HeyGen to script, cast, compose, and render.

Endpoint:

```text
POST /v3/video-agents
GET /v3/video-agents/{session_id}
GET /v3/videos/{video_id}
```

Good for:

- Fast demos.
- Social videos with styles.
- Content repurposing.
- Training/onboarding videos.
- Product/demo explanations.

Request fields:

- `prompt` required.
- `avatar_id` optional.
- `voice_id` optional.
- `orientation` optional.
- `duration_sec` optional, minimum 5.
- `files` optional, max 20 attachments.
- `callback_url`, `callback_id` optional.
- `incognito_mode` optional.

Modes:

- `generate`: one-shot, fire-and-forget.
- `chat`: multi-turn, storyboard/revision checkpoints.

NOVA default: use `chat` for anything expensive, brand-sensitive, or user-facing. It allows review before final render.

## 2. Direct Avatar Or Image Video

Use when script, avatar, voice, aspect, and timing must be controlled.

Endpoint:

```text
POST /v3/videos
GET /v3/videos/{video_id}
```

Types:

- `type: "avatar"`: avatar look talks using text script or external audio.
- `type: "image"`: arbitrary image talks/animates using text script or external audio.

Key rule:

- `script` + `voice_id` and `audio_url`/`audio_asset_id` are mutually exclusive.
- For Romanian, external audio may be better than HeyGen TTS, but lip-sync still needs sample PASS.

Recommended defaults:

```json
{
  "resolution": "1080p",
  "aspect_ratio": "9:16",
  "output_format": "mp4"
}
```

Use `aspect_ratio: "auto"` only when preserving source frame is more important than platform format.

## 3. Cinematic Avatar

Use for cinematic shots, not normal talking-head script delivery.

Endpoint:

```text
POST /v3/videos
```

Request shape:

```json
{
  "type": "cinematic_avatar",
  "prompt": "...",
  "avatar_id": ["look_id"],
  "aspect_ratio": "9:16",
  "resolution": "1080p",
  "duration": 10,
  "enhance_prompt": true
}
```

Constraints:

- `avatar_id`: 1-3 avatar look IDs.
- `duration`: 4-15 seconds, unless `auto_duration` is true.
- `resolution`: 720p or 1080p.
- `aspect_ratio`: 16:9, 9:16, or 1:1. No `auto`.
- No classic script/voice. Motion is prompt-driven.

NOVA use:

- Good for wow demo scenes.
- Safer than Romanian talking-head lip-sync when visuals matter more than exact mouth movement.

## 4. Avatar Creation

Endpoint:

```text
POST /v3/avatars
```

Types:

- `digital_twin`: from real video footage.
- `photo`: from a clear frontal photo.
- `prompt`: from text prompt, optionally reference images.

Concepts:

- Avatar Group = character identity.
- Avatar Look = outfit/pose/style. The look `id` is the `avatar_id` for video generation.

Consent:

```text
POST /v3/avatars/{group_id}/consent
```

Use consent for private avatars when required. Do not bypass consent for real people.

## 5. Voices And Speech

Endpoints:

```text
GET /v3/voices
POST /v3/voices
POST /v3/voices/clone
GET /v3/voices/{voice_id}
POST /v3/voices/speech
```

Capabilities:

- List voices, filter by engine/language/gender/type.
- Design a voice from natural language prompt.
- Clone a voice from audio.
- Generate speech audio with Starfish-compatible voices.

NOVA rule:

- Do not assume Romanian quality. Test one short sentence and ask Dan for PASS/FAIL.
- If using KIE/ElevenLabs gives better Romanian, generate external audio and pass it to Direct Video or Lipsync.

## 6. Lipsync

Endpoint:

```text
POST /v3/lipsyncs
GET /v3/lipsyncs/{lipsync_id}
```

Use when you already have:

- source video
- replacement audio

Modes:

- `speed`: fast draft.
- `precision`: higher quality, avatar inference, better candidate for final.

Useful options:

- `enable_caption`
- `keep_the_same_format`
- `enable_dynamic_duration`
- `disable_music_track`
- `enable_speech_enhancement`
- `start_time`, `end_time`
- `fps_mode`

NOVA gate:

- Romanian lipsync is not validated. Run a 5-8s sample only, then wait for Dan PASS.

## 7. Video Translation

Endpoint:

```text
POST /v3/video-translations
GET /v3/video-translations/{video_translation_id}
GET /v3/video-translations/languages
```

Use for:

- Translating an existing video into one or more languages.
- Voice cloning + lip-sync.
- Optional proofread flow before final render.

Quality modes:

- `speed`
- `precision`

Proofread endpoints:

```text
POST /v3/video-translations/proofreads
GET /v3/video-translations/proofreads/{proofread_id}
GET /v3/video-translations/proofreads/{proofread_id}/srt
PUT /v3/video-translations/proofreads/{proofread_id}/srt
POST /v3/video-translations/proofreads/{proofread_id}/generate
```

NOVA default:

- Use proofread for any final Romanian subtitles or brand-sensitive terminology.

## 8. Assets

Endpoints:

```text
POST /v3/assets
POST /v3/assets/direct-uploads
POST /v3/assets/{asset_id}/complete
GET /v3/assets/{asset_id}
DELETE /v3/assets/{asset_id}
```

Use for:

- Images, video, audio, PDF inputs.
- Files used by Video Agent or Direct Video.

Limits from docs:

- Basic upload max 32 MB.
- Supported common types: png, jpeg, mp4, webm, mp3, wav, pdf.

## 9. Webhooks

Use for production automation instead of polling.

Endpoints:

```text
POST /v3/webhooks/endpoints
GET /v3/webhooks/event-types
GET /v3/webhooks/events
```

Rules:

- URL must be public HTTPS.
- Store signing secret securely; it is shown only at creation/rotation.
- Webhook creation/deletion/rotation is external-stateful; ask for approval if not already authorized for the workflow.

## 10. HyperFrames, Realtime, Audio, AI Clipping

HeyGen API also exposes:

- HyperFrames render: HTML/JS/assets to video.
- Avatar Realtime: HLS streaming avatar with TTS/audio/text stream.
- Audio search: background music and sound effects.
- AI clipping: source video to short clips.
- Background removal.
- Brand kits and glossaries.

Use these only when they fit the task; otherwise keep NOVA Video's local ffmpeg/KIE/Kling pipeline for deterministic editing.
