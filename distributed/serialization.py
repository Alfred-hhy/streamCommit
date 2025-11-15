"""
分布式VDS序列化工具
用于在HTTP传输中序列化/反序列化Charm群元素和其他数据结构
"""

import base64
import json
from typing import Dict, List, Tuple, Any
from charm.toolbox.pairinggroup import PairingGroup, G1, G2, ZR
from charm.core.engine.util import objectToBytes, bytesToObject
from ecdsa import VerifyingKey, NIST256p
from distributed.config import config


def serialize_g1(elem: G1, group: PairingGroup) -> str:
    """序列化G1元素为base64字符串，特殊处理单位元"""
    # 检查是否是单位元
    if elem == group.init(G1, 1):
        return "__IDENTITY_G1__"
    return base64.b64encode(objectToBytes(elem, group)).decode('utf-8')


def deserialize_g1(data: str, group: PairingGroup) -> G1:
    """从base64字符串反序列化G1元素，特殊处理单位元"""
    if data == "__IDENTITY_G1__":
        return group.init(G1, 1)
    return bytesToObject(base64.b64decode(data), group)


def serialize_g2(elem: G2, group: PairingGroup) -> str:
    """序列化G2元素为base64字符串，特殊处理单位元"""
    # 检查是否是单位元
    if elem == group.init(G2, 1):
        return "__IDENTITY_G2__"
    return base64.b64encode(objectToBytes(elem, group)).decode('utf-8')


def deserialize_g2(data: str, group: PairingGroup) -> G2:
    """从base64字符串反序列化G2元素，特殊处理单位元"""
    if data == "__IDENTITY_G2__":
        return group.init(G2, 1)
    return bytesToObject(base64.b64decode(data), group)


def serialize_zr(elem: ZR, group: PairingGroup) -> str:
    """序列化ZR元素为base64字符串"""
    return base64.b64encode(objectToBytes(elem, group)).decode('utf-8')


def deserialize_zr(data: str, group: PairingGroup) -> ZR:
    """从base64字符串反序列化ZR元素"""
    return bytesToObject(base64.b64decode(data), group)


def serialize_vk(vk: VerifyingKey) -> str:
    """序列化ECDSA验证密钥"""
    return base64.b64encode(vk.to_string()).decode('utf-8')


def deserialize_vk(data: str) -> VerifyingKey:
    """反序列化ECDSA验证密钥"""
    return VerifyingKey.from_string(base64.b64decode(data), curve=NIST256p)


def serialize_bytes(data: bytes) -> str:
    """序列化字节数据为base64字符串"""
    return base64.b64encode(data).decode('utf-8')


def deserialize_bytes(data: str) -> bytes:
    """从base64字符串反序列化字节数据"""
    return base64.b64decode(data)


def serialize_crs(crs: dict, group: PairingGroup) -> dict:
    """序列化CRS用于网络传输"""
    result = {
        'n': crs['n'],
        'g': serialize_g1(crs['g'], group),
        'g_hat': serialize_g2(crs['g_hat'], group),
        'g_list': {str(k): serialize_g1(v, group) for k, v in crs['g_list'].items()},
        'g_hat_list': {str(k): serialize_g2(v, group) for k, v in crs['g_hat_list'].items()},
    }

    # 开发模式：包含alpha参数（警告：仅用于测试！）
    if config.dev_mode and 'alpha' in crs:
        result['alpha'] = serialize_zr(crs['alpha'], group)
        result['_dev_mode_warning'] = 'DEVELOPMENT MODE: alpha included (INSECURE!)'

    return result


def deserialize_crs(data: dict, group: PairingGroup) -> dict:
    """从网络数据反序列化CRS"""
    result = {
        'group': group,
        'n': data['n'],
        'g': deserialize_g1(data['g'], group),
        'g_hat': deserialize_g2(data['g_hat'], group),
        'g_list': {int(k): deserialize_g1(v, group) for k, v in data['g_list'].items()},
        'g_hat_list': {int(k): deserialize_g2(v, group) for k, v in data['g_hat_list'].items()},
    }

    # 开发模式：如果有alpha，反序列化它
    if 'alpha' in data:
        result['alpha'] = deserialize_zr(data['alpha'], group)

    return result


def serialize_global_pk(global_pk: dict, group: PairingGroup) -> dict:
    """序列化全局公钥"""
    # acc_pk是一个元组(g, g_hat, g_hat_s)
    acc_pk_tuple = global_pk['acc_pk']
    return {
        'vk_sig': serialize_vk(global_pk['vk_sig']),
        'acc_pk': [
            serialize_g1(acc_pk_tuple[0], group),  # g
            serialize_g2(acc_pk_tuple[1], group),  # g_hat
            serialize_g2(acc_pk_tuple[2], group),  # g_hat_s
        ],
        'f_current': serialize_g1(global_pk['f_current'], group),  # f_current是G1不是G2
    }


