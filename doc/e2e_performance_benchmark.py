"""
端到端性能基准测试 / End-to-End Performance Benchmark
=======================================================

测试完整的 VDS Scheme C+ 工作流性能，包括：
1. 批次创建 (DO)
2. 数据消费者查询 (DC)
3. 审计员审计 (DA)
4. 批次撤销 (DO)
5. 时间范围证明

运行方式：
    python e2e_performance_benchmark.py
"""

import time
import json
import sys
import os
from typing import Dict, List, Tuple
import tracemalloc
import pickle

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from charm.toolbox.pairinggroup import ZR
from vc_smallness import setup, keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier


class E2EPerformanceBenchmark:
    """端到端性能基准测试类"""
    
    def __init__(self, curve='MNT224'):
        """初始化基准测试"""
        print(f"🔧 初始化端到端性能测试 (曲线: {curve})...")
        self.params = setup(curve)
        self.group = self.params['group']
        self.results = {}
        self.bandwidth_results = {}
        
    def measure_time(self, func, *args, num_runs=10, **kwargs) -> Tuple[float, float, any]:
        """
        测量函数执行时间的平均值和标准差（秒）

        Args:
            func: 要测试的函数
            num_runs: 重复测试次数（默认10次）
            *args, **kwargs: 传递给函数的参数

        Returns:
            (平均时间, 标准差, 最后一次执行结果)
        """
        times = []
        result = None

        for _ in range(num_runs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            times.append(end - start)

        avg_time = sum(times) / len(times)
        std_dev = (sum((t - avg_time)**2 for t in times) / len(times)) ** 0.5

        return avg_time, std_dev, result
    
    def measure_size(self, obj) -> int:
        """测量对象序列化后的字节大小"""
        try:
            return len(pickle.dumps(obj))
        except:
            # 如果无法序列化，返回字符串长度的估计
            return len(str(obj).encode())
    
    def benchmark_batch_creation(self, vector_sizes: List[int], num_runs=10):
        """
        基准测试批次创建的端到端性能
        
        测试流程：
        1. DO 创建批次 (commit + sign)
        2. SS 存储批次
        """
        print("\n📊 批次创建端到端性能测试 (每个测试重复 {} 次)".format(num_runs))
        print("=" * 70)

        results = {
            'do_create_batch': {},
            'ss_store_batch': {},
            'total_batch_creation': {}
        }
        std_devs = {
            'do_create_batch': {},
            'ss_store_batch': {},
            'total_batch_creation': {}
        }
        bandwidth = {
            'public_header_size': {},
            'secrets_size': {}
        }

        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)
            
            # 设置系统
            crs = keygen_crs(n, self.group)
            do = DataOwner(crs, self.group)
            initial_keys = do.get_initial_server_keys()
            ss = StorageServer(crs, initial_keys)
            
            # 生成测试数据
            m_vector = [self.group.init(ZR, i + 10) for i in range(n)]
            t_vector = [self.group.init(ZR, i + 1) for i in range(n)]
            
            # 测试 DO 创建批次
            def create_batch():
                return do.create_batch(m_vector, t_vector)
            
            t1, s1, (batch_id, public_header, secrets) = self.measure_time(
                create_batch, num_runs=num_runs
            )
            
            # 测试 SS 存储批次
            def store_batch():
                ss.store_batch(batch_id, public_header, secrets)
            
            t2, s2, _ = self.measure_time(store_batch, num_runs=num_runs)
            
            # 总时间
            total_time = t1 + t2
            total_std = (s1**2 + s2**2) ** 0.5
            
            results['do_create_batch'][n] = t1
            results['ss_store_batch'][n] = t2
            results['total_batch_creation'][n] = total_time
            
            std_devs['do_create_batch'][n] = s1
            std_devs['ss_store_batch'][n] = s2
            std_devs['total_batch_creation'][n] = total_std
            
            # 测量带宽
            bandwidth['public_header_size'][n] = self.measure_size(public_header)
            bandwidth['secrets_size'][n] = self.measure_size(secrets)
            
            print(f"✓ DO:{t1*1000:.2f}±{s1*1000:.2f}ms SS:{t2*1000:.2f}±{s2*1000:.2f}ms 总:{total_time*1000:.2f}±{total_std*1000:.2f}ms")

        self.results['batch_creation'] = results
        self.results['batch_creation_std'] = std_devs
        self.bandwidth_results['batch_creation'] = bandwidth
        return results
    
    def benchmark_dc_query(self, vector_sizes: List[int], num_runs=10):
        """
        基准测试数据消费者查询的端到端性能
        
        测试流程：
        1. DC 发起查询 (提供挑战向量)
        2. SS 生成证明
        3. Verifier 验证证明
        """
        print("\n📊 DC 查询端到端性能测试 (每个测试重复 {} 次)".format(num_runs))
        print("=" * 70)

        results = {
            'ss_generate_proof': {},
            'verifier_verify': {},
            'total_dc_query': {}
        }
        std_devs = {
            'ss_generate_proof': {},
            'verifier_verify': {},
            'total_dc_query': {}
        }
        bandwidth = {
            'proof_size': {},
            'result_size': {}
        }

        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)
            
            # 设置系统并创建批次
            crs = keygen_crs(n, self.group)
            do = DataOwner(crs, self.group)
            initial_keys = do.get_initial_server_keys()
            ss = StorageServer(crs, initial_keys)
            global_pk = do.get_global_pk()
            verifier = Verifier(crs, global_pk, self.group)
            
            # 创建批次
            m_vector = [self.group.init(ZR, i + 10) for i in range(n)]
            t_vector = [self.group.init(ZR, i + 1) for i in range(n)]
            batch_id, public_header, secrets = do.create_batch(m_vector, t_vector)
            ss.store_batch(batch_id, public_header, secrets)
            
            # DC 挑战向量 (求和)
            t_challenge = [self.group.init(ZR, 1) for _ in range(n)]
            f_current = global_pk["f_current"]
            
            # 测试 SS 生成证明
            def generate_proof():
                return ss.generate_dc_data_proof(batch_id, t_challenge, f_current)
            
            t1, s1, (x_result, pi_audit, pi_non) = self.measure_time(
                generate_proof, num_runs=num_runs
            )
            
            # 测试 Verifier 验证
            def verify_proof():
                return verifier.verify_dc_query(
                    public_header, t_challenge, x_result, pi_audit, pi_non
                )
            
            t2, s2, is_valid = self.measure_time(verify_proof, num_runs=num_runs)
            
            # 总时间
            total_time = t1 + t2
            total_std = (s1**2 + s2**2) ** 0.5
            
            results['ss_generate_proof'][n] = t1
            results['verifier_verify'][n] = t2
            results['total_dc_query'][n] = total_time
            
            std_devs['ss_generate_proof'][n] = s1
            std_devs['verifier_verify'][n] = s2
            std_devs['total_dc_query'][n] = total_std
            
            # 测量带宽
            proof_size = self.measure_size(pi_audit) + self.measure_size(pi_non)
            bandwidth['proof_size'][n] = proof_size
            bandwidth['result_size'][n] = self.measure_size(x_result)
            
            status = "✓" if is_valid else "✗"
            print(f"{status} SS:{t1*1000:.2f}±{s1*1000:.2f}ms Ver:{t2*1000:.2f}±{s2*1000:.2f}ms 总:{total_time*1000:.2f}±{total_std*1000:.2f}ms")

        self.results['dc_query'] = results
        self.results['dc_query_std'] = std_devs
        self.bandwidth_results['dc_query'] = bandwidth
        return results
    
    def benchmark_da_audit(self, vector_sizes: List[int], num_runs=10):
        """
        基准测试审计员审计的端到端性能
        
        测试流程：
        1. SS 生成零知识审计证明
        2. Verifier 验证证明
        """
        print("\n📊 DA 审计端到端性能测试 (每个测试重复 {} 次)".format(num_runs))
        print("=" * 70)

        results = {
            'ss_generate_audit_proof': {},
            'verifier_verify_audit': {},
            'total_da_audit': {}
        }
        std_devs = {
            'ss_generate_audit_proof': {},
            'verifier_verify_audit': {},
            'total_da_audit': {}
        }
        bandwidth = {
            'audit_proof_size': {},
            'challenge_size': {}
        }

        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)
            
            # 设置系统并创建批次
            crs = keygen_crs(n, self.group)
            do = DataOwner(crs, self.group)
            initial_keys = do.get_initial_server_keys()
            ss = StorageServer(crs, initial_keys)
            global_pk = do.get_global_pk()
            verifier = Verifier(crs, global_pk, self.group)
            
            # 创建批次
            m_vector = [self.group.init(ZR, i + 10) for i in range(n)]
            t_vector = [self.group.init(ZR, i + 1) for i in range(n)]
            batch_id, public_header, secrets = do.create_batch(m_vector, t_vector)
            ss.store_batch(batch_id, public_header, secrets)
            
            f_current = global_pk["f_current"]
            
            # 测试 SS 生成审计证明
            def generate_audit_proof():
                return ss.generate_da_audit_proof(batch_id, f_current)
            
            t1, s1, (x_result, pi_audit, t_challenge, pi_non) = self.measure_time(
                generate_audit_proof, num_runs=num_runs
            )
            
            # 测试 Verifier 验证
            def verify_audit():
                return verifier.verify_da_audit(
                    public_header, n, x_result, pi_audit, t_challenge, pi_non
                )
            
            t2, s2, is_valid = self.measure_time(verify_audit, num_runs=num_runs)
            
            # 总时间
            total_time = t1 + t2
            total_std = (s1**2 + s2**2) ** 0.5
            
            results['ss_generate_audit_proof'][n] = t1
            results['verifier_verify_audit'][n] = t2
            results['total_da_audit'][n] = total_time
            
            std_devs['ss_generate_audit_proof'][n] = s1
            std_devs['verifier_verify_audit'][n] = s2
            std_devs['total_da_audit'][n] = total_std
            
            # 测量带宽
            audit_proof_size = self.measure_size(pi_audit) + self.measure_size(pi_non)
            bandwidth['audit_proof_size'][n] = audit_proof_size
            bandwidth['challenge_size'][n] = self.measure_size(t_challenge)
            
            status = "✓" if is_valid else "✗"
            print(f"{status} SS:{t1*1000:.2f}±{s1*1000:.2f}ms Ver:{t2*1000:.2f}±{s2*1000:.2f}ms 总:{total_time*1000:.2f}±{total_std*1000:.2f}ms")

        self.results['da_audit'] = results
        self.results['da_audit_std'] = std_devs
        self.bandwidth_results['da_audit'] = bandwidth
        return results

    def benchmark_revocation(self, vector_sizes: List[int], num_runs=10):
        """
        基准测试批次撤销的端到端性能

        测试流程：
        1. DO 撤销批次
        2. SS 更新密钥
        3. Verifier 更新 global_pk
        4. 验证撤销后的查询失败
        """
        print("\n📊 批次撤销端到端性能测试 (每个测试重复 {} 次)".format(num_runs))
        print("=" * 70)

        results = {
            'do_revoke_batch': {},
            'ss_update_keys': {},
            'verifier_update_pk': {},
            'verify_revoked_batch': {},
            'total_revocation': {}
        }
        std_devs = {
            'do_revoke_batch': {},
            'ss_update_keys': {},
            'verifier_update_pk': {},
            'verify_revoked_batch': {},
            'total_revocation': {}
        }
        bandwidth = {
            'new_key_size': {},
            'new_pk_size': {}
        }

        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)

            # 设置系统并创建批次
            crs = keygen_crs(n, self.group)
            do = DataOwner(crs, self.group)
            initial_keys = do.get_initial_server_keys()
            ss = StorageServer(crs, initial_keys)
            global_pk = do.get_global_pk()
            verifier = Verifier(crs, global_pk, self.group)

            # 创建批次
            m_vector = [self.group.init(ZR, i + 10) for i in range(n)]
            t_vector = [self.group.init(ZR, i + 1) for i in range(n)]
            batch_id, public_header, secrets = do.create_batch(m_vector, t_vector)
            ss.store_batch(batch_id, public_header, secrets)

            sigma_to_revoke = public_header["sigma"]

            # 测试 DO 撤销批次
            def revoke_batch():
                return do.revoke_batch(sigma_to_revoke)

            t1, s1, (g_s_q_new, new_global_pk) = self.measure_time(
                revoke_batch, num_runs=num_runs
            )

            # 测试 SS 更新密钥
            def update_ss_keys():
                ss.add_server_key(g_s_q_new)

            t2, s2, _ = self.measure_time(update_ss_keys, num_runs=num_runs)

            # 测试 Verifier 更新 global_pk
            def update_verifier_pk():
                verifier.update_global_pk(new_global_pk)

            t3, s3, _ = self.measure_time(update_verifier_pk, num_runs=num_runs)

            # 测试验证撤销后的批次
            t_challenge = [self.group.init(ZR, 1) for _ in range(n)]
            f_current_new = new_global_pk["f_current"]
            x_result, pi_audit, pi_non = ss.generate_dc_data_proof(
                batch_id, t_challenge, f_current_new
            )

            def verify_revoked():
                return verifier.verify_dc_query(
                    public_header, t_challenge, x_result, pi_audit, pi_non
                )

            t4, s4, is_valid = self.measure_time(verify_revoked, num_runs=num_runs)

            # 总时间
            total_time = t1 + t2 + t3 + t4
            total_std = (s1**2 + s2**2 + s3**2 + s4**2) ** 0.5

            results['do_revoke_batch'][n] = t1
            results['ss_update_keys'][n] = t2
            results['verifier_update_pk'][n] = t3
            results['verify_revoked_batch'][n] = t4
            results['total_revocation'][n] = total_time

            std_devs['do_revoke_batch'][n] = s1
            std_devs['ss_update_keys'][n] = s2
            std_devs['verifier_update_pk'][n] = s3
            std_devs['verify_revoked_batch'][n] = s4
            std_devs['total_revocation'][n] = total_std

            # 测量带宽
            bandwidth['new_key_size'][n] = self.measure_size(g_s_q_new)
            bandwidth['new_pk_size'][n] = self.measure_size(new_global_pk)

            status = "✓" if not is_valid else "✗"  # 撤销后应该验证失败
            print(f"{status} DO:{t1*1000:.2f}±{s1*1000:.2f}ms SS:{t2*1000:.2f}±{s2*1000:.2f}ms Ver:{t3*1000:.2f}±{s3*1000:.2f}ms 总:{total_time*1000:.2f}±{total_std*1000:.2f}ms")

        self.results['revocation'] = results
        self.results['revocation_std'] = std_devs
        self.bandwidth_results['revocation'] = bandwidth
        return results

    def benchmark_time_range_proof(self, vector_sizes: List[int], num_runs=10):
        """
        基准测试时间范围证明的端到端性能

        测试流程：
        1. SS 生成时间范围证明
        2. Verifier 验证时间范围证明
        """
        print("\n📊 时间范围证明端到端性能测试 (每个测试重复 {} 次)".format(num_runs))
        print("=" * 70)

        results = {
            'ss_generate_time_proof': {},
            'verifier_verify_time_proof': {},
            'total_time_range_proof': {}
        }
        std_devs = {
            'ss_generate_time_proof': {},
            'verifier_verify_time_proof': {},
            'total_time_range_proof': {}
        }
        bandwidth = {
            'time_proof_size': {}
        }

        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)

            # 设置系统并创建批次
            crs = keygen_crs(n, self.group)
            do = DataOwner(crs, self.group)
            initial_keys = do.get_initial_server_keys()
            ss = StorageServer(crs, initial_keys)
            global_pk = do.get_global_pk()
            verifier = Verifier(crs, global_pk, self.group)

            # 创建批次
            m_vector = [self.group.init(ZR, i + 10) for i in range(n)]
            t_vector = [self.group.init(ZR, i + 1) for i in range(n)]
            batch_id, public_header, secrets = do.create_batch(m_vector, t_vector)
            ss.store_batch(batch_id, public_header, secrets)

            f_current = global_pk["f_current"]

            # 测试 SS 生成时间范围证明
            def generate_time_proof():
                return ss.generate_time_range_proofs(batch_id, f_current)

            t1, s1, time_proofs = self.measure_time(
                generate_time_proof, num_runs=num_runs
            )

            # 测试 Verifier 验证时间范围证明
            def verify_time_proofs():
                results = []
                for proof_data in time_proofs:
                    is_valid = verifier.verify_time_range_proof(
                        public_header, proof_data, f_current
                    )
                    results.append(is_valid)
                return all(results)

            t2, s2, all_valid = self.measure_time(verify_time_proofs, num_runs=num_runs)

            # 总时间
            total_time = t1 + t2
            total_std = (s1**2 + s2**2) ** 0.5

            results['ss_generate_time_proof'][n] = t1
            results['verifier_verify_time_proof'][n] = t2
            results['total_time_range_proof'][n] = total_time

            std_devs['ss_generate_time_proof'][n] = s1
            std_devs['verifier_verify_time_proof'][n] = s2
            std_devs['total_time_range_proof'][n] = total_std

            # 测量带宽
            bandwidth['time_proof_size'][n] = sum(
                self.measure_size(proof) for proof in time_proofs
            )

            status = "✓" if all_valid else "✗"
            print(f"{status} SS:{t1*1000:.2f}±{s1*1000:.2f}ms Ver:{t2*1000:.2f}±{s2*1000:.2f}ms 总:{total_time*1000:.2f}±{total_std*1000:.2f}ms")

        self.results['time_range_proof'] = results
        self.results['time_range_proof_std'] = std_devs
        self.bandwidth_results['time_range_proof'] = bandwidth
        return results

    def save_results(self, filename='e2e_benchmark_results.json'):
        """保存测试结果到 JSON 文件"""
        output = {
            'performance': self.results,
            'bandwidth': self.bandwidth_results
        }

        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n💾 结果已保存到: {filename}")

    def print_summary(self):
        """打印测试结果摘要"""
        print("\n" + "=" * 70)
        print("📊 端到端性能测试摘要")
        print("=" * 70)

        # 批次创建摘要
        if 'batch_creation' in self.results:
            print("\n1️⃣  批次创建:")
            for n, time in self.results['batch_creation']['total_batch_creation'].items():
                std = self.results['batch_creation_std']['total_batch_creation'][n]
                header_size = self.bandwidth_results['batch_creation']['public_header_size'][n]
                secrets_size = self.bandwidth_results['batch_creation']['secrets_size'][n]
                print(f"   n={n:2d}: {time*1000:6.2f}±{std*1000:5.2f}ms | "
                      f"Header:{header_size/1024:6.2f}KB Secrets:{secrets_size/1024:6.2f}KB")

        # DC 查询摘要
        if 'dc_query' in self.results:
            print("\n2️⃣  DC 查询:")
            for n, time in self.results['dc_query']['total_dc_query'].items():
                std = self.results['dc_query_std']['total_dc_query'][n]
                proof_size = self.bandwidth_results['dc_query']['proof_size'][n]
                print(f"   n={n:2d}: {time*1000:6.2f}±{std*1000:5.2f}ms | "
                      f"Proof:{proof_size/1024:6.2f}KB")

        # DA 审计摘要
        if 'da_audit' in self.results:
            print("\n3️⃣  DA 审计:")
            for n, time in self.results['da_audit']['total_da_audit'].items():
                std = self.results['da_audit_std']['total_da_audit'][n]
                proof_size = self.bandwidth_results['da_audit']['audit_proof_size'][n]
                print(f"   n={n:2d}: {time*1000:6.2f}±{std*1000:5.2f}ms | "
                      f"Proof:{proof_size/1024:6.2f}KB")

        # 撤销摘要
        if 'revocation' in self.results:
            print("\n4️⃣  批次撤销:")
            for n, time in self.results['revocation']['total_revocation'].items():
                std = self.results['revocation_std']['total_revocation'][n]
                key_size = self.bandwidth_results['revocation']['new_key_size'][n]
                print(f"   n={n:2d}: {time*1000:6.2f}±{std*1000:5.2f}ms | "
                      f"NewKey:{key_size/1024:6.2f}KB")

        # 时间范围证明摘要
        if 'time_range_proof' in self.results:
            print("\n5️⃣  时间范围证明:")
            for n, time in self.results['time_range_proof']['total_time_range_proof'].items():
                std = self.results['time_range_proof_std']['total_time_range_proof'][n]
                proof_size = self.bandwidth_results['time_range_proof']['time_proof_size'][n]
                print(f"   n={n:2d}: {time*1000:6.2f}±{std*1000:5.2f}ms | "
                      f"Proof:{proof_size/1024:6.2f}KB")

        print("\n" + "=" * 70)


def main():
    """主函数"""
    print("🚀 VDS Scheme C+ 端到端性能基准测试")
    print("=" * 70)

    # 初始化测试
    benchmark = E2EPerformanceBenchmark(curve='MNT224')

    # 测试向量大小
    vector_sizes = [4, 8, 16]
    num_runs = 10

    print(f"\n📋 测试配置:")
    print(f"   - 向量大小: {vector_sizes}")
    print(f"   - 每个测试重复: {num_runs} 次")
    print(f"   - 曲线: MNT224")

    # 运行所有测试
    benchmark.benchmark_batch_creation(vector_sizes, num_runs)
    benchmark.benchmark_dc_query(vector_sizes, num_runs)
    benchmark.benchmark_da_audit(vector_sizes, num_runs)
    benchmark.benchmark_revocation(vector_sizes, num_runs)
    benchmark.benchmark_time_range_proof(vector_sizes, num_runs)

    # 打印摘要
    benchmark.print_summary()

    # 保存结果
    benchmark.save_results('e2e_benchmark_results.json')

    print("\n✅ 所有测试完成！")


if __name__ == '__main__':
    main()


