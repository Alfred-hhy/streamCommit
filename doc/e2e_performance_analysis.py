"""
端到端性能分析与可视化 / End-to-End Performance Analysis
========================================================

读取端到端性能测试结果并生成可视化图表。

运行方式：
    python e2e_performance_analysis.py
"""

import json
import sys
import os
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class E2EPerformanceAnalysis:
    """端到端性能分析类"""
    
    def __init__(self, results_file='e2e_benchmark_results.json'):
        """加载测试结果"""
        print(f"📂 加载测试结果: {results_file}")
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        self.performance = data['performance']
        self.bandwidth = data['bandwidth']
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        print("✅ 数据加载完成")
    
    def plot_batch_creation(self):
        """绘制批次创建性能图"""
        print("📊 生成批次创建性能图...")
        
        data = self.performance['batch_creation']
        std_data = self.performance['batch_creation_std']
        
        vector_sizes = sorted(data['total_batch_creation'].keys(), key=int)
        
        do_times = [data['do_create_batch'][n] * 1000 for n in vector_sizes]
        ss_times = [data['ss_store_batch'][n] * 1000 for n in vector_sizes]
        total_times = [data['total_batch_creation'][n] * 1000 for n in vector_sizes]
        
        do_stds = [std_data['do_create_batch'][n] * 1000 for n in vector_sizes]
        ss_stds = [std_data['ss_store_batch'][n] * 1000 for n in vector_sizes]
        total_stds = [std_data['total_batch_creation'][n] * 1000 for n in vector_sizes]
        
        x = np.arange(len(vector_sizes))
        width = 0.25
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.bar(x - width, do_times, width, yerr=do_stds, label='DO 创建批次', 
               capsize=5, alpha=0.8)
        ax.bar(x, ss_times, width, yerr=ss_stds, label='SS 存储批次', 
               capsize=5, alpha=0.8)
        ax.bar(x + width, total_times, width, yerr=total_stds, label='总时间', 
               capsize=5, alpha=0.8)
        
        ax.set_xlabel('向量大小 (n)', fontsize=12)
        ax.set_ylabel('时间 (ms)', fontsize=12)
        ax.set_title('批次创建端到端性能', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([f'n={n}' for n in vector_sizes])
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('e2e_batch_creation.png', dpi=300, bbox_inches='tight')
        print("   ✓ 保存: e2e_batch_creation.png")
        plt.close()
    
    def plot_query_performance(self):
        """绘制查询性能对比图"""
        print("📊 生成查询性能对比图...")
        
        dc_data = self.performance['dc_query']
        da_data = self.performance['da_audit']
        dc_std = self.performance['dc_query_std']
        da_std = self.performance['da_audit_std']
        
        vector_sizes = sorted(dc_data['total_dc_query'].keys(), key=int)
        
        dc_times = [dc_data['total_dc_query'][n] * 1000 for n in vector_sizes]
        da_times = [da_data['total_da_audit'][n] * 1000 for n in vector_sizes]
        
        dc_stds = [dc_std['total_dc_query'][n] * 1000 for n in vector_sizes]
        da_stds = [da_std['total_da_audit'][n] * 1000 for n in vector_sizes]
        
        x = np.arange(len(vector_sizes))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.bar(x - width/2, dc_times, width, yerr=dc_stds, label='DC 查询', 
               capsize=5, alpha=0.8, color='#2ecc71')
        ax.bar(x + width/2, da_times, width, yerr=da_stds, label='DA 审计', 
               capsize=5, alpha=0.8, color='#3498db')
        
        ax.set_xlabel('向量大小 (n)', fontsize=12)
        ax.set_ylabel('时间 (ms)', fontsize=12)
        ax.set_title('查询与审计性能对比', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([f'n={n}' for n in vector_sizes])
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('e2e_query_performance.png', dpi=300, bbox_inches='tight')
        print("   ✓ 保存: e2e_query_performance.png")
        plt.close()
    
    def plot_bandwidth(self):
        """绘制带宽/通信开销图"""
        print("📊 生成带宽/通信开销图...")
        
        batch_bw = self.bandwidth['batch_creation']
        dc_bw = self.bandwidth['dc_query']
        da_bw = self.bandwidth['da_audit']
        
        vector_sizes = sorted(batch_bw['public_header_size'].keys(), key=int)
        
        # 转换为 KB
        header_sizes = [batch_bw['public_header_size'][n] / 1024 for n in vector_sizes]
        secrets_sizes = [batch_bw['secrets_size'][n] / 1024 for n in vector_sizes]
        dc_proof_sizes = [dc_bw['proof_size'][n] / 1024 for n in vector_sizes]
        da_proof_sizes = [da_bw['audit_proof_size'][n] / 1024 for n in vector_sizes]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # 左图：批次创建的数据大小
        x = np.arange(len(vector_sizes))
        width = 0.35
        
        ax1.bar(x - width/2, header_sizes, width, label='公开头', alpha=0.8)
        ax1.bar(x + width/2, secrets_sizes, width, label='秘密数据', alpha=0.8)
        
        ax1.set_xlabel('向量大小 (n)', fontsize=12)
        ax1.set_ylabel('大小 (KB)', fontsize=12)
        ax1.set_title('批次创建数据大小', fontsize=13, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels([f'n={n}' for n in vector_sizes])
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 右图：证明大小对比
        ax2.bar(x - width/2, dc_proof_sizes, width, label='DC 证明', alpha=0.8, color='#2ecc71')
        ax2.bar(x + width/2, da_proof_sizes, width, label='DA 证明', alpha=0.8, color='#3498db')
        
        ax2.set_xlabel('向量大小 (n)', fontsize=12)
        ax2.set_ylabel('大小 (KB)', fontsize=12)
        ax2.set_title('证明大小对比', fontsize=13, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels([f'n={n}' for n in vector_sizes])
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('e2e_bandwidth.png', dpi=300, bbox_inches='tight')
        print("   ✓ 保存: e2e_bandwidth.png")
        plt.close()
    
    def plot_revocation_performance(self):
        """绘制撤销性能图"""
        print("📊 生成撤销性能图...")
        
        data = self.performance['revocation']
        std_data = self.performance['revocation_std']
        
        vector_sizes = sorted(data['total_revocation'].keys(), key=int)
        
        do_times = [data['do_revoke_batch'][n] * 1000 for n in vector_sizes]
        ss_times = [data['ss_update_keys'][n] * 1000 for n in vector_sizes]
        ver_times = [data['verifier_update_pk'][n] * 1000 for n in vector_sizes]
        verify_times = [data['verify_revoked_batch'][n] * 1000 for n in vector_sizes]
        
        do_stds = [std_data['do_revoke_batch'][n] * 1000 for n in vector_sizes]
        ss_stds = [std_data['ss_update_keys'][n] * 1000 for n in vector_sizes]
        ver_stds = [std_data['verifier_update_pk'][n] * 1000 for n in vector_sizes]
        verify_stds = [std_data['verify_revoked_batch'][n] * 1000 for n in vector_sizes]
        
        x = np.arange(len(vector_sizes))
        width = 0.2
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.bar(x - 1.5*width, do_times, width, yerr=do_stds, label='DO 撤销', 
               capsize=5, alpha=0.8)
        ax.bar(x - 0.5*width, ss_times, width, yerr=ss_stds, label='SS 更新密钥', 
               capsize=5, alpha=0.8)
        ax.bar(x + 0.5*width, ver_times, width, yerr=ver_stds, label='Verifier 更新PK', 
               capsize=5, alpha=0.8)
        ax.bar(x + 1.5*width, verify_times, width, yerr=verify_stds, label='验证撤销', 
               capsize=5, alpha=0.8)
        
        ax.set_xlabel('向量大小 (n)', fontsize=12)
        ax.set_ylabel('时间 (ms)', fontsize=12)
        ax.set_title('批次撤销端到端性能', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([f'n={n}' for n in vector_sizes])
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('e2e_revocation.png', dpi=300, bbox_inches='tight')
        print("   ✓ 保存: e2e_revocation.png")
        plt.close()
    
    def plot_time_range_proof(self):
        """绘制时间范围证明性能图"""
        print("📊 生成时间范围证明性能图...")
        
        data = self.performance['time_range_proof']
        std_data = self.performance['time_range_proof_std']
        
        vector_sizes = sorted(data['total_time_range_proof'].keys(), key=int)
        
        ss_times = [data['ss_generate_time_proof'][n] * 1000 for n in vector_sizes]
        ver_times = [data['verifier_verify_time_proof'][n] * 1000 for n in vector_sizes]
        total_times = [data['total_time_range_proof'][n] * 1000 for n in vector_sizes]
        
        ss_stds = [std_data['ss_generate_time_proof'][n] * 1000 for n in vector_sizes]
        ver_stds = [std_data['verifier_verify_time_proof'][n] * 1000 for n in vector_sizes]
        total_stds = [std_data['total_time_range_proof'][n] * 1000 for n in vector_sizes]
        
        x = np.arange(len(vector_sizes))
        width = 0.25
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.bar(x - width, ss_times, width, yerr=ss_stds, label='SS 生成证明', 
               capsize=5, alpha=0.8, color='#e74c3c')
        ax.bar(x, ver_times, width, yerr=ver_stds, label='Verifier 验证', 
               capsize=5, alpha=0.8, color='#9b59b6')
        ax.bar(x + width, total_times, width, yerr=total_stds, label='总时间', 
               capsize=5, alpha=0.8, color='#34495e')
        
        ax.set_xlabel('向量大小 (n)', fontsize=12)
        ax.set_ylabel('时间 (ms)', fontsize=12)
        ax.set_title('时间范围证明端到端性能', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([f'n={n}' for n in vector_sizes])
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('e2e_time_range_proof.png', dpi=300, bbox_inches='tight')
        print("   ✓ 保存: e2e_time_range_proof.png")
        plt.close()
    
    def plot_summary(self):
        """绘制总体性能摘要图"""
        print("📊 生成总体性能摘要图...")
        
        vector_sizes = sorted(
            self.performance['batch_creation']['total_batch_creation'].keys(), 
            key=int
        )
        
        # 收集所有操作的总时间
        batch_times = [
            self.performance['batch_creation']['total_batch_creation'][n] * 1000 
            for n in vector_sizes
        ]
        dc_times = [
            self.performance['dc_query']['total_dc_query'][n] * 1000 
            for n in vector_sizes
        ]
        da_times = [
            self.performance['da_audit']['total_da_audit'][n] * 1000 
            for n in vector_sizes
        ]
        revoke_times = [
            self.performance['revocation']['total_revocation'][n] * 1000 
            for n in vector_sizes
        ]
        time_proof_times = [
            self.performance['time_range_proof']['total_time_range_proof'][n] * 1000 
            for n in vector_sizes
        ]
        
        x = np.arange(len(vector_sizes))
        width = 0.15
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        ax.bar(x - 2*width, batch_times, width, label='批次创建', alpha=0.8)
        ax.bar(x - width, dc_times, width, label='DC 查询', alpha=0.8)
        ax.bar(x, da_times, width, label='DA 审计', alpha=0.8)
        ax.bar(x + width, revoke_times, width, label='批次撤销', alpha=0.8)
        ax.bar(x + 2*width, time_proof_times, width, label='时间范围证明', alpha=0.8)
        
        ax.set_xlabel('向量大小 (n)', fontsize=12)
        ax.set_ylabel('时间 (ms)', fontsize=12)
        ax.set_title('VDS Scheme C+ 端到端性能总览', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([f'n={n}' for n in vector_sizes])
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('e2e_summary.png', dpi=300, bbox_inches='tight')
        print("   ✓ 保存: e2e_summary.png")
        plt.close()
    
    def generate_all_plots(self):
        """生成所有图表"""
        print("\n🎨 开始生成所有图表...")
        print("=" * 70)
        
        self.plot_batch_creation()
        self.plot_query_performance()
        self.plot_bandwidth()
        self.plot_revocation_performance()
        self.plot_time_range_proof()
        self.plot_summary()
        
        print("\n✅ 所有图表生成完成！")
        print("\n生成的图表:")
        print("  1. e2e_batch_creation.png - 批次创建性能")
        print("  2. e2e_query_performance.png - 查询与审计性能对比")
        print("  3. e2e_bandwidth.png - 带宽/通信开销")
        print("  4. e2e_revocation.png - 批次撤销性能")
        print("  5. e2e_time_range_proof.png - 时间范围证明性能")
        print("  6. e2e_summary.png - 总体性能摘要")


def main():
    """主函数"""
    print("🚀 VDS Scheme C+ 端到端性能分析")
    print("=" * 70)
    
    try:
        analysis = E2EPerformanceAnalysis('e2e_benchmark_results.json')
        analysis.generate_all_plots()
    except FileNotFoundError:
        print("❌ 错误: 找不到 e2e_benchmark_results.json")
        print("   请先运行: python e2e_performance_benchmark.py")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

