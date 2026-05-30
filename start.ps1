param(
  [switch]$NoBackend,
  [switch]$NoFrontend
)

$Host.UI.RawUI.WindowTitle = "Resume Platform"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Resume Platform - Yi Jian Qi Dong    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir
$BackendPid = $null

# ---- Python Backend ----
if (-not $NoBackend) {
  Write-Host "[1/3] Qi Dong Python Hou Duan..." -ForegroundColor Yellow

  $VenvDir = "$RootDir\backend\.venv"
  if (-not (Test-Path $VenvDir)) {
    Write-Host "  Chuang Jian Python venv..." -ForegroundColor Gray
    python -m venv $VenvDir
    Write-Host "  An Zhuang Yi Lai..." -ForegroundColor Gray
    & "$VenvDir\Scripts\pip" install -r "$RootDir\backend\requirements.txt" --quiet 2>&1 | Out-Null
  }

  # Start backend in a visible separate window
  $BackendJob = Start-Process powershell -PassThru -WindowStyle Normal -ArgumentList "-NoExit", "-File", "$RootDir\_run_backend.ps1", "$RootDir"
  $BackendPid = $BackendJob.Id
  Write-Host "  Hou Duan Chuang Kou Yi Da Kai (PID: $BackendPid)..." -ForegroundColor Gray

  # Health check
  Write-Host "  Deng Dai Hou Duan Jiu Xu" -NoNewline -ForegroundColor Gray
  $Ready = $false
  for ($i = 0; $i -lt 20; $i++) {
    try {
      $resp = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
      if ($resp.StatusCode -eq 200) {
        $Ready = $true
        break
      }
    } catch {}
    Write-Host "." -NoNewline -ForegroundColor Gray
    Start-Sleep -Seconds 1
  }

  Write-Host ""
  if ($Ready) {
    Write-Host "  [OK] Python Hou Duan Jiu Xu (http://localhost:8000)" -ForegroundColor Green
    Write-Host "  [i] Hou Duan Ri Zhi Zai Du Li Chuang Kou Zhong" -ForegroundColor Cyan
  } else {
    Write-Host "  [!] Hou Duan Qi Dong Chao Shi" -ForegroundColor Yellow
  }
}

# ---- Frontends ----
if (-not $NoFrontend) {
  Write-Host "[2/3] An Zhuang Qian Duan Yi Lai (Ru Xu)..." -ForegroundColor Yellow
  npm install --silent 2>$null

  Write-Host "[3/3] Bing Xing Qi Dong Suo You Qian Duan Fu Wu..." -ForegroundColor Yellow
  Write-Host ""
  Write-Host "  +---------------------+------------------+" -ForegroundColor Cyan
  Write-Host "  | Ru Kou Ye            | localhost:3456   |" -ForegroundColor Cyan
  Write-Host "  | Jian Li You Hua Zhu  | localhost:5173   |" -ForegroundColor Cyan
  Write-Host "  | Jian Li Sheng Cheng   | localhost:3000   |" -ForegroundColor Cyan
  Write-Host "  +---------------------+------------------+" -ForegroundColor Cyan
  Write-Host ""
  Write-Host "An Ctrl+C Ting Zhi Suo You Fu Wu" -ForegroundColor Gray
  Write-Host ""

  npx turbo dev
}

# ---- Cleanup ----
if ($BackendPid) {
  Write-Host "Guan Bi Hou Duan Fu Wu..." -ForegroundColor Yellow
  Stop-Process -Id $BackendPid -Force -ErrorAction SilentlyContinue
  Write-Host "Hou Duan Fu Wu Yi Guan Bi" -ForegroundColor Green
}
