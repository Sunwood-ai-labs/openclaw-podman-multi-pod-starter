#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request


CONFIG_DIR = Path("/home/node/.openclaw")
CONTROL_ENV_PATH = CONFIG_DIR / "control.env"
OPENCLAW_CONFIG_PATH = CONFIG_DIR / "openclaw.json"
DEFAULT_OLLAMA_BASE_URL = "http://host.containers.internal:11434"
DEFAULT_OLLAMA_MODEL = "gemma4:e2b"
DEFAULT_MODEL_REF = f"ollama/{DEFAULT_OLLAMA_MODEL}"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
RATE_LIMIT_RETRY_COUNT = 10
RATE_LIMIT_RETRY_BASE_DELAY_SECONDS = 5
RATE_LIMIT_RETRY_MAX_DELAY_SECONDS = 30

HANDLES = {
    1: "iori",
    2: "tsumugi",
    3: "saku",
    4: "ruri",
    5: "hibiki",
    6: "kanae",
}

CHANNEL_PREFIX = "triad-"
MAX_TRIAD_CHANNELS = 8
MAX_RECENT_CHANNELS = 8
MAX_THREADS_PER_CHANNEL = 3
THREAD_PREVIEW_CHARS = 140

MIN_SECONDS_BETWEEN_ANY_TWO_POSTS = 60
MIN_SECONDS_BETWEEN_SAME_SPEAKER_POSTS = 4 * 60

BOT_IDS: dict[str, str] = {}
ENV_PLACEHOLDER_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


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


def resolved_model_ref(env: dict[str, str]) -> str:
    explicit = env.get("OPENCLAW_MODEL_REF", "").strip()
    if explicit:
        return explicit
    model_id = env.get("OPENCLAW_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip() or DEFAULT_OLLAMA_MODEL
    return f"ollama/{model_id}"


def split_model_ref(model_ref: str) -> tuple[str, str]:
    provider, separator, model_id = model_ref.partition("/")
    provider = provider.strip()
    model_id = model_id.strip()
    if not provider or not separator or not model_id:
        raise RuntimeError(f"OPENCLAW_MODEL_REF must look like provider/model. Got: {model_ref!r}")
    return provider, model_id


def planner_runtime_from_env(env: dict[str, str]) -> dict[str, str]:
    model_ref = resolved_model_ref(env)
    provider, model_id = split_model_ref(model_ref)
    if provider == "ollama":
        base_url = env.get("OPENCLAW_OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).strip() or DEFAULT_OLLAMA_BASE_URL
        api_key = env.get("OLLAMA_API_KEY", "").strip()
    elif provider == "openrouter":
        base_url = env.get("OPENCLAW_OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL).strip() or DEFAULT_OPENROUTER_BASE_URL
        api_key = env.get("OPENROUTER_API_KEY", "").strip()
    elif provider == "zai":
        base_url = env.get("OPENCLAW_ZAI_BASE_URL", DEFAULT_ZAI_BASE_URL).strip() or DEFAULT_ZAI_BASE_URL
        api_key = env.get("ZAI_API_KEY", "").strip()
    else:
        base_url = ""
        api_key = ""
    return {
        "model_ref": model_ref,
        "model_provider": provider,
        "model_id": model_id,
        "model_base_url": base_url,
        "model_api_key": api_key,
    }


def load_control_values() -> dict[str, str]:
    env = parse_env_file(CONTROL_ENV_PATH)
    runtime = planner_runtime_from_env(env)
    return {
        "team_name": env.get("OPENCLAW_MATTERMOST_TEAM_NAME", "openclaw").strip() or "openclaw",
        "default_channel": env.get("OPENCLAW_MATTERMOST_CHANNEL_NAME", "triad-lab").strip() or "triad-lab",
        "OPENCLAW_MATTERMOST_OPERATOR_USERNAME": env.get("OPENCLAW_MATTERMOST_OPERATOR_USERNAME", "operator").strip() or "operator",
        "OPENCLAW_MATTERMOST_ADMIN_USERNAME": env.get("OPENCLAW_MATTERMOST_ADMIN_USERNAME", "ocadmin").strip() or "ocadmin",
        **runtime,
    }


def load_openclaw_config() -> dict[str, object]:
    payload = json.loads(OPENCLAW_CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object in {OPENCLAW_CONFIG_PATH}")
    return payload


def resolve_env_placeholders(raw_value: str, env: dict[str, str]) -> str:
    return ENV_PLACEHOLDER_RE.sub(lambda match: env.get(match.group(1), match.group(0)), raw_value)


def load_mattermost_runtime() -> tuple[str, str]:
    config = load_openclaw_config()
    channels = config.get("channels")
    if not isinstance(channels, dict):
        raise RuntimeError("OpenClaw config is missing channels.mattermost")
    mattermost = channels.get("mattermost")
    if not isinstance(mattermost, dict):
        raise RuntimeError("OpenClaw config is missing channels.mattermost")
    control_env = {**os.environ, **parse_env_file(CONTROL_ENV_PATH)}
    base_url = resolve_env_placeholders(str(mattermost.get("baseUrl", "")), control_env).strip()
    bot_token = resolve_env_placeholders(str(mattermost.get("botToken", "")), control_env).strip()
    if not base_url or not bot_token:
        raise RuntimeError("Mattermost baseUrl/botToken is missing from openclaw.json")
    return base_url, bot_token


class RateLimitRetryError(RuntimeError):
    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def rate_limit_retry_delay_seconds(retry_index: int, retry_after_seconds: float | None = None) -> float:
    if retry_after_seconds is not None and retry_after_seconds > 0:
        return retry_after_seconds
    return float(min(RATE_LIMIT_RETRY_BASE_DELAY_SECONDS * max(1, retry_index), RATE_LIMIT_RETRY_MAX_DELAY_SECONDS))


def http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, object] | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, str], object | None]:
    data: bytes | None = None
    merged_headers = {"Accept": "application/json"}
    if headers:
        merged_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        merged_headers["Content-Type"] = "application/json"
    req = urllib_request.Request(url, data=data, method=method, headers=merged_headers)
    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            raw_body = response.read()
            parsed: object | None = None
            if raw_body:
                parsed = json.loads(raw_body.decode("utf-8"))
            return response.status, dict(response.headers.items()), parsed
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        if exc.code == 429:
            retry_after_seconds: float | None = None
            retry_after = exc.headers.get("Retry-After")
            if retry_after:
                try:
                    retry_after_seconds = float(retry_after)
                except ValueError:
                    retry_after_seconds = None
            if retry_after_seconds is None:
                reset_header = exc.headers.get("X-RateLimit-Reset")
                if reset_header:
                    try:
                        retry_after_seconds = max(0.0, (float(reset_header) / 1000.0) - time.time())
                    except ValueError:
                        retry_after_seconds = None
            raise RateLimitRetryError(f"HTTP {exc.code} {url}: {body}", retry_after_seconds=retry_after_seconds) from exc
        raise RuntimeError(f"HTTP {exc.code} {url}: {body}") from exc


def mattermost_request(
    base_url: str,
    token: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, str], object | None]:
    return http_json(
        base_url + path,
        method=method,
        headers={"Authorization": f"Bearer {token}"},
        payload=payload,
    )


