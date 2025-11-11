# VDS Scheme C+ 性能测试完整指南

## 📋 概述

本项目提供了两套完整的性能测试工具：

1. **密码学原语性能测试** - 测试底层密码学操作（CRS、承诺、证明、验证）
2. **端到端性能测试** - 测试完整的 VDS 工作流（批次创建、查询、审计、撤销、时间范围证明）

---

## 🎯 测试工具对比

| 测试类型 | 文件 | 测试内容 | 输出 |
|---------|------|---------|------|
| **密码学原语** | `doc/performance_benchmark.py` | CRS生成、承诺、证明、验证 | 7个PNG图表 + JSON |
| **端到端** | `doc/e2e_performance_benchmark.py` | 批次创建、查询、审计、撤销、时间范围证明 | 6个PNG图表 + JSON |

---

## 🚀 快速开始

### 选项 1: 运行密码学原语性能测试

```bash
cd try1028/doc

# 运行性能测试
python performance_benchmark.py

# 生成图表
python performance_analysis.py
```

**生成的图表**:
- `perf_crs_generation.png` - CRS 生成性能
- `perf_commitments.png` - 承诺生成对比
- `perf_proofs.png` - 证明生成对比
- `perf_verification.png` - 验证性能对比
- `perf_memory.png` - 内存使用
- `perf_complexity.png` - 复杂度分析
- `perf_summary.png` - 总体性能总结

**详细文档**: `doc/性能测试综合报告.md`

---

### 选项 2: 运行端到端性能测试

```bash
cd try1028/doc

# 运行端到端性能测试
python e2e_performance_benchmark.py

# 生成图表
python e2e_performance_analysis.py
```

**生成的图表**:
- `e2e_batch_creation.png` - 批次创建性能
- `e2e_query_performance.png` - 查询与审计性能对比
- `e2e_bandwidth.png` - 带宽/通信开销
- `e2e_revocation.png` - 批次撤销性能
- `e2e_time_range_proof.png` - 时间范围证明性能
- `e2e_summary.png` - 总体性能摘要

**详细文档**: `doc/E2E_PERFORMANCE_GUIDE.md`

---

### 选项 3: 运行所有测试

```bash
cd try1028/doc

# 运行所有测试
python performance_benchmark.py
python e2e_performance_benchmark.py

# 生成所有图表
python performance_analysis.py
python e2e_performance_analysis.py
```

---

## 📊 测试内容详解

### 1. 密码学原语性能测试

**测试内容**:
- ✅ CRS 生成时间
- ✅ 承诺生成时间 (commit_G, commit_Ghat, commit_Cy, commit_V)
- ✅ 证明生成时间 (点开放、聚合开放、等式、正交性、范围)
- ✅ 验证时间 (verify_1, verify_5, verify_7, verify_9, verify_16)
- ✅ 内存使用
- ✅ 复杂度分析

**适用场景**:
- 优化底层密码学实现
- 对比不同算法的性能
- 分析复杂度增长趋势

---

### 2. 端到端性能测试

**测试内容**:
- ✅ 批次创建 (DO → SS)
- ✅ DC 查询 (DC → SS → Verifier)
- ✅ DA 审计 (SS → Verifier, 零知识)
- ✅ 批次撤销 (DO → SS → Verifier)
- ✅ 时间范围证明 (SS → Verifier)
- ✅ 带宽/通信开销 (所有数据大小)

**适用场景**:
- 评估完整系统性能
- 估算实际应用中的开销
- 识别系统瓶颈
- 规划系统容量

---

## 📈 性能指标说明

### 时间指标

所有时间测试都重复 10 次，输出格式为：

```
平均值 ± 标准差
```

例如: `15.23 ± 0.45 ms`

- **平均值**: 10 次测试的平均时间
- **标准差**: 反映性能的稳定性（越小越稳定）

### 带宽指标

所有大小以 **KB** 为单位，测量序列化后的字节大小：

- **公开头大小**: public_header 的大小
- **秘密数据大小**: secrets 的大小
- **证明大小**: pi_audit + pi_non 的大小
- **结果大小**: x_result 的大小

---

## 🔧 自定义测试参数

### 修改向量大小

编辑测试文件的 `main()` 函数：

```python
# 默认: [4, 8, 16]
vector_sizes = [4, 8, 16, 32, 64]  # 添加更大的向量
```

### 修改重复次数

```python
# 默认: 10 次
num_runs = 20  # 增加到 20 次以获得更稳定的结果
```

### 修改曲线

```python
# 默认: MNT224
benchmark = E2EPerformanceBenchmark(curve='BN254')  # 使用 BN254 曲线
```

