#!/bin/bash
# Quick launcher - auto-creates venv if needed
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "Setting up venv..."
    python3 -m venv .venv
    .venv/bin/pip install -e . -q
fi

exec .venv/bin/clipper "$@"
