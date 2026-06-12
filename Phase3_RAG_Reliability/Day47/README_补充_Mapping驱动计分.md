# Day 47 补充章节：Mapping 驱动计分方法 (v2)

> **补充来源**: gjz_agent_python 项目工程化实践
> **补充位置**: 第 2.5 节，插入在 "2.4 输出格式稳定性策略" 之后
> **补充价值**: 解决 LLM Judge 评分中 tp/fp/fn 计数不一致的核心痛点

---

## 2.5 Mapping 驱动计分方法（v2）— 工程化最佳实践

### 2.5.1 问题：为什么 LLM 直接计数不可靠？

在 LLM-as-a-Judge 评估中，最常见的做法是让 LLM 直接输出 `tp/fp/fn` 计数：

```json
// ❌ 传统做法：LLM 直接输出计数
{
  "tp_list": ["恶寒", "发热"],
  "fp_list": ["咳嗽"],
  "fn_list": ["头痛"],
  "score": 0.67
}
```

**问题**：
- LLM 经常出现 `tp + fn ≠ expected总数` 的计数不一致
- 同一个症状可能同时出现在 tp 和 fn 中
- 短 TP 表述（如"恶寒"）与长 expected 原文（如"新起恶寒重"）的映射关系模糊
- 复合症状（如"痰多质稀"）被 Agent 拆成"痰多"+"痰质稀"时，LLM 难以准确计数

### 2.5.2 核心思想：LLM 只管语义对齐，代码确定性地推导 P/R/F1

**分离关注点**：让 LLM 做它擅长的事（语义对齐），让代码做它擅长的事（精确计数）。

