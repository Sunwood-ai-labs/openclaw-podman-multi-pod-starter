from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from openclaw_podman_starter import cli

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

MATTERMOST_GET_STATE_PATH = SCRIPTS_DIR / "mattermost_get_state.py"
mattermost_get_state_spec = importlib.util.spec_from_file_location("mattermost_get_state", MATTERMOST_GET_STATE_PATH)
mattermost_get_state = importlib.util.module_from_spec(mattermost_get_state_spec)
assert mattermost_get_state_spec and mattermost_get_state_spec.loader
sys.modules[mattermost_get_state_spec.name] = mattermost_get_state
mattermost_get_state_spec.loader.exec_module(mattermost_get_state)


def write_env_file(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "OPENCLAW_CONTAINER=openclaw",
                "OPENCLAW_PODMAN_CONTAINER=openclaw",
                "OPENCLAW_PODMAN_PUBLISH_HOST=127.0.0.1",
                "OPENCLAW_SCALE_INSTANCE_ROOT=./instances",
                "OPENCLAW_OLLAMA_MODEL=gemma4:e2b",
                "OPENCLAW_OLLAMA_BASE_URL=http://127.0.0.1:11434",
                "OLLAMA_API_KEY=ollama-local",
                "",
            ]
        ),
        encoding="utf-8",
    )


