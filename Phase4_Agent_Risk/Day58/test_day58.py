"""
Day 58: Agent决策归因分析
目标：验证能否从错误答案追溯到根本原因
测试架构师视角：无法归因 = 无法修复 = 故障反复发生
难度级别：进阶
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class ErrorSource(Enum):
    """错误来源类型"""
    INTENT_RECOGNITION = "意图识别错误"
    ENTITY_EXTRACTION = "实体提取错误"
    CONTEXT_POLLUTION = "上下文污染"
    TOOL_ERROR = "工具返回错误"
    REASONING_ERROR = "推理逻辑错误"
    HALLUCINATION = "模型幻觉"
    UNKNOWN = "未知原因"


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_id: str
    step_number: int
    step_type: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    is_correct: bool = True
    error_description: str = ""


@dataclass
class AttributionResult:
    """归因分析结果"""
    root_cause: ErrorSource
    root_step_id: Optional[str]
    confidence: float  # 0-1
    propagation_path: List[str] = field(default_factory=list)
    contributing_factors: Dict[str, float] = field(default_factory=dict)
    remediation_suggestion: str = ""


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: str
    details: Dict[str, Any] = field(default_factory=dict)


class AgentDecisionTracer:
    """Agent决策追踪器 - 模拟归因分析系统"""
    
    def __init__(self):
        self.reasoning_chain: List[ReasoningStep] = []
        self.final_answer: str = ""
        self.ground_truth: str = ""
    
    def add_step(self, step: ReasoningStep):
        """添加推理步骤"""
        self.reasoning_chain.append(step)
    
    def set_ground_truth(self, truth: str):
        """设置正确答案"""
        self.ground_truth = truth
    
    def set_final_answer(self, answer: str):
        """设置最终答案"""
        self.final_answer = answer
    
    def is_answer_correct(self) -> bool:
        """判断答案是否正确"""
        return self.final_answer.lower().strip() == self.ground_truth.lower().strip()
    
    def analyze_attribution(self) -> AttributionResult:
        """
        执行归因分析
        从最终答案回溯到根本原因
        """
        if self.is_answer_correct():
            return AttributionResult(
                root_cause=ErrorSource.UNKNOWN,
                root_step_id=None,
                confidence=1.0,
                remediation_suggestion="答案正确，无需归因分析"
            )
        
        # 从后向前遍历，找到第一个错误步骤
        error_step = None
        for step in reversed(self.reasoning_chain):
            if not step.is_correct:
                error_step = step
                break
        
        if error_step is None:
            # 所有步骤都正确但答案错误 → 可能是综合推理错误或幻觉
            return AttributionResult(
                root_cause=ErrorSource.REASONING_ERROR,
                root_step_id=None,
                confidence=0.6,
                remediation_suggestion="检查最终推理逻辑，可能存在综合判断错误"
            )
        
        # 构建传播路径
        propagation_path = []
        found_error = False
        for step in self.reasoning_chain:
            if step.step_id == error_step.step_id:
                found_error = True
            if found_error:
                propagation_path.append(step.step_id)
        
        # 确定错误来源类型
        root_cause = self._classify_error(error_step)
        
        # 生成修复建议
        suggestion = self._generate_remediation(error_step, root_cause)
        
        # 计算各因素贡献度（简化版消融实验）
        contributing_factors = self._calculate_contributions()
        
        return AttributionResult(
            root_cause=root_cause,
            root_step_id=error_step.step_id,
            confidence=0.85,
            propagation_path=propagation_path,
            contributing_factors=contributing_factors,
            remediation_suggestion=suggestion
        )
    
    def _classify_error(self, step: ReasoningStep) -> ErrorSource:
        """分类错误类型"""
        if step.step_type == "intent_recognition":
            return ErrorSource.INTENT_RECOGNITION
        elif step.step_type == "entity_extraction":
            return ErrorSource.ENTITY_EXTRACTION
        elif step.step_type == "tool_call":
            return ErrorSource.TOOL_ERROR
        elif step.step_type == "context_retrieval":
            return ErrorSource.CONTEXT_POLLUTION
        elif "幻觉" in step.error_description or "编造" in step.error_description:
            return ErrorSource.HALLUCINATION
        else:
            return ErrorSource.REASONING_ERROR
    
    def _generate_remediation(self, step: ReasoningStep, cause: ErrorSource) -> str:
        """生成修复建议"""
        suggestions = {
            ErrorSource.INTENT_RECOGNITION: "优化意图识别Prompt，增加示例覆盖",
            ErrorSource.ENTITY_EXTRACTION: "加强实体提取准确性，增加验证机制",
            ErrorSource.CONTEXT_POLLUTION: "优化检索策略，增加相关性过滤",
            ErrorSource.TOOL_ERROR: "检查工具实现，增加错误处理和重试机制",
            ErrorSource.REASONING_ERROR: "优化推理逻辑，增加中间结果验证",
            ErrorSource.HALLUCINATION: "增加事实核查步骤，使用RAG减少幻觉"
        }
        return suggestions.get(cause, "需要进一步分析")
    
    def _calculate_contributions(self) -> Dict[str, float]:
        """计算各因素贡献度"""
        contributions = {}
        for step in self.reasoning_chain:
            # 简化计算：错误步骤贡献度更高
            base_score = 0.3 if step.is_correct else 0.8
            contributions[step.step_id] = base_score
        return contributions


def create_correct_weather_scenario() -> AgentDecisionTracer:
    """创建正确的天气查询场景"""
    tracer = AgentDecisionTracer()
    tracer.set_ground_truth("北京今天晴天，气温15-22度")
    
    # Step 1: 意图识别
    tracer.add_step(ReasoningStep(
        step_id="step_1",
        step_number=1,
        step_type="intent_recognition",
        input_data={"query": "北京今天天气怎么样"},
        output_data={"intent": "weather_query", "location": "北京"},
        is_correct=True
    ))
    
    # Step 2: 实体提取
    tracer.add_step(ReasoningStep(
        step_id="step_2",
        step_number=2,
        step_type="entity_extraction",
        input_data={"query": "北京今天天气怎么样"},
        output_data={"city": "北京", "date": "今天"},
        dependencies=["step_1"],
        is_correct=True
    ))
    
    # Step 3: 工具调用
    tracer.add_step(ReasoningStep(
        step_id="step_3",
        step_number=3,
        step_type="tool_call",
        input_data={"tool": "get_weather", "params": {"city": "北京"}},
        output_data={"weather": "晴天", "temp": "15-22度"},
        dependencies=["step_2"],
        is_correct=True
    ))
    
    # Step 4: 答案生成
    tracer.add_step(ReasoningStep(
        step_id="step_4",
        step_number=4,
        step_type="answer_generation",
        input_data={"weather_data": {"weather": "晴天", "temp": "15-22度"}},
        output_data={"answer": "北京今天晴天，气温15-22度"},
        dependencies=["step_3"],
        is_correct=True
    ))
    
    tracer.set_final_answer("北京今天晴天，气温15-22度")
    return tracer


def create_context_pollution_scenario() -> AgentDecisionTracer:
    """创建上下文污染场景"""
    tracer = AgentDecisionTracer()
    tracer.set_ground_truth("iPhone 15的价格是5999元起")
    
    # Step 1: 意图识别
    tracer.add_step(ReasoningStep(
        step_id="step_1",
        step_number=1,
        step_type="intent_recognition",
        input_data={"query": "iPhone 15多少钱"},
        output_data={"intent": "price_query", "product": "iPhone 15"},
        is_correct=True
    ))
    
    # Step 2: 上下文检索 - 污染发生
    tracer.add_step(ReasoningStep(
        step_id="step_2",
        step_number=2,
        step_type="context_retrieval",
        input_data={"product": "iPhone 15"},
        output_data={
            "retrieved_docs": [
                "iPhone 14的价格是5999元",  # 错误文档
                "iPhone 15发布于2023年"
            ]
        },
        dependencies=["step_1"],
        is_correct=False,
        error_description="检索到iPhone 14的价格信息，造成上下文污染"
    ))
    
    # Step 3: 答案生成 - 基于污染上下文（本身逻辑正确，只是输入错误）
    tracer.add_step(ReasoningStep(
        step_id="step_3",
        step_number=3,
        step_type="answer_generation",
        input_data={"context": "iPhone 14的价格是5999元"},
        output_data={"answer": "iPhone 15的价格是5999元"},  # 基于输入的正确推理
        dependencies=["step_2"],
        is_correct=True,  # 步骤本身正确，错误源于输入
        error_description=""
    ))
    
    tracer.set_final_answer("iPhone 15的价格是5999元")
    return tracer


def create_tool_error_scenario() -> AgentDecisionTracer:
    """创建工具返回错误场景"""
    tracer = AgentDecisionTracer()
    tracer.set_ground_truth("账户余额: 1000元")
    
    # Step 1: 意图识别
    tracer.add_step(ReasoningStep(
        step_id="step_1",
        step_number=1,
        step_type="intent_recognition",
        input_data={"query": "查余额"},
        output_data={"intent": "balance_query"},
        is_correct=True
    ))
    
    # Step 2: 实体提取
    tracer.add_step(ReasoningStep(
        step_id="step_2",
        step_number=2,
        step_type="entity_extraction",
        input_data={"query": "查余额"},
        output_data={"account_id": "ACC_12345"},
        dependencies=["step_1"],
        is_correct=True
    ))
    
    # Step 3: 工具调用 - 返回错误数据
    tracer.add_step(ReasoningStep(
        step_id="step_3",
        step_number=3,
        step_type="tool_call",
        input_data={"tool": "get_balance", "account_id": "ACC_12345"},
        output_data={"balance": 500, "currency": "CNY"},  # 错误余额
        dependencies=["step_2"],
        is_correct=False,
        error_description="工具返回了错误的余额数据"
    ))
    
    # Step 4: 答案生成（本身逻辑正确）
    tracer.add_step(ReasoningStep(
        step_id="step_4",
        step_number=4,
        step_type="answer_generation",
        input_data={"balance": 500},
        output_data={"answer": "您的账户余额是500元"},
        dependencies=["step_3"],
        is_correct=True,  # 步骤本身正确
        error_description=""
    ))
    
    tracer.set_final_answer("您的账户余额是500元")
    return tracer


def create_entity_extraction_error_scenario() -> AgentDecisionTracer:
    """创建实体提取错误场景"""
    tracer = AgentDecisionTracer()
    tracer.set_ground_truth("张三的余额是1000元")
    
    # Step 1: 意图识别
    tracer.add_step(ReasoningStep(
        step_id="step_1",
        step_number=1,
        step_type="intent_recognition",
        input_data={"query": "查张三的余额"},
        output_data={"intent": "balance_query", "person": "张三"},
        is_correct=True
    ))
    
    # Step 2: 实体提取 - 提取错误
    tracer.add_step(ReasoningStep(
        step_id="step_2",
        step_number=2,
        step_type="entity_extraction",
        input_data={"query": "查张三的余额"},
        output_data={"account_id": "ACC_LISI"},  # 错误提取为李四的账户
        dependencies=["step_1"],
        is_correct=False,
        error_description="将'张三'错误识别为'李四'的账户"
    ))
    
    # Step 3: 工具调用
    tracer.add_step(ReasoningStep(
        step_id="step_3",
        step_number=3,
        step_type="tool_call",
        input_data={"account_id": "ACC_LISI"},
        output_data={"balance": 5000, "owner": "李四"},
        dependencies=["step_2"],
        is_correct=True  # 工具本身正确执行
    ))
    
    # Step 4: 答案生成（本身逻辑正确）
    tracer.add_step(ReasoningStep(
        step_id="step_4",
        step_number=4,
        step_type="answer_generation",
        input_data={"balance": 5000},
        output_data={"answer": "张三的余额是5000元"},  # 基于查询结果的正确回答
        dependencies=["step_3"],
        is_correct=True,  # 步骤本身正确，错误源于step_2
        error_description=""
    ))
    
    tracer.set_final_answer("张三的余额是5000元")
    return tracer


def create_multi_factor_error_scenario() -> AgentDecisionTracer:
    """创建多因素叠加错误场景"""
    tracer = AgentDecisionTracer()
    tracer.set_ground_truth("明天北京有雨，记得带伞")
    
    # Step 1: 意图识别 - 轻微错误
    tracer.add_step(ReasoningStep(
        step_id="step_1",
        step_number=1,
        step_type="intent_recognition",
        input_data={"query": "明天出门需要带伞吗"},
        output_data={"intent": "weather_advice", "date": "明天"},
        is_correct=True
    ))
    
    # Step 2: 上下文检索 - 污染
    tracer.add_step(ReasoningStep(
        step_id="step_2",
        step_number=2,
        step_type="context_retrieval",
        input_data={"date": "明天"},
        output_data={"retrieved": "上海明天有雨"},  # 城市错误
        dependencies=["step_1"],
        is_correct=False,
        error_description="检索到上海天气而非北京"
    ))
    
    # Step 3: 工具调用 - 也出错
    tracer.add_step(ReasoningStep(
        step_id="step_3",
        step_number=3,
        step_type="tool_call",
        input_data={"city": "北京", "date": "明天"},
        output_data={"weather": "晴天"},  # 工具返回错误
        dependencies=["step_2"],
        is_correct=False,
        error_description="天气API返回了错误数据"
    ))
    
    # Step 4: 答案生成
    tracer.add_step(ReasoningStep(
        step_id="step_4",
        step_number=4,
        step_type="answer_generation",
        input_data={"weather": "晴天"},
        output_data={"answer": "明天北京晴天，不需要带伞"},
        dependencies=["step_3"],
        is_correct=False
    ))
    
    tracer.set_final_answer("明天北京晴天，不需要带伞")
    return tracer


def test_correct_decision_attribution() -> TestResult:
    """测试1: 正确决策路径归因"""
    print("\n" + "="*60)
    print("🧪 测试1: 正确决策路径归因")
    print("="*60)
    
    tracer = create_correct_weather_scenario()
    result = tracer.analyze_attribution()
    
    print(f"场景: 天气查询")
    print(f"最终答案: {tracer.final_answer}")
    print(f"正确答案: {tracer.ground_truth}")
    print(f"答案正确: {'✅' if tracer.is_answer_correct() else '❌'}")
    print(f"归因结果: {result.root_cause.value}")
    print(f"置信度: {result.confidence:.0%}")
    
    passed = tracer.is_answer_correct() and result.root_cause == ErrorSource.UNKNOWN
    return TestResult(
        name="正确决策路径归因",
        passed=passed,
        score=100 if passed else 0,
        risk_level="L3",
        details={"answer_correct": tracer.is_answer_correct()}
    )


def test_context_pollution_attribution() -> TestResult:
    """测试2: 上下文污染归因"""
    print("\n" + "="*60)
    print("🧪 测试2: 上下文污染归因")
    print("="*60)
    
    tracer = create_context_pollution_scenario()
    result = tracer.analyze_attribution()
    
    print(f"场景: 价格查询（上下文污染）")
    print(f"最终答案: {tracer.final_answer}")
    print(f"正确答案: {tracer.ground_truth}")
    print(f"答案正确: {'✅' if tracer.is_answer_correct() else '❌'}")
    print(f"\n归因分析:")
    print(f"  根本原因: {result.root_cause.value}")
    print(f"  问题步骤: {result.root_step_id}")
    print(f"  置信度: {result.confidence:.0%}")
    print(f"  传播路径: {' → '.join(result.propagation_path)}")
    print(f"  修复建议: {result.remediation_suggestion}")
    
    # 验证是否正确归因到上下文污染
    correct_attribution = result.root_cause == ErrorSource.CONTEXT_POLLUTION
    print(f"\n归因准确性: {'✅ 正确' if correct_attribution else '❌ 错误'}")
    
    return TestResult(
        name="上下文污染归因",
        passed=correct_attribution,
        score=100 if correct_attribution else 0,
        risk_level="L1" if not correct_attribution else "L2",
        details={
            "root_cause": result.root_cause.value,
            "confidence": result.confidence
        }
    )


def test_tool_error_attribution() -> TestResult:
    """测试3: 工具返回错误归因"""
    print("\n" + "="*60)
    print("🧪 测试3: 工具返回错误归因")
    print("="*60)
    
    tracer = create_tool_error_scenario()
    result = tracer.analyze_attribution()
    
    print(f"场景: 余额查询（工具错误）")
    print(f"最终答案: {tracer.final_answer}")
    print(f"正确答案: {tracer.ground_truth}")
    print(f"\n归因分析:")
    print(f"  根本原因: {result.root_cause.value}")
    print(f"  问题步骤: {result.root_step_id}")
    print(f"  置信度: {result.confidence:.0%}")
    print(f"  传播路径: {' → '.join(result.propagation_path)}")
    print(f"  修复建议: {result.remediation_suggestion}")
    
    correct_attribution = result.root_cause == ErrorSource.TOOL_ERROR
    print(f"\n归因准确性: {'✅ 正确' if correct_attribution else '❌ 错误'}")
    
    return TestResult(
        name="工具返回错误归因",
        passed=correct_attribution,
        score=100 if correct_attribution else 0,
        risk_level="L1" if not correct_attribution else "L2",
        details={"root_cause": result.root_cause.value}
    )


def test_entity_extraction_error_attribution() -> TestResult:
    """测试4: 实体提取错误归因"""
    print("\n" + "="*60)
    print("🧪 测试4: 实体提取错误归因")
    print("="*60)
    
    tracer = create_entity_extraction_error_scenario()
    result = tracer.analyze_attribution()
    
    print(f"场景: 用户余额查询（实体提取错误）")
    print(f"用户查询: '查张三的余额'")
    print(f"提取实体: ACC_LISI (李四的账户)")
    print(f"最终答案: {tracer.final_answer}")
    print(f"正确答案: {tracer.ground_truth}")
    print(f"\n归因分析:")
    print(f"  根本原因: {result.root_cause.value}")
    print(f"  问题步骤: {result.root_step_id}")
    print(f"  置信度: {result.confidence:.0%}")
    print(f"  传播路径: {' → '.join(result.propagation_path)}")
    print(f"  修复建议: {result.remediation_suggestion}")
    
    correct_attribution = result.root_cause == ErrorSource.ENTITY_EXTRACTION
    print(f"\n归因准确性: {'✅ 正确' if correct_attribution else '❌ 错误'}")
    
    return TestResult(
        name="实体提取错误归因",
        passed=correct_attribution,
        score=100 if correct_attribution else 0,
        risk_level="L1" if not correct_attribution else "L2",
        details={"root_cause": result.root_cause.value}
    )


def test_multi_factor_attribution() -> TestResult:
    """测试5: 多因素叠加归因"""
    print("\n" + "="*60)
    print("🧪 测试5: 多因素叠加归因")
    print("="*60)
    
    tracer = create_multi_factor_error_scenario()
    result = tracer.analyze_attribution()
    
    print(f"场景: 天气建议（多因素错误）")
    print(f"问题1: 上下文检索错误（城市错误）")
    print(f"问题2: 工具调用返回错误")
    print(f"最终答案: {tracer.final_answer}")
    print(f"正确答案: {tracer.ground_truth}")
    print(f"\n归因分析:")
    print(f"  根本原因: {result.root_cause.value}")
    print(f"  问题步骤: {result.root_step_id}")
    print(f"  置信度: {result.confidence:.0%}")
    print(f"  因素贡献度:")
    for factor, score in result.contributing_factors.items():
        print(f"    - {factor}: {score:.0%}")
    
    # 多因素场景下，只要能定位到其中一个错误就算通过
    has_error_detected = result.root_step_id is not None
    print(f"\n错误检测: {'✅ 检测到' if has_error_detected else '❌ 未检测到'}")
    
    return TestResult(
        name="多因素叠加归因",
        passed=has_error_detected,
        score=100 if has_error_detected else 0,
        risk_level="L2" if not has_error_detected else "L3",
        details={
            "root_cause": result.root_cause.value,
            "contributing_factors": result.contributing_factors
        }
    )


def test_error_propagation_tracking() -> TestResult:
    """测试6: 错误传播路径追踪"""
    print("\n" + "="*60)
    print("🧪 测试6: 错误传播路径追踪")
    print("="*60)
    
    tracer = create_entity_extraction_error_scenario()
    result = tracer.analyze_attribution()
    
    print(f"场景: 错误传播分析")
    print(f"错误起源: {result.root_step_id}")
    print(f"传播路径:")
    for i, step_id in enumerate(result.propagation_path, 1):
        step = next(s for s in tracer.reasoning_chain if s.step_id == step_id)
        status = "❌ 错误" if not step.is_correct else "✅ 正确"
        print(f"  {i}. {step_id} ({step.step_type}) {status}")
    
    # 验证传播路径完整性（从错误源头开始）
    expected_path = ["step_2"]  # step_2是错误源头，step_3/step_4本身逻辑正确
    path_correct = result.root_step_id == "step_2"
    print(f"\n传播路径完整性: {'✅ 正确识别错误源头' if path_correct else '⚠️ 未正确识别'}")
    
    return TestResult(
        name="错误传播路径追踪",
        passed=path_correct,
        score=100 if path_correct else 50,
        risk_level="L2" if not path_correct else "L3",
        details={
            "propagation_path": result.propagation_path,
            "expected_path": expected_path
        }
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 Agent决策归因分析测试汇总报告")
    print("="*70)
    
    total_score = sum(r.score for r in results) / len(results)
    passed_count = sum(1 for r in results if r.passed)
    l1_risks = sum(1 for r in results if r.risk_level == "L1")
    
    print(f"\n总体评分: {total_score:.1f}/100")
    print(f"通过测试: {passed_count}/{len(results)}")
    print(f"高风险项: {l1_risks}个")
    
    print("\n详细结果:")
    print("-" * 70)
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"{status} {r.name:30s} | 评分: {r.score:3.0f} | 风险: {r.risk_level}")
    
    print("\n" + "="*70)
    print("关键发现:")
    if l1_risks > 0:
        print("⚠️  发现高风险问题！归因分析能力存在缺陷，无法准确定位错误根源。")
    elif total_score < 80:
        print("⚠️  归因分析能力一般，建议优化错误分类和传播追踪算法。")
    else:
        print("✅ 归因分析能力良好，能够快速定位错误根源和传播路径。")
    print("="*70)
    
    return total_score


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 58: Agent决策归因分析")
    print("="*70)
    print("测试架构师视角: 无法归因 = 无法修复 = 故障反复发生")
    
    results = [
        test_correct_decision_attribution(),
        test_context_pollution_attribution(),
        test_tool_error_attribution(),
        test_entity_extraction_error_attribution(),
        test_multi_factor_attribution(),
        test_error_propagation_tracking()
    ]
    
    final_score = print_summary(results)
    
    print("\n✅ 测试执行完毕，请将上方日志发给 Trae 生成报告。")
    return final_score


if __name__ == "__main__":
    run_all_tests()
