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
NUMBERED_ITEM_RE = re.compile(r"^\s*\d+\.\s+(?P<body>.+?)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(?P<text>.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\[(?P<state>[ xX])\]\s+(?P<text>.+?)\s*$")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
CALLOUT_RE = re.compile(r"^>\s*\[!(?P<kind>[a-z]+)\]\s*(?P<title>[^*]*?)\*\s*$", re.IGNORECASE)
HTML_INLINE_RE = re.compile(r"<(input|li|ul|ol|a)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# i18n — UI chrome strings (EN default, PT alternatve). Content comes from
# the MD source (PT) and falls back to itself for the EN block until the
# user adds a matching *.en.md file.
# ---------------------------------------------------------------------------

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "page_title_home": "Home",
        "page_title_stage": "Stage 1",
        "homepage_subtitle": "Interactive walkthrough in Portuguese. Tick objectives in your browser — progress persists (localStorage).",
        "cheatsheet_subtitle": "Interactive cheat sheet. Checkboxes persist in your browser.",
        "lang_btn_en": "EN",
        "lang_btn_pt": "PT",
        "main_quests": "Main Quests",
        "side_quests": "Side Quests",
        "type_label_main": "Main Quest",
        "type_label_side": "Side Quest",
        "type_emoji_main": "⚔️",
        "type_emoji_side": "🗡️",
        "section_resumo": "Summary",
        "section_objetivos": "Objectives",
        "section_walkthrough": "Walkthrough",
        "section_recompensas": "Rewards",
        "section_notas": "Important Notes",
        "ver_detalhes": "View full details →",
        "proxima_quest": "Next quest:",
        "sem_objetivos": "No objectives listed.",
        "resetar_progresso": "Reset progress",
        "stat_main": "Main Quests",
        "stat_side": "Side Quests",
        "stat_subs": "Sub-objectives",
        "alert_coming_soon": "UNDER CONSTRUCTION — translation coming soon",
        "alert_translation_pending": "(Translation pending)",
        "stage_card_open": "Open stage →",
        "view_toggle_locations": "📍 By location",
        "view_toggle_flow": "🗺 By recommended flow",
        "stage_card_main_fmt": "⚔ {n} main quests · 🗡 {s} side quests",
        "quick_links_label": "Quick links:",
        "quick_link_stage1": "Stage 1",
        "quick_link_locations": "Browse locations",
        "quick_link_reset": "Reset tracker",
        "quick_link_export": "Export JSON",
        "quick_link_import": "Import JSON",
        "export_btn": "⬇ Export JSON",
        "import_btn": "⬆ Import JSON",
        "diag_init": "Tracker initializing…",
        "diag_blocked": "localStorage BLOCKED. Progress will NOT persist.",
        "diag_active_fmt": "Tracker active: {n} checkboxes · {d} marked",
        "diag_save_fmt": "Saved ✓ ({n} marked)",
        "diag_reset": "Reset ✓ Reloading…",
        "diag_init_fail_fmt": "Init failed: {msg}",
        "diag_save_fail_fmt": "Failed to save localStorage: {msg}",
        "diag_load_fail_fmt": "Failed to read localStorage: {msg}",
        "diag_clear_fail_fmt": "Failed to clear localStorage: {msg}",
        "confirm_reset": "Reset ALL progress? This clears localStorage for this site.",
    },
    "pt": {
        "page_title_home": "Início",
        "page_title_stage": "Stage 1",
        "homepage_subtitle": "Walkthrough interativo em português. Marque os objetivos direto no navegador — o progresso persiste entre visitas (localStorage).",
        "cheatsheet_subtitle": "Cheat sheet interativo. Checkboxes persistem no navegador.",
        "lang_btn_en": "EN",
        "lang_btn_pt": "PT",
        "main_quests": "Main Quests",
        "side_quests": "Side Quests",
        "type_label_main": "Main Quest",
        "type_label_side": "Side Quest",
        "type_emoji_main": "⚔️",
        "type_emoji_side": "🗡️",
        "section_resumo": "Resumo",
        "section_objetivos": "Objetivos",
        "section_walkthrough": "Walkthrough",
        "section_recompensas": "Recompensas",
        "section_notas": "Notas Importantes",
        "ver_detalhes": "Ver detalhes →",
        "proxima_quest": "Próxima quest:",
        "sem_objetivos": "Sem objetivos listados.",
        "resetar_progresso": "Resetar progresso",
        "stat_main": "Main Quests",
        "stat_side": "Side Quests",
        "stat_subs": "Sub-objetivos",
        "alert_coming_soon": "EM CONSTRUÇÃO — tradução em breve",
        "alert_translation_pending": "(Tradução pendente)",
        "stage_card_open": "Abrir stage →",
        "view_toggle_locations": "📍 Por local",
        "view_toggle_flow": "🗺 Por fluxo recomendado",
        "stage_card_main_fmt": "⚔ {n} quests principais · 🗡 {s} quests secundárias",
        "quick_links_label": "Links rápidos:",
        "quick_link_stage1": "Stage 1",
        "quick_link_locations": "Ver locais",
        "quick_link_reset": "Zerar tracker",
        "quick_link_export": "Exportar JSON",
        "quick_link_import": "Importar JSON",
        "export_btn": "⬇ Exportar JSON",
        "import_btn": "⬆ Importar JSON",
        "diag_init": "Tracker inicializando…",
        "diag_blocked": "localStorage BLOQUEADO. Progresso NÃO vai persistir.",
        "diag_active_fmt": "Tracker ativo: {n} checkboxes · {d} marcados",
        "diag_save_fmt": "Salvo ✓ ({n} marcados)",
        "diag_reset": "Resetado ✓ Recarregando…",
        "diag_init_fail_fmt": "Init falhou: {msg}",
        "diag_save_fail_fmt": "Erro salvando localStorage: {msg}",
        "diag_load_fail_fmt": "Erro lendo localStorage: {msg}",
        "diag_clear_fail_fmt": "Erro limpando localStorage: {msg}",
        "confirm_reset": "Reset ALL progress? This clears localStorage for this site.",
    },
}


def L(lang: str, key: str, **fmt) -> str:
    """Look up a translated string for a language. Format placeholders work."""
    template = STRINGS[lang][key]
    if fmt:
        return template.format(**fmt)
    return template


def render_bilingual(en_text: str, pt_text: str, block: bool = False) -> str:
    """Emit BOTH language variants inline; JS controls which one is visible.

    block=True switches from inline display to block (for wrapping
    multi-paragraph content).
    """
    block_attr = ' data-block="1"' if block else ""
    return (
        f'<span class="i18n" data-lang="en"{block_attr}>{html.escape(en_text)}</span>'
        f'<span class="i18n" data-lang="pt"{block_attr} hidden>{html.escape(pt_text)}</span>'
    )


def render_bilingual_raw(en_html: str, pt_html: str) -> str:
    """Same idea as render_bilingual but accepts pre-rendered HTML on both sides
    (used for already-rendered quest content blocks, not chrome)."""
    return (
        f'<div class="i18n" data-lang="en" data-block="1">{en_html}</div>'
        f'<div class="i18n" data-lang="pt" data-block="1" hidden>{pt_html}</div>'
    )

# Tries to match location paths the user has used. New quests should
# stick to one of these canonical location strings.
LOCATION_ORDER: list[tuple[str, str]] = [
    ("Excavation Site", "🪨"),
    ("Ultramarine Waterfall", "💧"),
    ("Borderwatch Outpost", "🛡️"),
    ("Melve", "🏘️"),
    ("Melve → Vernworth", "🛤️"),
    ("Vernworth", "🏰"),
    ("Harve Village", "🏖️"),
    ("Moonglow Garden", "🌸"),
    ("Eini's House", "🏠"),
    ("Sacred Arbor", "🌳"),
    ("Checkpoint Rest Town", "🛏️"),
]

# ---------------------------------------------------------------------------
# File → stage index (populated by main() before any rendering).
# Lets resolve_wikilink() route cross-stage links correctly without
# threading the stage through every call site.
# ---------------------------------------------------------------------------

_FILE_STAGE: dict[str, int] = {}  # filename (e.g. "08 - In Dragon's Wake.md") → stage number


def _build_file_stage_index(quests_root: Path) -> None:
    """Populate _FILE_STAGE by scanning Quests/Stage */ for *.md files.

    Called once at startup from main(). Idempotent — re-calling overwrites.
    """
    _FILE_STAGE.clear()
    for stage_dir in sorted(quests_root.glob("Stage *")):
        if not stage_dir.is_dir():
            continue
        # Stage dir name is "Stage N" — extract N
        parts = stage_dir.name.split()
        if len(parts) != 2 or not parts[1].isdigit():
            continue
        stage_n = int(parts[1])
        for sub in ("Main Quests", "Side Quests"):
            sub_dir = stage_dir / sub
            if not sub_dir.exists():
                continue
            for path in sub_dir.glob("*.md"):
                _FILE_STAGE[path.name] = stage_n


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Objective:
    text: str
    done: bool
    divider: bool = False  # True for visual separator lines in the objectives list


@dataclass
class Quest:
    filename: str
    title: str
    location: str
    quest_type: str   # "main" | "side"
    quest_num: str
    stage: int = 1    # which Stage dir this quest lives in (1-based)
    objectives: list[Objective] = field(default_factory=list)
    summary: str = ""
    walkthrough: list[str] = field(default_factory=list)
    rewards: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    raw: str = ""
    # Path of the rendered page (relative to dist/), used to make
    # wiki-link hrefs in the body relative to the current page. Set
    # by the page renderer before any body content is emitted; empty
    # when rendering for the stage page (which uses root-relative
    # paths).
    from_path: str = ""

    @property
    def track_prefix(self) -> str:
        return f"s{self.stage}-{self.quest_type}-{self.quest_num}"

    @property
    def slug(self) -> str:
        s = self.filename.lower()
        # Strip BOTH `.en.md` (English source) AND `.md` (Portuguese source)
        # so the slug is identical for the pair. Without this, q_en.slug
        # ends up as e.g. `01-gaoled-awakening-en` and the rendered link
        # points to a file that was never written — `q_pt.slug` produces
        # the only file actually on disk. Symptom: 404 when clicking
        # "View full details →" with the language toggle in EN.
        if s.endswith(".en.md"):
            s = s[:-6]
        elif s.endswith(".md"):
            s = s[:-3]
        s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
        return s

    @property
    def url(self) -> str:
        sub = "main-quests" if self.quest_type == "main" else "side-quests"
        return f"quests/stage-{self.stage}/{sub}/{self.slug}.html"

    @property
    def status(self) -> str:
        if not self.objectives:
            return "Sem objetivos"
        # The build-time badge is a *placeholder* — the real state lives
        # in the user's localStorage and is overwritten by SHARED_JS's
        # updateTotals() on every page load. Always render as 0/N here
        # so users never see a misleading "✅ 6/6" flash on initial
        # paint (or after a JS error) when the MD just happens to have
        # all objectives authored as `- [x]`. The author-time hint is
        # preserved in the MD file itself; this string is just the
        # pre-JS default.
        total = len(self.objectives)
        return f"0/{total}"


# ---------------------------------------------------------------------------
# Stage metadata (for the homepage card grid)
# ---------------------------------------------------------------------------

@dataclass
class StageInfo:
    """Metadata for one stage, used by the homepage card."""
    number: int
    name: str           # raw frontmatter `name:` (single source-of-truth fallback)
    name_en: str        # frontmatter `name_en` (or `name` if absent)
    name_pt: str        # frontmatter `name_pt` (or `name` if absent)
    region: str         # from frontmatter `region:`
    objective: str      # from frontmatter `objective:`
    main_count: int     # *.md files in Stage N/Main Quests/
    side_count: int     # *.md files in Stage N/Side Quests/


def load_stage_info(stage_n: int, repo_root: Path) -> StageInfo:
    """Read the Stage MOC frontmatter + count quest files.

    Looks for the MOC in two places (first match wins):
      1. `Quests/Stage N/Stage N.md`         — inside the stage dir
      2. `Quests/Stage N.md`                 — alongside the stage dir
                                               (current convention in this vault)
    """
    quests_root = repo_root / "Quests"
    fm: dict[str, str] = {}
    candidates = [
        quests_root / f"Stage {stage_n}" / f"Stage {stage_n}.md",
        quests_root / f"Stage {stage_n}.md",
    ]
    for moc in candidates:
        if moc.exists():
            fm_text, _ = parse_frontmatter(moc.read_text(encoding="utf-8"))
            fm = fm_text
            break
    stage_dir = quests_root / f"Stage {stage_n}"
    main_dir = stage_dir / "Main Quests"
    side_dir = stage_dir / "Side Quests"
    # Filter out *.en.md so each bilingual pair is counted once.
    def _count_quests(d: Path) -> int:
        if not d.exists(): return 0
        return sum(1 for p in d.glob("*.md") if not p.stem.endswith(".en"))
    main_n = _count_quests(main_dir)
    side_n = _count_quests(side_dir)
    # Stage title: prefer `name_pt` for PT, `name_en` for EN, fallback to `name`.
    # Frontmatter authors can opt into bilingual stage titles by adding
    # both fields; otherwise the same string renders in both languages.
    return StageInfo(
        number=stage_n,
        name=fm.get("name", f"Stage {stage_n}"),
        name_en=fm.get("name_en", "") or fm.get("name", f"Stage {stage_n}"),
        name_pt=fm.get("name_pt", "") or fm.get("name", f"Stage {stage_n}"),
        region=fm.get("region", ""),
        objective=fm.get("objective", ""),
        main_count=main_n,
        side_count=side_n,
    )


