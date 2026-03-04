"""
AI服务核心实现 - 整合连接池、熔断器、超时控制
"""

import threading
import time
import random
import queue
from typing import Optional, Dict, List, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ServiceConfig:
    """服务配置"""
    # 连接池配置
    pool_size: int = 10
    connection_timeout: float = 2.0
    
    # 熔断器配置
    failure_threshold: float = 0.5
    min_calls: int = 10
    open_duration: float = 5.0
    
    # 超时配置
    connect_timeout: float = 1.0
    read_timeout: float = 3.0
    total_timeout: float = 10.0
    
    # 降级配置
    enable_fallback: bool = True
    fallback_response: str = "服务繁忙，请稍后重试"


class MockConnection:
    """模拟LLM连接"""
    
    def __init__(self, conn_id: str):
        self.id = conn_id
        self.created_at = time.time()
        self.last_used = time.time()
        self.use_count = 0
        self.is_active = True
    
    def query(self, prompt: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """模拟LLM查询"""
        if not self.is_active:
            return False, "连接已关闭"
        
        # 模拟处理时间
        process_time = random.uniform(0.5, 2.0)
        if process_time > timeout:
            return False, "查询超时"
        
        time.sleep(process_time)
        self.use_count += 1
        self.last_used = time.time()
        
        return True, f"AI回答: {prompt[:20]}..."
    
    def close(self):
        self.is_active = False


class ConnectionPool:
    """连接池 - 线程安全实现"""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self._pool: queue.Queue = queue.Queue()
        self._active: Dict[str, MockConnection] = {}
        self._lock = threading.Lock()
        self._stats = {"created": 0, "leased": 0, "released": 0, "leaked": 0}
        
        # 初始化连接
        for i in range(config.pool_size):
            conn = MockConnection(f"conn_{i}")
            self._pool.put(conn)
            self._stats["created"] += 1
    
    def acquire(self) -> Optional[MockConnection]:
        """获取连接"""
        try:
            conn = self._pool.get(timeout=self.config.connection_timeout)
            with self._lock:
                self._active[conn.id] = conn
                self._stats["leased"] += 1
            return conn
        except queue.Empty:
            return None
    
    def release(self, conn: MockConnection) -> bool:
        """归还连接"""
        if conn is None:
            return False
        
        with self._lock:
            if conn.id in self._active:
                del self._active[conn.id]
                self._stats["released"] += 1
        
        if conn.is_active:
            self._pool.put(conn)
            return True
        return False
    
    def get_stats(self) -> Dict:
        with self._lock:
            return {
                **self._stats,
                "active": len(self._active),
                "idle": self._pool.qsize(),
                "leak_rate": (self._stats["leased"] - self._stats["released"]) / max(self._stats["leased"], 1)
            }


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, config: ServiceConfig, name: str = "default"):
        self.config = config
        self.name = name
        self.state = CircuitState.CLOSED
        
        self._total = 0
        self._failed = 0
        self._consecutive_success = 0
        self._last_failure_time = 0
        self._half_open_calls = 0
        
        self._lock = threading.Lock()
    
    def can_execute(self) -> bool:
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self.config.open_duration:
                    self.state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._consecutive_success = 0
                    return True
                return False
            elif self.state == CircuitState.HALF_OPEN:
                if self._half_open_calls < 3:
                    self._half_open_calls += 1
                    return True
                return False
        return False
    
    def record_success(self):
        with self._lock:
            self._total += 1
            self._consecutive_success += 1
            
            if self.state == CircuitState.HALF_OPEN:
                if self._consecutive_success >= 2:
                    self.state = CircuitState.CLOSED
                    self._reset()
    
    def record_failure(self):
        with self._lock:
            self._total += 1
            self._failed += 1
            self._consecutive_success = 0
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self._last_failure_time = time.time()
            elif self.state == CircuitState.CLOSED:
                if self._total >= self.config.min_calls:
                    failure_rate = self._failed / self._total
                    if failure_rate >= self.config.failure_threshold:
                        self.state = CircuitState.OPEN
                        self._last_failure_time = time.time()
    
    def _reset(self):
        self._total = 0
        self._failed = 0
        self._consecutive_success = 0
        self._half_open_calls = 0
    
    def get_state(self) -> CircuitState:
        with self._lock:
            return self.state


