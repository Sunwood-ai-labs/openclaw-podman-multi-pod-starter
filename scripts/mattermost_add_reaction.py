#!/usr/bin/env python3
from __future__ import annotations

import argparse

from mattermost_autochat_turn import HANDLES, fetch_me, load_mattermost_runtime, mattermost_request


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

    emoji_name = normalize_emoji_name(args.emoji)
    _, _, payload = mattermost_request(
        base_url,
        token,
        "/api/v4/reactions",
        method="POST",
        payload={
            "user_id": str(me.get("id", "")).strip(),
            "post_id": args.post_id.strip(),
            "emoji_name": emoji_name,
        },
    )
    if not isinstance(payload, dict):
        raise RuntimeError("Mattermost reaction creation did not return a JSON object.")
    print(f"REACTION_ADDED {args.post_id.strip()} :{emoji_name}:")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(parse_args()))
