#!/usr/bin/env python3
"""DD2 Walkthrough — self-contained HTML build.

Reads the vault's plain Markdown files under Quests/ and emits a small
set of self-contained HTML pages under dist/. No npm, no Quartz, no
plugin ecosystem. Just Python 3 stdlib.

What gets generated:
  dist/index.html          — homepage (links into each stage)
  dist/stage-N.html        — cheat sheet for stage N
                             (anchor TOC + per-location sections +
                             inline JS for localStorage persistence)

Every output file is fully self-contained:
  - HTML structure
  - CSS in a <style> block (the same theme on every page)
  - JS in a <script> block (the localStorage tracker; a no-op on
    pages without checkboxes)

You can open dist/stage-1.html directly in a browser with no server
and the tracker still works.

Usage:
    python3 scripts/build.py [--repo-root PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Markdown parsing (intentionally minimal — only what the vault uses)
# ---------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\s*\n(?P<body>.*?)\n---\s*$", re.DOTALL | re.MULTILINE)
KV_RE = re.compile(r"^([a-zA-Z_][\w-]*)\s*:\s*(.*?)\s*$")
LIST_ITEM_RE = re.compile(r"^(?P<indent>\s*)- (?P<body>.+?)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(?P<text>.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\[(?P<state>[ xX])\]\s+(?P<text>.+?)\s*$")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
CALLOUT_RE = re.compile(r"^>\s*\[!(?P<kind>[a-z]+)\]\s*(?P<title>[^*]*?)\*\s*$", re.IGNORECASE)
HTML_INLINE_RE = re.compile(r"<(input|li|ul|ol|a)\b", re.IGNORECASE)

# Tries to match location paths the user has used. New quests should
# stick to one of these canonical location strings.
LOCATION_ORDER: list[tuple[str, str]] = [
    ("Excavation Site", "🪨"),
    ("Ultramarine Waterfall", "💧"),
    ("Borderwatch Outpost", "🛡️"),
    ("Melve", "🏘️"),
    ("Melve → Vernworth", "🛤️"),
]

# Hard-coded overrides so the road-quest (09) groups under "Melve → Vernworth"
# even though its frontmatter says Melve.
QUEST_OVERRIDES: dict[str, tuple[str, str, str]] = {
    "01 - Gaoled Awakening.md":         ("Excavation Site",       "main", "01"),
    "02 - Tale's Beginning.md":         ("Ultramarine Waterfall", "main", "02"),
    "08 - In Dragon's Wake.md":         ("Borderwatch Outpost",   "main", "08"),
    "03 - Ordeal's of a New Recruit.md": ("Borderwatch Outpost",  "side", "03"),
    "04 - The Provisioner's Plight.md": ("Borderwatch Outpost",   "side", "04"),
    "05 - Medicament Predicament.md":   ("Melve",                 "side", "05"),
    "06 - Brother's Brave and Timid.md": ("Melve",                "side", "06"),
    "07 - Nesting Troubles.md":         ("Melve",                 "side", "07"),
    "09 - One-Eyed Interloper.md":      ("Melve → Vernworth",     "side", "09"),
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Objective:
    text: str
    done: bool


@dataclass
class Quest:
    filename: str
    title: str
    location: str
    quest_type: str   # "main" | "side"
    quest_num: str
    objectives: list[Objective] = field(default_factory=list)
    summary: str = ""
    walkthrough: list[str] = field(default_factory=list)
    rewards: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    raw: str = ""

    @property
    def track_prefix(self) -> str:
        return f"s1-{self.quest_type}-{self.quest_num}"

    @property
    def slug(self) -> str:
        s = self.filename.lower()
        s = re.sub(r"\.md$", "", s)
        s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
        return s

    @property
    def url(self) -> str:
        sub = "main-quests" if self.quest_type == "main" else "side-quests"
        return f"quests/stage-1/{sub}/{self.slug}.html"

    @property
    def status(self) -> str:
        if not self.objectives:
            return "Sem objetivos"
        done = sum(1 for o in self.objectives if o.done)
        total = len(self.objectives)
        if done == total:
            return f"✅ {done}/{total}"
        if done == 0:
            return f"⬜ 0/{total}"
        return f"⏳ {done}/{total}"


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Returns (frontmatter_dict, body_without_frontmatter)."""
    m = FRONTMATTER_RE.search(text)
    if not m:
        return {}, text
    out: dict[str, str] = {}
    for line in m.group("body").splitlines():
        kv = KV_RE.match(line)
        if kv:
            out[kv.group(1).strip()] = kv.group(2).strip().strip('"').strip("'")
    return out, text[m.end():]


