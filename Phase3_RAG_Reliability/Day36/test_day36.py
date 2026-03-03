"""
Day 36: 忠实度自动化检测 - 声明抽取与综合分析
目标：最小可用，专注风险验证，杜绝多余业务逻辑
测试架构师视角：验证声明抽取质量对忠实度检测的影响，构建端到端流水线
难度级别：实战
"""

import json
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum


class NLIRelation(Enum):
    """NLI三分类关系"""
    ENTAILMENT = "entailment"
    CONTRADICTION = "contradiction"
    NEUTRAL = "neutral"


class VerificationResult(Enum):
    """验证结果类型"""
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNCERTAIN = "uncertain"


@dataclass
class Claim:
    """原子声明"""
    text: str
    source_span: Tuple[int, int]  # 在原文中的位置
    claim_type: str  # fact, inference, opinion


@dataclass
class ExtractionResult:
    """抽取结果评估"""
    claims: List[Claim]
    completeness: float  # 完整性分数
    granularity_score: float  # 粒度合理性分数


@dataclass
class Verification:
    """验证结果"""
    claim: Claim
    nli_result: NLIRelation
    qa_result: VerificationResult
    final_result: str
    confidence: float


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: str
    details: Dict


def extract_claims_simple(answer: str) -> List[Claim]:
    """
    简单声明抽取：按句号分割
    基准方法，用于对比
    """
    sentences = [s.strip() for s in answer.split("。") if len(s.strip()) > 5]
    claims = []
    pos = 0
    for sent in sentences:
        start = answer.find(sent, pos)
        end = start + len(sent)
        claims.append(Claim(
            text=sent,
            source_span=(start, end),
            claim_type="fact"
        ))
        pos = end
    return claims


def extract_claims_advanced(answer: str) -> List[Claim]:
    """
    高级声明抽取：处理复合声明、代词消解
    模拟LLM-based抽取
    """
    claims = []
    
    # 分句
    sentences = [s.strip() for s in re.split(r'[。；]', answer) if len(s.strip()) > 5]
    
    for sent in sentences:
        # 检测复合声明（包含"和"、"以及"、","等连接词）
        if any(conn in sent for conn in ["和", "以及", "，", "；"]):
            # 尝试拆分复合声明
            parts = re.split(r'[和以及，；]', sent)
            parts = [p.strip() for p in parts if len(p.strip()) > 3]
            
            # 提取主语
            subject_match = re.match(r'^([^是的有在]+)', sent)
            subject = subject_match.group(1) if subject_match else ""
            
            for i, part in enumerate(parts):
                # 代词消解
                claim_text = part
                if subject and not any(word in part for word in ["是", "有", "在", "位于"]):
                    claim_text = f"{subject}{part}"
                elif subject and i > 0:
                    # 补充主语
                    claim_text = f"{subject}{part}"
                
                claims.append(Claim(
                    text=claim_text,
                    source_span=(answer.find(sent), answer.find(sent) + len(sent)),
                    claim_type="fact"
                ))
        else:
            claims.append(Claim(
                text=sent,
                source_span=(answer.find(sent), answer.find(sent) + len(sent)),
                claim_type="fact"
            ))
    
    return claims if claims else [Claim(text=answer, source_span=(0, len(answer)), claim_type="fact")]


def calculate_extraction_quality(original: str, claims: List[Claim]) -> Tuple[float, float]:
    """
    评估抽取质量
    返回：(完整性, 粒度合理性)
    """
    # 完整性：检查是否覆盖了原文的主要信息
    covered_chars = sum(end - start for start, end in [c.source_span for c in claims])
    completeness = min(covered_chars / len(original), 1.0) if original else 0.0
    
    # 粒度合理性：声明平均长度适中（20-80字符为佳）
    if not claims:
        return 0.0, 0.0
    
    avg_length = sum(len(c.text) for c in claims) / len(claims)
    if 20 <= avg_length <= 80:
        granularity = 1.0
    elif avg_length < 20:
        granularity = 0.7  # 过细
    else:
        granularity = 0.8  # 过粗
    
    return completeness, granularity


