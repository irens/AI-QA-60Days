"""
Day 28: Embedding模型MTEB评测与选型（基础）
目标：模拟MTEB评测框架，建立多维度模型选型决策矩阵
测试架构师视角：选错模型=系统天花板被锁死，必须从源头把控质量
难度级别：基础
"""

import json
import random
import time
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
    """Embedding模型定义"""
    name: str
    dimension: int
    max_length: int
    multilingual: bool
    mteb_avg: float
    retrieval_score: float  # RAG最关心的指标
    sts_score: float
    speed_ms: float  # 编码延迟


# 主流Embedding模型数据（基于MTEB leaderboard）
MODELS_DB = [
    EmbeddingModel("text-embedding-3-small", 1536, 8192, True, 62.3, 56.5, 82.3, 25),
    EmbeddingModel("text-embedding-3-large", 3072, 8192, True, 64.6, 59.2, 85.1, 45),
    EmbeddingModel("bge-large-zh-v1.5", 1024, 512, False, 64.5, 61.8, 83.2, 30),
    EmbeddingModel("bge-m3", 1024, 8192, True, 65.1, 62.5, 84.5, 35),
    EmbeddingModel("m3e-base", 768, 512, False, 61.0, 57.2, 79.8, 20),
    EmbeddingModel("e5-large-v2", 1024, 512, True, 62.3, 58.1, 81.5, 28),
    EmbeddingModel("GTE-large", 1024, 512, True, 63.1, 59.5, 82.8, 25),
]


def mock_encode_stability(model: EmbeddingModel, text: str, n_times: int = 5) -> Tuple[float, List[float]]:
    """模拟编码稳定性测试：同一文本多次编码的相似度"""
    base_vector = hash(text) % 10000 / 10000  # 模拟基础向量值
    
    # 模拟不同模型的稳定性差异
    noise_factor = 0.001 if "large" in model.name else 0.003
    if "zh" in model.name:
        noise_factor *= 0.8  # 中文模型更稳定
    
    vectors = []
    for _ in range(n_times):
        noise = random.uniform(-noise_factor, noise_factor)
        vectors.append(base_vector + noise)
    
    # 计算两两相似度
    similarities = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            sim = 1 - abs(vectors[i] - vectors[j])
            similarities.append(sim)
    
    avg_similarity = sum(similarities) / len(similarities)
    return avg_similarity, vectors


def mock_long_text_handling(model: EmbeddingModel, text_length: int) -> Dict[str, Any]:
    """模拟长文本处理能力测试"""
    max_chars = model.max_length * 2  # 假设平均每个token 2字符
    
    if text_length <= max_chars:
        return {
            "truncated": False,
            "effective_ratio": 1.0,
            "quality_score": random.uniform(0.85, 0.95)
        }
    else:
        effective_ratio = max_chars / text_length
        # 截断后质量下降
        quality_penalty = (1 - effective_ratio) * 0.3
        return {
            "truncated": True,
            "effective_ratio": effective_ratio,
            "quality_score": random.uniform(0.6, 0.75) - quality_penalty
        }


def test_mteb_retrieval_ranking() -> TestResult:
    """测试1: MTEB检索任务排名验证"""
    print("\n" + "="*60)
    print("🧪 测试1: MTEB Retrieval任务排名验证")
    print("="*60)
    print("目的：验证各模型在RAG核心任务——检索任务上的表现")
    
    # 按检索分数排序
    sorted_models = sorted(MODELS_DB, key=lambda x: x.retrieval_score, reverse=True)
    
    print("\n📊 MTEB Retrieval Score排名（RAG最关注指标）：")
    print("-" * 50)
    for i, m in enumerate(sorted_models, 1):
        marker = "⭐" if i <= 3 else "  "
        print(f"{marker} {i}. {m.name:30} {m.retrieval_score:.1f}")
    
    top3_avg = sum(m.retrieval_score for m in sorted_models[:3]) / 3
    bottom3_avg = sum(m.retrieval_score for m in sorted_models[-3:]) / 3
    gap = top3_avg - bottom3_avg
    
    print(f"\n📈 关键发现：")
    print(f"   Top3平均: {top3_avg:.1f} | Bottom3平均: {bottom3_avg:.1f}")
    print(f"   差距: {gap:.1f}分 ({gap/bottom3_avg*100:.1f}%)")
    
    # 风险判定
    if gap > 5:
        risk = RiskLevel.L1
        passed = False
        score = max(0, 100 - gap * 5)
    elif gap > 3:
        risk = RiskLevel.L2
        passed = True
        score = 70
    else:
        risk = RiskLevel.L3
        passed = True
        score = 90
    
    print(f"\n🔴 风险等级: {risk.value}")
    print(f"   模型选择不当可能导致检索质量差异高达{gap:.1f}%")
    
    return TestResult(
        name="MTEB检索任务排名验证",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"top3_avg": top3_avg, "gap": gap}
    )


