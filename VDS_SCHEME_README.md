# VDS Scheme C+ Implementation

## 概述

本项目实现了一个支持**更新**和**撤销**的**可验证数据流 (Verifiable Data Streaming, VDS)** 方案。该方案基于：

1. **Libert et al. (2024)** 的向量承诺方案 (`vc_smallness` 库)
2. **Krupp et al. (2016)** 的双线性映射累加器（用于撤销）

---

## 架构

### 四个角色

1. **DO (Data Owner)** - 数据所有者
   - 计算能力受限
   - 创建批次（承诺 + 签名）
   - 管理撤销（更新累加器）
   - 发布动态公钥

2. **SS (Storage Server)** - 存储服务器
   - 不受信任，但计算能力强
   - 存储所有秘密数据
   - 生成所有证明（VC证明 + 累加器证明）

3. **DC (Data Consumer)** - 数据消费者
   - 需要验证特定内积（如总和）
   - 交互式验证（DC提供挑战）

4. **DA (Data Auditor)** - 数据审计员
   - 需要零知识防篡改验证
   - 非交互式验证（Fiat-Shamir）

---

## 核心组件

### 1. 累加器模块 (`vds_accumulator.py`)

基于 Krupp et al. (2016) 的双线性映射累加器，用作"黑名单"防止回滚攻击。

**关键功能**:
- `setup()`: 生成累加器密钥和初始状态
- `add_to_blacklist()`: 将项目添加到黑名单（DO调用）
- `expand_server_keys()`: 扩展服务器密钥（DO调用）
- `prove_non_membership()`: 生成非成员资格证明（SS调用）
- `verify_non_membership()`: 验证非成员资格证明（Verifier调用）

**安全性**:
- 基于 q-Strong Bilinear Diffie-Hellman (q-SBDH) 假设
- 非成员资格证明不可伪造

### 2. 工具模块 (`vds_utils.py`)

提供签名和序列化功能。

**关键功能**:
- `generate_signing_keys()`: 生成ECDSA签名密钥
- `sign_batch()`: 签名批次（绑定 C_data 和 C_time）
- `verify_batch_signature()`: 验证批次签名
- `serialize_*()`: 序列化群元素和签名

**安全性**:
- 使用ECDSA（NIST P-256）进行签名绑定
- 防止混合匹配攻击

### 3. 数据所有者 (`vds_owner.py`)

轻量级实体，创建批次并管理撤销。

**关键功能**:
- `create_batch()`: 创建并签名新批次
  - 生成承诺：C_data (G1), C_time (G2)
  - 签名绑定：σ = Sign(sk, Hash(C_data || C_time))
  - 返回公开头部和秘密数据
- `revoke_batch()`: 撤销批次
  - 更新累加器：f_new = f^{e_i + s}
  - 扩展服务器密钥：g^{s^q}
  - 发布新的 global_pk

**动态公钥**:
```python
global_pk = {
    "vk_sig": vk_DO,        # 静态：签名验证密钥
    "acc_pk": (g, ĝ, ĝ^s),  # 静态：累加器公钥
    "f_current": f          # 动态：当前黑名单状态
}
```

### 4. 存储服务器 (`vds_server.py`)

不受信任但强大的实体，生成所有证明。

**关键功能**:
- `store_batch()`: 存储批次数据
- `generate_dc_data_proof()`: 为DC生成交互式证明
  - 计算标量结果：x = ∑ m_i * t_i
  - 生成VC证明：π_audit
  - 生成累加器证明：π_non
- `generate_da_audit_proof()`: 为DA生成NIZK证明
  - 使用Fiat-Shamir生成挑战
  - 生成VC证明和累加器证明

### 5. 验证者 (`vds_verifier.py`)

验证DC和DA的证明。

**关键功能**:
- `update_global_pk()`: 更新全局公钥（必须在每次撤销后调用）
- `verify_dc_query()`: 验证DC查询
  1. 验证签名绑定
  2. 验证非成员资格（未撤销）
  3. 验证VC证明
- `verify_da_audit()`: 验证DA审计
  1. 验证签名绑定
  2. 验证非成员资格
  3. 重新计算Fiat-Shamir挑战
  4. 验证VC证明

---

## 安全属性

### 1. 签名绑定
- **防止**: 混合匹配攻击
- **机制**: ECDSA签名绑定 C_data 和 C_time
- **测试**: `test_4_binding_failure` ✅

### 2. 累加器撤销
- **防止**: 回滚攻击
- **机制**: 双线性映射累加器 + 非成员资格证明
- **测试**: `test_3_rollback_attack` ✅

### 3. VC证明
- **防止**: 数据篡改
- **机制**: Libert 2024 向量承诺证明
- **测试**: `test_5_tamper_failure` ✅

---

## 使用示例

### 完整工作流

