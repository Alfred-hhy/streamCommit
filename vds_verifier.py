"""
Verifier Implementation (DC and DA)
====================================

This module implements two types of verifiers:
1. Data Consumer (DC): Verifies specific inner products (interactive)
2. Data Auditor (DA): Verifies zero-knowledge anti-tampering (non-interactive)

Both verifiers perform the same core checks:
1. Signature verification (binding check)
2. Accumulator non-membership verification (revocation check)
3. VC proof verification (correctness check)

Key Differences:
----------------
- DC: Interactive (DC provides challenge t)
- DA: Non-interactive (challenge from Fiat-Shamir)

Security Model:
---------------
- Verifiers must have the latest global_pk from DO
- Verifiers are assumed to be honest (they want correct results)
- Verifiers detect any tampering or use of revoked batches
"""

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2
from typing import Dict, List, Tuple
from vc_smallness.verify import verify_1, verify_range_proof
from vc_smallness.fs_oracles import H_t
from vds_accumulator import Accumulator
import vds_utils


class Verifier:
    """
    Verifier for both DC and DA workflows.
    
    The verifier checks:
    1. Signature binding (prevents mix-and-match attacks)
    2. Accumulator non-membership (prevents use of revoked batches)
    3. VC proof correctness (prevents tampering with data)
    """
    
    def __init__(self, crs: dict, initial_global_pk: Dict, group: PairingGroup):
        """
        Initialize the Verifier.
        
        Parameters
        ----------
        crs : dict
            The Common Reference String from keygen_crs()
        initial_global_pk : dict
            The initial global public key from DO
        group : PairingGroup
            The pairing group
        
        Notes
        -----
        The verifier must:
        1. Obtain the CRS (public, from setup)
        2. Obtain the latest global_pk (from DO, via trusted channel)
        3. Update global_pk whenever DO publishes a new one
        """
        self.crs = crs
        self.group = group
        self.current_global_pk = initial_global_pk
        
        # Accumulator for verification
        self.accumulator = Accumulator(group)
    
    def update_global_pk(self, new_global_pk: Dict):
        """
        Update the global public key.
        
        Parameters
        ----------
        new_global_pk : dict
            The new global_pk from DO
        
        Notes
        -----
        This MUST be called whenever DO publishes a new global_pk
        (i.e., after each revocation).
        
        Failure to update will result in:
        - False negatives (rejecting valid non-revoked batches)
        - False positives (accepting revoked batches)
        """
        self.current_global_pk = new_global_pk
    
    def _verify_precheck(self, public_header: Dict, pi_non: Tuple) -> Tuple[bool, List[G1]]:
        """
        执行预验证检查（签名 + 黑名单）。

        Parameters
        ----------
        public_header : dict
            公开头部（C_data_list, C_time, sigma）
        pi_non : Tuple[G1, ZR]
            累加器非成员证明

        Returns
        -------
        is_valid : bool
            预检查通过返回 True
        C_data_list : List[G1]
            数据承诺列表（用于后续验证）

        Notes
        -----
        关键安全检查：
        1. 验证签名绑定（防止混合攻击）
        2. 验证非黑名单成员（防止回滚攻击）
        """
        try:
            # 提取全局公钥组件
            vk_sig = self.current_global_pk["vk_sig"]
            acc_pk = self.current_global_pk["acc_pk"]
            f_current = self.current_global_pk["f_current"]

            # 提取公开头部组件
            C_data_list = public_header["C_data_list"]
            C_time = public_header["C_time"]
            sigma = public_header["sigma"]

            # 检查 1：验证签名绑定
            if not vds_utils.verify_batch_signature(vk_sig, C_data_list, C_time, sigma):
                print("❌ 验证失败：签名绑定无效")
                print("   可能存在篡改或混合攻击")
                return False, None

            # 检查 2：验证非黑名单成员
            sigma_bytes = vds_utils.serialize_signature(sigma)
            if not self.accumulator.verify_non_membership(acc_pk, f_current, sigma_bytes, pi_non):
                print("❌ 验证失败：批次已被撤销")
                return False, None

            # 两项检查都通过
            return True, C_data_list

        except Exception as e:
            print(f"❌ 预检查错误: {e}")
            import traceback
            traceback.print_exc()
            return False, None
    
    def verify_dc_query(self, public_header: Dict, t_challenge_vector: List[ZR],
                       x_result: ZR, pi_audit: G1, pi_non: Tuple, column_index: int = 0) -> bool:
        """
        验证 DC 查询（支持多列）。

        Parameters
        ----------
        public_header : dict
            公开头部（C_data_list, C_time, sigma）
        t_challenge_vector : List[ZR]
            DC 提供的挑战权重
        x_result : ZR
            声称的结果 ∑ m_i * t_i
        pi_audit : G1
            VC 证明
        pi_non : Tuple[G1, ZR]
            累加器非成员证明
        column_index : int
            目标列索引（默认为 0）

        Returns
        -------
        bool
            验证通过返回 True

        Notes
        -----
        验证步骤：
        1. 预检查：签名 + 黑名单
        2. VC 验证：使用目标列的承诺
        """
        # 步骤 1 & 2：验证签名和黑名单
        is_valid_precheck, C_data_list = self._verify_precheck(public_header, pi_non)
        if not is_valid_precheck:
            return False

        # 验证列索引
        if column_index < 0 or column_index >= len(C_data_list):
            print(f"❌ 列索引 {column_index} 超出范围 [0, {len(C_data_list)})")
            return False

        # 提取目标列的承诺
        C_data = C_data_list[column_index]

        # 步骤 3：验证 VC 证明
        # e(C, ∏ ĝ_{n+1-i}^{t_i}) = e(pi_audit, ĝ) · e(g_1, ĝ_n)^{x_result}
        n = self.crs['n']
        g_hat = self.crs['g_hat']
        g_hat_list = self.crs['g_hat_list']
        g_list = self.crs['g_list']

        # 计算 LHS: e(C, ∏ ĝ_{n+1-i}^{t_i})
        g_hat_prod = self.group.init(G2, 1)
        for i in range(1, n + 1):
            idx = n + 1 - i
            if idx in g_hat_list:
                g_hat_prod *= g_hat_list[idx] ** t_challenge_vector[i - 1]

        lhs = self.group.pair_prod(C_data, g_hat_prod)

        # 计算 RHS: e(pi_audit, ĝ) · e(g_1, ĝ_n)^{x_result}
        rhs_1 = self.group.pair_prod(pi_audit, g_hat)
        rhs_2 = self.group.pair_prod(g_list[1], g_hat_list[n]) ** x_result
        rhs = rhs_1 * rhs_2

        # 检查等式
        is_vc_valid = (lhs == rhs)

        if not is_vc_valid:
            print("❌ VC 验证失败：证明与承诺不匹配")
            print("   可能存在数据篡改或证明错误")

        return is_vc_valid
    
    def verify_da_audit(self, public_header: Dict, n: int, x_result_random: ZR,
                       pi_audit_zk: G1, t_challenge_zk_provided: List[ZR],
                       pi_non: Tuple, column_index: int = 0) -> bool:
        """
        验证 DA 审计（支持多列）。

        Parameters
        ----------
        public_header : dict
            公开头部（C_data_list, C_time, sigma）
        n : int
            向量维度
        x_result_random : ZR
            使用随机挑战的声称结果
        pi_audit_zk : G1
            VC 证明
        t_challenge_zk_provided : List[ZR]
            SS 提供的 Fiat-Shamir 挑战
        pi_non : Tuple[G1, ZR]
            累加器非成员证明
        column_index : int
            目标列索引（默认为 0）

        Returns
        -------
        bool
            验证通过返回 True

        Notes
        -----
        验证步骤：
        1. 预检查：签名 + 黑名单
        2. 重新计算 Fiat-Shamir 挑战（确保 SS 未作弊）
        3. VC 验证
        """
        # 步骤 1 & 2：验证签名和黑名单
        is_valid_precheck, C_data_list = self._verify_precheck(public_header, pi_non)
        if not is_valid_precheck:
            return False

        # 验证列索引
        if column_index < 0 or column_index >= len(C_data_list):
            print(f"❌ 列索引 {column_index} 超出范围 [0, {len(C_data_list)})")
            return False

        # 提取目标列的承诺
        C_data = C_data_list[column_index]

        # 步骤 3：重新计算 Fiat-Shamir 挑战
        C_hat_dummy = self.group.init(G2, 1)
        C_y_dummy = self.group.init(G1, 1)
        t_challenge_zk_local = H_t(C_data, C_hat_dummy, C_y_dummy, n, self.group, b"VDS-DA-AUDIT-ZK")

        # 检查挑战一致性
        if len(t_challenge_zk_local) != len(t_challenge_zk_provided):
            print("❌ 验证失败：挑战长度不匹配")
            return False

        for i, (t_local, t_provided) in enumerate(zip(t_challenge_zk_local, t_challenge_zk_provided)):
            if t_local != t_provided:
                print(f"❌ 验证失败：ZK 挑战在位置 {i} 不匹配")
                print("   SS 可能尝试使用不同的挑战")
                return False

        # 步骤 4：验证 VC 证明
        g_hat = self.crs['g_hat']
        g_hat_list = self.crs['g_hat_list']
        g_list = self.crs['g_list']

        # 计算 LHS: e(C, ∏ ĝ_{n+1-i}^{t_i})
        g_hat_prod = self.group.init(G2, 1)
        for i in range(1, n + 1):
            idx = n + 1 - i
            if idx in g_hat_list:
                g_hat_prod *= g_hat_list[idx] ** t_challenge_zk_local[i - 1]

        lhs = self.group.pair_prod(C_data, g_hat_prod)

        # 计算 RHS: e(pi_audit_zk, ĝ) · e(g_1, ĝ_n)^{x_result_random}
        rhs_1 = self.group.pair_prod(pi_audit_zk, g_hat)
        rhs_2 = self.group.pair_prod(g_list[1], g_hat_list[n]) ** x_result_random
        rhs = rhs_1 * rhs_2

        # 检查等式
        is_vc_valid = (lhs == rhs)

        if not is_vc_valid:
            print("❌ VC 验证失败：证明与承诺不匹配")
            print("   可能存在数据篡改或证明错误")

        return is_vc_valid

    def verify_time_range_proof(self, public_header: Dict, proof_data: Dict,
                                f_current: G2) -> bool:
        """
        Verify a time range proof.

        This verifies that a time value is within a valid range [0, 2^l - 1].

        Parameters
        ----------
        public_header : dict
            The public header from the batch
        proof_data : dict
            The proof data containing:
            - 't_value': The time value
            - 'range_proof': The range proof
            - 'pi_non': The accumulator non-membership proof
        f_current : G2
            The current accumulator value

        Returns
        -------
        bool
            True if the proof is valid, False otherwise
        """
        # Step 1 & 2: Verify signature and blacklist
        is_valid_precheck, _ = self._verify_precheck(public_header, proof_data['pi_non'])
        if not is_valid_precheck:
            return False

        # Step 3: Verify range proof
        range_proof = proof_data['range_proof']
        l = range_proof['l']

        is_range_valid = verify_range_proof(range_proof, l, self.crs)

        if not is_range_valid:
            print("❌ Range proof verification failed.")
            print(f"   Time value {proof_data['t_value']} is not in range [0, 2^{l} - 1]")

        return is_range_valid