def test_dimension_efficiency() -> TestResult:
    """测试2: 向量维度效率分析"""
    print("\n" + "="*60)
    print("🧪 测试2: 向量维度效率分析")
    print("="*60)
    print("目的：评估高维向量的成本效益比")
    
    print("\n📊 维度-性能-成本矩阵：")
    print("-" * 70)
    print(f"{'模型':<30} {'维度':<8} {'检索分':<10} {'存储成本':<12} {'性价比':<10}")
    print("-" * 70)
    
    results = []
    for m in MODELS_DB:
        storage_cost = m.dimension / 100  # 归一化存储成本
        efficiency = m.retrieval_score / storage_cost
        results.append({
            "model": m.name,
            "dimension": m.dimension,
            "retrieval": m.retrieval_score,
            "cost": storage_cost,
            "efficiency": efficiency
        })
        print(f"{m.name:<30} {m.dimension:<8} {m.retrieval_score:<10.1f} {storage_cost:<12.1f}x {efficiency:<10.2f}")
    
    # 找出性价比最高和最低的
    best = max(results, key=lambda x: x["efficiency"])
    worst = min(results, key=lambda x: x["efficiency"])
    
    print(f"\n📈 关键发现：")
    print(f"   性价比最高: {best['model']} ({best['efficiency']:.2f})")
    print(f"   性价比最低: {worst['model']} ({worst['efficiency']:.2f})")
    print(f"   差距: {best['efficiency']/worst['efficiency']:.1f}x")
    
    # 3072维模型的性价比分析
    high_dim = [r for r in results if r["dimension"] >= 2048]
    if high_dim:
        avg_high_eff = sum(r["efficiency"] for r in high_dim) / len(high_dim)
        avg_low_eff = sum(r["efficiency"] for r in results if r["dimension"] < 1024) / len([r for r in results if r["dimension"] < 1024])
        
        if avg_high_eff < avg_low_eff * 0.8:
            risk = RiskLevel.L2
            passed = True
            score = 65
            print(f"\n⚠️ 警告: 高维模型(≥2048d)性价比低于低维模型20%以上")
        else:
            risk = RiskLevel.L3
            passed = True
            score = 85
    
    return TestResult(
        name="向量维度效率分析",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"best": best, "worst": worst}
    )


def test_encoding_stability() -> TestResult:
    """测试3: 编码稳定性测试"""
    print("\n" + "="*60)
    print("🧪 测试3: 编码稳定性测试")
    print("="*60)
    print("目的：验证同一文本多次编码的一致性（影响检索稳定性）")
    
    test_text = "人工智能正在改变我们的生活方式和工作模式"
    
    print(f"\n📊 测试文本: '{test_text[:20]}...'")
    print(f"{'模型':<30} {'稳定性得分':<15} {'状态':<10}")
    print("-" * 60)
    
    stability_results = []
    for m in MODELS_DB:
        stability, _ = mock_encode_stability(m, test_text, n_times=5)
        status = "✅ 稳定" if stability > 0.99 else "⚠️ 波动" if stability > 0.95 else "❌ 不稳定"
        print(f"{m.name:<30} {stability:<15.4f} {status:<10}")
        stability_results.append({"model": m.name, "stability": stability})
    
    avg_stability = sum(r["stability"] for r in stability_results) / len(stability_results)
    min_stability = min(r["stability"] for r in stability_results)
    
    print(f"\n📈 统计结果：")
    print(f"   平均稳定性: {avg_stability:.4f}")
    print(f"   最低稳定性: {min_stability:.4f}")
    
    if min_stability < 0.95:
        risk = RiskLevel.L1
        passed = False
        score = 50
        print(f"\n🔴 严重: 部分模型稳定性低于95%，会导致检索结果抖动")
    elif min_stability < 0.98:
        risk = RiskLevel.L2
        passed = True
        score = 75
        print(f"\n⚠️ 警告: 部分模型稳定性不足98%")
    else:
        risk = RiskLevel.L3
        passed = True
        score = 95
        print(f"\n✅ 所有模型稳定性良好")
    
    return TestResult(
        name="编码稳定性测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"avg_stability": avg_stability, "min_stability": min_stability}
    )


