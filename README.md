# openclaw-podman-starter

Windows ホストから `Podman` で current `OpenClaw` Gateway を動かしつつ、ホスト側 `Ollama` の `gemma4:e2b` を既定モデルとして使うための概念スターターです。

このフォルダは OpenClaw 本体を同梱しません。公式コンテナイメージと公式 CLI を前提に、起動導線と最小設定だけを切り出した薄いプロジェクトです。

2026-04-06 時点では、公式 Podman ドキュメント、公式 Ollama provider ドキュメント、GitHub Releases を確認し、既定イメージは `ghcr.io/openclaw/openclaw:2026.4.5`、既定モデルは `ollama/gemma4:e2b` としています。

## コンセプト

- `Podman` で OpenClaw Gateway コンテナを起動する
- OpenClaw の既定モデルを `ollama/gemma4:e2b` にする
- コンテナ内 OpenClaw からホスト Ollama へ `http://host.containers.internal:11434` でつなぐ
- 永続状態は repo ローカルの `./.openclaw` に隔離する
- OpenClaw 自体はコンテナ内なので `tools.profile: "full"` と `sandbox.mode: "off"` で使う
- ホスト側の `openclaw` CLI でも同じモデルを限定スモークできる

## ファイル構成

- `README.md`: 使い方と前提
- `.env.example`: Podman + Ollama 用の環境変数ひな形
- `pyproject.toml`: `uv` 管理の helper CLI 定義
- `scripts/init.ps1`: `.env` と repo ローカル state を初期化
- `scripts/doctor.ps1`: 前提コマンドと設定を確認
- `scripts/launch.ps1`: Podman コンテナを起動
- `scripts/status.ps1`: コンテナ状態を確認
- `scripts/logs.ps1`: コンテナログを表示
- `scripts/stop.ps1`: コンテナを停止
- `src/openclaw_podman_starter/cli.py`: 実処理

## 前提

- `uv`
- `Podman`
- `openclaw` CLI
- `ollama` CLI
- `ollama list` に `gemma4:e2b` が出ること

補足:

- OpenClaw の公式 Platforms ドキュメントでは、Windows では WSL2 運用が推奨されています。
- OpenClaw の Ollama 連携は native API 前提です。`OPENCLAW_OLLAMA_BASE_URL` に `/v1` を付けないでください。
- このワークスペースでは `podman` は未導入だったため、今回の確認は helper の挙動確認と host 側 OpenClaw の限定スモークまでです。

## クイックスタート

```powershell
cd D:\Prj\openclaw-podman-starter
uv sync
Copy-Item .env.example .env
notepad .env
.\scripts\init.ps1
.\scripts\doctor.ps1
.\scripts\launch.ps1
```

起動後の公式寄り導線:

```powershell
openclaw onboard --non-interactive --auth-choice ollama --custom-base-url "http://host.containers.internal:11434" --custom-model-id "gemma4:e2b" --accept-risk
openclaw models list
openclaw gateway status --deep
openclaw dashboard --no-open
```

ブラウザで `http://127.0.0.1:18789/` を開き、`OPENCLAW_CONFIG_DIR\.env` に入る `OPENCLAW_GATEWAY_TOKEN` を使って onboarding します。

## Host-Only Smoke

`Podman` がまだ無い環境でも、host 側 OpenClaw と Ollama だけで `gemma4:e2b` の限定スモークができます。

```powershell
$env:OLLAMA_API_KEY = "ollama-local"
openclaw --profile gemma4-e2b-lab config set agents.defaults.model.primary '"ollama/gemma4:e2b"'
openclaw --profile gemma4-e2b-lab agent --local --agent main --message "日本語で12文字以内の自己紹介を1行だけ返して。" --json
```

このワークスペースでは実際に上のコマンドを流し、`provider=ollama`、`model=gemma4:e2b` で 1 ターン応答するところまで確認しました。

## Scale Out

3 台を独立した pod として起動したい場合は、既存コマンドに `--count` を付けます。

```powershell
.\scripts\init.ps1 --count 3
.\scripts\launch.ps1 --count 3 --dry-run
.\scripts\status.ps1 --count 3
.\scripts\logs.ps1 --instance 2 -Follow
.\scripts\stop.ps1 --count 3 --remove
```

この mode では 1 instance = 1 pod = 1 OpenClaw gateway container です。既定では次のように派生します。

- `instance 1`: pod `openclaw-1-pod`, container `openclaw-1`, gateway `127.0.0.1:18789`, state `./.openclaw/instances/1`
- `instance 2`: pod `openclaw-2-pod`, container `openclaw-2`, gateway `127.0.0.1:18791`, state `./.openclaw/instances/2`
- `instance 3`: pod `openclaw-3-pod`, container `openclaw-3`, gateway `127.0.0.1:18793`, state `./.openclaw/instances/3`

`OPENCLAW_SCALE_GATEWAY_PORT_START`、`OPENCLAW_SCALE_BRIDGE_PORT_START`、`OPENCLAW_SCALE_PORT_STEP` を変えると、派生ポートもまとめてずらせます。

## よく使うコマンド

```powershell
.\scripts\status.ps1
.\scripts\logs.ps1 -Follow
.\scripts\stop.ps1
uv run openclaw-podman print-env
uv run openclaw-podman launch --dry-run
openclaw models list --all --provider ollama
```

