#!/usr/bin/env python
"""调试脚本：测试generate_dc_proof"""

from distributed.client import DOClient, SSClient

# 创建客户端
do_client = DOClient()
ss_client = SSClient()

# 初始化DO
print("初始化DO...")
result = do_client.init(n=16)
print(f"DO初始化: {result['success']}")
crs = result['crs']
global_pk = result['global_pk']
server_acc_keys = result['server_acc_keys']

# 初始化SS
print("初始化SS...")
result = ss_client.init(crs, server_acc_keys)
print(f"SS初始化: {result['success']}")

# 创建批次
print("\n创建批次...")
data_vectors = [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]]
time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
result = do_client.create_batch(data_vectors, time_vector)
print(f"创建批次: {result['success']}")
batch_id = result['batch_id']
public_header = result['public_header']
secrets = result['secrets_for_ss']

# 存储批次
print("存储批次...")
result = ss_client.store_batch(batch_id, public_header, secrets)
print(f"存储批次: {result['success']}")

# 生成DC证明
print("\n生成DC证明...")
t_challenge = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
f_current = global_pk['f_current']
print(f"f_current type: {type(f_current)}")

try:
    result = ss_client.generate_dc_proof(batch_id, t_challenge, f_current, column_index=0)
    print(f"成功: {result['success']}")
    if result['success']:
        print(f"结果: {result['x_result']}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
