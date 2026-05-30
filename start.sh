#!/bin/bash
set -e

echo "╔══════════════════════════════════════╗"
echo "║    Resume Platform - One-Click Start ║"
echo "╚══════════════════════════════════════╝"
echo ""

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# ── Python Backend ──
if [ "$1" != "--no-backend" ]; then
  echo "[1/3] Starting Python backend..."

  VENV_DIR="$ROOT_DIR/backend/.venv"
  if [ ! -d "$VENV_DIR" ]; then
    echo "  Creating Python venv..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -r "$ROOT_DIR/backend/requirements.txt" > /dev/null 2>&1
  fi

  # Start uvicorn in background
  cd "$ROOT_DIR/backend"
  PYTHONPATH="$ROOT_DIR/backend" "$VENV_DIR/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
  BACKEND_PID=$!
  cd "$ROOT_DIR"

  echo "  Python backend starting (localhost:8000)..."

  # Wait for backend health check
  for i in $(seq 1 15); do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>/dev/null | grep -q 200; then
      echo "  ✅ Python backend ready (localhost:8000)"
      break
    fi
    sleep 1
  done
fi

# ── Frontends ──
echo "[2/3] Installing frontend dependencies..."
npm install --silent 2>/dev/null

echo "[3/3] Starting all frontend services in parallel..."
echo ""
echo "  Landing Page   → http://localhost:3456"
echo "  Resume Optimizer → http://localhost:5173"
echo "  Resume Generator → http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Run turbo dev
npx turbo dev

# Cleanup
if [ "$1" != "--no-backend" ] && [ -n "$BACKEND_PID" ]; then
  kill $BACKEND_PID 2>/dev/null
fi
