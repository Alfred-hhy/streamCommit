"""
Utility Functions
=================

This module provides utility functions for group operations, multi-exponentiation,
pairing operations, and serialization.

Key Operations:
- Multi-exponentiation: Compute ∏ g_i^{e_i} efficiently
- Pairing products: Compute ∏ e(g_i, ĝ_i) efficiently
- GT operations: Division (multiplication by inverse) in GT
- Serialization: Convert group elements to/from bytes

According to charm-crypto documentation:
- Group operations use * for multiplication, ** for exponentiation
- Inverse is computed as elem ** -1
- Pairing is computed as pair(g1_elem, g2_elem)
- Serialization uses objectToBytes() and bytesToObject()
"""

from charm.toolbox.pairinggroup import PairingGroup, ZR, G1, G2, GT, pair
from charm.core.engine.util import objectToBytes, bytesToObject
from typing import List, Union


def multiexp_g1(bases: List[G1], exponents: List[ZR], group: PairingGroup) -> G1:
    """
    Compute multi-exponentiation in G1: ∏ bases[i]^{exponents[i]}.
    
    This is a fundamental operation used throughout the commitment and proof
    generation algorithms.
    
    Formula:
    --------
    result = ∏_{i=0}^{len(bases)-1} bases[i]^{exponents[i]}
    
    Parameters
    ----------
    bases : List[G1]
        List of base elements in G1
    exponents : List[ZR]
        List of exponents in Z_p
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    G1
        The product ∏ bases[i]^{exponents[i]}
    
    Notes
    -----
    - If bases is empty, returns the identity element 1_G
    - bases and exponents must have the same length
    - This function does NOT use any special multi-exponentiation algorithm;
      it computes the product directly as specified in the formulas
    
    Examples
    --------
    >>> result = multiexp_g1([g1, g2, g3], [e1, e2, e3], group)
    >>> # Equivalent to: g1^e1 * g2^e2 * g3^e3
    """
    if len(bases) == 0:
        return group.init(G1, 1)  # Identity element
    
    if len(bases) != len(exponents):
        raise ValueError(f"bases and exponents must have same length: {len(bases)} != {len(exponents)}")
    
    result = group.init(G1, 1)
    for base, exp in zip(bases, exponents):
        result *= base ** exp
    
    return result


def multiexp_g2(bases: List[G2], exponents: List[ZR], group: PairingGroup) -> G2:
    """
    Compute multi-exponentiation in G2: ∏ bases[i]^{exponents[i]}.
    
    Formula:
    --------
    result = ∏_{i=0}^{len(bases)-1} bases[i]^{exponents[i]}
    
    Parameters
    ----------
    bases : List[G2]
        List of base elements in G2
    exponents : List[ZR]
        List of exponents in Z_p
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    G2
        The product ∏ bases[i]^{exponents[i]}
    
    Notes
    -----
    - If bases is empty, returns the identity element 1_Ĝ
    - bases and exponents must have the same length
    """
    if len(bases) == 0:
        return group.init(G2, 1)  # Identity element
    
    if len(bases) != len(exponents):
        raise ValueError(f"bases and exponents must have same length: {len(bases)} != {len(exponents)}")
    
    result = group.init(G2, 1)
    for base, exp in zip(bases, exponents):
        result *= base ** exp
    
    return result


def pair_prod(g1_elems: List[G1], g2_elems: List[G2], group: PairingGroup) -> GT:
    """
    Compute product of pairings: ∏ e(g1_elems[i], g2_elems[i]).
    
    This is used extensively in verification equations to batch multiple
    pairing operations.
    
    Formula:
    --------
    result = ∏_{i=0}^{len(g1_elems)-1} e(g1_elems[i], g2_elems[i])
    
    Parameters
    ----------
    g1_elems : List[G1]
        List of G1 elements
    g2_elems : List[G2]
        List of G2 elements
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    GT
        The product of pairings ∏ e(g1_elems[i], g2_elems[i])
    
    Notes
    -----
    - If lists are empty, returns the identity element 1_GT
    - g1_elems and g2_elems must have the same length
    - Uses the bilinearity property: e(g1^a, g2^b) = e(g1, g2)^{ab}
    
    Examples
    --------
    >>> result = pair_prod([g1, g2], [g_hat1, g_hat2], group)
    >>> # Equivalent to: e(g1, g_hat1) * e(g2, g_hat2)
    """
    if len(g1_elems) == 0:
        return group.init(GT, 1)  # Identity element
    
    if len(g1_elems) != len(g2_elems):
        raise ValueError(f"g1_elems and g2_elems must have same length: {len(g1_elems)} != {len(g2_elems)}")
    
    result = group.init(GT, 1)
    for g1, g2 in zip(g1_elems, g2_elems):
        result *= pair(g1, g2)
    
    return result


