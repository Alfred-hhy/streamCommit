"""
Bilinear Map Accumulator for Revocation
========================================

This module implements a bilinear map accumulator based on Krupp et al. (2016)
Section 2.5 and Section 5. The accumulator is used as a "blacklist" to prevent
rollback attacks in the VDS scheme.

Key Concepts:
-------------
- Accumulator value f: Represents the current state of the blacklist
- Non-membership proof: Proves that an item is NOT in the blacklist
- Dynamic updates: f changes when items are added to the blacklist

Security:
---------
- Based on the q-Strong Bilinear Diffie-Hellman (q-SBDH) assumption
- Non-membership proofs are unforgeable under this assumption

References:
-----------
Krupp et al. (2016) "Nearly Optimal Verifiable Data Streaming"
- Section 2.5: Accumulator definition and properties
- Section 5: Non-membership proof construction
"""

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2, pair
from typing import Tuple, List
import hashlib
import numpy as np


class Accumulator:
    """
    Bilinear map accumulator for revocation (blacklist).
    
    This accumulator uses asymmetric pairings e: G1 × G2 → GT.
    
    Convention:
    -----------
    - Accumulator values f, g, w are in G1
    - Verification key g^s is in G2
    - This allows verification equation: e(w, ĝ^{e_i} · ĝ^s) = e(f · g^u, ĝ)
    
    The accumulator maintains a set of revoked items (blacklist).
    Non-membership proofs demonstrate that an item is NOT in the blacklist.
    """
    
    def __init__(self, group: PairingGroup):
        """
        Initialize the accumulator with a pairing group.
        
        Parameters
        ----------
        group : PairingGroup
            The pairing group (must support asymmetric pairings)
        """
        self.group = group
        self.g1 = self.group.random(G1)  # Generator for G1 (accumulator base)
        self.g2 = self.group.random(G2)  # Generator for G2 (verification base)
    
    def setup(self) -> Tuple[ZR, Tuple, G1, Tuple]:
        """
        Generate accumulator keys and initial state.

        Returns
        -------
        acc_sk : ZR
            Secret key s (only for DO, used to update f and expand server keys)
        acc_pk : Tuple
            Public key (g, ĝ, ĝ^s) for verification
        f_initial : G1
            Initial accumulator value (empty set = g)
        server_keys : Tuple
            Server keys (g,) in G1 for proof generation (initially just g)

        Notes
        -----
        - acc_sk must be kept secret by DO
        - acc_pk is public and included in global_pk
        - f_initial represents an empty blacklist
        - server_keys are given to SS to generate non-membership proofs
        - Initially, server_keys = (g,) representing q=0 (no revocations)
        - After first revocation, DO computes g^s and sends it to SS
        """
        # Generate secret key s
        s = self.group.random(ZR)
        acc_sk = s

        # Compute public verification keys
        g2_s = self.g2 ** s      # ĝ^s in G2 (used for verification)

        # Public key for verification
        acc_pk = (self.g1, self.g2, g2_s)  # (g, ĝ, ĝ^s)

        # Initial accumulator value (empty set)
        f_initial = self.g1  # f_0 = g (no items revoked yet)

        # Server keys for proof generation (initially just g)
        # After each revocation, DO will compute g^{s^q} and send it to SS
        server_keys = (self.g1,)  # (g,) - q=0 initially

        return (acc_sk, acc_pk, f_initial, server_keys)
    
    def _hash_item(self, item_bytes: bytes) -> ZR:
        """
        Hash an arbitrary item (e.g., signature bytes) to a non-zero element in ZR.
        
        Parameters
        ----------
        item_bytes : bytes
            The item to hash (e.g., serialized signature)
        
        Returns
        -------
        ZR
            A non-zero element in ZR representing the item
        
        Notes
        -----
        We ensure the hash is non-zero to avoid division by zero in proofs.
        If the hash is zero, we append a null byte and rehash.
        """
        h = self.group.hash(item_bytes, ZR)
        while h == 0:
            item_bytes += b'\x00'
            h = self.group.hash(item_bytes, ZR)
        return h
    
    def add_to_blacklist(self, acc_sk: ZR, f_current: G1, item_to_revoke_bytes: bytes) -> G1:
        """
        Add an item to the blacklist (called by DO).
        
        This updates the accumulator value f to include the revoked item.
        
        Parameters
        ----------
        acc_sk : ZR
            The secret key s
        f_current : G1
            The current accumulator value
        item_to_revoke_bytes : bytes
            The item to revoke (e.g., serialized signature)
        
        Returns
        -------
        G1
            The new accumulator value f_new = f_current^{e_i + s}
        
        Notes
        -----
        Formula: f_new = f_current^{e_i + s}
        where e_i = H(item_to_revoke_bytes)
        
        This is based on Krupp et al. (2016) Section 5.
        """
        e_i = self._hash_item(item_to_revoke_bytes)
        s = acc_sk
        
        # f_new = f_current^{e_i + s}
        f_new = f_current ** (e_i + s)
        
        return f_new
    
    def expand_server_keys(self, acc_sk: ZR, server_keys_tuple: Tuple,
                          update_count: int) -> Tuple[Tuple, G1]:
        """
        Expand server keys to include g^{s^q} (called by DO after revocation).

        Parameters
        ----------
        acc_sk : ZR
            The secret key s
        server_keys_tuple : Tuple
            Current server keys (g,) or (g, g^s, ..., g^{s^{q-1}})
        update_count : int
            The number of revocations so far (determines q)

        Returns
        -------
        new_server_keys : Tuple
            Extended server keys (g, g^s, ..., g^{s^q})
        g_s_q : G1
            The new key g^{s^q} (to be sent to SS)

        Notes
        -----
        After each revocation, DO computes g^{s^q} and sends it to SS.
        This allows SS to generate non-membership proofs for the updated blacklist.

        Formula:
        - First revocation (q=1): g^s = g^s
        - Subsequent revocations: g^{s^q} = (g^{s^{q-1}})^s
        """
        s = acc_sk

        # Get the last key
        g_last = server_keys_tuple[-1]

        # Compute g^{s^q} = (last_key)^s
        # For first revocation: g^s = g^s
        # For subsequent: g^{s^q} = (g^{s^{q-1}})^s
        g_s_q = g_last ** s

        # Extend the tuple
        new_server_keys = server_keys_tuple + (g_s_q,)

        return new_server_keys, g_s_q
    
    def _compute_polynomial_coefficients(self, X: List[ZR]) -> np.ndarray:
        """
        Compute coefficients of f_X(κ) = ∏_{x∈X}(x + κ).

        Parameters
        ----------
        X : List[ZR]
            The set of revoked items (hashed to ZR)

        Returns
        -------
        np.ndarray
            Coefficients [c_0, c_1, ..., c_q] where f_X(κ) = ∑ c_i κ^i

        Notes
        -----
        This uses dynamic programming to compute the polynomial product.
        Time complexity: O(q²) where q = |X|
        """
        if len(X) == 0:
            return np.array([1])  # f_∅(κ) = 1

        # Convert ZR elements to integers for polynomial arithmetic
        p = int(self.group.order())
        X_int = [int(x) % p for x in X]

        # Start with (x_1 + κ)
        poly = np.array([X_int[0], 1], dtype=object)  # [x_1, 1]

        # Multiply by (x_i + κ) for i = 2, ..., q
        for x_i in X_int[1:]:
            # Multiply poly by (x_i + κ)
            new_poly = np.zeros(len(poly) + 1, dtype=object)
            new_poly[:-1] += poly * x_i  # poly * x_i
            new_poly[1:] += poly          # poly * κ
            poly = new_poly % p

        return poly

    def _polynomial_division(self, dividend_coeffs: np.ndarray, divisor_coeffs: np.ndarray, p: int) -> np.ndarray:
        """
        Polynomial division in Z_p[X]: dividend / divisor.

        Parameters
        ----------
        dividend_coeffs : np.ndarray
            Coefficients of dividend polynomial
        divisor_coeffs : np.ndarray
            Coefficients of divisor polynomial
        p : int
            The modulus (group order)

        Returns
        -------
        np.ndarray
            Coefficients of quotient polynomial

        Notes
        -----
        This implements polynomial long division in Z_p.
        """
        # Remove leading zeros
        dividend = np.trim_zeros(dividend_coeffs, 'b')
        divisor = np.trim_zeros(divisor_coeffs, 'b')

        if len(divisor) == 0:
            raise ValueError("Division by zero polynomial")

        if len(dividend) < len(divisor):
            return np.array([0])

        # Quotient will have degree: deg(dividend) - deg(divisor)
        quotient = np.zeros(len(dividend) - len(divisor) + 1, dtype=object)

        # Working copy of dividend
        remainder = dividend.copy()

        # Leading coefficient of divisor
        divisor_lead = int(divisor[-1]) % p
        divisor_lead_inv = pow(divisor_lead, -1, p)  # Modular inverse

        # Polynomial long division
        for i in range(len(quotient) - 1, -1, -1):
            if len(remainder) < len(divisor):
                break

            # Coefficient for this term of quotient
            coeff = (int(remainder[-1]) * divisor_lead_inv) % p
            quotient[i] = coeff

            # Subtract divisor * coeff from remainder
            for j in range(len(divisor)):
                remainder[i + j] = (int(remainder[i + j]) - coeff * int(divisor[j])) % p

            # Remove leading term
            remainder = remainder[:-1]

        return quotient % p

    def prove_non_membership(self, server_keys_tuple: Tuple, f_current: G1,
                            item_to_check_bytes: bytes, X: List[bytes] = None) -> Tuple[G1, ZR]:
        """
        Generate a non-membership proof (called by SS).

        This proves that item_to_check is NOT in the blacklist represented by f_current.

        Parameters
        ----------
        server_keys_tuple : Tuple
            Server keys (g, g^s, ..., g^{s^q}) in G1
        f_current : G1
            The current accumulator value
        item_to_check_bytes : bytes
            The item to check (e.g., serialized signature)
        X : List[bytes], optional
            The list of revoked items (for non-empty accumulator)

        Returns
        -------
        pi_non : Tuple[G1, ZR]
            Non-membership proof (w, u) where:
            - w ∈ G1: witness
            - u ∈ ZR: auxiliary value

        Notes
        -----
        This implements Damgård et al. (2008) Section 3.2 and Krupp et al. (2016) Section 2.5.

        Algorithm:
        1. Compute y = H(item_to_check)
        2. Compute u_y = -∏_{x∈X}(x - y) mod p  (Damgård Eq 5)
        3. Compute f_X(κ) = ∏_{x∈X}(x + κ)
        4. Compute h_X(κ) = f_X(κ) - f_X(-y) = f_X(κ) - (-u_y)
        5. Compute q̂_X(κ) = h_X(κ) / (κ + y)  (polynomial division)
        6. Compute w_y = g^{q̂_X(s)} using server_keys

        Verification equation: e(w, ĝ^{y+s}) = e(f · g^u, ĝ)
        """
        y = self._hash_item(item_to_check_bytes)

        # Get the number of revoked items (q)
        q = len(server_keys_tuple) - 1  # server_keys = (g, g^s, ..., g^{s^q})

        if q == 0:
            # Empty accumulator: f = g (no revocations)
            # For empty set, u_y = -1, w_y = 1 (identity)
            w = self.group.init(G1, 1)  # Identity element in G1
            u = self.group.init(ZR, -1)
            return (w, u)

        # Non-empty accumulator: implement full Damgård algorithm
        if X is None or len(X) == 0:
            raise ValueError("For non-empty accumulator, X (revoked items) must be provided")

        # Step 1: Hash all revoked items to ZR
        X_hashed = [self._hash_item(item) for item in X]

        # Step 2: Compute u_y = -∏_{x∈X}(x - y) mod p  (Damgård Eq 5)
        p = int(self.group.order())
        u_y = 1
        for x_i in X_hashed:
            u_y = (u_y * (int(x_i) - int(y))) % p
        u_y = (-u_y) % p

        if u_y == 0:
            # y is actually in X, cannot generate non-membership proof
            raise ValueError("Item is in the blacklist, cannot prove non-membership")

        # Step 3: Compute f_X(κ) coefficients
        f_X_coeffs = self._compute_polynomial_coefficients(X_hashed)

        # Step 4: Compute h_X(κ) = f_X(κ) - f_X(-y)
        # f_X(-y) = -u_y (by definition)
        h_X_coeffs = f_X_coeffs.copy()
        h_X_coeffs[0] = (int(h_X_coeffs[0]) - (-u_y)) % p

        # Step 5: Polynomial division: q̂_X(κ) = h_X(κ) / (κ + y)
        divisor_coeffs = np.array([int(y), 1], dtype=object)  # (y + κ)
        q_hat_coeffs = self._polynomial_division(h_X_coeffs, divisor_coeffs, p)

        # Step 6: Compute w_y = g^{q̂_X(s)} = ∏ (g^{s^i})^{v_i}
        # where q̂_X(κ) = ∑ v_i κ^i
        w_y = self.group.init(G1, 1)
        for i, v_i in enumerate(q_hat_coeffs):
            if i >= len(server_keys_tuple):
                raise ValueError(f"Insufficient server keys: need g^{{s^{i}}}, have only up to g^{{s^{q}}}")
            w_y *= server_keys_tuple[i] ** int(v_i)

        # Return proof
        u = self.group.init(ZR, u_y)
        return (w_y, u)
    
    def verify_non_membership(self, acc_pk: Tuple, f_current: G1, 
                             item_to_check_bytes: bytes, pi_non: Tuple[G1, ZR]) -> bool:
        """
        Verify a non-membership proof (called by Verifier).
        
        This verifies that item_to_check is NOT in the blacklist represented by f_current.
        
        Parameters
        ----------
        acc_pk : Tuple
            Public key (g, ĝ, ĝ^s)
        f_current : G1
            The current accumulator value
        item_to_check_bytes : bytes
            The item to check (e.g., serialized signature)
        pi_non : Tuple[G1, ZR]
            Non-membership proof (w, u)
        
        Returns
        -------
        bool
            True if the item is NOT in the blacklist, False otherwise
        
        Notes
        -----
        Verification equation (Krupp et al. 2016):
        e(w, ĝ^{e_i} · ĝ^s) = e(f_current · g^u, ĝ)
        
        This equation holds if and only if:
        w^{e_i + s} = f_current · g^u
        
        which is true if and only if e_i is NOT in the accumulator.
        """
        (g, g_hat, g_hat_s) = acc_pk  # (g1, g2, g2^s)
        (w, u) = pi_non  # (w in G1, u in ZR)
        
        e_i = self._hash_item(item_to_check_bytes)
        
        # Compute LHS: e(w, ĝ^{e_i} · ĝ^s) = e(w, ĝ^{e_i + s})
        g_hat_e_i_plus_s = (g_hat ** e_i) * g_hat_s
        lhs = pair(w, g_hat_e_i_plus_s)
        
        # Compute RHS: e(f_current · g^u, ĝ)
        f_times_g_u = f_current * (g ** u)
        rhs = pair(f_times_g_u, g_hat)
        
        # Check equality
        return lhs == rhs