def strip_callout_marker(line: str) -> tuple[str | None, str]:
    """If line is `> [!info] Title *`, returns ('info', 'Title').
    Otherwise returns (None, line)."""
    m = CALLOUT_RE.match(line)
    if m:
        return m.group("kind").lower(), m.group("title").strip()
    return None, line


def parse_objectives(lines: list[str]) -> list[Objective]:
    """Pull the bullet list under `## Objetivos` / `## Objetivo`."""
    in_obj = False
    out: list[Objective] = []
    for line in lines:
        h = HEADING_RE.match(line)
        if h:
            txt = re.sub(r"\s*\^[A-Za-z0-9_-]+\s*$", "", h.group("text")).strip().lower()
            if txt.startswith("objetivo"):
                in_obj = True
                continue
            elif in_obj:
                break
        if not in_obj:
            continue
        li = LIST_ITEM_RE.match(line)
        if not li:
            continue
        body = li.group("body")
        cb = CHECKBOX_RE.match(body)
        if cb:
            out.append(Objective(text=cb.group("text"), done=cb.group("state").lower() == "x"))
    return out


def parse_section(lines: list[str], heading_match: str) -> list[str]:
    """Return the lines under the heading that matches `heading_match`."""
    out: list[str] = []
    capturing = False
    for line in lines:
        h = HEADING_RE.match(line)
        if h:
            txt = h.group("text").strip().lower()
            if txt == heading_match.lower() or txt.startswith(heading_match.lower()):
                capturing = True
                continue
            elif capturing:
                break
        if capturing:
            out.append(line)
    return out


def parse_quest(path: Path) -> Quest:
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    lines = body.splitlines()

    title = fm.get("quest") or path.stem
    filename = path.name

    if filename in QUEST_OVERRIDES:
        location, qtype, qnum = QUEST_OVERRIDES[filename]
    else:
        loc_raw = fm.get("location", "")
        m = WIKILINK_RE.search(loc_raw)
        location = (m.group(1).split("|", 1)[-1].rsplit("/", 1)[-1] if m else loc_raw.rsplit("/", 1)[-1] or "—")
        num_match = re.match(r"^(\d+)", filename)
        qnum = num_match.group(1) if num_match else "x"
        qtype = "side" if "Side Quests" in str(path) else "main"

    objectives = parse_objectives(lines)

    summary_lines = parse_section(lines, "Resumo")
    summary = "\n".join(summary_lines).strip()

    walk_lines = parse_section(lines, "Walkthrough")
    walkthrough = walk_lines  # raw — we'll render later

    rewards_lines = parse_section(lines, "Recompensas")
    rewards = rewards_lines

    notes_lines = parse_section(lines, "Notas Importantes")
    notes = notes_lines

    return Quest(
        filename=filename,
        title=title,
        location=location,
        quest_type=qtype,
        quest_num=qnum,
        objectives=objectives,
        summary=summary,
        walkthrough=walkthrough,
        rewards=rewards,
        notes=notes,
        raw=text,
    )


def collect_quests(roots: Iterable[Path]) -> list[Quest]:
    out: list[Quest] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.md")):
            out.append(parse_quest(path))
    return out


# ---------------------------------------------------------------------------
# Markdown → HTML (minimal)
# ---------------------------------------------------------------------------

