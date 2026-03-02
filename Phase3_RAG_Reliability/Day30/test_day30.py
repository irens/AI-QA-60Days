"""
Day 30: 向量相似度校准与阈值优化（实战）
目标：通过相似度分布分析、P-R曲线优化、模型间校准，找到最优阈值策略
测试架构师视角：相似度阈值是RAG系统的隐形杀手，必须科学校准
难度级别：实战
"""

import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from enum import Enum


class RiskLevel(Enum):
    L1 = "L1-高风险"
    L2 = "L2-中风险"
    L3 = "L3-低风险"


@dataclass
class TestResult:
    name: str
    passed: bool
    score: float
    risk_level: RiskLevel
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddingModel:
    name: str
    similarity_bias: float  # 相似度偏移（某些模型整体偏高/偏低）
    similarity_scale: float  # 相似度缩放因子


# 模型定义（模拟不同模型的相似度特性）
MODELS = [
    EmbeddingModel("OpenAI-3-small", 0.05, 0.85),   # 分布较散，高分段稀疏
    EmbeddingModel("BGE-large-zh", 0.10, 0.90),     # 分布集中
    EmbeddingModel("E5-large", 0.15, 0.95),         # 余弦相似度偏高
    EmbeddingModel("GTE-large", 0.00, 1.00),        # 基准模型
]


def generate_similarity_data(model: EmbeddingModel, n_positive: int = 100, n_negative: int = 200) -> Tuple[List[float], List[float]]:
    """生成正例和负例的相似度数据"""
    # 正例：相似度较高，分布在0.6-0.95
    positive = []
    for _ in range(n_positive):
        base = random.uniform(0.60, 0.95)
        # 应用模型特性
        adjusted = (base + model.similarity_bias) * model.similarity_scale
        adjusted = max(0.3, min(0.99, adjusted))
        positive.append(adjusted)
    
    # 负例：相似度较低，分布在0.1-0.7
    negative = []
    for _ in range(n_negative):
        base = random.uniform(0.10, 0.70)
        adjusted = (base + model.similarity_bias) * model.similarity_scale
        adjusted = max(0.1, min(0.85, adjusted))
        negative.append(adjusted)
    
    return positive, negative


def calculate_metrics_at_threshold(positive: List[float], negative: List[float], threshold: float) -> Dict[str, float]:
    """计算给定阈值下的各项指标"""
    tp = sum(1 for p in positive if p >= threshold)
    fn = sum(1 for p in positive if p < threshold)
    fp = sum(1 for n in negative if n >= threshold)
    tn = sum(1 for n in negative if n < threshold)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn
    }


def test_similarity_distribution() -> TestResult:
    """测试1: 相似度分布分析"""
    print("\n" + "="*60)
    print("🧪 测试1: 相似度分布分析")
    print("="*60)
    print("目的：分析正例/负例的相似度分布特征")
    
    target_model = MODELS[3]  # GTE作为基准
    positive, negative = generate_similarity_data(target_model)
    
    print(f"\n📊 测试数据: {len(positive)}正例, {len(negative)}负例")
    print(f"\n{'统计项':<20} {'正例':<15} {'负例':<15} {'差距':<10}")
    print("-" * 65)
    
    pos_mean = sum(positive) / len(positive)
    neg_mean = sum(negative) / len(negative)
    pos_min, pos_max = min(positive), max(positive)
    neg_min, neg_max = min(negative), max(negative)
    
    # 计算标准差
    pos_std = math.sqrt(sum((x - pos_mean) ** 2 for x in positive) / len(positive))
    neg_std = math.sqrt(sum((x - neg_mean) ** 2 for x in negative) / len(negative))
    
    print(f"{'平均值':<20} {pos_mean:<15.3f} {neg_mean:<15.3f} {pos_mean-neg_mean:<10.3f}")
    print(f"{'最小值':<20} {pos_min:<15.3f} {neg_min:<15.3f} {pos_min-neg_min:<10.3f}")
    print(f"{'最大值':<20} {pos_max:<15.3f} {neg_max:<15.3f} {pos_max-neg_max:<10.3f}")
    print(f"{'标准差':<20} {pos_std:<15.3f} {neg_std:<15.3f} {pos_std-neg_std:<10.3f}")
    
    # 分析重叠区域
    overlap_start = max(neg_min, pos_min)
    overlap_end = min(neg_max, pos_max)
    overlap_ratio = (overlap_end - overlap_start) / (max(pos_max, neg_max) - min(pos_min, neg_min))
    
    print(f"\n📈 关键发现：")
    print(f"   正例平均相似度: {pos_mean:.3f}")
    print(f"   负例平均相似度: {neg_mean:.3f}")
    print(f"   分布重叠区域: {overlap_start:.3f} - {overlap_end:.3f}")
    print(f"   重叠比例: {overlap_ratio:.1%}")
    
    if overlap_ratio > 0.5:
        print(f"\n⚠️ 警告: 正负例分布重叠严重({overlap_ratio:.1%})，阈值选择困难")
        risk = RiskLevel.L2
        passed = True
        score = 70
    elif overlap_ratio > 0.3:
        print(f"\n🟡 注意: 正负例存在一定重叠({overlap_ratio:.1%})")
        risk = RiskLevel.L2
        passed = True
        score = 80
    else:
        print(f"\n✅ 正负例分布分离良好({overlap_ratio:.1%})")
        risk = RiskLevel.L3
        passed = True
        score = 95
    
    return TestResult(
        name="相似度分布分析",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"pos_mean": pos_mean, "neg_mean": neg_mean, "overlap_ratio": overlap_ratio}
    )


