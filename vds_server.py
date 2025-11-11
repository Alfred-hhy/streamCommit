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
    
    def generate_dc_data_proof(self, batch_id: str, t_challenge_vector: List[ZR], 
                               f_current: G1) -> Tuple[ZR, G1, Tuple]:
        """
        Generate a proof for Data Consumer (DC) - Interactive query.
        
        Parameters
        ----------
        batch_id : str
            The batch to query
        t_challenge_vector : List[ZR]
            The challenge weights from DC (e.g., [1,1,...,1] for sum)
        f_current : G1
            The current accumulator value (from DO's global_pk)
        
        Returns
        -------
        x_result : ZR
            The scalar result ∑ m_i * t_i
        pi_audit : G1
            The VC proof (aggregated opening proof)
        pi_non : Tuple[G1, ZR]
            The accumulator non-membership proof (w, u)
        
        Notes
        -----
        This implements the DC workflow:
        1. Retrieve batch data
        2. Compute scalar result x = ∑ m_i * t_i
        3. Generate VC proof (Libert 2024 Equation 1)
        4. Generate accumulator non-membership proof
        
        Security:
        - If SS tries to cheat (wrong x or tampered data), verification will fail
        - If the batch is revoked, accumulator proof will fail
        """
        # Retrieve batch data
        if batch_id not in self.storage:
            raise ValueError(f"Batch {batch_id} not found")
        
        header, secrets = self.storage[batch_id]
        m = secrets["m"]
        gamma_data = secrets["gamma_data"]
        C_data = header["C_data"]
        sigma = header["sigma"]
        
        n = len(m)
        if len(t_challenge_vector) != n:
            raise ValueError(f"Challenge vector length {len(t_challenge_vector)} != n={n}")
        
        # Compute scalar result: x = ∑ m_i * t_i
        x_result = self.group.init(ZR, 0)
        for m_i, t_i in zip(m, t_challenge_vector):
            x_result += m_i * t_i
        
        # Generate VC proof (Libert 2024 Equation 1)
        # We need to generate point opening proofs for all positions
        # Then aggregate them with weights t_challenge_vector
        
        # Generate all point opening proofs
        pis = []
        for i in range(1, n + 1):
            pi_i = prove_point_open(C_data, m, gamma_data, i, self.crs)
            pis.append(pi_i)
        
        # Aggregate with challenge weights
        # π_S = ∏ π_i^{t_i}
        pi_audit = self.group.init(G1, 1)
        for pi_i, t_i in zip(pis, t_challenge_vector):
            pi_audit *= pi_i ** t_i
        
        # Generate accumulator non-membership proof
        sigma_bytes = vds_utils.serialize_signature(sigma)
        try:
            pi_non = self.accumulator.prove_non_membership(
                self.server_acc_keys, f_current, sigma_bytes, X=self.revoked_items
            )
        except ValueError as e:
            if "in the blacklist" in str(e):
                # Item is revoked, return a dummy proof that will fail verification
                # The verifier will detect this and reject the batch
                w_dummy = self.group.init(G1, 1)
                u_dummy = self.group.init(ZR, 0)
                pi_non = (w_dummy, u_dummy)
            else:
                raise

        return (x_result, pi_audit, pi_non)
    
    def generate_da_audit_proof(self, batch_id: str, f_current: G1) -> Tuple[ZR, G1, List[ZR], Tuple]:
        """
        Generate a proof for Data Auditor (DA) - Non-interactive ZK audit.
        
        Parameters
        ----------
        batch_id : str
            The batch to audit
        f_current : G1
            The current accumulator value (from DO's global_pk)
        
        Returns
        -------
        x_result_random : ZR
            The scalar result with random challenge
        pi_audit_zk : G1
            The VC proof (aggregated opening proof)
        t_challenge_zk : List[ZR]
            The Fiat-Shamir challenge (for verifier to check)
        pi_non : Tuple[G1, ZR]
            The accumulator non-membership proof (w, u)
        
        Notes
        -----
        This implements the DA workflow (NIZK):
        1. Retrieve batch data
        2. Generate Fiat-Shamir challenge t_zk = H(C_data)
        3. Compute scalar result x = ∑ m_i * t_zk_i
        4. Generate VC proof
        5. Generate accumulator non-membership proof
        
        Security:
        - The challenge is deterministic (Fiat-Shamir)
        - Verifier will recompute the challenge and check consistency
        - This prevents SS from choosing a favorable challenge
        """
        # Retrieve batch data
        if batch_id not in self.storage:
            raise ValueError(f"Batch {batch_id} not found")
        
        header, secrets = self.storage[batch_id]
        m = secrets["m"]
        gamma_data = secrets["gamma_data"]
        C_data = header["C_data"]
        sigma = header["sigma"]
        n = len(m)
        
        # Generate Fiat-Shamir challenge
        # We use a custom domain separator for DA audit
        # Note: H_t expects (C, C_hat, C_y, n, group, ctx_bytes)
        # For DA audit, we only have C_data, so we use dummy values for C_hat and C_y
        C_hat_dummy = self.group.init(G2, 1)
        C_y_dummy = self.group.init(G1, 1)
        t_challenge_zk = H_t(C_data, C_hat_dummy, C_y_dummy, n, self.group, b"VDS-DA-AUDIT-ZK")
        
        # Compute scalar result: x = ∑ m_i * t_zk_i
        x_result_random = self.group.init(ZR, 0)
        for m_i, t_i in zip(m, t_challenge_zk):
            x_result_random += m_i * t_i
        
        # Generate VC proof
        pis = []
        for i in range(1, n + 1):
            pi_i = prove_point_open(C_data, m, gamma_data, i, self.crs)
            pis.append(pi_i)
        
        # Aggregate with challenge weights
        pi_audit_zk = self.group.init(G1, 1)
        for pi_i, t_i in zip(pis, t_challenge_zk):
            pi_audit_zk *= pi_i ** t_i
        
        # Generate accumulator non-membership proof
        sigma_bytes = vds_utils.serialize_signature(sigma)
        try:
            pi_non = self.accumulator.prove_non_membership(
                self.server_acc_keys, f_current, sigma_bytes, X=self.revoked_items
            )
        except ValueError as e:
            if "in the blacklist" in str(e):
                # Item is revoked, return a dummy proof that will fail verification
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

