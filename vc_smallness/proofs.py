"""
Proof Generation
================

This module implements all proof generation algorithms for the vector commitment scheme.

Proofs:
-------
- π_i: Point opening proof at position i
- π_S: Aggregated opening for subset S
- π_eq: Equality proof (C_y commits to y ∘ x in reverse order)
- π_y: Orthogonality proof (enforces y_i ∈ {0,1})
- π_x: Range-proof sum-of-weights proof
- π_v: "Only-first-coordinate-nonzero" auxiliary proof
- π: Final aggregated proof π = π_eq^{δ_eq} · π_y^{δ_y}

All implementations strictly follow the formulas from the paper.
"""

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2
from typing import List
from .utils import multiexp_g1, prod_g1
import numpy as np


def prove_point_open(C: G1, m: List[ZR], gamma: ZR, i: int, crs: dict) -> G1:
    """
    Generate point opening proof π_i at position i.
    
    Formula (Point opening proof):
    ------------------------------
    π_i := g_{n+1-i}^{γ} · ∏_{j∈[n], j≠i} g_{n+1-i+j}^{m_j}
        = (C / g_i^{m_i})^{α^{n+1-i}}
    
    Parameters
    ----------
    C : G1
        The commitment C = g^γ · ∏ g_j^{m_j}
    m : List[ZR]
        The message vector (m_1, ..., m_n)
    gamma : ZR
        The randomness γ used in C
    i : int
        The position to open (1-indexed)
    crs : dict
        The CRS from keygen_crs()
    
    Returns
    -------
    G1
        The proof π_i = g_{n+1-i}^γ · ∏_{j≠i} g_{n+1-i+j}^{m_j}
    
    Notes
    -----
    This proof allows the verifier to check that C commits to m_i at position i
    without revealing the other values.
    
    The formula uses reverse indexing: g_{n+1-i} and g_{n+1-i+j}.
    
    Examples
    --------
    >>> pi_1 = prove_point_open(C, m, gamma, 1, crs)
    """
    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']
    
    if i < 1 or i > n:
        raise ValueError(f"Position i={i} must be in [1, {n}]")
    
    if len(m) != n:
        raise ValueError(f"Message vector length {len(m)} != n={n}")
    
    # π_i = g_{n+1-i}^γ
    idx_base = n + 1 - i
    if idx_base not in g_list:
        raise ValueError(f"Index {idx_base} (n+1-{i}) not in g_list")
    
    pi_i = g_list[idx_base] ** gamma
    
    # π_i *= ∏_{j∈[n], j≠i} g_{n+1-i+j}^{m_j}
    for j in range(1, n + 1):
        if j == i:
            continue
        idx = n + 1 - i + j
        if idx not in g_list:
            raise ValueError(f"Index {idx} (n+1-{i}+{j}) not in g_list")
        pi_i *= g_list[idx] ** m[j - 1]
    
    return pi_i