class CliTests(unittest.TestCase):
    def test_mattermost_lounge_prompt_mentions_action_scripts(self) -> None:
        instance = cli.ScaledInstance(
            instance_id=1,
            pod_name="openclaw-1-pod",
            container_name="openclaw-1",
            config=cli.Config(
                env_file=Path("D:/tmp/.env"),
                container_name="openclaw-1",
                image="image",
                gateway_port=18789,
                bridge_port=18790,
                board_port=18889,
                publish_host="127.0.0.1",
                network="podman",
                gateway_bind="lan",
                userns="keep-id",
                config_dir=Path("D:/tmp/instances/agent_001"),
                workspace_dir=Path("D:/tmp/instances/agent_001/workspace"),
                gateway_token="token",
                ollama_base_url="http://127.0.0.1:11434",
                ollama_model="gemma4:e2b",
                board_image="python:3.11-slim",
                raw_env={},
            ),
        )
        prompt = cli.build_mattermost_lounge_turn_prompt(instance)
        self.assertIn("mattermost_workspace_turn.py", prompt)
        self.assertIn(cli.CONTAINER_MATTERMOST_TOOLS_DIR, prompt)
        self.assertIn("workspace の `SOUL.md` / `IDENTITY.md` を source of truth", prompt)
        self.assertIn("stdout だけをそのまま返答してください", prompt)

    def test_latest_assistant_text_ignores_non_assistant_entries(self) -> None:
        payload = {
            "payloads": [
                {"role": "tool", "text": "tool output"},
                {"role": "assistant", "text": "python3 /tmp/example.py"},
                {"role": "assistant", "text": "POSTED abc123"},
            ]
        }
        self.assertEqual(cli.latest_assistant_text(payload), "POSTED abc123")

    def test_mattermost_get_state_module_exposes_main(self) -> None:
        self.assertTrue(hasattr(mattermost_get_state, "main"))

    def test_scaled_instance_state_seeds_triads_and_mattermost_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            env_file = temp_root / ".env"
            write_env_file(env_file)

            expected = {1: "いおり", 2: "つむぎ", 3: "さく"}
            for instance_id, name in expected.items():
                resolved = cli.ensure_scaled_instance_state(cli.scaled_instance(env_file, instance_id))
                soul_path = resolved.config.workspace_dir / "SOUL.md"
                identity_path = resolved.config.workspace_dir / "IDENTITY.md"
                tools_path = resolved.config.workspace_dir / "TOOLS.md"
                mattermost_tools = cli.mattermost_tools_root(resolved)

                self.assertTrue(soul_path.exists())
                self.assertTrue(identity_path.exists())
                self.assertTrue(tools_path.exists())
                self.assertFalse((resolved.config.workspace_dir / "BBS.md").exists())
                self.assertTrue((mattermost_tools / "mattermost_workspace_turn.py").exists())
                self.assertTrue((mattermost_tools / "mattermost_get_state.py").exists())
                self.assertTrue((mattermost_tools / "mattermost_post_message.py").exists())
                self.assertTrue((mattermost_tools / "mattermost_create_channel.py").exists())
                self.assertTrue((mattermost_tools / "mattermost_add_reaction.py").exists())
                self.assertTrue((mattermost_tools / "mattermost_autochat_turn.py").exists())

                soul_text = soul_path.read_text(encoding="utf-8")
                identity_text = identity_path.read_text(encoding="utf-8")
                tools_text = tools_path.read_text(encoding="utf-8")

                self.assertIn(f"# SOUL.md - {name}", soul_text)
                self.assertIn(f"**名前:** {name}", identity_text)
                self.assertIn(cli.CONTAINER_MATTERMOST_TOOLS_DIR, tools_text)

    def test_scaled_instance_manifest_no_longer_mounts_shared_board(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            env_file = temp_root / ".env"
            write_env_file(env_file)

            resolved = cli.ensure_scaled_instance_state(cli.scaled_instance(env_file, 2))
            manifest = json.loads((resolved.config.config_dir / "pod.yaml").read_text(encoding="utf-8"))
            containers = manifest["spec"]["containers"]
            volume_mounts = containers[0]["volumeMounts"]
            volumes = manifest["spec"]["volumes"]

            self.assertEqual(len(containers), 1)
            self.assertEqual(containers[0]["name"], "openclaw-2")
            self.assertEqual(volume_mounts, [{"name": "openclaw-state", "mountPath": cli.CONTAINER_CONFIG_DIR}])
            self.assertEqual(len(volumes), 1)
            self.assertEqual(volumes[0]["name"], "openclaw-state")
            self.assertFalse((resolved.config.config_dir / "board-pod.yaml").exists())

    def test_scaled_launch_dry_run_has_no_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            env_file = temp_root / ".env"
            write_env_file(env_file)

            args = argparse.Namespace(
                env_file=env_file,
                dry_run=True,
                no_init=False,
                instance=None,
                count=3,
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = cli.cmd_launch(args)

            self.assertEqual(exit_code, 0)
            self.assertRegex(output.getvalue().lower(), r"\bpodman(?:\.exe)? kube play\b")
            self.assertIn("--network", output.getvalue().lower())
            self.assertNotIn("board-pod.yaml", output.getvalue().lower())
            self.assertFalse((temp_root / "instances").exists())

    def test_mattermost_token_is_injected_into_scaled_instance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            env_file = temp_root / ".env"
            write_env_file(env_file)

            mattermost_root = temp_root / ".openclaw" / "mattermost"
            mattermost_root.mkdir(parents=True)
            (mattermost_root / "state.env").write_text(
                "OPENCLAW_MATTERMOST_BOT_TOKEN_002=mm-token-2\n",
                encoding="utf-8",
            )

            instance = cli.scaled_instance(env_file, 2)
            self.assertEqual(instance.config.raw_env["OPENCLAW_MATTERMOST_BOT_TOKEN"], "mm-token-2")
            self.assertEqual(instance.config.raw_env["OPENCLAW_MATTERMOST_ENABLED"], "true")

    def test_ensure_openclaw_config_writes_mattermost_channel_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            env_file = temp_root / ".env"
            write_env_file(env_file)
            env_text = env_file.read_text(encoding="utf-8")
            env_text += "\n".join(
                [
                    "OPENCLAW_MATTERMOST_ENABLED=true",
                    "OPENCLAW_MATTERMOST_BASE_URL=http://mattermost:8065",
                    "OPENCLAW_MATTERMOST_BOT_TOKEN=test-bot-token",
                    "",
                ]
            )
            env_file.write_text(env_text, encoding="utf-8")

            cfg = cli.ensure_state(cli.load_config(env_file))
            payload = json.loads((cfg.config_dir / "openclaw.json").read_text(encoding="utf-8"))

            self.assertEqual(payload["channels"]["mattermost"]["enabled"], True)
            self.assertEqual(payload["channels"]["mattermost"]["baseUrl"], "http://mattermost:8065")
            self.assertEqual(payload["channels"]["mattermost"]["botToken"], "test-bot-token")
            self.assertEqual(payload["channels"]["mattermost"]["chatmode"], "oncall")
            self.assertEqual(payload["channels"]["mattermost"]["groups"]["*"]["requireMention"], True)
            self.assertEqual(payload["channels"]["mattermost"]["network"]["dangerouslyAllowPrivateNetwork"], True)
            self.assertEqual(payload["plugins"]["entries"]["mattermost"]["enabled"], True)

    def test_load_mattermost_config_uses_default_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            env_file = temp_root / ".env"
            write_env_file(env_file)

            cfg = cli.load_mattermost_config(env_file)

            self.assertEqual(cfg.network, cli.DEFAULT_PODMAN_NETWORK)
            self.assertEqual(cli.mattermost_host_url(cfg), "http://127.0.0.1:8065")
            expected_manifest = os.path.normcase(os.path.realpath(str(temp_root / ".openclaw" / "mattermost" / "pod.yaml")))
            actual_manifest = os.path.normcase(os.path.realpath(str(cli.mattermost_manifest_path(cfg))))
            self.assertEqual(actual_manifest, expected_manifest)

    def test_mattermost_persona_usernames_use_romanized_handles(self) -> None:
        self.assertEqual(cli.mattermost_persona_username(1), "iori")
        self.assertEqual(cli.mattermost_persona_username(2), "tsumugi")
        self.assertEqual(cli.mattermost_persona_username(3), "saku")

    def test_mattermost_persona_avatar_files_exist(self) -> None:
        self.assertEqual(cli.mattermost_persona_avatar_file(1).name, "iori.png")
        self.assertEqual(cli.mattermost_persona_avatar_file(2).name, "tsumugi.png")
        self.assertEqual(cli.mattermost_persona_avatar_file(3).name, "saku.png")
        self.assertTrue(cli.mattermost_persona_avatar_file(1).exists())
        self.assertTrue(cli.mattermost_persona_avatar_file(2).exists())
        self.assertTrue(cli.mattermost_persona_avatar_file(3).exists())


if __name__ == "__main__":
    unittest.main()
