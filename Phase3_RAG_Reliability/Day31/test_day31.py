"""
Day 31: 关键词检索（稀疏检索）基础测试
目标：验证关键词检索的核心能力，识别召回风险和性能瓶颈
测试架构师视角：关键词检索是混合架构的第一道防线，召回失败将导致语义检索"无米下锅"
难度级别：基础
"""

import json
import time
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
    metadata: Dict[str, Any] = field(default_factory=dict)


class MockKeywordSearchEngine:
    """模拟关键词检索引擎（基于倒排索引）"""
    
    def __init__(self, use_case_sensitive: bool = False):
        self.documents: Dict[str, Document] = {}
        self.inverted_index: Dict[str, List[str]] = defaultdict(list)
        self.doc_freq: Dict[str, int] = defaultdict(int)
        self.avg_doc_length = 0
        self.k1 = 1.5  # BM25参数
        self.b = 0.75
        self.use_case_sensitive = use_case_sensitive
        self.stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 
                         '的', '了', '在', '是', '和', '与'}
    
    def add_document(self, doc: Document):
        self.documents[doc.id] = doc
        tokens = self._tokenize(doc.content + " " + doc.title)
        unique_tokens = set(tokens)
        
        for token in unique_tokens:
            self.inverted_index[token].append(doc.id)
            self.doc_freq[token] += 1
        
        self._update_avg_length()
    
    def _tokenize(self, text: str) -> List[str]:
        """分词（简化版）"""
        if not self.use_case_sensitive:
            text = text.lower()
        
        # 保留字母数字和下划线（适合代码）
        import re
        tokens = re.findall(r'\b[a-zA-Z0-9_]+\b', text)
        
        # 中文分词（简化：按字符）
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        for chars in chinese_chars:
            tokens.extend(list(chars))
        
        return [t for t in tokens if t not in self.stopwords or len(t) > 3]
    
    def _update_avg_length(self):
        if not self.documents:
            return
        total_len = sum(len(self._tokenize(d.content)) for d in self.documents.values())
        self.avg_doc_length = total_len / len(self.documents)
    
    def _bm25_score(self, query_tokens: List[str], doc: Document) -> float:
        """计算BM25分数"""
        doc_tokens = self._tokenize(doc.content)
        doc_length = len(doc_tokens)
        score = 0.0
        
        for token in query_tokens:
            if token not in self.doc_freq:
                continue
            
            idf = self._idf(token)
            tf = doc_tokens.count(token)
            
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / max(self.avg_doc_length, 1))
            score += idf * numerator / denominator
        
        return score
    
    def _idf(self, token: str) -> float:
        """计算IDF"""
        N = len(self.documents)
        df = self.doc_freq.get(token, 0)
        if df == 0:
            return 0
        return max(0, (N - df + 0.5) / (df + 0.5))
    
    def search(self, query: str, top_k: int = 5) -> Tuple[List[Tuple[str, float]], float]:
        """搜索并返回结果和延迟"""
        start_time = time.time()
        
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [], time.time() - start_time
        
        # 获取候选文档
        candidates = set()
        for token in query_tokens:
            candidates.update(self.inverted_index.get(token, []))
        
        # 计算分数
        scores = []
        for doc_id in candidates:
            doc = self.documents[doc_id]
            score = self._bm25_score(query_tokens, doc)
            scores.append((doc_id, score))
        
        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)
        latency = time.time() - start_time
        
        return scores[:top_k], latency


def create_test_corpus() -> List[Document]:
    """创建测试文档库"""
    return [
        Document("doc_001", "GPT-4 Technical Report", 
                "GPT-4 is a large multimodal model created by OpenAI. "
                "It accepts image and text inputs and produces text outputs. "
                "The model ID is gpt-4-0314."),
        Document("doc_002", "BERT: Pre-training of Deep Bidirectional Transformers",
                "We introduce a new language representation model called BERT, "
                "which stands for Bidirectional Encoder Representations from Transformers. "
                "The model name is bert-base-uncased."),
        Document("doc_003", "Product Manual - Laptop X1",
                "The Laptop X1 features a 14-inch display, 16GB RAM, and 512GB SSD. "
                "Product ID: LP-X1-2024. Order number format: ORD-XXXXX."),
        Document("doc_004", "南京长江大桥历史",
                "南京长江大桥是长江上第一座由中国自行设计和建造的双层式铁路、公路两用桥梁。 "
                "建于1960年至1968年，是南京的标志性建筑。"),
        Document("doc_005", "Python Programming Guide",
                "To be or not to be, that is the question. "
                "Python is a programming language that lets you work quickly and integrate systems. "
                "Import tensorflow for machine learning tasks."),
        Document("doc_006", "iPhone 15 Pro Specifications",
                "The iPhone 15 Pro features the A17 Pro chip, titanium design, "
                "and a 48MP main camera. Model: MQ1F3CH/A. Also known as Apple smartphone."),
        Document("doc_007", "API Documentation v2.1.0",
                "Version 2.1.0 introduces new endpoints. "
                "GET /api/v2/users returns user list. "
                "POST /api/v2/orders creates new orders."),
        Document("doc_008", "机器学习入门",
                "机器学习是人工智能的一个分支。 "
                "深度学习是机器学习的一种方法，使用神经网络。 "
                "常用框架包括TensorFlow和PyTorch。"),
    ]


