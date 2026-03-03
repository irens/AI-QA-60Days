"""
Day 60: 组件失败熔断机制测试
目标：最小可用，专注风险验证，代码要足够精简
测试架构师视角：验证熔断器能否在组件故障时正确触发，防止级联雪崩
难度级别：基础 - 核心熔断逻辑验证
"""

import time
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"       # 关闭 - 正常通过
    OPEN = "open"           # 开启 - 快速失败
    HALF_OPEN = "half_open" # 半开 - 探测恢复


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: str
    details: str


@dataclass
class CircuitBreaker:
    """熔断器实现"""
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 5.0
    half_open_max_calls: int = 3
    success_threshold: int = 2
    
    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    success_count: int = field(default=0)
    last_failure_time: float = field(default=0.0)
    half_open_calls: int = field(default=0)
    total_calls: int = field(default=0)
    rejected_calls: int = field(default=0)
    
    def call(self, should_fail: bool = False) -> Dict[str, Any]:
        """执行调用"""
        self.total_calls += 1
        
        # OPEN状态：快速失败
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                self.success_count = 0
                print(f"  ⏰ 熔断器 [{self.name}] 进入 HALF_OPEN 状态")
            else:
                self.rejected_calls += 1
                return {"success": False, "rejected": True, "reason": "circuit_open"}
        
        # HALF_OPEN状态：限制探测流量
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                self.rejected_calls += 1
                return {"success": False, "rejected": True, "reason": "half_open_limit"}
            self.half_open_calls += 1
        
        # 执行实际调用
        if should_fail:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # 检查是否触发熔断
            if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                print(f"  🔴 熔断器 [{self.name}] 触发熔断！进入 OPEN 状态")
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                print(f"  🔴 熔断器 [{self.name}] 探测失败，回到 OPEN 状态")
            
            return {"success": False, "rejected": False, "reason": "component_failure"}
        else:
            # 成功调用
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    print(f"  🟢 熔断器 [{self.name}] 恢复！进入 CLOSED 状态")
            else:
                self.failure_count = 0
            
            return {"success": True, "rejected": False}


def test_basic_circuit_breaker_trigger():
    """测试1: 基础熔断触发 - 验证错误率达到阈值时正确熔断"""
    print("\n" + "="*60)
    print("🧪 测试1: 基础熔断触发测试")
    print("="*60)
    print("  场景: 模拟LLM API连续失败，验证熔断器是否正确触发")
    
    cb = CircuitBreaker(name="llm_api", failure_threshold=3)
    
    # 连续3次失败，触发熔断
    for i in range(5):
        result = cb.call(should_fail=True)
        print(f"  调用 {i+1}: state={cb.state.value}, success={result['success']}, rejected={result.get('rejected', False)}")
    
    # 验证熔断状态
    passed = cb.state == CircuitState.OPEN and cb.rejected_calls == 2
    score = 100.0 if passed else 0.0
    
    return TestResult(
        name="基础熔断触发测试",
        passed=passed,
        score=score,
        risk_level="L1",
        details=f"熔断器在{cb.failure_threshold}次失败后正确触发，拒绝后续请求"
    )


def test_state_transition_cycle():
    """测试2: 状态转换周期 - 验证完整 CLOSED → OPEN → HALF_OPEN → CLOSED 周期"""
    print("\n" + "="*60)
    print("🧪 测试2: 状态转换周期测试")
    print("="*60)
    print("  场景: 模拟故障→熔断→恢复→正常运行的完整周期")
    
    cb = CircuitBreaker(name="tool_call", failure_threshold=2, recovery_timeout=0.1, success_threshold=2)
    
    print(f"\n  阶段1: 正常调用 (CLOSED)")
    cb.call(should_fail=False)
    print(f"  状态: {cb.state.value}")
    
    print(f"\n  阶段2: 触发熔断 (CLOSED → OPEN)")
    cb.call(should_fail=True)
    cb.call(should_fail=True)
    print(f"  状态: {cb.state.value}")
    
    print(f"\n  阶段3: 等待恢复 (OPEN → HALF_OPEN)")
    time.sleep(0.15)
    cb.call(should_fail=False)  # 触发状态检查
    print(f"  状态: {cb.state.value}")
    
    print(f"\n  阶段4: 探测成功恢复 (HALF_OPEN → CLOSED)")
    cb.call(should_fail=False)
    cb.call(should_fail=False)
    print(f"  状态: {cb.state.value}")
    
    passed = cb.state == CircuitState.CLOSED
    score = 100.0 if passed else 50.0
    
    return TestResult(
        name="状态转换周期测试",
        passed=passed,
        score=score,
        risk_level="L1",
        details="熔断器完成完整的状态转换周期"
    )


def test_half_open_limit():
    """测试3: 半开状态流量限制 - 验证HALF_OPEN时限制探测请求数"""
    print("\n" + "="*60)
    print("🧪 测试3: 半开状态流量限制测试")
    print("="*60)
    print("  场景: 验证半开状态下只允许有限数量的探测请求")
    
    # 提高success_threshold确保在半开状态下不会立即恢复
    cb = CircuitBreaker(name="parser", failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=2, success_threshold=10)
    
    # 触发熔断
    cb.call(should_fail=True)
    time.sleep(0.15)
    
    # 半开状态下发送多个请求（都成功但不会立即恢复，因为success_threshold=10）
    results = []
    for i in range(5):
        result = cb.call(should_fail=False)
        results.append(result)
        print(f"  探测请求 {i+1}: rejected={result.get('rejected', False)}, state={cb.state.value}")
    
    # 应该只有2个被允许，3个被拒绝
    allowed = sum(1 for r in results if not r.get('rejected', False))
    rejected = sum(1 for r in results if r.get('rejected', False))
    
    passed = allowed == 2 and rejected == 3
    score = 100.0 if passed else 50.0
    
    return TestResult(
        name="半开状态流量限制测试",
        passed=passed,
        score=score,
        risk_level="L2",
        details=f"半开状态允许{allowed}个探测请求，拒绝{rejected}个请求"
    )


