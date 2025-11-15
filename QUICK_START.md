# 🚀 VDS 一键部署快速卡片

## ⚡ 最快开始（2分钟了解）

### 对于新租赁的三台云服务器

```bash
# 用这一条命令！

# 在机器1上：
sudo bash quick-deploy.sh 1 192.168.1.10 192.168.1.10 192.168.1.20 192.168.1.30

# 在机器2上：
sudo bash quick-deploy.sh 2 192.168.1.20 192.168.1.10 192.168.1.20 192.168.1.30

# 在机器3上：
sudo bash quick-deploy.sh 3 192.168.1.30 192.168.1.10 192.168.1.20 192.168.1.30
```

**就这样！等待 25-35 分钟，完成！** ✅

---

## 📋 三种部署方式

| 方式 | 命令 | 耗时 | 适合 |
|------|------|------|------|
| **最快** | `sudo bash quick-deploy.sh ...` | 25-35分钟 | 新手，快速启动 |
| **分步** | `sudo bash init-*.sh` + `./deploy-*.sh` | 30-40分钟 | 想了解细节 |
| **重新部署** | `./deploy-machine-X.sh ...` | 15-20分钟 | 已有环境 |

---

## 🎯 命令速查表

### 快速部署（推荐）
```bash
sudo bash quick-deploy.sh <机器ID> <本IP> <DO_IP> <SS_IP> <VERIFIER_IP>
```

### 分步部署
```bash
# 第1步：初始化（在三台机器上都运行）
sudo bash init-environment.sh

# 第2步：克隆代码
git clone <repo> vds-project
cd vds-project

# 第3步：部署（在各自机器上）
./deploy-machine-1.sh 192.168.1.10 192.168.1.20 192.168.1.30  # 机器1
./deploy-machine-2.sh 192.168.1.10 192.168.1.20 192.168.1.30  # 机器2
./deploy-machine-3.sh 192.168.1.10 192.168.1.20 192.168.1.30  # 机器3
```

### 验证
```bash
curl http://192.168.1.10:5001/health
curl http://192.168.1.20:5002/health
curl http://192.168.1.30:5003/health
```

---

## 📚 文件一览

| 文件 | 大小 | 用途 |
|------|------|------|
| `quick-deploy.sh` | 12K | 一键部署（推荐） |
| `init-environment.sh` | 8.2K | 环境初始化 |
| `deploy-machine-1.sh` | 9.0K | 机器1部署 |
| `deploy-machine-2.sh` | 9.0K | 机器2部署 |
| `deploy-machine-3.sh` | 9.1K | 机器3部署 |
| `CLOUD_DEPLOYMENT_GUIDE.md` | 12K | 详细部署指南 |
| `DEPLOYMENT_SCRIPTS_GUIDE.md` | 8.3K | 脚本选择指南 |
| `DEPLOYMENT_SUMMARY.txt` | 18K | 完整总结 |

---

## ❓ 常见问题

**Q: 我该用哪个脚本？**
A: 如果是全新服务器 → `quick-deploy.sh`（最简单）
如果想分步操作 → `init-*.sh` + `deploy-*.sh`

**Q: 参数顺序是什么？**
A: 都是 `DO_IP SS_IP VERIFIER_IP`（顺序固定）

**Q: 需要修改代码吗？**
A: 不需要，只改 IP 地址就行

**Q: 首次为什么这么慢？**
A: Docker 镜像首次构建需要 10-15 分钟（编译库）

**Q: 可以改端口吗？**
A: 可以，但不推荐（用 5001/5002/5003）

---

## 🔥 三台机器的 IP 该填什么？

假设你租了三台服务器：
- 192.168.1.10 → 做机器1 (DO Server)
- 192.168.1.20 → 做机器2 (SS Server)
- 192.168.1.30 → 做机器3 (Verifier)

那么你在**每台机器上**都填相同的 IP：

```bash
# 在 192.168.1.10 上：
sudo bash quick-deploy.sh 1 192.168.1.10 192.168.1.10 192.168.1.20 192.168.1.30
                          ↑ 机器ID=1  ↑ 本机IP    ↑ 三个IP都一样

# 在 192.168.1.20 上：
sudo bash quick-deploy.sh 2 192.168.1.20 192.168.1.10 192.168.1.20 192.168.1.30
                          ↑ 机器ID=2  ↑ 本机IP    ↑ 三个IP都一样

# 在 192.168.1.30 上：
sudo bash quick-deploy.sh 3 192.168.1.30 192.168.1.10 192.168.1.20 192.168.1.30
                          ↑ 机器ID=3  ↑ 本机IP    ↑ 三个IP都一样
```

---

## 🎯 部署流程（5步）

```
第1步：租服务器（3台 Ubuntu 22.04 LTS）
  ↓
第2步：获取 IP 地址（192.168.1.10/20/30）
  ↓
第3步：SSH 连接每台机器
  ↓
第4步：在每台机器上运行 quick-deploy.sh
  ↓
第5步：验证 curl http://<IP>:500X/health
  ↓
✅ 完成！系统已就绪
```

---

## 📞 需要帮助？

- **详细步骤** → 读 `CLOUD_DEPLOYMENT_GUIDE.md`
- **选择脚本** → 读 `DEPLOYMENT_SCRIPTS_GUIDE.md`
- **遇到问题** → 查看对应文档的"故障排查"章节
- **脚本细节** → 查看脚本文件的注释

---

## 🎉 就这么简单！

1️⃣  三台新服务器
2️⃣  一条命令 (`quick-deploy.sh`)
3️⃣  30 分钟
4️⃣  完整的分布式系统就启动了！

祝你使用愉快！🚀
