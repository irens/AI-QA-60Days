"""
Day 47 补充：Mapping 驱动计分方法测试
目标：验证 mapping 驱动计分的正确性，对比传统 LLM 直接计数方法
来源：gjz_agent_python 项目工程化实践
难度级别：进阶 - 深入理解评估计分的一致性保证
"""

from typing import List, Dict, Any, Set


# ──────────────────────────────────────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    """归一化字符串，去除多余空格和标点差异"""
    return s.strip().replace("，", ",").replace("。", ".").lower()


def _unique_list(items: List[str]) -> List[str]:
    """去重但保持顺序"""
    seen = set()
    result = []
    for item in items:
        key = _normalize(item)
        if key not in seen and item.strip():
            seen.add(key)
            result.append(item.strip())
    return result


def _find_expected_match(
    exp: str, expected_clean: List[str], already_used: Set[str]
) -> str | None:
    """在 expected_clean 中查找匹配项，排除已使用的"""
    exp_key = _normalize(exp)
    for e in expected_clean:
        if _normalize(e) in already_used:
            continue
        if exp_key == _normalize(e) or exp_key in _normalize(e) or _normalize(e) in exp_key:
            return e
    return None


# ──────────────────────────────────────────────────────────────────────────────
# 核心函数：Mapping 驱动计分
# ──────────────────────────────────────────────────────────────────────────────

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

    # 预扫描：标记有 actual=[] 的 expected（表示部分覆盖）
    expected_has_empty_actual: Dict[str, bool] = {}
    for m in mappings:
        exp = m.get("expected", "").strip()
        if not exp:
            continue
        actual_items = m.get("actual", [])
        has_actual = any(str(a).strip() for a in actual_items)
        if not has_actual:
            exp_key = _normalize(exp)
            expected_has_empty_actual[exp_key] = True
            for e in expected_clean:
                if exp_key in _normalize(e) or _normalize(e) in exp_key:
                    expected_has_empty_actual[_normalize(e)] = True

    for m in mappings:
        exp = m.get("expected", "").strip()
        if not exp:
            continue
        actual_items = m.get("actual", [])
        has_actual = any(str(a).strip() for a in actual_items)

        if not has_actual:
            continue

        matched_exp = _find_expected_match(exp, expected_clean, set(_normalize(t) for t in tp_list))
        if matched_exp:
            matched_key = _normalize(matched_exp)
            if matched_key not in expected_has_empty_actual:
                tp_list.append(matched_exp)
        else:
            exp_key = _normalize(exp)
            if exp_key in {_normalize(e) for e in expected_clean} and \
               exp_key not in {_normalize(t) for t in tp_list}:
                if exp_key not in expected_has_empty_actual:
                    tp_list.append(exp)

        for act in actual_items:
            act = str(act).strip()
            if not act:
                continue
            act_key = _normalize(act)
            if act_key not in consumed_actual_keys:
                consumed_actual.append(act)
                consumed_actual_keys.add(act_key)

    # fn_list = expected 中未被覆盖的
    tp_keys = {_normalize(t) for t in tp_list}
    fn_list = [e for e in expected_clean if _normalize(e) not in tp_keys]

    # fp_list = unmatched_actual（清洗后）
    fp_list = _unique_list(unmatched_actual)
    fp_keys = {_normalize(f) for f in fp_list}
    overlap = consumed_actual_keys & fp_keys
    if overlap:
        fp_list = [f for f in fp_list if _normalize(f) not in consumed_actual_keys]

    # 校验：tp_list + fn_list = expected
    covered_keys = {_normalize(t) for t in tp_list}
    uncovered_keys = {_normalize(f) for f in fn_list}
    all_expected_keys = {_normalize(e) for e in expected_clean}
    missing = all_expected_keys - covered_keys - uncovered_keys
    if missing:
        for e in expected_clean:
            if _normalize(e) in missing and _normalize(e) not in uncovered_keys:
                fn_list.append(e)

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


# ──────────────────────────────────────────────────────────────────────────────
# 传统方法：LLM 直接输出 tp/fp/fn（模拟，用于对比）
# ──────────────────────────────────────────────────────────────────────────────