```python
from vc_smallness import setup, keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier

# 1. 系统设置
params = setup('MNT224')
group = params['group']
crs = keygen_crs(n=8, group=group)

# 2. 创建角色
do = DataOwner(crs, group)
ss = StorageServer(crs, do.get_initial_server_keys())
verifier = Verifier(crs, do.get_global_pk(), group)

# 3. DO创建批次
m = [group.init(ZR, i+10) for i in range(8)]
t = [group.init(ZR, i+1) for i in range(8)]
batch_id, header, secrets = do.create_batch(m, t)

# 4. SS存储批次
ss.store_batch(batch_id, header, secrets)

# 5. DC查询（交互式）
t_challenge = [group.init(ZR, 1) for _ in range(8)]  # 求和
f_current = do.get_global_pk()["f_current"]
x_result, pi_audit, pi_non = ss.generate_dc_data_proof(
    batch_id, t_challenge, f_current
)

# 6. Verifier验证
is_valid = verifier.verify_dc_query(
    header, t_challenge, x_result, pi_audit, pi_non
)
print(f"DC验证结果: {is_valid}")  # True

# 7. DO撤销批次
sigma_to_revoke = header["sigma"]
g_s_q_new, new_global_pk = do.revoke_batch(sigma_to_revoke)

# 8. 更新SS和Verifier
ss.add_server_key(g_s_q_new)
verifier.update_global_pk(new_global_pk)

# 9. 再次查询（应该失败）
x_result_2, pi_audit_2, pi_non_2 = ss.generate_dc_data_proof(
    batch_id, t_challenge, new_global_pk["f_current"]
)
is_valid_2 = verifier.verify_dc_query(
    header, t_challenge, x_result_2, pi_audit_2, pi_non_2
)
print(f"撤销后验证结果: {is_valid_2}")  # False
```

---

## 测试

运行所有测试：

```bash
cd try1028
python -m pytest tests/test_vds_scheme_c_plus.py -v
```

### 测试覆盖

1. ✅ **test_1_happy_path_dc**: DC交互式查询（正常情况）
2. ✅ **test_2_happy_path_da**: DA非交互式审计（正常情况）
3. ✅ **test_3_rollback_attack**: 回滚攻击防护
4. ✅ **test_4_binding_failure**: 混合匹配攻击防护
5. ✅ **test_5_tamper_failure**: 数据篡改检测

---

## 性能特点

### DO (轻量级)
- **承诺生成**: O(n) - 线性
- **签名**: O(1) - 常数
- **撤销**: O(1) - 常数（更新累加器）

### SS (重量级)
- **VC证明生成**: O(n) - 线性（每个位置）
- **累加器证明**: O(q) - 线性（q为撤销数量）

### Verifier
- **签名验证**: O(1) - 常数
- **累加器验证**: O(1) - 常数（配对运算）
- **VC验证**: O(n) - 线性（配对运算）

---

## 限制和未来工作

### 当前限制

1. **累加器证明**: 
   - 当前实现对于非空累加器使用占位符
   - 需要实现完整的Krupp et al. (2016) Section 2.5算法
   - 涉及多项式除法和扩展欧几里得算法

2. **时间证明**: 
   - 未实现（Test 6）
   - 需要实现范围证明（基于Libert 2024 Section 4.1）

### 未来改进

1. **完整累加器实现**:
   - 实现多项式算术
   - 实现扩展欧几里得算法
   - 支持任意数量的撤销

2. **范围证明**:
   - 实现 `prove_range_proof()`
   - 实现 `verify_range_proof()`
   - 支持时间戳验证

3. **批量范围证明**:
   - 实现批量时间证明（Libert 2024 Section 4.1）
   - 提高效率

4. **性能优化**:
   - 实现O(n)的 `prove_eq`（当前是O(n²)）
   - 使用多重指数运算优化

---

## 参考文献

1. **Libert et al. (2024)**: "Vector Commitments with Proofs of Smallness"
   - 向量承诺方案
   - 范围证明
   - 聚合证明

2. **Krupp et al. (2016)**: "Nearly Optimal Verifiable Data Streaming"
   - 双线性映射累加器
   - 非成员资格证明
   - 撤销机制

---

## 文件结构

```
try1028/
├── vds_accumulator.py      # 累加器模块
├── vds_utils.py            # 工具函数
├── vds_owner.py            # 数据所有者
├── vds_server.py           # 存储服务器
├── vds_verifier.py         # 验证者
├── tests/
│   └── test_vds_scheme_c_plus.py  # 端到端测试
├── vc_smallness/           # 向量承诺库
│   ├── commit.py
│   ├── proofs.py
│   ├── verify.py
│   └── ...
└── VDS_SCHEME_README.md    # 本文档
```

---

## 许可证

本实现基于学术研究，仅供教育和研究目的使用。

---

**实现日期**: 2025-11-03  
**状态**: ✅ 核心功能完成，5/6测试通过