class AIService:
    """AI服务 - 整合所有稳定性机制"""
    
    def __init__(self, config: ServiceConfig = None, service_id: str = None):
        self.config = config or ServiceConfig()
        self.service_id = service_id or str(uuid.uuid4())[:8]
        
        self.pool = ConnectionPool(self.config)
        self.breaker = CircuitBreaker(self.config, name=f"ai_service_{self.service_id}")
        
        # 统计
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "fallback_requests": 0,
            "timeout_requests": 0
        }
        self._stats_lock = threading.Lock()
    
    def query(self, prompt: str, user_id: str = "anonymous") -> Dict:
        """处理AI查询请求"""
        start_time = time.time()
        
        with self._stats_lock:
            self._stats["total_requests"] += 1
        
        # 1. 检查熔断器
        if not self.breaker.can_execute():
            with self._stats_lock:
                self._stats["fallback_requests"] += 1
            return {
                "success": False,
                "response": self.config.fallback_response if self.config.enable_fallback else "服务熔断",
                "fallback": True,
                "service_id": self.service_id,
                "time_ms": (time.time() - start_time) * 1000
            }
        
        # 2. 获取连接
        conn = self.pool.acquire()
        if conn is None:
            self.breaker.record_failure()
            with self._stats_lock:
                self._stats["timeout_requests"] += 1
            return {
                "success": False,
                "response": "获取连接超时",
                "service_id": self.service_id,
                "time_ms": (time.time() - start_time) * 1000
            }
        
        try:
            # 3. 执行查询
            success, response = conn.query(prompt, timeout=self.config.read_timeout)
            
            if success:
                self.breaker.record_success()
                with self._stats_lock:
                    self._stats["successful_requests"] += 1
                return {
                    "success": True,
                    "response": response,
                    "service_id": self.service_id,
                    "time_ms": (time.time() - start_time) * 1000
                }
            else:
                self.breaker.record_failure()
                with self._stats_lock:
                    self._stats["failed_requests"] += 1
                return {
                    "success": False,
                    "response": response,
                    "service_id": self.service_id,
                    "time_ms": (time.time() - start_time) * 1000
                }
        finally:
            self.pool.release(conn)
    
    def get_stats(self) -> Dict:
        """获取服务统计"""
        with self._stats_lock:
            stats = self._stats.copy()
        
        pool_stats = self.pool.get_stats()
        
        return {
            **stats,
            "pool": pool_stats,
            "breaker_state": self.breaker.get_state().value,
            "error_rate": stats["failed_requests"] / max(stats["total_requests"], 1)
        }


class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self, algorithm: str = "round_robin"):
        self.algorithm = algorithm
        self.services: List[AIService] = []
        self.healthy_services: set = set()
        self._index = 0
        self._lock = threading.Lock()
        
        # 健康检查
        self._health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_check_thread.start()
    
    def add_service(self, service: AIService):
        """添加服务实例"""
        with self._lock:
            self.services.append(service)
            self.healthy_services.add(service.service_id)
    
    def get_service(self) -> Optional[AIService]:
        """获取可用服务"""
        with self._lock:
            healthy = [s for s in self.services if s.service_id in self.healthy_services]
            
            if not healthy:
                return None
            
            if self.algorithm == "round_robin":
                service = healthy[self._index % len(healthy)]
                self._index += 1
                return service
            elif self.algorithm == "random":
                return random.choice(healthy)
            elif self.algorithm == "least_connections":
                return min(healthy, key=lambda s: s.pool.get_stats()["active"])
            
            return healthy[0]
    
    def _health_check_loop(self):
        """健康检查循环"""
        while True:
            time.sleep(5)
            self._check_health()
    
    def _check_health(self):
        """检查服务健康状态"""
        with self._lock:
            for service in self.services:
                stats = service.get_stats()
                error_rate = stats.get("error_rate", 0)
                
                if error_rate > 0.5:
                    self.healthy_services.discard(service.service_id)
                else:
                    self.healthy_services.add(service.service_id)
    
    def get_stats(self) -> Dict:
        """获取负载均衡器统计"""
        with self._lock:
            return {
                "total_services": len(self.services),
                "healthy_services": len(self.healthy_services),
                "algorithm": self.algorithm
            }


def main():
    """测试AI服务"""
    print("=" * 60)
    print("=== AI服务稳定性测试 ===")
    print("=" * 60)
    
    # 创建服务配置
    config = ServiceConfig(
        pool_size=5,
        connection_timeout=1.0,
        failure_threshold=0.5,
        open_duration=3.0
    )
    
    # 创建服务实例
    service = AIService(config, service_id="test_01")
    
    print("\n📊 单请求测试")
    result = service.query("什么是机器学习？", user_id="user_1")
    print(f"  结果: {result}")
    
    print("\n📊 并发测试")
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
    
    success_count = sum(1 for r in results if r["success"])
    fallback_count = sum(1 for r in results if r.get("fallback", False))
    
    print(f"  总请求: {len(results)}")
    print(f"  成功: {success_count}")
    print(f"  降级: {fallback_count}")
    
    print("\n📊 服务统计")
    stats = service.get_stats()
    print(f"  {stats}")
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    main()
