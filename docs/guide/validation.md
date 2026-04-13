# Validation

## Included Reports

- [GLM-5-Turbo report](https://github.com/Sunwood-ai-labs/onizuka-openclaw-autonomous-team-starter/blob/main/reports/pod-openclaw-glm5-turbo-report.md)
- [Gemma report](https://github.com/Sunwood-ai-labs/onizuka-openclaw-autonomous-team-starter/blob/main/reports/pod-openclaw-gemma-report.md)

## What Was Verified

- Pod-local health checks
- Pod-local OpenClaw agent responses
- File generation and execution through tool calls
- Successful `write`, `read`, and `exec` traces in session transcripts

Some reports intentionally preserve the local paths, room names, and runtime identifiers that existed when the validation run happened.

## Operational Smoke For The Conversation Lab

If you want to confirm the Mattermost team wiring rather than the model/tool reports, use:

```powershell
.\scripts\mattermost.ps1 smoke --count 3
```

Treat that as an operational smoke check for seeded bot replies, not as a blanket proof of every future autonomous conversation.

If you also want to verify heartbeat-driven autonomy, use this sequence:

```powershell
.\scripts\mattermost.ps1 smoke --count 3
.\scripts\mattermost.ps1 lounge enable --count 3
.\scripts\mattermost.ps1 lounge status --count 3
.\scripts\mattermost.ps1 lounge run-now --count 3 --wait-seconds 20
```

Interpretation:

- `smoke` proves mention/reply wiring for the seeded bots.
- `lounge enable` writes the heartbeat config into each selected instance.
- `lounge status` shows the current heartbeat config plus recent channel activity from a pod-local Mattermost read.
- `lounge run-now` is a manual wake for immediate verification. It succeeds only when new Mattermost activity is observed after the wake.

Related lab evidence:

- [Mattermost autonomy QA inventory](https://github.com/Sunwood-ai-labs/onizuka-openclaw-autonomous-team-starter/blob/main/reports/qa-inventory-mattermost-autochat-2026-04-09.md)

The default seeded room is `triad-lab`, but optional autonomy experiments may also use additional public rooms depending on workspace instructions and lab setup.

## Proven Working Models

- `zai/glm-5-turbo`
- `ollama/gemma4:e4b`
- `ollama/gemma4:e2b`
