#!/usr/bin/env python
"""测试跨group实例的序列化"""

from charm.toolbox.pairinggroup import PairingGroup, G1
from charm.core.engine.util import objectToBytes, bytesToObject
import base64

# 创建第一个group并生成一个元素
group1 = PairingGroup('MNT224')
elem1 = group1.random(G1)
print(f"Group1 elem1: {elem1}")

# 序列化
serialized = base64.b64encode(objectToBytes(elem1, group1)).decode('utf-8')
print(f"Serialized (first 50 chars): {serialized[:50]}")

# 创建第二个group并反序列化
group2 = PairingGroup('MNT224')
elem2 = bytesToObject(base64.b64decode(serialized), group2)
print(f"Group2 elem2: {elem2}")

# 检查是否相等
print(f"\nAre they equal? {elem1 == elem2}")

# 测试运算
result1 = elem1 ** 2
serialized_result = base64.b64encode(objectToBytes(result1, group1)).decode('utf-8')
result2 = bytesToObject(base64.b64decode(serialized_result), group2)
print(f"Result1 ** 2 == Result2? {result1 == result2}")
