#!/bin/bash

##############################################################################
# VDS 快速部署 - 3分钟一键完成
#
# 这个脚本将所有步骤合并，适合已有全新云服务器的用户
#
# 前置要求:
#   - 全新的 Ubuntu 22.04 LTS 服务器
#   - 可以 SSH 连接
#
# 使用方法:
#   chmod +x quick-deploy.sh
#   ./quick-deploy.sh <machine_id> <your_ip> <do_ip> <ss_ip> <verifier_ip>
#
# 示例:
#   # 在机器1上运行
#   ./quick-deploy.sh 1 192.168.1.10 192.168.1.10 192.168.1.20 192.168.1.30
#
#   # 在机器2上运行
#   ./quick-deploy.sh 2 192.168.1.20 192.168.1.10 192.168.1.20 192.168.1.30
#
#   # 在机器3上运行
#   ./quick-deploy.sh 3 192.168.1.30 192.168.1.10 192.168.1.20 192.168.1.30
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
if [ $# -ne 5 ]; then
    echo "使用方法: $0 <machine_id> <your_ip> <do_ip> <ss_ip> <verifier_ip>"
    echo ""
    echo "参数说明:"
    echo "  machine_id:   本机编号 (1=DO Server, 2=SS Server, 3=Verifier)"
    echo "  your_ip:      本机 IP 地址"
    echo "  do_ip:        DO Server 的 IP 地址"
    echo "  ss_ip:        SS Server 的 IP 地址"
    echo "  verifier_ip:  Verifier Server 的 IP 地址"
    echo ""
    echo "示例:"
    echo "  ./quick-deploy.sh 1 192.168.1.10 192.168.1.10 192.168.1.20 192.168.1.30"
    echo "  ./quick-deploy.sh 2 192.168.1.20 192.168.1.10 192.168.1.20 192.168.1.30"
    echo "  ./quick-deploy.sh 3 192.168.1.30 192.168.1.10 192.168.1.20 192.168.1.30"
    exit 1
fi

MACHINE_ID=$1
YOUR_IP=$2
DO_IP=$3
SS_IP=$4
VERIFIER_IP=$5

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then
    print_error "此脚本需要 root 权限，请使用 sudo 运行"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_header "VDS 快速部署 - 全流程一体化"

echo "配置参数:"
echo "  本机编号:        $MACHINE_ID"
echo "  本机 IP:         $YOUR_IP"
echo "  DO Server IP:    $DO_IP"
echo "  SS Server IP:    $SS_IP"
echo "  Verifier IP:     $VERIFIER_IP"
echo ""

read -p "配置是否正确？(y/n) [y]: " confirm
confirm="${confirm:-y}"

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    print_error "已取消部署"
    exit 1
fi

# ============================================================================
# 阶段1：系统环境初始化
# ============================================================================

print_header "阶段1/4: 系统环境初始化 (约 3-5 分钟)"

print_step "更新系统包..."
apt-get update -qq >/dev/null 2>&1
apt-get upgrade -y -qq >/dev/null 2>&1

print_step "安装基础工具..."
apt-get install -y -qq \
    curl wget git build-essential \
    libssl-dev libffi-dev python3-dev \
    python3-pip python3-venv ca-certificates \
    apt-transport-https software-properties-common \
    gnupg lsb-release ufw >/dev/null 2>&1

print_step "安装 Python 3.11..."
add-apt-repository ppa:deadsnakes/ppa -y >/dev/null 2>&1
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq python3.11 python3.11-dev >/dev/null 2>&1
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 >/dev/null 2>&1

print_info "✓ 系统环境初始化完成"

# ============================================================================
# 阶段2：Docker 安装配置
# ============================================================================

print_header "阶段2/4: Docker 安装配置 (约 2-3 分钟)"

print_step "安装 Docker..."
OS=$(grep "^ID=" /etc/os-release | cut -d'=' -f2 | tr -d '"')
mkdir -p /etc/apt/keyrings >/dev/null 2>&1
curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg >/dev/null 2>&1
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list >/dev/null 2>&1
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin >/dev/null 2>&1

print_step "启动 Docker 服务..."
systemctl enable docker >/dev/null 2>&1
systemctl start docker >/dev/null 2>&1

print_step "安装 docker-compose..."
apt-get install -y -qq docker-compose >/dev/null 2>&1

print_info "✓ Docker 安装配置完成"

# ============================================================================
# 阶段3：防火墙配置
# ============================================================================

print_header "阶段3/4: 防火墙配置"

print_step "配置防火墙..."
ufw --force enable >/dev/null 2>&1
ufw allow 22/tcp >/dev/null 2>&1
ufw allow 5001/tcp >/dev/null 2>&1
ufw allow 5002/tcp >/dev/null 2>&1
ufw allow 5003/tcp >/dev/null 2>&1

print_info "✓ 防火墙配置完成"

# ============================================================================
# 阶段4：项目部署
# ============================================================================

print_header "阶段4/4: 项目部署 (约 10-15 分钟)"

cd "$SCRIPT_DIR"

print_step "生成 docker-compose.yml..."

case $MACHINE_ID in
    1)
        CONTAINER_NAME="vds-do-server"
        SERVICE_NAME="do-server"
        COMMAND="python3 -m distributed.do_server"
        PORT="5001"
        SERVICE_HOST="0.0.0.0"
        SERVICE_PORT="5001"
        ;;
    2)
        CONTAINER_NAME="vds-ss-server"
        SERVICE_NAME="ss-server"
        COMMAND="python3 -m distributed.ss_server"
        PORT="5002"
        SERVICE_HOST="0.0.0.0"
        SERVICE_PORT="5002"
        ;;
    3)
        CONTAINER_NAME="vds-verifier-server"
        SERVICE_NAME="verifier-server"
        COMMAND="python3 -m distributed.verifier_server"
        PORT="5003"
        SERVICE_HOST="0.0.0.0"
        SERVICE_PORT="5003"
        ;;
    *)
        print_error "无效的机器编号 (需要 1、2 或 3)"
        exit 1
        ;;
