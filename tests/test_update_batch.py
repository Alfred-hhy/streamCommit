"""
测试批次更新功能
================

测试 VDS 系统的 update_batch 功能，验证：
1. 旧批次被正确撤销
2. 新批次被正确创建
3. 旧批次无法通过验证
4. 新批次可以通过验证
"""

import pytest
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2
from vc_smallness import setup, keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier


class TestUpdateBatch:
    """测试批次更新功能"""
    
    @pytest.fixture
    def setup_system(self):
        """设置测试系统"""
        # 系统参数
        params = setup('MNT224')
        group = params['group']
        n = 8
        crs = keygen_crs(n, group)
        
        # 创建角色
        do = DataOwner(crs, group)
        ss = StorageServer(crs, do.get_initial_server_keys())
        verifier = Verifier(crs, do.get_global_pk(), group)
        
        return {
            'group': group,
            'n': n,
            'crs': crs,
            'do': do,
            'ss': ss,
            'verifier': verifier
        }
    
    def test_update_batch_basic(self, setup_system):
        """
        测试基本的批次更新功能
        
        工作流程：
        1. DO 创建原始批次（数据 = [10, 11, 12, ...], 时间 = [1, 2, 3, ...]）
        2. SS 存储批次
        3. 验证原始批次可以通过验证
        4. DO 更新批次（数据 = [20, 21, 22, ...], 时间 = [11, 12, 13, ...]）
        5. SS 更新批次
        6. Verifier 更新全局公钥
        7. 验证旧批次无法通过验证（已撤销）
        8. 验证新批次可以通过验证
        """
        sys = setup_system
        do = sys['do']
        ss = sys['ss']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']
        
        # 步骤 1: 创建原始批次
        m_old = [group.init(ZR, 10 + i) for i in range(n)]  # [10, 11, 12, ..., 17]
        t_old = [group.init(ZR, i + 1) for i in range(n)]   # [1, 2, 3, ..., 8]
        
        batch_id_old, header_old, secrets_old = do.create_batch(m_old, t_old)
        
        # 步骤 2: SS 存储批次
        ss.store_batch(batch_id_old, header_old, secrets_old)
        
        # 步骤 3: 验证原始批次
        t_challenge = [group.init(ZR, 1) for _ in range(n)]  # 求和
        f_current_before = do.get_global_pk()["f_current"]
        
        x_old, pi_audit_old, pi_non_old = ss.generate_dc_data_proof(
            batch_id_old, t_challenge, f_current_before
        )
        
        is_valid_before = verifier.verify_dc_query(
            header_old, t_challenge, x_old, pi_audit_old, pi_non_old
        )
        
        assert is_valid_before, "原始批次应该通过验证"
        
        # 步骤 4: DO 更新批次
        m_new = [group.init(ZR, 20 + i) for i in range(n)]  # [20, 21, 22, ..., 27]
        t_new = [group.init(ZR, 11 + i) for i in range(n)]  # [11, 12, 13, ..., 18]
        
        g_s_q_new, new_global_pk, sigma_bytes, batch_id_new, header_new, secrets_new = \
            do.update_batch(header_old, m_new, t_new)
        
        # 步骤 5: SS 更新批次
        ss.update_batch(batch_id_old, g_s_q_new, sigma_bytes, 
                       batch_id_new, header_new, secrets_new)
        
        # 步骤 6: Verifier 更新全局公钥
        verifier.update_global_pk(new_global_pk)
        
        # 步骤 7: 验证旧批次无法通过验证
        f_current_after = new_global_pk["f_current"]
        
        # 旧批次已被删除，应该抛出异常
        with pytest.raises(ValueError, match="not found"):
            ss.generate_dc_data_proof(batch_id_old, t_challenge, f_current_after)
        
        # 步骤 8: 验证新批次可以通过验证
        x_new, pi_audit_new, pi_non_new = ss.generate_dc_data_proof(
            batch_id_new, t_challenge, f_current_after
        )
        
        is_valid_after = verifier.verify_dc_query(
            header_new, t_challenge, x_new, pi_audit_new, pi_non_new
        )
        
        assert is_valid_after, "新批次应该通过验证"
        
        # 验证结果不同（数据已更新）
        assert x_old != x_new, "新旧批次的查询结果应该不同"
        
        print("✅ 批次更新测试通过")
        print(f"   - 旧批次 ID: {batch_id_old[:8]}...")
        print(f"   - 新批次 ID: {batch_id_new[:8]}...")
        print(f"   - 旧批次结果: {x_old}")
        print(f"   - 新批次结果: {x_new}")

    def test_update_multidim_batch(self, setup_system):
        """
        测试多维批次的更新功能

        工作流程：
        1. 创建多维批次（3 列：温度、湿度、气压）
        2. 验证所有列都可以查询
        3. 更新批次（修改所有列的数据）
        4. 验证旧批次失效
        5. 验证新批次的所有列都可以查询
        """
        sys = setup_system
        do = sys['do']
        ss = sys['ss']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']

        # 步骤 1: 创建多维批次
        temp_old = [group.init(ZR, 20 + i) for i in range(n)]
        humid_old = [group.init(ZR, 50 + i) for i in range(n)]
        pressure_old = [group.init(ZR, 1000 + i) for i in range(n)]
        m_matrix_old = [temp_old, humid_old, pressure_old]
        t_old = [group.init(ZR, i + 1) for i in range(n)]

        batch_id_old, header_old, secrets_old = do.create_batch(m_matrix_old, t_old)
        ss.store_batch(batch_id_old, header_old, secrets_old)

        # 步骤 2: 验证所有列
        t_challenge = [group.init(ZR, 1) for _ in range(n)]
        f_current_before = do.get_global_pk()["f_current"]

        results_old = []
        for col_idx in range(3):
            x, pi_audit, pi_non = ss.generate_dc_data_proof(
                batch_id_old, t_challenge, f_current_before, column_index=col_idx
            )
            is_valid = verifier.verify_dc_query(
                header_old, t_challenge, x, pi_audit, pi_non, column_index=col_idx
            )
            assert is_valid, f"旧批次列 {col_idx} 应该通过验证"
            results_old.append(x)

        # 步骤 3: 更新批次
        temp_new = [group.init(ZR, 25 + i) for i in range(n)]
        humid_new = [group.init(ZR, 60 + i) for i in range(n)]
        pressure_new = [group.init(ZR, 1010 + i) for i in range(n)]
        m_matrix_new = [temp_new, humid_new, pressure_new]
        t_new = [group.init(ZR, 11 + i) for i in range(n)]

        g_s_q_new, new_global_pk, sigma_bytes, batch_id_new, header_new, secrets_new = \
            do.update_batch(header_old, m_matrix_new, t_new)

        ss.update_batch(batch_id_old, g_s_q_new, sigma_bytes,
                       batch_id_new, header_new, secrets_new)
        verifier.update_global_pk(new_global_pk)

        # 步骤 4: 验证旧批次失效
        with pytest.raises(ValueError, match="not found"):
            ss.generate_dc_data_proof(batch_id_old, t_challenge,
                                     new_global_pk["f_current"])

        # 步骤 5: 验证新批次的所有列
        results_new = []
        for col_idx in range(3):
            x, pi_audit, pi_non = ss.generate_dc_data_proof(
                batch_id_new, t_challenge, new_global_pk["f_current"],
                column_index=col_idx
            )
            is_valid = verifier.verify_dc_query(
                header_new, t_challenge, x, pi_audit, pi_non, column_index=col_idx
            )
            assert is_valid, f"新批次列 {col_idx} 应该通过验证"
            results_new.append(x)

        # 验证所有列的结果都不同
        for i in range(3):
            assert results_old[i] != results_new[i], f"列 {i} 的结果应该不同"

        print("✅ 多维批次更新测试通过")
        print(f"   - 列数: 3")
        print(f"   - 旧批次结果: {[str(r) for r in results_old]}")
        print(f"   - 新批次结果: {[str(r) for r in results_new]}")

    def test_multiple_updates(self, setup_system):
        """
        测试多次更新批次

        验证可以连续多次更新同一个批次。
        """
        sys = setup_system
        do = sys['do']
        ss = sys['ss']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']

        t_challenge = [group.init(ZR, 1) for _ in range(n)]

        # 创建初始批次
        m_v1 = [group.init(ZR, 10 + i) for i in range(n)]
        t_v1 = [group.init(ZR, i + 1) for i in range(n)]
        batch_id_v1, header_v1, secrets_v1 = do.create_batch(m_v1, t_v1)
        ss.store_batch(batch_id_v1, header_v1, secrets_v1)

        # 第一次更新
        m_v2 = [group.init(ZR, 20 + i) for i in range(n)]
        t_v2 = [group.init(ZR, 11 + i) for i in range(n)]
        g_s_q_2, pk_2, sigma_2, batch_id_v2, header_v2, secrets_v2 = \
            do.update_batch(header_v1, m_v2, t_v2)
        ss.update_batch(batch_id_v1, g_s_q_2, sigma_2, batch_id_v2, header_v2, secrets_v2)
        verifier.update_global_pk(pk_2)

        # 验证 v2
        x_v2, pi_audit_v2, pi_non_v2 = ss.generate_dc_data_proof(
            batch_id_v2, t_challenge, pk_2["f_current"]
        )
        assert verifier.verify_dc_query(header_v2, t_challenge, x_v2, pi_audit_v2, pi_non_v2)

        # 第二次更新
        m_v3 = [group.init(ZR, 30 + i) for i in range(n)]
        t_v3 = [group.init(ZR, 21 + i) for i in range(n)]
        g_s_q_3, pk_3, sigma_3, batch_id_v3, header_v3, secrets_v3 = \
            do.update_batch(header_v2, m_v3, t_v3)
        ss.update_batch(batch_id_v2, g_s_q_3, sigma_3, batch_id_v3, header_v3, secrets_v3)
        verifier.update_global_pk(pk_3)

        # 验证 v3
        x_v3, pi_audit_v3, pi_non_v3 = ss.generate_dc_data_proof(
            batch_id_v3, t_challenge, pk_3["f_current"]
        )
        assert verifier.verify_dc_query(header_v3, t_challenge, x_v3, pi_audit_v3, pi_non_v3)

        # 验证 v1 和 v2 都已失效
        with pytest.raises(ValueError, match="not found"):
            ss.generate_dc_data_proof(batch_id_v1, t_challenge, pk_3["f_current"])
        with pytest.raises(ValueError, match="not found"):
            ss.generate_dc_data_proof(batch_id_v2, t_challenge, pk_3["f_current"])

        print("✅ 多次更新测试通过")
        print(f"   - 更新次数: 2")
        print(f"   - 最终批次 ID: {batch_id_v3[:8]}...")
        print(f"   - 最终结果: {x_v3}")