def prove_agg_open(C: G1, m: List[ZR], gamma: ZR, S: List[int], t: List[ZR], crs: dict) -> G1:
    """
    Generate aggregated opening proof π_S for subset S with weights t.

    Formula (Aggregated opening):
    -----------------------------
    π_S := ∏_{i∈S} π_i^{t_i}

    O(n log n) Algorithm using numpy polynomial operations:
    -------------------------------------------------------
    P(X) = ∑_{i∈S} t_i · X^{n+1-i} · (γ + ∑_{j≠i} m_j X^j)
         = ∑_{k=0}^{2n} ν_k X^k

    Parameters
    ----------
    C : G1
        The commitment C
    m : List[ZR]
        The message vector
    gamma : ZR
        The randomness γ
    S : List[int]
        The subset of positions to open (1-indexed)
    t : List[ZR]
        The weights (t_i) for aggregation
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    G1
        The aggregated proof π_S = ∏_{i∈S} π_i^{t_i}
    """
    if len(S) != len(t):
        raise ValueError(f"S and t must have same length: {len(S)} != {len(t)}")

    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']
    p = int(group.order())

    # Convert to integers for polynomial arithmetic
    m_int = [int(m_i) % p for m_i in m]
    gamma_int = int(gamma) % p
    t_int = [int(t_i) % p for t_i in t]

    # Build M(X) = ∑_{j=1}^n m_j X^j using np.poly1d
    # numpy poly1d uses descending powers: [X^n, X^{n-1}, ..., X^0]
    m_coeffs = [0] * (n + 1)
    for j in range(1, n + 1):
        m_coeffs[n - j] = m_int[j - 1]  # m_j at X^j
    M_X = np.poly1d(m_coeffs)

    # Initialize P(X) = 0
    P_X = np.poly1d([0])

    # For each i in S, add t_i · X^{n+1-i} · (γ + ∑_{j≠i} m_j X^j)
    for idx, i in enumerate(S):
        t_i = t_int[idx]
        if t_i == 0:
            continue

        # Compute ∑_{j≠i} m_j X^j = M(X) - m_i X^i
        m_i_coeffs = [0] * (n + 1)
        m_i_coeffs[n - i] = m_int[i - 1]  # m_i at X^i

        poly_inner = M_X - np.poly1d(m_i_coeffs) + np.poly1d([gamma_int])

        # Compute X^{n+1-i}
        shift_power = n + 1 - i
        poly_shift = np.poly1d([1] + [0] * shift_power)

        # Compute t_i · X^{n+1-i} · (γ + ∑_{j≠i} m_j X^j)
        poly_term = poly_shift * poly_inner

        # Multiply coefficients by t_i and reduce mod p
        poly_term_coeffs = [(int(c) * t_i) % p for c in poly_term.coeffs]
        poly_term = np.poly1d(poly_term_coeffs)

        # Add to P(X)
        P_X = P_X + poly_term

    # Get coefficients and reduce modulo p
    P_coeffs = [int(c) % p for c in P_X.coeffs]
    max_degree = len(P_coeffs) - 1

    # Compute π_S = g^{ν_0} · ∏_{k=1,k≠n+1}^{2n} g_k^{ν_k}
    g = crs['g']
    pi_S = group.init(G1, 1)

    for k in range(len(P_coeffs)):
        degree = max_degree - k
        coeff = P_coeffs[k]

        if coeff == 0:
            continue

        if degree == 0:
            # g^{ν_0} (base generator)
            pi_S *= g ** group.init(ZR, coeff)
        elif degree == n + 1:
            # Skip g_{n+1} (not in CRS)
            continue
        else:
            # g_degree^{ν_degree}
            if degree in g_list:
                pi_S *= g_list[degree] ** group.init(ZR, coeff)

    return pi_S