def compute_metrics_traditional(
    expected: List[str],
    actual: List[str],
    llm_tp_list: List[str],
    llm_fp_list: List[str],
    llm_fn_list: List[str],
) -> Dict[str, Any]:
    """
    传统方法：LLM 直接输出 tp/fp/fn，代码直接计算 P/R/F1。
    模拟 LLM 可能出现的计数不一致问题。
    """
    expected_clean = _unique_list(expected)
    actual_clean = _unique_list(actual)

    tp = len(llm_tp_list)
    fp = len(llm_fp_list)
    fn = len(llm_fn_list)

    # 检查：LLM 输出的 tp+fn 是否等于 expected 总数
    count_consistent = (tp + fn) == len(expected_clean)

    if not actual_clean:
        if len(expected_clean) == 0:
            return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "count_consistent": True}
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "count_consistent": count_consistent}

    recall = tp / len(expected_clean) if expected_clean else 1.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "count_consistent": count_consistent,
        "tp_list": llm_tp_list,
        "fp_list": llm_fp_list,
        "fn_list": llm_fn_list,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 黄金测试用例（G1-G9）
# ──────────────────────────────────────────────────────────────────────────────

def test_G1_full_match_all_expected_covered():
    """
    G1: FEI_GM_01 — 17个专家标签全部被覆盖，Agent有4个额外输出（FP）
    验证：recall=1.0, precision≥0.70, 正确匹配的actual不在fp中
    """
    expected = [
        "新病无汗", "痰多质稀", "鼻塞流清涕", "新近感受风寒",
        "身痛", "咳嗽", "恶寒", "发热", "头痛",
        "舌苔薄白", "脉浮紧", "口不渴", "喷嚏", "肢节酸痛",
        "鼻痒", "咽痒", "咳嗽声重",
    ]
    actual = [
        "无汗", "痰多", "痰质稀", "鼻塞", "流清涕",
        "新近感受风寒", "身痛", "咳嗽", "恶寒", "发热", "头痛",
        "舌苔薄白", "脉浮紧", "口淡", "渴不欲饮",
        "喷嚏", "肢节酸痛", "鼻痒", "咽痒", "腹泻",
        "纳呆", "失眠", "尿多", "咳嗽声重",
    ]
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
        expected, actual, mappings, unmatched_actual, unmatched_expected
    )

    assert result["recall"] == 1.0, f"Expected recall=1.0, got {result['recall']}"
    assert result["precision"] >= 0.70, f"Expected precision≥0.70, got {result['precision']}"
    fp_set = set(result["fp_list"])
    assert "无汗" not in fp_set, "无汗 should not be in fp_list"
    assert "痰多" not in fp_set, "痰多 should not be in fp_list"
    assert "流清涕" not in fp_set, "流清涕 should not be in fp_list"
    consumed_set = set(result["consumed_actual"])
    assert consumed_set & fp_set == set(), "consumed_actual ∩ fp_list should be empty"
    print(f"G1 PASS: recall={result['recall']}, precision={result['precision']}, f1={result['f1']}")


def test_G2_agent_split_composite_expected():
    """
    G2: Agent 将复合症状"痰多质稀"拆成"痰多"+"痰质稀"
    验证：拆分后仍正确匹配，fp/fn 计数正确
    """
    expected = ["痰多质稀", "恶寒"]
    actual = ["痰多", "痰质稀", "恶寒", "咳嗽"]
    mappings = [
        {"expected": "痰多质稀", "actual": ["痰多", "痰质稀"]},
        {"expected": "恶寒", "actual": ["恶寒"]},
    ]
    unmatched_actual = ["咳嗽"]
    unmatched_expected = []

    result = compute_metrics_from_mappings(
        expected, actual, mappings, unmatched_actual, unmatched_expected
    )

    assert result["recall"] == 1.0, f"Expected recall=1.0, got {result['recall']}"
    assert result["precision"] == 3/4, f"Expected precision=0.75, got {result['precision']}"
    expected_f1 = 2 * 1.0 * 0.75 / (1.0 + 0.75)
    assert abs(result["f1"] - expected_f1) < 0.01, f"Expected f1≈{expected_f1}, got {result['f1']}"
    print(f"G2 PASS: recall={result['recall']}, precision={result['precision']}, f1={result['f1']}")


