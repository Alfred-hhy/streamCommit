"""
Commitment Generation
=====================

This module implements all commitment types used in the vector commitment scheme:
- C: Base commitment in G to vector m
- Ĉ: Base commitment in Ĝ to vector x
- C_y: Hadamard (reverse) commitment mixing y and x
- V̂: Integer commitment for range proofs

All implementations strictly follow the formulas from the paper.
"""

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2
from typing import List
from .utils import multiexp_g1, multiexp_g2


def commit_G(m: List[ZR], gamma: ZR, crs: dict) -> G1:
    """
    Generate base commitment C in G to vector m with randomness γ.
    
    Formula (Base commitment):
    --------------------------
    C := g^{γ} · ∏_{j=1}^n g_j^{m_j} ∈ G
    
    Parameters
    ----------
    m : List[ZR]
        The message vector (m_1, ..., m_n) in Z_p^n
    gamma : ZR
        The randomness γ ∈ Z_p
    crs : dict
        The CRS from keygen_crs()
    
    Returns
    -------
    G1
        The commitment C = g^γ · ∏_{j=1}^n g_j^{m_j}
    
    Notes
    -----
    This is the standard vector commitment in G (G1).
    The commitment is binding (assuming discrete log hardness) and hiding (due to γ).
    
    Examples
    --------
    >>> m = [group.random(ZR) for _ in range(n)]
    >>> gamma = group.random(ZR)
    >>> C = commit_G(m, gamma, crs)
    """
    group = crs['group']
    n = crs['n']
    g = crs['g']
    g_list = crs['g_list']
    
    if len(m) != n:
        raise ValueError(f"Message vector length {len(m)} != n={n}")
    
    # C = g^γ
    C = g ** gamma
    
    # C *= ∏_{j=1}^n g_j^{m_j}
    for j in range(1, n + 1):
        C *= g_list[j] ** m[j - 1]  # m is 0-indexed, g_list is 1-indexed
    
    return C


def commit_Ghat(x: List[ZR], gamma: ZR, crs: dict) -> G2:
    """
    Generate base commitment Ĉ in Ĝ to vector x with randomness γ.
    
    Formula (Base commitment in Ĝ):
    --------------------------------
    Ĉ := ĝ^{γ} · ∏_{j=1}^n ĝ_j^{x_j} ∈ Ĝ
    
    Parameters
    ----------
    x : List[ZR]
        The vector (x_1, ..., x_n) in Z_p^n
    gamma : ZR
        The randomness γ ∈ Z_p
    crs : dict
        The CRS from keygen_crs()
    
    Returns
    -------
    G2
        The commitment Ĉ = ĝ^γ · ∏_{j=1}^n ĝ_j^{x_j}
    
    Notes
    -----
    This is the base commitment in Ĝ (G2).
    Used in conjunction with C_y to prove properties about x.
    
    Examples
    --------
    >>> x = [group.random(ZR) for _ in range(n)]
    >>> gamma = group.random(ZR)
    >>> C_hat = commit_Ghat(x, gamma, crs)
    """
    group = crs['group']
    n = crs['n']
    g_hat = crs['g_hat']
    g_hat_list = crs['g_hat_list']
    
    if len(x) != n:
        raise ValueError(f"Vector length {len(x)} != n={n}")
    
    # Ĉ = ĝ^γ
    C_hat = g_hat ** gamma
    
    # Ĉ *= ∏_{j=1}^n ĝ_j^{x_j}
    for j in range(1, n + 1):
        C_hat *= g_hat_list[j] ** x[j - 1]  # x is 0-indexed, g_hat_list is 1-indexed
    
    return C_hat


