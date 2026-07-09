# Próximos Passos — Dragon's Dogma 2 Walkthrough

> Estado em 2026-07-09 (sessão #7 — build pipeline + MOC simplificação). Working tree: limpo (HEAD `e52d800` em `feat/stage-2-flow-restructure`, PR #12 atualizado com os 3 commits desta sessão). Próxima sessão: merge PR #12 → live no site; play-validation continua; Steps 2 (mermaid) e 3 (prereq tables) ainda pendentes.

## Onde paramos (sessão #7 — build pipeline + MOC simplification)

**Branch ativa: `feat/stage-2-flow-restructure`** com **PR #12 aberto** contra `main` (3 commits ahead). Histórico de commits:

```
e52d800 docs(stage-1): simplify MOC body to Cross-Stage Prep + Avisos + Fontes
536b4a6 feat(build): cross-stage stub cards + MOC body render + Obsidian callouts + markdown links
43b130f feat(stage-1+2): move Claw Them Into Shape (34) START/CONTINUE + Spellbound (36) START to Stage 1 MOC Cross-Stage Prep
```

**What session #7 did**:

1. **PR #11 foi merged** pelo usuário (`ca46d6c` em main). Stage 2 MOC restructure está live em https://mo3ses.github.io/dd2-walkthrough/stage-2.html.

2. **Cross-stage stub cards** injetados em `dist/stage-1.html`:
   - Logo depois de Brother's Brave (Melve side-quest, by-location view) E no by-flow view.
   - Cada stub mostra APENAS objectives que acontecem em Stage 1 (e.g., "Have 3 swords in inventory"), com notice "resto em Stage 2" e link para a página de detalhe Stage 2.
   - Tracker IDs reais `s2-side-34-i` e `s2-side-36-i` — ticks em Stage 1 sincronizam via localStorage com Stage 2.

3. **MOC body extras rendering** adicionado:
   - `_render_moc_extras()` em `scripts/build.py` renderiza seções do MOC que o build ignorava (NPCs, Fatos, Cross-Stage Prep, Avisos, Fontes).
   - Filtra sections já representadas: Locations TOC, Main Quests tables, Side Quests tables, Checklist, Ordem Recomendada, Fluxo Recomendado (mermaid).

4. **Stage 1 MOC simplificado**:
   - Removidos `## 🎯 NPCs notáveis` e `## 🔑 Fatos verificados` (info redundante — já vive em per-quest MDs).
   - Removida sub-section `### Quests iniciadas na estrada Melve → Vernworth` (agora tratada pelos cards stub cross-stage).
   - Re-escrito bullet `🛒 3 espadas`: agora corretamente diz "compre e entregue direto a Beren em Moonglow Garden durante Stage 1" (antes implicava "Stage 2 prep" — errado).
   - Re-escrito bullet `📜 Grimoires`: mantém só Fulminous Shield (Dudley em Melve) — o único grimoire com compra Stage 1 que avança Spellbound.
   - Removido `> [!warning] Stage 2 Preparation` — block duplicado/errado (a info já está no stub card).

5. **Build pipeline fixes**:
   - **CALLOUT_RE regex fixado**: removido trailing `\*?` (Obsidian não requer `*` final). Title agora aparece no `callout-title`, não duplicado no body.
   - **render_inline agora processa markdown links `[text](url)`** — antes passavam como texto literal (quebrado o Fontes block).
   - **INLINE_LINK_RE combinado wiki+markdown** num único regex pass — evita double-escape em apóstrofos (ex.: `Dragon's` agora renderiza como `Dragon's`, não `Dragon&amp;#x27;s`).
   - **Melve location-counter prefixes** agora inclui `s2-side-34,s2-side-36` — objective progress de Claw/Spellbound conta na barra de progresso da Melve.

**Open scope (play-validation + minor polishes)**:

- **A) Play-validate** — usuário joga contra `dist/stage-1.html` e `dist/stage-2.html` no live site (após merge PR #12) ou localmente, reporta qualquer bug. Cards stub podem ter objetivos faltando ou NPC errado.
- **B) Merge PR #12** — assim que usuário confirma que está OK, mergear e GitHub Pages rebuilda.
- **C) Step 2** — refresh mermaid diagram (lines 255-303). Espinha linear de 5 blocos está desatualizada vs. a nova flow de 6 sub-arcs. Pendente.
- **D) Step 3** — update per-block prereq tables (lines 119-208). DAG antiga reflete pre-a149699. Pendente.
- **E) Se play-validation achar bugs** → corrigir no mesmo branch → push update antes do merge.

