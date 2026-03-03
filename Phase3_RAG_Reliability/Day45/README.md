# Day 45: Ragas框架 - 自定义指标开发实战

## 🎯 1. 核心风险与测试目标 (20分钟)
> **测试架构师视角**：标准指标无法覆盖所有业务场景，必须掌握自定义指标开发能力

### 业务风险点
- **领域特殊性**：医疗、法律等领域有独特的质量要求，标准指标不适用
- **业务指标缺失**：用户体验、转化率等业务指标无法通过标准指标衡量
- **多语言支持**：标准指标主要针对英文，中文场景需要适配
- **成本敏感**：LLM-as-a-Judge成本高昂，需要轻量级替代方案

### 测试思路
1. **继承Ragas指标基类**：开发符合框架规范的自定义指标
2. **多维度组合**：将多个基础指标组合成复合业务指标
3. **规则+模型混合**：低成本规则检测 + 高精度模型验证的分层策略

## 📚 2. 核心理论

### 2.1 Ragas指标架构

```
┌─────────────────────────────────────────────────────────┐
│                    Ragas指标基类架构                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │           BaseMetric (指标基类)                  │   │
│  │  ├─ init()                                      │   │
│  │  ├─ score()  ← 子类必须实现                      │   │
│  │  └─ validate_input()                            │   │
│  └─────────────────────────────────────────────────┘   │
│                         ▲                               │
│           ┌─────────────┼─────────────┐                │
│           │             │             │                │
│     ┌─────┴────┐  ┌────┴────┐  ┌────┴────┐           │
│     │Context   │  │Answer   │  │Custom   │           │
│     │Metric    │  │Metric   │  │Metric   │           │
│     └──────────┘  └─────────┘  └─────────┘           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.2 自定义指标开发步骤

**Step 1: 定义指标需求**
```python
# 业务场景：客服机器人回答质量评估
# 标准指标不足：无法评估语气友好度、解决方案完整性
# 自定义指标：CustomerServiceQuality = 0.3*Accuracy + 0.3*Completeness + 0.4*Politeness
```

**Step 2: 继承基类实现**
```python
from ragas.metrics.base import Metric

class CustomerServiceQuality(Metric):
    def __init__(self):
        super().__init__()
        self.name = "customer_service_quality"
    
    def score(self, query: str, contexts: List[str], answer: str) -> float:
        # 1. 准确性（基于Faithfulness）
        accuracy = self._calculate_accuracy(contexts, answer)
        
        # 2. 完整性（检查是否回答所有子问题）
        completeness = self._calculate_completeness(query, answer)
        
        # 3. 礼貌度（规则+模型混合）
        politeness = self._calculate_politeness(answer)
        
        return 0.3 * accuracy + 0.3 * completeness + 0.4 * politeness
```

**Step 3: 集成到评估流水线**
```python
from ragas import evaluate

metrics = [
    faithfulness,
    answer_relevancy,
    CustomerServiceQuality()  # 自定义指标
]

result = evaluate(dataset, metrics=metrics)
```

### 2.3 常见自定义指标类型

| 指标类型 | 适用场景 | 实现复杂度 | 计算成本 |
|----------|----------|------------|----------|
| **领域适配指标** | 医疗/法律等专业领域 | 中 | 中 |
| **业务指标** | 转化率/满意度等业务目标 | 高 | 高 |
| **多语言指标** | 中文/日文等非英文场景 | 低 | 低 |
| **轻量级指标** | 高并发在线评估 | 低 | 低 |
| **复合指标** | 综合质量评分 | 中 | 中 |

### 2.4 自定义指标最佳实践

**原则1: 可解释性优先**
```python
# 好的实现：每个维度可独立解释
def score(self, query, contexts, answer):
    dimensions = {
        "accuracy": self._calc_accuracy(contexts, answer),
        "completeness": self._calc_completeness(query, answer),
        "politeness": self._calc_politeness(answer)
    }
    # 返回总分和详细维度
    return weighted_sum(dimensions), dimensions
```

**原则2: 渐进式复杂度**
```python
# 从简单规则开始，逐步引入模型
class CustomMetric:
    def __init__(self, use_llm=False):
        self.use_llm = use_llm
    
    def score(self, ...):
        # 基础规则评分（低成本）
        base_score = self._rule_based_score(...)
        
        # 可选：LLM增强（高精度）
        if self.use_llm:
            llm_score = self._llm_based_score(...)
            return 0.5 * base_score + 0.5 * llm_score
        
        return base_score
```

**原则3: 与标准指标互补**
```python
# 不要重复造轮子，复用标准指标
from ragas.metrics import Faithfulness, AnswerRelevancy

