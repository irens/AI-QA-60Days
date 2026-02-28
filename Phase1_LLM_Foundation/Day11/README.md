# Day 11: 输出鲁棒性测试——同义改写与噪声注入

## 🎯 1. 核心风险与测试目标

### 1.1 测试工程师视角
> **核心原则**：开发只管跑通，我们要想办法把它搞崩溃。LLM的"理解"是脆弱的——换个说法、加点噪声，同样的意思可能得到完全不同的答案。这不是智能，是**模式匹配的幻觉**。

### 1.2 业务风险点

| 风险类别 | 具体风险 | 线上事故场景 |
|---------|---------|-------------|
| **同义敏感** | 同一问题的不同表述得到不同答案 | 客服AI对"怎么退款"和"如何退货"给出矛盾流程 |
| **噪声脆弱** | 输入中的拼写错误导致输出质量骤降 | 用户输入有错别字时，AI突然"听不懂" |
| **格式依赖** | 对特定提示格式过度敏感 | 去掉"请"字后，AI拒绝回答问题 |
| **顺序敏感** | 信息顺序变化影响理解 | 调整条件顺序后，推理结果改变 |
| **边界失效** | 轻微超出训练分布即表现崩溃 | 遇到生僻词或新造词时输出胡言乱语 |

### 1.3 测试思路

**同义改写测试策略**：
- **词汇层面**：同义词替换、近义词变换
- **句法层面**：主动被动转换、语序调整、句式变换
- **语篇层面**：段落重组、衔接词替换、详略调整
- **跨语言**：翻译往返验证语义一致性

**噪声注入测试策略**：
- **字符级噪声**：随机替换、插入、删除字符
- **词级噪声**：随机替换同义词、插入停用词
- **句子级噪声**：随机插入无关句子、打乱句子顺序
- **渐进压力**：从5%噪声到50%噪声，记录性能衰减曲线

---

## 📚 2. 鲁棒性测试原理（测试必备知识）

### 2.1 为什么LLM对改写和噪声敏感

```
┌─────────────────────────────────────────────────────────────────┐
│              LLM脆弱性的本质原因                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  根本原因：自回归语言模型的训练目标                               │
│                                                                 │
│  训练目标：给定前缀，预测下一个token的概率分布                     │
│           P(token_t | token_1, token_2, ..., token_{t-1})        │
│                                                                 │
│  脆弱性来源：                                                    │
│  1. 局部敏感性 - 每个token的预测高度依赖紧邻上下文                 │
│  2. 路径依赖 - 早期token的选择影响后续整个生成轨迹                 │
│  3. 分布外脆弱 - 训练分布外的输入缺乏鲁棒性保证                    │
│                                                                 │
│  示例：                                                          │
│  输入A: "什么是光合作用？"                                       │
│  输入B: "请解释光合作用的概念"                                   │
│                                                                 │
│  虽然语义等价，但：                                               │
│  - 初始token分布不同（"光" vs "请"）                             │
│  - 生成路径分叉，可能导致不同答案                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 同义改写测试类型

| 改写类型 | 变换方法 | 预期行为 | 常见脆弱点 |
|---------|---------|---------|-----------|
| **词汇改写** | 同义词替换 | 核心语义保持 | 领域术语被替换导致专业性下降 |
| **句法改写** | 主动↔被动、语序调整 | 命题内容不变 | 否定词位置变化导致逻辑反转 |
| **语篇改写** | 段落重组、衔接词替换 | 整体意义等价 | 长距离依赖关系被破坏 |
| **跨语言改写** | 翻译往返 | 语义高度一致 | 文化特定概念丢失 |

```python
# 同义改写测试核心逻辑

class ParaphraseTester:
    """同义改写测试器"""
    
    def test_lexical_paraphrase(self, prompt: str, model) -> RobustnessResult:
        """
        词汇层面改写测试
        """
        # 生成词汇改写变体
        variations = [
            self.synonym_replace(prompt, ratio=0.3),  # 30%同义词替换
            self.synonym_replace(prompt, ratio=0.5),  # 50%同义词替换
        ]
        
        # 获取模型输出
        outputs = [model.generate(v) for v in variations]
        
        # 计算语义一致性
        consistency_scores = [
            self.semantic_similarity(outputs[0], o) 
            for o in outputs[1:]
        ]
        
        return RobustnessResult(
            test_type="lexical",
            variations=variations,
            outputs=outputs,
            consistency_scores=consistency_scores,
            is_robust=all(s > 0.8 for s in consistency_scores)
        )
    
    def test_syntactic_paraphrase(self, prompt: str, model) -> RobustnessResult:
        """
        句法层面改写测试
        """
        variations = [
            self.active_to_passive(prompt),    # 主动变被动
            self.reorder_clauses(prompt),       # 从句重排
            self.change_sentence_structure(prompt),  # 改变句式
        ]
        
        outputs = [model.generate(v) for v in variations]
        
        # 检查逻辑一致性（特别是否定词）
        logic_consistency = self.check_logic_consistency(outputs)
        
        return RobustnessResult(
            test_type="syntactic",
            variations=variations,
            outputs=outputs,
            logic_consistent=logic_consistency,
            is_robust=logic_consistency
        )
