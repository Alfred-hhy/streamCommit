"""
Test Suite for Verification Equations (1)-(20)
===============================================

This module tests each verification equation from the paper with both
positive (should pass) and negative (should fail) test cases.

Each test function corresponds to a numbered equation and verifies that:
1. The equation holds for correctly generated proofs (positive test)
2. The equation fails for tampered proofs or incorrect parameters (negative test)
"""

import pytest
from charm.toolbox.pairinggroup import ZR

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vc_smallness.groups import setup
from vc_smallness.crs import keygen_crs
from vc_smallness.commit import commit_G, commit_Ghat, commit_Cy, commit_V, bits_to_scalar
from vc_smallness.proofs import (
    prove_point_open, prove_agg_open, prove_eq, prove_y, prove_x, prove_v, aggregate_pi
)
from vc_smallness.verify import (
    verify_1, verify_3, verify_4, verify_5, verify_7, verify_9, verify_16, verify_20
)
from vc_smallness.fs_oracles import H_t, H_agg, H_s_batch


# Fixtures for common setup
@pytest.fixture(scope="module")
def pairing_params():
    """Initialize pairing group."""
    return setup('MNT224')


@pytest.fixture(scope="module")
def small_crs(pairing_params):
    """Generate CRS for small vector dimension (n=8)."""
    group = pairing_params['group']
    return keygen_crs(n=8, group=group)


@pytest.fixture(scope="module")
def medium_crs(pairing_params):
    """Generate CRS for medium vector dimension (n=16)."""
    group = pairing_params['group']
    return keygen_crs(n=16, group=group)


# ============================================================================
# Test Equation (1): Aggregated inner-product verification
# ============================================================================

def test_eq_1_positive(small_crs):
    """
    Test equation (1) with correctly generated proofs (positive case).
    
    Equation (1):
    e(C, ∏_{i=1}^{n} ĝ_{n+1-i}^{t_i}) = e(∏_{i=1}^{n} π_i^{t_i}, ĝ) · e(g_1, ĝ_n)^{∑ m_i t_i}
    """
    group = small_crs['group']
    n = small_crs['n']
    
    # Generate random message vector
    m = [group.random(ZR) for _ in range(n)]
    gamma = group.random(ZR)
    
    # Commit
    C = commit_G(m, gamma, small_crs)
    
    # Generate point opening proofs for all positions
    pis = [prove_point_open(C, m, gamma, i, small_crs) for i in range(1, n + 1)]
    
    # Generate random challenge weights
    t = [group.random(ZR) for _ in range(n)]
    
    # Verify equation (1)
    assert verify_1(C, pis, t, m, small_crs), "Equation (1) should hold for correct proofs"


def test_eq_1_negative_wrong_message(small_crs):
    """
    Test equation (1) with incorrect message (negative case).
    
    The verification should fail if we claim a different message.
    """
    group = small_crs['group']
    n = small_crs['n']
    
    # Generate random message vector
    m = [group.random(ZR) for _ in range(n)]
    gamma = group.random(ZR)
    
    # Commit
    C = commit_G(m, gamma, small_crs)
    
    # Generate point opening proofs
    pis = [prove_point_open(C, m, gamma, i, small_crs) for i in range(1, n + 1)]
    
    # Generate random challenge weights
    t = [group.random(ZR) for _ in range(n)]
    
    # Tamper with the message
    m_wrong = m.copy()
    m_wrong[0] = group.random(ZR)  # Change first element
    
    # Verify equation (1) with wrong message - should fail
    assert not verify_1(C, pis, t, m_wrong, small_crs), "Equation (1) should fail for wrong message"


def test_eq_1_negative_wrong_proof(small_crs):
    """
    Test equation (1) with tampered proof (negative case).
    """
    from charm.toolbox.pairinggroup import G1
    group = small_crs['group']
    n = small_crs['n']

    # Generate random message vector
    m = [group.random(ZR) for _ in range(n)]
    gamma = group.random(ZR)

    # Commit
    C = commit_G(m, gamma, small_crs)

    # Generate point opening proofs
    pis = [prove_point_open(C, m, gamma, i, small_crs) for i in range(1, n + 1)]

    # Generate random challenge weights
    t = [group.random(ZR) for _ in range(n)]

    # Tamper with one proof
    pis_wrong = pis.copy()
    pis_wrong[0] = group.random(G1)  # Replace with random element

    # Verify equation (1) with wrong proof - should fail
    assert not verify_1(C, pis_wrong, t, m, small_crs), "Equation (1) should fail for tampered proof"


