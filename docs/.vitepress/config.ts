import { defineConfig } from "vitepress";

const repo = "https://github.com/Sunwood-ai-labs/openclaw-podman-multi-pod-starter";

export default defineConfig({
  title: "openclaw-podman-multi-pod-starter",
  description:
    "Starter kit for running small OpenClaw agent teams in Podman with isolated pods, persona scaffolds, and a local Mattermost lab.",
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
      copyright: "Copyright (c) 2026 Sunwood-ai-labs",
    },
  },
  locales: {
    root: {
      label: "English",
      lang: "en-US",
      themeConfig: {
        nav: [
          { text: "Guide", link: "/guide/quickstart" },
          { text: "Agent Teams", link: "/guide/agent-teams" },
          { text: "Configuration", link: "/guide/configuration" },
          { text: "Validation", link: "/guide/validation" },
          { text: "GitHub", link: repo },
        ],
        sidebar: [
          {
            text: "Guide",
            items: [
              { text: "Quick Start", link: "/guide/quickstart" },
              { text: "Agent Team Starter", link: "/guide/agent-teams" },
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
          { text: "ガイド", link: "/ja/guide/quickstart" },
          { text: "エージェントチーム", link: "/ja/guide/agent-teams" },
          { text: "設定", link: "/ja/guide/configuration" },
          { text: "検証", link: "/ja/guide/validation" },
          { text: "GitHub", link: repo },
        ],
        sidebar: [
          {
            text: "ガイド",
            items: [
              { text: "クイックスタート", link: "/ja/guide/quickstart" },
              { text: "エージェントチーム導入", link: "/ja/guide/agent-teams" },
              { text: "設定", link: "/ja/guide/configuration" },
              { text: "検証", link: "/ja/guide/validation" },
            ],
          },
        ],
      },
    },
  },
});