def parse_stage_flow(stage_n: int, repo_root: Path) -> list[tuple[str, str]]:
    """Extract the recommended quest flow from the Stage MOC.

    Scans the MOC tables for `[[Main Quests/...]]` and `[[Side Quests/...]]`
    wiki-links, preserving document order. Returns a list of
    (quest_type, filename) tuples — e.g. `[("main", "01 - Gaoled Awakening"),
    ("main", "02 - Tale's Beginning"), ("side", "03 - Ordeal's of a New Recruit"), ...]`.

    Quests that don't appear in the MOC are appended at the end in
    filename order so the user still sees them in the flow view.
    """
    quests_root = repo_root / "Quests"
    candidates = [
        quests_root / f"Stage {stage_n}" / f"Stage {stage_n}.md",
        quests_root / f"Stage {stage_n}.md",
    ]
    moc_text = ""
    for moc in candidates:
        if moc.exists():
            moc_text = moc.read_text(encoding="utf-8")
            break
    flow: list[tuple[str, str]] = []
    seen: set[str] = set()
    if moc_text:
        for m in WIKILINK_RE.finditer(moc_text):
            target = m.group(1)
            for prefix, qtype in (("Main Quests/", "main"), ("Side Quests/", "side")):
                if target.startswith(prefix):
                    # `rstrip(".md")` would be wrong — it strips ANY of
                    # '.', 'm', 'd' from the end, mangling "Timid" to
                    # "Timi". Use removesuffix for the .md extension
                    # only.
                    fname = target[len(prefix):].removesuffix(".md").strip()
                    if fname and fname not in seen:
                        seen.add(fname)
                        flow.append((qtype, fname))
                    break
    # Append any quests not mentioned in the MOC (keeps the flow view
    # exhaustive even if the MOC is incomplete).
    stage_dir = quests_root / f"Stage {stage_n}"
    for sub, qtype in (("Main Quests", "main"), ("Side Quests", "side")):
        sub_dir = stage_dir / sub
        if not sub_dir.exists():
            continue
        for path in sorted(sub_dir.glob("*.md")):
            if path.stem.endswith(".en"):
                continue
            if path.stem not in seen:
                seen.add(path.stem)
                flow.append((qtype, path.stem))
    return flow


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
    """Pull the bullet list under `## Objetivos`/`## Objetivo` (PT)
    OR `## Objectives` (EN). Both spellings are accepted.

    Supports a divider syntax: a list item that starts with `--- ` is
    treated as a visual separator (not a checkbox), with the rest of
    the line as the label. This lets MD authors split a quest into
    parts — e.g. "--- durante [[Side Quests/09 - One-Eyed Interloper]] ---"
    between objective groups.

    Divider items are returned as `Objective(text=label, done=False,
    divider=True)`.
    """
    in_obj = False
    out: list[Objective] = []
    for line in lines:
        h = HEADING_RE.match(line)
        if h:
            txt = re.sub(r"\s*\^[A-Za-z0-9_-]+\s*$", "", h.group("text")).strip().lower()
            if txt.startswith("objetivo") or txt.startswith("objective"):
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
        elif body.lstrip().startswith("---"):
            # Divider: strip leading/trailing `---` and use the rest as label.
            label = body.strip().strip("-").strip()
            if label:
                out.append(Objective(text=label, done=False, divider=True))
    return out


def parse_section(lines: list[str], heading_match) -> list[str]:
    """Return the lines under the heading that matches any of the
    passed-in `heading_match` names (string or iterable of strings).

    Each candidate is matched against heading text lowercased and trimmed:
    equality OR startswith. Set `heading_match` to a list of aliases for
    one logical section (e.g. ("Resumo", "Summary")).
    """
    if isinstance(heading_match, str):
        candidates = [heading_match]
    else:
        candidates = list(heading_match)
    candidates_lc = [c.lower() for c in candidates]

    out: list[str] = []
    capturing = False
    for line in lines:
        h = HEADING_RE.match(line)
        if h:
            txt = h.group("text").strip().lower()
            if any(txt == c or txt.startswith(c) for c in candidates_lc):
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

    # Detect stage from path (e.g. "Quests/Stage 2/Main Quests/15 - Foo.md" → 2).
    # Defaults to 1 if no Stage dir is in the path.
    stage_n = 1
    for part in path.parts:
        m = re.match(r"^Stage\s+(\d+)$", part)
        if m:
            stage_n = int(m.group(1))
            break

    # Frontmatter is the source of truth for location + type.
    # Quest number is derived from the leading digits of the filename
    # (every quest file is named "NN - Title.md").
    loc_raw = fm.get("location", "")
    m = WIKILINK_RE.search(loc_raw)
    location = (m.group(1).split("|", 1)[-1].rsplit("/", 1)[-1] if m else loc_raw.rsplit("/", 1)[-1] or "—")
    num_match = re.match(r"^(\d+)", filename)
    qnum = num_match.group(1) if num_match else "x"
    qtype = "side" if "Side Quests" in str(path) else "main"

    objectives = parse_objectives(lines)

    summary_lines = parse_section(lines, ("Resumo", "Summary"))
    summary = "\n".join(summary_lines).strip()

    walk_lines = parse_section(lines, ("Walkthrough",))
    walkthrough = walk_lines  # raw — we'll render later

    rewards_lines = parse_section(lines, ("Recompensas", "Rewards"))
    rewards = rewards_lines

    notes_lines = parse_section(lines, ("Notas Importantes", "Important Notes"))
    notes = notes_lines

    return Quest(
        filename=filename,
        title=title,
        location=location,
        quest_type=qtype,
        quest_num=qnum,
        stage=stage_n,
        objectives=objectives,
        summary=summary,
        walkthrough=walkthrough,
        rewards=rewards,
        notes=notes,
        raw=text,
    )


def collect_quests_bilingual(roots: Iterable[Path]) -> "dict[str, dict[str, Quest]]":
    """Scan roots for both PT (`*.md`) and EN (`*.en.md`) quest files.

    Returns {stem: {"pt": Quest, "en": Quest-or-None}}. The "en" entry is
    None when no translation exists; renderers fall back to the PT quest
    in that case.
    """
    out: dict[str, dict[str, Quest]] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.md")):
            stem = path.stem
            lang = "pt"
            if stem.endswith(".en"):
                lang = "en"
                stem = stem[:-3]  # strip ".en"
            quest = parse_quest(path)
            entry = out.setdefault(stem, {})
            entry[lang] = quest
    return out


# Backwards-compat shim: when only PT is needed, return the PT list in
# stable order (used by callers that don't care about EN).
def collect_quests(roots: Iterable[Path]) -> list[Quest]:
    bundles = collect_quests_bilingual(roots)
    out: list[Quest] = []
    for stem in sorted(bundles):
        bundle = bundles[stem]
        out.append(bundle.get("pt") or bundle["en"])
    return out


# ---------------------------------------------------------------------------
# Markdown → HTML (minimal)
# ---------------------------------------------------------------------------

def render_inline(text: str, from_path: str = "") -> str:
    """Apply inline transforms: wiki-links → anchors, escape HTML, bold, code.

    `from_path` is the path (relative to dist/) of the page being
    rendered. It's used to make wiki-link hrefs relative to the current
    page so they work from per-quest pages too (not just the stage
    page). Pass an empty string to use absolute-from-root paths
    (suitable for the homepage and stage pages).

    Walks the text once, splitting on wiki-link matches. Plain text
    segments get html.escape()'d ONCE; wiki-link matches are
    substituted with already-properly-escaped <a> HTML. Without this
    split, calling html.escape() on the entire text and then again on
    the wiki-link alias double-escapes characters like `'` (the
    apostrophe in "Tale's Beginning"), surfacing as the literal entity
    `&amp;#x27;` in the rendered page.
    """
    parts: list[str] = []
    last_end = 0
    for m in WIKILINK_RE.finditer(text):
        # Escape everything BEFORE the wiki-link match
        parts.append(html.escape(text[last_end:m.start()]))
        # Build the <a> with both href and alias escaped exactly once
        target = m.group(1)
        if "|" in target:
            target, alias = target.split("|", 1)
        else:
            alias = target.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        href = resolve_wikilink(target, from_path=from_path)
        parts.append(f'<a href="{html.escape(href)}">{html.escape(alias)}</a>')
        last_end = m.end()
    # Escape the trailing text after the last wiki-link (or all of it if none)
    parts.append(html.escape(text[last_end:]))
    text = "".join(parts)
    # Bold then inline code (these patterns don't collide with HTML tags)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def _relative_path(from_path: str, to_path: str) -> str:
    """Compute a path from `from_path`'s directory to `to_path`.

    Both args are relative paths (no leading slash). Examples:
      ("stage-1.html", "quests/stage-1/main-quests/x.html")
        -> "quests/stage-1/main-quests/x.html"
      ("quests/stage-1/main-quests/01-foo.html", "quests/stage-1/main-quests/02-bar.html")
        -> "02-bar.html"
      ("quests/stage-1/main-quests/01-foo.html", "stage-1.html")
        -> "../../../stage-1.html"
    """
    from_dir = "/".join(from_path.split("/")[:-1])  # drop filename
    # Standard relpath: walk up from from_dir to root, then down to to_path
    from_parts = from_dir.split("/") if from_dir else []
    to_parts = to_path.split("/")
    # Find common prefix
    common = 0
    while common < len(from_parts) and common < len(to_parts) and from_parts[common] == to_parts[common]:
        common += 1
    ups = [".."] * (len(from_parts) - common)
    downs = to_parts[common:]
    if ups or downs:
        rel = "/".join(ups + downs)
        return rel if rel else to_path
    return to_path


def resolve_wikilink(target: str, from_path: str = "") -> str:
    """Map a [[wiki-link]] target to a relative HTML URL.

    `from_path` is the path of the page being rendered (relative to
    `dist/`). When provided, the returned path is relative to the
    current page's directory — so wiki-links work from per-quest
    pages as well as the stage page. When `from_path` is empty, the
    path is returned as-is (suitable for the homepage and stage page,
    where the default "from" is the dist/ root).
    """
    target = target.strip()
    # Strip .md
    if target.endswith(".md"):
        target = target[:-3]
    parts = target.split("/")
    # Map by filename
    fname = parts[-1]
    slug = re.sub(r"[^a-z0-9]+", "-", fname.lower()).strip("-")
    # Look up the target's stage from the prebuilt index. Cross-stage
    # links (e.g. Stage 2 page linking to a Stage 1 quest) resolve to
    # the correct stage path. Falls back to stage 1 if the target isn't
    # in the index (e.g. external-style link).
    def _target_stage() -> int:
        # Reattach the .md suffix to match the index key.
        candidate = fname + ".md"
        return _FILE_STAGE.get(candidate, 1)
    # "Stage 1.md" / "Stage 2.md" — special-case for MOC links
    if target.lower() in {"stage 1", "stage-1"}:
        abs_path = "stage-1.html"
        return _relative_path(from_path, abs_path) if from_path else abs_path
    if target.lower() in {"stage 2", "stage-2"}:
        abs_path = "stage-2.html"
        return _relative_path(from_path, abs_path) if from_path else abs_path
    if target.startswith("Main Quests/"):
        abs_path = f"quests/stage-{_target_stage()}/main-quests/{slug}.html"
        return _relative_path(from_path, abs_path) if from_path else abs_path
    if target.startswith("Side Quests/"):
        abs_path = f"quests/stage-{_target_stage()}/side-quests/{slug}.html"
        return _relative_path(from_path, abs_path) if from_path else abs_path
    if target.startswith("Locations/"):
        # Locations are not stage-scoped — they live at the top of the
        # vault. resolve_wikilink does not know if a Locations/ page has
        # been emitted; the build may 404 if not, but the path stays
        # stable across stages.
        abs_path = f"locations/{slug}.html"
        return _relative_path(from_path, abs_path) if from_path else abs_path
    if target.lower().startswith("quest"):
        abs_path = f"stage-1.html#{slugify(target)}"
        return _relative_path(from_path, abs_path) if from_path else abs_path
    # Fallback: if the bare target is a known quest file, route to its
    # actual stage (handles cross-stage links written without prefix).
    target_stage = _FILE_STAGE.get(fname + ".md", 1)
    if target_stage:
        # Determine sub (main-quests vs side-quests) by checking the on-disk
        # path. Faster than re-reading the file's frontmatter type: column
        # and survives renames. Falls back to flat slug if not found.
        repo_root = Path(__file__).resolve().parent.parent
        for sub_try in ("Main Quests", "Side Quests"):
            if (repo_root / "Quests" / f"Stage {target_stage}" / sub_try / (fname + ".md")).exists():
                sub = "main-quests" if sub_try == "Main Quests" else "side-quests"
                abs_path = f"quests/stage-{target_stage}/{sub}/{slug}.html"
                return _relative_path(from_path, abs_path) if from_path else abs_path
        abs_path = f"{slug}.html"
        return _relative_path(from_path, abs_path) if from_path else abs_path
    abs_path = f"{slug}.html"
    return _relative_path(from_path, abs_path) if from_path else abs_path


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