---

## 📊 典型性能数据

### 密码学原语 (n=8, MNT224)

| 操作 | 时间 (ms) | 复杂度 |
|------|----------|--------|
| CRS 生成 | 27.33 | O(n) |
| commit_G | 2.96 | O(n) |
| commit_Ghat | 21.28 | O(n) |
| prove_agg_open | 25.11 | O(n log n) |
| prove_eq | 38.54 | O(n log n) |
| verify_1 | 10.45 | O(n) |

### 端到端 (n=8, MNT224)

| 操作 | 时间 (ms) | 带宽 (KB) |
|------|----------|----------|
| 批次创建 | 31.57 | Header: 4.56, Secrets: 6.78 |
| DC 查询 | 39.12 | Proof: 2.34 |
| DA 审计 | 42.34 | Proof: 2.45 |
| 批次撤销 | 48.23 | NewKey: 0.12 |
| 时间范围证明 | 67.89 | Proof: 11.23 |

---

## 🎨 图表说明

### 密码学原语图表

1. **CRS 生成性能** - 显示 CRS 生成时间随 n 的增长
2. **承诺生成对比** - 对比 4 种承诺的性能
3. **证明生成对比** - 对比 5 种证明的性能
4. **验证性能对比** - 对比 5 种验证的性能
5. **内存使用** - 显示各操作的内存占用
6. **复杂度分析** - 显示时间复杂度的增长趋势
7. **总体性能总结** - 所有操作的性能对比

### 端到端图表

1. **批次创建性能** - DO 和 SS 的各阶段时间
2. **查询性能对比** - DC 查询 vs DA 审计
3. **带宽/通信开销** - 数据大小和证明大小
4. **批次撤销性能** - 撤销的各阶段时间
5. **时间范围证明性能** - 生成和验证时间
6. **总体性能摘要** - 所有操作的性能对比

---

## 📝 结果文件

### JSON 文件

- `benchmark_results.json` - 密码学原语测试结果
- `e2e_benchmark_results.json` - 端到端测试结果

**结构**:
```json
{
  "performance": {
    "operation_name": {
      "metric_name": {
        "4": 0.015,
        "8": 0.028,
        "16": 0.054
      }
    }
  },
  "bandwidth": {
    "operation_name": {
      "size_metric": {
        "4": 2048,
        "8": 4096,
        "16": 8192
      }
    }
  }
}
```

### PNG 图表

所有图表都是 300 DPI 的高分辨率 PNG 文件，适合用于：
- 论文和报告
- 演示文稿
- 技术文档

---

## 🔍 故障排除

### 问题 1: ModuleNotFoundError

**错误**: `ModuleNotFoundError: No module named 'vc_smallness'`

**解决方案**: 确保从 `try1028/doc` 目录运行测试：
```bash
cd try1028/doc
python e2e_performance_benchmark.py
```

### 问题 2: 测试运行时间过长

**原因**: 向量大小太大或重复次数太多

**解决方案**: 减少向量大小或重复次数：
```python
vector_sizes = [4, 8]  # 只测试小向量
num_runs = 5  # 减少重复次数
```

### 问题 3: 内存不足

**原因**: 向量大小太大

**解决方案**: 使用更小的向量大小：
```python
vector_sizes = [4, 8, 16]  # 避免使用 32, 64
```

---

## 📚 相关文档

- **VDS 快速开始**: `VDS_QUICKSTART.md`
- **VDS 完整文档**: `VDS_SCHEME_README.md`
- **密码学原语性能报告**: `doc/性能测试综合报告.md`
- **端到端性能指南**: `doc/E2E_PERFORMANCE_GUIDE.md`
- **实现说明**: `doc/IMPLEMENTATION_NOTES.md`
- **安全说明**: `doc/SECURITY_NOTES.md`

---

## ✅ 总结

本项目提供了完整的性能测试工具，涵盖：

✅ **密码学原语级别** - 底层操作的详细性能分析  
✅ **端到端级别** - 完整工作流的性能和带宽测试  
✅ **可视化图表** - 13 个高质量性能分析图表  
✅ **统计可靠性** - 每个测试重复 10 次，计算平均值和标准差  
✅ **灵活配置** - 可自定义向量大小、重复次数、曲线类型  

使用这些工具，你可以：
- 🎯 识别性能瓶颈
- 📊 评估系统可扩展性
- 💡 优化系统设计
- 📈 生成论文级别的性能图表

**开始测试**: `cd try1028/doc && python e2e_performance_benchmark.py`

