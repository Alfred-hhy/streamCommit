# 通信带宽/开销测试指南

## 概述

本文档介绍了 VDS 系统中新增的**通信带宽/开销测试**功能。该功能通过测量对象序列化后的字节大小来评估通信开销，直观展示了向量承诺（Vector Commitment）的核心优势：**证明大小为 O(1)，与数据量 N 无关**。

## 核心优势

### 1. 恒定大小的证明
无论数据向量的大小 N 如何增长，证明的大小始终保持恒定（约 180-188 字节）。这是向量承诺的核心特性。

### 2. 恒定大小的承诺
数据承诺（Header）的大小也保持恒定，不随数据量增长。

### 3. 显著的压缩比
当 N 增大时，证明相对于原始数据的压缩比显著提升：
- N=4: 0.35x（证明比原始数据大）
- N=32: 2.78x
- N=64: 5.51x
- N=128: 11.13x

## 测试方法

### 序列化方式
使用 `charm.core.engine.util.objectToBytes` 进行对象序列化，然后用 `len()` 测量字节大小。

**注意**：严禁使用 `tracemalloc` 测量带宽，因为那是测量内存使用，而非通信开销。

### 测试指标

1. **Header Size（承诺大小）**
   - 生成数据承诺 C = commit_G(m, γ, crs)
   - 序列化并测量字节数

2. **Proof Size（证明大小）**
   - 生成聚合证明 π_agg = prove_agg_open(C, m, γ, indices, t, crs)
   - 序列化并测量字节数

3. **Raw Data Size（原始数据大小）**
   - 理论值：N × 32 字节（假设每个 ZR 元素约 32 字节）
   - 用于对比基准

## 使用方法

### 方法 1：运行完整基准测试

```bash
cd /home/alfred/files/stream/try1028
python doc/performance_benchmark.py
```

这将运行所有性能测试，包括带宽测试，并生成 `try1028/benchmark_results.json`。

### 方法 2：只运行带宽测试

```bash
python test_bandwidth.py
```

这将只运行带宽测试，速度更快，适合快速验证。

### 方法 3：生成可视化图表

```bash
# 先运行基准测试
python doc/performance_benchmark.py

# 然后生成图表
python doc/performance_analysis.py
```

这将生成 `perf_bandwidth.png` 图表，展示三条曲线：
- **Header Size**（蓝色）：承诺大小，水平直线
- **Proof Size**（紫色）：证明大小，水平直线
- **Raw Data Size**（橙色）：原始数据大小，线性增长

**重要**：图表使用对数坐标（Y 轴），以便同时清晰显示恒定的证明大小和快速增长的原始数据大小。

## 测试结果示例

```
向量大小 (n)        Header (B)      Proof (B)       Raw Data (B)    压缩比       
----------------------------------------------------------------------
4               184             180             128             0.35x
8               188             180             256             0.70x
16              180             184             512             1.41x
32              188             180             1024            2.78x
64              188             184             2048            5.51x
128             184             184             4096            11.13x
```

## 关键观察

1. **Header 和 Proof 大小保持恒定**
   - 约 180-188 字节
   - 与向量大小 N 无关
   - 展示了 O(1) 的空间复杂度

2. **Raw Data 大小线性增长**
   - N=4: 128 字节
   - N=128: 4096 字节
   - 展示了 O(N) 的空间复杂度

3. **压缩比随 N 增大而提升**
   - 当 N=128 时，证明大小仅为原始数据的 1/11
   - 这意味着验证者只需下载 9% 的数据量即可验证

## 实际应用意义

### 1. 云存储审计
- 客户端只需下载固定大小的证明（~180 字节）
- 无需下载全部数据即可验证完整性
- 节省带宽和时间

### 2. 区块链数据可用性
- 轻节点只需下载证明，无需下载全部区块数据
- 显著降低存储和带宽需求

### 3. 分布式系统
- 节点间同步只需传输证明
- 降低网络开销

## 技术细节

### 代码位置

1. **基准测试代码**：`doc/performance_benchmark.py`
   - `benchmark_bandwidth()` 方法

2. **可视化代码**：`doc/performance_analysis.py`
   - `plot_bandwidth_analysis()` 方法

3. **测试脚本**：`test_bandwidth.py`

### 关键实现

```python
from charm.core.engine.util import objectToBytes

# 测量承诺大小
C = commit_G(m, gamma, crs)
C_bytes = objectToBytes(C, group)
header_size = len(C_bytes)

# 测量证明大小
pi_agg = prove_agg_open(C, m, gamma, indices, t, crs)
pi_bytes = objectToBytes(pi_agg, group)
proof_size = len(pi_bytes)
```

## 注意事项

1. **使用正确的序列化方法**
   - 必须使用 `objectToBytes`
   - 不要使用 `tracemalloc`（那是测量内存）

2. **对数坐标的重要性**
   - 由于证明大小和原始数据大小差距巨大
   - 必须使用对数坐标才能同时清晰显示两者

3. **中文字体警告**
   - 可能会出现中文字体缺失警告
   - 不影响图表生成，可以忽略

## 总结

通信带宽测试清晰地展示了 VDS 系统基于向量承诺的核心优势：
- ✅ 证明大小 O(1)，恒定不变
- ✅ 承诺大小 O(1)，恒定不变
- ✅ 压缩比随数据量增大而提升
- ✅ 显著降低通信开销

这使得 VDS 系统非常适合需要高效验证的场景，如云存储审计、区块链数据可用性等。

