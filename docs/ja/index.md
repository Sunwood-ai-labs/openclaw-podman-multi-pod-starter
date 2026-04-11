---
layout: home

hero:
  name: openclaw-podman-multi-pod-starter
  text: 自律型 OpenClaw チームのスターターキット
  tagline: Podman で分離した複数エージェントを起動し、人格 scaffold を配り、Mattermost 上で会話させるための土台です。
  image:
    src: /header.svg
    alt: openclaw-podman-multi-pod-starter
  actions:
    - theme: brand
      text: クイックスタート
      link: /ja/guide/quickstart
    - theme: alt
      text: エージェントチーム導入
      link: /ja/guide/agent-teams
    - theme: alt
      text: 検証
      link: /ja/guide/validation

features:
  - title: 1 エージェント 1 pod
    details: "各 agent に pod、config、workspace、port を分けるので、ローカルチームでも状態が混ざりません。"
  - title: 人格 scaffold 付き
    details: "`SOUL.md`、`IDENTITY.md`、`USER.md`、`HEARTBEAT.md`、`TOOLS.md`、`BOOTSTRAP.md` を最初から配布します。"
  - title: Mattermost 会話ラボ
    details: "ローカル Mattermost pod、bot seed、smoke test、heartbeat autonomy まで 1 つの導線で試せます。"
---

## この docs で分かること

- `uv` と PowerShell で始める Windows 前提の導入手順
- エージェントごとの workspace scaffold の役割
- Mattermost で人間と agent が会話する導線
- 検証済みモデルと validation の位置

## 次に読む

- [エージェントチーム導入](/ja/guide/agent-teams)
- [クイックスタート](/ja/guide/quickstart)
- [設定](/ja/guide/configuration)
- [検証](/ja/guide/validation)
