"""
Day 65: 负载测试与容量规划
目标：通过负载测试找到系统性能拐点，为容量规划提供数据支撑
"""

import threading
import time
import random
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from collections import deque


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: float
    response_time_ms: float
    success: bool
    concurrent_users: int


@dataclass
class LoadTestResult:
    """负载测试结果"""
    concurrent_users: int
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    tps: float
    avg_response_ms: float
    p50_response_ms: float
    p95_response_ms: float
    p99_response_ms: float
    error_rate: float
    cpu_usage: float  # 模拟
    memory_usage: float  # 模拟


class MockService:
    """模拟服务 - 具有性能瓶颈特征"""
    
    def __init__(self, base_latency_ms: float = 20):
        self.base_latency_ms = base_latency_ms
        self.active_requests = 0
        self.max_capacity = 100  # 最大容量
        self._lock = threading.Lock()
    
    def process(self, user_id: int) -> tuple:
        """处理请求 - 模拟性能衰减"""
        with self._lock:
            self.active_requests += 1
            current_load = self.active_requests
        
        try:
            # 基础延迟
            latency = self.base_latency_ms
            
            # 负载越高，延迟越大（模拟性能衰减）
            if current_load > 50:
                latency += (current_load - 50) * 2
            
            # 超过容量时可能失败
            if current_load > self.max_capacity:
                if random.random() < 0.3:
                    return False, "服务过载"
            
            # 模拟处理时间
            actual_delay = latency * random.uniform(0.8, 1.2) / 1000
            time.sleep(actual_delay)
            
            return True, f"User{user_id} processed"
        finally:
            with self._lock:
                self.active_requests -= 1
    
    def get_load(self) -> int:
        """获取当前负载"""
        with self._lock:
            return self.active_requests


