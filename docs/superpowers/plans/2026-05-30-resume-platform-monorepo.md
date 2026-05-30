# Resume Platform Monorepo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge three independent projects (landing page, resume optimizer frontend, resume generator frontend, Python backend) into a single monorepo with one-command startup.

**Architecture:** Root `package.json` with npm workspaces (`apps/*`) + Turborepo for parallel frontend orchestration. Python backend lives in `backend/` alongside `apps/`, managed via `start.ps1` script that starts uvicorn then kicks off `turbo dev`.

**Tech Stack:** Turborepo, npm workspaces, Vite (landing-page), Vue 3 + Vite (optimizer), Next.js 16 (generator), FastAPI + uvicorn (backend)

---

### Task 1: Create monorepo directory and move source files

**Files:**
- Move: `C:\Users\Lenovo\Desktop\界面\resume-page.html` → `C:\Users\Lenovo\Desktop\resume-platform\apps\landing-page\index.html`
- Move: `C:\Users\Lenovo\Desktop\简历 (2)\简历\frontend\*` → `C:\Users\Lenovo\Desktop\resume-platform\apps\resume-optimizer\`
- Move: `C:\Users\Lenovo\Desktop\新建文件夹 (5)\offerlab\*` → `C:\Users\Lenovo\Desktop\resume-platform\apps\resume-generator\`
- Move: `C:\Users\Lenovo\Desktop\简历 (2)\简历\backend\*` → `C:\Users\Lenovo\Desktop\resume-platform\backend\`
- Move: `C:\Users\Lenovo\Desktop\界面\docs\*` → `C:\Users\Lenovo\Desktop\resume-platform\docs\`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p "C:\Users\Lenovo\Desktop\resume-platform\apps\landing-page"
mkdir -p "C:\Users\Lenovo\Desktop\resume-platform\apps\resume-optimizer"
mkdir -p "C:\Users\Lenovo\Desktop\resume-platform\apps\resume-generator"
mkdir -p "C:\Users\Lenovo\Desktop\resume-platform\backend"
mkdir -p "C:\Users\Lenovo\Desktop\resume-platform\docs"
```

- [ ] **Step 2: Move visitor-facing pages (landing-page)**

```powershell
Move-Item "C:\Users\Lenovo\Desktop\界面\resume-page.html" "C:\Users\Lenovo\Desktop\resume-platform\apps\landing-page\index.html"
```

- [ ] **Step 3: Move resume optimizer frontend (Vue + Vite)**

```powershell
Move-Item "C:\Users\Lenovo\Desktop\简历 (2)\简历\frontend\*" "C:\Users\Lenovo\Desktop\resume-platform\apps\resume-optimizer\" -Force
```

- [ ] **Step 4: Move resume generator (Next.js)**

```powershell
Move-Item "C:\Users\Lenovo\Desktop\新建文件夹 (5)\offerlab\*" "C:\Users\Lenovo\Desktop\resume-platform\apps\resume-generator\" -Force
```

- [ ] **Step 5: Move Python backend**

```powershell
Move-Item "C:\Users\Lenovo\Desktop\简历 (2)\简历\backend\*" "C:\Users\Lenovo\Desktop\resume-platform\backend\" -Force
```

- [ ] **Step 6: Move design docs**

```powershell
Move-Item "C:\Users\Lenovo\Desktop\界面\docs\*" "C:\Users\Lenovo\Desktop\resume-platform\docs\" -Recurse -Force
```

---

### Task 2: Create root `package.json` with npm workspaces

**Files:**
- Create: `C:\Users\Lenovo\Desktop\resume-platform\package.json`

- [ ] **Step 1: Write root package.json**

```json
{
  "private": true,
  "name": "resume-platform",
  "scripts": {
    "dev": "turbo dev",
    "dev:optimizer": "npm -w apps/resume-optimizer run dev",
    "dev:generator": "npm -w apps/resume-generator run dev",
    "dev:landing": "npm -w apps/landing-page run dev",
    "build": "turbo build",
    "clean": "turbo clean"
  },
  "workspaces": [
    "apps/*"
  ],
  "devDependencies": {
    "turbo": "^2.5.0"
  }
}
```

- [ ] **Step 2: Create .gitignore**

```gitignore
node_modules/
.turbo/
dist/
.next/
*.env.local
backend/.venv/
backend/__pycache__/
backend/**/__pycache__/
```

---

### Task 3: Create `turbo.json`

**Files:**
- Create: `C:\Users\Lenovo\Desktop\resume-platform\turbo.json`

- [ ] **Step 1: Write turbo.json**

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "dev": {
      "cache": false,
      "persistent": true,
      "dependsOn": []
    },
    "build": {
      "dependsOn": [],
      "outputs": ["dist/**", ".next/**"]
    },
    "clean": {
      "cache": false
    }
  }
}
```

---

### Task 4: Create landing-page Vite wrapper

**Files:**
- Create: `C:\Users\Lenovo\Desktop\resume-platform\apps\landing-page\package.json`
- Create: `C:\Users\Lenovo\Desktop\resume-platform\apps\landing-page\vite.config.ts`

- [ ] **Step 1: Write landing-page package.json**

```json
{
  "private": true,
  "name": "landing-page",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "devDependencies": {
    "vite": "^6.3.0"
  }
}
```

- [ ] **Step 2: Write vite.config.ts**

```ts
import { defineConfig } from "vite";

