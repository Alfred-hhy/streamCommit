#!/usr/bin/env python3
"""
批次更新功能演示
================

演示如何使用 VDS 系统的 update_batch 功能来更新已存在的批次。

场景：
1. 创建初始批次（温度数据）
2. 查询并验证初始批次
3. 发现数据错误，需要更新
4. 使用 update_batch 更新批次
5. 验证旧批次失效，新批次有效
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from charm.toolbox.pairinggroup import PairingGroup, ZR
from vc_smallness import setup, keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier


def main():
    print("=" * 70)
    print("VDS 批次更新功能演示")
    print("=" * 70)
    print()
    
    # 1. 系统设置
    print("[1] 系统初始化...")
    params = setup('MNT224')
    group = params['group']
    n = 8
    crs = keygen_crs(n, group)
    
    # 创建角色
    do = DataOwner(crs, group)
    ss = StorageServer(crs, do.get_initial_server_keys())
    verifier = Verifier(crs, do.get_global_pk(), group)
    print("✅ 系统初始化完成")
    print()
    
    # 2. 创建初始批次
    print("[2] 创建初始批次（温度数据）...")
    temp_data_v1 = [group.init(ZR, 20 + i) for i in range(n)]  # [20, 21, 22, ..., 27]
    time_vector_v1 = [group.init(ZR, i + 1) for i in range(n)]  # [1, 2, 3, ..., 8]
    
    batch_id_v1, header_v1, secrets_v1 = do.create_batch(temp_data_v1, time_vector_v1)
    ss.store_batch(batch_id_v1, header_v1, secrets_v1)
    
    print(f"✅ 批次创建成功 (ID: {batch_id_v1[:8]}...)")
    print(f"    - 温度数据: [20, 21, 22, ..., 27]")
    print(f"    - 时间戳: [1, 2, 3, ..., 8]")
    print()
    
    # 3. 查询初始批次
    print("[3] 查询初始批次...")
    t_challenge = [group.init(ZR, 1) for _ in range(n)]  # 求和
    f_current_v1 = do.get_global_pk()["f_current"]
    
    x_v1, pi_audit_v1, pi_non_v1 = ss.generate_dc_data_proof(
        batch_id_v1, t_challenge, f_current_v1
    )
    
    is_valid_v1 = verifier.verify_dc_query(
        header_v1, t_challenge, x_v1, pi_audit_v1, pi_non_v1
    )
    
    print(f"✅ 查询结果: {x_v1}")
    print(f"✅ 验证结果: {'通过' if is_valid_v1 else '失败'}")
    print()
    
    # 4. 发现数据错误，需要更新
    print("[4] 发现数据错误，需要更新批次...")
    print("    - 原因: 传感器校准错误，温度读数偏低 5 度")
    print("    - 操作: 使用 update_batch 更新数据")
    print()
    
    # 5. 更新批次
    print("[5] 更新批次...")
    temp_data_v2 = [group.init(ZR, 25 + i) for i in range(n)]  # [25, 26, 27, ..., 32]（修正后）
    time_vector_v2 = [group.init(ZR, 11 + i) for i in range(n)]  # [11, 12, 13, ..., 18]（新时间戳）
    
    g_s_q_new, new_global_pk, sigma_bytes, batch_id_v2, header_v2, secrets_v2 = \
        do.update_batch(header_v1, temp_data_v2, time_vector_v2)
    
    # 更新 SS
    ss.update_batch(batch_id_v1, g_s_q_new, sigma_bytes, 
                   batch_id_v2, header_v2, secrets_v2)
    
    # 更新 Verifier
    verifier.update_global_pk(new_global_pk)
    
    print(f"✅ 批次更新成功")
    print(f"    - 旧批次 ID: {batch_id_v1[:8]}... (已撤销)")
    print(f"    - 新批次 ID: {batch_id_v2[:8]}...")
    print(f"    - 新温度数据: [25, 26, 27, ..., 32]")
    print(f"    - 新时间戳: [11, 12, 13, ..., 18]")
    print()
    
    # 6. 验证旧批次失效
    print("[6] 验证旧批次已失效...")
    try:
        ss.generate_dc_data_proof(batch_id_v1, t_challenge, new_global_pk["f_current"])
        print("❌ 错误：旧批次不应该存在！")
    except ValueError as e:
        print(f"✅ 旧批次已被删除: {e}")
    print()
    
    # 7. 查询新批次
    print("[7] 查询新批次...")
    x_v2, pi_audit_v2, pi_non_v2 = ss.generate_dc_data_proof(
        batch_id_v2, t_challenge, new_global_pk["f_current"]
    )
    
    is_valid_v2 = verifier.verify_dc_query(
        header_v2, t_challenge, x_v2, pi_audit_v2, pi_non_v2
    )
    
    print(f"✅ 查询结果: {x_v2}")
    print(f"✅ 验证结果: {'通过' if is_valid_v2 else '失败'}")
    print()
    
    # 8. 对比结果
    print("[8] 对比新旧批次...")
    print(f"    - 旧批次结果: {x_v1}")
    print(f"    - 新批次结果: {x_v2}")
    print(f"    - 差异: {x_v2 - x_v1}")
    print()
    
    print("=" * 70)
    print("✅ 演示完成")
    print("=" * 70)
    print()
    print("关键要点：")
    print("  1. update_batch 是原子操作，自动处理撤销 + 创建")
    print("  2. 旧批次立即失效，无法再查询或验证")
    print("  3. 新批次使用新的签名，独立于旧批次")
    print("  4. 累加器确保旧批次不能被回滚")
    print("  5. 适用于数据更正、刷新、修改等场景")
    print()


if __name__ == '__main__':
    main()