def render_md_block(text: str, from_path: str = "") -> str:
    """Render a small MD block (after parse_section) as HTML.

    `from_path` is forwarded to `render_inline` so wiki-link hrefs
    are computed relative to the current page (per-quest pages need
    `../../sub/sibling.html`, the stage page can use absolute paths).

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
            inner = "<br>".join(render_inline(l, from_path) for l in callout_lines if l.strip())
            out.append(f'<div class="callout callout-{kind}"><div class="callout-title">{kind}</div><div class="callout-body">{inner}</div></div>')
            continue

        # Bullet list
        if LIST_ITEM_RE.match(line):
            items: list[str] = []
            while i < len(lines) and LIST_ITEM_RE.match(lines[i]):
                m = LIST_ITEM_RE.match(lines[i])
                items.append(f'<li>{render_inline(m.group("body"), from_path)}</li>')
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # Numbered list (e.g. "1. Acompanhe o Pathfinder")
        if NUMBERED_ITEM_RE.match(line):
            items: list[str] = []
            while i < len(lines) and NUMBERED_ITEM_RE.match(lines[i]):
                m = NUMBERED_ITEM_RE.match(lines[i])
                items.append(f'<li>{render_inline(m.group("body"), from_path)}</li>')
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        # Table (simple |---| syntax)
        if "|" in stripped and i + 1 < len(lines) and re.match(r"^\s*\|?[\s\-:|]+\|?\s*$", lines[i + 1]):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2  # skip header + separator
            rows = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append("<tr>" + "".join(f"<td>{render_inline(c, from_path)}</td>" for c in row) + "</tr>")
                i += 1
            thead = "<thead><tr>" + "".join(f"<th>{render_inline(h, from_path)}</th>" for h in header) + "</tr></thead>"
            out.append(f"<table>{thead}<tbody>{''.join(rows)}</tbody></table>")
            continue

        # Heading inside section (shouldn't usually happen here, but support)
        h = HEADING_RE.match(line)
        if h:
            level = len(h.group(1))
            txt = re.sub(r"\s*\^[A-Za-z0-9_-]+\s*$", "", h.group("text"))
            out.append(f"<h{level + 2}>{render_inline(txt, from_path)}</h{level + 2}>")
            i += 1
            continue

        # Default: paragraph (greedy until blank line)
        para = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not LIST_ITEM_RE.match(lines[i]) and not NUMBERED_ITEM_RE.match(lines[i]) and not HEADING_RE.match(lines[i]) and not CALLOUT_RE.match(lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        out.append("<p>" + render_inline(" ".join(para), from_path) + "</p>")

    return "\n".join(out)


def render_quest_objectives_html(
    quest_pt: Quest,
    en_quest: Quest | None = None,
    index_offset: int = 1,
    show_dividers: bool = False,
) -> tuple[str, list[tuple[str, bool]]]:
    """Render the objectives checklist as a single `<ul>`.

    Each `<li>` carries exactly ONE `<input type="checkbox"
    data-track-id="…">`. If `en_quest` is given and its objective list
    lines up, the text inside is a pair of bilingual `<span
    class="i18n" data-lang="en">…</span><span class="i18n"
    data-lang="pt" hidden>…</span>`. JS toggles the `hidden` attribute
    to switch the visible language. Without `en_quest`, the PT text is
    rendered directly.

    A single shared `<input>` per track-id (instead of duplicating one
    per language) means the tracker JS binds once per objective. No
    duplicated rows, no duplicate checkboxes.

    Returns (html, list of (track_id, initial_done)). `initial_done`
    is from the source MD's `- [x]` — overridden at runtime by the
    localStorage value via the tracker JS.
    """
    items: list[str] = []
    tracks: list[tuple[str, bool]] = []
    # Walk PT and EN in parallel so dividers in one list stay aligned
    # with dividers in the other. The track-id counter advances only
    # for real (non-divider) objectives so the IDs don't shift.
    en_objs = en_quest.objectives if en_quest is not None else []
    i = 0  # 1-based tracker id (skips dividers)
    for pt_obj, en_obj in zip(quest_pt.objectives, en_objs):
        # Both sides a divider: emit the PT version (the EN text is
        # already represented by the language pill that the user can
        # click to flip). Resolve wiki-links so the label can mention
        # another quest by name. Skipped entirely when show_dividers
        # is False (per-quest page / by-location view).
        if pt_obj.divider and getattr(en_obj, "divider", False):
            if show_dividers:
                label_html = render_inline(pt_obj.text, from_path=quest_pt.from_path)
                items.append(f'<li class="obj-divider" aria-hidden="true">{label_html}</li>')
            continue
        # PT is a divider but EN isn't (or vice versa) — author error.
        # Treat it as a non-divider to keep both sides rendering.
        i += 1
        tid = f"{quest_pt.track_prefix}-{i}"
        text_html = (
            f'<span class="i18n" data-lang="en">{html.escape(en_obj.text)}</span>'
            f'<span class="i18n" data-lang="pt" hidden>{html.escape(pt_obj.text)}</span>'
        )
        items.append(
            f'<li data-track-id="{tid}">'
            f'<label><input type="checkbox" data-track-id="{tid}"> '
            f'<span class="obj-text">{text_html}</span>'
            f'</label></li>'
        )
        tracks.append((tid, pt_obj.done))
    # Tail of the longer list (in case PT and EN are not the same length)
    for tail_obj in quest_pt.objectives[len(en_objs):]:
        if tail_obj.divider:
            if show_dividers:
                label_html = render_inline(tail_obj.text, from_path=quest_pt.from_path)
                items.append(f'<li class="obj-divider" aria-hidden="true">{label_html}</li>')
            continue
        i += 1
        tid = f"{quest_pt.track_prefix}-{i}"
        items.append(
            f'<li data-track-id="{tid}">'
            f'<label><input type="checkbox" data-track-id="{tid}"> '
            f'<span class="obj-text">{html.escape(tail_obj.text)}</span>'
            f'</label></li>'
        )
        tracks.append((tid, tail_obj.done))
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
  --max-w: 1280px;
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

/* Quest cards — main (azul) vs side (amarelo) */
.quest-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin: 1.2rem 0;
  background: var(--bg-card);
  box-shadow: var(--shadow);
  overflow: hidden;
}
.quest-card > summary {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.7rem 1rem;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  list-style: none;
  user-select: none;
  transition: background 0.1s;
}
.quest-card > summary:hover { background: rgba(0,0,0,0.03); }
.quest-card > summary::-webkit-details-marker { display: none; }
.quest-card > summary::marker { display: none; }
.quest-card[open] > summary { border-bottom: 1px solid var(--border); }
.quest-card-caret {
  display: inline-block;
  width: 0.9em;
  text-align: center;
  color: var(--fg-muted);
  font-size: 0.85em;
  transition: transform 0.18s ease-out;
}
.quest-card[open] > summary .quest-card-caret { transform: rotate(90deg); }
.quest-card > summary h1, .quest-card > summary h3 {
  margin: 0;
  flex: 1;
  font-size: 1.15rem;
}
.quest-card > summary h1 { font-size: 1.4rem; }
.quest-card-body { padding: 0.8rem 1rem 0.4rem; }
.quest-type-label {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  white-space: nowrap;
}
.quest-master {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  margin: 0;
  cursor: pointer;
  accent-color: var(--accent);
}
.quest-card.main { border-top: 4px solid #1976d2; }
.quest-card.main .quest-type-label {
  background: rgba(25, 118, 210, 0.13);
  color: #1976d2;
}
.quest-card.side { border-top: 4px solid #c08400; }
.quest-card.side .quest-type-label {
  background: rgba(192, 132, 0, 0.18);
  color: #c08400;
}

code { background: var(--code-bg); padding: 0.05rem 0.35rem; border-radius: 4px; font-size: 0.92em; }
pre { background: var(--code-bg); padding: 0.8rem 1rem; border-radius: var(--radius); overflow-x: auto; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.95rem; }
th, td { padding: 0.45rem 0.65rem; border-bottom: 1px solid var(--border); text-align: left; }
th { background: var(--code-bg); font-weight: 600; }

/* i18n: every translatable block is emitted twice (EN + PT) inline.
   JS toggles the `hidden` attribute via applyLang(). The browser's
   built-in `[hidden] { display: none }` does the hiding; we only need
   to set layout shape for non-hidden elements (spans stay inline, block-
   content divs go block). */
.i18n[data-block="1"] { display: block; }
.i18n[data-lang="pt"][hidden],
.i18n[data-lang="en"][hidden] { display: none !important; }

/* Language switcher */
.lang-pill {
  position: relative;
  display: inline-block;
  margin-left: auto;
  font-size: 0.85rem;
}
.lang-pill-btn {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.3rem 0.7rem;
  cursor: pointer;
  font: inherit;
  color: var(--fg);
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}
.lang-pill-btn:hover { background: var(--code-bg); }
.lang-pill-label { line-height: 1; }
.lang-menu {
  position: absolute;
  top: calc(100% + 0.4rem);
  right: 0;
  min-width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  list-style: none;
  margin: 0;
  padding: 0.25rem;
  z-index: 100;
}
.lang-menu li { margin: 0; padding: 0; }
.lang-menu button {
  background: transparent;
  border: none;
  border-radius: 4px;
  padding: 0.4rem 0.7rem;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: var(--fg);
}
.lang-menu button:hover { background: var(--code-bg); }
.lang-menu button.active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}
.page-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}
.page-bar .crumbs { flex: 1; }

.toc {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.9rem 1.1rem;
  margin: 1.2rem 0;
  box-shadow: var(--shadow);
}
.toc h2 { margin: 0 0 0.5rem; border: none; padding: 0; font-size: 1.05rem; }

/* Locations — minimal card grid. One card per location. Just header
   (emoji + name + objectives counter), progress bar, and a small
   meta line with the quest count breakdown. No per-quest badges in the
   TOC — those live in the per-location sections below, which is where
   the live localStorage counter actually operates. */
.loc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.5rem;
}
.loc-card {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.5rem 0.7rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.loc-card-head {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  text-decoration: none;
  color: inherit;
}
.loc-card-head:hover .loc-name { color: var(--accent); }
.loc-emoji { font-size: 1.1rem; line-height: 1; }
.loc-name { font-weight: 600; flex: 1; transition: color 0.1s; }
.loc-counter {
  font-family: ui-monospace, monospace;
  font-size: 0.85rem;
  color: var(--fg-muted);
}
.loc-bar {
  height: 5px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}
.loc-bar-fill {
  height: 100%;
  background: var(--ok);
  transition: width 0.25s;
}
.loc-meta {
  font-size: 0.78rem;
  color: var(--fg-muted);
}

.summary-bar {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.7rem 1rem;
  margin: 1rem 0;
  box-shadow: var(--shadow);
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem 1.2rem;
  align-items: center;
}
.summary-bar .stat { display: flex; flex-direction: column; min-width: 0; }
.summary-bar .stat .label { font-size: 0.65rem; color: var(--fg-muted); text-transform: uppercase; letter-spacing: 0.06em; white-space: nowrap; }
.summary-bar .stat .value { font-size: 1.25rem; font-weight: 700; color: var(--fg); }
.summary-bar button {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.35rem 0.7rem;
  cursor: pointer;
  font-size: 0.8rem;
  white-space: nowrap;
}
.summary-bar button:hover { background: var(--code-bg); }
.summary-bar-actions { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-left: auto; }

/* ===== Homepage: hero, progress, stage card grid, quick links ===== */
.hero {
  text-align: center;
  padding: 2.5rem 1rem 1.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--border);
}
.hero h1 {
  margin: 0 0 0.4rem;
  font-size: 2.2rem;
  letter-spacing: -0.02em;
}
.hero-tagline {
  font-size: 1.05rem;
  color: var(--fg-muted);
  margin: 0 auto 1.5rem;
  max-width: 32em;
}
.progress { max-width: 28em; margin: 0 auto; }
.progress-track {
  background: var(--border);
  border-radius: 999px;
  height: 8px;
  overflow: hidden;
}
.progress-fill {
  background: var(--accent);
  height: 100%;
  width: 0%;
  transition: width 0.25s ease-out;
  border-radius: 999px;
}
.progress-text {
  font-size: 0.85rem;
  color: var(--fg-muted);
  margin-top: 0.4rem;
  font-family: ui-monospace, monospace;
  text-align: center;
}

.stage-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
  margin: 1.5rem 0;
}
.stage-card {
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1rem 1.1rem;
  text-decoration: none;
  color: var(--fg);
  transition: transform 0.12s, box-shadow 0.12s, border-color 0.12s;
}
.stage-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  text-decoration: none;
}
.stage-card header {
  margin-bottom: 0.4rem;
}
.stage-num {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.22rem 0.55rem;
  background: var(--accent-soft);
  color: var(--accent);
  border-radius: 999px;
}
.stage-card h2 {
  margin: 0.4rem 0 0.2rem;
  padding: 0;
  border: none;
  font-size: 1.15rem;
}
.stage-region {
  font-size: 0.85rem;
  color: var(--fg-muted);
  margin: 0 0 0.4rem;
}
.stage-objective {
  font-size: 0.95rem;
  margin: 0.4rem 0 0.8rem;
  flex: 1;
  line-height: 1.45;
}
.stage-card footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 0.6rem;
  border-top: 1px solid var(--border);
}
.stage-counts {
  font-size: 0.85rem;
  color: var(--fg-muted);
}
.stage-cta {
  font-weight: 600;
  color: var(--accent);
  white-space: nowrap;
}

.quick-links {
  margin: 2rem 0 1rem;
  padding: 0.8rem 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 0.95rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}
.quick-links strong { margin-right: 0.3rem; }
.quick-links .dot { color: var(--fg-muted); }
.reset-link {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.22rem 0.7rem;
  cursor: pointer;
  font: inherit;
  color: var(--fg);
  margin-left: 0.2rem;
}
.reset-link:hover { background: var(--code-bg); }

.page-footer {
  margin-top: 2.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  font-size: 0.85rem;
  color: var(--fg-muted);
  text-align: center;
}
.page-footer a { color: var(--fg-muted); text-decoration: underline; }

/* ----- import modal (built imperatively by SHARED_JS) ----- */
.dd2-modal-back {
  position: fixed; inset: 0; z-index: 9000;
  background: rgba(0, 0, 0, 0.45);
  display: flex; align-items: center; justify-content: center;
  padding: 1rem;
}
.dd2-modal-back[hidden] { display: none; }
.dd2-modal {
  background: var(--bg-card);
  color: var(--fg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.4rem 1.6rem;
  max-width: 480px;
  width: 100%;
  box-shadow: 0 8px 32px rgba(0,0,0,0.25);
  font: inherit;
}
.dd2-modal h3 { margin: 0 0 0.6rem; font-size: 1.1rem; }
.dd2-modal p { margin: 0 0 1rem; line-height: 1.45; }
.dd2-modal-actions {
  display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: flex-end;
}
.dd2-modal-actions button {
  font: inherit; cursor: pointer;
  padding: 0.4rem 0.9rem;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--fg);
}
.dd2-modal-actions button:hover { background: var(--code-bg); }
.dd2-modal-actions button.primary { background: var(--accent); color: #1a1a1c; border-color: var(--accent); }
.dd2-modal-actions button.danger { background: #c62828; color: #fff; border-color: #c62828; }
.dd2-modal-actions button.primary:hover { filter: brightness(0.95); }

/* ----- objective divider (for multi-part quests) ----- */
.dd2-checklist li.obj-divider {
  list-style: none;
  margin: 0.8rem 0 0.3rem;
  padding: 0.3rem 0.5rem;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-radius: var(--radius);
  text-align: center;
}
.view-toggle { font-weight: 600; }
.view-toggle.active { background: var(--accent); color: #1a1a1c; border-color: var(--accent); }
.view-toggle-group { display: inline-flex; gap: 0.3rem; padding: 0.2rem; background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); }
.view-toggle-group .view-toggle { border: 0; padding: 0.25rem 0.6rem; font-size: 0.78rem; }
body.flow-view .by-location { display: none; }
body.flow-view .by-flow { display: block; }
body:not(.flow-view) .by-flow { display: none; }
.quest-nav {
  display: flex; justify-content: space-between; align-items: center;
  gap: 1rem; margin: 2rem 0 1rem; padding: 0.8rem 1rem;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius);
}
.quest-nav a { color: var(--accent); text-decoration: none; font-weight: 500; }
.quest-nav a:hover { text-decoration: underline; }
.quest-nav-prev { margin-right: auto; }
.quest-nav-next { margin-left: auto; }

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
  .quest-card.main .quest-type-label { background: rgba(25, 118, 210, 0.28); color: #64b5f6; }
  .quest-card.side .quest-type-label { background: rgba(192, 132, 0, 0.28); color: #ffb74d; }
  .quest-card > summary:hover { background: rgba(255,255,255,0.04); }
  .stage-card:hover { box-shadow: 0 4px 12px rgba(255,255,255,0.06); }
}
"""

