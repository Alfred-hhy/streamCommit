# VDS 多机部署快速指南

## 📋 前置条件

- 三台 Linux 服务器（或 WSL）
- 已安装 Docker 和 docker-compose
- 三台机器在同一网络，可以互相 ping 通
- 防火墙已开放相关端口

---

## 🚀 快速部署（5分钟）

### 第1步：确认三台机器的IP

```bash
# 在每台机器上运行
hostname -I

# 假设得到以下结果：
# 机器1: 192.168.1.10   (DO Server)
# 机器2: 192.168.1.20   (SS Server)
# 机器3: 192.168.1.30   (Verifier Server)
```

### 第2步：在每台机器上克隆代码

```bash
# 在三台机器上都运行
git clone https://github.com/your-repo/try1028.git
cd try1028
```

### 第3步：使用配置模板

下面为三台机器分别准备了 `docker-compose.yml`

#### 机器1 (192.168.1.10) - DO Server

创建文件 `docker-compose.yml`：

```bash
cat > docker-compose.yml << 'EOF'
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
      - SS_HOST=192.168.1.20
      - SS_PORT=5002
      - VERIFIER_HOST=192.168.1.30
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
```

#### 机器2 (192.168.1.20) - SS Server

创建文件 `docker-compose.yml`：

```bash
cat > docker-compose.yml << 'EOF'
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
      - DO_HOST=192.168.1.10
      - DO_PORT=5001
      - VERIFIER_HOST=192.168.1.30
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
```

#### 机器3 (192.168.1.30) - Verifier Server

创建文件 `docker-compose.yml`：

```bash
cat > docker-compose.yml << 'EOF'
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
      - DO_HOST=192.168.1.10
      - DO_PORT=5001
      - SS_HOST=192.168.1.20
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
```

### 第4步：构建和启动

在每台机器上运行：

```bash
# 构建 Docker 镜像（第一次会比较慢，大约10-15分钟）
docker build -t vds-app:latest .

# 启动服务（后台运行）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 第5步：验证部署

```bash
# 在任何机器上测试所有服务
curl http://192.168.1.10:5001/health
curl http://192.168.1.20:5002/health
curl http://192.168.1.30:5003/health

# 如果返回 JSON，说明部署成功！
# {"status": "ok", "initialized": false}
```

---

## 🔧 防火墙配置（重要！）

每台机器都需要开放所有三个端口（这样才能跨机通信）：

```bash
# 机器1, 2, 3 都需要运行
sudo ufw allow 5001
sudo ufw allow 5002
sudo ufw allow 5003

# 验证
sudo ufw status
```

---

## 📝 完整的配置文件模板

### 环境变量对照表

| 配置项 | 机器1 (DO) | 机器2 (SS) | 机器3 (Verifier) |
|--------|-----------|-----------|-----------------|
| 自己的主机 | `DO_HOST=0.0.0.0` | `SS_HOST=0.0.0.0` | `VERIFIER_HOST=0.0.0.0` |
| 自己的端口 | `DO_PORT=5001` | `SS_PORT=5002` | `VERIFIER_PORT=5003` |
| DO 地址 | localhost | `192.168.1.10` | `192.168.1.10` |
| SS 地址 | `192.168.1.20` | localhost | `192.168.1.20` |
| Verifier 地址 | `192.168.1.30` | `192.168.1.30` | localhost |

### 自定义配置

如果你的 IP 地址不同，直接修改上面的 IP 即可。例如：

**如果你的网络是 10.0.0.x：**

机器1：
```yaml
environment:
  - SS_HOST=10.0.0.20
  - VERIFIER_HOST=10.0.0.30
```

**如果你只有一个子网，所有机器都在 172.16.0.x：**

机器1：
```yaml
environment:
  - SS_HOST=172.16.0.20
  - VERIFIER_HOST=172.16.0.30
```

---

## 🧪 测试多机部署

### 创建测试脚本 `test_distributed_deployment.py`

```python
#!/usr/bin/env python3
"""多机部署测试脚本"""

from distributed.client import DOClient, SSClient, VerifierClient
from charm.toolbox.pairinggroup import PairingGroup, ZR
import sys

# 这里改为你的实际 IP 地址
DO_URL = "http://192.168.1.10:5001"
SS_URL = "http://192.168.1.20:5002"
VERIFIER_URL = "http://192.168.1.30:5003"

