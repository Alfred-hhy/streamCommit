# 批次更新功能指南

## 概述

VDS 系统现在支持**批次更新 (Batch Update)** 功能。这是一个便捷的原子操作，封装了"撤销旧批次 + 创建新批次"的完整流程。

## 为什么需要批次更新？

### 密码学约束

基于**向量承诺 (Vector Commitment)** 的密码学特性，一旦承诺生成并签名，就**无法直接修改**：

```python
C_data = commit_G(m, gamma, crs)  # 承诺绑定了数据 m
sigma = sign(sk, Hash(C_data || C_time))  # 签名绑定了承诺
```

如果修改数据 `m'`，承诺会变成 `C_data'`，原来的签名 `sigma` 就不再匹配。

### 解决方案

**更新 = 撤销旧批次 + 创建新批次**

这是密码学设计的必然结果，也是最安全的方式。

## 使用场景

| 场景 | 是否需要更新 | 操作 |
|------|------------|------|
| **追加新数据** | ❌ 不需要 | 直接调用 `create_batch` |
| **修正错误数据** | ✅ 需要 | 调用 `update_batch` |
| **刷新过期数据** | ✅ 需要 | 调用 `update_batch` |
| **删除数据** | ✅ 需要 | 调用 `revoke_batch` |

## API 文档

### DataOwner.update_batch()

```python
def update_batch(self, old_batch_header: Dict, new_m_matrix: List[List[ZR]], 
                 new_t_vector: List[ZR]) -> Tuple[G1, Dict, bytes, str, Dict, Dict]:
    """
    更新批次：撤销旧批次并创建新批次（原子操作）。
    
    Parameters
    ----------
    old_batch_header : dict
        旧批次的公开头部（包含 sigma）
    new_m_matrix : List[List[ZR]] 或 List[ZR]
        新的数据矩阵（多列）或数据向量（单列）
    new_t_vector : List[ZR]
        新的时间向量
    
    Returns
    -------
    g_s_q_new : G1
        新的服务器密钥（用于累加器）
    new_global_pk : dict
        更新后的全局公钥
    sigma_bytes : bytes
        被撤销的签名（序列化）
    new_batch_id : str
        新批次的 ID
    new_public_header : dict
        新批次的公开头部
    new_secrets_for_ss : dict
        新批次的秘密数据
    """
```

### StorageServer.update_batch()

```python
def update_batch(self, old_batch_id: str, g_s_q_new: G1, sigma_bytes: bytes,
                 new_batch_id: str, new_public_header: Dict, new_secrets_for_ss: Dict):
    """
    更新批次：删除旧批次，存储新批次，更新累加器状态（原子操作）。
    
    Parameters
    ----------
    old_batch_id : str
        旧批次的 ID（将被删除）
    g_s_q_new : G1
        新的服务器密钥（来自 DO）
    sigma_bytes : bytes
        被撤销的签名（序列化）
    new_batch_id : str
        新批次的 ID
    new_public_header : dict
        新批次的公开头部
    new_secrets_for_ss : dict
        新批次的秘密数据
    """
```

## 使用示例

### 基本用法

```python
from vc_smallness import setup, keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier

# 1. 系统设置
params = setup('MNT224')
group = params['group']
n = 8
crs = keygen_crs(n, group)

do = DataOwner(crs, group)
ss = StorageServer(crs, do.get_initial_server_keys())
verifier = Verifier(crs, do.get_global_pk(), group)

# 2. 创建初始批次
m_old = [group.init(ZR, 10 + i) for i in range(n)]
t_old = [group.init(ZR, i + 1) for i in range(n)]
batch_id_old, header_old, secrets_old = do.create_batch(m_old, t_old)
ss.store_batch(batch_id_old, header_old, secrets_old)

# 3. 更新批次
m_new = [group.init(ZR, 20 + i) for i in range(n)]  # 新数据
t_new = [group.init(ZR, 11 + i) for i in range(n)]  # 新时间戳

# DO 执行更新
g_s_q_new, new_global_pk, sigma_bytes, batch_id_new, header_new, secrets_new = \
    do.update_batch(header_old, m_new, t_new)

# SS 执行更新
ss.update_batch(batch_id_old, g_s_q_new, sigma_bytes, 
               batch_id_new, header_new, secrets_new)

# Verifier 更新全局公钥
verifier.update_global_pk(new_global_pk)

# 4. 验证新批次
t_challenge = [group.init(ZR, 1) for _ in range(n)]
x, pi_audit, pi_non = ss.generate_dc_data_proof(
    batch_id_new, t_challenge, new_global_pk["f_current"]
)
is_valid = verifier.verify_dc_query(header_new, t_challenge, x, pi_audit, pi_non)
print(f"验证结果: {is_valid}")  # True
```

