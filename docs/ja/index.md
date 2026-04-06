---
layout: home

hero:
  name: openclaw-podman-multi-pod-starter
  text: OpenClaw を Podman pod で再現性よく運用
  tagline: kube-play manifest、複数 instance 分離、Gemma / GLM 実証をまとめたスターター。
  image:
    src: /header.svg
    alt: openclaw-podman-multi-pod-starter
  actions:
    - theme: brand
      text: クイックスタート
      link: /ja/guide/quickstart
    - theme: alt
      text: 検証
      link: /ja/guide/validation
    - theme: alt
      text: GitHub
      link: https://github.com/Sunwood-ai-labs/openclaw-podman-multi-pod-starter

features:
  - title: kube play 前提
    details: 実行時の source of truth を `pod.yaml` に寄せ、単発コマンド依存を減らします。
  - title: 複数 instance 分離
    details: state、workspace、token、port を instance ごとに分離して並列運用しやすくします。
  - title: 実機検証付き
    details: Z.AI GLM と Ollama Gemma を pod 内 OpenClaw agent で検証した記録を含みます。
---

## 含まれるもの

- `uv` 管理の helper CLI
- Windows 向け PowerShell wrapper
- 単一 / 複数 instance 用の `pod.yaml` 生成
- `glm-5-turbo`, `gemma4:e4b`, `gemma4:e2b` の検証レポート

## 次に読む

- [クイックスタート](/ja/guide/quickstart)
- [設定](/ja/guide/configuration)
- [検証](/ja/guide/validation)
