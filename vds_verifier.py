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
    
    def _verify_precheck(self, public_header: Dict, pi_non: Tuple) -> Tuple[bool, G1]:
        """
        Perform pre-verification checks (signature + blacklist).
        
        Parameters
        ----------
        public_header : dict
            The public header (C_data, C_time, sigma)
        pi_non : Tuple[G1, ZR]
            The accumulator non-membership proof
        
        Returns
        -------
        is_valid : bool
            True if precheck passes, False otherwise
        C_data : G1
            The data commitment (for subsequent verification)
        
        Notes
        -----
        This is the CRITICAL security check that:
        1. Verifies the signature binding (prevents mix-and-match)
        2. Verifies non-membership in blacklist (prevents rollback)
        
        If either check fails, the entire verification fails.
        """
        try:
            # Extract current global_pk components
            vk_sig = self.current_global_pk["vk_sig"]
            acc_pk = self.current_global_pk["acc_pk"]
            f_current = self.current_global_pk["f_current"]
            
            # Extract public header components
            C_data = public_header["C_data"]
            C_time = public_header["C_time"]
            sigma = public_header["sigma"]
            
            # Check 1: Verify signature binding
            if not vds_utils.verify_batch_signature(vk_sig, C_data, C_time, sigma):
                print("❌ Verification failed: Invalid signature binding.")
                print("   This indicates tampering or mix-and-match attack.")
                return False, None
            
            # Check 2: Verify non-membership in blacklist
            sigma_bytes = vds_utils.serialize_signature(sigma)
            if not self.accumulator.verify_non_membership(acc_pk, f_current, sigma_bytes, pi_non):
                print("❌ Verification failed: Item is in revocation list (blacklist).")
                print("   This batch has been revoked by DO.")
                return False, None
            
            # Both checks passed
            return True, C_data
            
        except Exception as e:
            print(f"❌ Precheck error: {e}")
            import traceback
            traceback.print_exc()
            return False, None
    
    def verify_dc_query(self, public_header: Dict, t_challenge_vector: List[ZR], 
                       x_result: ZR, pi_audit: G1, pi_non: Tuple) -> bool:
        """
        Verify a Data Consumer (DC) query.
        
        Parameters
        ----------
        public_header : dict
            The public header (C_data, C_time, sigma)
        t_challenge_vector : List[ZR]
            The challenge weights (provided by DC)
        x_result : ZR
            The claimed result ∑ m_i * t_i
        pi_audit : G1
            The VC proof (aggregated opening)
        pi_non : Tuple[G1, ZR]
            The accumulator non-membership proof
        
        Returns
        -------
        bool
            True if verification passes, False otherwise
        
        Notes
        -----
        DC Workflow:
        1. DC sends t_challenge to SS
        2. SS returns (x_result, pi_audit, pi_non)
        3. DC verifies using this function
        
        Verification steps:
        1. Precheck: signature + blacklist
        2. VC verification: Libert 2024 Equation 1
        """
        # Step 1 & 2: Verify signature and blacklist
        is_valid_precheck, C_data = self._verify_precheck(public_header, pi_non)
        if not is_valid_precheck:
            return False
        
        # Step 3: Verify VC proof (Libert 2024 Equation 1)
        # verify_1(C, pis, t, m, crs) checks:
        # e(C, ∏ ĝ_{n+1-i}^{t_i}) = e(∏ π_i^{t_i}, ĝ) · e(g_1, ĝ_n)^{∑ m_i t_i}
        
        # We have the aggregated proof pi_audit = ∏ π_i^{t_i}
        # We need to pass it as a list [pi_audit] and the result as [x_result]
        
        # Note: verify_1 expects pis as a list of individual proofs
        # But we have the aggregated proof, so we need to use a different approach
        
        # Actually, looking at verify_1 signature:
        # verify_1(C: G1, pis: List[G1], t: List[ZR], m: List[ZR], crs: dict)
        # It expects the full list of individual proofs and the full message vector
        
        # But we don't have the message vector m! That's the point of the proof.
        # We only have x_result = ∑ m_i * t_i
        
        # Let me check the verify_1 implementation again...
        # From the code: it computes ∑ m_i * t_i and uses it in the pairing
        
        # So we need a different verification approach.
        # We should use the aggregated verification directly.
        
        # The correct verification for aggregated opening is:
        # e(C, ∏ ĝ_{n+1-i}^{t_i}) = e(pi_audit, ĝ) · e(g_1, ĝ_n)^{x_result}
        
        # Let's implement this directly
        n = self.crs['n']
        g_hat = self.crs['g_hat']
        g_hat_list = self.crs['g_hat_list']
        g_list = self.crs['g_list']
        
        # Compute LHS: e(C, ∏ ĝ_{n+1-i}^{t_i})
        g_hat_prod = self.group.init(G2, 1)
        for i in range(1, n + 1):
            idx = n + 1 - i
            if idx in g_hat_list:
                g_hat_prod *= g_hat_list[idx] ** t_challenge_vector[i - 1]
        
        lhs = self.group.pair_prod(C_data, g_hat_prod)
        
        # Compute RHS: e(pi_audit, ĝ) · e(g_1, ĝ_n)^{x_result}
        rhs_1 = self.group.pair_prod(pi_audit, g_hat)
        rhs_2 = self.group.pair_prod(g_list[1], g_hat_list[n]) ** x_result
        rhs = rhs_1 * rhs_2
        
        # Check equality
        is_vc_valid = (lhs == rhs)
        
        if not is_vc_valid:
            print("❌ VC verification failed: Proof does not match commitment.")
            print("   This indicates tampering with data or incorrect proof.")
        
        return is_vc_valid
    
    def verify_da_audit(self, public_header: Dict, n: int, x_result_random: ZR, 
                       pi_audit_zk: G1, t_challenge_zk_provided: List[ZR], 
                       pi_non: Tuple) -> bool:
        """
        Verify a Data Auditor (DA) audit.
        
        Parameters
        ----------
        public_header : dict
            The public header (C_data, C_time, sigma)
        n : int
            The vector dimension
        x_result_random : ZR
            The claimed result with random challenge
        pi_audit_zk : G1
            The VC proof (aggregated opening)
        t_challenge_zk_provided : List[ZR]
            The Fiat-Shamir challenge (from SS)
        pi_non : Tuple[G1, ZR]
            The accumulator non-membership proof
        
        Returns
        -------
        bool
            True if verification passes, False otherwise
        
        Notes
        -----
        DA Workflow:
        1. DA requests audit from SS
        2. SS returns (x_result_random, pi_audit_zk, t_challenge_zk, pi_non)
        3. DA verifies using this function
        
        Verification steps:
        1. Precheck: signature + blacklist
        2. Recompute Fiat-Shamir challenge (ensure SS didn't cheat)
        3. VC verification: Libert 2024 Equation 1
        """
        # Step 1 & 2: Verify signature and blacklist
        is_valid_precheck, C_data = self._verify_precheck(public_header, pi_non)
        if not is_valid_precheck:
            return False
        
        # Step 3: Recompute Fiat-Shamir challenge
        C_hat_dummy = self.group.init(G2, 1)
        C_y_dummy = self.group.init(G1, 1)
        t_challenge_zk_local = H_t(C_data, C_hat_dummy, C_y_dummy, n, self.group, b"VDS-DA-AUDIT-ZK")
        
        # Check challenge consistency
        if len(t_challenge_zk_local) != len(t_challenge_zk_provided):
            print("❌ Verification failed: Challenge length mismatch.")
            return False
        
        for i, (t_local, t_provided) in enumerate(zip(t_challenge_zk_local, t_challenge_zk_provided)):
            if t_local != t_provided:
                print(f"❌ Verification failed: ZK Challenge mismatch at position {i}.")
                print("   This indicates SS tried to use a different challenge.")
                return False
        
        # Step 4: Verify VC proof (same as DC, but with ZK challenge)
        g_hat = self.crs['g_hat']
        g_hat_list = self.crs['g_hat_list']
        g_list = self.crs['g_list']
        
        # Compute LHS: e(C, ∏ ĝ_{n+1-i}^{t_i})
        g_hat_prod = self.group.init(G2, 1)
        for i in range(1, n + 1):
            idx = n + 1 - i
            if idx in g_hat_list:
                g_hat_prod *= g_hat_list[idx] ** t_challenge_zk_local[i - 1]
        
        lhs = self.group.pair_prod(C_data, g_hat_prod)
        
        # Compute RHS: e(pi_audit_zk, ĝ) · e(g_1, ĝ_n)^{x_result_random}
        rhs_1 = self.group.pair_prod(pi_audit_zk, g_hat)
        rhs_2 = self.group.pair_prod(g_list[1], g_hat_list[n]) ** x_result_random
        rhs = rhs_1 * rhs_2
        
        # Check equality
        is_vc_valid = (lhs == rhs)
        
        if not is_vc_valid:
            print("❌ VC verification failed: Proof does not match commitment.")
            print("   This indicates tampering with data or incorrect proof.")
        
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

