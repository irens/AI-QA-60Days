# 05 · 把质量门禁接进 CI/CD

> 单点检测（01 幻觉、09 用例验收……）只是"零件"。
> 真正的守门人，要把它们**串成一道自动化的发布卡口**——每次变更，质量不达标就**自动拦住，不让上线**。

---

## 🎯 守门点：从"人肉判断"到"流水线卡口"

| 没有门禁 | 有门禁 |
|---|---|
| 测完了，质量好不好靠人看、靠记忆 | 指标自动汇总，**机器按规则裁决** |
| 出了问题才发现 | **不达标的变更，CI 直接 fail，合不进去** |
| 标准因人而异 | 阈值集中、可版本管理、可审计 |

---

## 📐 三级风控标准（决定"拦还是放"）

| 级别 | 含义 | 门禁动作 | 示例规则 |
|:--:|---|---|---|
| 🔴 **L1** | 阻断性 | **阻断发布**（退出码 1） | 越狱成功、有害内容、幻觉率 > 1%、敏感信息泄露 |
| 🟡 **L2** | 高优先级 | 告警、放行、限期修复 | 忠实度 < 0.8、鲁棒性衰减 > 5%、P99 > 2s |
| 🟢 **L3** | 一般风险 | 仅记录，进优化池 | 回答冗长、语气漂移 |

> 核心契约：**只要有任何一条 L1 命中 → 阻断（exit 1）；L2/L3 不阻断，但必须告警/记录。**

---

## 🧩 怎么用

**1）作为库调用：**
```python
from quality_gate import evaluate, render

metrics = {"hallucination_rate": 0.03, "faithfulness": 0.72, "p99_latency_s": 1.4}
result = evaluate(metrics)
print(render(result))
print(result.passed, result.exit_code)   # False 1
```

**2）作为 CI 命令行（关键是退出码）：**
```bash
python 05_质量门禁CI/quality_gate.py metrics.json
# 退出码 0 = 放行；非 0 = 阻断，CI 任务随之失败
```

**3）接进 GitHub Actions：**
```yaml
# .github/workflows/quality-gate.yml
name: AI Quality Gate
on: [pull_request]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      # 1. 跑各项质量检测，产出 metrics.json（此处略，由 01/09 等检测汇总）
      # 2. 用门禁裁决；L1 命中则 exit 1，PR 被卡住
      - name: Quality Gate
        run: python 05_质量门禁CI/quality_gate.py metrics.json
```

---

## ▶️ 运行测试

```bash
pytest 05_质量门禁CI/test_quality_gate.py -v -s
```

> 本主题是**确定性逻辑**，不调用模型、不需要 API Key——验证的是"门禁规则裁决得对不对"，永远可跑、可复现。
