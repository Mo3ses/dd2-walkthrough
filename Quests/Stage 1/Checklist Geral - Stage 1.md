---
title: "Checklist Geral — Stage 1"
type: master-checklist
stage: 1
tags: [master-checklist, stage-1, mocs]
---

# ✅ Checklist Geral — Stage 1

> *"Um checklist para governar todos. Marque aqui e a sincronização mantém tudo coerente."*

> [!important] Como usar este arquivo
> Por padrão, este checklist funciona como qualquer outro (checkboxes manuais). Para **sincronização automática** entre o master e os quests individuais (parent ↔ sub-checkboxes), instale uma das opções:
>
> | Plugin | Função | Comando |
> |---|---|---|
> | **Checklist plugin** (delashment) | Cascade check/uncheck (parent ↔ children) | Marcar pai marca todos os filhos; marcar todos os filhos marca o pai |
> | **Obsidian Tasks** | Tasks com sintaxe `#task` + queries | Permite queries por quest específica |
> | **Dataview** | Queries dinâmicas de checkbox state | Mostra status sem alterar origem |
>
> Sem plugin, este master é uma visão consolidada — você pode marcar aqui E nos quests individuais manualmente.

> [!example] Layout usado
> ```markdown
> ### Quest Name
> - [ ] [[Main Quests/X - Quest Name]]      ← checkbox principal (cascateia para baixo)
>   - [ ] Objetivo 1                       ← sub-checkbox
>   - [ ] Objetivo 2
> ```

> [!info] Progresso automático
> A tabela em **[[_progress|Progresso Stage 1]]** é gerada automaticamente a cada deploy pelo script `scripts/generate_progress.py`. Ela lê os checkboxes da seção `## Objetivos` de cada quest e mostra contagens + status. Não precisa atualizar manualmente.

---

## ⚔️ Main Quests

### 01 - Gaoled Awakening
- [ ] [[Main Quests/01 - Gaoled Awakening]]
  - [ ] Siga a overseer
  - [ ] Pegue uma pedra
  - [ ] Carregue a pedra até Rook
  - [ ] Investigue o distúrbio
  - [ ] Mande a besta embora
  - [ ] Fuga pela sua vida

### 02 - Tale's Beginning
- [ ] [[Main Quests/02 - Tale's Beginning]]
  - [ ] Acompanhe o Pathfinder até a Cachoeira Ultramarine
  - [ ] Customize seu Main Pawn
  - [ ] Siga para Borderwatch

### 08 - In Dragon's Wake
- [ ] [[Main Quests/08 - In Dragon's Wake]]
  - [ ] Vá até Melve
  - [ ] Explore Melve
  - [ ] Fale com Lennart
  - [ ] Acompanhe Gregor até a capital
  - [ ] Chegue em Vernworth

---

## 🗡️ Side Quests — Borderwatch (faça antes de partir)

### 03 - Ordeal's of a New Recruit
- [ ] [[Side Quests/03 - Ordeal's of a New Recruit]]
  - [ ] Fale com Phill
  - [ ] Salve o irmão de Phill
  - [ ] Derrote as harpias
  - [ ] Reporte a Phill

### 04 - The Provisioner's Plight
- [ ] [[Side Quests/04 - The Provisioner's Plight]]
  - [ ] Fale com Geoffrey
  - [ ] Entregue a nota a Markus
  - [ ] Colete Harspuds
  - [ ] Craft Salubrious Draughts
  - [ ] Volte a Geoffrey

---

## 🗡️ Side Quests — Melve (durante In Dragon's Wake)

### 05 - Medicament Predicament
- [ ] [[Side Quests/05 - Medicament Predicament]]
  - [ ] Fale com Flora
  - [ ] Obtenha o Fruit Roborant
  - [ ] Entregue a Flora

### 06 - Brother's Brave and Timid
- [ ] [[Side Quests/06 - Brother's Brave and Timid]]
  - [ ] Fale com Ian
  - [ ] Escolte Ian até o ninho
  - [ ] Derrote os lobos
  - [ ] Resgate Norbert
  - [ ] Volte com os irmãos

### 07 - Nesting Troubles
- [ ] [[Side Quests/07 - Nesting Troubles]]
  - [ ] Fale com Lennart
  - [ ] Destrua os ovos com fogo
  - [ ] Pegue o veneno
  - [ ] Envenene o ninho
  - [ ] Reporte a Lennart

---

## 🐉 Side Quest — Estrada Melve → Vernworth

### 09 - One-Eyed Interloper
- [ ] [[Side Quests/09 - One-Eyed Interloper]]
  - [ ] Derrote o Ciclope
  - [ ] Mantenha Gregor vivo
  - [ ] Continue para Vernworth

---

## 📊 Progresso Total

> [!summary] Contadores rápidos
> Veja a tabela atualizada em **[[_progress|Progresso Stage 1]]** (gerada automaticamente pelo build).
>
> As contagens desta página (3 main + 6 side quests, 38 sub-objetivos totais) são estáticas — para valores ao vivo, use a página de progresso.

> [!note] Como funciona o auto-sync
> 1. Você marca/desmarca checkboxes na seção `## Objetivos` dos MDs das quests
> 2. Faz commit e push
> 3. O GitHub Actions roda `scripts/generate_progress.py`, que:
>    - Conta `- [x]` vs `- [ ]` na seção `## Objetivos` de cada quest
>    - Gera `Quests/Stage 1/_progress.md` com a tabela atualizada
>    - Publica como página acessível no site
> Não precisa manter contagens manualmente nesta página.

#dragon's dogma #stage-1 #master-checklist