export default defineConfig({
  root: ".",
  server: {
    port: 3456,
    open: true,
  },
  build: {
    outDir: "dist",
  },
});
```

---

### Task 5: Update landing-page index.html links

**Files:**
- Modify: `C:\Users\Lenovo\Desktop\resume-platform\apps\landing-page\index.html`

- [ ] **Step 1: Read current index.html and ensure links are correct**

The page should already have:
- 我有简历 → `window.location.href='http://localhost:5173'`
- 没有简历 → `window.location.href='http://localhost:3000'`

Verify these links exist correctly after the file move.

---

### Task 6: Update ALLOWED_ORIGINS in backend .env

**Files:**
- Modify: `C:\Users\Lenovo\Desktop\resume-platform\backend\.env`

- [ ] **Step 1: Add landing-page origin to ALLOWED_ORIGINS**

Edit the `ALLOWED_ORIGINS` line in `.env`:

```
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:3456
```

---

### Task 7: Create `start.ps1` startup script

**Files:**
- Create: `C:\Users\Lenovo\Desktop\resume-platform\start.ps1`

- [ ] **Step 1: Write start.ps1**

```powershell
param(
  [switch]$NoBackend
)

Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║    Resume Platform - 一键启动         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

# ── Python Backend ──
if (-not $NoBackend) {
  Write-Host "[1/3] 启动 Python 后端..." -ForegroundColor Yellow

  # Check if venv exists
  $VenvDir = "$RootDir\backend\.venv"
  if (-not (Test-Path $VenvDir)) {
    Write-Host "  创建 Python venv..." -ForegroundColor Gray
    python -m venv $VenvDir
    & "$VenvDir\Scripts\pip" install -r "$RootDir\backend\requirements.txt"
  }

  # Start uvicorn in background
  $BackendLog = "$RootDir\backend\server.log"
  $Job = Start-Job -ScriptBlock {
    param($Dir, $Venv)
    $env:PYTHONPATH = $Dir
    & "$Venv\Scripts\python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  } -ArgumentList "$RootDir\backend", $VenvDir

  Write-Host "  Python 后端启动中 (localhost:8000)..." -ForegroundColor Gray

  # Wait for backend health check
  $Retries = 15
  $Ready = $false
  for ($i = 0; $i -lt $Retries; $i++) {
    try {
      $resp = Invoke-WebRequest -Uri "http://localhost:8000/docs" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
      if ($resp.StatusCode -eq 200) {
        $Ready = $true
        break
      }
    } catch {}
    Start-Sleep -Seconds 1
  }

  if ($Ready) {
    Write-Host "  ✅ Python 后端就绪 (localhost:8000)" -ForegroundColor Green
  } else {
    Write-Host "  ⚠️  后端启动超时，尝试继续..." -ForegroundColor Yellow
  }
}

# ── Frontends ──
Write-Host "[2/3] 安装前端依赖（如需）..." -ForegroundColor Yellow
npm install --silent 2>$null

Write-Host "[3/3] 并行启动所有前端服务..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Landing Page   → http://localhost:3456" -ForegroundColor Cyan
Write-Host "  简历优化助手    → http://localhost:5173" -ForegroundColor Cyan
Write-Host "  简历生成助手    → http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止所有服务" -ForegroundColor Gray
Write-Host ""

# Run turbo dev
npx turbo dev

# Cleanup backend job on exit
if (-not $NoBackend -and $Job) {
  Stop-Job $Job -ErrorAction SilentlyContinue
  Remove-Job $Job -ErrorAction SilentlyContinue
}
```

---

### Task 8: Install dependencies and verify

- [ ] **Step 1: Install root dependencies**

```powershell
cd "C:\Users\Lenovo\Desktop\resume-platform"
npm install
```

Expected: installs turbo and all workspace dependencies (`apps/*`).

- [ ] **Step 2: Install Python dependencies**

```powershell
cd "C:\Users\Lenovo\Desktop\resume-platform\backend"
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

- [ ] **Step 3: Run start script (test mode, no backend)**

```powershell
cd "C:\Users\Lenovo\Desktop\resume-platform"
.\start.ps1 -NoBackend
```

Verify:
- Landing page opens at http://localhost:3456
- Optimizer frontend at http://localhost:5173
- Generator frontend at http://localhost:3000
- Click cards on landing page → navigates to each service

- [ ] **Step 4: Full test with backend**

```powershell
cd "C:\Users\Lenovo\Desktop\resume-platform"
.\start.ps1
```

Verify:
- Backend health check at http://localhost:8000/docs
- All three frontends accessible

---

### Post-Migration Cleanup

After verification, the old directories can be archived:

- `C:\Users\Lenovo\Desktop\界面\` — no longer needed (content in resume-platform)
- `C:\Users\Lenovo\Desktop\简历 (2)\` — no longer needed (content moved)
- `C:\Users\Lenovo\Desktop\新建文件夹 (5)\` — no longer needed (content moved)

Keep the files for a week as backup, then delete.
