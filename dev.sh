#!/usr/bin/env bash

set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_pid=""
frontend_pid=""

cleanup() {
  trap - EXIT INT TERM

  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill "$backend_pid" 2>/dev/null || true
  fi

  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    kill "$frontend_pid" 2>/dev/null || true
  fi

  wait "$backend_pid" "$frontend_pid" 2>/dev/null || true
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

check_port() {
  local port="$1"

  if command -v lsof >/dev/null 2>&1 && \
     lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "Port $port is already in use. Stop the existing server and try again."
  fi
}

[[ -x "$project_dir/.venv/bin/python" ]] || \
  fail "Python environment not found. Follow the Local setup steps in README.md."

[[ -f "$project_dir/backend/.env" ]] || \
  fail "backend/.env not found. Run: cp backend/.env.example backend/.env"

[[ -x "$project_dir/frontend/node_modules/.bin/next" ]] || \
  fail "Frontend dependencies not found. Run: cd frontend && npm ci"

check_port 8000
check_port 3000

trap cleanup EXIT INT TERM

printf 'Starting backend at http://localhost:8000\n'
(
  cd "$project_dir/backend"
  exec ../.venv/bin/python -m uvicorn api.main:app --reload --port 8000
) &
backend_pid=$!

printf 'Starting frontend at http://localhost:3000\n'
(
  cd "$project_dir/frontend"
  exec npm run dev
) &
frontend_pid=$!

printf 'Press Ctrl+C to stop both servers.\n\n'

while kill -0 "$backend_pid" 2>/dev/null && \
      kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

fail "A development server stopped unexpectedly."
