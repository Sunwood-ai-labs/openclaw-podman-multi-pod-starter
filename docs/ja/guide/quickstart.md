# クイックスタート

## 前提

- `uv`
- `Podman`
- `openclaw` CLI
- `ollama` CLI
- `ollama list` に使いたい model が出ていること

## 単一 instance

```powershell
cd D:\Prj\openclaw-podman-multi-pod-starter
uv sync
Copy-Item .env.example .env
notepad .env
.\scripts\init.ps1
.\scripts\doctor.ps1
.\scripts\launch.ps1 --dry-run
```

実行時は次に相当します。

```powershell
podman kube play --replace --no-pod-prefix .\.openclaw\pod.yaml
```

## 3台構成

```powershell
.\scripts\init.ps1 --count 3
.\scripts\launch.ps1 --count 3 --dry-run
.\scripts\status.ps1 --count 3
.\scripts\logs.ps1 --instance 2 -Follow
.\scripts\stop.ps1 --count 3 --remove
```
