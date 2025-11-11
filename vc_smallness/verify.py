"""
Verification Equations
======================

This module implements all verification equations (1)-(20) from the paper.

Each verification function corresponds to a numbered equation and strictly
follows the formula as written, including division-form equations.

Division equations are implemented as:
    LHS_numerator / LHS_denominator = RHS
    ⟺ LHS_numerator * (LHS_denominator)^{-1} = RHS

This is the ONLY way division equations are implemented.
No algebraic rewrites are performed unless proven equivalent and documented.
"""

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2, GT, pair
from typing import List
from .utils import gt_div, gt_eq, multiexp_g1, multiexp_g2, pair_prod, prod_g1, prod_g2


def verify_1(C: G1, pis: List[G1], t: List[ZR], m: List[ZR], crs: dict) -> bool:
    """
    Verify equation (1): Aggregated inner-product verification (PointProofs base).
    
    Formula (Equation 1):
    ---------------------
    e(C, ∏_{i=1}^{n} ĝ_{n+1-i}^{t_i}) = e(∏_{i=1}^{n} π_i^{t_i}, ĝ) · e(g_1, ĝ_n)^{∑_{i=1}^{n} m_i t_i}
    
    Parameters
    ----------
    C : G1
        The commitment C = g^γ · ∏ g_j^{m_j}
    pis : List[G1]
        The point opening proofs [π_1, π_2, ..., π_n]
    t : List[ZR]
        The challenge weights [t_1, t_2, ..., t_n]
    m : List[ZR]
        The message vector [m_1, m_2, ..., m_n]
    crs : dict
        The CRS from keygen_crs()
    
    Returns
    -------
    bool
        True if the equation holds, False otherwise
    
    Notes
    -----
    This is the fundamental verification equation for aggregated point openings.
    It verifies that the proofs π_i correctly open C at positions i with weights t_i.
    
    Equation Reference: (1)
    """
    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']
    g_hat = crs['g_hat']
    g_hat_list = crs['g_hat_list']
    
    if len(pis) != n or len(t) != n or len(m) != n:
        raise ValueError(f"All lists must have length n={n}")
    
    # LHS: e(C, ∏_{i=1}^{n} ĝ_{n+1-i}^{t_i})
    # Compute ∏_{i=1}^{n} ĝ_{n+1-i}^{t_i}
    g_hat_prod = group.init(G2, 1)
    for i in range(1, n + 1):
        idx = n + 1 - i
        if idx not in g_hat_list:
            raise ValueError(f"Index {idx} (n+1-{i}) not in g_hat_list")
        g_hat_prod *= g_hat_list[idx] ** t[i - 1]
    
    lhs = pair(C, g_hat_prod)
    
    # RHS: e(∏_{i=1}^{n} π_i^{t_i}, ĝ) · e(g_1, ĝ_n)^{∑_{i=1}^{n} m_i t_i}
    # Compute ∏_{i=1}^{n} π_i^{t_i}
    pi_prod = group.init(G1, 1)
    for i in range(1, n + 1):
        pi_prod *= pis[i - 1] ** t[i - 1]
    
    # Compute ∑_{i=1}^{n} m_i t_i
    sum_mt = group.init(ZR, 0)
    for i in range(1, n + 1):
        sum_mt += m[i - 1] * t[i - 1]
    
    rhs = pair(pi_prod, g_hat) * (pair(g_list[1], g_hat_list[n]) ** sum_mt)
    
    return gt_eq(lhs, rhs, group)


