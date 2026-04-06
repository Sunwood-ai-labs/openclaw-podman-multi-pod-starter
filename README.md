# openclaw-podman-starter

Windows ホストから `Podman` で current `OpenClaw` Gateway を動かし、ホスト側 `Ollama` の `gemma4:e2b` を既定モデルとして使うためのスターターです。

今の構成は `podman run` 直打ちではなく、instance ごとの manifest ファイルを生成して `podman kube play` / `podman kube down` で扱う前提です。運用の source of truth はファイルです。

## コンセプト

- 1 instance = 1 Podman pod = 1 OpenClaw gateway container
- 既定モデルは `ollama/gemma4:e2b`
- コンテナ内 OpenClaw からホスト Ollama へ `http://host.containers.internal:11434` で接続
- OpenClaw の内部 sandbox は切り、`tools.profile: "full"` / `sandbox.mode: "off"` を seed
- state, workspace, token, port は instance ごとに完全分離

## 前提

- `uv`
- `Podman`
- `openclaw` CLI
- `ollama` CLI
- `ollama list` に `gemma4:e2b` が出ること

補足:

- OpenClaw 公式では Windows は WSL2 運用が推奨です。
- Ollama 連携は native API 前提です。`OPENCLAW_OLLAMA_BASE_URL` に `/v1` は付けません。
- この repo の multi-instance 分離は same-trust operator 向けの運用分離であり、強い multi-tenant security boundary ではありません。

## 単一 instance

```powershell
cd D:\Prj\openclaw-podman-starter
uv sync
Copy-Item .env.example .env
notepad .env
.\scripts\init.ps1
.\scripts\doctor.ps1
.\scripts\launch.ps1 --dry-run
```

`init` 後には次が生成されます。

- `D:\Prj\openclaw-podman-starter\.openclaw\openclaw.json`
- `D:\Prj\openclaw-podman-starter\.openclaw\.env`
- `D:\Prj\openclaw-podman-starter\.openclaw\pod.yaml`

実起動は `podman kube play --replace --no-pod-prefix <pod.yaml>` 相当です。

## 3 instance 起動

```powershell
.\scripts\init.ps1 --count 3
.\scripts\launch.ps1 --count 3 --dry-run
.\scripts\status.ps1 --count 3
.\scripts\logs.ps1 --instance 2 -Follow
.\scripts\stop.ps1 --count 3 --remove
```

既定ではこう分かれます。

- `instance 1`: pod `openclaw-1-pod`, container `openclaw-1`, gateway `127.0.0.1:18789`, state `./.openclaw/instances/1`
- `instance 2`: pod `openclaw-2-pod`, container `openclaw-2`, gateway `127.0.0.1:18791`, state `./.openclaw/instances/2`
- `instance 3`: pod `openclaw-3-pod`, container `openclaw-3`, gateway `127.0.0.1:18793`, state `./.openclaw/instances/3`

各 instance には次が生成されます。

- `./.openclaw/instances/N/control.env`
- `./.openclaw/instances/N/.env`
- `./.openclaw/instances/N/openclaw.json`
- `./.openclaw/instances/N/pod.yaml`
- `./.openclaw/instances/N/workspace/`

## host-only smoke

`Podman` が無い環境でも、host 側 OpenClaw と Ollama だけで `gemma4:e2b` の限定スモークはできます。

```powershell
$env:OLLAMA_API_KEY = "ollama-local"
openclaw --profile gemma4-e2b-lab config set agents.defaults.model.primary '"ollama/gemma4:e2b"'
openclaw --profile gemma4-e2b-lab config set tools.profile '"full"'
openclaw --profile gemma4-e2b-lab config set agents.defaults.sandbox.mode '"off"'
openclaw --profile gemma4-e2b-lab agent --local --agent main --message "こんにちはを一語だけ返して。" --json
```

このワークスペースでは実際に `provider=ollama`, `model=gemma4:e2b`, `sandbox.mode=off` で 1 ターン応答することまで確認済みです。

