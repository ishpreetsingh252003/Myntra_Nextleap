#!/usr/bin/env sh
# Render start command wrapper (uses gunicorn workers + uvicorn worker).
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
