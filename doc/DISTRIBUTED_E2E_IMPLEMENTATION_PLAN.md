# VDS 分布式端到端测试实现计划

## 📋 目标

实现真正的分布式端到端测试，支持：
1. ✅ 多进程/多机器部署
2. ✅ 真实的网络通信（HTTP/REST API）
3. ✅ 真实的序列化/反序列化
4. ✅ 网络延迟和带宽模拟
5. ✅ 性能测量（包括网络开销）

---

## 🎯 实现路线图

### 阶段 1: 本地多进程 + HTTP（方案一）
**目标**: 在单机上实现分布式架构，测试基本功能  
**时间**: 1-2 天  
**难度**: ⭐⭐☆☆☆

### 阶段 2: Docker Compose（方案二）
**目标**: 容器化部署，支持网络模拟和多机部署  
**时间**: 1-2 天  
**难度**: ⭐⭐⭐☆☆

### 阶段 3: 性能测试与分析
**目标**: 完整的性能测试和可视化  
**时间**: 1 天  
**难度**: ⭐⭐☆☆☆

---

## 📐 系统架构设计

### 角色与端口分配

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   DataOwner     │         │ StorageServer   │         │    Verifier     │
│   (DO Server)   │         │   (SS Server)   │         │  (Ver Server)   │
│   Port: 5001    │         │   Port: 5002    │         │   Port: 5003    │
└─────────────────┘         └─────────────────┘         └─────────────────┘
        │                           │                           │
        │  POST /create_batch       │                           │
        ├──────────────────────────>│                           │
        │                           │                           │
        │                           │  POST /verify_dc_query    │
        │                           │<──────────────────────────┤
        │                           │                           │
        │  POST /revoke_batch       │                           │
        ├──────────────────────────>│                           │
        │                           │                           │
        │                           │  POST /update_global_pk   │
        │                           ├──────────────────────────>│
```

### API 端点设计

#### DO Server (Port 5001)

| 端点 | 方法 | 功能 | 输入 | 输出 |
|------|------|------|------|------|
| `/health` | GET | 健康检查 | - | `{status: "ok"}` |
| `/init` | POST | 初始化系统 | `{n: int}` | `{crs, global_pk, server_keys}` |
| `/create_batch` | POST | 创建批次 | `{m_matrix, t_vector}` | `{batch_id, header, secrets}` |
| `/revoke_batch` | POST | 撤销批次 | `{sigma}` | `{g_s_q_new, new_global_pk, sigma_bytes}` |
| `/update_batch` | POST | 更新批次 | `{old_header, new_m_matrix, new_t_vector}` | `{g_s_q_new, new_global_pk, sigma_bytes, new_batch_id, new_header, new_secrets}` |

#### SS Server (Port 5002)

| 端点 | 方法 | 功能 | 输入 | 输出 |
|------|------|------|------|------|
| `/health` | GET | 健康检查 | - | `{status: "ok"}` |
| `/init` | POST | 初始化存储 | `{crs, server_keys}` | `{status: "ok"}` |
| `/store_batch` | POST | 存储批次 | `{batch_id, header, secrets}` | `{status: "ok"}` |
| `/generate_dc_proof` | POST | 生成 DC 证明 | `{batch_id, t_query}` | `{proof, result}` |
| `/generate_da_proof` | POST | 生成 DA 证明 | `{batch_id}` | `{proof}` |
| `/generate_time_proofs` | POST | 生成时间证明 | `{batch_id}` | `{time_proofs}` |
| `/update_batch` | POST | 更新批次 | `{old_batch_id, g_s_q_new, sigma_bytes, new_batch_id, new_header, new_secrets}` | `{status: "ok"}` |
| `/add_server_key` | POST | 添加服务器密钥 | `{g_s_q_new}` | `{status: "ok"}` |
| `/add_revoked_item` | POST | 添加撤销项 | `{sigma_bytes}` | `{status: "ok"}` |

#### Verifier Server (Port 5003)

| 端点 | 方法 | 功能 | 输入 | 输出 |
|------|------|------|------|------|
| `/health` | GET | 健康检查 | - | `{status: "ok"}` |
| `/init` | POST | 初始化验证器 | `{crs, global_pk}` | `{status: "ok"}` |
| `/verify_dc_query` | POST | 验证 DC 查询 | `{header, proof, result, t_query}` | `{is_valid: bool}` |
| `/verify_da_audit` | POST | 验证 DA 审计 | `{header, proof}` | `{is_valid: bool}` |
| `/verify_time_proofs` | POST | 验证时间证明 | `{header, time_proofs}` | `{is_valid: bool}` |
| `/update_global_pk` | POST | 更新全局公钥 | `{new_global_pk}` | `{status: "ok"}` |

---

## 🔧 数据序列化格式

### 问题：Charm 对象无法直接 JSON 序列化

Charm 库的群元素（G1, G2, ZR）无法直接转换为 JSON。

### 解决方案：使用 Base64 编码

```python
from charm.core.engine.util import objectToBytes, bytesToObject
import base64
import json

