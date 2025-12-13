#!/bin/bash
cd "$(dirname "$0")"
PYTHONPATH="." .venv/bin/python -m clipper.tui "$@"