```

### 2.3 噪声注入测试设计

```
┌─────────────────────────────────────────────────────────────────┐
│                    噪声注入压力测试                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  噪声级别设计：                                                  │
│                                                                 │
│  Level 1 (5%噪声): 轻微干扰，模拟真实用户输入错误                 │
│    示例: "什么是光合作用" → "什么是光合zuo用"                    │
│                                                                 │
│  Level 2 (15%噪声): 中度干扰，测试容错能力                        │
│    示例: "什么是光合作用" → "什么是合光作用"                     │
│                                                                 │
│  Level 3 (30%噪声): 重度干扰，接近极限测试                        │
│    示例: "什么是光合作用" → "什么x光合 作用"                     │
│                                                                 │
│  Level 4 (50%噪声): 极端破坏，识别失效临界点                      │
│    示例: "什么是光xx用" （大部分信息丢失）                        │
│                                                                 │
│  评估指标：                                                      │
│  • 准确率衰减曲线（Accuracy vs Noise Level）                      │
│  • 失效临界点（性能骤降的噪声阈值）                               │
│  • 恢复能力（噪声移除后性能恢复程度）                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

```python
# 噪声注入核心逻辑

class NoiseInjector:
    """噪声注入器"""
    
    def inject_char_noise(self, text: str, noise_ratio: float) -> str:
        """
        字符级噪声注入
        
        Args:
            text: 原始文本
            noise_ratio: 噪声比例 (0.0 - 1.0)
        """
        chars = list(text)
        num_noisy = int(len(chars) * noise_ratio)
        
        noise_types = ['replace', 'insert', 'delete', 'swap']
        
        for _ in range(num_noisy):
            pos = random.randint(0, len(chars) - 1)
            noise_type = random.choice(noise_types)
            
            if noise_type == 'replace':
                chars[pos] = random.choice(string.ascii_letters)
            elif noise_type == 'insert':
                chars.insert(pos, random.choice(string.ascii_letters))
            elif noise_type == 'delete' and len(chars) > 1:
                chars.pop(pos)
            elif noise_type == 'swap' and pos < len(chars) - 1:
                chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
        
        return ''.join(chars)
    
    def inject_word_noise(self, text: str, noise_ratio: float) -> str:
        """
        词级噪声注入
        """
        words = text.split()
        num_noisy = int(len(words) * noise_ratio)
        
        for _ in range(num_noisy):
            pos = random.randint(0, len(words) - 1)
            noise_type = random.choice(['synonym', 'delete', 'repeat'])
            
            if noise_type == 'synonym':
                words[pos] = self.get_random_synonym(words[pos])
            elif noise_type == 'delete':
                words.pop(pos)
            elif noise_type == 'repeat':
                words.insert(pos, words[pos])
        
        return ' '.join(words)
```

### 2.4 鲁棒性评估指标

| 指标名称 | 计算方法 | 风险阈值 | 业务含义 |
|---------|---------|---------|---------|
| **语义一致性** | 改写前后输出的语义相似度 | < 0.8 | 同义敏感 |
| **准确率衰减率** | (无噪声准确率 - 有噪声准确率) / 无噪声准确率 | > 20% | 噪声脆弱 |
| **失效临界点** | 性能骤降的噪声比例 | < 30% | 容错能力差 |
| **逻辑一致性** | 改写前后逻辑判断一致性 | < 95% | 逻辑不稳定 |
| **格式稳定性** | 输出格式变化频率 | > 10% | 格式依赖 |

---

## 🧪 3. 实验验证任务

请运行本目录下的 `test_day11.py`，观察以下关键输出：

### 3.1 同义改写测试
- 词汇改写（同义词替换）
- 句法改写（主动被动转换）
- 语义一致性计算
- 鲁棒性判定

### 3.2 噪声注入测试
- 字符级噪声（5%、15%、30%、50%）
- 准确率衰减曲线
- 失效临界点识别

### 3.3 综合鲁棒性评估
- 多维度鲁棒性评分
- 风险等级矩阵
- 改进建议生成

---

## 📝 4. 产出要求

将运行结果贴回给 Trae，让其生成 `report_day11.md` 质量分析报告。

报告应包含：
1. **同义改写测试结果**：语义一致性分数、脆弱改写类型
2. **噪声注入测试结果**：准确率衰减曲线、失效临界点
3. **鲁棒性评估矩阵**：各维度鲁棒性评分
4. **风险场景清单**：高风险的改写模式和噪声类型
5. **改进建议**：提升鲁棒性的工程实践
