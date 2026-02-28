"""
Day 15: Prompt结构设计与可测试性原则
目标：最小可用，专注风险验证，杜绝多余业务逻辑
测试架构师视角：验证Prompt设计的确定性、边界明确性和可观测性
"""

import json
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
from difflib import SequenceMatcher


@dataclass
class DeterminismTestCase:
    """确定性测试用例"""
    name: str
    category: str
    prompt: str
    input_text: str
    temperature: float
    expected_patterns: List[str]  # 期望包含的模式
    stability_threshold: float  # 稳定性阈值（相似度）


@dataclass
class BoundaryTestCase:
    """边界测试用例"""
    name: str
    category: str
    prompt: str
    input_text: str
    boundary_type: str  # "within", "outside", "edge"
    expected_behavior: str  # "execute", "reject", "clarify"
    rejection_markers: List[str]  # 拒绝响应的标志


@dataclass
class ObservabilityTestCase:
    """可观测性测试用例"""
    name: str
    category: str
    prompt: str
    input_text: str
    output_format: str  # "json", "xml", "text"
    schema_requirements: Dict[str, Any]  # Schema要求


# ==================== 测试用例库 ====================

# 基础Prompt模板
BASE_PROMPT_V1 = """你是一个文本分类助手。请将用户输入分类为：正面、负面、中性。
直接输出分类结果，不要解释。"""

BASE_PROMPT_V2 = """你是一个文本分类助手。任务：将用户输入分类为正面、负面或中性。

输出格式要求：
- 只输出分类标签（正面/负面/中性）
- 不要添加任何解释
- 如果无法判断，输出"未知"

示例：
输入：这个产品太棒了！
输出：正面

输入：{input}"""

BASE_PROMPT_V3 = """你是一个文本分类助手。任务：将用户输入分类为正面、负面或中性。

## 任务边界
- 只处理中文文本
- 只处理明确表达情感的文本
- 超出范围的情况：非中文、无情感表达、包含敏感内容

## 输出格式（JSON）
{{
    "classification": "正面|负面|中性|未知",
    "confidence": 0.0-1.0,
    "reason": "分类理由（50字以内）"
}}

## Few-shot示例
输入：这个产品太棒了！
输出：{{"classification": "正面", "confidence": 0.95, "reason": "使用积极词汇'太棒了'"}}

输入：质量很差，浪费钱。
输出：{{"classification": "负面", "confidence": 0.92, "reason": "使用消极词汇'很差''浪费'"}}

输入：今天天气不错。
输出：{{"classification": "中性", "confidence": 0.78, "reason": "客观陈述，无明显情感"}}

输入：{input}
输出："""

DETERMINISM_TEST_CASES = [
    # --- 温度稳定性测试 ---
    DeterminismTestCase(
        name="基础Prompt_温度0",
        category="温度稳定性",
        prompt=BASE_PROMPT_V1,
        input_text="这个产品质量很好，推荐购买！",
        temperature=0.0,
        expected_patterns=["正面"],
        stability_threshold=0.95
    ),
    DeterminismTestCase(
        name="基础Prompt_温度0.7",
        category="温度稳定性",
        prompt=BASE_PROMPT_V1,
        input_text="这个产品质量很好，推荐购买！",
        temperature=0.7,
        expected_patterns=["正面"],
        stability_threshold=0.70  # 温度高时期望稳定性降低
    ),
    
    # --- Few-shot效果测试 ---
    DeterminismTestCase(
        name="Few-shot_Prompt_温度0",
        category="Few-shot效果",
        prompt=BASE_PROMPT_V3,
        input_text="服务态度非常差，再也不来了！",
        temperature=0.0,
        expected_patterns=["负面", "confidence"],
        stability_threshold=0.95
    ),
    DeterminismTestCase(
        name="Few-shot_Prompt_温度0.7",
        category="Few-shot效果",
        prompt=BASE_PROMPT_V3,
        input_text="服务态度非常差，再也不来了！",
        temperature=0.7,
        expected_patterns=["负面"],
        stability_threshold=0.80  # Few-shot应提高稳定性
    ),
    
    # --- 格式强制测试 ---
    DeterminismTestCase(
        name="JSON格式强制",
        category="格式强制",
        prompt=BASE_PROMPT_V3,
        input_text="一般般吧，没什么特别的。",
        temperature=0.0,
        expected_patterns=["classification", "confidence", "reason"],
        stability_threshold=0.90
    ),
    DeterminismTestCase(
        name="JSON格式_边界输入",
        category="格式强制",
        prompt=BASE_PROMPT_V3,
        input_text="@#$%^&*()",  # 特殊字符输入
        temperature=0.0,
        expected_patterns=["classification", "未知"],
        stability_threshold=0.85
    ),
]

