#!/usr/bin/env python3
"""Copia subagent Cursor da ~/.cursor/agents/ in .cursor/agents/ del progetto.

Sorgenti (unione):
- nomi in .cursor/agents-sync.manifest.json → agents[]
- se include_marked_global: file globali con sync_to_project: true nel frontmatter

Uso:
  python3 scripts/sync_cursor_agents.py
  python3 scripts/sync_cursor_agents.py --dry-run
  python3 scripts/sync_cursor_agents.py --force
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SYNC_FLAG_RE = re.compile(r"^sync_to_project:\s*true\s*$", re.MULTILINE)
NAME_RE = re.compile(r"^name:\s*([a-z0-9-]+)\s*$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def global_agents_dir() -> Path:
    return Path.home() / ".cursor" / "agents"


def read_manifest(root: Path) -> dict:
    path = root / ".cursor" / "agents-sync.manifest.json"
    if not path.is_file():
        return {"include_marked_global": False, "agents": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("agents"), list):
        raise SystemExit(f"Campo 'agents' non valido in {path}")
    return data


def agent_name_from_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = NAME_RE.search(text)
    if match:
        return match.group(1)
    return path.stem


def is_marked_global(path: Path) -> bool:
    return bool(SYNC_FLAG_RE.search(path.read_text(encoding="utf-8")))


def strip_sync_flag(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return text
    body = text[match.end() :]
    frontmatter = match.group(1)
    lines = [
        line
        for line in frontmatter.splitlines()
        if not re.match(r"^sync_to_project:\s*true\s*$", line)
    ]
    cleaned = "---\n" + "\n".join(lines) + "\n---\n" + body
    return cleaned


def collect_agent_names(manifest: dict, global_dir: Path) -> list[str]:
    names: set[str] = set(manifest.get("agents") or [])
    if manifest.get("include_marked_global") and global_dir.is_dir():
        for path in sorted(global_dir.glob("*.md")):
            if is_marked_global(path):
                names.add(agent_name_from_file(path))
    return sorted(names)


def resolve_source(global_dir: Path, name: str) -> Path | None:
    direct = global_dir / f"{name}.md"
    if direct.is_file():
        return direct
    if not global_dir.is_dir():
        return None
    for path in global_dir.glob("*.md"):
        if agent_name_from_file(path) == name:
            return path
    return None


def sync_agents(*, dry_run: bool, force: bool) -> int:
    root = repo_root()
    dest_dir = root / ".cursor" / "agents"
    global_dir = global_agents_dir()
    manifest = read_manifest(root)
    names = collect_agent_names(manifest, global_dir)

    if not names:
        print("Nessun subagent da sincronizzare (manifest vuoto e nessun sync_to_project globale).")
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0
    missing = 0

    for name in names:
        source = resolve_source(global_dir, name)
        if source is None:
            print(f"SKIP mancante in {global_dir}: {name}")
            missing += 1
            continue

        dest = dest_dir / f"{name}.md"
        if dest.exists() and not force and dest.stat().st_mtime >= source.stat().st_mtime:
            print(f"SKIP aggiornato: {name}")
            skipped += 1
            continue

        content = strip_sync_flag(source.read_text(encoding="utf-8"))
        if dry_run:
            print(f"DRY-RUN copia: {source} -> {dest}")
        else:
            dest.write_text(content, encoding="utf-8")
            print(f"COPIA: {name}")
        copied += 1

    print(f"Fatto: {copied} copiati, {skipped} saltati, {missing} mancanti.")
    return 1 if missing else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync subagent Cursor globali → progetto")
    parser.add_argument("--dry-run", action="store_true", help="Mostra azioni senza scrivere")
    parser.add_argument("--force", action="store_true", help="Sovrascrivi anche se destinazione più recente")
    args = parser.parse_args()
    raise SystemExit(sync_agents(dry_run=args.dry_run, force=args.force))


if __name__ == "__main__":
    main()