def fetch_me(base_url: str, token: str) -> dict[str, object]:
    _, _, payload = mattermost_request(base_url, token, "/api/v4/users/me")
    if not isinstance(payload, dict):
        raise RuntimeError("Could not resolve Mattermost bot user.")
    return payload


def resolve_team(base_url: str, token: str, team_name: str) -> tuple[str, str]:
    _, _, payload = mattermost_request(base_url, token, f"/api/v4/teams/name/{team_name}")
    if not isinstance(payload, dict):
        raise RuntimeError("Could not resolve Mattermost team.")
    return team_name, str(payload.get("id", "")).strip()


def list_team_channels(base_url: str, token: str, team_id: str) -> list[dict[str, object]]:
    _, _, payload = mattermost_request(base_url, token, f"/api/v4/teams/{team_id}/channels?page=0&per_page=200")
    if not isinstance(payload, list):
        raise RuntimeError("Could not list Mattermost team channels.")
    return [item for item in payload if isinstance(item, dict) and item.get("type") == "O"]


def list_my_channels(base_url: str, token: str, team_id: str) -> set[str]:
    _, _, payload = mattermost_request(base_url, token, f"/api/v4/users/me/teams/{team_id}/channels")
    if not isinstance(payload, list):
        return set()
    result: set[str] = set()
    for item in payload:
        if isinstance(item, dict):
            channel_id = str(item.get("id", "")).strip()
            if channel_id:
                result.add(channel_id)
    return result


def fetch_channel_posts(base_url: str, token: str, channel_id: str, per_page: int = 80) -> tuple[dict[str, object], list[str]]:
    _, _, payload = mattermost_request(base_url, token, f"/api/v4/channels/{channel_id}/posts?page=0&per_page={per_page}")
    if not isinstance(payload, dict):
        raise RuntimeError("Mattermost channel posts payload was not a JSON object.")
    posts = payload.get("posts")
    order = payload.get("order")
    if not isinstance(posts, dict) or not isinstance(order, list):
        raise RuntimeError("Mattermost channel posts payload is missing posts/order.")
    return posts, [str(item) for item in order]


def resolve_bot_ids(base_url: str, token: str) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for handle in HANDLES.values():
        _, _, payload = mattermost_request(base_url, token, f"/api/v4/users/username/{handle}")
        if isinstance(payload, dict):
            resolved[handle] = str(payload.get("id", "")).strip()
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


def should_rate_limit(handle: str, posts: dict[str, object], order: list[str], bot_ids: dict[str, str], force: bool) -> tuple[bool, str]:
    if force:
        return False, "force"
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    latest_ts = latest_channel_timestamp(posts, order)
    own_latest_ts = latest_post_for_handle(posts, order, bot_ids, handle)
    if own_latest_ts and now_ms - own_latest_ts < MIN_SECONDS_BETWEEN_SAME_SPEAKER_POSTS * 1000:
        return True, "recent-self"
    if latest_ts and now_ms - latest_ts < MIN_SECONDS_BETWEEN_ANY_TWO_POSTS * 1000:
        return True, "cooldown"
    return False, "ok"


