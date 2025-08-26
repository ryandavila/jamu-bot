#!/bin/bash
# Production runner script

export JAMU_ENV=prod
uv run python bot.py

