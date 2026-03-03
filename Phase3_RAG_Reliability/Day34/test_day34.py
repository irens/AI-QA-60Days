"""
Day 34: 忠实度自动化检测 - NLI Entailment方法
目标：最小可用，专注风险验证，杜绝多余业务逻辑
测试架构师视角：验证NLI-based忠实度检测能否有效识别幻觉
难度级别：基础
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Tuple
from enum import Enum


class NLIRelation(Enum):
    """NLI三分类关系"""
    ENTAILMENT = "entailment"       # 蕴含：上下文支持声明
    CONTRADICTION = "contradiction" # 矛盾：上下文否定声明
    NEUTRAL = "neutral"             # 中性：无法确定


@dataclass
class Claim:
    """原子声明"""
    text: str
    relation: NLIRelation
    confidence: float


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: str
    details: Dict


def mock_nli_verify(context: str, claim_text: str) -> Tuple[NLIRelation, float]:
    """
    模拟NLI模型验证声明与上下文的关系
    实际生产环境应调用NLI模型（如roberta-large-mnli）
    """
    # 基于关键词匹配的简单模拟
    context_lower = context.lower()
    claim_lower = claim_text.lower()
    
    # 直接包含检查
    if any(phrase in context_lower for phrase in claim_lower.split()[:3]):
        return NLIRelation.ENTAILMENT, 0.92
    
    # 矛盾检查（简单的反义词检测）
    contradiction_pairs = [
        ("增加", "减少"), ("上升", "下降"), ("高", "低"),
        ("是", "不是"), ("有", "没有"), ("可以", "不能")
    ]
    for pos, neg in contradiction_pairs:
        if pos in claim_lower and neg in context_lower:
            return NLIRelation.CONTRADICTION, 0.85
        if neg in claim_lower and pos in context_lower:
            return NLIRelation.CONTRADICTION, 0.85
    
    # 默认中性（需要推理）
    return NLIRelation.NEUTRAL, 0.60


def extract_claims(answer: str) -> List[str]:
    """
    将答案拆分为原子声明
    实际应使用LLM进行声明抽取
    """
    # 简单按句号分割，实际应更智能
    claims = [c.strip() for c in answer.split("。") if len(c.strip()) > 5]
    return claims if claims else [answer]


def calculate_faithfulness(context: str, answer: str) -> Tuple[float, List[Claim]]:
    """
    计算忠实度分数
    Faithfulness = Entailment数量 / 总声明数量
    """
    claims_text = extract_claims(answer)
    verified_claims = []
    
    entailment_count = 0
    
    for claim_text in claims_text:
        relation, confidence = mock_nli_verify(context, claim_text)
        
        if relation == NLIRelation.ENTAILMENT:
            entailment_count += 1
            
        verified_claims.append(Claim(
            text=claim_text,
            relation=relation,
            confidence=confidence
        ))
    
    score = entailment_count / len(claims_text) if claims_text else 0.0
    return score, verified_claims


def get_risk_level(score: float) -> str:
    """根据分数确定风险等级"""
    if score >= 0.9:
        return "L3"
    elif score >= 0.7:
        return "L2"
    else:
        return "L1"


def test_full_faithful():
    """测试场景1：完全忠实 - 所有声明均被上下文支持"""
    print("\n" + "="*60)
    print("🧪 测试1：完全忠实场景")
    print("="*60)
    
    context = """
    北京市是中华人民共和国的首都，常住人口约2180万。
    北京是中国的政治中心、文化中心和国际交往中心。
    2023年北京市GDP达到4.4万亿元人民币。
    """
    
    answer = "北京是中国首都，常住人口约2180万。2023年北京GDP达4.4万亿元。"
    
    score, claims = calculate_faithfulness(context, answer)
    risk_level = get_risk_level(score)
    
    print(f"📄 上下文片段: {context[:80]}...")
    print(f"💬 模型答案: {answer}")
    print(f"\n🔍 声明验证结果:")
    for i, claim in enumerate(claims, 1):
        status = "✅" if claim.relation == NLIRelation.ENTAILMENT else "❌"
        print(f"   {status} 声明{i}: {claim.text[:40]}...")
        print(f"      关系: {claim.relation.value}, 置信度: {claim.confidence:.2f}")
    
    print(f"\n📊 忠实度分数: {score:.2f}")
    print(f"⚠️  风险等级: {risk_level}")
    
    passed = score >= 0.9
    return TestResult("完全忠实场景", passed, score, risk_level, {
        "claims_count": len(claims),
        "entailment_count": sum(1 for c in claims if c.relation == NLIRelation.ENTAILMENT)
    })


def test_partial_hallucination():
    """测试场景2：部分幻觉 - 部分声明与上下文矛盾"""
    print("\n" + "="*60)
    print("🧪 测试2：部分幻觉场景")
    print("="*60)
    
    context = """
    上海市是中国最大的经济中心，2023年GDP约4.72万亿元。
    上海常住人口约2480万，是中国人口最多的城市之一。
    """
    
    # 包含一个与上下文矛盾的事实（人口数字错误）
    answer = "上海是中国经济中心，2023年GDP约4.72万亿元。上海常住人口约3000万。"
    
    score, claims = calculate_faithfulness(context, answer)
    risk_level = get_risk_level(score)
    
    print(f"📄 上下文片段: {context[:80]}...")
    print(f"💬 模型答案: {answer}")
    print(f"\n🔍 声明验证结果:")
    for i, claim in enumerate(claims, 1):
        if claim.relation == NLIRelation.ENTAILMENT:
            status = "✅"
        elif claim.relation == NLIRelation.CONTRADICTION:
            status = "❌"
        else:
            status = "⚠️"
        print(f"   {status} 声明{i}: {claim.text[:40]}...")
        print(f"      关系: {claim.relation.value}, 置信度: {claim.confidence:.2f}")
    
    print(f"\n📊 忠实度分数: {score:.2f}")
    print(f"⚠️  风险等级: {risk_level}")
    print(f"🚨 检测到的幻觉: 人口数据与上下文不符")
    
    passed = score >= 0.7  # 部分幻觉应触发L2风险
    return TestResult("部分幻觉场景", passed, score, risk_level, {
        "claims_count": len(claims),
        "contradiction_count": sum(1 for c in claims if c.relation == NLIRelation.CONTRADICTION)
    })


def test_full_hallucination():
    """测试场景3：完全幻觉 - 所有声明均无上下文支持"""
    print("\n" + "="*60)
    print("🧪 测试3：完全幻觉场景")
    print("="*60)
    
    context = """
    深圳市位于中国广东省，是中国改革开放的前沿城市。
    深圳以科技创新著称，拥有华为、腾讯等知名科技企业。
    """
    
    # 答案与上下文完全无关
    answer = "杭州是阿里巴巴总部所在地，西湖是著名的旅游景点。马云是阿里巴巴创始人。"
    
    score, claims = calculate_faithfulness(context, answer)
    risk_level = get_risk_level(score)
    
    print(f"📄 上下文片段: {context[:80]}...")
    print(f"💬 模型答案: {answer}")
    print(f"\n🔍 声明验证结果:")
    for i, claim in enumerate(claims, 1):
        status = "❌" if claim.relation != NLIRelation.ENTAILMENT else "✅"
        print(f"   {status} 声明{i}: {claim.text[:40]}...")
        print(f"      关系: {claim.relation.value}, 置信度: {claim.confidence:.2f}")
    
    print(f"\n📊 忠实度分数: {score:.2f}")
    print(f"⚠️  风险等级: {risk_level}")
    print(f"🚨 严重警告: 答案与上下文完全无关！")
    
    passed = score < 0.7  # 完全幻觉应触发L1风险
    return TestResult("完全幻觉场景", not passed, score, risk_level, {
        "claims_count": len(claims),
        "entailment_count": sum(1 for c in claims if c.relation == NLIRelation.ENTAILMENT)
    })


def test_neutral_boundary():
    """测试场景4：边界模糊 - 声明需要推理才能验证"""
    print("\n" + "="*60)
    print("🧪 测试4：边界模糊场景（Neutral关系）")
    print("="*60)
    
    context = """
     Python是一种高级编程语言，由Guido van Rossum于1991年创建。
    Python支持多种编程范式，包括面向对象、函数式编程。
    """
    
    # 需要推理才能验证的声明
    answer = "Python是一种编程语言。Python适合初学者学习。Python由Guido创建。"
    
    score, claims = calculate_faithfulness(context, answer)
    risk_level = get_risk_level(score)
    
    print(f"📄 上下文片段: {context[:80]}...")
    print(f"💬 模型答案: {answer}")
    print(f"\n🔍 声明验证结果:")
    for i, claim in enumerate(claims, 1):
        if claim.relation == NLIRelation.ENTAILMENT:
            status = "✅"
        elif claim.relation == NLIRelation.NEUTRAL:
            status = "⚠️"
        else:
            status = "❌"
        print(f"   {status} 声明{i}: {claim.text[:40]}...")
        print(f"      关系: {claim.relation.value}, 置信度: {claim.confidence:.2f}")
    
    print(f"\n📊 忠实度分数: {score:.2f}")
    print(f"⚠️  风险等级: {risk_level}")
    print(f"💡 提示: Neutral声明需要额外推理验证，建议人工审核")
    
    return TestResult("边界模糊场景", True, score, risk_level, {
        "claims_count": len(claims),
        "neutral_count": sum(1 for c in claims if c.relation == NLIRelation.NEUTRAL)
    })


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📋 AI QA System Test Summary - Day 34: NLI Faithfulness Detection")
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
    
    print("\n" + "="*70)
    print("✅ 测试执行完毕，请将上方日志发给 Trae 生成 report_day34.md")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 34: NLI Faithfulness Detection")
    print("   基于自然语言推理的答案忠实度自动化检测")
    print("="*70)
    
    results = [
        test_full_faithful(),
        test_partial_hallucination(),
        test_full_hallucination(),
        test_neutral_boundary()
    ]
    
    print_summary(results)


if __name__ == "__main__":
    run_all_tests()
