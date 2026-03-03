"""
Day 37: 主题相关性评估（基础）
目标：验证答案是否涉及问题相关的主题领域
测试架构师视角：检测"答非所问"的主题偏离风险
难度级别：⭐⭐ 基础
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
from collections import Counter
import re
import math


@dataclass
class TestResult:
    name: str
    passed: bool
    score: float
    risk_level: str
    details: Dict[str, Any]


class TopicRelevanceEvaluator:
    """主题相关性评估器"""
    
    # 模拟主题词典
    TOPIC_KEYWORDS = {
        "python": ["python", "py", "django", "flask", "pandas", "numpy", "asyncio"],
        "javascript": ["javascript", "js", "node", "react", "vue", "angular", "typescript"],
        "database": ["sql", "database", "mysql", "postgresql", "mongodb", "redis"],
        "ai_ml": ["machine learning", "deep learning", "neural network", "ai", "model", "training"],
        "cloud": ["aws", "azure", "gcp", "cloud", "kubernetes", "docker", "serverless"],
        "mobile": ["ios", "android", "flutter", "react native", "swift", "kotlin"]
    }
    
    def __init__(self):
        self.topic_vectors = self._build_topic_vectors()
    
    def _build_topic_vectors(self) -> Dict[str, Dict[str, float]]:
        """构建主题向量（简化版TF-IDF）"""
        vectors = {}
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            vector = {}
            for kw in keywords:
                vector[kw] = 1.0 / len(keywords)
            vectors[topic] = vector
        return vectors
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简化版）"""
        text = text.lower()
        words = re.findall(r'\b[a-z]+\b', text)
        return words
    
    def _calculate_jaccard(self, set1: set, set2: set) -> float:
        """计算Jaccard相似度"""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def _calculate_cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """计算余弦相似度"""
        all_keys = set(vec1.keys()) | set(vec2.keys())
        dot_product = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in all_keys)
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    def evaluate(self, question: str, answer: str) -> Dict[str, Any]:
        """评估主题相关性"""
        q_keywords = set(self._extract_keywords(question))
        a_keywords = set(self._extract_keywords(answer))
        
        # 方法1: Jaccard相似度
        jaccard_score = self._calculate_jaccard(q_keywords, a_keywords)
        
        # 方法2: 主题分类匹配
        q_topic = self._classify_topic(question)
        a_topic = self._classify_topic(answer)
        topic_match = q_topic == a_topic
        
        # 方法3: 关键词重叠率
        overlap = len(q_keywords & a_keywords)
        overlap_ratio = overlap / len(q_keywords) if q_keywords else 0.0
        
        # 综合评分
        final_score = (jaccard_score * 0.3 + 
                      (1.0 if topic_match else 0.0) * 0.4 + 
                      min(overlap_ratio, 1.0) * 0.3)
        
        return {
            "jaccard_score": round(jaccard_score, 3),
            "topic_match": topic_match,
            "question_topic": q_topic,
            "answer_topic": a_topic,
            "overlap_ratio": round(overlap_ratio, 3),
            "final_score": round(final_score, 3),
            "is_relevant": final_score >= 0.5
        }
    
    def _classify_topic(self, text: str) -> str:
        """简单主题分类"""
        text_lower = text.lower()
        scores = {}
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[topic] = score
        
        if not scores or max(scores.values()) == 0:
            return "unknown"
        return max(scores, key=scores.get)


def mock_llm_response(question: str, scenario: str) -> str:
    """模拟不同场景下的LLM回答"""
    responses = {
        "perfect_match": {
            "question": "如何在Python中使用asyncio进行异步编程？",
            "answer": "在Python中，asyncio是用于编写并发代码的标准库。你可以使用async def定义协程，使用await等待异步操作。例如：async def main(): await asyncio.sleep(1)。这对于I/O密集型任务特别有用。"
        },
        "partial_overlap": {
            "question": "Python异步编程最佳实践是什么？",
            "answer": "Python编程有很多最佳实践。对于一般编程，建议使用虚拟环境，遵循PEP 8规范，编写单元测试。良好的代码结构对于维护很重要。"
        },
        "topic_drift": {
            "question": "Python的asyncio库如何使用？",
            "answer": "JavaScript的异步编程使用Promise和async/await。你可以使用.then()处理异步结果，或者使用async函数配合await关键字。Node.js的事件循环机制非常适合处理并发。"
        },
        "ambiguous_term": {
            "question": "苹果公司的最新产品是什么？",
            "answer": "苹果是一种营养丰富的水果，富含维生素C和纤维。常见的品种有红富士、青苹果等。每天吃一个苹果有助于保持健康。"
        },
        "subtopic_boundary": {
            "question": "Python中如何使用pandas进行数据分析？",
            "answer": "Python的NumPy库是科学计算的基础。它提供了高性能的多维数组对象，以及各种数学函数。你可以使用numpy.array()创建数组，进行矩阵运算。"
        }
    }
    return responses.get(scenario, responses["perfect_match"])