# ============================================================================
# Test Equation (3): Per-coordinate pairing for C_y
# ============================================================================

def test_eq_3_positive(small_crs):
    """
    Test equation (3) with correctly generated C_y (positive case).
    
    Equation (3):
    e(C_y, ĝ_i) = e(g_i^{γ_y} · ∏_{j≠i} g_{n+1-j+i}^{y_j x_j}, ĝ) · e(g_1, ĝ_n)^{y_i x_i}
    """
    group = small_crs['group']
    n = small_crs['n']
    
    # Generate random vectors
    x = [group.random(ZR) for _ in range(n)]
    y = [group.random(ZR) for _ in range(n)]
    gamma_y = group.random(ZR)
    
    # Commit
    C_y = commit_Cy(y, x, gamma_y, small_crs)
    
    # Verify equation (3) for all coordinates
    for i in range(1, n + 1):
        assert verify_3(C_y, i, x, y, gamma_y, small_crs), f"Equation (3) should hold for coordinate {i}"


def test_eq_3_negative_wrong_gamma(small_crs):
    """
    Test equation (3) with incorrect gamma_y (negative case).
    """
    group = small_crs['group']
    n = small_crs['n']
    
    # Generate random vectors
    x = [group.random(ZR) for _ in range(n)]
    y = [group.random(ZR) for _ in range(n)]
    gamma_y = group.random(ZR)
    
    # Commit
    C_y = commit_Cy(y, x, gamma_y, small_crs)
    
    # Use wrong gamma_y for verification
    gamma_y_wrong = group.random(ZR)
    
    # Verify equation (3) with wrong gamma - should fail
    assert not verify_3(C_y, 1, x, y, gamma_y_wrong, small_crs), "Equation (3) should fail for wrong gamma_y"


# ============================================================================
# Test Equation (4): Per-coordinate pairing for Ĉ
# ============================================================================

def test_eq_4_positive(small_crs):
    """
    Test equation (4) with correctly generated Ĉ (positive case).
    
    Equation (4):
    e(g_{n+1-i}, Ĉ) = e(g_{n+1-i}^{γ} · ∏_{j≠i} g_{n+1-i+j}^{x_j}, ĝ) · e(g_1, ĝ_n)^{x_i}
    """
    group = small_crs['group']
    n = small_crs['n']
    
    # Generate random vector
    x = [group.random(ZR) for _ in range(n)]
    gamma = group.random(ZR)
    
    # Commit
    C_hat = commit_Ghat(x, gamma, small_crs)
    
    # Verify equation (4) for all coordinates
    for i in range(1, n + 1):
        assert verify_4(C_hat, i, x, gamma, small_crs), f"Equation (4) should hold for coordinate {i}"


def test_eq_4_negative_wrong_vector(small_crs):
    """
    Test equation (4) with incorrect vector x (negative case).
    """
    group = small_crs['group']
    n = small_crs['n']
    
    # Generate random vector
    x = [group.random(ZR) for _ in range(n)]
    gamma = group.random(ZR)
    
    # Commit
    C_hat = commit_Ghat(x, gamma, small_crs)
    
    # Use wrong vector for verification
    x_wrong = [group.random(ZR) for _ in range(n)]
    
    # Verify equation (4) with wrong vector - should fail
    assert not verify_4(C_hat, 1, x_wrong, gamma, small_crs), "Equation (4) should fail for wrong vector"


# ============================================================================
# Test Equation (5): Key division equation
# ============================================================================

