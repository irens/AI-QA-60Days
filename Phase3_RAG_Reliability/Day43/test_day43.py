"""
Day 43: Ragas框架 - Context检索质量指标
目标：验证Context Precision/Recall/Relevancy三大指标的计算与风险识别
测试架构师视角：检索层质量是RAG系统的根基，必须量化监控
难度级别：基础
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from enum import Enum


class RiskLevel(Enum):
    L1 = "L1-阻断性"
    L2 = "L2-高优先级"
    L3 = "L3-一般风险"


@dataclass
class TestResult:
    name: str
    passed: bool
    score: float
    risk_level: RiskLevel
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGTestCase:
    """RAG测试用例结构"""
    query: str
    contexts: List[str]
    answer: str
    ground_truth: str = ""


# ==================== 模拟测试数据集 ====================

TEST_CASES = {
    "ideal": RAGTestCase(
        query="什么是RAG系统？",
        contexts=[
            "RAG（Retrieval-Augmented Generation）是一种将检索与生成结合的AI架构。",
            "RAG系统首先从知识库中检索相关文档，然后将这些文档作为上下文输入给大语言模型。",
            "RAG的优势包括：减少幻觉、支持实时知识更新、提高答案可解释性。"
        ],
        answer="RAG（Retrieval-Augmented Generation）是一种将检索与生成结合的AI架构。它首先从知识库中检索相关文档，然后将这些文档作为上下文输入给大语言模型，从而减少幻觉、支持实时知识更新并提高答案可解释性。",
        ground_truth="RAG是将检索与生成结合的AI架构"
    ),
    "low_precision": RAGTestCase(
        query="Python的GIL是什么？",
        contexts=[
            "Python是一种高级编程语言，由Guido van Rossum创建。",
            "GIL（Global Interpreter Lock）是Python解释器中的全局解释器锁。",
            "Java也是一种流行的编程语言，常用于企业级应用开发。",
            "C++是一种高性能的编程语言，支持面向对象编程。",
            "GIL确保同一时刻只有一个线程执行Python字节码。"
        ],
        answer="GIL（Global Interpreter Lock）是Python解释器中的全局解释器锁，它确保同一时刻只有一个线程执行Python字节码。",
        ground_truth="GIL是Python的全局解释器锁"
    ),
    "low_recall": RAGTestCase(
        query="如何优化RAG系统的检索效果？",
        contexts=[
            "使用混合检索（向量+关键词）可以提高召回率。",
            "重排序（Reranking）模型可以优化检索结果的排序。"
        ],
        answer="优化RAG检索效果的方法包括：1) 使用混合检索（向量+关键词）；2) 重排序模型优化结果；3) 查询重写（Query Rewriting）扩展语义覆盖；4) 文档分块策略优化；5) 元数据过滤提升精确率。",
        ground_truth="多种优化方法"
    ),
    "irrelevant_contexts": RAGTestCase(
        query="Transformer架构的核心创新是什么？",
        contexts=[
            "CNN（卷积神经网络）在图像处理领域表现出色。",
            "RNN（循环神经网络）适合处理序列数据。",
            "Self-Attention机制是Transformer的核心创新，它允许模型直接建模序列中任意位置的关系。",
            "LSTM是一种特殊的RNN结构，可以解决长程依赖问题。"
        ],
        answer="Self-Attention机制是Transformer的核心创新，它允许模型直接建模序列中任意位置的关系。",
        ground_truth="Self-Attention机制"
    )
}


# ==================== 指标计算函数 ====================

def calculate_context_precision(contexts: List[str], answer: str) -> float:
    """
    计算Context Precision：相关上下文块数 / 召回总上下文块数
    模拟实现：通过关键词匹配判断上下文是否被答案使用
    """
    if not contexts:
        return 0.0
    
    used_count = 0
    answer_lower = answer.lower()
    
    for ctx in contexts:
        # 中文优化：按字符和关键词匹配
        ctx_lower = ctx.lower()
        # 提取上下文中的关键词（长度>1的词）
        ctx_keywords = set()
        for i in range(len(ctx_lower) - 1):
            word = ctx_lower[i:i+2]
            if len(word.strip()) == 2:  # 确保是有效字符
                ctx_keywords.add(word)
        
        # 检查这些关键词是否在答案中出现
        match_count = sum(1 for kw in ctx_keywords if kw in answer_lower)
        # 如果匹配度超过30%，认为被使用
        if ctx_keywords and match_count / len(ctx_keywords) > 0.3:
            used_count += 1
    
    return used_count / len(contexts)


def calculate_context_recall(contexts: List[str], answer: str) -> float:
    """
    计算Context Recall：被上下文支持的事实数 / 答案总事实数
    模拟实现：将答案分句，检查每句是否有上下文支持
    """
    # 简单分句（支持中英文）
    sentences = [s.strip() for s in answer.replace('；', '.').replace('。', '.').split('.') if s.strip()]
    
    if not sentences:
        return 1.0
    
    supported_count = 0
    all_context = ' '.join(contexts).lower()
    
    for sent in sentences:
        sent_lower = sent.lower()
        # 提取句子中的关键词（2字组合）
        sent_keywords = set()
        for i in range(len(sent_lower) - 1):
            word = sent_lower[i:i+2]
            if len(word.strip()) == 2:
                sent_keywords.add(word)
        
        # 检查关键词是否在上下文中出现
        if sent_keywords:
            match_count = sum(1 for kw in sent_keywords if kw in all_context)
            # 如果超过40%的关键词匹配，认为被支持
            if match_count / len(sent_keywords) > 0.4:
                supported_count += 1
    
    return supported_count / len(sentences)


def calculate_context_relevancy(query: str, contexts: List[str]) -> float:
    """
    计算Context Relevancy：上下文与查询的语义相关程度
    模拟实现：基于关键词重叠计算（中文优化版）
    """
    if not contexts:
        return 0.0
    
    query_lower = query.lower()
    
    # 提取查询中的核心实体词（长度>=2的词，过滤常见停用词）
    stop_words = {'什么', '怎么', '如何', '的', '是', '了', '在', '有', '和', '与', '或'}
    query_keywords = set()
    
    # 尝试提取有意义的词（2-4字）
    for length in [4, 3, 2]:
        for i in range(len(query_lower) - length + 1):
            word = query_lower[i:i+length]
            if word not in stop_words and all(c.isalnum() or '\u4e00' <= c <= '\u9fff' for c in word):
                query_keywords.add(word)
    
    if not query_keywords:
        return 0.0
    
    relevancy_scores = []
    
    for ctx in contexts:
        ctx_lower = ctx.lower()
        
        # 计算查询关键词在上下文中的匹配率
        matches = sum(1 for kw in query_keywords if kw in ctx_lower)
        
        # 相关度 = 匹配关键词数 / 总关键词数
        score = matches / len(query_keywords) if query_keywords else 0.0
        relevancy_scores.append(score)
    
    return sum(relevancy_scores) / len(relevancy_scores)


def evaluate_risk_level(precision: float, recall: float, relevancy: float) -> RiskLevel:
    """根据指标评估风险等级"""
    if precision < 0.4 or recall < 0.5 or relevancy < 0.4:
        return RiskLevel.L1
    elif precision < 0.7 or recall < 0.8 or relevancy < 0.6:
        return RiskLevel.L2
    else:
        return RiskLevel.L3


# ==================== 测试函数 ====================

def test_context_precision() -> TestResult:
    """测试Context Precision指标"""
    print("\n" + "="*60)
    print("🧪 测试1: Context Precision（上下文精确率）")
    print("="*60)
    print("测试目标：验证召回文档中真正相关的比例")
    
    results = []
    for name, case in TEST_CASES.items():
        score = calculate_context_precision(case.contexts, case.answer)
        results.append((name, score, len(case.contexts)))
        status = "✅" if score >= 0.7 else "⚠️"
        print(f"  {status} {name}: {score:.2f} (召回{len(case.contexts)}篇)")
    
    # 评估低Precision场景
    low_precision_case = TEST_CASES["low_precision"]
    score = calculate_context_precision(low_precision_case.contexts, low_precision_case.answer)
    
    print(f"\n📊 低Precision场景分析:")
    print(f"  查询: {low_precision_case.query}")
    print(f"  召回文档数: {len(low_precision_case.contexts)}")
    print(f"  相关文档数: 估计2篇")
    print(f"  Precision: {score:.2f}")
    print(f"  ⚠️ 风险: 噪声文档过多，可能干扰模型生成")
    
    avg_score = sum(r[1] for r in results) / len(results)
    passed = avg_score >= 0.6
    risk = RiskLevel.L2 if score < 0.7 else RiskLevel.L3
    
    return TestResult(
        name="Context Precision",
        passed=passed,
        score=avg_score,
        risk_level=risk,
        details={"case_results": results, "low_precision_score": score}
    )


def test_context_recall() -> TestResult:
    """测试Context Recall指标"""
    print("\n" + "="*60)
    print("🧪 测试2: Context Recall（上下文召回率）")
    print("="*60)
    print("测试目标：验证答案所需信息是否被完整召回")
    
    results = []
    for name, case in TEST_CASES.items():
        score = calculate_context_recall(case.contexts, case.answer)
        results.append((name, score))
        status = "✅" if score >= 0.8 else "⚠️"
        print(f"  {status} {name}: {score:.2f}")
    
    # 评估低Recall场景
    low_recall_case = TEST_CASES["low_recall"]
    score = calculate_context_recall(low_recall_case.contexts, low_recall_case.answer)
    
    print(f"\n📊 低Recall场景分析:")
    print(f"  查询: {low_recall_case.query}")
    print(f"  答案包含方法数: 5种")
    print(f"  上下文覆盖方法数: 估计2种")
    print(f"  Recall: {score:.2f}")
    print(f"  🚨 风险: 信息遗漏，答案中部分声明缺乏上下文支持（幻觉风险）")
    
    avg_score = sum(r[1] for r in results) / len(results)
    passed = avg_score >= 0.6
    risk = RiskLevel.L1 if score < 0.6 else RiskLevel.L2
    
    return TestResult(
        name="Context Recall",
        passed=passed,
        score=avg_score,
        risk_level=risk,
        details={"case_results": results, "low_recall_score": score}
    )


def test_context_relevancy() -> TestResult:
    """测试Context Relevancy指标"""
    print("\n" + "="*60)
    print("🧪 测试3: Context Relevancy（上下文相关性）")
    print("="*60)
    print("测试目标：验证召回文档与问题的语义匹配度")
    
    results = []
    for name, case in TEST_CASES.items():
        score = calculate_context_relevancy(case.query, case.contexts)
        results.append((name, score))
        status = "✅" if score >= 0.6 else "⚠️"
        print(f"  {status} {name}: {score:.2f}")
    
    # 评估不相关上下文场景
    irrelevant_case = TEST_CASES["irrelevant_contexts"]
    score = calculate_context_relevancy(irrelevant_case.query, irrelevant_case.contexts)
    
    print(f"\n📊 不相关上下文场景分析:")
    print(f"  查询: {irrelevant_case.query}")
    print(f"  召回文档数: {len(irrelevant_case.contexts)}")
    print(f"  相关文档数: 1篇（Self-Attention）")
    print(f"  Relevancy: {score:.2f}")
    print(f"  ⚠️ 风险: 召回大量无关文档，浪费上下文窗口")
    
    avg_score = sum(r[1] for r in results) / len(results)
    passed = avg_score >= 0.5
    risk = RiskLevel.L2 if score < 0.5 else RiskLevel.L3
    
    return TestResult(
        name="Context Relevancy",
        passed=passed,
        score=avg_score,
        risk_level=risk,
        details={"case_results": results, "irrelevant_score": score}
    )


def test_comprehensive_evaluation() -> TestResult:
    """综合评估：多指标联合分析"""
    print("\n" + "="*60)
    print("🧪 测试4: 综合评估 - 多指标联合分析")
    print("="*60)
    print("测试目标：建立完整的检索质量评估体系")
    
    print("\n📋 各场景综合评分:")
    print("-" * 70)
    print(f"{'场景':<20} {'Precision':>12} {'Recall':>10} {'Relevancy':>12} {'风险等级':>10}")
    print("-" * 70)
    
    all_scores = []
    for name, case in TEST_CASES.items():
        p = calculate_context_precision(case.contexts, case.answer)
        r = calculate_context_recall(case.contexts, case.answer)
        rel = calculate_context_relevancy(case.query, case.contexts)
        risk = evaluate_risk_level(p, r, rel)
        all_scores.append((p, r, rel))
        print(f"{name:<20} {p:>12.2f} {r:>10.2f} {rel:>12.2f} {risk.value:>10}")
    
    print("-" * 70)
    
    # 计算平均
    avg_p = sum(s[0] for s in all_scores) / len(all_scores)
    avg_r = sum(s[1] for s in all_scores) / len(all_scores)
    avg_rel = sum(s[2] for s in all_scores) / len(all_scores)
    
    print(f"{'平均值':<20} {avg_p:>12.2f} {avg_r:>10.2f} {avg_rel:>12.2f}")
    
    print("\n📊 质量评估结论:")
    overall_risk = evaluate_risk_level(avg_p, avg_r, avg_rel)
    print(f"  整体风险等级: {overall_risk.value}")
    
    if overall_risk == RiskLevel.L1:
        print("  🚨 检索质量严重不达标，需立即优化")
    elif overall_risk == RiskLevel.L2:
        print("  ⚠️ 检索质量存在隐患，建议优化")
    else:
        print("  ✅ 检索质量良好，持续监控")
    
    # 综合得分
    composite_score = (avg_p + avg_r + avg_rel) / 3
    
    return TestResult(
        name="Comprehensive Evaluation",
        passed=composite_score >= 0.6,
        score=composite_score,
        risk_level=overall_risk,
        details={
            "avg_precision": avg_p,
            "avg_recall": avg_r,
            "avg_relevancy": avg_rel,
            "composite_score": composite_score
        }
    )


# ==================== 主入口 ====================

def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 测试汇总报告 - Day 43: Ragas Context指标")
    print("="*70)
    
    print(f"\n{'测试项':<30} {'得分':>10} {'状态':>8} {'风险等级':>12}")
    print("-" * 70)
    
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{r.name:<30} {r.score:>10.2f} {status:>8} {r.risk_level.value:>12}")
    
    print("-" * 70)
    
    avg_score = sum(r.score for r in results) / len(results)
    passed_count = sum(1 for r in results if r.passed)
    l1_count = sum(1 for r in results if r.risk_level == RiskLevel.L1)
    l2_count = sum(1 for r in results if r.risk_level == RiskLevel.L2)
    
    print(f"\n📈 总体统计:")
    print(f"  平均得分: {avg_score:.2f}")
    print(f"  通过测试: {passed_count}/{len(results)}")
    print(f"  L1风险: {l1_count}个")
    print(f"  L2风险: {l2_count}个")
    
    print(f"\n🎯 关键发现:")
    print(f"  1. Context Precision关注'召回的准不准'")
    print(f"  2. Context Recall关注'该召的召回了没'")
    print(f"  3. Context Relevancy关注'召回来的是否相关'")
    print(f"  4. 三个指标需联合使用，单一指标无法全面评估")
    
    print(f"\n💡 下一步:")
    print(f"  运行 Day 44 测试，学习 Faithfulness + Answer Relevancy 指标")
    
    print("\n" + "="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 43: Ragas Context指标")
    print("="*70)
    print("测试架构师视角：检索层质量是RAG系统的根基")
    print("="*70)
    
    results = [
        test_context_precision(),
        test_context_recall(),
        test_context_relevancy(),
        test_comprehensive_evaluation()
    ]
    
    print_summary(results)
    
    # 输出JSON格式结果（便于报告生成）
    print("\n📤 JSON格式结果:")
    json_output = [
        {
            "name": r.name,
            "passed": r.passed,
            "score": round(r.score, 2),
            "risk_level": r.risk_level.value,
            "details": r.details
        }
        for r in results
    ]
    print(json.dumps(json_output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_all_tests()