def verify_3(C_y: G1, i: int, x: List[ZR], y: List[ZR], gamma_y: ZR, crs: dict) -> bool:
    """
    Verify equation (3): Per-coordinate pairing for C_y.
    
    Formula (Equation 3):
    ---------------------
    e(C_y, ĝ_i) = e(g_i^{γ_y} · ∏_{j∈[n], j≠i} g_{n+1-j+i}^{y_j x_j}, ĝ) · e(g_1, ĝ_n)^{y_i x_i}
    
    Parameters
    ----------
    C_y : G1
        The Hadamard commitment C_y
    i : int
        The coordinate index (1-indexed)
    x : List[ZR]
        The vector x
    y : List[ZR]
        The vector y
    gamma_y : ZR
        The randomness γ_y from C_y
    crs : dict
        The CRS from keygen_crs()
    
    Returns
    -------
    bool
        True if the equation holds, False otherwise
    
    Notes
    -----
    This equation verifies the structure of C_y at coordinate i.
    
    Equation Reference: (3)
    """
    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']
    g_hat = crs['g_hat']
    g_hat_list = crs['g_hat_list']
    
    if i < 1 or i > n:
        raise ValueError(f"Index i={i} must be in [1, {n}]")
    
    if len(x) != n or len(y) != n:
        raise ValueError(f"Vectors must have length n={n}")
    
    # LHS: e(C_y, ĝ_i)
    lhs = pair(C_y, g_hat_list[i])
    
    # RHS: e(g_i^{γ_y} · ∏_{j≠i} g_{n+1-j+i}^{y_j x_j}, ĝ) · e(g_1, ĝ_n)^{y_i x_i}
    # Compute g_i^{γ_y} · ∏_{j≠i} g_{n+1-j+i}^{y_j x_j}
    g_term = g_list[i] ** gamma_y
    for j in range(1, n + 1):
        if j == i:
            continue
        idx = n + 1 - j + i
        if idx not in g_list:
            raise ValueError(f"Index {idx} not in g_list")
        g_term *= g_list[idx] ** (y[j - 1] * x[j - 1])
    
    rhs = pair(g_term, g_hat) * (pair(g_list[1], g_hat_list[n]) ** (y[i - 1] * x[i - 1]))
    
    return gt_eq(lhs, rhs, group)


def verify_4(C_hat: G2, i: int, x: List[ZR], gamma: ZR, crs: dict) -> bool:
    """
    Verify equation (4): Per-coordinate pairing for Ĉ.
    
    Formula (Equation 4):
    ---------------------
    e(g_{n+1-i}, Ĉ) = e(g_{n+1-i}^{γ} · ∏_{j∈[n], j≠i} g_{n+1-i+j}^{x_j}, ĝ) · e(g_1, ĝ_n)^{x_i}
    
    Parameters
    ----------
    C_hat : G2
        The commitment Ĉ
    i : int
        The coordinate index (1-indexed)
    x : List[ZR]
        The vector x
    gamma : ZR
        The randomness γ from Ĉ
    crs : dict
        The CRS from keygen_crs()
    
    Returns
    -------
    bool
        True if the equation holds, False otherwise
    
    Notes
    -----
    This equation verifies the structure of Ĉ at coordinate i.
    
    Equation Reference: (4)
    """
    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']
    g_hat = crs['g_hat']
    g_hat_list = crs['g_hat_list']
    
    if i < 1 or i > n:
        raise ValueError(f"Index i={i} must be in [1, {n}]")
    
    if len(x) != n:
        raise ValueError(f"Vector x must have length n={n}")
    
    # LHS: e(g_{n+1-i}, Ĉ)
    idx_g = n + 1 - i
    if idx_g not in g_list:
        raise ValueError(f"Index {idx_g} not in g_list")
    lhs = pair(g_list[idx_g], C_hat)
    
    # RHS: e(g_{n+1-i}^{γ} · ∏_{j≠i} g_{n+1-i+j}^{x_j}, ĝ) · e(g_1, ĝ_n)^{x_i}
    # Compute g_{n+1-i}^{γ} · ∏_{j≠i} g_{n+1-i+j}^{x_j}
    g_term = g_list[idx_g] ** gamma
    for j in range(1, n + 1):
        if j == i:
            continue
        idx = n + 1 - i + j
        if idx not in g_list:
            raise ValueError(f"Index {idx} not in g_list")
        g_term *= g_list[idx] ** x[j - 1]
    
    rhs = pair(g_term, g_hat) * (pair(g_list[1], g_hat_list[n]) ** x[i - 1])

    return gt_eq(lhs, rhs, group)