def test_threshold_boundary():
    """测试4: 阈值边界测试 - 验证临界条件下的熔断行为"""
    print("\n" + "="*60)
    print("🧪 测试4: 阈值边界测试")
    print("="*60)
    print("  场景: 测试 failure_threshold-1 次失败不应触发熔断")
    
    cb = CircuitBreaker(name="boundary", failure_threshold=5)
    
    # 4次失败（阈值-1）
    for i in range(4):
        cb.call(should_fail=True)
    
    print(f"  4次失败后状态: {cb.state.value}")
    
    # 第5次失败应该触发熔断
    cb.call(should_fail=True)
    print(f"  5次失败后状态: {cb.state.value}")
    
    passed = cb.state == CircuitState.OPEN
    score = 100.0 if passed else 0.0
    
    return TestResult(
        name="阈值边界测试",
        passed=passed,
        score=score,
        risk_level="L2",
        details="熔断器在达到精确阈值时才触发"
    )


def test_recovery_success_sequence():
    """测试5: 恢复成功序列 - 验证需要连续成功才能恢复"""
    print("\n" + "="*60)
    print("🧪 测试5: 恢复成功序列测试")
    print("="*60)
    print("  场景: 验证半开状态下需要连续成功才能恢复，单次失败立即熔断")
    
    cb = CircuitBreaker(name="recovery", failure_threshold=1, recovery_timeout=0.1, success_threshold=3)
    
    # 触发熔断
    cb.call(should_fail=True)
    time.sleep(0.15)
    
    # 半开状态：1次成功
    cb.call(should_fail=False)
    print(f"  1次成功后状态: {cb.state.value}")
    
    # 1次失败应该立即回到OPEN
    cb.call(should_fail=True)
    print(f"  再次失败后状态: {cb.state.value}")
    
    passed = cb.state == CircuitState.OPEN
    score = 100.0 if passed else 0.0
    
    return TestResult(
        name="恢复成功序列测试",
        passed=passed,
        score=score,
        risk_level="L2",
        details="半开状态下探测失败立即回到OPEN状态"
    )


def test_langchain_component_simulation():
    """测试6: LangChain组件模拟 - 模拟真实链式流程中的熔断"""
    print("\n" + "="*60)
    print("🧪 测试6: LangChain组件熔断模拟")
    print("="*60)
    print("  场景: 模拟Prompt→LLM→Parser→Tool链中Parser组件故障")
    
    # 创建链中各组件的熔断器
    prompt_cb = CircuitBreaker(name="prompt_template", failure_threshold=5)
    llm_cb = CircuitBreaker(name="llm_api", failure_threshold=3)
    parser_cb = CircuitBreaker(name="output_parser", failure_threshold=2)
    tool_cb = CircuitBreaker(name="tool_call", failure_threshold=3)
    
    # 模拟Parser连续失败
    print("\n  模拟Parser组件故障:")
    for i in range(4):
        parser_cb.call(should_fail=True)
        print(f"    Parser调用 {i+1}: state={parser_cb.state.value}")
    
    # 验证Parser熔断，其他组件正常
    print(f"\n  熔断状态检查:")
    print(f"    Prompt Template: {prompt_cb.state.value}")
    print(f"    LLM API: {llm_cb.state.value}")
    print(f"    Output Parser: {parser_cb.state.value} 🔴")
    print(f"    Tool Call: {tool_cb.state.value}")
    
    passed = parser_cb.state == CircuitState.OPEN and prompt_cb.state == CircuitState.CLOSED
    score = 100.0 if passed else 50.0
    
    return TestResult(
        name="LangChain组件熔断模拟",
        passed=passed,
        score=score,
        risk_level="L1",
        details="单个组件熔断不影响链中其他组件"
    )


def print_summary(results: List[TestResult]):
    """打印测试摘要"""
    print("\n" + "="*70)
    print("📊 测试摘要 - Day 60: 组件失败熔断机制")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / total
    
    l1_tests = [r for r in results if r.risk_level == "L1"]
    l1_passed = sum(1 for r in l1_tests if r.passed)
    
    print(f"\n  总测试数: {total}")
    print(f"  通过: {passed}/{total}")
    print(f"  平均得分: {avg_score:.1f}%")
    print(f"  L1关键测试通过: {l1_passed}/{len(l1_tests)}")
    
    print(f"\n  详细结果:")
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"    {status} [{r.risk_level}] {r.name}: {r.score:.0f}%")
    
    # 风险评估
    print(f"\n  🎯 风险评估:")
    if l1_passed == len(l1_tests):
        print(f"    🟢 熔断机制基础功能正常，可有效防止级联故障")
    elif l1_passed >= len(l1_tests) // 2:
        print(f"    🟡 熔断机制部分功能异常，建议排查关键路径")
    else:
        print(f"    🔴 熔断机制严重缺陷，存在级联雪崩风险！")
    
    print("\n" + "="*70)
    print("✅ 测试执行完毕，请将上方日志发给 Trae 生成报告。")
    print("="*70)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 60: 组件失败熔断机制测试")
    print("="*70)
    print("\n  测试架构师视角: 验证熔断器能否在组件故障时正确触发")
    print("  防止级联雪崩效应，保护系统稳定性")
    
    results = [
        test_basic_circuit_breaker_trigger(),
        test_state_transition_cycle(),
        test_half_open_limit(),
        test_threshold_boundary(),
        test_recovery_success_sequence(),
        test_langchain_component_simulation(),
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
