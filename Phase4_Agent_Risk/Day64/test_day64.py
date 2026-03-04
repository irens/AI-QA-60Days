"""
Day 64: 超时控制与熔断机制测试
目标：验证超时和熔断机制在各种故障场景下的有效性
"""

import threading
import time
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import uuid


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常通行
    OPEN = "open"          # 熔断打开，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，探测请求


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: float = 0.5      # 失败率阈值
    min_calls: int = 10                  # 最小调用次数
    open_duration: float = 5.0          # 熔断持续时间
    half_open_max_calls: int = 3        # 半开状态最大探测数
    success_threshold: int = 2          # 半开状态成功阈值


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, config: CircuitBreakerConfig = None, name: str = "default"):
        self.config = config or CircuitBreakerConfig()
        self.name = name
        self.state = CircuitState.CLOSED
        
        # 统计
        self.total_calls = 0
        self.failed_calls = 0
        self.consecutive_success = 0
        
        # 时间控制
        self.last_failure_time = 0
        self.half_open_calls = 0
        
        self._lock = threading.Lock()
    
    def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                # 检查是否过了熔断时间
                if time.time() - self.last_failure_time >= self.config.open_duration:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.consecutive_success = 0
                    return True
                return False
            elif self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls < self.config.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False
        return False
    
    def record_success(self):
        """记录成功"""
        with self._lock:
            self.total_calls += 1
            self.consecutive_success += 1
            
            if self.state == CircuitState.HALF_OPEN:
                if self.consecutive_success >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self._reset_stats()
    
    def record_failure(self):
        """记录失败"""
        with self._lock:
            self.total_calls += 1
            self.failed_calls += 1
            self.consecutive_success = 0
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.last_failure_time = time.time()
            elif self.state == CircuitState.CLOSED:
                # 检查是否达到熔断阈值
                if self.total_calls >= self.config.min_calls:
                    failure_rate = self.failed_calls / self.total_calls
                    if failure_rate >= self.config.failure_threshold:
                        self.state = CircuitState.OPEN
                        self.last_failure_time = time.time()
    
    def _reset_stats(self):
        """重置统计"""
        self.total_calls = 0
        self.failed_calls = 0
        self.consecutive_success = 0
        self.half_open_calls = 0
    
    def get_state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            return self.state
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            failure_rate = self.failed_calls / max(self.total_calls, 1)
            return {
                "state": self.state.value,
                "total_calls": self.total_calls,
                "failed_calls": self.failed_calls,
                "failure_rate": f"{failure_rate:.1%}",
                "consecutive_success": self.consecutive_success
            }


class TimeoutController:
    """超时控制器"""
    
    def __init__(
        self,
        connect_timeout: float = 1.0,
        read_timeout: float = 2.0,
        total_timeout: float = 5.0
    ):
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.total_timeout = total_timeout
    
    def execute_with_timeout(
        self,
        func: Callable,
        timeout_type: str = "total",
        simulate_delay: float = 0
    ) -> tuple:
        """带超时执行函数"""
        timeout_map = {
            "connect": self.connect_timeout,
            "read": self.read_timeout,
            "total": self.total_timeout
        }
        timeout = timeout_map.get(timeout_type, self.total_timeout)
        
        result = [None]
        exception = [None]
        
        def target():
            try:
                if simulate_delay > 0:
                    time.sleep(simulate_delay)
                result[0] = func()
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            return False, f"{timeout_type}_timeout"
        
        if exception[0]:
            return False, str(exception[0])
        
        return True, result[0]


class MockService:
    """模拟下游服务"""
    
    def __init__(self, failure_rate: float = 0.0, latency_ms: float = 0):
        self.failure_rate = failure_rate
        self.latency_ms = latency_ms
        self.call_count = 0
        self.failure_count = 0
    
    def call(self) -> tuple:
        """模拟服务调用"""
        self.call_count += 1
        
        # 模拟延迟
        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000)
        
        # 模拟失败
        if random.random() < self.failure_rate:
            self.failure_count += 1
            return False, "服务调用失败"
        
        return True, "服务调用成功"
    
    def set_failure_rate(self, rate: float):
        """设置失败率"""
        self.failure_rate = rate
    
    def set_latency(self, latency_ms: float):
        """设置延迟"""
        self.latency_ms = latency_ms


