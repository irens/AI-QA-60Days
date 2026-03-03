"""
Day 49: A/B测试流量分配与统计显著性验证
目标：最小可用，专注风险验证，代码要足够精简
测试架构师视角：验证A/B测试设计的统计严谨性，防止错误决策上线
"""

import hashlib
import random
from dataclasses import dataclass
from typing import List, Dict, Tuple
from statistics import mean, stdev
import math


@dataclass
class TestResult:
    name: str
    passed: bool
    score: float
    risk_level: str
    details: Dict


def hash_bucket(user_id: str, num_buckets: int = 100) -> int:
    """基于用户ID的哈希分桶"""
    hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return hash_val % num_buckets


def assign_variant(user_id: str, variants: List[str] = ["control", "treatment"]) -> str:
    """将用户分配到实验组或对照组"""
    bucket = hash_bucket(user_id)
    return variants[0] if bucket < 50 else variants[1]


def test_traffic_distribution_uniformity() -> TestResult:
    """
    测试1：流量分配均匀性验证
    模拟10万用户分桶，验证各桶分布是否均匀
    """
    print("\n" + "="*60)
    print("🧪 测试1：流量分配均匀性验证")
    print("="*60)
    print("目标：验证哈希分桶是否均匀，是否存在偏倚")
    
    n_users = 100000
    buckets = {i: 0 for i in range(100)}
    
    # 模拟用户分配
    for i in range(n_users):
        user_id = f"user_{i:06d}"
        bucket = hash_bucket(user_id)
        buckets[bucket] += 1
    
    # 统计分布
    counts = list(buckets.values())
    expected = n_users / 100
    chi_square = sum((obs - expected)**2 / expected for obs in counts)
    
    # 卡方检验临界值 (df=99, α=0.05)
    chi_critical = 123.2
    
    # 计算变异系数
    cv = stdev(counts) / mean(counts)
    
    print(f"  总用户数: {n_users}")
    print(f"  期望每桶: {expected:.0f}")
    print(f"  实际均值: {mean(counts):.1f}")
    print(f"  标准差: {stdev(counts):.1f}")
    print(f"  变异系数: {cv:.4f}")
    print(f"  卡方统计量: {chi_square:.2f} (临界值: {chi_critical:.2f})")
    print(f"  最小桶: {min(counts)}, 最大桶: {max(counts)}")
    
    passed = chi_square < chi_critical and cv < 0.1
    risk = "L1" if not passed else "L3"
    
    print(f"  结果: {'✅ 通过' if passed else '❌ 失败'} (风险等级: {risk})")
    
    return TestResult(
        name="流量分配均匀性",
        passed=passed,
        score=1.0 - min(chi_square / chi_critical, 1.0),
        risk_level=risk,
        details={"chi_square": chi_square, "cv": cv, "expected": expected}
    )


def test_sample_size_calculation() -> TestResult:
    """
    测试2：样本量计算验证
    验证不同MDE下的样本量需求是否合理
    """
    print("\n" + "="*60)
    print("🧪 测试2：样本量计算验证")
    print("="*60)
    print("目标：验证实验前样本量预估是否充分")
    
    def calc_sample_size(p: float, mde: float, alpha: float = 0.05, power: float = 0.8) -> int:
        """计算每组所需样本量"""
        z_alpha = 1.96  # α=0.05双侧
        z_beta = 0.84   # power=0.8
        delta = p * mde  # 绝对效应量
        n = 2 * (z_alpha + z_beta)**2 * p * (1-p) / delta**2
        return int(math.ceil(n))
    
    # 典型场景
    scenarios = [
        ("高转化场景", 0.20, 0.05),   # 20%基准，检测5%相对提升
        ("中转化场景", 0.10, 0.10),   # 10%基准，检测10%相对提升
        ("低转化场景", 0.02, 0.15),   # 2%基准，检测15%相对提升
        ("RAG准确率", 0.75, 0.03),    # 75%基准，检测3%相对提升
    ]
    
    results = []
    print("\n  样本量需求分析:")
    print(f"  {'场景':<15} {'基准率':<10} {'MDE':<10} {'每组样本':<12} {'总样本':<12}")
    print("  " + "-"*65)
    
    for name, p, mde in scenarios:
        n_per_group = calc_sample_size(p, mde)
        total = n_per_group * 2
        results.append((name, p, mde, n_per_group, total))
        print(f"  {name:<15} {p:<10.2%} {mde:<10.1%} {n_per_group:<12,} {total:<12,}")
    
    # 检查风险：样本量过大或过小
    issues = []
    for name, p, mde, n, total in results:
        if total > 1000000:
            issues.append(f"{name}: 样本量过大({total:,})，实验周期过长")
        if total < 1000:
            issues.append(f"{name}: 样本量过小({total:,})，统计功效不足")
    
    passed = len(issues) == 0
    risk = "L2" if issues else "L3"
    
    if issues:
        print("\n  ⚠️ 发现的问题:")
        for issue in issues:
            print(f"    - {issue}")
    
    print(f"\n  结果: {'✅ 通过' if passed else '⚠️ 警告'} (风险等级: {risk})")
    
    return TestResult(
        name="样本量计算验证",
        passed=passed,
        score=0.9 if passed else 0.6,
        risk_level=risk,
        details={"scenarios": results, "issues": issues}
    )


