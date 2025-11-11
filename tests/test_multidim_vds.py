"""
多维数据存储 VDS 测试
===================

测试多列数据共享时间承诺和签名的功能。
"""

import pytest
from charm.toolbox.pairinggroup import ZR
from vc_smallness import setup, keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier


class TestMultiDimVDS:
    """多维数据存储测试套件"""
    
    @pytest.fixture
    def setup_system(self):
        """设置 VDS 系统"""
        params = setup('MNT224')
        group = params['group']
        n = 8  # 向量大小
        crs = keygen_crs(n=n, group=group)
        
        do = DataOwner(crs, group)
        initial_server_keys = do.get_initial_server_keys()
        ss = StorageServer(crs, initial_server_keys)
        initial_global_pk = do.get_global_pk()
        verifier = Verifier(crs, initial_global_pk, group)
        
        return {
            'crs': crs,
            'group': group,
            'do': do,
            'ss': ss,
            'verifier': verifier,
            'n': n
        }
    
    def test_single_column(self, setup_system):
        """测试单列数据（向后兼容）"""
        sys = setup_system
        do = sys['do']
        ss = sys['ss']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']
        
        # 创建单列数据
        m_matrix = [[group.init(ZR, i + 10) for i in range(n)]]  # 1列
        t_vector = [group.init(ZR, i + 1) for i in range(n)]
        
        batch_id, public_header, secrets_for_ss = do.create_batch(m_matrix, t_vector)
        ss.store_batch(batch_id, public_header, secrets_for_ss)
        
        # DC 查询第 0 列
        t_challenge = [group.init(ZR, 1) for _ in range(n)]
        f_current = do.get_global_pk()["f_current"]
        x_result, pi_audit, pi_non = ss.generate_dc_data_proof(batch_id, t_challenge, f_current, column_index=0)
        
        is_valid = verifier.verify_dc_query(public_header, t_challenge, x_result, pi_audit, pi_non, column_index=0)
        
        assert is_valid, "单列数据验证应通过"
        print("✅ 测试通过：单列数据验证成功")
    
    def test_multi_column_dc(self, setup_system):
        """测试多列数据 DC 查询"""
        sys = setup_system
        do = sys['do']
        ss = sys['ss']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']
        
        # 创建 3 列数据：温度、湿度、气压
        temp_data = [group.init(ZR, 20 + i) for i in range(n)]  # 温度
        humid_data = [group.init(ZR, 50 + i) for i in range(n)]  # 湿度
        pressure_data = [group.init(ZR, 1000 + i) for i in range(n)]  # 气压
        m_matrix = [temp_data, humid_data, pressure_data]
        t_vector = [group.init(ZR, i + 1) for i in range(n)]
        
        batch_id, public_header, secrets_for_ss = do.create_batch(m_matrix, t_vector)
        ss.store_batch(batch_id, public_header, secrets_for_ss)
        
        # 验证 Header 包含 3 个承诺
        assert len(public_header["C_data_list"]) == 3, "应有 3 个数据承诺"
        
        # DC 查询每一列
        t_challenge = [group.init(ZR, 1) for _ in range(n)]
        f_current = do.get_global_pk()["f_current"]
        
        for col_idx in range(3):
            x_result, pi_audit, pi_non = ss.generate_dc_data_proof(
                batch_id, t_challenge, f_current, column_index=col_idx
            )
            is_valid = verifier.verify_dc_query(
                public_header, t_challenge, x_result, pi_audit, pi_non, column_index=col_idx
            )
            assert is_valid, f"列 {col_idx} 验证应通过"
            print(f"✅ 列 {col_idx} 验证成功")
        
        print("✅ 测试通过：多列数据 DC 查询验证成功")
    
    def test_multi_column_da(self, setup_system):
        """测试多列数据 DA 审计"""
        sys = setup_system
        do = sys['do']
        ss = sys['ss']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']
        
        # 创建 2 列数据
        col1 = [group.init(ZR, 100 + i) for i in range(n)]
        col2 = [group.init(ZR, 200 + i) for i in range(n)]
        m_matrix = [col1, col2]
        t_vector = [group.init(ZR, i + 1) for i in range(n)]
        
        batch_id, public_header, secrets_for_ss = do.create_batch(m_matrix, t_vector)
        ss.store_batch(batch_id, public_header, secrets_for_ss)
        
        # DA 审计每一列
        f_current = do.get_global_pk()["f_current"]
        
        for col_idx in range(2):
            x_result_random, pi_audit_zk, t_challenge_zk, pi_non = ss.generate_da_audit_proof(
                batch_id, f_current, column_index=col_idx
            )
            is_valid = verifier.verify_da_audit(
                public_header, n, x_result_random, pi_audit_zk, t_challenge_zk, pi_non, column_index=col_idx
            )
            assert is_valid, f"列 {col_idx} DA 审计应通过"
            print(f"✅ 列 {col_idx} DA 审计成功")
        
        print("✅ 测试通过：多列数据 DA 审计验证成功")

    def test_shared_signature(self, setup_system):
        """测试多列共享同一个签名"""
        sys = setup_system
        do = sys['do']
        group = sys['group']
        n = sys['n']

        # 创建 3 列数据
        m_matrix = [
            [group.init(ZR, i + 10) for i in range(n)],
            [group.init(ZR, i + 20) for i in range(n)],
            [group.init(ZR, i + 30) for i in range(n)]
        ]
        t_vector = [group.init(ZR, i + 1) for i in range(n)]

        batch_id, public_header, secrets_for_ss = do.create_batch(m_matrix, t_vector)

        # 验证只有一个签名
        assert "sigma" in public_header, "应包含签名"
        assert len(public_header["C_data_list"]) == 3, "应有 3 个数据承诺"

        # 签名应绑定所有承诺
        import vds_utils
        vk_sig = do.get_global_pk()["vk_sig"]
        is_valid = vds_utils.verify_batch_signature(
            vk_sig,
            public_header["C_data_list"],
            public_header["C_time"],
            public_header["sigma"]
        )
        assert is_valid, "签名应绑定所有承诺"
        print("✅ 测试通过：多列共享同一个签名")

    def test_column_index_out_of_range(self, setup_system):
        """测试列索引越界"""
        sys = setup_system
        do = sys['do']
        ss = sys['ss']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']

        # 创建 2 列数据
        m_matrix = [
            [group.init(ZR, i + 10) for i in range(n)],
            [group.init(ZR, i + 20) for i in range(n)]
        ]
        t_vector = [group.init(ZR, i + 1) for i in range(n)]

        batch_id, public_header, secrets_for_ss = do.create_batch(m_matrix, t_vector)
        ss.store_batch(batch_id, public_header, secrets_for_ss)

        # 尝试访问不存在的列
        t_challenge = [group.init(ZR, 1) for _ in range(n)]
        f_current = do.get_global_pk()["f_current"]

        # 测试 SS 端越界检查
        with pytest.raises(ValueError, match="out of range"):
            ss.generate_dc_data_proof(batch_id, t_challenge, f_current, column_index=2)

        # 测试 Verifier 端越界检查
        x_result, pi_audit, pi_non = ss.generate_dc_data_proof(
            batch_id, t_challenge, f_current, column_index=0
        )
        is_valid = verifier.verify_dc_query(
            public_header, t_challenge, x_result, pi_audit, pi_non, column_index=2
        )
        assert not is_valid, "越界列索引应验证失败"

        print("✅ 测试通过：列索引越界检查正常")

