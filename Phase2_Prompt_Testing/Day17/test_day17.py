"""
Day 17: Few-shot示例选择与效果稳定性测试
目标：最小可用，专注风险验证，杜绝多余业务逻辑
测试架构师视角：验证Few-shot示例选择的系统性方法与效果稳定性
"""

import json
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Any
from difflib import SequenceMatcher
import math


@dataclass
class FewShotExample:
    """Few-shot示例结构"""
    input: str
    output: str
    complexity: int  # 1-10复杂度评分
    category: str    # 示例类别（用于多样性分析）
    quality_score: float  # 0-1质量评分


@dataclass
class PerturbationTest:
    """扰动测试用例"""
    name: str
    examples: List[FewShotExample]
    perturbation_type: str  # replace/delete/reorder
    target_input: str
    expected_patterns: List[str]
    risk_level: str  # L1/L2/L3


@dataclass
class TestResult:
    """测试结果"""
    name: str
    perturbation_type: str
    passed: bool
    stability_score: float  # 扰动稳定性分数
    details: Dict[str, Any]
    risk_level: str


# ==================== Few-shot示例库（情感分析任务） ====================

# 高质量示例集 - 覆盖不同复杂度、类别、情感
HIGH_QUALITY_EXAMPLES = [
    # 简单正面
    FewShotExample(
        input="这家餐厅的服务太棒了！",
        output='{"sentiment": "positive", "confidence": 0.95, "aspects": ["服务"]}',
        complexity=2,
        category="餐饮",
        quality_score=0.95
    ),
    # 简单负面
    FewShotExample(
        input="产品质量很差，完全不值这个价。",
        output='{"sentiment": "negative", "confidence": 0.92, "aspects": ["质量", "价格"]}',
        complexity=3,
        category="电商",
        quality_score=0.90
    ),
    # 中性
    FewShotExample(
        input="快递3天送到，包装完整。",
        output='{"sentiment": "neutral", "confidence": 0.88, "aspects": ["物流", "包装"]}',
        complexity=2,
        category="物流",
        quality_score=0.88
    ),
    # 复杂正面（多维度）
    FewShotExample(
        input="虽然价格稍贵，但是设计感和用料都很出色，用了一年没有任何问题，强烈推荐！",
        output='{"sentiment": "positive", "confidence": 0.91, "aspects": ["价格", "设计", "质量", "推荐度"]}',
        complexity=7,
        category="数码",
        quality_score=0.93
    ),
    # 复杂负面（隐含讽刺）
    FewShotExample(
        input="哇，这个'智能'助手真是太'聪明'了，问什么都不会。",
        output='{"sentiment": "negative", "confidence": 0.89, "aspects": ["智能程度"], "sarcasm": true}',
        complexity=8,
        category="软件",
        quality_score=0.91
    ),
]

# 低质量示例集（用于替换测试）
LOW_QUALITY_EXAMPLES = [
    FewShotExample(
        input="挺好的",
        output='{"sentiment": "positive"}',
        complexity=1,
        category="通用",
        quality_score=0.40
    ),
    FewShotExample(
        input="不好",
        output='{"sentiment": "negative"}',
        complexity=1,
        category="通用",
        quality_score=0.35
    ),
    FewShotExample(
        input="今天天气不错",
        output='{"sentiment": "positive", "topic": "天气"}',
        complexity=1,
        category="无关",
        quality_score=0.20  # 与目标任务无关
    ),
]

# 有偏见示例集（用于偏见检测测试）
BIASED_EXAMPLES = [
    FewShotExample(
        input="男性程序员写的代码",
        output='{"sentiment": "positive", "confidence": 0.90}',
        complexity=3,
        category="职场",
        quality_score=0.50  # 隐含性别偏见
    ),
    FewShotExample(
        input="女性程序员写的代码",
        output='{"sentiment": "neutral", "confidence": 0.70}',
        complexity=3,
        category="职场",
        quality_score=0.50  # 隐含性别偏见
    ),
]


# ==================== 模拟LLM响应（测试替身） ====================

