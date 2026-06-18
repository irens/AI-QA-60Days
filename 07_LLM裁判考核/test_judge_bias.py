"""
07 · LLM-as-a-Judge：用 AI 评 AI，谁守门？

前面 01（幻觉检测）、09（用例验收）都用了"裁判"或"参照"。但当你不得不
用 LLM 当裁判时——【裁判自己可不可信？】这就是本篇要守的门。

考核裁判最经典的一项：**位置偏见(position bias)**。
方法：每对答案（一好一坏，好坏有客观标准）换顺序问裁判两遍：
  - 顺序A：好答案放在"回答1"
  - 顺序B：好答案放在"回答2"
若裁判跟着"位置"走（总选第1个）而非跟着"质量"走，即暴露位置偏见。

两个量化指标：
  ① 准确率：裁判是否选中了那个【真正更好】的答案
  ② 位置一致性：换顺序后裁判是否仍选【同一个真实答案】

底线：未配置真实 API Key 时跳过(skip)，绝不伪造结果。
"""

import os
import re
import pytest
from dataclasses import dataclass
from typing import List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

MODEL = os.getenv("TEST_MODEL", "gpt-4o-mini")


# ==================== 考题：好坏有客观标准 ====================

@dataclass
class JudgeCase:
    question: str
    good: str   # 客观上更准确的答案
    bad: str    # 客观上错误的答案


CASES: List[JudgeCase] = [
    JudgeCase("地球绕太阳公转一圈大约需要多久？", "大约 365 天，也就是一年。", "大约 30 天。"),
    JudgeCase("水的化学式是什么？", "水的化学式是 H₂O。", "水的化学式是 CO₂。"),
    JudgeCase("一周有几天？", "一周有 7 天。", "一周有 5 天。"),
    JudgeCase("中华人民共和国的首都是哪里？", "北京。", "上海。"),
    JudgeCase("三角形的内角和是多少度？", "180 度。", "360 度。"),
    JudgeCase("光在真空中的速度约为多少？", "约每秒 30 万公里。", "约每秒 3 千公里。"),
]


JUDGE_PROMPT = """下面是针对同一个问题的两个回答，请判断哪个更准确、更好。
只回答数字 1 或 2，不要任何其他文字。

【问题】{q}

【回答1】{a1}

【回答2】{a2}

更好的是（只输出 1 或 2）："""


def _get_client():
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )


def _extract_content(resp) -> str:
    if hasattr(resp, "choices"):
        return resp.choices[0].message.content
    if isinstance(resp, dict):
        return resp["choices"][0]["message"]["content"]
    if isinstance(resp, str):
        return resp
    raise TypeError(f"无法解析响应：类型={type(resp)}")


def judge_pick(client, q: str, a1: str, a2: str) -> str:
    """让裁判在 a1/a2 中选更好的，返回 '1' 或 '2'。"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(q=q, a1=a1, a2=a2)}],
        temperature=0,
    )
    raw = _extract_content(resp).strip()
    if raw.lstrip().lower().startswith(("<!doctype", "<html")):
        raise RuntimeError("端点返回 HTML 而非模型输出——请检查 OPENAI_BASE_URL。")
    m = re.search(r"[12]", raw)
    if not m:
        raise ValueError(f"裁判未给出 1/2 选择，原始输出：{repr(raw)[:200]}")
    return m.group(0)


@pytest.fixture(scope="module")
def judgments():
    """对每个 case 跑两种顺序，返回逐对结果。"""
    c = _get_client()
    if c is None:
        pytest.skip("未配置真实 LLM（缺 OPENAI_API_KEY 或 openai 库）——按项目底线跳过，不伪造结果。")

    print("\n" + "=" * 64)
    print("⚖️  LLM 裁判考核 · 位置偏见检测")
    print("=" * 64)

    results = []
    for case in CASES:
        # 顺序A：好答案在位置1 → 正确应选 "1"
        pick_a = judge_pick(c, case.question, case.good, case.bad)
        # 顺序B：好答案在位置2 → 正确应选 "2"
        pick_b = judge_pick(c, case.question, case.bad, case.good)

        correct_a = (pick_a == "1")
        correct_b = (pick_b == "2")
        # 换顺序后是否仍选中"同一个真实答案"
        chose_good_a = correct_a
        chose_good_b = correct_b
        consistent = (chose_good_a == chose_good_b)

        results.append({"q": case.question, "correct_a": correct_a,
                        "correct_b": correct_b, "consistent": consistent})

        flag = "✅一致" if consistent else "⚠️翻转(位置偏见)"
        print(f"\n[{flag}] {case.question}")
        print(f"     顺序A(好在1) 选了{pick_a} {'✓' if correct_a else '✗'} | "
              f"顺序B(好在2) 选了{pick_b} {'✓' if correct_b else '✗'}")
    return results


def test_judge_position_consistency(judgments):
    """位置一致性：换顺序后裁判应仍选同一真实答案。低于阈值 = 有位置偏见，裁判不可信。"""
    consistent = sum(r["consistent"] for r in judgments)
    total = len(judgments)
    rate = consistent / total
    print(f"\n【位置一致性】 {consistent}/{total} = {rate:.0%}")
    assert rate >= 0.80, (
        f"位置一致性 {rate:.0%} < 80%，裁判存在明显位置偏见，"
        f"其评估结论不可信，不能用作质量门禁。"
    )


def test_judge_accuracy(judgments):
    """准确率：在 2N 次呈现中，裁判选中真正更好答案的比例。"""
    correct = sum(r["correct_a"] + r["correct_b"] for r in judgments)
    total = len(judgments) * 2
    rate = correct / total
    print(f"\n【裁判准确率】 {correct}/{total} = {rate:.0%}")
    assert rate >= 0.80, f"裁判准确率 {rate:.0%} < 80%，判别能力不足，不能用作裁判。"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
