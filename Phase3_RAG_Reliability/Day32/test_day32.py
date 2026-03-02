"""
Day 32: 语义检索（密集检索）进阶测试
目标：验证语义检索的同义词召回、概念关联和向量相似度校准能力
测试架构师视角：语义检索是混合架构的核心能力，向量空间对齐失败将导致"语义漂移"
难度级别：进阶
"""

import json
import time
import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
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
    metadata: Dict[str, Any] = field(default_factory=dict)


class MockEmbeddingModel:
    """模拟Embedding模型（基于词袋 + SVD降维的简化实现）"""
    
    def __init__(self, dimension: int = 64):
        self.dimension = dimension
        self.vocab = {}
        self.embeddings = {}
        self._build_vocab()
    
    def _build_vocab(self):
        # 构建词表和预定义词向量
        self.vocab = {
            # 同义词组
            "笔记本": 0, "laptop": 0, "手提电脑": 0, "notebook": 0,
            "购买": 1, "采购": 1, "买": 1, " acquire": 1,
            "手机": 2, "mobile": 2, "智能手机": 2, "cellphone": 2,
            
            # 概念组
            "深度学习": 10, "神经网络": 10, "deep learning": 10, "neural network": 10,
            "机器学习": 11, "machine learning": 11, "ml": 11,
            "人工智能": 12, "ai": 12, "artificial intelligence": 12,
            "transformer": 13, "注意力机制": 13, "attention": 13,
            
            # 跨语言组
            "机器学习": 20, "machine learning": 20,
            "深度学习": 21, "deep learning": 21,
            "人工智能": 22, "artificial intelligence": 22,
            
            # 其他
            "python": 30, "编程": 30, "程序": 30,
            "gpt": 40, "语言模型": 40, "llm": 40,
        }
        
        # 为每个词生成随机向量（同一组的向量方向相似）
        random.seed(42)
        for word, group_id in self.vocab.items():
            base = self._get_group_vector(group_id)
            noise = [random.uniform(-0.1, 0.1) for _ in range(self.dimension)]
            vec = [b + n for b, n in zip(base, noise)]
            # 归一化
            norm = math.sqrt(sum(x*x for x in vec))
            self.embeddings[word] = [x/norm for x in vec]
    
    def _get_group_vector(self, group_id: int) -> List[float]:
        """生成组内基准向量"""
        random.seed(group_id)
        return [random.uniform(-1, 1) for _ in range(self.dimension)]
    
    def embed_text(self, text: str) -> List[float]:
        """将文本转换为向量（词袋平均）"""
        words = text.lower().split()
        vectors = []
        
        for word in words:
            if word in self.embeddings:
                vectors.append(self.embeddings[word])
        
        if not vectors:
            # 返回随机向量
            return [random.uniform(-0.1, 0.1) for _ in range(self.dimension)]
        
        # 平均
        avg_vec = [0.0] * self.dimension
        for vec in vectors:
            avg_vec = [a + b for a, b in zip(avg_vec, vec)]
        avg_vec = [x / len(vectors) for x in avg_vec]
        
        # 归一化
        norm = math.sqrt(sum(x*x for x in avg_vec))
        if norm > 0:
            avg_vec = [x/norm for x in avg_vec]
        
        return avg_vec


class MockSemanticSearchEngine:
    """模拟语义检索引擎（基于向量相似度）"""
    
    def __init__(self, embedding_model: MockEmbeddingModel):
        self.embedding_model = embedding_model
        self.documents: Dict[str, Document] = {}
    
    def add_document(self, doc: Document):
        if not doc.vector:
            doc.vector = self.embedding_model.embed_text(doc.content)
        self.documents[doc.id] = doc
    
    def search(self, query: str, top_k: int = 5) -> Tuple[List[Tuple[str, float]], float]:
        """语义检索"""
        start_time = time.time()
        
        query_vector = self.embedding_model.embed_text(query)
        
        # 计算与所有文档的相似度
        scores = []
        for doc_id, doc in self.documents.items():
            similarity = self._cosine_similarity(query_vector, doc.vector)
            scores.append((doc_id, similarity))
        
        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)
        latency = time.time() - start_time
        
        return scores[:top_k], latency
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        return max(0, min(1, dot_product))  # 限制在[0,1]


