"""
Day 40: 上下文信息利用不足检测
目标：最小可用，突出风险验证，代码要足够精简
测试架构师视角：检测LLM是否充分利用了检索提供的上下文信息
难度级别：基础
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


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
    key_info: List[str]  # 文档中的关键信息点
    position: int  # 在上下文中的位置


@dataclass
class Question:
    """测试问题"""
    text: str
    required_info: List[str]  # 回答问题所需的关键信息
    expected_docs: List[str]  # 期望引用的文档ID


def mock_llm_generate(context_docs: List[ContextDoc], question: Question) -> Dict[str, Any]:
    """
    模拟LLM生成答案，基于上下文利用率的场景返回不同质量的结果
    
    模拟真实场景：
    - 上下文越长，利用率越低
    - 位置靠后的文档被引用的概率降低
    - 多跳问题容易遗漏信息
    """
    total_key_info = sum(len(doc.key_info) for doc in context_docs)
    
    # 模拟利用率衰减：每增加一个文档，利用率下降
    base_utilization = max(0.3, 1.0 - (len(context_docs) - 1) * 0.15)
    
    # 位置偏见：前面的文档更容易被利用
    utilized_docs = []
    covered_info = []
    
    for i, doc in enumerate(context_docs):
        # 位置越靠后，被利用的概率越低
        position_factor = max(0.2, 1.0 - i * 0.15)
        if i == 0:  # 第一个文档总是被利用
            doc_utilized = True
        else:
            doc_utilized = base_utilization * position_factor > 0.5
        
        if doc_utilized:
            utilized_docs.append(doc.doc_id)
            # 即使文档被利用，也可能只利用部分关键信息
            info_coverage = max(0.5, base_utilization * position_factor)
            covered_count = int(len(doc.key_info) * info_coverage)
            covered_info.extend(doc.key_info[:covered_count])
    
    # 生成答案（模拟）
    answer = f"基于文档信息，{question.text}的答案是："
    if covered_info:
        answer += " " + "；".join(covered_info[:3])  # 最多显示3个信息点
    else:
        answer += " 根据现有信息无法完整回答。"
    
    return {
        "answer": answer,
        "utilized_docs": utilized_docs,
        "covered_info": covered_info,
        "context_utilization_rate": len(utilized_docs) / len(context_docs) if context_docs else 0,
        "info_coverage_rate": len(set(covered_info) & set(question.required_info)) / len(question.required_info) if question.required_info else 0
    }


def calculate_context_utilization(context_docs: List[ContextDoc], utilized_docs: List[str]) -> float:
    """计算上下文利用率"""
    if not context_docs:
        return 0.0
    return len(utilized_docs) / len(context_docs)


def calculate_info_coverage(required_info: List[str], covered_info: List[str]) -> float:
    """计算信息覆盖率"""
    if not required_info:
        return 1.0
    covered_set = set(covered_info)
    required_set = set(required_info)
    return len(covered_set & required_set) / len(required_set)


def test_single_vs_multi_doc_utilization() -> TestResult:
    """
    测试1: 单文档 vs 多文档利用率对比
    验证：文档数量增加时，利用率是否显著下降
    """
    print("\n" + "="*60)
    print("🧪 测试1: 单文档 vs 多文档利用率对比")
    print("="*60)
    print("测试目的：验证文档数量对上下文利用率的影响")
    
    # 单文档场景
    single_doc = [
        ContextDoc("doc1", "产品A的价格是100元，支持7天无理由退货。", 
                   ["价格100元", "7天无理由退货"], 0)
    ]
    question = Question("产品A的价格和退货政策是什么？", 
                       ["价格100元", "7天无理由退货"], ["doc1"])
    
    result_single = mock_llm_generate(single_doc, question)
    utilization_single = result_single["context_utilization_rate"]
    coverage_single = result_single["info_coverage_rate"]
    
    print(f"\n📄 单文档场景:")
    print(f"   文档数: 1")
    print(f"   上下文利用率: {utilization_single:.1%}")
    print(f"   信息覆盖率: {coverage_single:.1%}")
    
    # 多文档场景（5个文档，只有1个相关）
    multi_docs = [
        ContextDoc("doc1", "产品A的价格是100元，支持7天无理由退货。", 
                   ["价格100元", "7天无理由退货"], 0),
        ContextDoc("doc2", "产品B的价格是200元，支持30天换货。", 
                   ["价格200元", "30天换货"], 1),
        ContextDoc("doc3", "公司成立于2020年，总部位于北京。", 
                   ["成立于2020年", "总部北京"], 2),
        ContextDoc("doc4", "客服电话：400-123-4567，工作时间9:00-18:00。", 
                   ["客服电话", "工作时间"], 3),
        ContextDoc("doc5", "配送范围覆盖全国，一般3-5天送达。", 
                   ["全国配送", "3-5天送达"], 4),
    ]
    
    result_multi = mock_llm_generate(multi_docs, question)
    utilization_multi = result_multi["context_utilization_rate"]
    coverage_multi = result_multi["info_coverage_rate"]
    
    print(f"\n📚 多文档场景:")
    print(f"   文档数: 5")
    print(f"   上下文利用率: {utilization_multi:.1%}")
    print(f"   信息覆盖率: {coverage_multi:.1%}")
    
    # 评估
    utilization_drop = utilization_single - utilization_multi
    coverage_drop = coverage_single - coverage_multi
    
    print(f"\n📊 对比分析:")
    print(f"   利用率下降: {utilization_drop:.1%}")
    print(f"   覆盖率下降: {coverage_drop:.1%}")
    
    # 判断标准：多文档场景下利用率不应低于50%，覆盖率不应低于70%
    passed = utilization_multi >= 0.5 and coverage_multi >= 0.7
    score = (utilization_multi * 0.5 + coverage_multi * 0.5) * 100
    
    risk = RiskLevel.L2 if utilization_multi < 0.5 or coverage_multi < 0.7 else RiskLevel.L3
    
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="单文档vs多文档利用率对比",
        passed=passed,
        score=score,
        risk_level=risk,
        details={
            "单文档利用率": utilization_single,
            "多文档利用率": utilization_multi,
            "利用率下降": utilization_drop,
            "覆盖率下降": coverage_drop
        }
    )


def test_key_info_position_sensitivity() -> TestResult:
    """
    测试2: 关键信息位置敏感性
    验证：关键信息放在上下文不同位置时，被利用的概率差异
    """
    print("\n" + "="*60)
    print("🧪 测试2: 关键信息位置敏感性测试")
    print("="*60)
    print("测试目的：验证LLM是否存在'Lost in the Middle'问题")
    
    key_fact = "⚠️ 重要警告：该产品不适合孕妇使用"
    question = Question("使用该产品有什么注意事项？", 
                       ["不适合孕妇使用"], ["doc_warning"])
    
    # 创建填充文档
    filler_docs = [
        ContextDoc(f"filler_{i}", f"这是填充文档{i}的内容，包含一些普通信息。", 
                   [f"普通信息{i}"], i) for i in range(8)
    ]
    
    positions = {
        "开头": 0,
        "中间": 4,
        "结尾": 8
    }
    
    results = {}
    
    for pos_name, pos_idx in positions.items():
        # 将关键文档插入指定位置
        docs = filler_docs.copy()
        warning_doc = ContextDoc("doc_warning", key_fact, ["不适合孕妇使用"], pos_idx)
        docs.insert(pos_idx, warning_doc)
        
        result = mock_llm_generate(docs, question)
        covered = "不适合孕妇使用" in result["covered_info"]
        results[pos_name] = covered
        
        status = "✅ 已引用" if covered else "❌ 未引用"
        print(f"\n📍 关键信息放在{pos_name} (位置{pos_idx}): {status}")
    
    # 评估：所有位置都应该被引用
    all_covered = all(results.values())
    coverage_count = sum(1 for v in results.values() if v)
    score = (coverage_count / len(positions)) * 100
    
    risk = RiskLevel.L2 if coverage_count < len(positions) else RiskLevel.L3
    
    print(f"\n📊 位置敏感性分析:")
    print(f"   位置覆盖率: {coverage_count}/{len(positions)} ({score:.0f}%)")
    
    passed = coverage_count == len(positions)
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="关键信息位置敏感性测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details=results
    )


def test_multi_hop_reasoning() -> TestResult:
    """
    测试3: 多跳信息综合测试
    验证：需要综合多个文档信息才能回答的问题，模型是否能完整利用
    """
    print("\n" + "="*60)
    print("🧪 测试3: 多跳信息综合测试")
    print("="*60)
    print("测试目的：验证LLM是否能综合多个文档的信息回答复杂问题")
    
    # 创建需要多跳推理的文档
    docs = [
        ContextDoc("doc_product", 
                   "产品X是由公司Y生产的智能设备。", 
                   ["产品X", "公司Y生产"], 0),
        ContextDoc("doc_company", 
                   "公司Y的总部位于上海，成立于2015年。", 
                   ["总部上海", "成立于2015年"], 1),
        ContextDoc("doc_warranty", 
                   "产品X提供2年质保服务，由公司Y的售后团队负责。", 
                   ["2年质保", "售后团队负责"], 2),
    ]
    
    # 需要综合多个文档信息的问题
    question = Question("产品X的生产商是哪家公司？这家公司在哪里成立？质保多久？", 
                       ["公司Y", "成立于2015年", "2年质保"], 
                       ["doc_product", "doc_company", "doc_warranty"])
    
    result = mock_llm_generate(docs, question)
    
    print(f"\n📚 提供的文档:")
    for doc in docs:
        print(f"   [{doc.doc_id}] {doc.content[:30]}...")
    
    print(f"\n❓ 问题: {question.text}")
    print(f"\n📝 生成的答案: {result['answer'][:100]}...")
    
    print(f"\n📊 利用率分析:")
    print(f"   引用的文档: {result['utilized_docs']}")
    print(f"   期望引用的文档: {question.expected_docs}")
    print(f"   上下文利用率: {result['context_utilization_rate']:.1%}")
    print(f"   信息覆盖率: {result['info_coverage_rate']:.1%}")
    
    # 检查是否引用了所有需要的文档
    expected_set = set(question.expected_docs)
    utilized_set = set(result['utilized_docs'])
    doc_coverage = len(expected_set & utilized_set) / len(expected_set)
    
    print(f"\n📋 文档引用完整性: {doc_coverage:.1%}")
    
    # 评估标准
    passed = doc_coverage >= 0.8 and result['info_coverage_rate'] >= 0.7
    score = ((doc_coverage + result['info_coverage_rate']) / 2) * 100
    
    risk = RiskLevel.L1 if doc_coverage < 0.6 else (RiskLevel.L2 if doc_coverage < 0.8 else RiskLevel.L3)
    
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="多跳信息综合测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={
            "文档引用完整性": doc_coverage,
            "信息覆盖率": result['info_coverage_rate'],
            "引用的文档": result['utilized_docs'],
            "期望的文档": question.expected_docs
        }
    )


def test_information_density_stress() -> TestResult:
    """
    测试4: 信息密度压力测试
    验证：在高密度信息场景下，模型的利用能力
    """
    print("\n" + "="*60)
    print("🧪 测试4: 信息密度压力测试")
    print("="*60)
    print("测试目的：验证LLM在高密度信息场景下的处理能力")
    
    # 低密度场景：3个文档，3个关键信息
    low_density_docs = [
        ContextDoc(f"low_{i}", f"信息{i+1}: 这是第{i+1}条独立信息。", 
                   [f"信息{i+1}"], i) for i in range(3)
    ]
    
    # 高密度场景：3个文档，每篇包含多个关键信息
    high_density_docs = [
        ContextDoc("high_1", 
                   "信息1: 产品价格100元。信息2: 支持7天退货。信息3: 包邮。",
                   ["价格100元", "7天退货", "包邮"], 0),
        ContextDoc("high_2", 
                   "信息4: 质保2年。信息5: 全国联保。信息6: 24小时客服。",
                   ["质保2年", "全国联保", "24小时客服"], 1),
        ContextDoc("high_3", 
                   "信息7: 支持分期付款。信息8: 信用卡优惠。信息9: 会员折扣。",
                   ["分期付款", "信用卡优惠", "会员折扣"], 2),
    ]
    
    question_low = Question("请列出所有信息。", 
                           [f"信息{i+1}" for i in range(3)], 
                           [f"low_{i}" for i in range(3)])
    
    question_high = Question("请列出所有产品信息。", 
                            ["价格100元", "7天退货", "包邮", "质保2年", "全国联保", 
                             "24小时客服", "分期付款", "信用卡优惠", "会员折扣"],
                            ["high_1", "high_2", "high_3"])
    
    result_low = mock_llm_generate(low_density_docs, question_low)
    result_high = mock_llm_generate(high_density_docs, question_high)
    
    print(f"\n📊 低密度场景 (3文档×1信息):")
    print(f"   上下文利用率: {result_low['context_utilization_rate']:.1%}")
    print(f"   信息覆盖率: {result_low['info_coverage_rate']:.1%}")
    
    print(f"\n📊 高密度场景 (3文档×3信息):")
    print(f"   上下文利用率: {result_high['context_utilization_rate']:.1%}")
    print(f"   信息覆盖率: {result_high['info_coverage_rate']:.1%}")
    
    coverage_drop = result_low['info_coverage_rate'] - result_high['info_coverage_rate']
    
    print(f"\n📉 信息密度影响:")
    print(f"   覆盖率下降: {coverage_drop:.1%}")
    
    # 评估：高密度场景下覆盖率不应低于60%
    passed = result_high['info_coverage_rate'] >= 0.6
    score = result_high['info_coverage_rate'] * 100
    
    risk = RiskLevel.L2 if result_high['info_coverage_rate'] < 0.7 else RiskLevel.L3
    
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="信息密度压力测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={
            "低密度覆盖率": result_low['info_coverage_rate'],
            "高密度覆盖率": result_high['info_coverage_rate'],
            "覆盖率下降": coverage_drop
        }
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 Day 40 测试汇总报告 - 上下文信息利用不足检测")
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
        print("   ⚠️ 上下文利用率存在严重问题，建议优化检索策略和提示工程")
    elif avg_score < 85:
        print("   ⚡ 上下文利用率尚可，但仍有改进空间")
    else:
        print("   ✅ 上下文利用率表现良好")
    
    if l1_count > 0:
        print(f"   🚨 发现{l1_count}个阻断性风险，需要立即处理")
    if l2_count > 0:
        print(f"   ⚠️ 发现{l2_count}个高优先级风险，建议优先处理")
    
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 40: 上下文信息利用不足检测")
    print("="*70)
    print("测试架构师视角：检测LLM是否充分利用检索提供的上下文信息")
    
    results = [
        test_single_vs_multi_doc_utilization(),
        test_key_info_position_sensitivity(),
        test_multi_hop_reasoning(),
        test_information_density_stress()
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
