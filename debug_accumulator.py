"""
调试累加器验证失败
"""
from distributed.client import DOClient, SSClient, VerifierClient
from charm.toolbox.pairinggroup import PairingGroup, ZR

# 初始化客户端
do_client = DOClient()
ss_client = SSClient()
verifier_client = VerifierClient()

print("=== 初始化系统 ===")
init_result = do_client.init(n=16)
print(f"DO初始化: {init_result['success']}")

# 获取CRS看看是否包含alpha
import requests
crs_resp = requests.get('http://localhost:5001/get_crs').json()
crs_data = crs_resp['crs']
print(f"CRS包含alpha: {'alpha' in crs_data}")

# 初始化SS和Verifier
ss_client.init(init_result['crs'], init_result['server_acc_keys'])
verifier_client.init(init_result['crs'], init_result['global_pk'])

print("\n=== 创建批次 ===")
# 创建数据
data_vectors = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]]
time_vector = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

batch_result = do_client.create_batch(data_vectors, time_vector)
batch_id = batch_result['batch_id']
print(f"批次ID: {batch_id}")

# 存储批次
ss_client.store_batch(batch_id, batch_result['public_header'], batch_result['secrets_for_ss'])

print("\n=== 比较global_pk组件 ===")
# 获取DO的global_pk
global_pk_resp = requests.get('http://localhost:5001/get_global_pk').json()
global_pk = global_pk_resp['global_pk']

# 打印f_current
print(f"f_current: {global_pk['f_current'][:50]}...")
print(f"acc_pk长度: {len(global_pk['acc_pk'])}")

# 打印accumulator签名
sigma_bytes = batch_result['public_header']['sigma']
print(f"sigma: {sigma_bytes[:50]}...")

print("\n=== 生成DC证明 ===")
t_challenge = time_vector
proof_result = ss_client.generate_dc_proof(batch_id, t_challenge, global_pk['f_current'])
print(f"x_result: {proof_result['x_result']}")

print("\n=== 验证 ===")
verify_result = verifier_client.verify_dc_query(
    batch_result['public_header'],
    t_challenge,
    proof_result['x_result'],
    proof_result['pi_audit'],
    proof_result['pi_non']
)

print(f"验证结果: {verify_result['is_valid']}")

# 直接测试accumulator验证
print("\n=== 直接测试累加器验证 ===")
from vds_accumulator import Accumulator
import vds_utils
from distributed.serialization import deserialize_global_pk, deserialize_bytes, deserialize_g1, deserialize_zr

group = PairingGroup('MNT224')

# 反序列化global_pk
gpk = deserialize_global_pk(global_pk, group)
sigma_b = deserialize_bytes(sigma_bytes)
pi_non_tuple = (
    deserialize_g1(proof_result['pi_non'][0], group),
    deserialize_zr(proof_result['pi_non'][1], group)
)

# 创建Accumulator实例
acc = Accumulator(group)

print(f"acc_pk type: {type(gpk['acc_pk'])}")
print(f"f_current type: {type(gpk['f_current'])}")
print(f"sigma_bytes length: {len(sigma_b)}")
print(f"pi_non type: {type(pi_non_tuple)}")

# 验证非成员
is_non_member = acc.verify_non_membership(
    gpk['acc_pk'],
    gpk['f_current'],
    sigma_b,
    pi_non_tuple
)
print(f"累加器非成员验证: {is_non_member}")

# 如果失败，尝试打印更多细节
if not is_non_member:
    print("\n=== 累加器验证失败详情 ===")
    # 检查f_current是否为单位元
    print(f"f_current == g: {gpk['f_current'] == gpk['acc_pk'][0]}")

    # 尝试手动验证配对等式
    g, g_hat, g_hat_s = gpk['acc_pk']
    f = gpk['f_current']
    pi_G, pi_r = pi_non_tuple

    # 计算消息哈希
    msg_hash = vds_utils.serialize_signature(sigma_b)
    h_m = group.hash(msg_hash, G1)

    print(f"h_m type: {type(h_m)}")
    print(f"pi_G type: {type(pi_G)}")
    print(f"pi_r type: {type(pi_r)}")

    # 验证配对等式：e(f / h_m^r, g_hat_s) = e(pi_G, g_hat)
    from charm.toolbox.pairinggroup import G1
    lhs_numerator = f
    lhs_denominator = h_m ** pi_r
    lhs_elem = lhs_numerator / lhs_denominator

    lhs = group.pair_prod(lhs_elem, g_hat_s)
    rhs = group.pair_prod(pi_G, g_hat)

    print(f"配对等式成立: {lhs == rhs}")