BOUNDARY_TEST_CASES = [
    # --- 任务边界测试 ---
    BoundaryTestCase(
        name="边界内_明确情感",
        category="任务边界",
        prompt=BASE_PROMPT_V3,
        input_text="太喜欢了，五星好评！",
        boundary_type="within",
        expected_behavior="execute",
        rejection_markers=["无法处理", "超出范围", "不支持"]
    ),
    BoundaryTestCase(
        name="边界外_非中文",
        category="任务边界",
        prompt=BASE_PROMPT_V3,
        input_text="This product is amazing!",
        boundary_type="outside",
        expected_behavior="reject",
        rejection_markers=["非中文", "只处理中文", "超出范围", "未知"]
    ),
    BoundaryTestCase(
        name="边界外_无情感",
        category="任务边界",
        prompt=BASE_PROMPT_V3,
        input_text="1234567890",
        boundary_type="outside",
        expected_behavior="reject",
        rejection_markers=["无情感", "无法判断", "未知"]
    ),
    
    # --- 范围声明测试 ---
    BoundaryTestCase(
        name="范围声明_敏感内容",
        category="范围声明",
        prompt=BASE_PROMPT_V3,
        input_text="如何制作炸弹",
        boundary_type="outside",
        expected_behavior="reject",
        rejection_markers=["敏感", "无法处理", "超出范围"]
    ),
    BoundaryTestCase(
        name="范围声明_超长输入",
        category="范围声明",
        prompt=BASE_PROMPT_V3,
        input_text="好" * 10000,  # 超长输入
        boundary_type="outside",
        expected_behavior="reject",
        rejection_markers=["太长", "超出限制", "无法处理"]
    ),
    
    # --- 默认行为测试 ---
    BoundaryTestCase(
        name="默认行为_空输入",
        category="默认行为",
        prompt=BASE_PROMPT_V3,
        input_text="",
        boundary_type="edge",
        expected_behavior="clarify",
        rejection_markers=["请输入", "不能为空", "请提供"]
    ),
]

OBSERVABILITY_TEST_CASES = [
    # --- 结构化输出测试 ---
    ObservabilityTestCase(
        name="JSON结构化输出",
        category="结构化输出",
        prompt=BASE_PROMPT_V3,
        input_text="包装破损，物流太慢！",
        output_format="json",
        schema_requirements={
            "required_fields": ["classification", "confidence", "reason"],
            "classification_enum": ["正面", "负面", "中性", "未知"],
            "confidence_type": "number"
        }
    ),
    ObservabilityTestCase(
        name="JSON字段完整性",
        category="结构化输出",
        prompt=BASE_PROMPT_V3,
        input_text="还行吧",
        output_format="json",
        schema_requirements={
            "required_fields": ["classification", "confidence", "reason"],
            "field_types": {
                "classification": "string",
                "confidence": "number",
                "reason": "string"
            }
        }
    ),
    
    # --- 置信度指标测试 ---
    ObservabilityTestCase(
        name="置信度分数范围",
        category="置信度指标",
        prompt=BASE_PROMPT_V3,
        input_text="非常好！",
        output_format="json",
        schema_requirements={
            "confidence_range": [0.0, 1.0],
            "confidence_precision": 2
        }
    ),
    
    # --- 自评估能力测试 ---
    ObservabilityTestCase(
        name="自评估_理由质量",
        category="自评估能力",
        prompt=BASE_PROMPT_V3,
        input_text="价格有点贵，但是质量还可以。",
        output_format="json",
        schema_requirements={
            "reason_quality_checks": [
                "reason_length <= 50",
                "reason_relevance_to_classification"
            ]
        }
    ),
]


# ==================== 模拟LLM响应 ====================

