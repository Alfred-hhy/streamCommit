"""
对比单进程和多进程的证明生成
"""
from charm.toolbox.pairinggroup import PairingGroup, ZR
from vc_smallness.crs import keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier
import requests
from distributed.serialization import deserialize_crs, deserialize_global_pk, deserialize_public_header, deserialize_g1, deserialize_zr

# 测试数据
data_vectors = [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]]
time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
t_challenge = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

print("=== 单进程测试 ===")
group1 = PairingGroup('MNT224')
crs1 = keygen_crs(16, group1)
do1 = DataOwner(crs1, group1)
ss1 = StorageServer(crs1, do1.server_acc_keys)
verifier1 = Verifier(crs1, do1.global_pk, group1)

# 转换数据为ZR
m_matrix1 = [[group1.init(ZR, val) for val in col] for col in data_vectors]
t_vector1 = [group1.init(ZR, val) for val in time_vector]
t_chal1 = [group1.init(ZR, val) for val in t_challenge]

# 创建批次
batch_id1, header1, secrets1 = do1.create_batch(m_matrix1, t_vector1)
ss1.store_batch(batch_id1, header1, secrets1)

# 生成证明
x_result1, pi_audit1, pi_non1 = ss1.generate_dc_data_proof(
    batch_id1, t_chal1, do1.global_pk['f_current'], column_index=0
)

# 验证
is_valid1 = verifier1.verify_dc_query(
    header1, t_chal1, x_result1, pi_audit1, pi_non1, column_index=0
)

print(f"单进程验证结果: {is_valid1}")
print(f"x_result: {x_result1}")
print(f"pi_audit: {pi_audit1}")
print(f"pi_non[0]: {pi_non1[0]}")
print(f"pi_non[1]: {pi_non1[1]}")

print("\n=== 多进程测试（HTTP） ===")

# 初始化HTTP系统
do_resp = requests.post('http://localhost:5001/init', json={'n': 16}).json()
ss_resp = requests.post('http://localhost:5002/init', json={
    'crs': do_resp['crs'],
    'server_acc_keys': do_resp['server_acc_keys']
}).json()
verifier_resp = requests.post('http://localhost:5003/init', json={
    'crs': do_resp['crs'],
    'global_pk': do_resp['global_pk']
}).json()

# 创建批次
batch_resp = requests.post('http://localhost:5001/create_batch', json={
    'data_vectors': data_vectors,
    'time_vector': time_vector
}).json()

# 存储批次
requests.post('http://localhost:5002/store_batch', json={
    'batch_id': batch_resp['batch_id'],
    'public_header': batch_resp['public_header'],
    'secrets_for_ss': batch_resp['secrets_for_ss']
}).json()

# 生成证明
proof_resp = requests.post('http://localhost:5002/generate_dc_proof', json={
    'batch_id': batch_resp['batch_id'],
    't_challenge': t_challenge,
    'f_current': do_resp['global_pk']['f_current'],
    'column_index': 0
}).json()

# 验证
verify_resp = requests.post('http://localhost:5003/verify_dc_query', json={
    'public_header': batch_resp['public_header'],
    't_challenge': t_challenge,
    'x_result': proof_resp['x_result'],
    'pi_audit': proof_resp['pi_audit'],
    'pi_non': proof_resp['pi_non'],
    'column_index': 0
}).json()

print(f"多进程验证结果: {verify_resp['is_valid']}")
print(f"x_result: {proof_resp['x_result']}")

# 反序列化以查看详情
group2 = PairingGroup('MNT224')
pi_audit2 = deserialize_g1(proof_resp['pi_audit'], group2)
pi_non2 = (
    deserialize_g1(proof_resp['pi_non'][0], group2),
    deserialize_zr(proof_resp['pi_non'][1], group2)
)

print(f"pi_audit: {pi_audit2}")
print(f"pi_non[0]: {pi_non2[0]}")
print(f"pi_non[1]: {pi_non2[1]}")

print("\n=== 比较结果 ===")
print(f"x_result相同: {int(x_result1) == proof_resp['x_result']}")

# 注意：不能直接比较不同group实例的元素，但可以比较序列化后的值
from distributed.serialization import serialize_g1, serialize_zr
pi_audit1_ser = serialize_g1(pi_audit1, group1)
pi_audit2_ser = serialize_g1(pi_audit2, group2)
print(f"pi_audit相同: {pi_audit1_ser == pi_audit2_ser}")

pi_non1_0_ser = serialize_g1(pi_non1[0], group1)
pi_non2_0_ser = serialize_g1(pi_non2[0], group2)
print(f"pi_non[0]相同: {pi_non1_0_ser == pi_non2_0_ser}")

pi_non1_1_ser = serialize_zr(pi_non1[1], group1)
pi_non2_1_ser = serialize_zr(pi_non2[1], group2)
print(f"pi_non[1]相同: {pi_non1_1_ser == pi_non2_1_ser}")
