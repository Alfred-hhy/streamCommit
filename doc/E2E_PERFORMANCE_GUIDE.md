# VDS Scheme C+ 端到端性能测试指南

## 📋 概述

本指南介绍如何运行 VDS Scheme C+ 的端到端性能测试，包括：

1. **批次创建性能** - DO 创建批次并由 SS 存储的完整流程
2. **DC 查询性能** - 数据消费者查询的完整流程（SS 生成证明 + Verifier 验证）
3. **DA 审计性能** - 审计员审计的完整流程（零知识证明）
4. **批次撤销性能** - DO 撤销批次并更新系统的完整流程
5. **时间范围证明性能** - 时间戳范围证明的完整流程
6. **带宽/通信开销** - 所有操作的数据传输量

---

## 🚀 快速开始

### 步骤 1: 运行端到端性能测试

```bash
cd try1028/doc
python e2e_performance_benchmark.py
```

**预期输出**:
```
🚀 VDS Scheme C+ 端到端性能基准测试
======================================================================

📋 测试配置:
   - 向量大小: [4, 8, 16]
   - 每个测试重复: 10 次
   - 曲线: MNT224

📊 批次创建端到端性能测试 (每个测试重复 10 次)
======================================================================
  测试 n=4... ✓ DO:15.23±0.45ms SS:2.34±0.12ms 总:17.57±0.47ms
  测试 n=8... ✓ DO:28.45±0.67ms SS:3.12±0.15ms 总:31.57±0.69ms
  测试 n=16... ✓ DO:54.23±1.23ms SS:4.56±0.23ms 总:58.79±1.26ms

📊 DC 查询端到端性能测试 (每个测试重复 10 次)
======================================================================
  测试 n=4... ✓ SS:12.34±0.34ms Ver:8.45±0.23ms 总:20.79±0.41ms
  测试 n=8... ✓ SS:23.45±0.56ms Ver:15.67±0.34ms 总:39.12±0.66ms
  测试 n=16... ✓ SS:45.67±1.12ms Ver:28.34±0.67ms 总:74.01±1.31ms

... (更多测试结果)

💾 结果已保存到: e2e_benchmark_results.json
✅ 所有测试完成！
```

**生成的文件**:
- `e2e_benchmark_results.json` - 包含所有性能数据和带宽数据的 JSON 文件

---

### 步骤 2: 生成可视化图表

```bash
python e2e_performance_analysis.py
```

**预期输出**:
```
🚀 VDS Scheme C+ 端到端性能分析
======================================================================
📂 加载测试结果: e2e_benchmark_results.json
✅ 数据加载完成

🎨 开始生成所有图表...
======================================================================
📊 生成批次创建性能图...
   ✓ 保存: e2e_batch_creation.png
📊 生成查询性能对比图...
   ✓ 保存: e2e_query_performance.png
📊 生成带宽/通信开销图...
   ✓ 保存: e2e_bandwidth.png
📊 生成撤销性能图...
   ✓ 保存: e2e_revocation.png
📊 生成时间范围证明性能图...
   ✓ 保存: e2e_time_range_proof.png
📊 生成总体性能摘要图...
   ✓ 保存: e2e_summary.png

✅ 所有图表生成完成！

生成的图表:
  1. e2e_batch_creation.png - 批次创建性能
  2. e2e_query_performance.png - 查询与审计性能对比
  3. e2e_bandwidth.png - 带宽/通信开销
  4. e2e_revocation.png - 批次撤销性能
  5. e2e_time_range_proof.png - 时间范围证明性能
  6. e2e_summary.png - 总体性能摘要
```

**生成的图表**:
- `e2e_batch_creation.png` - 批次创建的各个阶段性能
- `e2e_query_performance.png` - DC 查询 vs DA 审计性能对比
- `e2e_bandwidth.png` - 数据大小和证明大小
- `e2e_revocation.png` - 批次撤销的各个阶段性能
- `e2e_time_range_proof.png` - 时间范围证明性能
- `e2e_summary.png` - 所有操作的总体性能对比

---

## 📊 测试内容详解

### 1. 批次创建性能测试

**测试流程**:
```
DO.create_batch(m, t) → SS.store_batch(batch_id, header, secrets)
```

