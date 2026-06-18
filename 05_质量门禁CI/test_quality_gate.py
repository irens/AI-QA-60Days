"""
05 · 质量门禁引擎的单元测试

这是确定性逻辑测试，不调模型、不需要 API Key，永远可跑。
验证门禁的核心契约：L1 必阻断、L2 告警但放行、干净指标放行、退出码正确。
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from quality_gate import evaluate  # noqa: E402


def test_clean_metrics_pass():
    """全部达标 → 放行，退出码 0，无任何命中。"""
    r = evaluate({
        "jailbreak_success_rate": 0.0,
        "hallucination_rate": 0.0,
        "faithfulness": 0.95,
        "p99_latency_s": 1.2,
    })
    assert r.passed is True
    assert r.exit_code == 0
    assert not r.blockers and not r.warnings


def test_l1_blocks_release():
    """L1 命中（幻觉率 3% > 1%）→ 必须阻断，退出码 1。"""
    r = evaluate({"hallucination_rate": 0.03})
    assert r.passed is False
    assert r.exit_code == 1
    assert any("幻觉" in b for b in r.blockers)


def test_jailbreak_is_l1_blocker():
    """越狱成功属 L1，必须阻断。"""
    r = evaluate({"jailbreak_success_rate": 0.1})
    assert r.passed is False
    assert r.blockers


def test_l2_warns_but_passes():
    """仅 L2 命中（忠实度 0.7 < 0.8）→ 告警但放行，退出码 0。"""
    r = evaluate({"faithfulness": 0.7})
    assert r.passed is True
    assert r.exit_code == 0
    assert r.warnings and not r.blockers


def test_l1_dominates_l2():
    """同时有 L1 和 L2 命中时，只要有 L1 就阻断。"""
    r = evaluate({"hallucination_rate": 0.05, "faithfulness": 0.6})
    assert r.passed is False
    assert r.blockers and r.warnings


def test_missing_metrics_are_skipped():
    """未提供的指标不应误判为踩线。"""
    r = evaluate({"faithfulness": 0.99})
    assert r.passed is True
    assert not r.blockers and not r.warnings and not r.infos


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-s"]))
