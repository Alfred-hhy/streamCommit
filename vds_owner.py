"""
Data Owner (DO) Implementation
===============================

The Data Owner is a resource-constrained entity that:
1. Creates batches by committing to data and time vectors
2. Signs the commitments to bind them together
3. Offloads secrets to the Storage Server
4. Manages the revocation blacklist (accumulator)
5. Publishes a dynamic public key that includes the current blacklist state

Key Responsibilities:
---------------------
- Lightweight operations: Commit + Sign
- Secret management: Generate and offload secrets to SS
- Revocation: Update accumulator and publish new public key
- Key distribution: Publish global_pk for verifiers

Security Model:
---------------
- DO is trusted to create correct commitments
- DO is trusted to manage the accumulator correctly
- DO's signing key must be kept secret
- DO's accumulator secret key must be kept secret
"""

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2
from typing import Dict, List, Tuple
from vc_smallness.commit import commit_G, commit_Ghat
from vds_accumulator import Accumulator
import vds_utils


class DataOwner:
    """
    Data Owner (DO) - Creates and signs batches, manages revocation.
    
    The DO is a lightweight entity that creates commitments and manages
    the revocation blacklist. All heavy computation (proof generation)
    is offloaded to the Storage Server.
    """
    
    def __init__(self, crs: dict, group: PairingGroup):
        """
        Initialize the Data Owner.
        
        Parameters
        ----------
        crs : dict
            The Common Reference String from keygen_crs()
        group : PairingGroup
            The pairing group
        
        Notes
        -----
        This sets up:
        1. Signing keys (ECDSA)
        2. Accumulator (for revocation)
        3. Initial dynamic public key
        """
        # Store CRS and group
        self.crs = crs
        self.group = group
        
        # Generate signing keys (ECDSA, separate from pairing curve)
        self.sk_DO, self.vk_DO = vds_utils.generate_signing_keys()
        
        # Setup accumulator for revocation
        self.accumulator = Accumulator(group)
        (self.acc_sk, 
         self.acc_pk, 
         self.current_f, 
         self.server_acc_keys) = self.accumulator.setup()
        
        # Track number of revocations (for server key expansion)
        self.update_count = 0
        
        # Initialize dynamic public key
        self.global_pk = self._get_latest_global_pk()
    
    def _get_latest_global_pk(self) -> Dict:
        """
        Get the current dynamic public key.
        
        Returns
        -------
        dict
            The global public key containing:
            - vk_sig: Signature verification key (static)
            - acc_pk: Accumulator public key (static)
            - f_current: Current accumulator value (dynamic)
        
        Notes
        -----
        This public key must be published and distributed to all verifiers.
        It changes every time a batch is revoked (f_current changes).
        """
        return {
            "vk_sig": self.vk_DO,           # Static: signature verification key
            "acc_pk": self.acc_pk,          # Static: (g, ĝ, ĝ^s)
            "f_current": self.current_f     # Dynamic: current blacklist state
        }
    
    def create_batch(self, m_matrix: List[List[ZR]], t_vector: List[ZR]) -> Tuple[str, Dict, Dict]:
        """
        创建并签名新批次（支持多维数据）。

        Parameters
        ----------
        m_matrix : List[List[ZR]] 或 List[ZR]
            数据矩阵（多列）或数据向量（单列，向后兼容）
            - 多列格式：[[temp_t1, temp_t2, ...], [humid_t1, humid_t2, ...]]
            - 单列格式：[data_t1, data_t2, ...]（自动转换为 [[data_t1, data_t2, ...]]）
        t_vector : List[ZR]
            时间向量（所有列共享）

        Returns
        -------
        batch_id : str
            批次唯一标识符
        public_header : dict
            公开信息：
            - C_data_list: 数据承诺列表（每列一个）
            - C_time: 时间承诺
            - sigma: 绑定签名
        secrets_for_ss : dict
            秘密信息：
            - m_matrix: 数据矩阵
            - t: 时间向量
            - gamma_data_list: 每列的随机数列表
            - gamma_time: 时间承诺的随机数

        Notes
        -----
        多列共享同一个 C_time 和同一个签名 σ，降低存储和验证开销。
        向后兼容：如果传入单个向量，自动转换为单列矩阵。
        """
        n = self.crs['n']

        # 验证输入
        if len(t_vector) != n:
            raise ValueError(f"Time vector must have length n={n}")

        # 向后兼容：检测是否为单个向量（而非矩阵）
        # 如果第一个元素不是列表，则认为是单列向量
        if len(m_matrix) > 0 and not isinstance(m_matrix[0], list):
            # 单列向量格式，转换为矩阵格式
            if len(m_matrix) != n:
                raise ValueError(f"Data vector must have length n={n}")
            m_matrix = [m_matrix]  # 转换为单列矩阵

        # 验证矩阵格式
        if len(m_matrix) == 0:
            raise ValueError("m_matrix must contain at least one column")
        for col_idx, m_col in enumerate(m_matrix):
            if len(m_col) != n:
                raise ValueError(f"Column {col_idx} must have length n={n}")

        # 生成时间承诺（所有列共享）
        gamma_time = self.group.random(ZR)
        C_time = commit_Ghat(t_vector, gamma_time, self.crs)  # In G2

        # 为每一列生成数据承诺
        C_data_list = []
        gamma_data_list = []
        for m_col in m_matrix:
            gamma_data = self.group.random(ZR)
            C_data = commit_G(m_col, gamma_data, self.crs)  # In G1
            C_data_list.append(C_data)
            gamma_data_list.append(gamma_data)

        # 签名绑定所有承诺
        sigma = vds_utils.sign_batch(self.sk_DO, C_data_list, C_time)

        # 生成批次 ID
        import hashlib
        batch_id_bytes = vds_utils.hash_for_signing(C_data_list, C_time)
        batch_id = hashlib.sha256(batch_id_bytes).hexdigest()[:16]

        # 准备公开头部
        public_header = {
            "C_data_list": C_data_list,
            "C_time": C_time,
            "sigma": sigma
        }

        # 准备秘密数据
        secrets_for_ss = {
            "m_matrix": m_matrix,
            "t": t_vector,
            "gamma_data_list": gamma_data_list,
            "gamma_time": gamma_time
        }

        return batch_id, public_header, secrets_for_ss
    
    def revoke_batch(self, sigma_to_revoke: bytes) -> Tuple[G1, Dict, bytes]:
        """
        Revoke a batch by adding its signature to the blacklist.

        Parameters
        ----------
        sigma_to_revoke : bytes
            The signature of the batch to revoke

        Returns
        -------
        g_s_q_new : G1
            The new server key g^{s^q} (to be sent to SS)
        new_global_pk : dict
            The updated global public key (to be published)
        sigma_bytes : bytes
            Serialized signature (to be sent to SS for blacklist tracking)

        Notes
        -----
        Workflow:
        1. Add sigma to the blacklist (update f)
        2. Increment update_count
        3. Compute new server key g^{s^q}
        4. Update global_pk with new f
        5. Return new server key, new global_pk, and sigma_bytes

        Security:
        - After revocation, any proof using sigma_to_revoke will fail
        - Verifiers must use the new global_pk to detect revoked batches
        - SS must use the new server key to generate valid proofs

        Important:
        - DO must publish new_global_pk to all verifiers
        - DO must send g_s_q_new and sigma_bytes to SS
        - Verifiers must update their global_pk before verifying new proofs
        """
        # Serialize the signature for hashing
        sigma_bytes = vds_utils.serialize_signature(sigma_to_revoke)

        # Add to blacklist (update accumulator)
        self.current_f = self.accumulator.add_to_blacklist(
            self.acc_sk, self.current_f, sigma_bytes
        )

        # Increment update count
        self.update_count += 1

        # Compute new server key g^{s^q}
        self.server_acc_keys, g_s_q_new = self.accumulator.expand_server_keys(
            self.acc_sk, self.server_acc_keys, self.update_count
        )

        # Update global public key
        self.global_pk = self._get_latest_global_pk()

        # Return new server key, new global_pk, and sigma_bytes
        return g_s_q_new, self.global_pk, sigma_bytes

    def update_batch(self, old_batch_header: Dict, new_m_matrix: List[List[ZR]],
                     new_t_vector: List[ZR]) -> Tuple[G1, Dict, bytes, str, Dict, Dict]:
        """
        更新批次：撤销旧批次并创建新批次（原子操作）。

        这是一个便捷方法，封装了"撤销 + 创建"的完整流程。

        Parameters
        ----------
        old_batch_header : dict
            旧批次的公开头部（包含 sigma）
        new_m_matrix : List[List[ZR]] 或 List[ZR]
            新的数据矩阵（多列）或数据向量（单列）
        new_t_vector : List[ZR]
            新的时间向量

        Returns
        -------
        g_s_q_new : G1
            新的服务器密钥（用于累加器）
        new_global_pk : dict
            更新后的全局公钥
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
        1. 撤销旧批次（将其签名加入黑名单）
        2. 创建新批次（包含更新后的数据）
        3. 返回所有必要的信息供 SS 和 Verifier 更新

        使用场景：
        - 数据错误需要更正
        - 数据过期需要刷新
        - 数据内容需要修改

        安全性：
        - 旧批次立即失效，无法再通过验证
        - 新批次使用新的签名，独立于旧批次
        - 累加器确保旧批次不能被回滚

        Example
        -------
        >>> # 更新批次
        >>> g_s_q, new_pk, sigma_bytes, new_id, new_header, new_secrets = \\
        ...     do.update_batch(old_header, updated_data, updated_time)
        >>>
        >>> # 更新 SS
        >>> ss.update_batch(old_batch_id, g_s_q, sigma_bytes, new_id, new_header, new_secrets)
        >>>
        >>> # 更新 Verifier
        >>> verifier.update_global_pk(new_pk)
        """
        # 步骤 1: 撤销旧批次
        sigma_to_revoke = old_batch_header["sigma"]
        g_s_q_new, new_global_pk, sigma_bytes = self.revoke_batch(sigma_to_revoke)

        # 步骤 2: 创建新批次
        new_batch_id, new_public_header, new_secrets_for_ss = self.create_batch(
            new_m_matrix, new_t_vector
        )

        # 返回所有信息
        return (g_s_q_new, new_global_pk, sigma_bytes,
                new_batch_id, new_public_header, new_secrets_for_ss)

    def get_initial_server_keys(self) -> Tuple:
        """
        Get the initial server keys for SS.
        
        Returns
        -------
        Tuple
            The initial server keys (g, g^s)
        
        Notes
        -----
        This should be called once when setting up SS.
        After each revocation, DO sends the new g^{s^q} to SS.
        """
        return self.server_acc_keys
    
    def get_global_pk(self) -> Dict:
        """
        Get the current global public key.
        
        Returns
        -------
        dict
            The current global_pk
        
        Notes
        -----
        This should be published and made available to all verifiers.
        Verifiers must fetch the latest global_pk before verification.
        """
        return self.global_pk

