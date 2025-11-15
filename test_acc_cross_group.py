"""
测试累加器公钥在不同group中的兼容性
"""
from charm.toolbox.pairinggroup import PairingGroup, G1, G2, ZR
from distributed.serialization import serialize_g1, serialize_g2, deserialize_g1, deserialize_g2

# 在group1中生成acc_pk
group1 = PairingGroup('MNT224')
g1 = group1.random(G1)
g_hat1 = group1.random(G2)
s1 = group1.random(ZR)
g_hat_s1 = g_hat1 ** s1

acc_pk1 = (g1, g_hat1, g_hat_s1)

print("=== group1中的acc_pk ===")
print(f"g: {g1}")
print(f"g_hat: {g_hat1}")
print(f"g_hat_s: {g_hat_s1}")

# 序列化
g_ser = serialize_g1(g1, group1)
g_hat_ser = serialize_g2(g_hat1, group1)
g_hat_s_ser = serialize_g2(g_hat_s1, group1)

# 在group2中反序列化
group2 = PairingGroup('MNT224')
g2 = deserialize_g1(g_ser, group2)
g_hat2 = deserialize_g2(g_hat_ser, group2)
g_hat_s2 = deserialize_g2(g_hat_s_ser, group2)

acc_pk2 = (g2, g_hat2, g_hat_s2)

print("\n=== group2中反序列化的acc_pk ===")
print(f"g: {g2}")
print(f"g_hat: {g_hat2}")
print(f"g_hat_s: {g_hat_s2}")

print(f"\n数值相同: {str(g1) == str(g2) and str(g_hat1) == str(g_hat2) and str(g_hat_s1) == str(g_hat_s2)}")

# 测试累加器验证
from vds_accumulator import Accumulator
import hashlib

acc1 = Accumulator(group1)
acc2 = Accumulator(group2)

# 在group1中生成非成员证明（空累加器）
f_current1 = g1  # 空累加器
item = b"test_item"

# 注意：server_keys只有g，表示q=0
server_keys1 = (g1,)
pi_non1 = acc1.prove_non_membership(server_keys1, f_current1, item, X=[])

print(f"\n=== group1生成的非成员证明 ===")
print(f"w: {pi_non1[0]}")
print(f"u: {pi_non1[1]}")

# 序列化证明
from distributed.serialization import serialize_zr, deserialize_zr
w_ser = serialize_g1(pi_non1[0], group1)
u_ser = serialize_zr(pi_non1[1], group1)

# 在group2中反序列化证明和f_current
w2 = deserialize_g1(w_ser, group2)
u2 = deserialize_zr(u_ser, group2)
f_current2 = g2  # f_current也需要反序列化

pi_non2 = (w2, u2)

print(f"\n=== group2中反序列化的证明 ===")
print(f"w: {w2}")
print(f"u: {u2}")

# 在group2中验证
is_valid = acc2.verify_non_membership(acc_pk2, f_current2, item, pi_non2)

print(f"\n=== 验证结果 ===")
print(f"跨group验证: {is_valid}")

if not is_valid:
    print("\n❌ 问题：跨group的累加器验证失败！")
    print("即使acc_pk, f_current, pi_non都正确反序列化")
    print("验证仍然失败，说明group上下文很重要")