def test_pr_curve_optimization() -> TestResult:
    """测试2: P-R曲线与F1优化"""
    print("\n" + "="*60)
    print("🧪 测试2: P-R曲线与F1优化")
    print("="*60)
    print("目的：找到使F1分数最大化的最优阈值")
    
    target_model = MODELS[3]
    positive, negative = generate_similarity_data(target_model)
    
    # 测试不同阈值
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
    
    print(f"\n{'阈值':<10} {'精准率':<12} {'召回率':<12} {'F1分数':<12} {'状态':<10}")
    print("-" * 60)
    
    results = []
    for threshold in thresholds:
        metrics = calculate_metrics_at_threshold(positive, negative, threshold)
        
        if metrics["f1"] > 0.75:
            status = "✅ 优秀"
        elif metrics["f1"] > 0.65:
            status = "⚠️ 一般"
        else:
            status = "❌ 较差"
        
        print(f"{threshold:<10.2f} {metrics['precision']:<12.3f} {metrics['recall']:<12.3f} {metrics['f1']:<12.3f} {status:<10}")
        results.append({"threshold": threshold, **metrics})
    
    # 找到最优阈值
    best_result = max(results, key=lambda x: x["f1"])
    
    print(f"\n📈 关键发现：")
    print(f"   最优阈值: {best_result['threshold']:.2f}")
    print(f"   最优F1: {best_result['f1']:.3f}")
    print(f"   对应精准率: {best_result['precision']:.3f}")
    print(f"   对应召回率: {best_result['recall']:.3f}")
    
    # 检查高阈值风险
    high_threshold_result = [r for r in results if r["threshold"] == 0.85][0]
    if high_threshold_result["recall"] < 0.50:
        print(f"\n🔴 警告: 阈值0.85时召回率仅{high_threshold_result['recall']:.1%}，可能漏掉大量相关文档")
    
    # 检查低阈值风险
    low_threshold_result = [r for r in results if r["threshold"] == 0.55][0]
    if low_threshold_result["precision"] < 0.60:
        print(f"\n⚠️ 注意: 阈值0.55时精准率仅{low_threshold_result['precision']:.1%}，噪声文档较多")
    
    if best_result["f1"] < 0.70:
        risk = RiskLevel.L2
        passed = True
        score = 65
        print(f"\n⚠️ 最优F1低于0.70，建议优化Embedding模型或增加训练数据")
    elif best_result["f1"] < 0.80:
        risk = RiskLevel.L2
        passed = True
        score = 80
        print(f"\n🟡 最优F1在0.70-0.80之间，性能尚可但仍有提升空间")
    else:
        risk = RiskLevel.L3
        passed = True
        score = 95
        print(f"\n✅ 最优F1超过0.80，阈值设置合理")
    
    return TestResult(
        name="P-R曲线与F1优化",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"best_threshold": best_result["threshold"], "best_f1": best_result["f1"]}
    )