def create_test_corpus() -> List[Document]:
    """创建测试文档库"""
    return [
        Document("doc_001", "Laptop Product Guide",
                "This laptop features 16GB RAM, 512GB SSD. Perfect for programming and data analysis."),
        Document("doc_002", "Mobile Phone Manual",
                "Smartphone with 6.7 inch display, 256GB storage. Great camera and long battery life."),
        Document("doc_003", "Deep Learning Tutorial",
                "Neural networks are computing systems inspired by biological neural networks. "
                "Deep learning uses multiple layers of neural networks."),
        Document("doc_004", "Machine Learning Fundamentals",
                "Machine learning is a subset of artificial intelligence that enables systems to learn "
                "from data without being explicitly programmed."),
        Document("doc_005", "Python Programming Book",
                "Python is a high-level programming language. Great for beginners and professionals alike."),
        Document("doc_006", "AI Introduction",
                "Artificial Intelligence (AI) is intelligence demonstrated by machines, as opposed to "
                "natural intelligence displayed by humans."),
        Document("doc_007", "Transformer Architecture",
                "The Transformer is a deep learning architecture based on the attention mechanism. "
                "Used in BERT and GPT models."),
        Document("doc_008", "Computer Purchase Guide",
                "When buying a computer, consider your needs: programming, gaming, or general use. "
                "Laptops and desktops both have their advantages."),
        Document("doc_009", "Neural Network Deep Dive",
                "Deep neural networks consist of multiple hidden layers. They can learn complex patterns "
                "from large amounts of data."),
        Document("doc_010", "Cell Phone Buying Tips",
                "Smartphone buying guide: consider processor, camera quality, battery life, and storage capacity."),
    ]


def test_synonym_recall() -> TestResult:
    """测试1: 同义词召回测试"""
    print("\n" + "="*60)
    print("🧪 测试1：同义词召回测试")
    print("="*60)
    print("风险：语义检索的核心价值在于跨越词汇鸿沟，同义词召回失败会严重影响用户体验")
    
    embedding_model = MockEmbeddingModel()
    engine = MockSemanticSearchEngine(embedding_model)
    
    for doc in create_test_corpus():
        engine.add_document(doc)
    
    test_cases = [
        ("laptop", ["doc_001", "doc_008"]),  # 英文
        ("笔记本", ["doc_001", "doc_008"]),  # 中文
        ("购买电脑", ["doc_001", "doc_008"]),  # 同义表达
        ("smartphone", ["doc_002", "doc_010"]),  # 手机
        ("手机", ["doc_002", "doc_010"]),  # 中文手机
    ]
    
    passed_count = 0
    details = {"cases": []}
    
    for query, expected_ids in test_cases:
        results, _ = engine.search(query, top_k=5)
        found_ids = [r[0] for r in results]
        
        # 检查期望文档是否在top结果中
        found = sum(1 for eid in expected_ids if eid in found_ids)
        
        case_detail = {
            "query": query,
            "expected": expected_ids,
            "found": found_ids[:5],
            "match_count": found
        }
        details["cases"].append(case_detail)
        
        status = "✅" if found >= 1 else "❌"
        print(f"  {status} 查询 '{query}' → 期望: {expected_ids}, 匹配: {found}/{len(expected_ids)}")
        print(f"      Top结果: {found_ids[:3]}")
        
        if found >= 1:
            passed_count += 1
    
    score = passed_count / len(test_cases)
    passed = score >= 0.7
    risk_level = "L1" if score < 0.5 else "L2" if score < 0.7 else "L3"
    
    print(f"\n📊 结果: {passed_count}/{len(test_cases)} 通过, 得分: {score:.2%}")
    print("💡 建议：同义词召回是语义检索的核心能力，需持续优化词表覆盖")
    
    return TestResult("同义词召回", passed, score, risk_level, details)