SHARED_JS = r"""
(function () {
  "use strict";
  // v1 is the legacy flat shape: { "s1-main-01-1": true, ... }.
  // v2 wraps the data with a version + timestamp for future migrations.
  // On load: prefer v2; if absent, migrate v1 → v2 on the fly.
  // On save: always write v2. The v1 key is kept for one release as a
  // safety copy in case a user with a stale page hits save.
  const STORAGE_KEY_V1 = "dd2-tracker-v1";
  const STORAGE_KEY_V2 = "dd2-tracker-v2";
  const STORAGE_KEY = STORAGE_KEY_V2;  // current key
  const LANG_KEY = "dd2-lang";
  // Diagnostic banner is silent by default. Set DEBUG=true for ad-hoc
  // dev work, or append ?debug=1 to the URL to enable the banner
  // without rebuilding.
  const DEBUG = false;
  const debugEnabled = () => DEBUG ||
    (typeof location !== "undefined" &&
     new URLSearchParams(location.search).has("debug"));

  // ----- i18n: language toggle -----
  // Body class controls CSS visibility of <span class="i18n" data-lang="...">.
  // EN is default; everything in the page is rendered twice (en + pt inline
  // spans) and we swap which is visible by toggling body.lang-pt.
  const I18N = {
    en: { init: "Tracker initializing…", blocked: "localStorage BLOCKED in this browser/context. Progress will NOT persist.", active: "Tracker active: %n% checkboxes · %d% marked", saved: "Saved ✓ (%n% marked)", save_fail: "Failed to save localStorage: %msg%", load_fail: "Failed to read localStorage: %msg%", clear_fail: "Failed to clear localStorage: %msg%", reset: "Reset ✓ Reloading…", init_fail: "Init failed: %msg%", confirm_reset: "Reset ALL progress? This clears localStorage for this site.", export_btn: "⬇ Export JSON", import_btn: "⬆ Import JSON", import_modal_title: "Import progress", import_summary: "File contains %total% checked objective(s): %matched% match this build, %unknown% are from other stages or unknown.", import_action_merge: "Merge with current", import_action_replace: "Replace everything", import_action_cancel: "Cancel", import_merged: "Merged %n% objective(s).", import_replaced: "Replaced progress with %n% objective(s).", import_invalid: "Invalid file: not a DD2 progress JSON.", import_blocked: "localStorage is blocked; import cannot persist." },
    pt: { init: "Tracker inicializando…", blocked: "localStorage BLOQUEADO neste browser/contexto. Progresso não vai persistir.", active: "Tracker ativo: %n% checkboxes · %d% marcados", saved: "Salvo ✓ (%n% marcados)", save_fail: "Erro salvando localStorage: %msg%", load_fail: "Erro lendo localStorage: %msg%", clear_fail: "Erro limpando localStorage: %msg%", reset: "Resetado ✓ Recarregando…", init_fail: "Init falhou: %msg%", confirm_reset: "Resetar TODO o progresso? Isso limpa o localStorage deste site.", export_btn: "⬇ Exportar JSON", import_btn: "⬆ Importar JSON", import_modal_title: "Importar progresso", import_summary: "O arquivo contém %total% objetivo(s) marcado(s): %matched% deste build, %unknown% de outros stages ou desconhecidos.", import_action_merge: "Mesclar com o atual", import_action_replace: "Substituir tudo", import_action_cancel: "Cancelar", import_merged: "Mesclado(s) %n% objetivo(s).", import_replaced: "Progresso substituído por %n% objetivo(s).", import_invalid: "Arquivo inválido: não é um JSON de progresso do DD2.", import_blocked: "localStorage está bloqueado; o import não vai persistir." },
  };

  function getLang() {
    let lang = "en";
    try { lang = localStorage.getItem(LANG_KEY) || "en"; } catch (e) {}
    return (lang === "pt") ? "pt" : "en";
  }
  function tpl(str) { return str; }  // placeholder for any future templating
  function i18nFmt(key, vars) {
    let lang = getLang();
    let tmpl = (I18N[lang] && I18N[lang][key]) || key;
    Object.keys(vars || {}).forEach((k) => {
      tmpl = tmpl.split("%" + k + "%").join(vars[k]);
    });
    return tmpl;
  }

  function applyLang(lang) {
    document.documentElement.lang = lang;
    document.body.classList.toggle("lang-pt", lang === "pt");
    document.body.classList.toggle("lang-en", lang === "en");
    // Toggle the `hidden` attribute on every i18n block. More robust than
    // CSS rules depending on body class + specificity: the browser's own
    // `[hidden] { display: none }` does the hiding, and our CSS only
    // distinguishes inline vs block display wrapping.
    document.querySelectorAll(".i18n[data-lang]").forEach((el) => {
      el.hidden = (el.dataset.lang !== lang);
    });

    // Update the dropdown pill label and the active item highlight
    const cur = document.getElementById("dd2-lang-current");
    if (cur) cur.textContent = lang === "pt" ? "PT" : "EN";
    document.querySelectorAll(".lang-menu [data-set-lang]").forEach((b) => {
      b.classList.toggle("active", b.dataset.setLang === lang);
    });

    // Show/hide the matching reset/export/import buttons (we render two of each, one per lang)
    const enBtns = ["reset-tracker", "export-tracker", "import-tracker"];
    const ptBtns = ["reset-tracker-pt", "export-tracker-pt", "import-tracker-pt"];
    enBtns.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.style.display = (lang === "en") ? "" : "none";
    });
    ptBtns.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.style.display = (lang === "pt") ? "" : "none";
    });

    // Re-render homepage progress text in the new language ("X / N sub-objectives" / "sub-objetivos").
    if (typeof updateGlobalProgress === "function") updateGlobalProgress();
  }

  function closeLangMenu() {
    const menu = document.querySelector(".lang-menu");
    const btn  = document.querySelector(".lang-pill-btn");
    if (!menu || !btn) return;
    menu.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  }

  function openLangMenu() {
    const menu = document.querySelector(".lang-menu");
    const btn  = document.querySelector(".lang-pill-btn");
    if (!menu || !btn) return;
    menu.hidden = false;
    btn.setAttribute("aria-expanded", "true");
  }

  function initLang() {
    const lang = getLang();
    applyLang(lang);
    const pill = document.querySelector(".lang-pill-btn");
    if (pill) {
      pill.addEventListener("click", (e) => {
        e.stopPropagation();
        const menu = document.querySelector(".lang-menu");
        if (menu && menu.hidden) openLangMenu(); else closeLangMenu();
      });
    }
    document.querySelectorAll(".lang-menu [data-set-lang]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const wanted = btn.dataset.setLang;
        if (!wanted) return;
        try { localStorage.setItem(LANG_KEY, wanted); } catch (err) {}
        applyLang(wanted);
        closeLangMenu();
      });
    });
    // Close on outside click / Escape
    document.addEventListener("click", () => closeLangMenu());
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeLangMenu();
    });
  }

  // ----- diagnostic banner (visible feedback) -----
  let diagTimer = null;
  function showDiag(msg, level, autoHideMs) {
    if (!debugEnabled()) return;
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
  // Storage shape (v2):
  //   { "version": 2, "updatedAt": ISO-timestamp, "checked": { id: true, ... } }
  // v1 (legacy flat { id: true, ... }) is auto-migrated on first read and
  // a copy is left in the v1 key for one release as a safety net.

  function emptyState() {
    return { version: 2, updatedAt: new Date().toISOString(), checked: {} };
  }

  function loadState() {
    // Prefer v2; fall back to v1 with on-the-fly migration.
    try {
      const rawV2 = localStorage.getItem(STORAGE_KEY_V2);
      if (rawV2) {
        const parsed = JSON.parse(rawV2);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)
            && parsed.version === 2 && parsed.checked
            && typeof parsed.checked === "object" && !Array.isArray(parsed.checked)) {
          // Strip values that aren't strictly true; unknown keys stay
          // (they don't break anything and the user can re-import clean
          // data via Import).
          return parsed;
        }
        // v2 payload is malformed — quarantine it and start fresh.
        try { localStorage.setItem(STORAGE_KEY_V2 + ".corrupt-" + Date.now(), rawV2); } catch (_) {}
        try { localStorage.removeItem(STORAGE_KEY_V2); } catch (_) {}
      }
      // Try legacy v1.
      const rawV1 = localStorage.getItem(STORAGE_KEY_V1);
      if (rawV1) {
        const parsedV1 = JSON.parse(rawV1);
        if (parsedV1 && typeof parsedV1 === "object" && !Array.isArray(parsedV1)) {
          // Migrate: wrap v1's flat shape into v2. v1 stays in localStorage
          // for one release as a safety copy.
          const migrated = emptyState();
          Object.keys(parsedV1).forEach((k) => {
            if (parsedV1[k] === true) migrated.checked[k] = true;
          });
          return migrated;
        }
        // v1 is corrupt too — quarantine.
        try { localStorage.setItem(STORAGE_KEY_V1 + ".corrupt-" + Date.now(), rawV1); } catch (_) {}
        try { localStorage.removeItem(STORAGE_KEY_V1); } catch (_) {}
      }
      return emptyState();
    } catch (e) {
      showDiag(i18nFmt("load_fail", { msg: e.message }), "err");
      return emptyState();
    }
  }

  function saveState(state) {
    try {
      // Always write a fully-formed v2 object so future code can rely on
      // the shape without re-validating.
      const toSave = {
        version: 2,
        updatedAt: new Date().toISOString(),
        checked: (state && state.checked) ? state.checked : {},
      };
      localStorage.setItem(STORAGE_KEY_V2, JSON.stringify(toSave));
      const n = Object.values(toSave.checked).filter(Boolean).length;
      showDiag(i18nFmt("saved", { n: String(n) }), "ok", 1200);
      return true;
    } catch (e) {
      showDiag(i18nFmt("save_fail", { msg: e.message }), "err");
      return false;
    }
  }

  function clearAll() {
    try {
      localStorage.removeItem(STORAGE_KEY_V2);
      // Drop the legacy v1 too, so a user who resets and then re-imports
      // a v1 file doesn't get surprised by phantom IDs.
      try { localStorage.removeItem(STORAGE_KEY_V1); } catch (_) {}
      return true;
    } catch (e) {
      showDiag(i18nFmt("clear_fail", { msg: e.message }), "err");
      return false;
    }
  }

  // Return the current known tracker IDs from the current page DOM
  // (or, on the homepage, from a build-time data-known-ids attribute).
  function currentKnownIds() {
    const fromAttr = document.querySelector("[data-known-ids]");
    if (fromAttr) {
      try { return new Set(JSON.parse(fromAttr.getAttribute("data-known-ids") || "[]")); }
      catch (_) { return new Set(); }
    }
    const set = new Set();
    document.querySelectorAll("input[type=checkbox][data-track-id]").forEach((cb) => {
      const id = cb.getAttribute("data-track-id");
      if (id) set.add(id);
    });
    return set;
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

  // ----- per-card master checkbox sync -----
  // Computes the master's checked/indeterminate state from the
  // visible children inside its card and writes it back to the DOM
  // without firing a change event (so we don't loop).
  function syncMaster(card) {
    if (!card) return;
    const master = card.querySelector(":scope > summary > input.quest-master");
    if (!master) return;
    const children = card.querySelectorAll("input[type=checkbox][data-track-id]");
    if (children.length === 0) {
      master.checked = false;
      master.indeterminate = false;
      return;
    }
    let done = 0;
    children.forEach((c) => { if (c.checked) done += 1; });
    master.checked = done === children.length;
    master.indeterminate = done > 0 && done < children.length;
  }
  function syncAllMasters() {
    document.querySelectorAll("details.quest-card").forEach(syncMaster);
  }

  function updateTotals() {
    // Re-sync master checkboxes in case totals moved
    syncAllMasters();

    // Per-quest badges: text and class are recomputed from current
    // checkbox state (which already reflects localStorage). This means
    // the build-time label ("✅ 6/6" from MDs with `- [x]`) gets
    // overwritten on every page load, after every checkbox change, and
    // after reset — so the badges are always in sync with reality.
    document.querySelectorAll("[data-quest-count-for]").forEach((el) => {
      const prefix = el.getAttribute("data-quest-count-for");
      let done = 0, total = 0;
      document.querySelectorAll("input[type=checkbox][data-track-id]").forEach((cb) => {
        if ((cb.getAttribute("data-track-id") || "").startsWith(prefix)) {
          total += 1;
          if (cb.checked) done += 1;
        }
      });
      if (total === 0) {
        el.textContent = "Sem objetivos";
        el.className = "badge";
      } else if (done === 0) {
        el.textContent = "0/" + total;
        el.className = "badge pending";
      } else if (done === total) {
        el.textContent = "✓ " + done + "/" + total;
        el.className = "badge ok";
      } else {
        const pct = Math.round(100 * done / total);
        el.textContent = done + "/" + total + " (" + pct + "%)";
        el.className = "badge warn";
      }
    });

    // Stage-level summary (e.g. "12/39 sub-objetivos")
    document.querySelectorAll("[data-total-for]").forEach((el) => {
      const prefix = el.getAttribute("data-total-for");
      let done = 0, total = 0;
      document.querySelectorAll("input[type=checkbox][data-track-id]").forEach((cb) => {
        if ((cb.getAttribute("data-track-id") || "").startsWith(prefix)) {
          total += 1;
          if (cb.checked) done += 1;
        }
      });
      el.textContent = total === 0 ? "—" : done + "/" + total;
    });
  }

  // ----- global progress (homepage only) -----
  // Reads the build-time `data-total` attribute and live-counts checked
  // track-ids from localStorage. Falls back gracefully if either piece
  // is missing (e.g. on stage pages, no-op).
  function updateGlobalProgress() {
    const text = document.querySelector("[data-progress-text=\"global\"]");
    const fill = document.querySelector("[data-progress-fill=\"global\"]");
    if (!text && !fill) return;
    const total = parseInt((text && text.getAttribute("data-total")) || "0", 10) || 0;
    let done = 0;
    try {
      const raw = localStorage.getItem(STORAGE_KEY_V2) || localStorage.getItem(STORAGE_KEY_V1);
      if (raw) {
        const parsed = JSON.parse(raw);
        // Accept both v2 (wrapped) and v1 (flat) shapes.
        let checked = null;
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          if (parsed.version === 2 && parsed.checked && typeof parsed.checked === "object") {
            checked = parsed.checked;
          } else {
            // Treat as v1: every key with a truthy value counts.
            checked = parsed;
          }
        }
        if (checked) {
          // Count only IDs that the current build knows about, to avoid
          // overcounting from stale or imported keys.
          const known = currentKnownIds();
          done = Object.keys(checked).filter((k) => checked[k] === true && known.has(k)).length;
        }
      }
    } catch (e) { /* ignore */ }
    const pct = total > 0 ? Math.min(100, Math.round((100 * done) / total)) : 0;
    if (fill) fill.style.width = pct + "%";
    if (text) {
      const lang = getLang();
      text.textContent = (lang === "pt")
        ? `${done} / ${total} sub-objetivos`
        : `${done} / ${total} sub-objectives`;
    }
  }

  // ----- export / import JSON -----
  // "Export" writes the current tracker payload to a downloadable .json
  // file (date-stamped). "Import" opens a hidden file input, parses the
  // chosen file, and shows a non-native modal with Cancel / Merge / Replace
  // actions. Merge keeps the current state for matching IDs and adds the
  // imported ones; Replace overwrites everything.
  //
  // The modal is built imperatively (no extra HTML in the page) and uses
  // the same `i18n` data-lang swap as the rest of the page so its
  // labels flip with the language pill.
  function buildModal() {
    const back = document.createElement("div");
    back.id = "dd2-import-modal";
    back.className = "dd2-modal-back";
    back.hidden = true;
    back.innerHTML = `
      <div class="dd2-modal" role="dialog" aria-modal="true" aria-labelledby="dd2-import-title">
        <h3 id="dd2-import-title" class="i18n" data-lang="en">${htmlEscape(i18nFmt("import_modal_title", {}))}</h3>
        <h3 class="i18n" data-lang="pt" hidden>${htmlEscape(i18nFmt("import_modal_title", {}))}</h3>
        <p id="dd2-import-summary" class="i18n" data-lang="en"></p>
        <p id="dd2-import-summary-pt" class="i18n" data-lang="pt" hidden></p>
        <div class="dd2-modal-actions">
          <button type="button" data-import-action="cancel" class="i18n" data-lang="en">${htmlEscape(i18nFmt("import_action_cancel", {}))}</button>
          <button type="button" data-import-action="cancel-pt" class="i18n" data-lang="pt" hidden>${htmlEscape(i18nFmt("import_action_cancel", {}))}</button>
          <button type="button" data-import-action="merge" class="primary i18n" data-lang="en">${htmlEscape(i18nFmt("import_action_merge", {}))}</button>
          <button type="button" data-import-action="merge-pt" class="primary i18n" data-lang="pt" hidden>${htmlEscape(i18nFmt("import_action_merge", {}))}</button>
          <button type="button" data-import-action="replace" class="danger i18n" data-lang="en">${htmlEscape(i18nFmt("import_action_replace", {}))}</button>
          <button type="button" data-import-action="replace-pt" class="danger i18n" data-lang="pt" hidden>${htmlEscape(i18nFmt("import_action_replace", {}))}</button>
        </div>
      </div>
    `;
    document.body.appendChild(back);
    return back;
  }

  function htmlEscape(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function bindExportImport() {
    // Export buttons (one per language; only the active one is shown by applyLang).
    ["export-tracker", "export-tracker-pt"].forEach((id) => {
      const btn = document.getElementById(id);
      if (!btn) return;
      btn.addEventListener("click", () => {
        try {
          const state = loadState();
          const exportObj = {
            version: 2,
            exportedAt: new Date().toISOString(),
            checked: state.checked || {},
          };
          const blob = new Blob([JSON.stringify(exportObj, null, 2)], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          const stamp = new Date().toISOString().slice(0, 10);
          a.href = url;
          a.download = "dd2-progress-" + stamp + ".json";
          document.body.appendChild(a);
          a.click();
          setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 0);
        } catch (err) {
          showDiag(i18nFmt("save_fail", { msg: err.message }), "err");
        }
      });
    });

    // Import: a single hidden file input + a single click handler on the
    // (per-language) import button. The button just clicks the input.
    const fileInput = document.getElementById("dd2-import-file");
    ["import-tracker", "import-tracker-pt"].forEach((id) => {
      const btn = document.getElementById(id);
      if (!btn) return;
      btn.addEventListener("click", () => { if (fileInput) fileInput.click(); });
    });
    if (!fileInput) return;
    fileInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        let parsed = null;
        try { parsed = JSON.parse(reader.result); }
        catch (err) { showDiag(i18nFmt("import_invalid", {}), "err"); fileInput.value = ""; return; }

        // Accept either v2 wrapped or v1 flat shape; normalize to a flat map.
        let incoming = {};
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          if (parsed.version === 2 && parsed.checked && typeof parsed.checked === "object" && !Array.isArray(parsed.checked)) {
            incoming = parsed.checked;
          } else {
            // Treat as v1: keep only keys whose value is strictly true.
            Object.keys(parsed).forEach((k) => { if (parsed[k] === true) incoming[k] = true; });
          }
        } else {
          showDiag(i18nFmt("import_invalid", {}), "err");
          fileInput.value = "";
          return;
        }

        const known = currentKnownIds();
        let matched = 0, unknown = 0;
        Object.keys(incoming).forEach((k) => {
          if (known.has(k)) matched++;
          else unknown++;
        });
        const total = matched + unknown;

        // Persist a staging copy so the modal can read the proposed payload
        // regardless of which action the user picks.
        window.__dd2PendingImport = incoming;
        showImportModal(total, matched, unknown, fileInput);
      };
      reader.onerror = () => {
        showDiag(i18nFmt("load_fail", { msg: reader.error ? reader.error.message : "" }), "err");
        fileInput.value = "";
      };
      reader.readAsText(file);
    });
  }

  function showImportModal(total, matched, unknown, fileInput) {
    let back = document.getElementById("dd2-import-modal");
    if (!back) back = buildModal();
    back.hidden = false;
    const summaryEn = document.getElementById("dd2-import-summary");
    const summaryPt = document.getElementById("dd2-import-summary-pt");
    const sEn = i18nFmt("import_summary", { total: String(total), matched: String(matched), unknown: String(unknown) });
    const sPt = i18nFmt("import_summary", { total: String(total), matched: String(matched), unknown: String(unknown) });
    if (summaryEn) summaryEn.textContent = sEn;
    if (summaryPt) summaryPt.textContent = sPt;

    const close = () => {
      back.hidden = true;
      if (fileInput) fileInput.value = "";
      window.__dd2PendingImport = null;
    };
    const onAction = (e) => {
      const t = e.target;
      if (!(t instanceof HTMLElement)) return;
      const a = t.getAttribute("data-import-action") || "";
      const incoming = window.__dd2PendingImport || {};
      const current = loadState();
      const cur = current.checked || (current.checked = {});
      if (a === "cancel" || a === "cancel-pt") {
        close();
        return;
      }
      if (a === "merge" || a === "merge-pt") {
        // Additive merge: current state wins for conflicting keys, but
        // we also add keys from `incoming` that are missing locally.
        // Net effect: the union, with the current tab's choices preserved.
        let added = 0;
        Object.keys(incoming).forEach((k) => {
          if (incoming[k] === true && !cur[k]) { cur[k] = true; added++; }
        });
        saveState(current);
        showDiag(i18nFmt("import_merged", { n: String(added) }), "ok", 1500);
      } else if (a === "replace" || a === "replace-pt") {
        // Replace: drop everything and re-apply the imported set as-is.
        const next = { version: 2, updatedAt: new Date().toISOString(), checked: {} };
        Object.keys(incoming).forEach((k) => { if (incoming[k] === true) next.checked[k] = true; });
        saveState(next);
        showDiag(i18nFmt("import_replaced", { n: String(Object.keys(next.checked).length) }), "ok", 1500);
      }
      close();
      // Re-apply state to DOM and refresh every counter.
      const items = document.querySelectorAll("input[type=checkbox][data-track-id]");
      items.forEach((cb) => applyTo(cb, next ? next.checked : current.checked));
      updateTotals();
      updateGlobalProgress();
    };
    // Use one delegated listener; replace it on each open to avoid stacking.
    if (back.__handler) back.removeEventListener("click", back.__handler);
    back.__handler = onAction;
    back.addEventListener("click", onAction);
  }

  // ----- view toggle (stage pages) -----
  // The stage page renders TWO views in the DOM: a per-location view
  // (default) and a "by recommended flow" view (a flat list in the
  // order defined by the Stage MOC). This function wires up the
  // .view-toggle buttons in the summary bar to swap between them by
  // toggling a `flow-view` class on <body>; the CSS in SHARED_CSS
  // does the actual show/hide.
  function bindViewToggle() {
    const toggles = document.querySelectorAll(".view-toggle");
    if (toggles.length === 0) return;
    toggles.forEach((btn) => {
      btn.addEventListener("click", () => {
        const view = btn.getAttribute("data-view");
        if (view === "flow") document.body.classList.add("flow-view");
        else document.body.classList.remove("flow-view");
        toggles.forEach((t) => t.classList.toggle("active", t === btn));
      });
    });
  }

  // ----- main -----
  function init() {
    // Run language toggle first so diag messages / reset confirm land
    // in the user's preferred language for the rest of init.
    try { initLang(); } catch (e) { /* non-fatal */ }

    if (debugEnabled()) showDiag(i18nFmt("init", {}), "info");

    // Verify localStorage is usable
    try {
      localStorage.setItem("__dd2_probe", "1");
      localStorage.removeItem("__dd2_probe");
    } catch (e) {
      showDiag(i18nFmt("blocked", {}), "err");
      return;
    }

    const state = loadState();
    const checkedMap = state.checked || {};
    const items = document.querySelectorAll("input[type=checkbox][data-track-id]");
    items.forEach((cb) => applyTo(cb, checkedMap));
    updateTotals();
    updateGlobalProgress();

    const doneCount = Object.values(checkedMap).filter(Boolean).length;
    if (debugEnabled()) showDiag(
      i18nFmt("active", { n: String(items.length), d: String(doneCount) }),
      "ok", 2000
    );

    // Event delegation — one listener on document catches all checkbox toggles
    document.addEventListener("change", (e) => {
      const t = e.target;
      if (!(t instanceof HTMLInputElement)) return;
      if (t.type !== "checkbox") return;

      // Master checkbox: toggle every child inside the same card.
      // We handle propagation in the inline onclick on the master
      // so the summary click doesn't ALSO collapse/expand the card.
      if (t.classList.contains("quest-master")) {
        const card = t.closest("details.quest-card");
        if (!card) return;
        const want = t.checked;
        const children = card.querySelectorAll("input[type=checkbox][data-track-id]");
        const s = loadState();
        const m = s.checked || (s.checked = {});
        let dirty = false;
        children.forEach((cb) => {
          if (cb.checked === want) return;
          cb.checked = want;
          cb.closest("li")?.classList.toggle("is-checked", want);
          const cid = cb.getAttribute("data-track-id");
          if (cid) {
            if (want) m[cid] = true;
            else delete m[cid];
            dirty = true;
          }
        });
        if (dirty) { saveState(s); updateTotals(); }
        else { syncMaster(card); }
        return;
      }

      // Regular tracked objective
      const id = t.getAttribute("data-track-id");
      if (!id) return;
      const s = loadState();
      const m = s.checked || (s.checked = {});
      if (t.checked) m[id] = true;
      else delete m[id];
      t.closest("li")?.classList.toggle("is-checked", t.checked);
      const ok = saveState(s);
      if (ok) updateTotals();
    });

    // Reset buttons: there are two (id="reset-tracker" English,
    // id="reset-tracker-pt" Portuguese). The active one is shown by
    // applyLang(); both share the same logic. The homepage renders
    // reset-tracker-home as a single pill in the quick-links section.
    ["reset-tracker", "reset-tracker-pt", "reset-tracker-home"].forEach((id) => {
      const btn = document.getElementById(id);
      if (!btn) return;
      btn.addEventListener("click", () => {
        if (confirm(i18nFmt("confirm_reset", {}))) {
          if (clearAll()) {
            showDiag(i18nFmt("reset", {}), "ok");
            setTimeout(() => location.reload(), 400);
          }
        }
      });
    });

    // ----- export / import JSON -----
    // The "Export" button writes the current localStorage payload to a
    // downloadable .json file. The "Import" button opens a hidden file
    // picker; once a file is chosen, a non-native modal asks the user
    // whether to merge with the current state or replace it outright.
    bindExportImport();

    // View toggle: "By location" / "By recommended flow" buttons in the
    // summary bar. Adds a body class that CSS uses to swap the per-location
    // sections for a flat list ordered by the Stage MOC.
    bindViewToggle();

    // Cross-tab sync: when another tab writes to the tracker key, re-apply
    // the new value to this tab's DOM. The storage event is fired in
    // OTHER tabs only (not the one that wrote), so this is safe to call
    // on every change.
    window.addEventListener("storage", (e) => {
      if (e.key === STORAGE_KEY_V2 || e.key === STORAGE_KEY_V1) {
        const s = loadState();
        const items = document.querySelectorAll("input[type=checkbox][data-track-id]");
        items.forEach((cb) => applyTo(cb, s.checked));
        updateTotals();
        updateGlobalProgress();
      }
    });
  }

  // Robust initialization
  function boot() {
    try { init(); }
    catch (e) { showDiag(i18nFmt("init_fail", { msg: e.message }), "err"); }
  }

  // Set <html lang> synchronously, before first paint, so search engines
  // and screen readers see the correct language from the first frame.
  // (The body is not yet available here, so this is intentionally a
  // minimal version of applyLang — the full version runs in init().)
  try {
    document.documentElement.lang = getLang();
  } catch (e) { /* no-op */ }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    setTimeout(boot, 0);
  }
})();
"""


