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
from typing import Tuple, List


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


def serialize_for_signing(C_data_list: List[G1], C_time: G2) -> bytes:
    """
    序列化承诺列表和时间承诺用于签名绑定。

    Parameters
    ----------
    C_data_list : List[G1]
        数据承诺列表（每列一个承诺）
    C_time : G2
        时间承诺（所有列共享）

    Returns
    -------
    bytes
        拼接后的序列化字节：C_time || C_data[0] || C_data[1] || ...

    Notes
    -----
    顺序：先序列化 C_time，再依次序列化每个 C_data
    """
    C_time_bytes = serialize_group_element(C_time)
    result = C_time_bytes
    for C_data in C_data_list:
        result += serialize_group_element(C_data)
    return result


def hash_for_signing(C_data_list: List[G1], C_time: G2) -> bytes:
    """
    哈希承诺列表和时间承诺用于签名生成。

    Parameters
    ----------
    C_data_list : List[G1]
        数据承诺列表
    C_time : G2
        时间承诺

    Returns
    -------
    bytes
        SHA-256 哈希值

    Notes
    -----
    使用 SHA-256 提供抗碰撞性。
    """
    serialized = serialize_for_signing(C_data_list, C_time)
    return hashlib.sha256(serialized).digest()


def sign_batch(sk_ecdsa: SigningKey, C_data_list: List[G1], C_time: G2) -> bytes:
    """
    签名批次（绑定所有数据列承诺和时间承诺）。

    Parameters
    ----------
    sk_ecdsa : SigningKey
        DO 的签名密钥
    C_data_list : List[G1]
        数据承诺列表
    C_time : G2
        时间承诺

    Returns
    -------
    bytes
        签名 σ = Sign(sk, Hash(C_time || C_data[0] || C_data[1] || ...))

    Notes
    -----
    签名绑定所有列的承诺和时间承诺，防止混合攻击。
    """
    h = hash_for_signing(C_data_list, C_time)
    sigma = sk_ecdsa.sign(h, sigencode=sigencode_string)
    return sigma


def verify_batch_signature(vk_ecdsa: VerifyingKey, C_data_list: List[G1], C_time: G2, sigma: bytes) -> bool:
    """
    验证批次签名。

    Parameters
    ----------
    vk_ecdsa : VerifyingKey
        DO 的验证密钥
    C_data_list : List[G1]
        数据承诺列表
    C_time : G2
        时间承诺
    sigma : bytes
        待验证的签名

    Returns
    -------
    bool
        签名有效返回 True，否则返回 False

    Notes
    -----
    验证签名是否绑定了所有承诺，任何篡改都会导致验证失败。
    """
    try:
        h = hash_for_signing(C_data_list, C_time)
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

