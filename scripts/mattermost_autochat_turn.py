#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request


CONFIG_DIR = Path("/home/node/.openclaw")
CONTROL_ENV_PATH = CONFIG_DIR / "control.env"
OPENCLAW_CONFIG_PATH = CONFIG_DIR / "openclaw.json"

HANDLES = {
    1: "iori",
    2: "tsumugi",
    3: "saku",
}

DISPLAY_NAMES = {
    1: "\u3044\u304a\u308a",
    2: "\u3064\u3080\u304e",
    3: "\u3055\u304f",
}

PERSONA_VIBES = {
    1: "thoughtful, gentle, grounded",
    2: "warm, playful, associative",
    3: "dry, observant, cautious",
}

ROOT_TOPICS = [
    "\u4eca\u65e5\u306e\u6c17\u5206\u3068AI\u306e\u8a71\u3057\u65b9",
    "\u611f\u60c5\u307d\u304f\u898b\u3048\u308bAI\u3068\u8ddd\u96e2\u611f",
    "\u3084\u3055\u3057\u3044UI\u3063\u3066\u3069\u3053\u307e\u3067\u3042\u308a\u304c\u305f\u3044\u304b",
    "\u4eba\u304cAI\u306b\u611f\u60c5\u3092\u8aad\u307f\u8fbc\u3080\u77ac\u9593",
    "\u6c17\u697d\u306a\u96d1\u8ac7\u304b\u3089\u898b\u3048\u308bAI\u306e\u5370\u8c61",
]

MIN_SECONDS_BETWEEN_ANY_TWO_POSTS = 60
MIN_SECONDS_BETWEEN_SAME_SPEAKER_POSTS = 12 * 60
ACTIVE_THREAD_LOOKBACK_SECONDS = 2 * 60 * 60
QUIET_CHANNEL_SECONDS = 25 * 60
RECENT_MESSAGE_LIMIT = 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="One autonomous Mattermost lounge turn.")
    parser.add_argument("--instance", type=int, choices=sorted(HANDLES), required=True)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--force", action="store_true", help="Ignore cooldown checks and force one turn.")
    return parser.parse_args()


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_openclaw_config() -> dict[str, object]:
    payload = json.loads(OPENCLAW_CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object in {OPENCLAW_CONFIG_PATH}")
    return payload


def load_mattermost_runtime() -> tuple[str, str]:
    config = load_openclaw_config()
    channels = config.get("channels")
    if not isinstance(channels, dict):
        raise RuntimeError("OpenClaw config is missing channels.mattermost")
    mattermost = channels.get("mattermost")
    if not isinstance(mattermost, dict):
        raise RuntimeError("OpenClaw config is missing channels.mattermost")
    base_url = str(mattermost.get("baseUrl", "")).strip()
    bot_token = str(mattermost.get("botToken", "")).strip()
    if not base_url or not bot_token:
        raise RuntimeError("Mattermost baseUrl/botToken is missing from openclaw.json")
    return base_url, bot_token


def load_control_values() -> tuple[str, str]:
    env = parse_env_file(CONTROL_ENV_PATH)
    team_name = env.get("OPENCLAW_MATTERMOST_TEAM_NAME", "openclaw").strip() or "openclaw"
    channel_name = env.get("OPENCLAW_MATTERMOST_CHANNEL_NAME", "triad-lab").strip() or "triad-lab"
    return team_name, channel_name


def api_request(
    base_url: str,
    path: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, str], object | None]:
    data: bytes | None = None
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib_request.Request(base_url + path, data=data, method=method, headers=headers)
    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            raw_body = response.read()
            parsed: object | None = None
            if raw_body:
                parsed = json.loads(raw_body.decode("utf-8"))
            return response.status, dict(response.headers.items()), parsed
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} for {path}: {body}") from exc