def mock_llm_sentiment_analysis(examples: List[FewShotExample], query: str) -> Dict[str, Any]:
    """
    模拟LLM情感分析响应
    基于示例质量和相关性模拟输出质量
    """
    if not examples:
        # 0-shot：基础能力
        base_confidence = 0.65
        quality_factor = 0.5
    else:
        # 计算示例集质量指标
        avg_quality = sum(e.quality_score for e in examples) / len(examples)
        
        # 多样性：类别覆盖率
        categories = set(e.category for e in examples)
        diversity_factor = len(categories) / max(len(examples), 3)
        
        # 复杂度分布
        complexities = [e.complexity for e in examples]
        complexity_range = max(complexities) - min(complexities) if len(complexities) > 1 else 0
        
        # 质量因子 = 平均质量 * 多样性 * 复杂度覆盖
        quality_factor = avg_quality * (0.5 + 0.5 * diversity_factor)
        base_confidence = 0.65 + 0.30 * quality_factor
    
    # 模拟输出结构完整性
    has_aspects = quality_factor > 0.6
    has_confidence = quality_factor > 0.5
    
    # 根据查询内容判断情感
    positive_words = ["棒", "好", "喜欢", "推荐", "优秀", "满意", "惊喜"]
    negative_words = ["差", "坏", "失望", "垃圾", "后悔", "问题", "故障"]
    
    pos_count = sum(1 for w in positive_words if w in query)
    neg_count = sum(1 for w in negative_words if w in query)
    
    if pos_count > neg_count:
        sentiment = "positive"
        confidence = base_confidence + 0.05
    elif neg_count > pos_count:
        sentiment = "negative"
        confidence = base_confidence + 0.05
    else:
        sentiment = "neutral"
        confidence = base_confidence - 0.05
    
    # 结构完整性随示例质量下降
    result = {"sentiment": sentiment}
    if has_confidence:
        result["confidence"] = round(min(confidence, 0.98), 2)
    if has_aspects:
        result["aspects"] = ["整体体验"]
    
    return result


def calculate_output_quality(output: Dict[str, Any]) -> float:
    """计算输出质量分数"""
    score = 0.0
    
    # 必须有sentiment字段
    if "sentiment" in output:
        score += 0.4
    
    # 有confidence字段加分
    if "confidence" in output:
        score += 0.3
        score += output["confidence"] * 0.1
    
    # 有aspects字段加分
    if "aspects" in output:
        score += 0.2
    
    return min(score, 1.0)


def calculate_similarity(text1: str, text2: str) -> float:
    """计算文本相似度（简化版嵌入空间距离）"""
    return SequenceMatcher(None, text1, text2).ratio()


def calculate_diversity_coverage(examples: List[FewShotExample]) -> float:
    """计算多样性覆盖率"""
    if len(examples) <= 1:
        return 1.0
    
    categories = set(e.category for e in examples)
    return len(categories) / len(examples)


# ==================== 测试执行函数 ====================

def test_example_replacement() -> TestResult:
    """测试1：示例替换测试 - 将高质量示例替换为低质量示例"""
    print("\n" + "="*60)
    print("🧪 测试1：示例替换测试 (Replace Perturbation)")
    print("="*60)
    
    target = "这款手机拍照效果很好，但是电池续航一般。"
    
    # 基准：全部高质量示例
    baseline_output = mock_llm_sentiment_analysis(HIGH_QUALITY_EXAMPLES, target)
    baseline_quality = calculate_output_quality(baseline_output)
    
    print(f"\n📊 基准测试（{len(HIGH_QUALITY_EXAMPLES)}个高质量示例）:")
    print(f"   输出: {baseline_output}")
    print(f"   质量分: {baseline_quality:.2f}")
    
    # 替换测试：逐步替换为低质量示例
    results = []
    for i in range(1, 4):
        perturbed = HIGH_QUALITY_EXAMPLES.copy()
        # 替换前i个示例为低质量示例
        for j in range(min(i, len(LOW_QUALITY_EXAMPLES))):
            if j < len(perturbed):
                perturbed[j] = LOW_QUALITY_EXAMPLES[j]
        
        output = mock_llm_sentiment_analysis(perturbed, target)
        quality = calculate_output_quality(output)
        
        # 计算稳定性分数
        stability = 1 - abs(baseline_quality - quality) / max(baseline_quality, 0.01)
        results.append({
            "replaced": i,
            "quality": quality,
            "stability": stability,
            "output": output
        })
        
        print(f"\n   替换{i}个示例后:")
        print(f"   输出: {output}")
        print(f"   质量分: {quality:.2f}, 稳定性: {stability:.2f}")
    
    # 判断风险
    avg_stability = sum(r["stability"] for r in results) / len(results)
    passed = avg_stability > 0.7
    
    return TestResult(
        name="示例替换测试",
        perturbation_type="replace",
        passed=passed,
        stability_score=avg_stability,
        details={
            "baseline_quality": baseline_quality,
            "perturbation_results": results,
            "risk_threshold": 0.7
        },
        risk_level="L1" if avg_stability < 0.6 else "L2" if avg_stability < 0.8 else "L3"
    )


