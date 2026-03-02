"""
Day 33: 重排序优化与混合架构实战测试
目标：验证重排序对混合检索效果的提升，测量延迟开销，测试端到端流程
测试架构师视角：重排序是混合检索的"最后一公里"，排序错误将直接导致用户看到不相关的结果
难度级别：实战
"""

import json
import time
import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict


@dataclass
class TestResult:
    name: str
    passed: bool
    score: float
    risk_level: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    id: str
    title: str
    content: str
    vector: List[float] = field(default_factory=list)
    relevance_score: float = 0.0  # 用于模拟真实相关性
    metadata: Dict[str, Any] = field(default_factory=dict)


class MockEmbeddingModel:
    """模拟Embedding模型"""
    
    def __init__(self, dimension: int = 64):
        self.dimension = dimension
        random.seed(42)
        self.word_vectors = {}
    
    def embed_text(self, text: str) -> List[float]:
        words = text.lower().split()
        vec = [0.0] * self.dimension
        for word in words:
            if word not in self.word_vectors:
                self.word_vectors[word] = [random.uniform(-1, 1) for _ in range(self.dimension)]
            for i in range(self.dimension):
                vec[i] += self.word_vectors[word][i]
        
        # 归一化
        norm = math.sqrt(sum(x*x for x in vec))
        if norm > 0:
            vec = [x/norm for x in vec]
        return vec