# 序列化
def serialize_charm_object(obj):
    """将 Charm 对象序列化为 Base64 字符串"""
    obj_bytes = objectToBytes(obj, group)
    return base64.b64encode(obj_bytes).decode('utf-8')

# 反序列化
def deserialize_charm_object(b64_str):
    """将 Base64 字符串反序列化为 Charm 对象"""
    obj_bytes = base64.b64decode(b64_str.encode('utf-8'))
    return bytesToObject(obj_bytes, group)

# 序列化复杂对象
def serialize_header(header):
    """序列化批次头部"""
    return {
        'C_data_list': [serialize_charm_object(C) for C in header['C_data_list']],
        'C_time': serialize_charm_object(header['C_time']),
        'sigma': base64.b64encode(header['sigma']).decode('utf-8')
    }

# 反序列化复杂对象
def deserialize_header(header_dict):
    """反序列化批次头部"""
    return {
        'C_data_list': [deserialize_charm_object(C) for C in header_dict['C_data_list']],
        'C_time': deserialize_charm_object(header_dict['C_time']),
        'sigma': base64.b64decode(header_dict['sigma'].encode('utf-8'))
    }
```

### 序列化工具模块

创建 `distributed/serialization.py`：
- `serialize_*()` - 序列化各种对象
- `deserialize_*()` - 反序列化各种对象
- 支持：G1, G2, ZR, list, dict, bytes

---

## 📁 文件结构

```
try1028/
├── distributed/                    # 新增：分布式组件
│   ├── __init__.py
│   ├── serialization.py           # 序列化工具
│   ├── do_server.py               # DO 服务器
│   ├── ss_server.py               # SS 服务器
│   ├── verifier_server.py         # Verifier 服务器
│   ├── client.py                  # 客户端库（封装 HTTP 调用）
│   └── config.py                  # 配置文件
│
├── distributed_tests/              # 新增：分布式测试
│   ├── __init__.py
│   ├── test_distributed_basic.py  # 基础功能测试
│   ├── test_distributed_e2e.py    # 端到端测试
│   └── test_distributed_perf.py   # 性能测试
│
├── docker/                         # 新增：Docker 配置
│   ├── Dockerfile.do              # DO 镜像
│   ├── Dockerfile.ss              # SS 镜像
│   ├── Dockerfile.verifier        # Verifier 镜像
│   ├── docker-compose.yml         # 编排文件
│   └── docker-compose.perf.yml    # 性能测试编排
│
├── scripts/                        # 新增：启动脚本
│   ├── start_local.sh             # 启动本地多进程
│   ├── stop_local.sh              # 停止本地进程
│   ├── start_docker.sh            # 启动 Docker
│   └── run_distributed_tests.sh   # 运行分布式测试
│
└── doc/
    ├── DISTRIBUTED_E2E_IMPLEMENTATION_PLAN.md  # 本文档
    ├── DISTRIBUTED_API_REFERENCE.md            # API 参考文档
    └── DISTRIBUTED_DEPLOYMENT_GUIDE.md         # 部署指南