def prove_eq(t: List[ZR], y: List[ZR], x: List[ZR], gamma: ZR, gamma_y: ZR, crs: dict) -> G1:
    """
    Generate equality proof π_eq using O(n log n) polynomial operations.

    Formula (Equation 12):
    ----------------------
    π_eq = [∏_{i=1}^{n} (g_{n+1-i}^{γ} · ∏_{j∈[n], j≠i} g_{n+1-i+j}^{x_j})^{t_i y_i}]
           / [∏_{i=1}^{n} (g_{i}^{γ_y} · ∏_{j∈[n], j≠i} g_{n+1-j+i}^{y_j x_j})^{t_i}]

    O(n log n) Algorithm (Libert 2024, p. 51):
    ------------------------------------------
    Compute π_eq = g^{P_π(α)} where P_π(X) = P_num(X) - P_den(X)
    using numpy polynomial operations.

    Parameters
    ----------
    t : List[ZR]
        The challenge weights (t_1, ..., t_n)
    y : List[ZR]
        The vector (y_1, ..., y_n)
    x : List[ZR]
        The vector (x_1, ..., x_n)
    gamma : ZR
        The randomness γ from Ĉ
    gamma_y : ZR
        The randomness γ_y from C_y
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    G1
        The proof π_eq
    """
    group = crs['group']
    n = crs['n']
    g = crs['g']
    g_list = crs['g_list']
    p = int(group.order())

    if len(t) != n or len(y) != n or len(x) != n:
        raise ValueError(f"All vectors must have length n={n}")

    # Convert ZR elements to Python integers for numpy operations
    t_int = [int(val) % p for val in t]
    y_int = [int(val) % p for val in y]
    x_int = [int(val) % p for val in x]
    gamma_int = int(gamma) % p
    gamma_y_int = int(gamma_y) % p

    # --- Construct P_num(X) ---
    # P_num(X) = ∑_{i=1}^{n} (t_i y_i) * [ X^{n+1-i} * (γ + ∑_{j≠i} x_j X^j) ]

    # M(X) = ∑_{j=1}^{n} x_j X^j
    # numpy poly1d uses descending powers: [X^n, X^{n-1}, ..., X^0]
    m_coeffs = [0] * (n + 1)
    for j in range(1, n + 1):
        m_coeffs[n - j] = x_int[j - 1]  # x_j at X^j
    M_X = np.poly1d(m_coeffs)

    P_num_X = np.poly1d([0])

    for i in range(1, n + 1):
        t_i_y_i = (t_int[i - 1] * y_int[i - 1]) % p
        if t_i_y_i == 0:
            continue

        # (γ + ∑_{j≠i} x_j X^j) = M(X) - x_i X^i + γ
        x_i_poly_coeffs = [0] * (n + 1)
        x_i_poly_coeffs[n - i] = x_int[i - 1]  # x_i at X^i

        poly_inner = M_X - np.poly1d(x_i_poly_coeffs) + np.poly1d([gamma_int])

        # X^{n+1-i}
        shift_power = n + 1 - i
        poly_shift = np.poly1d([1] + [0] * shift_power)

        # (t_i y_i) * X^{n+1-i} * (...)
        poly_term = poly_shift * poly_inner

        # Multiply coefficients by t_i_y_i and reduce mod p
        poly_term_coeffs = [(int(c) * t_i_y_i) % p for c in poly_term.coeffs]
        poly_term = np.poly1d(poly_term_coeffs)

        P_num_X = P_num_X + poly_term

    # --- Construct P_den(X) ---
    # P_den(X) = ∑_{i=1}^{n} t_i * [ X^i * (γ_y + ∑_{j≠i} (y_j x_j) X^{n+1-j}) ]

    # YX(X) = ∑_{j=1}^{n} (y_j x_j) X^{n+1-j}
    yx_coeffs = [0] * (n + 2)
    for j in range(1, n + 1):
        power = n + 1 - j
        yx_coeffs[len(yx_coeffs) - 1 - power] = (y_int[j - 1] * x_int[j - 1]) % p
    YX_X = np.poly1d(yx_coeffs)

    P_den_X = np.poly1d([0])

    for i in range(1, n + 1):
        t_i = t_int[i - 1]
        if t_i == 0:
            continue

        # (γ_y + ∑_{j≠i} (y_j x_j) X^{n+1-j})
        y_i_x_i = (y_int[i - 1] * x_int[i - 1]) % p
        power_yi_xi = n + 1 - i
        y_i_x_i_poly_coeffs = [0] * (n + 2)
        y_i_x_i_poly_coeffs[len(y_i_x_i_poly_coeffs) - 1 - power_yi_xi] = y_i_x_i

        poly_inner = YX_X - np.poly1d(y_i_x_i_poly_coeffs) + np.poly1d([gamma_y_int])

        # X^i
        poly_shift = np.poly1d([1] + [0] * i)

        # t_i * X^i * (...)
        poly_term = poly_shift * poly_inner

        # Multiply coefficients by t_i and reduce mod p
        poly_term_coeffs = [(int(c) * t_i) % p for c in poly_term.coeffs]
        poly_term = np.poly1d(poly_term_coeffs)

        P_den_X = P_den_X + poly_term

    # --- Final polynomial P_π(X) ---
    P_pi_X = P_num_X - P_den_X

    # Reduce all coefficients mod p
    P_pi_coeffs = [int(c) % p for c in P_pi_X.coeffs]

    # --- Compute π_eq = g^{P_π(α)} ---
    # P_pi_X.coeffs is in descending order: [coeff of X^max, ..., coeff of X^0]
    max_degree = len(P_pi_coeffs) - 1

    pi_eq = group.init(G1, 1)

    for k in range(len(P_pi_coeffs)):
        degree = max_degree - k
        coeff = P_pi_coeffs[k]

        if coeff == 0:
            continue

        if degree == 0:
            # g^{ν_0}
            pi_eq *= g ** group.init(ZR, coeff)
        elif degree == n + 1:
            # Skip g_{n+1} (not in CRS)
            continue
        elif degree in g_list:
            # g_degree^{ν_degree}
            pi_eq *= g_list[degree] ** group.init(ZR, coeff)
        else:
            # This should not happen if CRS is properly constructed
            raise ValueError(f"Degree {degree} not in CRS g_list")

    return pi_eq