**Validated locally**:

```
python scripts/check_wikilinks.py  # OK, 1516 links, 0 broken
python scripts/build.py            # OK, 51 per-quest pages across 3 stages
```

**Como retomar próxima sessão**:

```bash
git fetch origin
git checkout feat/stage-2-flow-restructure
git log --oneline -5                         # ver 43b130f / 536b4a6 / e52d800
start dist/stage-1.html                      # preview local
# ou após merge do PR #12: https://mo3ses.github.io/dd2-walkthrough/stage-1.html
```

---

## Onde paramos (sessão #5 — cross-source fetcher + Stage 1 review, merged via PR #10)

**What session #6 did**:

- Reescreveu a `## 🎮 Ordem Recomendada de Execução` em ambos MOC files (PT + EN): 47 entries → **113 entries** em **6 sub-arcs** (parser vê como lista flat — H3 markers são visual only):
  - **MELVE setup** (Stage 1 preface, steps 1-14): Gaoled, Tale's, In Dragon's Wake, Ordeal's, Provisioner's, Claw prep, Spellbound @ Eini's, Seat @ Melve, Medicament, Nesting, One-Eyed Interloper, Seat → Vernworth.
  - **VERNWORTH pt.1** (steps 15-30): In Dragon's Wake COMPLETAR, Claw chain, Beren's Final Lesson, Ornate Box, Beggar's Tale, Gift of Giving, Heel of History, Seat COMPLETAR.
  - **Cycle pt.1↔pt.2** (steps 31-52): Monster Culling, Disa's Plot, Caged Magistrate, Ornate continuations, Saint of the Slums, A Place to Call Home, House of Blue Sunbright, Monster Culling @ Trevo Mine + grifo, Nameless Village, Stolen Throne, Arisen's Shadow, Scaly Invaders, Readvent @ Melve, Nameless COMPLETAR.
  - **VERNWORTH pt.2** (steps 53-82): Arisen's Shadow COMPLETAR, Till Death, Tolled To Rest, A Game of Wits (sphinx), Hunt Jadeite, Prey for Pack, Saint of Slums (Radcliff), Sorcerer's Appraisal, Trial of Archery, Till Death COMPLETAR, Wendy/Howling, **Brother's Brave and Timid (EN-only cross-ref @ step 74)**, Spellbound continuations + COMPLETAR, Trial COMPLETAR, Ailing Arborheart, Taliesin.
  - **Cycle pt.2↔pt.3** (step 83): Readvent of Calamity @ Harve/Ulrika.
  - **VERNWORTH pt.3** (steps 84-113): Trouble on Cape, Sculptor's Block, Dulled Steel, Masked Correspondence, Disa's Plot (castelo/prisão), Caged Magistrate CONTINUAR/COMPLETAR, Magesterial Amenity, Stolen Throne COMPLETAR, Every Rose, Feast of Deception, **Stage 3 transitions** (A Noble Exchange, Nation of the Lambert Flame, A Veil of Gossamer), Saint of Slums COMPLETAR (Lubomir), Sorcerer's Appraisal COMPLETAR, **I'm In achievement**.

- Cross-refs entre stages via path completo: `[[Stage 1/Side Quests/<slug>]]`, `[[Stage 3/Main Quests/<slug>]]`.
- Corrigiu typo PT `39.` (que era um número repetido) via renumeração completa.
- Validação local:
  - `python scripts/check_wikilinks.py` → **OK, 1521 links, 0 broken**.
  - `python scripts/build.py` → **OK, 51 per-quest pages across 3 stages** (Stage 1: 9, Stage 2: 39, Stage 3: 3).
- Commited em `feat/stage-2-flow-restructure` (commit `5dd59da`); PR #11 aberto.

**Open scope (próxima sessão / após play-validation)**:

- **A) Play-validate a nova flow** — usuário vai jogar contra `dist/stage-2.html` e reportar bugs. Capture:
  - Qualquer step com ordem errada ou estado (INICIAR/CONTINUAR/COMPLETAR) mal marcado.
  - Prereq violado (quest aparece antes da side quest que a desbloqueia).
  - Action annotations erradas (NPC, localização, item).