```

---

## 🚀 阶段 1: 本地多进程 + HTTP（方案一）

### 1.1 创建序列化工具 (`distributed/serialization.py`)

**功能**:
- 序列化/反序列化 Charm 对象（G1, G2, ZR）
- 序列化/反序列化复杂对象（header, secrets, proof）
- 支持 JSON 传输

**关键函数**:
```python
serialize_g1(obj: G1) -> str
deserialize_g1(s: str) -> G1
serialize_header(header: dict) -> dict
deserialize_header(data: dict) -> dict
serialize_proof(proof: dict) -> dict
deserialize_proof(data: dict) -> dict
```

### 1.2 创建 DO 服务器 (`distributed/do_server.py`)

**技术栈**: Flask + Flask-CORS  
**端口**: 5001

**核心代码结构**:
```python
from flask import Flask, request, jsonify
from vds_owner import DataOwner
from distributed.serialization import *

app = Flask(__name__)
do = None  # 全局 DataOwner 实例

@app.route('/init', methods=['POST'])
def init():
    global do
    data = request.json
    n = data['n']
    # 初始化 DO
    # 返回 CRS, global_pk, server_keys

@app.route('/create_batch', methods=['POST'])
def create_batch():
    # 接收 m_matrix, t_vector
    # 调用 do.create_batch()
    # 返回序列化的结果

# ... 其他端点
```

### 1.3 创建 SS 服务器 (`distributed/ss_server.py`)

**技术栈**: Flask + Flask-CORS  
**端口**: 5002

**核心代码结构**:
```python
from flask import Flask, request, jsonify
from vds_server import StorageServer
from distributed.serialization import *

app = Flask(__name__)
ss = None  # 全局 StorageServer 实例

@app.route('/init', methods=['POST'])
def init():
    global ss
    # 初始化 SS

@app.route('/store_batch', methods=['POST'])
def store_batch():
    # 接收并反序列化数据
    # 调用 ss.store_batch()

# ... 其他端点
```

### 1.4 创建 Verifier 服务器 (`distributed/verifier_server.py`)

**技术栈**: Flask + Flask-CORS  
**端口**: 5003

### 1.5 创建客户端库 (`distributed/client.py`)

**功能**: 封装 HTTP 调用，提供简洁的 API

```python
class DOClient:
    def __init__(self, base_url='http://localhost:5001'):
        self.base_url = base_url
    
    def init(self, n):
        response = requests.post(f'{self.base_url}/init', json={'n': n})
        return response.json()
    
    def create_batch(self, m_matrix, t_vector):
        data = {
            'm_matrix': serialize_matrix(m_matrix),
            't_vector': serialize_vector(t_vector)
        }
        response = requests.post(f'{self.base_url}/create_batch', json=data)
        return deserialize_batch_response(response.json())

class SSClient:
    # 类似实现

class VerifierClient:
    # 类似实现
```

### 1.6 创建启动脚本 (`scripts/start_local.sh`)

```bash
#!/bin/bash

# 启动 DO 服务器
python distributed/do_server.py &
DO_PID=$!

# 启动 SS 服务器
python distributed/ss_server.py &
SS_PID=$!

# 启动 Verifier 服务器
python distributed/verifier_server.py &
VER_PID=$!

echo "DO Server PID: $DO_PID"
echo "SS Server PID: $SS_PID"
echo "Verifier Server PID: $VER_PID"

# 保存 PID 到文件
echo "$DO_PID $SS_PID $VER_PID" > .server_pids
```

### 1.7 创建分布式测试 (`distributed_tests/test_distributed_e2e.py`)

```python
import pytest
from distributed.client import DOClient, SSClient, VerifierClient

def test_distributed_batch_creation():
    """测试分布式批次创建"""
    do_client = DOClient('http://localhost:5001')
    ss_client = SSClient('http://localhost:5002')
    
    # 初始化
    init_data = do_client.init(n=8)
    ss_client.init(init_data['crs'], init_data['server_keys'])
    
    # 创建批次
    m_matrix = [[10, 11, 12, 13, 14, 15, 16, 17]]
    t_vector = [1, 2, 3, 4, 5, 6, 7, 8]
    batch_data = do_client.create_batch(m_matrix, t_vector)
    
    # 存储批次
    ss_client.store_batch(batch_data['batch_id'], 
                          batch_data['header'], 
                          batch_data['secrets'])
    
    assert True  # 如果没有异常，测试通过