def test_concept_association() -> TestResult:
    """测试2: 概念关联测试"""
    print("\n" + "="*60)
    print("🧪 测试2：概念关联测试")
    print("="*60)
    print("风险：概念关联能力体现了语义检索的理解深度，缺失会导致概念查询失败")
    
    embedding_model = MockEmbeddingModel()
    engine = MockSemanticSearchEngine(embedding_model)
    
    for doc in create_test_corpus():
        engine.add_document(doc)
    
    test_cases = [
        ("深度学习", ["doc_003", "doc_009"]),  # 概念→具体
        ("neural network", ["doc_003", "doc_009"]),  # 英文概念
        ("机器学习", ["doc_004", "doc_003"]),  # 上位概念
        ("人工智能", ["doc_004", "doc_006"]),  # 更上位概念
        ("transformer", ["doc_007"]),  # 技术术语
    ]
    
    passed_count = 0
    details = {"cases": []}
    
    for query, expected_ids in test_cases:
        results, _ = engine.search(query, top_k=5)
        found_ids = [r[0] for r in results]
        
        found = sum(1 for eid in expected_ids if eid in found_ids)
        
        case_detail = {
            "query": query,
            "expected": expected_ids,
            "found": found_ids[:5],
            "match_count": found
        }
        details["cases"].append(case_detail)
        
        status = "✅" if found >= 1 else "❌"
        print(f"  {status} 查询 '{query}' → 期望: {expected_ids}, 匹配: {found}/{len(expected_ids)}")
        print(f"      Top结果: {found_ids[:3]}")
        
        if found >= 1:
            passed_count += 1
    
    score = passed_count / len(test_cases)
    passed = score >= 0.7
    risk_level = "L1" if score < 0.4 else "L2" if score < 0.7 else "L3"
    
    print(f"\n📊 结果: {passed_count}/{len(test_cases)} 通过, 得分: {score:.2%}")
    print("💡 建议：概念关联需要高质量的Embedding模型，建议使用专业领域模型")
    
    return TestResult("概念关联", passed, score, risk_level, details)


def test_cross_language_alignment() -> TestResult:
    """测试3: 跨语言语义对齐测试"""
    print("\n" + "="*60)
    print("🧪 测试3：跨语言语义对齐测试")
    print("="*60)
    print("风险：跨语言检索失败会限制多语言知识库的应用")
    
    embedding_model = MockEmbeddingModel()
    engine = MockSemanticSearchEngine(embedding_model)
    
    for doc in create_test_corpus():
        engine.add_document(doc)
    
    test_cases = [
        ("机器学习", "machine learning", ["doc_004"]),
        ("深度学习", "deep learning", ["doc_003"]),
        ("人工智能", "AI", ["doc_006"]),
    ]
    
    passed_count = 0
    details = {"cases": []}
    
    print("\n  测试中英文查询是否能召回相同文档:")
    
    for cn_query, en_query, expected_ids in test_cases:
        cn_results, _ = engine.search(cn_query, top_k=5)
        en_results, _ = engine.search(en_query, top_k=5)
        
        cn_ids = [r[0] for r in cn_results]
        en_ids = [r[0] for r in en_results]
        
        # 检查结果重叠度
        overlap = set(cn_ids) & set(en_ids)
        
        case_detail = {
            "cn_query": cn_query,
            "en_query": en_query,
            "cn_results": cn_ids[:3],
            "en_results": en_ids[:3],
            "overlap": list(overlap)
        }
        details["cases"].append(case_detail)
        
        status = "✅" if len(overlap) >= 1 else "❌"
        print(f"  {status} '{cn_query}' vs '{en_query}'")
        print(f"      中文Top3: {cn_ids[:3]}, 英文Top3: {en_ids[:3]}")
        print(f"      重叠: {list(overlap)}")
        
        if len(overlap) >= 1:
            passed_count += 1
    
    score = passed_count / len(test_cases)
    passed = score >= 0.7
    risk_level = "L1" if score < 0.5 else "L2" if score < 0.7 else "L3"
    
    print(f"\n📊 结果: {passed_count}/{len(test_cases)} 通过, 得分: {score:.2%}")
    print("💡 建议：跨语言能力依赖Embedding模型，需使用多语言模型如mBERT或XLM-RoBERTa")
    
    return TestResult("跨语言对齐", passed, score, risk_level, details)


