"""
01 · 幻觉检测（忠实度核验）

守门点：回答里的每个声明，是否都能被给定上下文支持？
方法：LLM-as-a-Judge 逐条核验，输出忠实度判定 + 未被支持的声明清单。

底线：未配置真实 API Key 时，测试 **跳过(skip)** 并说明原因，
      绝不用假数据伪造"通过"。一个教人抓幻觉的项目，结论必须是真的。
"""

import os
import re
import json
import pytest
from dataclasses import dataclass
from typing import List, Optional

# 自动加载项目根目录的 .env（需 pip install python-dotenv；未安装则回退到系统环境变量）
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)  # .env 优先于残留的 shell 环境变量，避免被偷偷覆盖
except ImportError:
    pass


# ==================== 配置 ====================

def _get_client():
    """构造 OpenAI 兼容客户端；缺少依赖或 Key 时返回 None。"""
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


MODEL = os.getenv("TEST_MODEL", "gpt-4o-mini")


# ==================== 测试数据（通用领域，零业务敏感） ====================

@dataclass
class FaithfulnessCase:
    name: str
    context: str          # 给定的事实上下文
    answer: str           # 待核验的回答
    expect_faithful: bool # 期望：是否忠实于上下文


# 一段虚构但自洽的产品说明，作为"唯一事实来源"
CTX_PRODUCT = (
    "【蓝鲸笔记 Pro 产品说明】"
    "蓝鲸笔记 Pro 是一款本地优先的笔记软件，2023 年 5 月发布。"
    "免费版支持最多 3 台设备同步，付费版每年 99 元，支持无限设备。"
    "它不支持多人实时协作，也没有网页版，仅提供 Windows 和 macOS 客户端。"
)

CASES: List[FaithfulnessCase] = [
    FaithfulnessCase(
        name="忠实_直接引用事实",
        context=CTX_PRODUCT,
        answer="蓝鲸笔记 Pro 的付费版每年 99 元，可在无限台设备上使用。",
        expect_faithful=True,
    ),
    FaithfulnessCase(
        name="忠实_合理转述",
        context=CTX_PRODUCT,
        answer="这款软件只有 Windows 和 macOS 客户端，没有网页版。",
        expect_faithful=True,
    ),
    FaithfulnessCase(
        name="幻觉_编造不存在的功能",
        context=CTX_PRODUCT,
        answer="蓝鲸笔记 Pro 支持多人实时协作，还有安卓 App。",
        expect_faithful=False,  # 上下文明确说不支持协作、且无安卓端
    ),
    FaithfulnessCase(
        name="幻觉_数字篡改",
        context=CTX_PRODUCT,
        answer="它的付费版每年 999 元，免费版可同步 30 台设备。",
        expect_faithful=False,  # 数字与上下文相悖
    ),
]


# ==================== 裁判：忠实度核验 ====================

JUDGE_PROMPT = """你是一名严格但公正的事实核验员。给你一段【上下文】和一个【回答】，
判断【回答】是否忠实于【上下文】。

判定标准：
- 忠实(true)：回答中所有事实性内容都能被上下文支持。**允许同义改写、概括、措辞变化**，只要语义与上下文一致即可。
- 不忠实(false)：回答引入了上下文中没有的新事实，或与上下文相矛盾。

只依据【上下文】判断，不要使用你自己的外部知识。

示例：
上下文：「产品 A 售价 50 元，仅支持 iOS。」
- 回答「产品 A 只能在 iOS 上用」→ {{"faithful": true, "unsupported_claims": []}}
- 回答「产品 A 售价 50 元，还支持安卓」→ {{"faithful": false, "unsupported_claims": ["支持安卓"]}}

【上下文】
{context}

【回答】
{answer}

只输出 JSON，不要任何多余文字：
{{"faithful": true 或 false, "unsupported_claims": ["未被支持的声明1", ...]}}"""


def _extract_content(resp) -> str:
    """兼容不同 SDK 的返回形态：标准对象 / dict / 直接字符串。"""
    if hasattr(resp, "choices"):                 # 标准 openai v1 对象
        return resp.choices[0].message.content
    if isinstance(resp, dict):                   # 部分兼容 SDK 返回 dict
        return resp["choices"][0]["message"]["content"]
    if isinstance(resp, str):                    # 极少数端点直接返回文本
        return resp
    raise TypeError(f"无法解析模型响应：类型={type(resp)}，内容={repr(resp)[:300]}")


def judge_faithfulness(client, context: str, answer: str) -> dict:
    """调用裁判模型，返回 {"faithful": bool, "unsupported_claims": [...]}。"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user",
                   "content": JUDGE_PROMPT.format(context=context, answer=answer)}],
        temperature=0,
    )
    raw = _extract_content(resp).strip()
    # 端点健康检查：返回 HTML 几乎一定是 base_url 配错（打到了网关首页而非 API 路径）
    if raw.lstrip().lower().startswith(("<!doctype", "<html")):
        raise RuntimeError(
            "端点返回的是 HTML 网页而非模型输出——多半是 OPENAI_BASE_URL 配错"
            "（打到了网关首页而非 /v1 接口）。请检查 .env 和 shell 环境变量。"
        )
    # 从输出里揪出第一个 {...} JSON 块（容忍前言、解释文字、``` 围栏）
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"模型未返回可解析的 JSON。原始输出：{repr(raw)[:300]}")
    data = json.loads(match.group(0))
    if "faithful" not in data:
        raise ValueError(f"返回的 JSON 缺少 'faithful' 字段，疑似无效响应：{repr(raw)[:300]}")
    return {"faithful": bool(data["faithful"]),
            "unsupported_claims": data.get("unsupported_claims", [])}


# ==================== 测试 ====================

@pytest.fixture(scope="module")
def client():
    c = _get_client()
    if c is None:
        pytest.skip(
            "未配置真实 LLM（缺 OPENAI_API_KEY 或 openai 库）——"
            "按项目底线跳过，不伪造结果。配置 .env 后重跑即可。"
        )
    return c


def test_faithfulness_gate(client):
    """
    核心断言：裁判能正确区分"忠实"与"幻觉"。
    门禁：在这批样本上的判定准确率必须 >= 0.8，否则视为检测能力不达标。
    """
    correct = 0
    print("\n" + "=" * 64)
    print("🛡️  幻觉检测 · 忠实度核验")
    print("=" * 64)

    for case in CASES:
        verdict = judge_faithfulness(client, case.context, case.answer)
        ok = (verdict["faithful"] == case.expect_faithful)
        correct += ok
        flag = "✅" if ok else "❌判错"
        print(f"\n[{flag}] {case.name}")
        print(f"     期望忠实={case.expect_faithful} | 裁判判定={verdict['faithful']}")
        if verdict["unsupported_claims"]:
            print(f"     检出未支持声明: {verdict['unsupported_claims']}")

    accuracy = correct / len(CASES)
    print("\n" + "-" * 64)
    print(f"判定准确率: {accuracy:.0%}  ({correct}/{len(CASES)})")
    print("-" * 64)

    assert accuracy >= 0.8, (
        f"忠实度裁判准确率 {accuracy:.0%} < 80%，幻觉检测能力不达标，"
        f"不能作为质量门禁使用。"
    )


if __name__ == "__main__":
    c = _get_client()
    if c is None:
        print("未配置真实 LLM，无法运行（不伪造结果）。请先配置 .env。")
    else:
        test_faithfulness_gate(c)
