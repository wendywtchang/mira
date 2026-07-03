#!/usr/bin/env bash
# MIRA production 啟動腳本（Render 用）
# 架構跟本地 run_mira.py 一樣：Django 後端（僅 localhost）+ Chainlit 前端（對外）
set -e
cd "$(dirname "$0")/.."

# ── Django 後端：只綁 127.0.0.1，外部無法直接存取，只有 Chainlit 打得到 ──
gunicorn --chdir mira_backend mira_backend.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 1 --threads 4 \
    --timeout 120 &

# ── 等 Django health check 通過再起前端 ──
echo "Waiting for Django backend..."
for i in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:8000/api/v1/health/ > /dev/null 2>&1; then
        echo "Django backend is ready."
        break
    fi
    sleep 2
done

# ── Chainlit 前端：綁 Render 提供的 $PORT，這是唯一對外的服務 ──
cd mira_frontend
exec chainlit run app.py --host 0.0.0.0 --port "${PORT:-8501}" --headless
