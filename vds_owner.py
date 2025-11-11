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
    
    def create_batch(self, m_vector: List[ZR], t_vector: List[ZR]) -> Tuple[str, Dict, Dict]:
        """
        Create and sign a new batch.
        
        Parameters
        ----------
        m_vector : List[ZR]
            The data vector (length n)
        t_vector : List[ZR]
            The time vector (length n)
        
        Returns
        -------
        batch_id : str
            A unique identifier for this batch
        public_header : dict
            Public information for verifiers:
            - C_data: Data commitment (G1)
            - C_time: Time commitment (G2)
            - sigma: Binding signature
        secrets_for_ss : dict
            Secret information for SS (to generate proofs):
            - m: Data vector
            - t: Time vector
            - gamma_data: Randomness for C_data
            - gamma_time: Randomness for C_time
        
        Notes
        -----
        Workflow:
        1. Generate random blinding factors (gamma_data, gamma_time)
        2. Compute commitments: C_data = commit_G(m, gamma_data)
                               C_time = commit_Ghat(t, gamma_time)
        3. Sign the commitments: sigma = Sign(sk_DO, Hash(C_data || C_time))
        4. Prepare public header and secrets
        5. Return everything for SS to store
        
        Security:
        - The signature binds C_data and C_time together
        - Any tampering will be detected during verification
        - Secrets are only given to SS (trusted for storage)
        """
        n = self.crs['n']
        
        # Validate input lengths
        if len(m_vector) != n or len(t_vector) != n:
            raise ValueError(f"Vectors must have length n={n}")
        
        # Generate random blinding factors
        gamma_data = self.group.random(ZR)
        gamma_time = self.group.random(ZR)
        
        # Compute commitments
        C_data = commit_G(m_vector, gamma_data, self.crs)      # In G1
        C_time = commit_Ghat(t_vector, gamma_time, self.crs)  # In G2
        
        # Sign the commitments (binding)
        sigma = vds_utils.sign_batch(self.sk_DO, C_data, C_time)
        
        # Generate batch ID (simple hash of commitments)
        import hashlib
        batch_id_bytes = vds_utils.hash_for_signing(C_data, C_time)
        batch_id = hashlib.sha256(batch_id_bytes).hexdigest()[:16]
        
        # Prepare public header (for verifiers)
        public_header = {
            "C_data": C_data,
            "C_time": C_time,
            "sigma": sigma
        }
        
        # Prepare secrets (for SS to generate proofs)
        secrets_for_ss = {
            "m": m_vector,
            "t": t_vector,
            "gamma_data": gamma_data,
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

