# HeyGen API Surface

Sources: HeyGen OpenAPI, API Reference, CLI Commands, Changelog.

Base URL:

```text
https://api.heygen.com
```

Auth:

```text
X-Api-Key: $HEYGEN_API_KEY
```

## Health / Account

- `GET /v3/users/me` — profile, credits/billing fields.
- `GET /v1/user/me` — legacy account info; current docs mention credit fields on both v1 and v3.

Use before generation to verify auth and optionally check credit balance.

## Video Agent

- `POST /v3/video-agents` — create session.
- `GET /v3/video-agents` — list sessions.
- `GET /v3/video-agents/styles` — list style templates.
- `GET /v3/video-agents/{session_id}` — session status, progress, `video_id`, messages.
- `POST /v3/video-agents/{session_id}` — send follow-up/revision; chat mode only.
- `GET /v3/video-agents/{session_id}/resources/{resource_id}` — retrieve storyboard/resource.
- `GET /v3/video-agents/{session_id}/videos` — list session videos.
- `POST /v3/video-agents/{session_id}/stop` — stop at checkpoint.

Create fields:

- `prompt`
- `avatar_id`
- `voice_id`
- `orientation`
- `duration_sec`
- `files`
- `callback_url`
- `callback_id`
- `incognito_mode`

Statuses include active/review/generation/completed/failed states. When `video_id` appears, poll `GET /v3/videos/{video_id}`.

## Videos

- `POST /v3/videos`
- `GET /v3/videos`
- `GET /v3/videos/{video_id}`
- `DELETE /v3/videos/{video_id}`

Request is a discriminated union:

### `type: "avatar"`

Fields:

- `avatar_id`
- `script` + `voice_id`, or `audio_url` / `audio_asset_id`
- `resolution`
- `aspect_ratio`
- `fit`
- `background`
- `remove_background`
- `caption`
- `output_format`
- `voice_settings`
- `motion_prompt`
- `expressiveness`
- `engine`
- `callback_url`, `callback_id`
- `title`

Important:

- `script` is mutually exclusive with external audio.
- `motion_prompt` support depends on avatar type and engine.
- `engine: {"type":"avatar_v"}` opts into Avatar V when the look supports it.
- Check `supported_api_engines` on avatar look before picking engine.

### `type: "image"`

Same as avatar video, but uses `image` instead of `avatar_id`.

### `type: "cinematic_avatar"`

Fields:

- `prompt`
- `avatar_id`: array, 1-3 look IDs.
- `references`
- `aspect_ratio`: 16:9, 9:16, 1:1.
- `resolution`: 720p or 1080p.
- `duration`: 4-15 seconds.
- `auto_duration`
- `enhance_prompt`
- `title`

## Avatars

- `POST /v3/avatars`
- `GET /v3/avatars`
- `GET /v3/avatars/{group_id}`
- `DELETE /v3/avatars/{group_id}`
- `POST /v3/avatars/{group_id}/consent`
- `GET /v3/avatars/looks`
- `GET /v3/avatars/looks/{look_id}`
- `PATCH /v3/avatars/looks/{look_id}`
- `DELETE /v3/avatars/looks/{look_id}`

Create types:

- `digital_twin`: `type`, `name`, `file`, optional `avatar_group_id`.
- `photo`: `type`, `name`, `file`, optional `avatar_group_id`.
- `prompt`: `type`, `name`, `prompt`, optional `reference_images`, `avatar_group_id`, `avatar_id`.

List filters:

- Groups: `ownership`, `limit`, `token`.
- Looks: `group_id`, `avatar_type`, `ownership`, `limit`, `token`.

Use look `id` as `avatar_id` in video generation.

## Voices

- `GET /v3/voices`
- `POST /v3/voices`
- `POST /v3/voices/clone`
- `GET /v3/voices/{voice_id}`
- `DELETE /v3/voices/{voice_id}`
- `POST /v3/voices/speech`

List filters:

- `type`
- `engine`
- `language`
- `gender`
- `limit`
- `token`

Speech fields:

- `text`
- `voice_id`
- speed range 0.5-2.0
- language/locale
- input type text or SSML

Docs say Starfish-compatible voices are required for `/v3/voices/speech`; filter `engine=starfish`.

## Lipsync

