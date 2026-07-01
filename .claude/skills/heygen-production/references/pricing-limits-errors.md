# HeyGen Pricing, Limits, And Errors

Sources: Self-Serve Pricing, Usage Limits, Error Codes, Changelog. Last reviewed 2026-06-30.

## Billing Model

With API key auth, HeyGen bills against the API tier / prepaid USD wallet. With OAuth/MCP, usage can consume the connected HeyGen web plan credits. Check account/balance with:

```text
GET /v3/users/me
```

Rates below are self-serve API rates from the public docs at review time. Always mention that actual billing can vary by plan/contract.

## Published Rates

Video Agent:

- Prompt to Video: `$0.0333 / sec`

Avatar video:

- Avatar V Digital Twin: `$0.0667 / sec`
- Avatar IV Photo Avatar: `$0.05 / sec`
- Avatar IV Digital Twin: `$0.0667 / sec`
- Avatar IV Studio Avatar: `$0.0667 / sec`
- Avatar III Digital Twin: `$0.0167 / sec`
- Avatar III Photo Avatar: `$0.0433 / sec`

Cinematic Avatar:

- `$7.00 / video`
- 4-15 seconds
- 720p/1080p only

Avatar Realtime:

- `$0.05 / sec`
- 720p only

HyperFrames:

- 1080p / 30 fps: `$0.10 / min`
- 1080p / 60 fps: `$0.20 / min`
- 4K / 30 fps: `$0.15 / min`
- 4K / 60 fps: `$0.30 / min`

Video Translation:

- Speed audio only: `$0.0333 / sec`
- Speed lip-sync: `$0.0333 / sec`
- Precision lip-sync: `$0.0667 / sec`

Lipsync:

- Speed: `$0.0333 / sec`
- Precision: `$0.0667 / sec`

AI Clipping:

- `$0.15 / clip`

Text-to-Speech:

- Starfish speech: `$0.000667 / sec`

Avatar creation:

- Digital Twin: `$1.00 / call`
- Photo Avatar: `$1.00 / call`

## Cost Estimation Pattern

Before paid calls, tell Dan:

```text
Ruta: <Video Agent / Direct Video / Lipsync / etc.>
Durată estimată: <N sec>
Preț public: <rate>
Cost estimat: <N * rate>
Poate consuma credite HeyGen. Confirmi generarea?
```

For Cinematic Avatar:

```text
Cost estimat: $7 per video, indiferent de durata 4-15 secunde.
```

For unknown plan/account behavior:

```text
Prețul public este X, dar billing-ul real poate depinde de planul contului. Confirmi să testăm/generăm?
```

## Usage Limits

Concurrency:

- Pay-As-You-Go: 10 concurrent video jobs.
- Async jobs include Video Agent, avatar renders, and video translations.
- On `429`, respect `Retry-After`.

Input limits for `POST /v3/videos`:

- Video: MP4/WebM, max 100 MB, max resolution below 2K.
- Image: JPG/PNG, max 50 MB, max resolution below 2K.
- Audio: WAV/MP3, max 50 MB.
- URLs must be publicly accessible direct file URLs.
- File extension must match actual format.
- Files must not be corrupted.

Avatar video inputs:

- Script text max 5,000 characters.
- Audio input max 10 minutes / 600 seconds.

Video Agent inputs:

- Prompt 1-10,000 characters.
- Up to 20 file attachments.
- Supported attachments: PNG, JPEG, MP4, WebM, MP3, WAV, PDF.
- Files can be `asset_id`, HTTPS URL, or base64.

Assets:

- Basic `POST /v3/assets`: max 32 MB.
- For larger files, use direct upload flow and obey returned `max_bytes`.

TTS:

- Text 1-5,000 characters.
- Speed 0.5x to 2.0x.
- Plain text or SSML.

Output specs:

- Avatar videos: 25 fps.
- Width/height between 128 and 4096 px.
- Default output 1080p.
- Aspect ratios include 16:9 and 9:16 in limits docs; direct video docs also include 4:5, 5:4, 1:1, auto depending on type.
- Maximum scenes: 50.
- Maximum duration: 30 minutes.

Pagination:

- Most list endpoints use `limit` + `next_token`.
- Max examples: videos 100, avatars 50, avatar looks 50, voices 100, styles 100, translations 100.

## Error Handling

HTTP classes:

- `400`: malformed/invalid parameters.
- `401`: invalid/missing API key.
- `402`: insufficient credit or plan/trial limit.
- `403`: no permission/resource access denied/vendor restricted/voice unusable.
- `404`: resource not found.
- `409`: conflict, resource not ready, idempotency request in progress.
- `429`: rate limit/quota exceeded.
- `500`: HeyGen server error.

Common error codes to handle:

- `unauthorized`
- `forbidden`
- `resource_access_denied`
- `ai_vendor_access_restricted`
- `voice_not_usable`
- `rate_limit_exceeded`
- `quota_exceeded`
- `insufficient_credit`
- `trial_limit_exceeded`
- `plan_upgrade_required`
- `video_not_found`
- `avatar_not_found`
- `voice_not_found`
- `asset_not_found`
- `webhook_not_found`
- `resource_not_found`
- `invalid_parameter`
- `conflict`
- `resource_not_ready`
- `request_in_progress`
- `content_policy_violation`
- `avatar_consent_required`
- `resource_limit_reached`

Always capture:

- HTTP status;
- response body;
- `error.code`;
- `error.message`;
- `error.param` if present;
- `failure_code` and `failure_message` for async video/lipsync/translation jobs.
