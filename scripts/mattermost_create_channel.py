#!/usr/bin/env python3
from __future__ import annotations

import argparse

from mattermost_autochat_turn import (
    CHANNEL_PREFIX,
    HANDLES,
    MAX_TRIAD_CHANNELS,
    create_public_channel,
    ensure_joined_channel,
    fetch_me,
    list_team_channels,
    load_control_values,
    load_mattermost_runtime,
    mattermost_request,
    normalize_channel_name,
    resolve_team,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or reuse a public Mattermost channel.")
    parser.add_argument("--instance", type=int, choices=sorted(HANDLES), required=True)
    parser.add_argument("--channel-name", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--purpose", required=True)
    return parser.parse_args()


def ensure_user_joined_by_username(base_url: str, token: str, channel_id: str, username: str) -> None:
    handle = username.strip()
    if not handle:
        return
    _, _, payload = mattermost_request(base_url, token, f"/api/v4/users/username/{handle}")
    if not isinstance(payload, dict):
        raise RuntimeError(f"Could not resolve Mattermost user: {handle}")
    user_id = str(payload.get("id", "")).strip()
    if not user_id:
        raise RuntimeError(f"Mattermost user has no id: {handle}")
    _, _, _ = mattermost_request(
        base_url,
        token,
        f"/api/v4/channels/{channel_id}/members",
        method="POST",
        payload={"user_id": user_id},
    )


def ensure_default_humans_joined(base_url: str, token: str, runtime: dict[str, str], channel_id: str) -> None:
    for username in (
        runtime.get("OPENCLAW_MATTERMOST_OPERATOR_USERNAME", ""),
        runtime.get("OPENCLAW_MATTERMOST_ADMIN_USERNAME", ""),
    ):
        ensure_user_joined_by_username(base_url, token, channel_id, username)


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
    channel_name = normalize_channel_name(args.channel_name)
    team_channels = list_team_channels(base_url, token, team_id)

    for channel in team_channels:
        if str(channel.get("name", "")).strip() == channel_name:
            channel_id = str(channel.get("id", "")).strip()
            ensure_joined_channel(base_url, token, me, channel_id)
            ensure_default_humans_joined(base_url, token, runtime, channel_id)
            print(f"CHANNEL_EXISTS {channel_id} {channel_name}")
            return 0

    triad_count = sum(1 for item in team_channels if str(item.get("name", "")).startswith(CHANNEL_PREFIX))
    if channel_name.startswith(CHANNEL_PREFIX) and triad_count >= MAX_TRIAD_CHANNELS:
        raise RuntimeError("triad channel cap reached")

    created = create_public_channel(base_url, token, team_id, channel_name, args.display_name, args.purpose)
    channel_id = str(created.get("id", "")).strip()
    ensure_joined_channel(base_url, token, me, channel_id)
    ensure_default_humans_joined(base_url, token, runtime, channel_id)
    print(f"CHANNEL_READY {channel_id} {channel_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(parse_args()))
