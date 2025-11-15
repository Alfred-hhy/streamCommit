"""
Storage Server (SS) HTTP服务器
负责存储批次数据和生成证明
"""

from flask import Flask, request, jsonify
from charm.toolbox.pairinggroup import PairingGroup
from vds_server import StorageServer
from distributed.serialization import *
from distributed.config import config
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

# 全局状态
ss_state = {
    'group': None,
    'crs': None,
    'ss': None,
    'initialized': False
}


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'initialized': ss_state['initialized']})


@app.route('/init', methods=['POST'])
def init():
    """初始化SS（接收CRS和初始累加器密钥）"""
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
            print("⚠️  SS: Using shared alpha to regenerate CRS (DEV MODE)", file=sys.stderr)
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

        # 反序列化初始累加器密钥
        initial_g = deserialize_g1(data['server_acc_keys'], group)
        initial_server_acc_keys = (initial_g,)

        # 创建SS实例
        ss = StorageServer(crs, initial_server_acc_keys)

        # 保存状态
        ss_state['group'] = group
        ss_state['crs'] = crs
        ss_state['ss'] = ss
        ss_state['initialized'] = True

        return jsonify({'success': True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/store_batch', methods=['POST'])
def store_batch():
    """存储批次"""
    if not ss_state['initialized']:
        return jsonify({'success': False, 'error': 'SS not initialized'}), 400

    try:
        data = request.json
        group = ss_state['group']

        batch_id = data['batch_id']
        public_header = deserialize_public_header(data['public_header'], group)
        secrets = deserialize_secrets_for_ss(data['secrets_for_ss'], group)

        # 存储批次
        ss_state['ss'].store_batch(batch_id, public_header, secrets)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/add_server_key', methods=['POST'])
def add_server_key():
    """添加新的累加器服务器密钥"""
    if not ss_state['initialized']:
        return jsonify({'success': False, 'error': 'SS not initialized'}), 400

    try:
        data = request.json
        group = ss_state['group']

        g_s_q_new = deserialize_g1(data['g_s_q_new'], group)
        ss_state['ss'].add_server_key(g_s_q_new)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/add_revoked_item', methods=['POST'])
def add_revoked_item():
    """添加撤销的签名到黑名单"""
    if not ss_state['initialized']:
        return jsonify({'success': False, 'error': 'SS not initialized'}), 400

    try:
        data = request.json
        sigma_bytes = deserialize_bytes(data['sigma_bytes'])
        ss_state['ss'].add_revoked_item(sigma_bytes)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/update_batch', methods=['POST'])
def update_batch():
    """更新批次（撤销旧批次并存储新批次）"""
    if not ss_state['initialized']:
        return jsonify({'success': False, 'error': 'SS not initialized'}), 400

    try:
        data = request.json
        group = ss_state['group']

        old_batch_id = data['old_batch_id']
        g_s_q_new = deserialize_g1(data['g_s_q_new'], group)
        sigma_bytes = deserialize_bytes(data['sigma_bytes'])
        new_batch_id = data['new_batch_id']
        new_public_header = deserialize_public_header(data['new_public_header'], group)
        new_secrets = deserialize_secrets_for_ss(data['new_secrets_for_ss'], group)

        # 更新批次
        ss_state['ss'].update_batch(
            old_batch_id, g_s_q_new, sigma_bytes,
            new_batch_id, new_public_header, new_secrets
        )

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/generate_dc_proof', methods=['POST'])
def generate_dc_proof():
    """生成DC查询证明"""
    if not ss_state['initialized']:
        return jsonify({'success': False, 'error': 'SS not initialized'}), 400

    try:
        data = request.json
        group = ss_state['group']

        batch_id = data['batch_id']
        t_challenge = [group.init(ZR, val) for val in data['t_challenge']]
        f_current = deserialize_g1(data['f_current'], group)  # f_current是G1不是G2
        column_index = data.get('column_index', 0)

        # 生成证明
        x_result, pi_audit, pi_non = ss_state['ss'].generate_dc_data_proof(
            batch_id, t_challenge, f_current, column_index
        )

        # 序列化返回
        return jsonify({
            'success': True,
            'x_result': int(x_result),
            'pi_audit': serialize_g1(pi_audit, group),
            'pi_non': [  # 使用list而不是tuple，JSON会保持list
                serialize_g1(pi_non[0], group),
                serialize_zr(pi_non[1], group)
            ]
        })
    except Exception as e:
        import traceback
        traceback.print_exc()  # 打印详细错误到日志
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/generate_da_proof', methods=['POST'])
def generate_da_proof():
    """生成DA审计证明"""
    if not ss_state['initialized']:
        return jsonify({'success': False, 'error': 'SS not initialized'}), 400

    try:
        data = request.json
        group = ss_state['group']

        batch_id = data['batch_id']
        f_current = deserialize_g1(data['f_current'], group)  # f_current是G1不是G2
        column_index = data.get('column_index', 0)

        # 生成证明
        x_result, pi_audit, t_challenge, pi_non = ss_state['ss'].generate_da_audit_proof(
            batch_id, f_current, column_index
        )

        # 序列化返回
        return jsonify({
            'success': True,
            'x_result': int(x_result),
            'pi_audit': serialize_g1(pi_audit, group),
            't_challenge': [int(t) for t in t_challenge],
            'pi_non': [  # 使用list而不是tuple
                serialize_g1(pi_non[0], group),
                serialize_zr(pi_non[1], group)
            ]
        })
    except Exception as e:
        import traceback
        traceback.print_exc()  # 打印详细错误到日志
        return jsonify({'success': False, 'error': str(e)}), 500


def main():
    """启动SS服务器"""
    host = config.ss_host
    port = config.ss_port
    print(f"Starting SS server on {host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
