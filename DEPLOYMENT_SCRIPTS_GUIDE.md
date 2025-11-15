# 🚀 VDS 云服务器部署脚本总览

## 📋 脚本概览

| 脚本名称 | 用途 | 何时使用 | 耗时 |
|---------|------|--------|------|
| `init-environment.sh` | 系统环境初始化 | 首次部署，安装 Docker 等依赖 | 5-10 分钟 |
| `deploy-machine-1.sh` | 机器1 (DO Server) 部署 | 在 DO Server 上运行 | 15-20 分钟 |
| `deploy-machine-2.sh` | 机器2 (SS Server) 部署 | 在 SS Server 上运行 | 15-20 分钟 |
| `deploy-machine-3.sh` | 机器3 (Verifier) 部署 | 在 Verifier Server 上运行 | 15-20 分钟 |
| `quick-deploy.sh` | 一体化快速部署 | 新服务器，一条命令搞定 | 25-35 分钟 |

## 🎯 快速选择指南

### 场景1：已有三台服务器，想快速部署

**推荐方案：使用 `quick-deploy.sh`**

```bash
# 在每台服务器上运行一条命令，完成从环境初始化到服务启动的全流程

# 在机器1上：
sudo bash quick-deploy.sh 1 192.168.1.10 192.168.1.10 192.168.1.20 192.168.1.30

# 在机器2上：
sudo bash quick-deploy.sh 2 192.168.1.20 192.168.1.10 192.168.1.20 192.168.1.30

# 在机器3上：
sudo bash quick-deploy.sh 3 192.168.1.30 192.168.1.10 192.168.1.20 192.168.1.30
```

**优点：**
- 一条命令完成所有配置
- 无需分步操作
- 适合快速原型部署

---

### 场景2：想分步部署，便于排查问题

**推荐方案：分步使用脚本**

**第1步：初始化环境**
```bash
# 在三台机器上都运行
sudo bash init-environment.sh
```

**第2步：克隆项目代码**
```bash
# 在三台机器上都运行
git clone <your-repo-url> vds-project
cd vds-project
```

**第3步：分别部署**
```bash
# 在机器1上：
./deploy-machine-1.sh 192.168.1.10 192.168.1.20 192.168.1.30

# 在机器2上：
./deploy-machine-2.sh 192.168.1.10 192.168.1.20 192.168.1.30

# 在机器3上：
./deploy-machine-3.sh 192.168.1.10 192.168.1.20 192.168.1.30
```

**优点：**
- 可以检查每个步骤的结果
- 便于故障排查
- 对环境有更多了解

---

### 场景3：已经初始化过环境，重新部署应用

**推荐方案：直接使用 `deploy-machine-X.sh`**

```bash
cd /path/to/vds-project

# 在对应的机器上运行相应的脚本
./deploy-machine-1.sh 192.168.1.10 192.168.1.20 192.168.1.30
```

---

## 📖 详细使用指南

### 方法A：快速部署（推荐新用户）

#### 第1步：准备工作
1. 租用三台 Ubuntu 22.04 LTS 服务器
2. 记下三台机器的 IP 地址
3. 确保能通过 SSH 连接到每台机器
4. 获取项目代码（git clone 或下载）

#### 第2步：在每台机器上执行
```bash
# SSH 连接到机器
ssh root@192.168.1.10

# 进入项目目录
cd /path/to/vds-project

# 运行一键部署脚本
sudo bash quick-deploy.sh 1 192.168.1.10 192.168.1.10 192.168.1.20 192.168.1.30
```

每台机器执行一次，唯一的区别是：
- 机器 ID：1、2 或 3
- 自己的 IP：第二个参数不同

#### 第3步：验证
```bash
# 从任何一台机器
curl http://192.168.1.10:5001/health
curl http://192.168.1.20:5002/health
curl http://192.168.1.30:5003/health
```

---

### 方法B：分步部署（推荐想深入了解的用户）

#### 第1步：系统初始化
```bash
# 在三台机器上都运行
ssh root@192.168.1.10
sudo bash init-environment.sh

ssh root@192.168.1.20
sudo bash init-environment.sh

ssh root@192.168.1.30
sudo bash init-environment.sh
```

这个脚本会：
- 更新系统包
- 安装 Docker 和 docker-compose
- 安装 Python 3.11
- 配置防火墙
- 验证环境

#### 第2步：克隆代码
```bash
# 在三台机器上都运行
git clone <your-repo-url> vds-project
cd vds-project
```

#### 第3步：部署应用
```bash
# 在机器1上
cd vds-project
chmod +x deploy-machine-1.sh
./deploy-machine-1.sh 192.168.1.10 192.168.1.20 192.168.1.30

# 在机器2上
cd vds-project
chmod +x deploy-machine-2.sh
./deploy-machine-2.sh 192.168.1.10 192.168.1.20 192.168.1.30

# 在机器3上
cd vds-project
chmod +x deploy-machine-3.sh
./deploy-machine-3.sh 192.168.1.10 192.168.1.20 192.168.1.30
```

---

## 🔍 脚本详解

### init-environment.sh

**功能：** 全面的系统环境初始化