## 設定の考え方

主に使う環境変数:

- `OPENCLAW_CONTAINER`: ホスト CLI から見たコンテナ名
- `OPENCLAW_PODMAN_CONTAINER`: Podman 側のコンテナ名
- `OPENCLAW_PODMAN_IMAGE`: Podman 用に明示したい OpenClaw イメージ
- `OPENCLAW_IMAGE`: `OPENCLAW_PODMAN_IMAGE` 未指定時のフォールバック
- `OPENCLAW_PODMAN_GATEWAY_HOST_PORT`: ホスト公開ポート
- `OPENCLAW_PODMAN_BRIDGE_HOST_PORT`: bridge 公開ポート
- `OPENCLAW_PODMAN_PUBLISH_HOST`: 既定は `127.0.0.1`
- `OPENCLAW_GATEWAY_BIND`: コンテナ内部 bind。既定は `lan`
- `OPENCLAW_CONFIG_DIR`: repo ローカルの OpenClaw 設定ディレクトリ
- `OPENCLAW_WORKSPACE_DIR`: repo ローカルの OpenClaw workspace ディレクトリ
- `OPENCLAW_SCALE_INSTANCE_ROOT`: scaled instance を置くルート。既定は `./.openclaw/instances`
- `OPENCLAW_SCALE_GATEWAY_PORT_START`: instance 1 の gateway 公開ポート
- `OPENCLAW_SCALE_BRIDGE_PORT_START`: instance 1 の bridge 公開ポート
- `OPENCLAW_SCALE_PORT_STEP`: instance ごとのポート増分。既定は `2`
- `OPENCLAW_GATEWAY_TOKEN`: `init` が `OPENCLAW_CONFIG_DIR\.env` に補完する Control UI 用トークン
- `OLLAMA_API_KEY`: OpenClaw が Ollama provider を有効化するためのマーカー。ローカルでは任意値でよい
- `OPENCLAW_OLLAMA_BASE_URL`: コンテナから見た Ollama の native API URL。既定は `http://host.containers.internal:11434`
- `OPENCLAW_OLLAMA_MODEL`: 既定の Ollama model ID。既定は `gemma4:e2b`

helper は `OPENCLAW_CONFIG_DIR\.env` の `OPENCLAW_GATEWAY_TOKEN` と repo 側 `.env` の `*_API_KEY` を allowlist でコンテナへ渡します。`OLLAMA_API_KEY=ollama-local` はそのままコンテナへ渡されます。

## Full Access Mode

この starter は「OpenClaw 自体を Podman コンテナ内で動かすので、その中ではフルアクセスでよい」という前提に寄せています。`init` は repo ローカル `openclaw.json` に次を seed します。

- `tools.profile: "full"`
- `agents.defaults.sandbox.mode: "off"`
- `tools.fs.workspaceOnly: false`
- `tools.exec.applyPatch.workspaceOnly: false`

つまり OpenClaw の内部 sandbox には頼らず、外側の Podman コンテナを実行境界として扱う設計です。
この分離は same-trust operator 向けの運用分離であり、強い multi-tenant security boundary ではありません。

## 想定する実行モデル

`launch` は次のような形の `podman run` を組み立てます。

- `--replace` 付きで同名コンテナを差し替える
- `127.0.0.1:18789` と `127.0.0.1:18790` を公開する
- `OPENCLAW_CONFIG_DIR` を `/home/node/.openclaw` に bind mount する
- 必要なら `OPENCLAW_WORKSPACE_DIR` を `/home/node/.openclaw/workspace` に別 mount する
- `OPENCLAW_GATEWAY_BIND=lan`、`OPENCLAW_GATEWAY_TOKEN`、`OLLAMA_API_KEY` を環境変数で渡す
- repo ローカル `openclaw.json` に `models.providers.ollama.baseUrl=http://host.containers.internal:11434` と `ollama/gemma4:e2b` の explicit model 定義を書く
- repo ローカル `openclaw.json` に `tools.profile=full` と `sandbox.mode=off` を書く
- scaled mode では `podman pod create` で pod を先に作り、その pod に gateway container を載せる

## 注意点

- 公式 Podman ドキュメントは rootless Podman 前提です。
- Windows + Podman Machine では bind mount と `host.containers.internal` の見え方が環境依存になることがあります。
- `doctor` は `podman` 未導入時に `[fail] podman` を返します。
- `launch --dry-run` は API キーと gateway token をマスクして表示します。
- `gemma4:e2b` はローカル小型モデルなので、より大きいモデルより tool の安定性や安全余裕は低い可能性があります。
- OpenClaw の内部 sandbox は切っているので、コンテナ内ファイルやプロセスには広く触れられます。安全境界は Podman コンテナ側です。

## 参考

- [OpenClaw Podman docs](https://docs.openclaw.ai/install/podman)
- [OpenClaw Ollama provider docs](https://docs.openclaw.ai/providers/ollama)
- [OpenClaw local models guidance](https://docs.openclaw.ai/gateway/local-models)
- [Ollama OpenClaw integration docs](https://docs.ollama.com/integrations/openclaw)
- [Ollama Gemma 4 library page](https://ollama.com/library/gemma4)
- [OpenClaw releases](https://github.com/openclaw/openclaw/releases)