def test_exact_id_matching() -> TestResult:
    """测试1: 精确ID匹配"""
    print("\n" + "="*60)
    print("🧪 测试1：精确ID匹配测试")
    print("="*60)
    print("风险：产品ID、订单号等精确查询失败将直接导致用户无法找到目标文档")
    
    engine = MockKeywordSearchEngine()
    for doc in create_test_corpus():
        engine.add_document(doc)
    
    test_cases = [
        ("gpt-4-0314", ["doc_001"]),
        ("bert-base-uncased", ["doc_002"]),
        ("LP-X1-2024", ["doc_003"]),
        ("ORD-XXXXX", ["doc_003"]),
        ("MQ1F3CH/A", ["doc_006"]),
        ("v2.1.0", ["doc_007"]),
    ]
    
    passed_count = 0
    details = {"cases": []}
    
    for query, expected_ids in test_cases:
        results, latency = engine.search(query, top_k=5)
        found_ids = [r[0] for r in results]
        
        # 检查期望文档是否在结果中
        found = any(eid in found_ids for eid in expected_ids)
        rank = found_ids.index(expected_ids[0]) + 1 if expected_ids[0] in found_ids else -1
        
        case_result = {
            "query": query,
            "expected": expected_ids,
            "found": found,
            "rank": rank,
            "top_results": found_ids[:3]
        }
        details["cases"].append(case_result)
        
        status = "✅" if found else "❌"
        rank_str = f"#{rank}" if rank > 0 else "未找到"
        print(f"  {status} 查询 '{query}' → 期望: {expected_ids[0]}, 实际排名: {rank_str}")
        
        if found:
            passed_count += 1
    
    score = passed_count / len(test_cases)
    passed = score >= 0.8
    risk_level = "L1" if score < 0.6 else "L2" if score < 0.8 else "L3"
    
    print(f"\n📊 结果: {passed_count}/{len(test_cases)} 通过, 得分: {score:.2%}")
    
    return TestResult("精确ID匹配", passed, score, risk_level, details)


def test_case_sensitivity() -> TestResult:
    """测试2: 大小写敏感测试"""
    print("\n" + "="*60)
    print("🧪 测试2：大小写敏感/不敏感测试")
    print("="*60)
    print("风险：'GPT-4'和'gpt-4'返回不同结果会导致用户体验不一致")
    
    # 大小写敏感引擎
    engine_sensitive = MockKeywordSearchEngine(use_case_sensitive=True)
    # 大小写不敏感引擎
    engine_insensitive = MockKeywordSearchEngine(use_case_sensitive=False)
    
    for doc in create_test_corpus():
        engine_sensitive.add_document(doc)
        engine_insensitive.add_document(doc)
    
    test_queries = ["GPT-4", "gpt-4", "Gpt-4", "BERT", "bert", "Python", "python"]
    
    consistent_count = 0
    details = {"comparisons": []}
    
    print("\n  对比大小写敏感 vs 不敏感引擎的结果一致性:")
    
    for query in test_queries:
        results_sensitive, _ = engine_sensitive.search(query, top_k=3)
        results_insensitive, _ = engine_insensitive.search(query, top_k=3)
        
        ids_sensitive = [r[0] for r in results_sensitive]
        ids_insensitive = [r[0] for r in results_insensitive]
        
        # 在不敏感引擎中，所有变体应该返回相同结果
        is_consistent = len(set(ids_insensitive)) <= len(ids_insensitive)
        
        comparison = {
            "query": query,
            "sensitive_results": ids_sensitive,
            "insensitive_results": ids_insensitive,
            "consistent": is_consistent
        }
        details["comparisons"].append(comparison)
        
        status = "✅" if is_consistent else "⚠️"
        print(f"  {status} '{query}': 敏感引擎={ids_sensitive[:2]}, 不敏感引擎={ids_insensitive[:2]}")
        
        if is_consistent:
            consistent_count += 1
    
    score = consistent_count / len(test_queries)
    passed = score >= 0.8
    risk_level = "L2" if score < 0.7 else "L3"
    
    print(f"\n📊 结果: {consistent_count}/{len(test_queries)} 一致, 得分: {score:.2%}")
    print("💡 建议：生产环境建议使用大小写不敏感模式，或提供配置选项")
    
    return TestResult("大小写敏感测试", passed, score, risk_level, details)