def test_example_deletion() -> TestResult:
    """测试2：示例删除测试 - 逐步删除示例"""
    print("\n" + "="*60)
    print("🧪 测试2：示例删除测试 (Deletion Perturbation)")
    print("="*60)
    
    target = "物流很快，包装也很用心，但是商品有轻微瑕疵。"
    
    # 基准：全部示例
    baseline_output = mock_llm_sentiment_analysis(HIGH_QUALITY_EXAMPLES, target)
    baseline_quality = calculate_output_quality(baseline_output)
    
    print(f"\n📊 基准测试（{len(HIGH_QUALITY_EXAMPLES)}个示例）:")
    print(f"   质量分: {baseline_quality:.2f}")
    
    # 逐步删除示例
    results = []
    for count in [4, 3, 2, 1, 0]:
        reduced = HIGH_QUALITY_EXAMPLES[:count]
        output = mock_llm_sentiment_analysis(reduced, target)
        quality = calculate_output_quality(output)
        
        # 计算边际收益
        if count > 0:
            prev_quality = results[-1]["quality"] if results else baseline_quality
            marginal_gain = quality - prev_quality if count < len(HIGH_QUALITY_EXAMPLES) else 0
        else:
            marginal_gain = 0
        
        results.append({
            "example_count": count,
            "quality": quality,
            "marginal_gain": marginal_gain,
            "diversity": calculate_diversity_coverage(reduced)
        })
        
        print(f"\n   {count}-shot: 质量分={quality:.2f}, 多样性={results[-1]['diversity']:.2f}")
    
    # 计算数量效率比
    zero_shot_quality = results[-1]["quality"]
    five_shot_quality = results[0]["quality"]
    efficiency_ratio = (five_shot_quality - zero_shot_quality) / 5 if len(results) >= 5 else 0
    
    print(f"\n📈 数量效率比 (5-shot vs 0-shot): {efficiency_ratio:.3f}/示例")
    
    # 识别临界点（边际收益<0.05）
    critical_point = None
    for i, r in enumerate(results):
        if i > 0 and abs(r["marginal_gain"]) < 0.05:
            critical_point = r["example_count"]
            break
    
    if critical_point:
        print(f"⚠️  边际收益临界点: {critical_point}-shot")
    
    passed = efficiency_ratio > 0.03  # 每个示例至少带来3%提升
    
    return TestResult(
        name="示例删除测试",
        perturbation_type="delete",
        passed=passed,
        stability_score=efficiency_ratio * 20,  # 归一化
        details={
            "efficiency_ratio": efficiency_ratio,
            "critical_point": critical_point,
            "zero_shot_quality": zero_shot_quality,
            "deletion_curve": results
        },
        risk_level="L2"
    )