def test_model_calibration() -> TestResult:
    """测试3: 模型间相似度校准"""
    print("\n" + "="*60)
    print("🧪 测试3: 模型间相似度校准")
    print("="*60)
    print("目的：建立不同模型间的相似度映射关系")
    
    # 使用基准模型(GTE)生成数据
    base_model = MODELS[3]
    base_positive, base_negative = generate_similarity_data(base_model, n_positive=50, n_negative=100)
    
    print(f"\n📊 模型间相似度对比（同一样本在不同模型下的得分）：")
    print(f"\n{'模型':<25} {'平均相似度':<15} {'校准偏移':<15} {'校准缩放':<10}")
    print("-" * 70)
    
    calibration_params = []
    for model in MODELS:
        # 模拟该模型对同一样本的相似度
        model_positive, model_negative = generate_similarity_data(model, n_positive=50, n_negative=100)
        model_mean = (sum(model_positive) + sum(model_negative)) / (len(model_positive) + len(model_negative))
        base_mean = (sum(base_positive) + sum(base_negative)) / (len(base_positive) + len(base_negative))
        
        # 计算校准参数
        offset = base_mean - model_mean
        scale = base_mean / model_mean if model_mean > 0 else 1.0
        
        print(f"{model.name:<25} {model_mean:<15.3f} {offset:<15.3f} {scale:<10.3f}")
        calibration_params.append({
            "model": model.name,
            "offset": offset,
            "scale": scale,
            "original_mean": model_mean
        })
    
    # 检查校准必要性
    max_diff = max(abs(p["offset"]) for p in calibration_params)
    
    print(f"\n📈 关键发现：")
    print(f"   最大平均差异: {max_diff:.3f}")
    
    if max_diff > 0.15:
        print(f"\n🔴 严重: 模型间相似度差异超过0.15，直接复用阈值将导致灾难")
        print(f"   必须进行相似度校准后才能切换模型")
        risk = RiskLevel.L1
        passed = False
        score = 45
    elif max_diff > 0.08:
        print(f"\n⚠️ 警告: 模型间相似度差异{max_diff:.3f}，建议进行校准")
        risk = RiskLevel.L2
        passed = True
        score = 70
    else:
        print(f"\n✅ 模型间相似度差异较小({max_diff:.3f})，可直接迁移")
        risk = RiskLevel.L3
        passed = True
        score = 90
    
    # 输出校准公式
    print(f"\n📐 校准公式示例（以GTE为基准）：")
    for p in calibration_params:
        if p["model"] != "GTE-large":
            print(f"   {p['model']}: sim_calibrated = (sim_original + {p['offset']:.3f}) × {p['scale']:.3f}")
    
    return TestResult(
        name="模型间相似度校准",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"max_diff": max_diff, "calibration_needed": max_diff > 0.08}
    )


