"""
Day 63: 连接池管理与资源竞争测试
目标：验证连接池在高并发场景下的行为，检测资源竞争和连接泄漏
"""

import threading
import time
import random
import queue
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set
from enum import Enum
import uuid


class ConnectionStatus(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass
class MockConnection:
    """模拟数据库连接"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: ConnectionStatus = ConnectionStatus.IDLE
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0
    
    def execute(self, query: str) -> tuple:
        """模拟执行查询"""
        if self.status == ConnectionStatus.CLOSED:
            return False, "连接已关闭"
        time.sleep(random.uniform(0.01, 0.05))  # 模拟查询耗时
        self.use_count += 1
        self.last_used = time.time()
        return True, f"查询执行成功: {query[:20]}..."
    
    def close(self):
        """关闭连接"""
        self.status = ConnectionStatus.CLOSED
    
    def is_valid(self, max_lifetime: float = 300) -> bool:
        """检查连接是否有效"""
        if self.status == ConnectionStatus.CLOSED:
            return False
        age = time.time() - self.created_at
        return age < max_lifetime


class ConnectionPool:
    """连接池实现 - 包含故意设计的缺陷用于测试"""
    
    def __init__(
        self,
        max_connections: int = 5,
        connection_timeout: float = 2.0,
        leak_simulation: bool = False  # 模拟连接泄漏
    ):
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.leak_simulation = leak_simulation
        
        self._pool: queue.Queue = queue.Queue()
        self._active_connections: Dict[str, MockConnection] = {}
        self._lock = threading.Lock()
        self._total_created = 0
        self._leaked_count = 0
        
        # 初始化最小连接
        for _ in range(max(2, max_connections // 2)):
            conn = MockConnection()
            self._pool.put(conn)
            self._total_created += 1
    
    def get_connection(self) -> Optional[MockConnection]:
        """获取连接 - 可能泄漏"""
        try:
            conn = self._pool.get(timeout=self.connection_timeout)
            if not conn.is_valid():
                conn = MockConnection()
                self._total_created += 1
            
            conn.status = ConnectionStatus.ACTIVE
            with self._lock:
                self._active_connections[conn.id] = conn
            
            return conn
        except queue.Empty:
            return None
    
    def release_connection(self, conn: MockConnection) -> bool:
        """归还连接 - 模拟泄漏"""
        if conn is None or conn.status == ConnectionStatus.CLOSED:
            return False
        
        # 模拟连接泄漏缺陷
        if self.leak_simulation and random.random() < 0.3:
            self._leaked_count += 1
            return False  # 故意不归还
        
        with self._lock:
            if conn.id in self._active_connections:
                del self._active_connections[conn.id]
        
        conn.status = ConnectionStatus.IDLE
        self._pool.put(conn)
        return True
    
    def get_stats(self) -> Dict:
        """获取连接池统计"""
        with self._lock:
            return {
                "total_created": self._total_created,
                "active": len(self._active_connections),
                "idle": self._pool.qsize(),
                "leaked": self._leaked_count,
                "available": self._pool.qsize() + len(self._active_connections)
            }
    
    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except queue.Empty:
                break
        with self._lock:
            for conn in self._active_connections.values():
                conn.close()
            self._active_connections.clear()


class ResourceCompetitionTester:
    """资源竞争测试器"""
    
    def __init__(self):
        self.results: List[Dict] = []
        self.lock = threading.Lock()
    
    def test_basic_pool_functionality(self) -> Dict:
        """测试连接池基础功能"""
        print("\n[连接池基础功能] 测试中...")
        
        pool = ConnectionPool(max_connections=3, leak_simulation=False)
        
        try:
            # 获取连接
            conn = pool.get_connection()
            assert conn is not None, "获取连接失败"
            
            # 执行查询
            success, msg = conn.execute("SELECT * FROM test")
            assert success, f"查询失败: {msg}"
            
            # 归还连接
            released = pool.release_connection(conn)
            assert released, "归还连接失败"
            
            stats = pool.get_stats()
            pool.close_all()
            
            return {
                "name": "连接池基础功能",
                "passed": True,
                "score": 1.0,
                "details": f"获取/执行/归还 均正常 | 统计: {stats}",
                "risk_level": "L3"
            }
        except Exception as e:
            pool.close_all()
            return {
                "name": "连接池基础功能",
                "passed": False,
                "score": 0.0,
                "details": f"异常: {str(e)}",
                "risk_level": "L1"
            }
    
    def test_concurrent_competition(self) -> Dict:
        """测试并发竞争"""
        print("\n[并发竞争测试] 测试中...")
        
        pool = ConnectionPool(max_connections=5, connection_timeout=1.5, leak_simulation=False)
        results = {"success": 0, "timeout": 0, "error": 0}
        
        def worker(worker_id: int):
            try:
                conn = pool.get_connection()
                if conn is None:
                    with self.lock:
                        results["timeout"] += 1
                    return
                
                # 模拟工作
                time.sleep(random.uniform(0.1, 0.3))
                conn.execute(f"Query from worker {worker_id}")
                pool.release_connection(conn)
                
                with self.lock:
                    results["success"] += 1
            except Exception as e:
                with self.lock:
                    results["error"] += 1
        
        # 启动20个并发线程
        threads = []
        for i in range(20):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=5)
        
        pool.close_all()
        
        # 评估结果
        passed = results["error"] == 0 and results["timeout"] > 0  # 应该有超时但无错误
        risk_level = "L2" if results["error"] > 0 else "L3"
        
        return {
            "name": "并发竞争测试",
            "passed": passed,
            "score": results["success"] / 20,
            "details": f"成功: {results['success']}/20, 超时: {results['timeout']}, 错误: {results['error']}",
            "risk_level": risk_level
        }
    
    def test_connection_leak(self) -> Dict:
        """测试连接泄漏检测"""
        print("\n[连接泄漏检测] 测试中...")
        
        pool = ConnectionPool(max_connections=5, leak_simulation=True)  # 启用泄漏模拟
        
        # 模拟多次获取不归还
        for _ in range(10):
            conn = pool.get_connection()
            if conn:
                # 30%概率泄漏
                pool.release_connection(conn)
            time.sleep(0.01)
        
        stats = pool.get_stats()
        pool.close_all()
        
        leak_rate = stats["leaked"] / stats["total_created"] if stats["total_created"] > 0 else 0
        
        # 泄漏率超过20%视为严重问题
        passed = leak_rate < 0.2
        risk_level = "L1" if leak_rate > 0.3 else "L2" if leak_rate > 0.1 else "L3"
        
        return {
            "name": "连接泄漏检测",
            "passed": passed,
            "score": 1.0 - leak_rate,
            "details": f"总创建: {stats['total_created']}, 泄漏: {stats['leaked']}, 泄漏率: {leak_rate:.1%}",
            "risk_level": risk_level
        }
    
    def test_deadlock_detection(self) -> Dict:
        """测试死锁检测"""
        print("\n[死锁检测] 测试中...")
        
        resource_a = threading.Lock()
        resource_b = threading.Lock()
        results = {"deadlock_detected": False, "completed": 0}
        
        def thread1():
            try:
                with resource_a:
                    time.sleep(0.01)
                    # 设置超时避免真正死锁
                    acquired = resource_b.acquire(timeout=1.0)
                    if acquired:
                        resource_b.release()
                results["completed"] += 1
            except:
                results["deadlock_detected"] = True
        
        def thread2():
            try:
                with resource_b:
                    time.sleep(0.01)
                    acquired = resource_a.acquire(timeout=1.0)
                    if acquired:
                        resource_a.release()
                results["completed"] += 1
            except:
                results["deadlock_detected"] = True
        
        t1 = threading.Thread(target=thread1)
        t2 = threading.Thread(target=thread2)
        
        t1.start()
        t2.start()
        
        t1.join(timeout=3)
        t2.join(timeout=3)
        
        # 如果都完成了，说明没有死锁（超时机制生效）
        passed = results["completed"] == 2
        
        return {
            "name": "死锁检测",
            "passed": passed,
            "score": 1.0 if passed else 0.0,
            "details": f"完成线程: {results['completed']}/2, 死锁检测: {'通过' if passed else '失败'}",
            "risk_level": "L1" if not passed else "L3"
        }
    
    def test_resource_limits(self) -> Dict:
        """测试资源上限"""
        print("\n[资源上限测试] 测试中...")
        
        pool = ConnectionPool(max_connections=10, leak_simulation=False)
        connections = []
        
        try:
            # 尝试获取超过最大连接数的连接
            for i in range(15):
                conn = pool.get_connection()
                if conn:
                    connections.append(conn)
            
            stats = pool.get_stats()
            
            # 验证连接数不超过上限
            within_limit = stats["active"] <= 10
            
            # 归还所有连接
            for conn in connections:
                pool.release_connection(conn)
            
            pool.close_all()
            
            return {
                "name": "资源上限测试",
                "passed": within_limit,
                "score": 1.0 if within_limit else 0.5,
                "details": f"最大活跃: {stats['active']}/10, 连接数限制: {'生效' if within_limit else '失效'}",
                "risk_level": "L2" if not within_limit else "L3"
            }
        except Exception as e:
            pool.close_all()
            return {
                "name": "资源上限测试",
                "passed": False,
                "score": 0.0,
                "details": f"异常: {str(e)}",
                "risk_level": "L1"
            }
    
    def run_all_tests(self) -> List[Dict]:
        """运行所有测试"""
        print("=" * 60)
        print("=== Day 63: 连接池管理与资源竞争测试 ===")
        print("=" * 60)
        
        print("\n🔧 测试环境")
        print("- 连接池大小: 5")
        print("- 并发线程数: 20")
        print("- 连接超时: 1.5s")
        
        print("\n📊 测试执行")
        
        tests = [
            self.test_basic_pool_functionality,
            self.test_concurrent_competition,
            self.test_connection_leak,
            self.test_deadlock_detection,
            self.test_resource_limits,
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
        
        return results


def main():
    tester = ResourceCompetitionTester()
    results = tester.run_all_tests()
    
    # 返回整体通过状态
    all_passed = all(r["passed"] for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
