#!/bin/bash

# VDS 多机部署 IP 配置助手
#
# 帮助用户快速配置多机部署的 IP 地址

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

clear

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          VDS 多机部署 IP 配置助手                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo "本助手将帮助你快速生成多机部署配置文件"
echo ""

# 获取三台机器的 IP
echo -e "${YELLOW}请输入三台机器的 IP 地址${NC}"
echo ""

read -p "机器1 (DO Server) IP [192.168.1.10]: " IP1
IP1="${IP1:-192.168.1.10}"

read -p "机器2 (SS Server) IP [192.168.1.20]: " IP2
IP2="${IP2:-192.168.1.20}"

read -p "机器3 (Verifier Server) IP [192.168.1.30]: " IP3
IP3="${IP3:-192.168.1.30}"

echo ""
echo -e "${GREEN}✓ IP 地址配置完成${NC}"
echo ""
echo "配置总结:"
echo "  DO Server IP:       $IP1"
echo "  SS Server IP:       $IP2"
echo "  Verifier Server IP: $IP3"
echo ""

# 确认
read -p "配置是否正确？(y/n) [y]: " confirm
confirm="${confirm:-y}"

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 1
fi

echo ""

# 获取当前机器ID
echo -e "${YELLOW}请选择这是哪台机器${NC}"
echo "  1) DO Server (机器1)"
echo "  2) SS Server (机器2)"
echo "  3) Verifier Server (机器3)"
echo ""
read -p "请选择 [1-3]: " MACHINE_ID

case $MACHINE_ID in
    1|2|3)
        echo -e "${GREEN}✓ 选择了机器 $MACHINE_ID${NC}"
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""

# 生成配置文件
echo -e "${YELLOW}正在生成配置文件...${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

case $MACHINE_ID in
    1)
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
        echo -e "${GREEN}✓ 已生成 DO Server 配置${NC}"
        ;;
    2)
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
        echo -e "${GREEN}✓ 已生成 SS Server 配置${NC}"
        ;;
    3)
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
        echo -e "${GREEN}✓ 已生成 Verifier Server 配置${NC}"
        ;;
esac

echo ""
echo -e "${YELLOW}下一步:${NC}"
echo ""
echo "  1. 构建 Docker 镜像:"
echo "     ${BLUE}docker build -t vds-app:latest .${NC}"
echo ""
echo "  2. 启动服务:"
echo "     ${BLUE}docker-compose up -d${NC}"
echo ""
echo "  3. 查看日志:"
echo "     ${BLUE}docker-compose logs -f${NC}"
echo ""
echo "  4. 验证其他服务:"
echo "     ${BLUE}curl http://$IP1:5001/health${NC}"
echo "     ${BLUE}curl http://$IP2:5002/health${NC}"
echo "     ${BLUE}curl http://$IP3:5003/health${NC}"
echo ""
echo -e "${GREEN}✅ 配置完成！${NC}"