def commit_Cy(y: List[ZR], x: List[ZR], gamma_y: ZR, crs: dict) -> G1:
    """
    Generate Hadamard (reverse) commitment C_y mixing y and x.
    
    Formula (Equation 2):
    ---------------------
    C_y = g^{γ_y} · ∏_{j=1}^{n} g_{n+1-j}^{y_j x_j}
    
    Parameters
    ----------
    y : List[ZR]
        The vector (y_1, ..., y_n) in Z_p^n (typically binary: y_i ∈ {0,1})
    x : List[ZR]
        The vector (x_1, ..., x_n) in Z_p^n
    gamma_y : ZR
        The randomness γ_y ∈ Z_p
    crs : dict
        The CRS from keygen_crs()
    
    Returns
    -------
    G1
        The commitment C_y = g^{γ_y} · ∏_{j=1}^{n} g_{n+1-j}^{y_j x_j}
    
    Notes
    -----
    This commitment uses REVERSE indexing: g_{n+1-j} instead of g_j.
    This is crucial for the equality proof π_eq.
    
    The commitment binds to the Hadamard product y ∘ x = (y_1 x_1, ..., y_n x_n)
    in reverse order.
    
    Equation Reference: (2)
    
    Examples
    --------
    >>> y = [group.random(ZR) for _ in range(n)]
    >>> x = [group.random(ZR) for _ in range(n)]
    >>> gamma_y = group.random(ZR)
    >>> C_y = commit_Cy(y, x, gamma_y, crs)
    """
    group = crs['group']
    n = crs['n']
    g = crs['g']
    g_list = crs['g_list']
    
    if len(y) != n or len(x) != n:
        raise ValueError(f"Vector lengths must equal n={n}: len(y)={len(y)}, len(x)={len(x)}")
    
    # C_y = g^{γ_y}
    C_y = g ** gamma_y
    
    # C_y *= ∏_{j=1}^{n} g_{n+1-j}^{y_j x_j}
    for j in range(1, n + 1):
        idx = n + 1 - j  # Reverse indexing
        if idx not in g_list:
            raise ValueError(f"Index {idx} (n+1-{j}) not in g_list")
        exponent = y[j - 1] * x[j - 1]  # y_j * x_j
        C_y *= g_list[idx] ** exponent
    
    return C_y


def commit_V(x_scalar: ZR, r: ZR, crs: dict) -> G2:
    """
    Generate integer commitment V̂ for range proofs.
    
    Formula (Integer commitment):
    -----------------------------
    V̂ := ĝ^{r} · ĝ_1^{x}
    
    where x = ∑_{i=1}^{ℓ} x_i 2^{i-1} with bits x_i ∈ {0,1}
    
    Parameters
    ----------
    x_scalar : ZR
        The scalar value x ∈ Z_p (should be the sum ∑ x_i 2^{i-1})
    r : ZR
        The randomness r ∈ Z_p
    crs : dict
        The CRS from keygen_crs()
    
    Returns
    -------
    G2
        The commitment V̂ = ĝ^r · ĝ_1^x
    
    Notes
    -----
    This commitment is used in range proofs to commit to a scalar value x
    that is claimed to be the weighted sum of bits x_i.
    
    The proof π_x (equation 9) verifies that the bits in Ĉ sum to x in V̂.
    
    Examples
    --------
    >>> x_bits = [0, 1, 1, 0, 1]  # Binary representation
    >>> x_scalar = sum(x_bits[i] * (2**i) for i in range(len(x_bits)))
    >>> r = group.random(ZR)
    >>> V_hat = commit_V(group.init(ZR, x_scalar), r, crs)
    """
    group = crs['group']
    g_hat = crs['g_hat']
    g_hat_list = crs['g_hat_list']
    
    # V̂ = ĝ^r · ĝ_1^x
    V_hat = (g_hat ** r) * (g_hat_list[1] ** x_scalar)
    
    return V_hat


def bits_to_scalar(bits: List[int], group: PairingGroup) -> ZR:
    """
    Convert a bit vector to a scalar: x = ∑_{i=1}^{ℓ} x_i 2^{i-1}.
    
    Parameters
    ----------
    bits : List[int]
        The bit vector [x_1, x_2, ..., x_ℓ] where x_i ∈ {0, 1}
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    ZR
        The scalar x = ∑_{i=1}^{ℓ} x_i 2^{i-1}
    
    Examples
    --------
    >>> bits = [1, 0, 1, 1]  # Represents 1 + 0*2 + 1*4 + 1*8 = 13
    >>> x = bits_to_scalar(bits, group)
    """
    x = group.init(ZR, 0)
    for i, bit in enumerate(bits):
        if bit not in [0, 1]:
            raise ValueError(f"Bit {i} has value {bit}, must be 0 or 1")
        x += group.init(ZR, bit * (2 ** i))
    return x


def scalar_to_bits(x: int, ell: int) -> List[int]:
    """
    Convert a scalar to a bit vector of length ℓ.
    
    Parameters
    ----------
    x : int
        The scalar value
    ell : int
        The bit length ℓ
    
    Returns
    -------
    List[int]
        The bit vector [x_1, x_2, ..., x_ℓ] where x = ∑ x_i 2^{i-1}
    
    Examples
    --------
    >>> bits = scalar_to_bits(13, 4)  # [1, 0, 1, 1]
    """
    bits = []
    for i in range(ell):
        bits.append((x >> i) & 1)
    return bits

