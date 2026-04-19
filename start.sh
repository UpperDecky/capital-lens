#!/usr/bin/env bash
# start.sh — run Capital Lens locally
# Usage: bash start.sh
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Check .env
if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "⚠️  Created .env from .env.example — add your ANTHROPIC_API_KEY to enable AI enrichment."
fi

# Install Python deps if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "[setup] Installing Python dependencies..."
  pip install -r "$ROOT/requirements.txt"
fi

# Install frontend deps if needed
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "[setup] Installing frontend dependencies..."
  cd "$ROOT/frontend" && npm install --legacy-peer-deps && cd "$ROOT"
fi

echo ""
echo "Starting Capital Lens..."
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo "  API Docs → http://localhost:8000/docs"
echo ""

# Start backend
cd "$ROOT"
python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

# Trap Ctrl+C to stop both
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

echo "Press Ctrl+C to stop."
wait
