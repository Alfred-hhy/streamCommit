#!/bin/bash

##############################################################################
# VDS 云服务器环境初始化脚本
#
# 这是一个完整的一键化环境初始化脚本，可以在全新的云服务器上从零开始
# 自动安装和配置所有必要的环境。
#
# 使用方法:
#   chmod +x init-environment.sh
#   ./init-environment.sh
#
# 支持的系统:
#   - Ubuntu 22.04 LTS
#   - Ubuntu 20.04 LTS
#   - Debian 11+
#
# 脚本功能:
#   ✓ 更新系统包
#   ✓ 安装 Docker
#   ✓ 安装 docker-compose
#   ✓ 安装 Python 3.11
#   ✓ 安装系统开发工具
#   ✓ 配置 Docker 代理（可选）
#   ✓ 验证所有环境
#
##############################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then
    print_error "此脚本需要 root 权限，请使用 sudo 运行"
    exit 1
fi

print_header "VDS 云服务器环境初始化脚本"

# 获取系统信息
print_info "检测系统信息..."
OS=$(grep "^ID=" /etc/os-release | cut -d'=' -f2 | tr -d '"')
VERSION=$(grep "^VERSION_ID=" /etc/os-release | cut -d'=' -f2 | tr -d '"')
print_info "系统: $OS $VERSION"

# 检查系统支持
if [[ "$OS" != "ubuntu" && "$OS" != "debian" ]]; then
    print_error "不支持的系统: $OS（仅支持 Ubuntu 和 Debian）"
    exit 1
fi

# ============================================================================
# 第1步：更新系统包
# ============================================================================

print_header "第1步: 更新系统包"

print_step "更新包管理器..."
apt-get update -qq
apt-get upgrade -y -qq

print_info "✓ 系统包更新完成"

# ============================================================================
# 第2步：安装基础开发工具
# ============================================================================

print_header "第2步: 安装基础开发工具"

print_step "安装必要的工具..."
apt-get install -y -qq \
    curl \
    wget \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    python3-pip \
    python3-venv \
    ca-certificates \
    apt-transport-https \
    software-properties-common \
    gnupg \
    lsb-release \
    ufw

print_info "✓ 基础开发工具安装完成"

# ============================================================================
# 第3步：安装 Python 3.11
# ============================================================================

print_header "第3步: 安装 Python 3.11"

print_step "添加 deadsnakes PPA..."
add-apt-repository ppa:deadsnakes/ppa -y
apt-get update -qq

print_step "安装 Python 3.11..."
apt-get install -y -qq \
    python3.11 \
    python3.11-dev \
    python3.11-venv

print_step "设置默认 Python 版本..."
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

print_info "Python 3.11 安装完成"
python3 --version

# ============================================================================
# 第4步：安装 Docker
# ============================================================================

print_header "第4步: 安装 Docker"

print_step "添加 Docker 官方仓库..."
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -qq

print_step "安装 Docker..."
apt-get install -y -qq \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-compose-plugin

print_step "启动 Docker 服务..."
systemctl enable docker
systemctl start docker

print_info "✓ Docker 安装完成"
docker --version

# ============================================================================
# 第5步：安装 docker-compose
# ============================================================================

print_header "第5步: 安装 docker-compose"

print_step "安装 docker-compose..."
apt-get install -y -qq docker-compose

print_info "✓ docker-compose 安装完成"
docker-compose --version

# ============================================================================
# 第6步：配置 Docker（可选）
# ============================================================================

print_header "第6步: 配置 Docker"

# 配置 Docker 代理（如果需要）
read -p "是否需要配置 Docker 代理？(y/n) [n]: " configure_proxy
configure_proxy="${configure_proxy:-n}"

if [ "$configure_proxy" = "y" ] || [ "$configure_proxy" = "Y" ]; then
    read -p "请输入代理地址（例如 http://proxy.example.com:8080）: " proxy_url

    if [ -n "$proxy_url" ]; then
        mkdir -p /etc/systemd/system/docker.service.d
        cat > /etc/systemd/system/docker.service.d/http-proxy.conf << EOF
[Service]
Environment="HTTP_PROXY=$proxy_url"
Environment="HTTPS_PROXY=$proxy_url"
EOF
        systemctl daemon-reload
        systemctl restart docker
        print_info "✓ Docker 代理配置完成: $proxy_url"
    fi
fi

# 配置 Docker 用户组（允许非 root 用户使用 Docker）
print_step "配置 Docker 用户组..."
if ! getent group docker > /dev/null; then
    groupadd docker
fi

# 获取当前用户（如果以 sudo 运行）
if [ -n "$SUDO_USER" ]; then
    usermod -aG docker $SUDO_USER
    print_info "✓ 已将用户 '$SUDO_USER' 添加到 docker 组"
fi

print_info "✓ Docker 配置完成"

# ============================================================================
# 第7步：配置防火墙
# ============================================================================

print_header "第7步: 配置防火墙"

print_step "启用防火墙..."
ufw --force enable

print_step "开放 SSH 端口..."
ufw allow 22/tcp

print_step "开放 VDS 服务端口..."
ufw allow 5001/tcp  # DO Server
ufw allow 5002/tcp  # SS Server
ufw allow 5003/tcp  # Verifier Server

print_info "✓ 防火墙配置完成"

# ============================================================================
# 第8步：验证环境
# ============================================================================

print_header "第8步: 验证环境"

print_step "验证 Docker..."
docker --version

print_step "验证 docker-compose..."
docker-compose --version

print_step "验证 Python..."
python3 --version
python3.11 --version

print_step "验证 Docker 运行状态..."
if docker ps &> /dev/null; then
    print_info "✓ Docker 运行正常"
else
    print_warn "⚠ Docker 可能需要权限配置"
fi

# ============================================================================
# 完成总结
# ============================================================================

print_header "✅ 环境初始化完成！"

echo "已安装的工具:"
echo "  • Docker:        $(docker --version)"
echo "  • docker-compose: $(docker-compose --version)"
echo "  • Python:        $(python3 --version)"
echo ""
echo "防火墙已开放端口:"
echo "  • SSH:     22"
echo "  • DO:      5001"
echo "  • SS:      5002"
echo "  • Verifier: 5003"
echo ""
echo "后续步骤:"
echo "  1. 克隆项目代码"
echo "  2. 运行对应的部署脚本（deploy-machine-*.sh）"
echo "  3. 验证服务是否正常运行"
echo ""
echo "如需帮助，查看 README.md 或 MULTI_MACHINE_DEPLOYMENT.md"
echo ""

if [ -n "$SUDO_USER" ]; then
    print_info "注意: 请重新登录使 Docker 权限配置生效"
fi
