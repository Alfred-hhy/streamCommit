"""
Verifier (DC/DA) HTTP服务器
负责验证DC查询证明和DA审计证明
"""

from flask import Flask, request, jsonify
from charm.toolbox.pairinggroup import PairingGroup
from vds_verifier import Verifier
from distributed.serialization import *
from distributed.config import config
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

# 全局状态
verifier_state = {
    'group': None,
    'crs': None,
    'verifier': None,
    'initialized': False
}


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'initialized': verifier_state['initialized']})


@app.route('/init', methods=['POST'])
def init():
    """初始化Verifier（接收CRS和初始全局公钥）"""
    try:
        data = request.json
        curve = data.get('curve', config.pairing_curve)

        # 初始化群
        group = PairingGroup(curve)

        # 反序列化CRS
        crs_data = deserialize_crs(data['crs'], group)

        # 开发模式：如果CRS包含alpha，使用它重新生成完全相同的CRS
        if 'alpha' in crs_data and config.dev_mode:
            import sys
            print("⚠️  Verifier: Using shared alpha to regenerate CRS (DEV MODE)", file=sys.stderr)
            print(f"  alpha: {crs_data['alpha']}", file=sys.stderr)
            print(f"  g before regen: {crs_data['g']}", file=sys.stderr)
            from vc_smallness.crs import keygen_crs
            # 使用相同的alpha和生成器重新生成CRS
            crs = keygen_crs(
                crs_data['n'],
                group,
                alpha=crs_data['alpha'],
                g=crs_data['g'],
                g_hat=crs_data['g_hat']
            )
            print(f"  g after regen: {crs['g']}", file=sys.stderr)
            print(f"  g_list[1] after: {crs['g_list'][1]}", file=sys.stderr)
        else:
            crs = crs_data

        # 反序列化初始全局公钥
        global_pk = deserialize_global_pk(data['global_pk'], group)

        # 创建Verifier实例
        verifier = Verifier(crs, global_pk, group)

        # 保存状态
        verifier_state['group'] = group
        verifier_state['crs'] = crs
        verifier_state['verifier'] = verifier
        verifier_state['initialized'] = True

        return jsonify({'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/update_global_pk', methods=['POST'])
def update_global_pk():
    """更新全局公钥"""
    if not verifier_state['initialized']:
        return jsonify({'success': False, 'error': 'Verifier not initialized'}), 400

    try:
        data = request.json
        group = verifier_state['group']

        # 反序列化新的全局公钥
        new_global_pk = deserialize_global_pk(data['new_global_pk'], group)

        # 更新
        verifier_state['verifier'].update_global_pk(new_global_pk)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/verify_dc_query', methods=['POST'])
def verify_dc_query():
    """验证DC查询证明"""
    if not verifier_state['initialized']:
        return jsonify({'success': False, 'error': 'Verifier not initialized'}), 400

    try:
        data = request.json
        group = verifier_state['group']

        # 调试：打印接收到的数据类型
        import sys
        print(f"[Verifier] Received data keys: {data.keys()}", file=sys.stderr)
        print(f"[Verifier] public_header type: {type(data['public_header'])}", file=sys.stderr)
        if isinstance(data['public_header'], dict):
            print(f"[Verifier] public_header keys: {data['public_header'].keys()}", file=sys.stderr)
            print(f"[Verifier] C_data_list type: {type(data['public_header'].get('C_data_list'))}", file=sys.stderr)
        print(f"[Verifier] pi_non type: {type(data['pi_non'])}", file=sys.stderr)

        # 反序列化参数
        public_header = deserialize_public_header(data['public_header'], group)
        t_challenge = [group.init(ZR, val) for val in data['t_challenge']]
        x_result = group.init(ZR, data['x_result'])
        pi_audit = deserialize_g1(data['pi_audit'], group)
        pi_non = (
            deserialize_g1(data['pi_non'][0], group),
            deserialize_zr(data['pi_non'][1], group)
        )
        column_index = data.get('column_index', 0)

        # 调试：验证反序列化后的数据
        print(f"[Verifier] After deserialization:", file=sys.stderr)
        print(f"[Verifier] public_header keys: {public_header.keys()}", file=sys.stderr)
        print(f"[Verifier] C_data_list length: {len(public_header['C_data_list'])}", file=sys.stderr)
        print(f"[Verifier] C_data_list[0] type: {type(public_header['C_data_list'][0])}", file=sys.stderr)
        print(f"[Verifier] t_challenge length: {len(t_challenge)}", file=sys.stderr)
        print(f"[Verifier] x_result type: {type(x_result)}", file=sys.stderr)
        print(f"[Verifier] pi_audit type: {type(pi_audit)}", file=sys.stderr)
        print(f"[Verifier] pi_non type: {type(pi_non)}", file=sys.stderr)
        print(f"[Verifier] pi_non[0] type: {type(pi_non[0])}", file=sys.stderr)

        # 验证
        is_valid = verifier_state['verifier'].verify_dc_query(
            public_header, t_challenge, x_result, pi_audit, pi_non, column_index
        )

        import sys
        print(f"[Verifier] DC query verification result: {is_valid}", file=sys.stderr, flush=True)

        return jsonify({'success': True, 'is_valid': is_valid})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/verify_da_audit', methods=['POST'])
def verify_da_audit():
    """验证DA审计证明"""
    if not verifier_state['initialized']:
        return jsonify({'success': False, 'error': 'Verifier not initialized'}), 400

    try:
        data = request.json
        group = verifier_state['group']

        # 反序列化参数
        public_header = deserialize_public_header(data['public_header'], group)
        n = data['n']
        x_result = group.init(ZR, data['x_result'])
        pi_audit = deserialize_g1(data['pi_audit'], group)
        t_challenge = [group.init(ZR, val) for val in data['t_challenge']]
        pi_non = (
            deserialize_g1(data['pi_non'][0], group),
            deserialize_zr(data['pi_non'][1], group)
        )
        column_index = data.get('column_index', 0)

        # 验证
        is_valid = verifier_state['verifier'].verify_da_audit(
            public_header, n, x_result, pi_audit, t_challenge, pi_non, column_index
        )

        return jsonify({'success': True, 'is_valid': is_valid})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def main():
    """启动Verifier服务器"""
    host = config.verifier_host
    port = config.verifier_port
    print(f"Starting Verifier server on {host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