- **B) Step 2 — refresh mermaid** (lines 255-303) — diagrama atual é spine linear de 5 blocos, desatualizado vs. nova flow de 6 sub-arcs. Use subgraphs para cluster sub-arcs, short labels (e.g. `S15_Sovran`), validate em mermaid.live antes de commitar.
- **C) Step 3 — update per-block prereq tables** (lines 119-208) — DAG antiga reflete pre-a149699. Default: minimal change (move row only if quest changed blocks).
- **D) Merge PR #11 → GitHub Pages rebuilds** (`dist/stage-2.html`).
- **E) Se bugs surgirem do play-validation → corrigir no mesmo branch → push update** antes do merge.
- **F) Stage 3 bodies (01 A Noble Exchange / 02 Nation Lambert Flame / 03 A Veil of Gossamer) — frontmatter-only stubs**, sem `## Objectives`. Work-research pesado.

**Skipped nesta sessão (consciente)**:

- Houve um falso-positivo no `check_wikilinks.py` por causa do template `[[Stage 1/Side Quests/<slug>]]` que coloquei na callout do intro — o regex apanhou como wikilink real. Corrigido reescrevendo a callout sem os colchetes literais (`path absoluto a partir de `Quests/Stage 1/Side Quests/<slug>.md``).
- Não rodei Step 2 (mermaid) nem Step 3 (tables) ainda — risco de refazer se a play-validation achar bugs na Step 1.

**Como retomar**:

```bash
git checkout feat/stage-2-flow-restructure
python scripts/check_wikilinks.py        # 0 broken
python scripts/build.py                  # gera dist/stage-2.html local
start dist/stage-2.html                  # preview local
# ou abre https://mo3ses.github.io/dd2-walkthrough/stage-2.html após merge do PR #11
```

---

## Onde paramos (sessão #5 — committed, merged via PR #10)

> **Branch ativa: `feat/stage-2-recommended-flow`**, 9 commits ahead de `main`. **Working tree limpo** (próximo batch = `git push`).

**What session #5 did** (2 commits novos, este branch):

- **dff6bb2** feat(scripts): cross-source fetcher + checker coverage report — `scripts/fetch_sources.py` novo (CLI; sequential por quest; sleep+retry no Fandom 403; soft-404 detector); checker agora reporta `Source coverage: 3/3=X, 2/3=Y, 1/3=Z`
- **6e0b99d** feat(scripts): TITLE_OVERRIDES + checker includes Stage 1 — Ordeal's→Ordeals, Brother's→Brothers; removed `needs_verification: false` gate; skip `.en.md` siblings

**URL patterns (verified 2026-07-09)**:

- **Fextralife:** `dragonsdogma2.wiki.fextralife.com/<Title+With+Plusses>` (apóstrofo raw, preposições lowercase)
- **Fandom:** `dragonsdogma.fandom.com/wiki/<Title_With_Underscores>` (%27, preposições lowercase). RATE-LIMITED — 403 após burst; precisa 1.5s sleep + retry
- **IGN:** `www.ign.com/wikis/dragons-dogma-2/<Title_With_Underscores>` (%27). Algumas páginas 404 (estrutura mudou)

**Stage 1 review (9 quests × 3 fontes)**:

- ✅ **6 OK sem conflito:** 03, 04, 05, 06, 07, 08 (Ordeals/Brothers via TITLE_OVERRIDES)
- ⚠️ **2 Fandom=None (não-conflitos reais):** 01 Gaoled Awakening (fex=The Pathfinder), 02 Tale's Beginning (fex=Brant). Fandom literalmente não registrou quest_giver nessas páginas; Fextralife é fonte. **Decisão:** confiar no Fextralife.
- ⚠️ **1 partial:** 09 One-Eyed Interloper — Fandom rate-limit persistente + IGN não tem página.

**Como usar a pipeline nova**:

```bash
python3 scripts/fetch_sources.py --quest-num 45    # 1 quest
python3 scripts/fetch_sources.py --all             # todas as Stage quests (~80s)
python3 scripts/check_cross_source.py              # diff
```

**Open scope (próxima sessão)**:

