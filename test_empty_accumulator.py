"""
测试空累加器的非成员证明
"""
from charm.toolbox.pairinggroup import PairingGroup, G1, G2, ZR, pair
from vds_accumulator import Accumulator
import hashlib

group = PairingGroup('MNT224')
acc = Accumulator(group)

# 生成累加器公钥
g = group.random(G1)
g_hat = group.random(G2)
s = group.random(ZR)
g_hat_s = g_hat ** s

acc_pk = (g, g_hat, g_hat_s)
server_keys = (g,)  # 只有g，表示q=0（空累加器）
f_current = g  # 空累加器

# 创建一个要证明非成员的item
item = b"test_signature"

# 生成非成员证明
print("=== 生成非成员证明 ===")
pi_non = acc.prove_non_membership(server_keys, f_current, item, X=[])
w, u = pi_non
print(f"w type: {type(w)}")
print(f"u: {u}")
print(f"u == -1: {u == group.init(ZR, -1)}")

# 验证证明
print("\n=== 验证非成员证明 ===")
is_valid = acc.verify_non_membership(acc_pk, f_current, item, pi_non)
print(f"验证结果: {is_valid}")

# 手动验证配对等式
print("\n=== 手动验证配对等式 ===")
e_i = acc._hash_item(item)
print(f"e_i: {e_i}")

# LHS: e(w, ĝ^{e_i} · ĝ^s) = e(w, ĝ^{e_i + s})
g_hat_e_i_plus_s = (g_hat ** e_i) * g_hat_s
lhs = pair(w, g_hat_e_i_plus_s)
print(f"LHS: e(w, ĝ^{{e_i + s}})")

# RHS: e(f_current · g^u, ĝ)
f_times_g_u = f_current * (g ** u)
rhs = pair(f_times_g_u, g_hat)
print(f"RHS: e(f · g^u, ĝ)")

print(f"LHS == RHS: {lhs == rhs}")

# 对于空累加器，w=1（单位元），u=-1
# 所以 f * g^u = g * g^{-1} = 1（单位元）
f_times_g_u_expected = f_current * (g ** group.init(ZR, -1))
print(f"\nf * g^{{-1}}: {f_times_g_u_expected}")
print(f"f * g^{{-1}} == 单位元: {f_times_g_u_expected == group.init(G1, 1)}")

# 验证等式简化版：e(1, ĝ^{e_i + s}) ?= e(1, ĝ)
# 这不可能成立！除非e_i + s == 1（模p）

print(f"\n检查：e_i + s (mod p)")
sum_val = (int(e_i) + int(s)) % int(group.order())
print(f"e_i + s (mod p): {sum_val}")
print(f"是否等于1: {sum_val == 1}")
