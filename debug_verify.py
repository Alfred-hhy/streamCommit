#!/usr/bin/env python
"""调试验证流程"""

from distributed.client import DOClient, SSClient, VerifierClient

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
print("初始化完成")

# 创建批次
print("\n=== 创建批次 ===")
data_vectors = [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]]
time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
result = do_client.create_batch(data_vectors, time_vector)
batch_id = result['batch_id']
public_header = result['public_header']
secrets = result['secrets_for_ss']
print(f"批次ID: {batch_id}")

# 存储批次
ss_client.store_batch(batch_id, public_header, secrets)
print("批次已存储")

# 生成DC证明
print("\n=== 生成DC证明 ===")
t_challenge = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
result = ss_client.generate_dc_proof(batch_id, t_challenge, global_pk['f_current'], column_index=0)
x_result = result['x_result']
pi_audit = result['pi_audit']
pi_non = result['pi_non']
print(f"结果: {x_result}")
print(f"pi_audit type: {type(pi_audit)}")
print(f"pi_non type: {type(pi_non)}")

# 验证
print("\n=== 验证DC证明 ===")
result = verifier_client.verify_dc_query(
    public_header, t_challenge, x_result, pi_audit, pi_non, column_index=0
)
print(f"验证成功: {result['success']}")
print(f"验证结果: {result['is_valid']}")

# 如果失败，打印详细信息
if not result['is_valid']:
    print("\n验证失败！让我们检查数据...")
    print(f"public_header keys: {public_header.keys()}")
    print(f"t_challenge length: {len(t_challenge)}")
    print(f"x_result: {x_result}")