class LoadTester:
    """负载测试器"""
    
    def __init__(self):
        self.service = MockService(base_latency_ms=20)
        self.results: List[LoadTestResult] = []
    
    def run_benchmark(self, duration: float = 5.0) -> LoadTestResult:
        """基准测试 - 单用户"""
        print("\n[基准测试] 执行中...")
        
        metrics: List[PerformanceMetrics] = []
        start_time = time.time()
        request_count = 0
        success_count = 0
        
        while time.time() - start_time < duration:
            req_start = time.time()
            success, _ = self.service.process(0)
            response_time = (time.time() - req_start) * 1000
            
            metrics.append(PerformanceMetrics(
                timestamp=req_start,
                response_time_ms=response_time,
                success=success,
                concurrent_users=1
            ))
            
            request_count += 1
            if success:
                success_count += 1
        
        return self._calculate_result(1, duration, metrics)
    
    def run_load_test(self, concurrent_users: int, duration: float = 10.0) -> LoadTestResult:
        """负载测试"""
        print(f"\n[负载测试 - {concurrent_users}并发] 执行中...")
        
        metrics: List[PerformanceMetrics] = []
        stop_event = threading.Event()
        metrics_lock = threading.Lock()
        
        def user_worker(user_id: int):
            while not stop_event.is_set():
                req_start = time.time()
                success, _ = self.service.process(user_id)
                response_time = (time.time() - req_start) * 1000
                
                with metrics_lock:
                    metrics.append(PerformanceMetrics(
                        timestamp=req_start,
                        response_time_ms=response_time,
                        success=success,
                        concurrent_users=concurrent_users
                    ))
                
                # 模拟用户思考时间
                time.sleep(random.uniform(0.05, 0.15))
        
        # 启动并发用户
        threads = []
        for i in range(concurrent_users):
            t = threading.Thread(target=user_worker, args=(i,))
            t.daemon = True
            t.start()
            threads.append(t)
        
        # 运行指定时间
        time.sleep(duration)
        stop_event.set()
        
        # 等待线程结束
        for t in threads:
            t.join(timeout=2)
        
        return self._calculate_result(concurrent_users, duration, metrics)
    
    def run_stress_test(self, max_users: int = 150, step: int = 20) -> Dict:
        """压力测试 - 找到性能拐点"""
        print("\n[压力测试 - 找拐点] 执行中...")
        
        results = []
        inflection_point = None
        breaking_point = None
        
        for users in range(10, max_users + 1, step):
            result = self.run_load_test(users, duration=5.0)
            results.append(result)
            
            # 检测性能拐点（P95延迟突增）
            if inflection_point is None and result.p95_response_ms > 200:
                inflection_point = users
            
            # 检测崩溃点（错误率>5%）
            if breaking_point is None and result.error_rate > 0.05:
                breaking_point = users
                break
        
        return {
            "results": results,
            "inflection_point": inflection_point or max_users,
            "breaking_point": breaking_point or max_users,
            "max_tps": max(r.tps for r in results)
        }
    
    def run_soak_test(self, duration: float = 30.0, concurrent_users: int = 50) -> Dict:
        """稳定性测试"""
        print(f"\n[稳定性测试 - {duration}s] 执行中...")
        
        result = self.run_load_test(concurrent_users, duration)
        
        # 模拟内存使用增长检测
        memory_growth = random.uniform(0, 5)  # MB
        has_memory_leak = memory_growth > 3
        
        # 检测响应时间稳定性
        response_variance = result.p99_response_ms - result.p50_response_ms
        is_stable = response_variance < 200
        
        return {
            "result": result,
            "memory_growth_mb": memory_growth,
            "has_memory_leak": has_memory_leak,
            "response_stable": is_stable
        }
    
    def _calculate_result(
        self,
        concurrent_users: int,
        duration: float,
        metrics: List[PerformanceMetrics]
    ) -> LoadTestResult:
        """计算测试结果"""
        if not metrics:
            return LoadTestResult(
                concurrent_users=concurrent_users,
                duration_seconds=duration,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                tps=0,
                avg_response_ms=0,
                p50_response_ms=0,
                p95_response_ms=0,
                p99_response_ms=0,
                error_rate=0,
                cpu_usage=0,
                memory_usage=0
            )
        
        response_times = [m.response_time_ms for m in metrics]
        success_count = sum(1 for m in metrics if m.success)
        total = len(metrics)
        
        # 计算百分位数
        sorted_times = sorted(response_times)
        p50 = sorted_times[int(len(sorted_times) * 0.5)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        
        # 模拟系统资源使用
        cpu_usage = min(95, concurrent_users * 0.8 + random.uniform(-5, 5))
        memory_usage = min(90, 30 + concurrent_users * 0.3 + random.uniform(-2, 2))
        
        return LoadTestResult(
            concurrent_users=concurrent_users,
            duration_seconds=duration,
            total_requests=total,
            successful_requests=success_count,
            failed_requests=total - success_count,
            tps=total / duration,
            avg_response_ms=statistics.mean(response_times),
            p50_response_ms=p50,
            p95_response_ms=p95,
            p99_response_ms=p99,
            error_rate=(total - success_count) / total if total > 0 else 0,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage
        )
    
    def generate_capacity_plan(self, results: List[LoadTestResult]) -> Dict:
        """生成容量规划建议"""
        # 找到性能拐点
        inflection = None
        for r in results:
            if r.p95_response_ms > 200 or r.cpu_usage > 70:
                inflection = r.concurrent_users
                break
        
        if inflection is None:
            inflection = max(r.concurrent_users for r in results)
        
        # 建议扩容点（75%阈值）
        scale_up_threshold = int(inflection * 0.75)
        
        # 安全边际
        safety_margin = 1.5
        
        # 预估日请求量
        max_tps = max(r.tps for r in results)
        daily_requests = int(max_tps * 3600 * 24 * 0.3)  # 假设30%峰值时间
        
        return {
            "current_capacity_users": inflection,
            "scale_up_threshold": scale_up_threshold,
            "safety_margin": safety_margin,
            "recommended_capacity": int(inflection * safety_margin),
            "estimated_daily_requests": daily_requests,
            "max_tps": max_tps
        }
    
    def run_all_tests(self) -> List[Dict]:
        """运行所有测试"""
        print("=" * 60)
        print("=== Day 65: 负载测试与容量规划 ===")
        print("=" * 60)
        
        print("\n🔧 测试环境")
        print("- 模拟并发用户: 10-150")
        print("- 测试持续时间: 5-30s/阶段")
        print("- 目标TPS: 500")
        print("- 目标P95延迟: <200ms")
        
        print("\n📊 测试执行")
        
        results = []
        
        # 1. 基准测试
        benchmark = self.run_benchmark(duration=5.0)
        benchmark_passed = benchmark.tps > 0
        results.append({
            "name": "基准测试",
            "passed": benchmark_passed,
            "score": 1.0 if benchmark_passed else 0.0,
            "details": f"单用户TPS: {benchmark.tps:.1f}, P95: {benchmark.p95_response_ms:.0f}ms",
            "risk_level": "L3",
            "data": benchmark
        })
        
        # 2. 负载测试 - 50并发
        load_50 = self.run_load_test(50, duration=8.0)
        load_50_passed = load_50.p95_response_ms < 200 and load_50.error_rate < 0.01
        results.append({
            "name": "负载测试-50并发",
            "passed": load_50_passed,
            "score": 1.0 if load_50_passed else 0.5,
            "details": f"TPS: {load_50.tps:.0f}, P95: {load_50.p95_response_ms:.0f}ms, 错误率: {load_50.error_rate:.1%}",
            "risk_level": "L2" if not load_50_passed else "L3",
            "data": load_50
        })
        
        # 3. 负载测试 - 100并发
        load_100 = self.run_load_test(100, duration=8.0)
        load_100_passed = load_100.p95_response_ms < 300  # 放宽要求
        results.append({
            "name": "负载测试-100并发",
            "passed": load_100_passed,
            "score": 1.0 if load_100_passed else 0.5,
            "details": f"TPS: {load_100.tps:.0f}, P95: {load_100.p95_response_ms:.0f}ms, CPU: {load_100.cpu_usage:.0f}%",
            "risk_level": "L2" if not load_100_passed else "L3",
            "data": load_100
        })
        
        # 4. 压力测试
        stress_result = self.run_stress_test(max_users=150, step=25)
        stress_passed = stress_result["inflection_point"] >= 50
        results.append({
            "name": "压力测试-找拐点",
            "passed": stress_passed,
            "score": 1.0 if stress_passed else 0.0,
            "details": f"性能拐点: {stress_result['inflection_point']}并发, 最大TPS: {stress_result['max_tps']:.0f}",
            "risk_level": "L1" if not stress_passed else "L3",
            "data": stress_result
        })
        
        # 5. 稳定性测试
        soak_result = self.run_soak_test(duration=15.0, concurrent_users=60)
        soak_passed = not soak_result["has_memory_leak"] and soak_result["response_stable"]
        results.append({
            "name": "稳定性测试",
            "passed": soak_passed,
            "score": 1.0 if soak_passed else 0.5,
            "details": f"内存增长: {soak_result['memory_growth_mb']:.1f}MB, 响应稳定: {soak_result['response_stable']}",
            "risk_level": "L2" if not soak_passed else "L3",
            "data": soak_result
        })
        
        # 打印详细结果
        for r in results:
            status = "✅ 通过" if r["passed"] else "❌ 失败"
            print(f"\n[{r['name']}] {status}")
            print(f"  └─ {r['details']}")
        
        # 容量规划建议
        print("\n" + "-" * 40)
        print("[容量规划建议]")
        
        all_load_results = [r["data"] for r in results if "data" in r and isinstance(r["data"], LoadTestResult)]
        if all_load_results:
            plan = self.generate_capacity_plan(all_load_results)
            print(f"  ├─ 当前容量: {plan['current_capacity_users']}并发用户")
            print(f"  ├─ 建议扩容点: {plan['scale_up_threshold']}并发 (75%阈值)")
            print(f"  ├─ 安全边际: {plan['safety_margin']}倍")
            print(f"  ├─ 推荐容量: {plan['recommended_capacity']}并发")
            print(f"  └─ 预估支撑: 日均{plan['estimated_daily_requests']//10000}万请求")
        
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
        else:
            print("\n✅ 所有测试通过，系统容量规划合理")
        
        return results


def main():
    tester = LoadTester()
    results = tester.run_all_tests()
    
    all_passed = all(r["passed"] for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
