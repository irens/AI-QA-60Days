# Day 43: Ragas框架 - Context检索质量指标

## 🎯 1. 核心风险与测试目标 (20分钟)
> **测试架构师视角**：检索层是RAG系统的根基，检索失败会导致生成层"Garbage In, Garbage Out"

### 业务风险点
- **检索遗漏**：关键文档未被召回，导致答案缺失重要信息（用户投诉"答非所问"）
- **检索噪声**：召回大量无关文档，稀释有效信息，增加幻觉风险
- **排序失效**：相关文档排名靠后，超出上下文窗口，导致信息丢失

### 测试思路
1. **Context Precision（上下文精确率）**：验证召回文档中真正相关的比例
2. **Context Recall（上下文召回率）**：验证答案所需信息是否被完整召回
3. **Context Relevancy（上下文相关性）**：验证召回文档与问题的语义匹配度

## 📚 2. 核心理论

### 2.1 Context Precision（上下文精确率）

**定义**：召回的上下文块中，被答案实际使用（或支持答案）的比例

**计算公式**：
```
Context Precision = 相关上下文块数 / 召回总上下文块数
```

**测试意义**：
- 低Precision = 噪声过多，模型被无关信息干扰
- 企业阈值建议：> 0.7（70%以上召回文档应被实际使用）

**失效模式**：
| 场景 | Precision | 风险 |
|------|-----------|------|
| 召回10篇，仅2篇相关 | 0.2 | 噪声淹没有效信息 |
| 召回5篇，全部相关 | 1.0 | 理想状态 |
| 召回20篇，排序靠后 | 0.1 | 有效信息被截断 |

### 2.2 Context Recall（上下文召回率）

**定义**：答案中所有事实/声明，能在上下文中找到支持的比例

**计算公式**：
```
Context Recall = 被上下文支持的事实数 / 答案总事实数
```

**测试意义**：
- 低Recall = 信息遗漏，答案不完整
- 企业阈值建议：> 0.8（80%以上答案事实应有上下文支持）

**失效模式**：
| 场景 | Recall | 风险 |
|------|--------|------|
| 答案包含外部知识 | 0.6 | 幻觉风险 |
| 关键文档未被召回 | 0.5 | 答案缺失核心信息 |
| 上下文覆盖全部事实 | 1.0 | 理想状态 |

### 2.3 Context Relevancy（上下文相关性）

**定义**：召回上下文与查询问题的语义相关程度

**计算方法**：
1. 提取问题中的关键实体/关键词
2. 计算每个上下文块与问题的语义相似度
3. 取平均或加权平均

**与Precision的区别**：
| 指标 | 关注点 | 计算方式 |
|------|--------|----------|
| Context Precision | 是否被答案使用 | 基于答案分析 |
| Context Relevancy | 是否与问题相关 | 基于语义相似度 |

## 🧪 3. 实验验证任务

请运行本目录下的 `test_day43.py`

```bash
python test_day43.py
```

### 预期输出
- 3个Context指标的基准测试
- 不同检索策略的对比分析
- 风险等级评估（L1/L2/L3）

## 📝 4. 产出要求

将运行结果贴回给 Trae，让其生成 `report_day43.md`

## 🔗 关联内容
- **前一天**：Day 42 父文档检索器策略
- **后一天**：Day 44 Faithfulness + Answer Relevancy指标

## 📖 扩展阅读

### Ragas框架官方指标说明

```python
# Context Precision 伪代码逻辑
def context_precision(contexts, answer):
    """
    1. 将答案分解为多个事实声明
    2. 对每个上下文块，判断是否支持答案中的某个事实
    3. 统计被使用的上下文块比例
    """
    used_contexts = 0
    for ctx in contexts:
        if is_used_in_answer(ctx, answer):
            used_contexts += 1
    return used_contexts / len(contexts)

# Context Recall 伪代码逻辑
def context_recall(contexts, answer):
    """
    1. 将答案分解为多个事实声明
    2. 对每个事实，判断是否有上下文支持
    3. 统计被支持的事实比例
    """
    facts = extract_facts(answer)
    supported_facts = 0
    for fact in facts:
        if has_context_support(fact, contexts):
            supported_facts += 1
    return supported_facts / len(facts)
```

### 企业级阈值参考

| 指标 | 优秀 | 合格 | 需优化 |
|------|------|------|--------|
| Context Precision | > 0.85 | 0.70-0.85 | < 0.70 |
| Context Recall | > 0.90 | 0.80-0.90 | < 0.80 |
| Context Relevancy | > 0.80 | 0.65-0.80 | < 0.65 |
