"""
调试alpha传输流程
"""
from charm.toolbox.pairinggroup import PairingGroup
from vc_smallness.crs import keygen_crs
from distributed.serialization import serialize_crs, deserialize_crs
from distributed.config import config

print(f"DEV_MODE: {config.dev_mode}")
print()

# 生成CRS
group = PairingGroup('MNT224')
crs = keygen_crs(16, group)
print(f"原始CRS包含alpha: {'alpha' in crs}")
print(f"alpha值: {crs['alpha']}")
print()

# 序列化
serialized = serialize_crs(crs, group)
print(f"序列化后包含alpha: {'alpha' in serialized}")
if 'alpha' in serialized:
    print(f"序列化的alpha: {serialized['alpha']}")
if '_dev_mode_warning' in serialized:
    print(f"警告信息: {serialized['_dev_mode_warning']}")
print()

# 反序列化
group2 = PairingGroup('MNT224')
deserialized = deserialize_crs(serialized, group2)
print(f"反序列化后包含alpha: {'alpha' in deserialized}")
if 'alpha' in deserialized:
    print(f"反序列化的alpha: {deserialized['alpha']}")