- **A) Push + abrir PR manual** — `feat/stage-2-recommended-flow` → `main` (9 commits). GitHub Actions rebuilda Pages automaticamente.
- **B) Fetch restante do Stage 2** — 14 quests ainda em 1/3 sources (apenas Fextralife via MD). Rodar `python3 scripts/fetch_sources.py --all` e re-check.
- **C) EN translations** — 41 files PT sem `.en.md` irmão (7 Main + 28 Side Stage 2 + 5 Locations + 1 MOC). Estimativa 4-6h manual.
- **D) Preencher `sources_verified: []`** — 11 side quests Stage 2 (10,11,12,13,14,16,18,20,25,28,30) + 3 com `needs_verification: true` (22, 27, 29).
- **E) Stage 3 bodies** — Main Quests 01-03 são frontmatter-only stubs; precisa de walkthrough/Objectives/Summary/Rewards.
- **F) Out of scope from batch #3**: 7 untranslated STRINGS keys (Main/Side Quests em PT), a11y, light/dark toggle, print CSS, OG meta, sitemap, PWA.

**Skipped nesta sessão (consciente)**:

- **IGN extractor para quest_giver** — IGN não usa template "Quest Giver" como Fandom, é texto solto. Extractor regex não acha. Próxima sessão: refinar regex com lookbehind ou usar BeautifulSoup.
- **Auto-update MD frontmatter** — você escolheu "mínimo"; checker reporta mas não escreve nos MDs.
- **Fandom rate-limit persistente** — sleep+retry ajuda mas IP-level block em rajada. Workaround futuro: proxy rotativo ou curl com `--cookie-jar` pra reusar sessão.

**Decidido nesta sessão**:

- ❌ `docs/REWRITE-PROPOSAL.md` (24KB, untracked) — deletado.
- ✅ Confiança no Fextralife para quests 01 e 02 (Fandom=None não é erro).

## Onde paramos (anterior — batch #4)

**What batch #4 did** (7 commits, este branch):

- **9dcc8c5** feat: stage 2 recommended flow + multi-part dividers (22 quests × PT+EN)
- **a149699** docs: re-encode pt.2 + pt.3 to match user 2026-07-08 detailed flow
- **50ee906** feat: 4 missing Stage 2 quest MDs + Ancient Battleground location + Stage 1 cross-stage prep
- **1606261** fix: wikilink Till Death Do Us Part is Side (not Main) in quests 45
- **e9ff6da** fix: Till Death wikilink in 45 Related body section
- **746d969** feat(quests): cross-source recompensas 45-48 (PT+EN) + wikilink 404 fixes em build.py — 98→0 broken hrefs
- **8332119** feat(stage-3): stub 3 transition Main Quests + Battahl location

**Cross-source recompensas (commit 746d969)**:

- 4/4 Fextralife OK (200), 3/4 IGN OK (46 = 404), Fandom 403 (w3m UA também, paywall mudou desde 2026-07-07)
- 45: 3.000 XP / 9.000 G / Ancient Battleground Key (Fextra) vs Ancient Cenotaph Key (IGN — divergência de nome)
- 46: branching — Eternal Wakestone (outcome vitorioso)
- 47: 4.500 XP + 18.500 G (perfeita) ou 7.000 G (mal)
- 48: 6.000 XP / 35.000 G / Unlocks: Steeled Resolve, Blazing Forge
- Bônus: 45 `quest_giver: Oscar` (Fextra image alt)
- All 4 stay `needs_verification: true` (1-2/3 sources only)

## Onde paramos (anterior — batch #3)

**What batch #3 did** (no game-research needed — code-only session):
- Added **Export / Import JSON** buttons next to Reset on every page. Modal with Cancel / Merge / Replace actions. Modal reports "X matched this build, Y unknown" so users importing from another stage see what's accepted.
- Wrapped `localStorage` schema in **v2** (`{ version: 2, updatedAt, checked: {...} }`). Auto-migrates from v1 on first read; keeps a v1 copy as a safety net for one release.
- Tightened `loadState()`: rejects arrays / nulls / non-objects; on JSON.parse error the corrupt value is **quarantined** under `dd2-tracker-v1.corrupt-{ts}` and the user gets a clean state. Same for malformed v2 payloads.
- Stage total no longer displays as `0/38/38` (the duplicated denominator bug). Now shows `34/39` cleanly.
- Diagnostic banner is **silent by default**; pass `?debug=1` to enable.
- Reset confirmation is now properly localized for PT users (was hard-coded English before).
- Removed the "marked marked" / "marcados marcados" duplication in i18n templates.
- `<html lang>` is set **synchronously** before first paint, so search engines and screen readers see the right language from frame 0.
- Added cross-tab `storage` event sync: two open tabs of the same page now stay in sync.
- Homepage progress bar counts only **known IDs** (build-time `data-known-ids` attribute) and clamps to 100%, so stale or imported keys can't inflate the numerator.
- Footer tip on stage pages no longer tells users to "copy the JSON from localStorage" — it now points at the new buttons.

