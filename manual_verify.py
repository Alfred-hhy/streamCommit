"""
详细调试Verifier验证过程
"""
import requests
from distributed.serialization import *
from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2, pair

# 初始化系统
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
    'data_vectors': [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]],
    'time_vector': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
}).json()

# 存储批次
requests.post('http://localhost:5002/store_batch', json={
    'batch_id': batch_resp['batch_id'],
    'public_header': batch_resp['public_header'],
    'secrets_for_ss': batch_resp['secrets_for_ss']
}).json()

# 生成证明
t_challenge = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
proof_resp = requests.post('http://localhost:5002/generate_dc_proof', json={
    'batch_id': batch_resp['batch_id'],
    't_challenge': t_challenge,
    'f_current': do_resp['global_pk']['f_current'],
    'column_index': 0
}).json()

print("=== 在客户端手动验证 ===")

# 设置group和CRS
group = PairingGroup('MNT224')
crs_data = deserialize_crs(do_resp['crs'], group)

# 如果有alpha，重新生成CRS（模拟Verifier的行为）
if 'alpha' in crs_data:
    from vc_smallness.crs import keygen_crs
    crs = keygen_crs(
        crs_data['n'],
        group,
        alpha=crs_data['alpha'],
        g=crs_data['g'],
        g_hat=crs_data['g_hat']
    )
    print("✓ 使用alpha重新生成了CRS")
else:
    crs = crs_data
    print("✗ CRS没有alpha，直接使用反序列化的CRS")

# 反序列化数据
public_header = deserialize_public_header(batch_resp['public_header'], group)
global_pk = deserialize_global_pk(do_resp['global_pk'], group)
x_result = group.init(ZR, proof_resp['x_result'])  # x_result是int
pi_audit = deserialize_g1(proof_resp['pi_audit'], group)
pi_non = (
    deserialize_g1(proof_resp['pi_non'][0], group),
    deserialize_zr(proof_resp['pi_non'][1], group)
)
t_challenge_zr = [group.init(ZR, t) for t in t_challenge]

print(f"\n=== 步骤1：预检查（签名和累加器） ===")

# 检查签名
from vds_accumulator import Accumulator
import vds_utils

vk_sig = global_pk['vk_sig']
C_data_list = public_header['C_data_list']
C_time = public_header['C_time']
sigma = public_header['sigma']

sig_valid = vds_utils.verify_batch_signature(vk_sig, C_data_list, C_time, sigma)
print(f"签名验证: {sig_valid}")

# 检查累加器
acc = Accumulator(group)
acc_pk = global_pk['acc_pk']
f_current = global_pk['f_current']
sigma_bytes = vds_utils.serialize_signature(sigma)

acc_valid = acc.verify_non_membership(acc_pk, f_current, sigma_bytes, pi_non)
print(f"累加器验证: {acc_valid}")

if not sig_valid or not acc_valid:
    print(f"\n❌ 预检查失败！")
    exit(1)

print(f"\n✓ 预检查通过")

print(f"\n=== 步骤2：VC验证 ===")

# VC验证公式：e(C, ∏ ĝ_{n+1-i}^{t_i}) = e(pi_audit, ĝ) · e(g_1, ĝ_n)^{x_result}

n = crs['n']
g_hat = crs['g_hat']
g_hat_list = crs['g_hat_list']
g_list = crs['g_list']
C_data = C_data_list[0]

print(f"n = {n}")
print(f"C_data: {C_data}")
print(f"pi_audit: {pi_audit}")
print(f"x_result: {x_result}")

# 计算LHS: e(C, ∏ ĝ_{n+1-i}^{t_i})
print(f"\n计算LHS: e(C, ∏ ĝ_{{n+1-i}}^{{t_i}})")
g_hat_prod = group.init(G2, 1)
for i in range(1, n + 1):
    idx = n + 1 - i
    if idx in g_hat_list:
        g_hat_prod *= g_hat_list[idx] ** t_challenge_zr[i - 1]
        if i <= 3:
            print(f"  i={i}, idx={idx}, t={t_challenge_zr[i-1]}")

print(f"g_hat_prod计算完成")

lhs = pair(C_data, g_hat_prod)
print(f"LHS = e(C, g_hat_prod)")

# 计算RHS: e(pi_audit, ĝ) · e(g_1, ĝ_n)^{x_result}
print(f"\n计算RHS: e(pi_audit, ĝ) · e(g_1, ĝ_n)^{{x_result}}")
rhs_1 = pair(pi_audit, g_hat)
print(f"rhs_1 = e(pi_audit, g_hat)")

rhs_2 = pair(g_list[1], g_hat_list[n]) ** x_result
print(f"rhs_2 = e(g_1, g_hat_n)^x_result")

rhs = rhs_1 * rhs_2
print(f"RHS = rhs_1 * rhs_2")

# 比较
print(f"\n=== 结果 ===")
print(f"LHS == RHS: {lhs == rhs}")

if lhs != rhs:
    print("\n❌ VC验证失败！")
    print("可能原因：")
    print("1. CRS不一致")
    print("2. 证明生成错误")
    print("3. 承诺和证明不匹配")
else:
    print("\n✓ VC验证通过！")