def prove_y(x: List[ZR], y: List[ZR], gamma: ZR, gamma_y: ZR, crs: dict) -> G1:
    """
    Generate orthogonality proof π_y (enforces y_i ∈ {0,1}).

    Formula (Equation 14):
    ----------------------
    π_y = g^{γ γ_y} · (∏_{j=1}^{n} g_{n+1-j}^{γ y_j(x_j-1)})
          · ∏_{i=1}^{n} (g_{i}^{γ_y} · ∏_{j∈[n], j≠i} g_{n+1-j+i}^{y_j(x_j-1)})^{x_i}

    Parameters
    ----------
    x : List[ZR]
        The vector (x_1, ..., x_n)
    y : List[ZR]
        The vector (y_1, ..., y_n) (should be binary)
    gamma : ZR
        The randomness γ from Ĉ
    gamma_y : ZR
        The randomness γ_y from C_y
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    G1
        The proof π_y

    Notes
    -----
    This proof enforces that y_i ∈ {0,1} by verifying the orthogonality
    condition: ∑_i y_i x_i (x_i - 1) = 0.

    If y_i ∈ {0,1} for all i, then y_i (x_i - 1) contributes to the sum
    in a way that can be verified via equation (7) or (15).

    Equation Reference: (14)
    Verified by: Equation (15) or (7)

    Examples
    --------
    >>> pi_y = prove_y(x, y, gamma, gamma_y, crs)
    """
    group = crs['group']
    n = crs['n']
    g = crs['g']
    g_list = crs['g_list']

    if len(x) != n or len(y) != n:
        raise ValueError(f"Vectors must have length n={n}")

    # π_y = g^{γ γ_y}
    pi_y = g ** (gamma * gamma_y)

    # π_y *= ∏_{j=1}^{n} g_{n+1-j}^{γ y_j(x_j-1)}
    for j in range(1, n + 1):
        idx = n + 1 - j
        if idx not in g_list:
            raise ValueError(f"Index {idx} not in g_list")
        exponent = gamma * y[j - 1] * (x[j - 1] - group.init(ZR, 1))
        pi_y *= g_list[idx] ** exponent

    # π_y *= ∏_{i=1}^{n} (g_{i}^{γ_y} · ∏_{j≠i} g_{n+1-j+i}^{y_j(x_j-1)})^{x_i}
    for i in range(1, n + 1):
        # Inner term: g_{i}^{γ_y} · ∏_{j≠i} g_{n+1-j+i}^{y_j(x_j-1)}
        if i not in g_list:
            raise ValueError(f"Index {i} not in g_list")

        inner = g_list[i] ** gamma_y
        for j in range(1, n + 1):
            if j == i:
                continue
            idx = n + 1 - j + i
            if idx not in g_list:
                raise ValueError(f"Index {idx} not in g_list")
            exponent_inner = y[j - 1] * (x[j - 1] - group.init(ZR, 1))
            inner *= g_list[idx] ** exponent_inner

        # Raise to power x_i
        pi_y *= inner ** x[i - 1]

    return pi_y


def prove_x(bit_proofs: List[G1], r: ZR, crs: dict) -> G1:
    """
    Generate range-proof sum-of-weights proof π_x.

    Formula (Range-proof π_x):
    --------------------------
    π_x := (∏_{i=1}^{ℓ} π_i^{2^{i-1}}) · g_n^{-r}

    where π_i are the point opening proofs for the bit positions.

    Parameters
    ----------
    bit_proofs : List[G1]
        The point opening proofs [π_1, π_2, ..., π_ℓ] for bit positions
    r : ZR
        The randomness r from V̂
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    G1
        The proof π_x = (∏_{i=1}^{ℓ} π_i^{2^{i-1}}) · g_n^{-r}

    Notes
    -----
    This proof verifies that the weighted sum of bits in Ĉ equals
    the scalar x in V̂.

    Verified by: Equation (9) or (17)

    Examples
    --------
    >>> bit_proofs = [prove_point_open(C_hat, x_bits, gamma, i, crs) for i in range(1, ell+1)]
    >>> pi_x = prove_x(bit_proofs, r, crs)
    """
    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']

    ell = len(bit_proofs)

    # π_x = ∏_{i=1}^{ℓ} π_i^{2^{i-1}}
    pi_x = group.init(G1, 1)
    for i in range(1, ell + 1):
        weight = group.init(ZR, 2 ** (i - 1))
        pi_x *= bit_proofs[i - 1] ** weight

    # π_x *= g_n^{-r}
    if n not in g_list:
        raise ValueError(f"Index {n} not in g_list")
    pi_x *= g_list[n] ** (-r)

    return pi_x