esac

cat > "$SCRIPT_DIR/docker-compose.yml" << 'COMPOSE_EOF'
version: '3.8'

services:
  SERVICE_PLACEHOLDER:
    build: .
    container_name: CONTAINER_PLACEHOLDER
    command: COMMAND_PLACEHOLDER
    ports:
      - "0.0.0.0:PORT_PLACEHOLDER:PORT_PLACEHOLDER"
    environment:
      - MACHINE_SPECIFIC_ENV
      - DO_HOST=DO_IP_PLACEHOLDER
      - DO_PORT=5001
      - SS_HOST=SS_IP_PLACEHOLDER
      - SS_PORT=5002
      - VERIFIER_HOST=VERIFIER_IP_PLACEHOLDER
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
COMPOSE_EOF

# 针对不同机器做替换
case $MACHINE_ID in
    1)
        sed -i 's/SERVICE_PLACEHOLDER/do-server/g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's/CONTAINER_PLACEHOLDER/vds-do-server/g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's|COMMAND_PLACEHOLDER|python3 -m distributed.do_server|g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's/PORT_PLACEHOLDER/5001/g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's/MACHINE_SPECIFIC_ENV/- DO_HOST=0.0.0.0/g' "$SCRIPT_DIR/docker-compose.yml"
        ;;
    2)
        sed -i 's/SERVICE_PLACEHOLDER/ss-server/g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's/CONTAINER_PLACEHOLDER/vds-ss-server/g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's|COMMAND_PLACEHOLDER|python3 -m distributed.ss_server|g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's/PORT_PLACEHOLDER/5002/g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's/MACHINE_SPECIFIC_ENV/- SS_HOST=0.0.0.0/g' "$SCRIPT_DIR/docker-compose.yml"
        ;;
    3)
        sed -i 's/SERVICE_PLACEHOLDER/verifier-server/g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's/CONTAINER_PLACEHOLDER/vds-verifier-server/g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's|COMMAND_PLACEHOLDER|python3 -m distributed.verifier_server|g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's/PORT_PLACEHOLDER/5003/g' "$SCRIPT_DIR/docker-compose.yml"
        sed -i 's/MACHINE_SPECIFIC_ENV/- VERIFIER_HOST=0.0.0.0/g' "$SCRIPT_DIR/docker-compose.yml"
        ;;
esac

sed -i "s/DO_IP_PLACEHOLDER/$DO_IP/g" "$SCRIPT_DIR/docker-compose.yml"
sed -i "s/SS_IP_PLACEHOLDER/$SS_IP/g" "$SCRIPT_DIR/docker-compose.yml"
sed -i "s/VERIFIER_IP_PLACEHOLDER/$VERIFIER_IP/g" "$SCRIPT_DIR/docker-compose.yml"

print_info "✓ docker-compose.yml 生成完成"

print_step "构建 Docker 镜像..."
print_warn "⚠ 首次构建需要 10-15 分钟，请耐心等待..."

if docker build -t vds-app:latest . >/dev/null 2>&1; then
    print_info "✓ Docker 镜像构建成功"
else
    print_error "镜像构建失败，请检查网络和磁盘空间"
    exit 1
fi

print_step "清理旧的服务..."
docker-compose down 2>/dev/null || true
sleep 2

print_step "启动服务..."
if docker-compose up -d >/dev/null 2>&1; then
    print_info "✓ 服务已启动"
else
    print_error "服务启动失败"
    exit 1
fi

print_step "等待服务启动..."
sleep 5

# ============================================================================
# 健康检查
# ============================================================================

print_header "验证服务"

print_step "检查容器状态..."
docker-compose ps

print_step "运行健康检查..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        print_info "✓ 服务健康检查通过"
        curl -s http://localhost:$PORT/health | python3 -m json.tool 2>/dev/null || echo "Status: OK"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "服务健康检查失败"
    print_info "查看日志:"
    docker-compose logs
    exit 1
fi

# ============================================================================
# 完成
# ============================================================================

print_header "✅ 部署完成！"

echo "服务信息:"
echo "  DO Server:       http://$DO_IP:5001"
echo "  SS Server:       http://$SS_IP:5002"
echo "  Verifier Server: http://$VERIFIER_IP:5003"
echo ""
echo "常用命令:"
echo "  查看日志:        docker-compose logs -f"
echo "  查看状态:        docker-compose ps"
echo "  重启服务:        docker-compose restart"
echo "  停止服务:        docker-compose stop"
echo "  启动服务:        docker-compose start"
echo ""
echo "总耗时: 约 20-30 分钟"
echo ""