```

---

## 🐳 阶段 2: Docker Compose（方案二）

### 2.1 创建 Dockerfile (`docker/Dockerfile.do`)

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgmp-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["python", "distributed/do_server.py"]
```

类似创建 `Dockerfile.ss` 和 `Dockerfile.verifier`

### 2.2 创建 Docker Compose 配置 (`docker/docker-compose.yml`)

```yaml
version: '3.8'

services:
  do:
    build:
      context: ..
      dockerfile: docker/Dockerfile.do
    container_name: vds_do
    ports:
      - "5001:5001"
    networks:
      vds_network:
        ipv4_address: 172.20.0.2
    environment:
      - FLASK_ENV=production
      - HOST=0.0.0.0
      - PORT=5001
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  ss:
    build:
      context: ..
      dockerfile: docker/Dockerfile.ss
    container_name: vds_ss
    ports:
      - "5002:5002"
    networks:
      vds_network:
        ipv4_address: 172.20.0.3
    environment:
      - FLASK_ENV=production
      - HOST=0.0.0.0
      - PORT=5002
    depends_on:
      - do
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5002/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  verifier:
    build:
      context: ..
      dockerfile: docker/Dockerfile.verifier
    container_name: vds_verifier
    ports:
      - "5003:5003"
    networks:
      vds_network:
        ipv4_address: 172.20.0.4
    environment:
      - FLASK_ENV=production
      - HOST=0.0.0.0
      - PORT=5003
    depends_on:
      - do
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5003/health"]
      interval: 10s
      timeout: 5s
      retries: 3

networks:
  vds_network:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.20.0.0/16
```

### 2.3 网络延迟模拟配置

创建 `docker/docker-compose.perf.yml`（性能测试专用）：

```yaml
version: '3.8'

services:
  do:
    extends:
      file: docker-compose.yml
      service: do
    cap_add:
      - NET_ADMIN  # 允许使用 tc 命令
    command: >
      sh -c "
        apt-get update && apt-get install -y iproute2 &&
        tc qdisc add dev eth0 root netem delay 50ms &&
        python distributed/do_server.py
      "

  ss:
    extends:
      file: docker-compose.yml
      service: ss
    cap_add:
      - NET_ADMIN
    command: >
      sh -c "
        apt-get update && apt-get install -y iproute2 &&
        tc qdisc add dev eth0 root netem delay 100ms &&
        python distributed/ss_server.py
      "

  verifier:
    extends:
      file: docker-compose.yml
      service: verifier
    cap_add:
      - NET_ADMIN
    command: >
      sh -c "
        apt-get update && apt-get install -y iproute2 &&
        tc qdisc add dev eth0 root netem delay 30ms &&
        python distributed/verifier_server.py
      "
```

**网络模拟参数**:
- DO: 50ms 延迟（模拟轻量级设备）
- SS: 100ms 延迟（模拟云服务器）
- Verifier: 30ms 延迟（模拟本地验证）

### 2.4 Docker 启动脚本 (`scripts/start_docker.sh`)

```bash
#!/bin/bash

echo "🐳 启动 VDS 分布式系统（Docker Compose）"

# 检查是否使用性能测试配置
if [ "$1" == "perf" ]; then
    echo "📊 使用性能测试配置（包含网络延迟模拟）"
    docker-compose -f docker/docker-compose.yml -f docker/docker-compose.perf.yml up -d
else
    echo "🚀 使用标准配置"
    docker-compose -f docker/docker-compose.yml up -d
fi

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 健康检查
echo "🔍 检查服务健康状态..."
curl -s http://localhost:5001/health && echo "✅ DO Server OK"
curl -s http://localhost:5002/health && echo "✅ SS Server OK"
curl -s http://localhost:5003/health && echo "✅ Verifier Server OK"

echo "✅ 所有服务已启动！"
```

---

## 📊 阶段 3: 性能测试与分析

