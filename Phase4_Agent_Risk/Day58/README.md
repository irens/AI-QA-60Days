# Day 58: Agent决策归因分析

## 🎯 1. 核心风险与测试目标 (20分钟)
> **测试架构师视角**：当Agent给出错误答案时，必须能快速定位是哪个推理步骤或哪条上下文导致了错误。

### 业务风险点
| 风险场景 | 业务影响 |
|---------|---------|
| 错误归因困难 | 无法确定是模型幻觉、上下文污染还是工具返回错误导致的答案错误 |
| 责任边界模糊 | 无法区分是Agent决策错误还是外部工具/数据源的过错 |
| 修复方向不明 | 不知道应该优化Prompt、更换模型还是改进工具 |
| 根因分析耗时 | 每次故障排查需要数小时甚至数天，严重影响系统稳定性 |
| 重复故障发生 | 无法从错误中学习，相同问题反复出现 |

### 测试思路
1. **决策路径回溯**：验证能否从最终答案追溯到每个中间决策
2. **上下文影响分析**：量化每条上下文对最终决策的贡献度
3. **工具调用归因**：明确工具返回结果如何影响Agent结论
4. **错误传播追踪**：分析错误如何在推理链中传播和放大

## 📚 2. 核心理论

### 2.1 归因分析的核心问题

```
归因分析三问：
┌─────────────────────────────────────────────────────────┐
│ 1. WHY: 为什么Agent会给出这个答案？                        │
│    → 识别关键决策点和影响因素                              │
├─────────────────────────────────────────────────────────┤
│ 2. WHERE: 错误发生在哪个环节？                            │
│    → 定位具体步骤、上下文或工具调用                        │
├─────────────────────────────────────────────────────────┤
│ 3. HOW: 错误如何传播到最终结果？                          │
│    → 分析错误传播路径和放大机制                            │
└─────────────────────────────────────────────────────────┘
```

### 2.2 归因分析技术栈

| 技术 | 适用场景 | 实现复杂度 |
|-----|---------|-----------|
| **注意力权重分析** | 定位关键上下文片段 | 中（需要模型支持） |
| **消融实验** | 量化各因素贡献度 | 低（多次推理对比） |
| **反事实推理** | 验证"如果...会怎样" | 中（修改输入重跑） |
| **梯度归因** | 识别输入特征重要性 | 高（需要白盒访问） |
| **推理链对比** | 正确vs错误路径对比 | 低（日志分析） |

### 2.3 消融实验设计

```python
# 消融实验：逐步移除因素，观察影响
def ablation_attribution(agent, query, context, tools_used):
    """
    通过消融实验分析各因素贡献
    """
    baseline = agent.run(query, context, tools_used)
    
    attributions = {}
    
    # 1. 移除特定上下文片段
    for i, ctx_item in enumerate(context):
        reduced_context = context[:i] + context[i+1:]
        result = agent.run(query, reduced_context, tools_used)
        attributions[f"context_{i}"] = baseline.similarity(result)
    
    # 2. 移除特定工具调用
    for tool in tools_used:
        reduced_tools = [t for t in tools_used if t != tool]
        result = agent.run(query, context, reduced_tools)
        attributions[f"tool_{tool}"] = baseline.similarity(result)
    
    # 3. 分析各因素贡献度
    for factor, score in attributions.items():
        impact = 1 - score  # 影响度 = 1 - 相似度
        print(f"{factor}: 影响度 {impact:.2%}")
    
    return attributions
```

### 2.4 错误传播分析模型

```
错误传播路径示例：

用户输入: "查询张三的账户余额"
    ↓
[Step 1: 意图识别] ✅ 正确: 识别为"查询余额"
    ↓
[Step 2: 实体提取] ⚠️ 错误: 提取到"李四"的账户ID
    ↓
[Step 3: 工具调用] ⚠️ 错误传播: 查询了李四的余额
    ↓
[Step 4: 结果生成] ❌ 严重错误: 返回了李四的余额给张三

归因结论:
- 根本原因: Step 2 实体提取错误
- 影响范围: 导致后续所有步骤基于错误信息执行
- 修复建议: 加强实体提取的准确性，增加账户ID验证
```

## 🧪 3. 实验验证任务
请运行本目录下的 `test_day58.py`，观察归因分析测试结果。

### 测试覆盖场景
1. ✅ 正确决策路径归因
2. ⚠️ 上下文污染归因
3. ⚠️ 工具返回错误归因
4. ⚠️ 推理步骤错误归因
5. ⚠️ 多因素叠加归因
6. ⚠️ 错误传播路径追踪

## 📝 4. 产出要求
将运行结果贴回给 Trae，让其生成 `report_day58.md` 质量分析报告。

## 🔗 关联内容
- **前一天**：Day 57 - Chain-of-Thought记录完整性
- **后一天**：Day 59 - 审计日志

## 📖 延伸阅读
- LIME (Local Interpretable Model-agnostic Explanations)
- SHAP (SHapley Additive exPlanations)
- Attention Visualization in Transformers
