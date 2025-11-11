"""
Vector Commitments with Proofs of Smallness
============================================

A complete implementation of the vector commitment scheme with proofs of smallness
from the paper "Vector Commitments with Proofs of Smallness (Short)".

This package implements all commitment types, proof generation, and verification
equations (1)-(20) using charm-crypto with Type-3 asymmetric pairing curves.

Modules:
--------
- groups: Group initialization and setup
- crs: Common Reference String generation (powers of α)
- commit: Commitment generation (C, Ĉ, C_y, V̂)
- proofs: Proof generation (π_i, π_S, π_eq, π_y, π_x, π_v, π)
- verify: Verification of equations (1)-(20)
- fs_oracles: Fiat-Shamir random oracles with domain separation
- utils: Utility functions (multiexp, pairing operations, serialization)

Usage:
------
    from vc_smallness import setup, keygen_crs
    from vc_smallness.commit import commit_G, commit_Ghat
    from vc_smallness.proofs import prove_point_open
    from vc_smallness.verify import verify_1
    
    # Setup
    params = setup('MNT224')
    crs = keygen_crs(n=16, group=params['group'])
    
    # Commit and prove
    m = [params['group'].random(ZR) for _ in range(16)]
    gamma = params['group'].random(ZR)
    C = commit_G(m, gamma, crs)
    pi_1 = prove_point_open(C, m, gamma, 1, crs)
"""

__version__ = "0.1.0"
__author__ = "Vector Commitments Implementation"

from .groups import setup
from .crs import keygen_crs

__all__ = ['setup', 'keygen_crs']

