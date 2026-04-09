#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from mattermost_autochat_turn import (
    BOT_IDS,
    HANDLES,
    fetch_channel_posts,
    fetch_me,
    find_channel_summary,
    list_my_channels,
    list_team_channels,
    load_control_values,
    load_mattermost_runtime,
    resolve_bot_ids,
    resolve_team,
    should_rate_limit,
    summarize_channels,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch summarized Mattermost lounge state.")
    parser.add_argument("--instance", type=int, choices=sorted(HANDLES), required=True)
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
    team_channels = list_team_channels(base_url, token, team_id)
    my_channel_ids = list_my_channels(base_url, token, team_id)
    bot_ids = resolve_bot_ids(base_url, token)
    BOT_IDS.clear()
    BOT_IDS.update(bot_ids)
    channel_summaries = summarize_channels(
        base_url,
        token,
        team_channels,
        my_channel_ids,
        runtime["default_channel"],
        bot_ids,
    )

    rate_limit = {
        "limited": False,
        "reason": "no-default-channel",
    }
    default_summary = find_channel_summary(channel_summaries, runtime["default_channel"])
    if isinstance(default_summary, dict):
        channel_id = str(default_summary.get("channel_id", "")).strip()
        posts, order = fetch_channel_posts(base_url, token, channel_id)
        limited, reason = should_rate_limit(handle, posts, order, bot_ids, False)
        rate_limit = {
            "limited": limited,
            "reason": reason,
            "post_count": len(order),
        }

    payload = {
        "instance_id": instance_id,
        "handle": handle,
        "me": {
            "id": str(me.get("id", "")).strip(),
            "username": actual_handle,
            "display_name": str(me.get("display_name", "")).strip(),
        },
        "team": {
            "name": runtime["team_name"],
            "id": team_id,
        },
        "default_channel": runtime["default_channel"],
        "rate_limit": rate_limit,
        "channels": channel_summaries,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(parse_args()))
