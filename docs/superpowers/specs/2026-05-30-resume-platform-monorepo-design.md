# Resume Platform Monorepo Design

## Overview

Merge three separate projects (resume landing page, resume optimizer, resume generator) into a single monorepo with one-command startup. The optimizer's Python backend lives in the same repo but managed separately from the JS frontends.

## Architecture

```
resume-platform/
├── apps/
│   ├── landing-page/              # Resume entry page (static HTML + Vite wrapper)
│   ├── resume-optimizer/          # Vue 3 + Vite frontend (port 5173)
│   └── resume-generator/          # Next.js 16 (port 3000)
├── backend/                       # FastAPI Python backend (port 8000)
├── package.json                   # Root: npm workspaces + turbo
├── turbo.json                     # Parallel task orchestration
├── start.ps1                      # One-click startup (Windows)
└── start.sh                       # One-click startup (Mac/Linux)
```

## Tech Stack

| Component | Stack | Port |
|-----------|-------|------|
| landing-page | Static HTML + Vite dev server | 3456 |
| resume-optimizer | Vue 3 + Vite | 5173 |
| resume-generator | Next.js 16 + TypeScript | 3000 |
| backend | FastAPI + uvicorn | 8000 |
| Orchestration | Turborepo + npm workspaces | - |

## Directory Migration

| Source | Destination |
|--------|------------|
| `桌面/界面/resume-page.html` | `apps/landing-page/index.html` |
| `桌面/简历 (2)/简历/frontend/` | `apps/resume-optimizer/` |
| `桌面/新建文件夹 (5)/offerlab/` | `apps/resume-generator/` |
| `桌面/简历 (2)/简历/backend/` | `backend/` |

## Integration Points

- **Entry page links**: `landing-page/index.html` links to `localhost:5173` (optimizer) and `localhost:3000` (generator) — unchanged
- **CORS**: Backend `ALLOWED_ORIGINS` env var expanded to include all frontend origins
- **Shared state**: No shared runtime state between services; each is independent

## Startup Flow

1. `npm install` in root installs all workspace dependencies
2. `pip install -r backend/requirements.txt` installs Python deps
3. `./start.ps1`:
   a. Activates Python venv, starts uvicorn on port 8000 (background)
   b. Waits for backend health check
   c. Runs `turbo dev` — parallel launches of all 3 frontends

## Files to Create

- `resume-platform/package.json` — npm workspaces config
- `resume-platform/turbo.json` — Turborepo task definitions
- `resume-platform/apps/landing-page/package.json` — Vite dev dependency
- `resume-platform/apps/landing-page/vite.config.ts` — Static file server config
- `resume-platform/start.ps1` — Windows startup script
- `resume-platform/start.sh` — Unix startup script

## Exclusions

- Python backend stays as-is; no monorepo tooling touches it
- No code changes to existing Vue, Next.js, or FastAPI logic