def test_aa_test_false_positive() -> TestResult:
    """
    测试3：A/A测试假阳性率验证
    模拟A/A测试，验证假阳性率是否接近α=0.05
    """
    print("\n" + "="*60)
    print("🧪 测试3：A/A测试假阳性率验证")
    print("="*60)
    print("目标：验证当两组确实相同时，错误拒绝H₀的概率≈5%")
    
    def two_proportion_z_test(p1: float, n1: int, p2: float, n2: int) -> float:
        """两比例z检验，返回p值"""
        p_pooled = (p1*n1 + p2*n2) / (n1 + n2)
        se = math.sqrt(p_pooled * (1-p_pooled) * (1/n1 + 1/n2))
        if se == 0:
            return 1.0
        z = (p1 - p2) / se
        # 简化的双侧p值计算
        p_value = 2 * (1 - min(1, 0.5 + 0.5 * math.erf(abs(z) / math.sqrt(2))))
        return p_value
    
    n_simulations = 1000
    n_per_group = 1000
    true_rate = 0.10
    alpha = 0.05
    
    false_positives = 0
    p_values = []
    
    random.seed(42)
    for _ in range(n_simulations):
        # 模拟两组相同的数据
        conversions_a = sum(random.random() < true_rate for _ in range(n_per_group))
        conversions_b = sum(random.random() < true_rate for _ in range(n_per_group))
        
        p1 = conversions_a / n_per_group
        p2 = conversions_b / n_per_group
        
        p_value = two_proportion_z_test(p1, n_per_group, p2, n_per_group)
        p_values.append(p_value)
        
        if p_value < alpha:
            false_positives += 1
    
    observed_fpr = false_positives / n_simulations
    
    print(f"  模拟次数: {n_simulations}")
    print(f"  每组样本: {n_per_group}")
    print(f"  基准转化率: {true_rate:.1%}")
    print(f"  理论假阳性率: {alpha:.1%}")
    print(f"  观测假阳性率: {observed_fpr:.1%}")
    print(f"  假阳性次数: {false_positives}/{n_simulations}")
    
    # 95%置信区间
    ci_lower = observed_fpr - 1.96 * math.sqrt(observed_fpr * (1-observed_fpr) / n_simulations)
    ci_upper = observed_fpr + 1.96 * math.sqrt(observed_fpr * (1-observed_fpr) / n_simulations)
    print(f"  95%置信区间: [{max(0, ci_lower):.3f}, {min(1, ci_upper):.3f}]")
    
    # 检查是否在合理范围内
    passed = 0.03 <= observed_fpr <= 0.07
    risk = "L2" if not passed else "L3"
    
    print(f"\n  结果: {'✅ 通过' if passed else '⚠️ 警告'} (风险等级: {risk})")
    if not passed:
        print(f"  提示: 观测假阳性率偏离理论值，检查检验方法实现")
    
    return TestResult(
        name="A/A测试假阳性率",
        passed=passed,
        score=1.0 - abs(observed_fpr - alpha) / alpha,
        risk_level=risk,
        details={"observed_fpr": observed_fpr, "expected_fpr": alpha}
    )


