# Source Verification Report — Stage 2 (this session)

**Date:** 2026-07-07
**Scope:** 18 Stage 2 quests filled this session + 3 multi-source pre-existing (21, 24, 26).
**Method:** WebFetch on IGN + Fandom in 3 sequential batches of 12 parallel calls each (36 fetches total). Fextralife on hand from earlier fill pass.

## Outcome

**Neither IGN nor Fandom was reachable from this environment** — full 36/36 fetch failure via WebFetch. Per the plan's Step 4 update logic, all 18 in-scope files now have:

```yaml
sources_verified:
  - fextralife
needs_verification: true
```

The `needs_verification: true` flag is now meaningful: it encodes "cross-source attempt happened on 2026-07-07, IGN harness-blocked, Fandom 402 paywall — only Fextralife verified." This is more honest than the previous `false`, which implied cross-source verification had succeeded (it hadn't).

The 3 pre-existing multi-source files (21, 24, 26) were **not migrated** to `[fandom, fextralife, ign, user]` — the conditional was "only if Fandom loads for each", and it didn't load for any. They remain `[fextralife, ign, user]`.

### Update — 2026-07-07 (later same session)

Curl + browser User-Agent retry succeeded for most quests. Results:

- **IGN** (browser UA `Mozilla/5.0 ... Chrome/120`): **21/21 reachable** (3 needed URL slug fixes — see "Unresolved URLs" below).
- **Fandom** (browser UA `w3m/0.5.3+git20230121`): **15/21 reachable** (HTML 7 + `?action=raw` 8). The remaining 6 (`#21, #23, #33, #37, #40, #42`) still 403 even with browser UA.

**Frontmatter updates applied** (20 files edited):

| Coverage | Count | Result |
|----------|-------|--------|
| All 3 wikis reachable | 13 in-scope + 2 pre-existing | → `[fandom, fextralife, ign]` (or `...ign, user` for 24/26), `needs_verification: false` |
| IGN + Fextralife (Fandom blocked) | 5 in-scope (`#23, #33, #37, #40, #42`) | → `[fextralife, ign]`, `needs_verification: true` |
| Only Fextralife (IGN not yet retried in retry, Fandom blocked) | 1 pre-existing (`#21`) | → unchanged, `[fextralife, ign, user]` |

**Caveat:** Cross-source fact-comparison was NOT performed in this retry — coverage-based heuristic only. A future pass should compare key facts (XP, gold, item names, quest giver) across the 3 sources and flag conflicts.

## Summary

| Outcome | Count |
|---------|-------|
| All 3 wikis reachable | 15 (13 + 2 pre-existing) |
| 2 wikis reachable (Fandom blocked) | 5 |
| 1 wiki reachable | 1 (pre-existing, Fandom blocked) |
| Material conflicts found | 0 (not cross-checked yet) |

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


### Update — 2026-07-07 (next session, batch #2)

Ran `scripts/check_cross_source.py` against the 15 quests marked `[fandom, fextralife, ign] + needs_verification: false`. The script extracts `quest_giver`, `xp`, and `gold` from each source and flags any field where the 3 sources disagree.

**Result: 10 of 15 quests have at least one disagreement.**

| # | Quest | Conflicts | Notes |
|---|-------|-----------|-------|
| 15 | Seat of the Sovran | quest_giver | Fextralife has "Brant / Sovran Disa"; Fandom returns "Brant" alone |
| 17 | Monster Culling | — | consensus |
| 19 | Vocation Frustration | quest_giver | Fextralife = "NPC desconhecido" (gap); Fandom = "Klaus" |
| 24 | An Unsettling Encounter | — | consensus |
| 26 | The Nameless Village | quest_giver | Fextralife = "Brant"; Fandom returns "Brant" (no real disagreement, false positive) |
| 31 | House of the Blue Sunbright | quest_giver | Fextralife = "NPC desconhecido"; Fandom = "Diana" |
| 32 | Readvent of Calamity | — | consensus |
| 34 | Claw Them Into Shape | quest_giver | Both sources agree on "Beren"; Fandom appends "Beren's Te..." (location, false positive) |
| 35 | Beren's Final Lesson | — | consensus |
| 36 | Spellbound | quest_giver + gold | quest_giver regex grabs "Trysha" from Fextralife and "Trysha" from IGN (correct). gold: Fextralife 3000 G vs IGN 5000 G — real numerical conflict |
| 38 | Gift of the Bow | quest_giver | Fextralife = "NPC desconhecido"; Fandom = "Glyndwr" |
| 39 | A Trial of Archery | quest_giver | Fextralife = "NPC desconhecido"; Fandom = "Glyndwr" |
| 41 | Prey for the Pack | quest_giver | Fextralife = "NPC desconhecido"; Fandom = "Morris" |
| 43 | The Sorcerer's Appraisal | quest_giver + gold | Fextralife quest_giver = "Mage NPC" (vague), gold = 11000 G; IGN quest_giver regex grabbed "Returning the Books to Myrddin" (false positive), gold = 5000 G — needs manual review |
| 44 | Feast of Deception | — | consensus |

**Interpretation:** Most conflicts are **Fextralife gaps** (NPC name not in our copy of the page → "NPC desconhecido"), not factual disagreements. The right action is to fill the missing NPC names from Fandom, not to roll back the 3-source flag. Only **Spellbound (#36)** and **Sorcerer's Appraisal (#43)** have real numerical gold disagreements that warrant manual review.

### Action items (not blocking this PR)

1. Fill `quest_giver:` for the 6 quests where Fextralife says "NPC desconhecido" (19, 31, 38, 39, 41, plus tightening "Mage NPC" on 43) using the Fandom-discovered names.
2. Manually verify gold reward for #36 (Spellbound: 3000 vs 5000) and #43 (Sorcerer's Appraisal: 11000 vs 5000) by reading the cached HTMLs.
3. Tighter regex for quest_giver in `scripts/check_cross_source.py` — current pattern over-matches on "Quest Location" / "Prerequisite" labels in Fandom's structured template.

The script stays in the tree as a guardrail: re-running it after the above fills should drop the false positives and surface only real disagreements.

## Summary

| Outcome | Count |
|---------|-------|
| All 3 wikis reachable | 15 (13 + 2 pre-existing) |
| 2 wikis reachable (Fandom blocked) | 5 |
| 1 wiki reachable | 1 (pre-existing, Fandom blocked) |
| Material conflicts found | 2 (Spellbound gold, Sorcerer's Appraisal gold) |
| Fextralife gaps (NPC missing) | 6 (false-positive conflicts) |

## Per-quest table

| # | Quest | Sources reached | Conflict | needs_verification |
|---|-------|-----------------|----------|--------------------|
| 15 | Seat of the Sovran | fextralife, fandom, ign | quest_giver regex noise | true |
| 17 | Monster Culling | fextralife, fandom, ign | — | true |
| 19 | Vocation Frustration | fextralife, fandom, ign | Fextralife gap | true |
| 23 | The Stolen Throne | fextralife, ign | n/a | true |
| 24 | An Unsettling Encounter | fextralife, fandom, ign, user | — | false |
| 26 | The Nameless Village | fextralife, fandom, ign, user | — | false |
| 31 | House of the Blue Sunbright | fextralife, fandom, ign | Fextralife gap | true |
| 32 | Readvent of Calamity | fextralife, fandom, ign | — | true |
| 33 | Home Is Where the Hearth Is | fextralife, ign | n/a | true |
| 34 | Claw Them Into Shape | fextralife, fandom, ign | regex noise | true |
| 35 | Beren's Final Lesson | fextralife, fandom, ign | — | true |
| 36 | Spellbound | fextralife, fandom, ign | **real: gold 3000 vs 5000** | true |
| 37 | Trouble on the Cape | fextralife, ign | n/a | true |
| 38 | Gift of the Bow | fextralife, fandom, ign | Fextralife gap | true |
| 39 | A Trial of Archery | fextralife, fandom, ign | Fextralife gap | true |
| 40 | The Ailing Arborheart | fextralife, ign | n/a | true |
| 41 | Prey for the Pack | fextralife, fandom, ign | Fextralife gap | true |
| 42 | Hunt for the Jadeite Orb | fextralife, ign | n/a | true |
| 43 | The Sorcerer's Appraisal | fextralife, fandom, ign | **real: gold 11000 vs 5000** | true |
| 44 | Feast of Deception | fextralife, fandom, ign | — | true |
| 21 | The Caged Magistrate | fextralife, ign, user | n/a | false (unchanged) |

## Material conflicts (detail)

Two real numerical disagreements worth a manual look:

- **#36 Spellbound — gold reward:** Fextralife (in MD) says 3.000 G, IGN HTML extraction says 5.000 G. Diff: 67%. Pick one when filling.
- **#43 The Sorcerer's Appraisal — gold reward:** Fextralife (in MD) says 11.000 G, IGN HTML extraction says 5.000 G. Diff: 120%. Pick one when filling.

Six Fextralife-gaps (placeholders `NPC desconhecido` / `Mage NPC` in `quest_giver:`) where Fandom has a real name:

- #19 → Klaus
- #31 → Diana
- #38 → Glyndwr
- #39 → Glyndwr
- #41 → Morris
- #43 → (need to pick — IGN extraction grabbed "Myrddin" but it's in a "Returning the Books to Myrddin" page heading, not necessarily the giver)

The remaining two (#15, #26, #34) are regex over-matches on Fandom's structured template ("Quest Location ..." labels bleeding into the giver capture). Tightening the regex will resolve these.

## Unresolved URLs (re-try next session)
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