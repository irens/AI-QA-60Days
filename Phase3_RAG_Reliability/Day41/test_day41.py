"""
Day 41: 上下文信息过载检测
目标：最小可用，突出风险验证，代码要足够精简
测试架构师视角：检测LLM在面对过多无关信息时的处理能力下降
难度级别：进阶
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from enum import Enum
import random


class RiskLevel(Enum):
    L1 = "L1-阻断性"
    L2 = "L2-高优先级"
    L3 = "L3-一般风险"


@dataclass
class TestResult:
    name: str
    passed: bool
    score: float  # 0-100
    risk_level: RiskLevel
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextDoc:
    """模拟检索文档"""
    doc_id: str
    content: str
    relevance_score: float  # 0-1，相关性得分
    is_relevant: bool  # 是否与问题相关


@dataclass
class Question:
    """测试问题"""
    text: str
    expected_answer_keywords: List[str]  # 期望答案包含的关键词


def mock_llm_with_noise(context_docs: List[ContextDoc], question: Question, 
                        noise_sensitivity: float = 0.3) -> Dict[str, Any]:
    """
    模拟LLM在噪声环境下的生成
    
    模拟真实场景：
    - 噪声比例越高，答案质量越低
    - 无关文档会"污染"答案，引入错误信息
    - 长上下文导致处理效率下降
    """
    relevant_docs = [d for d in context_docs if d.is_relevant]
    irrelevant_docs = [d for d in context_docs if not d.is_relevant]
    
    # 计算信噪比
    snr = len(relevant_docs) / max(1, len(irrelevant_docs))
    
    # 噪声影响：噪声比例越高，答案质量越低
    noise_ratio = len(irrelevant_docs) / max(1, len(context_docs))
    quality_degradation = noise_ratio * noise_sensitivity
    
    # 基础准确率（无噪声时）
    base_accuracy = 0.95
    
    # 实际准确率
    actual_accuracy = max(0.3, base_accuracy - quality_degradation)
    
    # 模拟答案质量
    covered_keywords = []
    noise_intrusion = False
    
    for keyword in question.expected_answer_keywords:
        # 每个关键词被覆盖的概率 = 实际准确率
        if random.random() < actual_accuracy:
            covered_keywords.append(keyword)
    
    # 噪声侵入：无关文档可能污染答案
    if noise_ratio > 0.4 and random.random() < noise_ratio:
        noise_intrusion = True
    
    # 生成模拟答案
    if covered_keywords:
        answer = f"根据信息，{'，'.join(covered_keywords[:2])}"
        if noise_intrusion:
            answer += "（但可能包含不准确信息）"
    else:
        answer = "无法从提供的文档中找到完整答案。"
    
    return {
        "answer": answer,
        "covered_keywords": covered_keywords,
        "keyword_coverage": len(covered_keywords) / len(question.expected_answer_keywords) if question.expected_answer_keywords else 0,
        "noise_ratio": noise_ratio,
        "snr": snr,
        "quality_degradation": quality_degradation,
        "noise_intrusion": noise_intrusion,
        "actual_accuracy": actual_accuracy
    }


def mock_rerank(docs: List[ContextDoc], top_k: int = 3) -> List[ContextDoc]:
    """模拟重排序：按相关性得分排序，返回Top-K"""
    sorted_docs = sorted(docs, key=lambda x: x.relevance_score, reverse=True)
    return sorted_docs[:top_k]


def test_noise_ratio_pressure() -> TestResult:
    """
    测试1: 噪声比例压力测试
    验证：随着无关文档比例增加，答案质量如何变化
    """
    print("\n" + "="*60)
    print("🧪 测试1: 噪声比例压力测试")
    print("="*60)
    print("测试目的：验证噪声比例对答案质量的影响")
    
    # 固定相关文档数量，逐步增加无关文档
    base_relevant_docs = [
        ContextDoc(f"rel_{i}", f"相关文档{i}的内容", 0.9, True) 
        for i in range(3)
    ]
    
    question = Question("请总结关键信息", ["信息1", "信息2", "信息3"])
    
    noise_ratios = [0.0, 0.3, 0.5, 0.7, 0.9]
    results = []
    
    print("\n📊 不同噪声比例下的表现:")
    print("-" * 50)
    print(f"{'噪声比例':<12} {'信噪比':<10} {'关键词覆盖率':<15} {'质量衰减':<10}")
    print("-" * 50)
    
    for noise_ratio in noise_ratios:
        # 计算需要的无关文档数量
        if noise_ratio == 0:
            noise_docs = []
        else:
            num_irrelevant = int(len(base_relevant_docs) * noise_ratio / (1 - noise_ratio))
            noise_docs = [
                ContextDoc(f"noise_{i}", f"无关文档{i}的内容", 0.2, False)
                for i in range(num_irrelevant)
            ]
        
        docs = base_relevant_docs + noise_docs
        result = mock_llm_with_noise(docs, question)
        results.append((noise_ratio, result))
        
        print(f"{noise_ratio:<12.1%} {result['snr']:<10.2f} "
              f"{result['keyword_coverage']:<15.1%} {result['quality_degradation']:<10.1%}")
    
    # 分析拐点
    coverage_drop = results[0][1]['keyword_coverage'] - results[-1][1]['keyword_coverage']
    
    print("\n📉 质量衰减分析:")
    print(f"   无噪声覆盖率: {results[0][1]['keyword_coverage']:.1%}")
    print(f"   高噪声覆盖率: {results[-1][1]['keyword_coverage']:.1%}")
    print(f"   覆盖率下降: {coverage_drop:.1%}")
    
    # 评估：高噪声(70%)下覆盖率不应低于50%
    high_noise_coverage = results[3][1]['keyword_coverage']  # 70%噪声
    passed = high_noise_coverage >= 0.5
    score = (1 - coverage_drop) * 100
    
    risk = RiskLevel.L2 if coverage_drop > 0.4 else RiskLevel.L3
    
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="噪声比例压力测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={
            "覆盖率下降": coverage_drop,
            "高噪声覆盖率": high_noise_coverage,
            "噪声比例测试点": noise_ratios
        }
    )


def test_context_length_breakpoint() -> TestResult:
    """
    测试2: 上下文长度拐点测试
    验证：随着上下文长度增加，找出性能拐点
    """
    print("\n" + "="*60)
    print("🧪 测试2: 上下文长度拐点测试")
    print("="*60)
    print("测试目的：找出上下文长度的性能拐点")
    
    question = Question("产品的价格是多少？", ["价格", "100元"])
    
    # 不同上下文长度配置（文档数量）
    length_configs = [3, 5, 8, 12, 20]
    
    # 保持信噪比恒定（1:1），只改变总量
    results = []
    
    print("\n📊 不同上下文长度下的表现:")
    print("-" * 60)
    print(f"{'文档总数':<12} {'相关文档':<12} {'无关文档':<12} {'覆盖率':<12}")
    print("-" * 60)
    
    for total_docs in length_configs:
        num_relevant = total_docs // 2
        num_irrelevant = total_docs - num_relevant
        
        docs = (
            [ContextDoc(f"rel_{i}", f"相关文档{i}", 0.85, True) for i in range(num_relevant)] +
            [ContextDoc(f"noise_{i}", f"无关文档{i}", 0.25, False) for i in range(num_irrelevant)]
        )
        
        result = mock_llm_with_noise(docs, question, noise_sensitivity=0.25)
        results.append((total_docs, result))
        
        print(f"{total_docs:<12} {num_relevant:<12} {num_irrelevant:<12} "
              f"{result['keyword_coverage']:<12.1%}")
    
    # 找出拐点（覆盖率下降超过20%的点）
    baseline_coverage = results[0][1]['keyword_coverage']
    breakpoint_found = None
    
    for length, result in results:
        coverage_drop = baseline_coverage - result['keyword_coverage']
        if coverage_drop > 0.2 and breakpoint_found is None:
            breakpoint_found = length
            break
    
    print(f"\n📉 性能拐点分析:")
    if breakpoint_found:
        print(f"   发现性能拐点: {breakpoint_found}个文档")
        print(f"   超过此长度后，答案质量显著下降")
    else:
        print(f"   未在测试范围内发现明显拐点")
    
    # 评估：最大测试长度下覆盖率不应低于60%
    final_coverage = results[-1][1]['keyword_coverage']
    passed = final_coverage >= 0.6
    score = final_coverage * 100
    
    risk = RiskLevel.L2 if final_coverage < 0.7 else RiskLevel.L3
    
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="上下文长度拐点测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={
            "性能拐点": breakpoint_found,
            "最终覆盖率": final_coverage,
            "测试长度点": length_configs
        }
    )


def test_information_conflict() -> TestResult:
    """
    测试3: 信息冲突处理测试
    验证：当上下文中存在矛盾信息时，模型的处理能力
    """
    print("\n" + "="*60)
    print("🧪 测试3: 信息冲突处理测试")
    print("="*60)
    print("测试目的：验证LLM处理矛盾信息的能力")
    
    # 场景1：无冲突（基准）
    docs_no_conflict = [
        ContextDoc("doc1", "产品价格：100元", 0.9, True),
        ContextDoc("doc2", "产品特性：高品质", 0.85, True),
        ContextDoc("doc3", "售后服务：7天无理由", 0.8, True),
    ]
    
    # 场景2：有冲突（相同主题，不同信息）
    docs_with_conflict = [
        ContextDoc("doc1", "产品价格：100元", 0.9, True),
        ContextDoc("doc2_conflict", "产品价格：150元", 0.7, True),  # 冲突！
        ContextDoc("doc3", "产品特性：高品质", 0.85, True),
    ]
    
    # 场景3：多冲突点
    docs_multi_conflict = [
        ContextDoc("doc1", "产品价格：100元", 0.9, True),
        ContextDoc("doc2", "产品价格：150元", 0.7, True),
        ContextDoc("doc3", "质保期：1年", 0.8, True),
        ContextDoc("doc4", "质保期：2年", 0.75, True),
    ]
    
    question = Question("请告诉我产品价格和质保期", ["价格", "质保"])
    
    # 测试三种场景
    scenarios = [
        ("无冲突", docs_no_conflict),
        ("单冲突", docs_with_conflict),
        ("多冲突", docs_multi_conflict)
    ]
    
    results = {}
    print("\n📊 不同冲突场景下的表现:")
    print("-" * 50)
    
    for name, docs in scenarios:
        result = mock_llm_with_noise(docs, question, noise_sensitivity=0.2)
        results[name] = result
        
        status = "✅ 正常" if result['keyword_coverage'] >= 0.7 else "⚠️ 下降"
        print(f"   {name}: 覆盖率 {result['keyword_coverage']:.1%} {status}")
    
    # 分析冲突影响
    baseline = results["无冲突"]['keyword_coverage']
    single_conflict = results["单冲突"]['keyword_coverage']
    multi_conflict = results["多冲突"]['keyword_coverage']
    
    single_drop = baseline - single_conflict
    multi_drop = baseline - multi_conflict
    
    print(f"\n📉 冲突影响分析:")
    print(f"   单冲突导致覆盖率下降: {single_drop:.1%}")
    print(f"   多冲突导致覆盖率下降: {multi_drop:.1%}")
    
    # 评估：冲突场景下覆盖率不应低于60%
    min_coverage = min(single_conflict, multi_conflict)
    passed = min_coverage >= 0.6
    score = min_coverage * 100
    
    risk = RiskLevel.L2 if multi_drop > 0.3 else RiskLevel.L3
    
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="信息冲突处理测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={
            "无冲突覆盖率": baseline,
            "单冲突覆盖率": single_conflict,
            "多冲突覆盖率": multi_conflict,
            "最大下降": max(single_drop, multi_drop)
        }
    )


def test_reranking_effectiveness() -> TestResult:
    """
    测试4: 重排序效果验证
    验证：重排序策略对过滤噪声的效果
    """
    print("\n" + "="*60)
    print("🧪 测试4: 重排序效果验证")
    print("="*60)
    print("测试目的：量化重排序对提升答案质量的效果")
    
    # 创建混合文档（包含相关和无关）
    mixed_docs = [
        ContextDoc("rel_1", "产品价格：100元，性价比高", 0.92, True),
        ContextDoc("noise_1", "公司历史：成立于2010年", 0.3, False),
        ContextDoc("rel_2", "产品特性：高性能处理器", 0.88, True),
        ContextDoc("noise_2", "办公地址：北京市海淀区", 0.25, False),
        ContextDoc("rel_3", "售后服务：7天无理由退货", 0.85, True),
        ContextDoc("noise_3", "员工数量：500人", 0.28, False),
        ContextDoc("noise_4", "融资情况：B轮融资", 0.22, False),
        ContextDoc("rel_4", "配送方式：全国包邮", 0.8, True),
    ]
    
    question = Question("请告诉我产品价格、特性和售后政策", 
                       ["价格", "特性", "售后"])
    
    # 场景A：无重排序，使用所有文档
    print("\n📊 场景A: 无重排序 (使用所有8个文档)")
    result_no_rerank = mock_llm_with_noise(mixed_docs, question)
    print(f"   噪声比例: {result_no_rerank['noise_ratio']:.1%}")
    print(f"   关键词覆盖率: {result_no_rerank['keyword_coverage']:.1%}")
    print(f"   噪声侵入: {'是' if result_no_rerank['noise_intrusion'] else '否'}")
    
    # 场景B：有重排序，只使用Top-3
    print("\n📊 场景B: 有重排序 (只使用Top-3相关文档)")
    reranked_docs = mock_rerank(mixed_docs, top_k=3)
    result_with_rerank = mock_llm_with_noise(reranked_docs, question)
    print(f"   噪声比例: {result_with_rerank['noise_ratio']:.1%}")
    print(f"   关键词覆盖率: {result_with_rerank['keyword_coverage']:.1%}")
    print(f"   噪声侵入: {'是' if result_with_rerank['noise_intrusion'] else '否'}")
    
    # 计算改进
    coverage_improvement = result_with_rerank['keyword_coverage'] - result_no_rerank['keyword_coverage']
    noise_reduction = result_no_rerank['noise_ratio'] - result_with_rerank['noise_ratio']
    
    print(f"\n📈 重排序效果:")
    print(f"   覆盖率提升: {coverage_improvement:+.1%}")
    print(f"   噪声比例降低: {noise_reduction:+.1%}")
    
    # 评估：重排序后覆盖率应提升至少10%
    passed = coverage_improvement >= 0.1
    score = min(100, (result_with_rerank['keyword_coverage'] * 100) + (coverage_improvement * 50))
    
    risk = RiskLevel.L2 if coverage_improvement < 0.1 else RiskLevel.L3
    
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="重排序效果验证",
        passed=passed,
        score=score,
        risk_level=risk,
        details={
            "无重排序覆盖率": result_no_rerank['keyword_coverage'],
            "有重排序覆盖率": result_with_rerank['keyword_coverage'],
            "覆盖率提升": coverage_improvement,
            "噪声比例降低": noise_reduction
        }
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 Day 41 测试汇总报告 - 上下文信息过载检测")
    print("="*70)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / total_tests
    
    l1_count = sum(1 for r in results if r.risk_level == RiskLevel.L1)
    l2_count = sum(1 for r in results if r.risk_level == RiskLevel.L2)
    l3_count = sum(1 for r in results if r.risk_level == RiskLevel.L3)
    
    print(f"\n📈 整体统计:")
    print(f"   测试项总数: {total_tests}")
    print(f"   通过: {passed_tests} | 未通过: {total_tests - passed_tests}")
    print(f"   平均得分: {avg_score:.1f}/100")
    
    print(f"\n🚨 风险分布:")
    print(f"   {RiskLevel.L1.value}: {l1_count}项")
    print(f"   {RiskLevel.L2.value}: {l2_count}项")
    print(f"   {RiskLevel.L3.value}: {l3_count}项")
    
    print(f"\n📋 详细结果:")
    for i, result in enumerate(results, 1):
        status = "✅ 通过" if result.passed else "❌ 未通过"
        print(f"   {i}. {result.name}")
        print(f"      状态: {status} | 得分: {result.score:.1f} | 风险: {result.risk_level.value}")
    
    print("\n" + "="*70)
    print("💡 关键发现:")
    if avg_score < 70:
        print("   ⚠️ 信息过载问题严重，建议实施重排序和上下文压缩")
    elif avg_score < 85:
        print("   ⚡ 信息过载控制尚可，建议优化检索策略")
    else:
        print("   ✅ 信息过载控制良好")
    
    if l1_count > 0:
        print(f"   🚨 发现{l1_count}个阻断性风险，需要立即处理")
    if l2_count > 0:
        print(f"   ⚠️ 发现{l2_count}个高优先级风险，建议优先处理")
    
    print("\n🔧 优化建议:")
    print("   1. 实施重排序策略，只保留Top-K最相关文档")
    print("   2. 设置上下文长度上限，避免过长上下文")
    print("   3. 使用上下文压缩技术，减少Token消耗")
    print("   4. 监控信噪比，设置噪声容忍阈值")
    
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 41: 上下文信息过载检测")
    print("="*70)
    print("测试架构师视角：检测LLM在面对过多无关信息时的处理能力")
    
    results = [
        test_noise_ratio_pressure(),
        test_context_length_breakpoint(),
        test_information_conflict(),
        test_reranking_effectiveness()
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