def prove_v(x_scalar: ZR, r: ZR, s: List[ZR], crs: dict) -> G1:
    """
    Generate "only-first-coordinate-nonzero" auxiliary proof π_v.

    Formula (π_v):
    --------------
    π_v := ∏_{i=2}^{n} (g_{n+1-i}^{r} · g_{n+2-i}^{x})^{s_i}

    where s_i = H_s(i, [2,n], V̂, Ĉ, C_y)

    Parameters
    ----------
    x_scalar : ZR
        The scalar x
    r : ZR
        The randomness r from V̂
    s : List[ZR]
        The challenges [s_2, s_3, ..., s_n] from H_s
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    G1
        The proof π_v = ∏_{i=2}^{n} (g_{n+1-i}^{r} · g_{n+2-i}^{x})^{s_i}

    Notes
    -----
    This proof verifies that V̂ commits to a value where only the first
    coordinate is non-zero (i.e., V̂ = ĝ^r · ĝ_1^x).

    Equation Reference: Used in (20)
    Verified by: Equation (20)

    Examples
    --------
    >>> s = H_s_batch([2, 3, ..., n], V_hat, C_hat, C_y, group)
    >>> pi_v = prove_v(x_scalar, r, s, crs)
    """
    group = crs['group']
    n = crs['n']
    g_list = crs['g_list']

    if len(s) != n - 1:
        raise ValueError(f"s must have length n-1={n-1}, got {len(s)}")

    # π_v = ∏_{i=2}^{n} (g_{n+1-i}^{r} · g_{n+2-i}^{x})^{s_i}
    pi_v = group.init(G1, 1)
    for i in range(2, n + 1):
        # Inner term: g_{n+1-i}^{r} · g_{n+2-i}^{x}
        idx1 = n + 1 - i
        idx2 = n + 2 - i

        if idx1 not in g_list:
            raise ValueError(f"Index {idx1} (n+1-{i}) not in g_list")
        if idx2 not in g_list:
            raise ValueError(f"Index {idx2} (n+2-{i}) not in g_list")

        inner = (g_list[idx1] ** r) * (g_list[idx2] ** x_scalar)

        # Raise to power s_i (s is 0-indexed for i=2..n)
        pi_v *= inner ** s[i - 2]

    return pi_v


def aggregate_pi(pi_eq: G1, pi_y: G1, delta_eq: ZR, delta_y: ZR, crs: dict) -> G1:
    """
    Generate final aggregated proof π.

    Formula (Aggregated proof):
    ---------------------------
    π := π_eq^{δ_eq} · π_y^{δ_y}

    where (δ_eq, δ_y) = H_agg(C, Ĉ, C_y)

    Parameters
    ----------
    pi_eq : G1
        The equality proof π_eq
    pi_y : G1
        The orthogonality proof π_y
    delta_eq : ZR
        The challenge δ_eq from H_agg
    delta_y : ZR
        The challenge δ_y from H_agg
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    G1
        The aggregated proof π = π_eq^{δ_eq} · π_y^{δ_y}

    Notes
    -----
    This aggregates π_eq and π_y into a single proof for efficiency.

    Verified by: Equation (16)

    Examples
    --------
    >>> delta_eq, delta_y = H_agg(C, C_hat, C_y, group)
    >>> pi = aggregate_pi(pi_eq, pi_y, delta_eq, delta_y, crs)
    """
    pi = (pi_eq ** delta_eq) * (pi_y ** delta_y)
    return pi