def deserialize_global_pk(data: dict, group: PairingGroup) -> dict:
    """反序列化全局公钥"""
    # acc_pk序列化为列表，反序列化为元组
    acc_pk_list = data['acc_pk']
    return {
        'vk_sig': deserialize_vk(data['vk_sig']),
        'acc_pk': (
            deserialize_g1(acc_pk_list[0], group),  # g
            deserialize_g2(acc_pk_list[1], group),  # g_hat
            deserialize_g2(acc_pk_list[2], group),  # g_hat_s
        ),
        'f_current': deserialize_g1(data['f_current'], group),  # f_current是G1不是G2
    }


def serialize_public_header(header: dict, group: PairingGroup) -> dict:
    """序列化批次公开头部"""
    return {
        'C_data_list': [serialize_g1(c, group) for c in header['C_data_list']],
        'C_time': serialize_g2(header['C_time'], group),
        'sigma': serialize_bytes(header['sigma']),
    }


def deserialize_public_header(data: dict, group: PairingGroup) -> dict:
    """反序列化批次公开头部"""
    return {
        'C_data_list': [deserialize_g1(c, group) for c in data['C_data_list']],
        'C_time': deserialize_g2(data['C_time'], group),
        'sigma': deserialize_bytes(data['sigma']),
    }


def serialize_secrets_for_ss(secrets: dict, group: PairingGroup) -> dict:
    """序列化SS存储的秘密数据"""
    # 将ZR元素转换为int（如果需要）
    def to_int_list(vec):
        if len(vec) > 0 and hasattr(vec[0], '__int__'):  # 是ZR元素
            return [int(v) for v in vec]
        return vec  # 已经是int列表

    # 处理m_matrix（可能是List[List[ZR]]或List[List[int]]）
    m_matrix_ints = [to_int_list(col) for col in secrets['m_matrix']]

    # 处理t（可能是List[ZR]或List[int]）
    t_ints = to_int_list(secrets['t'])

    return {
        'm_matrix': m_matrix_ints,
        't': t_ints,
        'gamma_data_list': [serialize_zr(r, group) for r in secrets['gamma_data_list']],
        'gamma_time': serialize_zr(secrets['gamma_time'], group),
    }


def deserialize_secrets_for_ss(data: dict, group: PairingGroup) -> dict:
    """反序列化SS存储的秘密数据"""
    # 将int转换为ZR元素
    m_matrix_zr = [[group.init(ZR, val) for val in col] for col in data['m_matrix']]
    t_zr = [group.init(ZR, val) for val in data['t']]

    return {
        'm_matrix': m_matrix_zr,
        't': t_zr,
        'gamma_data_list': [deserialize_zr(r, group) for r in data['gamma_data_list']],
        'gamma_time': deserialize_zr(data['gamma_time'], group),
    }


def serialize_point_proof(proof: dict, group: PairingGroup) -> dict:
    """序列化点查询证明"""
    return {
        'pi_vc': {
            'pi_G': serialize_g1(proof['pi_vc']['pi_G'], group),
            'pi_Ghat': serialize_g2(proof['pi_vc']['pi_Ghat'], group),
        },
        'pi_non': (
            serialize_g1(proof['pi_non'][0], group),
            serialize_zr(proof['pi_non'][1], group),
        ),
        'y': proof['y'],  # int
    }


def deserialize_point_proof(data: dict, group: PairingGroup) -> dict:
    """反序列化点查询证明"""
    return {
        'pi_vc': {
            'pi_G': deserialize_g1(data['pi_vc']['pi_G'], group),
            'pi_Ghat': deserialize_g2(data['pi_vc']['pi_Ghat'], group),
        },
        'pi_non': (
            deserialize_g1(data['pi_non'][0], group),
            deserialize_zr(data['pi_non'][1], group),
        ),
        'y': data['y'],
    }


def serialize_agg_proof(proof: dict, group: PairingGroup) -> dict:
    """序列化聚合证明"""
    return {
        'pi_vc': {
            'pi_G': serialize_g1(proof['pi_vc']['pi_G'], group),
            'pi_Ghat': serialize_g2(proof['pi_vc']['pi_Ghat'], group),
        },
        'pi_non': (
            serialize_g1(proof['pi_non'][0], group),
            serialize_zr(proof['pi_non'][1], group),
        ),
        'y': proof['y'],  # int
    }


def deserialize_agg_proof(data: dict, group: PairingGroup) -> dict:
    """反序列化聚合证明"""
    return {
        'pi_vc': {
            'pi_G': deserialize_g1(data['pi_vc']['pi_G'], group),
            'pi_Ghat': deserialize_g2(data['pi_vc']['pi_Ghat'], group),
        },
        'pi_non': (
            deserialize_g1(data['pi_non'][0], group),
            deserialize_zr(data['pi_non'][1], group),
        ),
        'y': data['y'],
    }