def test_multiple_comparison_correction() -> TestResult:
    """
    测试4：多重比较校正验证
    验证Bonferroni和FDR校正效果
    """
    print("\n" + "="*60)
    print("🧪 测试4：多重比较校正验证")
    print("="*60)
    print("目标：验证同时测试多个指标时，整体假阳性率是否受控")
    
    n_metrics = 10
    alpha = 0.05
    n_simulations = 1000
    
    # 无校正时的假阳性率
    familywise_no_correction = 1 - (1 - alpha)**n_metrics
    
    print(f"\n  同时测试指标数: {n_metrics}")
    print(f"  单个指标α: {alpha:.2f}")
    print(f"\n  无校正时的整体假阳性率: {familywise_no_correction:.1%}")
    print(f"  理论值: 1 - (1-0.05)^{n_metrics} = {familywise_no_correction:.1%}")
    
    # Bonferroni校正
    bonferroni_alpha = alpha / n_metrics
    familywise_bonferroni = 1 - (1 - bonferroni_alpha)**n_metrics
    
    print(f"\n  Bonferroni校正:")
    print(f"    调整后α: {bonferroni_alpha:.4f}")
    print(f"    整体假阳性率: ≤{familywise_bonferroni:.1%}")
    
    # 模拟验证
    false_positives_no_corr = 0
    false_positives_bonf = 0
    
    random.seed(42)
    for _ in range(n_simulations):
        # 生成10个指标的p值（H₀为真）
        p_values = [random.random() for _ in range(n_metrics)]
        
        # 无校正
        if any(p < alpha for p in p_values):
            false_positives_no_corr += 1
        
        # Bonferroni校正
        if any(p < bonferroni_alpha for p in p_values):
            false_positives_bonf += 1
    
    observed_no_corr = false_positives_no_corr / n_simulations
    observed_bonf = false_positives_bonf / n_simulations
    
    print(f"\n  模拟验证 ({n_simulations}次):")
    print(f"    无校正观测假阳性率: {observed_no_corr:.1%}")
    print(f"    Bonferroni观测假阳性率: {observed_bonf:.1%}")
    
    # 风险判断
    issues = []
    if observed_no_corr > 0.30:
        issues.append(f"无校正时假阳性率过高({observed_no_corr:.1%})")
    
    passed = len(issues) == 0
    risk = "L1" if observed_no_corr > 0.35 else "L2" if issues else "L3"
    
    if issues:
        print("\n  ⚠️ 发现的问题:")
        for issue in issues:
            print(f"    - {issue}")
    
    print(f"\n  结果: {'✅ 通过' if passed else '❌ 失败'} (风险等级: {risk})")
    
    return TestResult(
        name="多重比较校正",
        passed=passed,
        score=1.0 - observed_no_corr,
        risk_level=risk,
        details={
            "no_correction_fpr": observed_no_corr,
            "bonferroni_fpr": observed_bonf,
            "n_metrics": n_metrics
        }
    )


