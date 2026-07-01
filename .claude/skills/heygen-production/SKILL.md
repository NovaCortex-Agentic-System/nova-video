---
name: heygen-production
description: "Use this before any HeyGen work: Video Agent, avatar video, cinematic avatar, avatar creation, voices/TTS, lipsync, translation, assets, webhooks, MCP, CLI, or raw API. It documents the official HeyGen v3 surface and NOVA Video production gates."
triggers:
  - "heygen"
  - "video agent"
  - "avatar api"
  - "avatar video"
  - "cinematic avatar"
  - "heygen lipsync"
  - "video translation"
  - "heygen cli"
  - "heygen mcp"
secrets_required:
  - HEYGEN_API_KEY
outputs:
  - "working HeyGen execution plan, generated asset, or explicit blocker"
---

# HeyGen Production Skill

This is the routing and safety layer for all HeyGen work in NOVA Video.

## Load Order

Read only the references needed for the current task:

- `references/auth-and-surfaces.md` — always read first. Covers MCP vs CLI vs raw API and validation.
- `references/workflows.md` — read when choosing a production route.
- `references/api-surface.md` — read when calling endpoints or writing request bodies.
- `references/pricing-limits-errors.md` — read before estimating cost, sizing inputs, or diagnosing failures.
- `references/nova-rules.md` — always read before paid generation or Telegram delivery.
- `references/sources.md` — read when you need source links or freshness context.

## Mandatory First Steps

1. Identify the intended HeyGen route:
   - Video Agent: prompt to finished video.
   - Direct video: explicit avatar/image + script or audio.
   - Cinematic Avatar: prompt-driven cinematic shot from 1-3 avatar looks.
   - Avatar creation: digital twin, photo avatar, or prompt avatar.
   - Voice/TTS: list/design/clone/generate speech.
   - Lipsync: source video + replacement audio.
   - Video translation: translate/dub existing video.
   - Assets/webhooks/HyperFrames/realtime: supporting or advanced flows.
2. Read `auth-and-surfaces.md` and verify one auth surface before drafting code:
   - MCP tools, if available.
   - HeyGen CLI, if installed and authenticated.
   - Raw API with `HEYGEN_API_KEY`, as last resort.
3. For any paid generation, stop before execution and ask Dan for explicit cost confirmation.
4. For Romanian lip-sync or Romanian voice, run a 5-8s sample first. No full clip until Dan gives explicit PASS.
5. Every final video must be delivered as confirmed Telegram attachment, not only as a local path or UI file.

## Route Selection

Default choices:

- Need fast ideation or a demo from a natural language brief: use Video Agent in `mode: "chat"` if Dan should review storyboard, or `mode: "generate"` only after cost approval.
- Need exact script/avatar/voice/timing: use Direct Video (`POST /v3/videos`, `type: "avatar"` or `type: "image"`).
- Need cinematic B-roll or visually impressive short shots without talking-head risk: use Cinematic Avatar or KIE/Kling pipeline; do not force lip-sync.
- Need Romanian talking-head validation: test `POST /v3/lipsyncs` or Direct Video with one sentence only, then wait for Dan PASS/FAIL.
- Need localization: use Video Translation `precision` for final quality, and proofread sessions when subtitle accuracy matters.

## Non-Negotiable Rules

- Do not ask Dan to paste API keys into chat. If key is missing, ask him to configure it in the environment/dashboard.
- Do not delete videos, avatars, voices, assets, webhooks, or translations without explicit approval.
- Do not create paid assets without cost confirmation.
- Do not present HeyGen as validated for Romanian lip-sync. It is currently unvalidated/failed until a Dan-approved sample proves otherwise.
- Prefer direct execution over "ready-to-run" scripts. If blocked, state the one blocker.
- If an endpoint fails, capture HTTP status, error body, `failure_code`, and `failure_message` where available.

## Completion Checklist

- Auth surface verified.
- Correct route selected and documented.
- Request body saved in the task output folder when generation is performed.
- Cost confirmed before any paid call.
- Job status polled or webhook registered.
- Output downloaded locally and checked with `ffprobe`/file size.
- Telegram attachment sent and confirmed.
- Memory updated with any new endpoint behavior, limits, or failure.
