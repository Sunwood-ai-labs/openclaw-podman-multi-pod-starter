---
layout: home

hero:
  name: openclaw-podman-multi-pod-starter
  text: OpenClaw on repeatable Podman pods
  tagline: File-based kube-play manifests, isolated multi-instance state, and verified Gemma / GLM runs.
  image:
    src: /header.svg
    alt: openclaw-podman-multi-pod-starter
  actions:
    - theme: brand
      text: Quick Start
      link: /guide/quickstart
    - theme: alt
      text: Validation
      link: /guide/validation
    - theme: alt
      text: GitHub
      link: https://github.com/Sunwood-ai-labs/openclaw-podman-multi-pod-starter

features:
  - title: Podman kube play first
    details: The repo treats generated pod manifests as the runtime source of truth instead of relying on ad-hoc one-off commands.
  - title: Multi-instance isolation
    details: State, workspace, tokens, and ports are split per instance so local side-by-side pods remain manageable.
  - title: Real model verification
    details: Validation reports document pod-local file generation and execution using Z.AI GLM and Ollama Gemma models.
---

## What You Get

- A small helper CLI managed by `uv`
- PowerShell entry points for Windows-first operation
- Generated `pod.yaml` manifests for single-instance and multi-instance runs
- Validation reports for `glm-5-turbo`, `gemma4:e4b`, and `gemma4:e2b`

## Read Next

- [Quick Start](/guide/quickstart)
- [Configuration](/guide/configuration)
- [Validation](/guide/validation)