def test_example_reordering() -> TestResult:
    """测试3：示例重排测试 - 改变示例顺序"""
    print("\n" + "="*60)
    print("🧪 测试3：示例重排测试 (Reorder Perturbation)")
    print("="*60)
    
    target = "性价比很高，会再次购买。"
    
    # 原始顺序
    original_output = mock_llm_sentiment_analysis(HIGH_QUALITY_EXAMPLES, target)
    original_str = json.dumps(original_output, sort_keys=True)
    
    print(f"\n📊 原始顺序输出: {original_output}")
    
    # 多次随机重排
    consistency_scores = []
    for i in range(5):
        shuffled = HIGH_QUALITY_EXAMPLES.copy()
        random.shuffle(shuffled)
        output = mock_llm_sentiment_analysis(shuffled, target)
        output_str = json.dumps(output, sort_keys=True)
        
        # 计算一致性
        consistency = calculate_similarity(original_str, output_str)
        consistency_scores.append(consistency)
        
        print(f"   重排{i+1}: 一致性={consistency:.2f}, 输出={output}")
    
    avg_consistency = sum(consistency_scores) / len(consistency_scores)
    
    print(f"\n📈 平均顺序一致性: {avg_consistency:.2f}")
    
    # 测试难度梯度排序
    print("\n📊 难度梯度排序测试:")
    sorted_by_complexity = sorted(HIGH_QUALITY_EXAMPLES, key=lambda x: x.complexity)
    sorted_output = mock_llm_sentiment_analysis(sorted_by_complexity, target)
    print(f"   简单→复杂排序输出: {sorted_output}")
    
    sorted_reverse = sorted(HIGH_QUALITY_EXAMPLES, key=lambda x: x.complexity, reverse=True)
    reverse_output = mock_llm_sentiment_analysis(sorted_reverse, target)
    print(f"   复杂→简单排序输出: {reverse_output}")
    
    gradient_consistency = calculate_similarity(
        json.dumps(sorted_output, sort_keys=True),
        json.dumps(reverse_output, sort_keys=True)
    )
    print(f"   梯度排序一致性: {gradient_consistency:.2f}")
    
    passed = avg_consistency > 0.8
    
    return TestResult(
        name="示例重排测试",
        perturbation_type="reorder",
        passed=passed,
        stability_score=avg_consistency,
        details={
            "consistency_scores": consistency_scores,
            "gradient_consistency": gradient_consistency,
            "threshold": 0.8
        },
        risk_level="L2" if avg_consistency < 0.9 else "L3"
    )


def test_similarity_threshold() -> TestResult:
    """测试4：相似度阈值测试"""
    print("\n" + "="*60)
    print("🧪 测试4：相似度阈值测试 (Similarity Threshold)")
    print("="*60)
    
    # 测试查询与示例的相似度
    test_queries = [
        "这家餐厅的食物非常美味，服务也很周到。",  # 与餐饮示例高相似
        "代码写得非常优雅，逻辑清晰。",  # 与软件示例中等相似
        "今天的天气真不错，适合出游。",  # 与目标任务低相似
    ]
    
    results = []
    for query in test_queries:
        # 计算与示例库的最大相似度
        max_similarity = max(
            calculate_similarity(query, e.input) for e in HIGH_QUALITY_EXAMPLES
        )
        
        output = mock_llm_sentiment_analysis(HIGH_QUALITY_EXAMPLES, query)
        quality = calculate_output_quality(output)
        
        results.append({
            "query": query[:20] + "...",
            "max_similarity": max_similarity,
            "output_quality": quality
        })
        
        risk = "🔴 高风险" if max_similarity < 0.6 else "🟡 中风险" if max_similarity < 0.75 else "🟢 低风险"
        print(f"\n   查询: {query[:25]}...")
        print(f"   最大相似度: {max_similarity:.2f} {risk}")
        print(f"   输出质量: {quality:.2f}")
    
    # 检查相似度与质量的相关性
    similarities = [r["max_similarity"] for r in results]
    qualities = [r["output_quality"] for r in results]
    
    # 简单相关性计算
    correlation = sum(
        (s - 0.5) * (q - 0.7) for s, q in zip(similarities, qualities)
    ) / max(len(results) * 0.1, 0.01)
    
    print(f"\n📈 相似度-质量相关性: {correlation:.2f}")
    
    # 高风险示例数量
    high_risk_count = sum(1 for r in results if r["max_similarity"] < 0.6)
    
    passed = high_risk_count == 0
    
    return TestResult(
        name="相似度阈值测试",
        perturbation_type="similarity",
        passed=passed,
        stability_score=1 - high_risk_count / len(results),
        details={
            "query_results": results,
            "correlation": correlation,
            "high_risk_count": high_risk_count
        },
        risk_level="L1" if high_risk_count > 0 else "L3"
    )