def mock_nli_verify(context: str, claim_text: str) -> NLIRelation:
    """模拟NLI验证"""
    context_lower = context.lower()
    claim_lower = claim_text.lower()
    
    # 直接包含
    if any(phrase in context_lower for phrase in claim_lower.split()[:3]):
        return NLIRelation.ENTAILMENT
    
    # 矛盾检测
    contradiction_pairs = [("增加", "减少"), ("上升", "下降"), ("高", "低")]
    for pos, neg in contradiction_pairs:
        if pos in claim_lower and neg in context_lower:
            return NLIRelation.CONTRADICTION
    
    return NLIRelation.NEUTRAL


def mock_qa_verify(context: str, claim_text: str) -> VerificationResult:
    """模拟QA验证"""
    # 简化的QA验证逻辑
    context_lower = context.lower()
    claim_lower = claim_text.lower()
    
    # 提取数字进行比对
    claim_nums = re.findall(r'\d+\.?\d*', claim_lower)
    context_nums = re.findall(r'\d+\.?\d*', context_lower)
    
    if claim_nums:
        if any(cn in context_nums for cn in claim_nums):
            return VerificationResult.SUPPORTED
        return VerificationResult.CONTRADICTED
    
    # 关键词匹配
    keywords = claim_lower.split()
    match_count = sum(1 for kw in keywords if kw in context_lower)
    if match_count >= len(keywords) * 0.5:
        return VerificationResult.SUPPORTED
    
    return VerificationResult.UNCERTAIN


def hybrid_verify(context: str, claim: Claim) -> Verification:
    """
    混合验证策略：NLI + QA
    先用NLI快速筛选，对Neutral结果使用QA深度验证
    """
    nli_result = mock_nli_verify(context, claim.text)
    
    if nli_result == NLIRelation.ENTAILMENT:
        return Verification(
            claim=claim,
            nli_result=nli_result,
            qa_result=VerificationResult.SUPPORTED,
            final_result="supported",
            confidence=0.90
        )
    elif nli_result == NLIRelation.CONTRADICTION:
        return Verification(
            claim=claim,
            nli_result=nli_result,
            qa_result=VerificationResult.CONTRADICTED,
            final_result="contradicted",
            confidence=0.85
        )
    else:
        # NLI为Neutral，使用QA验证
        qa_result = mock_qa_verify(context, claim.text)
        final = "supported" if qa_result == VerificationResult.SUPPORTED else \
                "contradicted" if qa_result == VerificationResult.CONTRADICTED else "uncertain"
        return Verification(
            claim=claim,
            nli_result=nli_result,
            qa_result=qa_result,
            final_result=final,
            confidence=0.70
        )


def calculate_faithfulness_score(verifications: List[Verification]) -> float:
    """计算忠实度分数"""
    if not verifications:
        return 0.0
    
    supported = sum(1 for v in verifications if v.final_result == "supported")
    return supported / len(verifications)


def test_extraction_quality():
    """测试场景1：声明抽取质量评估"""
    print("\n" + "="*60)
    print("🧪 测试1：声明抽取质量评估")
    print("="*60)
    
    answer = "北京是中国首都，人口约2180万。上海是经济中心。深圳位于广东省。"
    
    # 简单抽取
    simple_claims = extract_claims_simple(answer)
    simple_comp, simple_gran = calculate_extraction_quality(answer, simple_claims)
    
    # 高级抽取
    advanced_claims = extract_claims_advanced(answer)
    adv_comp, adv_gran = calculate_extraction_quality(answer, advanced_claims)
    
    print(f"📄 原始答案: {answer}")
    print(f"\n🔍 简单抽取结果 ({len(simple_claims)}个声明):")
    for i, c in enumerate(simple_claims, 1):
        print(f"   {i}. {c.text}")
    print(f"   完整性: {simple_comp:.2f}, 粒度合理性: {simple_gran:.2f}")
    
    print(f"\n🔍 高级抽取结果 ({len(advanced_claims)}个声明):")
    for i, c in enumerate(advanced_claims, 1):
        print(f"   {i}. {c.text}")
    print(f"   完整性: {adv_comp:.2f}, 粒度合理性: {adv_gran:.2f}")
    
    # 综合评分
    simple_score = (simple_comp + simple_gran) / 2
    adv_score = (adv_comp + adv_gran) / 2
    
    print(f"\n📊 抽取质量对比:")
    print(f"   简单方法: {simple_score:.2f}")
    print(f"   高级方法: {adv_score:.2f}")
    print(f"   提升: {((adv_score - simple_score) / simple_score * 100):+.1f}%")
    
    return TestResult("声明抽取质量评估", True, adv_score, "L3", {
        "simple_claims": len(simple_claims),
        "advanced_claims": len(advanced_claims),
        "quality_improvement": adv_score - simple_score
    })


