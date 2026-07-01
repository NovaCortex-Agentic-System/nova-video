# HeyGen Auth And Surfaces

Sources: HeyGen Quick Start, For AI Agents, MCP Overview, CLI Overview, Skills Overview, Commands.

## Auth Ladder

Use the first available surface. Do not mix surfaces in one task unless there is a clear reason.

1. MCP
   - Best when `mcp__heygen__*` tools are visible.
   - Auth is OAuth through HeyGen remote MCP.
   - No API key handling in the agent.
   - Usage consumes existing HeyGen plan credits.
   - Verify with `get_current_user` tool if available.

2. CLI
   - Best for terminal/agent automation when `heygen` is installed.
   - Uses structured JSON by default.
   - `HEYGEN_API_KEY` environment variable takes precedence over stored credentials.
   - Verify with:
     ```bash
     heygen auth status
     ```
   - Install if missing and Dan approves setup:
     ```bash
     curl -fsSL https://static.heygen.ai/cli/install.sh | bash
     heygen --version
     ```

3. Raw API
   - Last resort when MCP and CLI are unavailable.
   - Requires:
     ```bash
     HEYGEN_API_KEY
     ```
   - Base URL:
     ```text
     https://api.heygen.com
     ```
   - Auth header:
     ```text
     X-Api-Key: $HEYGEN_API_KEY
     ```
   - Verify:
     ```bash
     curl -sS "https://api.heygen.com/v3/users/me" \
       -H "X-Api-Key: $HEYGEN_API_KEY"
     ```

## Key Handling

- Never print secret values.
- Never ask Dan to paste a key into chat.
- If key is missing, say:
  ```text
  HeyGen API key is not available in this agent environment. Please add HEYGEN_API_KEY to nova-video .env or org secrets, then restart nova-video.
  ```
- If `.env` changed, hard restart the affected agent so the PTY environment reloads.

## CLI Command Families

- `heygen video-agent create|get|send|stop`
- `heygen video-agent styles list`
- `heygen video-agent videos list`
- `heygen video create|list|get|delete|download`
- `heygen avatar create|list|get`
- `heygen avatar looks list|get|update`
- `heygen avatar consent create`
- `heygen voice list|create`
- `heygen voice speech create`
- `heygen lipsync create|list|get|update|delete`
- `heygen video-translate create|list|get|update|delete`
- `heygen video-translate languages list`
- `heygen video-translate proofreads create|get|generate`
- `heygen webhook endpoints create|list|update|delete|rotate-secret`
- `heygen webhook event-types list`
- `heygen webhook events list`
- `heygen asset create`
- `heygen user me get`

Use `--request-schema` on CLI commands before constructing complex JSON:

```bash
heygen video create --request-schema
heygen lipsync create --request-schema
heygen video-agent create --request-schema
```

## MCP Tool Families

Official MCP exposes equivalent tools for:

- Video Agent: create session, get session, send message, get resources, list session videos, list sessions, stop session.
- Videos: avatar video, cinematic avatar, image video, list/get/delete.
- Avatars: list groups, get group, list/get/update/delete looks, create digital twin/photo/prompt avatar, consent.
- Voices/audio: list/design/clone voices, generate speech, search music/sound effects.
- Lipsync and Video Translation.
- Assets, brand kits/glossaries, account.

If MCP tools are available, prefer them over raw HTTP.
