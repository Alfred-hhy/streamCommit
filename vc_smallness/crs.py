"""
Common Reference String (CRS) Generation
=========================================

This module generates the CRS (Common Reference String) for the vector commitment scheme.

The CRS consists of powers of a secret α in both G and Ĝ groups:
- For G:  g_i := g^{α^i}      for i ∈ [2n] \ {n+1}
- For Ĝ:  ĝ_i := ĝ^{α^i}      for i ∈ [n]

The index n+1 is explicitly excluded from the G-side CRS to prevent certain attacks.

Mathematical Notation:
----------------------
- [n] = {1, 2, ..., n}
- [2n] \ {n+1} = {1, 2, ..., n, n+2, n+3, ..., 2n}
- α ∈ Z_p is the secret trapdoor (must be securely deleted after CRS generation)
- g ∈ G, ĝ ∈ Ĝ are the canonical generators
"""

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2


def keygen_crs(n: int, group: PairingGroup, alpha: ZR = None, g: G1 = None, g_hat: G2 = None) -> dict:
    """
    Generate the Common Reference String (CRS) for vector dimension n.
    
    This function generates the structured reference string required for the
    vector commitment scheme. The CRS contains powers of a secret α:
    
    For G (G1):  g_i = g^{α^i}  for i ∈ [2n] \ {n+1}
    For Ĝ (G2):  ĝ_i = ĝ^{α^i}  for i ∈ [n]
    
    Parameters
    ----------
    n : int
        The vector dimension. The CRS will support vectors of length n.
    group : PairingGroup
        The initialized pairing group from setup()
    alpha : ZR, optional
        The secret trapdoor. If None, a random α is generated.
        WARNING: In production, α must be securely deleted after CRS generation.
    g : G1, optional
        The generator of G. If None, a random generator is chosen.
    g_hat : G2, optional
        The generator of Ĝ. If None, a random generator is chosen.
    
    Returns
    -------
    dict
        A dictionary containing:
        - 'group': The PairingGroup object
        - 'n': The vector dimension
        - 'g': The generator g ∈ G (G1)
        - 'g_hat': The generator ĝ ∈ Ĝ (G2)
        - 'alpha': The secret α ∈ Z_p (for testing only; should be deleted in production)
        - 'g_list': Dictionary mapping i → g_i = g^{α^i} for i ∈ [2n] \ {n+1}
        - 'g_hat_list': Dictionary mapping i → ĝ_i = ĝ^{α^i} for i ∈ [n]
    
    Notes
    -----
    Index Convention:
    - g_list[i] corresponds to g_i in the paper (1-indexed)
    - g_hat_list[i] corresponds to ĝ_i in the paper (1-indexed)
    - The index n+1 is EXCLUDED from g_list to prevent attacks
    
    Reverse Indexing:
    - g_{n+1-i} is accessed as g_list[n+1-i]
    - g_{n+1-i+j} is accessed as g_list[n+1-i+j]
    - These patterns appear frequently in the commitment and proof formulas
    
    Security:
    - The secret α must be securely deleted after CRS generation
    - Knowledge of α allows breaking the binding property
    - In a real deployment, use a trusted setup or MPC ceremony
    
    Examples
    --------
    >>> from vc_smallness.groups import setup
    >>> params = setup('MNT224')
    >>> crs = keygen_crs(n=16, group=params['group'])
    >>> # Access g_1
    >>> g_1 = crs['g_list'][1]
    >>> # Access g_{n+1-i} for i=5, n=16: g_{16+1-5} = g_{12}
    >>> g_12 = crs['g_list'][12]
    """
    # Generate secret α if not provided
    if alpha is None:
        alpha = group.random(ZR)
    
    # Generate generators if not provided
    if g is None:
        g = group.random(G1)
    if g_hat is None:
        g_hat = group.random(G2)
    
    # Compute powers of α
    # α^i for i ∈ [2n]
    alpha_powers = {}
    alpha_powers[0] = group.init(ZR, 1)  # α^0 = 1
    alpha_powers[1] = alpha
    for i in range(2, 2 * n + 1):
        alpha_powers[i] = alpha_powers[i - 1] * alpha
    
    # Generate g_list: g_i = g^{α^i} for i ∈ [2n] \ {n+1}
    g_list = {}
    for i in range(1, 2 * n + 1):
        if i == n + 1:
            # Explicitly skip n+1 as per the paper
            continue
        g_list[i] = g ** alpha_powers[i]
    
    # Generate g_hat_list: ĝ_i = ĝ^{α^i} for i ∈ [n]
    g_hat_list = {}
    for i in range(1, n + 1):
        g_hat_list[i] = g_hat ** alpha_powers[i]
    
    return {
        'group': group,
        'n': n,
        'g': g,
        'g_hat': g_hat,
        'alpha': alpha,  # WARNING: Should be deleted in production
        'g_list': g_list,
        'g_hat_list': g_hat_list,
    }


def get_g_reverse(crs: dict, i: int) -> G1:
    """
    Helper function to access g_{n+1-i}.
    
    This is a common pattern in the formulas where we need g_{n+1-i}.
    
    Parameters
    ----------
    crs : dict
        The CRS dictionary from keygen_crs()
    i : int
        The index i (1-indexed)
    
    Returns
    -------
    G1
        The group element g_{n+1-i}
    
    Examples
    --------
    >>> g_rev = get_g_reverse(crs, i=5)  # Returns g_{n+1-5}
    """
    n = crs['n']
    idx = n + 1 - i
    if idx not in crs['g_list']:
        raise ValueError(f"Index {idx} (n+1-{i}) not in g_list. Note: n+1 is excluded from CRS.")
    return crs['g_list'][idx]


def get_g_hat_reverse(crs: dict, i: int) -> G2:
    """
    Helper function to access ĝ_{n+1-i}.
    
    This is a common pattern in the formulas where we need ĝ_{n+1-i}.
    
    Parameters
    ----------
    crs : dict
        The CRS dictionary from keygen_crs()
    i : int
        The index i (1-indexed)
    
    Returns
    -------
    G2
        The group element ĝ_{n+1-i}
    
    Examples
    --------
    >>> g_hat_rev = get_g_hat_reverse(crs, i=5)  # Returns ĝ_{n+1-5}
    """
    n = crs['n']
    idx = n + 1 - i
    if idx not in crs['g_hat_list']:
        raise ValueError(f"Index {idx} (n+1-{i}) not in g_hat_list.")
    return crs['g_hat_list'][idx]


def validate_crs(crs: dict) -> bool:
    """
    Validate that the CRS is well-formed.
    
    Checks:
    - g_list has 2n-1 elements (excluding n+1)
    - g_hat_list has n elements
    - All required indices are present
    
    Parameters
    ----------
    crs : dict
        The CRS dictionary from keygen_crs()
    
    Returns
    -------
    bool
        True if CRS is valid, False otherwise
    """
    n = crs['n']
    
    # Check g_list size (should be 2n - 1, excluding n+1)
    if len(crs['g_list']) != 2 * n - 1:
        return False
    
    # Check g_hat_list size (should be n)
    if len(crs['g_hat_list']) != n:
        return False
    
    # Check that n+1 is NOT in g_list
    if (n + 1) in crs['g_list']:
        return False
    
    # Check all required indices in g_list
    for i in range(1, 2 * n + 1):
        if i == n + 1:
            continue
        if i not in crs['g_list']:
            return False
    
    # Check all required indices in g_hat_list
    for i in range(1, n + 1):
        if i not in crs['g_hat_list']:
            return False
    
    return True

