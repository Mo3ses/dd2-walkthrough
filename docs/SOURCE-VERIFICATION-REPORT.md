# Source Verification Report — Stage 2 (this session)

**Date:** 2026-07-07
**Scope:** 18 Stage 2 quests filled this session + 3 multi-source pre-existing (21, 24, 26).
**Method:** WebFetch on IGN + Fandom in 3 sequential batches of 12 parallel calls each (36 fetches total). Fextralife on hand from earlier fill pass.

## Outcome

**Neither IGN nor Fandom was reachable from this environment** — full 36/36 fetch failure. Per the plan's Step 4 update logic, all 18 in-scope files now have:

```yaml
sources_verified:
  - fextralife
needs_verification: true
```

The `needs_verification: true` flag is now meaningful: it encodes "cross-source attempt happened on 2026-07-07, IGN harness-blocked, Fandom 402 paywall — only Fextralife verified." This is more honest than the previous `false`, which implied cross-source verification had succeeded (it hadn't).

The 3 pre-existing multi-source files (21, 24, 26) were **not migrated** to `[fandom, fextralife, ign, user]` — the conditional was "only if Fandom loads for each", and it didn't load for any. They remain `[fextralife, ign, user]`.

## Summary

| Outcome | Count |
|---------|-------|
| All 3 wikis reachable, all agree | 0 |
| All 3 wikis reachable, conflict | 0 |
| 1-2 wikis unreachable (audit flipped to `true`) | 18 |
| Pre-existing multi-source, no migration triggered | 3 |
| Material conflict identified | 0 (no data to compare) |

## Per-quest table

| # | Quest | Sources reached | Conflict | needs_verification |
|---|-------|-----------------|----------|--------------------|
| 15 | Seat of the Sovran | fextralife | n/a (others unreachable) | true |
| 17 | Monster Culling | fextralife | n/a | true |
| 19 | Vocation Frustration | fextralife | n/a | true |
| 23 | The Stolen Throne | fextralife | n/a | true |
| 31 | House of the Blue Sunbright | fextralife | n/a | true |
| 32 | Readvent of Calamity | fextralife | n/a | true |
| 33 | Home Is Where the Hearth Is | fextralife | n/a | true |
| 34 | Claw Them Into Shape | fextralife | n/a | true |
| 35 | Beren's Final Lesson | fextralife | n/a | true |
| 36 | Spellbound | fextralife | n/a | true |
| 37 | Trouble on the Cape | fextralife | n/a | true |
| 38 | Gift of the Bow | fextralife | n/a | true |
| 39 | A Trial of Archery | fextralife | n/a | true |
| 40 | The Ailing Arborheart | fextralife | n/a | true |
| 41 | Prey for the Pack | fextralife | n/a | true |
| 42 | Hunt for the Jadeite Orb | fextralife | n/a | true |
| 43 | The Sorcerer's Appraisal | fextralife | n/a | true |
| 44 | Feast of Deception | fextralife | n/a | true |
| 21 | The Caged Magistrate | fextralife, ign | n/a | false (unchanged) |
| 24 | An Unsettling Encounter | fextralife, ign | n/a | false (unchanged) |
| 26 | The Nameless Village | fextralife, ign | n/a | false (unchanged) |

## Material conflicts (detail)

None — IGN and Fandom both returned errors on every fetch, so no cross-source comparison was possible.

## Unresolved URLs (re-try next session)

### IGN — 18/18 failed at harness level

All 18 attempts on `https://www.ign.com/wikis/dragons-dogma-2/<Title_With_Underscores>` returned the error:

> Claude Code is unable to fetch from www.ign.com

This is **not a 404** — the URL pattern was never tested. It's a harness-level block on the `www.ign.com` domain. No retry strategy within WebFetch will work. Two options for next session:

1. **Bash + curl with browser User-Agent** (e.g. `curl -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"`) — IGN's anti-bot is likely User-Agent-string based.
2. **Manual fetch** — open IGN URLs in a browser, paste walkthrough data into the frontmatter by hand.

### Fandom — 18/18 returned HTTP 402 Payment Required

Tested patterns per quest:

- `https://dragonsdogma.fandom.com/wiki/<Title_With_Underscores>` → 402
- `https://dragonsdogma.fandom.com/wiki/<Title_With_Underscores>?action=raw` → 402 (raw content also blocked)
- (Plus-fallback pattern not retried after `?action=raw` also 402'd)

Fandom's 402 is on **all** endpoints — this is a per-domain paywall, not a content gate. The documented workaround (per plan Section 9) is `curl -H "User-Agent: <browser UA>"` because Fandom often relaxes the paywall for legitimate browser UAs. Same retry options as IGN above.

### Domains tried but unavailable

- `dragonsthinhs.com` (Dragon's Thin's — typo'd alternative wiki) — DNS ENOTFOUND. Skip.
- Fandom namespace prefixes like `Dragon%27s_Dogma_2:<Title>` — not retried after the 402 pattern; unlikely to help since the 402 is domain-wide.

## Build impact

None. `sources_verified` is purely informational — `scripts/build.py` lines 1849-1858 emit the 3 source names as a static footer regardless of frontmatter content. The `dist/` HTML output is unchanged in any user-visible way. Verified post-edit: build passes, page counts unchanged (44 per-quest pages across 2 stages).

## Follow-up

1. **Single biggest lever:** a Bash + `curl -A "Mozilla/..."` retry pass for both IGN and Fandom. With proper UAs, the 18 IGN and 18 Fandom fetches may all succeed on the second try, flipping `needs_verification` back to `false` for the 18 in-scope files and triggering the conditional migration of 21/24/26.
2. **Secondary scope:** the 11 Stage 2 side quests with empty `sources_verified: []` (10, 11, 12, 13, 14, 16, 18, 20, 25, 28, 30) and the 3 with `needs_verification: true` + empty sources (22, 27, 29) are still open — those were deferred per user scope decision but should be picked up in a future sweep.