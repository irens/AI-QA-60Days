"""
综合测试套件 - 整合Day 63-65所有测试场景
"""

import threading
import time
import random
import statistics
from typing import List, Dict
from dataclasses import dataclass

from ai_service import AIService, LoadBalancer, ServiceConfig


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    details: str
    risk_level: str
    metrics: Dict = None


class ComprehensiveTester:
    """综合测试器"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.lb = LoadBalancer(algorithm="round_robin")
        
        # 创建服务实例
        for i in range(2):
            config = ServiceConfig(
                pool_size=5,
                connection_timeout=1.0,
                read_timeout=2.0,
                failure_threshold=0.5,
                open_duration=3.0
            )
            service = AIService(config, service_id=f"service_{i+1}")
            self.lb.add_service(service)
    
    def test_connection_pool_exhaustion(self) -> TestResult:
        """测试连接池耗尽场景"""
        print("\n[测试1] 连接池耗尽恢复测试")
        
        config = ServiceConfig(pool_size=3, connection_timeout=0.5)
        service = AIService(config, service_id="pool_test")
        
        results = []
        
        def worker(i):
            r = service.query(f"问题{i}", user_id=f"user_{i}")
            results.append(r)
        
        threads = []
        for i in range(20):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        timeout_count = sum(1 for r in results if "超时" in r.get("response", ""))
        success_count = sum(1 for r in results if r["success"])
        
        passed = success_count > 0 and timeout_count > 0
        
        return TestResult(
            name="连接池耗尽恢复",
            passed=passed,
            score=success_count / len(results),
            details=f"成功: {success_count}/20, 超时: {timeout_count}/20",
            risk_level="L2" if not passed else "L3",
            metrics={"success": success_count, "timeout": timeout_count}
        )
    
    def test_circuit_breaker_protection(self) -> TestResult:
        """测试熔断器保护"""
        print("\n[测试2] 熔断器保护测试")
        
        config = ServiceConfig(
            pool_size=10,
            failure_threshold=0.5,
            min_calls=5,
            open_duration=2.0
        )
        service = AIService(config, service_id="circuit_test")
        
        results = []
        for i in range(30):
            if random.random() < 0.7:
                config.read_timeout = 0.001
            else:
                config.read_timeout = 5.0
            
            r = service.query(f"问题{i}", user_id=f"user_{i}")
            results.append(r)
            time.sleep(0.05)
        
        stats = service.get_stats()
        fallback_count = stats.get("fallback_requests", 0)
        breaker_state = stats.get("breaker_state", "unknown")
        
        passed = fallback_count > 0 or breaker_state == "open"
        
        return TestResult(
            name="熔断器保护",
            passed=passed,
            score=1.0 if passed else 0.0,
            details=f"熔断状态: {breaker_state}, 降级请求: {fallback_count}",
            risk_level="L1" if not passed else "L3",
            metrics={"fallback": fallback_count, "state": breaker_state}
        )
    
    def test_load_balancing(self) -> TestResult:
        """测试负载均衡"""
        print("\n[测试3] 负载均衡测试")
        
        service_calls = {"service_1": 0, "service_2": 0}
        
        for i in range(20):
            service = self.lb.get_service()
            if service:
                r = service.query(f"问题{i}", user_id=f"user_{i}")
                service_calls[service.service_id] = service_calls.get(service.service_id, 0) + 1
        
        total = sum(service_calls.values())
        if total == 0:
            passed = False
            balance_ratio = 0
        else:
            ratio = abs(service_calls["service_1"] - service_calls["service_2"]) / total
            passed = ratio < 0.5
            balance_ratio = 1 - ratio
        
        return TestResult(
            name="负载均衡",
            passed=passed,
            score=balance_ratio,
            details=f"Service1: {service_calls['service_1']}, Service2: {service_calls['service_2']}",
            risk_level="L2" if not passed else "L3",
            metrics=service_calls
        )
    
    def test_concurrent_stress(self) -> TestResult:
        """并发压力测试"""
        print("\n[测试4] 并发压力测试")
        
        all_results = []
        response_times = []
        
        def worker(i):
            start = time.time()
            service = self.lb.get_service()
            if service:
                r = service.query(f"压力测试问题{i}", user_id=f"user_{i}")
                all_results.append(r)
                response_times.append((time.time() - start) * 1000)
        
        threads = []
        for i in range(50):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        success_count = sum(1 for r in all_results if r["success"])
        error_rate = 1 - (success_count / len(all_results)) if all_results else 1
        
        if response_times:
            avg_time = statistics.mean(response_times)
            p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
        else:
            avg_time = 0
            p95_time = 0
        
        passed = error_rate < 0.1 and p95_time < 5000
        
        return TestResult(
            name="并发压力测试",
            passed=passed,
            score=1.0 - error_rate,
            details=f"成功率: {success_count}/{len(all_results)}, P95延迟: {p95_time:.0f}ms",
            risk_level="L1" if error_rate > 0.2 else "L2" if error_rate > 0.05 else "L3",
            metrics={
                "total": len(all_results),
                "success": success_count,
                "error_rate": error_rate,
                "avg_time": avg_time,
                "p95_time": p95_time
            }
        )
    
    def test_stability(self) -> TestResult:
        """稳定性测试"""
        print("\n[测试5] 稳定性测试")
        
        service = self.lb.get_service()
        if not service:
            return TestResult(
                name="稳定性测试",
                passed=False,
                score=0,
                details="无可用服务",
                risk_level="L1"
            )
        
        initial_stats = service.get_stats()
        
        for i in range(50):
            service.query(f"稳定性测试{i}", user_id=f"user_{i}")
            time.sleep(0.05)
        
        final_stats = service.get_stats()
        
        initial_leaked = initial_stats.get("pool", {}).get("leaked", 0)
        final_leaked = final_stats.get("pool", {}).get("leaked", 0)
        
        no_leak = final_leaked == initial_leaked
        
        return TestResult(
            name="稳定性测试",
            passed=no_leak,
            score=1.0 if no_leak else 0.5,
            details=f"连接泄漏: {final_leaked} (初始: {initial_leaked})",
            risk_level="L2" if not no_leak else "L3",
            metrics={"initial_leaked": initial_leaked, "final_leaked": final_leaked}
        )
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("=== Day 63-65 综合实战测试 ===")
        print("=" * 60)
        
        tests = [
            self.test_connection_pool_exhaustion,
            self.test_circuit_breaker_protection,
            self.test_load_balancing,
            self.test_concurrent_stress,
            self.test_stability,
        ]
        
        results = []
        for test in tests:
            result = test()
            results.append(result)
            status = "✅ 通过" if result.passed else "❌ 失败"
            print(f"\n[{result.name}] {status}")
            print(f"  └─ {result.details}")
        
        print("\n" + "=" * 60)
        print("📊 测试汇总")
        
        passed_count = sum(1 for r in results if r.passed)
        total_count = len(results)
        
        l1_count = sum(1 for r in results if r.risk_level == "L1" and not r.passed)
        l2_count = sum(1 for r in results if r.risk_level == "L2" and not r.passed)
        
        print(f"通过: {passed_count}/{total_count}")
        print(f"L1风险: {l1_count}个")
        print(f"L2风险: {l2_count}个")
        
        if l1_count > 0:
            print("\n⚠️ 发现L1级别风险，需立即修复！")
        elif l2_count > 0:
            print("\n⚠️ 发现L2级别风险，建议优化")
        else:
            print("\n✅ 所有测试通过！")
        
        return results


def main():
    tester = ComprehensiveTester()
    results = tester.run_all_tests()
    
    all_passed = all(r.passed for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
