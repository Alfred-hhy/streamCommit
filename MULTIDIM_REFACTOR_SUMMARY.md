# VDS 多维数据存储重构总结

## 概述

成功将 VDS (Verifiable Data Streaming) 系统从**单维数据存储**升级为**多维数据存储（列式架构）**。

## 核心架构变更

### 1. 复用机制
- **时间承诺共享**：一个批次内的所有数据列共享同一个时间承诺 `C_time`
- **签名共享**：所有列共享同一个签名 `σ`，显著降低存储和验证开销
- **独立数据承诺**：每一列有独立的数据承诺 `C_data`

### 2. 数据结构变更

#### 旧格式（单维）
```python
m_vector: List[ZR]  # 单个数据向量
C_data: G1          # 单个数据承诺
```

#### 新格式（多维）
```python
m_matrix: List[List[ZR]]  # 数据矩阵，外层=列，内层=时间点
C_data_list: List[G1]     # 承诺列表，每列一个
```

### 3. 签名绑定
```
旧签名：σ = Sign(sk, Hash(C_data || C_time))
新签名：σ = Sign(sk, Hash(C_time || C_data[0] || C_data[1] || ...))
```

## 修改的文件

### 1. `vds_utils.py`
**修改函数**：
- `serialize_for_signing(C_data_list, C_time)` - 支持承诺列表序列化
- `hash_for_signing(C_data_list, C_time)` - 支持承诺列表哈希
- `sign_batch(sk, C_data_list, C_time)` - 签名绑定所有承诺
- `verify_batch_signature(vk, C_data_list, C_time, sigma)` - 验证承诺列表签名

**关键变更**：
- 参数从 `C_data: G1` 改为 `C_data_list: List[G1]`
- 序列化顺序：`C_time || C_data[0] || C_data[1] || ...`

### 2. `vds_owner.py`
**修改函数**：
- `create_batch(m_matrix, t_vector)` - 支持多维数据矩阵

**关键变更**：
- 输入参数从 `m_vector` 改为 `m_matrix`
- 为每一列生成独立的 `C_data` 和 `gamma_data`
- 所有列共享同一个 `C_time` 和 `sigma`
- **向后兼容**：自动检测单向量输入并转换为单列矩阵

**输出变更**：
```python
public_header = {
    "C_data_list": [C_data_0, C_data_1, ...],  # 原 C_data
    "C_time": C_time,
    "sigma": sigma
}

secrets_for_ss = {
    "m_matrix": [[col0_data], [col1_data], ...],  # 原 m
    "t": t_vector,
    "gamma_data_list": [gamma_0, gamma_1, ...],   # 原 gamma_data
    "gamma_time": gamma_time
}
```

### 3. `vds_server.py`
**修改函数**：
- `generate_dc_data_proof(..., column_index=0)` - 增加列索引参数
- `generate_da_audit_proof(..., column_index=0)` - 增加列索引参数

**关键变更**：
- 新增 `column_index` 参数指定查询哪一列
- 从 `m_matrix[column_index]` 提取目标列数据
- 从 `gamma_data_list[column_index]` 提取对应随机数
- 从 `C_data_list[column_index]` 提取对应承诺
- 签名 `σ` 对所有列共享，累加器证明逻辑不变

### 4. `vds_verifier.py`
**修改函数**：
- `_verify_precheck(public_header, pi_non)` - 验证承诺列表签名
- `verify_dc_query(..., column_index=0)` - 增加列索引参数
- `verify_da_audit(..., column_index=0)` - 增加列索引参数

**关键变更**：
- 从 `C_data_list` 提取所有承诺进行签名验证
- 使用 `C_data_list[column_index]` 进行 VC 证明验证
- 增加列索引越界检查

## 向后兼容性

### 自动转换机制
`create_batch` 函数自动检测输入格式：
```python
# 旧代码（单向量）- 仍然有效
m_vector = [10, 11, 12, ...]
batch_id, header, secrets = do.create_batch(m_vector, t_vector)

# 新代码（多列矩阵）
m_matrix = [[10, 11, 12, ...], [20, 21, 22, ...]]
batch_id, header, secrets = do.create_batch(m_matrix, t_vector)
```

### 默认参数
所有新增的 `column_index` 参数默认值为 `0`，确保旧代码无需修改即可运行。

## 测试覆盖

### 新增测试文件：`tests/test_multidim_vds.py`
1. **test_single_column** - 单列数据（向后兼容性测试）
2. **test_multi_column_dc** - 多列 DC 查询
3. **test_multi_column_da** - 多列 DA 审计
4. **test_shared_signature** - 验证签名共享机制
5. **test_column_index_out_of_range** - 列索引越界检查

### 测试结果
```
✅ 所有 28 个测试通过
   - 17 个原有测试（向后兼容）
   - 5 个新增多维测试
   - 6 个 VDS 方案测试
```

## 使用示例

### 单列数据（向后兼容）
```python
# 温度数据
temp_data = [group.init(ZR, 20 + i) for i in range(n)]
t_vector = [group.init(ZR, i + 1) for i in range(n)]

batch_id, header, secrets = do.create_batch(temp_data, t_vector)
ss.store_batch(batch_id, header, secrets)

# 查询（默认 column_index=0）
x, pi_audit, pi_non = ss.generate_dc_data_proof(batch_id, t_challenge, f_current)
is_valid = verifier.verify_dc_query(header, t_challenge, x, pi_audit, pi_non)
```

### 多列数据
```python
# 3 列数据：温度、湿度、气压
temp_data = [group.init(ZR, 20 + i) for i in range(n)]
humid_data = [group.init(ZR, 50 + i) for i in range(n)]
pressure_data = [group.init(ZR, 1000 + i) for i in range(n)]
m_matrix = [temp_data, humid_data, pressure_data]
t_vector = [group.init(ZR, i + 1) for i in range(n)]

batch_id, header, secrets = do.create_batch(m_matrix, t_vector)
ss.store_batch(batch_id, header, secrets)

# 查询第 1 列（湿度）
x, pi_audit, pi_non = ss.generate_dc_data_proof(
    batch_id, t_challenge, f_current, column_index=1
)
is_valid = verifier.verify_dc_query(
    header, t_challenge, x, pi_audit, pi_non, column_index=1
)
```

## 性能优势

### 存储开销
- **旧方案**：N 列数据需要 N 个批次，N 个签名，N 个时间承诺
- **新方案**：N 列数据只需 1 个批次，1 个签名，1 个时间承诺
- **节省**：签名和时间承诺开销降低 N 倍

### 验证开销
- 签名验证：从 N 次降低到 1 次
- 累加器验证：从 N 次降低到 1 次
- VC 验证：仍需 N 次（每列独立验证）

## 安全性保证

1. **签名绑定**：签名覆盖所有列的承诺，防止混合攻击
2. **独立证明**：每列有独立的 VC 证明，防止跨列篡改
3. **共享撤销**：整个批次共享撤销状态，简化管理
4. **向后兼容**：不影响现有安全属性

## 总结

成功实现了 VDS 系统的多维数据存储升级，在保持向后兼容性的同时，显著降低了存储和验证开销。所有测试通过，代码质量良好。

