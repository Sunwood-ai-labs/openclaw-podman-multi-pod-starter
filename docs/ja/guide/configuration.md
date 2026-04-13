# 設定

## 主な環境変数

- `OPENCLAW_IMAGE`: 起動する OpenClaw image
- `OPENCLAW_PODMAN_PUBLISH_HOST`: host 側 publish address
- `OPENCLAW_OLLAMA_BASE_URL`: Ollama native API URL
- `OPENCLAW_OLLAMA_MODEL`: 既定 Ollama model id
- `OPENCLAW_SCALE_INSTANCE_ROOT`: 生成される instance root
- `OPENCLAW_SCALE_GATEWAY_PORT_START`: 最初の gateway port
- `OPENCLAW_SCALE_BRIDGE_PORT_START`: 最初の bridge port
- `OPENCLAW_SCALE_PORT_STEP`: instance ごとの port 刻み

## エージェントチーム向けの調整ポイント

会話ラボ関連の主な設定:

- `OPENCLAW_MATTERMOST_ENABLED`
- `OPENCLAW_MATTERMOST_CHANNEL_NAME`
- `OPENCLAW_MATTERMOST_AUTONOMY_ENABLED`
- `OPENCLAW_MATTERMOST_AUTONOMY_INTERVAL`
- `OPENCLAW_MATTERMOST_AUTONOMY_INTERVAL_INSTANCE_00N`
- `OPENCLAW_MATTERMOST_AUTONOMY_MODEL`

ただし、チームの振る舞い自体は環境変数より workspace scaffold 側で決まる部分が大きいです。インフラ既定値は `.env`、人格や役割は各 workspace の `SOUL.md`、`IDENTITY.md`、`USER.md`、`HEARTBEAT.md` で調整するのが基本です。

## Windows + WSL Podman の注意

検証環境で Windows host 上の Ollama に届いた URL は次でした。

```text
http://172.27.208.1:11434
```

`.env` が既定の `host.containers.internal` を使っている場合、現在は Windows + Podman でその host alias が使えない時に、生成される runtime config が Podman-machine gateway へ自動解決します。`.\scripts\doctor.ps1` も、実際に使われる Ollama `/api/tags` endpoint に届かなければ fail します。

固定したい Ollama endpoint がある場合だけ、`.env` の `OPENCLAW_OLLAMA_BASE_URL` を明示的に差し替えてください。

`.env.example` の `OPENCLAW_MATTERMOST_AUTONOMY_MODEL` は意図的に空欄です。`mattermost lounge enable` 実行時は、明示 override が無ければ現在の primary model をそのまま継承します。

## 信頼境界

この project は same-trust operator 向けです。主な隔離は OpenClaw 内部 sandbox ではなく Podman pod 境界に依存します。