def test_bias_detection() -> TestResult:
    """测试5：偏见检测测试"""
    print("\n" + "="*60)
    print("🧪 测试5：偏见检测测试 (Bias Detection)")
    print("="*60)
    
    # 使用有偏见的示例集
    biased_examples = HIGH_QUALITY_EXAMPLES[:3] + BIASED_EXAMPLES
    
    test_queries = [
        "男性工程师的技术方案",
        "女性工程师的技术方案",
        "工程师的技术方案",
    ]
    
    results = []
    for query in test_queries:
        output = mock_llm_sentiment_analysis(biased_examples, query)
        results.append({
            "query": query,
            "output": output
        })
        print(f"\n   查询: {query}")
        print(f"   输出: {output}")
    
    # 检查敏感属性分布
    # 简化：检查示例集中敏感属性的平衡性
    sensitive_balance = len(BIASED_EXAMPLES) / len(biased_examples)
    
    print(f"\n📊 敏感属性示例占比: {sensitive_balance:.1%}")
    
    if sensitive_balance > 0.3:
        print("⚠️  警告：敏感属性示例占比过高，存在偏见放大风险")
    
    passed = sensitive_balance <= 0.3
    
    return TestResult(
        name="偏见检测测试",
        perturbation_type="bias",
        passed=passed,
        stability_score=1 - sensitive_balance,
        details={
            "query_results": results,
            "sensitive_ratio": sensitive_balance,
            "warning": sensitive_balance > 0.3
        },
        risk_level="L1" if sensitive_balance > 0.3 else "L3"
    )


# ==================== 主测试入口 ====================

def run_all_tests():
    """运行所有Few-shot稳定性测试"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 17: Few-shot示例选择与效果稳定性")
    print("="*70)
    print("\n测试架构师视角：验证Few-shot示例选择的系统性方法与效果稳定性")
    print("测试场景：情感分析任务的Few-shot示例选择")
    
    # 执行所有测试
    results = [
        test_example_replacement(),
        test_example_deletion(),
        test_example_reordering(),
        test_similarity_threshold(),
        test_bias_detection(),
    ]
    
    # 汇总报告
    print("\n" + "="*70)
    print("📋 测试汇总报告")
    print("="*70)
    
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    
    print(f"\n✅ 通过: {passed_count}/{total_count}")
    print(f"❌ 失败: {total_count - passed_count}/{total_count}")
    
    print("\n📊 各测试项结果:")
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        risk_icon = "🔴" if r.risk_level == "L1" else "🟡" if r.risk_level == "L2" else "🟢"
        print(f"   {status} [{risk_icon} {r.risk_level}] {r.name}: 稳定性={r.stability_score:.2f}")
    
    # 风险汇总
    l1_count = sum(1 for r in results if r.risk_level == "L1")
    l2_count = sum(1 for r in results if r.risk_level == "L2")
    l3_count = sum(1 for r in results if r.risk_level == "L3")
    
    print(f"\n⚠️ 风险分布:")
    print(f"   🔴 L1 (高风险): {l1_count}项")
    print(f"   🟡 L2 (中风险): {l2_count}项")
    print(f"   🟢 L3 (低风险): {l3_count}项")
    
    # 关键发现
    print("\n🔍 关键发现:")
    
    # 找出效率比结果
    deletion_result = next((r for r in results if r.perturbation_type == "delete"), None)
    if deletion_result and "efficiency_ratio" in deletion_result.details:
        ratio = deletion_result.details["efficiency_ratio"]
        print(f"   • 数量效率比: {ratio:.3f}/示例 {'✅ 达标' if ratio > 0.03 else '❌ 偏低'}")
    
    # 临界点
    if deletion_result and deletion_result.details.get("critical_point"):
        print(f"   • 边际收益临界点: {deletion_result.details['critical_point']}-shot")
    
    # 顺序一致性
    reorder_result = next((r for r in results if r.perturbation_type == "reorder"), None)
    if reorder_result:
        print(f"   • 顺序一致性: {reorder_result.stability_score:.2f} {'✅ 稳定' if reorder_result.stability_score > 0.8 else '⚠️ 敏感'}")
    
    print("\n" + "="*70)
    print("✅ 测试执行完毕，请将上方日志发给 Trae 生成报告。")
    print("="*70)
    
    return results


if __name__ == "__main__":
    run_all_tests()
