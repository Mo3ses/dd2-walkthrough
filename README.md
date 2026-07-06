# Dragon's Dogma 2 — Walkthrough

Walkthrough interativo de Dragon's Dogma 2 em português, organizado por stage de progressão (Stage 1 → 4 + NG+).

Site: **https://mo3ses.github.io/dd2-walkthrough/**

## Estrutura

```
Quests/
├── Locations/         ← 4 local files (Excavation Site, Ultramarine, Borderwatch, Melve)
├── Stage 1/
│   ├── Main Quests/   ← 3 main quest files
│   ├── Side Quests/   ← 6 side quest files
│   └── Checklist Geral - Stage 1.md  (opcional, MOC agregadora)
└── Stage 2/...        (futuro)
scripts/
└── build.py           ← gera dist/*.html self-contained
.github/workflows/
└── deploy.yml         ← Python build → GitHub Pages
```

## Como funciona

- **Source**: arquivos MD plain (sem syntax proprietária). Organize no Obsidian ou em qualquer editor.
- **Build**: `python3 scripts/build.py` lê `Quests/` e gera `dist/` com HTML self-contained.
- **Output**: cada `dist/*.html` é um arquivo standalone com HTML + CSS + JS inline. Abre direto no browser, sem servidor, sem build step em runtime.
- **Persistência**: checkboxes usam `localStorage["dd2-tracker-v1"]` com IDs determinísticos (`s{stage}-{main|side}-{NN}-{i}`).

## Editar

1. Edite qualquer `.md` em `Quests/`
2. Rode `python3 scripts/build.py` localmente (ou só push)
3. O GitHub Actions rebuilda e deploya

## Local preview

```bash
python3 scripts/build.py
xdg-open dist/stage-1.html   # ou browser de sua preferência
```

## Resetar progresso

No console do navegador:
```js
localStorage.removeItem("dd2-tracker-v1")
```

Sem deps, sem build step em runtime, sem plugins. Só Python e Markdown.