### 多维批次更新

```python
# 创建多维批次（3 列：温度、湿度、气压）
temp_old = [group.init(ZR, 20 + i) for i in range(n)]
humid_old = [group.init(ZR, 50 + i) for i in range(n)]
pressure_old = [group.init(ZR, 1000 + i) for i in range(n)]
m_matrix_old = [temp_old, humid_old, pressure_old]
t_old = [group.init(ZR, i + 1) for i in range(n)]

batch_id_old, header_old, secrets_old = do.create_batch(m_matrix_old, t_old)
ss.store_batch(batch_id_old, header_old, secrets_old)

# 更新所有列
temp_new = [group.init(ZR, 25 + i) for i in range(n)]
humid_new = [group.init(ZR, 60 + i) for i in range(n)]
pressure_new = [group.init(ZR, 1010 + i) for i in range(n)]
m_matrix_new = [temp_new, humid_new, pressure_new]
t_new = [group.init(ZR, 11 + i) for i in range(n)]

g_s_q_new, new_global_pk, sigma_bytes, batch_id_new, header_new, secrets_new = \
    do.update_batch(header_old, m_matrix_new, t_new)

ss.update_batch(batch_id_old, g_s_q_new, sigma_bytes,
               batch_id_new, header_new, secrets_new)
verifier.update_global_pk(new_global_pk)
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                    DO.update_batch()                        │
├─────────────────────────────────────────────────────────────┤
│  1. 撤销旧批次 (revoke_batch)                               │
│     - 将旧签名加入黑名单                                     │
│     - 更新累加器 f_new = f^{e_i + s}                        │
│     - 生成新的服务器密钥 g^{s^q}                            │
│  2. 创建新批次 (create_batch)                               │
│     - 生成新的承诺 C_data', C_time'                         │
│     - 生成新的签名 σ'                                       │
│  3. 返回所有必要信息                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   SS.update_batch()                         │
├─────────────────────────────────────────────────────────────┤
│  1. 添加新的服务器密钥                                       │
│  2. 将旧签名加入黑名单                                       │
│  3. 删除旧批次数据                                          │
│  4. 存储新批次数据                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Verifier.update_global_pk()                    │
├─────────────────────────────────────────────────────────────┤
│  更新全局公钥（包含新的累加器状态 f_current）                │
└─────────────────────────────────────────────────────────────┘
```

## 安全性保证

1. **原子性**: 更新操作要么全部成功，要么全部失败
2. **即时撤销**: 旧批次立即失效，无法再通过验证
3. **独立签名**: 新批次使用新的签名，独立于旧批次
4. **防回滚**: 累加器确保旧批次不能被恢复
5. **可审计**: 所有更新操作都有记录（黑名单）

## 性能考虑

### 时间复杂度
- **DO**: O(n) - 生成承诺和签名
- **SS**: O(1) - 删除和存储操作
- **Verifier**: O(1) - 更新全局公钥

### 空间复杂度
- **旧批次删除**: 节省存储空间
- **黑名单增长**: 每次更新增加一个签名（约 64 字节）
- **累加器密钥**: 每次更新增加一个 G1 元素（约 56 字节）

## 注意事项

1. **不可逆**: 更新操作不可逆，旧批次数据会被删除
2. **同步**: 必须确保 SS 和 Verifier 都更新到最新状态
3. **并发**: 不支持并发更新同一批次
4. **历史记录**: 如需保留历史，请在删除前备份

## 运行演示

```bash
# 运行演示脚本
python demo_update_batch.py

# 运行测试
python -m pytest tests/test_update_batch.py -v
```

## 总结

批次更新功能提供了一个便捷、安全、高效的方式来修改已存在的批次数据。它完美地结合了密码学安全性和实用性，适用于各种需要数据更新的场景。