def build_thread_summaries(posts: dict[str, object], order: list[str], bot_ids: dict[str, str]) -> list[dict[str, object]]:
    summaries: dict[str, dict[str, object]] = {}
    for post_id in reversed(order):
        post = posts.get(post_id)
        if not isinstance(post, dict):
            continue
        root_id = str(post.get("root_id", "")).strip() or post_id
        create_at = int(post.get("create_at", 0) or 0)
        bucket = summaries.setdefault(
            root_id,
            {
                "root_post_id": root_id,
                "last_post_id": "",
                "last_ts": 0,
                "last_handle": "",
                "root_handle": "",
                "count": 0,
                "root_preview": "",
                "participants": [],
            },
        )
        bucket["count"] = int(bucket["count"]) + 1
        user_id = str(post.get("user_id", ""))
        handle = next((h for h, bid in bot_ids.items() if bid == user_id), user_id)
        participants = bucket.get("participants")
        if isinstance(participants, list) and handle and handle not in participants:
            participants.append(handle)
        if create_at >= int(bucket["last_ts"]):
            bucket["last_ts"] = create_at
            bucket["last_post_id"] = post_id
            bucket["last_handle"] = handle
        if root_id == post_id and not bucket["root_preview"]:
            preview = str(post.get("message", "")).replace("\r\n", " ").strip()
            bucket["root_preview"] = preview[:THREAD_PREVIEW_CHARS]
            bucket["root_handle"] = handle
    return sorted(summaries.values(), key=lambda item: int(item["last_ts"]), reverse=True)


def summarize_channels(
    base_url: str,
    token: str,
    team_channels: list[dict[str, object]],
    my_channel_ids: set[str],
    default_channel: str,
    bot_ids: dict[str, str],
) -> list[dict[str, object]]:
    triad_channels = [
        channel
        for channel in team_channels
        if str(channel.get("name", "")).startswith(CHANNEL_PREFIX)
    ]
    sorted_channels = sorted(triad_channels, key=lambda item: int(item.get("last_post_at", 0) or 0), reverse=True)
    selected: list[dict[str, object]] = []
    default_match = next((channel for channel in sorted_channels if str(channel.get("name", "")).strip() == default_channel), None)
    if isinstance(default_match, dict):
        selected.append(default_match)
    for channel in sorted_channels:
        if default_match is channel:
            continue
        selected.append(channel)
        if len(selected) >= MAX_RECENT_CHANNELS:
            break
    result: list[dict[str, object]] = []
    for channel in selected:
        channel_id = str(channel.get("id", "")).strip()
        posts, order = fetch_channel_posts(base_url, token, channel_id)
        result.append(
            {
                "channel_id": channel_id,
                "channel_name": str(channel.get("name", "")).strip(),
                "display_name": str(channel.get("display_name", "")).strip(),
                "purpose": str(channel.get("purpose", "")).strip(),
                "member": channel_id in my_channel_ids,
                "last_post_at": int(channel.get("last_post_at", 0) or 0),
                "threads": build_thread_summaries(posts, order, bot_ids)[:MAX_THREADS_PER_CHANNEL],
            }
        )
    return result


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


def normalize_channel_name(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", raw.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if not slug.startswith(CHANNEL_PREFIX):
        slug = CHANNEL_PREFIX + slug.lstrip("-")
    return slug


def ensure_joined_channel(base_url: str, token: str, me: dict[str, object], channel_id: str) -> None:
    user_id = str(me.get("id", "")).strip()
    _, _, _ = mattermost_request(
        base_url,
        token,
        f"/api/v4/channels/{channel_id}/members",
        method="POST",
        payload={"user_id": user_id},
    )


def post_message(base_url: str, token: str, channel_id: str, message: str, *, root_post_id: str | None = None) -> str:
    payload = {"channel_id": channel_id, "message": clean_message(message)}
    if root_post_id:
        payload["root_id"] = root_post_id
    _, _, response = mattermost_request(base_url, token, "/api/v4/posts", method="POST", payload=payload)
    if not isinstance(response, dict):
        raise RuntimeError("Mattermost post creation did not return a JSON object.")
    post_id = str(response.get("id", "")).strip()
    if not post_id:
        raise RuntimeError("Mattermost post creation returned no post id.")
    return post_id


def create_public_channel(base_url: str, token: str, team_id: str, channel_name: str, display_name: str, purpose: str) -> dict[str, object]:
    payload = {
        "team_id": team_id,
        "name": channel_name,
        "display_name": display_name,
        "purpose": purpose,
        "type": "O",
    }
    _, _, response = mattermost_request(base_url, token, "/api/v4/channels", method="POST", payload=payload)
    if not isinstance(response, dict):
        raise RuntimeError("Mattermost channel creation did not return a JSON object.")
    return response


def find_channel_summary(channel_summaries: list[dict[str, object]], channel_name: str) -> dict[str, object] | None:
    for channel in channel_summaries:
        if str(channel.get("channel_name", "")).strip() == channel_name:
            return channel
    return None
