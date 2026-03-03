"""
Day 38: 意图相关性与完整相关性评估（进阶）
目标：验证答案是否针对用户真实意图并覆盖所有要点
测试架构师视角：检测"主题对但意图偏"和"答一半漏一半"的风险
难度级别：⭐⭐⭐ 进阶
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
import re


@dataclass
class TestResult:
    name: str
    passed: bool
    score: float
    risk_level: str
    details: Dict[str, Any]


class IntentRelevanceEvaluator:
    """意图相关性评估器"""
    
    # 意图关键词映射
    INTENT_PATTERNS = {
        "how_to": ["如何", "怎么", "怎样", "步骤", "教程", "guide", "how to", "steps"],
        "what_is": ["什么是", "什么叫", "定义", "概念", "what is", "definition"],
        "compare": ["区别", "对比", "比较", "哪个好", "vs", "versus", "compare", "difference"],
        "troubleshoot": ["为什么", "报错", "错误", "失败", "问题", "error", "issue", "troubleshoot"],
        "list": ["哪些", "列表", "所有", "支持", "有什么", "list", "what are"]
    }
    
    def __init__(self):
        pass
    
    def detect_intent(self, question: str) -> str:
        """检测问题意图"""
        q_lower = question.lower()
        scores = {}
        
        for intent, keywords in self.INTENT_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in q_lower)
            scores[intent] = score
        
        if not scores or max(scores.values()) == 0:
            return "unknown"
        return max(scores, key=scores.get)
    
    def evaluate_intent_match(self, question: str, answer: str) -> Dict[str, Any]:
        """评估意图匹配度"""
        q_intent = self.detect_intent(question)
        
        # 基于意图类型检查答案特征
        intent_indicators = {
            "how_to": ["步骤", "首先", "然后", "最后", "1.", "2.", "step", "first", "then"],
            "what_is": ["是", "指", "表示", "一种", "is a", "refers to", "means"],
            "compare": ["区别", "相比", "更", "优势", "劣势", "vs", "compared", "better"],
            "troubleshoot": ["原因", "解决", "检查", "尝试", "cause", "solution", "fix"],
            "list": ["1.", "2.", "3.", "包括", "有", "、", ",", "list"]
        }
        
        indicators = intent_indicators.get(q_intent, [])
        a_lower = answer.lower()
        
        match_count = sum(1 for ind in indicators if ind in a_lower)
        match_ratio = match_count / len(indicators) if indicators else 0.5
        
        # 意图匹配评分
        intent_score = min(match_ratio * 2, 1.0)  # 放大信号
        
        return {
            "question_intent": q_intent,
            "match_indicators_found": match_count,
            "intent_score": round(intent_score, 3),
            "is_intent_match": intent_score >= 0.5
        }
    
    def extract_key_points(self, question: str) -> List[str]:
        """提取问题要点"""
        points = []
        
        # 提取引号内容
        quotes = re.findall(r'["""]([^"""]+)["""]', question)
        points.extend(quotes)
        
        # 提取技术术语（简化版）
        tech_terms = re.findall(r'\b[A-Z][a-zA-Z]*\b|\b[a-z]+_[a-z]+\b', question)
        points.extend(tech_terms)
        
        # 提取疑问词后的内容
        wh_patterns = re.findall(r'(?:如何|怎么|什么|哪些|为什么)\s*([^?？]+)', question)
        points.extend(wh_patterns)
        
        return list(set(points))
    
    def evaluate_completeness(self, question: str, answer: str) -> Dict[str, Any]:
        """评估完整性"""
        key_points = self.extract_key_points(question)
        
        if not key_points:
            return {
                "key_points": [],
                "covered_points": [],
                "coverage_ratio": 1.0,
                "completeness_score": 1.0
            }
        
        a_lower = answer.lower()
        covered = []
        
        for point in key_points:
            if point.lower() in a_lower or any(word in a_lower for word in point.lower().split()):
                covered.append(point)
        
        coverage_ratio = len(covered) / len(key_points)
        
        # 完整性评分（考虑部分覆盖）
        completeness_score = coverage_ratio
        
        return {
            "key_points": key_points,
            "covered_points": covered,
            "coverage_ratio": round(coverage_ratio, 3),
            "completeness_score": round(completeness_score, 3),
            "is_complete": completeness_score >= 0.8
        }
    
    def evaluate(self, question: str, answer: str) -> Dict[str, Any]:
        """综合评估"""
        intent_result = self.evaluate_intent_match(question, answer)
        completeness_result = self.evaluate_completeness(question, answer)
        
        # 综合评分（意图匹配权重更高）
        final_score = (intent_result["intent_score"] * 0.6 + 
                      completeness_result["completeness_score"] * 0.4)
        
        return {
            "intent": intent_result,
            "completeness": completeness_result,
            "final_score": round(final_score, 3),
            "is_relevant": final_score >= 0.6
        }


def mock_llm_response(scenario: str) -> Dict[str, str]:
    """模拟不同场景下的LLM回答"""
    responses = {
        "perfect_intent_match": {
            "question": "如何在Python中安装pandas库？",
            "answer": "安装pandas非常简单，按照以下步骤操作：\n1. 打开终端或命令行\n2. 运行命令：pip install pandas\n3. 等待安装完成\n4. 验证安装：python -c \"import pandas; print(pandas.__version__)\""
        },
        "intent_drift_how_to_what": {
            "question": "如何在Python中安装pandas库？",
            "answer": "pandas是一个强大的数据分析库，它提供了DataFrame数据结构，可以方便地处理表格数据。pandas支持数据清洗、转换、分析等功能，是数据科学领域最常用的工具之一。"
        },
        "intent_wrong_compare": {
            "question": "Python和JavaScript有什么区别？",
            "answer": "Python是一种高级编程语言，由Guido van Rossum创建。它具有简洁的语法，广泛应用于数据科学、人工智能、Web开发等领域。Python有丰富的标准库和第三方库。"
        },
        "incomplete_answer": {
            "question": "如何在Python中读取CSV文件并进行数据清洗？",
            "answer": "使用pandas读取CSV文件：df = pd.read_csv('file.csv')。pandas提供了强大的数据读取功能，支持多种文件格式。"
        },
        "compare_incomplete": {
            "question": "MySQL和PostgreSQL各有什么优缺点？",
            "answer": "MySQL的优点是性能优秀、社区活跃、易于使用。它广泛应用于Web开发，特别是LAMP栈。MySQL支持主从复制和分区功能。"
        }
    }
    return responses.get(scenario, responses["perfect_intent_match"])


def test_perfect_intent_match() -> TestResult:
    """测试1: 意图完全匹配"""
    print("\n" + "="*60)
    print("🧪 测试1: 意图完全匹配")
    print("="*60)
    
    data = mock_llm_response("perfect_intent_match")
    evaluator = IntentRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer'][:100]}...")
    print(f"检测意图: {result['intent']['question_intent']}")
    print(f"意图匹配度: {result['intent']['intent_score']}")
    print(f"完整性评分: {result['completeness']['completeness_score']}")
    print(f"综合评分: {result['final_score']}")
    
    passed = result['is_relevant'] and result['final_score'] >= 0.7
    risk = "L3" if passed else "L1"
    
    return TestResult(
        name="意图完全匹配",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_intent_drift_how_to_what() -> TestResult:
    """测试2: 意图偏差（操作→概念）"""
    print("\n" + "="*60)
    print("🧪 测试2: 意图偏差（操作→概念）")
    print("="*60)
    
    data = mock_llm_response("intent_drift_how_to_what")
    evaluator = IntentRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer'][:100]}...")
    print(f"⚠️ 问题意图: how_to（寻求操作步骤）")
    print(f"⚠️ 答案类型: what_is（概念解释）")
    print(f"检测意图: {result['intent']['question_intent']}")
    print(f"意图匹配度: {result['intent']['intent_score']}")
    print(f"综合评分: {result['final_score']}")
    
    # 应该检测到低意图匹配
    passed = result['final_score'] < 0.6
    risk = "L2"
    
    return TestResult(
        name="意图偏差（操作→概念）",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_intent_wrong_compare() -> TestResult:
    """测试3: 意图完全错误（比较→单方描述）"""
    print("\n" + "="*60)
    print("🧪 测试3: 意图完全错误（比较→单方描述）")
    print("="*60)
    
    data = mock_llm_response("intent_wrong_compare")
    evaluator = IntentRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer'][:100]}...")
    print(f"❌ 问题意图: compare（寻求对比）")
    print(f"❌ 答案类型: 单方描述，无对比")
    print(f"检测意图: {result['intent']['question_intent']}")
    print(f"意图匹配度: {result['intent']['intent_score']}")
    print(f"综合评分: {result['final_score']}")
    
    # 应该检测到低意图匹配
    passed = result['final_score'] < 0.5
    risk = "L1"
    
    return TestResult(
        name="意图完全错误（比较→单方）",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_incomplete_answer() -> TestResult:
    """测试4: 要点遗漏"""
    print("\n" + "="*60)
    print("🧪 测试4: 要点遗漏（只答一半）")
    print("="*60)
    
    data = mock_llm_response("incomplete_answer")
    evaluator = IntentRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer']}")
    print(f"🔍 问题要点: 1)读取CSV 2)数据清洗")
    print(f"🔍 答案覆盖: 仅覆盖读取CSV")
    print(f"完整性评分: {result['completeness']['completeness_score']}")
    print(f"综合评分: {result['final_score']}")
    
    # 应该检测到不完整性
    passed = not result['completeness']['is_complete']
    risk = "L2"
    
    return TestResult(
        name="要点遗漏（不完整回答）",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_compare_incomplete() -> TestResult:
    """测试5: 比较类问题不完整"""
    print("\n" + "="*60)
    print("🧪 测试5: 比较类问题不完整（只答一方）")
    print("="*60)
    
    data = mock_llm_response("compare_incomplete")
    evaluator = IntentRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer'][:100]}...")
    print(f"🔍 问题要点: MySQL优缺点 + PostgreSQL优缺点")
    print(f"🔍 答案覆盖: 仅MySQL")
    print(f"检测意图: {result['intent']['question_intent']}")
    print(f"意图匹配度: {result['intent']['intent_score']}")
    print(f"完整性评分: {result['completeness']['completeness_score']}")
    print(f"综合评分: {result['final_score']}")
    
    # 比较类问题不完整应该被检测
    passed = result['final_score'] < 0.7
    risk = "L2"
    
    return TestResult(
        name="比较类问题不完整",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📊 Day 38 意图相关性与完整相关性 - 测试汇总")
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
    print("  1. 意图偏差可以被检测（测试2通过）")
    print("  2. 比较类问题不完整是高风险场景（测试3、5）")
    print("  3. 要点遗漏检测需要更精细的分解（测试4）")
    print("  4. 建议结合LLM进行更准确的意图识别")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 38: 意图相关性与完整相关性（进阶）")
    print("="*70)
    print("目标: 验证答案是否针对用户真实意图并覆盖所有要点")
    print("测试架构师视角: 检测'主题对但意图偏'和'答一半漏一半'的风险")
    
    results = [
        test_perfect_intent_match(),
        test_intent_drift_how_to_what(),
        test_intent_wrong_compare(),
        test_incomplete_answer(),
        test_compare_incomplete()
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
