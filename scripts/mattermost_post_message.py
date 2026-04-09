#!/usr/bin/env python3
from __future__ import annotations

import argparse

from mattermost_autochat_turn import (
    HANDLES,
    ensure_joined_channel,
    fetch_me,
    find_channel_summary,
    list_my_channels,
    list_team_channels,
    load_control_values,
    load_mattermost_runtime,
    post_message,
    resolve_bot_ids,
    resolve_team,
    summarize_channels,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post a Mattermost message or thread reply.")
    parser.add_argument("--instance", type=int, choices=sorted(HANDLES), required=True)
    parser.add_argument("--channel-name", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--root-post-id")
    return parser.parse_args()


def main(args: argparse.Namespace) -> int:
    instance_id = args.instance
    handle = HANDLES[instance_id]
    runtime = load_control_values()
    base_url, token = load_mattermost_runtime()

    me = fetch_me(base_url, token)
    actual_handle = str(me.get("username", "")).strip()
    if actual_handle and actual_handle != handle:
        raise RuntimeError(f"wrong-handle expected={handle} actual={actual_handle}")

    _, team_id = resolve_team(base_url, token, runtime["team_name"])
    channel_summaries = summarize_channels(
        base_url,
        token,
        list_team_channels(base_url, token, team_id),
        list_my_channels(base_url, token, team_id),
        runtime["default_channel"],
        resolve_bot_ids(base_url, token),
    )
    channel = find_channel_summary(channel_summaries, args.channel_name)
    if channel is None:
        raise RuntimeError(f"channel not found: {args.channel_name}")

    channel_id = str(channel.get("channel_id", "")).strip()
    ensure_joined_channel(base_url, token, me, channel_id)
    post_id = post_message(
        base_url,
        token,
        channel_id,
        args.message,
        root_post_id=args.root_post_id.strip() if args.root_post_id else None,
    )
    marker = "REPLIED" if args.root_post_id else "POSTED"
    print(f"{marker} {post_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(parse_args()))