class CompositeMetric:
    def __init__(self):
        self.faithfulness = Faithfulness()
        self.relevancy = AnswerRelevancy()
    
    def score(self, query, contexts, answer):
        # 复用标准指标
        f_score = self.faithfulness.score(contexts, answer)
        r_score = self.relevancy.score(query, answer)
        
        # 添加自定义维度
        custom_score = self._custom_dimension(...)
        
        return combine_scores(f_score, r_score, custom_score)
```

## 🧪 3. 实验验证任务

请运行本目录下的 `test_day45.py`

```bash
python test_day45.py
```

### 预期输出
- 自定义指标基类实现
- 3个实战自定义指标（领域适配、业务指标、轻量级指标）
- 自定义指标与标准指标对比
- 企业级指标开发规范

## 📝 4. 产出要求

将运行结果贴回给 Trae，让其生成 `report_day45.md`

## 🔗 关联内容
- **前一天**：Day 44 Faithfulness + Answer Relevancy
- **后一天**：Day 46 LLM-as-a-Judge评估流水线

## 📖 扩展阅读

### 自定义指标模板代码

```python
"""
Ragas自定义指标完整模板
"""
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class MetricResult:
    """指标计算结果"""
    score: float
    details: Dict[str, any]
    reasoning: str

class CustomRAGMetric:
    """
    Ragas自定义指标模板
    
    使用示例:
        metric = CustomRAGMetric(name="my_metric", weight=0.5)
        result = metric.calculate(query, contexts, answer)
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
        """
        计算指标分数
        
        Args:
            query: 用户查询
            contexts: 检索到的上下文
            answer: 生成的答案
            
        Returns:
            MetricResult: 包含分数、详细信息和推理过程
        """
        # 1. 输入验证
        self._validate_input(query, contexts, answer)
        
        # 2. 计算分数
        score = self._compute_score(query, contexts, answer)
        
        # 3. 生成解释
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
    
    def _compute_score(self, query: str, contexts: List[str], answer: str) -> float:
        """核心评分逻辑 - 子类可重写"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def _generate_details(self, query: str, contexts: List[str], answer: str) -> Dict:
        """生成详细分析 - 子类可重写"""
        return {}
    
    def _generate_reasoning(self, score: float, details: Dict) -> str:
        """生成推理说明"""
        return f"Score {score:.2f} calculated based on {len(details)} dimensions"


# ==================== 实战示例：客服质量指标 ====================

class CustomerServiceQualityMetric(CustomRAGMetric):
    """
    客服场景专用质量指标
    
    评估维度:
    1. 准确性 (30%): 答案是否基于知识库
    2. 完整性 (30%): 是否回答所有子问题
    3. 礼貌度 (40%): 语气是否友好专业
    """
    
    def __init__(self):
        super().__init__(name="customer_service_quality")
        self.politeness_keywords = {
            "positive": ["请", "谢谢", "抱歉", "欢迎", "很高兴"],
            "negative": ["不知道", "自己看", "没办法", "不可能"]
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
        matched = sum(1 for w in answer_words if w in all_context)
        return min(matched / len(answer_words) * 1.5, 1.0) if answer_words else 0
    
    def _calc_completeness(self, query: str, answer: str) -> float:
        """检查是否回答所有问题"""
        # 简单实现：检查问号和答案长度
        question_count = query.count('?') + query.count('？')
        if question_count == 0:
            return 1.0
        # 假设每个问题至少需要10个字回答
        expected_length = question_count * 10
        return min(len(answer) / expected_length, 1.0)
    
    def _calc_politeness(self, answer: str) -> float:
        """基于关键词计算礼貌度"""
        answer_lower = answer.lower()
        
        positive_count = sum(1 for w in self.politeness_keywords["positive"] if w in answer_lower)
        negative_count = sum(1 for w in self.politeness_keywords["negative"] if w in answer_lower)
        
        score = 0.5 + positive_count * 0.1 - negative_count * 0.2
        return max(0, min(1, score))
    
    def _generate_details(self, query: str, contexts: List[str], answer: str) -> Dict:
        return {
            "accuracy": self._calc_accuracy(contexts, answer),
            "completeness": self._calc_completeness(query, answer),
            "politeness": self._calc_politeness(answer),
            "answer_length": len(answer),
            "context_count": len(contexts)
        }
```

### 企业级指标开发规范

1. **命名规范**: `{domain}_{metric_name}_{version}`，如 `medical_faithfulness_v1`
2. **文档要求**: 每个指标必须有使用场景说明和阈值建议
3. **测试覆盖**: 单元测试覆盖率 > 80%，包含边界情况
4. **性能基准**: 单次计算延迟 < 500ms（P99）
5. **可解释性**: 必须提供分数计算的详细推理过程
