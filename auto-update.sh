#!/bin/bash
# 自动拉取 GitHub 更新并重启服务
cd /Users/apple/.openclaw/workspace/vl-workflow

LOG="/tmp/vl-auto-update.log"
echo "$(date): Checking for updates..." >> "$LOG"

# Fetch and check for changes
git fetch origin main 2>/dev/null
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date): Updates found! Pulling..." >> "$LOG"
    
    # Pull changes
    git pull origin main 2>&1 >> "$LOG"
    
    # Install new dependencies if needed
    export DYLD_LIBRARY_PATH="/opt/homebrew/opt/expat/lib"
    
    cd 海外视频本地化MVP
    .venv/bin/pip install -q -r requirements.txt 2>/dev/null
    cd ..
    
    cd overseas-loc-mvp
    .venv/bin/pip install -q -r requirements.txt 2>/dev/null
    cd ..
    
    cd tiktok_collector
    .venv/bin/pip install -q -r requirements.txt 2>/dev/null
    cd ..
    
    # Restart services
    kill $(lsof -ti:8788) 2>/dev/null
    kill $(lsof -ti:8890) 2>/dev/null
    sleep 2
    
    cd 海外视频本地化MVP
    nohup env DYLD_LIBRARY_PATH="/opt/homebrew/opt/expat/lib" WORKBENCH_LAUNCHER=startup-cmd WORKBENCH_HOST=0.0.0.0 WORKBENCH_PORT=8788 .venv/bin/python -m app.main > /tmp/vl-workbench.log 2>&1 &
    cd ..
    
    cd tiktok_collector
    nohup env DYLD_LIBRARY_PATH="/opt/homebrew/opt/expat/lib" .venv/bin/python tiktok_web_ui.py > /tmp/vl-tiktok.log 2>&1 &
    cd ..
    
    echo "$(date): Services restarted!" >> "$LOG"
else
    echo "$(date): No updates." >> "$LOG"
fi
