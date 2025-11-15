#!/usr/bin/env python
"""对比HTTP和本地的数据是否完全一致"""

from charm.toolbox.pairinggroup import PairingGroup, ZR
from vc_smallness.crs import keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier
from distributed.serialization import *

# 方案A: 完全本地
print("=== 方案A: 完全本地 ===")
group = PairingGroup('MNT224')
crs = keygen_crs(16, group)
do = DataOwner(crs, group)
ss = StorageServer(crs, do.server_acc_keys)
verifier = Verifier(crs, do.global_pk, group)

data_vectors = [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]]
time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
m_matrix = [[group.init(ZR, val) for val in col] for col in data_vectors]
t_vector = [group.init(ZR, val) for val in time_vector]

batch_id, public_header, secrets = do.create_batch(m_matrix, t_vector)
ss.store_batch(batch_id, public_header, secrets)

t_challenge = [group.init(ZR, 1) for _ in range(16)]
x_result, pi_audit, pi_non = ss.generate_dc_data_proof(batch_id, t_challenge, do.global_pk['f_current'], 0)

is_valid_a = verifier.verify_dc_query(public_header, t_challenge, x_result, pi_audit, pi_non, 0)
print(f"方案A验证结果: {is_valid_a}")

# 方案B: 模拟HTTP序列化
print("\n=== 方案B: 模拟HTTP序列化 ===")
group2 = PairingGroup('MNT224')
crs2 = keygen_crs(16, group2)
do2 = DataOwner(crs2, group2)
ss2 = StorageServer(crs2, do2.server_acc_keys)
verifier2 = Verifier(crs2, do2.global_pk, group2)

m_matrix2 = [[group2.init(ZR, val) for val in col] for col in data_vectors]
t_vector2 = [group2.init(ZR, val) for val in time_vector]

batch_id2, public_header2, secrets2 = do2.create_batch(m_matrix2, t_vector2)

# 序列化 + 反序列化模拟HTTP传输
header_serialized = serialize_public_header(public_header2, group2)
header_deserialized = deserialize_public_header(header_serialized, group2)
secrets_serialized = serialize_secrets_for_ss(secrets2, group2)
secrets_deserialized = deserialize_secrets_for_ss(secrets_serialized, group2)

ss2.store_batch(batch_id2, header_deserialized, secrets_deserialized)

t_challenge2 = [group2.init(ZR, 1) for _ in range(16)]
x_result2, pi_audit2, pi_non2 = ss2.generate_dc_data_proof(batch_id2, t_challenge2, do2.global_pk['f_current'], 0)

# 序列化证明
pi_audit_serialized = serialize_g1(pi_audit2, group2)
pi_non_serialized = [serialize_g1(pi_non2[0], group2), serialize_zr(pi_non2[1], group2)]

# 反序列化证明
pi_audit_deserialized = deserialize_g1(pi_audit_serialized, group2)
pi_non_deserialized = (deserialize_g1(pi_non_serialized[0], group2), deserialize_zr(pi_non_serialized[1], group2))

is_valid_b = verifier2.verify_dc_query(header_deserialized, t_challenge2, x_result2, pi_audit_deserialized, pi_non_deserialized, 0)
print(f"方案B验证结果: {is_valid_b}")

print("\n=== 结论 ===")
print(f"方案A（本地）: {is_valid_a}")
print(f"方案B（模拟HTTP）: {is_valid_b}")
