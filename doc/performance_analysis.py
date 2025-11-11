"""
性能分析和可视化 / Performance Analysis and Visualization
=========================================================

生成性能分析图表，包括：
- 执行时间对比
- 内存使用趋势
- 性能扩展分析
- 操作复杂度分析

运行方式：
    python performance_analysis.py
"""

import json
import sys
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
import numpy as np
from typing import Dict, List

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置中文字体
rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'SimHei']
rcParams['axes.unicode_minus'] = False


class PerformanceAnalyzer:
    """性能分析类"""

    def __init__(self, results_file='try1028/benchmark_results.json'):
        """加载基准测试结果"""
        try:
            with open(results_file, 'r') as f:
                data = json.load(f)
                self.timing_results = data.get('timing', {})
                self.memory_results = data.get('memory', {})
        except FileNotFoundError:
            print(f"❌ 找不到结果文件: {results_file}")
            print("请先运行: python performance_benchmark.py")
            exit(1)
    
    def plot_crs_generation(self):
        """绘制 CRS 生成性能"""
        print("📊 绘制 CRS 生成性能图表...")
        
        data = self.timing_results.get('crs_generation', {})
        if not data:
            print("⚠️  没有 CRS 生成数据")
            return
        
        n_values = sorted([int(k) for k in data.keys()])
        times = [data[str(n)] * 1000 for n in n_values]  # 转换为 ms
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(n_values, times, 'o-', linewidth=2, markersize=8, color='#2E86AB', label='CRS Generation')
        ax.fill_between(n_values, times, alpha=0.3, color='#2E86AB')
        
        ax.set_xlabel('Vector Size (n)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Time (ms)', fontsize=12, fontweight='bold')
        ax.set_title('CRS Generation Performance', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11)
        
        plt.tight_layout()
        plt.savefig('perf_crs_generation.png', dpi=300, bbox_inches='tight')
        print("✅ 已保存: perf_crs_generation.png")
        plt.close()
    
    def plot_commitments_comparison(self):
        """绘制承诺生成对比"""
        print("📊 绘制承诺生成对比图表...")
        
        data = self.timing_results.get('commitments', {})
        if not data:
            print("⚠️  没有承诺数据")
            return
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        n_values = sorted([int(k) for k in data['commit_G'].keys()])
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
        
        for (name, color) in zip(['commit_G', 'commit_Ghat', 'commit_Cy', 'commit_V'], colors):
            times = [data[name][str(n)] * 1000 for n in n_values]
            ax.plot(n_values, times, 'o-', linewidth=2, markersize=8, label=name, color=color)
        
        ax.set_xlabel('Vector Size (n)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Time (ms)', fontsize=12, fontweight='bold')
        ax.set_title('Commitment Generation Performance Comparison', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        plt.tight_layout()
        plt.savefig('perf_commitments.png', dpi=300, bbox_inches='tight')
        print("✅ 已保存: perf_commitments.png")
        plt.close()
    
    def plot_proofs_comparison(self):
        """绘制证明生成对比"""
        print("📊 绘制证明生成对比图表...")
        
        data = self.timing_results.get('proofs', {})
        if not data:
            print("⚠️  没有证明数据")
            return
        
        fig, ax = plt.subplots(figsize=(12, 7))
        
        n_values = sorted([int(k) for k in data['point_open'].keys()])
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']
        
        for (name, color) in zip(['point_open', 'agg_open', 'equality', 'orthogonality', 'range'], colors):
            times = [data[name][str(n)] * 1000 for n in n_values]
            ax.plot(n_values, times, 'o-', linewidth=2, markersize=8, label=name, color=color)
        
        ax.set_xlabel('Vector Size (n)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Time (ms)', fontsize=12, fontweight='bold')
        ax.set_title('Proof Generation Performance Comparison', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        
        plt.tight_layout()
        plt.savefig('perf_proofs.png', dpi=300, bbox_inches='tight')
        print("✅ 已保存: perf_proofs.png")
        plt.close()
    
    def plot_verification_comparison(self):
        """绘制验证性能对比"""
        print("📊 绘制验证性能对比图表...")

        data = self.timing_results.get('verification', {})
        if not data:
            print("⚠️  没有验证数据")
            return

        fig, ax = plt.subplots(figsize=(12, 7))

        # 使用正确的键名
        verify_keys = ['verify_1_point_opening', 'verify_5_equality', 'verify_7_orthogonality',
                      'verify_9_range', 'verify_16_aggregated']
        n_values = sorted([int(k) for k in data[verify_keys[0]].keys()])
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']

        for (name, color) in zip(verify_keys, colors):
            times = [data[name][str(n)] * 1000 for n in n_values]
            ax.plot(n_values, times, 'o-', linewidth=2, markersize=8, label=name, color=color)

        ax.set_xlabel('Vector Size (n)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Time (ms)', fontsize=12, fontweight='bold')
        ax.set_title('Verification Performance Comparison', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)

        plt.tight_layout()
        plt.savefig('perf_verification.png', dpi=300, bbox_inches='tight')
        print("✅ 已保存: perf_verification.png")
        plt.close()
    
    def plot_memory_usage(self):
        """绘制内存使用"""
        print("📊 绘制内存使用图表...")
        
        data = self.memory_results.get('crs', {})
        if not data:
            print("⚠️  没有内存数据")
            return
        
        n_values = sorted([int(k) for k in data.keys()])
        memory = [data[str(n)] for n in n_values]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(range(len(n_values)), memory, color='#2E86AB', alpha=0.7, edgecolor='black', linewidth=1.5)
        ax.set_xticks(range(len(n_values)))
        ax.set_xticklabels([f'n={n}' for n in n_values])
        
        ax.set_xlabel('Vector Size (n)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Memory Usage (MB)', fontsize=12, fontweight='bold')
        ax.set_title('CRS Memory Usage', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加数值标签
        for i, v in enumerate(memory):
            ax.text(i, v + 0.01, f'{v:.2f}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('perf_memory.png', dpi=300, bbox_inches='tight')
        print("✅ 已保存: perf_memory.png")
        plt.close()
    
    def plot_complexity_analysis(self):
        """绘制复杂度分析"""
        print("📊 绘制复杂度分析图表...")
        
        data = self.timing_results.get('commitments', {})
        if not data:
            print("⚠️  没有数据")
            return
        
        n_values = sorted([int(k) for k in data['commit_G'].keys()])
        times = [data['commit_G'][str(n)] * 1000 for n in n_values]
        
        # 拟合 O(n) 和 O(n log n)
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # 实际数据
        ax.plot(n_values, times, 'o-', linewidth=2, markersize=8, label='Actual (commit_G)', color='#2E86AB')
        
        # 理论复杂度
        if len(n_values) >= 2:
            # 计算 O(n) 的系数
            coeff_n = times[0] / n_values[0]
            linear = [coeff_n * n for n in n_values]
            ax.plot(n_values, linear, '--', linewidth=2, label='O(n) fit', color='#F18F01', alpha=0.7)
            
            # 计算 O(n log n) 的系数
            coeff_nlogn = times[0] / (n_values[0] * np.log(n_values[0]))
            nlogn = [coeff_nlogn * n * np.log(n) for n in n_values]
            ax.plot(n_values, nlogn, ':', linewidth=2, label='O(n log n) fit', color='#C73E1D', alpha=0.7)
        
        ax.set_xlabel('Vector Size (n)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Time (ms)', fontsize=12, fontweight='bold')
        ax.set_title('Complexity Analysis: Commitment Generation', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11)
        
        plt.tight_layout()
        plt.savefig('perf_complexity.png', dpi=300, bbox_inches='tight')
        print("✅ 已保存: perf_complexity.png")
        plt.close()
    
    def plot_overall_summary(self):
        """绘制总体性能总结"""
        print("📊 绘制总体性能总结图表...")

        # 获取最大向量大小的数据
        data_commit = self.timing_results.get('commitments', {})
        data_proof = self.timing_results.get('proofs', {})
        data_verify = self.timing_results.get('verification', {})

        if not (data_commit and data_proof and data_verify):
            print("⚠️  数据不完整")
            return

        # 获取最大 n 值
        max_n = max(
            max(int(k) for k in data_commit['commit_G'].keys()),
            max(int(k) for k in data_proof['point_open'].keys()),
            max(int(k) for k in data_verify['verify_1_point_opening'].keys())
        )

        # 获取最大 n 的数据
        max_n_str = str(max_n)

        categories = ['Commit_G', 'Commit_Ghat', 'Commit_Cy', 'Point_Open', 'Agg_Open', 'Verify_1', 'Verify_5']
        times = [
            data_commit['commit_G'][max_n_str] * 1000,
            data_commit['commit_Ghat'][max_n_str] * 1000,
            data_commit['commit_Cy'][max_n_str] * 1000,
            data_proof['point_open'][max_n_str] * 1000,
            data_proof['agg_open'][max_n_str] * 1000,
            data_verify['verify_1_point_opening'][max_n_str] * 1000,
            data_verify['verify_5_equality'][max_n_str] * 1000,
        ]

        fig, ax = plt.subplots(figsize=(14, 7))
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E', '#D62828', '#F77F00']
        bars = ax.barh(categories, times, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)

        ax.set_xlabel('Time (ms)', fontsize=12, fontweight='bold')
        ax.set_title(f'Overall Performance Summary (n={max_n})', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')

        # 添加数值标签
        for i, (bar, time) in enumerate(zip(bars, times)):
            ax.text(time + 0.1, i, f'{time:.2f}ms', va='center', fontweight='bold')

        plt.tight_layout()
        plt.savefig('perf_summary.png', dpi=300, bbox_inches='tight')
        print("✅ 已保存: perf_summary.png")
        plt.close()
    def plot_bandwidth_analysis(self):
            """绘制通信带宽/开销分析"""
            print("📊 绘制通信带宽/开销分析图表...")

            data = self.timing_results.get('bandwidth', {})
            if not data:
                print("⚠️  没有带宽数据")
                return

            # 提取数据
            n_values = sorted([int(k) for k in data['header_size'].keys()])
            header_sizes = [data['header_size'][str(n)] for n in n_values]
            proof_sizes = [data['proof_size'][str(n)] for n in n_values]
            raw_data_sizes = [data['raw_data_size'][str(n)] for n in n_values]

            # 创建图表
            fig, ax = plt.subplots(figsize=(12, 8))

            # 绘制三条线
            ax.plot(n_values, header_sizes, 'o-', linewidth=2.5, markersize=10,
                    label='Header Size (Commitment)', color='#2E86AB') # 改为英文标签
            ax.plot(n_values, proof_sizes, 's-', linewidth=2.5, markersize=10,
                    label='Proof Size (VC Proof)', color='#A23B72')   # 改为英文标签
            ax.plot(n_values, raw_data_sizes, '^-', linewidth=2.5, markersize=10,
                    label='Raw Data Size (Baseline)', color='#F18F01') # 改为英文标签

            # 设置对数坐标（Y轴）
            ax.set_yscale('log')

            # 设置标签和标题（改为英文，避免乱码）
            ax.set_xlabel('Vector Size (N)', fontsize=13, fontweight='bold')
            ax.set_ylabel('Bytes (Log Scale)', fontsize=13, fontweight='bold')
            ax.set_title('Communication Cost Analysis', fontsize=15, fontweight='bold', pad=20)

            # 网格和图例
            ax.grid(True, alpha=0.3, which='both', linestyle='--')
            ax.legend(fontsize=11, loc='upper left', framealpha=0.9)

            # 添加注释说明 O(1) 特性
            if len(n_values) >= 2:
                mid_idx = len(n_values) // 2
                # 修改点：将箭头颜色改为黑色 ('black')，避免混淆
                ax.annotate('Constant Size O(1)', 
                            xy=(n_values[mid_idx], proof_sizes[mid_idx]),
                            xytext=(n_values[mid_idx] * 1.3, proof_sizes[mid_idx] * 5), #稍微调高一点位置
                            fontsize=10, fontweight='bold', color='black', # 文字改黑色
                            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8, edgecolor='gray'),
                            arrowprops=dict(arrowstyle='->', color='black', lw=1.5)) # 箭头改黑色

            plt.tight_layout()
            plt.savefig('perf_bandwidth.png', dpi=300, bbox_inches='tight')
            print("✅ 已保存: perf_bandwidth.png")
            plt.close()
    
    def generate_all_plots(self):
        """生成所有图表"""
        print("\n" + "="*60)
        print("🎨 开始生成性能分析图表")
        print("="*60 + "\n")

        self.plot_crs_generation()
        self.plot_commitments_comparison()
        self.plot_proofs_comparison()
        self.plot_verification_comparison()
        self.plot_memory_usage()
        self.plot_complexity_analysis()
        self.plot_overall_summary()
        self.plot_bandwidth_analysis()

        print("\n" + "="*60)
        print("✅ 所有图表已生成")
        print("="*60)


if __name__ == '__main__':
    analyzer = PerformanceAnalyzer()
    analyzer.generate_all_plots()