- `POST /v3/lipsyncs`
- `GET /v3/lipsyncs`
- `GET /v3/lipsyncs/{lipsync_id}`
- `PATCH /v3/lipsyncs/{lipsync_id}`
- `DELETE /v3/lipsyncs/{lipsync_id}`

Create fields:

- `video`: URL or asset_id source.
- `audio`: URL or asset_id replacement.
- `mode`: `speed` or `precision`.
- `title`
- `callback_url`, `callback_id`
- `enable_caption`
- `keep_the_same_format`
- `enable_dynamic_duration`
- `disable_music_track`
- `enable_speech_enhancement`
- `enable_watermark`
- `start_time`, `end_time`
- `fps_mode`: `vfr`, `cfr`, `passthrough`.
- `folder_id`

## Video Translation

- `POST /v3/video-translations`
- `GET /v3/video-translations`
- `GET /v3/video-translations/{video_translation_id}`
- `PATCH /v3/video-translations/{video_translation_id}`
- `DELETE /v3/video-translations/{video_translation_id}`
- `GET /v3/video-translations/languages`

Create fields:

- `video`
- `output_languages`
- `mode`: `speed` or `precision`.
- `input_language`
- `audio`
- `translate_audio_only`
- `speaker_num`
- `enable_caption`
- `keep_the_same_format`
- `enable_dynamic_duration`
- `disable_music_track`
- `enable_speech_enhancement`
- `brand_glossary_id`
- `stock_voice_config`
- `srt`
- `srt_role`
- `fps_mode`
- `callback_url`, `callback_id`

Proofread:

- `POST /v3/video-translations/proofreads`
- `GET /v3/video-translations/proofreads/{proofread_id}`
- `GET /v3/video-translations/proofreads/{proofread_id}/srt`
- `PUT /v3/video-translations/proofreads/{proofread_id}/srt`
- `POST /v3/video-translations/proofreads/{proofread_id}/generate`

## Assets

- `POST /v3/assets` — upload file, max 32 MB.
- `GET /v3/assets/{asset_id}`
- `DELETE /v3/assets/{asset_id}`
- `POST /v3/assets/direct-uploads`
- `POST /v3/assets/{asset_id}/complete`
- `GET /v3/assets/search`

Direct upload flow:

1. Create upload with filename/content-type/size/checksum.
2. PUT bytes to presigned upload URL.
3. Complete asset.
4. Use `asset_id` in Video Agent, video, lipsync, or translation.

## Audio

- `GET /v3/audio/sounds` — semantic search for background music and sound effects.

Changelog note: `type=sound_effects` was added in June 2026; parsers must allow both `music` and `sound_effects`.

## Webhooks

- `GET /v3/webhooks/event-types`
- `GET /v3/webhooks/endpoints`
- `POST /v3/webhooks/endpoints`
- `PATCH /v3/webhooks/endpoints/{endpoint_id}`
- `DELETE /v3/webhooks/endpoints/{endpoint_id}`
- `POST /v3/webhooks/endpoints/{endpoint_id}/rotate-secret`
- `GET /v3/webhooks/events`

Secret is shown only on create/rotate; store securely.

## HyperFrames

- `POST /v3/hyperframes/renders`
- `GET /v3/hyperframes/renders`
- `GET /v3/hyperframes/renders/{render_id}`
- `DELETE /v3/hyperframes/renders/{render_id}`

Changelog:

- `resolution`: `1080p` or `4k`; defaults to `1080p`.
- `aspect_ratio`: 16:9, 9:16, 1:1.
- Old combined resolution presets are deprecated.

## Avatar Realtime / Live

- `POST /v3/avatar-realtime`
- `GET /v3/avatar-realtime/{stream_id}`
- `GET /v3/avatar-realtime/{stream_id}/words`
- `POST /v3/avatar-realtime/{stream_id}/text`
- `POST /v3/avatar-realtime/{stream_id}/cancel`

Use only for streaming/broadcast conversation workflows, not normal rendered clips.

## Other V3 Capabilities

- `POST /v3/ai-clipping`
- `POST /v3/background-removals`
- `GET /v3/brand-kits`
- `GET /v3/brand-glossaries`

Use when the brief specifically needs clipping, background removal, or brand resources.

## Error Handling

- `401`: missing/invalid auth.
- `429`: rate/concurrency limit. Respect `Retry-After`.
- Video failures: inspect `failure_code` and `failure_message`.
- URL input failures: files must be publicly accessible direct URLs.
- Persist response JSON in the task folder for debugging.