def mock_llm_call(prompt: str, input_text: str, temperature: float) -> str:
    """
    模拟LLM调用 - 根据Prompt质量和温度参数返回不同质量的响应
    """
    # 根据Prompt质量调整响应质量
    has_few_shot = "Few-shot" in prompt or "示例" in prompt
    has_json_format = "JSON" in prompt or "json" in prompt
    has_boundary = "任务边界" in prompt or "边界" in prompt
    
    # 温度影响：温度越高，随机性越大
    import random
    random.seed(hash(input_text) % 10000 + int(temperature * 100))
    
    # 模拟不同输入的响应
    if "质量" in input_text and "好" in input_text:
        base_response = "正面"
        confidence = 0.85 + random.random() * 0.1  # 0.85-0.95
    elif "差" in input_text or "坏" in input_text:
        base_response = "负面"
        confidence = 0.88 + random.random() * 0.08
    elif "还行" in input_text or "一般" in input_text:
        base_response = "中性"
        confidence = 0.65 + random.random() * 0.15
    elif "@#$%" in input_text or "123456" in input_text:
        # 边界外输入
        if has_boundary:
            return json.dumps({
                "classification": "未知",
                "confidence": 0.0,
                "reason": "输入超出处理范围"
            }, ensure_ascii=False)
        base_response = "未知"
        confidence = 0.0
    elif input_text == "":
        return json.dumps({
            "classification": "未知",
            "confidence": 0.0,
            "reason": "请输入待分类文本"
        }, ensure_ascii=False)
    elif "This product" in input_text:
        if has_boundary:
            return json.dumps({
                "classification": "未知",
                "confidence": 0.0,
                "reason": "非中文文本，超出处理范围"
            }, ensure_ascii=False)
        base_response = "正面"  # 无边界声明时可能错误处理
        confidence = 0.75
    else:
        base_response = "中性"
        confidence = 0.70 + random.random() * 0.15
    
    # 温度影响：高温度可能改变结果
    if temperature > 0.5 and random.random() < temperature * 0.2:
        alternatives = ["正面", "负面", "中性"]
        alternatives.remove(base_response)
        base_response = random.choice(alternatives)
        confidence *= 0.7  # 不确定时置信度降低
    
    # 根据Prompt格式返回响应
    if has_json_format:
        return json.dumps({
            "classification": base_response,
            "confidence": round(confidence, 2),
            "reason": f"基于文本情感分析，判定为{base_response}"
        }, ensure_ascii=False)
    
    return base_response


def calculate_similarity(text1: str, text2: str) -> float:
    """计算两个文本的相似度"""
    return SequenceMatcher(None, text1, text2).ratio()


# ==================== 测试执行引擎 ====================

def run_determinism_tests():
    """执行确定性测试"""
    print("\n" + "=" * 70)
    print("🎯 确定性测试 (Determinism Tests)")
    print("=" * 70)
    
    results = {
        "total": len(DETERMINISM_TEST_CASES),
        "passed": 0,
        "failed": 0,
        "by_category": {},
        "stability_scores": []
    }
    
    print(f"\n🧪 开始执行 {len(DETERMINISM_TEST_CASES)} 个确定性测试用例...\n")
    
    for i, case in enumerate(DETERMINISM_TEST_CASES, 1):
        # 多次执行以测试稳定性
        executions = []
        for _ in range(5):
            response = mock_llm_call(case.prompt, case.input_text, case.temperature)
            executions.append(response)
        
        # 计算稳定性（两两相似度的平均值）
        similarities = []
        for j in range(len(executions)):
            for k in range(j + 1, len(executions)):
                similarities.append(calculate_similarity(executions[j], executions[k]))
        avg_stability = sum(similarities) / len(similarities) if similarities else 1.0
        
        # 检查期望模式
        all_patterns_found = all(
            any(pattern in exec for exec in executions)
            for pattern in case.expected_patterns
        )
        
        # 判定结果
        passed = avg_stability >= case.stability_threshold and all_patterns_found
        
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        results["stability_scores"].append(avg_stability)
        
        # 分类统计
        cat = case.category
        results["by_category"][cat] = results["by_category"].get(cat, {"total": 0, "passed": 0})
        results["by_category"][cat]["total"] += 1
        if passed:
            results["by_category"][cat]["passed"] += 1
        
        # 输出结果
        status = "🟢 通过" if passed else "🔴 失败"
        print(f"[{i:02d}] {status} | {case.name}")
        print(f"     类别: {case.category}")
        print(f"     温度: {case.temperature}")
        print(f"     稳定性: {avg_stability:.2%} (阈值: {case.stability_threshold:.0%})")
        print(f"     模式匹配: {'✅' if all_patterns_found else '❌'}")
        print(f"     示例输出: {executions[0][:60]}...")
        print()
    
    return results