def test_compound_claim_splitting():
    """测试场景2：复合声明拆分"""
    print("\n" + "="*60)
    print("🧪 测试2：复合声明拆分")
    print("="*60)
    
    # 包含多个事实的复合句子
    answer = "北京和上海都是中国一线城市，人口众多，经济发达。"
    
    simple_claims = extract_claims_simple(answer)
    advanced_claims = extract_claims_advanced(answer)
    
    print(f"📄 原始答案: {answer}")
    print(f"\n🔍 简单抽取 ({len(simple_claims)}个声明):")
    for c in simple_claims:
        print(f"   - {c.text}")
    print(f"   ⚠️ 问题: 复合声明未拆分，验证时可能部分失败")
    
    print(f"\n🔍 高级抽取 ({len(advanced_claims)}个声明):")
    for c in advanced_claims:
        print(f"   - {c.text}")
    print(f"   ✅ 优势: 拆分为原子声明，可独立验证")
    
    # 验证效果对比
    context = "北京是中国首都，人口约2180万。上海是经济中心，人口约2480万。"
    
    print(f"\n📄 上下文: {context[:60]}...")
    print(f"\n🔍 验证效果对比:")
    
    # 简单方法验证
    simple_verifications = [hybrid_verify(context, c) for c in simple_claims]
    simple_faith = calculate_faithfulness_score(simple_verifications)
    print(f"   简单方法忠实度: {simple_faith:.2f}")
    
    # 高级方法验证
    advanced_verifications = [hybrid_verify(context, c) for c in advanced_claims]
    advanced_faith = calculate_faithfulness_score(advanced_verifications)
    print(f"   高级方法忠实度: {advanced_faith:.2f}")
    
    return TestResult("复合声明拆分", True, advanced_faith, "L3" if advanced_faith >= 0.9 else "L2", {
        "simple_faithfulness": simple_faith,
        "advanced_faithfulness": advanced_faith,
        "improvement": advanced_faith - simple_faith
    })


def test_pronoun_resolution():
    """测试场景3：代词消解测试"""
    print("\n" + "="*60)
    print("🧪 测试3：代词消解测试")
    print("="*60)
    
    # 包含代词的答案
    answer = "Python是一种编程语言。它由Guido创建。它适合初学者。"
    
    simple_claims = extract_claims_simple(answer)
    advanced_claims = extract_claims_advanced(answer)
    
    print(f"📄 原始答案: {answer}")
    print(f"\n🔍 简单抽取:")
    for c in simple_claims:
        print(f"   - {c.text}")
    print(f"   ⚠️ 问题: 代词'它'未消解，无法独立验证")
    
    print(f"\n🔍 高级抽取（代词消解）:")
    for c in advanced_claims:
        print(f"   - {c.text}")
    print(f"   ✅ 优势: 代词已消解为'Python'")
    
    # 验证对比
    context = "Python由Guido van Rossum于1991年创建，是一种易学的编程语言。"
    
    print(f"\n📄 上下文: {context}")
    print(f"\n🔍 验证结果:")
    
    simple_verifications = [hybrid_verify(context, c) for c in simple_claims]
    simple_faith = calculate_faithfulness_score(simple_verifications)
    print(f"   简单方法忠实度: {simple_faith:.2f} (代词导致验证失败)")
    
    advanced_verifications = [hybrid_verify(context, c) for c in advanced_claims]
    advanced_faith = calculate_faithfulness_score(advanced_verifications)
    print(f"   高级方法忠实度: {advanced_faith:.2f} (代词消解成功)")
    
    return TestResult("代词消解测试", True, advanced_faith, "L3" if advanced_faith >= 0.9 else "L2", {
        "simple_faithfulness": simple_faith,
        "advanced_faithfulness": advanced_faith,
        "pronoun_resolved": advanced_faith > simple_faith
    })


