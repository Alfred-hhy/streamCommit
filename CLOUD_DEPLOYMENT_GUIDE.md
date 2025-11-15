# VDS 云服务器一键部署完整指南

## 📋 目录

1. [快速开始](#快速开始)
2. [系统要求](#系统要求)
3. [部署步骤](#部署步骤)
4. [验证部署](#验证部署)
5. [常见问题](#常见问题)
6. [故障排查](#故障排查)

---

## 🚀 快速开始

如果你有三台全新的云服务器，只需按照以下步骤操作：

### 第1步：在所有三台机器上初始化环境

```bash
# 在每台机器上运行（需要 root 权限）
sudo bash init-environment.sh
```

这个脚本会自动安装：
- Docker 和 docker-compose
- Python 3.11
- 所有系统依赖
- 防火墙配置

**耗时：约 5-10 分钟（取决于网络速度）**

### 第2步：克隆项目代码

```bash
# 在每台机器上运行（在一个合适的目录）
git clone <your-repo-url> vds-project
cd vds-project
```

### 第3步：在三台机器上分别运行对应的部署脚本

假设你的 IP 地址是：
- 机器1 (DO Server):       192.168.1.10
- 机器2 (SS Server):       192.168.1.20
- 机器3 (Verifier Server): 192.168.1.30

**在机器1上运行：**
```bash
chmod +x deploy-machine-1.sh
./deploy-machine-1.sh 192.168.1.10 192.168.1.20 192.168.1.30
```

**在机器2上运行：**
```bash
chmod +x deploy-machine-2.sh
./deploy-machine-2.sh 192.168.1.10 192.168.1.20 192.168.1.30
```

**在机器3上运行：**
```bash
chmod +x deploy-machine-3.sh
./deploy-machine-3.sh 192.168.1.10 192.168.1.20 192.168.1.30
```

**耗时：约 15-20 分钟（包括 Docker 镜像构建）**

### 第4步：验证所有服务都已启动

```bash
# 从任何一台机器运行（假设知道其他机器的 IP）
curl http://192.168.1.10:5001/health
curl http://192.168.1.20:5002/health
curl http://192.168.1.30:5003/health
```

✅ 如果都返回 `200 OK`，说明部署成功！

---

## 📊 系统要求

### 硬件要求

| 配置 | 最低要求 | 推荐配置 |
|------|---------|--------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 20 GB | 50 GB |
| 网络 | 100 Mbps | 1 Gbps |

### 软件要求

| 软件 | 版本 |
|------|------|
| OS | Ubuntu 22.04 LTS 或 20.04 LTS |
| Kernel | 4.15+ |

### 网络要求

- 三台机器必须能相互 ping 通
- 开放以下端口：
  - **5001** (DO Server)
  - **5002** (SS Server)
  - **5003** (Verifier Server)
  - **22** (SSH，用于管理)

---

## 📝 部署步骤详细说明

### 步骤1：获取三台云服务器

1. 在你的云服务商（如 AWS、DigitalOcean、Linode 等）租用三台 Ubuntu 22.04 LTS 服务器
2. 记下三台服务器的 IP 地址
3. 确保你能通过 SSH 连接到每台服务器

### 步骤2：在每台机器上初始化环境

连接到第一台机器：
```bash
ssh root@192.168.1.10
```

下载并运行初始化脚本：
```bash
# 下载脚本（两种方式选一）

# 方式1：直接下载文件
wget https://your-repo-url/init-environment.sh
chmod +x init-environment.sh
sudo bash init-environment.sh

# 方式2：从 git 克隆后运行
git clone <your-repo-url> vds-project
cd vds-project
sudo bash init-environment.sh
```

脚本会提示你：
- 是否配置 Docker 代理（可选）
- 然后自动完成其余配置

重复此步骤，在机器2和机器3上运行相同的命令。

### 步骤3：克隆项目代码

在每台机器上：
```bash
# 进入你想安装项目的目录
cd /opt  # 或其他你喜欢的目录

# 克隆项目
git clone <your-repo-url> vds-project
cd vds-project

# 列出脚本文件
ls -la deploy-machine-*.sh
```

### 步骤4：运行对应的部署脚本

这里很关键！每台机器运行不同的脚本。

**在机器1 (192.168.1.10) 上：**
```bash
cd /opt/vds-project  # 根据实际路径调整
chmod +x deploy-machine-1.sh
./deploy-machine-1.sh 192.168.1.10 192.168.1.20 192.168.1.30
```

脚本会：
- 显示配置摘要，让你确认
- 检查 Docker 等环境
- 生成 docker-compose.yml
- 构建 Docker 镜像（首次需要 10-15 分钟）
- 启动服务
- 运行健康检查

**重要提示：**
```
脚本参数顺序：
./deploy-machine-1.sh <DO_IP> <SS_IP> <VERIFIER_IP>
./deploy-machine-2.sh <DO_IP> <SS_IP> <VERIFIER_IP>
./deploy-machine-3.sh <DO_IP> <SS_IP> <VERIFIER_IP>

三台机器运行的脚本不同，但参数顺序相同！
```

---

## ✅ 验证部署

### 1. 检查容器运行状态

在任何一台机器上：
```bash
docker-compose ps

# 应该看到类似输出（根据机器不同）：
# CONTAINER ID   IMAGE         COMMAND                  PORTS               STATUS
# xxx            vds-app       python3 -m ...          0.0.0.0:5001->5001  Up
```

### 2. 检查服务健康

```bash
# 从你的本地电脑或任何一台机器
curl http://192.168.1.10:5001/health
curl http://192.168.1.20:5002/health
curl http://192.168.1.30:5003/health

# 应该返回 JSON 响应，包含 "status": "healthy"
```

### 3. 查看实时日志

```bash
# 在相应的机器上
docker-compose logs -f

# 看到类似日志说明启动成功：
# vds-do-server      | 2024-01-15 10:30:00 Starting DO Server...
# vds-do-server      | 2024-01-15 10:30:05 Server listening on 0.0.0.0:5001
```

### 4. 测试跨机器通信

在机器1上，测试能否连接到机器2和3：
```bash
# 从机器1测试到机器2
curl http://192.168.1.20:5002/health

# 从机器1测试到机器3
curl http://192.168.1.30:5003/health
```

如果都成功，说明网络通信正常。

### 5. 运行端到端测试（可选）

如果有测试脚本：
```bash
python3 test_distributed_deployment.py 192.168.1.10 192.168.1.20 192.168.1.30
```

---

## ❓ 常见问题

### Q1: init-environment.sh 需要 root 权限吗？

**A:** 是的，需要用 `sudo` 运行，因为需要安装系统包和配置防火墙。

```bash
sudo bash init-environment.sh
```

### Q2: 可以在非 Ubuntu 系统上运行这些脚本吗？

**A:** 目前脚本只支持 Ubuntu 和 Debian。其他系统可能需要修改部分命令。

### Q3: Docker 构建失败了怎么办？

**A:** 通常是网络问题。可以：
1. 检查网络连接
2. 配置代理（运行 init-environment.sh 时选择配置）
3. 手动运行 `docker build -t vds-app:latest .` 查看具体错误

### Q4: 可以更改服务端口吗？

**A:** 可以，但不推荐。如果要改，需要：
1. 修改部署脚本中的环境变量
2. 更新防火墙规则

### Q5: 如何重启服务？

**A:** 在任何一台机器上：
```bash
docker-compose restart

# 或者重启特定服务
docker-compose restart do-server
```

### Q6: 如何查看日志？

**A:**
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f do-server

# 查看最后 100 行日志
docker-compose logs --tail=100
```

### Q7: 如何停止服务？

**A:**
```bash
# 停止但不删除容器
docker-compose stop

# 停止并删除容器
docker-compose down

# 重新启动
docker-compose start
```

---

## 🔧 故障排查

### 问题1：init-environment.sh 执行失败

**症状：** 脚本在安装某个包时卡住或出错

**解决方案：**
```bash
# 1. 检查网络连接
ping 8.8.8.8

# 2. 更新包管理器
sudo apt-get update

# 3. 重新运行脚本
sudo bash init-environment.sh
```

### 问题2：Docker 镜像构建超时

**症状：** `docker build` 过程中断

**解决方案：**
```bash
# 1. 增加 Docker 超时时间
docker build --build-arg BUILDKIT_STEP_LOG_MAX_SIZE=10485760 -t vds-app:latest .

# 2. 或者配置 Docker 代理再重试
```

### 问题3：容器启动后立即退出

**症状：** `docker-compose ps` 显示容器 `Exited`

**解决方案：**
```bash
# 1. 查看容器日志
docker logs vds-do-server

# 2. 检查环境变量配置
docker-compose config | grep environment

# 3. 检查网络连通性
docker exec vds-do-server ping 192.168.1.20
```

### 问题4：健康检查失败

**症状：** `curl http://localhost:5001/health` 返回 Connection refused

**解决方案：**
```bash
# 1. 检查容器状态
docker-compose ps

# 2. 查看容器日志
docker-compose logs do-server

# 3. 检查端口是否开放
netstat -tuln | grep 5001

# 4. 如果有防火墙，确保端口已开放
sudo ufw allow 5001/tcp
```

### 问题5：机器间无法通信

**症状：** 从机器1无法 ping 通或连接到机器2

**解决方案：**
```bash
# 1. 检查基本连通性
ping 192.168.1.20

# 2. 检查特定端口
telnet 192.168.1.20 5002

# 3. 检查防火墙规则
sudo ufw status

# 4. 如果有云服务商的安全组，也要在那边开放端口
```

### 问题6：内存不足导致构建失败

**症状：** 构建过程中出现 "out of memory" 错误

**解决方案：**
```bash
# 1. 检查可用内存
free -h

# 2. 增加 Docker 可用内存
sudo systemctl edit docker

# 添加以下内容：
# [Service]
# Environment="DOCKER_MEMORY_LIMIT=2g"

# 3. 重启 Docker
sudo systemctl restart docker
```

---

## 📞 获取更多帮助

- **部署指南：** 查看 `MULTI_MACHINE_DEPLOYMENT.md`
- **快速参考：** 查看 `QUICK_REFERENCE.md`
- **脚本说明：** 查看各脚本文件的头部注释

---

## 🎯 部署流程总结

```
┌─────────────────────────────────────────────┐
│ 步骤1：获取三台云服务器                      │
│ (Ubuntu 22.04 LTS)                          │
└──────────────┬──────────────────────────────┘
               ▼
┌─────────────────────────────────────────────┐
│ 步骤2：在三台机器上运行                      │
│ sudo bash init-environment.sh                │
│ (耗时约 5-10 分钟)                          │
└──────────────┬──────────────────────────────┘
               ▼
┌─────────────────────────────────────────────┐
│ 步骤3：在三台机器上克隆项目代码              │
│ git clone <repo-url> vds-project             │
└──────────────┬──────────────────────────────┘
               ▼
┌─────────────────────────────────────────────┐
│ 步骤4：在三台机器上分别运行                  │
│ ./deploy-machine-N.sh <IP1> <IP2> <IP3>     │
│ (耗时约 15-20 分钟)                         │
└──────────────┬──────────────────────────────┘
               ▼
┌─────────────────────────────────────────────┐
│ 步骤5：验证部署                              │
│ curl http://<IP>:500X/health                │
└──────────────┬──────────────────────────────┘
               ▼
┌─────────────────────────────────────────────┐
│ ✅ 部署完成！                               │
│ 系统已就绪，可以开始测试                    │
└─────────────────────────────────────────────┘
```

---

## 🎉 恭喜！

如果你看到了这段消息，说明你已经成功部署了完整的分布式 VDS 系统！

现在你可以：
1. 运行端到端测试
2. 开发新功能
3. 进行性能测试
4. 进行多机协作测试

祝你使用愉快！🚀
