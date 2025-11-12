"""
Storage Server (SS) Implementation
===================================

The Storage Server is an untrusted but computationally powerful entity that:
1. Stores all secrets (data vectors, time vectors, randomness)
2. Generates all proofs on demand (VC proofs + accumulator proofs)
3. Serves Data Consumers (DC) with interactive proofs
4. Serves Data Auditors (DA) with non-interactive ZK proofs

Key Responsibilities:
---------------------
- Heavy computation: Generate all proofs
- Storage: Store all batches and secrets
- Proof generation: VC proofs (Libert 2024) + Accumulator proofs (Krupp 2016)
- Dual service: Interactive (DC) and non-interactive (DA) proofs

Security Model:
---------------
- SS is untrusted (may try to cheat)
- SS cannot forge proofs without knowing the secrets
- SS must use the current f_current to generate valid accumulator proofs
- Verifiers will detect any tampering or use of revoked batches
"""

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2
from typing import Dict, List, Tuple
from vc_smallness.proofs import prove_point_open, prove_agg_open, prove_range_proof
from vc_smallness.fs_oracles import H_t
from vds_accumulator import Accumulator
import vds_utils


class StorageServer:
    """
    Storage Server (SS) - Stores secrets and generates proofs.
    
    The SS is an untrusted but powerful entity that handles all
    heavy computation (proof generation) for the VDS scheme.
    """
    
    def __init__(self, crs: dict, initial_server_acc_keys: Tuple):
        """
        Initialize the Storage Server.

        Parameters
        ----------
        crs : dict
            The Common Reference String from keygen_crs()
        initial_server_acc_keys : Tuple
            Initial accumulator server keys (g,) from DO

        Notes
        -----
        The SS stores:
        1. CRS (public)
        2. Accumulator server keys (for proof generation)
        3. All batch data (secrets)
        4. Revoked items list X (for accumulator proofs)
        """
        self.crs = crs
        self.group = crs['group']
        self.storage = {}  # batch_id -> (public_header, secrets_for_ss)

        # Accumulator for non-membership proofs
        self.accumulator = Accumulator(self.group)
        self.server_acc_keys = initial_server_acc_keys  # (g, g^s, ...)

        # Track revoked items (blacklist)
        self.revoked_items = []  # List[bytes] - serialized signatures
    
    def add_server_key(self, g_s_q_new: G1):
        """
        Add a new server key after DO revokes a batch.

        Parameters
        ----------
        g_s_q_new : G1
            The new server key g^{s^q}

        Notes
        -----
        DO calls this after each revocation to update SS's server keys.
        This allows SS to generate non-membership proofs for the updated blacklist.
        """
        self.server_acc_keys += (g_s_q_new,)

    def add_revoked_item(self, sigma_bytes: bytes):
        """
        Add a revoked signature to the blacklist.

        Parameters
        ----------
        sigma_bytes : bytes
            Serialized signature of the revoked batch

        Notes
        -----
        DO calls this after revoking a batch.
        SS needs this list to generate non-membership proofs.
        """
        self.revoked_items.append(sigma_bytes)
    
    def store_batch(self, batch_id: str, public_header: Dict, secrets_for_ss: Dict):
        """
        Store a batch.

        Parameters
        ----------
        batch_id : str
            Unique identifier for the batch
        public_header : dict
            Public information (C_data, C_time, sigma)
        secrets_for_ss : dict
            Secret information (m, t, gamma_data, gamma_time)

        Notes
        -----
        SS stores both public and secret information.
        Public info is used for proof generation.
        Secret info is used to compute the proofs.
        """
        self.storage[batch_id] = (public_header, secrets_for_ss)

    def update_batch(self, old_batch_id: str, g_s_q_new: G1, sigma_bytes: bytes,
                     new_batch_id: str, new_public_header: Dict, new_secrets_for_ss: Dict):
        """
        更新批次：删除旧批次，存储新批次，更新累加器状态（原子操作）。

        这是一个便捷方法，封装了完整的批次更新流程。

        Parameters
        ----------
        old_batch_id : str
            旧批次的 ID（将被删除）
        g_s_q_new : G1
            新的服务器密钥（来自 DO）
        sigma_bytes : bytes
            被撤销的签名（序列化）
        new_batch_id : str
            新批次的 ID
        new_public_header : dict
            新批次的公开头部
        new_secrets_for_ss : dict
            新批次的秘密数据

        Notes
        -----
        工作流程：
        1. 添加新的服务器密钥（用于累加器证明）
        2. 将旧签名加入黑名单
        3. 删除旧批次数据（可选，节省存储空间）
        4. 存储新批次数据

        安全性：
        - 旧批次的签名被加入黑名单，无法再生成有效证明
        - 新批次使用新的签名，独立于旧批次

        存储优化：
        - 删除旧批次数据可以节省存储空间
        - 如果需要保留历史记录，可以注释掉删除步骤

        Example
        -------
        >>> # 配合 DO.update_batch 使用
        >>> g_s_q, new_pk, sigma_bytes, new_id, new_header, new_secrets = \\
        ...     do.update_batch(old_header, updated_data, updated_time)
        >>> ss.update_batch(old_batch_id, g_s_q, sigma_bytes, new_id, new_header, new_secrets)
        """
        # 步骤 1: 更新累加器密钥
        self.add_server_key(g_s_q_new)

        # 步骤 2: 将旧签名加入黑名单
        self.add_revoked_item(sigma_bytes)

        # 步骤 3: 删除旧批次（可选，节省存储）
        if old_batch_id in self.storage:
            del self.storage[old_batch_id]

        # 步骤 4: 存储新批次
        self.store_batch(new_batch_id, new_public_header, new_secrets_for_ss)
    
    def generate_dc_data_proof(self, batch_id: str, t_challenge_vector: List[ZR],
                               f_current: G1, column_index: int = 0) -> Tuple[ZR, G1, Tuple]:
        """
        为 DC 生成交互式查询证明（支持多列）。

        Parameters
        ----------
        batch_id : str
            批次 ID
        t_challenge_vector : List[ZR]
            DC 提供的挑战权重
        f_current : G1
            当前累加器值
        column_index : int
            目标列索引（默认为 0）

        Returns
        -------
        x_result : ZR
            标量结果 ∑ m_i * t_i
        pi_audit : G1
            VC 证明
        pi_non : Tuple[G1, ZR]
            累加器非成员证明

        Notes
        -----
        从 m_matrix[column_index] 和 gamma_data_list[column_index] 提取数据生成证明。
        签名 σ 对所有列共享，因此累加器证明不变。
        """
        # 获取批次数据
        if batch_id not in self.storage:
            raise ValueError(f"Batch {batch_id} not found")

        header, secrets = self.storage[batch_id]
        m_matrix = secrets["m_matrix"]
        gamma_data_list = secrets["gamma_data_list"]
        C_data_list = header["C_data_list"]
        sigma = header["sigma"]

        # 验证列索引
        if column_index < 0 or column_index >= len(m_matrix):
            raise ValueError(f"column_index {column_index} out of range [0, {len(m_matrix)})")

        # 提取目标列的数据
        m = m_matrix[column_index]
        gamma_data = gamma_data_list[column_index]
        C_data = C_data_list[column_index]

        n = len(m)
        if len(t_challenge_vector) != n:
            raise ValueError(f"Challenge vector length {len(t_challenge_vector)} != n={n}")

        # 计算标量结果：x = ∑ m_i * t_i
        x_result = self.group.init(ZR, 0)
        for m_i, t_i in zip(m, t_challenge_vector):
            x_result += m_i * t_i

        # 生成 VC 证明
        pis = []
        for i in range(1, n + 1):
            pi_i = prove_point_open(C_data, m, gamma_data, i, self.crs)
            pis.append(pi_i)

        # 聚合证明：π_S = ∏ π_i^{t_i}
        pi_audit = self.group.init(G1, 1)
        for pi_i, t_i in zip(pis, t_challenge_vector):
            pi_audit *= pi_i ** t_i

        # 生成累加器非成员证明（签名对所有列共享）
        sigma_bytes = vds_utils.serialize_signature(sigma)
        try:
            pi_non = self.accumulator.prove_non_membership(
                self.server_acc_keys, f_current, sigma_bytes, X=self.revoked_items
            )
        except ValueError as e:
            if "in the blacklist" in str(e):
                # 批次已撤销，返回虚拟证明
                w_dummy = self.group.init(G1, 1)
                u_dummy = self.group.init(ZR, 0)
                pi_non = (w_dummy, u_dummy)
            else:
                raise

        return (x_result, pi_audit, pi_non)
    
    def generate_da_audit_proof(self, batch_id: str, f_current: G1, column_index: int = 0) -> Tuple[ZR, G1, List[ZR], Tuple]:
        """
        为 DA 生成非交互式 ZK 审计证明（支持多列）。

        Parameters
        ----------
        batch_id : str
            批次 ID
        f_current : G1
            当前累加器值
        column_index : int
            目标列索引（默认为 0）

        Returns
        -------
        x_result_random : ZR
            使用随机挑战的标量结果
        pi_audit_zk : G1
            VC 证明
        t_challenge_zk : List[ZR]
            Fiat-Shamir 挑战
        pi_non : Tuple[G1, ZR]
            累加器非成员证明

        Notes
        -----
        使用 Fiat-Shamir 变换生成确定性挑战，防止 SS 选择有利的挑战。
        """
        # 获取批次数据
        if batch_id not in self.storage:
            raise ValueError(f"Batch {batch_id} not found")

        header, secrets = self.storage[batch_id]
        m_matrix = secrets["m_matrix"]
        gamma_data_list = secrets["gamma_data_list"]
        C_data_list = header["C_data_list"]
        sigma = header["sigma"]

        # 验证列索引
        if column_index < 0 or column_index >= len(m_matrix):
            raise ValueError(f"column_index {column_index} out of range [0, {len(m_matrix)})")

        # 提取目标列的数据
        m = m_matrix[column_index]
        gamma_data = gamma_data_list[column_index]
        C_data = C_data_list[column_index]
        n = len(m)

        # 生成 Fiat-Shamir 挑战
        C_hat_dummy = self.group.init(G2, 1)
        C_y_dummy = self.group.init(G1, 1)
        t_challenge_zk = H_t(C_data, C_hat_dummy, C_y_dummy, n, self.group, b"VDS-DA-AUDIT-ZK")

        # 计算标量结果：x = ∑ m_i * t_zk_i
        x_result_random = self.group.init(ZR, 0)
        for m_i, t_i in zip(m, t_challenge_zk):
            x_result_random += m_i * t_i

        # 生成 VC 证明
        pis = []
        for i in range(1, n + 1):
            pi_i = prove_point_open(C_data, m, gamma_data, i, self.crs)
            pis.append(pi_i)

        # 聚合证明
        pi_audit_zk = self.group.init(G1, 1)
        for pi_i, t_i in zip(pis, t_challenge_zk):
            pi_audit_zk *= pi_i ** t_i

        # 生成累加器非成员证明
        sigma_bytes = vds_utils.serialize_signature(sigma)
        try:
            pi_non = self.accumulator.prove_non_membership(
                self.server_acc_keys, f_current, sigma_bytes, X=self.revoked_items
            )
        except ValueError as e:
            if "in the blacklist" in str(e):
                # 批次已撤销
                w_dummy = self.group.init(G1, 1)
                u_dummy = self.group.init(ZR, 0)
                pi_non = (w_dummy, u_dummy)
            else:
                raise

        return (x_result_random, pi_audit_zk, t_challenge_zk, pi_non)

    def generate_time_range_proofs(self, batch_id: str, f_current: G2) -> List[Dict]:
        """
        Generate time range proofs for all time values in a batch.

        This demonstrates the time range proof functionality by generating
        a range proof for each time value in the batch.

        Parameters
        ----------
        batch_id : str
            The batch identifier
        f_current : G2
            The current accumulator value

        Returns
        -------
        List[Dict]
            List of time range proofs, one for each time value
            Each dict contains: {'t_value': ZR, 'range_proof': dict, 'pi_non': tuple}
        """
        if batch_id not in self.storage:
            raise ValueError(f"Batch {batch_id} not found")

        header, secrets = self.storage[batch_id]
        t = secrets["t"]
        sigma = header["sigma"]

        # Generate accumulator non-membership proof (shared for all time proofs)
        sigma_bytes = vds_utils.serialize_signature(sigma)
        try:
            pi_non = self.accumulator.prove_non_membership(
                self.server_acc_keys, f_current, sigma_bytes, X=self.revoked_items
            )
        except ValueError as e:
            if "in the blacklist" in str(e):
                # Item is revoked, return dummy proof
                w_dummy = self.group.init(G1, 1)
                u_dummy = self.group.init(ZR, 0)
                pi_non = (w_dummy, u_dummy)
            else:
                raise

        # Generate range proof for each time value
        time_proofs = []
        for t_i in t:
            # Generate range proof for t_i ∈ [0, 2^l - 1]
            # We use l=32 bits as a reasonable range for timestamps
            l = 32
            range_proof = prove_range_proof(t_i, l, self.crs)

            time_proofs.append({
                't_value': t_i,
                'range_proof': range_proof,
                'pi_non': pi_non
            })

        return time_proofs

