#!/usr/bin/env python3
"""
追加 vs 更新对比演示
===================

演示 VDS 系统中"追加新批次"和"更新批次"的区别。

场景对比：
1. 追加新批次：创建新批次，不影响旧批次
2. 更新批次：撤销旧批次，创建新批次
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


def demo_append():
    """演示追加新批次"""
    print("=" * 70)
    print("场景 1: 追加新批次（Append）")
    print("=" * 70)
    print()
    
    # 系统设置
    params = setup('MNT224')
    group = params['group']
    n = 8
    crs = keygen_crs(n, group)
    
    do = DataOwner(crs, group)
    ss = StorageServer(crs, do.get_initial_server_keys())
    verifier = Verifier(crs, do.get_global_pk(), group)
    
    # 创建批次 A（时间段 1）
    print("[1] 创建批次 A（时间段 1: 2024-01-01）...")
    m_a = [group.init(ZR, 10 + i) for i in range(n)]
    t_a = [group.init(ZR, i + 1) for i in range(n)]
    batch_id_a, header_a, secrets_a = do.create_batch(m_a, t_a)
    ss.store_batch(batch_id_a, header_a, secrets_a)
    print(f"✅ 批次 A 创建成功 (ID: {batch_id_a[:8]}...)")
    print()
    
    # 创建批次 B（时间段 2）
    print("[2] 追加批次 B（时间段 2: 2024-01-02）...")
    m_b = [group.init(ZR, 20 + i) for i in range(n)]
    t_b = [group.init(ZR, 11 + i) for i in range(n)]
    batch_id_b, header_b, secrets_b = do.create_batch(m_b, t_b)
    ss.store_batch(batch_id_b, header_b, secrets_b)
    print(f"✅ 批次 B 创建成功 (ID: {batch_id_b[:8]}...)")
    print()
    
    # 验证两个批次都有效
    print("[3] 验证两个批次...")
    t_challenge = [group.init(ZR, 1) for _ in range(n)]
    f_current = do.get_global_pk()["f_current"]
    
    # 验证批次 A
    x_a, pi_audit_a, pi_non_a = ss.generate_dc_data_proof(batch_id_a, t_challenge, f_current)
    is_valid_a = verifier.verify_dc_query(header_a, t_challenge, x_a, pi_audit_a, pi_non_a)
    print(f"✅ 批次 A 验证: {'通过' if is_valid_a else '失败'} (结果: {x_a})")
    
    # 验证批次 B
    x_b, pi_audit_b, pi_non_b = ss.generate_dc_data_proof(batch_id_b, t_challenge, f_current)
    is_valid_b = verifier.verify_dc_query(header_b, t_challenge, x_b, pi_audit_b, pi_non_b)
    print(f"✅ 批次 B 验证: {'通过' if is_valid_b else '失败'} (结果: {x_b})")
    print()
    
    print("📊 总结：")
    print("  - 批次 A 和 B 都有效")
    print("  - 两个批次独立存在，互不影响")
    print("  - 适用场景：时间序列数据、日志记录、历史数据")
    print()


def demo_update():
    """演示更新批次"""
    print("=" * 70)
    print("场景 2: 更新批次（Update）")
    print("=" * 70)
    print()
    
    # 系统设置
    params = setup('MNT224')
    group = params['group']
    n = 8
    crs = keygen_crs(n, group)
    
    do = DataOwner(crs, group)
    ss = StorageServer(crs, do.get_initial_server_keys())
    verifier = Verifier(crs, do.get_global_pk(), group)
    
    # 创建批次 A（错误数据）
    print("[1] 创建批次 A（包含错误数据）...")
    m_a = [group.init(ZR, 10 + i) for i in range(n)]
    t_a = [group.init(ZR, i + 1) for i in range(n)]
    batch_id_a, header_a, secrets_a = do.create_batch(m_a, t_a)
    ss.store_batch(batch_id_a, header_a, secrets_a)
    print(f"✅ 批次 A 创建成功 (ID: {batch_id_a[:8]}...)")
    print()
    
    # 验证批次 A
    print("[2] 验证批次 A...")
    t_challenge = [group.init(ZR, 1) for _ in range(n)]
    f_current_before = do.get_global_pk()["f_current"]
    x_a, pi_audit_a, pi_non_a = ss.generate_dc_data_proof(batch_id_a, t_challenge, f_current_before)
    is_valid_a = verifier.verify_dc_query(header_a, t_challenge, x_a, pi_audit_a, pi_non_a)
    print(f"✅ 批次 A 验证: {'通过' if is_valid_a else '失败'} (结果: {x_a})")
    print()
    
    # 更新批次 A（修正数据）
    print("[3] 发现数据错误，更新批次 A...")
    m_a_corrected = [group.init(ZR, 20 + i) for i in range(n)]  # 修正后的数据
    t_a_new = [group.init(ZR, 11 + i) for i in range(n)]  # 新时间戳
    
    g_s_q_new, new_global_pk, sigma_bytes, batch_id_a_new, header_a_new, secrets_a_new = \
        do.update_batch(header_a, m_a_corrected, t_a_new)
    
    ss.update_batch(batch_id_a, g_s_q_new, sigma_bytes, 
                   batch_id_a_new, header_a_new, secrets_a_new)
    verifier.update_global_pk(new_global_pk)
    
    print(f"✅ 批次更新成功")
    print(f"    - 旧批次 ID: {batch_id_a[:8]}... (已撤销)")
    print(f"    - 新批次 ID: {batch_id_a_new[:8]}...")
    print()
    
    # 验证旧批次失效
    print("[4] 验证旧批次已失效...")
    try:
        ss.generate_dc_data_proof(batch_id_a, t_challenge, new_global_pk["f_current"])
        print("❌ 错误：旧批次不应该存在！")
    except ValueError:
        print("✅ 旧批次已被删除")
    print()
    
    # 验证新批次有效
    print("[5] 验证新批次...")
    x_a_new, pi_audit_a_new, pi_non_a_new = ss.generate_dc_data_proof(
        batch_id_a_new, t_challenge, new_global_pk["f_current"]
    )
    is_valid_a_new = verifier.verify_dc_query(
        header_a_new, t_challenge, x_a_new, pi_audit_a_new, pi_non_a_new
    )
    print(f"✅ 新批次验证: {'通过' if is_valid_a_new else '失败'} (结果: {x_a_new})")
    print()
    
    print("📊 总结：")
    print("  - 旧批次被撤销并删除")
    print("  - 新批次替代旧批次")
    print("  - 适用场景：数据更正、数据刷新、数据修改")
    print()


def main():
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "追加 vs 更新对比演示" + " " * 28 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    # 演示追加
    demo_append()
    
    print()
    print("-" * 70)
    print()
    
    # 演示更新
    demo_update()
    
    # 对比总结
    print("=" * 70)
    print("对比总结")
    print("=" * 70)
    print()
    print("┌─────────────────┬──────────────────────┬──────────────────────┐")
    print("│     特性        │   追加 (Append)      │   更新 (Update)      │")
    print("├─────────────────┼──────────────────────┼──────────────────────┤")
    print("│ 旧批次状态      │ 保持有效             │ 立即失效             │")
    print("│ 新批次状态      │ 独立有效             │ 替代旧批次           │")
    print("│ 批次数量        │ 增加                 │ 保持不变             │")
    print("│ 存储空间        │ 增加                 │ 保持不变             │")
    print("│ 撤销操作        │ 不需要               │ 自动撤销             │")
    print("│ 使用场景        │ 时间序列、日志       │ 数据更正、刷新       │")
    print("└─────────────────┴──────────────────────┴──────────────────────┘")
    print()


if __name__ == '__main__':
    main()

