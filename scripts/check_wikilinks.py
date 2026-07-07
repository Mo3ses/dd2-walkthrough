#!/usr/bin/env python3
"""Validate [[wiki-links]] in the Quests/ vault.

Scans every *.md under Quests/ (PT and EN both — they share links),
extracts [[...]] references, and verifies each target resolves to an
existing MD file on disk. Reports broken links grouped by source file.

Exit code 0 if no broken links, 1 otherwise.

Mirrors the regex + resolution logic of scripts/build.py (WIKILINK_RE
line 50, resolve_wikilink line 615) but stays standalone — no import of
build.py, since that module pulls in argparse/datetime/etc.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUEST_ROOT = REPO_ROOT / "Quests"
LOCATIONS = QUEST_ROOT / "Locations"

# Same regex as build.py:50.
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def slugify_for_lookup(text: str) -> str:
    """Same slug rule as build.py:slugify (line 663) — strips non-alnum to dashes."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def build_slug_index() -> dict[str, Path]:
    """Map slug → on-disk MD path for every Quests/**/*.md.

    Lets the validator catch bare wikilinks like [[Gaoled Awakening]]
    which build.py resolves via slug-based lookup (the actual file is
    `01 - Gaoled Awakening.md`).
    """
    index: dict[str, Path] = {}
    for md in QUEST_ROOT.rglob("*.md"):
        s = slugify_for_lookup(md.stem)
        # First-wins; if two files slug-collide, keep the first scanned.
        index.setdefault(s, md)
    return index


def target_to_candidates(target: str) -> list[Path]:
    """Return disk paths to check for a given [[target]].

    Mirrors build.py:resolve_wikilink but in reverse — produces the
    possible on-disk source locations instead of the HTML URL.
    """
    t = target.strip()
    if "|" in t:
        t = t.split("|", 1)[0].strip()
    if t.endswith(".md"):
        t = t[:-3].strip()
    fname = t.split("/")[-1]

    norm = t.lower().replace(" ", "").replace("-", "")
    if norm in {"stage1", "stage2", "stage3", "stage4", "stage5"}:
        return [QUEST_ROOT / f"{t}.md"]

    candidates: list[Path] = []

    if t.startswith("Main Quests/"):
        for stage in (1, 2, 3, 4):
            candidates.append(QUEST_ROOT / f"Stage {stage}" / "Main Quests" / f"{fname}.md")
        return candidates

    if t.startswith("Side Quests/"):
        for stage in (1, 2, 3, 4):
            candidates.append(QUEST_ROOT / f"Stage {stage}" / "Side Quests" / f"{fname}.md")
        return candidates

    if t.startswith("Locations/"):
        return [LOCATIONS / f"{fname}.md"]

    # Fallback: bare filename — try all known roots first.
    for stage in (1, 2, 3, 4):
        candidates.append(QUEST_ROOT / f"Stage {stage}" / "Main Quests" / f"{fname}.md")
        candidates.append(QUEST_ROOT / f"Stage {stage}" / "Side Quests" / f"{fname}.md")
    candidates.append(LOCATIONS / f"{fname}.md")
    candidates.append(QUEST_ROOT / f"{fname}.md")
    # Final fallback: slug-based lookup (matches build.py:resolve_wikilink
    # behavior for bare quest refs without "Main Quests/" / "Side Quests/" prefix).
    candidates.append(_SLUG_INDEX.get(slugify_for_lookup(fname), _MISSING))
    return candidates


# Populated at module load — used only as the final fallback candidate.
_MISSING = Path("/nonexistent")
_SLUG_INDEX: dict[str, Path] = build_slug_index()


def scan_vault() -> dict[str, list[tuple[str, str]]]:
    """Return {source_md_path: [(target, error)]} for broken links.

    Empty dict = no broken links.
    """
    broken: dict[str, list[tuple[str, str]]] = {}
    total_links = 0
    files_scanned = 0

    for md in sorted(QUEST_ROOT.rglob("*.md")):
        files_scanned += 1
        text = md.read_text(encoding="utf-8")
        for m in WIKILINK_RE.finditer(text):
            total_links += 1
            target = m.group(1)
            for cand in target_to_candidates(target):
                if cand.exists():
                    break
            else:
                broken.setdefault(str(md.relative_to(REPO_ROOT)), []).append(
                    (target, "no matching .md on disk")
                )

    if not broken:
        print(f"OK: {total_links} links scanned across {files_scanned} files")
        return broken

    print(f"BROKEN: {sum(len(v) for v in broken.values())} broken links across {len(broken)} files (of {files_scanned} total)")
    for src in sorted(broken):
        print(f"\n  {src}")
        for target, err in broken[src]:
            print(f"    [[{target}]]  → {err}")
    return broken


def main() -> int:
    broken = scan_vault()
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())