def gt_div(numerator: GT, denominator: GT, group: PairingGroup) -> GT:
    """
    Compute division in GT: numerator / denominator.
    
    This is implemented as: numerator * denominator^{-1}
    
    This function is CRITICAL for implementing the division-form equations
    (5), (9), (13), (16), (17), (18) which all have the form:
    
        LHS_numerator / LHS_denominator = RHS
    
    Formula:
    --------
    result = numerator * denominator^{-1}
    
    Parameters
    ----------
    numerator : GT
        The numerator in GT
    denominator : GT
        The denominator in GT
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    GT
        The quotient numerator / denominator
    
    Notes
    -----
    According to charm-crypto API:
    - Inverse in GT is computed as: elem ** -1
    - This is the ONLY way to implement division equations
    - Do NOT rewrite division equations in any other form
    
    Examples
    --------
    >>> # For equation (5): LHS_num / LHS_den = e(π_eq, ĝ)
    >>> lhs = gt_div(lhs_num, lhs_den, group)
    >>> rhs = pair(pi_eq, g_hat)
    >>> assert gt_eq(lhs, rhs, group)
    """
    return numerator * (denominator ** -1)


def gt_eq(a: GT, b: GT, group: PairingGroup, tolerance: float = 1e-10) -> bool:
    """
    Test equality of two GT elements.
    
    Parameters
    ----------
    a : GT
        First GT element
    b : GT
        Second GT element
    group : PairingGroup
        The pairing group
    tolerance : float, optional
        Tolerance for floating-point comparison (not typically needed)
    
    Returns
    -------
    bool
        True if a == b, False otherwise
    
    Notes
    -----
    According to charm-crypto, direct comparison with == should work.
    If there are issues with floating-point representations, we can
    compare serialized forms.
    """
    # Direct comparison
    if a == b:
        return True
    
    # Fallback: compare serialized forms
    try:
        a_bytes = objectToBytes(a, group)
        b_bytes = objectToBytes(b, group)
        return a_bytes == b_bytes
    except:
        return False


def serialize_element(elem: Union[G1, G2, GT, ZR], group: PairingGroup) -> bytes:
    """
    Serialize a group element to bytes.
    
    According to charm-crypto documentation:
    Use objectToBytes(obj, group) to serialize group elements.
    
    Parameters
    ----------
    elem : Union[G1, G2, GT, ZR]
        The group element to serialize
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    bytes
        The serialized element
    """
    return objectToBytes(elem, group)


def deserialize_element(data: bytes, group: PairingGroup) -> Union[G1, G2, GT, ZR]:
    """
    Deserialize a group element from bytes.
    
    According to charm-crypto documentation:
    Use bytesToObject(bytes, group) to deserialize group elements.
    
    Parameters
    ----------
    data : bytes
        The serialized data
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    Union[G1, G2, GT, ZR]
        The deserialized group element
    """
    return bytesToObject(data, group)


def prod_g1(elems: List[G1], group: PairingGroup) -> G1:
    """
    Compute product of G1 elements: ∏ elems[i].
    
    Parameters
    ----------
    elems : List[G1]
        List of G1 elements
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    G1
        The product ∏ elems[i]
    """
    if len(elems) == 0:
        return group.init(G1, 1)
    
    result = group.init(G1, 1)
    for elem in elems:
        result *= elem
    return result


def prod_g2(elems: List[G2], group: PairingGroup) -> G2:
    """
    Compute product of G2 elements: ∏ elems[i].
    
    Parameters
    ----------
    elems : List[G2]
        List of G2 elements
    group : PairingGroup
        The pairing group
    
    Returns
    -------
    G2
        The product ∏ elems[i]
    """
    if len(elems) == 0:
        return group.init(G2, 1)
    
    result = group.init(G2, 1)
    for elem in elems:
        result *= elem
    return result

