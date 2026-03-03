"""
Day 45: Ragas框架 - 自定义指标开发实战
目标：掌握自定义指标开发能力，应对业务特殊需求
测试架构师视角：标准指标无法覆盖所有场景，必须掌握扩展能力
难度级别：实战
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum
from abc import ABC, abstractmethod


class RiskLevel(Enum):
    L1 = "L1-阻断性"
    L2 = "L2-高优先级"
    L3 = "L3-一般风险"


@dataclass
class TestResult:
    name: str
    passed: bool
    score: float
    risk_level: RiskLevel
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricResult:
    """指标计算结果"""
    score: float
    details: Dict[str, Any]
    reasoning: str


# ==================== 自定义指标基类 ====================

class CustomRAGMetric(ABC):
    """
    Ragas自定义指标抽象基类
    所有自定义指标必须继承此类
    """
    
    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight
        self.version = "1.0.0"
    
    def calculate(
        self, 
        query: str, 
        contexts: List[str], 
        answer: str
    ) -> MetricResult:
        """计算指标分数"""
        self._validate_input(query, contexts, answer)
        score = self._compute_score(query, contexts, answer)
        details = self._generate_details(query, contexts, answer)
        reasoning = self._generate_reasoning(score, details)
        return MetricResult(score, details, reasoning)
    
    def _validate_input(self, query: str, contexts: List[str], answer: str):
        """验证输入有效性"""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if not contexts:
            raise ValueError("Contexts cannot be empty")
        if not answer or not answer.strip():
            raise ValueError("Answer cannot be empty")
    
    @abstractmethod
    def _compute_score(self, query: str, contexts: List[str], answer: str) -> float:
        """核心评分逻辑 - 子类必须实现"""
        pass
    
    def _generate_details(self, query: str, contexts: List[str], answer: str) -> Dict:
        """生成详细分析 - 子类可重写"""
        return {}
    
    def _generate_reasoning(self, score: float, details: Dict) -> str:
        """生成推理说明"""
        return f"Score {score:.2f} calculated based on {len(details)} dimensions"


# ==================== 实战自定义指标 ====================

class CustomerServiceQualityMetric(CustomRAGMetric):
    """
    客服场景专用质量指标
    评估维度: 准确性(30%) + 完整性(30%) + 礼貌度(40%)
    """
    
    def __init__(self):
        super().__init__(name="customer_service_quality")
        self.politeness_keywords = {
            "positive": ["请", "谢谢", "抱歉", "欢迎", "很高兴", "为您", "帮助"],
            "negative": ["不知道", "自己看", "没办法", "不可能", "不行", "不管"]
        }
    
    def _compute_score(self, query: str, contexts: List[str], answer: str) -> float:
        accuracy = self._calc_accuracy(contexts, answer)
        completeness = self._calc_completeness(query, answer)
        politeness = self._calc_politeness(answer)
        return 0.3 * accuracy + 0.3 * completeness + 0.4 * politeness
    
    def _calc_accuracy(self, contexts: List[str], answer: str) -> float:
        """基于上下文覆盖计算准确性"""
        all_context = ' '.join(contexts).lower()
        answer_words = set(answer.lower().split())
        if not answer_words:
            return 0.0
        matched = sum(1 for w in answer_words if w in all_context and len(w) > 1)
        return min(matched / len(answer_words) * 1.5, 1.0)
    
    def _calc_completeness(self, query: str, answer: str) -> float:
        """检查是否回答所有问题"""
        question_count = query.count('?') + query.count('？') + query.count('吗') + query.count('多少')
        if question_count == 0:
            return 1.0
        expected_length = max(question_count * 15, 30)
        return min(len(answer) / expected_length, 1.0)
    
    def _calc_politeness(self, answer: str) -> float:
        """基于关键词计算礼貌度"""
        answer_lower = answer.lower()
        positive_count = sum(1 for w in self.politeness_keywords["positive"] if w in answer_lower)
        negative_count = sum(1 for w in self.politeness_keywords["negative"] if w in answer_lower)
        score = 0.5 + positive_count * 0.08 - negative_count * 0.15
        return max(0, min(1, score))
    
    def _generate_details(self, query: str, contexts: List[str], answer: str) -> Dict:
        return {
            "accuracy": round(self._calc_accuracy(contexts, answer), 2),
            "completeness": round(self._calc_completeness(query, answer), 2),
            "politeness": round(self._calc_politeness(answer), 2),
            "answer_length": len(answer),
            "context_count": len(contexts)
        }


class TechnicalAccuracyMetric(CustomRAGMetric):
    """
    技术文档场景：代码准确性指标
    评估代码示例是否正确、API使用是否规范
    """
    
    def __init__(self):
        super().__init__(name="technical_accuracy")
        self.code_patterns = {
            "python": ["def ", "class ", "import ", "return ", "print("],
            "javascript": ["function", "const ", "let ", "var ", "=>"],
            "sql": ["SELECT", "FROM", "WHERE", "INSERT", "UPDATE"]
        }
    
    def _compute_score(self, query: str, contexts: List[str], answer: str) -> float:
        # 1. 代码存在性
        has_code = self._detect_code_blocks(answer)
        if not has_code:
            return 0.5  # 中性分数
        
        # 2. 代码与上下文一致性
        code_consistency = self._check_code_consistency(contexts, answer)
        
        # 3. 代码完整性
        code_completeness = self._check_code_completeness(answer)
        
        return 0.4 * (1.0 if has_code else 0) + 0.4 * code_consistency + 0.2 * code_completeness
    
    def _detect_code_blocks(self, answer: str) -> bool:
        """检测是否包含代码块"""
        markers = ["```", "def ", "class ", "function", "SELECT ", "import "]
        return any(marker in answer for marker in markers)
    
    def _check_code_consistency(self, contexts: List[str], answer: str) -> float:
        """检查代码是否与上下文一致"""
        all_context = ' '.join(contexts).lower()
        # 提取代码中的API/函数名
        import re
        api_patterns = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\(', answer)
        if not api_patterns:
            return 0.8
        
        matched = sum(1 for api in api_patterns if api.lower() in all_context)
        return matched / len(api_patterns) if api_patterns else 0.8
    
    def _check_code_completeness(self, answer: str) -> float:
        """检查代码是否完整可运行"""
        # 简单检查：是否有导入语句 + 是否有返回值/输出
        has_import = "import " in answer or "require(" in answer
        has_output = "return " in answer or "print(" in answer or "console.log" in answer
        
        if has_import and has_output:
            return 1.0
        elif has_import or has_output:
            return 0.7
        return 0.4
    
    def _generate_details(self, query: str, contexts: List[str], answer: str) -> Dict:
        return {
            "has_code": self._detect_code_blocks(answer),
            "code_consistency": round(self._check_code_consistency(contexts, answer), 2),
            "code_completeness": round(self._check_code_completeness(answer), 2)
        }


class LightweightFaithfulnessMetric(CustomRAGMetric):
    """
    轻量级忠实度指标
    用于高并发在线评估，不使用LLM，纯规则实现
    """
    
    def __init__(self):
        super().__init__(name="lightweight_faithfulness")
    
    def _compute_score(self, query: str, contexts: List[str], answer: str) -> float:
        all_context = ' '.join(contexts).lower()
        answer_lower = answer.lower()
        
        # 1. 分句
        sentences = [s.strip() for s in answer_lower.replace('；', '.').replace('。', '.').split('.') if s.strip()]
        if not sentences:
            return 1.0
        
        # 2. 每句检查是否有上下文支持
        supported_count = 0
        for sent in sentences:
            sent_words = set(sent.split())
            if not sent_words:
                continue
            # 检查关键词覆盖
            overlap = sum(1 for w in sent_words if len(w) > 2 and w in all_context)
            coverage = overlap / len([w for w in sent_words if len(w) > 2])
            if coverage > 0.5:
                supported_count += 1
        
        return supported_count / len(sentences)
    
    def _generate_details(self, query: str, contexts: List[str], answer: str) -> Dict:
        all_context = ' '.join(contexts).lower()
        answer_lower = answer.lower()
        sentences = [s.strip() for s in answer_lower.replace('；', '.').replace('。', '.').split('.') if s.strip()]
        
        sentence_analysis = []
        for sent in sentences:
            sent_words = set(sent.split())
            overlap = sum(1 for w in sent_words if len(w) > 2 and w in all_context)
            total = len([w for w in sent_words if len(w) > 2])
            coverage = overlap / total if total else 0
            sentence_analysis.append({
                "sentence": sent[:50],
                "coverage": round(coverage, 2),
                "supported": coverage > 0.5
            })
        
        return {
            "sentence_count": len(sentences),
            "supported_count": sum(1 for s in sentence_analysis if s["supported"]),
            "sentence_analysis": sentence_analysis[:3]  # 只展示前3句
        }


class CompositeQualityMetric(CustomRAGMetric):
    """
    复合质量指标
    整合多个基础指标，输出综合质量评分
    """
    
    def __init__(self):
        super().__init__(name="composite_quality")
        self.sub_metrics = {
            "context_precision": 0.15,
            "context_recall": 0.15,
            "faithfulness": 0.25,
            "answer_relevancy": 0.25,
            "conciseness": 0.20
        }
    
    def _compute_score(self, query: str, contexts: List[str], answer: str) -> float:
        scores = {
            "context_precision": self._calc_context_precision(contexts, answer),
            "context_recall": self._calc_context_recall(contexts, answer),
            "faithfulness": self._calc_faithfulness(contexts, answer),
            "answer_relevancy": self._calc_answer_relevancy(query, answer),
            "conciseness": self._calc_conciseness(query, answer)
        }
        
        weighted_sum = sum(scores[k] * self.sub_metrics[k] for k in scores)
        return weighted_sum
    
    def _calc_context_precision(self, contexts: List[str], answer: str) -> float:
        used = sum(1 for ctx in contexts if len(set(ctx.lower().split()) & set(answer.lower().split())) > 2)
        return used / len(contexts) if contexts else 0
    
    def _calc_context_recall(self, contexts: List[str], answer: str) -> float:
        sentences = [s.strip() for s in answer.replace('；', '.').replace('。', '.').split('.') if s.strip()]
        if not sentences:
            return 1.0
        all_ctx = ' '.join(contexts).lower()
        supported = sum(1 for s in sentences if any(w in all_ctx for w in s.lower().split() if len(w) > 2))
        return supported / len(sentences)
    
    def _calc_faithfulness(self, contexts: List[str], answer: str) -> float:
        all_ctx = ' '.join(contexts).lower()
        sentences = [s.strip() for s in answer.lower().replace('；', '.').replace('。', '.').split('.') if s.strip()]
        if not sentences:
            return 1.0
        supported = sum(1 for s in sentences if any(w in all_ctx for w in s.split() if len(w) > 2))
        return supported / len(sentences)
    
    def _calc_answer_relevancy(self, query: str, answer: str) -> float:
        qw = set(query.lower().split())
        aw = set(answer.lower().split())
        if not qw or not aw:
            return 0.0
        overlap = qw & aw
        return len(overlap) / len(qw)
    
    def _calc_conciseness(self, query: str, answer: str) -> float:
        """评估答案简洁度"""
        expected_length = len(query) * 2
        actual_length = len(answer)
        if actual_length <= expected_length:
            return 1.0
        elif actual_length <= expected_length * 2:
            return 0.8
        elif actual_length <= expected_length * 3:
            return 0.6
        return 0.4
    
    def _generate_details(self, query: str, contexts: List[str], answer: str) -> Dict:
        return {
            "context_precision": round(self._calc_context_precision(contexts, answer), 2),
            "context_recall": round(self._calc_context_recall(contexts, answer), 2),
            "faithfulness": round(self._calc_faithfulness(contexts, answer), 2),
            "answer_relevancy": round(self._calc_answer_relevancy(query, answer), 2),
            "conciseness": round(self._calc_conciseness(query, answer), 2),
            "weights": self.sub_metrics
        }


# ==================== 测试数据集 ====================

TEST_CASES = {
    "customer_service": {
        "query": "请问如何重置密码？我的账户被锁定了",
        "contexts": [
            "密码重置流程：1. 点击登录页面的'忘记密码'链接；2. 输入注册邮箱；3. 查收重置邮件；4. 设置新密码。",
            "账户锁定处理：连续5次输入错误密码会导致账户锁定，24小时后自动解锁或联系客服人工解锁。"
        ],
        "answer": "您好！很抱歉给您带来不便。重置密码请按以下步骤操作：1) 点击登录页面的'忘记密码'；2) 输入您的注册邮箱；3) 查收重置邮件并设置新密码。关于账户锁定，连续5次错误输入会导致锁定，24小时后会自动解锁，您也可以联系客服人工解锁。如有其他问题，欢迎随时咨询！"
    },
    "technical_doc": {
        "query": "如何用Python读取CSV文件？",
        "contexts": [
            "使用pandas库读取CSV：import pandas as pd; df = pd.read_csv('file.csv')",
            "也可以使用标准库csv：import csv; with open('file.csv') as f: reader = csv.reader(f)"
        ],
        "answer": """您可以使用pandas库来读取CSV文件：

