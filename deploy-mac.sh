#!/bin/bash
# 海外视频本地化 - macOS 内网部署脚本
set -e
cd "$(dirname "$0")"

# macOS Sequoia 需要设置 expat 路径
export DYLD_LIBRARY_PATH="/opt/homebrew/opt/expat/lib:${DYLD_LIBRARY_PATH:-}"

echo ""
echo "  海外视频本地化 · 内网部署启动"
echo "  ─────────────────────────────────────"
echo ""

# 设置默认值
export WORKBENCH_HOST=${WORKBENCH_HOST:-0.0.0.0}
export WORKBENCH_PORT=${WORKBENCH_PORT:-8788}

# 获取本机 IP
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)

echo "  主工作台：http://${LOCAL_IP}:${WORKBENCH_PORT}"
echo "  TikTok 采集器：http://${LOCAL_IP}:8890"
echo ""

# 启动主工作台（后台）
echo "  [1/2] 启动主工作台 (端口 ${WORKBENCH_PORT})..."
cd 海外视频本地化MVP
WORKBENCH_HOST=$WORKBENCH_HOST WORKBENCH_PORT=$WORKBENCH_PORT .venv/bin/python -m app.main &
WORKBENCH_PID=$!
cd ..

# 等待主工作台启动
sleep 3

# 启动 TikTok 采集器（后台）
echo "  [2/2] 启动 TikTok 采集器 (端口 8890)..."
cd tiktok_collector
.venv/bin/python tiktok_web_ui.py &
TIKTOK_PID=$!
cd ..

echo ""
echo "  ✅ 服务已启动"
echo "  主工作台 PID: $WORKBENCH_PID"
echo "  TikTok 采集器 PID: $TIKTOK_PID"
echo ""
echo "  访问地址："
echo "  - 主工作台: http://${LOCAL_IP}:${WORKBENCH_PORT}"
echo "  - TikTok 采集器: http://${LOCAL_IP}:8890"
echo ""
echo "  按 Ctrl+C 停止所有服务"

# 等待子进程
trap "kill $WORKBENCH_PID $TIKTOK_PID 2>/dev/null; exit 0" INT TERM
wait
