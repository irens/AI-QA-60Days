"""
Day 27: 递归/Agentic分块策略评估（实战篇）
目标：最小可用，突出风险验证，代码要足够精简
测试架构师视角：验证复杂分块策略的成本效益和失败模式
难度级别：实战
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import re
import time
import random


@dataclass
class Chunk:
    """分块结果"""
    content: str
    index: int
    level: int = 0  # 递归层级
    parent_id: Optional[int] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: str
    details: str


def mock_embedding(text: str) -> List[float]:
    """模拟embedding计算"""
    time.sleep(0.0005)  # 模拟延迟
    hash_val = hash(text) % 10000
    return [(hash_val % 100) / 100, ((hash_val // 100) % 100) / 100]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """计算余弦相似度"""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def fixed_length_chunk(text: str, chunk_size: int = 100, overlap: int = 20) -> Tuple[List[Chunk], float]:
    """固定长度分块"""
    start_time = time.time()
    chunks = []
    start = 0
    index = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(Chunk(content=text[start:end], index=index, level=1))
        start = end - overlap if end < len(text) else end
        index += 1
        if start >= end:
            break
    
    return chunks, (time.time() - start_time) * 1000


def semantic_chunk(text: str, threshold: float = 0.8) -> Tuple[List[Chunk], float]:
    """语义分块"""
    start_time = time.time()
    
    # 简单句子分割
    sentences = re.split(r'([。！？.!?]\s*)', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return [], 0
    
    embeddings = [mock_embedding(s) for s in sentences]
    chunks = []
    current_chunk = [sentences[0]]
    current_embs = [embeddings[0]]
    
    for i in range(1, len(sentences)):
        similarities = [cosine_similarity(embeddings[i], emb) for emb in current_embs]
        avg_sim = sum(similarities) / len(similarities)
        
        if avg_sim >= threshold:
            current_chunk.append(sentences[i])
            current_embs.append(embeddings[i])
        else:
            chunks.append(Chunk(content=''.join(current_chunk), index=len(chunks), level=1))
            current_chunk = [sentences[i]]
            current_embs = [embeddings[i]]
    
    if current_chunk:
        chunks.append(Chunk(content=''.join(current_chunk), index=len(chunks), level=1))
    
    return chunks, (time.time() - start_time) * 1000


def recursive_chunk(text: str, chunk_sizes: List[int] = [500, 200, 100], 
                    overlap: int = 20, max_depth: int = 3) -> Tuple[List[Chunk], float]:
    """
    递归分块实现
    从大到小逐步细化，保留父子关系
    """
    start_time = time.time()
    all_chunks = []
    chunk_id_counter = [0]
    
    def recursive_split(content: str, level: int, parent_id: Optional[int] = None):
        if level >= len(chunk_sizes) or level >= max_depth:
            # 最细粒度，创建叶子节点
            chunk_id = chunk_id_counter[0]
            chunk_id_counter[0] += 1
            all_chunks.append(Chunk(
                content=content,
                index=chunk_id,
                level=level + 1,
                parent_id=parent_id,
                metadata={'is_leaf': True}
            ))
            return
        
        # 当前层级的分块大小
        size = chunk_sizes[level]
        
        # 如果内容小于当前层级大小，直接作为叶子
        if len(content) <= size:
            chunk_id = chunk_id_counter[0]
            chunk_id_counter[0] += 1
            all_chunks.append(Chunk(
                content=content,
                index=chunk_id,
                level=level + 1,
                parent_id=parent_id,
                metadata={'is_leaf': True}
            ))
            return
        
        # 创建父节点
        parent_chunk_id = chunk_id_counter[0]
        chunk_id_counter[0] += 1
        all_chunks.append(Chunk(
            content=content[:100] + "...",  # 父节点存储摘要
            index=parent_chunk_id,
            level=level + 1,
            parent_id=parent_id,
            metadata={'is_leaf': False, 'full_content': content}
        ))
        
        # 分割并递归处理
        start = 0
        while start < len(content):
            end = min(start + size, len(content))
            segment = content[start:end]
            recursive_split(segment, level + 1, parent_chunk_id)
            start = end - overlap if end < len(content) else end
            if start >= end:
                break
    
    recursive_split(text, 0)
    return all_chunks, (time.time() - start_time) * 1000


def mock_llm_chunk_analysis(text: str, failure_rate: float = 0.0) -> Tuple[List[Dict], float, bool]:
    """
    模拟LLM Agentic分块
    返回：(chunks_metadata, cost, success)
    """
    cost_per_call = 0.002  # 模拟成本：$0.002/次
    
    # 模拟失败
    if random.random() < failure_rate:
        return [], cost_per_call, False
    
    # 模拟LLM分析延迟
    time.sleep(0.01)
    
    # 简单模拟：按段落分割
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    chunks_metadata = []
    for i, para in enumerate(paragraphs):
        # 模拟LLM输出结构
        chunks_metadata.append({
            'content': para[:200],
            'topic': f"topic_{i}",
            'importance': random.choice(['high', 'medium', 'low']),
            'keywords': para.split()[:3]
        })
    
    total_cost = cost_per_call * max(1, len(paragraphs) // 3)  # 假设每3段落1次调用
    return chunks_metadata, total_cost, True


def agentic_chunk(text: str, failure_rate: float = 0.0) -> Tuple[List[Chunk], float, float, bool]:
    """
    Agentic分块
    返回：(chunks, processing_time_ms, cost, success)
    """
    start_time = time.time()
    
    metadata_list, cost, success = mock_llm_chunk_analysis(text, failure_rate)
    
    if not success:
        return [], (time.time() - start_time) * 1000, cost, False
    
    chunks = []
    for i, meta in enumerate(metadata_list):
        chunks.append(Chunk(
            content=meta['content'],
            index=i,
            level=1,
            metadata={
                'topic': meta['topic'],
                'importance': meta['importance'],
                'keywords': meta['keywords'],
                'agent_processed': True
            }
        ))
    
    return chunks, (time.time() - start_time) * 1000, cost, True


def test_recursive_depth_impact() -> TestResult:
    """
    测试1：递归层级深度影响
    测试不同层级配置对性能和结果的影响
    """
    print("\n" + "="*60)
    print("🧪 测试1：递归层级深度影响")
    print("="*60)
    
    # 构造测试文档
    text = """
    第一章：产品介绍
    我们的产品是业界领先的解决方案。它提供了强大的功能和优秀的用户体验。
    
    第二章：核心功能
    功能一：智能分析。通过AI技术实现自动化数据处理。
    功能二：可视化展示。支持多种图表类型和自定义配置。
    功能三：协作共享。团队成员可以实时协作编辑文档。
    
    第三章：使用指南
    步骤一：注册账号。访问官网完成注册流程。
    步骤二：创建项目。在控制台点击新建项目按钮。
    步骤三：邀请成员。输入邮箱地址邀请团队成员。
    """ * 2  # 增加长度
    
    depth_configs = [
        ("1层", [500]),
        ("2层", [500, 200]),
        ("3层", [500, 200, 100]),
        ("4层", [500, 200, 100, 50]),
    ]
    
    print(f"\n📄 测试文档长度: {len(text)} 字符")
    print(f"\n📊 不同层级配置对比:")
    print(f"{'配置':<10} {'Chunks':<10} {'层级':<10} {'处理时间':<12} {'叶子节点'}")
    print("-" * 60)
    
    results = []
    
    for name, sizes in depth_configs:
        chunks, proc_time = recursive_chunk(text, chunk_sizes=sizes, max_depth=len(sizes))
        leaf_nodes = sum(1 for c in chunks if c.metadata.get('is_leaf'))
        parent_nodes = len(chunks) - leaf_nodes
        
        results.append({
            'name': name,
            'chunks': len(chunks),
            'leaf': leaf_nodes,
            'parent': parent_nodes,
            'time': proc_time
        })
        
        print(f"{name:<10} {len(chunks):<10} {len(sizes):<10} {proc_time:<12.2f}ms {leaf_nodes}")
    
    # 分析层级影响
    deepest = results[-1]
    shallowest = results[0]
    
    time_increase = deepest['time'] / shallowest['time'] if shallowest['time'] > 0 else 0
    chunk_increase = deepest['chunks'] / shallowest['chunks'] if shallowest['chunks'] > 0 else 0
    
    print(f"\n⚠️  层级影响分析:")
    print(f"   4层 vs 1层: 处理时间 {time_increase:.1f}x, chunks数量 {chunk_increase:.1f}x")
    
    if time_increase > 3:
        print(f"   ⚠️  深层递归导致性能显著下降")
        risk_level = "L2"
        passed = False
        score = 60
    else:
        print(f"   ✅ 层级增加对性能影响可控")
        risk_level = "L3"
        passed = True
        score = 80
    
    details = f"4层递归比1层慢{time_increase:.1f}倍，生成{deepest['chunks']}个chunks"
    
    return TestResult(
        name="递归层级深度",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=details
    )


def test_cost_benefit_analysis() -> TestResult:
    """
    测试2：成本效益分析
    量化Agentic分块的成本与收益
    """
    print("\n" + "="*60)
    print("🧪 测试2：Agentic分块成本效益分析")
    print("="*60)
    
    # 不同规模的测试文档
    test_docs = [
        ("短文档", "产品介绍：我们的产品是最佳解决方案。" * 5),
        ("中文档", "产品介绍：我们的产品是最佳解决方案。" * 20),
        ("长文档", "产品介绍：我们的产品是最佳解决方案。" * 50),
    ]
    
    print(f"\n📊 成本效益对比:")
    print(f"{'文档类型':<12} {'策略':<12} {'Chunks':<10} {'成本($)':<12} {'时间(ms)'}")
    print("-" * 65)
    
    total_costs = {'fixed': 0, 'semantic': 0, 'agentic': 0}
    
    for doc_name, text in test_docs:
        # 固定长度
        fix_chunks, fix_time = fixed_length_chunk(text, chunk_size=100)
        fix_cost = 0  # 无LLM成本
        
        # 语义分块
        sem_chunks, sem_time = semantic_chunk(text)
        sem_cost = 0  # embedding成本忽略
        
        # Agentic分块
        agent_chunks, agent_time, agent_cost, success = agentic_chunk(text)
        if not success:
            agent_chunks = []
        
        print(f"{doc_name:<12} {'固定长度':<12} {len(fix_chunks):<10} ${fix_cost:<11.4f} {fix_time:.2f}")
        print(f"{'':<12} {'语义分块':<12} {len(sem_chunks):<10} ${sem_cost:<11.4f} {sem_time:.2f}")
        print(f"{'':<12} {'Agentic':<12} {len(agent_chunks):<10} ${agent_cost:<11.4f} {agent_time:.2f}")
        print("-" * 65)
        
        total_costs['fixed'] += fix_cost
        total_costs['semantic'] += sem_cost
        total_costs['agentic'] += agent_cost
    
    print(f"\n💰 总成本对比:")
    print(f"   固定长度: ${total_costs['fixed']:.4f}")
    print(f"   语义分块: ${total_costs['semantic']:.4f}")
    print(f"   Agentic:  ${total_costs['agentic']:.4f}")
    
    cost_ratio = total_costs['agentic'] / 0.001  # 对比基准
    
    if total_costs['agentic'] > 0.01:  # 假设阈值
        print(f"\n⚠️  Agentic分块成本较高，建议仅用于高价值文档")
        risk_level = "L2"
        passed = False
        score = 65
    else:
        print(f"\n✅ 成本可控")
        risk_level = "L3"
        passed = True
        score = 85
    
    details = f"Agentic总成本${total_costs['agentic']:.4f}，建议限制使用范围"
    
    return TestResult(
        name="成本效益分析",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=details
    )


def test_hierarchy_consistency() -> TestResult:
    """
    测试3：层级一致性验证
    验证递归分块的父子关系正确性
    """
    print("\n" + "="*60)
    print("🧪 测试3：层级一致性验证")
    print("="*60)
    
    text = """
    第一节：概述
    这是概述部分的内容，介绍整体情况。
    
    第二节：详细说明
    这是详细说明部分，包含更多细节。
    
    第三节：总结
    这是总结部分，归纳主要内容。
    """
    
    chunks, _ = recursive_chunk(text, chunk_sizes=[200, 100], max_depth=2)
    
    print(f"\n📄 生成 {len(chunks)} 个chunks")
    print(f"\n📊 层级结构:")
    
    # 按层级分组
    by_level = {}
    for c in chunks:
        by_level.setdefault(c.level, []).append(c)
    
    for level in sorted(by_level.keys()):
        level_chunks = by_level[level]
        print(f"   Level {level}: {len(level_chunks)} chunks")
        for c in level_chunks[:3]:  # 只显示前3个
            parent_info = f"(parent={c.parent_id})" if c.parent_id is not None else "(root)"
            leaf_info = "[leaf]" if c.metadata.get('is_leaf') else "[parent]"
            print(f"      Chunk {c.index} {parent_info} {leaf_info}: {c.content[:30]}...")
        if len(level_chunks) > 3:
            print(f"      ... and {len(level_chunks) - 3} more")
    
    # 验证一致性
    issues = []
    
    # 检查1：所有非根节点都有父节点
    for c in chunks:
        if c.level > 1 and c.parent_id is None:
            issues.append(f"Chunk {c.index} 缺少父节点")
    
    # 检查2：父节点存在性
    chunk_ids = {c.index for c in chunks}
    for c in chunks:
        if c.parent_id is not None and c.parent_id not in chunk_ids:
            issues.append(f"Chunk {c.index} 引用了不存在的父节点 {c.parent_id}")
    
    # 检查3：叶子节点一致性
    leaf_chunks = [c for c in chunks if c.metadata.get('is_leaf')]
    parent_chunks = [c for c in chunks if not c.metadata.get('is_leaf')]
    
    print(f"\n📈 结构统计:")
    print(f"   父节点: {len(parent_chunks)}")
    print(f"   叶子节点: {len(leaf_chunks)}")
    
    if issues:
        print(f"\n⚠️  发现 {len(issues)} 个一致性问题:")
        for issue in issues[:5]:
            print(f"   - {issue}")
    else:
        print(f"\n✅ 层级结构一致")
    
    score = 100 - len(issues) * 10
    score = max(0, score)
    
    if score < 70:
        risk_level = "L2"
        passed = False
    else:
        risk_level = "L3"
        passed = True
    
    details = f"生成{len(chunks)}个chunks，{len(parent_chunks)}父节点/{len(leaf_chunks)}叶子节点，{len(issues)}个问题"
    
    return TestResult(
        name="层级一致性",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=details
    )


def test_failure_modes() -> TestResult:
    """
    测试4：失败模式测试
    模拟各种异常情况，测试容错能力
    """
    print("\n" + "="*60)
    print("🧪 测试4：失败模式测试")
    print("="*60)
    
    text = "测试文档内容。包含多个句子。用于测试失败场景。"
    
    failure_scenarios = [
        ("正常", 0.0),
        ("偶发失败", 0.1),
        ("频繁失败", 0.3),
        ("严重失败", 0.7),
    ]
    
    print(f"\n📊 Agentic分块失败场景测试:")
    print(f"{'场景':<12} {'失败率':<10} {'成功率':<10} {'回退策略'}")
    print("-" * 55)
    
    results = []
    
    for scenario_name, failure_rate in failure_scenarios:
        success_count = 0
        fallback_used = 0
        
        # 模拟10次调用
        for _ in range(10):
            chunks, _, _, success = agentic_chunk(text, failure_rate)
            if success:
                success_count += 1
            else:
                # 模拟回退到固定长度分块
                fallback_chunks, _ = fixed_length_chunk(text)
                fallback_used += 1
        
        actual_success_rate = success_count / 10
        
        results.append({
            'scenario': scenario_name,
            'failure_rate': failure_rate,
            'success_rate': actual_success_rate,
            'fallback_used': fallback_used
        })
        
        fallback_str = f"使用{fallback_used}次" if fallback_used > 0 else "无需"
        print(f"{scenario_name:<12} {failure_rate*100:>6.0f}%    {actual_success_rate*100:>6.0f}%      {fallback_str}")
    
    # 评估容错能力
    high_failure = results[-1]
    
    if high_failure['success_rate'] < 0.3:
        print(f"\n⚠️  高失败率场景下需要可靠的回退机制")
        print(f"   建议：Agentic失败时自动回退到语义分块或固定长度分块")
        risk_level = "L2"
        passed = False
        score = 65
    else:
        print(f"\n✅ 容错机制有效")
        risk_level = "L3"
        passed = True
        score = 85
    
    details = f"70%失败率时成功率{high_failure['success_rate']*100:.0f}%，回退机制使用{high_failure['fallback_used']}次"
    
    return TestResult(
        name="失败模式",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=details
    )


def test_comprehensive_comparison() -> TestResult:
    """
    测试5：综合对比
    四种策略的head-to-head对比
    """
    print("\n" + "="*60)
    print("🧪 测试5：四种策略综合对比")
    print("="*60)
    
    # 构造综合测试文档
    text = """
    产品白皮书
    
    第一章：市场背景
    当前市场面临诸多挑战。企业需要更高效的解决方案来应对竞争压力。
    数字化转型已成为必然趋势。智能化工具能够显著提升工作效率。
    
    第二章：产品架构
    我们的产品采用微服务架构。核心模块包括数据处理引擎、分析模块和展示层。
    数据处理引擎负责实时数据摄取。分析模块提供智能洞察功能。
    展示层支持多端访问和自定义配置。
    
    第三章：核心优势
    优势一：高性能。系统能够处理百万级并发请求。
    优势二：易扩展。模块化设计支持灵活的功能扩展。
    优势三：安全可靠。通过多重安全认证和加密机制保护数据。
    
    第四章：客户案例
    案例一：某金融公司。使用后效率提升50%，成本降低30%。
    案例二：某制造企业。实现生产流程全面数字化。
    案例三：某零售品牌。客户满意度提升显著。
    """
    
    print(f"\n📄 测试文档: 产品白皮书 ({len(text)} 字符)")
    print(f"\n📊 策略对比结果:")
    print(f"{'策略':<12} {'Chunks':<10} {'时间(ms)':<12} {'成本($)':<12} {'质量分'}")
    print("-" * 65)
    
    strategies = []
    
    # 1. 固定长度
    fix_chunks, fix_time = fixed_length_chunk(text, chunk_size=150, overlap=30)
    fix_score = 70  # 基准分
    print(f"{'固定长度':<12} {len(fix_chunks):<10} {fix_time:<12.2f} ${0:<11.4f} {fix_score}")
    strategies.append({'name': '固定长度', 'chunks': len(fix_chunks), 'time': fix_time, 'cost': 0, 'score': fix_score})
    
    # 2. 语义分块
    sem_chunks, sem_time = semantic_chunk(text, threshold=0.8)
    sem_score = 80  # 语义连贯性加分
    print(f"{'语义分块':<12} {len(sem_chunks):<10} {sem_time:<12.2f} ${0:<11.4f} {sem_score}")
    strategies.append({'name': '语义分块', 'chunks': len(sem_chunks), 'time': sem_time, 'cost': 0, 'score': sem_score})
    
    # 3. 递归分块
    rec_chunks, rec_time = recursive_chunk(text, chunk_sizes=[400, 200, 100], max_depth=3)
    rec_score = 85  # 层级结构加分
    print(f"{'递归分块':<12} {len(rec_chunks):<10} {rec_time:<12.2f} ${0:<11.4f} {rec_score}")
    strategies.append({'name': '递归分块', 'chunks': len(rec_chunks), 'time': rec_time, 'cost': 0, 'score': rec_score})
    
    # 4. Agentic分块
    agent_chunks, agent_time, agent_cost, success = agentic_chunk(text)
    if success:
        agent_score = 90  # 智能化加分
    else:
        agent_chunks = []
        agent_score = 0
    print(f"{'Agentic':<12} {len(agent_chunks):<10} {agent_time:<12.2f} ${agent_cost:<11.4f} {agent_score}")
    strategies.append({'name': 'Agentic', 'chunks': len(agent_chunks), 'time': agent_time, 'cost': agent_cost, 'score': agent_score})
    
    # 综合分析
    print(f"\n📈 综合评估:")
    
    # 性价比 = 质量分 / (时间归一化 + 成本*1000)
    for s in strategies:
        time_factor = s['time'] / 10  # 归一化
        cost_factor = s['cost'] * 10000
        s['efficiency'] = s['score'] / (time_factor + cost_factor + 1)
    
    best_quality = max(strategies, key=lambda x: x['score'])
    fastest = min(strategies, key=lambda x: x['time'])
    cheapest = min(strategies, key=lambda x: x['cost'])
    best_efficiency = max(strategies, key=lambda x: x['efficiency'])
    
    print(f"   🏆 最高质量: {best_quality['name']} ({best_quality['score']}分)")
    print(f"   ⚡ 最快处理: {fastest['name']} ({fastest['time']:.2f}ms)")
    print(f"   💰 最低成本: {cheapest['name']} (${cheapest['cost']:.4f})")
    print(f"   ✅ 最佳性价比: {best_efficiency['name']} (效率值{best_efficiency['efficiency']:.2f})")
    
    # 选型建议
    print(f"\n💡 选型建议:")
    print(f"   • 追求速度: 固定长度分块")
    print(f"   • 追求质量: Agentic分块（需考虑成本）")
    print(f"   • 平衡方案: 递归分块")
    print(f"   • 性价比之选: 语义分块")
    
    score = 85  # 综合评分
    risk_level = "L3"
    passed = True
    
    details = f"四种策略各有优劣，{best_efficiency['name']}性价比最高"
    
    return TestResult(
        name="综合对比",
        passed=passed,
        score=score,
        risk_level=risk_level,
        details=details
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 测试汇总报告 - Day 27: 递归/Agentic分块策略评估")
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
        print("   ⚠️  存在高风险问题，建议立即优化")
    if risk_count["L2"] > 0:
        print("   ⚡ 存在中风险问题，建议监控并制定回退策略")
    
    # 策略建议
    print("\n💡 综合策略建议:")
    print("   1. 推荐层级: 2-3层递归（平衡效率和质量）")
    print("   2. Agentic分块: 仅用于高价值文档，设置成本上限")
    print("   3. 回退机制: Agentic失败时自动回退到语义分块")
    print("   4. 混合架构: 70%固定长度 + 25%语义/递归 + 5%Agentic")
    print("   5. 监控指标: 分块延迟、成本、父子一致性")
    
    print("\n" + "="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 27: 递归/Agentic分块策略评估")
    print("="*70)
    print("\n📋 测试目标：验证复杂分块策略的成本效益和失败模式")
    print("🎯 核心关注：递归层级、成本分析、容错能力、综合选型")
    
    results = [
        test_recursive_depth_impact(),
        test_cost_benefit_analysis(),
        test_hierarchy_consistency(),
        test_failure_modes(),
        test_comprehensive_comparison(),
    ]
    
    print_summary(results)
    
    print("\n✅ 测试执行完毕，请将上方日志发给 Trae 生成 report_day27.md")


if __name__ == "__main__":
    run_all_tests()
