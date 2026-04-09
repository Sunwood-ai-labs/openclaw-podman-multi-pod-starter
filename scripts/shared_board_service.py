#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


MANAGED_MARKER = "<!-- Managed by openclaw-podman-starter: shared board scaffold -->"
DEFAULT_AUTHOR = "Visitor"
DEFAULT_AUTHOR_SLUG = "visitor"
APP_TEMPLATE_FILE = Path(__file__).with_name("shared_board_app.html")

THREAD_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS threads (
    thread_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

POST_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS posts (
    message_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    author_slug TEXT NOT NULL,
    author_label TEXT NOT NULL,
    body_markdown TEXT NOT NULL,
    preview_text TEXT NOT NULL,
    source_path TEXT NOT NULL UNIQUE,
    source_mtime_ns INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_posts_thread_sort
ON posts(thread_id, created_at, sort_order, message_id);
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the shared board as a minimal SQLite-backed web app.")
    parser.add_argument("--board-root", type=Path, required=True)
    parser.add_argument("--db-path", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=18888)
    parser.add_argument("--template", type=Path, default=APP_TEMPLATE_FILE)
    return parser.parse_args()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(timespec="seconds")


def timestamp_slug() -> str:
    return utc_now().strftime("%Y%m%d-%H%M%SZ")


def slugify_thread_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or "thread"


def sanitize_author(value: str | None) -> str:
    candidate = (value or "").replace("\r", " ").replace("\n", " ").strip()
    if not candidate:
        return DEFAULT_AUTHOR
    return candidate[:48]


def detect_kind(path: Path) -> str:
    if path.name == "topic.md":
        return "topic"
    if path.name == "summary.md":
        return "summary"
    if path.name.startswith("reply-"):
        return "reply"
    if path.name.startswith("turn-"):
        return "turn"
    return "note"


def default_author_label(slug: str) -> str:
    labels = {
        "aster": "Aster",
        "lyra": "Lyra",
        "noctis": "Noctis",
        "system": "System",
        "visitor": DEFAULT_AUTHOR,
        "human": DEFAULT_AUTHOR,
    }
    if slug in labels:
        return labels[slug]
    return slug.replace("-", " ").title()


def detect_author_slug(path: Path) -> str:
    if path.name in {"topic.md", "summary.md"}:
        return "system"
    for prefix in ("reply-", "turn-"):
        if path.name.startswith(prefix):
            remainder = path.stem[len(prefix) :]
            first = remainder.split("-", 1)[0].strip().lower()
            if first:
                return first
    return "system"


def extract_metadata_value(text: str, key: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1).strip() or None


def extract_author_label(path: Path, text: str) -> tuple[str, str]:
    slug = detect_author_slug(path)
    for key in ("Started by", "Responder", "Author"):
        value = extract_metadata_value(text, key)
        if value:
            return slug, sanitize_author(value)
    return slug, default_author_label(slug)


def extract_thread_title(thread_id: str, topic_text: str | None) -> str:
    if topic_text:
        for raw in topic_text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                return line.lstrip("# ").strip() or thread_id.replace("-", " ").title()
            return line[:120]
    return thread_id.replace("-", " ").title()


def strip_metadata_lines(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    kept: list[str] = []
    skipped_heading = False
    for raw in lines:
        line = raw.strip()
        if not skipped_heading and line.startswith("#"):
            skipped_heading = True
            continue
        if re.match(r"^(Started by|Responder|Author):\s*.+$", line, flags=re.IGNORECASE):
            continue
        kept.append(raw)
    return "\n".join(kept).strip()


def preview_text(text: str) -> str:
    body = strip_metadata_lines(text)
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        cleaned = re.sub(r"^[#>\-\*\d\.\)\s]+", "", line).strip()
        if cleaned:
            return cleaned[:160]
    fallback = text.strip().splitlines()
    return fallback[0][:160] if fallback else ""


def topic_markdown(title: str, author: str, body: str) -> str:
    return (
        f"# {title.strip()}\n\n"
        f"Started by: {sanitize_author(author)}\n\n"
        f"{body.strip()}\n"
    )


def reply_markdown(author: str, body: str) -> str:
    return (
        f"Responder: {sanitize_author(author)}\n\n"
        f"{body.strip()}\n"
    )


class BoardRepository:
    def __init__(self, board_root: Path, db_path: Path) -> None:
        self.board_root = board_root.resolve()
        self.db_path = db_path.resolve()
        self._lock = threading.Lock()

    def initialize(self) -> None:
        (self.board_root / "threads").mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            with conn:
                conn.executescript(THREAD_TABLE_SQL)
                conn.executescript(POST_TABLE_SQL)
                conn.executescript(INDEX_SQL)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _sync_locked(self) -> str:
        threads_root = self.board_root / "threads"
        threads_root.mkdir(parents=True, exist_ok=True)
        seen_thread_ids: set[str] = set()
        seen_source_paths: set[str] = set()

        with closing(self._connect()) as conn:
            with conn:
                for thread_dir in sorted((path for path in threads_root.iterdir() if path.is_dir()), key=lambda item: item.name):
                    files = sorted((path for path in thread_dir.iterdir() if path.is_file() and path.suffix.lower() == ".md"), key=lambda item: (item.stat().st_mtime_ns, item.name))
                    if not files:
                        continue

                    seen_thread_ids.add(thread_dir.name)
                    topic_text = None
                    created_at = iso_from_timestamp(min(path.stat().st_mtime for path in files))
                    updated_at = iso_from_timestamp(max(path.stat().st_mtime for path in files))
                    for path in files:
                        if path.name == "topic.md":
                            topic_text = path.read_text(encoding="utf-8")
                            break
                    title = extract_thread_title(thread_dir.name, topic_text)

                    conn.execute(
                        """
                        INSERT INTO threads(thread_id, title, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(thread_id) DO UPDATE SET
                            title = excluded.title,
                            created_at = excluded.created_at,
                            updated_at = excluded.updated_at
                        """,
                        (thread_dir.name, title, created_at, updated_at),
                    )

                    for sort_order, path in enumerate(files):
                        text = path.read_text(encoding="utf-8")
                        author_slug, author_label = extract_author_label(path, text)
                        source_path = path.relative_to(self.board_root).as_posix()
                        seen_source_paths.add(source_path)
                        conn.execute(
                            """
                            INSERT INTO posts(
                                message_id,
                                thread_id,
                                kind,
                                author_slug,
                                author_label,
                                body_markdown,
                                preview_text,
                                source_path,
                                source_mtime_ns,
                                created_at,
                                sort_order
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(message_id) DO UPDATE SET
                                kind = excluded.kind,
                                author_slug = excluded.author_slug,
                                author_label = excluded.author_label,
                                body_markdown = excluded.body_markdown,
                                preview_text = excluded.preview_text,
                                source_path = excluded.source_path,
                                source_mtime_ns = excluded.source_mtime_ns,
                                created_at = excluded.created_at,
                                sort_order = excluded.sort_order
                            """,
                            (
                                source_path,
                                thread_dir.name,
                                detect_kind(path),
                                author_slug,
                                author_label,
                                text,
                                preview_text(text),
                                source_path,
                                path.stat().st_mtime_ns,
                                iso_from_timestamp(path.stat().st_mtime),
                                sort_order,
                            ),
                        )

                if seen_source_paths:
                    placeholders = ",".join("?" for _ in seen_source_paths)
                    conn.execute(f"DELETE FROM posts WHERE source_path NOT IN ({placeholders})", tuple(sorted(seen_source_paths)))
                else:
                    conn.execute("DELETE FROM posts")

                if seen_thread_ids:
                    placeholders = ",".join("?" for _ in seen_thread_ids)
                    conn.execute(f"DELETE FROM threads WHERE thread_id NOT IN ({placeholders})", tuple(sorted(seen_thread_ids)))
                else:
                    conn.execute("DELETE FROM threads")

        return utc_now().isoformat(timespec="seconds")

    def sync(self) -> str:
        with self._lock:
            return self._sync_locked()

    def list_threads(self) -> dict[str, object]:
        synced_at = self.sync()
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT
                    t.thread_id,
                    t.title,
                    t.created_at,
                    t.updated_at,
                    COUNT(p.message_id) AS post_count,
                    COALESCE(
                        (
                            SELECT p2.preview_text
                            FROM posts AS p2
                            WHERE p2.thread_id = t.thread_id
                            ORDER BY p2.created_at DESC, p2.sort_order DESC, p2.message_id DESC
                            LIMIT 1
                        ),
                        ''
                    ) AS preview
                FROM threads AS t
                LEFT JOIN posts AS p ON p.thread_id = t.thread_id
                GROUP BY t.thread_id
                ORDER BY t.updated_at DESC, t.thread_id DESC
                """
            ).fetchall()
        return {
            "syncedAt": synced_at,
            "threads": [
                {
                    "threadId": row["thread_id"],
                    "title": row["title"],
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                    "postCount": row["post_count"],
                    "preview": row["preview"],
                }
                for row in rows
            ],
        }

    def get_thread(self, thread_id: str) -> dict[str, object]:
        synced_at = self.sync()
        with closing(self._connect()) as conn:
            thread = conn.execute(
                "SELECT thread_id, title, created_at, updated_at FROM threads WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            if thread is None:
                raise KeyError(thread_id)

            posts = conn.execute(
                """
                SELECT
                    message_id,
                    kind,
                    author_slug,
                    author_label,
                    body_markdown,
                    preview_text,
                    source_path,
                    created_at
                FROM posts
                WHERE thread_id = ?
                ORDER BY created_at ASC, sort_order ASC, message_id ASC
                """,
                (thread_id,),
            ).fetchall()

        return {
            "syncedAt": synced_at,
            "thread": {
                "threadId": thread["thread_id"],
                "title": thread["title"],
                "createdAt": thread["created_at"],
                "updatedAt": thread["updated_at"],
                "posts": [
                    {
                        "messageId": row["message_id"],
                        "kind": row["kind"],
                        "authorSlug": row["author_slug"],
                        "authorLabel": row["author_label"],
                        "bodyMarkdown": row["body_markdown"],
                        "preview": row["preview_text"],
                        "sourcePath": row["source_path"],
                        "createdAt": row["created_at"],
                    }
                    for row in posts
                ],
            },
        }

    def create_thread(self, title: str, body: str, author: str) -> dict[str, object]:
        normalized_title = title.strip()
        normalized_body = body.strip()
        if not normalized_title:
            raise ValueError("title is required")
        if not normalized_body:
            raise ValueError("body is required")

        base_thread_id = slugify_thread_id(normalized_title)
        thread_id = base_thread_id
        thread_dir = self.board_root / "threads" / thread_id
        if thread_dir.exists():
            thread_id = f"{base_thread_id}-{timestamp_slug().lower()}"
            thread_dir = self.board_root / "threads" / thread_id

        thread_dir.mkdir(parents=True, exist_ok=True)
        topic_path = thread_dir / "topic.md"
        topic_path.write_text(topic_markdown(normalized_title, author, normalized_body), encoding="utf-8")
        return self.get_thread(thread_id)

    def create_post(self, thread_id: str, body: str, author: str) -> dict[str, object]:
        normalized_body = body.strip()
        if not normalized_body:
            raise ValueError("body is required")

        thread_dir = self.board_root / "threads" / thread_id
        if not thread_dir.exists():
            raise KeyError(thread_id)

        stamp = timestamp_slug()
        path = thread_dir / f"reply-{DEFAULT_AUTHOR_SLUG}-{stamp}.md"
        suffix = 1
        while path.exists():
            path = thread_dir / f"reply-{DEFAULT_AUTHOR_SLUG}-{stamp}-{suffix}.md"
            suffix += 1
        path.write_text(reply_markdown(author, normalized_body), encoding="utf-8")
        return self.get_thread(thread_id)

    def health(self) -> dict[str, object]:
        with closing(self._connect()) as conn:
            thread_count = conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0]
            post_count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        return {
            "ok": True,
            "syncedAt": utc_now().isoformat(timespec="seconds"),
            "boardRoot": str(self.board_root),
            "dbPath": str(self.db_path),
            "threadCount": thread_count,
            "postCount": post_count,
        }


class SharedBoardHandler(BaseHTTPRequestHandler):
    repo: BoardRepository
    template_path: Path

    server_version = "SharedBoard/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            if path in {"/", "/index.html"}:
                self._send_html(self._app_html())
                return
            if path == "/healthz":
                self._send_json(HTTPStatus.OK, self.repo.health())
                return
            if path == "/api/threads":
                self._send_json(HTTPStatus.OK, self.repo.list_threads())
                return
            if path.startswith("/api/threads/"):
                thread_id = unquote(path.removeprefix("/api/threads/")).strip("/")
                if not thread_id:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "thread id is required"})
                    return
                self._send_json(HTTPStatus.OK, self.repo.get_thread(thread_id))
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except KeyError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "thread not found"})
        except Exception as exc:  # pragma: no cover - runtime diagnostic path
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        try:
            payload = self._read_json()
            if path == "/api/threads":
                result = self.repo.create_thread(
                    title=str(payload.get("title", "")),
                    body=str(payload.get("body", "")),
                    author=sanitize_author(str(payload.get("author", DEFAULT_AUTHOR))),
                )
                self._send_json(HTTPStatus.CREATED, result)
                return
            if path.startswith("/api/threads/") and path.endswith("/posts"):
                thread_id = unquote(path.removeprefix("/api/threads/").removesuffix("/posts")).strip("/")
                if not thread_id:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "thread id is required"})
                    return
                result = self.repo.create_post(
                    thread_id=thread_id,
                    body=str(payload.get("body", "")),
                    author=sanitize_author(str(payload.get("author", DEFAULT_AUTHOR))),
                )
                self._send_json(HTTPStatus.CREATED, result)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except KeyError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "thread not found"})
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - runtime diagnostic path
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def _app_html(self) -> str:
        if self.template_path.exists():
            return self.template_path.read_text(encoding="utf-8")
        return "<!doctype html><title>Shared Board</title><p>Missing shared_board_app.html</p>"

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("invalid JSON body") from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def _send_html(self, html_text: str) -> None:
        body = html_text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_server(repo: BoardRepository, template_path: Path, host: str, port: int) -> ThreadingHTTPServer:
    handler = type(
        "ConfiguredSharedBoardHandler",
        (SharedBoardHandler,),
        {"repo": repo, "template_path": template_path},
    )
    return ThreadingHTTPServer((host, port), handler)


def main() -> int:
    args = parse_args()
    repo = BoardRepository(args.board_root, args.db_path)
    repo.initialize()
    repo.sync()
    server = build_server(repo, args.template, args.host, args.port)
    print(f"Shared board listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - manual shutdown path
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
