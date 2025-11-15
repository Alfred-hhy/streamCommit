"""
分布式VDS端到端测试
测试DC查询和DA审计的完整流程
"""

import pytest
import time
from distributed.client import DOClient, SSClient, VerifierClient


class TestDistributedE2E:
    """端到端测试类"""

    @classmethod
    def setup_class(cls):
        """初始化分布式系统"""
        print("\n=== 初始化分布式系统 ===")

        # 创建客户端
        cls.do_client = DOClient()
        cls.ss_client = SSClient()
        cls.verifier_client = VerifierClient()

        # 等待服务器启动
        time.sleep(1)

        # 初始化DO
        print("初始化DO...")
        result = cls.do_client.init(n=16)
        assert result['success']
        cls.crs = result['crs']
        cls.global_pk = result['global_pk']
        cls.server_acc_keys = result['server_acc_keys']

        # 初始化SS
        print("初始化SS...")
        result = cls.ss_client.init(cls.crs, cls.server_acc_keys)
        assert result['success']

        # 初始化Verifier
        print("初始化Verifier...")
        result = cls.verifier_client.init(cls.crs, cls.global_pk)
        assert result['success']

        print("系统初始化完成\n")

    def test_dc_query_single_column(self):
        """测试DC查询（单列数据）"""
        print("\n=== 测试DC查询（单列） ===")

        # 1. DO创建批次
        print("1. DO创建批次...")
        data_vectors = [[10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160]]
        time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

        result = self.do_client.create_batch(data_vectors, time_vector)
        assert result['success']
        batch_id = result['batch_id']
        public_header = result['public_header']
        secrets = result['secrets_for_ss']
        print(f"批次ID: {batch_id}")

        # 2. SS存储批次
        print("2. SS存储批次...")
        result = self.ss_client.store_batch(batch_id, public_header, secrets)
        assert result['success']

        # 3. DC提供挑战并请求证明
        print("3. DC生成挑战并请求证明...")
        t_challenge = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        result = self.ss_client.generate_dc_proof(
            batch_id, t_challenge, self.global_pk['f_current'], column_index=0
        )
        assert result['success']
        x_result = result['x_result']
        pi_audit = result['pi_audit']
        pi_non = result['pi_non']
        print(f"返回结果: {x_result}")

        # 4. DC验证证明
        print("4. DC验证证明...")
        result = self.verifier_client.verify_dc_query(
            public_header, t_challenge, x_result, pi_audit, pi_non, column_index=0
        )
        assert result['success']
        assert result['is_valid'], "DC查询验证失败"
        print("验证通过！\n")

    def test_dc_query_multi_column(self):
        """测试DC查询（多列数据）"""
        print("\n=== 测试DC查询（多列） ===")

        # 1. DO创建多列批次
        print("1. DO创建多列批次...")
        data_vectors = [
            [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160],  # 温度
            [50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125]   # 湿度
        ]
        time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

        result = self.do_client.create_batch(data_vectors, time_vector)
        assert result['success']
        batch_id = result['batch_id']
        public_header = result['public_header']
        secrets = result['secrets_for_ss']
        print(f"批次ID: {batch_id}")

        # 2. SS存储批次
        print("2. SS存储批次...")
        result = self.ss_client.store_batch(batch_id, public_header, secrets)
        assert result['success']

        # 3. 查询第一列（温度）
        print("3. 查询第一列（温度）...")
        t_challenge = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        result = self.ss_client.generate_dc_proof(
            batch_id, t_challenge, self.global_pk['f_current'], column_index=0
        )
        assert result['success']
        x_result = result['x_result']
        pi_audit = result['pi_audit']
        pi_non = result['pi_non']
        print(f"温度列结果: {x_result}")

        # 4. 验证第一列
        print("4. 验证第一列...")
        result = self.verifier_client.verify_dc_query(
            public_header, t_challenge, x_result, pi_audit, pi_non, column_index=0
        )
        assert result['success']
        assert result['is_valid'], "第一列验证失败"
        print("第一列验证通过！")

        # 5. 查询第二列（湿度）
        print("5. 查询第二列（湿度）...")
        result = self.ss_client.generate_dc_proof(
            batch_id, t_challenge, self.global_pk['f_current'], column_index=1
        )
        assert result['success']
        x_result = result['x_result']
        pi_audit = result['pi_audit']
        pi_non = result['pi_non']
        print(f"湿度列结果: {x_result}")

        # 6. 验证第二列
        print("6. 验证第二列...")
        result = self.verifier_client.verify_dc_query(
            public_header, t_challenge, x_result, pi_audit, pi_non, column_index=1
        )
        assert result['success']
        assert result['is_valid'], "第二列验证失败"
        print("第二列验证通过！\n")

    def test_da_audit(self):
        """测试DA审计"""
        print("\n=== 测试DA审计 ===")

        # 1. DO创建批次
        print("1. DO创建批次...")
        data_vectors = [[15, 25, 35, 45, 55, 65, 75, 85, 95, 105, 115, 125, 135, 145, 155, 165]]
        time_vector = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

        result = self.do_client.create_batch(data_vectors, time_vector)
        assert result['success']
        batch_id = result['batch_id']
        public_header = result['public_header']
        secrets = result['secrets_for_ss']
        print(f"批次ID: {batch_id}")

        # 2. SS存储批次
        print("2. SS存储批次...")
        result = self.ss_client.store_batch(batch_id, public_header, secrets)
        assert result['success']

        # 3. DA请求审计证明
        print("3. DA请求审计证明...")
        result = self.ss_client.generate_da_proof(
            batch_id, self.global_pk['f_current'], column_index=0
        )
        assert result['success']
        x_result = result['x_result']
        pi_audit = result['pi_audit']
        t_challenge = result['t_challenge']
        pi_non = result['pi_non']
        print(f"返回结果: {x_result}")

        # 4. DA验证证明
        print("4. DA验证证明...")
        result = self.verifier_client.verify_da_audit(
            public_header, 16, x_result, pi_audit, t_challenge, pi_non, column_index=0
        )
        assert result['success']
        assert result['is_valid'], "DA审计验证失败"
        print("验证通过！\n")

    def test_batch_revocation(self):
        """测试批次撤销"""
        print("\n=== 测试批次撤销 ===")

        # 1. DO创建批次
        print("1. DO创建批次...")
        data_vectors = [[5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]]
        time_vector = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

        result = self.do_client.create_batch(data_vectors, time_vector)
        assert result['success']
        batch_id = result['batch_id']
        public_header = result['public_header']
        secrets = result['secrets_for_ss']
        sigma = public_header['sigma']
        print(f"批次ID: {batch_id}")

        # 2. SS存储批次
        print("2. SS存储批次...")
        result = self.ss_client.store_batch(batch_id, public_header, secrets)
        assert result['success']

        # 3. DO撤销批次
        print("3. DO撤销批次...")
        result = self.do_client.revoke_batch(sigma)
        assert result['success']
        g_s_q_new = result['g_s_q_new']
        new_global_pk = result['new_global_pk']
        sigma_bytes = result['sigma_bytes']

        # 4. SS更新累加器状态
        print("4. SS更新累加器状态...")
        result = self.ss_client.add_server_key(g_s_q_new)
        assert result['success']
        result = self.ss_client.add_revoked_item(sigma_bytes)
        assert result['success']

        # 5. Verifier更新全局公钥
        print("5. Verifier更新全局公钥...")
        result = self.verifier_client.update_global_pk(new_global_pk)
        assert result['success']

        # 6. 尝试使用已撤销批次生成证明
        print("6. 尝试查询已撤销的批次...")
        t_challenge = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        result = self.ss_client.generate_dc_proof(
            batch_id, t_challenge, new_global_pk['f_current'], column_index=0
        )
        assert result['success']
        x_result = result['x_result']
        pi_audit = result['pi_audit']
        pi_non = result['pi_non']

        # 7. 验证应该失败
        print("7. 验证应该失败（批次已撤销）...")
        result = self.verifier_client.verify_dc_query(
            public_header, t_challenge, x_result, pi_audit, pi_non, column_index=0
        )
        assert result['success']
        assert not result['is_valid'], "已撤销批次验证应该失败"
        print("验证失败（预期行为）！\n")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
