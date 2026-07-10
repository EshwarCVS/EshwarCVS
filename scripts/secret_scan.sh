#!/usr/bin/env bash
# Mirror CI secret-scan job locally (same tool as .github/workflows/profile.yml)
set -euo pipefail

cd "$(dirname "$0")/.."

echo "🔒 Running leash-secrets scan (same as GitHub Actions)..."
npx --yes leash-secrets@1.2.1 scan . "$@"
