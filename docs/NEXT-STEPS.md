# Próximos Passos — Dragon's Dogma 2 Walkthrough

> Estado em 2026-07-07. Continuar deste ponto em qualquer máquina.

## Onde paramos

> Uncommitted changes from the 2026-07-07 session — review with `git status` before continuing. Last committed: `41817bf feat: stage 2 vault + multi-stage build support`.

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