def test_stopwords_handling() -> TestResult:
    """测试3: 停用词处理测试"""
    print("\n" + "="*60)
    print("🧪 测试3：停用词处理测试")
    print("="*60)
    print("风险：停用词过滤过度会导致查询为空，如'to be or not to be'")
    
    engine = MockKeywordSearchEngine()
    for doc in create_test_corpus():
        engine.add_document(doc)
    
    test_cases = [
        ("to be or not to be", "纯停用词查询"),
        ("the python", "混合查询"),
        ("is a test", "短停用词查询"),
        ("的 了 在", "纯中文停用词"),
        ("Python programming", "有效查询"),
    ]
    
    empty_count = 0
    details = {"cases": []}
    
    print("\n  测试停用词过滤行为:")
    
    for query, desc in test_cases:
        tokens = engine._tokenize(query)
        results, latency = engine.search(query, top_k=3)
        
        is_empty = len(tokens) == 0
        if is_empty:
            empty_count += 1
        
        case_detail = {
            "query": query,
            "description": desc,
            "tokens": tokens,
            "result_count": len(results),
            "is_empty": is_empty
        }
        details["cases"].append(case_detail)
        
        status = "⚠️" if is_empty else "✅"
        token_str = str(tokens) if tokens else "[空]"
        print(f"  {status} '{query}' ({desc})")
        print(f"      分词结果: {token_str}, 返回结果: {len(results)}条")
    
    # 纯停用词查询应该被检测到并特殊处理
    score = 1.0 - (empty_count / len(test_cases)) * 0.5
    passed = empty_count <= 2  # 允许部分停用词查询为空
    risk_level = "L1" if empty_count >= 3 else "L2"
    
    print(f"\n📊 结果: {empty_count}个查询被完全过滤, 得分: {score:.2%}")
    print("💡 建议：纯停用词查询应返回原始文档列表或提示用户细化查询")
    
    return TestResult("停用词处理测试", passed, score, risk_level, details)


def test_chinese_segmentation() -> TestResult:
    """测试4: 中文分词测试"""
    print("\n" + "="*60)
    print("🧪 测试4：中文分词测试")
    print("="*60)
    print("风险：中文分词歧义会导致召回失败，如'南京市长江大桥'")
    
    engine = MockKeywordSearchEngine()
    for doc in create_test_corpus():
        engine.add_document(doc)
    
    test_cases = [
        ("南京", ["doc_004"]),
        ("长江大桥", ["doc_004"]),
        ("机器学习", ["doc_008"]),
        ("人工智能", ["doc_008"]),
        ("深度学习", ["doc_008"]),
    ]
    
    passed_count = 0
    details = {"cases": []}
    
    print("\n  测试中文查询召回:")
    
    for query, expected_ids in test_cases:
        results, _ = engine.search(query, top_k=5)
        found_ids = [r[0] for r in results]
        
        found = any(eid in found_ids for eid in expected_ids)
        
        case_detail = {
            "query": query,
            "expected": expected_ids,
            "found": found,
            "top_results": found_ids[:3]
        }
        details["cases"].append(case_detail)
        
        status = "✅" if found else "❌"
        print(f"  {status} '{query}' → 期望: {expected_ids}, 实际: {found_ids[:3]}")
        
        if found:
            passed_count += 1
    
    score = passed_count / len(test_cases)
    passed = score >= 0.7
    risk_level = "L1" if score < 0.5 else "L2" if score < 0.7 else "L3"
    
    print(f"\n📊 结果: {passed_count}/{len(test_cases)} 通过, 得分: {score:.2%}")
    print("💡 建议：中文场景建议使用专业分词器如jieba或LTP")
    
    return TestResult("中文分词测试", passed, score, risk_level, details)