### 3.1 分布式性能测试 (`distributed_tests/test_distributed_perf.py`)

```python
"""
分布式端到端性能测试
测试真实的网络通信、序列化、延迟等
"""

import time
import json
from typing import List, Dict
from distributed.client import DOClient, SSClient, VerifierClient

class DistributedPerformanceBenchmark:
    """分布式性能基准测试"""

    def __init__(self,
                 do_url='http://localhost:5001',
                 ss_url='http://localhost:5002',
                 verifier_url='http://localhost:5003'):
        self.do_client = DOClient(do_url)
        self.ss_client = SSClient(ss_url)
        self.verifier_client = VerifierClient(verifier_url)
        self.results = {}

    def measure_time(self, func, *args, num_runs=10, **kwargs):
        """测量函数执行时间（包含网络延迟）"""
        times = []
        result = None

        for _ in range(num_runs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)

        avg_time = sum(times) / len(times)
        std_dev = (sum((t - avg_time)**2 for t in times) / len(times)) ** 0.5

        return avg_time, std_dev, result

    def benchmark_batch_creation(self, vector_sizes: List[int], num_runs=10):
        """
        测试批次创建的端到端性能（包含网络通信）

        测试流程：
        1. DO 创建批次（HTTP 请求 + 响应）
        2. SS 存储批次（HTTP 请求 + 响应）

        测量内容：
        - DO 创建时间（包含序列化 + 网络传输）
        - SS 存储时间（包含反序列化 + 存储）
        - 总时间
        - 数据传输大小
        """
        print("\n📊 分布式批次创建性能测试")
        print("=" * 70)

        results = {}

        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)

            # 初始化系统
            init_data = self.do_client.init(n)
            self.ss_client.init(init_data['crs'], init_data['server_keys'])
            self.verifier_client.init(init_data['crs'], init_data['global_pk'])

            # 生成测试数据
            m_matrix = [[i + 10 for i in range(n)]]
            t_vector = [i + 1 for i in range(n)]

            # 测试 DO 创建批次（包含网络通信）
            def create_batch():
                return self.do_client.create_batch(m_matrix, t_vector)

            t1, s1, batch_data = self.measure_time(create_batch, num_runs=num_runs)

            # 测试 SS 存储批次（包含网络通信）
            def store_batch():
                return self.ss_client.store_batch(
                    batch_data['batch_id'],
                    batch_data['header'],
                    batch_data['secrets']
                )

            t2, s2, _ = self.measure_time(store_batch, num_runs=num_runs)

            # 总时间
            total_time = t1 + t2
            total_std = (s1**2 + s2**2) ** 0.5

            results[n] = {
                'do_create': t1,
                'ss_store': t2,
                'total': total_time,
                'do_create_std': s1,
                'ss_store_std': s2,
                'total_std': total_std
            }

            print(f"✓ DO:{t1*1000:.2f}±{s1*1000:.2f}ms "
                  f"SS:{t2*1000:.2f}±{s2*1000:.2f}ms "
                  f"总:{total_time*1000:.2f}±{total_std*1000:.2f}ms")

        self.results['batch_creation'] = results
        return results

    def benchmark_dc_query(self, vector_sizes: List[int], num_runs=10):
        """测试 DC 查询的端到端性能"""
        # 类似实现
        pass

    def benchmark_update_batch(self, vector_sizes: List[int], num_runs=10):
        """测试批次更新的端到端性能"""
        # 类似实现
        pass

    def save_results(self, filename='distributed_perf_results.json'):
        """保存测试结果"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 结果已保存到 {filename}")
```

### 3.2 性能对比测试

创建 `distributed_tests/test_local_vs_distributed.py`：

