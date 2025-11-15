#!/usr/bin/env python
"""对比本地和HTTP的数据"""

from charm.toolbox.pairinggroup import PairingGroup, ZR
from vc_smallness.crs import keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier
from distributed.serialization import *

# 初始化
group = PairingGroup('MNT224')
crs = keygen_crs(16, group)
do = DataOwner(crs, group)

# 创建批次
data_vectors = [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]]
time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
m_matrix = [[group.init(ZR, val) for val in col] for col in data_vectors]
t_vector = [group.init(ZR, val) for val in time_vector]
batch_id, public_header, secrets = do.create_batch(m_matrix, t_vector)

print("=== 原始数据 ===")
print(f"C_data_list类型: {type(public_header['C_data_list'])}")
print(f"C_data_list长度: {len(public_header['C_data_list'])}")
print(f"C_data_list[0]类型: {type(public_header['C_data_list'][0])}")
print(f"C_time类型: {type(public_header['C_time'])}")
print(f"sigma类型: {type(public_header['sigma'])}")

# 序列化
serialized = serialize_public_header(public_header, group)
print("\n=== 序列化后 ===")
print(f"C_data_list类型: {type(serialized['C_data_list'])}")
print(f"C_data_list长度: {len(serialized['C_data_list'])}")
print(f"C_data_list[0]类型: {type(serialized['C_data_list'][0])}")
print(f"C_time类型: {type(serialized['C_time'])}")
print(f"sigma类型: {type(serialized['sigma'])}")

# 反序列化
deserialized = deserialize_public_header(serialized, group)
print("\n=== 反序列化后 ===")
print(f"C_data_list类型: {type(deserialized['C_data_list'])}")
print(f"C_data_list长度: {len(deserialized['C_data_list'])}")
print(f"C_data_list[0]类型: {type(deserialized['C_data_list'][0])}")
print(f"C_time类型: {type(deserialized['C_time'])}")
print(f"sigma类型: {type(deserialized['sigma'])}")

# 检查是否相等
print("\n=== 数据一致性检查 ===")
print(f"C_data_list[0]相等: {public_header['C_data_list'][0] == deserialized['C_data_list'][0]}")
print(f"C_time相等: {public_header['C_time'] == deserialized['C_time']}")
print(f"sigma相等: {public_header['sigma'] == deserialized['sigma']}")
