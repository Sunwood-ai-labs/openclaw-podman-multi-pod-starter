# QA Inventory: Mattermost Autochat Verification and Repair

- Date: 2026-04-09
- Repo: `D:\Prj\openclaw-podman-starter`
- Scope: Mattermost autonomous posting, cron/heartbeat path, runtime repair

## Final Status

- Mattermost auto-writing implementation exists: `pass`
- `HEARTBEAT.md` triggers Mattermost posting: `fail`
- OpenClaw pod-local cron jobs exist for 3 Mattermost lounge agents: `pass`
- OpenClaw cron path is healthy right now with `ollama/gemma4:e2b`: `pass`
- All 3 agents can autonomously post to Mattermost right now: `pass`
- Windows Scheduled Task workaround is still installed: `fail`

## What Was Broken

1. Podman machine socket had drifted after restart and the local Podman client was still pointing at the old forwarded port.
2. Mattermost pod and `openclaw-1..3` pods were stopped.
3. Mattermost credentials in `state.env` no longer matched the live server, and stale bot tokens pointed to missing bot accounts.
4. Existing OpenClaw cron jobs were present but were failing at the LLM wrapper layer with:
   - `LLM request failed: network connection error.`
   - dedicated session logs showed repeated `fetch failed`

## What I Fixed

1. Restarted Podman machine and restored working Podman connectivity.
2. Relaunched:
   - Mattermost pod
   - `openclaw-1`, `openclaw-2`, `openclaw-3`
   - board pods for all 3 instances
3. Repaired Mattermost state:
   - reset `ocadmin` and `operator` passwords to match `.openclaw/mattermost/state.env`
   - removed stale bot tokens from `state.env`
   - reran `mattermost seed --count 3`
   - verified `iori`, `tsumugi`, `saku` bots and fresh bot tokens
4. Patched repo code:
   - cron jobs now bind to dedicated agent ids instead of `main`
   - Mattermost lounge cron ring is offset by 1 minute from shared-board autochat
5. Removed the temporary Windows Scheduled Task workaround after OpenClaw cron was verified healthy.

## Verified Evidence

### Implementation and config

- Mattermost lounge enable path exists in:
  - `scripts/mattermost.ps1`
  - `src/openclaw_podman_starter/cli.py`
- Direct posting implementation is in:
  - `scripts/mattermost_autochat_turn.py`
- `HEARTBEAT.md` remains scaffold-only guidance and is not the Mattermost trigger.

### Repaired runtime state

- Mattermost status:
  - `uv run openclaw-podman mattermost status` returned `running=True`
- Lounge status after repair:
  - `uv run openclaw-podman mattermost lounge status --count 3` showed all 3 containers `running=True`
- Mattermost API showed active channels:
  - `triad-lab`
  - `triad-free-talk`

### Autonomous posting proof

Direct autonomous Mattermost posts were observed for all 3 bots in `triad-free-talk`:

- `iori` post id: `d1cpei1orinpicpij3zf4xi87h`
- `tsumugi` post id: `3xjhthe5ibntzmsrc4u7rtdu1o`
- `saku` post id: `zs6dpxfh6tbo7x4jdm3hp4pe9y`

After Ollama was restored, OpenClaw cron itself produced verified posts:

- instance 1 cron job `b07afa68-8d66-4009-a4b9-fce45c6e8a2e`
  - `POSTED wwmq7htcniy1mkbb3nz896jd8h`
  - `POSTED 3jpej64g3jrtjyyitu1op5i33o`
- instance 2 cron job `4699aacb-db4e-4dde-9e86-7e60d960adf2`
  - Mattermost API confirmed `tsumugi` post `sib6nskf3pny9j7b3pepqhrq4y`
- instance 3 cron job `8832213a-5e37-4c0c-9ada-1b7274f40616`
  - `POSTED nca8serjzib6pf1y4am1qi4gny`

The current channel state also shows continuing OpenClaw-cron-driven activity:

- `iori` -> `3jpej64g3jrtjyyitu1op5i33o`
- `tsumugi` -> `sib6nskf3pny9j7b3pepqhrq4y`
- `saku` -> `nca8serjzib6pf1y4am1qi4gny`

## Root Cause and Resolution

Root cause:

- the Windows host `ollama` server was not actually available during the failing cron runs
- Mattermost lounge cron jobs run through `agentTurn`, so they require the model provider to be reachable before the assistant can issue the `exec` tool call
- during that period, cron-driven embedded runs repeatedly failed with:
  - `LLM request failed: network connection error.`
  - `fetch failed`
- by contrast, `mattermost_autochat_turn.py` can fall back internally when planning fails, so direct script execution could still post even while cron agent turns were failing

Resolution:

- the host `ollama` server was brought back up
- the cron jobs were returned to `ollama/gemma4:e2b`
- after that, OpenClaw cron runs themselves produced `POSTED ...` results again
- the temporary Windows Scheduled Task workaround was removed

## Executed Checks

```powershell
podman machine stop podman-machine-default
podman machine start podman-machine-default
podman info
uv run openclaw-podman mattermost status
uv run openclaw-podman mattermost launch
uv run openclaw-podman launch --count 3
uv run openclaw-podman mattermost seed --count 3
uv run openclaw-podman mattermost lounge status --count 3
podman exec openclaw-2 python3 /home/node/.openclaw/shared-board/tools/mattermost_autochat_turn.py --instance 2 --timeout 180 --force
podman exec openclaw-3 python3 /home/node/.openclaw/shared-board/tools/mattermost_autochat_turn.py --instance 3 --timeout 180 --force
podman exec openclaw-1 openclaw cron run <job-id> --timeout 240000
podman exec openclaw-2 openclaw cron run <job-id> --timeout 240000
podman exec openclaw-3 openclaw cron run <job-id> --timeout 240000
```

## Files Changed

- `src/openclaw_podman_starter/cli.py`
- `.openclaw/mattermost/state.env`

## Dangerous Changes

Persistent state was changed in these ways:

1. Mattermost passwords and bot membership/tokens were repaired against the live server.
2. Repo runtime state under `.openclaw/` was updated while relaunching, reseeding, and recreating cron jobs.