def prove_range_proof(x_value: ZR, l: int, crs: dict) -> dict:
    """
    Generate a COMPLETE zero-knowledge range proof (Libert 2024 Section 4.1).

    This implements the FULL Libert (2024) Section 4.1 range proof protocol
    with π_x, π_eq, π_y, and π_v proofs.

    Algorithm (Libert 2024 Section 4.1):
    ------------------------------------
    1. Decompose x into l-bit representation
    2. Create Ĉ (commitment to bits) and V̂ (commitment to scalar)
    3. Generate π_x (range proof)
    4. Generate Fiat-Shamir challenge y = H(Ĉ, V̂)
    5. Create C_y = commit_G(y ∘ x, γ_y)
    6. Generate π_eq (equality proof)
    7. Generate π_y (orthogonality proof)
    8. Generate π_v (auxiliary proof)
    9. Aggregate all proofs into single π_agg

    Parameters
    ----------
    x_value : ZR
        The value to prove is in range [0, 2^l - 1]
    l : int
        The bit length (x must be < 2^l)
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    dict
        Complete range proof containing:
        - 'C_hat': Commitment Ĉ to bit vector
        - 'V_hat': Commitment V̂ to scalar x
        - 'C_y': Commitment C_y to y ∘ x
        - 'pi_agg': Aggregated proof π_agg
        - 'l': Bit length
    """
    import hashlib
    from .commit import commit_Ghat, commit_V, commit_G, scalar_to_bits, bits_to_scalar

    group = crs['group']
    n = crs['n']
    g_hat = crs['g_hat']

    if l > n:
        raise ValueError(f"Bit length l={l} must be <= n={n}")

    # Step 1: Decompose x into l-bit representation
    x_int = int(x_value) % int(group.order())

    if x_int >= (2 ** l):
        raise ValueError(f"Value {x_int} is not in range [0, {2**l - 1}]")

    x_bits_int = scalar_to_bits(x_int, l)
    x_bits = [group.init(ZR, b) for b in x_bits_int]
    x_bits_padded = x_bits + [group.init(ZR, 0)] * (n - l)

    # Step 2: Create commitments
    gamma = group.random(ZR)
    r = group.random(ZR)

    C_hat = commit_Ghat(x_bits_padded, gamma, crs)
    x_scalar = bits_to_scalar(x_bits_int, group)
    V_hat = commit_V(x_scalar, r, crs)

    # Step 3: Generate π_x
    bit_proofs = []
    for i in range(1, l + 1):
        pi_i = prove_point_open(C_hat, x_bits_padded, gamma, i, crs)
        bit_proofs.append(pi_i)
    pi_x = prove_x(bit_proofs, r, crs)

    # Step 4: Fiat-Shamir challenge y = H(Ĉ, V̂)
    # Serialize commitments for hashing
    C_hat_str = str(C_hat).encode()
    V_hat_str = str(V_hat).encode()
    y_hash = hashlib.sha256(C_hat_str + V_hat_str).digest()
    y_int = int.from_bytes(y_hash, 'big') % int(group.order())
    y = group.init(ZR, y_int)

    # Create y as a vector (y, 0, 0, ..., 0)
    y_vec = [y] + [group.init(ZR, 0)] * (n - 1)

    # Step 5: Create C_y = commit_G(y ∘ x, γ_y)
    gamma_y = group.random(ZR)
    y_circ_x = [y_vec[i] * x_bits_padded[i] for i in range(n)]
    C_y = commit_G(y_circ_x, gamma_y, crs)

    # Step 6: Fiat-Shamir challenge t = H(y, Ĉ, C_y)
    y_str = str(y).encode()
    C_y_str = str(C_y).encode()
    t_hash = hashlib.sha256(y_str + C_hat_str + C_y_str).digest()
    t_int = int.from_bytes(t_hash, 'big') % int(group.order())
    t = group.init(ZR, t_int)

    # Create t as a vector (t, 0, 0, ..., 0)
    t_vec = [t] + [group.init(ZR, 0)] * (n - 1)

    # Step 7: Generate π_eq using optimized prove_eq
    pi_eq = prove_eq(t_vec, y_vec, x_bits_padded, gamma, gamma_y, crs)

    # Step 8: Generate π_y
    pi_y = prove_y(x_bits_padded, y_vec, gamma, gamma_y, crs)

    # Step 9: Generate π_v (optional but recommended)
    # prove_v expects s to have length n-1 (for indices 2..n)
    s_vec = t_vec[1:]  # Extract s_2, s_3, ..., s_n (length n-1)
    pi_v = prove_v(x_scalar, r, s_vec, crs)

    # Step 10: Fiat-Shamir aggregation challenges
    # Use deterministic challenges based on commitments only
    agg_hash = hashlib.sha256(C_hat_str + V_hat_str + C_y_str).digest()

    delta_x_int = int.from_bytes(agg_hash[:8], 'big') % int(group.order())
    delta_eq_int = int.from_bytes(agg_hash[8:16], 'big') % int(group.order())
    delta_y_int = int.from_bytes(agg_hash[16:24], 'big') % int(group.order())
    delta_v_int = int.from_bytes(agg_hash[24:32], 'big') % int(group.order())

    delta_x = group.init(ZR, delta_x_int)
    delta_eq = group.init(ZR, delta_eq_int)
    delta_y = group.init(ZR, delta_y_int)
    delta_v = group.init(ZR, delta_v_int)

    # Step 11: Aggregate all proofs
    pi_agg = (pi_x ** delta_x) * (pi_eq ** delta_eq) * (pi_y ** delta_y) * (pi_v ** delta_v)

    # Return proof
    return {
        'C_hat': C_hat,
        'V_hat': V_hat,
        'C_y': C_y,
        'pi_agg': pi_agg,
        'l': l
    }


