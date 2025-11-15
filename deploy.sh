#!/bin/bash

# VDS 多机部署快速脚本
#
# 使用方法:
#   chmod +x deploy.sh
#   ./deploy.sh <机器ID> <IP1> <IP2> <IP3>
#
# 示例:
#   ./deploy.sh 1 192.168.1.10 192.168.1.20 192.168.1.30

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 脚本路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 打印带颜色的信息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查参数
if [ $# -ne 4 ]; then
    echo "使用方法: $0 <机器ID> <IP1> <IP2> <IP3>"
    echo ""
    echo "参数说明:"
    echo "  机器ID: 1 (DO Server) | 2 (SS Server) | 3 (Verifier Server)"
    echo "  IP1: 机器1的IP地址 (DO Server)"
    echo "  IP2: 机器2的IP地址 (SS Server)"
    echo "  IP3: 机器3的IP地址 (Verifier Server)"
    echo ""
    echo "示例:"
    echo "  ./deploy.sh 1 192.168.1.10 192.168.1.20 192.168.1.30"
    exit 1
fi

MACHINE_ID=$1
IP1=$2
IP2=$3
IP3=$4

print_info "========================================"
print_info "VDS 多机部署脚本"
print_info "========================================"
print_info "机器ID: $MACHINE_ID"
print_info "DO Server IP: $IP1"
print_info "SS Server IP: $IP2"
print_info "Verifier IP: $IP3"
print_info ""

# 验证机器ID
if [ "$MACHINE_ID" != "1" ] && [ "$MACHINE_ID" != "2" ] && [ "$MACHINE_ID" != "3" ]; then
    print_error "机器ID必须是 1、2 或 3"
    exit 1
fi

# 检查 Docker 是否已安装
if ! command -v docker &> /dev/null; then
    print_error "Docker 未安装"
    exit 1
fi

print_info "Docker 已安装"

# 检查 docker-compose 是否已安装
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose 未安装"
    exit 1
fi

print_info "docker-compose 已安装"

# 进入项目目录
cd "$SCRIPT_DIR"
print_info "进入项目目录: $SCRIPT_DIR"

# 根据机器ID选择配置
case $MACHINE_ID in
    1)
        print_info "配置 DO Server (机器1)..."
        cat > docker-compose.yml << EOF
version: '3.8'

services:
  do-server:
    build: .
    container_name: vds-do-server
    command: python3 -m distributed.do_server
    ports:
      - "0.0.0.0:5001:5001"
    environment:
      - DO_HOST=0.0.0.0
      - DO_PORT=5001
      - SS_HOST=$IP2
      - SS_PORT=5002
      - VERIFIER_HOST=$IP3
      - VERIFIER_PORT=5003
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
        ;;
    2)
        print_info "配置 SS Server (机器2)..."
        cat > docker-compose.yml << EOF
version: '3.8'

services:
  ss-server:
    build: .
    container_name: vds-ss-server
    command: python3 -m distributed.ss_server
    ports:
      - "0.0.0.0:5002:5002"
    environment:
      - SS_HOST=0.0.0.0
      - SS_PORT=5002
      - DO_HOST=$IP1
      - DO_PORT=5001
      - VERIFIER_HOST=$IP3
      - VERIFIER_PORT=5003
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
        ;;
    3)
        print_info "配置 Verifier Server (机器3)..."
        cat > docker-compose.yml << EOF
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
      - DO_HOST=$IP1
      - DO_PORT=5001
      - SS_HOST=$IP2
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
        ;;
esac

print_info "docker-compose.yml 已生成"
echo ""

# 构建镜像
print_info "构建 Docker 镜像..."
print_warn "首次构建可能需要 10-15 分钟，请耐心等待..."
if docker build -t vds-app:latest .; then
    print_info "镜像构建成功"
else
    print_error "镜像构建失败"
    exit 1
fi

echo ""

# 启动服务
print_info "启动服务..."
if docker-compose up -d; then
    print_info "服务启动成功"
else
    print_error "服务启动失败"
    exit 1
fi

echo ""

# 等待容器启动
print_info "等待容器启动..."
sleep 5

# 检查服务状态
print_info "检查服务状态..."
docker-compose ps

echo ""

# 开放防火墙端口
print_info "开放防火墙端口..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 5001 2>/dev/null || true
    sudo ufw allow 5002 2>/dev/null || true
    sudo ufw allow 5003 2>/dev/null || true
    print_info "防火墙规则已添加"
else
    print_warn "未检测到 ufw，跳过防火墙配置"
    print_warn "请手动开放端口 5001、5002、5003"
fi

echo ""

# 测试服务
print_info "测试服务连接..."
case $MACHINE_ID in
    1)
        PORT=5001
        ;;
    2)
        PORT=5002
        ;;
    3)
        PORT=5003
        ;;
esac

if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
    print_info "服务健康检查通过"
    curl -s http://localhost:$PORT/health | python3 -m json.tool
else
    print_error "服务健康检查失败"
    print_info "查看详细日志："
    print_info "  docker-compose logs"
    exit 1
fi

echo ""
print_info "========================================"
print_info "✅ 部署完成！"
print_info "========================================"
echo ""
print_info "快速命令:"
echo "  查看日志:      docker-compose logs -f"
echo "  查看状态:      docker-compose ps"
echo "  重启服务:      docker-compose restart"
echo "  停止服务:      docker-compose stop"
echo "  删除容器:      docker-compose down"
echo ""
print_info "验证其他服务:"
echo "  curl http://$IP1:5001/health"
echo "  curl http://$IP2:5002/health"
echo "  curl http://$IP3:5003/health"
echo ""
print_info "如需更多帮助，查看:"
echo "  cat MULTI_MACHINE_DEPLOYMENT.md"
