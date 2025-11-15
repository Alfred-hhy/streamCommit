"""
单进程 vs 多进程的关键差异分析
"""
from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2, pair
from vc_smallness.crs import keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier

print("=== 单进程实现 ===")
print("1. 共享PairingGroup实例")
print("2. 所有组件使用同一个group对象")
print("3. CRS中的元素都属于同一个group")
print()

# 单进程示例
group = PairingGroup('MNT224')
crs = keygen_crs(16, group)
do = DataOwner(crs, group)
ss = StorageServer(crs, do.server_acc_keys)
verifier = Verifier(crs, do.global_pk, group)

print(f"DO的group: {id(group)}")
print(f"SS的group: {id(ss.group)}")
print(f"Verifier的group: {id(verifier.group)}")
print(f"三者是同一个对象: {id(group) == id(ss.group) == id(verifier.group)}")
print()

print("=== 多进程实现 ===")
print("1. 每个进程创建独立的PairingGroup实例")
print("2. 虽然参数相同(MNT224)，但是不同的对象")
print("3. CRS通过序列化/反序列化在进程间传输")
print()

# 模拟多进程：创建多个独立的group
group_do = PairingGroup('MNT224')
group_ss = PairingGroup('MNT224')
group_verifier = PairingGroup('MNT224')

print(f"DO的group: {id(group_do)}")
print(f"SS的group: {id(group_ss)}")
print(f"Verifier的group: {id(group_verifier)}")
print(f"三者是不同对象: {id(group_do) != id(group_ss) != id(group_verifier)}")
print()

print("=== 关键问题 ===")
print("当一个Element从group_do序列化后，再在group_ss中反序列化：")
print("- 元素的数值表示相同")
print("- 但内部可能关联到不同的group上下文")
print()

# 测试序列化/反序列化
from distributed.serialization import serialize_g1, deserialize_g1

g1 = group_do.random(G1)
print(f"原始元素在group_do中: {g1}")

# 序列化
ser = serialize_g1(g1, group_do)
print(f"序列化后: {ser[:50]}...")

# 在不同group中反序列化
g2 = deserialize_g1(ser, group_ss)
print(f"反序列化到group_ss: {g2}")

# 检查数值是否相等
print(f"数值表示相同: {str(g1) == str(g2)}")
print()

print("=== 配对运算的差异 ===")

# 在group_do中创建元素并计算配对
g1_do = group_do.random(G1)
g2_do = group_do.random(G2)
pair_do = pair(g1_do, g2_do)

# 序列化并在group_ss中反序列化
from distributed.serialization import serialize_g2, deserialize_g2
g1_ser = serialize_g1(g1_do, group_do)
g2_ser = serialize_g2(g2_do, group_do)

g1_ss = deserialize_g1(g1_ser, group_ss)
g2_ss = deserialize_g2(g2_ser, group_ss)

# 在group_ss中计算配对
pair_ss = pair(g1_ss, g2_ss)

print(f"在group_do中计算配对: {pair_do}")
print(f"在group_ss中计算配对: {pair_ss}")
print(f"配对结果相同: {str(pair_do) == str(str(pair_ss))}")
print()

print("=== 问题根源分析 ===")
print("可能的问题：")
print("1. CRS在DO中生成，包含g_list和g_hat_list")
print("2. 这些元素序列化后发送给SS和Verifier")
print("3. SS用它的group反序列化CRS")
print("4. SS生成证明时使用反序列化的CRS元素")
print("5. 证明序列化后发送给Verifier")
print("6. Verifier用它的group反序列化证明")
print("7. Verifier用它的CRS(也是反序列化的)进行验证")
print()
print("即使我们共享了alpha并重新生成CRS，")
print("但DO创建承诺时用的CRS，和Verifier验证时用的CRS，")
print("虽然数学上相同，但可能在group上下文上有细微差异")
