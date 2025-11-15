#!/bin/bash

##############################################################################
# VDS 多机部署 - 机器3 (Verifier Server) 一键部署脚本
#
# 这是一个完整的一键化部署脚本，自动处理所有部署步骤。
#
# 前置要求:
#   - init-environment.sh 已成功运行
#   - Docker 已安装和配置
#
# 使用方法:
#   chmod +x deploy-machine-3.sh
#   ./deploy-machine-3.sh <do_ip> <ss_ip> <your_ip>
#
# 示例:
#   ./deploy-machine-3.sh 192.168.1.10 192.168.1.20 192.168.1.30
#
# 脚本功能:
#   ✓ 克隆/更新项目代码
#   ✓ 生成 docker-compose.yml
#   ✓ 构建 Docker 镜像
#   ✓ 启动 Docker 服务
#   ✓ 验证服务运行状态
#   ✓ 运行健康检查
#
##############################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 打印函数
print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}➜${NC} $1"
}

# 检查参数
if [ $# -ne 3 ]; then
    echo "使用方法: $0 <do_ip> <ss_ip> <your_ip>"
    echo ""
    echo "参数说明:"
    echo "  do_ip:      DO Server 的 IP 地址"
    echo "  ss_ip:      SS Server 的 IP 地址"
    echo "  your_ip:    本机 IP 地址 (Verifier Server)"
    echo ""
    echo "示例:"
    echo "  ./deploy-machine-3.sh 192.168.1.10 192.168.1.20 192.168.1.30"
    exit 1
fi

DO_IP=$1
SS_IP=$2
VERIFIER_IP=$3

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_header "VDS Verifier Server (机器3) 一键部署"

echo "配置参数:"
echo "  DO Server IP:       $DO_IP"
echo "  SS Server IP:       $SS_IP"
echo "  Verifier Server IP: $VERIFIER_IP"
echo ""

# 确认
read -p "配置是否正确？(y/n) [y]: " confirm
confirm="${confirm:-y}"

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    print_error "已取消部署"
    exit 1
fi

echo ""

# ============================================================================
# 第1步：检查前置环境
# ============================================================================

print_header "第1步: 检查前置环境"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker 未安装，请先运行 init-environment.sh"
    exit 1
fi
print_info "✓ Docker 已安装"

# 检查 docker-compose
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose 未安装，请先运行 init-environment.sh"
    exit 1
fi
print_info "✓ docker-compose 已安装"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 未安装，请先运行 init-environment.sh"
    exit 1
fi
print_info "✓ Python 3 已安装"

# ============================================================================
# 第2步：克隆/更新项目代码
# ============================================================================

print_header "第2步: 克隆/更新项目代码"

cd "$SCRIPT_DIR"

if [ -d ".git" ]; then
    print_step "更新现有代码..."
    git pull origin main 2>/dev/null || print_warn "Git pull 失败，继续使用现有代码"
else
    print_warn "未检测到 git 仓库，假设代码已存在"
fi

print_info "✓ 项目代码就绪"

# ============================================================================
# 第3步：生成 docker-compose.yml
# ============================================================================

print_header "第3步: 生成 docker-compose.yml"

print_step "生成 Verifier Server 配置文件..."

cat > "$SCRIPT_DIR/docker-compose.yml" << EOF
version: '3.8'

services:
  verifier-server:
    build: .
    container_name: vds-verifier-server
    command: python3 -m distributed.verifier_server
    ports:
      - "0.0.0.0:5003:5003"
    environment:
      - VERIFIER_HOST=0.0.0.0
      - VERIFIER_PORT=5003
      - DO_HOST=$DO_IP
      - DO_PORT=5001
      - SS_HOST=$SS_IP
      - SS_PORT=5002
      - DEV_MODE=true
      - VECTOR_DIM=16
      - PAIRING_CURVE=MNT224
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  default:
    name: vds-network
EOF

print_info "✓ docker-compose.yml 生成完成"

# ============================================================================
# 第4步：构建 Docker 镜像
# ============================================================================

print_header "第4步: 构建 Docker 镜像"

print_warn "⚠ 首次构建可能需要 10-15 分钟，请耐心等待..."
print_step "开始构建镜像..."

if docker build -t vds-app:latest .; then
    print_info "✓ Docker 镜像构建成功"
else
    print_error "镜像构建失败，请检查构建日志"
    exit 1
fi

# ============================================================================
# 第5步：停止旧的服务（如果存在）
# ============================================================================

print_header "第5步: 清理旧的服务"

if docker-compose ps 2>/dev/null | grep -q vds-verifier-server; then
    print_step "停止旧的服务..."
    docker-compose down 2>/dev/null || true
    sleep 2
fi

print_info "✓ 旧的服务已清理"

# ============================================================================
# 第6步：启动 Docker 服务
# ============================================================================

print_header "第6步: 启动 Docker 服务"

print_step "启动 Verifier Server..."

if docker-compose up -d; then
    print_info "✓ 服务已启动"
else
    print_error "服务启动失败"
    exit 1
fi

# 等待容器完全启动
print_step "等待容器启动..."
sleep 5

# ============================================================================
# 第7步：验证服务状态
# ============================================================================

print_header "第7步: 验证服务状态"

print_step "检查容器状态..."
docker-compose ps

# ============================================================================
# 第8步：运行健康检查
# ============================================================================

print_header "第8步: 运行健康检查"

MAX_RETRIES=30
RETRY_COUNT=0

print_step "检查 Verifier Server 健康状态..."

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:5003/health > /dev/null 2>&1; then
        print_info "✓ Verifier Server 健康检查通过"
        curl -s http://localhost:5003/health | python3 -m json.tool
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        print_warn "健康检查失败（$RETRY_COUNT/$MAX_RETRIES），重试中..."
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "Verifier Server 健康检查失败"
    print_info "查看日志："
    docker-compose logs verifier-server
    exit 1
fi

# ============================================================================
# 第9步：测试其他服务的连接性
# ============================================================================

print_header "第9步: 测试其他服务的连接性"

print_step "测试到 DO Server ($DO_IP:5001) 的连接..."
if curl -s http://$DO_IP:5001/health > /dev/null 2>&1; then
    print_info "✓ DO Server 可访问"
else
    print_warn "⚠ DO Server 暂无响应（可能还未启动）"
fi

print_step "测试到 SS Server ($SS_IP:5002) 的连接..."
if curl -s http://$SS_IP:5002/health > /dev/null 2>&1; then
    print_info "✓ SS Server 可访问"
else
    print_warn "⚠ SS Server 暂无响应（可能还未启动）"
fi

# ============================================================================
# 完成总结
# ============================================================================

print_header "✅ Verifier Server (机器3) 部署完成！"

echo "服务信息:"
echo "  DO Server:       http://$DO_IP:5001"
echo "  SS Server:       http://$SS_IP:5002"
echo "  Verifier Server: http://$VERIFIER_IP:5003"
echo ""
echo "常用命令:"
echo "  查看日志:    docker-compose logs -f"
echo "  查看状态:    docker-compose ps"
echo "  重启服务:    docker-compose restart"
echo "  停止服务:    docker-compose stop"
echo "  启动服务:    docker-compose start"
echo "  删除容器:    docker-compose down"
echo ""
echo "后续步骤:"
echo "  1. 在其他两台机器上运行对应的部署脚本"
echo "  2. 等待所有服务都启动完成"
echo "  3. 运行端到端测试验证系统"
echo ""