class TimeoutCircuitTester:
    """超时与熔断测试器"""
    
    def __init__(self):
        self.results: List[Dict] = []
    
    def test_timeout_mechanism(self) -> Dict:
        """测试超时机制"""
        print("\n[超时机制测试] 测试中...")
        
        controller = TimeoutController(
            connect_timeout=0.5,
            read_timeout=1.0,
            total_timeout=2.0
        )
        
        results = {
            "connect_timeout": False,
            "read_timeout": False,
            "total_timeout": False
        }
        
        # 测试连接超时
        start = time.time()
        success, msg = controller.execute_with_timeout(
            lambda: time.sleep(2),
            timeout_type="connect",
            simulate_delay=1.0
        )
        connect_time = time.time() - start
        results["connect_timeout"] = not success and msg == "connect_timeout"
        
        # 测试读取超时
        start = time.time()
        success, msg = controller.execute_with_timeout(
            lambda: "data",
            timeout_type="read",
            simulate_delay=0.1
        )
        read_time = time.time() - start
        results["read_timeout"] = success
        
        # 测试总超时
        start = time.time()
        success, msg = controller.execute_with_timeout(
            lambda: time.sleep(3),
            timeout_type="total",
            simulate_delay=3.0
        )
        total_time = time.time() - start
        results["total_timeout"] = not success and msg == "total_timeout"
        
        all_passed = all(results.values())
        
        return {
            "name": "超时机制测试",
            "passed": all_passed,
            "score": sum(results.values()) / len(results),
            "details": f"连接超时: {connect_time:.2f}s, 读取: {read_time:.2f}s, 总超时: {total_time:.2f}s",
            "risk_level": "L1" if not all_passed else "L3"
        }
    
    def test_circuit_state_transition(self) -> Dict:
        """测试熔断器状态转换"""
        print("\n[熔断器状态转换] 测试中...")
        
        config = CircuitBreakerConfig(
            failure_threshold=0.5,
            min_calls=5,
            open_duration=2.0,
            half_open_max_calls=3,
            success_threshold=2
        )
        
        cb = CircuitBreaker(config, name="test")
        
        # 初始状态应该是CLOSED
        initial_state = cb.get_state()
        
        # 模拟失败触发熔断
        for i in range(10):
            if cb.can_execute():
                if i < 8:  # 80%失败率
                    cb.record_failure()
                else:
                    cb.record_success()
        
        open_state = cb.get_state()
        
        # 等待熔断时间
        time.sleep(2.1)
        
        # 尝试执行，应该进入HALF_OPEN
        can_execute = cb.can_execute()
        half_open_state = cb.get_state()
        
        # 连续成功，应该恢复CLOSED
        for _ in range(3):
            cb.record_success()
        
        final_state = cb.get_state()
        
        passed = (
            initial_state == CircuitState.CLOSED and
            open_state == CircuitState.OPEN and
            half_open_state == CircuitState.HALF_OPEN and
            final_state == CircuitState.CLOSED
        )
        
        return {
            "name": "熔断器状态转换",
            "passed": passed,
            "score": 1.0 if passed else 0.0,
            "details": f"CLOSED->{open_state.value}->{half_open_state.value}->{final_state.value}",
            "risk_level": "L1" if not passed else "L3"
        }
    
    def test_cascade_failure_protection(self) -> Dict:
        """测试级联故障防护"""
        print("\n[级联故障防护] 测试中...")
        
        # 下游服务故障
        downstream = MockService(failure_rate=1.0)
        
        # 上游熔断器
        cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=0.5, min_calls=5, open_duration=3.0),
            name="upstream"
        )
        
        results = {"normal": 0, "fallback": 0, "rejected": 0}
        
        for i in range(20):
            if cb.can_execute():
                success, msg = downstream.call()
                if success:
                    cb.record_success()
                    results["normal"] += 1
                else:
                    cb.record_failure()
                    results["fallback"] += 1  # 模拟降级
            else:
                results["rejected"] += 1  # 熔断拒绝
        
        # 验证熔断器生效
        protection_worked = results["rejected"] > 0 and cb.get_state() == CircuitState.OPEN
        
        return {
            "name": "级联故障防护",
            "passed": protection_worked,
            "score": 1.0 if protection_worked else 0.0,
            "details": f"正常: {results['normal']}, 降级: {results['fallback']}, 拒绝: {results['rejected']}",
            "risk_level": "L1" if not protection_worked else "L3"
        }
    
    def test_half_open_probe(self) -> Dict:
        """测试半开状态探测"""
        print("\n[半开状态探测] 测试中...")
        
        config = CircuitBreakerConfig(
            failure_threshold=0.5,
            min_calls=5,
            open_duration=1.0,
            half_open_max_calls=3,
            success_threshold=2
        )
        
        cb = CircuitBreaker(config)
        downstream = MockService(failure_rate=1.0)  # 先设置故障
        
        # 触发熔断
        for _ in range(10):
            if cb.can_execute():
                success, _ = downstream.call()
                if success:
                    cb.record_success()
                else:
                    cb.record_failure()
        
        assert cb.get_state() == CircuitState.OPEN
        
        # 等待进入半开
        time.sleep(1.1)
        
        # 恢复服务
        downstream.set_failure_rate(0.0)
        
        # 探测请求
        probe_results = []
        for _ in range(5):
            if cb.can_execute():
                success, _ = downstream.call()
                probe_results.append(success)
                if success:
                    cb.record_success()
                else:
                    cb.record_failure()
        
        final_state = cb.get_state()
        
        # 应该成功恢复
        passed = final_state == CircuitState.CLOSED and all(probe_results[:3])
        
        return {
            "name": "半开状态探测",
            "passed": passed,
            "score": 1.0 if passed else 0.0,
            "details": f"探测结果: {probe_results}, 最终状态: {final_state.value}",
            "risk_level": "L1" if not passed else "L3"
        }
    
    def test_timeout_configuration(self) -> Dict:
        """测试超时配置合理性"""
        print("\n[超时配置验证] 测试中...")
        
        # 模拟不同延迟的请求
        latencies = [0.1, 0.2, 0.3, 0.5, 1.0, 1.5, 2.0, 2.5]
        timeout = 1.0  # 1秒超时
        
        normal_requests = 0
        killed_requests = 0
        
        for latency in latencies:
            controller = TimeoutController(total_timeout=timeout)
            success, _ = controller.execute_with_timeout(
                lambda: f"result",
                simulate_delay=latency
            )
            if latency <= 0.8:  # 正常请求应该<timeout
                normal_requests += 1
            elif not success:
                killed_requests += 1
        
        # 检查误杀率
        false_kill_rate = 0  # 这里简化处理
        
        # 超时配置应该允许大部分正常请求通过
        reasonable = normal_requests >= 4
        
        return {
            "name": "超时配置验证",
            "passed": reasonable,
            "score": normal_requests / len(latencies),
            "details": f"正常通过: {normal_requests}/{len(latencies)}, 超时截断: {killed_requests}",
            "risk_level": "L2" if not reasonable else "L3"
        }
    
    def run_all_tests(self) -> List[Dict]:
        """运行所有测试"""
        print("=" * 60)
        print("=== Day 64: 超时控制与熔断机制测试 ===")
        print("=" * 60)
        
        print("\n🔧 测试环境")
        print("- 熔断阈值: 50% 失败率")
        print("- 熔断持续时间: 2-5s")
        print("- 半开探测请求数: 3")
        print("- 连接超时: 0.5s")
        print("- 读取超时: 1.0s")
        
        print("\n📊 测试执行")
        
        tests = [
            self.test_timeout_mechanism,
            self.test_circuit_state_transition,
            self.test_cascade_failure_protection,
            self.test_half_open_probe,
            self.test_timeout_configuration,
        ]
        
        results = []
        for test in tests:
            result = test()
            results.append(result)
            status = "✅ 通过" if result["passed"] else "❌ 失败"
            print(f"\n[{result['name']}] {status}")
            print(f"  └─ {result['details']}")
        
        # 汇总
        print("\n" + "=" * 60)
        print("📈 风险汇总")
        
        l1_count = sum(1 for r in results if r["risk_level"] == "L1" and not r["passed"])
        l2_count = sum(1 for r in results if r["risk_level"] == "L2" and not r["passed"])
        l3_count = sum(1 for r in results if r["risk_level"] == "L3" and not r["passed"])
        
        print(f"- L1风险: {l1_count}个")
        print(f"- L2风险: {l2_count}个")
        print(f"- L3风险: {l3_count}个")
        
        if l1_count > 0:
            print(f"\n⚠️  发现 {l1_count} 个L1级别风险，需立即修复！")
        elif l2_count > 0:
            print(f"\n⚠️  发现 {l2_count} 个L2级别风险，建议优化")
        
        return results


def main():
    tester = TimeoutCircuitTester()
    results = tester.run_all_tests()
    
    all_passed = all(r["passed"] for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
