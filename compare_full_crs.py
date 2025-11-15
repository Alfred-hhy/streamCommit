"""
详细比较DO、SS和Verifier的完整CRS
"""
import requests
from distributed.serialization import deserialize_crs
from charm.toolbox.pairinggroup import PairingGroup

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

# 从DO获取CRS
group = PairingGroup('MNT224')
crs = deserialize_crs(do_resp['crs'], group)

print("=== CRS基本信息 ===")
print(f"n: {crs['n']}")
print(f"g: {crs['g']}")
print(f"g_hat: {crs['g_hat']}")

print(f"\n=== g_list (前10个) ===")
for i in range(1, min(11, crs['n']+1)):
    print(f"g_list[{i}]: {crs['g_list'][i]}")

print(f"\n=== g_hat_list (前10个) ===")
for i in range(1, min(11, crs['n']+1)):
    print(f"g_hat_list[{i}]: {crs['g_hat_list'][i]}")

# 检查日志
import subprocess

print(f"\n=== 检查SS日志中的g_list ===")
ss_log = subprocess.check_output(['tail', '-100', 'logs/ss.log']).decode()
for line in ss_log.split('\n'):
    if 'g_list[1] after' in line or 'g before regen' in line or 'g after regen' in line:
        print(line)

print(f"\n=== 检查Verifier日志中的g_list ===")
ver_log = subprocess.check_output(['tail', '-100', 'logs/verifier.log']).decode()
for line in ver_log.split('\n'):
    if 'g_list[1] after' in line or 'g before regen' in line or 'g after regen' in line:
        print(line)
