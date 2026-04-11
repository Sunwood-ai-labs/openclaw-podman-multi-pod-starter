<!-- Managed by openclaw-podman-starter: persona scaffold -->
# TOOLS.md - るり 用のローカルメモ

## Runtime Snapshot

- Instance: 4
- Pod: `openclaw-4-pod`
- Container: `openclaw-4`
- Model: `google/gemma-4-31b-it`
- Gateway: `http://127.0.0.1:18795/`
- Bridge: `http://127.0.0.1:18796/`
- Workspace: `D:\Prj\openclaw-podman-starter\.openclaw\instances\agent_004\workspace`
- Config dir: `D:\Prj\openclaw-podman-starter\.openclaw\instances\agent_004`
- Mattermost lounge scripts: `/home/node/.openclaw/mattermost-tools`

## 実務メモ

- Python は `uv` を使う
- Instance init: `./scripts/init.ps1 --instance 4`
- Dry-run launch: `./scripts/launch.ps1 --instance 4 --dry-run`
- Logs: `./scripts/logs.ps1 --instance 4 -Follow`

## この file の用途

これは るり 用の cheat sheet です。環境固有の事実はここへ置き、
共有 skill prompt には混ぜないでください。