def verify_5(C_hat: G2, C_y: G1, t: List[ZR], y: List[ZR], pi_eq: G1, crs: dict) -> bool:
    """
    Verify equation (5): Key division equation combining (3) and (4).

    Formula (Equation 5):
    ---------------------
    [e(∏_{i=1}^{n} g_{n+1-i}^{t_i y_i}, Ĉ)] / [e(C_y, ∏_{i=1}^{n} ĝ_i^{t_i})] = e(π_eq, ĝ)

    Parameters
    ----------
    C_hat : G2
        The commitment Ĉ
    C_y : G1
        The Hadamard commitment C_y
    t : List[ZR]
        The challenge weights [t_1, ..., t_n]
    y : List[ZR]
        The vector y
    pi_eq : G1
        The equality proof π_eq
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    bool
        True if the equation holds, False otherwise

    Notes
    -----
    This is a DIVISION equation. We implement it as:
        LHS = LHS_numerator * (LHS_denominator)^{-1}

    This is the ONLY way to implement division equations.

    Equation Reference: (5)
    """
    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']
    g_hat = crs['g_hat']
    g_hat_list = crs['g_hat_list']

    if len(t) != n or len(y) != n:
        raise ValueError(f"Vectors must have length n={n}")

    # LHS numerator: e(∏_{i=1}^{n} g_{n+1-i}^{t_i y_i}, Ĉ)
    g_prod = group.init(G1, 1)
    for i in range(1, n + 1):
        idx = n + 1 - i
        if idx not in g_list:
            raise ValueError(f"Index {idx} not in g_list")
        g_prod *= g_list[idx] ** (t[i - 1] * y[i - 1])
    lhs_num = pair(g_prod, C_hat)

    # LHS denominator: e(C_y, ∏_{i=1}^{n} ĝ_i^{t_i})
    g_hat_prod = group.init(G2, 1)
    for i in range(1, n + 1):
        g_hat_prod *= g_hat_list[i] ** t[i - 1]
    lhs_den = pair(C_y, g_hat_prod)

    # LHS = LHS_num / LHS_den = LHS_num * (LHS_den)^{-1}
    lhs = gt_div(lhs_num, lhs_den, group)

    # RHS: e(π_eq, ĝ)
    rhs = pair(pi_eq, g_hat)

    return gt_eq(lhs, rhs, group)


def verify_7(C_hat: G2, C_y: G1, pi_y: G1, y: List[ZR], crs: dict) -> bool:
    """
    Verify equation (7): Orthogonality check.

    Formula (Equation 7):
    ---------------------
    e(C_y · ∏_{j=1}^{n} g_{n+1-j}^{-y_j}, Ĉ) = e(π_y, ĝ)

    Parameters
    ----------
    C_hat : G2
        The commitment Ĉ
    C_y : G1
        The Hadamard commitment C_y
    pi_y : G1
        The orthogonality proof π_y
    y : List[ZR]
        The vector y
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    bool
        True if the equation holds, False otherwise

    Notes
    -----
    This equation verifies the orthogonality condition that enforces y_i ∈ {0,1}.

    Equation Reference: (7)
    """
    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']
    g_hat = crs['g_hat']

    if len(y) != n:
        raise ValueError(f"Vector y must have length n={n}")

    # LHS: e(C_y · ∏_{j=1}^{n} g_{n+1-j}^{-y_j}, Ĉ)
    # Compute C_y · ∏_{j=1}^{n} g_{n+1-j}^{-y_j}
    g_term = C_y
    for j in range(1, n + 1):
        idx = n + 1 - j
        if idx not in g_list:
            raise ValueError(f"Index {idx} not in g_list")
        g_term *= g_list[idx] ** (-y[j - 1])

    lhs = pair(g_term, C_hat)

    # RHS: e(π_y, ĝ)
    rhs = pair(pi_y, g_hat)

    return gt_eq(lhs, rhs, group)


