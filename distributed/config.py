"""
分布式VDS配置
定义各服务器的地址和端口
"""

import os

# 默认配置
DEFAULT_DO_HOST = os.getenv('DO_HOST', 'localhost')
DEFAULT_DO_PORT = int(os.getenv('DO_PORT', 5001))

DEFAULT_SS_HOST = os.getenv('SS_HOST', 'localhost')
DEFAULT_SS_PORT = int(os.getenv('SS_PORT', 5002))

DEFAULT_VERIFIER_HOST = os.getenv('VERIFIER_HOST', 'localhost')
DEFAULT_VERIFIER_PORT = int(os.getenv('VERIFIER_PORT', 5003))

# VDS参数
DEFAULT_VECTOR_DIM = int(os.getenv('VECTOR_DIM', 16))
DEFAULT_PAIRING_CURVE = os.getenv('PAIRING_CURVE', 'MNT224')

# 开发模式：允许共享alpha参数（仅用于测试！）
# 警告：在生产环境必须设置为False
DEV_MODE = os.getenv('DEV_MODE', 'true').lower() == 'true'


class Config:
    """配置类"""

    def __init__(self):
        self.do_host = DEFAULT_DO_HOST
        self.do_port = DEFAULT_DO_PORT
        self.ss_host = DEFAULT_SS_HOST
        self.ss_port = DEFAULT_SS_PORT
        self.verifier_host = DEFAULT_VERIFIER_HOST
        self.verifier_port = DEFAULT_VERIFIER_PORT
        self.vector_dim = DEFAULT_VECTOR_DIM
        self.pairing_curve = DEFAULT_PAIRING_CURVE
        self.dev_mode = DEV_MODE

    @property
    def do_url(self):
        return f"http://{self.do_host}:{self.do_port}"

    @property
    def ss_url(self):
        return f"http://{self.ss_host}:{self.ss_port}"

    @property
    def verifier_url(self):
        return f"http://{self.verifier_host}:{self.verifier_port}"


# 全局配置实例
config = Config()
