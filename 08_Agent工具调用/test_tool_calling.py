"""
08 · Agent 工具调用正确性

守门点：Agent 的核心能力是用工具。要验证三件事——
  ① 该不该调：闲聊别乱调工具；有需求别漏调
  ② 选得对不对：选对工具
  ③ 参数准不准：从自然语言里抽对参数

方法：给模型工具清单，让它对每个请求输出 JSON 形式的工具调用，
      再客观核对【工具名】和【关键参数】。

门禁：工具调用正确率 >= 0.8。

底线：未配置真实 API Key 时跳过(skip)，绝不伪造结果。
"""

import os
import re
import json
import pytest
from dataclasses import dataclass, field
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

MODEL = os.getenv("TEST_MODEL", "gpt-4o-mini")

TOOLS_DESC = """你可以使用以下工具：
1. get_weather(city)  —— 查询某城市天气，参数 city 为城市名
2. calculate(expression) —— 计算数学表达式，参数 expression 为算式字符串
如果用户的请求不需要任何工具（如闲聊），则不调用工具。"""

PROMPT_TMPL = """{tools}

用户请求：{query}

请只输出一个 JSON，表示你要调用的工具。格式：
{{"tool": "工具名 或 none", "args": {{参数键值对}}}}
不要输出任何多余文字。"""


@dataclass
class ToolCase:
    query: str
    expect_tool: str
    expect_args_contains: List[str] = field(default_factory=list)


CASES: List[ToolCase] = [
    ToolCase("北京今天天气怎么样？", "get_weather", ["北京"]),
    ToolCase("查一下上海的天气", "get_weather", ["上海"]),
    ToolCase("帮我算一下 23 乘以 47 等于多少", "calculate", ["23", "47"]),
    ToolCase("100 加 200 是多少？", "calculate", ["100", "200"]),
    ToolCase("你好呀，今天心情不错", "none", []),
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


def decide_tool(client, query: str) -> dict:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user",
                   "content": PROMPT_TMPL.format(tools=TOOLS_DESC, query=query)}],
        temperature=0,
    )
    raw = _extract_content(resp).strip()
    if raw.lstrip().lower().startswith(("<!doctype", "<html")):
        raise RuntimeError("端点返回 HTML 而非模型输出——请检查 OPENAI_BASE_URL。")
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError(f"未返回可解析的 JSON：{repr(raw)[:200]}")
    return json.loads(m.group(0))


def check(case: ToolCase, decision: dict) -> bool:
    tool = str(decision.get("tool", "")).lower()
    if case.expect_tool == "none":
        return tool in ("none", "", "null")
    if tool != case.expect_tool:
        return False
    args_dump = json.dumps(decision.get("args", {}), ensure_ascii=False)
    return all(kw in args_dump for kw in case.expect_args_contains)


def test_tool_calling_correctness():
    """工具调用正确率（选对工具 + 参数对）必须 >= 0.8。"""
    c = _get_client()
    if c is None:
        pytest.skip("未配置真实 LLM——按项目底线跳过，不伪造结果。")

    print("\n" + "=" * 64)
    print("🔧 Agent 工具调用正确性")
    print("=" * 64)

    correct = 0
    for case in CASES:
        decision = decide_tool(c, case.query)
        ok = check(case, decision)
        correct += ok
        print(f"   [{'✓' if ok else '✗'}] {case.query}")
        print(f"        期望 tool={case.expect_tool} {case.expect_args_contains} | 实际={decision}")

    rate = correct / len(CASES)
    print(f"\n工具调用正确率: {correct}/{len(CASES)} = {rate:.0%}")
    assert rate >= 0.8, f"工具调用正确率 {rate:.0%} < 80%，Agent 的工具决策不可靠。"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
