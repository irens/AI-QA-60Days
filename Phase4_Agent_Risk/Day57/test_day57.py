"""
Day 57: Chain-of-Thought记录完整性测试
目标：验证Agent推理过程的CoT记录是否完整可追溯
测试架构师视角：CoT缺失 = 黑箱故障无法排查
难度级别：基础
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class CoTStep:
    """单个CoT推理步骤"""
    step_number: int
    step_type: str  # observation, thought, action, conclusion
    content: str
    timestamp: Optional[str] = None
    context_refs: List[str] = field(default_factory=list)
    token_usage: Optional[int] = None


@dataclass
class CoTRecord:
    """完整CoT记录"""
    request_id: str
    timestamp_start: str
    model_version: str
    timestamp_end: Optional[str] = None
    steps: List[CoTStep] = field(default_factory=list)
    total_token_usage: Optional[int] = None


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float  # 0-100
    risk_level: str  # L1/L2/L3
    details: Dict[str, Any] = field(default_factory=dict)


def generate_complete_cot() -> CoTRecord:
    """生成完整的CoT记录（作为基准）"""
    return CoTRecord(
        request_id="req_001_complete",
        timestamp_start="2024-01-15T10:00:00Z",
        timestamp_end="2024-01-15T10:00:05Z",
        model_version="gpt-4-turbo",
        total_token_usage=450,
        steps=[
            CoTStep(
                step_number=1,
                step_type="observation",
                content="用户询问北京今天的天气",
                timestamp="2024-01-15T10:00:01Z",
                context_refs=["user_input_001"],
                token_usage=50
            ),
            CoTStep(
                step_number=2,
                step_type="thought",
                content="需要调用天气查询工具获取实时数据",
                timestamp="2024-01-15T10:00:02Z",
                context_refs=[],
                token_usage=80
            ),
            CoTStep(
                step_number=3,
                step_type="action",
                content="调用get_weather_tool(location='北京')",
                timestamp="2024-01-15T10:00:03Z",
                context_refs=["tool_call_001"],
                token_usage=120
            ),
            CoTStep(
                step_number=4,
                step_type="conclusion",
                content="北京今天晴天，气温15-22度",
                timestamp="2024-01-15T10:00:04Z",
                context_refs=["tool_result_001"],
                token_usage=200
            )
        ]
    )


def generate_missing_step_cot() -> CoTRecord:
    """生成缺少步骤的CoT记录"""
    cot = generate_complete_cot()
    cot.request_id = "req_002_missing_step"
    # 删除step 2，造成步骤不连续
    cot.steps = [s for s in cot.steps if s.step_number != 2]
    return cot


def generate_empty_thought_cot() -> CoTRecord:
    """生成思考内容为空的CoT记录"""
    cot = generate_complete_cot()
    cot.request_id = "req_003_empty_thought"
    cot.steps[1].content = ""  # 第二步thought为空
    return cot


def generate_missing_context_ref_cot() -> CoTRecord:
    """生成缺少上下文引用的CoT记录"""
    cot = generate_complete_cot()
    cot.request_id = "req_004_missing_ref"
    cot.steps[2].context_refs = []  # action步骤无工具引用
    return cot


def generate_missing_timestamp_cot() -> CoTRecord:
    """生成缺少时间戳的CoT记录"""
    cot = generate_complete_cot()
    cot.request_id = "req_005_missing_ts"
    cot.timestamp_end = None
    cot.steps[0].timestamp = None
    return cot


def generate_missing_metadata_cot() -> CoTRecord:
    """生成缺少元数据的CoT记录"""
    cot = generate_complete_cot()
    cot.request_id = "req_006_missing_meta"
    cot.model_version = ""
    cot.total_token_usage = None
    return cot


def validate_cot_completeness(cot: CoTRecord) -> Dict[str, Any]:
    """
    验证CoT记录完整性
    返回详细的验证结果
    """
    issues = []
    warnings = []
    
    # 1. 检查步骤连续性
    step_numbers = [s.step_number for s in cot.steps]
    expected_steps = list(range(1, len(cot.steps) + 1))
    if step_numbers != expected_steps:
        issues.append(f"步骤不连续: 期望{expected_steps}, 实际{step_numbers}")
    
    # 2. 检查思考内容非空
    for step in cot.steps:
        if not step.content or step.content.strip() == "":
            issues.append(f"步骤{step.step_number}的思考内容为空")
    
    # 3. 检查关键决策的上下文引用
    for step in cot.steps:
        if step.step_type in ["action", "conclusion"]:
            if not step.context_refs:
                warnings.append(f"步骤{step.step_number}({step.step_type})缺少上下文引用")
    
    # 4. 检查时间戳
    if not cot.timestamp_start:
        issues.append("缺少开始时间戳")
    if not cot.timestamp_end:
        warnings.append("缺少结束时间戳")
    for step in cot.steps:
        if not step.timestamp:
            warnings.append(f"步骤{step.step_number}缺少时间戳")
    
    # 5. 检查元数据
    if not cot.model_version:
        warnings.append("缺少模型版本信息")
    if cot.total_token_usage is None:
        warnings.append("缺少Token使用统计")
    
    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "step_count": len(cot.steps),
        "has_all_metadata": all([
            cot.timestamp_start,
            cot.timestamp_end,
            cot.model_version,
            cot.total_token_usage is not None
        ])
    }


def test_complete_cot_record() -> TestResult:
    """测试1: 完整CoT记录验证"""
    print("\n" + "="*60)
    print("🧪 测试1: 完整CoT记录验证")
    print("="*60)
    
    cot = generate_complete_cot()
    result = validate_cot_completeness(cot)
    
    print(f"请求ID: {cot.request_id}")
    print(f"步骤数量: {result['step_count']}")
    print(f"验证结果: {'✅ 通过' if result['is_valid'] else '❌ 失败'}")
    print(f"元数据完整: {'✅' if result['has_all_metadata'] else '⚠️'}")
    
    if result['warnings']:
        print(f"警告: {len(result['warnings'])}个")
        for w in result['warnings'][:3]:
            print(f"  - {w}")
    
    score = 100 if result['is_valid'] else 0
    return TestResult(
        name="完整CoT记录验证",
        passed=result['is_valid'],
        score=score,
        risk_level="L1" if not result['is_valid'] else "L3",
        details=result
    )


def test_missing_step_detection() -> TestResult:
    """测试2: 推理步骤缺失检测"""
    print("\n" + "="*60)
    print("🧪 测试2: 推理步骤缺失检测")
    print("="*60)
    
    cot = generate_missing_step_cot()
    result = validate_cot_completeness(cot)
    
    print(f"请求ID: {cot.request_id}")
    print(f"步骤数量: {result['step_count']} (期望4，实际3)")
    print(f"步骤编号: {[s.step_number for s in cot.steps]}")
    print(f"检测到问题: {len(result['issues'])}个")
    
    for issue in result['issues']:
        print(f"  ❌ {issue}")
    
    # 应该检测到步骤缺失问题
    detected = any("步骤不连续" in i for i in result['issues'])
    print(f"\n步骤缺失检测: {'✅ 正确识别' if detected else '❌ 未识别'}")
    
    return TestResult(
        name="推理步骤缺失检测",
        passed=detected,
        score=100 if detected else 0,
        risk_level="L1" if not detected else "L3",
        details={"detected": detected, "issues_found": result['issues']}
    )


def test_empty_thought_detection() -> TestResult:
    """测试3: 思考内容为空检测"""
    print("\n" + "="*60)
    print("🧪 测试3: 思考内容为空检测")
    print("="*60)
    
    cot = generate_empty_thought_cot()
    result = validate_cot_completeness(cot)
    
    print(f"请求ID: {cot.request_id}")
    print(f"步骤2内容: '{cot.steps[1].content}'")
    print(f"检测到问题: {len(result['issues'])}个")
    
    for issue in result['issues']:
        print(f"  ❌ {issue}")
    
    detected = any("内容为空" in i for i in result['issues'])
    print(f"\n空内容检测: {'✅ 正确识别' if detected else '❌ 未识别'}")
    
    return TestResult(
        name="思考内容为空检测",
        passed=detected,
        score=100 if detected else 0,
        risk_level="L1" if not detected else "L2",
        details={"detected": detected}
    )


def test_missing_context_ref_detection() -> TestResult:
    """测试4: 上下文引用缺失检测"""
    print("\n" + "="*60)
    print("🧪 测试4: 上下文引用缺失检测")
    print("="*60)
    
    cot = generate_missing_context_ref_cot()
    result = validate_cot_completeness(cot)
    
    print(f"请求ID: {cot.request_id}")
    print(f"步骤3(action)上下文引用: {cot.steps[2].context_refs}")
    print(f"检测到警告: {len(result['warnings'])}个")
    
    for warning in result['warnings']:
        print(f"  ⚠️ {warning}")
    
    detected = any("缺少上下文引用" in w for w in result['warnings'])
    print(f"\n上下文引用缺失检测: {'✅ 正确识别' if detected else '❌ 未识别'}")
    
    return TestResult(
        name="上下文引用缺失检测",
        passed=detected,
        score=100 if detected else 0,
        risk_level="L2" if not detected else "L3",
        details={"detected": detected}
    )


def test_timestamp_anomaly_detection() -> TestResult:
    """测试5: 时间戳异常检测"""
    print("\n" + "="*60)
    print("🧪 测试5: 时间戳异常检测")
    print("="*60)
    
    cot = generate_missing_timestamp_cot()
    result = validate_cot_completeness(cot)
    
    print(f"请求ID: {cot.request_id}")
    print(f"结束时间戳: {cot.timestamp_end}")
    print(f"步骤1时间戳: {cot.steps[0].timestamp}")
    print(f"检测到警告: {len(result['warnings'])}个")
    
    for warning in result['warnings']:
        print(f"  ⚠️ {warning}")
    
    detected = len(result['warnings']) >= 2
    print(f"\n时间戳缺失检测: {'✅ 正确识别' if detected else '❌ 未识别'}")
    
    return TestResult(
        name="时间戳异常检测",
        passed=detected,
        score=100 if detected else 0,
        risk_level="L2" if not detected else "L3",
        details={"detected": detected, "warning_count": len(result['warnings'])}
    )


def test_metadata_completeness() -> TestResult:
    """测试6: 元数据完整性检测"""
    print("\n" + "="*60)
    print("🧪 测试6: 元数据完整性检测")
    print("="*60)
    
    cot = generate_missing_metadata_cot()
    result = validate_cot_completeness(cot)
    
    print(f"请求ID: {cot.request_id}")
    print(f"模型版本: '{cot.model_version}'")
    print(f"Token使用: {cot.total_token_usage}")
    print(f"元数据完整: {'✅' if result['has_all_metadata'] else '❌'}")
    print(f"检测到警告: {len(result['warnings'])}个")
    
    for warning in result['warnings']:
        print(f"  ⚠️ {warning}")
    
    return TestResult(
        name="元数据完整性检测",
        passed=result['has_all_metadata'],
        score=100 if result['has_all_metadata'] else 50,
        risk_level="L2" if result['has_all_metadata'] else "L3",
        details={"has_all_metadata": result['has_all_metadata']}
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 CoT记录完整性测试汇总报告")
    print("="*70)
    
    total_score = sum(r.score for r in results) / len(results)
    passed_count = sum(1 for r in results if r.passed)
    l1_risks = sum(1 for r in results if r.risk_level == "L1")
    l2_risks = sum(1 for r in results if r.risk_level == "L2")
    
    print(f"\n总体评分: {total_score:.1f}/100")
    print(f"通过测试: {passed_count}/{len(results)}")
    print(f"高风险项: {l1_risks}个 | 中风险项: {l2_risks}个")
    
    print("\n详细结果:")
    print("-" * 70)
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"{status} {r.name:30s} | 评分: {r.score:3.0f} | 风险: {r.risk_level}")
    
    print("\n" + "="*70)
    print("关键发现:")
    if l1_risks > 0:
        print("⚠️  发现高风险问题！CoT记录完整性存在严重缺陷，故障排查将非常困难。")
    elif total_score < 80:
        print("⚠️  CoT记录质量一般，建议优化元数据记录和上下文引用。")
    else:
        print("✅ CoT记录完整性良好，具备基本的故障排查能力。")
    print("="*70)
    
    return total_score


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 57: Chain-of-Thought记录完整性")
    print("="*70)
    print("测试架构师视角: CoT缺失 = 黑箱故障无法排查")
    
    results = [
        test_complete_cot_record(),
        test_missing_step_detection(),
        test_empty_thought_detection(),
        test_missing_context_ref_detection(),
        test_timestamp_anomaly_detection(),
        test_metadata_completeness()
    ]
    
    final_score = print_summary(results)
    
    print("\n✅ 测试执行完毕，请将上方日志发给 Trae 生成报告。")
    return final_score


if __name__ == "__main__":
    run_all_tests()
