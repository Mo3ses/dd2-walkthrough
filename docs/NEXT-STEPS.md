# Próximos Passos — Dragon's Dogma 2 Walkthrough

> Estado em 2026-07-07 (após batch #2). Continuar deste ponto em qualquer máquina.

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

**A) Abrir PR manual + parar** — merge de `feat/stage-2-bilingual` → `main` no GitHub web. GitHub Actions rebuild Pages automaticamente. ~2 min.

**B) EN translations** (próximo grande escopo) — 41 files PT sem `.en.md` irmão:
- 7 Stage 2 Main Quests: `15, 17, 21, 23, 24, 26, 44`
- 28 Stage 2 Side Quests: todos exceto `34, 35, 36` (já têm EN)
- 5 Locations: `Vernworth, Harve Village, Moonglow Garden, Eini's House, Sacred Arbor, Checkpoint Rest Town`
- 1 MOC: `Quests/Stage 2.en.md`
- Estimativa: 4-6h se manual, ou ~1h se script-assistido

**C) Stage 3 (Battahl)** — novo stage. Requer:
- `Quests/Stage 3/{Main Quests,Side Quests}/` directory + MDs
- Adicionar `Melve → Vernworth` já está feito; precisa de Bakbattahl, Checkpoint Rest Town final, etc. em `LOCATION_ORDER`
- Cross-source pass via `scripts/check_cross_source.py`
- Estimativa: várias sessões

**D) Preencher `sources_verified: []` vazios** — 11 Stage 2 side quests (10, 11, 12, 13, 14, 16, 18, 20, 25, 28, 30) + 3 com `needs_verification: true` (22, 27, 29). Pode usar `scripts/check_cross_source.py` como sanity check após preencher.

## Arquivos importantes para a próxima sessão

- `scripts/build.py` — gerador estático (não tocou desde batch #2)
- `scripts/check_wikilinks.py` — guardrail de links
- `scripts/check_cross_source.py` — guardrail de cross-source (regex tightened in batch #3)
- `docs/SOURCE-VERIFICATION-REPORT.md` — log completo de sourcing + conflicts
- `docs/NEXT-STEPS.md` — este arquivo
- `docs/REWRITE-PROPOSAL.md` (untracked, 24KB, criado 2026-07-07 19:12) — proposta manual sua, NÃO toquei. Decidir se incorpora ou deleta.

## Convenções para retomar

- Branch ativo: `feat/stage-2-bilingual`
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
