"""
分布式VDS客户端库
封装HTTP调用，提供统一的接口
"""

import requests
from typing import Dict, List, Tuple, Any
from distributed.config import config


class DOClient:
    """Data Owner客户端"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.do_url

    def health(self) -> dict:
        """健康检查"""
        resp = requests.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    def init(self, n: int = None, curve: str = None) -> dict:
        """初始化DO"""
        data = {}
        if n:
            data['n'] = n
        if curve:
            data['curve'] = curve
        resp = requests.post(f"{self.base_url}/init", json=data)
        resp.raise_for_status()
        return resp.json()

    def get_crs(self) -> dict:
        """获取CRS"""
        resp = requests.get(f"{self.base_url}/get_crs")
        resp.raise_for_status()
        return resp.json()

    def get_global_pk(self) -> dict:
        """获取全局公钥"""
        resp = requests.get(f"{self.base_url}/get_global_pk")
        resp.raise_for_status()
        return resp.json()

    def create_batch(self, data_vectors: List[List[int]], time_vector: List[int]) -> dict:
        """创建批次"""
        resp = requests.post(f"{self.base_url}/create_batch", json={
            'data_vectors': data_vectors,
            'time_vector': time_vector
        })
        resp.raise_for_status()
        return resp.json()

    def revoke_batch(self, sigma: str) -> dict:
        """撤销批次"""
        resp = requests.post(f"{self.base_url}/revoke_batch", json={'sigma': sigma})
        resp.raise_for_status()
        return resp.json()

    def update_batch(self, old_header: dict, new_data_vectors: List[List[int]],
                     new_time_vector: List[int]) -> dict:
        """更新批次"""
        resp = requests.post(f"{self.base_url}/update_batch", json={
            'old_header': old_header,
            'new_data_vectors': new_data_vectors,
            'new_time_vector': new_time_vector
        })
        resp.raise_for_status()
        return resp.json()


class SSClient:
    """Storage Server客户端"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.ss_url

    def health(self) -> dict:
        """健康检查"""
        resp = requests.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    def init(self, crs: dict, server_acc_keys: str, curve: str = None) -> dict:
        """初始化SS"""
        data = {'crs': crs, 'server_acc_keys': server_acc_keys}
        if curve:
            data['curve'] = curve
        resp = requests.post(f"{self.base_url}/init", json=data)
        resp.raise_for_status()
        return resp.json()

    def store_batch(self, batch_id: str, public_header: dict, secrets_for_ss: dict) -> dict:
        """存储批次"""
        resp = requests.post(f"{self.base_url}/store_batch", json={
            'batch_id': batch_id,
            'public_header': public_header,
            'secrets_for_ss': secrets_for_ss
        })
        resp.raise_for_status()
        return resp.json()

    def add_server_key(self, g_s_q_new: str) -> dict:
        """添加新的累加器密钥"""
        resp = requests.post(f"{self.base_url}/add_server_key", json={'g_s_q_new': g_s_q_new})
        resp.raise_for_status()
        return resp.json()

    def add_revoked_item(self, sigma_bytes: str) -> dict:
        """添加撤销的签名到黑名单"""
        resp = requests.post(f"{self.base_url}/add_revoked_item", json={'sigma_bytes': sigma_bytes})
        resp.raise_for_status()
        return resp.json()

    def update_batch(self, old_batch_id: str, g_s_q_new: str, sigma_bytes: str,
                     new_batch_id: str, new_public_header: dict, new_secrets_for_ss: dict) -> dict:
        """更新批次"""
        resp = requests.post(f"{self.base_url}/update_batch", json={
            'old_batch_id': old_batch_id,
            'g_s_q_new': g_s_q_new,
            'sigma_bytes': sigma_bytes,
            'new_batch_id': new_batch_id,
            'new_public_header': new_public_header,
            'new_secrets_for_ss': new_secrets_for_ss
        })
        resp.raise_for_status()
        return resp.json()

    def generate_dc_proof(self, batch_id: str, t_challenge: List[int],
                          f_current: str, column_index: int = 0) -> dict:
        """生成DC查询证明"""
        resp = requests.post(f"{self.base_url}/generate_dc_proof", json={
            'batch_id': batch_id,
            't_challenge': t_challenge,
            'f_current': f_current,
            'column_index': column_index
        })
        resp.raise_for_status()
        return resp.json()

    def generate_da_proof(self, batch_id: str, f_current: str, column_index: int = 0) -> dict:
        """生成DA审计证明"""
        resp = requests.post(f"{self.base_url}/generate_da_proof", json={
            'batch_id': batch_id,
            'f_current': f_current,
            'column_index': column_index
        })
        resp.raise_for_status()
        return resp.json()


class VerifierClient:
    """Verifier客户端"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.verifier_url

    def health(self) -> dict:
        """健康检查"""
        resp = requests.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    def init(self, crs: dict, global_pk: dict, curve: str = None) -> dict:
        """初始化Verifier"""
        data = {'crs': crs, 'global_pk': global_pk}
        if curve:
            data['curve'] = curve
        resp = requests.post(f"{self.base_url}/init", json=data)
        resp.raise_for_status()
        return resp.json()

    def update_global_pk(self, new_global_pk: dict) -> dict:
        """更新全局公钥"""
        resp = requests.post(f"{self.base_url}/update_global_pk", json={'new_global_pk': new_global_pk})
        resp.raise_for_status()
        return resp.json()

    def verify_dc_query(self, public_header: dict, t_challenge: List[int],
                        x_result: int, pi_audit: str, pi_non: tuple, column_index: int = 0) -> dict:
        """验证DC查询证明"""
        resp = requests.post(f"{self.base_url}/verify_dc_query", json={
            'public_header': public_header,
            't_challenge': t_challenge,
            'x_result': x_result,
            'pi_audit': pi_audit,
            'pi_non': pi_non,
            'column_index': column_index
        })
        resp.raise_for_status()
        return resp.json()

    def verify_da_audit(self, public_header: dict, n: int, x_result: int,
                        pi_audit: str, t_challenge: List[int], pi_non: tuple, column_index: int = 0) -> dict:
        """验证DA审计证明"""
        resp = requests.post(f"{self.base_url}/verify_da_audit", json={
            'public_header': public_header,
            'n': n,
            'x_result': x_result,
            'pi_audit': pi_audit,
            't_challenge': t_challenge,
            'pi_non': pi_non,
            'column_index': column_index
        })
        resp.raise_for_status()
        return resp.json()