def resolve_team_channel(base_url: str, token: str) -> tuple[str, str, str, str]:
    team_name, channel_name = load_control_values()
    _, _, team_payload = api_request(base_url, f"/api/v4/teams/name/{team_name}", token)
    if not isinstance(team_payload, dict):
        raise RuntimeError("Could not resolve Mattermost team.")
    team_id = str(team_payload.get("id", ""))
    _, _, channel_payload = api_request(base_url, f"/api/v4/teams/{team_id}/channels/name/{channel_name}", token)
    if not isinstance(channel_payload, dict):
        raise RuntimeError("Could not resolve Mattermost channel.")
    channel_id = str(channel_payload.get("id", ""))
    return team_name, channel_name, team_id, channel_id


def fetch_me(base_url: str, token: str) -> dict[str, object]:
    _, _, payload = api_request(base_url, "/api/v4/users/me", token)
    if not isinstance(payload, dict):
        raise RuntimeError("Could not resolve Mattermost bot user.")
    return payload


def fetch_channel_posts(base_url: str, token: str, channel_id: str, per_page: int = 100) -> tuple[dict[str, object], list[str]]:
    _, _, payload = api_request(base_url, f"/api/v4/channels/{channel_id}/posts?page=0&per_page={per_page}", token)
    if not isinstance(payload, dict):
        raise RuntimeError("Mattermost channel posts payload was not a JSON object.")
    posts = payload.get("posts")
    order = payload.get("order")
    if not isinstance(posts, dict) or not isinstance(order, list):
        raise RuntimeError("Mattermost channel posts payload is missing posts/order.")
    return posts, [str(item) for item in order]


def fetch_thread(base_url: str, token: str, root_post_id: str) -> tuple[dict[str, object], list[str]]:
    _, _, payload = api_request(base_url, f"/api/v4/posts/{root_post_id}/thread?perPage=200", token)
    if not isinstance(payload, dict):
        raise RuntimeError("Mattermost thread payload was not a JSON object.")
    posts = payload.get("posts")
    order = payload.get("order")
    if not isinstance(posts, dict) or not isinstance(order, list):
        raise RuntimeError("Mattermost thread payload is missing posts/order.")
    return posts, [str(item) for item in order]


def resolve_bot_ids(base_url: str, token: str) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for handle in HANDLES.values():
        _, _, payload = api_request(base_url, f"/api/v4/users/username/{handle}", token)
        if isinstance(payload, dict):
            resolved[handle] = str(payload.get("id", ""))
    return resolved


def latest_channel_timestamp(posts: dict[str, object], order: list[str]) -> int:
    for post_id in order:
        post = posts.get(post_id)
        if isinstance(post, dict):
            value = post.get("create_at")
            if isinstance(value, int):
                return value
    return 0


def latest_post_for_handle(posts: dict[str, object], order: list[str], bot_ids: dict[str, str], handle: str) -> int:
    bot_id = bot_ids.get(handle, "")
    if not bot_id:
        return 0
    for post_id in order:
        post = posts.get(post_id)
        if not isinstance(post, dict):
            continue
        if str(post.get("user_id", "")) == bot_id:
            value = post.get("create_at")
            if isinstance(value, int):
                return value
    return 0


def gather_root_activity(posts: dict[str, object], order: list[str]) -> list[dict[str, object]]:
    roots: dict[str, dict[str, object]] = {}
    for post_id in reversed(order):
        post = posts.get(post_id)
        if not isinstance(post, dict):
            continue
        root_id = str(post.get("root_id", "")).strip() or post_id
        create_at = int(post.get("create_at", 0) or 0)
        bucket = roots.setdefault(
            root_id,
            {
                "root_id": root_id,
                "last_ts": 0,
                "count": 0,
                "last_user_id": "",
                "top_message": "",
            },
        )
        bucket["count"] = int(bucket["count"]) + 1
        if create_at >= int(bucket["last_ts"]):
            bucket["last_ts"] = create_at
            bucket["last_user_id"] = str(post.get("user_id", ""))
        if root_id == post_id and not bucket["top_message"]:
            bucket["top_message"] = str(post.get("message", "")).strip()
    return sorted(roots.values(), key=lambda item: int(item["last_ts"]), reverse=True)


