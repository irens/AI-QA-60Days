"""
02 · 温度与采样：输出稳定性

守门点：很多业务（分类、抽取、事实问答）需要【可复现】的输出。
温度(temperature)直接决定随机性——温度越低越稳定。
但"温度=0"也不保证 100% 一致（贪婪解码仍可能受基础设施影响）。

方法：同一 prompt 重复调用 N 次，分别在低温(0)与高温(1.3)下，
测量"稳定性"= 出现最多的那个答案占比。

门禁：低温下稳定性必须 >= 0.8（否则不适合用于需可复现的业务）。

底线：未配置真实 API Key 时跳过(skip)，绝不伪造结果。
"""

import os
import pytest
from collections import Counter

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

MODEL = os.getenv("TEST_MODEL", "gpt-4o-mini")
N_CALLS = 5
PROMPT = "用一个数字回答：水在标准大气压下的沸点是多少摄氏度？只回答数字。"


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


def call(client, temperature: float) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=temperature,
        max_tokens=50,
    )
    raw = _extract_content(resp).strip()
    if raw.lstrip().lower().startswith(("<!doctype", "<html")):
        raise RuntimeError("端点返回 HTML 而非模型输出——请检查 OPENAI_BASE_URL。")
    return raw


def stability(responses) -> float:
    """稳定性 = 出现最多的答案占比（归一化后比较）。"""
    norm = [r.strip().lower() for r in responses]
    most_common_count = Counter(norm).most_common(1)[0][1]
    return most_common_count / len(norm)


@pytest.fixture(scope="module")
def runs():
    c = _get_client()
    if c is None:
        pytest.skip("未配置真实 LLM（缺 OPENAI_API_KEY 或 openai 库）——按项目底线跳过，不伪造结果。")

    print("\n" + "=" * 64)
    print("🌡️  温度与采样 · 输出稳定性")
    print("=" * 64)

    low = [call(c, 0.0) for _ in range(N_CALLS)]
    high = [call(c, 1.3) for _ in range(N_CALLS)]

    print(f"\n低温(0.0) {N_CALLS} 次: {low}")
    print(f"高温(1.3) {N_CALLS} 次: {high}")
    return {"low": low, "high": high}


def test_low_temperature_is_stable(runs):
    """低温下输出必须高度稳定（>= 0.8），才适合用于需可复现的业务。"""
    s = stability(runs["low"])
    print(f"\n低温稳定性: {s:.0%}")
    assert s >= 0.8, f"低温稳定性 {s:.0%} < 80%，输出不可复现，不适合确定性业务。"


def test_temperature_affects_diversity(runs):
    """对照：高温稳定性不应高于低温（温度确实在起作用）。"""
    s_low = stability(runs["low"])
    s_high = stability(runs["high"])
    print(f"\n低温稳定性={s_low:.0%} | 高温稳定性={s_high:.0%}")
    assert s_high <= s_low, (
        f"高温稳定性 {s_high:.0%} 高于低温 {s_low:.0%}，温度未按预期影响随机性，需排查。"
    )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
