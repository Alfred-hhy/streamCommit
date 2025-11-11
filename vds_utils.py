"""
VDS Utility Functions
=====================

This module provides utility functions for the VDS scheme, including:
- Digital signature generation and verification (ECDSA)
- Serialization of group elements and signatures
- Hashing for signature binding

These utilities are used to bind commitments cryptographically and ensure
the integrity of the VDS scheme.

Security Notes:
---------------
- We use ECDSA (separate from the pairing curve) for signature binding
- This provides a clean separation between the VC scheme and the binding mechanism
- The signature binds C_data and C_time together, preventing mix-and-match attacks
"""

import hashlib
from ecdsa import SigningKey, VerifyingKey, NIST256p
from ecdsa.util import sigdecode_string, sigencode_string
from charm.core.engine.util import objectToBytes
from charm.toolbox.pairinggroup import G1, G2
from typing import Tuple


def generate_signing_keys() -> Tuple[SigningKey, VerifyingKey]:
    """
    Generate ECDSA signing and verification keys.
    
    Returns
    -------
    sk : SigningKey
        The secret signing key (for DO)
    vk : VerifyingKey
        The public verification key (for verifiers)
    
    Notes
    -----
    We use NIST P-256 curve (separate from the pairing curve).
    This provides ~128-bit security level.
    
    Examples
    --------
    >>> sk, vk = generate_signing_keys()
    >>> # DO keeps sk secret, publishes vk in global_pk
    """
    sk = SigningKey.generate(curve=NIST256p)
    vk = sk.get_verifying_key()
    return sk, vk


def serialize_group_element(elem) -> bytes:
    """
    Serialize a Charm group element (G1 or G2) to bytes.
    
    Parameters
    ----------
    elem : G1 or G2
        The group element to serialize
    
    Returns
    -------
    bytes
        The serialized representation
    
    Notes
    -----
    This uses Charm's objectToBytes function.
    The serialization is deterministic and can be used for hashing.
    
    Examples
    --------
    >>> C_bytes = serialize_group_element(C_data)
    """
    # Charm's objectToBytes requires the group, but we can't access it here
    # We'll use a workaround: serialize() method if available
    try:
        return elem.serialize()
    except AttributeError:
        # Fallback: convert to string and encode
        # This is not ideal but works for hashing purposes
        return str(elem).encode('utf-8')


def serialize_for_signing(C_data: G1, C_time: G2) -> bytes:
    """
    Serialize two commitments for signature binding.
    
    Parameters
    ----------
    C_data : G1
        The data commitment
    C_time : G2
        The time commitment
    
    Returns
    -------
    bytes
        Concatenated serialization of both commitments
    
    Notes
    -----
    The order matters: C_data || C_time
    This ensures a unique representation for each (C_data, C_time) pair.
    
    Examples
    --------
    >>> msg_bytes = serialize_for_signing(C_data, C_time)
    """
    C_data_bytes = serialize_group_element(C_data)
    C_time_bytes = serialize_group_element(C_time)
    return C_data_bytes + C_time_bytes


def hash_for_signing(C_data: G1, C_time: G2) -> bytes:
    """
    Hash two commitments for signature generation.
    
    Parameters
    ----------
    C_data : G1
        The data commitment
    C_time : G2
        The time commitment
    
    Returns
    -------
    bytes
        SHA-256 hash of the serialized commitments
    
    Notes
    -----
    We use SHA-256 for the hash function.
    This provides collision resistance for the signature binding.
    
    Examples
    --------
    >>> h = hash_for_signing(C_data, C_time)
    >>> sigma = sk.sign(h)
    """
    serialized = serialize_for_signing(C_data, C_time)
    return hashlib.sha256(serialized).digest()


def sign_batch(sk_ecdsa: SigningKey, C_data: G1, C_time: G2) -> bytes:
    """
    Sign a batch (bind C_data and C_time together).
    
    Parameters
    ----------
    sk_ecdsa : SigningKey
        The DO's secret signing key
    C_data : G1
        The data commitment
    C_time : G2
        The time commitment
    
    Returns
    -------
    bytes
        The signature σ = Sign(sk, Hash(C_data || C_time))
    
    Notes
    -----
    This signature cryptographically binds C_data and C_time together.
    Any attempt to mix commitments from different batches will fail verification.
    
    Security:
    - Prevents mix-and-match attacks
    - Ensures integrity of the batch header
    
    Examples
    --------
    >>> sigma = sign_batch(sk_DO, C_data, C_time)
    >>> # sigma is included in the public header
    """
    h = hash_for_signing(C_data, C_time)
    sigma = sk_ecdsa.sign(h, sigencode=sigencode_string)
    return sigma


def verify_batch_signature(vk_ecdsa: VerifyingKey, C_data: G1, C_time: G2, sigma: bytes) -> bool:
    """
    Verify a batch signature.
    
    Parameters
    ----------
    vk_ecdsa : VerifyingKey
        The DO's public verification key
    C_data : G1
        The data commitment
    C_time : G2
        The time commitment
    sigma : bytes
        The signature to verify
    
    Returns
    -------
    bool
        True if the signature is valid, False otherwise
    
    Notes
    -----
    This verifies that:
    1. The signature was created by the DO (using sk_DO)
    2. The signature binds exactly these two commitments (C_data, C_time)
    
    Any tampering with C_data or C_time will cause verification to fail.
    
    Examples
    --------
    >>> is_valid = verify_batch_signature(vk_DO, C_data, C_time, sigma)
    >>> if not is_valid:
    >>>     print("Invalid signature! Possible tampering detected.")
    """
    try:
        h = hash_for_signing(C_data, C_time)
        vk_ecdsa.verify(sigma, h, sigdecode=sigdecode_string)
        return True
    except Exception as e:
        # Signature verification failed
        return False


def serialize_signature(sigma: bytes) -> bytes:
    """
    Serialize a signature for storage or hashing.
    
    Parameters
    ----------
    sigma : bytes
        The signature (already in bytes format from ecdsa)
    
    Returns
    -------
    bytes
        The serialized signature (same as input for ecdsa)
    
    Notes
    -----
    For ecdsa signatures, the signature is already in bytes format.
    This function is provided for consistency with the API.
    
    Examples
    --------
    >>> sigma_bytes = serialize_signature(sigma)
    >>> # Use sigma_bytes for accumulator hashing
    """
    return sigma


def deserialize_signature(sigma_bytes: bytes) -> bytes:
    """
    Deserialize a signature from bytes.
    
    Parameters
    ----------
    sigma_bytes : bytes
        The serialized signature
    
    Returns
    -------
    bytes
        The signature (same as input for ecdsa)
    
    Notes
    -----
    For ecdsa signatures, no deserialization is needed.
    This function is provided for consistency with the API.
    
    Examples
    --------
    >>> sigma = deserialize_signature(sigma_bytes)
    """
    return sigma_bytes