def render_inline(text: str) -> str:
    """Apply inline transforms: wiki-links → anchors, escape HTML, bold."""
    text = html.escape(text)
    # Wiki-links: [[File]] or [[File|Alias]] → <a href="...">Alias or File</a>
    def link_repl(m: re.Match) -> str:
        target = m.group(1)
        if "|" in target:
            target, alias = target.split("|", 1)
        else:
            alias = target.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        href = resolve_wikilink(target)
        return f'<a href="{href}">{html.escape(alias)}</a>'
    text = WIKILINK_RE.sub(link_repl, text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def resolve_wikilink(target: str) -> str:
    """Map a [[wiki-link]] target to a relative HTML URL."""
    target = target.strip()
    # Strip .md
    if target.endswith(".md"):
        target = target[:-3]
    parts = target.split("/")
    # Map by filename
    fname = parts[-1]
    slug = re.sub(r"[^a-z0-9]+", "-", fname.lower()).strip("-")
    # If "Stage 1.md" → "stage-1.html"
    if target.lower() in {"stage 1", "stage-1"}:
        return "stage-1.html"
    if target.startswith("Main Quests/"):
        return f"quests/stage-1/main-quests/{slug}.html"
    if target.startswith("Side Quests/"):
        return f"quests/stage-1/side-quests/{slug}.html"
    if target.startswith("Locations/"):
        return f"quests/stage-1/locations/{slug}.html"
    if target.lower().startswith("quest"):
        return f"stage-1.html#{slugify(target)}"
    # Fallback: same directory, slugified
    return f"{slug}.html"


def slugify(text: str) -> str:
    s = text.lower()
    repl = str.maketrans({
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u", "ü": "u",
        "ç": "c",
    })
    s = s.translate(repl)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def render_md_block(text: str) -> str:
    """Render a small MD block (after parse_section) as HTML.

    Supports: paragraphs, bullet lists, simple tables, callouts.
    """
    out: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # Callout: > [!kind] Title *
        kind, body = strip_callout_marker(stripped)
        if kind is not None:
            callout_lines = [body]
            i += 1
            while i < len(lines):
                cont = lines[i]
                if not cont.lstrip().startswith(">"):
                    break
                callout_lines.append(cont.lstrip()[1:].lstrip())
                i += 1
            inner = "<br>".join(render_inline(l) for l in callout_lines if l.strip())
            out.append(f'<div class="callout callout-{kind}"><div class="callout-title">{kind}</div><div class="callout-body">{inner}</div></div>')
            continue

        # Bullet list
        if LIST_ITEM_RE.match(line):
            items: list[str] = []
            while i < len(lines) and LIST_ITEM_RE.match(lines[i]):
                m = LIST_ITEM_RE.match(lines[i])
                items.append(f'<li>{render_inline(m.group("body"))}</li>')
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # Table (simple |---| syntax)
        if "|" in stripped and i + 1 < len(lines) and re.match(r"^\s*\|?[\s\-:|]+\|?\s*$", lines[i + 1]):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2  # skip header + separator
            rows = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append("<tr>" + "".join(f"<td>{render_inline(c)}</td>" for c in row) + "</tr>")
                i += 1
            thead = "<thead><tr>" + "".join(f"<th>{render_inline(h)}</th>" for h in header) + "</tr></thead>"
            out.append(f"<table>{thead}<tbody>{''.join(rows)}</tbody></table>")
            continue

        # Heading inside section (shouldn't usually happen here, but support)
        h = HEADING_RE.match(line)
        if h:
            level = len(h.group(1))
            txt = re.sub(r"\s*\^[A-Za-z0-9_-]+\s*$", "", h.group("text"))
            out.append(f"<h{level + 2}>{render_inline(txt)}</h{level + 2}>")
            i += 1
            continue

        # Default: paragraph (greedy until blank line)
        para = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not LIST_ITEM_RE.match(lines[i]) and not HEADING_RE.match(lines[i]) and not CALLOUT_RE.match(lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>" + render_inline(" ".join(para)) + "</p>")

    return "\n".join(out)


def render_quest_objectives_html(quest: Quest, index_offset: int = 1) -> tuple[str, list[tuple[str, bool]]]:
    """Render objectives as <li><input type=checkbox data-track-id=...> for
    the cheat sheet. Returns (html, list of (track_id, done)) for the
    tracker.

    IMPORTANT: We never emit the `checked` attribute here, even if the
    source MD has `- [x]`. The published site should show a fresh
    tracking slate on every visit; user-supplied state lives in
    localStorage, not in the HTML. The MD's `- [x]` markers stay useful
    as an authoring hint for the human writing the files but they do
    NOT drive the published checkbox state.
    """
    items: list[str] = []
    tracks: list[tuple[str, bool]] = []
    for i, obj in enumerate(quest.objectives, index_offset):
        tid = f"{quest.track_prefix}-{i}"
        items.append(
            f'<li data-track-id="{tid}">'
            f'<label><input type="checkbox" data-track-id="{tid}"> '
            f'<span class="obj-text">{html.escape(obj.text)}</span>'
            f'</label></li>'
        )
        tracks.append((tid, obj.done))
    return "\n".join(items), tracks


# ---------------------------------------------------------------------------
# HTML templates (CSS + JS are shared between every page)
# ---------------------------------------------------------------------------

SHARED_CSS = """
:root {
  --bg: #faf8f5;
  --bg-card: #fff;
  --fg: #2a2a2a;
  --fg-muted: #6b6b6b;
  --border: #e0d8d0;
  --accent: #7b3f00;
  --accent-soft: #fff3e0;
  --ok: #2e7d32;
  --warn: #c08400;
  --pending: #555;
  --code-bg: #f4f0ea;
  --shadow: 0 1px 2px rgba(0,0,0,0.04);
  --radius: 6px;
  --max-w: 920px;
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.55;
  font-size: 16px;
}
main {
  max-width: var(--max-w);
  margin: 0 auto;
  padding: 2rem 1.25rem 4rem;
}
header.page {
  border-bottom: 1px solid var(--border);
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
}
header.page h1 {
  margin: 0 0 0.25rem;
  font-size: 1.8rem;
  letter-spacing: -0.01em;
}
header.page .subtitle {
  color: var(--fg-muted);
  font-size: 0.95rem;
}
nav.crumbs {
  font-size: 0.85rem;
  color: var(--fg-muted);
  margin-bottom: 1rem;
}
nav.crumbs a { color: var(--fg-muted); text-decoration: none; }
nav.crumbs a:hover { text-decoration: underline; }

h2 { margin-top: 2rem; font-size: 1.4rem; border-bottom: 1px solid var(--border); padding-bottom: 0.25rem; }
h3 { margin-top: 1.5rem; font-size: 1.15rem; }
h4 { margin-top: 1.2rem; font-size: 1rem; color: var(--fg-muted); text-transform: uppercase; letter-spacing: 0.05em; }

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

ul { padding-left: 1.4rem; }
ul.dd2-checklist {
  list-style: none;
  padding-left: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-card);
  box-shadow: var(--shadow);
}
ul.dd2-checklist li {
  border-bottom: 1px solid var(--border);
  padding: 0.55rem 0.85rem;
}
ul.dd2-checklist li:last-child { border-bottom: none; }
ul.dd2-checklist label {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  cursor: pointer;
  user-select: none;
}
ul.dd2-checklist input[type="checkbox"] {
  margin-top: 0.2rem;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  accent-color: var(--accent);
}
ul.dd2-checklist li.is-checked .obj-text {
  text-decoration: line-through;
  color: var(--fg-muted);
}

.badge {
  display: inline-block;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  background: var(--accent-soft);
  color: var(--accent);
  margin-left: 0.4rem;
  vertical-align: middle;
}
.badge.ok { background: #e6f3e8; color: var(--ok); }
.badge.warn { background: #fff4d6; color: var(--warn); }
.badge.pending { background: #eee; color: var(--pending); }

.callout {
  border-left: 4px solid var(--accent);
  background: var(--accent-soft);
  padding: 0.6rem 0.9rem;
  margin: 1rem 0;
  border-radius: var(--radius);
}
.callout .callout-title {
  text-transform: uppercase;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 0.2rem;
}
.callout-warning { border-left-color: var(--warn); background: #fff4d6; }
.callout-warning .callout-title { color: var(--warn); }
.callout-tip { border-left-color: var(--ok); background: #e6f3e8; }
.callout-tip .callout-title { color: var(--ok); }
.callout-info { border-left-color: #1976d2; background: #e3f2fd; }
.callout-info .callout-title { color: #1976d2; }

code { background: var(--code-bg); padding: 0.05rem 0.35rem; border-radius: 4px; font-size: 0.92em; }
pre { background: var(--code-bg); padding: 0.8rem 1rem; border-radius: var(--radius); overflow-x: auto; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.95rem; }
th, td { padding: 0.45rem 0.65rem; border-bottom: 1px solid var(--border); text-align: left; }
th { background: var(--code-bg); font-weight: 600; }

.toc {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.9rem 1.1rem;
  margin: 1.2rem 0;
  box-shadow: var(--shadow);
}
.toc h2 { margin: 0 0 0.5rem; border: none; padding: 0; font-size: 1.05rem; }
.toc ul { list-style: none; padding-left: 0; margin: 0; }
.toc li { padding: 0.18rem 0; }
.toc li a { display: flex; align-items: baseline; gap: 0.4rem; justify-content: space-between; }
.toc .toc-count {
  font-family: ui-monospace, monospace;
  font-size: 0.82rem;
  color: var(--fg-muted);
}

.summary-bar {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.9rem 1.1rem;
  margin: 1.2rem 0;
  box-shadow: var(--shadow);
  display: flex;
  flex-wrap: wrap;
  gap: 1.2rem;
  align-items: center;
}
.summary-bar .stat { display: flex; flex-direction: column; }
.summary-bar .stat .label { font-size: 0.7rem; color: var(--fg-muted); text-transform: uppercase; letter-spacing: 0.08em; }
.summary-bar .stat .value { font-size: 1.4rem; font-weight: 700; color: var(--fg); }
.summary-bar button {
  margin-left: auto;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.4rem 0.8rem;
  cursor: pointer;
  font-size: 0.85rem;
}
.summary-bar button:hover { background: var(--code-bg); }

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1a1a1c;
    --bg-card: #25252a;
    --fg: #e8e6e3;
    --fg-muted: #999;
    --border: #3a3a40;
    --accent: #ffb88c;
    --accent-soft: #3a2418;
    --code-bg: #2a2a2f;
  }
  .callout-info { background: #1e2a3a; }
  .callout-warning { background: #3a2a18; }
  .callout-tip { background: #1e3a22; }
}
"""

SHARED_JS = r"""
(function () {
  "use strict";
  const STORAGE_KEY = "dd2-tracker-v1";
  const DEBUG = true;  // set to false to silence the diagnostic banner

  // ----- diagnostic banner (visible feedback) -----
  let diagTimer = null;
  function showDiag(msg, level, autoHideMs) {
    if (!DEBUG) return;
    let el = document.getElementById("dd2-diag");
    if (!el) {
      el = document.createElement("div");
      el.id = "dd2-diag";
      el.style.cssText = "position:fixed;bottom:1rem;right:1rem;padding:0.5rem 0.9rem;border-radius:6px;font:13px ui-monospace,monospace;z-index:9999;box-shadow:0 2px 6px rgba(0,0,0,0.15);transition:opacity 0.3s;max-width:90vw;text-align:right;";
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.style.opacity = "1";
    if (level === "ok") el.style.background = "#2e7d32";
    else if (level === "err") el.style.background = "#c62828";
    else el.style.background = "#37474f";
    el.style.color = "#fff";
    if (diagTimer) clearTimeout(diagTimer);
    if (autoHideMs) {
      diagTimer = setTimeout(() => { el.style.opacity = "0"; }, autoHideMs);
    }
  }

  // ----- storage helpers (with explicit error reporting) -----
  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return (parsed && typeof parsed === "object") ? parsed : {};
    } catch (e) {
      showDiag("Erro lendo localStorage: " + e.message, "err");
      return {};
    }
  }

  function saveState(state) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      showDiag("Salvo ✓ (" + Object.keys(state).length + " marcados)", "ok", 1200);
      return true;
    } catch (e) {
      showDiag("Erro salvando localStorage: " + e.message, "err");
      return false;
    }
  }

  function clearAll() {
    try {
      localStorage.removeItem(STORAGE_KEY);
      return true;
    } catch (e) {
      showDiag("Erro limpando localStorage: " + e.message, "err");
      return false;
    }
  }

  // ----- apply state to a single checkbox (overrides HTML's checked attr) -----
  function applyTo(cb, state) {
    const id = cb.getAttribute("data-track-id");
    if (!id) return;
    const want = !!state[id];
    // Set BOTH the property AND the attribute to be defensive
    cb.checked = want;
    if (want) cb.setAttribute("checked", "checked");
    else cb.removeAttribute("checked");
    cb.closest("li")?.classList.toggle("is-checked", want);
  }

  function updateTotals() {
    document.querySelectorAll("[data-total-for]").forEach((el) => {
      const prefix = el.getAttribute("data-total-for");
      let done = 0, total = 0;
      document.querySelectorAll("input[type=checkbox][data-track-id]").forEach((cb) => {
        if ((cb.getAttribute("data-track-id") || "").startsWith(prefix)) {
          total += 1;
          if (cb.checked) done += 1;
        }
      });
      el.textContent = total === 0 ? "—" : (done === total ? "✅ " : "") + done + "/" + total;
    });
  }

  // ----- main -----
  function init() {
    if (DEBUG) showDiag("Tracker inicializando…", "info");

    // Verify localStorage is usable
    try {
      localStorage.setItem("__dd2_probe", "1");
      localStorage.removeItem("__dd2_probe");
    } catch (e) {
      showDiag("localStorage BLOQUEADO neste browser/contexto. Progresso não vai persistir.", "err");
      return;
    }

    const state = loadState();
    const items = document.querySelectorAll("input[type=checkbox][data-track-id]");
    items.forEach((cb) => applyTo(cb, state));
    updateTotals();

    const doneCount = Object.values(state).filter(Boolean).length;
    if (DEBUG) showDiag("Tracker ativo: " + items.length + " checkboxes · " + doneCount + " marcados", "ok", 2000);

    // Event delegation — one listener on document catches all checkbox toggles
    document.addEventListener("change", (e) => {
      const t = e.target;
      if (!(t instanceof HTMLInputElement)) return;
      if (t.type !== "checkbox") return;
      const id = t.getAttribute("data-track-id");
      if (!id) return;
      const s = loadState();
      if (t.checked) s[id] = true;
      else delete s[id];
      t.closest("li")?.classList.toggle("is-checked", t.checked);
      const ok = saveState(s);
      if (ok) updateTotals();
    });

    // Reset button
    const reset = document.getElementById("reset-tracker");
    if (reset) {
      reset.addEventListener("click", () => {
        if (confirm("Reset ALL progress? This clears localStorage for this site.")) {
          if (clearAll()) {
            showDiag("Resetado ✓ Recarregando…", "ok");
            setTimeout(() => location.reload(), 400);
          }
        }
      });
    }
  }

  // Robust initialization
  function boot() {
    try { init(); }
    catch (e) { showDiag("Init falhou: " + e.message, "err"); }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    setTimeout(boot, 0);
  }
})();
"""


def page_shell(*, title: str, body_html: str, crumbs_html: str = "", extra_css: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Dragon's Dogma 2 Walkthrough</title>
<meta name="description" content="Walkthrough e checklist interativo de Dragon's Dogma 2">
<style>{SHARED_CSS}{extra_css}</style>
</head>
<body>
<main>
{nav_crumbs(crumbs_html)}
{body_html}
</main>
<script>{SHARED_JS}</script>
</body>
</html>
"""


def nav_crumbs(inner_html: str) -> str:
    if not inner_html:
        return ""
    return f'<nav class="crumbs"><a href="index.html">Início</a> › {inner_html}</nav>\n'


def status_badge(status: str) -> str:
    if "✅" in status:
        cls, label = "ok", status
    elif "⬜" in status:
        cls, label = "pending", status
    else:
        cls, label = "warn", status
    return f'<span class="badge {cls}">{html.escape(label)}</span>'


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------

def render_index(repo_root: Path, stages: list[int]) -> str:
    """Generate dist/index.html."""
    body = ['<header class="page">',
            '<h1>🐉 Dragon\'s Dogma 2 — Walkthrough</h1>',
            '<div class="subtitle">Walkthrough interativo em português. Marque os objetivos direto no navegador — o progresso persiste entre visitas (localStorage).</div>',
            '</header>']
    body.append('<div class="callout callout-info"><div class="callout-title">Info</div>'
                '<div class="callout-body">Cada página é <strong>self-contained</strong>: HTML + CSS + JS num único arquivo. Abra direto no browser, funciona offline.</div></div>')
    body.append('<h2>Stages</h2>')
    body.append('<ul>')
    for n in stages:
        body.append(f'  <li><a href="stage-{n}.html">Stage {n}</a> — Cheat sheet interativa com TODOs, NPCs e recompensas</li>')
    body.append('</ul>')

    body.append('<h2>Como funciona o tracker</h2>')
    body.append('<p>Os checkboxes em cada página de stage usam <code>data-track-id</code> com esquema '
                '<code>s{stage}-{main|side}-{NN}-{i}</code>. O JS no fim de cada página lê/escreve '
                '<code>localStorage["dd2-tracker-v1"]</code>.</p>')
    body.append('<p>Para zerar tudo: abra o console do navegador e rode '
                '<code>localStorage.removeItem("dd2-tracker-v1")</code>.</p>')

    body.append('<h2>Fonte dos dados</h2>')
    body.append('<ul>')
    body.append('<li><a href="https://dragonsdogma2.wiki.fextralife.com/">Fextralife Wiki DD2</a></li>')
    body.append('<li><a href="https://www.ign.com/wikis/dragons-dogma-2/">IGN DD2 Guide</a></li>')
    body.append('<li><a href="https://dragonsdogma.fandom.com/wiki/Dragon%27s_Dogma_2_Wiki">Dragon\'s Dogma Wiki (Fandom)</a></li>')
    body.append('</ul>')

    return page_shell(title="Início", body_html="\n".join(body))


def render_stage(stage_n: int, quests: list[Quest]) -> str:
    """Generate dist/stage-{n}.html — the cheat sheet."""
    # Group by canonical location
    by_loc: dict[str, list[Quest]] = {loc: [] for loc, _ in LOCATION_ORDER}
    for q in quests:
        by_loc.setdefault(q.location, []).append(q)
    for loc in by_loc:
        by_loc[loc].sort(key=lambda q: (0 if q.quest_type == "main" else 1, q.quest_num))

    total_done = sum(sum(1 for o in q.objectives if o.done) for q in quests)
    total_all = sum(len(q.objectives) for q in quests)
    main_count = sum(1 for q in quests if q.quest_type == "main")
    side_count = sum(1 for q in quests if q.quest_type == "side")

    body: list[str] = []
    body.append(f'<header class="page">')
    body.append(f'<h1>🎮 Stage {stage_n} — Playthrough</h1>')
    body.append(f'<div class="subtitle">Cheat sheet interativo. Checkboxes persistem no navegador.</div>')
    body.append('</header>')

    body.append(f'''<div class="summary-bar">
  <div class="stat"><span class="label">Main Quests</span><span class="value">{main_count}</span></div>
  <div class="stat"><span class="label">Side Quests</span><span class="value">{side_count}</span></div>
  <div class="stat"><span class="label">Sub-objetivos</span><span class="value"><span data-total-for="s{stage_n}-">{total_done}</span>/{total_all}</span></div>
  <button id="reset-tracker" type="button">Resetar progresso</button>
</div>''')

    # TOC
    body.append('<nav class="toc">')
    body.append('<h2>📍 Locais (âncoras)</h2>')
    body.append('<ul>')
    for loc, emoji in LOCATION_ORDER:
        if not by_loc.get(loc):
            continue
        slug = slugify(loc)
        badges = []
        for q in by_loc[loc]:
            badges.append(f'<code>{q.quest_num}</code> {status_badge(q.status)}')
        body.append(f'  <li><a href="#{slug}">{emoji} {html.escape(loc)} <span class="toc-count">{" ".join(badges)}</span></a></li>')
    body.append('</ul>')
    body.append('</nav>')

    # Per-location sections
    for loc, emoji in LOCATION_ORDER:
        if not by_loc.get(loc):
            continue
        loc_quests = by_loc[loc]
        slug = slugify(loc)
        main_q = [q for q in loc_quests if q.quest_type == "main"]
        side_q = [q for q in loc_quests if q.quest_type == "side"]

        body.append(f'<h2 id="{slug}">{emoji} {html.escape(loc)}</h2>')

        if main_q:
            body.append('<h4>⚔️ Main Quests</h4>')
            for q in main_q:
                body.append(render_quest_block(q))
        if side_q:
            body.append('<h4>🗡️ Side Quests</h4>')
            for q in side_q:
                body.append(render_quest_block(q))

    # Footer tip
    body.append('<div class="callout callout-tip"><div class="callout-title">Tip</div>'
                '<div class="callout-body">Os <code>data-track-id</code> são determinísticos '
                f'(formato <code>s{stage_n}-{{main|side}}-{{NN}}-{{i}}</code>), então se você quiser '
                'exportar/importar progresso é só copiar o JSON do <code>localStorage</code>.</div></div>')

    return page_shell(
        title=f"Stage {stage_n}",
        body_html="\n".join(body),
        crumbs_html=f'Stage {stage_n}',
    )


def render_quest_block(quest: Quest) -> str:
    """Render a quest as a collapsible-ish section in the cheat sheet."""
    parts: list[str] = []
    parts.append(f'<h3>{html.escape(quest.title)} {status_badge(quest.status)}</h3>')

    parts.append(f'<p><small>Quest ID: <code>{quest.track_prefix}</code> · '
                 f'<a href="{quest.url}">Ver detalhes completos →</a></small></p>')

    if quest.summary:
        parts.append(f'<p>{render_inline(quest.summary)}</p>')

    if quest.objectives:
        obj_html, _ = render_quest_objectives_html(quest)
        parts.append(f'<ul class="dd2-checklist">\n{obj_html}\n</ul>')
    else:
        parts.append('<p><em>Sem objetivos listados.</em></p>')

    return "\n".join(parts)


def render_quest_detail(quest: Quest) -> str:
    """Generate a per-quest detail page (e.g., quests/stage-1/main-quests/01---gaoled-awakening.html)."""
    parts: list[str] = []
    parts.append('<header class="page">')
    parts.append(f'<h1>{html.escape(quest.title)}</h1>')
    parts.append(f'<div class="subtitle">Quest <code>{quest.track_prefix}</code> · {html.escape(quest.location)} {status_badge(quest.status)}</div>')
    parts.append('</header>')

    if quest.summary:
        parts.append('<h2>Resumo</h2>')
        parts.append(render_md_block(quest.summary))

    if quest.objectives:
        parts.append('<h2>Objetivos</h2>')
        obj_html, _ = render_quest_objectives_html(quest)
        parts.append(f'<ul class="dd2-checklist">\n{obj_html}\n</ul>')

    if quest.walkthrough:
        parts.append('<h2>Walkthrough</h2>')
        parts.append(render_md_block("\n".join(quest.walkthrough)))

    if quest.rewards:
        parts.append('<h2>Recompensas</h2>')
        parts.append(render_md_block("\n".join(quest.rewards)))

    if quest.notes:
        parts.append('<h2>Notas Importantes</h2>')
        parts.append(render_md_block("\n".join(quest.notes)))

    sub = "main-quests" if quest.quest_type == "main" else "side-quests"
    return page_shell(
        title=quest.title,
        body_html="\n".join(parts),
        crumbs_html=f'<a href="../../../../stage-{1}.html">Stage 1</a> › <a href="../../../../stage-1.html#{sub}">{sub.replace("-", " ").title()}</a> › {html.escape(quest.title)}',
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    p.add_argument("--out", type=Path, default=None, help="Output directory (default: <repo>/dist)")
    args = p.parse_args(argv)

    repo_root = args.repo_root.resolve()
    out = (args.out or repo_root / "dist").resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Stage 1 quest roots
    stage1 = repo_root / "Quests" / "Stage 1"
    roots = [stage1 / "Main Quests", stage1 / "Side Quests"]
    quests = collect_quests(roots)

    if not quests:
        print("[warn] No quests parsed; nothing to write.", file=sys.stderr)
        return 1

    # dist/index.html
    stages = [1]
    (out / "index.html").write_text(render_index(repo_root, stages), encoding="utf-8")
    print(f"[ok] {out/'index.html'}")

    # dist/stage-1.html
    (out / "stage-1.html").write_text(render_stage(1, quests), encoding="utf-8")
    print(f"[ok] {out/'stage-1.html'}")

    # dist/quests/stage-1/{main-quests,side-quests}/<slug>.html
    for q in quests:
        sub = "main-quests" if q.quest_type == "main" else "side-quests"
        target = out / "quests" / "stage-1" / sub / f"{q.slug}.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_quest_detail(q), encoding="utf-8")
    print(f"[ok] {len(quests)} per-quest pages")

    print(f"\nDone. Open {out/'stage-1.html'} in your browser to preview.")
    return 0


if __name__ == "__main__":
    sys.exit(main())