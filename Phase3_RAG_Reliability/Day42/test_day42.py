"""
Day 42: 父文档检索器与上下文压缩效率
目标：最小可用，突出风险验证，代码要足够精简
测试架构师视角：验证父文档检索器策略在平衡检索精度与上下文完整性方面的效果
难度级别：实战
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
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
class ParentDoc:
    """父级文档"""
    doc_id: str
    title: str
    content: str
    key_info: List[str]  # 关键信息点
    child_chunks: List['ChildChunk'] = field(default_factory=list)


@dataclass
class ChildChunk:
    """子块（用于检索）"""
    chunk_id: str
    content: str
    parent_id: str  # 所属父文档ID
    relevance_score: float  # 与查询的相关性


@dataclass
class Question:
    """测试问题"""
    text: str
    required_info: List[str]  # 回答问题所需的关键信息
    optimal_parent: str  # 最优父文档ID


def create_test_corpus() -> List[ParentDoc]:
    """创建测试文档库"""
    corpus = [
        ParentDoc(
            doc_id="parent_1",
            title="产品A用户手册",
            content="""产品A是一款高性能智能设备。主要特性包括：
            1. 处理器：采用最新8核芯片，运行速度快
            2. 电池：5000mAh大容量，续航24小时
            3. 屏幕：6.5英寸OLED显示屏
            4. 存储：128GB/256GB可选
            注意事项：请勿在潮湿环境中使用。""",
            key_info=["8核芯片", "5000mAh电池", "6.5英寸OLED", "128GB/256GB", "勿在潮湿环境使用"]
        ),
        ParentDoc(
            doc_id="parent_2",
            title="产品B技术规格",
            content="""产品B技术规格详情：
            - 处理器：6核中端芯片
            - 电池：4000mAh，续航18小时
            - 屏幕：6.1英寸LCD显示屏
            - 重量：180g，轻薄设计
            保修政策：整机保修1年，电池保修6个月。""",
            key_info=["6核芯片", "4000mAh电池", "6.1英寸LCD", "180g", "保修1年"]
        ),
        ParentDoc(
            doc_id="parent_3",
            title="售后服务政策",
            content="""售后服务政策说明：
            1. 退换货：7天无理由退货，15天换货
            2. 维修：全国联保，免费上门取件
            3. 客服：7x24小时在线支持
            4. 延保：可购买延保服务，最长延至3年
            特别提示：人为损坏不在保修范围内。""",
            key_info=["7天退货", "15天换货", "全国联保", "7x24客服", "人为损坏不保"]
        ),
        ParentDoc(
            doc_id="parent_4",
            title="产品价格与促销",
            content="""产品价格信息：
            - 产品A：标准版2999元，高配版3999元
            - 产品B：标准版1999元，高配版2499元
            当前促销活动：
            - 满3000减300
            - 以旧换新最高抵扣500元
            - 分期付款0利息（6期内）""",
            key_info=["产品A 2999/3999元", "产品B 1999/2499元", "满3000减300", "以旧换新", "分期0利息"]
        )
    ]
    
    # 为每个父文档创建子块
    for parent in corpus:
        chunks = parent.content.split('\n')
        parent.child_chunks = [
            ChildChunk(
                chunk_id=f"{parent.doc_id}_chunk_{i}",
                content=chunk.strip(),
                parent_id=parent.doc_id,
                relevance_score=0.0  # 将在检索时计算
            )
            for i, chunk in enumerate(chunks) if chunk.strip()
        ]
    
    return corpus


def mock_semantic_search(corpus: List[ParentDoc], query: str, top_k: int = 3) -> List[ChildChunk]:
    """模拟语义检索：返回最相关的子块"""
    all_chunks = []
    for parent in corpus:
        for chunk in parent.child_chunks:
            # 模拟相关性计算（基于关键词匹配）
            query_words = set(query.lower().split())
            chunk_words = set(chunk.content.lower().split())
            overlap = len(query_words & chunk_words)
            chunk.relevance_score = min(1.0, overlap / max(1, len(query_words)) * 2)
            all_chunks.append(chunk)
    
    # 按相关性排序，返回Top-K
    all_chunks.sort(key=lambda x: x.relevance_score, reverse=True)
    return all_chunks[:top_k]


def mock_parent_retrieval(child_chunks: List[ChildChunk], corpus: List[ParentDoc]) -> List[ParentDoc]:
    """模拟父文档召回：根据子块召回父文档"""
    parent_ids = set(chunk.parent_id for chunk in child_chunks)
    
    # 模拟召回准确率（90%准确率）
    parents = []
    for pid in parent_ids:
        if random.random() < 0.9:  # 90%概率正确召回
            parent = next((p for p in corpus if p.doc_id == pid), None)
            if parent:
                parents.append(parent)
        else:
            # 10%概率召回错误（模拟召回错误）
            wrong_parent = random.choice([p for p in corpus if p.doc_id != pid])
            parents.append(wrong_parent)
    
    return parents


def mock_llm_generate(context: str, question: Question) -> Dict[str, Any]:
    """模拟LLM生成答案"""
    # 计算信息覆盖率
    covered_info = []
    for info in question.required_info:
        if info.lower() in context.lower():
            covered_info.append(info)
    
    coverage = len(covered_info) / len(question.required_info) if question.required_info else 0
    
    # 生成答案
    if coverage > 0.7:
        answer = f"根据文档信息，{'；'.join(covered_info[:3])}"
    elif coverage > 0.3:
        answer = f"部分信息：{'；'.join(covered_info[:2])}（信息不完整）"
    else:
        answer = "无法从提供的文档中找到完整答案。"
    
    return {
        "answer": answer,
        "covered_info": covered_info,
        "coverage": coverage,
        "context_length": len(context)
    }


def test_parent_document_retrieval_accuracy() -> TestResult:
    """
    测试1: 父文档召回准确性测试
    验证：检索子块后，能否正确召回所属父文档
    """
    print("\n" + "="*60)
    print("🧪 测试1: 父文档召回准确性测试")
    print("="*60)
    print("测试目的：验证父文档召回的准确性")
    
    corpus = create_test_corpus()
    
    test_queries = [
        Question("产品A的电池容量是多少？", ["5000mAh"], "parent_1"),
        Question("保修政策是什么？", ["保修1年"], "parent_2"),
        Question("如何申请退货？", ["7天无理由退货"], "parent_3"),
        Question("产品B的价格是多少？", ["1999元"], "parent_4"),
    ]
    
    correct_retrievals = 0
    total_tests = len(test_queries)
    
    print("\n📊 召回准确性测试:")
    print("-" * 60)
    
    for question in test_queries:
        # 检索子块
        child_chunks = mock_semantic_search(corpus, question.text, top_k=2)
        
        # 召回父文档
        retrieved_parents = mock_parent_retrieval(child_chunks, corpus)
        
        # 检查是否正确召回
        correct = any(p.doc_id == question.optimal_parent for p in retrieved_parents)
        if correct:
            correct_retrievals += 1
        
        status = "✅ 正确" if correct else "❌ 错误"
        print(f"   查询: {question.text[:20]}... | 期望: {question.optimal_parent} | {status}")
    
    accuracy = correct_retrievals / total_tests
    
    print(f"\n📈 召回准确性: {correct_retrievals}/{total_tests} ({accuracy:.1%})")
    
    # 评估：召回准确率应不低于80%
    passed = accuracy >= 0.8
    score = accuracy * 100
    
    risk = RiskLevel.L2 if accuracy < 0.8 else RiskLevel.L3
    
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="父文档召回准确性测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={
            "召回准确率": accuracy,
            "正确召回数": correct_retrievals,
            "总测试数": total_tests
        }
    )


def test_three_strategy_comparison() -> TestResult:
    """
    测试2: 三种策略对比测试
    对比小片段、大段落、父文档三种策略的答案质量
    """
    print("\n" + "="*60)
    print("🧪 测试2: 三种策略对比测试")
    print("="*60)
    print("测试目的：对比不同检索策略的效果")
    
    corpus = create_test_corpus()
    question = Question(
        "产品A的性能和价格是多少？保修政策如何？",
        ["8核芯片", "2999元", "7天退货"],
        "parent_1"
    )
    
    # 策略A：小片段策略（只使用检索到的子块）
    print("\n📊 策略A: 小片段策略")
    child_chunks = mock_semantic_search(corpus, question.text, top_k=3)
    small_context = "\n".join([c.content for c in child_chunks])
    result_small = mock_llm_generate(small_context, question)
    print(f"   上下文长度: {result_small['context_length']}字符")
    print(f"   信息覆盖率: {result_small['coverage']:.1%}")
    
    # 策略B：大段落策略（使用所有父文档的完整内容）
    print("\n📊 策略B: 大段落策略")
    large_context = "\n\n".join([p.content for p in corpus])
    result_large = mock_llm_generate(large_context, question)
    print(f"   上下文长度: {result_large['context_length']}字符")
    print(f"   信息覆盖率: {result_large['coverage']:.1%}")
    
    # 策略C：父文档策略（检索子块+召回父文档）
    print("\n📊 策略C: 父文档策略")
    retrieved_parents = mock_parent_retrieval(child_chunks, corpus)
    parent_context = "\n\n".join([p.content for p in retrieved_parents])
    result_parent = mock_llm_generate(parent_context, question)
    print(f"   召回父文档: {[p.doc_id for p in retrieved_parents]}")
    print(f"   上下文长度: {result_parent['context_length']}字符")
    print(f"   信息覆盖率: {result_parent['coverage']:.1%}")
    
    # 对比分析
    print("\n📈 策略对比:")
    print("-" * 60)
    print(f"{'策略':<15} {'上下文长度':<15} {'覆盖率':<15} {'效率':<10}")
    print("-" * 60)
    
    strategies = [
        ("小片段", result_small),
        ("大段落", result_large),
        ("父文档", result_parent)
    ]
    
    for name, result in strategies:
        efficiency = result['coverage'] / (result['context_length'] / 1000 + 1)  # 覆盖率/千字符
        print(f"{name:<15} {result['context_length']:<15} {result['coverage']:<15.1%} {efficiency:<10.3f}")
    
    # 评估：父文档策略应在覆盖率和效率上取得平衡
    parent_coverage = result_parent['coverage']
    small_coverage = result_small['coverage']
    
    # 父文档策略应优于或等于小片段策略
    passed = parent_coverage >= small_coverage
    score = parent_coverage * 100
    
    risk = RiskLevel.L2 if parent_coverage < small_coverage else RiskLevel.L3
    
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="三种策略对比测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={
            "小片段覆盖率": small_coverage,
            "大段落覆盖率": result_large['coverage'],
            "父文档覆盖率": parent_coverage,
            "父文档vs小片段": parent_coverage - small_coverage
        }
    )


def test_context_compression_efficiency() -> TestResult:
    """
    测试3: 上下文压缩效率测试
    测试不同压缩比例下的信息保留率
    """
    print("\n" + "="*60)
    print("🧪 测试3: 上下文压缩效率测试")
    print("="*60)
    print("测试目的：找出最佳压缩平衡点")
    
    corpus = create_test_corpus()
    parent = corpus[0]  # 使用产品A手册
    
    question = Question("产品A的主要特性和注意事项", 
                       parent.key_info[:4], "parent_1")
    
    # 不同压缩比例
    compression_ratios = [1.0, 0.7, 0.5, 0.3, 0.1]
    
    print("\n📊 不同压缩比例下的信息保留:")
    print("-" * 60)
    print(f"{'压缩比例':<12} {'压缩后长度':<15} {'信息保留率':<15} {'质量评分':<10}")
    print("-" * 60)
    
    results = []
    original_length = len(parent.content)
    
    for ratio in compression_ratios:
        # 模拟压缩：按比例保留内容
        compressed_length = int(original_length * ratio)
        compressed_content = parent.content[:compressed_length]
        
        # 计算信息保留率
        retained_info = []
        for info in parent.key_info:
            if info.lower() in compressed_content.lower():
                retained_info.append(info)
        
        retention_rate = len(retained_info) / len(parent.key_info)
        quality_score = retention_rate * ratio  # 质量 = 保留率 × 压缩比
        
        results.append((ratio, retention_rate, quality_score, compressed_length))
        
        print(f"{ratio:<12.0%} {compressed_length:<15} {retention_rate:<15.1%} {quality_score:<10.3f}")
    
    # 找出最佳压缩点（质量评分最高）
    best_compression = max(results, key=lambda x: x[2])
    
    print(f"\n📈 最佳压缩点:")
    print(f"   压缩比例: {best_compression[0]:.0%}")
    print(f"   信息保留率: {best_compression[1]:.1%}")
    print(f"   质量评分: {best_compression[2]:.3f}")
    
    # 评估：50%压缩下信息保留率应不低于70%
    retention_at_50 = next(r[1] for r in results if r[0] == 0.5)
    passed = retention_at_50 >= 0.7
    score = retention_at_50 * 100
    
    risk = RiskLevel.L2 if retention_at_50 < 0.7 else RiskLevel.L3
    
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="上下文压缩效率测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={
            "50%压缩保留率": retention_at_50,
            "最佳压缩比例": best_compression[0],
            "最佳质量评分": best_compression[2]
        }
    )


def test_end_to_end_integration() -> TestResult:
    """
    测试4: 端到端综合测试
    模拟真实RAG场景，综合评估父文档检索器效果
    """
    print("\n" + "="*60)
    print("🧪 测试4: 端到端综合测试")
    print("="*60)
    print("测试目的：综合评估父文档检索器在真实场景下的表现")
    
    corpus = create_test_corpus()
    
    # 复杂查询场景
    complex_questions = [
        {
            "question": Question(
                "产品A和产品B的主要区别是什么？",
                ["8核芯片", "6核芯片", "5000mAh", "4000mAh", "OLED", "LCD"],
                "parent_1,parent_2"
            ),
            "requires_multi_parent": True
        },
        {
            "question": Question(
                "购买产品A后，如果出现问题如何售后？",
                ["7天退货", "15天换货", "全国联保", "人为损坏不保"],
                "parent_3"
            ),
            "requires_multi_parent": False
        },
        {
            "question": Question(
                "产品A高配版多少钱？有什么促销？",
                ["3999元", "满3000减300", "以旧换新", "分期0利息"],
                "parent_4"
            ),
            "requires_multi_parent": False
        }
    ]
    
    print("\n📊 端到端场景测试:")
    print("-" * 70)
    
    total_coverage = 0
    total_parents_recalled = 0
    
    for i, scenario in enumerate(complex_questions, 1):
        question = scenario["question"]
        
        print(f"\n场景{i}: {question.text[:30]}...")
        
        # 检索子块
        child_chunks = mock_semantic_search(corpus, question.text, top_k=3)
        
        # 召回父文档
        retrieved_parents = mock_parent_retrieval(child_chunks, corpus)
        
        # 生成上下文
        parent_context = "\n\n".join([p.content for p in retrieved_parents])
        
        # 生成答案
        result = mock_llm_generate(parent_context, question)
        
        print(f"   召回父文档: {[p.doc_id for p in retrieved_parents]}")
        print(f"   信息覆盖率: {result['coverage']:.1%}")
        
        total_coverage += result['coverage']
        total_parents_recalled += len(retrieved_parents)
    
    avg_coverage = total_coverage / len(complex_questions)
    avg_parents = total_parents_recalled / len(complex_questions)
    
    print(f"\n📈 综合评估:")
    print(f"   平均信息覆盖率: {avg_coverage:.1%}")
    print(f"   平均召回父文档数: {avg_parents:.1f}")
    
    # 评估：平均覆盖率应不低于75%
    passed = avg_coverage >= 0.75
    score = avg_coverage * 100
    
    risk = RiskLevel.L2 if avg_coverage < 0.75 else RiskLevel.L3
    
    print(f"\n✅ 测试结果: {'通过' if passed else '未通过'} | 风险等级: {risk.value}")
    
    return TestResult(
        name="端到端综合测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={
            "平均覆盖率": avg_coverage,
            "平均召回文档数": avg_parents,
            "测试场景数": len(complex_questions)
        }
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 Day 42 测试汇总报告 - 父文档检索器与上下文压缩效率")
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
        print("   ⚠️ 父文档检索器效果不佳，建议优化召回策略")
    elif avg_score < 85:
        print("   ⚡ 父文档检索器表现尚可，建议调优压缩参数")
    else:
        print("   ✅ 父文档检索器表现良好，可有效平衡精度与上下文")
    
    if l1_count > 0:
        print(f"   🚨 发现{l1_count}个阻断性风险，需要立即处理")
    if l2_count > 0:
        print(f"   ⚠️ 发现{l2_count}个高优先级风险，建议优先处理")
    
    print("\n🔧 优化建议:")
    print("   1. 优化子块切分策略，提高检索精度")
    print("   2. 实施父文档去重，避免重复召回")
    print("   3. 根据查询复杂度动态调整召回父文档数量")
    print("   4. 结合上下文压缩，提高Token使用效率")
    
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 42: 父文档检索器与上下文压缩效率")
    print("="*70)
    print("测试架构师视角：验证父文档检索器在平衡检索精度与上下文完整性方面的效果")
    
    results = [
        test_parent_document_retrieval_accuracy(),
        test_three_strategy_comparison(),
        test_context_compression_efficiency(),
        test_end_to_end_integration()
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
