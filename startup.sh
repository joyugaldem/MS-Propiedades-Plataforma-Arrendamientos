#!/bin/bash
set -e

# Find Oryx extraction dir (must have app/main.py)
APP_DIR=""
for d in $(find /tmp -maxdepth 1 -mindepth 1 -type d 2>/dev/null); do
    if [ -f "$d/app/main.py" ]; then
        APP_DIR="$d"
        break
    fi
done
APP_DIR=${APP_DIR:-/home/site/wwwroot}

echo "[startup] APP_DIR=$APP_DIR"
ls "$APP_DIR"
cd "$APP_DIR"

export PYTHONPATH="$APP_DIR/vendor:$APP_DIR:${PYTHONPATH:-}"
export PATH="$APP_DIR/vendor/bin:$PATH"

echo "[startup] Launching gunicorn..."
exec python -m gunicorn app.main:app \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