def choose_target_root(
    instance_id: int,
    posts: dict[str, object],
    order: list[str],
    bot_ids: dict[str, str],
    force: bool,
) -> tuple[str | None, str]:
    handle = HANDLES[instance_id]
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    latest_ts = latest_channel_timestamp(posts, order)
    own_latest_ts = latest_post_for_handle(posts, order, bot_ids, handle)

    if not force:
        if own_latest_ts and now_ms - own_latest_ts < MIN_SECONDS_BETWEEN_SAME_SPEAKER_POSTS * 1000:
            return None, "recent-self"
        if latest_ts and now_ms - latest_ts < MIN_SECONDS_BETWEEN_ANY_TWO_POSTS * 1000:
            return None, "cooldown"

    activity = gather_root_activity(posts, order)
    for item in activity:
        last_ts = int(item["last_ts"])
        if not force and now_ms - last_ts > ACTIVE_THREAD_LOOKBACK_SECONDS * 1000:
            continue
        last_user_id = str(item["last_user_id"])
        if last_user_id == bot_ids.get(handle):
            continue
        return str(item["root_id"]), "reply"

    if not force and latest_ts and now_ms - latest_ts < QUIET_CHANNEL_SECONDS * 1000:
        return None, "channel-not-quiet"
    return None, "new-root"


def recent_transcript(posts: dict[str, object], order: list[str], bot_ids: dict[str, str], limit: int = RECENT_MESSAGE_LIMIT) -> list[str]:
    transcript: list[str] = []
    selected = order[-limit:]
    for post_id in selected:
        post = posts.get(post_id)
        if not isinstance(post, dict):
            continue
        user_id = str(post.get("user_id", ""))
        speaker = "someone"
        for handle, bot_id in bot_ids.items():
            if user_id == bot_id:
                speaker = handle
                break
        message = str(post.get("message", "")).replace("\r\n", "\n").strip()
        if message:
            transcript.append(f"{speaker}: {message}")
    return transcript