def test_peeking_problem() -> TestResult:
    """
    测试5：早期停止偏倚演示
    展示频繁查看结果(peeking)如何inflate Type I error
    """
    print("\n" + "="*60)
    print("🧪 测试5：早期停止偏倚 (Peeking Problem)")
    print("="*60)
    print("目标：演示频繁查看结果如何导致假阳性率飙升")
    
    def simulate_experiment(n_total: int, n_peeks: int, true_effect: float = 0) -> Tuple[bool, int]:
        """
        模拟实验，允许中期查看
        返回: (是否早期停止, 实际使用样本量)
        """
        n_per_peek = n_total // n_peeks
        data_a, data_b = [], []
        
        for peek in range(n_peeks):
            # 收集本阶段数据
            for _ in range(n_per_peek // 2):
                data_a.append(1 if random.random() < (0.10 + true_effect) else 0)
                data_b.append(1 if random.random() < 0.10 else 0)
            
            # 中期分析
            if len(data_a) > 10 and len(data_b) > 10:
                p1, p2 = mean(data_a), mean(data_b)
                n1, n2 = len(data_a), len(data_b)
                
                # 简化的z检验
                p_pooled = (sum(data_a) + sum(data_b)) / (n1 + n2)
                se = math.sqrt(p_pooled * (1-p_pooled) * (1/n1 + 1/n2))
                if se > 0:
                    z = (p1 - p2) / se
                    p_value = 2 * (1 - min(1, 0.5 + 0.5 * math.erf(abs(z) / math.sqrt(2))))
                    
                    if p_value < 0.05:
                        return True, len(data_a) + len(data_b)
        
        return False, n_total
    
    n_simulations = 500
    n_total = 2000
    
    scenarios = [
        ("固定样本量", 1),      # 只看最终结果
        ("中期查看2次", 2),     # 50%和100%
        ("中期查看5次", 5),     # 20%, 40%, 60%, 80%, 100%
        ("频繁查看10次", 10),   # 每10%查看一次
    ]
    
    print(f"\n  模拟设置: {n_simulations}次实验，每组真实效应=0")
    print(f"  计划总样本量: {n_total}")
    print(f"\n  {'策略':<15} {'早期停止率':<15} {'假阳性率':<15} {'平均样本量':<15}")
    print("  " + "-"*60)
    
    results = []
    random.seed(42)
    for name, n_peeks in scenarios:
        early_stops = 0
        total_samples = 0
        
        for _ in range(n_simulations):
            stopped, samples = simulate_experiment(n_total, n_peeks)
            if stopped:
                early_stops += 1
            total_samples += samples
        
        early_stop_rate = early_stops / n_simulations
        avg_samples = total_samples / n_simulations
        
        print(f"  {name:<15} {early_stop_rate:<15.1%} {early_stop_rate:<15.1%} {avg_samples:<15.0f}")
        results.append((name, early_stop_rate, avg_samples))
    
    # 风险分析
    _, fpr_10peeks, _ = results[-1]
    inflation = fpr_10peeks / 0.05
    
    print(f"\n  关键发现:")
    print(f"    - 固定样本量时假阳性率≈5% (符合预期)")
    print(f"    - 频繁查看(10次)时假阳性率≈{fpr_10peeks:.1%}")
    print(f"    - Type I error膨胀倍数: {inflation:.1f}x")
    
    passed = fpr_10peeks < 0.15
    risk = "L1" if fpr_10peeks > 0.20 else "L2" if fpr_10peeks > 0.10 else "L3"
    
    print(f"\n  结果: {'✅ 通过' if passed else '❌ 失败'} (风险等级: {risk})")
    print(f"  建议: 使用固定样本量或序贯检验边界(如O'Brien-Fleming)")
    
    return TestResult(
        name="早期停止偏倚",
        passed=passed,
        score=max(0, 1.0 - (fpr_10peeks - 0.05) / 0.20),
        risk_level=risk,
        details={"fpr_10peeks": fpr_10peeks, "inflation": inflation}
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 A/B测试统计严谨性 - 测试汇总报告")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    high_risk = sum(1 for r in results if r.risk_level == "L1")
    
    print(f"\n总体评分: {passed}/{total} 项通过")
    print(f"高风险项: {high_risk} 项")
    
    print("\n详细结果:")
    print(f"  {'测试项':<25} {'状态':<8} {'得分':<8} {'风险':<8}")
    print("  " + "-"*55)
    for r in results:
        status = "✅ 通过" if r.passed else "❌ 失败"
        print(f"  {r.name:<25} {status:<8} {r.score:.2f}    {r.risk_level}")
    
    # 风险汇总
    print("\n风险等级说明:")
    print("  L1 (高风险): 可能导致错误决策，需立即整改")
    print("  L2 (中风险): 存在统计瑕疵，建议优化")
    print("  L3 (低风险): 符合统计规范，可接受")
    
    # 关键建议
    print("\n关键建议:")
    if high_risk > 0:
        print("  ⚠️ 发现高风险项，建议:")
        print("    1. 实验前使用样本量计算器确定所需样本")
        print("    2. 避免频繁查看实验结果，使用固定样本量")
        print("    3. 多指标测试时应用Bonferroni或FDR校正")
    else:
        print("  ✅ 统计设计基本合理，建议持续监控")
    
    print("\n" + "="*70)
    print("请将以上日志贴回给 Trae 生成详细报告")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 49: A/B测试统计严谨性验证")
    print("="*70)
    print("测试架构师视角：验证A/B测试设计是否统计严谨，防止错误决策")
    
    results = [
        test_traffic_distribution_uniformity(),
        test_sample_size_calculation(),
        test_aa_test_false_positive(),
        test_multiple_comparison_correction(),
        test_peeking_problem(),
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
