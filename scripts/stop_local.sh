#!/bin/bash
# 停止本地分布式VDS系统

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# PID文件目录
PID_DIR="$PROJECT_ROOT/pids"

echo "停止分布式VDS系统..."

# 停止DO服务器
if [ -f "$PID_DIR/do.pid" ]; then
    PID=$(cat "$PID_DIR/do.pid")
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止DO服务器 (PID: $PID)..."
        kill $PID
        rm "$PID_DIR/do.pid"
    else
        echo "DO服务器未运行"
        rm "$PID_DIR/do.pid"
    fi
else
    echo "DO服务器PID文件不存在"
fi

# 停止SS服务器
if [ -f "$PID_DIR/ss.pid" ]; then
    PID=$(cat "$PID_DIR/ss.pid")
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止SS服务器 (PID: $PID)..."
        kill $PID
        rm "$PID_DIR/ss.pid"
    else
        echo "SS服务器未运行"
        rm "$PID_DIR/ss.pid"
    fi
else
    echo "SS服务器PID文件不存在"
fi

# 停止Verifier服务器
if [ -f "$PID_DIR/verifier.pid" ]; then
    PID=$(cat "$PID_DIR/verifier.pid")
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止Verifier服务器 (PID: $PID)..."
        kill $PID
        rm "$PID_DIR/verifier.pid"
    else
        echo "Verifier服务器未运行"
        rm "$PID_DIR/verifier.pid"
    fi
else
    echo "Verifier服务器PID文件不存在"
fi

echo "所有服务器已停止"