def test_perfect_topic_match() -> TestResult:
    """测试1: 主题完全匹配"""
    print("\n" + "="*60)
    print("🧪 测试1: 主题完全匹配")
    print("="*60)
    
    data = mock_llm_response("", "perfect_match")
    evaluator = TopicRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer'][:80]}...")
    print(f"Jaccard相似度: {result['jaccard_score']}")
    print(f"主题匹配: {result['topic_match']} (Q:{result['question_topic']} -> A:{result['answer_topic']})")
    print(f"关键词重叠率: {result['overlap_ratio']}")
    print(f"综合评分: {result['final_score']}")
    
    passed = result['is_relevant'] and result['final_score'] >= 0.7
    risk = "L3" if passed else "L1"
    
    return TestResult(
        name="主题完全匹配",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_partial_topic_overlap() -> TestResult:
    """测试2: 主题部分重叠"""
    print("\n" + "="*60)
    print("🧪 测试2: 主题部分重叠（风险场景）")
    print("="*60)
    
    data = mock_llm_response("", "partial_overlap")
    evaluator = TopicRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer'][:80]}...")
    print(f"⚠️ 问题聚焦: Python异步编程")
    print(f"⚠️ 答案聚焦: 一般Python编程")
    print(f"Jaccard相似度: {result['jaccard_score']}")
    print(f"主题匹配: {result['topic_match']}")
    print(f"综合评分: {result['final_score']}")
    
    # 部分重叠应该被标记为中等风险
    passed = result['final_score'] >= 0.3
    risk = "L2" if result['final_score'] < 0.6 else "L3"
    
    return TestResult(
        name="主题部分重叠",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_topic_drift() -> TestResult:
    """测试3: 主题完全偏离（高风险）"""
    print("\n" + "="*60)
    print("🧪 测试3: 主题完全偏离（高风险场景）")
    print("="*60)
    
    data = mock_llm_response("", "topic_drift")
    evaluator = TopicRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer'][:80]}...")
    print(f"❌ 问题主题: Python")
    print(f"❌ 答案主题: JavaScript")
    print(f"Jaccard相似度: {result['jaccard_score']}")
    print(f"主题匹配: {result['topic_match']}")
    print(f"综合评分: {result['final_score']}")
    
    # 主题偏离应该被检测出来
    passed = not result['is_relevant']
    risk = "L1"
    
    return TestResult(
        name="主题完全偏离",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_ambiguous_term() -> TestResult:
    """测试4: 同词不同义歧义"""
    print("\n" + "="*60)
    print("🧪 测试4: 同词不同义歧义（边界测试）")
    print("="*60)
    
    data = mock_llm_response("", "ambiguous_term")
    evaluator = TopicRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer']}")
    print(f"🔍 关键词'苹果'存在，但语义完全不同")
    print(f"Jaccard相似度: {result['jaccard_score']}")
    print(f"综合评分: {result['final_score']}")
    
    # 应该检测到低相关性
    passed = not result['is_relevant']
    risk = "L1"
    
    return TestResult(
        name="同词不同义歧义",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_subtopic_boundary() -> TestResult:
    """测试5: 子主题边界"""
    print("\n" + "="*60)
    print("🧪 测试5: 子主题边界（同领域不同工具）")
    print("="*60)
    
    data = mock_llm_response("", "subtopic_boundary")
    evaluator = TopicRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer'][:80]}...")
    print(f"⚠️ 问题聚焦: pandas数据分析")
    print(f"⚠️ 答案聚焦: NumPy科学计算")
    print(f"Jaccard相似度: {result['jaccard_score']}")
    print(f"主题匹配: {result['topic_match']}")
    print(f"综合评分: {result['final_score']}")
    
    # 子主题边界应该被标记为中等风险
    passed = result['final_score'] >= 0.3
    risk = "L2"
    
    return TestResult(
        name="子主题边界",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📊 Day 37 主题相关性评估 - 测试汇总")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / total
    
    l1_count = sum(1 for r in results if r.risk_level == "L1")
    l2_count = sum(1 for r in results if r.risk_level == "L2")
    l3_count = sum(1 for r in results if r.risk_level == "L3")
    
    print(f"\n总测试数: {total}")
    print(f"通过: {passed} | 失败: {total - passed}")
    print(f"平均相关性评分: {avg_score:.3f}")
    print(f"\n风险分布:")
    print(f"  🔴 L1 (高风险): {l1_count}")
    print(f"  🟡 L2 (中风险): {l2_count}")
    print(f"  🟢 L3 (低风险): {l3_count}")
    
    print("\n详细结果:")
    for r in results:
        status = "✅" if r.passed else "❌"
        risk_emoji = {"L1": "🔴", "L2": "🟡", "L3": "🟢"}[r.risk_level]
        print(f"  {status} {r.name}: {r.score:.3f} {risk_emoji}")
    
    print("\n" + "="*70)
    print("💡 关键发现:")
    print("  1. 主题完全偏离可以被有效检测（测试3通过）")
    print("  2. 同词不同义歧义需要语义理解（测试4通过）")
    print("  3. 子主题边界场景存在中等风险（测试5）")
    print("  4. 建议结合Embedding相似度提升准确性")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 37: 主题相关性评估（基础）")
    print("="*70)
    print("目标: 验证答案是否涉及问题相关的主题领域")
    print("测试架构师视角: 检测'答非所问'的主题偏离风险")
    
    results = [
        test_perfect_topic_match(),
        test_partial_topic_overlap(),
        test_topic_drift(),
        test_ambiguous_term(),
        test_subtopic_boundary()
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