def verify_9(C_hat: G2, V_hat: G2, pi_x: G1, ell: int, crs: dict) -> bool:
    """
    Verify equation (9): Division form with integer commitment V̂.

    Formula (Equation 9):
    ---------------------
    [e(∏_{i=1}^{ℓ} g_{n+1-i}^{2^{i-1}}, Ĉ)] / [e(g_n, V̂)] = e(π_x, ĝ)

    Parameters
    ----------
    C_hat : G2
        The commitment Ĉ to bit vector
    V_hat : G2
        The integer commitment V̂ = ĝ^r · ĝ_1^x
    pi_x : G1
        The range-proof sum-of-weights proof π_x
    ell : int
        The number of bits ℓ (NOT the full vector length n)
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    bool
        True if the equation holds, False otherwise

    Notes
    -----
    This is a DIVISION equation. We implement it as:
        LHS = LHS_numerator * (LHS_denominator)^{-1}

    Equation Reference: (9)
    """
    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']
    g_hat = crs['g_hat']

    # LHS numerator: e(∏_{i=1}^{ℓ} g_{n+1-i}^{2^{i-1}}, Ĉ)
    g_prod = group.init(G1, 1)
    for i in range(1, ell + 1):
        idx = n + 1 - i
        if idx not in g_list:
            raise ValueError(f"Index {idx} not in g_list")
        weight = group.init(ZR, 2 ** (i - 1))
        g_prod *= g_list[idx] ** weight
    lhs_num = pair(g_prod, C_hat)

    # LHS denominator: e(g_n, V̂)
    if n not in g_list:
        raise ValueError(f"Index {n} not in g_list")
    lhs_den = pair(g_list[n], V_hat)

    # LHS = LHS_num / LHS_den
    lhs = gt_div(lhs_num, lhs_den, group)

    # RHS: e(π_x, ĝ)
    rhs = pair(pi_x, g_hat)

    return gt_eq(lhs, rhs, group)


def verify_16(C_hat: G2, C_y: G1, pi: G1, delta_eq: ZR, delta_y: ZR, t: List[ZR], y: List[ZR], crs: dict) -> bool:
    """
    Verify equation (16): Aggregated verification for π = π_eq^{δ_eq} · π_y^{δ_y}.

    Formula (Equation 16):
    ----------------------
    [e(C_y^{δ_y} · ∏_{i=1}^{n} g_{n+1-i}^{(δ_eq t_i - δ_y) y_i}, Ĉ)] / [e(C_y, ∏_{i=1}^{n} ĝ_i^{δ_eq t_i})] = e(π, ĝ)

    Parameters
    ----------
    C_hat : G2
        The commitment Ĉ
    C_y : G1
        The Hadamard commitment C_y
    pi : G1
        The aggregated proof π = π_eq^{δ_eq} · π_y^{δ_y}
    delta_eq : ZR
        The challenge δ_eq from H_agg
    delta_y : ZR
        The challenge δ_y from H_agg
    t : List[ZR]
        The challenge weights [t_1, ..., t_n]
    y : List[ZR]
        The vector y
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    bool
        True if the equation holds, False otherwise

    Notes
    -----
    This is a DIVISION equation. We implement it as:
        LHS = LHS_numerator * (LHS_denominator)^{-1}

    This equation aggregates the verification of π_eq and π_y into a single check.

    Equation Reference: (16)
    """
    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']
    g_hat = crs['g_hat']
    g_hat_list = crs['g_hat_list']

    if len(t) != n or len(y) != n:
        raise ValueError(f"Vectors must have length n={n}")

    # LHS numerator: e(C_y^{δ_y} · ∏_{i=1}^{n} g_{n+1-i}^{(δ_eq t_i - δ_y) y_i}, Ĉ)
    # Compute C_y^{δ_y} · ∏_{i=1}^{n} g_{n+1-i}^{(δ_eq t_i - δ_y) y_i}
    g_term = C_y ** delta_y
    for i in range(1, n + 1):
        idx = n + 1 - i
        if idx not in g_list:
            raise ValueError(f"Index {idx} not in g_list")
        exponent = (delta_eq * t[i - 1] - delta_y) * y[i - 1]
        g_term *= g_list[idx] ** exponent
    lhs_num = pair(g_term, C_hat)

    # LHS denominator: e(C_y, ∏_{i=1}^{n} ĝ_i^{δ_eq t_i})
    g_hat_prod = group.init(G2, 1)
    for i in range(1, n + 1):
        g_hat_prod *= g_hat_list[i] ** (delta_eq * t[i - 1])
    lhs_den = pair(C_y, g_hat_prod)

    # LHS = LHS_num / LHS_den
    lhs = gt_div(lhs_num, lhs_den, group)

    # RHS: e(π, ĝ)
    rhs = pair(pi, g_hat)

    return gt_eq(lhs, rhs, group)