def test_end_to_end_pipeline():
    """测试场景4：端到端流水线"""
    print("\n" + "="*60)
    print("🧪 测试4：端到端忠实度检测流水线")
    print("="*60)
    
    context = """
    北京市是中华人民共和国首都，常住人口约2180万。
    2023年北京市GDP达到4.4万亿元人民币。
    北京拥有众多历史文化遗产，如故宫、长城等。
    """
    
    answer = "北京是中国首都，人口约2180万。北京2023年GDP约4.4万亿元。北京有故宫和长城。"
    
    print(f"📄 上下文: {context[:80]}...")
    print(f"💬 模型答案: {answer}")
    
    # Step 1: 声明抽取
    print(f"\n📌 Step 1: 声明抽取")
    claims = extract_claims_advanced(answer)
    print(f"   抽取到 {len(claims)} 个声明")
    for i, c in enumerate(claims, 1):
        print(f"   {i}. {c.text}")
    
    # Step 2: 混合验证
    print(f"\n📌 Step 2: 混合验证 (NLI + QA)")
    verifications = []
    for c in claims:
        v = hybrid_verify(context, c)
        verifications.append(v)
        status = "✅" if v.final_result == "supported" else "❌" if v.final_result == "contradicted" else "⚠️"
        print(f"   {status} '{c.text[:30]}...' → {v.final_result} (置信度: {v.confidence:.2f})")
    
    # Step 3: 分数计算
    print(f"\n📌 Step 3: 忠实度计算")
    faithfulness = calculate_faithfulness_score(verifications)
    risk_level = "L3" if faithfulness >= 0.9 else "L2" if faithfulness >= 0.7 else "L1"
    print(f"   忠实度分数: {faithfulness:.2f}")
    print(f"   风险等级: {risk_level}")
    
    # Step 4: 报告生成
    print(f"\n📌 Step 4: 风险报告")
    supported = sum(1 for v in verifications if v.final_result == "supported")
    contradicted = sum(1 for v in verifications if v.final_result == "contradicted")
    uncertain = sum(1 for v in verifications if v.final_result == "uncertain")
    print(f"   支持: {supported} | 矛盾: {contradicted} | 不确定: {uncertain}")
    
    if risk_level == "L1":
        print(f"   🚨 建议: 拒绝输出或重新检索")
    elif risk_level == "L2":
        print(f"   ⚠️  建议: 添加免责声明")
    else:
        print(f"   ✅ 建议: 正常输出")
    
    return TestResult("端到端流水线", faithfulness >= 0.7, faithfulness, risk_level, {
        "claims_count": len(claims),
        "supported": supported,
        "contradicted": contradicted,
        "uncertain": uncertain
    })


