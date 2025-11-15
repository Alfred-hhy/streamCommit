#!/bin/bash
# 启动本地分布式VDS系统（3个进程）

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 日志目录
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# PID文件目录
PID_DIR="$PROJECT_ROOT/pids"
mkdir -p "$PID_DIR"

echo "启动分布式VDS系统..."
echo "项目根目录: $PROJECT_ROOT"
echo "日志目录: $LOG_DIR"

# 启动DO服务器
echo "启动DO服务器 (端口 5001)..."
cd "$PROJECT_ROOT"
nohup python -m distributed.do_server > "$LOG_DIR/do.log" 2>&1 &
echo $! > "$PID_DIR/do.pid"
echo "DO服务器 PID: $(cat $PID_DIR/do.pid)"

# 等待DO启动
sleep 2

# 启动SS服务器
echo "启动SS服务器 (端口 5002)..."
cd "$PROJECT_ROOT"
nohup python -m distributed.ss_server > "$LOG_DIR/ss.log" 2>&1 &
echo $! > "$PID_DIR/ss.pid"
echo "SS服务器 PID: $(cat $PID_DIR/ss.pid)"

# 等待SS启动
sleep 2

# 启动Verifier服务器
echo "启动Verifier服务器 (端口 5003)..."
cd "$PROJECT_ROOT"
nohup python -m distributed.verifier_server > "$LOG_DIR/verifier.log" 2>&1 &
echo $! > "$PID_DIR/verifier.pid"
echo "Verifier服务器 PID: $(cat $PID_DIR/verifier.pid)"

# 等待Verifier启动
sleep 2

echo ""
echo "所有服务器启动完成！"
echo "查看日志: tail -f $LOG_DIR/*.log"
echo "停止服务器: $SCRIPT_DIR/stop_local.sh"