def page_shell(*, title: str, body_html: str, crumbs_html: str = "", extra_css: str = "",
               crumbs_safe: bool = False, crumbs_home_href: str = "index.html") -> str:
    # Dropdown lang switcher: single pill button (current lang) + a
    # hidden menu listing both options. JS in SHARED_JS handles toggling,
    # selection, and click-outside-to-close.
    lang_switcher = (
        '<div class="lang-pill">'
          '<button class="lang-pill-btn" type="button" aria-haspopup="true" aria-expanded="false">'
            '<span class="lang-pill-label">🌐 <span id="dd2-lang-current">EN</span> ▾</span>'
          '</button>'
          '<ul class="lang-menu" role="menu" hidden>'
            f'<li role="none"><button type="button" role="menuitem" data-set-lang="en">🌐 English</button></li>'
            f'<li role="none"><button type="button" role="menuitem" data-set-lang="pt">🌐 Português</button></li>'
          '</ul>'
        '</div>'
    )
    page_bar = f'<div class="page-bar">{nav_crumbs(crumbs_html, home_href=crumbs_home_href, safe=crumbs_safe)}{lang_switcher}</div>\n' if crumbs_html else lang_switcher
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Dragon's Dogma 2 Walkthrough</title>
<meta name="description" content="Walkthrough e checklist interativo de Dragon's Dogma 2">
<style>{SHARED_CSS}{extra_css}</style>
</head>
<body>
<main>
{page_bar}
{body_html}
</main>
<!-- Hidden file picker used by the "Import JSON" buttons rendered on
     every page. The picker is duplicated for each stage so it lives
     outside the summary bar (which gets remounted on language toggle). -->
