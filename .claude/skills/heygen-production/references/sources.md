# HeyGen Source Map

Last reviewed: 2026-06-30.

Official docs used:

- https://developers.heygen.com/docs/quick-start
- https://developers.heygen.com/docs/for-ai-agents
- https://developers.heygen.com/docs/choosing-the-right-video-api
- https://developers.heygen.com/docs/overview
- https://developers.heygen.com/docs/video-agent
- https://developers.heygen.com/docs/styles-and-references
- https://developers.heygen.com/docs/upload-assets
- https://developers.heygen.com/docs/interactive-sessions
- https://developers.heygen.com/reference/list-video-agent-sessions
- https://developers.heygen.com/reference/create-video-agent-session
- https://developers.heygen.com/reference/create-video
- https://developers.heygen.com/reference/create-avatar
- https://developers.heygen.com/reference/create-lipsync
- https://developers.heygen.com/reference/generate-speech
- https://developers.heygen.com/reference/list-voices
- https://developers.heygen.com/mcp/overview
- https://developers.heygen.com/skills/overview
- https://developers.heygen.com/cli
- https://developers.heygen.com/commands
- https://developers.heygen.com/features
- https://developers.heygen.com/output-modes
- https://developers.heygen.com/examples
- https://developers.heygen.com/overview
- https://developers.heygen.com/changelog
- https://developers.heygen.com/docs/pricing
- https://developers.heygen.com/docs/usage-limits
- https://developers.heygen.com/docs/error-codes
- https://developers.heygen.com/openapi/external-api.json
- https://developers.heygen.com/openapi.yaml

Important freshness notes from changelog:

- June 2026: Cinematic Avatar added to `POST /v3/videos` as `type: "cinematic_avatar"`.
- June 2026: `motion_prompt` expanded for body motion and hand gestures, with support depending on avatar type and engine.
- June 2026: audio search supports `type=sound_effects`, not only music.
- June 2026: user endpoints expose credit usage fields.
- June 2026 / May 31: HyperFrames render now uses separate `resolution` and `aspect_ratio`; `resolution` is `1080p` or `4k`.

When in doubt, consult:

- Documentation index: https://developers.heygen.com/llms.txt
- OpenAPI JSON: https://developers.heygen.com/openapi/external-api.json
