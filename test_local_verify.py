#!/usr/bin/env python
"""本地验证测试（不通过HTTP）"""

from charm.toolbox.pairinggroup import PairingGroup, ZR
from vc_smallness.crs import keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier

# 初始化
print("=== 初始化 ===")
group = PairingGroup('MNT224')
crs = keygen_crs(16, group)
do = DataOwner(crs, group)
ss = StorageServer(crs, do.server_acc_keys)
verifier = Verifier(crs, do.global_pk, group)
print("初始化完成")

# 创建批次
print("\n=== 创建批次 ===")
data_vectors = [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]]
time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

# 转换为ZR
m_matrix = [[group.init(ZR, val) for val in col] for col in data_vectors]
t_vector = [group.init(ZR, val) for val in time_vector]

batch_id, public_header, secrets_for_ss = do.create_batch(m_matrix, t_vector)
print(f"批次ID: {batch_id}")

# 存储批次
ss.store_batch(batch_id, public_header, secrets_for_ss)
print("批次已存储")

# 生成DC证明
print("\n=== 生成DC证明 ===")
t_challenge = [group.init(ZR, 1) for _ in range(16)]
x_result, pi_audit, pi_non = ss.generate_dc_data_proof(
    batch_id, t_challenge, do.global_pk['f_current'], column_index=0
)
print(f"结果: {x_result}")

# 验证
print("\n=== 验证DC证明 ===")
is_valid = verifier.verify_dc_query(
    public_header, t_challenge, x_result, pi_audit, pi_non, column_index=0
)
print(f"验证结果: {is_valid}")

if is_valid:
    print("✓ 本地验证成功！")
else:
    print("✗ 本地验证失败！")