## よく使うコマンド

```powershell
.\scripts\print-env.ps1
uv run openclaw-podman print-env --instance 2
uv run openclaw-podman launch --count 3 --dry-run
uv run openclaw-podman status --count 3
uv run openclaw-podman stop --count 3 --remove --dry-run
```

PowerShell ラッパーは `init.ps1`, `doctor.ps1`, `launch.ps1`, `status.ps1`, `logs.ps1`, `stop.ps1` だけです。追加引数はそのまま透過されます。

## 設定

主に使う env は次です。

- `OPENCLAW_CONTAINER`: host CLI から見た単一 instance の container 名
- `OPENCLAW_PODMAN_CONTAINER`: Podman 側の base container 名
- `OPENCLAW_IMAGE`: OpenClaw image
- `OPENCLAW_PODMAN_PUBLISH_HOST`: host publish IP
- `OPENCLAW_PODMAN_GATEWAY_HOST_PORT`: 単一 instance の gateway port
- `OPENCLAW_PODMAN_BRIDGE_HOST_PORT`: 単一 instance の bridge port
- `OPENCLAW_CONFIG_DIR`: 単一 instance の config dir
- `OPENCLAW_WORKSPACE_DIR`: 単一 instance の workspace dir
- `OPENCLAW_SCALE_INSTANCE_ROOT`: scaled instances の root dir
- `OPENCLAW_SCALE_GATEWAY_PORT_START`: instance 1 の gateway port
- `OPENCLAW_SCALE_BRIDGE_PORT_START`: instance 1 の bridge port
- `OPENCLAW_SCALE_PORT_STEP`: instance ごとの port 増分
- `OLLAMA_API_KEY`: OpenClaw が Ollama provider を有効化するための marker
- `OPENCLAW_OLLAMA_BASE_URL`: Ollama native API URL
- `OPENCLAW_OLLAMA_MODEL`: 既定 model ID

helper は state 側 `.env` に `OPENCLAW_GATEWAY_TOKEN` を書き、repo 側 `.env` から `*_API_KEY` をコンテナへ渡します。

## kube play モデル

`launch` は instance ごとに `pod.yaml` を生成して、次を実行するイメージです。

```powershell
podman kube play --replace --no-pod-prefix <pod.yaml>
```

`stop` は次を実行するイメージです。

```powershell
podman kube down <pod.yaml>
```

manifest には次が入ります。

- pod 名
- hostPort / containerPort の publish
- `OLLAMA_API_KEY`, `OPENCLAW_GATEWAY_BIND`, `OPENCLAW_GATEWAY_TOKEN`
- hostPath mount での `OPENCLAW_CONFIG_DIR -> /home/node/.openclaw`

## 注意点

- `podman` 未導入時、`doctor` は `[fail] podman` を返します。
- `launch --dry-run` は API key と gateway token をマスクします。
- `status` は `podman pod ps` ベース、`logs` は `podman pod logs --names` ベースです。
- `gemma4:e2b` はローカル小型モデルなので、より大きいモデルより tool の安定性や安全余裕は低い可能性があります。
- runtime の live 検証はまだ dry-run 止まりです。`podman` が入った環境で `kube play` 実機確認が必要です。

## 参考

- [OpenClaw Podman docs](https://docs.openclaw.ai/install/podman)
- [OpenClaw Multiple Gateways](https://docs.openclaw.ai/gateway/multiple-gateways)
- [OpenClaw Ollama provider docs](https://docs.openclaw.ai/providers/ollama)
- [OpenClaw local models guidance](https://docs.openclaw.ai/gateway/local-models)
- [Podman kube play](https://docs.podman.io/en/latest/markdown/podman-kube-play.1.html)
- [Podman kube down](https://docs.podman.io/en/latest/markdown/podman-kube-down.1.html)
- [Ollama OpenClaw integration docs](https://docs.ollama.com/integrations/openclaw)