def test_G3_expected_not_covered():
    """
    G3: 有专家标签未被 Agent 覆盖
    验证：recall < 1.0, fn_list 包含未覆盖的标签
    """
    expected = ["恶寒", "发热", "头痛", "咳嗽"]
    actual = ["恶寒", "发热"]
    mappings = [
        {"expected": "恶寒", "actual": ["恶寒"]},
        {"expected": "发热", "actual": ["发热"]},
    ]
    unmatched_actual = []
    unmatched_expected = ["头痛", "咳嗽"]

    result = compute_metrics_from_mappings(
        expected, actual, mappings, unmatched_actual, unmatched_expected
    )

    assert result["recall"] == 0.5, f"Expected recall=0.5, got {result['recall']}"
    assert result["precision"] == 1.0, f"Expected precision=1.0, got {result['precision']}"
    assert set(result["fn_list"]) == {"头痛", "咳嗽"}
    print(f"G3 PASS: recall={result['recall']}, precision={result['precision']}, f1={result['f1']}")


def test_G4_empty_actual():
    """G4: Agent 输出为空，所有 expected 都不是 TP"""
    expected = ["恶寒", "发热"]
    actual = []
    mappings = []
    unmatched_actual = []
    unmatched_expected = ["恶寒", "发热"]

    result = compute_metrics_from_mappings(
        expected, actual, mappings, unmatched_actual, unmatched_expected
    )

    assert result["recall"] == 0.0
    assert result["precision"] == 0.0
    assert result["f1"] == 0.0
    print(f"G4 PASS: recall={result['recall']}, precision={result['precision']}, f1={result['f1']}")


def test_G5_empty_expected():
    """G5: 专家标签为空"""
    expected = []
    actual = ["恶寒", "发热"]
    mappings = []
    unmatched_actual = ["恶寒", "发热"]
    unmatched_expected = []

    result = compute_metrics_from_mappings(
        expected, actual, mappings, unmatched_actual, unmatched_expected
    )

    assert result["recall"] == 1.0
    assert result["precision"] == 1.0
    assert result["f1"] == 1.0
    print(f"G5 PASS: recall={result['recall']}, precision={result['precision']}, f1={result['f1']}")


def test_G6_both_empty():
    """G6: 专家标签和 Agent 输出都为空"""
    expected = []
    actual = []
    mappings = []
    unmatched_actual = []
    unmatched_expected = []

    result = compute_metrics_from_mappings(
        expected, actual, mappings, unmatched_actual, unmatched_expected
    )

    assert result["recall"] == 1.0
    assert result["precision"] == 1.0
    assert result["f1"] == 1.0
    print(f"G6 PASS: f1={result['f1']}")


def test_G7_complex_real_case():
    """
    G7: 真实场景——FEI_KS_03（咳嗽，6个专家标签，Agent 输出5个，2个FP）
    """
    expected = ["干咳", "咽干", "痰少而黏", "声音嘶哑", "舌质红", "脉细数"]
    actual = ["干咳", "咽干", "痰少", "痰黏", "声音嘶哑", "舌质红", "脉细数", "口渴", "乏力"]
    mappings = [
        {"expected": "干咳", "actual": ["干咳"]},
        {"expected": "咽干", "actual": ["咽干"]},
        {"expected": "痰少而黏", "actual": ["痰少", "痰黏"]},
        {"expected": "声音嘶哑", "actual": ["声音嘶哑"]},
        {"expected": "舌质红", "actual": ["舌质红"]},
        {"expected": "脉细数", "actual": ["脉细数"]},
    ]
    unmatched_actual = ["口渴", "乏力"]
    unmatched_expected = []

    result = compute_metrics_from_mappings(
        expected, actual, mappings, unmatched_actual, unmatched_expected
    )

    assert result["recall"] == 1.0
    # consumed = 8 (干咳+咽干+痰少+痰黏+声音嘶哑+舌质红+脉细数...)
    # fp = 2 (口渴+乏力)
    # precision = 7/(7+2) ≈ 0.7778
    assert result["precision"] >= 0.70
    assert result["f1"] >= 0.80
    print(f"G7 PASS: recall={result['recall']}, precision={result['precision']}, f1={result['f1']}")