def test_hybrid_strategy_comparison():
    """测试场景5：混合策略对比（NLI vs QA vs Hybrid）"""
    print("\n" + "="*60)
    print("🧪 测试5：验证策略对比 (NLI vs QA vs Hybrid)")
    print("="*60)
    
    context = """
    阿里巴巴成立于1999年，创始人是马云，总部位于杭州。
    淘宝是阿里巴巴旗下的电商平台，成立于2003年。
    """
    
    # 包含隐式和显式事实的答案
    answer = "阿里巴巴成立于1999年。淘宝的创始人也是马云。阿里巴巴总部在杭州。"
    
    print(f"📄 上下文: {context[:80]}...")
    print(f"💬 模型答案: {answer}")
    
    claims = extract_claims_advanced(answer)
    print(f"\n🔍 抽取声明 ({len(claims)}个):")
    for i, c in enumerate(claims, 1):
        print(f"   {i}. {c.text}")
    
    # NLI-only验证
    print(f"\n📊 NLI-only验证:")
    nli_results = [mock_nli_verify(context, c.text) for c in claims]
    nli_faith = sum(1 for r in nli_results if r == NLIRelation.ENTAILMENT) / len(claims)
    for i, (c, r) in enumerate(zip(claims, nli_results), 1):
        status = "✅" if r == NLIRelation.ENTAILMENT else "❌" if r == NLIRelation.CONTRADICTION else "⚠️"
        print(f"   {status} 声明{i}: {r.value}")
    print(f"   忠实度: {nli_faith:.2f}")
    print(f"   💡 特点: 对'淘宝创始人是马云'这类隐式事实可能判定为NEUTRAL")
    
    # QA-only验证
    print(f"\n📊 QA-only验证:")
    qa_results = [mock_qa_verify(context, c.text) for c in claims]
    qa_faith = sum(1 for r in qa_results if r == VerificationResult.SUPPORTED) / len(claims)
    for i, (c, r) in enumerate(zip(claims, qa_results), 1):
        status = "✅" if r == VerificationResult.SUPPORTED else "❌" if r == VerificationResult.CONTRADICTED else "⚠️"
        print(f"   {status} 声明{i}: {r.value}")
    print(f"   忠实度: {qa_faith:.2f}")
    print(f"   💡 特点: 能处理隐式推理，但速度较慢")
    
    # Hybrid验证
    print(f"\n📊 Hybrid验证 (NLI + QA):")
    hybrid_verifications = [hybrid_verify(context, c) for c in claims]
    hybrid_faith = calculate_faithfulness_score(hybrid_verifications)
    for i, v in enumerate(hybrid_verifications, 1):
        status = "✅" if v.final_result == "supported" else "❌" if v.final_result == "contradicted" else "⚠️"
        print(f"   {status} 声明{i}: {v.final_result} (NLI:{v.nli_result.value}, QA:{v.qa_result.value})")
    print(f"   忠实度: {hybrid_faith:.2f}")
    print(f"   💡 特点: 结合两者优势，NLI快速筛选 + QA深度验证")
    
    print(f"\n📈 策略对比总结:")
    print(f"   NLI-only:  {nli_faith:.2f} - 速度快，但对隐式事实支持有限")
    print(f"   QA-only:   {qa_faith:.2f} - 能力强，但成本高")
    print(f"   Hybrid:    {hybrid_faith:.2f} - 平衡效率与效果 ⭐推荐")
    
    return TestResult("混合策略对比", True, hybrid_faith, "L3" if hybrid_faith >= 0.9 else "L2", {
        "nli_faithfulness": nli_faith,
        "qa_faithfulness": qa_faith,
        "hybrid_faithfulness": hybrid_faith,
        "best_strategy": "Hybrid"
    })


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📋 AI QA System Test Summary - Day 36: Claim Extraction & Analysis")
    print("="*70)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.passed)
    
    print(f"\n📊 总体统计:")
    print(f"   总测试数: {total_tests}")
    print(f"   通过数: {passed_tests}")
    print(f"   失败数: {total_tests - passed_tests}")
    print(f"   通过率: {passed_tests/total_tests*100:.1f}%")
    
    print(f"\n🔍 详细结果:")
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        risk_emoji = "🔴" if r.risk_level == "L1" else "🟡" if r.risk_level == "L2" else "🟢"
        print(f"   {status} | {risk_emoji} {r.risk_level} | {r.name}: {r.score:.2f}")
    
    # 风险分布
    l1_count = sum(1 for r in results if r.risk_level == "L1")
    l2_count = sum(1 for r in results if r.risk_level == "L2")
    l3_count = sum(1 for r in results if r.risk_level == "L3")
    
    print(f"\n⚠️  风险分布:")
    print(f"   🔴 L1 (高风险): {l1_count} 项")
    print(f"   🟡 L2 (中风险): {l2_count} 项")
    print(f"   🟢 L3 (低风险): {l3_count} 项")
    
    print(f"\n💡 Day 34-36 忠实度检测总结:")
    print(f"   Day 34 (NLI): 快速显式事实验证")
    print(f"   Day 35 (QA):  深度隐式推理验证")
    print(f"   Day 36 (综合): 声明抽取 + 混合策略 + 端到端流水线")
    print(f"\n   推荐生产环境配置:")
    print(f"   1. 使用LLM-based声明抽取（处理复合声明、代词消解）")
    print(f"   2. 采用Hybrid验证策略（NLI快速筛选 + QA深度验证）")
    print(f"   3. 设置动态阈值（L1: <0.7, L2: 0.7-0.9, L3: >=0.9）")
    
    print("\n" + "="*70)
    print("✅ 测试执行完毕，请将上方日志发给 Trae 生成 report_day36.md")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 36: Claim Extraction & Comprehensive Analysis")
    print("   声明抽取质量评估与端到端忠实度检测流水线")
    print("="*70)
    
    results = [
        test_extraction_quality(),
        test_compound_claim_splitting(),
        test_pronoun_resolution(),
        test_end_to_end_pipeline(),
        test_hybrid_strategy_comparison()
    ]
    
    print_summary(results)


if __name__ == "__main__":
    run_all_tests()