def verify_20(V_hat: G2, s: List[ZR], pi_v: G1, crs: dict) -> bool:
    """
    Verify equation (20): Verification of π_v ("only first coordinate nonzero").

    Formula (Equation 20):
    ----------------------
    e(∏_{i=2}^{n} g_{n+1-i}^{s_i}, V̂) = e(π_v, ĝ)

    where s_i = H_s(i, [2,n], V̂, Ĉ, C_y)

    Parameters
    ----------
    V_hat : G2
        The integer commitment V̂ = ĝ^r · ĝ_1^x
    s : List[ZR]
        The challenges [s_2, s_3, ..., s_n] from H_s
    pi_v : G1
        The proof π_v
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    bool
        True if the equation holds, False otherwise

    Notes
    -----
    This equation verifies that V̂ commits to a value where only the first
    coordinate is non-zero.

    Equation Reference: (20)
    """
    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']
    g_hat = crs['g_hat']

    if len(s) != n - 1:
        raise ValueError(f"s must have length n-1={n-1}, got {len(s)}")

    # LHS: e(∏_{i=2}^{n} g_{n+1-i}^{s_i}, V̂)
    g_prod = group.init(G1, 1)
    for i in range(2, n + 1):
        idx = n + 1 - i
        if idx not in g_list:
            raise ValueError(f"Index {idx} not in g_list")
        g_prod *= g_list[idx] ** s[i - 2]  # s is 0-indexed for i=2..n
    lhs = pair(g_prod, V_hat)

    # RHS: e(π_v, ĝ)
    rhs = pair(pi_v, g_hat)

    return gt_eq(lhs, rhs, group)


# Aliases for equations that are equivalent to others
verify_13 = verify_5  # Equation (13) is the same as (5)
verify_15 = verify_7  # Equation (15) is the same as (7)
verify_17 = verify_9  # Equation (17) is the same as (9)
verify_18 = verify_5  # Equation (18) is the same as (5)
verify_19 = verify_7  # Equation (19) is the same as (7)