class MockKeywordSearchEngine:
    """模拟关键词检索引擎"""
    
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.inverted_index: Dict[str, List[str]] = defaultdict(list)
    
    def add_document(self, doc: Document):
        self.documents[doc.id] = doc
        words = set(doc.content.lower().split() + doc.title.lower().split())
        for word in words:
            self.inverted_index[word].append(doc.id)
    
    def search(self, query: str, top_k: int = 10) -> Tuple[List[Tuple[str, float]], float]:
        start = time.time()
        query_words = set(query.lower().split())
        
        candidates = set()
        for word in query_words:
            candidates.update(self.inverted_index.get(word, []))
        
        scores = []
        for doc_id in candidates:
            doc = self.documents[doc_id]
            score = sum(1 for w in query_words if w in doc.content.lower())
            scores.append((doc_id, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        latency = time.time() - start
        return scores[:top_k], latency


class MockSemanticSearchEngine:
    """模拟语义检索引擎"""
    
    def __init__(self, embedding_model: MockEmbeddingModel):
        self.embedding_model = embedding_model
        self.documents: Dict[str, Document] = {}
    
    def add_document(self, doc: Document):
        if not doc.vector:
            doc.vector = self.embedding_model.embed_text(doc.content)
        self.documents[doc.id] = doc
    
    def search(self, query: str, top_k: int = 10) -> Tuple[List[Tuple[str, float]], float]:
        start = time.time()
        query_vec = self.embedding_model.embed_text(query)
        
        scores = []
        for doc_id, doc in self.documents.items():
            similarity = sum(a * b for a, b in zip(query_vec, doc.vector))
            scores.append((doc_id, max(0, similarity)))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        latency = time.time() - start
        return scores[:top_k], latency


class MockReranker:
    """模拟重排序模型（Cross-Encoder简化版）"""
    
    def __init__(self, latency_ms: float = 50):
        self.latency_ms = latency_ms
        random.seed(42)
    
    def rerank(self, query: str, candidates: List[Document]) -> List[Tuple[str, float]]:
        """对候选文档进行重排序"""
        # 模拟重排序延迟
        time.sleep(self.latency_ms / 1000.0 * len(candidates) / 10)
        
        scores = []
        for doc in candidates:
            # 模拟更精确的相关性评分
            # 基于文档的预设相关性分数 + 一些随机性
            base_score = doc.relevance_score
            
            # 查询词匹配度
            query_words = set(query.lower().split())
            doc_words = set(doc.content.lower().split())
            overlap = len(query_words & doc_words) / max(len(query_words), 1)
            
            # 最终分数
            score = base_score * 0.6 + overlap * 0.4 + random.uniform(-0.05, 0.05)
            scores.append((doc.id, max(0, min(1, score))))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


class HybridSearchEngine:
    """混合检索引擎"""
    
    def __init__(self, keyword_engine: MockKeywordSearchEngine, 
                 semantic_engine: MockSemanticSearchEngine,
                 reranker: Optional[MockReranker] = None):
        self.keyword_engine = keyword_engine
        self.semantic_engine = semantic_engine
        self.reranker = reranker
    
    def search(self, query: str, top_k: int = 5, use_rerank: bool = True) -> Dict[str, Any]:
        """执行混合检索"""
        result = {
            "query": query,
            "stages": {}
        }
        
        # Stage 1: 关键词检索
        kw_start = time.time()
        kw_results, kw_latency = self.keyword_engine.search(query, top_k=20)
        result["stages"]["keyword"] = {
            "results": kw_results[:5],
            "latency_ms": round(kw_latency * 1000, 3)
        }
        
        # Stage 2: 语义检索
        sem_start = time.time()
        sem_results, sem_latency = self.semantic_engine.search(query, top_k=20)
        result["stages"]["semantic"] = {
            "results": sem_results[:5],
            "latency_ms": round(sem_latency * 1000, 3)
        }
        
        # Stage 3: RRF融合
        rrf_start = time.time()
        rrf_results = self._rrf_fusion(
            [r[0] for r in kw_results],
            [r[0] for r in sem_results],
            k=60
        )
        rrf_latency = time.time() - rrf_start
        result["stages"]["rrf_fusion"] = {
            "results": rrf_results[:10],
            "latency_ms": round(rrf_latency * 1000, 3)
        }
        
        # Stage 4: 重排序（可选）
        if use_rerank and self.reranker:
            rerank_start = time.time()
            
            # 获取候选文档
            candidates = []
            for doc_id, _ in rrf_results[:20]:
                if doc_id in self.keyword_engine.documents:
                    candidates.append(self.keyword_engine.documents[doc_id])
                elif doc_id in self.semantic_engine.documents:
                    candidates.append(self.semantic_engine.documents[doc_id])
            
            reranked = self.reranker.rerank(query, candidates)
            rerank_latency = time.time() - rerank_start
            
            result["stages"]["rerank"] = {
                "results": reranked[:top_k],
                "latency_ms": round(rerank_latency * 1000, 3)
            }
            result["final_results"] = reranked[:top_k]
        else:
            result["final_results"] = rrf_results[:top_k]
        
        # 计算总延迟
        total_latency = sum(s["latency_ms"] for s in result["stages"].values())
        result["total_latency_ms"] = round(total_latency, 3)
        
        return result
    
    def _rrf_fusion(self, keyword_results: List[str], semantic_results: List[str], k: int = 60) -> List[Tuple[str, float]]:
        """RRF融合算法"""
        scores = defaultdict(float)
        
        for rank, doc_id in enumerate(keyword_results):
            scores[doc_id] += 1.0 / (k + rank + 1)
        
        for rank, doc_id in enumerate(semantic_results):
            scores[doc_id] += 1.0 / (k + rank + 1)
        
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def create_test_corpus() -> List[Document]:
    """创建带相关性标注的测试文档库"""
    return [
        Document("doc_001", "Python Programming Guide",
                "Python is a high-level programming language. Great for beginners and professionals.",
                relevance_score=0.9),
        Document("doc_002", "Machine Learning Basics",
                "Machine learning enables computers to learn from data without explicit programming.",
                relevance_score=0.85),
        Document("doc_003", "Deep Learning Tutorial",
                "Deep learning uses neural networks with multiple layers to learn complex patterns.",
                relevance_score=0.8),
        Document("doc_004", "Data Science Handbook",
                "Data science combines statistics, programming, and domain knowledge.",
                relevance_score=0.75),
        Document("doc_005", "AI Ethics Discussion",
                "Ethical considerations in artificial intelligence development and deployment.",
                relevance_score=0.6),
        Document("doc_006", "Cloud Computing Overview",
                "Cloud computing provides on-demand computing resources over the internet.",
                relevance_score=0.5),
        Document("doc_007", "Database Design Principles",
                "Database design involves organizing data according to a database model.",
                relevance_score=0.4),
        Document("doc_008", "Web Development Trends",
                "Modern web development uses frameworks like React, Vue, and Angular.",
                relevance_score=0.3),
        Document("doc_009", "Mobile App Development",
                "Developing applications for mobile devices requires platform-specific knowledge.",
                relevance_score=0.25),
        Document("doc_010", "Cybersecurity Fundamentals",
                "Cybersecurity protects systems, networks, and programs from digital attacks.",
                relevance_score=0.2),
    ]


def test_reranking_effectiveness() -> TestResult:
    """测试1: 重排序效果提升测试"""
    print("\n" + "="*60)
    print("🧪 测试1：重排序效果提升测试")
    print("="*60)
    print("风险：重排序的核心价值是提升Top-K准确性，如果效果不提升则增加延迟无意义")
    
    # 初始化引擎
    embedding_model = MockEmbeddingModel()
    keyword_engine = MockKeywordSearchEngine()
    semantic_engine = MockSemanticSearchEngine(embedding_model)
    
    for doc in create_test_corpus():
        keyword_engine.add_document(doc)
        semantic_engine.add_document(doc)
    
    # 创建带重排序和不带重排序的引擎
    engine_without_rerank = HybridSearchEngine(keyword_engine, semantic_engine, None)
    reranker = MockReranker(latency_ms=30)
    engine_with_rerank = HybridSearchEngine(keyword_engine, semantic_engine, reranker)
    
    test_queries = [
        ("python programming", ["doc_001"]),
        ("machine learning", ["doc_002"]),
        ("deep learning neural networks", ["doc_003"]),
    ]
    
    improvements = []
    details = {"cases": []}
    
    print("\n  对比有无重排序的效果:")
    
    for query, expected_ids in test_queries:
        # 无重排序
        result_no_rerank = engine_without_rerank.search(query, use_rerank=False)
        results_no = [r[0] for r in result_no_rerank["final_results"]]
        
        # 有重排序
        result_with_rerank = engine_with_rerank.search(query, use_rerank=True)
        results_with = [r[0] for r in result_with_rerank["final_results"]]
        
        # 计算期望文档的排名
        rank_no = results_no.index(expected_ids[0]) + 1 if expected_ids[0] in results_no else -1
        rank_with = results_with.index(expected_ids[0]) + 1 if expected_ids[0] in results_with else -1
        
        improvement = "提升" if rank_with < rank_no or (rank_no == -1 and rank_with > 0) else "无变化" if rank_with == rank_no else "下降"
        
        case_detail = {
            "query": query,
            "expected": expected_ids[0],
            "rank_without_rerank": rank_no,
            "rank_with_rerank": rank_with,
            "improvement": improvement
        }
        details["cases"].append(case_detail)
        
        print(f"\n  📝 查询: '{query}'")
        print(f"     期望文档: {expected_ids[0]}")
        print(f"     无重排序: 排名 #{rank_no if rank_no > 0 else '未找到'}")
        print(f"     有重排序: 排名 #{rank_with if rank_with > 0 else '未找到'}")
        print(f"     效果: {improvement}")
        
        if improvement == "提升":
            improvements.append(1)
        elif improvement == "无变化":
            improvements.append(0.5)
        else:
            improvements.append(0)
    
    score = sum(improvements) / len(improvements)
    passed = score >= 0.5
    risk_level = "L2" if score < 0.5 else "L3"
    
    print(f"\n📊 结果: 平均提升得分 {score:.2%}")
    print("💡 建议：重排序应至少提升50%查询的Top-K准确性")
    
    return TestResult("重排序效果", passed, score, risk_level, details)


def test_latency_overhead() -> TestResult:
    """测试2: 延迟开销测试"""
    print("\n" + "="*60)
    print("🧪 测试2：延迟开销测试")
    print("="*60)
    print("风险：重排序增加的延迟如果过高，会影响用户体验甚至导致超时")
    
    embedding_model = MockEmbeddingModel()
    keyword_engine = MockKeywordSearchEngine()
    semantic_engine = MockSemanticSearchEngine(embedding_model)
    
    for doc in create_test_corpus():
        keyword_engine.add_document(doc)
        semantic_engine.add_document(doc)
    
    # 测试不同重排序延迟配置
    latency_configs = [10, 30, 50, 100]  # ms per doc
    
    results = []
    details = {"configs": []}
    
    print("\n  测试不同重排序延迟配置:")
    
    for latency_ms in latency_configs:
        reranker = MockReranker(latency_ms=latency_ms)
        engine = HybridSearchEngine(keyword_engine, semantic_engine, reranker)
        
        # 多次测试取平均
        latencies = []
        for _ in range(5):
            result = engine.search("python programming", use_rerank=True)
            latencies.append(result["total_latency_ms"])
        
        avg_latency = sum(latencies) / len(latencies)
        rerank_stage = result["stages"].get("rerank", {}).get("latency_ms", 0)
        
        config_result = {
            "reranker_latency_per_doc_ms": latency_ms,
            "avg_total_latency_ms": round(avg_latency, 2),
            "rerank_stage_latency_ms": round(rerank_stage, 2)
        }
        details["configs"].append(config_result)
        
        status = "✅" if avg_latency < 500 else "⚠️" if avg_latency < 1000 else "❌"
        print(f"  {status} 重排序延迟 {latency_ms}ms/doc → 总延迟: {avg_latency:.1f}ms (重排序阶段: {rerank_stage:.1f}ms)")
        
        results.append(avg_latency)
    
    avg_overall = sum(results) / len(results)
    score = 1.0 if avg_overall < 200 else 0.8 if avg_overall < 500 else 0.5 if avg_overall < 1000 else 0.2
    passed = avg_overall < 500
    risk_level = "L3" if avg_overall < 200 else "L2" if avg_overall < 500 else "L1"
    
    print(f"\n📊 结果: 平均总延迟 {avg_overall:.1f}ms")
    print("💡 建议：混合检索总延迟应控制在500ms以内，重排序延迟应<200ms")
    
    return TestResult("延迟开销", passed, score, risk_level, details)


def test_end_to_end_pipeline() -> TestResult:
    """测试3: 混合架构端到端测试"""
    print("\n" + "="*60)
    print("🧪 测试3：混合架构端到端测试")
    print("="*60)
    print("风险：端到端流程的召回率和准确性决定了最终用户体验")
    
    embedding_model = MockEmbeddingModel()
    keyword_engine = MockKeywordSearchEngine()
    semantic_engine = MockSemanticSearchEngine(embedding_model)
    
    for doc in create_test_corpus():
        keyword_engine.add_document(doc)
        semantic_engine.add_document(doc)
    
    reranker = MockReranker(latency_ms=30)
    engine = HybridSearchEngine(keyword_engine, semantic_engine, reranker)
    
    test_cases = [
        ("python programming", ["doc_001"]),
        ("machine learning", ["doc_002"]),
        ("deep learning", ["doc_003"]),
        ("data science", ["doc_004"]),
        ("artificial intelligence", ["doc_002", "doc_003", "doc_005"]),
    ]
    
    recall_scores = []
    details = {"cases": []}
    
    print("\n  测试端到端召回效果:")
    
    for query, expected_ids in test_cases:
        result = engine.search(query, use_rerank=True)
        final_results = [r[0] for r in result["final_results"]]
        
        # 计算召回
        found = sum(1 for eid in expected_ids if eid in final_results)
        recall = found / len(expected_ids)
        
        # 计算精确度（假设Top-5）
        precision = found / len(final_results) if final_results else 0
        
        case_detail = {
            "query": query,
            "expected": expected_ids,
            "found": [fid for fid in final_results if fid in expected_ids],
            "recall": round(recall, 2),
            "precision": round(precision, 2),
            "total_latency_ms": result["total_latency_ms"]
        }
        details["cases"].append(case_detail)
        
        status = "✅" if recall >= 0.8 else "⚠️" if recall >= 0.5 else "❌"
        print(f"  {status} '{query}' → 召回: {recall:.0%}, 精确: {precision:.0%}, 延迟: {result['total_latency_ms']:.1f}ms")
        
        recall_scores.append(recall)
    
    avg_recall = sum(recall_scores) / len(recall_scores)
    score = avg_recall
    passed = avg_recall >= 0.7
    risk_level = "L1" if avg_recall < 0.5 else "L2" if avg_recall < 0.7 else "L3"
    
    details["summary"] = {"avg_recall": round(avg_recall, 2)}
    
    print(f"\n📊 结果: 平均召回率 {avg_recall:.2%}")
    print("💡 建议：端到端召回率应>70%，理想情况下>80%")
    
    return TestResult("端到端流程", passed, score, risk_level, details)


def test_edge_cases() -> TestResult:
    """测试4: 异常场景处理测试"""
    print("\n" + "="*60)
    print("🧪 测试4：异常场景处理测试")
    print("="*60)
    print("风险：异常场景处理不当会导致系统崩溃或返回错误结果")
    
    embedding_model = MockEmbeddingModel()
    keyword_engine = MockKeywordSearchEngine()
    semantic_engine = MockSemanticSearchEngine(embedding_model)
    
    for doc in create_test_corpus():
        keyword_engine.add_document(doc)
        semantic_engine.add_document(doc)
    
    reranker = MockReranker(latency_ms=30)
    engine = HybridSearchEngine(keyword_engine, semantic_engine, reranker)
    
    edge_cases = [
        ("", "空查询"),
        ("xyz123nonexistent", "无结果查询"),
        ("python " * 100, "超长查询"),
        ("!@#$%^&*()", "特殊字符查询"),
    ]
    
    handled_count = 0
    details = {"cases": []}
    
    print("\n  测试异常场景处理:")
    
    for query, desc in edge_cases:
        try:
            result = engine.search(query, use_rerank=True)
            has_results = len(result["final_results"]) > 0
            no_error = True
        except Exception as e:
            has_results = False
            no_error = False
        
        case_detail = {
            "query": query[:50] + "..." if len(query) > 50 else query,
            "description": desc,
            "handled": no_error,
            "has_results": has_results
        }
        details["cases"].append(case_detail)
        
        status = "✅" if no_error else "❌"
        print(f"  {status} {desc}: {'正常处理' if no_error else '异常'}, 返回结果: {has_results}")
        
        if no_error:
            handled_count += 1
    
    score = handled_count / len(edge_cases)
    passed = score >= 0.75
    risk_level = "L1" if score < 0.5 else "L2" if score < 0.75 else "L3"
    
    print(f"\n📊 结果: {handled_count}/{len(edge_cases)} 场景正常处理")
    print("💡 建议：所有异常场景都应优雅处理，不抛出未捕获异常")
    
    return TestResult("异常场景处理", passed, score, risk_level, details)


def test_reranking_strategies() -> TestResult:
    """测试5: 不同重排序策略对比"""
    print("\n" + "="*60)
    print("🧪 测试5：不同重排序策略对比")
    print("="*60)
    print("风险：不同场景需要不同的重排序策略，选型错误会影响效果或成本")
    
    embedding_model = MockEmbeddingModel()
    keyword_engine = MockKeywordSearchEngine()
    semantic_engine = MockSemanticSearchEngine(embedding_model)
    
    for doc in create_test_corpus():
        keyword_engine.add_document(doc)
        semantic_engine.add_document(doc)
    
    # 不同延迟配置模拟不同策略
    strategies = {
        "轻量级CE (10ms/doc)": MockReranker(latency_ms=10),
        "标准CE (30ms/doc)": MockReranker(latency_ms=30),
        "高精度CE (100ms/doc)": MockReranker(latency_ms=100),
    }
    
    query = "machine learning python"
    
    results = []
    details = {"strategies": []}
    
    print(f"\n  对比不同策略处理查询 '{query}':")
    
    for name, reranker in strategies.items():
        engine = HybridSearchEngine(keyword_engine, semantic_engine, reranker)
        result = engine.search(query, use_rerank=True)
        
        final_results = result["final_results"]
        top3 = [r[0] for r in final_results[:3]]
        total_latency = result["total_latency_ms"]
        rerank_latency = result["stages"].get("rerank", {}).get("latency_ms", 0)
        
        strategy_result = {
            "name": name,
            "top3_results": top3,
            "total_latency_ms": round(total_latency, 2),
            "rerank_latency_ms": round(rerank_latency, 2)
        }
        details["strategies"].append(strategy_result)
        
        print(f"\n  📊 {name}:")
        print(f"     Top3: {top3}")
        print(f"     总延迟: {total_latency:.1f}ms (重排序: {rerank_latency:.1f}ms)")
        
        # 评分：延迟越低越好，但效果也要考虑
        latency_score = 1.0 if total_latency < 200 else 0.7 if total_latency < 500 else 0.4
        results.append(latency_score)
    
    score = sum(results) / len(results)
    passed = score >= 0.6
    risk_level = "L3" if score >= 0.8 else "L2"
    
    print(f"\n📊 结果: 策略对比完成")
    print("💡 建议：")
    print("   - 实时场景：轻量级CE (10-30ms)")
    print("   - 高精度场景：高精度CE或LLM-based")
    print("   - 平衡场景：标准CE (30-50ms)")
    
    return TestResult("重排序策略对比", passed, score, risk_level, details)


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📋 Day 33 测试汇总报告 - 重排序优化与混合架构实战测试")
    print("="*70)
    
    total_score = sum(r.score for r in results) / len(results)
    passed_count = sum(1 for r in results if r.passed)
    high_risk_count = sum(1 for r in results if r.risk_level == "L1")
    
    print(f"\n📊 总体得分: {total_score:.2%}")
    print(f"✅ 通过测试: {passed_count}/{len(results)}")
    print(f"🔴 高风险项: {high_risk_count}个")
    
    print("\n📋 详细结果:")
    print("-" * 70)
    print(f"{'测试项':<20} {'状态':<8} {'得分':<10} {'风险等级':<10}")
    print("-" * 70)
    
    for r in results:
        status = "✅ 通过" if r.passed else "❌ 失败"
        risk_emoji = "🔴" if r.risk_level == "L1" else "🟡" if r.risk_level == "L2" else "🟢"
        print(f"{r.name:<20} {status:<8} {r.score:<10.2%} {risk_emoji} {r.risk_level}")
    
    print("-" * 70)
    
    print("\n🎯 风险等级说明:")
    print("   🔴 L1 - 高风险：可能导致线上故障，需立即修复")
    print("   🟡 L2 - 中风险：存在潜在问题，建议优化")
    print("   🟢 L3 - 低风险：表现良好，可接受")
    
    print("\n🔍 关键发现:")
    if high_risk_count > 0:
        high_risk_tests = [r.name for r in results if r.risk_level == "L1"]
        print(f"   ⚠️ 发现 {high_risk_count} 个高风险项: {', '.join(high_risk_tests)}")
    else:
        print("   ✅ 混合检索架构表现良好")
    
    print("\n💡 混合检索架构最佳实践:")
    print("   1. 分层架构：关键词(<5ms) → 语义(50-100ms) → 重排序(100-500ms)")
    print("   2. 降级策略：重排序超时时回退到RRF结果")
    print("   3. 监控指标：召回率@K、NDCG@K、延迟P99")
    print("\n" + "="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 33: 重排序优化与混合架构实战测试")
    print("="*70)
    print("\n测试架构师视角：验证重排序对混合检索效果的提升，测量延迟开销，测试端到端流程")
    
    results = [
        test_reranking_effectiveness(),
        test_latency_overhead(),
        test_end_to_end_pipeline(),
        test_edge_cases(),
        test_reranking_strategies(),
    ]
    
    print_summary(results)
    
    output = {
        "day": 33,
        "theme": "重排序优化与混合架构实战测试",
        "summary": {
            "total_score": sum(r.score for r in results) / len(results),
            "passed": sum(1 for r in results if r.passed),
            "total": len(results),
            "high_risk": sum(1 for r in results if r.risk_level == "L1")
        },
        "details": [
            {
                "name": r.name,
                "passed": r.passed,
                "score": r.score,
                "risk_level": r.risk_level,
                "details": r.details
            }
            for r in results
        ]
    }
    
    with open("day33_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n💾 详细结果已保存至 day33_results.json")
    print("📤 请将上方日志贴回给 Trae 生成 report_day33.md")


if __name__ == "__main__":
    run_all_tests()
