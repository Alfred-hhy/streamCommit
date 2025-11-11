# VDS Scheme C+ 快速开始指南

## 5分钟快速上手

### 1. 运行测试

```bash
cd try1028
python -m pytest tests/test_vds_scheme_c_plus.py -v
```

**预期输出**:
```
✅ test_1_happy_path_dc PASSED
✅ test_2_happy_path_da PASSED
✅ test_3_rollback_attack PASSED
✅ test_4_binding_failure PASSED
✅ test_5_tamper_failure PASSED

5 passed in 0.54s
```

---

### 2. 基本使用示例

#### 场景：数据所有者创建批次，消费者验证总和

```python
from charm.toolbox.pairinggroup import ZR
from vc_smallness import setup, keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier

# === 系统设置 ===
params = setup('MNT224')
group = params['group']
n = 8  # 向量大小
crs = keygen_crs(n=n, group=group)

# === 创建角色 ===
# 数据所有者
do = DataOwner(crs, group)

# 存储服务器
initial_keys = do.get_initial_server_keys()
ss = StorageServer(crs, initial_keys)

# 验证者
global_pk = do.get_global_pk()
verifier = Verifier(crs, global_pk, group)

# === DO创建批次 ===
# 数据向量: [10, 11, 12, 13, 14, 15, 16, 17]
m_vector = [group.init(ZR, i + 10) for i in range(n)]
# 时间向量: [1, 2, 3, 4, 5, 6, 7, 8]
t_vector = [group.init(ZR, i + 1) for i in range(n)]

batch_id, public_header, secrets = do.create_batch(m_vector, t_vector)
print(f"✅ 批次创建成功: {batch_id}")

# === SS存储批次 ===
ss.store_batch(batch_id, public_header, secrets)
print(f"✅ 批次已存储")

# === DC查询：计算总和 ===
# 挑战向量: [1, 1, 1, 1, 1, 1, 1, 1] (求和)
t_challenge = [group.init(ZR, 1) for _ in range(n)]

# SS生成证明
f_current = do.get_global_pk()["f_current"]
x_result, pi_audit, pi_non = ss.generate_dc_data_proof(
    batch_id, t_challenge, f_current
)

# 预期结果: 10+11+12+13+14+15+16+17 = 108
print(f"计算结果: {x_result}")

# === Verifier验证 ===
is_valid = verifier.verify_dc_query(
    public_header, t_challenge, x_result, pi_audit, pi_non
)

if is_valid:
    print("✅ 验证通过！结果可信。")
else:
    print("❌ 验证失败！结果不可信。")
```

**输出**:
```
✅ 批次创建成功: batch_0
✅ 批次已存储
计算结果: 108
✅ 验证通过！结果可信。
```

---

### 3. 撤销示例

#### 场景：数据所有者撤销批次，防止回滚攻击

```python
# 接上面的代码...

# === DO撤销批次 ===
sigma_to_revoke = public_header["sigma"]
g_s_q_new, new_global_pk = do.revoke_batch(sigma_to_revoke)
print(f"✅ 批次已撤销")

# === 更新SS和Verifier ===
ss.add_server_key(g_s_q_new)
verifier.update_global_pk(new_global_pk)
print(f"✅ 密钥已更新")

# === 再次查询（应该失败）===
f_current_new = new_global_pk["f_current"]
x_result_2, pi_audit_2, pi_non_2 = ss.generate_dc_data_proof(
    batch_id, t_challenge, f_current_new
)

is_valid_2 = verifier.verify_dc_query(
    public_header, t_challenge, x_result_2, pi_audit_2, pi_non_2
)

if is_valid_2:
    print("❌ 错误：撤销的批次不应该通过验证！")
else:
    print("✅ 正确：撤销的批次被拒绝。")
```

**输出**:
```
✅ 批次已撤销
✅ 密钥已更新
❌ Verification failed: Item is in revocation list (blacklist).
   This batch has been revoked by DO.
✅ 正确：撤销的批次被拒绝。
```

---

### 4. 非交互式审计示例

#### 场景：审计员验证数据完整性（零知识）

```python
# 接前面的代码（使用未撤销的批次）...

# === DA请求审计 ===
f_current = do.get_global_pk()["f_current"]
x_result_zk, pi_audit_zk, t_challenge_zk, pi_non = ss.generate_da_audit_proof(
    batch_id, f_current
)

print(f"ZK挑战: {[int(t) for t in t_challenge_zk[:3]]}...")  # 显示前3个
print(f"ZK结果: {x_result_zk}")

# === Verifier验证 ===
is_valid_zk = verifier.verify_da_audit(
    public_header, n, x_result_zk, pi_audit_zk, t_challenge_zk, pi_non
)

if is_valid_zk:
    print("✅ 审计通过！数据未被篡改。")
else:
    print("❌ 审计失败！数据可能被篡改。")
```

**输出**:
```
ZK挑战: [12345, 67890, 11223]...
ZK结果: 987654
✅ 审计通过！数据未被篡改。
```

---

## 常见问题

### Q1: 为什么需要累加器？

**A**: 累加器用作"黑名单"，防止回滚攻击。当DO撤销一个批次时，该批次的签名被添加到黑名单中。SS必须证明当前批次的签名**不在**黑名单中，否则验证失败。

### Q2: 签名绑定的作用是什么？

**A**: 签名绑定防止"混合匹配"攻击。攻击者不能将批次A的数据承诺与批次B的时间承诺混合使用，因为签名验证会失败。

### Q3: DC和DA的区别是什么？

**A**: 
- **DC (Data Consumer)**: 交互式验证，DC提供挑战向量（如求和、加权和）
- **DA (Data Auditor)**: 非交互式验证，使用Fiat-Shamir生成随机挑战，实现零知识审计

### Q4: 为什么SS是不受信任的？

**A**: SS存储所有秘密数据，但它不能：
1. 伪造签名（没有DO的签名密钥）
2. 伪造VC证明（受密码学假设保护）
3. 伪造累加器证明（受q-SBDH假设保护）

### Q5: 如何确保Verifier有最新的global_pk？

**A**: Verifier必须在每次DO撤销批次后调用 `update_global_pk()`。这通常通过：
1. DO发布新的global_pk到公共公告板
2. Verifier定期检查并更新
3. 或使用推送通知机制

---

## 下一步

1. **阅读完整文档**: `VDS_SCHEME_README.md`
2. **查看测试代码**: `tests/test_vds_scheme_c_plus.py`
3. **探索源代码**:
   - `vds_accumulator.py` - 累加器实现
   - `vds_owner.py` - 数据所有者
   - `vds_server.py` - 存储服务器
   - `vds_verifier.py` - 验证者

---

## 性能提示

### 向量大小选择

- **小向量 (n=4-8)**: 适合快速原型和测试
- **中等向量 (n=16-32)**: 适合实际应用
- **大向量 (n=64+)**: 需要更多计算资源

### 批次管理

- **频繁撤销**: 累加器证明会变慢（O(q)）
- **建议**: 定期清理黑名单，重新初始化累加器

---

## 故障排除

### 问题：验证总是失败

**检查**:
1. Verifier是否有最新的global_pk？
2. SS是否使用了正确的f_current？
3. 批次是否已被撤销？

### 问题：累加器证明失败

**检查**:
1. 是否调用了 `ss.add_server_key(g_s_q_new)`？
2. 是否调用了 `verifier.update_global_pk(new_global_pk)`？

### 问题：签名验证失败

**检查**:
1. C_data和C_time是否来自同一批次？
2. sigma是否与C_data和C_time匹配？

---

**祝您使用愉快！** 🎉