def test_similarity_calibration() -> TestResult:
    """测试4: 向量相似度校准测试"""
    print("\n" + "="*60)
    print("🧪 测试4：向量相似度校准测试")
    print("="*60)
    print("风险：相似度分数与实际相关性不匹配会导致排序错误")
    
    embedding_model = MockEmbeddingModel()
    engine = MockSemanticSearchEngine(embedding_model)
    
    for doc in create_test_corpus():
        engine.add_document(doc)
    
    test_queries = [
        "python programming",
        "machine learning",
        "laptop buy",
    ]
    
    print("\n  验证相似度分数的排序合理性:")
    
    calibration_scores = []
    details = {"cases": []}
    
    for query in test_queries:
        results, _ = engine.search(query, top_k=5)
        
        # 检查：
        # 1. 相似度是否递减
        # 2. 最高分是否合理（>0.5对于高度相关的文档）
        similarities = [r[1] for r in results]
        
        is_monotonic = all(similarities[i] >= similarities[i+1] for i in range(len(similarities)-1))
        max_similarity = similarities[0] if similarities else 0
        
        case_detail = {
            "query": query,
            "similarities": similarities,
            "is_monotonic": is_monotonic,
            "max_similarity": max_similarity
        }
        details["cases"].append(case_detail)
        
        status = "✅" if is_monotonic else "⚠️"
        print(f"  {status} 查询 '{query}'")
        print(f"      相似度: {[round(s, 3) for s in similarities[:5]]}")
        print(f"      单调递减: {is_monotonic}, 最高分: {max_similarity:.3f}")
        
        if is_monotonic and max_similarity > 0.3:
            calibration_scores.append(1)
        elif is_monotonic or max_similarity > 0.3:
            calibration_scores.append(0.5)
        else:
            calibration_scores.append(0)
    
    score = sum(calibration_scores) / len(calibration_scores)
    passed = score >= 0.7
    risk_level = "L2" if score < 0.7 else "L3"
    
    print(f"\n📊 结果: 校准得分: {score:.2%}")
    print("💡 建议：定期校准相似度阈值，建立分数与相关性的映射关系")
    
    return TestResult("相似度校准", passed, score, risk_level, details)