**测量指标**:
- DO 创建批次时间 (commit + sign)
- SS 存储批次时间
- 总时间
- 公开头大小 (public_header)
- 秘密数据大小 (secrets)

**关键发现**:
- DO 的操作非常轻量（只需 commit + sign）
- SS 的存储操作几乎是常数时间
- 公开头大小随 n 线性增长
- 秘密数据大小随 n 线性增长

---

### 2. DC 查询性能测试

**测试流程**:
```
DC 提供挑战 t → SS.generate_dc_data_proof() → Verifier.verify_dc_query()
```

**测量指标**:
- SS 生成证明时间
- Verifier 验证时间
- 总时间
- 证明大小 (pi_audit + pi_non)
- 结果大小 (x_result)

**关键发现**:
- SS 的证明生成是主要瓶颈
- Verifier 的验证时间约为证明生成时间的 50-70%
- 证明大小随 n 增长（因为包含累加器证明）

---

### 3. DA 审计性能测试

**测试流程**:
```
SS.generate_da_audit_proof() → Verifier.verify_da_audit()
```

**测量指标**:
- SS 生成审计证明时间（包含 Fiat-Shamir 挑战生成）
- Verifier 验证时间（包含挑战重新计算）
- 总时间
- 审计证明大小
- 挑战向量大小

**关键发现**:
- DA 审计比 DC 查询稍慢（因为需要生成随机挑战）
- Verifier 需要重新计算 Fiat-Shamir 挑战
- 审计证明大小与 DC 证明相似

---

### 4. 批次撤销性能测试

**测试流程**:
```
DO.revoke_batch(sigma) → SS.add_server_key(g_s_q) → 
Verifier.update_global_pk(new_pk) → 验证撤销后的批次失败
```

**测量指标**:
- DO 撤销批次时间（更新累加器）
- SS 更新密钥时间
- Verifier 更新 global_pk 时间
- 验证撤销后批次的时间
- 总时间
- 新密钥大小
- 新 global_pk 大小

**关键发现**:
- DO 的撤销操作是主要开销（需要更新累加器）
- SS 和 Verifier 的更新操作非常快
- 撤销后的验证会正确失败

---

### 5. 时间范围证明性能测试

**测试流程**:
```
SS.generate_time_range_proofs() → Verifier.verify_time_range_proof()
```

**测量指标**:
- SS 生成时间范围证明时间（为每个时间值生成范围证明）
- Verifier 验证时间（验证所有范围证明）
- 总时间
- 时间范围证明总大小

**关键发现**:
- 时间范围证明使用 O(n log n) 优化后的 `prove_range_proof`
- 每个时间值的范围证明是独立的
- 验证时间与时间值数量成正比

---

## 📈 性能分析图表说明

### 1. `e2e_batch_creation.png`

**内容**: 批次创建的各个阶段性能柱状图

**X 轴**: 向量大小 (n=4, 8, 16)  
**Y 轴**: 时间 (ms)  
**柱状图**: DO 创建批次、SS 存储批次、总时间

**用途**: 了解批次创建的性能瓶颈

---

### 2. `e2e_query_performance.png`

**内容**: DC 查询 vs DA 审计性能对比

**X 轴**: 向量大小 (n=4, 8, 16)  
**Y 轴**: 时间 (ms)  
**柱状图**: DC 查询总时间、DA 审计总时间

**用途**: 对比交互式查询和非交互式审计的性能差异

---

### 3. `e2e_bandwidth.png`

**内容**: 带宽/通信开销（两个子图）

**左图**: 批次创建数据大小
- X 轴: 向量大小 (n=4, 8, 16)
- Y 轴: 大小 (KB)
- 柱状图: 公开头、秘密数据

**右图**: 证明大小对比
- X 轴: 向量大小 (n=4, 8, 16)
- Y 轴: 大小 (KB)
- 柱状图: DC 证明、DA 证明

**用途**: 了解系统的通信开销和存储需求

---

### 4. `e2e_revocation.png`

**内容**: 批次撤销的各个阶段性能

**X 轴**: 向量大小 (n=4, 8, 16)  
**Y 轴**: 时间 (ms)  
**柱状图**: DO 撤销、SS 更新密钥、Verifier 更新PK、验证撤销

**用途**: 了解撤销操作的性能开销

