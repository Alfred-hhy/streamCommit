"""
Group Initialization and Setup
===============================

This module handles the initialization of Type-3 asymmetric pairing groups
for the vector commitment scheme.

According to charm-crypto documentation (https://jhuisi.github.io/charm/tutorial.html):
- PairingGroup('MNT224') provides asymmetric Type-3 pairings with 224-bit base field
- Alternative curves: 'BN254', 'SS512' (symmetric, but can be used)
- G1, G2 are the source groups; GT is the target group
- Pairing operation: pair(g1_elem, g2_elem) -> GT element
"""

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2, GT, pair


def setup(group_name: str = 'MNT224') -> dict:
    """
    Initialize the pairing group for the vector commitment scheme.
    
    This function sets up the Type-3 asymmetric bilinear pairing groups:
    - G (represented as G1 in charm-crypto)
    - Ĝ (represented as G2 in charm-crypto)
    - G_T (represented as GT in charm-crypto)
    - Bilinear map e: G × Ĝ → G_T (implemented as pair function)
    
    Parameters
    ----------
    group_name : str, optional
        The pairing curve identifier. Default is 'MNT224'.
        Supported curves:
        - 'MNT224': Asymmetric Type-3, 224-bit base field (preferred)
        - 'BN254': Asymmetric Type-3, 254-bit base field (fallback)
        - 'SS512': Symmetric, 512-bit base field (fallback)
    
    Returns
    -------
    dict
        A dictionary containing:
        - 'group': The PairingGroup object
        - 'group_name': The name of the curve used
        - 'G1': The G1 group type constant
        - 'G2': The G2 group type constant
        - 'GT': The GT group type constant
        - 'ZR': The ZR (scalar field) type constant
        - 'pair': The pairing function
    
    Notes
    -----
    According to charm-crypto API:
    - Use group.random(G1) to generate random G1 elements
    - Use group.random(G2) to generate random G2 elements
    - Use group.random(ZR) to generate random scalars in Z_p
    - Use pair(g1_elem, g2_elem) to compute pairings
    - Use group.hash(data, ZR) to hash data to scalars
    
    Examples
    --------
    >>> params = setup('MNT224')
    >>> group = params['group']
    >>> g = group.random(G1)
    >>> g_hat = group.random(G2)
    >>> e_result = pair(g, g_hat)  # e_result is in GT
    """
    try:
        group = PairingGroup(group_name)
    except Exception as e:
        # Fallback to BN254 if MNT224 is not available
        print(f"Warning: {group_name} not available ({e}), falling back to BN254")
        try:
            group = PairingGroup('BN254')
            group_name = 'BN254'
        except Exception as e2:
            # Final fallback to SS512
            print(f"Warning: BN254 not available ({e2}), falling back to SS512")
            group = PairingGroup('SS512')
            group_name = 'SS512'
    
    return {
        'group': group,
        'group_name': group_name,
        'G1': G1,
        'G2': G2,
        'GT': GT,
        'ZR': ZR,
        'pair': pair,
    }


def get_generators(group: PairingGroup) -> tuple:
    """
    Generate canonical generators for G1 and G2.
    
    Parameters
    ----------
    group : PairingGroup
        The initialized pairing group
    
    Returns
    -------
    tuple
        (g, g_hat) where:
        - g is a random generator of G1 (representing G in the paper)
        - g_hat is a random generator of G2 (representing Ĝ in the paper)
    
    Notes
    -----
    In the paper notation:
    - g ∈ G is the canonical generator of G
    - ĝ ∈ Ĝ is the canonical generator of Ĝ
    
    These generators are used to construct the CRS elements:
    - g_i = g^{α^i} for i ∈ [2n] \ {n+1}
    - ĝ_i = ĝ^{α^i} for i ∈ [n]
    """
    g = group.random(G1)
    g_hat = group.random(G2)
    return g, g_hat


def init_random_seed(group: PairingGroup, seed: int = None):
    """
    Initialize the random number generator with a seed for reproducibility.
    
    Parameters
    ----------
    group : PairingGroup
        The initialized pairing group
    seed : int, optional
        The random seed. If None, uses system randomness.
    
    Notes
    -----
    This is useful for testing to ensure reproducible results.
    According to charm-crypto, the group object manages its own RNG state.
    """
    if seed is not None:
        # Charm-crypto uses its own RNG; we set Python's seed for consistency
        import random
        random.seed(seed)
        # Note: charm-crypto's internal RNG may not be directly seedable
        # This provides partial reproducibility for test data generation

