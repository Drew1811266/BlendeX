#!/usr/bin/env bash
set -euo pipefail
PYTHONPATH=src:. python3 -m unittest discover -s tests -t . -v
