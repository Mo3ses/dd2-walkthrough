#!/usr/bin/env python3
"""Fetch quest pages from Fextralife, Fandom, IGN into /tmp/xsrc/.

Usage:
    python3 scripts/fetch_sources.py --quest-num 45
    python3 scripts/fetch_sources.py --all
    python3 scripts/fetch_sources.py --quest "Beren's Final Lesson"

Output: /tmp/xsrc/{src}_{NN}.html where NN is the zero-padded quest number
from the MD filename. `--quest` saves under `adhoc` (no number).

Exit codes:
    0  all 3 sources fetched successfully for every target
    1  at least one target is partial (1-2 of 3 sources)
    2  all targets have zero sources (network broken / wrong URLs)

URL patterns (verified 2026-07-08):

    Fextralife  https://dragonsdogma2.wiki.fextralife.com/<Title+With+Plusses>
                Apostrophes stay raw ('). Prepositions lowercase: "to", "of".
                (NOT www.wiki.fextralife.com — that's the wrong subdomain now.)

    Fandom      https://dragonsdogma.fandom.com/wiki/<Title_With_Underscores>
                Apostrophes URL-encoded as %27. RATE-LIMITED: needs 1s sleep
                between requests + retry on 403. (The 402 reported in NEXT-STEPS
                was transient; Fandom itself is fine but throttles bots.)

    IGN         https://www.ign.com/wikis/dragons-dogma-2/<Title_With_Underscores>
                Apostrophes URL-encoded as %27. Some specific quest pages 404
                (URL structure changed post-launch); treat 404 as "no data".

Apostrophes are URL-encoded as %27 for IGN/Fandom; Fextralife accepts raw '.
Sequential per-quest: Fandom's rate limit makes parallelism unsafe.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUEST_ROOT = REPO_ROOT / "Quests"
CACHE = Path("/tmp/xsrc")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Prepositions to lowercase if not the first word.
PREPOSITIONS = {"a", "an", "the", "of", "in", "on", "at", "by",
                "for", "from", "and", "or", "to", "but", "as"}


def title_case(title: str) -> list[str]:
    """'Beren's Final Lesson' -> ['Beren's', 'Final', 'Lesson'] (preserve case).

    Lowercases prepositions except the first word.
    """
    words = title.split()
    out = []
    for i, w in enumerate(words):
        if i > 0 and w.lower() in PREPOSITIONS:
            out.append(w.lower())
        else:
            out.append(w)
    return out


def fextralife_slug(title: str) -> str:
    return "+".join(title_case(title))


def wiki_slug(title: str, base_sep: str) -> str:
    """Title_With_Underscores with %27 for apostrophe."""
    return base_sep.join(title_case(title)).replace("'", "%27")


SOURCES: list[tuple[str, str, callable]] = [
    # (src_key, base_url, slug_fn)
    ("fex", "https://dragonsdogma2.wiki.fextralife.com/", fextralife_slug),
    ("fan", "https://dragonsdogma.fandom.com/wiki/", lambda t: wiki_slug(t, "_")),
    ("ign", "https://www.ign.com/wikis/dragons-dogma-2/", lambda t: wiki_slug(t, "_")),
]

# Soft-404 / error page heuristic: <1KB body is almost never a real wiki page.
MIN_BODY_BYTES = 1000

# Fandom-specific: rate-limited, needs sleep + retry on 403.
FANDOM_SLEEP_SECONDS = 1.5
FANDOM_MAX_RETRIES = 3


def fetch_one(src: str, base: str, slug: str, num: str) -> tuple[str, int, int]:
    """curl one URL, save to cache, return (src, http_code, size_bytes)."""
    url = base + slug
    out = CACHE / f"{src}_{num}.html"
    code, size = 0, 0
    try:
        result = subprocess.run(
            ["curl", "-sL", "-A", UA,
             "-o", str(out),
             "-w", "%{http_code}|%{size_download}",
             "--max-time", "15", url],
            capture_output=True, text=True, timeout=20,
        )
        meta = result.stdout.strip()
        if "|" in meta:
            code_str, size_str = meta.rsplit("|", 1)
            code = int(code_str)
            size = int(size_str)
        if code != 200 or size < MIN_BODY_BYTES:
            out.unlink(missing_ok=True)
            code = code if code != 200 else 0
            size = 0
    except (subprocess.TimeoutExpired, ValueError):
        out.unlink(missing_ok=True)
    return src, code, size


def fetch_with_retry(src: str, base: str, slug: str, num: str) -> tuple[int, int]:
    """fetch_one with Fandom-style rate-limit handling. Returns (code, size)."""
    if src != "fan":
        _, code, size = fetch_one(src, base, slug, num)
        return code, size
    last_code, last_size = 0, 0
    for attempt in range(FANDOM_MAX_RETRIES):
        if attempt:
            time.sleep(FANDOM_SLEEP_SECONDS * attempt)  # backoff: 1.5s, 3s
        _, code, size = fetch_one(src, base, slug, num)
        last_code, last_size = code, size
        if code == 200:
            return code, size
        if code != 403:  # only 403 is "rate-limited, retry"; 404 = no such page
            return code, size
    return last_code, last_size


def collect_targets(args: argparse.Namespace) -> list[tuple[str, str]]:
    """Resolve CLI args into [(title, num), ...]."""
    if args.quest:
        return [(args.quest, "adhoc")]
    if args.quest_num:
        num = args.quest_num.zfill(2)
        for md in sorted(QUEST_ROOT.rglob(f"{num} - *.md")):
            if "/Stage " not in str(md) or md.name.endswith(".en.md"):
                continue
            text = md.read_text(encoding="utf-8")
            m = re.search(r"^quest:\s*(.+)$", text, re.MULTILINE)
            if m:
                return [(m.group(1).strip().strip("'\""), num)]
        print(f"No quest MD found for num={args.quest_num}", file=sys.stderr)
        sys.exit(2)
    out = []
    for md in sorted(QUEST_ROOT.rglob("*.md")):
        if "/Stage " not in str(md) or md.name.endswith(".en.md"):
            continue
        m = re.match(r"^(\d+)", md.name)
        if not m:
            continue
        num = m.group(1).zfill(2)
        text = md.read_text(encoding="utf-8")
        tm = re.search(r"^quest:\s*(.+)$", text, re.MULTILINE)
        if tm:
            out.append((tm.group(1).strip().strip("'\""), num))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--quest-num", help="Zero-padded number (e.g. 45)")
    g.add_argument("--all", action="store_true", help="All Stage quests")
    g.add_argument("--quest", help="Direct title (saved as num='adhoc')")
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    targets = collect_targets(args)
    if not targets:
        print("No targets.", file=sys.stderr)
        return 2

    print(f"Fetching {len(targets)} quest(s) × 3 sources → {CACHE}\n")

    full = partial = zero = 0
    for title, num in targets:
        results: dict[str, tuple[int, int]] = {}
        # Fextralife → IGN → Fandom (Fandom last because rate-limited).
        for src, base, slug_fn in SOURCES:
            results[src] = fetch_with_retry(src, base, slug_fn(title), num)
            if src == "fan":
                time.sleep(FANDOM_SLEEP_SECONDS)
        ok = sum(1 for c, _ in results.values() if c == 200)
        bits = "  ".join(f"{s}={c}" for s, (c, _) in results.items())
        print(f"#{num} {title[:40]:<40}  {bits}")
        if ok == 3:
            full += 1
        elif ok == 0:
            zero += 1
        else:
            partial += 1

    print(f"\nSummary: {full} full / {partial} partial / {zero} zero "
          f"of {len(targets)} target(s)")
    if zero == len(targets):
        return 2
    return 0 if full == len(targets) else 1


if __name__ == "__main__":
    sys.exit(main())