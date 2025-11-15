"""
测试跨group的承诺验证
"""
from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2, pair
from vc_smallness.crs import keygen_crs
from vc_smallness.commit import commit_G
from distributed.serialization import serialize_g1, deserialize_g1, serialize_crs, deserialize_crs

# 场景：模拟DO和Verifier使用不同的group

print("=== 场景1：DO生成承诺，Verifier反序列化CRS后验证 ===")

# DO的group
group_do = PairingGroup('MNT224')
crs_do = keygen_crs(16, group_do)
alpha_do = crs_do['alpha']

# DO创建承诺
m = [group_do.init(ZR, i*10) for i in range(1, 17)]
gamma = group_do.random(ZR)
C_do = commit_G(m, gamma, crs_do)

print(f"DO的承诺C: {C_do}")

# 序列化C和CRS
C_ser = serialize_g1(C_do, group_do)
crs_ser = serialize_crs(crs_do, group_do)

# Verifier的group
group_ver = PairingGroup('MNT224')

# 方法1：直接反序列化CRS
crs_ver_deser = deserialize_crs(crs_ser, group_ver)
C_ver_deser = deserialize_g1(C_ser, group_ver)

# 方法2：用alpha重新生成CRS
crs_ver_regen = keygen_crs(
    crs_ver_deser['n'],
    group_ver,
    alpha=crs_ver_deser['alpha'],
    g=crs_ver_deser['g'],
    g_hat=crs_ver_deser['g_hat']
)

print(f"\nVerifier反序列化的承诺C: {C_ver_deser}")
print(f"C相同(字符串): {str(C_do) == str(C_ver_deser)}")

# 比较两种CRS的g_list[1]
print(f"\n反序列化CRS的g_list[1]: {crs_ver_deser['g_list'][1]}")
print(f"重新生成CRS的g_list[1]: {crs_ver_regen['g_list'][1]}")
print(f"g_list[1]相同: {str(crs_ver_deser['g_list'][1]) == str(crs_ver_regen['g_list'][1])}")

# 现在测试：用哪个CRS能验证？
# 简单验证：重新计算承诺，看是否相同
m_ver = [group_ver.init(ZR, i*10) for i in range(1, 17)]

# 用反序列化的gamma重新生成应该不同(gamma是随机的，我们无法传输)
# 但我们可以验证配对等式

print("\n=== 验证配对等式 ===")
# 使用VC的验证公式：e(C, ĝ^t) = e(π, ĝ) * e(g_1, ĝ_n)^x
# 简化版：只检查C是否使用了正确的g_list

# 重新计算C应该使用的g元素
from vc_smallness.commit import commit_G

# 用反序列化的CRS重新生成承诺（不同gamma）
gamma_ver1 = group_ver.random(ZR)
C_ver1 = commit_G(m_ver, gamma_ver1, crs_ver_deser)

# 用重新生成的CRS生成承诺（不同gamma）
gamma_ver2 = group_ver.random(ZR)
C_ver2 = commit_G(m_ver, gamma_ver2, crs_ver_regen)

print(f"用反序列化CRS生成的C: {C_ver1}")
print(f"用重新生成CRS生成的C: {C_ver2}")
print(f"两者不同(因为gamma不同): {str(C_ver1) != str(C_ver2)}")

# 关键测试：DO的C和Verifier重新生成的CRS是否兼容
print("\n=== 关键测试：混合使用是否有效 ===")

# 计算一个简单的配对来验证兼容性
# e(C_do反序列化, g_hat_反序列化) vs e(C_do反序列化, g_hat_重新生成)

e1 = pair(C_ver_deser, crs_ver_deser['g_hat'])
e2 = pair(C_ver_deser, crs_ver_regen['g_hat'])

print(f"e(C反序列化, g_hat反序列化): {e1}")
print(f"e(C反序列化, g_hat重新生成): {e2}")
print(f"配对结果相同: {str(e1) == str(e2)}")

if str(e1) != str(e2):
    print("\n❌ 问题：反序列化的C和重新生成的CRS不兼容！")
    print("原因：虽然g_hat数值相同，但内部group上下文不同")
else:
    print("\n✅ 反序列化的C和重新生成的CRS兼容")
