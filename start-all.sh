#!/bin/bash
# 海外视频本地化 - 启动所有服务
export DYLD_LIBRARY_PATH="/opt/homebrew/opt/expat/lib:${DYLD_LIBRARY_PATH:-}"
export WORKBENCH_LAUNCHER=startup-cmd
cd /Users/apple/.openclaw/workspace/vl-workflow

# 启动主工作台
cd 海外视频本地化MVP
WORKBENCH_HOST=0.0.0.0 WORKBENCH_PORT=8788 .venv/bin/python -m app.main &
cd ..

# 启动 TikTok 采集器
cd tiktok_collector
.venv/bin/python tiktok_web_ui.py &
cd ..

wait