**Out of scope for this PR** (next session candidates):
- 7 untranslated `STRINGS` keys (Main Quests / Side Quests in PT — visible chrome bug).
- a11y: focus-visible outlines, skip-link, prefers-reduced-motion, progressbar ARIA.
- Wiki-links: `[[Locations/Foo]]` 404, `[[Stage 3+]]` literal links 404, typos silently route to Stage 1.
- Light/dark theme toggle, print CSS, back-to-top, ?lang=pt URL param, OG/Twitter meta, sitemap, PWA.

## Onde paramos (anterior — batch #2)

## Onde paramos

> **Batch #2 committed**: `8db5337 feat: batch #2 — wikilink validator, QUEST_OVERRIDES refactor, cross-source check` on `feat/stage-2-bilingual`. Pushed to origin. **PR not opened yet** (token 403) — open manually at https://github.com/Mo3ses/dd2-walkthrough/compare/main...feat/stage-2-bilingual.

**What batch #2 did**:
- Fixed 56 broken `[[wiki-links]]` flagged by `scripts/check_wikilinks.py`.
- Dropped 35-entry `QUEST_OVERRIDES` dict — frontmatter is now source of truth.
- New `scripts/check_cross_source.py` extracts quest_giver/xp/gold from Fextralife + IGN + Fandom; found 10/15 disagreements (mostly Fextralife NPC gaps, 2 real gold conflicts on #36 and #43).

**Stage 1**: completo, no ar em <https://mo3ses.github.io/dd2-walkthrough/>.
**Stage 2**:
- Vault em PT — **todos os 35 walkthroughs preenchidos** (4 Main + 28 Side + 3 Locations com chain) nesta sessão, contra Fextralife. Build local já gera `dist/stage-2.html`.
- Cross-source audit attempted (IGN + Fandom) — ambos inacessíveis. 18 in-scope files flipadas pra `needs_verification: true`. Relatório em `docs/SOURCE-VERIFICATION-REPORT.md`.
- Locations TOC no `stage-N.html` foi redesignada de fileira-inline-cramped pra card-grid minimal (sem badges per-quest). Per-quest badges continuam nas per-location sections, onde o live JS atualiza.

## O que precisa de tradução EN (prioridade)

São **41 arquivos novos sem `.en.md` irmão**:

| Origem | Total |
|---|---|
| `Quests/Stage 2/Main Quests/*.md` | 7 |
| `Quests/Stage 2/Side Quests/*.md` | 28 |
| `Quests/Stage 2.md` (MOC) | 1 |
| `Quests/Locations/*.md` (sem `.en.md`) | 5 (Vernworth, Harve Village, Moonglow Garden, Eini's House, Sacred Arbor, Checkpoint Rest Town) |

Padrão de pareamento já existe no build (`*.md` ↔ `*.en.md` por stem). PT é fallback quando EN falta, então o site funciona, mas fica 100% PTBR.

### Workflow sugerido

Para cada PT file, criar o `.en.md` correspondente:

1. Copiar a estrutura (frontmatter + seções)
2. Traduzir títulos das seções PT → EN conforme a tabela em `CLAUDE.md`:
   - `## Objetivos` → `## Objectives`
   - `## Resumo` → `## Summary`
   - `## Recompensas` → `## Rewards`
   - `## Notas Importantes` → `## Important Notes`
3. Manter wiki-links `[[...]]` em inglês quando o destino já tem EN; senão manter como está
4. Frontmatter: copiar inteiro (keys PT ficam igual, valores mudam)

**Não precisa traduzir frontmatter `tags:`** — são keywords técnicas.

### Ordem recomendada

Priorizar os **Main Quests** primeiro (7), depois MOC, depois Locations, depois Side Quests em ordem numérica (10 → 43).

## Melhorias no build (opcional)

- **`.gitignore`**: adicionar `.obsidian/` (config local do editor)
- **`QUEST_OVERRIDES`**: crescer — 35 entries hardcoded hoje. Idealmente mover pro frontmatter dos MDs e cair o dict
- **Stage 3/4**: mesma estrutura, só criar `Quests/Stage 3/` + `Stage 4/` e o build auto-detecta
- **Validação de wiki-links**: script que checa todos os `[[...]]` contra files existentes e reporta broken links

## Cross-source verification (2026-07-07)

Tentativa de fechar o gap de single-source `[fextralife]` nas 18 quests Stage 2 que foram preenchidas nesta sessão. Resultado: **IGN e Fandom ambos inacessíveis** deste environment.

- IGN (18/18): erro `Claude Code is unable to fetch from www.ign.com` (block ao nível do harness, não 404).
- Fandom (18/18): HTTP 402 em todos os 3 patterns testados (`Title_With_Underscores`, `?action=raw`, e `Title_With_Pluses`) — paywall per-domain.

Ação tomada: `needs_verification` flipado de `false` para `true` em todas as 18 in-scope files; `sources_verified` continua `[fextralife]` (a fonte que efetivamente carregou). Esse flag agora codifica "tentou cross-source, blocked" — é mais honesto que o `false` anterior.

21/24/26 (que já eram `[fextralife, ign, user]`) ficaram **como estão** — a migration condicional para `[fandom, fextralife, ign, user]` exigia Fandom carregar, e não carregou.

Relatório completo: `docs/SOURCE-VERIFICATION-REPORT.md`.

**Follow-up single biggest lever:** Bash + `curl -A "Mozilla/5.0 (...)"` retry pra ambos IGN e Fandom. User-Agent de browser deve bypassar o anti-bot do IGN e o paywall do Fandom. Se isso passar:
- 18 in-scope files voltam a `needs_verification: false` + ganham `[fandom, fextralife, ign]` (se os 3 concordarem).
- 21/24/26 migram pra `[fandom, fextralife, ign, user]`.

**Deferred scope:** 11 side quests com `sources_verified: []` (10, 11, 12, 13, 14, 16, 18, 20, 25, 28, 30) + 3 com `needs_verification: true` e sources vazias (22, 27, 29) — fora do escopo desta sessão, mas abertas pra sweep futura.

## Como rodar local

```bash
# Clone (em outra máquina)
git clone <repo-url>
cd Dragons\ dogma

# Build
python3 scripts/build.py

# Preview (Linux)
xdg-open dist/index.html
# macOS: open dist/index.html

# Reset progresso no browser console:
# localStorage.removeItem("dd2-tracker-v1")
```

## Deploy

Push em `main` → GitHub Action (`.github/workflows/deploy.yml`) rebuilda e publica. Nada manual.

## Onde achar contexto

| Arquivo | Conteúdo |
|---|---|
| `CLAUDE.md` | Instruções completas do projeto, formato do vault, bilingual pattern |
| `Quests/Stage 2.md` | MOC com flowchart mermaid, prereq tables, NPCs, checklist |
| `scripts/build.py` (topo) | `STRINGS` dict com toda UI chrome EN/PT |
| `~/.claude/projects/.../memory/obsidian-vault-conventions.md` | Padrões Obsidian (callouts, frontmatter) |

## Caveats conhecidos

- **WebSearch quebrado** (API 400) — usar `curl` com User-Agent se precisar de pesquisa
- **WebFetch blocks** (2026-07-07): `www.ign.com` é blocked no nível do harness (`Claude Code is unable to fetch from www.ign.com`); `dragonsdogma.fandom.com` retorna HTTP 402 em todos os endpoints. Workaround em Bash: `curl -A "Mozilla/5.0 ..."`. Detalhes em `docs/SOURCE-VERIFICATION-REPORT.md`.
- Fextralife às vezes classifica Main como Side — IGN/Fandom divergem; já verificado e corrigido para 21/24/26
- "One-Eyed Interloper" (Stage 1, quest 09) tecnicamente dispara durante Stage 2 main quest — mantido em Stage 1 por organização, cross-linkado em `15 - Seat of the Sovran`

### Batch #3 recap
- Filled 6 `quest_giver: NPC desconhecido` placeholders in 12 MDs (6 PT + 6 EN) using Fandom + IGN HTMLs.
- Tightened `scripts/check_cross_source.py` regex:
  - `quest_giver` stops at next capitalized label (no more "Diana Quest Location Vernworth" bleed)
  - `gold` only matches structured `Reward <N> Gold` (Fandom) or completion-line `reward, <N> gold` near `completing` (IGN) — no more "buy the book for 5,000 G" false positives
- Result: `python3 scripts/check_cross_source.py` now reports **1 of 15 conflicts** (was 10). The 1 remaining (#15 "Brant / Sovran Disa" vs "Brant") is a Fextralife-vs-Fandom scope difference, not a factual conflict — MD preferred.

## Estado técnico atual

```bash
# Tudo verde:
python3 scripts/check_wikilinks.py        # OK: 1262 links across 113 files
python3 scripts/check_cross_source.py     # 1 of 15 conflicts (noise, not blocking)
python3 scripts/build.py                  # 44 per-quest pages, 0 errors
git status                                 # clean working tree on feat/stage-2-bilingual
```

## Próximas ações (escolher uma)

**A) Commit + abrir PR manual + parar** — 8 files cross-source (+76/-22) + 5 commits do branch. PR body: `feat: stage 2 recommended flow + 4 stub MDs + cross-source recompensas (45-48)`. ~3 min.

**B) 3 quests Stage 3 transition (decisão)** — A Noble Exchange, Nation of the Lambert Flame, A Veil of Gossamer. Sem Stage 3 dir existente. Opções:
- Criar `Quests/Stage 3/{Main,Side}/` + stubs frontmatter-only (mínimo 6 files) — parse_stage_flow para de pular
- Remover do MOC pt.3 até Stage 3 começar (limpa links, mas perde a referência narrativa)
- Deixar como broken link conhecido (status quo — documentado em MOC linha 23)

**C) EN translations** (próximo grande escopo) — 41 files PT sem `.en.md` irmão:
- 7 Stage 2 Main Quests: `15, 17, 21, 23, 24, 26, 44`
- 28 Stage 2 Side Quests: todos exceto `34, 35, 36` (já têm EN)
- 5 Locations: `Vernworth, Harve Village, Moonglow Garden, Eini's House, Sacred Arbor, Checkpoint Rest Town`
- 1 MOC: `Quests/Stage 2.en.md`
- Estimativa: 4-6h se manual, ou ~1h se script-assistido