```python
import pandas as pd

# 读取CSV文件
df = pd.read_csv('file.csv')

# 查看前5行
print(df.head())
```

或者使用标准库csv：

```python
import csv

with open('file.csv', 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        print(row)
```"""
    },
    "hallucination_risk": {
        "query": "Python的GIL是什么？",
        "contexts": [
            "GIL（Global Interpreter Lock）是Python解释器中的全局解释器锁。",
            "GIL确保同一时刻只有一个线程执行Python字节码。"
        ],
        "answer": "GIL是Python的全局解释器锁，它确保同一时刻只有一个线程执行Python字节码。GIL在Python 3.8版本中被移除，推荐使用多进程替代多线程。"
    }
}


# ==================== 测试函数 ====================

def test_customer_service_metric() -> TestResult:
    """测试客服质量指标"""
    print("\n" + "="*60)
    print("🧪 测试1: CustomerServiceQualityMetric（客服质量指标）")
    print("="*60)
    
    metric = CustomerServiceQualityMetric()
    case = TEST_CASES["customer_service"]
    
    result = metric.calculate(case["query"], case["contexts"], case["answer"])
    
    print(f"\n📋 指标名称: {metric.name}")
    print(f"📊 综合得分: {result.score:.2f}")
    print(f"\n📊 维度分解:")
    for dim, score in result.details.items():
        if isinstance(score, (int, float)) and dim not in ["answer_length", "context_count"]:
            print(f"  • {dim}: {score:.2f}")
    
    print(f"\n💡 推理说明: {result.reasoning}")
    
    # 评估风险
    risk = RiskLevel.L3 if result.score >= 0.8 else RiskLevel.L2 if result.score >= 0.6 else RiskLevel.L1
    
    return TestResult(
        name="CustomerServiceQuality",
        passed=result.score >= 0.7,
        score=result.score,
        risk_level=risk,
        details=result.details
    )


def test_technical_accuracy_metric() -> TestResult:
    """测试技术准确性指标"""
    print("\n" + "="*60)
    print("🧪 测试2: TechnicalAccuracyMetric（技术准确性指标）")
    print("="*60)
    
    metric = TechnicalAccuracyMetric()
    case = TEST_CASES["technical_doc"]
    
    result = metric.calculate(case["query"], case["contexts"], case["answer"])
    
    print(f"\n📋 指标名称: {metric.name}")
    print(f"📊 综合得分: {result.score:.2f}")
    print(f"\n📊 维度分解:")
    for dim, value in result.details.items():
        if dim == "has_code":
            print(f"  • 包含代码: {'是' if value else '否'}")
        elif isinstance(value, float):
            print(f"  • {dim}: {value:.2f}")
    
    print(f"\n💡 推理说明: {result.reasoning}")
    
    risk = RiskLevel.L3 if result.score >= 0.8 else RiskLevel.L2 if result.score >= 0.5 else RiskLevel.L1
    
    return TestResult(
        name="TechnicalAccuracy",
        passed=result.score >= 0.6,
        score=result.score,
        risk_level=risk,
        details=result.details
    )


def test_lightweight_faithfulness() -> TestResult:
    """测试轻量级忠实度指标"""
    print("\n" + "="*60)
    print("🧪 测试3: LightweightFaithfulnessMetric（轻量级忠实度）")
    print("="*60)
    
    metric = LightweightFaithfulnessMetric()
    
    # 测试忠实案例
    faithful_case = TEST_CASES["customer_service"]
    faithful_result = metric.calculate(
        faithful_case["query"], 
        faithful_case["contexts"], 
        faithful_case["answer"]
    )
    
    # 测试幻觉案例
    hallucination_case = TEST_CASES["hallucination_risk"]
    hallucination_result = metric.calculate(
        hallucination_case["query"],
        hallucination_case["contexts"],
        hallucination_case["answer"]
    )
    
    print(f"\n📋 指标名称: {metric.name}")
    print(f"\n📊 忠实案例得分: {faithful_result.score:.2f}")
    print(f"📊 幻觉案例得分: {hallucination_result.score:.2f}")
    
    print(f"\n📊 幻觉案例分析:")
    print(f"  句子总数: {hallucination_result.details['sentence_count']}")
    print(f"  支持句子数: {hallucination_result.details['supported_count']}")
    print(f"  前3句分析:")
    for i, sent in enumerate(hallucination_result.details['sentence_analysis'], 1):
        status = "✓" if sent["supported"] else "✗"
        print(f"    {status} 句{i}: {sent['sentence'][:30]}... (覆盖度: {sent['coverage']})")
    
    # 检测能力评估
    can_detect = faithful_result.score > hallucination_result.score + 0.1
    
    print(f"\n💡 检测能力: {'✅ 能区分忠实/幻觉' if can_detect else '⚠️ 区分能力较弱'}")
    
    avg_score = (faithful_result.score + hallucination_result.score) / 2
    risk = RiskLevel.L3 if can_detect else RiskLevel.L2
    
    return TestResult(
        name="LightweightFaithfulness",
        passed=can_detect,
        score=avg_score,
        risk_level=risk,
        details={
            "faithful_score": faithful_result.score,
            "hallucination_score": hallucination_result.score,
            "can_detect": can_detect
        }
    )


def test_composite_metric() -> TestResult:
    """测试复合质量指标"""
    print("\n" + "="*60)
    print("🧪 测试4: CompositeQualityMetric（复合质量指标）")
    print("="*60)
    
    metric = CompositeQualityMetric()
    case = TEST_CASES["customer_service"]
    
    result = metric.calculate(case["query"], case["contexts"], case["answer"])
    
    print(f"\n📋 指标名称: {metric.name}")
    print(f"📊 综合得分: {result.score:.2f}")
    
    print(f"\n📊 子指标得分（含权重）:")
    for sub_metric, score in result.details.items():
        if sub_metric in result.details.get("weights", {}):
            weight = result.details["weights"][sub_metric]
            weighted = score * weight
            print(f"  • {sub_metric}: {score:.2f} × {weight} = {weighted:.2f}")
    
    print(f"\n💡 推理说明: {result.reasoning}")
    
    risk = RiskLevel.L3 if result.score >= 0.75 else RiskLevel.L2 if result.score >= 0.6 else RiskLevel.L1
    
    return TestResult(
        name="CompositeQuality",
        passed=result.score >= 0.7,
        score=result.score,
        risk_level=risk,
        details=result.details
    )


def test_metric_comparison() -> TestResult:
    """多指标对比测试"""
    print("\n" + "="*60)
    print("🧪 测试5: 多指标对比分析")
    print("="*60)
    
    metrics = {
        "客服质量": CustomerServiceQualityMetric(),
        "技术准确": TechnicalAccuracyMetric(),
        "轻量忠实": LightweightFaithfulnessMetric(),
        "复合质量": CompositeQualityMetric()
    }
    
    print("\n📋 同一测试用例的多指标评估:")
    print("-" * 70)
    print(f"{'指标名称':<15} {'得分':>8} {'适用场景':<25} {'计算成本':>10}")
    print("-" * 70)
    
    case = TEST_CASES["customer_service"]
    scores = []
    
    for name, metric in metrics.items():
        result = metric.calculate(case["query"], case["contexts"], case["answer"])
        scores.append(result.score)
        
        # 场景和成本标签
        if name == "客服质量":
            scenario, cost = "客服机器人", "低"
        elif name == "技术准确":
            scenario, cost = "技术文档", "中"
        elif name == "轻量忠实":
            scenario, cost = "在线监控", "极低"
        else:
            scenario, cost = "综合评估", "中"
        
        print(f"{name:<15} {result.score:>8.2f} {scenario:<25} {cost:>10}")
    
    print("-" * 70)
    
    avg_score = sum(scores) / len(scores)
    std_score = (sum((s - avg_score) ** 2 for s in scores) / len(scores)) ** 0.5
    
    print(f"\n📊 统计分析:")
    print(f"  平均分: {avg_score:.2f}")
    print(f"  标准差: {std_score:.2f}")
    print(f"  分数范围: {min(scores):.2f} - {max(scores):.2f}")
    
    print(f"\n💡 选型建议:")
    print(f"  • 高并发在线监控 → 轻量忠实指标")
    print(f"  • 客服质量报告 → 客服质量指标")
    print(f"  • 综合质量评估 → 复合质量指标")
    
    return TestResult(
        name="MetricComparison",
        passed=True,
        score=avg_score,
        risk_level=RiskLevel.L3,
        details={
            "avg_score": avg_score,
            "std_score": std_score,
            "min_score": min(scores),
            "max_score": max(scores)
        }
    )


# ==================== 主入口 ====================

def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 测试汇总报告 - Day 45: 自定义指标开发实战")
    print("="*70)
    
    print(f"\n{'测试项':<30} {'得分':>10} {'状态':>8} {'风险等级':>12}")
    print("-" * 70)
    
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{r.name:<30} {r.score:>10.2f} {status:>8} {r.risk_level.value:>12}")
    
    print("-" * 70)
    
    avg_score = sum(r.score for r in results) / len(results)
    passed_count = sum(1 for r in results if r.passed)
    
    print(f"\n📈 总体统计:")
    print(f"  平均得分: {avg_score:.2f}")
    print(f"  通过测试: {passed_count}/{len(results)}")
    
    print(f"\n🎯 关键发现:")
    print(f"  1. 自定义指标需继承基类并实现_compute_score方法")
    print(f"  2. 多维度分解有助于问题定位和可解释性")
    print(f"  3. 轻量级指标适合高并发场景，高精度指标适合离线评估")
    print(f"  4. 复合指标可整合多个维度，提供综合质量视图")
    
    print(f"\n📋 自定义指标开发规范:")
    print(f"  ✓ 命名规范: {{domain}}_{{metric_name}}_{{version}}")
    print(f"  ✓ 输入验证: 必须检查query/contexts/answer有效性")
    print(f"  ✓ 详细输出: 提供details和reasoning便于调试")
    print(f"  ✓ 异常处理: 空输入等边界情况需优雅处理")
    
    print(f"\n💡 下一步:")
    print(f"  运行 Day 46 测试，学习 LLM-as-a-Judge 评估流水线")
    
    print("\n" + "="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 45: 自定义指标开发实战")
    print("="*70)
    print("测试架构师视角：标准指标无法覆盖所有业务场景")
    print("="*70)
    
    results = [
        test_customer_service_metric(),
        test_technical_accuracy_metric(),
        test_lightweight_faithfulness(),
        test_composite_metric(),
        test_metric_comparison()
    ]
    
    print_summary(results)
    
    # 输出JSON格式结果
    print("\n📤 JSON格式结果:")
    json_output = [
        {
            "name": r.name,
            "passed": r.passed,
            "score": round(r.score, 2),
            "risk_level": r.risk_level.value,
            "details": r.details
        }
        for r in results
    ]
    print(json.dumps(json_output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_all_tests()
