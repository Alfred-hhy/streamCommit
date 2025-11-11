#!/usr/bin/env python3
"""
多维 VDS 系统演示
================

演示如何使用新的多维数据存储功能。
"""

from charm.toolbox.pairinggroup import ZR
from vc_smallness import setup, keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier


def main():
    print("=" * 60)
    print("VDS 多维数据存储演示")
    print("=" * 60)
    
    # 1. 系统初始化
    print("\n[1] 初始化系统...")
    params = setup('MNT224')
    group = params['group']
    n = 8  # 向量大小
    crs = keygen_crs(n=n, group=group)
    
    do = DataOwner(crs, group)
    initial_server_keys = do.get_initial_server_keys()
    ss = StorageServer(crs, initial_server_keys)
    initial_global_pk = do.get_global_pk()
    verifier = Verifier(crs, initial_global_pk, group)
    
    print(f"✅ 系统初始化完成 (n={n})")
    
    # 2. 创建多维数据批次
    print("\n[2] 创建多维数据批次...")
    print("    - 列 0: 温度数据 [20, 21, 22, ..., 27]")
    print("    - 列 1: 湿度数据 [50, 51, 52, ..., 57]")
    print("    - 列 2: 气压数据 [1000, 1001, 1002, ..., 1007]")
    
    temp_data = [group.init(ZR, 20 + i) for i in range(n)]
    humid_data = [group.init(ZR, 50 + i) for i in range(n)]
    pressure_data = [group.init(ZR, 1000 + i) for i in range(n)]
    m_matrix = [temp_data, humid_data, pressure_data]
    t_vector = [group.init(ZR, i + 1) for i in range(n)]
    
    batch_id, public_header, secrets_for_ss = do.create_batch(m_matrix, t_vector)
    ss.store_batch(batch_id, public_header, secrets_for_ss)
    
    print(f"✅ 批次创建成功 (ID: {batch_id[:8]}...)")
    print(f"    - 数据列数: {len(public_header['C_data_list'])}")
    print(f"    - 共享签名: 1 个")
    print(f"    - 共享时间承诺: 1 个")
    
    # 3. DC 查询不同列
    print("\n[3] DC 查询不同列...")
    t_challenge = [group.init(ZR, 1) for _ in range(n)]
    f_current = do.get_global_pk()["f_current"]
    
    column_names = ["温度", "湿度", "气压"]
    for col_idx in range(3):
        x_result, pi_audit, pi_non = ss.generate_dc_data_proof(
            batch_id, t_challenge, f_current, column_index=col_idx
        )
        is_valid = verifier.verify_dc_query(
            public_header, t_challenge, x_result, pi_audit, pi_non, column_index=col_idx
        )
        
        status = "✅ 通过" if is_valid else "❌ 失败"
        print(f"    列 {col_idx} ({column_names[col_idx]}): {status}")
    
    # 4. DA 审计不同列
    print("\n[4] DA 审计不同列...")
    for col_idx in range(3):
        x_result_random, pi_audit_zk, t_challenge_zk, pi_non = ss.generate_da_audit_proof(
            batch_id, f_current, column_index=col_idx
        )
        is_valid = verifier.verify_da_audit(
            public_header, n, x_result_random, pi_audit_zk, t_challenge_zk, pi_non, column_index=col_idx
        )
        
        status = "✅ 通过" if is_valid else "❌ 失败"
        print(f"    列 {col_idx} ({column_names[col_idx]}): {status}")
    
    # 5. 向后兼容性测试
    print("\n[5] 向后兼容性测试（单列数据）...")
    single_col_data = [group.init(ZR, 100 + i) for i in range(n)]
    t_vector2 = [group.init(ZR, i + 1) for i in range(n)]
    
    batch_id2, header2, secrets2 = do.create_batch(single_col_data, t_vector2)
    ss.store_batch(batch_id2, header2, secrets2)
    
    x_result, pi_audit, pi_non = ss.generate_dc_data_proof(
        batch_id2, t_challenge, f_current
    )
    is_valid = verifier.verify_dc_query(
        header2, t_challenge, x_result, pi_audit, pi_non
    )
    
    print(f"    单列批次创建: ✅")
    print(f"    单列批次验证: {'✅ 通过' if is_valid else '❌ 失败'}")
    
    # 6. 性能对比
    print("\n[6] 性能对比...")
    print("    旧方案（3 列数据）:")
    print("      - 批次数: 3")
    print("      - 签名数: 3")
    print("      - 时间承诺数: 3")
    print("    新方案（3 列数据）:")
    print("      - 批次数: 1")
    print("      - 签名数: 1 ⬇️ 降低 66.7%")
    print("      - 时间承诺数: 1 ⬇️ 降低 66.7%")
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

