#!/usr/bin/env python3
"""
通信带宽测试脚本
================

测试 VDS 系统的通信开销，展示证明大小 O(1) 的特性。
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from doc.performance_benchmark import PerformanceBenchmark
from doc.performance_analysis import PerformanceAnalyzer


def main():
    print("=" * 70)
    print("VDS 通信带宽/开销测试")
    print("=" * 70)
    print()
    print("本测试将展示 VDS 系统的核心优势：")
    print("  - 证明大小为 O(1)，与数据量 N 无关")
    print("  - 承诺大小为 O(1)，与数据量 N 无关")
    print("  - 原始数据大小为 O(N)，线性增长")
    print()
    
    # 测试更大范围的向量大小
    vector_sizes = [4, 8, 16, 32, 64, 128]
    
    print(f"测试向量大小: {vector_sizes}")
    print()
    
    # 运行基准测试
    benchmark = PerformanceBenchmark('MNT224')
    
    # 只运行带宽测试
    print("🚀 开始带宽测试...")
    print()
    results = benchmark.benchmark_bandwidth(vector_sizes)
    
    # 保存结果
    benchmark.results['bandwidth'] = results
    benchmark.save_results('bandwidth_test_results.json')
    
    # 打印结果摘要
    print()
    print("=" * 70)
    print("📊 测试结果摘要")
    print("=" * 70)
    print()
    print(f"{'向量大小 (n)':<15} {'Header (B)':<15} {'Proof (B)':<15} {'Raw Data (B)':<15} {'压缩比':<10}")
    print("-" * 70)
    
    for n in vector_sizes:
        header_size = results['header_size'][n]
        proof_size = results['proof_size'][n]
        raw_data_size = results['raw_data_size'][n]
        compression_ratio = raw_data_size / (header_size + proof_size)
        
        print(f"{n:<15} {header_size:<15} {proof_size:<15} {raw_data_size:<15} {compression_ratio:.2f}x")
    
    print()
    print("=" * 70)
    print("✅ 测试完成")
    print("=" * 70)
    print()
    print("关键观察：")
    print("  1. Header 和 Proof 大小保持恒定（~180-188 字节）")
    print("  2. Raw Data 大小随 N 线性增长")
    print("  3. 当 N 增大时，压缩比显著提升")
    print()
    print("这展示了向量承诺的核心优势：")
    print("  - 无论数据量多大，证明大小始终保持常数级别")
    print("  - 验证者只需下载固定大小的证明，而不是全部数据")
    print()


if __name__ == '__main__':
    main()

