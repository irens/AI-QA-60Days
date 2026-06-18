"""
09 · 用 AI 生成测试用例，如何验收质量

群聊真实痛点："AI 写的用例还要我花时间擦屁股。"
守门点：AI 生成的测试用例不能直接用——它可能给出【错误的预期结果】，
        也可能只覆盖 happy path。必须用一个可信参照(oracle)来客观验收。

靶子：闰年判断（有确定性标准答案）。让 AI 生成用例，再用参照实现核对：
  ① 预期正确性：AI 标的 expected 对不对
  ② 覆盖度：是否覆盖全部 4 个关键等价类（尤其 B3 这种坑）

底线：未配置真实 API Key 时跳过(skip)，绝不伪造结果。
"""

import os
import re
import json
import pytest

# 自动加载 .env（override 优先，避免被残留 shell 变量覆盖）
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

MODEL = os.getenv("TEST_MODEL", "gpt-4o-mini")


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


# ==================== 可信参照（oracle）：唯一事实来源 ====================

def is_leap_year(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


# 关键等价类：好的测试集必须覆盖这 4 类
def bucket_of(year: int) -> str:
    if year % 400 == 0:
        return "B2_整除400_闰"
    if year % 100 == 0:
        return "B3_整除100非400_平"   # 最易被漏/答错的坑
    if year % 4 == 0:
        return "B1_整除4非100_闰"
    return "B4_不整除4_平"


ALL_BUCKETS = {"B1_整除4非100_闰", "B2_整除400_闰", "B3_整除100非400_平", "B4_不整除4_平"}


# ==================== 让 AI 生成测试用例 ====================

SPEC = ("判断公历年份是否为闰年。规则：能被 4 整除但不能被 100 整除的是闰年；"
        "能被 400 整除的也是闰年；其余都不是。")

GEN_PROMPT = """你是测试工程师。请为下面这个函数生成 8 条测试用例。
函数规格：{spec}

只输出 JSON 数组，每个元素形如 {{"year": 整数, "expected": true 或 false}}，
expected 表示该年是否为闰年。不要输出多余文字。"""


def _extract_content(resp) -> str:
    """兼容不同 SDK 返回形态：标准对象 / dict / 纯字符串。"""
    if hasattr(resp, "choices"):
        return resp.choices[0].message.content
    if isinstance(resp, dict):
        return resp["choices"][0]["message"]["content"]
    if isinstance(resp, str):
        return resp
    raise TypeError(f"无法解析响应：类型={type(resp)}，内容={repr(resp)[:200]}")


def generate_cases(client) -> list:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": GEN_PROMPT.format(spec=SPEC)}],
        temperature=0,
    )
    raw = _extract_content(resp).strip()
    # 端点健康检查：HTML 几乎一定是 base_url 配错
    if raw.lstrip().lower().startswith(("<!doctype", "<html")):
        raise RuntimeError("端点返回 HTML 而非模型输出——请检查 OPENAI_BASE_URL。")
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        raise ValueError(f"AI 未返回可解析的 JSON 数组：{repr(raw)[:300]}")
    return json.loads(match.group(0))


# ==================== 验收 ====================

@pytest.fixture(scope="module")
def cases():
    c = _get_client()
    if c is None:
        pytest.skip("未配置真实 LLM（缺 OPENAI_API_KEY 或 openai 库）——按项目底线跳过，不伪造结果。")
    data = generate_cases(c)
    assert isinstance(data, list) and data, "AI 未生成任何用例"
    print("\n" + "=" * 64)
    print(f"🤖 AI 生成了 {len(data)} 条测试用例")
    print("=" * 64)
    for c_ in data:
        print(f"   year={c_.get('year')}, expected={c_.get('expected')}")
    return data


def test_ai_cases_expected_correctness(cases):
    """
    验收①：AI 标注的【预期结果】必须正确（用可信参照核对）。
    否则等于把错误固化进测试集——这是 L1 阻断级风险。
    """
    wrong = []
    for c in cases:
        truth = is_leap_year(int(c["year"]))
        if bool(c["expected"]) != truth:
            wrong.append((c["year"], c["expected"], truth))

    total = len(cases)
    print(f"\n【验收①·预期正确性】 {total - len(wrong)}/{total} 正确")
    for y, exp, truth in wrong:
        print(f"   ❌ year={y}: AI 标 expected={exp}，实际应为 {truth}")

    assert not wrong, (
        f"AI 生成的用例里有 {len(wrong)} 条预期结果是错的，"
        f"直接采用会把 bug 固化进测试集，必须人工修正后才能用。"
    )


def test_ai_cases_coverage(cases):
    """
    验收②：必须覆盖全部 4 个关键等价类。
    尤其 B3（能被 100 整除但不被 400 整除，如 1900）——AI 最常漏的坑。
    """
    covered = {bucket_of(int(c["year"])) for c in cases}
    missing = ALL_BUCKETS - covered

    print(f"\n【验收②·覆盖度】 覆盖 {len(covered)}/4 个等价类: {sorted(covered)}")
    if missing:
        print(f"   ⚠️ 缺失等价类: {sorted(missing)}")

    assert not missing, f"AI 用例未覆盖关键等价类: {sorted(missing)}，覆盖率虚高，需补充。"


if __name__ == "__main__":
    c = _get_client()
    if c is None:
        print("未配置真实 LLM，无法运行（不伪造结果）。请先配置 .env。")
    else:
        data = generate_cases(c)
        print(f"AI 生成 {len(data)} 条用例：{data}")
        # 简易自检
        wrong = [(x["year"], x["expected"], is_leap_year(int(x["year"])))
                 for x in data if bool(x["expected"]) != is_leap_year(int(x["year"]))]
        covered = {bucket_of(int(x["year"])) for x in data}
        print("预期错误:", wrong or "无")
        print("覆盖等价类:", sorted(covered), "| 缺失:", sorted(ALL_BUCKETS - covered) or "无")
