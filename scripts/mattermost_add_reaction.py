#!/usr/bin/env python3
from __future__ import annotations

import argparse

from mattermost_autochat_turn import (
    HANDLES,
    ensure_joined_channel,
    fetch_me,
    load_mattermost_runtime,
    mattermost_request,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add a Mattermost reaction to a post.")
    parser.add_argument("--instance", type=int, choices=sorted(HANDLES), required=True)
    parser.add_argument("--post-id", required=True)
    parser.add_argument("--emoji", required=True)
    return parser.parse_args()


def normalize_emoji_name(value: str) -> str:
    return value.strip().strip(":")


def main(args: argparse.Namespace) -> int:
    instance_id = args.instance
    handle = HANDLES[instance_id]
    base_url, token = load_mattermost_runtime()

    me = fetch_me(base_url, token)
    actual_handle = str(me.get("username", "")).strip()
    if actual_handle and actual_handle != handle:
        raise RuntimeError(f"wrong-handle expected={handle} actual={actual_handle}")

    post_id = args.post_id.strip()
    _, _, post_payload = mattermost_request(base_url, token, f"/api/v4/posts/{post_id}")
    if not isinstance(post_payload, dict):
        raise RuntimeError("Mattermost post lookup did not return a JSON object.")
    channel_id = str(post_payload.get("channel_id", "")).strip()
    if not channel_id:
        raise RuntimeError("Mattermost post lookup returned no channel_id.")
    ensure_joined_channel(base_url, token, me, channel_id)

    emoji_name = normalize_emoji_name(args.emoji)
    _, _, payload = mattermost_request(
        base_url,
        token,
        "/api/v4/reactions",
        method="POST",
        payload={
            "user_id": str(me.get("id", "")).strip(),
            "post_id": post_id,
            "emoji_name": emoji_name,
        },
    )
    if not isinstance(payload, dict):
        raise RuntimeError("Mattermost reaction creation did not return a JSON object.")
    print(f"REACTION_ADDED {post_id} :{emoji_name}:")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(parse_args()))