```python
"""
对比本地测试 vs 分布式测试的性能差异
"""

def test_performance_comparison():
    """
    对比测试：
    1. 本地测试（直接函数调用）
    2. 本地分布式（localhost HTTP）
    3. Docker 分布式（容器间通信）
    4. Docker 分布式 + 网络延迟模拟

    预期结果：
    - 本地测试最快（无序列化、无网络）
    - 本地分布式稍慢（有序列化、localhost 网络）
    - Docker 分布式更慢（容器间网络）
    - Docker + 延迟最慢（模拟真实网络）
    """

    vector_sizes = [8, 16, 32, 64]

    # 1. 本地测试
    local_results = run_local_benchmark(vector_sizes)

    # 2. 本地分布式
    local_dist_results = run_local_distributed_benchmark(vector_sizes)

    # 3. Docker 分布式
    docker_results = run_docker_benchmark(vector_sizes)

    # 4. Docker + 延迟
    docker_perf_results = run_docker_perf_benchmark(vector_sizes)

    # 生成对比图表
    plot_comparison(local_results, local_dist_results,
                   docker_results, docker_perf_results)
```

### 3.3 可视化分析 (`distributed_tests/distributed_performance_analysis.py`)

```python
"""
分布式性能测试结果可视化
"""

import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei']  # 中文支持

class DistributedPerformanceAnalysis:
    """分布式性能分析与可视化"""

    def __init__(self, results_file='distributed_perf_results.json'):
        with open(results_file, 'r') as f:
            self.results = json.load(f)

    def plot_network_overhead(self):
        """
        绘制网络开销分析图

        对比：
        - 本地测试时间（无网络）
        - 分布式测试时间（有网络）
        - 网络开销 = 分布式时间 - 本地时间
        """
        pass

    def plot_serialization_overhead(self):
        """
        绘制序列化开销分析图

        测量：
        - 序列化时间
        - 反序列化时间
        - 数据大小
        """
        pass

    def plot_latency_impact(self):
        """
        绘制网络延迟影响图

        对比：
        - 无延迟（localhost）
        - 50ms 延迟
        - 100ms 延迟
        - 200ms 延迟
        """
        pass

    def generate_all_plots(self):
        """生成所有图表"""
        self.plot_network_overhead()
        self.plot_serialization_overhead()
        self.plot_latency_impact()
        print("✅ 所有图表已生成")
```

---

## 📝 详细实现步骤

### 步骤 1: 创建序列化工具（1-2 小时）

**文件**: `distributed/serialization.py`

**任务清单**:
- [ ] 实现 `serialize_g1()`, `deserialize_g1()`
- [ ] 实现 `serialize_g2()`, `deserialize_g2()`
- [ ] 实现 `serialize_zr()`, `deserialize_zr()`
- [ ] 实现 `serialize_header()`, `deserialize_header()`
- [ ] 实现 `serialize_secrets()`, `deserialize_secrets()`
- [ ] 实现 `serialize_proof()`, `deserialize_proof()`
- [ ] 编写单元测试 `test_serialization.py`

**验收标准**:
- ✅ 所有 Charm 对象可以序列化为 JSON
- ✅ 反序列化后的对象与原对象相等
- ✅ 所有单元测试通过

### 步骤 2: 创建 DO 服务器（2-3 小时）

**文件**: `distributed/do_server.py`

**任务清单**:
- [ ] 实现 `/health` 端点
- [ ] 实现 `/init` 端点
- [ ] 实现 `/create_batch` 端点
- [ ] 实现 `/revoke_batch` 端点
- [ ] 实现 `/update_batch` 端点
- [ ] 添加错误处理和日志
- [ ] 编写 API 测试

**验收标准**:
- ✅ 所有端点正常工作
- ✅ 错误处理完善
- ✅ 日志清晰可读

### 步骤 3: 创建 SS 服务器（2-3 小时）

**文件**: `distributed/ss_server.py`

**任务清单**:
- [ ] 实现所有 API 端点（参考 API 设计）
- [ ] 添加错误处理和日志
- [ ] 编写 API 测试

### 步骤 4: 创建 Verifier 服务器（2-3 小时）

**文件**: `distributed/verifier_server.py`

**任务清单**:
- [ ] 实现所有 API 端点
- [ ] 添加错误处理和日志
- [ ] 编写 API 测试

### 步骤 5: 创建客户端库（1-2 小时）

**文件**: `distributed/client.py`