def test_dynamic_threshold() -> TestResult:
    """测试4: 动态阈值效果"""
    print("\n" + "="*60)
    print("🧪 测试4: 动态阈值效果")
    print("="*60)
    print("目的：对比固定阈值vs动态阈值的性能差异")
    
    # 模拟不同复杂度的查询
    query_types = [
        {"name": "简单查询", "complexity": 0.3, "n_samples": 30},
        {"name": "中等查询", "complexity": 0.5, "n_samples": 40},
        {"name": "复杂查询", "complexity": 0.7, "n_samples": 30},
    ]
    
    base_threshold = 0.70
    
    print(f"\n📊 固定阈值 vs 动态阈值对比：")
    print(f"   固定阈值: {base_threshold}")
    print(f"   动态阈值公式: threshold = {base_threshold} - (complexity - 0.5) × 0.15")
    print()
    
    print(f"{'查询类型':<15} {'复杂度':<10} {'固定阈值':<12} {'动态阈值':<12} {'F1提升':<10}")
    print("-" * 65)
    
    dynamic_results = []
    for qt in query_types:
        # 动态阈值计算
        dynamic_threshold = base_threshold - (qt["complexity"] - 0.5) * 0.15
        dynamic_threshold = max(0.50, min(0.90, dynamic_threshold))
        
        # 模拟该查询类型的数据（复杂度越高，正负例越难区分）
        noise = qt["complexity"] * 0.1
        positive = [random.uniform(0.65 - noise, 0.95) for _ in range(qt["n_samples"])]
        negative = [random.uniform(0.15, 0.70 + noise) for _ in range(qt["n_samples"] * 2)]
        
        # 固定阈值性能
        fixed_metrics = calculate_metrics_at_threshold(positive, negative, base_threshold)
        
        # 动态阈值性能
        dynamic_metrics = calculate_metrics_at_threshold(positive, negative, dynamic_threshold)
        
        f1_improvement = (dynamic_metrics["f1"] - fixed_metrics["f1"]) / fixed_metrics["f1"] if fixed_metrics["f1"] > 0 else 0
        
        print(f"{qt['name']:<15} {qt['complexity']:<10.1f} {base_threshold:<12.2f} {dynamic_threshold:<12.2f} {f1_improvement:<9.1%}")
        
        dynamic_results.append({
            "query_type": qt["name"],
            "fixed_f1": fixed_metrics["f1"],
            "dynamic_f1": dynamic_metrics["f1"],
            "improvement": f1_improvement
        })
    
    avg_improvement = sum(r["improvement"] for r in dynamic_results) / len(dynamic_results)
    
    print(f"\n📈 关键发现：")
    print(f"   平均F1提升: {avg_improvement:.1%}")
    
    if avg_improvement > 0.10:
        print(f"\n✅ 动态阈值显著提升性能，建议实施")
        risk = RiskLevel.L3
        passed = True
        score = 90
    elif avg_improvement > 0.05:
        print(f"\n🟡 动态阈值有一定提升，可视复杂度决定是否实施")
        risk = RiskLevel.L2
        passed = True
        score = 80
    else:
        print(f"\n⚠️ 动态阈值提升不明显，固定阈值可能已足够")
        risk = RiskLevel.L2
        passed = True
        score = 70
    
    return TestResult(
        name="动态阈值效果",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"avg_improvement": avg_improvement}
    )