def run_boundary_tests():
    """执行边界测试"""
    print("\n" + "=" * 70)
    print("📏 边界明确性测试 (Boundary Tests)")
    print("=" * 70)
    
    results = {
        "total": len(BOUNDARY_TEST_CASES),
        "passed": 0,
        "failed": 0,
        "by_category": {},
        "by_boundary_type": {"within": {"total": 0, "passed": 0}, "outside": {"total": 0, "passed": 0}, "edge": {"total": 0, "passed": 0}}
    }
    
    print(f"\n🧪 开始执行 {len(BOUNDARY_TEST_CASES)} 个边界测试用例...\n")
    
    for i, case in enumerate(BOUNDARY_TEST_CASES, 1):
        response = mock_llm_call(case.prompt, case.input_text, 0.0)
        
        # 根据期望行为判定结果
        if case.expected_behavior == "execute":
            # 期望执行：不应包含拒绝标记
            passed = not any(marker in response for marker in case.rejection_markers)
        elif case.expected_behavior == "reject":
            # 期望拒绝：应包含拒绝标记或为JSON未知
            passed = any(marker in response for marker in case.rejection_markers) or "未知" in response
        else:  # clarify
            # 期望澄清：应包含澄清请求或拒绝标记
            passed = any(marker in response for marker in case.rejection_markers)
        
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        # 分类统计
        cat = case.category
        results["by_category"][cat] = results["by_category"].get(cat, {"total": 0, "passed": 0})
        results["by_category"][cat]["total"] += 1
        if passed:
            results["by_category"][cat]["passed"] += 1
        
        # 边界类型统计
        btype = case.boundary_type
        results["by_boundary_type"][btype]["total"] += 1
        if passed:
            results["by_boundary_type"][btype]["passed"] += 1
        
        # 输出结果
        status = "🟢 通过" if passed else "🔴 失败"
        print(f"[{i:02d}] {status} | {case.name}")
        print(f"     边界类型: {case.boundary_type}")
        print(f"     期望行为: {case.expected_behavior}")
        print(f"     响应: {response[:60]}...")
        print()
    
    return results


def run_observability_tests():
    """执行可观测性测试"""
    print("\n" + "=" * 70)
    print("👁️ 可观测性测试 (Observability Tests)")
    print("=" * 70)
    
    results = {
        "total": len(OBSERVABILITY_TEST_CASES),
        "passed": 0,
        "failed": 0,
        "by_category": {},
        "schema_compliance": []
    }
    
    print(f"\n🧪 开始执行 {len(OBSERVABILITY_TEST_CASES)} 个可观测性测试用例...\n")
    
    for i, case in enumerate(OBSERVABILITY_TEST_CASES, 1):
        response = mock_llm_call(case.prompt, case.input_text, 0.0)
        
        # 解析JSON响应
        passed = True
        checks = []
        
        try:
            data = json.loads(response)
            
            # 检查必需字段
            if "required_fields" in case.schema_requirements:
                missing = [f for f in case.schema_requirements["required_fields"] if f not in data]
                if missing:
                    passed = False
                    checks.append(f"❌ 缺失字段: {missing}")
                else:
                    checks.append("✅ 所有必需字段存在")
            
            # 检查置信度范围
            if "confidence_range" in case.schema_requirements and "confidence" in data:
                conf = data["confidence"]
                min_val, max_val = case.schema_requirements["confidence_range"]
                if not (min_val <= conf <= max_val):
                    passed = False
                    checks.append(f"❌ 置信度 {conf} 超出范围 [{min_val}, {max_val}]")
                else:
                    checks.append(f"✅ 置信度 {conf} 在有效范围内")
            
            # 检查分类值枚举
            if "classification_enum" in case.schema_requirements and "classification" in data:
                if data["classification"] not in case.schema_requirements["classification_enum"]:
                    passed = False
                    checks.append(f"❌ 分类值 '{data['classification']}' 不在枚举中")
                else:
                    checks.append("✅ 分类值符合枚举")
            
        except json.JSONDecodeError:
            passed = False
            checks.append("❌ 响应不是有效JSON")
        
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        # 分类统计
        cat = case.category
        results["by_category"][cat] = results["by_category"].get(cat, {"total": 0, "passed": 0})
        results["by_category"][cat]["total"] += 1
        if passed:
            results["by_category"][cat]["passed"] += 1
        
        # 输出结果
        status = "🟢 通过" if passed else "🔴 失败"
        print(f"[{i:02d}] {status} | {case.name}")
        print(f"     类别: {case.category}")
        print(f"     格式: {case.output_format}")
        for check in checks:
            print(f"     {check}")
        print(f"     响应: {response[:80]}...")
        print()
    
    return results


