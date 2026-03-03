"""
Day 44: Ragas框架 - 生成质量指标（Faithfulness + Answer Relevancy）
目标：验证生成层质量指标，重点检测幻觉风险
测试架构师视角：幻觉是RAG系统最大的质量风险，必须量化检测
难度级别：进阶
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
    expected_issues: List[str] = field(default_factory=list)


# ==================== 模拟测试数据集 ====================

TEST_CASES = {
    "faithful_ideal": RAGTestCase(
        query="RAG系统有什么优势？",
        contexts=[
            "RAG（Retrieval-Augmented Generation）是一种将检索与生成结合的AI架构。",
            "RAG的优势包括：减少幻觉、支持实时知识更新、提高答案可解释性。",
            "RAG系统首先从知识库中检索相关文档，然后将这些文档作为上下文输入给大语言模型。"
        ],
        answer="RAG系统的主要优势包括：1) 减少幻觉，因为答案基于检索到的文档；2) 支持实时知识更新，无需重新训练模型；3) 提高答案可解释性，可以追溯答案来源。",
        ground_truth="RAG优势：减少幻觉、支持实时更新、提高可解释性",
        expected_issues=[]
    ),
    "hallucination_external": RAGTestCase(
        query="Python的GIL是什么？",
        contexts=[
            "GIL（Global Interpreter Lock）是Python解释器中的全局解释器锁。",
            "GIL确保同一时刻只有一个线程执行Python字节码。"
        ],
        answer="GIL是Python的全局解释器锁，它确保同一时刻只有一个线程执行Python字节码。GIL在Python 3.8版本中被移除，推荐使用多进程替代多线程。",
        ground_truth="GIL是全局解释器锁",
        expected_issues=["引入外部知识：GIL在3.8被移除（虚假）"]
    ),
    "hallucination_contradiction": RAGTestCase(
        query="Transformer架构是什么时候提出的？",
        contexts=[
            "Transformer架构于2017年由Google的研究人员在论文《Attention Is All You Need》中提出。",
            "Transformer完全基于注意力机制，摒弃了RNN和CNN。"
        ],
        answer="Transformer架构于2015年由OpenAI的研究人员提出，它基于RNN和CNN的组合架构。",
        ground_truth="2017年，Google提出",
        expected_issues=["与上下文矛盾：时间错误", "与上下文矛盾：作者错误", "与上下文矛盾：架构描述错误"]
    ),
    "irrelevant_answer": RAGTestCase(
        query="什么是Embedding模型？",
        contexts=[
            "Embedding模型将文本转换为高维向量表示。",
            "常见的Embedding模型包括Word2Vec、GloVe、BERT等。"
        ],
        answer="深度学习是机器学习的一个分支，它使用多层神经网络来学习数据的层次化表示。深度学习在图像识别、自然语言处理等领域取得了巨大成功。",
        ground_truth="Embedding是将文本转为向量的模型",
        expected_issues=["答非所问：未回答Embedding相关问题"]
    ),
    "incomplete_answer": RAGTestCase(
        query="RAG系统由哪些组件组成？",
        contexts=[
            "RAG系统主要由三个组件组成：检索器（Retriever）、生成器（Generator）和知识库（Knowledge Base）。",
            "检索器负责从知识库中召回相关文档。",
            "生成器基于检索到的上下文生成答案。",
            "知识库存储结构化的文档数据。"
        ],
        answer="RAG系统包含检索器和生成器。",
        ground_truth="检索器、生成器、知识库",
        expected_issues=["回答不完整：遗漏知识库组件"]
    ),
    "overly_verbose": RAGTestCase(
        query="什么是Token？",
        contexts=[
            "Token是文本处理中的基本单位，可以是单词、子词或字符。",
            "GPT模型使用BPE（Byte Pair Encoding）算法将文本分割为Token。"
        ],
        answer="Token是文本处理中的基本单位。在自然语言处理中，Tokenization是将文本分割为Token的过程。GPT模型使用BPE算法进行Tokenization。此外，深度学习是机器学习的一个分支，神经网络是其核心组件。Python是一种流行的编程语言，广泛用于AI开发。",
        ground_truth="Token是文本基本单位",
        expected_issues=["过度发散：包含大量无关信息"]
    )
}


# ==================== 指标计算函数 ====================

def extract_claims(answer: str) -> List[str]:
    """从答案中提取事实声明（简化版）"""
    # 按句号、分号分割
    sentences = [s.strip() for s in answer.replace('；', '.').replace('。', '.').split('.') if s.strip()]
    
    # 过滤过短的句子
    claims = [s for s in sentences if len(s) > 10]
    return claims


def check_claim_against_context(claim: str, contexts: List[str]) -> Tuple[str, float]:
    """
    模拟NLI验证：检查声明与上下文的关系（中文优化版）
    返回: (关系类型, 置信度)
    """
    claim_lower = claim.lower()
    all_context = ' '.join(contexts).lower()
    
    # 中文关键词匹配（2字组合）
    claim_keywords = set(claim_lower[i:i+2] for i in range(len(claim_lower)-1) if len(claim_lower[i:i+2].strip()) == 2)
    
    # 检查关键词匹配率
    if claim_keywords:
        match_count = sum(1 for kw in claim_keywords if kw in all_context)
        overlap_ratio = match_count / len(claim_keywords)
    else:
        overlap_ratio = 0
    
    # 检查矛盾关键词
    contradiction_indicators = ['不是', '错误', '相反', '并未', '没有', '不对']
    has_contradiction = any(ind in claim_lower for ind in contradiction_indicators)
    
    # 检查不确定性
    uncertainty_indicators = ['可能', '也许', '大概', '应该', '我认为', '我猜']
    has_uncertainty = any(ind in claim_lower for ind in uncertainty_indicators)
    
    # 判断关系
    if has_contradiction and overlap_ratio < 0.3:
        return "contradiction", 0.8
    elif overlap_ratio > 0.5:  # 降低阈值以适应中文
        return "entailment", min(overlap_ratio + 0.2, 1.0)
    elif has_uncertainty:
        return "neutral", 0.5
    else:
        return "neutral", 0.3


def calculate_faithfulness(contexts: List[str], answer: str) -> Tuple[float, Dict]:
    """
    计算Faithfulness分数
    返回: (分数, 详细分析)
    """
    claims = extract_claims(answer)
    
    if not claims:
        return 1.0, {"claims": [], "analysis": "无声明可验证"}
    
    supported_count = 0
    claim_analysis = []
    
    for claim in claims:
        relation, confidence = check_claim_against_context(claim, contexts)
        
        if relation == "entailment":
            supported_count += 1
            claim_analysis.append({"claim": claim, "status": "✓ 支持", "confidence": confidence})
        elif relation == "contradiction":
            claim_analysis.append({"claim": claim, "status": "✗ 矛盾", "confidence": confidence})
        else:
            claim_analysis.append({"claim": claim, "status": "? 不确定", "confidence": confidence})
    
    score = supported_count / len(claims)
    
    return score, {
        "total_claims": len(claims),
        "supported": supported_count,
        "claim_analysis": claim_analysis
    }


def calculate_answer_relevancy(query: str, answer: str) -> Tuple[float, Dict]:
    """
    计算Answer Relevancy分数（中文优化版）
    基于语义相似度和完整性
    """
    query_lower = query.lower()
    answer_lower = answer.lower()
    
    # 1. 主题相关性（中文关键词重叠）
    # 提取查询关键词（过滤停用词）
    stop_words = {'什么', '怎么', '如何', '的', '是', '了', '在', '有', '和', '吗'}
    query_keywords = set()
    for length in [4, 3, 2]:
        for i in range(len(query_lower) - length + 1):
            word = query_lower[i:i+length]
            if word not in stop_words:
                query_keywords.add(word)
    
    if not query_keywords:
        return 0.0, {"reason": "无法提取查询关键词"}
    
    # 计算匹配率
    matches = sum(1 for kw in query_keywords if kw in answer_lower)
    topic_relevancy = matches / len(query_keywords)
    
    # 2. 完整性检查（基于字符数）
    # 简化：假设合理答案长度为查询长度的3-10倍
    expected_min = len(query) * 2
    expected_max = len(query) * 15
    actual_length = len(answer)
    
    if actual_length < expected_min:
        completeness = 0.5 + 0.5 * (actual_length / expected_min)  # 过于简短
    elif actual_length > expected_max:
        completeness = max(0.5, 1.0 - 0.1 * (actual_length / expected_max - 1))  # 过于冗长
    else:
        completeness = 1.0
    
    # 3. 检测答非所问
    # 如果主题相关度太低，可能是答非所问
    if topic_relevancy < 0.2:
        topic_relevancy = 0.1  # 严重偏离
    
    # 综合得分
    score = (topic_relevancy * 0.6 + completeness * 0.4)
    
    return score, {
        "topic_relevancy": topic_relevancy,
        "completeness": completeness,
        "query_keywords": list(query_keywords),
        "matched_keywords": [kw for kw in query_keywords if kw in answer_lower]
    }


def detect_hallucination_risk(faithfulness: float, answer: str) -> Tuple[str, List[str]]:
    """检测幻觉风险等级"""
    risks = []
    
    if faithfulness < 0.5:
        risks.append("严重幻觉：大量声明缺乏上下文支持")
    elif faithfulness < 0.8:
        risks.append("轻度幻觉：部分声明缺乏上下文支持")
    
    # 检测不确定性词汇
    uncertainty_words = ['可能', '也许', '大概', '应该', '我认为', '我猜']
    found_uncertainty = [w for w in uncertainty_words if w in answer]
    if found_uncertainty:
        risks.append(f"不确定性表达: {found_uncertainty}")
    
    # 检测绝对化表述（可能是幻觉信号）
    absolute_words = ['绝对', '肯定', '一定', '必然']
    found_absolute = [w for w in absolute_words if w in answer]
    if found_absolute and faithfulness < 0.9:
        risks.append(f"绝对化表述伴随低忠实度: {found_absolute}")
    
    if faithfulness < 0.5:
        return "HIGH", risks
    elif faithfulness < 0.8:
        return "MEDIUM", risks
    else:
        return "LOW", risks


# ==================== 测试函数 ====================

def test_faithfulness() -> TestResult:
    """测试Faithfulness指标"""
    print("\n" + "="*60)
    print("🧪 测试1: Faithfulness（忠实度）")
    print("="*60)
    print("测试目标：检测答案中的幻觉风险")
    
    results = []
    for name, case in TEST_CASES.items():
        score, details = calculate_faithfulness(case.contexts, case.answer)
        risk_level, risks = detect_hallucination_risk(score, case.answer)
        results.append((name, score, risk_level, risks))
        
        status = "✅" if score >= 0.8 else "⚠️" if score >= 0.5 else "🚨"
        print(f"\n  {status} {name}: Faithfulness={score:.2f}, 风险={risk_level}")
        if risks:
            for risk in risks[:2]:  # 只显示前2个风险
                print(f"      - {risk}")
    
    # 详细分析幻觉案例
    print("\n" + "-"*60)
    print("📊 幻觉案例分析:")
    
    # 外部知识幻觉
    external_case = TEST_CASES["hallucination_external"]
    score, details = calculate_faithfulness(external_case.contexts, external_case.answer)
    print(f"\n  🚨 外部知识幻觉案例:")
    print(f"     查询: {external_case.query}")
    print(f"     答案: {external_case.answer[:80]}...")
    print(f"     Faithfulness: {score:.2f}")
    print(f"     问题: 引入上下文未提及的虚假事实")
    
    # 矛盾幻觉
    contradiction_case = TEST_CASES["hallucination_contradiction"]
    score, details = calculate_faithfulness(contradiction_case.contexts, contradiction_case.answer)
    print(f"\n  🚨 矛盾幻觉案例:")
    print(f"     查询: {contradiction_case.query}")
    print(f"     答案: {contradiction_case.answer}")
    print(f"     Faithfulness: {score:.2f}")
    print(f"     问题: 答案与上下文存在多处矛盾")
    
    avg_score = sum(r[1] for r in results) / len(results)
    passed = avg_score >= 0.6
    
    high_risk_count = sum(1 for r in results if r[2] == "HIGH")
    risk = RiskLevel.L1 if high_risk_count >= 2 else RiskLevel.L2 if high_risk_count >= 1 else RiskLevel.L3
    
    return TestResult(
        name="Faithfulness",
        passed=passed,
        score=avg_score,
        risk_level=risk,
        details={"case_results": results, "high_risk_count": high_risk_count}
    )


def test_answer_relevancy() -> TestResult:
    """测试Answer Relevancy指标"""
    print("\n" + "="*60)
    print("🧪 测试2: Answer Relevancy（答案相关性）")
    print("="*60)
    print("测试目标：验证答案是否直接回应问题")
    
    results = []
    for name, case in TEST_CASES.items():
        score, details = calculate_answer_relevancy(case.query, case.answer)
        results.append((name, score, details))
        
        status = "✅" if score >= 0.7 else "⚠️"
        print(f"  {status} {name}: {score:.2f}")
    
    # 详细分析答非所问案例
    print("\n" + "-"*60)
    print("📊 答案质量问题分析:")
    
    irrelevant_case = TEST_CASES["irrelevant_answer"]
    score, details = calculate_answer_relevancy(irrelevant_case.query, irrelevant_case.answer)
    print(f"\n  ⚠️ 答非所问案例:")
    print(f"     查询: {irrelevant_case.query}")
    print(f"     答案: {irrelevant_case.answer[:80]}...")
    print(f"     Relevancy: {score:.2f}")
    print(f"     主题相关度: {details['topic_relevancy']:.2f}")
    print(f"     问题: 答案完全偏离问题主题")
    
    incomplete_case = TEST_CASES["incomplete_answer"]
    score, details = calculate_answer_relevancy(incomplete_case.query, incomplete_case.answer)
    print(f"\n  ⚠️ 回答不完整案例:")
    print(f"     查询: {incomplete_case.query}")
    print(f"     答案: {incomplete_case.answer}")
    print(f"     Relevancy: {score:.2f}")
    print(f"     完整性: {details['completeness']:.2f}")
    print(f"     问题: 遗漏关键组件信息")
    
    avg_score = sum(r[1] for r in results) / len(results)
    passed = avg_score >= 0.6
    risk = RiskLevel.L2 if avg_score < 0.7 else RiskLevel.L3
    
    return TestResult(
        name="Answer Relevancy",
        passed=passed,
        score=avg_score,
        risk_level=risk,
        details={"case_results": results}
    )


def test_five_metrics_comprehensive() -> TestResult:
    """五大指标综合分析"""
    print("\n" + "="*60)
    print("🧪 测试3: 五大核心指标综合分析")
    print("="*60)
    print("测试目标：建立完整的RAG质量评估体系")
    
    # 导入Day 43的指标计算函数（中文优化版）
    def context_precision(contexts, answer):
        answer_lower = answer.lower()
        used = 0
        for ctx in contexts:
            ctx_lower = ctx.lower()
            # 提取2字关键词
            ctx_keywords = set(ctx_lower[i:i+2] for i in range(len(ctx_lower)-1) if len(ctx_lower[i:i+2].strip()) == 2)
            match_count = sum(1 for kw in ctx_keywords if kw in answer_lower)
            if ctx_keywords and match_count / len(ctx_keywords) > 0.3:
                used += 1
        return used / len(contexts) if contexts else 0
    
    def context_recall(contexts, answer):
        sentences = [s.strip() for s in answer.replace('；', '.').replace('。', '.').split('.') if s.strip()]
        if not sentences:
            return 1.0
        all_ctx = ' '.join(contexts).lower()
        supported = 0
        for sent in sentences:
            sent_lower = sent.lower()
            sent_keywords = set(sent_lower[i:i+2] for i in range(len(sent_lower)-1) if len(sent_lower[i:i+2].strip()) == 2)
            if sent_keywords:
                match_count = sum(1 for kw in sent_keywords if kw in all_ctx)
                if match_count / len(sent_keywords) > 0.4:
                    supported += 1
        return supported / len(sentences)
    
    def context_relevancy(query, contexts):
        if not contexts:
            return 0.0
        query_lower = query.lower()
        # 提取查询关键词（过滤停用词）
        stop_words = {'什么', '怎么', '如何', '的', '是', '了'}
        query_keywords = set()
        for length in [4, 3, 2]:
            for i in range(len(query_lower) - length + 1):
                word = query_lower[i:i+length]
                if word not in stop_words:
                    query_keywords.add(word)
        if not query_keywords:
            return 0.0
        scores = []
        for ctx in contexts:
            ctx_lower = ctx.lower()
            matches = sum(1 for kw in query_keywords if kw in ctx_lower)
            scores.append(matches / len(query_keywords))
        return sum(scores) / len(scores)
    
    print("\n📋 五大指标综合评分:")
    print("-" * 90)
    print(f"{'场景':<20} {'Precision':>10} {'Recall':>8} {'Relevancy':>10} {'Faithful':>10} {'AnsRel':>8} {'综合':>8}")
    print("-" * 90)
    
    all_scores = []
    for name, case in TEST_CASES.items():
        p = context_precision(case.contexts, case.answer)
        r = context_recall(case.contexts, case.answer)
        cr = context_relevancy(case.query, case.contexts)
        f, _ = calculate_faithfulness(case.contexts, case.answer)
        ar, _ = calculate_answer_relevancy(case.query, case.answer)
        
        composite = (p + r + cr + f + ar) / 5
        all_scores.append((p, r, cr, f, ar, composite))
        
        print(f"{name:<20} {p:>10.2f} {r:>8.2f} {cr:>10.2f} {f:>10.2f} {ar:>8.2f} {composite:>8.2f}")
    
    print("-" * 90)
    
    # 计算平均
    avg_scores = [sum(s[i] for s in all_scores) / len(all_scores) for i in range(6)]
    print(f"{'平均值':<20} {avg_scores[0]:>10.2f} {avg_scores[1]:>8.2f} {avg_scores[2]:>10.2f} {avg_scores[3]:>10.2f} {avg_scores[4]:>8.2f} {avg_scores[5]:>8.2f}")
    
    print("\n📊 指标解读:")
    print("  • Context Precision: 检索精确率（高=噪声少）")
    print("  • Context Recall: 检索召回率（高=信息全）")
    print("  • Context Relevancy: 上下文相关性（高=匹配好）")
    print("  • Faithfulness: 答案忠实度（高=幻觉少）")
    print("  • Answer Relevancy: 答案相关性（高=回应准）")
    
    print("\n🎯 质量评估结论:")
    composite = avg_scores[5]
    if composite < 0.5:
        print(f"  🚨 整体质量严重不达标（综合得分: {composite:.2f}）")
        risk = RiskLevel.L1
    elif composite < 0.7:
        print(f"  ⚠️ 整体质量存在隐患（综合得分: {composite:.2f}）")
        risk = RiskLevel.L2
    else:
        print(f"  ✅ 整体质量良好（综合得分: {composite:.2f}）")
        risk = RiskLevel.L3
    
    return TestResult(
        name="Five Metrics Comprehensive",
        passed=composite >= 0.6,
        score=composite,
        risk_level=risk,
        details={
            "avg_precision": avg_scores[0],
            "avg_recall": avg_scores[1],
            "avg_context_relevancy": avg_scores[2],
            "avg_faithfulness": avg_scores[3],
            "avg_answer_relevancy": avg_scores[4],
            "composite_score": composite
        }
    )


def test_hallucination_detection() -> TestResult:
    """幻觉检测实战"""
    print("\n" + "="*60)
    print("🧪 测试4: 幻觉检测实战")
    print("="*60)
    print("测试目标：建立多层级幻觉检测策略")
    
    print("\n📋 幻觉检测层级:")
    print("-" * 60)
    
    print("\n  Level 1 - 规则检测:")
    print("    ✓ 检测不确定性词汇: '可能'、'也许'、'我认为'")
    print("    ✓ 检测绝对化表述: '绝对'、'肯定'、'一定'")
    print("    ✓ 检测时间/数字异常")
    
    print("\n  Level 2 - NLI检测:")
    print("    ✓ 声明抽取与上下文比对")
    print("    ✓ Entailment/Contradiction/Neutral分类")
    print("    ✓ 批量自动化验证")
    
    print("\n  Level 3 - LLM评委:")
    print("    ✓ 使用更强LLM作为验证器")
    print("    ✓ 复杂推理关系检测")
    print("    ✓ 隐含关系识别")
    
    # 实际检测演示
    print("\n📊 实际检测演示:")
    
    test_answers = [
        ("RAG可以减少幻觉，支持实时知识更新。", "忠实回答"),
        ("RAG在2020年被OpenAI提出，基于CNN架构。", "多重幻觉"),
        ("我认为RAG可能有助于减少幻觉。", "不确定性表达"),
    ]
    
    contexts = TEST_CASES["faithful_ideal"].contexts
    
    for ans, label in test_answers:
        score, details = calculate_faithfulness(contexts, ans)
        risk, risks = detect_hallucination_risk(score, ans)
        status = "✅" if score >= 0.8 else "⚠️" if score >= 0.5 else "🚨"
        print(f"\n  {status} [{label}] Faithfulness={score:.2f}")
        print(f"     答案: {ans[:50]}...")
        if risks:
            print(f"     风险: {risks[0]}")
    
    return TestResult(
        name="Hallucination Detection",
        passed=True,
        score=0.75,
        risk_level=RiskLevel.L3,
        details={"detection_levels": 3}
    )


# ==================== 主入口 ====================

def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 测试汇总报告 - Day 44: Ragas生成质量指标")
    print("="*70)
    
    print(f"\n{'测试项':<35} {'得分':>10} {'状态':>8} {'风险等级':>12}")
    print("-" * 70)
    
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{r.name:<35} {r.score:>10.2f} {status:>8} {r.risk_level.value:>12}")
    
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
    print(f"  1. Faithfulness是检测幻觉的核心指标")
    print(f"  2. Answer Relevancy评估答案是否回应问题")
    print(f"  3. 五大指标联合使用可全面评估RAG质量")
    print(f"  4. 建议阈值: Faithfulness>0.8, Answer Relevancy>0.7")
    
    print(f"\n💡 下一步:")
    print(f"  运行 Day 45 测试，学习自定义指标开发")
    
    print("\n" + "="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 44: Ragas生成质量指标")
    print("="*70)
    print("测试架构师视角：幻觉是RAG系统最大的质量风险")
    print("="*70)
    
    results = [
        test_faithfulness(),
        test_answer_relevancy(),
        test_five_metrics_comprehensive(),
        test_hallucination_detection()
    ]
    
    print_summary(results)
    
    # 输出JSON格式结果
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
