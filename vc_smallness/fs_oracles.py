"""
Fiat-Shamir Random Oracles
===========================

This module implements the random oracles (hash functions) used in the
Fiat-Shamir transformation to make the interactive proofs non-interactive.

Random Oracles:
---------------
- H_t: Generate challenge weights (t_i) for aggregated opening
- H_agg: Generate aggregation challenges (δ_eq, δ_y) for proof aggregation
- H_s: Generate challenges (s_i) for the "only-first-coordinate" proof

Domain Separation:
------------------
Each hash function uses a different prefix to ensure domain separation:
- H_t uses prefix b"HT"
- H_agg uses prefix b"HAGG"
- H_s uses prefix b"HS"

According to charm-crypto documentation:
- Use group.hash(data, ZR) to hash arbitrary data to a scalar in Z_p
- Data should be serialized to bytes before hashing
"""

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2
from charm.core.engine.util import objectToBytes
from typing import List, Tuple
import hashlib


def _serialize_for_hash(group: PairingGroup, *args) -> bytes:
    """
    Serialize multiple group elements and other data for hashing.

    Parameters
    ----------
    group : PairingGroup
        The pairing group
    *args : variable
        Elements to serialize (group elements, integers, bytes, etc.)

    Returns
    -------
    bytes
        Concatenated serialization of all arguments
    """
    result = b""
    for arg in args:
        if isinstance(arg, bytes):
            result += arg
        elif isinstance(arg, int):
            result += arg.to_bytes(8, 'big')
        elif isinstance(arg, str):
            result += arg.encode('utf-8')
        elif isinstance(arg, list):
            for item in arg:
                if isinstance(item, int):
                    result += item.to_bytes(8, 'big')
                else:
                    # Try to serialize as group element
                    try:
                        result += objectToBytes(item, group)
                    except:
                        result += str(item).encode('utf-8')
        else:
            # Try to serialize as group element (G1, G2, GT, ZR)
            try:
                result += objectToBytes(arg, group)
            except:
                # Fallback: convert to string
                result += str(arg).encode('utf-8')
    return result


def H_t(C: G1, C_hat: G2, C_y: G1, n: int, group: PairingGroup, ctx_bytes: bytes = b"") -> List[ZR]:
    """
    Random oracle H_t: Generate challenge weights (t_i) for aggregated opening.
    
    This oracle is used to generate random weights for aggregating multiple
    point opening proofs into a single proof.
    
    Formula Context:
    ----------------
    Used in equations (1), (5), (12), (13), (16), (18) where we need random
    weights t_i to aggregate proofs or verify aggregated relations.
    
    Parameters
    ----------
    C : G1
        The commitment C = g^γ · ∏ g_j^{m_j}
    C_hat : G2
        The commitment Ĉ = ĝ^γ · ∏ ĝ_j^{x_j}
    C_y : G1
        The Hadamard commitment C_y = g^{γ_y} · ∏ g_{n+1-j}^{y_j x_j}
    n : int
        The vector dimension
    group : PairingGroup
        The pairing group
    ctx_bytes : bytes, optional
        Additional context bytes to include in the hash
    
    Returns
    -------
    List[ZR]
        A list of n random scalars [t_1, t_2, ..., t_n] in Z_p
    
    Notes
    -----
    Domain separation: Uses prefix b"HT"
    The hash is computed over (prefix || C || C_hat || C_y || ctx_bytes)
    and then expanded to n scalars using a counter.
    """
    prefix = b"HT"
    base_input = _serialize_for_hash(group, prefix, C, C_hat, C_y, ctx_bytes)
    
    # Generate n independent challenges by appending a counter
    t_list = []
    for i in range(1, n + 1):
        input_i = base_input + i.to_bytes(4, 'big')
        t_i = group.hash(input_i, ZR)
        t_list.append(t_i)
    
    return t_list


def H_agg(C: G1, C_hat: G2, C_y: G1, group: PairingGroup) -> Tuple[ZR, ZR]:
    """
    Random oracle H_agg: Generate aggregation challenges (δ_eq, δ_y).
    
    This oracle generates two random challenges used to aggregate π_eq and π_y
    into a single proof π = π_eq^{δ_eq} · π_y^{δ_y}.
    
    Formula Context:
    ----------------
    Used in equation (16) for the aggregated verification:
    
    π = π_eq^{δ_eq} · π_y^{δ_y}
    
    where (δ_eq, δ_y) = H_agg(C, Ĉ, C_y)
    
    Parameters
    ----------
    C : G1
        The commitment C
    C_hat : G2
        The commitment Ĉ
    C_y : G1
        The Hadamard commitment C_y
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    Tuple[ZR, ZR]
        A tuple (δ_eq, δ_y) of two random scalars in Z_p
    
    Notes
    -----
    Domain separation: Uses prefix b"HAGG"
    The hash is computed over (prefix || C || C_hat || C_y)
    and expanded to two scalars using counters.
    """
    prefix = b"HAGG"
    base_input = _serialize_for_hash(group, prefix, C, C_hat, C_y)
    
    # Generate two independent challenges
    delta_eq = group.hash(base_input + b"\x00", ZR)
    delta_y = group.hash(base_input + b"\x01", ZR)
    
    return delta_eq, delta_y


def H_s(i: int, domain: List[int], V_hat: G2, C_hat: G2, C_y: G1, group: PairingGroup) -> ZR:
    """
    Random oracle H_s: Generate challenge s_i for "only-first-coordinate" proof.
    
    This oracle generates challenges used in the proof π_v that verifies
    that V̂ commits to a value where only the first coordinate is non-zero.
    
    Formula Context:
    ----------------
    Used in equation (20):
    
    π_v = ∏_{i=2}^{n} (g_{n+1-i}^r · g_{n+2-i}^x)^{s_i}
    
    where s_i = H_s(i, [2,n], V̂, Ĉ, C_y)
    
    Parameters
    ----------
    i : int
        The index i (typically in range [2, n])
    domain : List[int]
        The domain of indices (typically [2, n])
    V_hat : G2
        The integer commitment V̂ = ĝ^r · ĝ_1^x
    C_hat : G2
        The commitment Ĉ
    C_y : G1
        The Hadamard commitment C_y
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    ZR
        A random scalar s_i in Z_p
    
    Notes
    -----
    Domain separation: Uses prefix b"HS"
    The hash is computed over (prefix || i || domain || V_hat || C_hat || C_y)
    """
    prefix = b"HS"
    domain_bytes = b"".join([idx.to_bytes(4, 'big') for idx in domain])
    input_data = _serialize_for_hash(group, prefix, i, domain_bytes, V_hat, C_hat, C_y)
    
    s_i = group.hash(input_data, ZR)
    return s_i


def H_s_batch(domain: List[int], V_hat: G2, C_hat: G2, C_y: G1, group: PairingGroup) -> List[ZR]:
    """
    Batch version of H_s: Generate all s_i for i in domain.
    
    Parameters
    ----------
    domain : List[int]
        The list of indices (typically [2, 3, ..., n])
    V_hat : G2
        The integer commitment V̂
    C_hat : G2
        The commitment Ĉ
    C_y : G1
        The Hadamard commitment C_y
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    List[ZR]
        A list of scalars [s_i for i in domain]
    
    Examples
    --------
    >>> s_list = H_s_batch([2, 3, 4, 5], V_hat, C_hat, C_y, group)
    >>> # s_list[0] corresponds to s_2, s_list[1] to s_3, etc.
    """
    return [H_s(i, domain, V_hat, C_hat, C_y, group) for i in domain]

