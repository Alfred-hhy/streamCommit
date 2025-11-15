#!/usr/bin/env python
"""完整HTTP流程调试 - 打印所有中间数据"""

from distributed.client import DOClient, SSClient, VerifierClient
import requests

# 创建客户端
do_client = DOClient()
ss_client = SSClient()
verifier_client = VerifierClient()

# 初始化
print("=== 初始化 ===")
result = do_client.init(n=16)
crs = result['crs']
global_pk = result['global_pk']
server_acc_keys = result['server_acc_keys']

ss_client.init(crs, server_acc_keys)
verifier_client.init(crs, global_pk)

# 创建批次
print("\n=== 创建批次 ===")
data_vectors = [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]]
time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
result = do_client.create_batch(data_vectors, time_vector)
batch_id = result['batch_id']
public_header = result['public_header']
secrets = result['secrets_for_ss']

print(f"public_header类型: {type(public_header)}")
print(f"public_header keys: {public_header.keys()}")
print(f"C_data_list类型: {type(public_header['C_data_list'])}")
print(f"C_data_list[0]类型: {type(public_header['C_data_list'][0])}")

# 存储批次
ss_client.store_batch(batch_id, public_header, secrets)

# 生成DC证明
print("\n=== 生成DC证明 ===")
t_challenge = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
result = ss_client.generate_dc_proof(batch_id, t_challenge, global_pk['f_current'], column_index=0)
x_result = result['x_result']
pi_audit = result['pi_audit']
pi_non = result['pi_non']

print(f"x_result: {x_result}")
print(f"pi_audit类型: {type(pi_audit)}")
print(f"pi_non类型: {type(pi_non)}")
print(f"pi_non长度: {len(pi_non)}")

# 手动构造验证请求并打印
print("\n=== 验证请求数据 ===")
verify_data = {
    'public_header': public_header,
    't_challenge': t_challenge,
    'x_result': x_result,
    'pi_audit': pi_audit,
    'pi_non': pi_non,
    'column_index': 0
}
print(f"verify_data keys: {verify_data.keys()}")
print(f"public_header中C_data_list[0][:50]: {public_header['C_data_list'][0][:50]}")
print(f"pi_non[0][:50]: {pi_non[0][:50]}")
print(f"pi_non[1][:50]: {pi_non[1][:50]}")

# 验证
result = verifier_client.verify_dc_query(
    public_header, t_challenge, x_result, pi_audit, pi_non, column_index=0
)
print(f"\n验证结果: {result['is_valid']}")
