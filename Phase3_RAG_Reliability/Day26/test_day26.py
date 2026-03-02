"""
Day 26: 语义分块策略评估（进阶篇）
目标：最小可用，突出风险验证，代码要足够精简
测试架构师视角：验证语义分块的阈值敏感性和性能开销
难度级别：进阶
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
import re
import time


@dataclass
class Chunk:
    """分块结果"""
    content: str
    index: int
    sentences: List[str]


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: str
    details: str


def mock_embedding(text: str) -> List[float]:
    """
    模拟embedding计算
    基于文本特征生成模拟向量（实际场景使用真实embedding模型）
    """
    # 模拟延迟
    time.sleep(0.001)
    
    # 基于文本内容生成确定性向量
    hash_val = hash(text) % 10000
    vector = [
        (hash_val % 100) / 100,
        ((hash_val // 100) % 100) / 100,
        ((hash_val // 10000) % 100) / 100,
    ]
    return vector


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """计算余弦相似度"""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def split_to_sentences(text: str) -> List[str]:
    """将文本分割为句子"""
    # 支持中英文句子分隔符
    sentences = re.split(r'([。！？.!?]\s*)', text)
    # 合并分隔符和句子
    result = []
    i = 0
    while i < len(sentences):
        if i + 1 < len(sentences):
            result.append(sentences[i] + sentences[i + 1])
            i += 2
        else:
            if sentences[i].strip():
                result.append(sentences[i])
            i += 1
    return [s.strip() for s in result if s.strip()]


def semantic_chunk(text: str, threshold: float = 0.8) -> Tuple[List[Chunk], float]:
    """
    语义分块实现
    基于句子间语义相似度进行分块
    返回：(chunks, processing_time_ms)
    """
    start_time = time.time()
    
    sentences = split_to_sentences(text)
    if not sentences:
        return [], 0
    
    # 计算句子embedding
    embeddings = [mock_embedding(s) for s in sentences]
    
    chunks = []
    current_chunk_sentences = [sentences[0]]
    current_chunk_embs = [embeddings[0]]
    
    for i in range(1, len(sentences)):
        # 计算当前句子与chunk中句子的平均相似度
        similarities = [cosine_similarity(embeddings[i], emb) for emb in current_chunk_embs]
        avg_similarity = sum(similarities) / len(similarities)
        
        if avg_similarity >= threshold:
            # 相似度高，加入当前chunk
            current_chunk_sentences.append(sentences[i])
            current_chunk_embs.append(embeddings[i])
        else:
            # 相似度低，创建新chunk
            chunks.append(Chunk(
                content=''.join(current_chunk_sentences),
                index=len(chunks),
                sentences=current_chunk_sentences.copy()
            ))
            current_chunk_sentences = [sentences[i]]
            current_chunk_embs = [embeddings[i]]
    
    # 添加最后一个chunk
    if current_chunk_sentences:
        chunks.append(Chunk(
            content=''.join(current_chunk_sentences),
            index=len(chunks),
            sentences=current_chunk_sentences.copy()
        ))
    
    processing_time = (time.time() - start_time) * 1000
    return chunks, processing_time


def fixed_length_chunk(text: str, chunk_size: int = 100, overlap: int = 20) -> Tuple[List[Chunk], float]:
    """
    固定长度分块（用于对比）
    """
    start_time = time.time()
    
    chunks = []
    start = 0
    index = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        content = text[start:end]
        
        chunks.append(Chunk(
            content=content,
            index=index,
            sentences=[]
        ))
        
        start = end - overlap if end < len(text) else end
        index += 1
        
        if start >= end:
            break
    
    processing_time = (time.time() - start_time) * 1000
    return chunks, processing_time


def calculate_chunk_quality(chunks: List[Chunk], expected_topics: List[str]) -> Dict:
    """
    计算分块质量指标
    """
    # 模拟主题一致性检查
    topic_consistency = 0
    for chunk in chunks:
        chunk_topics = sum(1 for topic in expected_topics if topic in chunk.content)
        if chunk_topics > 0:
            topic_consistency += 1
    
    consistency_rate = (topic_consistency / len(chunks) * 100) if chunks else 0
    
    # 计算块大小方差（越小越好，表示分块均匀）
    sizes = [len(c.content) for c in chunks]
    avg_size = sum(sizes) / len(sizes) if sizes else 0
    variance = sum((s - avg_size) ** 2 for s in sizes) / len(sizes) if sizes else 0
    
    return {
        'consistency_rate': consistency_rate,
        'avg_chunk_size': avg_size,
        'size_variance': variance,
        'num_chunks': len(chunks)
    }


def test_threshold_sensitivity() -> TestResult:
    """
    测试1：阈值敏感性
    扫描不同相似度阈值对分块质量的影响
    """
    print("\n" + "="*60)
    print("🧪 测试1：阈值敏感性扫描")
    print("="*60)
    
    # 构造主题混合的测试文本
    text = """
    人工智能是计算机科学的一个重要分支。它研究如何使计算机模拟人类智能。
    机器学习是人工智能的核心技术之一。深度学习则是机器学习的一个子领域。
    自然语言处理让计算机理解人类语言。计算机视觉让机器看懂图像。
    这些技术正在改变我们的生活方式。未来AI将在更多领域发挥作用。
    """
    
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
    results = []
    
    print(f"\n📄 测试文本长度: {len(text)} 字符")
    print(f"\n� 不同阈值对比:")
    print(f"{'阈值':<10} {'Chunks':<10} {'平均大小':<12} {'处理时间':<12}")
    print("-" * 50)
    
    for threshold in thresholds:
        chunks, proc_time = semantic_chunk(text, threshold)
        sizes = [len(c.content) for c in chunks]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        results.append({
            'threshold': threshold,
            'num_chunks': len(chunks),
            'avg_size': avg_size,
            'time': proc_time
        })
        print(f"{threshold:<10.2f} {len(chunks):<10} {avg_size:<12.0f} {proc_time:<12.1f}ms")
    
    # 分析阈值影响
    min_chunks = min(results, key=lambda x: x['num_chunks'])
    max_chunks = max(results, key=lambda x: x['num_chunks'])
    
    print(f"\n⚠️  阈值影响分析:")
    print(f"   最低阈值({min_chunks['threshold']}) → {min_chunks['num_chunks']} chunks (块过大)")
    print(f"   最高阈值({max_chunks['threshold']}) → {max_chunks['num_chunks']} chunks (可能过度分割)")
    
    # 推荐阈值：平衡chunks数量和大小
    optimal = min(results, key=lambda x: abs(x['num_chunks'] - 3))  # 假设目标3个chunks
    print(f"\n✅ 推荐阈值: {optimal['threshold']} (生成{optimal['num_chunks']}个chunks)")
    
    # 风险评估：阈值范围是否合适
    chunk_variation = max_chunks['num_chunks'] - min_chunks['num_chunks']
    if chunk_variation > 5:
        risk_level = "L2"
        passed = False
        score = 60
    else:
        risk_level = "L3"
        passed = True
        score = 85
    
    details = f"阈值范围{min_chunks['threshold']}-{max_chunks['threshold']}产生{chunk_variation}个chunks差异，推荐{optimal['threshold']}"
    
    return TestResult(
        name="阈值敏感性",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=details
    )


def test_performance_comparison() -> TestResult:
    """
    测试2：性能对比
    对比语义分块和固定长度分块的处理速度
    """
    print("\n" + "="*60)
    print("🧪 测试2：性能对比测试")
    print("="*60)
    
    # 构造不同长度的测试文本
    base_text = "人工智能正在改变我们的世界。机器学习是核心技术。深度学习是子领域。" * 10
    test_cases = [
        ("短文本", base_text[:200]),
        ("中文本", base_text[:500]),
        ("长文本", base_text[:1000]),
    ]
    
    print(f"\n📊 性能对比结果:")
    print(f"{'文本类型':<12} {'语义分块':<15} {'固定长度':<15} {'Overhead':<12}")
    print("-" * 60)
    
    overheads = []
    
    for name, text in test_cases:
        # 语义分块
        _, sem_time = semantic_chunk(text, threshold=0.8)
        
        # 固定长度分块
        _, fix_time = fixed_length_chunk(text, chunk_size=100, overlap=20)
        
        overhead = (sem_time / fix_time) if fix_time > 0 else 999
        overheads.append(overhead)
        
        print(f"{name:<12} {sem_time:<15.2f}ms {fix_time:<15.2f}ms {overhead:<12.1f}x")
    
    avg_overhead = sum(overheads) / len(overheads)
    
    print(f"\n📈 平均性能开销: {avg_overhead:.1f}x")
    
    if avg_overhead > 50:
        risk_level = "L1"
        passed = False
        score = 40
    elif avg_overhead > 10:
        risk_level = "L2"
        passed = False
        score = 60
    else:
        risk_level = "L3"
        passed = True
        score = 80
    
    details = f"语义分块比固定长度慢{avg_overhead:.1f}倍"
    
    return TestResult(
        name="性能对比",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=details
    )


def test_domain_adaptation() -> TestResult:
    """
    测试3：领域适配性
    测试通用语义模型在专业领域的效果
    """
    print("\n" + "="*60)
    print("🧪 测试3：领域适配性测试")
    print("="*60)
    
    # 不同领域的测试文本
    domains = {
        "通用": "人工智能是计算机科学的一个分支。它研究如何模拟人类智能。",
        "法律": "根据《合同法》第52条规定，有下列情形之一的，合同无效：一方以欺诈、胁迫的手段订立合同，损害国家利益。",
        "医疗": "糖尿病患者应定期监测血糖水平。HbA1c指标反映过去2-3个月的平均血糖控制情况。",
        "金融": "该基金的夏普比率为1.25，年化收益率8.5%，最大回撤控制在12%以内。",
    }
    
    print(f"\n📊 领域适配性测试:")
    print(f"{'领域':<10} {'Chunks':<10} {'平均大小':<12} {'一致性'}")
    print("-" * 50)
    
    results = []
    
    for domain, text in domains.items():
        chunks, _ = semantic_chunk(text, threshold=0.8)
        sizes = [len(c.content) for c in chunks]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        
        # 模拟一致性检查（实际应使用领域知识库）
        consistency = "✓" if len(chunks) >= 2 else "?"
        
        results.append({
            'domain': domain,
            'num_chunks': len(chunks),
            'avg_size': avg_size
        })
        
        print(f"{domain:<10} {len(chunks):<10} {avg_size:<12.0f} {consistency}")
    
    # 检查领域差异
    chunk_counts = [r['num_chunks'] for r in results]
    max_diff = max(chunk_counts) - min(chunk_counts)
    
    print(f"\n📈 领域差异分析:")
    print(f"   最大差异: {max_diff} chunks")
    
    if max_diff > 2:
        print(f"   ⚠️  不同领域分块结果差异较大，建议考虑领域专用模型")
        risk_level = "L2"
        passed = False
        score = 65
    else:
        print(f"   ✅ 各领域分块结果相对一致")
        risk_level = "L3"
        passed = True
        score = 85
    
    details = f"测试{len(domains)}个领域，chunks数量差异{max_diff}"
    
    return TestResult(
        name="领域适配性",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=details
    )


def test_short_text_handling() -> TestResult:
    """
    测试4：短文本处理
    测试短段落和单句的处理
    """
    print("\n" + "="*60)
    print("🧪 测试4：短文本处理测试")
    print("="*60)
    
    test_cases = [
        ("单句", "这是一个单句测试。"),
        ("两句", "这是第一句。这是第二句。"),
        ("短段", "人工智能很重要。它改变生活。未来会更好。"),
        ("FAQ", "Q: 如何退款？A: 7天内可申请。Q: 多久到账？A: 3-5个工作日。"),
    ]
    
    print(f"\n📊 短文本处理结果:")
    print(f"{'类型':<12} {'原文长度':<12} {'Chunks':<10} {'处理结果'}")
    print("-" * 55)
    
    issues = []
    
    for name, text in test_cases:
        chunks, _ = semantic_chunk(text, threshold=0.8)
        
        # 评估处理结果
        if len(chunks) == 0:
            result = "❌ 未分块"
            issues.append(f"{name}: 未产生chunks")
        elif len(chunks) == 1 and len(text) > 50:
            result = "⚠️  合并过度"
            issues.append(f"{name}: 短文本被合并")
        elif len(chunks) > len(text) // 20:  # 假设每20字符一个chunk过多
            result = "⚠️  过度分割"
            issues.append(f"{name}: 过度分割")
        else:
            result = "✓ 正常"
        
        print(f"{name:<12} {len(text):<12} {len(chunks):<10} {result}")
    
    if issues:
        print(f"\n⚠️  发现 {len(issues)} 个问题:")
        for issue in issues:
            print(f"   - {issue}")
    
    score = 100 - len(issues) * 15
    score = max(0, score)
    
    if score < 60:
        risk_level = "L2"
        passed = False
    else:
        risk_level = "L3"
        passed = True
    
    details = f"测试{len(test_cases)}种短文本场景，发现{len(issues)}个问题"
    
    return TestResult(
        name="短文本处理",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=details
    )


def test_recall_comparison() -> TestResult:
    """
    测试5：召回率对比
    Head-to-head对比语义分块和固定长度分块
    """
    print("\n" + "="*60)
    print("🧪 测试5：召回率对比测试")
    print("="*60)
    
    # 构造有明确主题的测试文档
    text = """
    产品使用指南
    
    第一章：快速入门
    欢迎使用我们的产品。本指南将帮助您快速上手。
    安装步骤：下载安装包 → 运行安装程序 → 完成配置。
    
    第二章：核心功能
    智能搜索功能支持全文检索。您可以输入关键词快速找到所需内容。
    数据分析模块提供多种报表。支持导出Excel和PDF格式。
    
    第三章：常见问题
    如何重置密码？在登录页面点击"忘记密码"链接。
    如何联系客服？发送邮件至 support@example.com。
    """
    
    # 模拟查询
    queries = [
        (["安装", "步骤"], "安装指南"),
        (["搜索", "功能"], "搜索功能"),
        (["密码", "重置"], "密码问题"),
        (["客服", "联系"], "客服信息"),
    ]
    
    print(f"\n📄 测试文档: 产品使用指南 ({len(text)} 字符)")
    
    # 语义分块
    sem_chunks, _ = semantic_chunk(text, threshold=0.8)
    print(f"\n🔹 语义分块: {len(sem_chunks)} chunks")
    
    # 固定长度分块
    fix_chunks, _ = fixed_length_chunk(text, chunk_size=100, overlap=20)
    print(f"🔹 固定长度分块: {len(fix_chunks)} chunks")
    
    # 模拟检索评估
    print(f"\n📊 检索效果对比:")
    print(f"{'查询':<15} {'语义分块':<12} {'固定长度':<12} {'提升'}")
    print("-" * 55)
    
    sem_hits = 0
    fix_hits = 0
    
    for keywords, desc in queries:
        # 简单模拟：检查chunks是否包含关键词
        sem_hit = sum(1 for c in sem_chunks if any(kw in c.content for kw in keywords))
        fix_hit = sum(1 for c in fix_chunks if any(kw in c.content for kw in keywords))
        
        improvement = ((sem_hit - fix_hit) / fix_hit * 100) if fix_hit > 0 else 0
        
        sem_hits += sem_hit
        fix_hits += fix_hit
        
        print(f"{desc:<15} {sem_hit:<12} {fix_hit:<12} {improvement:+.0f}%")
    
    avg_improvement = ((sem_hits - fix_hits) / fix_hits * 100) if fix_hits > 0 else 0
    
    print(f"\n📈 平均召回提升: {avg_improvement:+.1f}%")
    
    # 行业研究声称可提升9%，我们验证是否达到
    if avg_improvement >= 5:
        print(f"   ✅ 达到预期提升（目标>5%）")
        score = 90
        risk_level = "L3"
        passed = True
    elif avg_improvement >= 0:
        print(f"   ⚠️  提升有限（实际{avg_improvement:+.1f}%）")
        score = 70
        risk_level = "L2"
        passed = False
    else:
        print(f"   ❌ 召回率下降")
        score = 50
        risk_level = "L2"
        passed = False
    
    details = f"语义分块召回率提升{avg_improvement:+.1f}%（vs固定长度）"
    
    return TestResult(
        name="召回率对比",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=details
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 测试汇总报告 - Day 26: 语义分块策略评估")
    print("="*70)
    
    print(f"\n{'测试项':<20} {'状态':<8} {'得分':<8} {'风险':<8} {'详情'}")
    print("-"*70)
    
    risk_count = {"L1": 0, "L2": 0, "L3": 0}
    
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"{r.name:<20} {status:<8} {r.score:>6.1f}%  {r.risk_level:<8} {r.details}")
        risk_count[r.risk_level] += 1
    
    print("-"*70)
    
    avg_score = sum(r.score for r in results) / len(results)
    passed_count = sum(1 for r in results if r.passed)
    
    print(f"\n📈 总体得分: {avg_score:.1f}%")
    print(f"✅ 通过测试: {passed_count}/{len(results)}")
    print(f"🔴 L1风险: {risk_count['L1']}个 | 🟡 L2风险: {risk_count['L2']}个 | 🟢 L3风险: {risk_count['L3']}个")
    
    # 关键发现
    print("\n🔍 关键发现:")
    if risk_count["L1"] > 0:
        print("   ⚠️  存在高风险问题，建议优化阈值或考虑混合策略")
    if risk_count["L2"] > 0:
        print("   ⚡ 存在中风险问题，注意监控生产环境表现")
    
    # 策略建议
    print("\n💡 策略建议:")
    print("   1. 推荐相似度阈值: 0.75-0.85（通用场景）")
    print("   2. 性能敏感场景: 考虑预计算embedding或异步处理")
    print("   3. 专业领域: 评估领域专用embedding模型")
    print("   4. 混合策略: 固定长度快速分块 + 语义优化关键文档")
    
    print("\n" + "="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 26: 语义分块策略评估")
    print("="*70)
    print("\n📋 测试目标：验证语义分块的阈值敏感性和性能开销")
    print("🎯 核心关注：阈值调优、性能对比、领域适配")
    
    results = [
        test_threshold_sensitivity(),
        test_performance_comparison(),
        test_domain_adaptation(),
        test_short_text_handling(),
        test_recall_comparison(),
    ]
    
    print_summary(results)
    
    print("\n✅ 测试执行完毕，请将上方日志发给 Trae 生成 report_day26.md")


if __name__ == "__main__":
    run_all_tests()