```
┌─────────────────────────────────────────────────────────────────┐
│                   Mapping 驱动计分架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐                                               │
│  │  LLM Judge    │  ◀── 只做语义对齐，输出 mapping 表             │
│  │  (语义对齐)    │      不输出 score/tp/fp/fn                    │
│  └──────┬───────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────────────────────────────────────┐               │
│  │  compute_metrics_from_mappings (纯函数)       │               │
│  │  ◀── 确定性推导 P/R/F1                       │               │
│  │                                              │               │
│  │  Recall  = |{expected 被覆盖}| / |expected|   │               │
│  │  Precision = |consumed_actual| / (|consumed| + |fp|) │       │
│  │                                              │               │
│  │  保证：                                       │              │
│  │  • tp + fn = expected总数（Recall 自洽）      │               │
│  │  • consumed ∩ fp = ∅（Precision 互斥）        │               │
│  └──────────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5.3 LLM Judge 输出格式：Mapping 表

让 LLM 输出语义对齐映射表，而不是直接计数：

```json
// ✅ 新做法：LLM 输出 mapping 表
{
  "mappings": [
    {"expected": "新病无汗", "actual": ["无汗"]},
    {"expected": "痰多质稀", "actual": ["痰多", "痰质稀"]},
    {"expected": "鼻塞流清涕", "actual": ["鼻塞", "流清涕"]},
    {"expected": "恶寒", "actual": ["恶寒"]}
  ],
  "unmatched_actual": ["腹泻", "纳呆", "失眠"],
  "unmatched_expected": ["口不渴"],
  "explanation": "Agent将'痰多质稀'拆为'痰多'和'痰质稀'，语义一致；'口不渴'未在Agent输出中找到匹配"
}
```

**关键约束**（在 Prompt 中强制执行）：
1. 每条 `expected` 最多出现在一个 mapping 中
2. 每条 `actual` 在所有 mapping 的 actual 列表中最多出现一次
3. 进入 mapping 的 actual 不得再出现在 `unmatched_actual` 中
4. `len(mappings) + len(unmatched_expected) = 专家标签总数`
5. 所有 actual 的并集 + unmatched_actual 应覆盖 Agent 输出全部

### 2.5.4 代码确定性计分

```python
def compute_metrics_from_mappings(
    expected: List[str],
    actual: List[str],
    mappings: List[Dict[str, Any]],
    unmatched_actual: List[str],
    unmatched_expected: List[str],
) -> Dict[str, Any]:
    """
    从 mapping 表确定性推导 P/R/F1。
    
    核心规则：
    - Recall 以专家标签为单位：每个 expected 要么被覆盖（在mapping里），
      要么在 unmatched_expected 里
    - Precision 以 Agent 输出为单位：每条 actual 只归 consumed 或 FP 之一
    - consumed_actual = mappings 中出现的所有 actual（去重）
    - fp_list = unmatched_actual（真正 FP）
    - tp_list = mappings 中的 expected（被覆盖的专家标签）
    - fn_list = unmatched_expected（未被覆盖的专家标签）
    """
    expected_clean = _unique_list(expected)
    actual_clean = _unique_list(actual)

    # 边界：两者都为空
    if not expected_clean and not actual_clean:
        return {
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "tp_list": [],
            "fp_list": [],
            "fn_list": [],
            "consumed_actual": [],
            "matched_pairs": mappings,
        }

    # 边界：actual 为空（expected 非空）
    if not actual_clean:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "tp_list": [],
            "fp_list": [],
            "fn_list": list(expected_clean),
            "consumed_actual": [],
            "matched_pairs": mappings,
        }

    # 边界：expected 为空（actual 非空）
    if not expected_clean:
        return {
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "tp_list": [],
            "fp_list": [],
            "fn_list": [],
            "consumed_actual": [],
            "matched_pairs": mappings,
        }

    # 从 mappings 提取 tp_list 和 consumed_actual
    tp_list: List[str] = []
    consumed_actual: List[str] = []
    consumed_actual_keys: Set[str] = set()

    for m in mappings:
        exp = m.get("expected", "").strip()
        actual_items = m.get("actual", [])
        has_actual = any(str(a).strip() for a in actual_items)
        if not has_actual:
            continue  # actual=[] 表示该 expected 未被覆盖

        # expected 被覆盖 → 归入 TP
        matched_exp = _find_expected_match(exp, expected_clean, tp_list)
        if matched_exp:
            tp_list.append(matched_exp)

        # 收集 consumed actual
        for act in actual_items:
            act = str(act).strip()
            if act and _normalize(act) not in consumed_actual_keys:
                consumed_actual.append(act)
                consumed_actual_keys.add(_normalize(act))

    # fn_list = expected 中未被覆盖的
    tp_keys = {_normalize(t) for t in tp_list}
    fn_list = [e for e in expected_clean if _normalize(e) not in tp_keys]

    # fp_list = unmatched_actual（清洗后）
    fp_list = _unique_list(unmatched_actual)
    fp_keys = {_normalize(f) for f in fp_list}
    overlap = consumed_actual_keys & fp_keys
    if overlap:
        fp_list = [f for f in fp_list if _normalize(f) not in consumed_actual_keys]

    # 计分
    tp_count = len(tp_list)
    consumed_count = len(consumed_actual)
    fp_count = len(fp_list)

    recall = tp_count / len(expected_clean) if expected_clean else 1.0
    precision = consumed_count / (consumed_count + fp_count) if (consumed_count + fp_count) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp_list": tp_list,
        "fp_list": fp_list,
        "fn_list": fn_list,
        "consumed_actual": consumed_actual,
        "matched_pairs": mappings,
    }
