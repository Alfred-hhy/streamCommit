"""
Data Owner (DO) HTTP服务器
负责创建批次、撤销批次、管理累加器
"""

from flask import Flask, request, jsonify
from charm.toolbox.pairinggroup import PairingGroup
from vc_smallness.crs import keygen_crs
from vds_owner import DataOwner
from distributed.serialization import *
from distributed.config import config
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

# 全局状态
do_state = {
    'group': None,
    'crs': None,
    'do': None,
    'initialized': False
}


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'initialized': do_state['initialized']})


@app.route('/init', methods=['POST'])
def init():
    """初始化DO（生成密钥、CRS）"""
    try:
        data = request.json
        n = data.get('n', config.vector_dim)
        curve = data.get('curve', config.pairing_curve)

        # 开发模式警告
        if config.dev_mode:
            import sys
            print("⚠️  WARNING: Running in DEVELOPMENT MODE - alpha will be shared (INSECURE!)", file=sys.stderr)
            print("⚠️  Set DEV_MODE=false for production use", file=sys.stderr)

        # 初始化群
        group = PairingGroup(curve)
        crs = keygen_crs(n, group)

        print(f"DO CRS g_list[1]: {crs['g_list'][1]}", file=sys.stderr)

        # 创建DO实例
        do = DataOwner(crs, group)

        # 保存状态
        do_state['group'] = group
        do_state['crs'] = crs
        do_state['do'] = do
        do_state['initialized'] = True

        # 返回CRS和初始全局公钥、累加器服务器密钥
        return jsonify({
            'success': True,
            'crs': serialize_crs(crs, group),
            'global_pk': serialize_global_pk(do.global_pk, group),
            'server_acc_keys': serialize_g1(do.server_acc_keys[0], group)  # 初始只有g
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/get_crs', methods=['GET'])
def get_crs():
    """获取CRS"""
    if not do_state['initialized']:
        return jsonify({'success': False, 'error': 'DO not initialized'}), 400

    return jsonify({
        'success': True,
        'crs': serialize_crs(do_state['crs'], do_state['group'])
    })


@app.route('/get_global_pk', methods=['GET'])
def get_global_pk():
    """获取当前全局公钥"""
    if not do_state['initialized']:
        return jsonify({'success': False, 'error': 'DO not initialized'}), 400

    return jsonify({
        'success': True,
        'global_pk': serialize_global_pk(do_state['do'].global_pk, do_state['group'])
    })


@app.route('/create_batch', methods=['POST'])
def create_batch():
    """创建新批次"""
    if not do_state['initialized']:
        return jsonify({'success': False, 'error': 'DO not initialized'}), 400

    try:
        data = request.json
        group = do_state['group']

        # 反序列化数据矩阵和时间向量
        # data_vectors是int列表的列表: [[col1], [col2], ...]
        data_vectors = data['data_vectors']
        time_vector = data['time_vector']

        # 转换为ZR元素
        m_matrix = [[group.init(ZR, val) for val in col] for col in data_vectors]
        t_vector = [group.init(ZR, val) for val in time_vector]

        # 创建批次
        batch_id, public_header, secrets_for_ss = do_state['do'].create_batch(m_matrix, t_vector)

        # 序列化返回
        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'public_header': serialize_public_header(public_header, group),
            'secrets_for_ss': serialize_secrets_for_ss(secrets_for_ss, group)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/revoke_batch', methods=['POST'])
def revoke_batch():
    """撤销批次"""
    if not do_state['initialized']:
        return jsonify({'success': False, 'error': 'DO not initialized'}), 400

    try:
        data = request.json
        group = do_state['group']

        # 反序列化签名
        sigma = deserialize_bytes(data['sigma'])

        # 撤销批次
        g_s_q_new, new_global_pk, sigma_bytes = do_state['do'].revoke_batch(sigma)

        # 序列化返回
        return jsonify({
            'success': True,
            'g_s_q_new': serialize_g1(g_s_q_new, group),
            'new_global_pk': serialize_global_pk(new_global_pk, group),
            'sigma_bytes': serialize_bytes(sigma_bytes)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/update_batch', methods=['POST'])
def update_batch():
    """更新批次（撤销旧批次并创建新批次）"""
    if not do_state['initialized']:
        return jsonify({'success': False, 'error': 'DO not initialized'}), 400

    try:
        data = request.json
        group = do_state['group']

        # 反序列化旧批次头部
        old_header = deserialize_public_header(data['old_header'], group)

        # 反序列化新数据
        new_data_vectors = data['new_data_vectors']
        new_time_vector = data['new_time_vector']

        # 转换为ZR元素
        new_m_matrix = [[group.init(ZR, val) for val in col] for col in new_data_vectors]
        new_t_vector = [group.init(ZR, val) for val in new_time_vector]

        # 更新批次
        result = do_state['do'].update_batch(old_header, new_m_matrix, new_t_vector)
        g_s_q_new, new_global_pk, sigma_bytes, new_batch_id, new_header, new_secrets = result

        # 序列化返回
        return jsonify({
            'success': True,
            'g_s_q_new': serialize_g1(g_s_q_new, group),
            'new_global_pk': serialize_global_pk(new_global_pk, group),
            'sigma_bytes': serialize_bytes(sigma_bytes),
            'new_batch_id': new_batch_id,
            'new_public_header': serialize_public_header(new_header, group),
            'new_secrets_for_ss': serialize_secrets_for_ss(new_secrets, group)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def main():
    """启动DO服务器"""
    host = config.do_host
    port = config.do_port
    print(f"Starting DO server on {host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
