"""
比较DO和SS/Verifier的密钥一致性
"""
import requests
from distributed.serialization import deserialize_g1, deserialize_g2, deserialize_global_pk
from charm.toolbox.pairinggroup import PairingGroup

# 初始化DO
print("=== 初始化DO ===")
do_resp = requests.post('http://localhost:5001/init', json={'n': 16}).json()
print(f"DO初始化成功: {do_resp['success']}")

# 获取CRS和global_pk
crs_data = do_resp['crs']
global_pk_data = do_resp['global_pk']
server_acc_keys_data = do_resp['server_acc_keys']

# 初始化SS
print("\n=== 初始化SS ===")
ss_resp = requests.post('http://localhost:5002/init', json={
    'crs': crs_data,
    'server_acc_keys': server_acc_keys_data
}).json()
print(f"SS初始化成功: {ss_resp['success']}")

# 初始化Verifier
print("\n=== 初始化Verifier ===")
verifier_resp = requests.post('http://localhost:5003/init', json={
    'crs': crs_data,
    'global_pk': global_pk_data
}).json()
print(f"Verifier初始化成功: {verifier_resp['success']}")

# 反序列化并比较
group = PairingGroup('MNT224')

print("\n=== 反序列化global_pk ===")
gpk = deserialize_global_pk(global_pk_data, group)
print(f"global_pk keys: {gpk.keys()}")
print(f"acc_pk: {gpk['acc_pk']}")
print(f"f_current: {gpk['f_current']}")

print("\n=== 反序列化server_acc_keys ===")
server_g = deserialize_g1(server_acc_keys_data, group)
print(f"server_acc_keys[0]: {server_g}")

print("\n=== 比较密钥 ===")
acc_pk_g = gpk['acc_pk'][0]
print(f"acc_pk[0] == server_g: {acc_pk_g == server_g}")
print(f"f_current == acc_pk[0]: {gpk['f_current'] == acc_pk_g}")

# 创建批次
print("\n=== 创建批次 ===")
batch_resp = requests.post('http://localhost:5001/create_batch', json={
    'data_vectors': [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]],
    'time_vector': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
}).json()
print(f"批次创建成功: {batch_resp['success']}")
batch_id = batch_resp['batch_id']

# 存储批次到SS
print("\n=== 存储批次到SS ===")
store_resp = requests.post('http://localhost:5002/store_batch', json={
    'batch_id': batch_id,
    'public_header': batch_resp['public_header'],
    'secrets_for_ss': batch_resp['secrets_for_ss']
}).json()
print(f"批次存储成功: {store_resp['success']}")

# 生成DC证明
print("\n=== 生成DC证明 ===")
proof_resp = requests.post('http://localhost:5002/generate_dc_proof', json={
    'batch_id': batch_id,
    't_challenge': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    'f_current': global_pk_data['f_current'],
    'column_index': 0
}).json()
print(f"证明生成成功: {proof_resp['success']}")

# 验证证明
print("\n=== 验证DC证明 ===")
verify_resp = requests.post('http://localhost:5003/verify_dc_query', json={
    'public_header': batch_resp['public_header'],
    't_challenge': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    'x_result': proof_resp['x_result'],
    'pi_audit': proof_resp['pi_audit'],
    'pi_non': proof_resp['pi_non'],
    'column_index': 0
}).json()
print(f"验证请求成功: {verify_resp['success']}")
print(f"验证结果: {verify_resp.get('is_valid', 'ERROR')}")
