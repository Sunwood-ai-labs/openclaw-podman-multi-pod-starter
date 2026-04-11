<!-- Managed by openclaw-podman-starter: persona scaffold -->
# TOOLS.md - ひびき 用のローカルメモ

## Runtime Snapshot

- Instance: 5
- Pod: `openclaw-5-pod`
- Container: `openclaw-5`
- Model: `google/gemma-3-27b-it`
- Gateway: `http://127.0.0.1:18797/`
- Bridge: `http://127.0.0.1:18798/`
- Workspace: `D:\Prj\openclaw-podman-starter\.openclaw\instances\agent_005\workspace`
- Config dir: `D:\Prj\openclaw-podman-starter\.openclaw\instances\agent_005`
- Mattermost lounge scripts: `/home/node/.openclaw/mattermost-tools`

## 実務メモ

- Python は `uv` を使う
- Instance init: `./scripts/init.ps1 --instance 5`
- Dry-run launch: `./scripts/launch.ps1 --instance 5 --dry-run`
- Logs: `./scripts/logs.ps1 --instance 5 -Follow`

## この file の用途

これは ひびき 用の cheat sheet です。環境固有の事実はここへ置き、
共有 skill prompt には混ぜないでください。
