#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dispatch one Mattermost lounge turn via helper scripts.")
    parser.add_argument("--instance", type=int, required=True)
    return parser.parse_args()


def run_command(command: str) -> str:
    completed = subprocess.run(
        shlex.split(command),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = (completed.stdout.strip() or completed.stderr.strip()).strip()
    if completed.returncode != 0:
        raise RuntimeError(f"command failed: {command}\n{output}")
    return output


def load_state(instance_id: int) -> dict[str, object]:
    output = run_command(
        f"python3 /home/node/.openclaw/shared-board/tools/mattermost_get_state.py --instance {instance_id}"
    )
    payload = json.loads(output)
    if not isinstance(payload, dict):
        raise RuntimeError("mattermost_get_state.py did not return a JSON object.")
    return payload


def main(args: argparse.Namespace) -> int:
    state = load_state(args.instance)
    suggested = state.get("suggested_next")
    if not isinstance(suggested, dict):
        raise RuntimeError("suggested_next is missing from state payload.")

    kind = str(suggested.get("kind", "")).strip()
    if kind == "idle":
        final_text = str(suggested.get("final_text", "")).strip()
        if not final_text:
            raise RuntimeError("idle state is missing final_text.")
        print(final_text)
        return 0

    command = str(suggested.get("command", "")).strip()
    if not command:
        raise RuntimeError("suggested_next.command is missing.")
    output = run_command(command)
    expected_prefix = str(suggested.get("expected_prefix", "")).strip()
    if expected_prefix and not output.startswith(expected_prefix):
        raise RuntimeError(f"unexpected action output: {output}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(parse_args()))