def test_eq_5_positive(small_crs):
    """
    Test equation (5) with correctly generated π_eq (positive case).
    
    Equation (5):
    [e(∏ g_{n+1-i}^{t_i y_i}, Ĉ)] / [e(C_y, ∏ ĝ_i^{t_i})] = e(π_eq, ĝ)
    """
    group = small_crs['group']
    n = small_crs['n']
    
    # Generate random vectors
    x = [group.random(ZR) for _ in range(n)]
    y = [group.random(ZR) for _ in range(n)]
    gamma = group.random(ZR)
    gamma_y = group.random(ZR)
    
    # Commit
    C_hat = commit_Ghat(x, gamma, small_crs)
    C_y = commit_Cy(y, x, gamma_y, small_crs)
    
    # Generate challenge weights
    t = [group.random(ZR) for _ in range(n)]
    
    # Generate proof
    pi_eq = prove_eq(t, y, x, gamma, gamma_y, small_crs)
    
    # Verify equation (5)
    assert verify_5(C_hat, C_y, t, y, pi_eq, small_crs), "Equation (5) should hold for correct π_eq"


def test_eq_5_negative_wrong_proof(small_crs):
    """
    Test equation (5) with tampered π_eq (negative case).
    """
    from charm.toolbox.pairinggroup import G1
    group = small_crs['group']
    n = small_crs['n']

    # Generate random vectors
    x = [group.random(ZR) for _ in range(n)]
    y = [group.random(ZR) for _ in range(n)]
    gamma = group.random(ZR)
    gamma_y = group.random(ZR)

    # Commit
    C_hat = commit_Ghat(x, gamma, small_crs)
    C_y = commit_Cy(y, x, gamma_y, small_crs)

    # Generate challenge weights
    t = [group.random(ZR) for _ in range(n)]

    # Use wrong proof
    pi_eq_wrong = group.random(G1)

    # Verify equation (5) with wrong proof - should fail
    assert not verify_5(C_hat, C_y, t, y, pi_eq_wrong, small_crs), "Equation (5) should fail for wrong π_eq"


# ============================================================================
# Test Equation (7): Orthogonality check
# ============================================================================

def test_eq_7_positive_binary(small_crs):
    """
    Test equation (7) with binary x and y vectors (positive case).

    Equation (7):
    e(C_y · ∏_{j=1}^{n} g_{n+1-j}^{-y_j}, Ĉ) = e(π_y, ĝ)

    Note: The orthogonality condition ∑ y_i x_i (x_i - 1) = 0 is satisfied
    when BOTH x and y are binary, because x_i(x_i - 1) = 0 for x_i ∈ {0,1}.
    """
    group = small_crs['group']
    n = small_crs['n']

    # Generate BINARY vectors x and y
    x = [group.init(ZR, 0) if i % 3 == 0 else group.init(ZR, 1) for i in range(n)]
    y = [group.init(ZR, 0) if i % 2 == 0 else group.init(ZR, 1) for i in range(n)]

    gamma = group.random(ZR)
    gamma_y = group.random(ZR)

    # Commit
    C_hat = commit_Ghat(x, gamma, small_crs)
    C_y = commit_Cy(y, x, gamma_y, small_crs)

    # Generate proof
    pi_y = prove_y(x, y, gamma, gamma_y, small_crs)

    # Verify equation (7)
    assert verify_7(C_hat, C_y, pi_y, y, small_crs), "Equation (7) should hold for binary x and y"


def test_eq_7_negative_wrong_proof(small_crs):
    """
    Test equation (7) with tampered π_y (negative case).
    """
    from charm.toolbox.pairinggroup import G1
    group = small_crs['group']
    n = small_crs['n']

    # Generate random vectors
    x = [group.random(ZR) for _ in range(n)]
    y = [group.init(ZR, 0) if i % 2 == 0 else group.init(ZR, 1) for i in range(n)]
    gamma = group.random(ZR)
    gamma_y = group.random(ZR)

    # Commit
    C_hat = commit_Ghat(x, gamma, small_crs)
    C_y = commit_Cy(y, x, gamma_y, small_crs)

    # Use wrong proof
    pi_y_wrong = group.random(G1)

    # Verify equation (7) with wrong proof - should fail
    assert not verify_7(C_hat, C_y, pi_y_wrong, y, small_crs), "Equation (7) should fail for wrong π_y"


# ============================================================================
# Test Equation (9): Division form with integer commitment
# ============================================================================

