# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A **Dragon's Dogma 2 walkthrough hub** built from Obsidian-vault Markdown files. The vault (under `Quests/`) is the human-editable source of truth, and `scripts/build.py` compiles it into a small set of **self-contained HTML pages** under `dist/` that can be opened directly in any browser, with no server, no CDN, no runtime build step. Pages have an EN/PT language toggle and a `localStorage`-backed checkbox tracker for quest objectives.

Live site: <https://mo3ses.github.io/dd2-walkthrough/>

## Commands

There is no `npm`, no test runner, no linter — the project is Python 3 stdlib only.

```bash
# Build everything (run from repo root)
python3 scripts/build.py

# Build with a custom repo root or output dir
python3 scripts/build.py --repo-root /path/to/repo --out /path/to/out

# Preview
xdg-open dist/stage-1.html      # Linux
open    dist/stage-1.html       # macOS

# Reset progress in the browser console
# localStorage.removeItem("dd2-tracker-v1")
```

The `.github/workflows/deploy.yml` workflow runs `python3 scripts/build.py` on every push to `main` and publishes `dist/` to GitHub Pages — no manual deploy step needed.

## Architecture

### Data flow

```
Quests/**/*.md  ──►  scripts/build.py  ──►  dist/**/*.html  ──►  GitHub Pages
 (Obsidian vault)     (Python stdlib)     (self-contained)
```

`scripts/build.py` is intentionally one file (~1.8k LOC) doing parsing, rendering, and template emission in a single pass. No plugins, no templating engine.

### Vault layout (source)

```
Quests/
├── Locations/                  ← per-location reference files
│   ├── Excavation Site.md       (each has a matching .en.md)
│   ├── Ultramarine Waterfall.md
│   ├── Borderwatch Outpost.md
│   └── Melve.md
├── Stage 1.md                  ← MOC / index for the stage
├── Stage 1/
│   ├── "Checklist Geral - Stage 1.md"  (optional aggregator)
│   ├── Main Quests/
│   │   ├── "01 - Gaoled Awakening.md"
│   │   ├── "02 - Tale's Beginning.md"
│   │   └── "08 - In Dragon's Wake.md"
│   └── Side Quests/
│       ├── "03 - Ordeal's of a New Recruit.md"
│       └── … (06 side quests total)
└── Stage 2/…                   ← future stages follow the same shape
```

### Bilingual source convention

- `*.md`        → Portuguese (PT is the primary language; the vault predates EN)
- `*.en.md`     → English (optional; PT is used as fallback when the EN file is missing)
- The build script pairs files by stem (e.g. `01 - Gaoled Awakening.md` ↔ `01 - Gaoled Awakening.en.md`).
- All UI chrome strings (button labels, section headers, JS messages) live in a single `STRINGS` dict at the top of `scripts/build.py` with `en` and `pt` keys.

### Quest MD format (what the parser understands)

Frontmatter with: `quest`, `type` (Main Quest | Side Quest), `stage`, `location` (as a `[[wiki-link]]`), `quest_giver`, and `tags`.

Body sections (PT) or English equivalents. The parser is **deliberately minimal** — it only recognizes these section names:

| Purpose        | PT heading             | EN heading          |
|----------------|------------------------|---------------------|
| Objectives     | `## Objetivos`         | `## Objectives`     |
| Summary        | `## Resumo`            | `## Summary`        |
| Walkthrough    | `## Walkthrough`       | (same)              |
| Rewards        | `## Recompensas`       | `## Rewards`        |
| Important notes| `## Notas Importantes` | `## Important Notes`|

Headings may carry a Dataview-style anchor suffix like `^some-id` (stripped before matching). Wiki-links `[[Foo/Bar]]` and `[[Foo/Bar|Alias]]` are resolved to `dist/...` relative URLs via `resolve_wikilink()`.

Objective checklist lines like `- [x] …` and `- [ ] …` are the source of the tracker IDs.

### Bilingual rendering pattern (this is the core trick)

The build emits **both** language variants inline on the page; client-side JS swaps which is visible:

```html
<span class="i18n" data-lang="en">Objective text in English</span>
<span class="i18n" data-lang="pt" hidden>Texto do objetivo em português</span>
```

