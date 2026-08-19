#!/usr/bin/env bash
set -euo pipefail
if [ ! -L AGENTS.md ]; then
  ln -sf CLAUDE.md AGENTS.md
fi