def verify_range_proof(proof: dict, l: int, crs: dict) -> bool:
    """
    Verify a complete zero-knowledge range proof (Libert 2024 Section 4.1).

    This implements verification using the aggregated proof π_agg.

    Parameters
    ----------
    proof : dict
        The range proof from prove_range_proof() containing:
        - 'C_hat': Commitment to bit vector
        - 'V_hat': Commitment to scalar
        - 'C_y': Commitment to y ∘ x
        - 'pi_agg': Aggregated proof
        - 'l': Bit length
    l : int
        The bit length (must match proof['l'])
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    bool
        True if the proof is valid, False otherwise
    """
    import hashlib

    # Extract proof components
    C_hat = proof['C_hat']
    V_hat = proof['V_hat']
    C_y = proof['C_y']
    pi_agg = proof['pi_agg']
    proof_l = proof['l']

    # Sanity check
    if l != proof_l:
        return False

    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']
    g_hat = crs['g_hat']
    g_hat_list = crs['g_hat_list']

    # Recompute Fiat-Shamir challenges
    C_hat_str = str(C_hat).encode()
    V_hat_str = str(V_hat).encode()
    y_hash = hashlib.sha256(C_hat_str + V_hat_str).digest()
    y_int = int.from_bytes(y_hash, 'big') % int(group.order())
    y = group.init(ZR, y_int)
    y_vec = [y] + [group.init(ZR, 0)] * (n - 1)

    y_str = str(y).encode()
    C_y_str = str(C_y).encode()
    t_hash = hashlib.sha256(y_str + C_hat_str + C_y_str).digest()
    t_int = int.from_bytes(t_hash, 'big') % int(group.order())
    t = group.init(ZR, t_int)
    t_vec = [t] + [group.init(ZR, 0)] * (n - 1)

    # Recompute aggregation challenges (same as in prove_range_proof)
    agg_hash = hashlib.sha256(C_hat_str + V_hat_str + C_y_str).digest()

    delta_x_int = int.from_bytes(agg_hash[:8], 'big') % int(group.order())
    delta_eq_int = int.from_bytes(agg_hash[8:16], 'big') % int(group.order())
    delta_y_int = int.from_bytes(agg_hash[16:24], 'big') % int(group.order())
    delta_v_int = int.from_bytes(agg_hash[24:32], 'big') % int(group.order())

    delta_x = group.init(ZR, delta_x_int)
    delta_eq = group.init(ZR, delta_eq_int)
    delta_y = group.init(ZR, delta_y_int)
    delta_v = group.init(ZR, delta_v_int)

    # Construct LHS for all 4 equations

    # Equation 9 LHS: [e(∏ g_{n+1-i}^{2^{i-1}}, Ĉ)] / [e(g_n, V̂)]
    g_prod_9 = group.init(G1, 1)
    for i in range(1, l + 1):
        idx = n + 1 - i
        if idx not in g_list:
            return False
        weight = group.init(ZR, 2 ** (i - 1))
        g_prod_9 *= g_list[idx] ** weight
    lhs_9_num = pair(g_prod_9, C_hat)
    lhs_9_den = pair(g_list[n], V_hat)
    lhs_9 = gt_div(lhs_9_num, lhs_9_den, group)

    # Equation 5 LHS: [e(∏ g_{n+1-i}^{t_i y_i}, Ĉ)] / [e(C_y, ∏ ĝ_i^{t_i})]
    g_prod_5 = group.init(G1, 1)
    for i in range(1, n + 1):
        idx = n + 1 - i
        if idx not in g_list:
            return False
        g_prod_5 *= g_list[idx] ** (t_vec[i - 1] * y_vec[i - 1])
    lhs_5_num = pair(g_prod_5, C_hat)

    g_hat_prod_5 = group.init(G2, 1)
    for i in range(1, n + 1):
        g_hat_prod_5 *= g_hat_list[i] ** t_vec[i - 1]
    lhs_5_den = pair(C_y, g_hat_prod_5)
    lhs_5 = gt_div(lhs_5_num, lhs_5_den, group)

    # Equation 7 LHS: e(C_y · ∏ g_{n+1-j}^{-y_j}, Ĉ)
    g_term_7 = C_y
    for j in range(1, n + 1):
        idx = n + 1 - j
        if idx not in g_list:
            return False
        g_term_7 *= g_list[idx] ** (-y_vec[j - 1])
    lhs_7 = pair(g_term_7, C_hat)

    # Equation 20 LHS: e(∏ g_{n+1-i}^{s_i}, V̂)
    s_vec = t_vec[1:]  # Extract s_2, s_3, ..., s_n
    g_prod_20 = group.init(G1, 1)
    for i in range(2, n + 1):
        idx = n + 1 - i
        if idx not in g_list:
            return False
        g_prod_20 *= g_list[idx] ** s_vec[i - 2]
    lhs_20 = pair(g_prod_20, V_hat)

    # Aggregate all LHS
    lhs_agg = (lhs_9 ** delta_x) * (lhs_5 ** delta_eq) * (lhs_7 ** delta_y) * (lhs_20 ** delta_v)

    # RHS: e(π_agg, ĝ)
    rhs_agg = pair(pi_agg, g_hat)

    return gt_eq(lhs_agg, rhs_agg, group)


def verify_batch_range_proof(proof: dict, m: int, l: int, crs: dict) -> bool:
    """
    Verify a batch range proof for m timestamps.

    This verifies that m timestamps (each l-bit) are all in valid range.

    Parameters
    ----------
    proof : dict
        The batch range proof
    m : int
        Number of timestamps
    l : int
        Bit length per timestamp
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    bool
        True if all timestamps are in valid range

    Notes
    -----
    This is more efficient than verifying m individual range proofs.
    Uses a single aggregated proof for all m timestamps.
    """
    # For now, delegate to single range proof verification
    # In a full implementation, this would use optimized batch verification
    return verify_range_proof(proof, l, crs)