<input type="file" id="dd2-import-file" accept="application/json,.json" hidden>
<script>{SHARED_JS}</script>
</body>
</html>
"""


def nav_crumbs(inner_html: str, *, home_href: str = "index.html", safe: bool = False) -> str:
    """Render a bilingual breadcrumb.

    EN and PT both show the full chain `Home › {inner_html}`. The page
    name (e.g., "Stage 1") comes from `inner_html` — typically the
    current page's section label. On per-quest pages, the caller can
    pass safe=True to inject pre-built HTML with clickable links to
    the stage and sub-folder (the default html.escape would otherwise
    mangle the `<a>` tags).

    `home_href` lets per-quest pages point back to the site root with
    the right relative path (e.g. "../../../index.html").

    Each text segment is wrapped in `<span class="i18n"
    data-lang="…">` so JS (or CSS) can swap visibility per language.
    The Home link itself is bilingual so the entire breadcrumb feels
    coherent in either language.
    """
    if not inner_html:
        return ""
    suffix_en = inner_html if safe else html.escape(inner_html)
    suffix_pt = inner_html if safe else html.escape(inner_html)
    return (
        '<nav class="crumbs">'
        # Home link, bilingual
        f'<a href="{html.escape(home_href)}" class="i18n" data-lang="en">{html.escape(L("en", "page_title_home"))}</a>'
        f'<a href="{html.escape(home_href)}" class="i18n" data-lang="pt" hidden>{html.escape(L("pt", "page_title_home"))}</a>'
        # › <inner_html> suffix, bilingual
        f'<span class="i18n" data-lang="en"> &rsaquo; {suffix_en}</span>'
        f'<span class="i18n" data-lang="pt" hidden> &rsaquo; {suffix_pt}</span>'
        '</nav>\n'
    )


def status_badge(status: str, prefix: str = "") -> str:
    """Render a quest status badge.

    If `prefix` is given (e.g. "s1-main-01"), the badge receives a
    `data-quest-count-for` attribute so the inline JS can overwrite the
    label AND class with live counts from localStorage on every page
    load and every checkbox change. Without `prefix`, the badge is
    fully static (used for places like the per-quest page header where
    the page only shows one quest and a static label is fine).
    """
    if "✅" in status:
        cls, label = "ok", status
    elif "⬜" in status:
        cls, label = "pending", status
    else:
        cls, label = "warn", status
    data_attr = f' data-quest-count-for="{html.escape(prefix)}"' if prefix else ""
    return f'<span class="badge {cls}"{data_attr}>{html.escape(label)}</span>'


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------

def render_index(repo_root: Path, stages: list[int]) -> str:
    """Generate dist/index.html — homepage with hero, stage card grid, quick links."""
    body: list[str] = []

    # === HERO ============================================================
    body.append('<section class="hero">')
    body.append('<h1>🐉 '
                '<span class="i18n" data-lang="en">Dragon\'s Dogma 2 Walkthrough</span>'
                '<span class="i18n" data-lang="pt" hidden>Dragon\'s Dogma 2 Walkthrough</span>'
                '</h1>')
    hero_tagline_en = "Interactive EN/PT walkthrough with progress tracker."
    hero_tagline_pt = "Walkthrough interativo EN/PT com tracker de progresso."
    body.append(f'<p class="hero-tagline">{render_bilingual(hero_tagline_en, hero_tagline_pt)}</p>')
    # Global progress bar — JS in SHARED_JS reads `data-total` for the
    # denominator and live-counts `localStorage[dd2-tracker-v2]` for the
    # numerator. The page has no checkboxes of its own, so this is the
    # only place global progress shows. The `data-known-ids` attribute
    # carries the full set of tracker IDs from the current build, so the
    # JS can ignore stale or imported IDs that no longer match anything
    # in the vault (and the progress bar can never exceed 100%).
    total_objectives, known_ids = _count_total_objectives(repo_root, stages)
    body.append('<div class="progress"'
                f' data-known-ids=\'{html.escape(json.dumps(sorted(known_ids), ensure_ascii=False))}\'>')
    body.append('  <div class="progress-track">')
    body.append('    <div class="progress-fill" data-progress-fill="global"></div>')
    body.append('  </div>')
    body.append('  <div class="progress-text">')
    body.append(f'    <span data-progress-text="global" data-total="{total_objectives}"></span>')
    body.append('  </div>')
    body.append('</div>')
    body.append('</section>')

    # === STAGE CARD GRID =================================================
    body.append('<section class="stage-grid">')
    for n in stages:
        si = load_stage_info(n, repo_root)
        if si is None:
            continue
        body.append(f'<a class="stage-card" href="stage-{n}.html" data-stage="{n}">')
        body.append(f'  <header><span class="stage-num">Stage {si.number}</span></header>')
        # Bilingual title — uses `name_en`/`name_pt` from the MOC frontmatter
        # (falling back to the single `name` field if those are absent).
        body.append(f'  <h2><span class="i18n" data-lang="en">{html.escape(si.name_en)}</span>'
                    f'<span class="i18n" data-lang="pt" hidden>{html.escape(si.name_pt)}</span></h2>')
        if si.region:
            body.append(f'  <p class="stage-region">{html.escape(si.region)}</p>')
        if si.objective:
            obj = si.objective
            if len(obj) > 140:
                obj = obj[:137] + "…"
            body.append(f'  <p class="stage-objective">{html.escape(obj)}</p>')
        # Footer: counts (left) + CTA (right)
        body.append('  <footer>')
        counts_en = L("en", "stage_card_main_fmt").format(n=si.main_count, s=si.side_count)
        counts_pt = L("pt", "stage_card_main_fmt").format(n=si.main_count, s=si.side_count)
        body.append(f'    <span class="stage-counts">{render_bilingual(counts_en, counts_pt)}</span>')
        body.append(f'    <span class="stage-cta">{render_bilingual(L("en", "stage_card_open"), L("pt", "stage_card_open"))}</span>')
        body.append('  </footer>')
        body.append('</a>')
    body.append('</section>')

    # === QUICK LINKS =====================================================
    body.append('<section class="quick-links">')
    body.append(f'  <strong>{render_bilingual(L("en", "quick_links_label"), L("pt", "quick_links_label"))}</strong>')
    body.append(f'  <a href="stage-1.html">{render_bilingual(L("en", "quick_link_stage1"), L("pt", "quick_link_stage1"))}</a>')
    body.append('  <span class="dot">·</span>')
    # Browse locations: anchor to stage-1.html's locations TOC until a
    # dedicated page exists. The TOC is at #locations-list (rendered by
    # render_stage when it has locations; fall back to # for safety).
    body.append(f'  <a href="stage-1.html#locations">{render_bilingual(L("en", "quick_link_locations"), L("pt", "quick_link_locations"))}</a>')
    body.append('  <span class="dot">·</span>')
    body.append(f'  <button type="button" id="export-tracker" class="reset-link">'
                f'{render_bilingual(L("en", "quick_link_export"), L("pt", "quick_link_export"))}</button>')
    body.append('  <button type="button" id="export-tracker-pt" class="reset-link" style="display:none">'
                f'{render_bilingual(L("en", "quick_link_export"), L("pt", "quick_link_export"))}</button>')
    body.append(f'  <button type="button" id="import-tracker" class="reset-link">'
                f'{render_bilingual(L("en", "quick_link_import"), L("pt", "quick_link_import"))}</button>')
    body.append('  <button type="button" id="import-tracker-pt" class="reset-link" style="display:none">'
                f'{render_bilingual(L("en", "quick_link_import"), L("pt", "quick_link_import"))}</button>')
    body.append(f'  <button type="button" id="reset-tracker-home" class="reset-link">'
                f'{render_bilingual(L("en", "quick_link_reset"), L("pt", "quick_link_reset"))}</button>')
    body.append('</section>')

    # === FOOTER (discreet sources) =======================================
    body.append('<footer class="page-footer">')
    body.append('  <p>')
    body.append('    <span class="i18n" data-lang="en">Sources: </span>')
    body.append('    <span class="i18n" data-lang="pt" hidden>Fontes: </span>')
    body.append('    <a href="https://dragonsdogma2.wiki.fextralife.com/">Fextralife</a> · '
                '<a href="https://www.ign.com/wikis/dragons-dogma-2/">IGN</a> · '
                '<a href="https://dragonsdogma.fandom.com/wiki/Dragon%27s_Dogma_2_Wiki">Fandom</a>')
    body.append('  </p>')
    body.append('</footer>')

    return page_shell(title=L("en", "page_title_home"), body_html="\n".join(body))


def _count_total_objectives(repo_root: Path, stages: list[int]) -> tuple[int, list[str]]:
    """Sum objective counts across all stages for the global progress bar.

    Returns (total, known_ids). The known_ids list is the full set of
    `data-track-id` strings emitted by the build; it's used to filter
    storage on the homepage so stale or imported keys don't inflate the
    progress numerator.
    """
    total = 0
    known: list[str] = []
    for n in stages:
        stage_dir = repo_root / "Quests" / f"Stage {n}"
        for sub in ("Main Quests", "Side Quests"):
            sub_dir = stage_dir / sub
            if not sub_dir.exists():
                continue
            for path in sub_dir.glob("*.md"):
                if path.stem.endswith(".en"):  # only count one of the pair
                    continue
                fm, body_text = parse_frontmatter(path.read_text(encoding="utf-8"))
                qtype = "side" if "Side Quests" in str(path) else "main"
                num_match = re.match(r"^(\d+)", path.name)
                qnum = num_match.group(1) if num_match else "x"
                prefix = f"s{n}-{qtype}-{qnum}"
                for i, _ in enumerate(parse_objectives(body_text.splitlines()), start=1):
                    known.append(f"{prefix}-{i}")
                total += len(parse_objectives(body_text.splitlines()))
    return total, known


# ---------------------------------------------------------------------------
# Bilingual quest card helpers (called by render_stage / render_quest_detail)
# ---------------------------------------------------------------------------

def _type_label_pair(quest_type: str) -> tuple[str, str]:
    """(EN, PT) of the type-label HTML for the given quest type."""
    emoji_key = "type_emoji_main" if quest_type == "main" else "type_emoji_side"
    label_key = "type_label_main" if quest_type == "main" else "type_label_side"
    return (
        f'{L("en", emoji_key)} {L("en", label_key)}',
        f'{L("pt", emoji_key)} {L("pt", label_key)}',
    )


def _quest_card_inner(quest: Quest, lang: str) -> str:
    """Render the body section (between <summary> and </details>) in one language.

    The chrome (summary header) is shared between languages and is
    emitted by render_quest_block_bilingual; this only renders the
    per-language quest content. The objectives checklist is NOT rendered
    here — it's emitted once by render_quest_block_bilingual, outside
    the bilingual wrappers, so the page shows a single `<ul>` regardless
    of which language is active.
    """
    parts: list[str] = []
    parts.append(
        f'<p><small>'
        f'<span class="i18n" data-lang="en">Quest ID</span>'
        f'<span class="i18n" data-lang="pt" hidden>Quest ID</span>'
        f': <code>{quest.track_prefix}</code> · '
        f'<a href="{quest.url}">{html.escape(L(lang, "ver_detalhes"))}</a>'
        f'</small></p>'
    )
    if quest.summary:
        parts.append(render_md_block(quest.summary))
    else:
        # Even when summary is empty, signal "no objectives" placeholder
        # in the active language. The actual <ul> is rendered separately
        # outside the bilingual block; here we keep this branch for
        # parity with the per-quest detail renderer.
        pass
    return "\n".join(parts)


def render_quest_block_bilingual(q_en: Quest, q_pt: Quest, show_dividers: bool = False) -> str:
    """Render a quest as a colored, collapsible, bilingual card."""
    q_pt_fallback = q_en  # if q_pt missing, EN acts as fallback
    # Use PT quest for type (always present) and EN for chrome (fallback to PT).
    qt = q_pt or q_pt_fallback
    qe = q_en or q_pt_fallback
    type_en, type_pt = _type_label_pair(qt.quest_type)

    parts: list[str] = []
    parts.append(f'<details class="quest-card {qt.quest_type}">')
    parts.append('<summary>')
    parts.append('<span class="quest-card-caret" aria-hidden="true">▶</span>')
    if qt.objectives:
        title_for_aria = qe.title
        parts.append(
            '<input type="checkbox" class="quest-master" '
            f'aria-label="{html.escape(L("en", "type_label_main" if qt.quest_type == "main" else "type_label_side"))} '
            f'{html.escape(title_for_aria)}: mark-all" '
            'onclick="event.stopPropagation()">'
        )
    parts.append(f'<span class="quest-type-label">{render_bilingual(type_en, type_pt)}</span>')
    parts.append(f'<h3>{render_bilingual(qe.title, qt.title)}</h3>')
    parts.append(status_badge(qt.status, qt.track_prefix))
    parts.append('</summary>')

    # Card body — bilingual wrapper for summary link, then a SINGLE
    # <ul> for objectives with bilingual <span>s inside each <li>. JS
    # toggles the inner span visibility, no duplication of checkboxes.
    parts.append('<div class="quest-card-body">')
    en_inner = _quest_card_inner(qe, "en")
    pt_inner = _quest_card_inner(qt, "pt")
    parts.append(render_bilingual_raw(en_inner, pt_inner))

    # Render objectives ONCE, outside the bilingual wrappers. The text
    # inside each <li> is itself bilingual (rendered by
    # render_quest_objectives_html when given an en_quest), so a single
    # <ul> covers both languages and JS only has to swap which span is
    # visible.
    en_for_obj = qe if qe.objectives else None
    if qt.objectives or (en_for_obj and en_for_obj.objectives):
        # Forward the show_dividers flag to the objectives renderer so
        # the by-flow view on the stage page can show the 2-part
        # structure while the per-quest card (default caller) stays flat.
        obj_html, _ = render_quest_objectives_html(qt, en_for_obj, show_dividers=show_dividers)
        parts.append(f'<ul class="dd2-checklist">\n{obj_html}\n</ul>')

    parts.append('</div>')  # /quest-card-body
    parts.append('</details>')
    return "\n".join(parts)


def render_quest_detail_bilingual(
    q_en: Quest,
    q_pt: Quest,
    stage_n: int,
    prev_quest: "Quest | None" = None,
    next_quest: "Quest | None" = None,
) -> str:
    """Generate a per-quest detail page with bilingual chrome + content.

    `prev_quest` and `next_quest` are rendered as Previous/Next links
    at the bottom of the page (built from the same iteration order
    `render_stage` uses), so the user can walk through the quest list
    linearly without bouncing back to the stage index.

    `stage_n` is used to render the breadcrumb correctly (the old code
    hardcoded "Stage 1" which broke for Stage 2+).
    """
    qt = q_pt or q_en
    qe = q_en or q_pt
    type_en, type_pt = _type_label_pair(qt.quest_type)

    # Per-quest detail page: open by default (the user came to read
    # this specific quest; forcing them to click to see the body is
    # friction). Stage-page cards stay closed so the cheat sheet
    # doesn't expand into a wall of text.
    parts: list[str] = []
    parts.append(f'<details class="quest-card {qt.quest_type}" open>')
    parts.append('<summary>')
    parts.append('<span class="quest-card-caret" aria-hidden="true">▶</span>')
    if qt.objectives:
        parts.append(
            '<input type="checkbox" class="quest-master" '
            f'aria-label="Mark all objectives for {html.escape(qe.title)}" '
            'onclick="event.stopPropagation()">'
        )
    # from_path is used by render_md_block below to make wiki-link hrefs
    # relative to the current per-quest page. Must be defined BEFORE
    # the Summary block that consumes it.
    sub_early = "main-quests" if qt.quest_type == "main" else "side-quests"
    from_path = f"quests/stage-{stage_n}/{sub_early}/{qt.slug}.html"
    parts.append(f'<span class="quest-type-label">{render_bilingual(type_en, type_pt)}</span>')
    parts.append(f'<h1>{render_bilingual(qe.title, qt.title)}</h1>')
    parts.append(status_badge(qt.status, qt.track_prefix))
    parts.append('</summary>')
    parts.append('<div class="quest-card-body">')

    # Quest ID + location (chrome)
    parts.append(
        f'<p style="margin-top:0"><small>'
        f'<span class="i18n" data-lang="en">Quest</span>'
        f'<span class="i18n" data-lang="pt" hidden>Quest</span>'
        f' <code>{qt.track_prefix}</code> · {html.escape(qt.location)}'
        f'</small></p>'
    )

    # Summary in both langs
    if qe.summary or qt.summary:
        parts.append(f'<h2>{render_bilingual(L("en", "section_resumo"), L("pt", "section_resumo"))}</h2>')
        en_summary = render_md_block(qe.summary, from_path=from_path) if qe.summary else ''
        pt_summary = render_md_block(qt.summary, from_path=from_path) if qt.summary else ''
        parts.append(render_bilingual_raw(en_summary, pt_summary))

    # Objectives — single UL with bilingual text inside each <li>;
    # rendered AFTER the bilingual content blocks so the JS language
    # toggle controls the inner <span class="i18n"> labels without
    # duplicating the checklist.
    if qt.objectives or qe.objectives:
        parts.append(f'<h2>{render_bilingual(L("en", "section_objetivos"), L("pt", "section_objetivos"))}</h2>')
        # Per-quest detail page: no dividers (flat list of all
        # objectives; the 2-part structure is a flow-context concept
        # shown only on the by-flow view).
        obj_html, _ = render_quest_objectives_html(qt, qe if qe.objectives else None, show_dividers=False)
        parts.append(f'<ul class="dd2-checklist">\n{obj_html}\n</ul>')

    # Section-level content
    if qt.walkthrough or qe.walkthrough:
        parts.append(f'<h2>{render_bilingual(L("en", "section_walkthrough"), L("pt", "section_walkthrough"))}</h2>')
        en_walk = render_md_block("\n".join(qe.walkthrough), from_path=from_path) if qe.walkthrough else ''
        pt_walk = render_md_block("\n".join(qt.walkthrough), from_path=from_path) if qt.walkthrough else ''
        parts.append(render_bilingual_raw(en_walk, pt_walk))

    if qt.rewards or qe.rewards:
        parts.append(f'<h2>{render_bilingual(L("en", "section_recompensas"), L("pt", "section_recompensas"))}</h2>')
        en_r = render_md_block("\n".join(qe.rewards), from_path=from_path) if qe.rewards else ''
        pt_r = render_md_block("\n".join(qt.rewards), from_path=from_path) if qt.rewards else ''
        parts.append(render_bilingual_raw(en_r, pt_r))

    if qt.notes or qe.notes:
        parts.append(f'<h2>{render_bilingual(L("en", "section_notas"), L("pt", "section_notas"))}</h2>')
        en_n = render_md_block("\n".join(qe.notes), from_path=from_path) if qe.notes else ''
        pt_n = render_md_block("\n".join(qt.notes), from_path=from_path) if qt.notes else ''
        parts.append(render_bilingual_raw(en_n, pt_n))

    parts.append('</div>')  # /quest-card-body
    parts.append('</details>')  # /quest-card

    sub = "main-quests" if qt.quest_type == "main" else "side-quests"
    sub_label = "Main Quests" if qt.quest_type == "main" else "Side Quests"
    # Clickable breadcrumb suffix (nav_crumbs already adds the Home link).
    # Stage N → Sub-folder → quest title. The quest title is the current
    # page (plain text, not a link). All links use ../../../ because the
    # page lives 3 levels deep in dist/quests/stage-N/sub/.
    crumbs_html = (
        f'<a href="../../../stage-{stage_n}.html">Stage {stage_n}</a>'
        f' &rsaquo; '
        f'<a href="../../../stage-{stage_n}.html#locations">{sub_label}</a>'
        f' &rsaquo; '
        f'<span class="i18n" data-lang="en">{html.escape(qt.title)}</span>'
        f'<span class="i18n" data-lang="pt" hidden>{html.escape(qt.title)}</span>'
    )

    # Prev / Next navigation at the bottom of the page.
    nav_links: list[str] = []
    if prev_quest is not None:
        nav_links.append(
            f'<a class="quest-nav-prev" href="../../{sub}/{prev_quest.slug}.html">'
            f'← {html.escape(prev_quest.title)}</a>'
        )
    if next_quest is not None:
        nav_links.append(
            f'<a class="quest-nav-next" href="../../{sub}/{next_quest.slug}.html">'
            f'{html.escape(next_quest.title)} →</a>'
        )
    if nav_links:
        parts.append('<nav class="quest-nav">')
        parts.extend(nav_links)
        parts.append('</nav>')

    return page_shell(
        title=qt.title,
        body_html="\n".join(parts),
        crumbs_html=crumbs_html,
        crumbs_safe=True,
        crumbs_home_href="../../../index.html",
    )


def render_stage(stage_n: int, bundles: "dict[str, dict[str, Quest]]", repo_root: Path) -> str:
    """Generate dist/stage-{n}.html — the cheat sheet (bilingual)."""
    # Flatten PT quests for location grouping + totals. Bilingual content
    # is rendered pair-by-pair in the loop below; here we just need
    # the PT view for grouping.
    quests_for_meta = [b.get("pt") or b["en"] for b in bundles.values()]

    by_loc: dict[str, list[Quest]] = {loc: [] for loc, _ in LOCATION_ORDER}
    for q in quests_for_meta:
        by_loc.setdefault(q.location, []).append(q)
    for loc in by_loc:
        by_loc[loc].sort(key=lambda q: (0 if q.quest_type == "main" else 1, q.quest_num))

    total_done = sum(sum(1 for o in q.objectives if o.done) for q in quests_for_meta)
    total_all = sum(len(q.objectives) for q in quests_for_meta)
    main_count = sum(1 for q in quests_for_meta if q.quest_type == "main")
    side_count = sum(1 for q in quests_for_meta if q.quest_type == "side")

    body: list[str] = []
    body.append('<header class="page">')
    body.append(f'<h1>{render_bilingual(f"🎮 Stage {stage_n} — Playthrough", f"🎮 Stage {stage_n} — Playthrough")}</h1>')
    body.append(f'<div class="subtitle">{render_bilingual(L("en", "cheatsheet_subtitle"), L("pt", "cheatsheet_subtitle"))}</div>')
    body.append('</header>')

    body.append(f'''<div class="summary-bar">
  <div class="stat"><span class="label">{L("en", "stat_main")}</span><span class="value">{main_count}</span></div>
  <div class="stat"><span class="label">{L("pt", "stat_side")}</span><span class="value">{side_count}</span></div>
  <div class="stat"><span class="label">{L("en", "stat_subs")}</span><span class="value"><span data-total-for="s{stage_n}-">{total_done}/{total_all}</span></span></div>
  <div class="view-toggle-group">
    <button id="view-toggle-locations" type="button" class="view-toggle active" data-view="locations">{render_bilingual(L("en", "view_toggle_locations"), L("pt", "view_toggle_locations"))}</button>
    <button id="view-toggle-flow" type="button" class="view-toggle" data-view="flow">{render_bilingual(L("en", "view_toggle_flow"), L("pt", "view_toggle_flow"))}</button>
  </div>
  <div class="summary-bar-actions">
    <button id="export-tracker" type="button" class="reset-link">{L("en", "export_btn")}</button>
    <button id="export-tracker-pt" type="button" class="reset-link" style="display:none">{L("pt", "export_btn")}</button>
    <button id="import-tracker" type="button" class="reset-link">{L("en", "import_btn")}</button>
    <button id="import-tracker-pt" type="button" class="reset-link" style="display:none">{L("pt", "import_btn")}</button>
    <button id="reset-tracker" type="button">{L("en", "resetar_progresso")}</button>
    <button id="reset-tracker-pt" type="button" style="display:none">{L("pt", "resetar_progresso")}</button>
  </div>
</div>''')

    # TOC — minimal card grid. Just header + progress bar + meta (quest
    # count breakdown). No per-quest chips — those live in the per-location
    # sections below, which is also where the live localStorage counter
    # operates via data-quest-count-for.
    body.append('<nav class="toc" id="locations">')
    body.append('<h2>📍 <span class="i18n" data-lang="en">Locations (anchors)</span><span class="i18n" data-lang="pt" hidden>Locais (âncoras)</span></h2>')
    body.append('<div class="loc-grid">')
    for loc, emoji in LOCATION_ORDER:
        loc_quests = by_loc.get(loc) or []
        if not loc_quests:
            continue
        slug = slugify(loc)
        main_q = [q for q in loc_quests if q.quest_type == "main"]
        side_q = [q for q in loc_quests if q.quest_type == "side"]
        total_obj = sum(len(q.objectives) for q in loc_quests)
        total_done = sum(sum(1 for o in q.objectives if o.done) for q in loc_quests)
        pct = (100 * total_done / total_obj) if total_obj else 0

        body.append('<div class="loc-card">')
        body.append(f'  <a href="#{slug}" class="loc-card-head">')
        body.append(f'    <span class="loc-emoji">{emoji}</span>')
        body.append(f'    <span class="loc-name">{html.escape(loc)}</span>')
        body.append(f'    <span class="loc-counter">{total_done}/{total_obj}</span>')
        body.append('  </a>')
        body.append(f'  <div class="loc-bar"><div class="loc-bar-fill" style="width: {pct:.0f}%"></div></div>')
        body.append(f'  <div class="loc-meta">{len(main_q)} main · {len(side_q)} side · {len(loc_quests)} quests</div>')
        body.append('</div>')
    body.append('</div>')
    body.append('</nav>')

    # Per-location sections (the default "by location" view)
    body.append('<div class="by-location">')
    for loc, emoji in LOCATION_ORDER:
        if not by_loc.get(loc):
            continue
        loc_quests = by_loc[loc]
        slug = slugify(loc)
        main_q = [q for q in loc_quests if q.quest_type == "main"]
        side_q = [q for q in loc_quests if q.quest_type == "side"]

        body.append(f'<h2 id="{slug}">{emoji} {html.escape(loc)}</h2>')

        if main_q:
            body.append(f'<h4>{render_bilingual(L("en", "main_quests"), L("pt", "main_quests"))}</h4>')
            for q in main_q:
                # Look up the bilingual bundle keyed by the same track_prefix
                bundle = bundles.get(_bundle_key_for(q)) or {}
                q_pt = bundle.get("pt") or q
                q_en = bundle.get("en") or q
                body.append(render_quest_block_bilingual(q_en, q_pt))
        if side_q:
            body.append(f'<h4>{render_bilingual(L("en", "side_quests"), L("pt", "side_quests"))}</h4>')
            for q in side_q:
                bundle = bundles.get(_bundle_key_for(q)) or {}
                q_pt = bundle.get("pt") or q
                q_en = bundle.get("en") or q
                body.append(render_quest_block_bilingual(q_en, q_pt))
    body.append('</div>')  # /by-location

    # "By recommended flow" view: flat list in MOC order, no location
    # grouping. Hidden by default; toggled by the .view-toggle buttons
    # in the summary bar (JS in SHARED_JS).
    flow_order = parse_stage_flow(stage_n, repo_root)
    body.append('<div class="by-flow" hidden>')
    body.append('<h2 id="flow">🗺 <span class="i18n" data-lang="en">Recommended flow</span>'
                '<span class="i18n" data-lang="pt" hidden>Fluxo recomendado</span></h2>')
    for qtype, fname in flow_order:
        sub = "main-quests" if qtype == "main" else "side-quests"
        # Find the matching quest in any bundle (look for a PT or EN match
        # with the same filename stem)
        match = None
        for b in bundles.values():
            for side in ("pt", "en"):
                q = b.get(side)
                if q is not None and q.filename.replace(".md", "").replace(".en", "") == fname:
                    match = b
                    break
            if match:
                break
        if not match:
            continue
        q_pt = match.get("pt") or match["en"]
        q_en = match.get("en") or match["pt"]
        # show_dividers=True only on the by-flow view: the per-quest
        # page and the by-location view show objectives as a flat list
        # (the 2-part structure is a flow-context concept).
        body.append(render_quest_block_bilingual(q_en, q_pt, show_dividers=True))
    body.append('</div>')  # /by-flow

    # Footer tip
    body.append('<div class="callout callout-tip"><div class="callout-title">Tip</div>'
                '<div class="callout-body"><span class="i18n" data-lang="en">Use the <strong>Export JSON</strong> and '
                '<strong>Import JSON</strong> buttons above to back up or move your progress between browsers and devices. '
                f'IDs follow the format <code>s{stage_n}-{{main|side}}-{{NN}}-{{i}}</code>.</span>'
                '<span class="i18n" data-lang="pt" hidden>Use os botões <strong>Exportar JSON</strong> e '
                '<strong>Importar JSON</strong> acima para fazer backup ou mover seu progresso entre navegadores e '
                f'dispositivos. Os IDs seguem o formato <code>s{stage_n}-{{main|side}}-{{NN}}-{{i}}</code>.</span></div></div>')

    return page_shell(
        title=f"Stage {stage_n}",
        body_html="\n".join(body),
        crumbs_html=f'Stage {stage_n}',
    )


def _bundle_key_for(quest: Quest) -> str:
    """Key for looking up the bilingual bundle for a given Quest.

    Bundle keys are the file STEM (without extension). The Quest.filename
    keeps the original `.md` suffix because parse_quest() uses it elsewhere,
    so we strip the extension here.
    """
    name = quest.filename
    if name.endswith(".md"):
        name = name[:-3]
    if name.endswith(".en"):
        name = name[:-3]
    return name





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

    # Build filename → stage index so resolve_wikilink can route cross-stage links.
    _build_file_stage_index(repo_root / "Quests")

    # Auto-discover stages: any `Quests/Stage N/` directory. The same glob
    # also matches `Stage N.md` MOC files; the `is_dir()` filter excludes them.
    quests_root = repo_root / "Quests"
    stages: list[int] = sorted(
        int(p.name.split()[-1])
        for p in quests_root.glob("Stage *")
        if p.is_dir()
    )
    if not stages:
        print("[warn] No stage directories found under Quests/.", file=sys.stderr)
        return 1

    # dist/index.html — auto-discovers all stages for the card grid
    (out / "index.html").write_text(render_index(repo_root, stages), encoding="utf-8")
    print(f"[ok] {out/'index.html'}")

    total_quests = 0
    for n in stages:
        stage_dir = quests_root / f"Stage {n}"
        roots = [stage_dir / "Main Quests", stage_dir / "Side Quests"]
        bundles = collect_quests_bilingual(roots)
        if not bundles:
            print(f"[warn] No quests parsed for Stage {n}; skipping.", file=sys.stderr)
            continue

        # dist/stage-{n}.html
        (out / f"stage-{n}.html").write_text(render_stage(n, bundles, repo_root), encoding="utf-8")
        print(f"[ok] {out/f'stage-{n}.html'}")

        # dist/quests/stage-{n}/{main-quests,side-quests}/<slug>.html
        # Pre-sort so we can hand each quest page its prev/next neighbour
        # for the bottom-of-page navigation links.
        ordered_bundles = []
        for loc_key, _ in LOCATION_ORDER:
            loc_quests = [b for b in bundles.values()
                          if (b.get("pt") or b["en"]).location == loc_key]
            loc_quests.sort(key=lambda b: (0 if (b.get("pt") or b["en"]).quest_type == "main" else 1,
                                           (b.get("pt") or b["en"]).quest_num))
            ordered_bundles.extend(loc_quests)
        for idx, bundle in enumerate(ordered_bundles):
            q_pt = bundle.get("pt") or bundle["en"]
            q_en = bundle.get("en") or bundle["pt"]
            sub = "main-quests" if q_pt.quest_type == "main" else "side-quests"
            target = out / "quests" / f"stage-{n}" / sub / f"{q_pt.slug}.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            # Use the same stage ordering to find the prev/next Quest objects
            # (only neighbour quest objects, not the full bundle dict).
            prev_q = ordered_bundles[idx - 1].get("pt") or ordered_bundles[idx - 1]["en"] if idx > 0 else None
            next_q = ordered_bundles[idx + 1].get("pt") or ordered_bundles[idx + 1]["en"] if idx + 1 < len(ordered_bundles) else None
            # from_path lets wiki-links inside this page's body
            # resolve to hrefs that work from the per-quest file
            # (3 levels deep in dist/).
            q_en.from_path = q_pt.from_path = f"quests/stage-{n}/{sub}/{q_pt.slug}.html"
            target.write_text(
                render_quest_detail_bilingual(q_en, q_pt, stage_n=n,
                                              prev_quest=prev_q, next_quest=next_q),
                encoding="utf-8",
            )
        total_quests += len(bundles)
        print(f"[ok] {len(bundles)} per-quest pages for Stage {n}")

    print(f"\nDone. {total_quests} per-quest pages across {len(stages)} stage(s).")
    if stages:
        print(f"Open {out/f'stage-{stages[0]}.html'} in your browser to preview.")
    return 0


if __name__ == "__main__":
    sys.exit(main())