def test_G8_traditional_vs_mapping_consistency():
    """
    G8: 对比测试——传统方法 vs Mapping 方法
    模拟 LLM 直接计数可能出现的不一致
    """
    expected = ["恶寒", "发热", "头痛", "咳嗽"]
    actual = ["恶寒", "发热", "咳嗽", "咽痛"]

    # --- Mapping 方法 ---
    mappings = [
        {"expected": "恶寒", "actual": ["恶寒"]},
        {"expected": "发热", "actual": ["发热"]},
        {"expected": "咳嗽", "actual": ["咳嗽"]},
    ]
    unmatched_actual = ["咽痛"]
    unmatched_expected = ["头痛"]

    map_result = compute_metrics_from_mappings(
        expected, actual, mappings, unmatched_actual, unmatched_expected
    )

    # --- 传统方法（模拟 LLM 不一致） ---
    # 场景A：LLM 正确计数
    trad_result_a = compute_metrics_traditional(
        expected, actual,
        llm_tp_list=["恶寒", "发热", "咳嗽"],
        llm_fp_list=["咽痛"],
        llm_fn_list=["头痛"],
    )
    assert trad_result_a["count_consistent"] == True

    # 场景B：LLM 将"头痛"同时放入 tp 和 fn（常见错误）
    trad_result_b = compute_metrics_traditional(
        expected, actual,
        llm_tp_list=["恶寒", "发热", "咳嗽", "头痛"],  # 把 fn 也放进了 tp
        llm_fp_list=["咽痛"],
        llm_fn_list=["头痛"],  # 同时出现在 fn 中
    )
    assert trad_result_b["count_consistent"] == False, "传统方法应检测到不一致"
    # 传统方法因为 tp+fn=5≠expected=4，count_consistent=False
    # 但 Mapping 方法天然保证一致性

    # 验证 Mapping 方法结果与传统方法一致（场景A）
    assert map_result["recall"] == trad_result_a["recall"]
    assert map_result["precision"] == trad_result_a["precision"]
    print(f"G8 PASS: mapping_f1={map_result['f1']}, traditional_consistent={trad_result_a['count_consistent']}, traditional_bug={trad_result_b['count_consistent']}")


def test_G9_mapping_tp_fn_mutually_exclusive():
    """
    G9: 验证 tp_list 和 fn_list 互斥
    LLM 常见错误：同一症状同时出现在 tp 和 fn 中
    Mapping 方法通过代码保证互斥
    """
    expected = ["恶寒", "发热", "头痛"]
    actual = ["恶寒", "发热"]
    mappings = [
        {"expected": "恶寒", "actual": ["恶寒"]},
        {"expected": "发热", "actual": ["发热"]},
    ]
    unmatched_actual = []
    unmatched_expected = ["头痛"]

    result = compute_metrics_from_mappings(
        expected, actual, mappings, unmatched_actual, unmatched_expected
    )

    tp_set = set(result["tp_list"])
    fn_set = set(result["fn_list"])
    assert tp_set & fn_set == set(), f"tp_list ∩ fn_list should be empty, got {tp_set & fn_set}"
    assert len(tp_set) + len(fn_set) == len(set(expected)), \
        f"tp+fn should equal expected count, got {len(tp_set)}+{len(fn_set)}≠{len(set(expected))}"
    print(f"G9 PASS: tp={tp_set}, fn={fn_set}, mutually_exclusive=True")


# ──────────────────────────────────────────────────────────────────────────────
# 运行所有测试
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest as _pytest_module
    test_functions = [
        test_G1_full_match_all_expected_covered,
        test_G2_agent_split_composite_expected,
        test_G3_expected_not_covered,
        test_G4_empty_actual,
        test_G5_empty_expected,
        test_G6_both_empty,
        test_G7_complex_real_case,
        test_G8_traditional_vs_mapping_consistency,
        test_G9_mapping_tp_fn_mutually_exclusive,
    ]
    passed = 0
    for test_fn in test_functions:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test_fn.__name__} — {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed}/{len(test_functions)} tests passed")
    print(f"{'='*50}")