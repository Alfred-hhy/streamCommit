# VDS 多机部署快速参考卡片

## 🚀 30秒快速开始

```bash
# 第1步：运行配置助手
chmod +x setup-deployment.sh
./setup-deployment.sh

# 第2步：构建镜像
docker build -t vds-app:latest .

# 第3步：启动服务
docker-compose up -d

# 第4步：验证
curl http://localhost:5001/health
curl http://localhost:5002/health
curl http://localhost:5003/health
```

---

## 📋 配置文件速查表

### 机器1 (DO Server) - 192.168.1.10

```yaml
ports:
  - "0.0.0.0:5001:5001"
environment:
  - DO_HOST=0.0.0.0
  - SS_HOST=192.168.1.20      # ← 改这个
  - VERIFIER_HOST=192.168.1.30 # ← 改这个
```

### 机器2 (SS Server) - 192.168.1.20

```yaml
ports:
  - "0.0.0.0:5002:5002"
environment:
  - SS_HOST=0.0.0.0
  - DO_HOST=192.168.1.10       # ← 改这个
  - VERIFIER_HOST=192.168.1.30 # ← 改这个
```

### 机器3 (Verifier) - 192.168.1.30

```yaml
ports:
  - "0.0.0.0:5003:5003"
environment:
  - VERIFIER_HOST=0.0.0.0
  - DO_HOST=192.168.1.10       # ← 改这个
  - SS_HOST=192.168.1.20       # ← 改这个
```

---

## 🔧 常用命令

| 操作 | 命令 |
|------|------|
| 构建镜像 | `docker build -t vds-app:latest .` |
| 启动服务 | `docker-compose up -d` |
| 查看日志 | `docker-compose logs -f` |
| 查看状态 | `docker-compose ps` |
| 重启服务 | `docker-compose restart` |
| 停止服务 | `docker-compose stop` |
| 启动服务 | `docker-compose start` |
| 删除容器 | `docker-compose down` |
| 进入容器 | `docker exec -it vds-do-server bash` |

---

## 🧪 快速测试

### 单服务测试

```bash
# 测试 DO Server
curl http://192.168.1.10:5001/health

# 测试 SS Server
curl http://192.168.1.20:5002/health

# 测试 Verifier Server
curl http://192.168.1.30:5003/health
```

### 完整端到端测试

```bash
python3 test_distributed_deployment.py
```

---

## 🔐 防火墙配置

```bash
# 开放端口
sudo ufw allow 5001
sudo ufw allow 5002
sudo ufw allow 5003

# 验证
sudo ufw status
```

---

## 🐛 故障排查

| 问题 | 解决方案 |
|------|---------|
| 连接拒绝 | `docker-compose logs` 查看错误 |
| 网络不通 | `ping 192.168.1.20` 检查连通性 |
| 容器不启动 | `docker-compose restart` 重启 |
| 端口被占用 | `lsof -i :5001` 检查占用 |

---

## 📊 环境变量速查表

```
DO_HOST          = 0.0.0.0          (本机)
DO_PORT          = 5001             (端口)
SS_HOST          = 192.168.1.20     (SS机器IP)
SS_PORT          = 5002             (SS端口)
VERIFIER_HOST    = 192.168.1.30     (Verifier机器IP)
VERIFIER_PORT    = 5003             (Verifier端口)
DEV_MODE         = true|false       (开发模式)
VECTOR_DIM       = 16               (向量维度)
PAIRING_CURVE    = MNT224           (配对曲线)
```

---

## 📁 文件清单

```
项目根目录/
├── MULTI_MACHINE_DEPLOYMENT.md    # 详细部署指南
├── QUICK_REFERENCE.md              # 快速参考（本文件）
├── docker-compose.machine1.yml     # 机器1配置模板
├── docker-compose.machine2.yml     # 机器2配置模板
├── docker-compose.machine3.yml     # 机器3配置模板
├── deploy.sh                       # 自动部署脚本
├── setup-deployment.sh             # 交互式配置助手
└── test_distributed_deployment.py  # 多机测试脚本
```

---

## ✅ 部署检查清单

- [ ] IP 地址已确认无误
- [ ] docker-compose.yml 已修改
- [ ] Docker 镜像已构建
- [ ] 三个服务都已启动
- [ ] 防火墙已开放端口
- [ ] 健康检查通过
- [ ] 端到端测试通过

---

## 💡 常见问题

**Q: 所有机器的 docker-compose.yml 都不一样吗？**
A: 是的，每台机器有自己专属的配置。只需改 IP 地址即可。

**Q: 可以自动生成配置吗？**
A: 可以，运行 `./setup-deployment.sh` 使用配置助手。

**Q: 支持自定义端口吗？**
A: 支持，但建议保持 5001/5002/5003 的约定。

**Q: 三台机器必须在同一网段吗？**
A: 理论上不必须，但需要网络连通性。

**Q: 如何查看实时日志？**
A: `docker-compose logs -f` 查看所有日志，或 `docker logs -f 容器名` 查看单个。

---

## 🎯 下一步

1. **阅读详细指南** → MULTI_MACHINE_DEPLOYMENT.md
2. **运行配置助手** → ./setup-deployment.sh
3. **构建镜像** → docker build -t vds-app:latest .
4. **启动服务** → docker-compose up -d
5. **运行测试** → python3 test_distributed_deployment.py

---

## 📞 获取帮助

- 详细文档：`MULTI_MACHINE_DEPLOYMENT.md`
- 问题排查：`MULTI_MACHINE_DEPLOYMENT.md` 中的 "故障排查" 章节
- 配置示例：`docker-compose.machine[1-3].yml`

---

**祝你部署顺利！🎉**
