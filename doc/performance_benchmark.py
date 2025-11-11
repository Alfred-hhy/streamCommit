"""
性能基准测试 / Performance Benchmark
====================================

详细的性能测试，包括：
- 各个操作的执行时间
- 不同向量大小的性能扩展
- 内存使用情况
- 性能对比分析

运行方式：
    python performance_benchmark.py
"""

import time
import json
import sys
import os
from typing import Dict, List, Tuple
import tracemalloc

# 添加父目录到路径以导入 vc_smallness
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vc_smallness import setup, keygen_crs
from vc_smallness.commit import commit_G, commit_Ghat, commit_Cy, commit_V
from vc_smallness.proofs import (
    prove_point_open, prove_agg_open, prove_eq, prove_y, prove_x, aggregate_pi
)
from vc_smallness.verify import verify_1, verify_5, verify_7, verify_9, verify_16
from vc_smallness.fs_oracles import H_t, H_agg, H_s
from charm.toolbox.pairinggroup import ZR
from charm.core.engine.util import objectToBytes


class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self, curve='MNT224'):
        """初始化基准测试"""
        print(f"🔧 初始化性能测试 (曲线: {curve})...")
        self.params = setup(curve)
        self.group = self.params['group']
        self.results = {}
        self.memory_results = {}
        
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
    
    def measure_memory(self, func, *args, **kwargs) -> Tuple[float, any]:
        """测量函数内存使用（MB）"""
        tracemalloc.start()
        result = func(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return peak / 1024 / 1024, result  # 转换为 MB
    
    def benchmark_crs_generation(self, vector_sizes: List[int], num_runs=10):
        """基准测试 CRS 生成"""
        print("\n📊 CRS 生成性能测试 (每个测试重复 {} 次)".format(num_runs))
        print("=" * 60)

        results = {}
        std_devs = {}
        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)
            avg_time, std_dev, crs = self.measure_time(keygen_crs, n, self.group, num_runs=num_runs)
            results[n] = avg_time
            std_devs[n] = std_dev
            print(f"✓ {avg_time*1000:.2f} ± {std_dev*1000:.2f} ms")

        self.results['crs_generation'] = results
        self.results['crs_generation_std'] = std_devs
        return results
    
    def benchmark_commitments(self, vector_sizes: List[int], num_runs=10):
        """基准测试承诺生成"""
        print("\n📊 承诺生成性能测试 (每个测试重复 {} 次)".format(num_runs))
        print("=" * 60)

        results = {'commit_G': {}, 'commit_Ghat': {}, 'commit_Cy': {}, 'commit_V': {}}
        std_devs = {'commit_G': {}, 'commit_Ghat': {}, 'commit_Cy': {}, 'commit_V': {}}

        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)
            crs = keygen_crs(n, self.group)

            # 生成测试数据
            m = [self.group.random(ZR) for _ in range(n)]
            x = [self.group.random(ZR) for _ in range(n)]
            y = [self.group.init(ZR, i % 2) for i in range(n)]  # 二进制向量
            gamma = self.group.random(ZR)
            gamma_y = self.group.random(ZR)

            # 测试各个承诺
            t1, s1, _ = self.measure_time(commit_G, m, gamma, crs, num_runs=num_runs)
            t2, s2, _ = self.measure_time(commit_Ghat, x, gamma, crs, num_runs=num_runs)
            t3, s3, _ = self.measure_time(commit_Cy, y, x, gamma_y, crs, num_runs=num_runs)
            t4, s4, _ = self.measure_time(commit_V, self.group.init(ZR, 42), gamma, crs, num_runs=num_runs)

            results['commit_G'][n] = t1
            results['commit_Ghat'][n] = t2
            results['commit_Cy'][n] = t3
            results['commit_V'][n] = t4

            std_devs['commit_G'][n] = s1
            std_devs['commit_Ghat'][n] = s2
            std_devs['commit_Cy'][n] = s3
            std_devs['commit_V'][n] = s4

            print(f"✓ G:{t1*1000:.2f}±{s1*1000:.2f}ms Ĝ:{t2*1000:.2f}±{s2*1000:.2f}ms Cy:{t3*1000:.2f}±{s3*1000:.2f}ms V:{t4*1000:.2f}±{s4*1000:.2f}ms")

        self.results['commitments'] = results
        self.results['commitments_std'] = std_devs
        return results
    
    def benchmark_proofs(self, vector_sizes: List[int], num_runs=10):
        """基准测试证明生成"""
        print("\n📊 证明生成性能测试 (每个测试重复 {} 次)".format(num_runs))
        print("=" * 60)

        results = {
            'point_open': {},
            'agg_open': {},
            'equality': {},
            'orthogonality': {},
            'range': {}
        }
        std_devs = {
            'point_open': {},
            'agg_open': {},
            'equality': {},
            'orthogonality': {},
            'range': {}
        }

        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)
            crs = keygen_crs(n, self.group)

            # 生成测试数据
            m = [self.group.random(ZR) for _ in range(n)]
            x = [self.group.random(ZR) for _ in range(n)]
            y = [self.group.init(ZR, i % 2) for i in range(n)]
            gamma = self.group.random(ZR)
            gamma_y = self.group.random(ZR)

            # 生成承诺
            C = commit_G(m, gamma, crs)
            C_hat = commit_Ghat(x, gamma, crs)
            C_y = commit_Cy(y, x, gamma_y, crs)

            # 点开放证明
            t1, s1, pi_i = self.measure_time(prove_point_open, C, m, gamma, 1, crs, num_runs=num_runs)

            # 聚合开放证明
            t = [self.group.random(ZR) for _ in range(n)]
            t2, s2, pi_agg = self.measure_time(prove_agg_open, C, m, gamma, list(range(1, n+1)), t, crs, num_runs=num_runs)

            # 等式证明
            t3, s3, pi_eq = self.measure_time(prove_eq, t, y, x, gamma, gamma_y, crs, num_runs=num_runs)

            # 正交性证明
            t4, s4, pi_y = self.measure_time(prove_y, x, y, gamma, gamma_y, crs, num_runs=num_runs)

            # 范围证明
            bit_proofs = [prove_point_open(C_hat, x, gamma, i, crs) for i in range(1, min(n+1, 9))]
            t5, s5, pi_x = self.measure_time(prove_x, bit_proofs, gamma, crs, num_runs=num_runs)

            results['point_open'][n] = t1
            results['agg_open'][n] = t2
            results['equality'][n] = t3
            results['orthogonality'][n] = t4
            results['range'][n] = t5

            std_devs['point_open'][n] = s1
            std_devs['agg_open'][n] = s2
            std_devs['equality'][n] = s3
            std_devs['orthogonality'][n] = s4
            std_devs['range'][n] = s5

            print(f"✓ PO:{t1*1000:.2f}±{s1*1000:.2f}ms AO:{t2*1000:.2f}±{s2*1000:.2f}ms EQ:{t3*1000:.2f}±{s3*1000:.2f}ms ORT:{t4*1000:.2f}±{s4*1000:.2f}ms RNG:{t5*1000:.2f}±{s5*1000:.2f}ms")

        self.results['proofs'] = results
        self.results['proofs_std'] = std_devs
        return results
    
    def benchmark_verification(self, vector_sizes: List[int], num_runs=10):
        """
        基准测试验证

        验证方程说明:
        - verify_1 (方程1): 验证点开放证明 - 验证承诺C在特定位置的开放是否正确
        - verify_5 (方程5): 验证等式证明 - 验证 Ĉ 和 C_y 之间的等式关系
        - verify_7 (方程7): 验证正交性证明 - 验证向量 x 和 y 的正交性 (内积为0)
        - verify_9 (方程9): 验证范围证明 - 验证 Ĉ 和 V̂ 表示同一个值的不同表示
        - verify_16 (方程16): 验证聚合证明 - 同时验证等式和正交性的聚合证明
        """
        print("\n📊 验证性能测试 (每个测试重复 {} 次)".format(num_runs))
        print("=" * 60)

        results = {
            'verify_1_point_opening': {},
            'verify_5_equality': {},
            'verify_7_orthogonality': {},
            'verify_9_range': {},
            'verify_16_aggregated': {}
        }
        std_devs = {
            'verify_1_point_opening': {},
            'verify_5_equality': {},
            'verify_7_orthogonality': {},
            'verify_9_range': {},
            'verify_16_aggregated': {}
        }

        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)
            crs = keygen_crs(n, self.group)

            # 生成测试数据
            m = [self.group.random(ZR) for _ in range(n)]
            x = [self.group.random(ZR) for _ in range(n)]
            y = [self.group.init(ZR, i % 2) for i in range(n)]
            gamma = self.group.random(ZR)
            gamma_y = self.group.random(ZR)

            # 生成承诺和证明
            C = commit_G(m, gamma, crs)
            C_hat = commit_Ghat(x, gamma, crs)
            C_y = commit_Cy(y, x, gamma_y, crs)

            t = [self.group.random(ZR) for _ in range(n)]
            pis = [prove_point_open(C, m, gamma, i, crs) for i in range(1, n+1)]
            pi_eq = prove_eq(t, y, x, gamma, gamma_y, crs)
            pi_y = prove_y(x, y, gamma, gamma_y, crs)

            # 验证
            t1, s1, _ = self.measure_time(verify_1, C, pis, t, m, crs, num_runs=num_runs)
            t2, s2, _ = self.measure_time(verify_5, C_hat, C_y, t, y, pi_eq, crs, num_runs=num_runs)
            t3, s3, _ = self.measure_time(verify_7, C_hat, C_y, pi_y, y, crs, num_runs=num_runs)

            # verify_9 和 verify_16 需要特殊处理
            ell = min(n, 8)
            # 创建完整长度的向量，但只有前 ell 个是二进制位
            x_bits_full = [self.group.init(ZR, i % 2) if i < ell else self.group.init(ZR, 0) for i in range(n)]
            x_scalar = self.group.init(ZR, sum(int(x_bits_full[i]) * (2**i) for i in range(ell)))
            V_hat = commit_V(x_scalar, gamma, crs)
            bit_proofs = [prove_point_open(C_hat, x_bits_full, gamma, i, crs) for i in range(1, ell+1)]
            pi_x = prove_x(bit_proofs, gamma, crs)

            t4, s4, _ = self.measure_time(verify_9, C_hat, V_hat, pi_x, ell, crs, num_runs=num_runs)

            # verify_16
            delta_eq = self.group.random(ZR)
            delta_y = self.group.random(ZR)
            pi = aggregate_pi(pi_eq, pi_y, delta_eq, delta_y, crs)
            t5, s5, _ = self.measure_time(verify_16, C_hat, C_y, pi, delta_eq, delta_y, t, y, crs, num_runs=num_runs)

            results['verify_1_point_opening'][n] = t1
            results['verify_5_equality'][n] = t2
            results['verify_7_orthogonality'][n] = t3
            results['verify_9_range'][n] = t4
            results['verify_16_aggregated'][n] = t5

            std_devs['verify_1_point_opening'][n] = s1
            std_devs['verify_5_equality'][n] = s2
            std_devs['verify_7_orthogonality'][n] = s3
            std_devs['verify_9_range'][n] = s4
            std_devs['verify_16_aggregated'][n] = s5

            print(f"✓ V1:{t1*1000:.2f}±{s1*1000:.2f}ms V5:{t2*1000:.2f}±{s2*1000:.2f}ms V7:{t3*1000:.2f}±{s3*1000:.2f}ms V9:{t4*1000:.2f}±{s4*1000:.2f}ms V16:{t5*1000:.2f}±{s5*1000:.2f}ms")

        self.results['verification'] = results
        self.results['verification_std'] = std_devs
        return results
    
    def benchmark_memory(self, vector_sizes: List[int]):
        """基准测试内存使用"""
        print("\n📊 内存使用性能测试")
        print("=" * 60)

        results = {}
        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)
            mem, crs = self.measure_memory(keygen_crs, n, self.group)
            results[n] = mem
            print(f"✓ {mem:.2f} MB")

        self.memory_results['crs'] = results
        return results

    def benchmark_bandwidth(self, vector_sizes: List[int]):
        """
        基准测试通信带宽/开销

        通过序列化对象并测量字节大小来评估通信开销。
        这展示了 VDS 系统的核心优势：证明大小为 O(1)，与数据量 N 无关。
        """
        print("\n📊 通信带宽/开销性能测试")
        print("=" * 60)

        results = {
            'header_size': {},
            'proof_size': {},
            'raw_data_size': {}
        }

        for n in vector_sizes:
            print(f"  测试 n={n}...", end=" ", flush=True)

            # 生成 CRS
            crs = keygen_crs(n, self.group)

            # 生成随机数据向量 m (长度 N)
            m = [self.group.random(ZR) for _ in range(n)]
            gamma = self.group.random(ZR)

            # Header 大小：生成承诺 C
            C = commit_G(m, gamma, crs)
            C_bytes = objectToBytes(C, self.group)
            header_size = len(C_bytes)

            # Proof 大小：生成聚合证明 π_agg
            t = [self.group.random(ZR) for _ in range(n)]
            pi_agg = prove_agg_open(C, m, gamma, list(range(1, n+1)), t, crs)
            pi_bytes = objectToBytes(pi_agg, self.group)
            proof_size = len(pi_bytes)

            # Raw Data 大小（基准对比）：假设每个 ZR 元素约 32 字节
            raw_data_size = n * 32

            # 记录结果
            results['header_size'][n] = header_size
            results['proof_size'][n] = proof_size
            results['raw_data_size'][n] = raw_data_size

            print(f"✓ Header:{header_size}B Proof:{proof_size}B RawData:{raw_data_size}B")

        self.results['bandwidth'] = results
        return results
    
    def run_all_benchmarks(self, vector_sizes: List[int] = None, num_runs: int = 10):
        """
        运行所有基准测试

        Args:
            vector_sizes: 要测试的向量大小列表
            num_runs: 每个测试重复的次数（默认10次）
        """
        if vector_sizes is None:
            vector_sizes = [4, 8, 16, 32, 64]

        print("\n" + "="*60)
        print("🚀 开始性能基准测试")
        print(f"   每个测试将重复 {num_runs} 次并计算平均值和标准差")
        print("="*60)

        self.benchmark_crs_generation(vector_sizes, num_runs)
        self.benchmark_commitments(vector_sizes, num_runs)
        self.benchmark_proofs(vector_sizes, num_runs)
        self.benchmark_verification(vector_sizes, num_runs)
        self.benchmark_memory(vector_sizes)
        self.benchmark_bandwidth(vector_sizes)

        print("\n" + "="*60)
        print("✅ 性能基准测试完成")
        print("="*60)
    
    def save_results(self, filename='benchmark_results.json'):
        """保存结果到 JSON 文件"""
        import os
        # 确保目录存在
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)

        data = {
            'timing': self.results,
            'memory': self.memory_results
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n💾 结果已保存到 {filename}")
    
    def print_summary(self):
        """打印性能总结"""
        print("\n" + "="*60)
        print("📈 性能总结")
        print("="*60)
        
        for category, data in self.results.items():
            print(f"\n{category.upper()}:")
            if isinstance(data, dict):
                for key, values in data.items():
                    if isinstance(values, dict):
                        print(f"  {key}:")
                        for n, t in values.items():
                            print(f"    n={n}: {t*1000:.2f} ms")
                    else:
                        print(f"  {key}: {values*1000:.2f} ms")


if __name__ == '__main__':
    # 运行基准测试
    # num_runs=10 表示每个测试重复10次，计算平均值和标准差
    benchmark = PerformanceBenchmark('MNT224')
    benchmark.run_all_benchmarks([4, 8, 16, 32], num_runs=10)
    benchmark.save_results('try1028/benchmark_results.json')
    benchmark.print_summary()