def test_eq_9_positive(small_crs):
    """
    Test equation (9) with correctly generated π_x (positive case).

    Equation (9):
    [e(∏ g_{n+1-i}^{2^{i-1}}, Ĉ)] / [e(g_n, V̂)] = e(π_x, ĝ)
    """
    group = small_crs['group']
    n = small_crs['n']

    # Generate bit vector (ℓ = 5 bits)
    ell = 5
    x_bits_int = [0, 1, 1, 0, 1]  # Binary representation
    x_bits = [group.init(ZR, b) for b in x_bits_int]

    # Compute scalar value
    x_scalar = bits_to_scalar(x_bits_int, group)

    # Pad x_bits to length n
    x_bits_padded = x_bits + [group.init(ZR, 0)] * (n - ell)

    gamma = group.random(ZR)
    r = group.random(ZR)

    # Commit
    C_hat = commit_Ghat(x_bits_padded, gamma, small_crs)
    V_hat = commit_V(x_scalar, r, small_crs)

    # Generate point opening proofs for bit positions
    bit_proofs = [prove_point_open(C_hat, x_bits_padded, gamma, i, small_crs) for i in range(1, ell + 1)]

    # Generate π_x
    pi_x = prove_x(bit_proofs, r, small_crs)

    # Verify equation (9)
    assert verify_9(C_hat, V_hat, pi_x, ell, small_crs), "Equation (9) should hold for correct π_x"


def test_eq_9_negative_wrong_scalar(small_crs):
    """
    Test equation (9) with incorrect scalar in V̂ (negative case).
    """
    group = small_crs['group']
    n = small_crs['n']

    # Generate bit vector
    ell = 5
    x_bits_int = [0, 1, 1, 0, 1]
    x_bits = [group.init(ZR, b) for b in x_bits_int]
    x_scalar = bits_to_scalar(x_bits_int, group)
    x_bits_padded = x_bits + [group.init(ZR, 0)] * (n - ell)

    gamma = group.random(ZR)
    r = group.random(ZR)

    # Commit with WRONG scalar
    C_hat = commit_Ghat(x_bits_padded, gamma, small_crs)
    x_scalar_wrong = group.random(ZR)
    V_hat_wrong = commit_V(x_scalar_wrong, r, small_crs)

    # Generate proofs with correct bits
    bit_proofs = [prove_point_open(C_hat, x_bits_padded, gamma, i, small_crs) for i in range(1, ell + 1)]
    pi_x = prove_x(bit_proofs, r, small_crs)

    # Verify equation (9) with wrong V̂ - should fail
    assert not verify_9(C_hat, V_hat_wrong, pi_x, ell, small_crs), "Equation (9) should fail for wrong V̂"


# ============================================================================
# Test Equation (16): Aggregated verification
# ============================================================================

def test_eq_16_positive(small_crs):
    """
    Test equation (16) with correctly aggregated proof (positive case).

    Equation (16):
    [e(C_y^{δ_y} · ∏ g_{n+1-i}^{(δ_eq t_i - δ_y) y_i}, Ĉ)] / [e(C_y, ∏ ĝ_i^{δ_eq t_i})] = e(π, ĝ)

    Note: Using binary x and y to satisfy orthogonality condition.
    """
    group = small_crs['group']
    n = small_crs['n']

    # Generate BINARY vectors x and y (to satisfy orthogonality)
    x = [group.init(ZR, 0) if i % 3 == 0 else group.init(ZR, 1) for i in range(n)]
    y = [group.init(ZR, 0) if i % 2 == 0 else group.init(ZR, 1) for i in range(n)]
    gamma = group.random(ZR)
    gamma_y = group.random(ZR)

    # Commit
    C_hat = commit_Ghat(x, gamma, small_crs)
    C_y = commit_Cy(y, x, gamma_y, small_crs)

    # Generate challenge weights
    t = [group.random(ZR) for _ in range(n)]

    # Generate proofs
    pi_eq = prove_eq(t, y, x, gamma, gamma_y, small_crs)
    pi_y = prove_y(x, y, gamma, gamma_y, small_crs)

    # Generate aggregation challenges
    delta_eq, delta_y = H_agg(C_hat, C_hat, C_y, group)

    # Aggregate proofs
    pi = aggregate_pi(pi_eq, pi_y, delta_eq, delta_y, small_crs)

    # Verify equation (16)
    assert verify_16(C_hat, C_y, pi, delta_eq, delta_y, t, y, small_crs), "Equation (16) should hold for aggregated π"


