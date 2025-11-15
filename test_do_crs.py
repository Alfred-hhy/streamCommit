"""
检查DO的CRS是否与SS/Verifier一致
"""
import requests
from distributed.serialization import deserialize_crs, deserialize_g1
from charm.toolbox.pairinggroup import PairingGroup

# 重新初始化系统
print("=== 初始化DO ===")
do_resp = requests.post('http://localhost:5001/init', json={'n': 16}).json()
print(f"DO初始化成功: {do_resp['success']}")

crs_data = do_resp['crs']

# 初始化SS
print("\n=== 初始化SS ===")
ss_resp = requests.post('http://localhost:5002/init', json={
    'crs': crs_data,
    'server_acc_keys': do_resp['server_acc_keys']
}).json()

# 初始化Verifier
print("\n=== 初始化Verifier ===")
verifier_resp = requests.post('http://localhost:5003/init', json={
    'crs': crs_data,
    'global_pk': do_resp['global_pk']
}).json()

# 反序列化CRS
group = PairingGroup('MNT224')
crs = deserialize_crs(crs_data, group)

print("\n=== DO的CRS ===")
print(f"CRS包含alpha: {'alpha' in crs}")
print(f"g: {crs['g']}")
print(f"g_list[1]: {crs['g_list'][1]}")

# 检查服务器日志中的g_list[1]
print("\n=== 检查SS日志中的g_list[1] ===")
import subprocess
ss_log = subprocess.check_output(['tail', '-50', 'logs/ss.log']).decode()
for line in ss_log.split('\n'):
    if 'g_list[1] after' in line:
        print(line)

print("\n=== 检查Verifier日志中的g_list[1] ===")
ver_log = subprocess.check_output(['tail', '-50', 'logs/verifier.log']).decode()
for line in ver_log.split('\n'):
    if 'g_list[1] after' in line:
        print(line)
