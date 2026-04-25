#!/usr/bin/env bash
# Run frontend code-quality checks.
# Usage:
#   ./frontend-quality.sh          # check formatting (CI mode)
#   ./frontend-quality.sh --fix    # auto-fix formatting in place

set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "$0")/frontend" && pwd)"

cd "$FRONTEND_DIR"

# Install dev dependencies if node_modules is missing
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dev dependencies..."
    npm install
fi

if [ "${1:-}" = "--fix" ]; then
    echo "Formatting frontend files with Prettier..."
    npx prettier --write "*.{html,js,css}"
    echo "Done."
else
    echo "Checking frontend formatting with Prettier..."
    npx prettier --check "*.{html,js,css}"
    echo "All frontend quality checks passed."
fi