**包含的操作：**
```
1. 更新系统包 (apt-get update/upgrade)
2. 安装开发工具 (build-essential, git, curl, wget, etc.)
3. 安装 Python 3.11
4. 安装 Docker
5. 安装 docker-compose
6. 配置 Docker 代理（可选）
7. 配置防火墙（ufw）
8. 验证环境
```

**运行权限：** 需要 sudo

**参数：** 无

**使用：**
```bash
sudo bash init-environment.sh
```

**输出示例：**
```
✓ 系统包更新完成
✓ 基础开发工具安装完成
✓ Python 3.11 安装完成
✓ Docker 安装完成
✓ docker-compose 安装完成
✓ 防火墙配置完成
```

---

### deploy-machine-N.sh

**功能：** 特定机器的应用部署

**包含的操作：**
```
1. 检查前置环境 (Docker, docker-compose, Python)
2. 克隆/更新项目代码 (git pull)
3. 生成 docker-compose.yml (配置 IP 地址)
4. 构建 Docker 镜像 (docker build)
5. 清理旧的服务 (docker-compose down)
6. 启动新的服务 (docker-compose up -d)
7. 验证服务状态 (docker-compose ps)
8. 运行健康检查 (curl /health)
9. 测试跨机器连接
```

**运行权限：** 普通用户（但 Docker 操作需要权限）

**参数：**
```
$1: DO Server IP (例：192.168.1.10)
$2: SS Server IP (例：192.168.1.20)
$3: Verifier Server IP (例：192.168.1.30)
```

**使用：**
```bash
# 在机器1上
./deploy-machine-1.sh 192.168.1.10 192.168.1.20 192.168.1.30

# 在机器2上
./deploy-machine-2.sh 192.168.1.10 192.168.1.20 192.168.1.30

# 在机器3上
./deploy-machine-3.sh 192.168.1.10 192.168.1.20 192.168.1.30
```

---

### quick-deploy.sh

**功能：** 一体化快速部署，无需预先初始化环境

**包含的操作：**
```
阶段1：系统环境初始化
  - 更新系统包
  - 安装 Docker 和依赖
  - 安装 Python 3.11

阶段2：Docker 安装配置
  - 安装 Docker
  - 配置防火墙

阶段3：防火墙配置
  - 开放必要的端口

阶段4：项目部署
  - 生成 docker-compose.yml
  - 构建镜像
  - 启动服务
  - 运行健康检查
```

**运行权限：** 需要 root（使用 sudo）

**参数：**
```
$1: 机器编号 (1, 2, 或 3)
$2: 本机 IP
$3: DO Server IP
$4: SS Server IP
$5: Verifier Server IP
```

**使用：**
```bash
sudo bash quick-deploy.sh 1 192.168.1.10 192.168.1.10 192.168.1.20 192.168.1.30
sudo bash quick-deploy.sh 2 192.168.1.20 192.168.1.10 192.168.1.20 192.168.1.30
sudo bash quick-deploy.sh 3 192.168.1.30 192.168.1.10 192.168.1.20 192.168.1.30
```

---

## ⚠️ 重要提示

### 参数顺序很关键！

三个脚本的参数顺序 **都是相同的**：
```
DO_IP SS_IP VERIFIER_IP
```

但是机器编号不同：
- 机器1：`deploy-machine-1.sh <DO> <SS> <VERIFIER>`
- 机器2：`deploy-machine-2.sh <DO> <SS> <VERIFIER>`
- 机器3：`deploy-machine-3.sh <DO> <SS> <VERIFIER>`

### 权限问题

- `init-environment.sh` 和 `quick-deploy.sh` 需要 `sudo` 或 root 权限
- `deploy-machine-X.sh` 需要能够运行 Docker 命令

如果普通用户运行 deploy 脚本出错，可能需要：
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 网络连通性

部署前，请确保：
1. 三台机器能相互 ping 通
2. 防火墙已正确配置（开放 5001、5002、5003 端口）
3. 云服务商的安全组也已配置

---

## 🐛 故障排查

### 脚本权限不足
```bash
chmod +x *.sh
```

### Docker 构建超时
- 检查网络连接
- 配置 Docker 代理
- 增加 Docker 超时时间

### 容器启动失败
```bash
# 查看详细日志
docker-compose logs -f
docker-compose logs <service-name>
```

### 健康检查失败
```bash
# 检查端口是否开放
sudo ufw status
netstat -tuln | grep 500[1-3]

# 检查容器是否运行
docker-compose ps
```

---

## 📚 相关文档

- **CLOUD_DEPLOYMENT_GUIDE.md** - 详细的云部署指南
- **MULTI_MACHINE_DEPLOYMENT.md** - 多机部署详细说明
- **QUICK_REFERENCE.md** - 快速参考卡片

---

## 🎉 总结

| 需求 | 推荐方案 | 命令 |
|------|--------|------|
| 快速上手 | `quick-deploy.sh` | `sudo bash quick-deploy.sh ...` |
| 分步操作 | `init-environment.sh` + `deploy-machine-X.sh` | 分两步运行 |
| 重新部署 | `deploy-machine-X.sh` | `./deploy-machine-X.sh ...` |
| 了解细节 | 查看脚本代码和 CLOUD_DEPLOYMENT_GUIDE.md | - |

祝你部署顺利！🚀
