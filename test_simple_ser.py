#!/usr/bin/env python
"""简化的序列化测试"""

from charm.toolbox.pairinggroup import PairingGroup, ZR
from vc_smallness.crs import keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier
from distributed.serialization import *

# 创建一个完整的系统
group = PairingGroup('MNT224')
crs = keygen_crs(16, group)
do = DataOwner(crs, group)
ss = StorageServer(crs, do.server_acc_keys)
verifier = Verifier(crs, do.global_pk, group)

# 创建批次
data_vectors = [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]]
time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
m_matrix = [[group.init(ZR, val) for val in col] for col in data_vectors]
t_vector = [group.init(ZR, val) for val in time_vector]

batch_id, public_header_orig, secrets_orig = do.create_batch(m_matrix, t_vector)

# 测试1: 不序列化，直接使用
print("=== 测试1: 直接使用原始数据 ===")
ss.storage.clear()  # 清空存储
ss.store_batch(batch_id, public_header_orig, secrets_orig)
t_challenge = [group.init(ZR, 1) for _ in range(16)]
x_result, pi_audit, pi_non = ss.generate_dc_data_proof(batch_id, t_challenge, do.global_pk['f_current'], 0)
is_valid_1 = verifier.verify_dc_query(public_header_orig, t_challenge, x_result, pi_audit, pi_non, 0)
print(f"验证结果: {is_valid_1}\n")

# 测试2: 序列化+反序列化后使用
print("=== 测试2: 序列化+反序列化后使用 ===")
# 序列化
header_ser = serialize_public_header(public_header_orig, group)
secrets_ser = serialize_secrets_for_ss(secrets_orig, group)

# 反序列化
header_deser = deserialize_public_header(header_ser, group)
secrets_deser = deserialize_secrets_for_ss(secrets_ser, group)

# 使用反序列化的数据
ss.storage.clear()
ss.store_batch(batch_id, header_deser, secrets_deser)
x_result2, pi_audit2, pi_non2 = ss.generate_dc_data_proof(batch_id, t_challenge, do.global_pk['f_current'], 0)
is_valid_2 = verifier.verify_dc_query(header_deser, t_challenge, x_result2, pi_audit2, pi_non2, 0)
print(f"验证结果: {is_valid_2}\n")

# 对比数据
print("=== 数据对比 ===")
print(f"header相等: {public_header_orig['C_data_list'][0] == header_deser['C_data_list'][0]}")
print(f"结果相等: {x_result == x_result2}")
print(f"证明相等: {pi_audit == pi_audit2}")