**D) Preencher `sources_verified: []` vazios** — 11 Stage 2 side quests (10, 11, 12, 13, 14, 16, 18, 20, 25, 28, 30) + 3 com `needs_verification: true` (22, 27, 29). Pode usar `scripts/check_cross_source.py` como sanity check após preencher.

**E) Avaliar `docs/REWRITE-PROPOSAL.md`** — 24KB, untracked desde 2026-07-07 19:12. Lê, decide incorpora/deleta/refatora.

## Arquivos importantes para a próxima sessão

- `scripts/build.py` — gerador estático (não tocou desde batch #2)
- `scripts/check_wikilinks.py` — guardrail de links
- `scripts/check_cross_source.py` — guardrail de cross-source (regex tightened in batch #3)
- `docs/SOURCE-VERIFICATION-REPORT.md` — log completo de sourcing + conflicts
- `docs/NEXT-STEPS.md` — este arquivo
- `docs/REWRITE-PROPOSAL.md` (untracked, 24KB, criado 2026-07-07 19:12) — proposta manual sua, NÃO toquei. Decidir se incorpora ou deleta.

## Convenções para retomar

- Branch ativo: `feat/stage-2-recommended-flow`
- PT é source of truth. EN vem depois.
- Wikilink anchor syntax `[[Foo#heading]]` não é suportada pelo build — sempre linkar a página inteira.
- Frontmatter `location:` para `Locations/<name>` (não apenas `<name>`) para o validator passar.
- `quest_giver: NPC desconhecido` é placeholder; usar nome real quando souber.

## PR manual

Abrir em https://github.com/Mo3ses/dd2-walkthrough/compare/main...feat/stage-2-bilingual

Body sugerido:
```
## Batch #2 + #3 — wikilinks, QUEST_OVERRIDES refactor, NPC fills, regex tightening

3 commits, 58 files, ~660 insertions / 160 deletions.

See docs/NEXT-STEPS.md and docs/SOURCE-VERIFICATION-REPORT.md for full context.
```