```

### 2.5.5 对比：传统方法 vs Mapping 驱动方法

| 维度 | 传统方法（LLM 直接计数） | Mapping 驱动方法（v2） |
|------|------------------------|---------------------|
| **LLM 职责** | 语义对齐 + 计数 | 仅语义对齐 |
| **计数方式** | LLM 推理（不可靠） | 代码确定性推导（可靠） |
| **计数一致性** | 经常出现 tp+fn≠expected | 100% 自洽（数学保证） |
| **复合症状处理** | 容易出错 | 通过 mapping 自然处理 |
| **可调试性** | 黑盒，难以定位错误 | 映射表可追溯，每个 TP/FP/FN 有来源 |
| **可复用性** | 不同场景需重新设计 Prompt | 计分逻辑场景无关，可复用 |
| **Prompt 设计难度** | 高（需同时约束语义和计数） | 低（只需约束语义对齐） |

### 2.5.6 实际案例

**案例**：FEI_GM_01（风寒感冒，17个专家标签，24个Agent输出）

```python
# LLM 输出的 mapping 表
mappings = [
    {"expected": "新病无汗", "actual": ["无汗"]},
    {"expected": "痰多质稀", "actual": ["痰多", "痰质稀"]},
    {"expected": "鼻塞流清涕", "actual": ["鼻塞", "流清涕"]},
    {"expected": "新近感受风寒", "actual": ["新近感受风寒"]},
    {"expected": "身痛", "actual": ["身痛"]},
    {"expected": "咳嗽", "actual": ["咳嗽"]},
    {"expected": "恶寒", "actual": ["恶寒"]},
    {"expected": "发热", "actual": ["发热"]},
    {"expected": "头痛", "actual": ["头痛"]},
    {"expected": "舌苔薄白", "actual": ["舌苔薄白"]},
    {"expected": "脉浮紧", "actual": ["脉浮紧"]},
    {"expected": "口不渴", "actual": ["口淡", "渴不欲饮"]},
    {"expected": "喷嚏", "actual": ["喷嚏"]},
    {"expected": "肢节酸痛", "actual": ["肢节酸痛"]},
    {"expected": "鼻痒", "actual": ["鼻痒"]},
    {"expected": "咽痒", "actual": ["咽痒"]},
    {"expected": "咳嗽声重", "actual": ["咳嗽声重"]},
]
unmatched_actual = ["腹泻", "纳呆", "失眠", "尿多"]
unmatched_expected = []

result = compute_metrics_from_mappings(
    expected=expected, actual=actual,
    mappings=mappings,
    unmatched_actual=unmatched_actual,
    unmatched_expected=unmatched_expected,
)

# 结果：
# recall = 17/17 = 1.0（所有专家标签被覆盖）
# precision = 20/(20+4) = 0.8333（consumed=20, fp=4）
# f1 = 2*1.0*0.8333/(1.0+0.8333) = 0.9091
# 无汗、痰多、流清涕、身痛 均不在 fp_list 中 ✓
# consumed_actual ∩ fp_list = ∅ ✓
```

### 2.5.7 适用场景

Mapping 驱动计分特别适合以下场景：

| 场景 | 为什么适合 |
|------|-----------|
| **信息抽取**（如症状提取、实体识别） | 输出是结构化列表，天然适合做映射对齐 |
| **复合语义拆分**（如"痰多质稀"→"痰多"+"痰质稀"） | mapping 可以一条 expected 对应多条 actual |
| **近义词/口语-术语映射**（如"胃口不好"↔"纳呆"） | 语义对齐而非字符串匹配 |
| **需要可追溯的评估结果** | 每个 TP/FP/FN 都可追溯到具体 mapping 条目 |

### 2.5.8 工程落地建议

1. **温度设为 0**：确保 mapping 表输出稳定可复现
2. **强制 JSON 输出**：使用 `response_format: json_object` 或 Prompt 约束 + 正则兜底
3. **后处理清洗**：代码侧做 `sanitize` 步骤，确保 unmatched 与 mapping 互斥
4. **黄金测试集**：针对典型案例建立黄金测试（Golden Tests），确保计分逻辑正确
5. **Layer 评估**：`final_score = 0.4 × F1(rule-based) + 0.6 × LLM_Judge_score(mapping)`

---

## 🧪 补充实验：Mapping 驱动计分 vs 传统计分

请运行 `test_day47_mapping.py`，观察以下测试场景：

1. **G1-G9 黄金测试**：验证计分逻辑在 9 个典型 case 上的正确性
2. **传统方法 vs Mapping 方法对比**：同一 case 两种方法的一致性差异
3. **边界测试**：空 expected、空 actual、全部匹配、全部不匹配

---

## 📝 补充产出要求

实验报告应包含：
- 传统方法 vs Mapping 方法的计数一致性对比
- 各黄金测试 case 的 Precision/Recall/F1 验证
- 两种方法在复合症状处理上的差异分析