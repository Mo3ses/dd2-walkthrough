#!/usr/bin/env python3
"""Cross-source fact-comparison for quests marked sources_verified: [fandom, fextralife, ign].

For each 3-source Stage 2 quest, reads the cached HTML for IGN + Fandom at
/tmp/xsrc/ and the Fextralife data embedded in the MD frontmatter +
`## Recompensas`, extracts the key fields (quest_giver, XP, G, headline item),
and reports consensus vs. conflict.

Smoke test philosophy: this script flags *material* disagreements (different
quest_giver names, >20% XP divergence). It does NOT verify that each value
appears verbatim — the regexes are intentionally tolerant because the HTMLs
are inconsistent (IGN uses commas, Fandom uses periods, etc.).

Exit code 0 = no conflicts, 1 = at least one conflict.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUEST_ROOT = REPO_ROOT / "Quests"
HTML_CACHE = Path("/tmp/xsrc")


@dataclass
class Fact:
    """One field extracted from one source. None = not found."""
    quest_giver: str | None = None
    xp: int | None = None
    gold: int | None = None
    raw_text: str = field(default="", repr=False)


@dataclass
class QuestFacts:
    name: str
    md_path: Path
    fextralife: Fact = field(default_factory=Fact)
    ign: Fact = field(default_factory=Fact)
    fandom: Fact = field(default_factory=Fact)

    def conflicts(self) -> list[str]:
        """Return list of `field: source_a=X vs source_b=Y` strings."""
        out: list[str] = []
        for field_name in ("quest_giver", "xp", "gold"):
            values = {
                src: getattr(self, src).__dict__[field_name]
                for src in ("fextralife", "ign", "fandom")
                if getattr(self, src).__dict__[field_name] is not None
            }
            if len(set(map(str, values.values()))) > 1:
                pretty = ", ".join(f"{k}={v}" for k, v in values.items())
                out.append(f"{field_name}: {pretty}")
        return out


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_html_text(path: Path) -> str:
    """Read an HTML file, strip tags, normalize whitespace."""
    if not path.exists():
        return ""
    html = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\s+", " ", text)
    return text


def load_md_facts(path: Path) -> Fact:
    """Pull Fextralife data out of the PT quest MD frontmatter + Recompensas.

    PT is canonical for the vault, but if PT is missing we fall back to EN.
    """
    if not path.exists():
        return Fact()
    text = path.read_text(encoding="utf-8")

    # Quest giver — frontmatter `quest_giver:` line.
    giver = None
    m = re.search(r"^quest_giver:\s*(.+)$", text, re.MULTILINE)
    if m:
        raw = m.group(1).strip()
        # Strip surrounding quotes if any.
        giver = raw.strip("'\"")

    # XP — look for `N.NNN XP` or `N,NNN XP` or `N XP` in the Recompensas section.
    xp = None
    recompensas_match = re.search(
        r"##\s+(?:Recompensas|Rewards)\s*\n(.*?)(?=\n##\s|\Z)",
        text, re.DOTALL | re.IGNORECASE,
    )
    section = recompensas_match.group(1) if recompensas_match else text
    xp_match = re.search(r"([\d.,]+)\s*XP", section)
    if xp_match:
        xp = _parse_int(xp_match.group(1))

    # Gold — `N.NNN G` / `N,NNN G` / `N Gold` / `N G`.
    gold = None
    g_match = re.search(r"([\d.,]+)\s*(?:G\b|Gold)", section)
    if g_match:
        gold = _parse_int(g_match.group(1))

    return Fact(quest_giver=giver, xp=xp, gold=gold, raw_text=section[:500])


def _parse_int(s: str) -> int | None:
    """Parse '1.600' / '1,600' / '5000' → int. Returns None if not numeric."""
    s = s.replace(".", "").replace(",", "")
    try:
        return int(s)
    except ValueError:
        return None


def load_html_facts(path: Path) -> Fact:
    """Best-effort extraction from a cached HTML."""
    text = load_html_text(path)
    if not text:
        return Fact()

    giver = None
    # Fandom's structured template is `Quest Giver <Name> Quest Location <Loc>
    # Prerequisite <Pre> Reward <Reward>` — grab only the first Name token,
    # stopping at the next capitalized label or punctuation.
    giver_match = re.search(
        r"(?:Quest\s+Giver|Started\s+by|Given\s+by|Giver)\s+"
        r"([A-Z][a-zA-Z'\-]+)"
        r"(?=\s+(?:Quest|Started|Prerequisite|Next|Reward|Type|is\s+a)|[,.;]|\Z)",
        text,
    )
    if giver_match:
        giver = giver_match.group(1).strip()

    xp = None
    xp_match = re.search(r"([\d.,]+)\s*(?:XP|Experience)", text)
    if xp_match:
        xp = _parse_int(xp_match.group(1))

    gold = None
    # Only count G from quest-completion reward text. IGN walkthroughs list
    # multiple sub-rewards ("another 3000 gold from the soldiers"); we want
    # the *main* completion reward, which appears as either:
    #   - Fandom structured label: "Reward <N> Gold/XP"
    #   - IGN completion line: "reward, <N> gold, <N> xp" near "completing"
    # Vendor prices ("buy the book for 5,000 G") and sub-rewards are skipped.
    g_match = re.search(
        r"\bReward\s+(\d[\d.,]+)\s*(?:Gold|G\b)",
        text, re.IGNORECASE,
    )
    if not g_match:
        g_match = re.search(
            r"reward,\s*(\d[\d.,]+)\s*(?:Gold|G\b)[^.]{0,80}?(?:completing|quest)",
            text, re.IGNORECASE,
        )
    if g_match:
        gold = _parse_int(g_match.group(1))

    return Fact(quest_giver=giver, xp=xp, gold=gold, raw_text=text[:500])


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def find_three_source_quests() -> list[Path]:
    """Return PT quest MDs that list fandom + fextralife + ign under
    sources_verified (single-line or YAML multi-line list).

    `needs_verification` is intentionally NOT a gate here — Stage 1 MDs
    often omit it because the data was trusted on first write. This script
    checks the cross-source claim regardless of that flag.
    """
    out: list[Path] = []
    for md in sorted(QUEST_ROOT.rglob("*.md")):
        # Skip EN siblings — they're translations of the same quest; the
        # PT MD is canonical for sourcing.
        if "/Stage " not in str(md) or md.name.endswith(".en.md"):
            continue
        text = md.read_text(encoding="utf-8")
        # Capture everything between `sources_verified:` and the next YAML key
        # (a non-indented line) so multi-line YAML lists parse correctly.
        m = re.search(
            r"^sources_verified:\s*\n((?:\s+-\s+\S+\s*\n)+)",
            text, re.MULTILINE,
        )
        if not m:
            continue
        block = m.group(1)
        if all(s in block for s in ("fandom", "fextralife", "ign")):
            out.append(md)
    return out


def num_from_filename(path: Path) -> str | None:
    m = re.match(r"^(\d+)", path.name)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    quests = find_three_source_quests()
    if not quests:
        print("No 3-source quests found. Run a frontmatter audit first.")
        return 0

    print(f"Cross-source check for {len(quests)} 3-source quests\n")
    print(f"{'#':>3}  {'Quest':<40}  {'Conflicts'}")
    print("-" * 80)

    all_conflicts: list[tuple[str, list[str]]] = []
    coverage = {"3/3": 0, "2/3": 0, "1/3": 0, "0/3": 0}
    for md in quests:
        q = QuestFacts(name=md.stem, md_path=md)
        q.fextralife = load_md_facts(md)
        num = num_from_filename(md)
        if num:
            q.ign = load_html_facts(HTML_CACHE / f"ign_{num}.html")
            q.fandom = load_html_facts(HTML_CACHE / f"fan_{num}.html")
        conflicts = q.conflicts()
        # Sources with at least one non-None field = "has data".
        n_src = sum(
            1 for s in (q.fextralife, q.ign, q.fandom)
            if any(getattr(s, f) is not None for f in ("quest_giver", "xp", "gold"))
        )
        coverage[f"{n_src}/3"] = coverage.get(f"{n_src}/3", 0) + 1
        flag = "OK" if not conflicts else "CONFLICT"
        print(f"[{flag}] {num or '?':>2}  {md.stem:<40}  {len(conflicts)} conflict(s)  ({n_src}/3 sources)")
        for c in conflicts:
            print(f"           - {c}")
        if conflicts:
            all_conflicts.append((md.stem, conflicts))

    print(f"\nSummary: {len(all_conflicts)} of {len(quests)} quests have cross-source conflicts.")
    cov = ", ".join(f"{k}={v}" for k, v in coverage.items() if v)
    print(f"Source coverage: {cov}")
    return 1 if all_conflicts else 0


if __name__ == "__main__":
    sys.exit(main())