def test_length_boundary() -> TestResult:
    """测试4: 文本长度边界测试"""
    print("\n" + "="*60)
    print("🧪 测试4: 文本长度边界测试")
    print("="*60)
    print("目的：测试模型对超长文本的处理能力")
    
    # 模拟不同长度的文本
    test_cases = [
        ("短文本(100字符)", 100),
        ("中等文本(500字符)", 500),
        ("长文本(1500字符)", 1500),
        ("超长文本(3000字符)", 3000),
    ]
    
    print(f"\n{'模型':<25} {'最大长度':<12} ", end="")
    for name, _ in test_cases:
        print(f"{name:<15}", end="")
    print()
    print("-" * 90)
    
    issues = []
    for m in MODELS_DB:
        print(f"{m.name:<25} {m.max_length:<12} ", end="")
        for case_name, length in test_cases:
            result = mock_long_text_handling(m, length)
            if result["truncated"]:
                status = f"截断({result['effective_ratio']*100:.0f}%)"
                if result["effective_ratio"] < 0.5:
                    issues.append(f"{m.name}@{case_name}: 有效信息<50%")
            else:
                status = "完整"
            print(f"{status:<15}", end="")
        print()
    
    print(f"\n📈 关键发现：")
    long_context_models = [m for m in MODELS_DB if m.max_length >= 4096]
    short_context_models = [m for m in MODELS_DB if m.max_length <= 512]
    
    print(f"   长上下文模型(≥4096): {len(long_context_models)}个")
    print(f"   短上下文模型(≤512): {len(short_context_models)}个")
    
    if len(long_context_models) < 3:
        risk = RiskLevel.L2
        passed = True
        score = 70
        print(f"\n⚠️ 警告: 长上下文模型选择有限")
    else:
        risk = RiskLevel.L3
        passed = True
        score = 90
    
    if issues:
        print(f"\n🔴 截断风险: {len(issues)}个场景存在严重信息丢失")
        for issue in issues[:3]:
            print(f"   - {issue}")
    
    return TestResult(
        name="文本长度边界测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"long_context_count": len(long_context_models), "issues": len(issues)}
    )


def test_multilingual_support() -> TestResult:
    """测试5: 多语言支持验证"""
    print("\n" + "="*60)
    print("🧪 测试5: 多语言支持验证")
    print("="*60)
    print("目的：验证模型的多语言能力和中文场景适配性")
    
    print("\n📊 多语言支持矩阵：")
    print("-" * 60)
    print(f"{'模型':<30} {'多语言':<10} {'中文优化':<10} {'推荐场景':<20}")
    print("-" * 60)
    
    for m in MODELS_DB:
        multilingual = "✅ 是" if m.multilingual else "❌ 否"
        chinese_optimized = "✅ 是" if "zh" in m.name or "m3e" in m.name else "⚪ 一般"
        
        if "zh" in m.name:
            scenario = "中文为主RAG"
        elif m.multilingual:
            scenario = "多语言RAG"
        else:
            scenario = "英文RAG"
        
        print(f"{m.name:<30} {multilingual:<10} {chinese_optimized:<10} {scenario:<20}")
    
    # 中文场景分析
    chinese_models = [m for m in MODELS_DB if "zh" in m.name or "m3e" in m.name]
    multilingual_models = [m for m in MODELS_DB if m.multilingual]
    
    print(f"\n📈 关键发现：")
    print(f"   中文优化模型: {len(chinese_models)}个")
    print(f"   多语言模型: {len(multilingual_models)}个")
    
    # 检查中文场景风险
    chinese_best = max(chinese_models, key=lambda x: x.retrieval_score) if chinese_models else None
    multilingual_best = max(multilingual_models, key=lambda x: x.retrieval_score) if multilingual_models else None
    
    if chinese_best and multilingual_best:
        gap = chinese_best.retrieval_score - multilingual_best.retrieval_score
        if gap > 0:
            print(f"\n✅ 中文场景推荐: {chinese_best.name} (检索分领先{gap:.1f})")
            risk = RiskLevel.L3
            passed = True
            score = 90
        else:
            print(f"\n⚠️ 中文场景: 专用模型优势不明显")
            risk = RiskLevel.L2
            passed = True
            score = 80
    else:
        risk = RiskLevel.L2
        passed = True
        score = 75
    
    return TestResult(
        name="多语言支持验证",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"chinese_models": len(chinese_models), "multilingual_models": len(multilingual_models)}
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 AI QA System Test - Day 28 测试汇总报告")
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
        print("🔴 存在高风险项！模型选型存在重大隐患，建议立即整改:")
        for r in results:
            if r.risk_level == RiskLevel.L1:
                print(f"   - {r.name}: {r.score:.1f}分")
    elif risk_counts["L2-中风险"] > 2:
        print("🟡 中风险项较多，建议优化模型选型策略")
    else:
        print("🟢 模型选型风险可控，建议按计划推进")
    
    # 推荐模型
    print("\n🏆 推荐模型（按场景）:")
    print("   中文RAG首选: bge-large-zh-v1.5 / bge-m3")
    print("   多语言RAG首选: bge-m3 / text-embedding-3-large")
    print("   成本敏感场景: text-embedding-3-small / m3e-base")
    print("   长文本场景: bge-m3 / text-embedding-3-large")


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 28: Embedding模型MTEB评测与选型")
    print("="*70)
    print("测试架构师视角: 选错模型=系统天花板被锁死，必须从源头把控质量")
    
    results = [
        test_mteb_retrieval_ranking(),
        test_dimension_efficiency(),
        test_encoding_stability(),
        test_length_boundary(),
        test_multilingual_support(),
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