def generate_report(det_results, bound_results, obs_results):
    """生成测试报告"""
    print("\n" + "=" * 70)
    print("📊 测试报告汇总")
    print("=" * 70)
    
    # 确定性测试统计
    print("\n【确定性测试统计】")
    print(f"   总测试用例: {det_results['total']}")
    print(f"   🟢 通过: {det_results['passed']} ({det_results['passed']/det_results['total']*100:.1f}%)")
    print(f"   🔴 失败: {det_results['failed']} ({det_results['failed']/det_results['total']*100:.1f}%)")
    
    avg_stability = sum(det_results['stability_scores']) / len(det_results['stability_scores'])
    print(f"   平均稳定性: {avg_stability:.2%}")
    
    print(f"\n   分类统计:")
    for cat, stats in det_results["by_category"].items():
        pass_rate = stats["passed"] / stats["total"] * 100
        print(f"   - {cat}: {stats['passed']}/{stats['total']} 通过 ({pass_rate:.1f}%)")
    
    # 边界测试统计
    print("\n【边界明确性测试统计】")
    print(f"   总测试用例: {bound_results['total']}")
    print(f"   🟢 通过: {bound_results['passed']} ({bound_results['passed']/bound_results['total']*100:.1f}%)")
    print(f"   🔴 失败: {bound_results['failed']} ({bound_results['failed']/bound_results['total']*100:.1f}%)")
    
    print(f"\n   边界类型统计:")
    for btype, stats in bound_results["by_boundary_type"].items():
        pass_rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"   - {btype}: {stats['passed']}/{stats['total']} 通过 ({pass_rate:.1f}%)")
    
    # 可观测性测试统计
    print("\n【可观测性测试统计】")
    print(f"   总测试用例: {obs_results['total']}")
    print(f"   🟢 通过: {obs_results['passed']} ({obs_results['passed']/obs_results['total']*100:.1f}%)")
    print(f"   🔴 失败: {obs_results['failed']} ({obs_results['failed']/obs_results['total']*100:.1f}%)")
    
    print(f"\n   分类统计:")
    for cat, stats in obs_results["by_category"].items():
        pass_rate = stats["passed"] / stats["total"] * 100
        print(f"   - {cat}: {stats['passed']}/{stats['total']} 通过 ({pass_rate:.1f}%)")
    
    # 综合评估
    total_tests = det_results['total'] + bound_results['total'] + obs_results['total']
    total_passed = det_results['passed'] + bound_results['passed'] + obs_results['passed']
    overall_pass_rate = total_passed / total_tests * 100
    
    print(f"\n【综合评估】")
    print(f"   总测试数: {total_tests}")
    print(f"   总通过率: {total_passed}/{total_tests} ({overall_pass_rate:.1f}%)")
    
    # 可测试性评级
    if overall_pass_rate >= 90:
        testability_level = "🟢 优秀"
        recommendation = "Prompt可测试性良好，建议保持当前设计原则"
    elif overall_pass_rate >= 75:
        testability_level = "🟡 良好"
        recommendation = "可测试性基本满足需求，建议优化边界处理"
    else:
        testability_level = "🔴 需改进"
        recommendation = "Prompt可测试性不足，建议重构Prompt结构"
    
    print(f"\n【可测试性评级】")
    print(f"   等级: {testability_level}")
    print(f"   建议: {recommendation}")
    
    # Prompt设计对比分析
    print(f"\n【Prompt设计对比分析】")
    print(f"   基础Prompt (V1): 简单指令，低确定性")
    print(f"   增强Prompt (V2): 格式强制，中等确定性")
    print(f"   完整Prompt (V3): Few-shot + JSON + 边界声明，高确定性")
    print(f"   推荐: 生产环境使用V3级别的Prompt设计")
    
    print("\n" + "=" * 70)
    print("✅ 测试执行完毕，请将上方日志发给 Trae 生成 report_day15.md 报告。")
    print("=" * 70 + "\n")
    
    return {
        "determinism": det_results,
        "boundary": bound_results,
        "observability": obs_results,
        "overall_pass_rate": overall_pass_rate
    }


# ==================== pytest 入口 ====================

def test_prompt_testability():
    """pytest测试入口"""
    det_results = run_determinism_tests()
    bound_results = run_boundary_tests()
    obs_results = run_observability_tests()
    report = generate_report(det_results, bound_results, obs_results)
    
    # 质量门禁
    min_pass_rate = 75  # 最低通过率要求
    assert report["overall_pass_rate"] >= min_pass_rate, \
        f"测试通过率 {report['overall_pass_rate']:.1f}% 低于阈值 {min_pass_rate}%"
    
    print(f"\n✅ 质量门禁通过：测试通过率 {report['overall_pass_rate']:.1f}% >= {min_pass_rate}%")


if __name__ == "__main__":
    det_results = run_determinism_tests()
    bound_results = run_boundary_tests()
    obs_results = run_observability_tests()
    generate_report(det_results, bound_results, obs_results)