def test_eq_16_negative_wrong_aggregation(small_crs):
    """
    Test equation (16) with incorrect aggregation (negative case).
    """
    group = small_crs['group']
    n = small_crs['n']

    # Generate BINARY vectors x and y
    x = [group.init(ZR, 0) if i % 3 == 0 else group.init(ZR, 1) for i in range(n)]
    y = [group.init(ZR, 0) if i % 2 == 0 else group.init(ZR, 1) for i in range(n)]
    gamma = group.random(ZR)
    gamma_y = group.random(ZR)

    # Commit
    C_hat = commit_Ghat(x, gamma, small_crs)
    C_y = commit_Cy(y, x, gamma_y, small_crs)

    # Generate challenge weights
    t = [group.random(ZR) for _ in range(n)]

    # Generate proofs
    pi_eq = prove_eq(t, y, x, gamma, gamma_y, small_crs)
    pi_y = prove_y(x, y, gamma, gamma_y, small_crs)

    # Generate aggregation challenges
    delta_eq, delta_y = H_agg(C_hat, C_hat, C_y, group)

    # Aggregate with WRONG challenges
    delta_eq_wrong = group.random(ZR)
    delta_y_wrong = group.random(ZR)
    pi_wrong = aggregate_pi(pi_eq, pi_y, delta_eq_wrong, delta_y_wrong, small_crs)

    # Verify equation (16) with wrong aggregation - should fail
    assert not verify_16(C_hat, C_y, pi_wrong, delta_eq, delta_y, t, y, small_crs), "Equation (16) should fail for wrong aggregation"


# ============================================================================
# Test Equation (20): Only-first-coordinate-nonzero proof
# ============================================================================

def test_eq_20_positive(small_crs):
    """
    Test equation (20) with correctly generated π_v (positive case).

    Equation (20):
    e(∏_{i=2}^{n} g_{n+1-i}^{s_i}, V̂) = e(π_v, ĝ)
    """
    group = small_crs['group']
    n = small_crs['n']

    # Generate scalar and randomness
    x_scalar = group.random(ZR)
    r = group.random(ZR)

    # Commit
    V_hat = commit_V(x_scalar, r, small_crs)

    # For testing, create dummy C_hat and C_y
    x_dummy = [group.random(ZR) for _ in range(n)]
    y_dummy = [group.random(ZR) for _ in range(n)]
    C_hat = commit_Ghat(x_dummy, group.random(ZR), small_crs)
    C_y = commit_Cy(y_dummy, x_dummy, group.random(ZR), small_crs)

    # Generate challenges
    s = H_s_batch(list(range(2, n + 1)), V_hat, C_hat, C_y, group)

    # Generate proof
    pi_v = prove_v(x_scalar, r, s, small_crs)

    # Verify equation (20)
    assert verify_20(V_hat, s, pi_v, small_crs), "Equation (20) should hold for correct π_v"


def test_eq_20_negative_wrong_challenges(small_crs):
    """
    Test equation (20) with incorrect challenges (negative case).
    """
    group = small_crs['group']
    n = small_crs['n']

    # Generate scalar and randomness
    x_scalar = group.random(ZR)
    r = group.random(ZR)

    # Commit
    V_hat = commit_V(x_scalar, r, small_crs)

    # For testing, create dummy C_hat and C_y
    x_dummy = [group.random(ZR) for _ in range(n)]
    y_dummy = [group.random(ZR) for _ in range(n)]
    C_hat = commit_Ghat(x_dummy, group.random(ZR), small_crs)
    C_y = commit_Cy(y_dummy, x_dummy, group.random(ZR), small_crs)

    # Generate challenges
    s = H_s_batch(list(range(2, n + 1)), V_hat, C_hat, C_y, group)

    # Generate proof with correct challenges
    pi_v = prove_v(x_scalar, r, s, small_crs)

    # Use WRONG challenges for verification
    s_wrong = [group.random(ZR) for _ in range(n - 1)]

    # Verify equation (20) with wrong challenges - should fail
    assert not verify_20(V_hat, s_wrong, pi_v, small_crs), "Equation (20) should fail for wrong challenges"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