def test_deployment():
    """测试完整的分布式部署"""

    print("=" * 60)
    print("VDS 多机部署测试")
    print("=" * 60)

    # 初始化客户端
    do_client = DOClient(DO_URL)
    ss_client = SSClient(SS_URL)
    verifier_client = VerifierClient(VERIFIER_URL)

    # 1. 健康检查
    print("\n[1] 健康检查...")
    try:
        result = do_client.health()
        print(f"  ✅ DO Server: {result}")
    except Exception as e:
        print(f"  ❌ DO Server 连接失败: {e}")
        return False

    try:
        result = ss_client.health()
        print(f"  ✅ SS Server: {result}")
    except Exception as e:
        print(f"  ❌ SS Server 连接失败: {e}")
        return False

    try:
        result = verifier_client.health()
        print(f"  ✅ Verifier Server: {result}")
    except Exception as e:
        print(f"  ❌ Verifier Server 连接失败: {e}")
        return False

    # 2. 初始化 DO
    print("\n[2] 初始化 DO Server...")
    try:
        init_result = do_client.init(n=16)
        print(f"  ✅ DO 初始化成功")
        crs = init_result['crs']
        global_pk = init_result['global_pk']
    except Exception as e:
        print(f"  ❌ DO 初始化失败: {e}")
        return False

    # 3. SS 初始化
    print("\n[3] 初始化 SS Server...")
    try:
        ss_client.init(crs=crs, global_pk=global_pk, server_acc_keys=init_result['server_acc_keys'])
        print(f"  ✅ SS 初始化成功")
    except Exception as e:
        print(f"  ❌ SS 初始化失败: {e}")
        return False

    # 4. Verifier 初始化
    print("\n[4] 初始化 Verifier Server...")
    try:
        verifier_client.init(crs=crs, global_pk=global_pk)
        print(f"  ✅ Verifier 初始化成功")
    except Exception as e:
        print(f"  ❌ Verifier 初始化失败: {e}")
        return False

    # 5. 创建批次
    print("\n[5] 创建批次...")
    try:
        data_vectors = [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]]
        time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

        batch_result = do_client.create_batch(data_vectors, time_vector)
        batch_id = batch_result['batch_id']
        print(f"  ✅ 批次创建成功: {batch_id}")
    except Exception as e:
        print(f"  ❌ 批次创建失败: {e}")
        return False

    # 6. SS 存储批次
    print("\n[6] SS 存储批次...")
    try:
        ss_client.store_batch(
            batch_id=batch_id,
            public_header=batch_result['public_header'],
            secrets_for_ss=batch_result['secrets_for_ss']
        )
        print(f"  ✅ 批次存储成功")
    except Exception as e:
        print(f"  ❌ 批次存储失败: {e}")
        return False

    # 7. SS 生成证明
    print("\n[7] SS 生成 DC 证明...")
    try:
        proof_result = ss_client.generate_dc_proof(
            batch_id=batch_id,
            t_challenge=[1]*16,
            f_current=global_pk['f_current'],
            column_index=0
        )
        print(f"  ✅ 证明生成成功")
    except Exception as e:
        print(f"  ❌ 证明生成失败: {e}")
        return False

    # 8. Verifier 验证
    print("\n[8] Verifier 验证证明...")
    try:
        verify_result = verifier_client.verify_dc_query(
            public_header=batch_result['public_header'],
            t_challenge=[1]*16,
            x_result=proof_result['x_result'],
            pi_audit=proof_result['pi_audit'],
            pi_non=proof_result['pi_non'],
            column_index=0
        )

        if verify_result['success']:
            print(f"  ✅ 验证通过！")
        else:
            print(f"  ❌ 验证失败！")
            return False
    except Exception as e:
        print(f"  ❌ 验证出错: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！多机部署成功！")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_deployment()
    sys.exit(0 if success else 1)
```

运行测试：

```bash
python3 test_distributed_deployment.py
```

---

## 🐛 故障排查

### 问题1：连接被拒绝

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**解决方案：**
```bash
# 检查服务是否正在运行
docker-compose ps

# 检查防火墙
sudo ufw status

# 检查日志
docker-compose logs
```

### 问题2：网络不通

```
requests.exceptions.ConnectionError: ...
```

**解决方案：**
```bash
# 检查 IP 是否正确
ping 192.168.1.20

# 检查 DNS
nslookup 192.168.1.20

# 测试端口连接
nc -zv 192.168.1.20 5002
```

### 问题3：容器启动失败

**解决方案：**
```bash
# 查看详细日志
docker-compose logs -f

# 重新构建镜像
docker-compose down
docker build --no-cache -t vds-app:latest .
docker-compose up -d
```

---

## 📊 监控和管理

### 查看实时日志

```bash
# 查看所有日志
docker-compose logs -f

# 查看特定服务日志
docker logs -f vds-do-server

# 查看最后100行日志
docker-compose logs --tail=100
```

### 容器管理

```bash
# 查看运行状态
docker-compose ps

# 重启服务
docker-compose restart

# 停止服务
docker-compose stop

# 启动服务
docker-compose start

# 删除容器
docker-compose down

# 删除镜像
docker image rm vds-app:latest
```

---

## 🔐 生产环境建议

### 1. 关闭开发模式

修改 `docker-compose.yml`：

```yaml
environment:
  - DEV_MODE=false  # 改为 false，不会泄露 alpha
```

### 2. 添加资源限制

```yaml
services:
  do-server:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### 3. 添加健康检查

```yaml
services:
  do-server:
    # ... 其他配置
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### 4. 使用 HTTPS

```yaml
services:
  do-server:
    # ... 其他配置
    ports:
      - "0.0.0.0:5001:5001"
    # 需要在服务代码中添加 SSL 证书支持
```

---

## 📞 常见问题

**Q: 三台机器必须在同一网络吗？**
A: 理论上可以跨网络，但需要正确配置 IP 地址和路由。

**Q: 可以用域名代替 IP 吗？**
A: 可以，但需要确保 DNS 能解析。直接用 IP 更稳定。

**Q: 容器内的端口必须是 5001/5002/5003 吗？**
A: 不必须，但建议保持一致以减少复杂性。

**Q: 如何扩展到更多服务？**
A: 添加新的 docker-compose.yml 配置，指向新的 IP 和端口。

**Q: 如何监控系统性能？**
A: 可以使用 Prometheus + Grafana，或简单的 `docker stats` 命令。

---

## ✅ 部署检查清单

- [ ] 三台机器 IP 地址已确认
- [ ] Docker 已在三台机器上安装
- [ ] 代码已克隆到三台机器
- [ ] docker-compose.yml 已根据 IP 修改
- [ ] 防火墙已开放 5001/5002/5003 端口
- [ ] 镜像已构建
- [ ] 容器已启动
- [ ] 健康检查通过
- [ ] 测试脚本已运行成功

---

## 🎉 下一步

部署成功后，你可以：

1. **学习代码** - 查看 `distributed/` 和核心模块
2. **开发新功能** - 修改代码并重新构建
3. **性能测试** - 运行 `test_bandwidth.py` 等
4. **生产部署** - 添加监控和备份

祝你部署顺利！

