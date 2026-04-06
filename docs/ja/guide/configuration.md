# 設定

## 主な環境変数

- `OPENCLAW_IMAGE`
- `OPENCLAW_PODMAN_PUBLISH_HOST`
- `OPENCLAW_OLLAMA_BASE_URL`
- `OPENCLAW_OLLAMA_MODEL`
- `OPENCLAW_SCALE_INSTANCE_ROOT`
- `OPENCLAW_SCALE_GATEWAY_PORT_START`
- `OPENCLAW_SCALE_BRIDGE_PORT_START`
- `OPENCLAW_SCALE_PORT_STEP`

## Windows + WSL Podman での注意

検証環境では、Windows host 上の Ollama へ届いた URL は次でした。

```text
http://172.27.208.1:11434
```

`host.containers.internal` で届かない場合は `.env` の `OPENCLAW_OLLAMA_BASE_URL` を置き換えてください。

## 信頼境界

この repo は same-trust operator 向けです。OpenClaw の内部 sandbox よりも Podman pod 側の境界を主に使う想定です。