---

### 5. `e2e_time_range_proof.png`

**内容**: 时间范围证明性能

**X 轴**: 向量大小 (n=4, 8, 16)  
**Y 轴**: 时间 (ms)  
**柱状图**: SS 生成证明、Verifier 验证、总时间

**用途**: 了解时间范围证明的性能特性

---

### 6. `e2e_summary.png`

**内容**: 所有操作的总体性能对比

**X 轴**: 向量大小 (n=4, 8, 16)  
**Y 轴**: 时间 (ms)  
**柱状图**: 批次创建、DC 查询、DA 审计、批次撤销、时间范围证明

**用途**: 一目了然地对比所有操作的性能

---

## 🔧 自定义测试

### 修改测试参数

编辑 `e2e_performance_benchmark.py` 的 `main()` 函数：

```python
def main():
    # 修改向量大小
    vector_sizes = [4, 8, 16, 32]  # 添加 n=32
    
    # 修改重复次数
    num_runs = 20  # 增加到 20 次以获得更稳定的结果
    
    # 修改曲线
    benchmark = E2EPerformanceBenchmark(curve='BN254')  # 使用 BN254 曲线
```

### 只运行特定测试

注释掉不需要的测试：

```python
# 只运行批次创建和 DC 查询测试
benchmark.benchmark_batch_creation(vector_sizes, num_runs)
benchmark.benchmark_dc_query(vector_sizes, num_runs)
# benchmark.benchmark_da_audit(vector_sizes, num_runs)  # 注释掉
# benchmark.benchmark_revocation(vector_sizes, num_runs)  # 注释掉
# benchmark.benchmark_time_range_proof(vector_sizes, num_runs)  # 注释掉
```

---

## 📝 结果解读

### 性能摘要示例

```
📊 端到端性能测试摘要
======================================================================

1️⃣  批次创建:
   n= 4:  17.57± 0.47ms | Header:  2.34KB Secrets:  3.45KB
   n= 8:  31.57± 0.69ms | Header:  4.56KB Secrets:  6.78KB
   n=16:  58.79± 1.26ms | Header:  8.90KB Secrets: 13.45KB

2️⃣  DC 查询:
   n= 4:  20.79± 0.41ms | Proof:  1.23KB
   n= 8:  39.12± 0.66ms | Proof:  2.34KB
   n=16:  74.01± 1.31ms | Proof:  4.56KB

3️⃣  DA 审计:
   n= 4:  23.45± 0.52ms | Proof:  1.34KB
   n= 8:  42.34± 0.78ms | Proof:  2.45KB
   n=16:  79.23± 1.45ms | Proof:  4.67KB

4️⃣  批次撤销:
   n= 4:  45.67± 1.12ms | NewKey:  0.12KB
   n= 8:  48.23± 1.23ms | NewKey:  0.12KB
   n=16:  51.34± 1.34ms | NewKey:  0.12KB

5️⃣  时间范围证明:
   n= 4:  34.56± 0.89ms | Proof:  5.67KB
   n= 8:  67.89± 1.34ms | Proof: 11.23KB
   n=16: 132.45± 2.67ms | Proof: 22.34KB
```

### 关键观察

1. **批次创建**: 时间随 n 线性增长，DO 的操作非常轻量
2. **DC 查询**: 时间随 n 增长，SS 的证明生成是瓶颈
3. **DA 审计**: 比 DC 查询稍慢，但提供零知识保证
4. **批次撤销**: 时间几乎不随 n 变化（主要是累加器操作）
5. **时间范围证明**: 时间随 n 线性增长（每个时间值一个证明）

---

## ✅ 总结

本端到端性能测试提供了：

✅ **完整的工作流测试** - 从 DO 到 SS 到 Verifier 的完整流程  
✅ **带宽/通信开销测量** - 所有数据传输的大小  
✅ **时间范围证明测试** - 验证时间戳范围的完整流程  
✅ **可视化图表** - 6 个性能分析图表  
✅ **统计可靠性** - 每个测试重复 10 次，计算平均值和标准差  

这些测试结果可以帮助你：
- 了解系统的性能瓶颈
- 评估不同向量大小的性能影响
- 估算实际应用中的通信开销
- 优化系统设计和参数选择

