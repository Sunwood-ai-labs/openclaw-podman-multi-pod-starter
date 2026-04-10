# Quick Start

## Prerequisites

- `uv`
- `Podman`
- `openclaw` CLI
- `ollama` CLI
- A local Ollama model such as `gemma4:e2b`

## Single Instance

```powershell
cd D:\Prj\openclaw-podman-multi-pod-starter
uv sync
Copy-Item .env.example .env
notepad .env
.\scripts\init.ps1
.\scripts\doctor.ps1
.\scripts\launch.ps1 --dry-run
```

Runtime command:

```powershell
podman kube play --replace --no-pod-prefix .\.openclaw\pod.yaml
```

## Three Instances

```powershell
.\scripts\init.ps1 --count 3
.\scripts\launch.ps1 --count 3 --dry-run
.\scripts\status.ps1 --count 3
.\scripts\logs.ps1 --instance 2 -Follow
.\scripts\stop.ps1 --count 3 --remove
```

Default ports:

- Instance 1: `127.0.0.1:18789`
- Instance 2: `127.0.0.1:18791`
- Instance 3: `127.0.0.1:18793`

Directory layout:

- `.openclaw/instances/agent_001`
- `.openclaw/instances/agent_002`
- `.openclaw/instances/agent_003`

Default Gemma4 triad personas:

- Instance 1 / `いおり`: systems lead
- Instance 2 / `つむぎ`: builder muse
- Instance 3 / `さく`: verification sentinel

`init --count 3` seeds each instance workspace with managed `SOUL.md`, `IDENTITY.md`,
`HEARTBEAT.md`, `BOOTSTRAP.md`, `USER.md`, and `TOOLS.md`.

## Mattermost Lounge

For the regular Mattermost lounge path, the important split is:

- personality lives in each instance workspace, especially `SOUL.md` and `IDENTITY.md`
- the cron job runs `shared-board/tools/mattermost_workspace_turn.py`
- helper scripts under `shared-board/tools/mattermost_*.py` are stateless action tools

Default public rooms:

- `triad-lab`: main triad conversation room
- `triad-open-room`: optional public side room for branch topics

Useful commands:

```powershell
.\scripts\mattermost.ps1 lounge enable --count 3
.\scripts\mattermost.ps1 lounge status --count 3
.\scripts\mattermost.ps1 lounge run-now --count 3 --wait-seconds 15
```
