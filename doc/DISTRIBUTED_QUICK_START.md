# VDS 分布式系统快速开始指南

## 🚀 5 分钟快速上手

### 前置要求

**方案一（本地多进程）**:
- Python 3.9+
- pip 包管理器
- 已安装项目依赖

**方案二（Docker）**:
- Docker 20.10+
- Docker Compose 1.29+

---

## 📦 方案一：本地多进程部署

### 步骤 1: 安装依赖

```bash
# 安装 Flask（如果还没有）
pip install flask flask-cors requests
```

### 步骤 2: 启动服务

```bash
# 方式 1: 使用启动脚本（推荐）
bash scripts/start_local.sh

# 方式 2: 手动启动
# 终端 1: 启动 DO Server
python distributed/do_server.py

# 终端 2: 启动 SS Server
python distributed/ss_server.py

# 终端 3: 启动 Verifier Server
python distributed/verifier_server.py
```

### 步骤 3: 验证服务

```bash
# 检查所有服务是否正常
curl http://localhost:5001/health  # DO Server
curl http://localhost:5002/health  # SS Server
curl http://localhost:5003/health  # Verifier Server

# 预期输出: {"status":"ok","timestamp":1699876543}
```

### 步骤 4: 运行测试

```bash
# 运行分布式测试
python -m pytest distributed_tests/test_distributed_e2e.py -v

# 运行性能测试
python distributed_tests/test_distributed_perf.py
```

### 步骤 5: 停止服务

```bash
# 使用停止脚本
bash scripts/stop_local.sh

# 或手动停止（Ctrl+C 每个终端）
```

---

## 🐳 方案二：Docker Compose 部署

### 步骤 1: 构建镜像

```bash
# 进入 docker 目录
cd docker

# 构建所有镜像
docker-compose build

# 或单独构建
docker-compose build do
docker-compose build ss
docker-compose build verifier
```

### 步骤 2: 启动服务

```bash
# 标准模式（无网络延迟）
docker-compose up -d

# 性能测试模式（包含网络延迟模拟）
docker-compose -f docker-compose.yml -f docker-compose.perf.yml up -d

# 查看日志
docker-compose logs -f
```

### 步骤 3: 验证服务

```bash
# 检查容器状态
docker-compose ps

# 检查健康状态
curl http://localhost:5001/health
curl http://localhost:5002/health
curl http://localhost:5003/health
```

### 步骤 4: 运行测试

```bash
# 在宿主机运行测试（连接到 Docker 服务）
python -m pytest distributed_tests/test_distributed_e2e.py -v

# 或在容器内运行
docker-compose exec do python -m pytest distributed_tests/ -v
```

### 步骤 5: 停止服务

```bash
# 停止并删除容器
docker-compose down

# 停止但保留容器
docker-compose stop

# 重启服务
docker-compose restart
```

---

## 📝 使用示例

### Python 客户端示例

```python
from distributed.client import DOClient, SSClient, VerifierClient

# 创建客户端
do = DOClient('http://localhost:5001')
ss = SSClient('http://localhost:5002')
verifier = VerifierClient('http://localhost:5003')

# 1. 初始化系统
init_data = do.init(n=8)
ss.init(init_data['crs'], init_data['server_keys'])
verifier.init(init_data['crs'], init_data['global_pk'])

# 2. 创建批次
m_matrix = [[10, 11, 12, 13, 14, 15, 16, 17]]  # 单列数据
t_vector = [1, 2, 3, 4, 5, 6, 7, 8]             # 时间向量

batch_data = do.create_batch(m_matrix, t_vector)
ss.store_batch(batch_data['batch_id'], 
               batch_data['header'], 
               batch_data['secrets'])

# 3. DC 查询
t_query = [1, 1, 1, 1, 1, 1, 1, 1]  # 求和查询
proof_data = ss.generate_dc_proof(batch_data['batch_id'], t_query)

# 4. 验证
result = verifier.verify_dc_query(
    proof_data['header'],
    proof_data['proof'],
    proof_data['result'],
    t_query
)

print(f"验证结果: {result['is_valid']}")  # True
```

### cURL 示例

```bash
# 1. 初始化 DO
curl -X POST http://localhost:5001/init \
  -H "Content-Type: application/json" \
  -d '{"n": 8}'

# 2. 创建批次
curl -X POST http://localhost:5001/create_batch \
  -H "Content-Type: application/json" \
  -d '{
    "m_matrix": [["<base64>", "<base64>", ...]],
    "t_vector": ["<base64>", "<base64>", ...]
  }'

# 3. 存储批次
curl -X POST http://localhost:5002/store_batch \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "a1b2c3d4...",
    "header": {...},
    "secrets": {...}
  }'
```

---

## 🔍 故障排查

### 问题 1: 端口被占用

**错误**: `Address already in use`

**解决**:
```bash
# 查找占用端口的进程
lsof -i :5001
lsof -i :5002
lsof -i :5003

# 杀死进程
kill -9 <PID>
```

### 问题 2: 服务无法连接

**错误**: `Connection refused`

**解决**:
```bash
# 检查服务是否启动
ps aux | grep "do_server\|ss_server\|verifier_server"

# 检查防火墙
sudo ufw status

# 检查日志
tail -f logs/do_server.log
```

### 问题 3: Docker 容器无法启动

**错误**: `Container exited with code 1`

**解决**:
```bash
# 查看容器日志
docker-compose logs do
docker-compose logs ss
docker-compose logs verifier

# 重新构建镜像
docker-compose build --no-cache

# 清理并重启
docker-compose down -v
docker-compose up -d
```

---

## 📊 性能测试快速开始

### 运行完整性能测试

```bash
# 1. 启动服务（标准模式）
bash scripts/start_local.sh

# 2. 运行性能测试
python distributed_tests/test_distributed_perf.py

# 3. 生成可视化图表
python distributed_tests/distributed_performance_analysis.py

# 4. 查看结果
ls -lh distributed_perf_*.png
```

### 对比测试（本地 vs 分布式）

```bash
# 1. 运行本地测试
python doc/e2e_performance_benchmark.py

# 2. 启动分布式服务
bash scripts/start_local.sh

# 3. 运行分布式测试
python distributed_tests/test_distributed_perf.py

# 4. 生成对比图表
python distributed_tests/test_local_vs_distributed.py
```

---

## 🎯 下一步

- 📖 阅读 [完整实现计划](DISTRIBUTED_E2E_IMPLEMENTATION_PLAN.md)
- 📚 查看 [API 参考文档](DISTRIBUTED_API_REFERENCE.md)
- 🧪 运行 [分布式测试](../distributed_tests/)
- 📊 查看 [性能分析结果](../distributed_perf_results.json)