def test_threshold_sensitivity() -> TestResult:
    """测试5: 阈值敏感性分析"""
    print("\n" + "="*60)
    print("🧪 测试5: 阈值敏感性分析")
    print("="*60)
    print("目的：分析阈值微小变化对系统性能的影响")
    
    target_model = MODELS[3]
    positive, negative = generate_similarity_data(target_model)
    
    # 基准阈值
    base_threshold = 0.70
    base_metrics = calculate_metrics_at_threshold(positive, negative, base_threshold)
    
    # 测试阈值偏移
    offsets = [-0.10, -0.05, -0.02, 0.00, 0.02, 0.05, 0.10]
    
    print(f"\n📊 阈值敏感性分析（基准阈值: {base_threshold}）：")
    print(f"\n{'阈值偏移':<12} {'实际阈值':<12} {'F1变化':<12} {'召回变化':<12} {'风险':<10}")
    print("-" * 75)
    
    sensitivity_results = []
    for offset in offsets:
        threshold = base_threshold + offset
        metrics = calculate_metrics_at_threshold(positive, negative, threshold)
        
        f1_change = (metrics["f1"] - base_metrics["f1"]) / base_metrics["f1"] if base_metrics["f1"] > 0 else 0
        recall_change = (metrics["recall"] - base_metrics["recall"]) / base_metrics["recall"] if base_metrics["recall"] > 0 else 0
        
        # 风险评估
        if abs(f1_change) > 0.15:
            risk = "🔴 高"
        elif abs(f1_change) > 0.08:
            risk = "🟡 中"
        else:
            risk = "🟢 低"
        
        print(f"{offset:+.2f}        {threshold:<12.2f} {f1_change:<+11.1%} {recall_change:<+11.1%} {risk:<10}")
        
        sensitivity_results.append({
            "offset": offset,
            "f1_change": f1_change,
            "recall_change": recall_change
        })
    
    # 计算敏感性指标
    max_f1_change = max(abs(r["f1_change"]) for r in sensitivity_results)
    max_recall_change = max(abs(r["recall_change"]) for r in sensitivity_results)
    
    print(f"\n📈 关键发现：")
    print(f"   最大F1变化: {max_f1_change:.1%}")
    print(f"   最大召回变化: {max_recall_change:.1%}")
    
    # 检查0.05偏移的影响
    offset_005 = [r for r in sensitivity_results if abs(r["offset"] - 0.05) < 0.001][0]
    if abs(offset_005["f1_change"]) > 0.10:
        print(f"\n🔴 严重: 阈值偏移0.05导致F1变化{offset_005['f1_change']:.1%}，系统对阈值非常敏感")
        risk = RiskLevel.L1
        passed = False
        score = 50
    elif abs(offset_005["f1_change"]) > 0.05:
        print(f"\n⚠️ 警告: 阈值偏移0.05导致F1变化{offset_005['f1_change']:.1%}，需谨慎调整阈值")
        risk = RiskLevel.L2
        passed = True
        score = 70
    else:
        print(f"\n✅ 阈值稳定性良好，0.05偏移仅导致F1变化{offset_005['f1_change']:.1%}")
        risk = RiskLevel.L3
        passed = True
        score = 90
    
    # 给出建议
    print(f"\n💡 阈值设置建议：")
    if max_f1_change > 0.20:
        print(f"   - 系统对阈值高度敏感，建议实施动态阈值或阈值区间")
        print(f"   - 生产环境阈值变更需经过A/B测试验证")
    else:
        print(f"   - 阈值稳定性良好，可按业务需求灵活调整")
        print(f"   - 建议设置阈值监控告警")
    
    return TestResult(
        name="阈值敏感性分析",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"max_f1_change": max_f1_change, "max_recall_change": max_recall_change}
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 AI QA System Test - Day 30 测试汇总报告")
    print("="*70)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / total_tests
    
    risk_counts = {"L1-高风险": 0, "L2-中风险": 0, "L3-低风险": 0}
    for r in results:
        risk_counts[r.risk_level.value] += 1
    
    print(f"\n📈 测试统计:")
    print(f"   总测试数: {total_tests}")
    print(f"   通过: {passed_tests} | 失败: {total_tests - passed_tests}")
    print(f"   平均得分: {avg_score:.1f}/100")
    
    print(f"\n🎯 风险分布:")
    for risk, count in risk_counts.items():
        icon = "🔴" if "L1" in risk else "🟡" if "L2" in risk else "🟢"
        print(f"   {icon} {risk}: {count}项")
    
    print(f"\n📋 详细结果:")
    print("-" * 70)
    print(f"{'测试项':<35} {'状态':<8} {'得分':<8} {'风险':<12}")
    print("-" * 70)
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{r.name:<35} {status:<8} {r.score:<8.1f} {r.risk_level.value:<12}")
    
    print("\n" + "="*70)
    print("💡 核心结论:")
    print("="*70)
    
    if risk_counts["L1-高风险"] > 0:
        print("🔴 存在高风险项！相似度阈值设置存在重大隐患:")
        for r in results:
            if r.risk_level == RiskLevel.L1:
                print(f"   - {r.name}: {r.score:.1f}分")
        print("\n建议: 立即进行阈值优化和模型校准")
    elif risk_counts["L2-中风险"] > 2:
        print("🟡 中风险项较多，建议制定阈值优化计划:")
        print("   1. 建立相似度分布监控")
        print("   2. 实施动态阈值策略")
        print("   3. 建立模型切换校准流程")
    else:
        print("🟢 相似度阈值风险可控，建议按计划推进")
        print("   持续监控阈值敏感性和模型一致性")
    
    print("\n📚 阈值优化最佳实践:")
    print("   1. 基于F1最大化原则确定初始阈值")
    print("   2. 根据业务目标（精准优先/召回优先）微调")
    print("   3. 切换Embedding模型时必须重新校准阈值")
    print("   4. 复杂查询场景考虑动态阈值策略")
    print("   5. 建立阈值漂移监控和告警机制")
    
    print("\n🔧 推荐阈值范围（按模型）:")
    print("   OpenAI text-embedding-3: 0.70-0.85")
    print("   BGE-large-zh: 0.65-0.80")
    print("   E5-large: 0.75-0.90")
    print("   GTE-large: 0.60-0.75")


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 30: 向量相似度校准与阈值优化（实战）")
    print("="*70)
    print("测试架构师视角: 相似度阈值是RAG系统的隐形杀手，必须科学校准")
    
    results = [
        test_similarity_distribution(),
        test_pr_curve_optimization(),
        test_model_calibration(),
        test_dynamic_threshold(),
        test_threshold_sensitivity(),
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
