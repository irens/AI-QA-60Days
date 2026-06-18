"""
03 · 鲁棒性：同义改写

守门点：语义相同、只是换了说法的问题，模型应给出一致的答案。
若"换个问法答案就变"，说明模型对表述方式过度敏感——这是隐蔽的质量缺陷
（用户用不同措辞提问，本应得到相同结论）。

方法：每个问题准备多个【语义等价】的改写，逐一提问，检查是否都命中正确答案。
判定客观：答案是否包含预期关键词。

门禁：鲁棒性（所有改写都答对的问题占比）>= 0.8。

底线：未配置真实 API Key 时跳过(skip)，绝不伪造结果。
"""

import os
import pytest
from dataclasses import dataclass
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

MODEL = os.getenv("TEST_MODEL", "gpt-4o-mini")


@dataclass
class RobustnessCase:
    name: str
    paraphrases: List[str]   # 语义等价的多种问法
    expected: str            # 正确答案应包含的关键词


CASES: List[RobustnessCase] = [
    RobustnessCase("法国首都",
                   ["法国的首都是哪里？", "请问法国首都是什么城市？", "哪座城市是法国的首都？"],
                   "巴黎"),
    RobustnessCase("一加一",
                   ["1 加 1 等于几？", "请计算 1 + 1。", "一加一的结果是多少？只要数字。"],
                   "2"),
    RobustnessCase("日出方向",
                   ["太阳从哪个方向升起？", "日出的方位是哪里？", "早晨太阳出现在哪一边？"],
                   "东"),
    RobustnessCase("水的状态",
                   ["水在 0 摄氏度以下会变成什么？", "零度以下的水是什么状态？", "把水冻起来会变成什么？"],
                   "冰"),
]


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


def ask(client, q: str) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": q}],
        temperature=0,
        max_tokens=100,
    )
    raw = _extract_content(resp).strip()
    if raw.lstrip().lower().startswith(("<!doctype", "<html")):
        raise RuntimeError("端点返回 HTML 而非模型输出——请检查 OPENAI_BASE_URL。")
    return raw


def test_robustness_to_paraphrasing():
    """同义改写下，答案应保持一致正确。鲁棒性 >= 0.8 才算稳。"""
    c = _get_client()
    if c is None:
        pytest.skip("未配置真实 LLM（缺 OPENAI_API_KEY 或 openai 库）——按项目底线跳过，不伪造结果。")

    print("\n" + "=" * 64)
    print("🔁 鲁棒性 · 同义改写")
    print("=" * 64)

    robust_count = 0
    for case in CASES:
        hits = []
        for q in case.paraphrases:
            ans = ask(c, q)
            hit = case.expected.lower() in ans.lower()
            hits.append(hit)
            print(f"   [{'✓' if hit else '✗'}] {q}  ->  {ans[:40]}")
        all_ok = all(hits)
        robust_count += all_ok
        flag = "✅稳健" if all_ok else "⚠️不稳（换说法答案就变）"
        print(f"[{flag}] {case.name}\n")

    rate = robust_count / len(CASES)
    print("-" * 64)
    print(f"鲁棒性: {robust_count}/{len(CASES)} = {rate:.0%}")
    print("-" * 64)

    assert rate >= 0.8, (
        f"鲁棒性 {rate:.0%} < 80%，模型对表述方式过度敏感，"
        f"换个问法就可能答错，存在稳定性风险。"
    )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