Critical: the objectives **checklist** is rendered **once** (a single `<ul>`), with bilingual text *inside* each `<li>`. JS toggles the `hidden` attribute on inner spans. This way checkbox state and `data-track-id` are shared — never duplicated per language.

The whole CSS theme (`SHARED_CSS`) and the tracker/language JS (`SHARED_JS`) are inlined into every page via `page_shell()`, which is what makes each file truly self-contained.

### Tracker IDs (deterministic)

Every objective checkbox gets a stable `data-track-id` with the shape:

```
s{stage}-{main|side}-{NN}-{i}     e.g. s1-main-01-3, s1-side-05-2
```

This ID is **the key** in the `localStorage` object under `dd2-tracker-v1`. Two quest files with the same number/type guarantee the same IDs — so progress survives rebuilds and stage reorganization is safe as long as numbering is preserved.

Per-card master checkboxes (`<input class="quest-master">`) and per-quest badges with `data-quest-count-for` / stage totals with `data-total-for` are all updated live from checkbox state on every change — never from build-time MD `- [x]` markers.

### Stage 1 metadata that the build hard-codes

- `LOCATION_ORDER`   → canonical visit order (used for TOC grouping on `stage-1.html`)
- `QUEST_OVERRIDES`  → maps each quest filename to `(location, main|side, num)`; needed because the road-quest (09) groups under "Melve → Vernworth" even though its frontmatter says Melve

When adding a new quest, **prefer fixing the quest's MD frontmatter** over adding an entry to `QUEST_OVERRIDES`. New overrides are a code smell.

### Key locations in `scripts/build.py`

| Function                  | Role                                                            |
|---------------------------|-----------------------------------------------------------------|
| `parse_frontmatter`       | YAML-subset extractor (no PyYAML dependency).                   |
| `parse_quest`             | Builds a `Quest` dataclass from one MD file.                    |
| `collect_quests_bilingual`| Scans roots, returns `{stem: {"pt": Quest, "en": Quest\|None}}`.|
| `render_inline`           | Wiki-link → anchor, escaping exactly once (see comment block).  |
| `render_md_block`         | Paragraphs, bullets, numbered lists, tables, Obsidian callouts. |
| `render_quest_objectives_html` | The single-`<ul>` bilingual checklist — read comments.    |
| `render_quest_block_bilingual` / `render_quest_detail_bilingual` | Card vs detail page. |
| `L()`                     | UI string lookup with `{var}` formatting.                       |
| `SHARED_CSS`, `SHARED_JS` | Single source for theme + tracker; injected by `page_shell`.   |

## Conventions from the user's vault

- **PT is the source of truth.** Keep the apostrophe canonical spellings in filenames (e.g. `Ordeal's`, not `Ordeals`).
- **One file per quest**, frontmatter + sections as in `obsidian-vault-conventions` memory.
- **Wiki-link everything** that cross-references another file (`[[01 - Quest Name]]`).
- **Callouts**: `> [!warning]`, `> [!info]`, `> [!tip]`, `> [!note]`, `> [!todo]`, `> [!summary]` are all rendered in `render_md_block`.
- **No external images / no CDN** — keep pages truly offline-capable.

## What lives in `dist/` is generated

Anything in `dist/` is overwritten by the build. Edit `Quests/*.md` or `scripts/build.py` instead. `dist/` is gitignored at the user side (the workflow re-creates it on deploy).

## Known limitations of the build

- No PyYAML — frontmatter parsing is a hand-rolled `KEY: value` regex. Multi-line values, anchors, and typed arrays are not supported. Keep frontmatter single-line per key.
- Tables only support the `| col | col |` + `|---|---|` header syntax.
- Headings inside sections get re-leveled (`#` → `<h3>`, `##` → `<h4>`, etc.) by `render_md_block` — the cheat sheet sinks a section two levels under the page title.
- Stage 2/3/4 directories don't exist yet. The build only emits Stage 1 (see `stages = [1]` in `main()`). To enable another stage: create `Quests/Stage N/{Main Quests,Side Quests}/`, add it to `stages`, and update `Quest.url` to match the new folder name.
