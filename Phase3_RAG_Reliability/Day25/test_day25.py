"""
Day 25: 固定长度分块策略评估（基础篇）
目标：最小可用，突出风险验证，代码要足够精简
测试架构师视角：验证固定长度分块的边界信息丢失风险
难度级别：基础
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
import re


@dataclass
class Chunk:
    """分块结果"""
    content: str
    index: int
    start_pos: int
    end_pos: int


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float  # 0-100
    risk_level: str  # L1/L2/L3
    details: str


def fixed_length_chunk(text: str, chunk_size: int, chunk_overlap: int = 0) -> List[Chunk]:
    """
    固定长度分块实现
    模拟真实场景的分块逻辑
    """
    chunks = []
    start = 0
    index = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        content = text[start:end]
        
        chunks.append(Chunk(
            content=content,
            index=index,
            start_pos=start,
            end_pos=end
        ))
        
        # 下一个chunk的起始位置（考虑重叠）
        start = end - chunk_overlap if end < len(text) else end
        index += 1
        
        # 防止无限循环
        if start >= end:
            break
    
    return chunks


def calculate_semantic_continuity(chunks: List[Chunk]) -> float:
    """
    计算语义连续性得分
    检查chunk边界是否截断了句子
    """
    if len(chunks) <= 1:
        return 100.0
    
    broken_boundaries = 0
    total_boundaries = len(chunks) - 1
    
    for i in range(len(chunks) - 1):
        current_end = chunks[i].content.strip()
        next_start = chunks[i + 1].content.strip()
        
        # 检查当前chunk结尾是否是完整句子
        if current_end and not re.search(r'[。！？.!?]\s*$', current_end[-5:]):
            # 检查下一个chunk开头是否是小写字母或中文（句子中间）
            if next_start and re.match(r'^[a-z\u4e00-\u9fa5]', next_start[0]):
                broken_boundaries += 1
    
    continuity_score = (1 - broken_boundaries / total_boundaries) * 100
    return continuity_score


def simulate_retrieval(chunks: List[Chunk], query_keywords: List[str]) -> Tuple[int, int]:
    """
    模拟检索过程
    返回：(命中的chunk数, 包含完整信息的chunk数)
    """
    hit_chunks = 0
    complete_info_chunks = 0
    
    for chunk in chunks:
        # 简单模拟：检查chunk是否包含查询关键词
        keyword_hits = sum(1 for kw in query_keywords if kw in chunk.content)
        
        if keyword_hits > 0:
            hit_chunks += 1
            # 模拟：如果chunk包含关键词且长度足够，认为信息完整
            if keyword_hits >= len(query_keywords) * 0.5 and len(chunk.content) > 50:
                complete_info_chunks += 1
    
    return hit_chunks, complete_info_chunks


def test_sentence_boundary_cutting() -> TestResult:
    """
    测试1：句子边界切割
    验证分块是否会在句子中间截断
    """
    print("\n" + "="*60)
    print("🧪 测试1：句子边界切割")
    print("="*60)
    
    # 构造测试文本：包含多个句子的段落
    text = """人工智能是计算机科学的一个分支。它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大。"""
    
    chunk_size = 30  # 故意设置较小，测试边界情况
    chunks = fixed_length_chunk(text, chunk_size, chunk_overlap=5)
    
    print(f"\n📄 原文长度: {len(text)} 字符")
    print(f"🔧 分块参数: chunk_size={chunk_size}, overlap=5")
    print(f"📦 生成 {len(chunks)} 个chunks:")
    
    for chunk in chunks:
        print(f"   Chunk {chunk.index}: [{chunk.content[:40]}...]")
    
    # 计算语义连续性
    continuity_score = calculate_semantic_continuity(chunks)
    
    # 统计被截断的句子
    broken_sentences = 0
    for chunk in chunks[:-1]:  # 除了最后一个
        content = chunk.content.strip()
        if content and not re.search(r'[。！？.!?]\s*$', content[-3:]):
            broken_sentences += 1
    
    print(f"\n� 语义连续性得分: {continuity_score:.1f}%")
    print(f"⚠️  疑似截断边界数: {broken_sentences}")
    
    # 评估风险
    if continuity_score < 50:
        risk_level = "L1"
        passed = False
    elif continuity_score < 80:
        risk_level = "L2"
        passed = False
    else:
        risk_level = "L3"
        passed = True
    
    details = f"生成{len(chunks)}个chunks，语义连续性{continuity_score:.1f}%，{broken_sentences}个边界疑似截断"
    
    return TestResult(
        name="句子边界切割",
        passed=passed,
        score=continuity_score,
        risk_level=risk_level,
        details=details
    )


def test_overlap_effectiveness() -> TestResult:
    """
    测试2：重叠效果验证
    测试不同重叠比例对信息连续性的影响
    """
    print("\n" + "="*60)
    print("🧪 测试2：重叠效果验证")
    print("="*60)
    
    # 构造跨边界的关键信息
    text = """退款政策：用户购买商品后，可以在7天内申请全额退款。退款需要提供订单号和购买凭证。特殊商品（如定制商品）不支持退款。"""
    
    query = ["7天", "退款"]  # 模拟查询关键词
    
    overlap_ratios = [0, 0.1, 0.2, 0.5]
    chunk_size = 35
    
    results = []
    
    print(f"\n📄 测试文本: {text[:50]}...")
    print(f"🔍 模拟查询关键词: {query}")
    print(f"\n📊 不同重叠比例对比:")
    
    for overlap_ratio in overlap_ratios:
        overlap = int(chunk_size * overlap_ratio)
        chunks = fixed_length_chunk(text, chunk_size, overlap)
        hit, complete = simulate_retrieval(chunks, query)
        
        # 计算召回率
        recall = (complete / len(chunks) * 100) if chunks else 0
        results.append((overlap_ratio, recall, len(chunks)))
        
        print(f"   重叠{overlap_ratio*100:>3.0f}%: {len(chunks)} chunks, 完整信息召回率 {recall:.1f}%")
    
    # 找出最佳重叠比例
    best = max(results, key=lambda x: x[1])
    worst = min(results, key=lambda x: x[1])
    
    print(f"\n✅ 最佳重叠比例: {best[0]*100:.0f}% (召回率{best[1]:.1f}%)")
    print(f"⚠️  最差重叠比例: {worst[0]*100:.0f}% (召回率{worst[1]:.1f}%)")
    
    # 0%重叠的风险评估
    zero_overlap_recall = next(r for r in results if r[0] == 0)[1]
    
    if zero_overlap_recall < 30:
        risk_level = "L1"
        passed = False
    elif zero_overlap_recall < 60:
        risk_level = "L2"
        passed = False
    else:
        risk_level = "L3"
        passed = True
    
    details = f"0%重叠时召回率{zero_overlap_recall:.1f}%，推荐重叠比例{best[0]*100:.0f}%"
    
    return TestResult(
        name="重叠效果验证",
        passed=passed,
        score=zero_overlap_recall,
        risk_level=risk_level,
        details=details
    )


def test_chunk_size_impact() -> TestResult:
    """
    测试3：块大小影响
    扫描不同块大小对召回率和存储效率的影响
    """
    print("\n" + "="*60)
    print("🧪 测试3：块大小影响扫描")
    print("="*60)
    
    # 构造测试文档
    text = """
    产品功能介绍：
    1. 智能搜索：支持全文检索和语义搜索，快速定位所需信息。
    2. 数据分析：提供多维度数据分析报表，助力业务决策。
    3. 自动化工作流：自定义审批流程，提升团队协作效率。
    4. 安全保障：企业级数据加密，符合ISO27001安全标准。
    5. API集成：开放API接口，支持与第三方系统无缝对接。
    6. 多端同步：支持Web、iOS、Android多平台数据实时同步。
    """ * 3  # 重复以生成足够长的文本
    
    chunk_sizes = [50, 100, 200, 500, 1000]
    overlap_ratio = 0.1
    
    print(f"\n📄 文档长度: {len(text)} 字符")
    print(f"🔧 固定重叠比例: {overlap_ratio*100:.0f}%")
    print(f"\n📊 块大小扫描结果:")
    
    results = []
    
    for size in chunk_sizes:
        overlap = int(size * overlap_ratio)
        chunks = fixed_length_chunk(text, size, overlap)
        
        # 计算指标
        num_chunks = len(chunks)
        storage_overhead = sum(len(c.content) for c in chunks) / len(text)
        avg_chunk_size = sum(len(c.content) for c in chunks) / num_chunks if num_chunks else 0
        
        results.append({
            'size': size,
            'num_chunks': num_chunks,
            'overhead': storage_overhead,
            'avg_size': avg_chunk_size
        })
        
        print(f"   Size {size:>4}: {num_chunks:>3} chunks, 存储开销 {storage_overhead:.2f}x, 均大小 {avg_chunk_size:.0f}")
    
    # 推荐配置：平衡chunks数量和存储开销
    optimal = min(results, key=lambda x: abs(x['num_chunks'] - 10))  # 假设目标10个chunks
    
    print(f"\n✅ 推荐块大小: {optimal['size']} (生成{optimal['num_chunks']}个chunks)")
    
    # 评估风险：chunks数量过多或过少
    if optimal['num_chunks'] > 50 or optimal['num_chunks'] < 3:
        risk_level = "L2"
        passed = False
        score = 50
    else:
        risk_level = "L3"
        passed = True
        score = 80
    
    details = f"推荐chunk_size={optimal['size']}，生成{optimal['num_chunks']}个chunks，存储开销{optimal['overhead']:.2f}x"
    
    return TestResult(
        name="块大小影响扫描",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=details
    )


def test_special_character_handling() -> TestResult:
    """
    测试4：特殊字符处理
    测试中文、emoji、代码块等边界处理
    """
    print("\n" + "="*60)
    print("🧪 测试4：特殊字符边界处理")
    print("="*60)
    
    test_cases = [
        ("中文测试", "人工智能🤖是未来的趋势。机器学习📊正在改变各行各业。"),
        ("Emoji测试", "Hello 👋 World 🌍! This is a test 🧪."),
        ("代码测试", "def hello():\n    return 'world'\n\nclass Test:\n    pass"),
        ("混合测试", "价格：¥100 💰 | 时间：2024年📅 | 状态：✅完成"),
    ]
    
    chunk_size = 20
    issues = []
    
    print(f"\n📊 特殊字符处理测试:")
    
    for name, text in test_cases:
        chunks = fixed_length_chunk(text, chunk_size, chunk_overlap=5)
        
        # 检查每个chunk的完整性
        for chunk in chunks:
            try:
                # 尝试编码解码，检查是否完整
                encoded = chunk.content.encode('utf-8')
                decoded = encoded.decode('utf-8')
                if decoded != chunk.content:
                    issues.append(f"{name}: Chunk编码异常")
            except Exception as e:
                issues.append(f"{name}: 编码错误 - {e}")
        
        print(f"   {name}: {len(chunks)} chunks ✓")
    
    if issues:
        print(f"\n⚠️  发现 {len(issues)} 个问题:")
        for issue in issues[:3]:
            print(f"   - {issue}")
    else:
        print(f"\n✅ 所有特殊字符处理正常")
    
    score = 100 if not issues else max(0, 100 - len(issues) * 20)
    risk_level = "L3" if score > 80 else "L2" if score > 50 else "L1"
    passed = score > 80
    
    return TestResult(
        name="特殊字符处理",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=f"测试{len(test_cases)}种特殊字符场景，发现{len(issues)}个问题"
    )


def test_context_dependency() -> TestResult:
    """
    测试5：上下文依赖
    测试跨chunk信息关联的完整性
    """
    print("\n" + "="*60)
    print("🧪 测试5：上下文依赖验证")
    print("="*60)
    
    # 构造有上下文依赖的文本
    text = """退款政策说明：
    
    条件一：用户必须在购买后的7天内提出退款申请。超过7天的订单不予受理。
    
    条件二：退款金额将根据支付方式原路返回。信用卡支付需要3-5个工作日到账。
    
    条件三：以下情况不支持退款：已使用的虚拟商品、超过有效期的服务、促销特价商品。
    
    流程：申请退款 → 客服审核 → 财务处理 → 资金到账。整个流程约需5-7个工作日。"""
    
    chunk_size = 80
    overlap = 20
    
    chunks = fixed_length_chunk(text, chunk_size, overlap)
    
    print(f"\n📄 测试文本: 退款政策（含多条件依赖）")
    print(f"🔧 分块参数: size={chunk_size}, overlap={overlap}")
    print(f"📦 生成 {len(chunks)} 个chunks")
    
    # 模拟查询场景
    queries = [
        (["退款", "7天"], "退款时间条件"),
        (["信用卡", "到账"], "退款到账方式"),
        (["不支持退款", "虚拟商品"], "退款限制条件"),
    ]
    
    print(f"\n🔍 查询场景测试:")
    
    complete_answers = 0
    for keywords, desc in queries:
        hit_chunks, complete = simulate_retrieval(chunks, keywords)
        status = "✅" if complete > 0 else "❌"
        print(f"   {status} {desc}: 命中{hit_chunks} chunks, 完整信息{complete}个")
        if complete > 0:
            complete_answers += 1
    
    completeness_rate = (complete_answers / len(queries)) * 100
    
    print(f"\n📊 信息完整性: {complete_answers}/{len(queries)} ({completeness_rate:.0f}%)")
    
    if completeness_rate < 50:
        risk_level = "L1"
        passed = False
    elif completeness_rate < 80:
        risk_level = "L2"
        passed = False
    else:
        risk_level = "L3"
        passed = True
    
    return TestResult(
        name="上下文依赖验证",
        passed=passed,
        score=completeness_rate,
        risk_level=risk_level,
        details=f"{complete_answers}/{len(queries)}个查询场景能获取完整信息"
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 测试汇总报告 - Day 25: 固定长度分块策略评估")
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
        print("   ⚠️  存在高风险问题，建议立即优化分块参数")
    if risk_count["L2"] > 0:
        print("   ⚡ 存在中风险问题，建议调整重叠比例或块大小")
    if avg_score < 70:
        print("   📉 整体分块质量偏低，建议考虑语义分块策略")
    else:
        print("   ✅ 整体分块质量良好，注意监控边界情况")
    
    print("\n💡 优化建议:")
    print("   1. 推荐chunk_size: 500-1000字符（中文场景）")
    print("   2. 推荐overlap: 10-20%")
    print("   3. 对关键文档建议增加人工审核边界chunks")
    print("   4. 考虑使用语义分块作为补充策略")
    
    print("\n" + "="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 25: 固定长度分块策略评估")
    print("="*70)
    print("\n📋 测试目标：验证固定长度分块的边界信息丢失风险")
    print("🎯 核心关注：语义连续性、重叠效果、块大小优化")
    
    results = [
        test_sentence_boundary_cutting(),
        test_overlap_effectiveness(),
        test_chunk_size_impact(),
        test_special_character_handling(),
        test_context_dependency(),
    ]
    
    print_summary(results)
    
    print("\n✅ 测试执行完毕，请将上方日志发给 Trae 生成 report_day25.md")


if __name__ == "__main__":
    run_all_tests()
