# 批次更新功能快速上手

## 一分钟了解

VDS 系统现在支持**批次更新**功能！一行代码即可完成"撤销旧批次 + 创建新批次"的操作。

## 快速示例

```python
from vc_smallness import setup, keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier

# 1. 系统设置
params = setup('MNT224')
group = params['group']
crs = keygen_crs(8, group)

do = DataOwner(crs, group)
ss = StorageServer(crs, do.get_initial_server_keys())
verifier = Verifier(crs, do.get_global_pk(), group)

# 2. 创建初始批次
m_old = [group.init(ZR, 10 + i) for i in range(8)]
t_old = [group.init(ZR, i + 1) for i in range(8)]
batch_id_old, header_old, secrets_old = do.create_batch(m_old, t_old)
ss.store_batch(batch_id_old, header_old, secrets_old)

# 3. 更新批次（一行代码！）
m_new = [group.init(ZR, 20 + i) for i in range(8)]
t_new = [group.init(ZR, 11 + i) for i in range(8)]

g_s_q, new_pk, sigma, batch_id_new, header_new, secrets_new = \
    do.update_batch(header_old, m_new, t_new)

# 4. 更新 SS 和 Verifier
ss.update_batch(batch_id_old, g_s_q, sigma, batch_id_new, header_new, secrets_new)
verifier.update_global_pk(new_pk)

# 5. 验证新批次
t_challenge = [group.init(ZR, 1) for _ in range(8)]
x, pi_audit, pi_non = ss.generate_dc_data_proof(batch_id_new, t_challenge, new_pk["f_current"])
is_valid = verifier.verify_dc_query(header_new, t_challenge, x, pi_audit, pi_non)
print(f"验证结果: {is_valid}")  # True
```

## 何时使用？

| 场景 | 使用方法 |
|------|---------|
| 追加新数据（时间序列） | `create_batch()` |
| 修正错误数据 | `update_batch()` ✅ |
| 刷新过期数据 | `update_batch()` ✅ |
| 删除数据 | `revoke_batch()` |

## 运行演示

```bash
# 批次更新演示
python demo_update_batch.py

# 追加 vs 更新对比
python demo_append_vs_update.py

# 运行测试
python -m pytest tests/test_update_batch.py -v
```

## 核心特性

✅ **原子操作**: 自动处理撤销 + 创建  
✅ **即时生效**: 旧批次立即失效  
✅ **安全可靠**: 防止回滚攻击  
✅ **节省空间**: 自动删除旧批次  
✅ **向后兼容**: 不影响现有功能  

## 详细文档

- 📖 [完整使用指南](doc/UPDATE_BATCH_GUIDE.md)
- 📊 [功能实现总结](UPDATE_BATCH_FEATURE_SUMMARY.md)
- 🎯 [最终总结](FINAL_SUMMARY.md)

## 测试结果

```
31 个测试全部通过 ✅
- 17 个原有测试
- 5 个多维数据测试
- 3 个批次更新测试
- 6 个 VDS 方案测试
```

## 问题反馈

如有问题，请查看：
1. `doc/UPDATE_BATCH_GUIDE.md` - 详细使用指南
2. `demo_update_batch.py` - 完整演示代码
3. `tests/test_update_batch.py` - 测试用例