**任务清单**:
- [ ] 实现 `DOClient` 类
- [ ] 实现 `SSClient` 类
- [ ] 实现 `VerifierClient` 类
- [ ] 添加重试机制
- [ ] 添加超时处理

### 步骤 6: 创建启动脚本（1 小时）

**文件**: `scripts/start_local.sh`, `scripts/stop_local.sh`

**任务清单**:
- [ ] 编写启动脚本
- [ ] 编写停止脚本
- [ ] 添加健康检查
- [ ] 测试脚本功能

### 步骤 7: 编写分布式测试（2-3 小时）

**文件**: `distributed_tests/test_distributed_e2e.py`

**任务清单**:
- [ ] 测试批次创建
- [ ] 测试 DC 查询
- [ ] 测试 DA 审计
- [ ] 测试批次撤销
- [ ] 测试批次更新
- [ ] 所有测试通过

### 步骤 8: Docker 化（2-3 小时）

**文件**: `docker/Dockerfile.*`, `docker/docker-compose.yml`

**任务清单**:
- [ ] 创建 Dockerfile.do
- [ ] 创建 Dockerfile.ss
- [ ] 创建 Dockerfile.verifier
- [ ] 创建 docker-compose.yml
- [ ] 创建 docker-compose.perf.yml
- [ ] 测试 Docker 部署

### 步骤 9: 性能测试（2-3 小时）

**文件**: `distributed_tests/test_distributed_perf.py`

**任务清单**:
- [ ] 实现性能测试
- [ ] 运行本地测试
- [ ] 运行 Docker 测试
- [ ] 运行 Docker + 延迟测试
- [ ] 生成性能报告

### 步骤 10: 可视化分析（1-2 小时）

**文件**: `distributed_tests/distributed_performance_analysis.py`

**任务清单**:
- [ ] 实现可视化代码
- [ ] 生成对比图表
- [ ] 编写分析报告

---

## 📊 预期性能对比

### 本地测试 vs 分布式测试（n=32）

| 操作 | 本地测试 | 本地分布式 | Docker | Docker+延迟 |
|------|---------|-----------|--------|------------|
| **批次创建** | 20ms | 25ms (+25%) | 30ms (+50%) | 180ms (+800%) |
| **DC 查询** | 40ms | 50ms (+25%) | 60ms (+50%) | 260ms (+550%) |
| **DA 审计** | 80ms | 95ms (+19%) | 110ms (+38%) | 310ms (+288%) |
| **批次撤销** | 15ms | 20ms (+33%) | 25ms (+67%) | 175ms (+1067%) |

**关键发现**:
- 序列化开销：约 5-10ms
- 本地网络开销：约 5-10ms
- Docker 网络开销：约 10-15ms
- 网络延迟影响：50-100ms 延迟会显著增加总时间

---

## ✅ 验收标准

### 阶段 1 验收标准

- [ ] 所有服务器可以独立启动
- [ ] 所有 API 端点正常工作
- [ ] 客户端库可以正常调用所有 API
- [ ] 所有分布式测试通过
- [ ] 启动/停止脚本正常工作

### 阶段 2 验收标准

- [ ] Docker 镜像成功构建
- [ ] Docker Compose 成功启动所有服务
- [ ] 容器间通信正常
- [ ] 健康检查正常
- [ ] 网络延迟模拟生效

### 阶段 3 验收标准

- [ ] 性能测试成功运行
- [ ] 生成完整的性能报告
- [ ] 生成对比图表
- [ ] 性能数据符合预期

---

## 🎯 总结

### 方案一优势
- ✅ 实现简单，快速验证
- ✅ 易于调试
- ✅ 无需 Docker 知识
- ✅ 适合开发阶段

### 方案二优势
- ✅ 更接近真实环境
- ✅ 可以模拟网络延迟
- ✅ 易于部署到多机器
- ✅ 可重复性强
- ✅ 适合生产环境

### 迁移路径
1. 先实现方案一，验证功能
2. 添加 Docker 配置（代码零修改）
3. 测试 Docker 部署
4. 添加网络模拟
5. 运行完整性能测试

**预计总时间**: 3-5 天（包含测试和文档）


