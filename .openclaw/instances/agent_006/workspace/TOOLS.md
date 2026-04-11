<!-- Managed by openclaw-podman-starter: persona scaffold -->
# TOOLS.md - かなえ 用のローカルメモ

## Runtime Snapshot

- Instance: 6
- Pod: `openclaw-6-pod`
- Container: `openclaw-6`
- Model: `google/gemma-4-26b-a4b-it`
- Gateway: `http://127.0.0.1:18799/`
- Bridge: `http://127.0.0.1:18800/`
- Workspace: `D:\Prj\openclaw-podman-starter\.openclaw\instances\agent_006\workspace`
- Config dir: `D:\Prj\openclaw-podman-starter\.openclaw\instances\agent_006`
- Mattermost lounge scripts: `/home/node/.openclaw/mattermost-tools`

## 実務メモ

- Python は `uv` を使う
- Instance init: `./scripts/init.ps1 --instance 6`
- Dry-run launch: `./scripts/launch.ps1 --instance 6 --dry-run`
- Logs: `./scripts/logs.ps1 --instance 6 -Follow`

## この file の用途

これは かなえ 用の cheat sheet です。環境固有の事実はここへ置き、
共有 skill prompt には混ぜないでください。
