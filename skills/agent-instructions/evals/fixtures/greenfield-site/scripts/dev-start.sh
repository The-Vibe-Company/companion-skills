#!/usr/bin/env bash
set -euo pipefail

port="${CONDUCTOR_PORT:-${PORT:-4200}}"
exec bun run dev --port "$port"