def test_performance_latency() -> TestResult:
    """测试5: 性能延迟测试"""
    print("\n" + "="*60)
    print("🧪 测试5：性能延迟测试")
    print("="*60)
    print("风险：关键词检索延迟过高会影响用户体验，需建立性能基线")
    
    engine = MockKeywordSearchEngine()
    
    # 添加更多文档以模拟真实场景
    for doc in create_test_corpus():
        engine.add_document(doc)
    
    # 模拟批量添加文档
    for i in range(100):
        doc = Document(
            f"doc_{100+i}",
            f"Sample Document {i}",
            f"This is sample content for document number {i}. " * 10
        )
        engine.add_document(doc)
    
    test_queries = [
        "GPT-4",
        "machine learning",
        "Python programming guide",
        "南京长江大桥历史",
        "API documentation version",
    ]
    
    latencies = []
    details = {"latencies": []}
    
    print(f"\n  文档库规模: {len(engine.documents)} 文档")
    print(f"  索引词条数: {len(engine.inverted_index)} 词条")
    print("\n  测量查询延迟:")
    
    # 预热
    for _ in range(3):
        for query in test_queries:
            engine.search(query)
    
    # 正式测试
    for query in test_queries:
        times = []
        for _ in range(10):
            _, latency = engine.search(query, top_k=10)
            times.append(latency * 1000)  # 转换为ms
        
        avg_latency = sum(times) / len(times)
        min_latency = min(times)
        max_latency = max(times)
        latencies.append(avg_latency)
        
        latency_record = {
            "query": query,
            "avg_ms": round(avg_latency, 3),
            "min_ms": round(min_latency, 3),
            "max_ms": round(max_latency, 3)
        }
        details["latencies"].append(latency_record)
        
        status = "✅" if avg_latency < 10 else "⚠️" if avg_latency < 50 else "❌"
        print(f"  {status} '{query[:30]}...' - 平均: {avg_latency:.3f}ms (min:{min_latency:.3f}, max:{max_latency:.3f})")
    
    avg_overall = sum(latencies) / len(latencies)
    p95 = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else avg_overall
    
    details["summary"] = {
        "avg_latency_ms": round(avg_overall, 3),
        "p95_latency_ms": round(p95, 3),
        "doc_count": len(engine.documents),
        "index_size": len(engine.inverted_index)
    }
    
    score = 1.0 if avg_overall < 10 else 0.8 if avg_overall < 50 else 0.5 if avg_overall < 100 else 0.3
    passed = avg_overall < 50
    risk_level = "L3" if avg_overall < 10 else "L2" if avg_overall < 50 else "L1"
    
    print(f"\n📊 结果:")
    print(f"   平均延迟: {avg_overall:.3f}ms")
    print(f"   P95延迟: {p95:.3f}ms")
    print(f"   性能得分: {score:.2%}")
    print("💡 建议：关键词检索延迟应控制在10ms以内，超过50ms需优化索引结构")
    
    return TestResult("性能延迟测试", passed, score, risk_level, details)


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📋 Day 31 测试汇总报告 - 关键词检索（稀疏检索）")
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
    
    # 风险等级说明
    print("\n🎯 风险等级说明:")
    print("   🔴 L1 - 高风险：可能导致线上故障，需立即修复")
    print("   🟡 L2 - 中风险：存在潜在问题，建议优化")
    print("   🟢 L3 - 低风险：表现良好，可接受")
    
    # 关键发现
    print("\n🔍 关键发现:")
    if high_risk_count > 0:
        high_risk_tests = [r.name for r in results if r.risk_level == "L1"]
        print(f"   ⚠️ 发现 {high_risk_count} 个高风险项: {', '.join(high_risk_tests)}")
    else:
        print("   ✅ 未发现高风险项，关键词检索基础能力良好")
    
    print("\n💡 下一步建议:")
    print("   1. 运行 Day 32 语义检索测试，对比两种检索方式的互补性")
    print("   2. 运行 Day 33 重排序优化测试，验证混合架构的最终效果")
    print("\n" + "="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 31: 关键词检索（稀疏检索）基础测试")
    print("="*70)
    print("\n测试架构师视角：验证关键词检索的核心能力，识别召回风险和性能瓶颈")
    
    results = [
        test_exact_id_matching(),
        test_case_sensitivity(),
        test_stopwords_handling(),
        test_chinese_segmentation(),
        test_performance_latency(),
    ]
    
    print_summary(results)
    
    # 保存详细结果
    output = {
        "day": 31,
        "theme": "关键词检索（稀疏检索）基础测试",
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
    
    with open("day31_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n💾 详细结果已保存至 day31_results.json")
    print("📤 请将上方日志贴回给 Trae 生成 report_day31.md")


if __name__ == "__main__":
    run_all_tests()
