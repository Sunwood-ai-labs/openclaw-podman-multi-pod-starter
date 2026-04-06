import { defineConfig } from "vitepress";

const repo = "https://github.com/Sunwood-ai-labs/openclaw-podman-multi-pod-starter";

export default defineConfig({
  title: "openclaw-podman-multi-pod-starter",
  description:
    "Run OpenClaw in Podman pods with kube-play manifests, isolated multi-instance state, and validated Ollama Gemma / Z.AI GLM setups.",
  lang: "en-US",
  base: "/openclaw-podman-multi-pod-starter/",
  cleanUrls: true,
  lastUpdated: true,
  head: [["link", { rel: "icon", href: "/header.svg" }]],
  themeConfig: {
    siteTitle: "openclaw-podman-multi-pod-starter",
    logo: "/header.svg",
    socialLinks: [{ icon: "github", link: repo }],
    footer: {
      message: "Released under the MIT License.",
      copyright: "Copyright © 2026 Sunwood-ai-labs",
    },
  },
  locales: {
    root: {
      label: "English",
      lang: "en-US",
      themeConfig: {
        nav: [
          { text: "Guide", link: "/guide/quickstart" },
          { text: "Configuration", link: "/guide/configuration" },
          { text: "Validation", link: "/guide/validation" },
          { text: "GitHub", link: repo },
        ],
        sidebar: [
          {
            text: "Guide",
            items: [
              { text: "Quick Start", link: "/guide/quickstart" },
              { text: "Configuration", link: "/guide/configuration" },
              { text: "Validation", link: "/guide/validation" },
            ],
          },
        ],
      },
    },
    ja: {
      label: "Japanese",
      lang: "ja-JP",
      themeConfig: {
        nav: [
          { text: "Guide", link: "/ja/guide/quickstart" },
          { text: "Configuration", link: "/ja/guide/configuration" },
          { text: "Validation", link: "/ja/guide/validation" },
          { text: "GitHub", link: repo },
        ],
        sidebar: [
          {
            text: "Guide",
            items: [
              { text: "Quick Start", link: "/ja/guide/quickstart" },
              { text: "Configuration", link: "/ja/guide/configuration" },
              { text: "Validation", link: "/ja/guide/validation" },
            ],
          },
        ],
      },
    },
  },
});
