"""
06 · RAG 评估：检索准不准 vs 答得对不对

守门点：RAG 系统必须把两件事【解耦】来测——
  ① 检索层：有没有捞到包含答案的资料？（Context Recall）
  ② 生成层：基于资料答得对不对？（Answer Correctness）
混在一起测，出了问题分不清是"没捞到"还是"捞到了却答错"。

本主题：用一个极简知识库 + 朴素检索器演示这套解耦评估。
  - 检索层测试：确定性，不需 API Key，永远可跑
  - 生成层测试：真实调用模型

底线：未配置真实 API Key 时，生成层测试跳过(skip)，绝不伪造结果。
"""

import os
import re
import pytest
from dataclasses import dataclass
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

MODEL = os.getenv("TEST_MODEL", "gpt-4o-mini")


# ==================== 极简知识库（通用，零业务敏感） ====================

KB = [
    {"id": "D1", "text": "蓝鲸笔记 Pro 的付费版每年 99 元，支持无限台设备。"},
    {"id": "D2", "text": "蓝鲸笔记 Pro 于 2023 年 5 月发布，仅提供 Windows 和 macOS 客户端。"},
    {"id": "D3", "text": "蓝鲸笔记 Pro 不支持多人实时协作，也没有网页版。"},
    {"id": "D4", "text": "蓝鲸笔记的免费版最多支持 3 台设备同步。"},
]


@dataclass
class RagCase:
    query: str
    gold_doc: str   # 应被检索到的文档 id
    gold_kw: str    # 正确答案应包含的关键词


CASES: List[RagCase] = [
    RagCase("付费版每年多少钱？", "D1", "99"),
    RagCase("蓝鲸笔记 Pro 提供哪些客户端？", "D2", "windows"),
    RagCase("免费版最多能同步几台设备？", "D4", "3"),
]


# ==================== 朴素检索器（确定性；字符 bigram 重叠） ====================

def _bigrams(s: str):
    s = re.sub(r"\s", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def retrieve(query: str):
    """返回 bigram 重叠最高的文档（朴素但确定）。"""
    qb = _bigrams(query)
    scored = sorted(KB, key=lambda d: len(qb & _bigrams(d["text"])), reverse=True)
    return scored[0]


# ==================== 模型调用 ====================

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


def generate(client, query: str, context: str) -> str:
    prompt = (f"只根据下面的资料回答问题，不要使用资料以外的知识。\n\n"
              f"资料：{context}\n\n问题：{query}")
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=100,
    )
    raw = _extract_content(resp).strip()
    if raw.lstrip().lower().startswith(("<!doctype", "<html")):
        raise RuntimeError("端点返回 HTML 而非模型输出——请检查 OPENAI_BASE_URL。")
    return raw


# ==================== ① 检索层（确定性，不需 Key） ====================

def test_retrieval_recall():
    """检索层：是否捞到了包含答案的正确文档。"""
    print("\n" + "=" * 64)
    print("🔎 RAG 评估 · ① 检索层")
    print("=" * 64)
    hit = 0
    for case in CASES:
        doc = retrieve(case.query)
        ok = (doc["id"] == case.gold_doc)
        hit += ok
        print(f"   [{'✓' if ok else '✗'}] {case.query} -> 命中 {doc['id']}（期望 {case.gold_doc}）")
    rate = hit / len(CASES)
    print(f"\n检索命中率: {hit}/{len(CASES)} = {rate:.0%}")
    assert rate >= 0.8, f"检索命中率 {rate:.0%} < 80%，资料没捞对，生成层再强也没用。"


# ==================== ② 生成层（真实模型） ====================

def test_generation_correctness():
    """生成层：基于检索到的资料，答案是否正确。"""
    c = _get_client()
    if c is None:
        pytest.skip("未配置真实 LLM——按项目底线跳过生成层测试，不伪造结果。")

    print("\n" + "=" * 64)
    print("🧠 RAG 评估 · ② 生成层")
    print("=" * 64)
    correct = 0
    for case in CASES:
        doc = retrieve(case.query)
        ans = generate(c, case.query, doc["text"])
        ok = case.gold_kw.lower() in ans.lower()
        correct += ok
        print(f"   [{'✓' if ok else '✗'}] {case.query} -> {ans[:50]}")
    rate = correct / len(CASES)
    print(f"\n答案正确率: {correct}/{len(CASES)} = {rate:.0%}")
    assert rate >= 0.8, f"答案正确率 {rate:.0%} < 80%，生成层未能基于资料正确作答。"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
