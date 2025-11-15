"""
检查关键问题：DO创建承诺 vs SS/Verifier的CRS是否一致
"""
import requests
from distributed.serialization import deserialize_crs, serialize_g1
from charm.toolbox.pairinggroup import PairingGroup

# 初始化DO
print("=== 1. 初始化DO ===")
do_resp = requests.post('http://localhost:5001/init', json={'n': 16}).json()
crs_sent = do_resp['crs']

print(f"DO发送的CRS包含alpha: {'alpha' in crs_sent}")
print(f"DO的g_list[1]: {crs_sent['g_list']['1'][:50]}...")

# 初始化SS（SS会用alpha重新生成CRS）
print("\n=== 2. 初始化SS ===")
ss_resp = requests.post('http://localhost:5002/init', json={
    'crs': crs_sent,
    'server_acc_keys': do_resp['server_acc_keys']
}).json()

# 初始化Verifier（Verifier也会用alpha重新生成CRS）
print("\n=== 3. 初始化Verifier ===")
verifier_resp = requests.post('http://localhost:5003/init', json={
    'crs': crs_sent,
    'global_pk': do_resp['global_pk']
}).json()

# 从DO再次获取CRS，看DO内部保存的是什么
print("\n=== 4. DO创建批次 ===")
batch_resp = requests.post('http://localhost:5001/create_batch', json={
    'data_vectors': [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]],
    'time_vector': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
}).json()

# 关键：检查承诺C_data是用什么CRS生成的
C_data_from_do = batch_resp['public_header']['C_data_list'][0]
print(f"DO生成的承诺C_data: {C_data_from_do[:50]}...")

# 在客户端用相同数据和DO的CRS生成承诺，看是否匹配
print("\n=== 5. 客户端验证：用DO的CRS生成承诺 ===")
group = PairingGroup('MNT224')
crs = deserialize_crs(crs_sent, group)

from vc_smallness.commit import commit_G
from charm.toolbox.pairinggroup import ZR

m = [group.init(ZR, v) for v in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]]
gamma = group.random(ZR)
C_local = commit_G(m, gamma, crs)

print(f"客户端生成的承诺: {serialize_g1(C_local, group)[:50]}...")
print(f"注意：由于gamma是随机的，两个承诺不会相同")

# 现在检查SS和Verifier是否使用了重新生成的CRS
print("\n=== 6. 检查服务器日志 ===")
import subprocess

ss_log = subprocess.check_output(['tail', '-50', 'logs/ss.log']).decode()
ss_alpha = None
for line in ss_log.split('\n'):
    if 'alpha:' in line and 'SS:' not in line:
        ss_alpha = line.strip()
        break

ver_log = subprocess.check_output(['tail', '-50', 'logs/verifier.log']).decode()
ver_alpha = None
for line in ver_log.split('\n'):
    if 'alpha:' in line and 'Verifier:' not in line:
        ver_alpha = line.strip()
        break

print(f"SS日志中的alpha: {ss_alpha}")
print(f"Verifier日志中的alpha: {ver_alpha}")

print("\n=== 关键分析 ===")
print("问题：")
print("- DO在init时生成CRS（包含alpha）")
print("- DO把CRS序列化发送给SS和Verifier")
print("- SS和Verifier用alpha重新生成CRS（数学上相同）")
print("- 但DO在create_batch时，使用的是哪个CRS？")
print()
print("DO使用的是：它在init时生成的原始CRS对象")
print("SS使用的是：用alpha重新生成的CRS对象")
print("Verifier使用的是：用alpha重新生成的CRS对象")
print()
print("虽然数学上相同，但它们属于不同的group实例！")
print("DO的CRS属于DO的group")
print("SS的CRS属于SS的group（重新生成的）")
print("Verifier的CRS属于Verifier的group（重新生成的）")