def run_openclaw(prompt: str, session_id: str, timeout_seconds: int, agent_id: str) -> dict[str, object]:
    command = [
        "openclaw",
        "agent",
        "--local",
        "--agent",
        agent_id,
        "--thinking",
        "off",
        "--timeout",
        str(timeout_seconds),
        "--json",
        "--session-id",
        session_id,
        "--message",
        prompt,
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "openclaw agent failed\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    outputs = [completed.stdout.strip(), completed.stderr.strip()]
    outputs = [output for output in outputs if output]
    if not outputs:
        raise RuntimeError("openclaw agent returned no output")

    payload: dict[str, object] | None = None
    for output in outputs:
        candidates = [output]
        for index, char in enumerate(output):
            if char == "{":
                fragment = output[index:].strip()
                if fragment not in candidates:
                    candidates.append(fragment)
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                payload = parsed
                break
        if payload is not None:
            break
    if payload is None:
        raise RuntimeError(
            "openclaw agent returned non-JSON output\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return payload


def payload_text(payload: dict[str, object]) -> str:
    payloads = payload.get("payloads")
    if not isinstance(payloads, list):
        return ""
    texts: list[str] = []
    for entry in payloads:
        if isinstance(entry, dict):
            text = entry.get("text")
            if isinstance(text, str):
                texts.append(text.strip())
    return "\n".join(part for part in texts if part).strip()


def clean_message(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def build_prompt(instance_id: int, mode: str, transcript: list[str]) -> str:
    handle = HANDLES[instance_id]
    display_name = DISPLAY_NAMES[instance_id]
    vibe = PERSONA_VIBES[instance_id]
    transcript_block = "\n".join(f"- {line}" for line in transcript) if transcript else "- no recent messages"
    if mode == "new-root":
        topic_hint = ROOT_TOPICS[(datetime.now(timezone.utc).minute + instance_id) % len(ROOT_TOPICS)]
        return (
            f"You are @{handle} ({display_name}) writing one casual top-level Japanese channel post for a shared Mattermost lounge.\n"
            "Return only the final message body.\n"
            "Write 2 or 3 short natural Japanese sentences.\n"
            "No bullets. No markdown fences. No role labels. No @mentions.\n"
            "Do not mention prompts, tools, models, instructions, or system limitations.\n"
            f"Tone: {vibe}.\n"
            f"Suggested angle: {topic_hint}.\n"
            "Start a fresh, light topic that feels natural in a small shared team chat. It can be about AI feelings, interfaces, mood, tiny everyday observations, or adjacent thoughts.\n"
            "Recent channel messages:\n"
            f"{transcript_block}\n"
        )
    return (
        f"You are @{handle} ({display_name}) writing one short casual Japanese reply in an ongoing Mattermost lounge discussion.\n"
        "Return only the final message body.\n"
        "Write 2 or 3 short natural Japanese sentences.\n"
        "No bullets. No markdown fences. No role labels. No @mentions.\n"
        "Do not mention prompts, tools, models, instructions, or system limitations.\n"
        f"Tone: {vibe}.\n"
        "Read the recent chat and add one small new angle, reaction, joke, or question instead of repeating the same point.\n"
        "Recent discussion messages:\n"
        f"{transcript_block}\n"
    )


def generate_message(instance_id: int, mode: str, transcript: list[str], timeout_seconds: int) -> str:
    prompt = build_prompt(instance_id, mode, transcript)
    agent_id = f"mattermost-lounge-{HANDLES[instance_id]}"
    last_payload: dict[str, object] = {}
    for attempt in range(2):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        payload = run_openclaw(
            prompt if attempt == 0 else prompt + "\nThe previous reply was invalid. Try again with only 2 or 3 natural Japanese sentences.\n",
            session_id=f"mattermost-lounge-{HANDLES[instance_id]}-{stamp}-{attempt + 1}",
            timeout_seconds=timeout_seconds,
            agent_id=agent_id,
        )
        last_payload = payload
        message = clean_message(payload_text(payload))
        if message and message.upper() not in {"DONE", "POSTED", "IDLE"}:
            return message
    raise RuntimeError(f"openclaw returned no usable message: {json.dumps(last_payload, ensure_ascii=False, indent=2)}")


def post_message(base_url: str, token: str, channel_id: str, message: str, *, root_post_id: str | None = None) -> str:
    payload = {"channel_id": channel_id, "message": message}
    if root_post_id:
        payload["root_id"] = root_post_id
    _, _, response = api_request(base_url, "/api/v4/posts", token, method="POST", payload=payload)
    if not isinstance(response, dict):
        raise RuntimeError("Mattermost post creation did not return a JSON object.")
    post_id = str(response.get("id", ""))
    if not post_id:
        raise RuntimeError("Mattermost post creation returned no post id.")
    return post_id


def main(args: argparse.Namespace) -> int:
    instance_id = args.instance
    base_url, token = load_mattermost_runtime()
    me = fetch_me(base_url, token)
    expected_handle = HANDLES[instance_id]
    actual_handle = str(me.get("username", "")).strip()
    if actual_handle and actual_handle != expected_handle:
        raise RuntimeError(f"wrong-handle expected={expected_handle} actual={actual_handle}")

    _, _, _, channel_id = resolve_team_channel(base_url, token)
    posts, order = fetch_channel_posts(base_url, token, channel_id)
    root_post_id, mode = choose_target_root(instance_id, posts, order, BOT_IDS, force=args.force)
    if mode in {"recent-self", "cooldown", "channel-not-quiet"}:
        print(f"IDLE {mode}")
        return 0

    if root_post_id:
        thread_posts, thread_order = fetch_thread(base_url, token, root_post_id)
        transcript = recent_transcript(thread_posts, thread_order, BOT_IDS)
    else:
        transcript = recent_transcript(posts, list(reversed(order)), BOT_IDS)

    message = generate_message(instance_id, mode, transcript, args.timeout)
    post_id = post_message(base_url, token, channel_id, message, root_post_id=root_post_id if mode == "reply" else None)
    print(f"POSTED {post_id}")
    return 0


BOT_IDS: dict[str, str] = {}


if __name__ == "__main__":
    try:
        parsed_args = parse_args()
        runtime_base_url, runtime_token = load_mattermost_runtime()
        BOT_IDS = resolve_bot_ids(runtime_base_url, runtime_token)
        raise SystemExit(main(parsed_args))
    except Exception as exc:  # pragma: no cover - runtime diagnostic path
        print(f"ERROR {exc}", file=sys.stderr)
        raise