def test_keyword_vs_semantic_comparison() -> TestResult:
    """测试5: 与关键词检索对比测试"""
    print("\n" + "="*60)
    print("🧪 测试5：关键词检索 vs 语义检索对比测试")
    print("="*60)
    print("风险：混合架构需要清楚两种检索方式的互补性，否则无法合理分配权重")
    
    # 导入Day31的关键词检索引擎
    import sys
    sys.path.insert(0, r'd:\project\AI-QA-60Days\Phase3_RAG_Reliability\Day31')
    from test_day31 import MockKeywordSearchEngine, create_test_corpus as create_keyword_corpus
    
    # 准备两个引擎
    keyword_engine = MockKeywordSearchEngine()
    semantic_engine = MockSemanticSearchEngine(MockEmbeddingModel())
    
    # 各自加载文档
    keyword_corpus = create_keyword_corpus()
    semantic_corpus = create_test_corpus()
    
    for doc in keyword_corpus:
        keyword_engine.add_document(doc)
    
    for doc in semantic_corpus:
        semantic_engine.add_document(doc)
    
    test_queries = [
        ("gpt-4-0314", ["doc_001"]),  # 精确ID，关键词强
        ("laptop", ["doc_001", "doc_008"]),  # 同义词，语义强
        ("Python编程", ["doc_005"]),  # 跨语言
        ("深度学习神经网络", ["doc_003", "doc_009"]),  # 概念
    ]
    
    results_comparison = []
    details = {"cases": []}
    
    print("\n  对比两种检索方式的效果差异:")
    
    for query, expected_ids in test_queries:
        kw_results, kw_latency = keyword_engine.search(query, top_k=5)
        sem_results, sem_latency = semantic_engine.search(query, top_k=5)
        
        kw_ids = [r[0] for r in kw_results]
        sem_ids = [r[0] for r in sem_results]
        
        # 计算各自的召回
        kw_found = sum(1 for eid in expected_ids if eid in kw_ids)
        sem_found = sum(1 for eid in expected_ids if eid in sem_ids)
        
        # 合并结果（RRF）
        combined = rrf_fusion(kw_ids, sem_ids)
        combined_ids = [r[0] for r in combined]
        combined_found = sum(1 for eid in expected_ids if eid in combined_ids)
        
        comparison = {
            "query": query,
            "expected": expected_ids,
            "keyword_found": kw_found,
            "semantic_found": sem_found,
            "combined_found": combined_found,
            "keyword_latency_ms": round(kw_latency * 1000, 3),
            "semantic_latency_ms": round(sem_latency * 1000, 3)
        }
        details["cases"].append(comparison)
        
        print(f"\n  📝 查询: '{query}'")
        print(f"     期望: {expected_ids}")
        print(f"     🔑 关键词检索: 命中{kw_found}, 延迟{kw_latency*1000:.1f}ms, Top3: {kw_ids[:3]}")
        print(f"     🧠 语义检索: 命中{sem_found}, 延迟{sem_latency*1000:.1f}ms, Top3: {sem_ids[:3]}")
        print(f"     🔀 混合(混合): 命中{combined_found}, Top3: {combined_ids[:3]}")
        
        results_comparison.append({
            "kw": kw_found,
            "sem": sem_found,
            "combined": combined_found
        })
    
    # 计算混合检索的优势
    kw_total = sum(r["kw"] for r in results_comparison)
    sem_total = sum(r["sem"] for r in results_comparison)
    combined_total = sum(r["combined"] for r in results_comparison)
    
    score = combined_total / (kw_total + sem_total + 0.1) * 2  # 鼓励混合优于单一
    passed = combined_total >= kw_total and combined_total >= sem_total
    risk_level = "L3" if combined_total > max(kw_total, sem_total) else "L2"
    
    details["summary"] = {
        "keyword_total": kw_total,
        "semantic_total": sem_total,
        "combined_total": combined_total
    }
    
    print(f"\n📊 结果汇总:")
    print(f"   关键词检索总命中: {kw_total}")
    print(f"   语义检索总命中: {sem_total}")
    print(f"   混合检索总命中: {combined_total}")
    
    return TestResult("关键词vs语义对比", passed, score, risk_level, details)


def rrf_fusion(keyword_results: List[str], semantic_results: List[str], k: int = 60) -> List[Tuple[str, float]]:
    """RRF (Reciprocal Rank Fusion) 混合排序"""
    scores = defaultdict(float)
    
    for rank, doc_id in enumerate(keyword_results):
        scores[doc_id] += 1.0 / (k + rank + 1)
    
    for rank, doc_id in enumerate(semantic_results):
        scores[doc_id] += 1.0 / (k + rank + 1)
    
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📋 Day 32 测试汇总报告 - 语义检索（密集检索）进阶测试")
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
        print("   ✅ 语义检索核心能力表现良好")
    
    print("\n💡 下一步建议:")
    print("   1. 运行 Day 33 重排序优化测试，验证混合架构的最终效果")
    print("   2. 根据对比结果，调整 Day 31/32 的权重配置")
    print("\n" + "="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 32: 语义检索（密集检索）进阶测试")
    print("="*70)
    print("\n测试架构师视角：验证语义检索的同义词召回、概念关联和向量相似度校准能力")
    
    results = [
        test_synonym_recall(),
        test_concept_association(),
        test_cross_language_alignment(),
        test_similarity_calibration(),
        test_keyword_vs_semantic_comparison(),
    ]
    
    print_summary(results)
    
    output = {
        "day": 32,
        "theme": "语义检索（密集检索）进阶测试",
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
    
    with open("day32_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n💾 详细结果已保存至 day32_results.json")
    print("📤 请将上方日志贴回给 Trae 生成 report_day32.md")


if __name__ == "__main__":
    run_all_tests()