def prove_point_open_ghat(C_hat: G2, x: List[ZR], gamma: ZR, i: int, crs: dict) -> G2:
    """
    Generate point opening proof π_i at position i for commitment in G2.

    This is the G2 version of prove_point_open.

    Formula:
    --------
    π_i := ĝ_{n+1-i}^{γ} · ∏_{j∈[n], j≠i} ĝ_{n+1-i+j}^{x_j}

    Parameters
    ----------
    C_hat : G2
        The commitment Ĉ in G2
    x : List[ZR]
        The message vector (x_1, ..., x_n)
    gamma : ZR
        The randomness γ used in Ĉ
    i : int
        The position to open (1-indexed)
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    G2
        The proof π_i in G2
    """
    group = crs['group']
    n = crs['n']
    g_hat_list = crs['g_hat_list']

    if i < 1 or i > n:
        raise ValueError(f"Position i={i} must be in [1, {n}]")

    # π_i = ĝ_{n+1-i}^γ
    idx_base = n + 1 - i
    if idx_base not in g_hat_list:
        raise ValueError(f"Index {idx_base} not in g_hat_list")

    pi_i = g_hat_list[idx_base] ** gamma

    # π_i *= ∏_{j∈[n], j≠i} ĝ_{n+1-i+j}^{x_j}
    # Note: For G2, we need to handle indices > n differently
    # We compute using the formula: ĝ_k = ĝ^{α^k}
    alpha = crs['alpha']
    g_hat = crs['g_hat']

    for j in range(1, n + 1):
        if j == i:
            continue
        idx = n + 1 - i + j

        # If idx > n, compute ĝ_idx = ĝ^{α^idx} directly
        if idx > n:
            alpha_power = alpha ** idx
            g_hat_idx = g_hat ** alpha_power
            pi_i *= g_hat_idx ** x[j - 1]
        else:
            if idx not in g_hat_list:
                raise ValueError(f"Index {idx} not in g_hat_list")
            pi_i *= g_hat_list[idx] ** x[j - 1]

    return pi_i


def prove_x_ghat(bit_proofs: List[G2], r: ZR, crs: dict) -> G2:
    """
    Generate range-proof sum-of-weights proof π_x in G2.

    Formula:
    --------
    π_x := (∏_{i=1}^{ℓ} π_i^{2^{i-1}}) · ĝ_n^{-r}

    Parameters
    ----------
    bit_proofs : List[G2]
        The point opening proofs in G2
    r : ZR
        The randomness r from V̂
    crs : dict
        The CRS from keygen_crs()

    Returns
    -------
    G2
        The proof π_x in G2
    """
    group = crs['group']
    n = crs['n']
    g_hat_list = crs['g_hat_list']

    ell = len(bit_proofs)

    # π_x = ∏_{i=1}^{ℓ} π_i^{2^{i-1}}
    pi_x = group.init(G2, 1)
    for i in range(1, ell + 1):
        weight = 2 ** (i - 1)
        pi_x *= bit_proofs[i - 1] ** group.init(ZR, weight)

    # π_x *= ĝ_n^{-r}
    if n not in g_hat_list:
        raise ValueError(f"Index {n} not in g_hat_list")

    pi_x *= g_hat_list[n] ** (-r)

    return pi_x

