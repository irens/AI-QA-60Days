"""
Day 66: 记忆模块持久化测试
目标：验证长期记忆存储的可靠性、数据持久化能力、存储性能
测试架构师视角：模拟各种存储故障场景，验证记忆数据的完整性和可恢复性
"""

import json
import time
import random
import hashlib
import os
import tempfile
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
from enum import Enum


class StorageType(Enum):
    """存储类型"""
    MEMORY = "memory"      # 内存存储（易失性）
    FILE = "file"          # 文件存储
    DATABASE = "database"  # 数据库存储
    CACHE = "cache"        # 缓存存储


class MemoryLevel(Enum):
    """记忆级别"""
    SHORT_TERM = "short_term"    # 短期记忆
    LONG_TERM = "long_term"      # 长期记忆
    EPISODIC = "episodic"        # 情景记忆
    SEMANTIC = "semantic"        # 语义记忆


@dataclass
class TestCase:
    """测试用例定义"""
    name: str
    category: str
    input_data: Dict
    expected_behavior: str
    risk_level: str


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    details: str
    risk_level: str
    metrics: Dict[str, Any] = None


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    user_id: str
    content: str
    memory_type: str
    level: MemoryLevel
    timestamp: datetime
    importance: float  # 0.0 - 1.0
    access_count: int
    last_accessed: datetime
    metadata: Dict[str, Any]
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._calculate_checksum()

    def _calculate_checksum(self) -> str:
        """计算内容校验和"""
        data = f"{self.id}:{self.user_id}:{self.content}:{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def verify_integrity(self) -> bool:
        """验证数据完整性"""
        return self.checksum == self._calculate_checksum()


# ==================== 测试用例库 ====================

TEST_CASES = [
    # L1 阻断性风险测试
    TestCase(
        name="存储故障恢复测试",
        category="故障恢复",
        input_data={"scenario": "storage_failure", "fail_type": "disk_full"},
        expected_behavior="自动切换到备用存储，数据不丢失",
        risk_level="L1"
    ),
    TestCase(
        name="数据持久化验证",
        category="持久化",
        input_data={"scenario": "persistence", "data_count": 1000},
        expected_behavior="所有数据成功持久化，重启后可恢复",
        risk_level="L1"
    ),
    TestCase(
        name="并发写入一致性",
        category="并发控制",
        input_data={"scenario": "concurrent_write", "threads": 10, "ops_per_thread": 100},
        expected_behavior="无数据竞争，最终一致性",
        risk_level="L1"
    ),

    # L2 高优先级风险测试
    TestCase(
        name="存储性能基准测试",
        category="性能测试",
        input_data={"scenario": "performance", "target_qps": 1000, "max_latency_ms": 100},
        expected_behavior="QPS达标，延迟在阈值内",
        risk_level="L2"
    ),
    TestCase(
        name="大数据量存储测试",
        category="容量测试",
        input_data={"scenario": "large_data", "entry_count": 100000},
        expected_behavior="存储稳定，查询性能不下降超过20%",
        risk_level="L2"
    ),
    TestCase(
        name="数据压缩与解压",
        category="存储优化",
        input_data={"scenario": "compression", "compression_ratio": 0.5},
        expected_behavior="压缩率达标，解压无数据损坏",
        risk_level="L2"
    ),

    # L3 一般风险测试
    TestCase(
        name="存储配额管理",
        category="资源管理",
        input_data={"scenario": "quota", "max_size_mb": 100},
        expected_behavior="超出配额时优雅处理，优先保留重要数据",
        risk_level="L3"
    ),
    TestCase(
        name="过期数据清理",
        category="数据生命周期",
        input_data={"scenario": "ttl_cleanup", "ttl_hours": 24},
        expected_behavior="过期数据自动清理，活跃数据保留",
        risk_level="L3"
    ),
    TestCase(
        name="存储格式兼容性",
        category="兼容性",
        input_data={"scenario": "format_compat", "versions": ["v1", "v2", "v3"]},
        expected_behavior="新旧版本数据格式兼容",
        risk_level="L3"
    ),
]


# ==================== 模拟记忆存储系统 ====================

class MockMemoryStorage:
    """模拟记忆存储系统"""

    def __init__(self, failure_rate: float = 0.0, storage_type: StorageType = StorageType.FILE):
        self.failure_rate = failure_rate
        self.storage_type = storage_type
        self.memory_store: Dict[str, MemoryEntry] = {}
        self.file_store: Dict[str, str] = {}
        self.db_store: Dict[str, Dict] = {}
        self.cache_store: Dict[str, MemoryEntry] = {}
        self.temp_dir = tempfile.mkdtemp()
        self.storage_size_mb = 0.0
        self.max_size_mb = 1000.0
        self.write_count = 0
        self.read_count = 0
        self.failed_operations = 0
        self.latencies: List[float] = []
        self.is_available = True
        self.backup_storage = None

    def set_backup_storage(self, backup: 'MockMemoryStorage'):
        """设置备用存储"""
        self.backup_storage = backup

    def _simulate_failure(self) -> Tuple[bool, str]:
        """模拟故障"""
        if not self.is_available:
            return False, "存储服务不可用"
        if random.random() < self.failure_rate:
            self.failed_operations += 1
            return False, "模拟存储故障"
        return True, ""

    def _record_latency(self, start_time: float):
        """记录延迟"""
        latency = (time.time() - start_time) * 1000  # ms
        self.latencies.append(latency)

    def _entry_to_dict(self, entry: MemoryEntry) -> Dict:
        """将MemoryEntry转换为可序列化的字典"""
        return {
            "id": entry.id,
            "user_id": entry.user_id,
            "content": entry.content,
            "memory_type": entry.memory_type,
            "level": entry.level.value,  # 枚举转字符串
            "timestamp": entry.timestamp.isoformat() if isinstance(entry.timestamp, datetime) else entry.timestamp,
            "importance": entry.importance,
            "access_count": entry.access_count,
            "last_accessed": entry.last_accessed.isoformat() if isinstance(entry.last_accessed, datetime) else entry.last_accessed,
            "metadata": entry.metadata,
            "checksum": entry.checksum
        }

    def store(self, entry: MemoryEntry) -> Tuple[bool, str]:
        """存储记忆条目"""
        start_time = time.time()

        # 检查存储容量
        entry_dict = self._entry_to_dict(entry)
        entry_size = len(json.dumps(entry_dict)) / (1024 * 1024)  # MB
        if self.storage_size_mb + entry_size > self.max_size_mb:
            if self.backup_storage:
                return self.backup_storage.store(entry)
            return False, "存储空间不足"

        # 模拟故障
        success, error = self._simulate_failure()
        if not success:
            if self.backup_storage:
                return self.backup_storage.store(entry)
            return False, error

        # 根据存储类型存储
        if self.storage_type == StorageType.MEMORY:
            self.memory_store[entry.id] = entry
        elif self.storage_type == StorageType.FILE:
            self.file_store[entry.id] = json.dumps(entry_dict)
        elif self.storage_type == StorageType.DATABASE:
            self.db_store[entry.id] = entry_dict
        elif self.storage_type == StorageType.CACHE:
            self.cache_store[entry.id] = entry

        self.storage_size_mb += entry_size
        self.write_count += 1
        self._record_latency(start_time)
        return True, "存储成功"

    def _dict_to_entry(self, entry_dict: Dict) -> MemoryEntry:
        """将字典转换为MemoryEntry"""
        # 处理level字段，从字符串转回枚举
        level_value = entry_dict.get("level", "short_term")
        if isinstance(level_value, str):
            level = MemoryLevel(level_value)
        else:
            level = level_value

        # 处理时间字段
        timestamp = entry_dict.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        last_accessed = entry_dict.get("last_accessed")
        if isinstance(last_accessed, str):
            last_accessed = datetime.fromisoformat(last_accessed)

        return MemoryEntry(
            id=entry_dict["id"],
            user_id=entry_dict["user_id"],
            content=entry_dict["content"],
            memory_type=entry_dict["memory_type"],
            level=level,
            timestamp=timestamp,
            importance=entry_dict["importance"],
            access_count=entry_dict["access_count"],
            last_accessed=last_accessed,
            metadata=entry_dict["metadata"],
            checksum=entry_dict.get("checksum", "")
        )

    def retrieve(self, entry_id: str) -> Tuple[Optional[MemoryEntry], str]:
        """检索记忆条目"""
        start_time = time.time()

        success, error = self._simulate_failure()
        if not success:
            return None, error

        entry = None
        if self.storage_type == StorageType.MEMORY:
            entry = self.memory_store.get(entry_id)
        elif self.storage_type == StorageType.FILE:
            data = self.file_store.get(entry_id)
            if data:
                entry_dict = json.loads(data)
                entry = self._dict_to_entry(entry_dict)
        elif self.storage_type == StorageType.DATABASE:
            data = self.db_store.get(entry_id)
            if data:
                entry = self._dict_to_entry(data)
        elif self.storage_type == StorageType.CACHE:
            entry = self.cache_store.get(entry_id)

        self.read_count += 1
        if entry:
            entry.access_count += 1
            entry.last_accessed = datetime.now()

        self._record_latency(start_time)
        return entry, "检索成功" if entry else "条目不存在"

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        max_latency = max(self.latencies) if self.latencies else 0
        p99_latency = sorted(self.latencies)[int(len(self.latencies) * 0.99)] if self.latencies else 0

        return {
            "write_count": self.write_count,
            "read_count": self.read_count,
            "failed_operations": self.failed_operations,
            "storage_size_mb": self.storage_size_mb,
            "avg_latency_ms": avg_latency,
            "max_latency_ms": max_latency,
            "p99_latency_ms": p99_latency,
            "entry_count": len(self.memory_store) + len(self.file_store) + len(self.db_store) + len(self.cache_store)
        }

    def simulate_disk_full(self):
        """模拟磁盘满"""
        self.storage_size_mb = self.max_size_mb

    def simulate_crash(self):
        """模拟系统崩溃（内存数据丢失）"""
        if self.storage_type == StorageType.MEMORY:
            lost_count = len(self.memory_store)
            self.memory_store.clear()
            return lost_count
        return 0

    def cleanup_expired(self, max_age_hours: int) -> int:
        """清理过期数据"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        removed = 0

        for store in [self.memory_store, self.cache_store]:
            expired = [k for k, v in store.items() if v.last_accessed < cutoff]
            for k in expired:
                del store[k]
                removed += 1

        return removed


# ==================== 测试执行引擎 ====================

def create_test_memory_entries(count: int, user_id: str = "user_001") -> List[MemoryEntry]:
    """创建测试记忆条目"""
    entries = []
    memory_types = ["conversation", "fact", "preference", "context"]

    for i in range(count):
        entry = MemoryEntry(
            id=f"mem_{i:06d}",
            user_id=user_id,
            content=f"Test memory content {i}: " + "x" * random.randint(50, 500),
            memory_type=random.choice(memory_types),
            level=random.choice(list(MemoryLevel)),
            timestamp=datetime.now() - timedelta(hours=random.randint(0, 720)),
            importance=random.random(),
            access_count=random.randint(0, 100),
            last_accessed=datetime.now() - timedelta(hours=random.randint(0, 168)),
            metadata={"source": "test", "version": "1.0"}
        )
        entries.append(entry)
    return entries


def run_test_case(test_case: TestCase, storage: MockMemoryStorage) -> TestResult:
    """执行单个测试用例"""
    scenario = test_case.input_data.get("scenario", "normal")
    metrics = {}
    passed = False
    details = ""

    try:
        if scenario == "storage_failure":
            # 存储故障恢复测试
            fail_type = test_case.input_data.get("fail_type", "disk_full")
            backup_storage = MockMemoryStorage(failure_rate=0.0)
            storage.set_backup_storage(backup_storage)

            # 先存储一些数据
            entries = create_test_memory_entries(10)
            stored_count = 0
            for entry in entries:
                success, _ = storage.store(entry)
                if success:
                    stored_count += 1

            # 模拟故障
            if fail_type == "disk_full":
                storage.simulate_disk_full()

            # 尝试继续存储（应该切换到备用）
            new_entries = create_test_memory_entries(5)
            backup_stored = 0
            for entry in new_entries:
                success, msg = storage.store(entry)
                if success and backup_storage.retrieve(entry.id)[0]:
                    backup_stored += 1

            passed = backup_stored > 0
            details = f"主存储写入{stored_count}条，备用存储接管写入{backup_stored}条"
            metrics = {"primary_stored": stored_count, "backup_stored": backup_stored}

        elif scenario == "persistence":
            # 数据持久化验证
            data_count = test_case.input_data.get("data_count", 100)
            entries = create_test_memory_entries(data_count)

            # 存储数据
            stored_ids = []
            for entry in entries:
                success, _ = storage.store(entry)
                if success:
                    stored_ids.append(entry.id)

            # 模拟崩溃（如果是内存存储）
            if storage.storage_type == StorageType.MEMORY:
                lost = storage.simulate_crash()
                passed = False  # 内存存储崩溃后数据丢失
                details = f"存储{len(stored_ids)}条，崩溃后丢失{lost}条（内存存储特性）"
                metrics = {"stored": len(stored_ids), "lost_after_crash": lost}
            else:
                # 验证数据可恢复
                recovered = 0
                for entry_id in stored_ids:
                    entry, _ = storage.retrieve(entry_id)
                    if entry and entry.verify_integrity():
                        recovered += 1

                passed = recovered == len(stored_ids)
                details = f"存储{len(stored_ids)}条，成功恢复{recovered}条，完整性验证通过"
                metrics = {"stored": len(stored_ids), "recovered": recovered}

        elif scenario == "concurrent_write":
            # 并发写入一致性测试
            import threading

            threads_count = test_case.input_data.get("threads", 10)
            ops_per_thread = test_case.input_data.get("ops_per_thread", 100)
            errors = []
            success_count = [0]
            lock = threading.Lock()

            def worker(thread_id: int):
                for i in range(ops_per_thread):
                    entry = MemoryEntry(
                        id=f"concurrent_{thread_id}_{i}",
                        user_id=f"user_{thread_id}",
                        content=f"Concurrent write test {i}",
                        memory_type="test",
                        level=MemoryLevel.SHORT_TERM,
                        timestamp=datetime.now(),
                        importance=0.5,
                        access_count=0,
                        last_accessed=datetime.now(),
                        metadata={}
                    )
                    success, msg = storage.store(entry)
                    if success:
                        with lock:
                            success_count[0] += 1
                    else:
                        with lock:
                            errors.append(msg)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(threads_count)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            expected = threads_count * ops_per_thread
            passed = success_count[0] == expected
            details = f"预期写入{expected}条，成功{success_count[0]}条，失败{len(errors)}条"
            metrics = {"expected": expected, "success": success_count[0], "errors": len(errors)}

        elif scenario == "performance":
            # 存储性能基准测试
            target_qps = test_case.input_data.get("target_qps", 1000)
            max_latency_ms = test_case.input_data.get("max_latency_ms", 100)

            entries = create_test_memory_entries(1000)
            start = time.time()

            for entry in entries:
                storage.store(entry)

            elapsed = time.time() - start
            actual_qps = len(entries) / elapsed if elapsed > 0 else 0
            stats = storage.get_stats()

            passed = actual_qps >= target_qps and stats["p99_latency_ms"] <= max_latency_ms
            details = f"QPS: {actual_qps:.0f} (目标{target_qps}), P99延迟: {stats['p99_latency_ms']:.2f}ms (阈值{max_latency_ms}ms)"
            metrics = {"qps": actual_qps, "p99_latency": stats["p99_latency_ms"], "avg_latency": stats["avg_latency_ms"]}

        elif scenario == "large_data":
            # 大数据量存储测试
            entry_count = test_case.input_data.get("entry_count", 100000)

            # 分批存储
            batch_size = 1000
            batches = entry_count // batch_size
            start = time.time()

            for batch in range(batches):
                entries = create_test_memory_entries(batch_size)
                for entry in entries:
                    storage.store(entry)

            elapsed = time.time() - start
            stats = storage.get_stats()

            # 测试查询性能
            query_start = time.time()
            for _ in range(100):
                entry_id = f"mem_{random.randint(0, entry_count-1):06d}"
                storage.retrieve(entry_id)
            query_elapsed = time.time() - query_start

            avg_query_time = (query_elapsed / 100) * 1000  # ms

            passed = stats["entry_count"] >= entry_count * 0.95  # 允许少量失败
            details = f"存储{stats['entry_count']}条，总耗时{elapsed:.1f}s，平均查询{avg_query_time:.2f}ms"
            metrics = {"stored": stats["entry_count"], "store_time": elapsed, "avg_query_ms": avg_query_time}

        elif scenario == "quota":
            # 存储配额管理测试
            max_size_mb = test_case.input_data.get("max_size_mb", 100)
            storage.max_size_mb = max_size_mb

            # 尝试存储超过配额的数据
            entries = create_test_memory_entries(1000)
            stored = 0
            rejected = 0

            for entry in entries:
                success, msg = storage.store(entry)
                if success:
                    stored += 1
                else:
                    rejected += 1
                    if "空间不足" in msg:
                        break

            passed = stored > 0 and rejected > 0  # 应该既有成功也有拒绝
            details = f"配额{max_size_mb}MB，成功存储{stored}条，拒绝{rejected}条"
            metrics = {"quota_mb": max_size_mb, "stored": stored, "rejected": rejected}

        elif scenario == "ttl_cleanup":
            # 过期数据清理测试
            ttl_hours = test_case.input_data.get("ttl_hours", 24)

            # 创建一些过期和一些活跃的数据
            old_entries = create_test_memory_entries(50)
            for entry in old_entries:
                entry.last_accessed = datetime.now() - timedelta(hours=ttl_hours + 1)
                storage.store(entry)

            new_entries = create_test_memory_entries(50)
            for entry in new_entries:
                entry.last_accessed = datetime.now()
                storage.store(entry)

            before_count = storage.get_stats()["entry_count"]
            removed = storage.cleanup_expired(ttl_hours)
            after_count = storage.get_stats()["entry_count"]

            passed = removed > 0 and after_count < before_count
            details = f"清理前{before_count}条，清理{removed}条，清理后{after_count}条"
            metrics = {"before": before_count, "removed": removed, "after": after_count}

        elif scenario == "format_compat":
            # 存储格式兼容性测试
            versions = test_case.input_data.get("versions", ["v1", "v2"])

            # 模拟不同版本的数据格式
            compat_issues = 0
            for version in versions:
                entry = MemoryEntry(
                    id=f"compat_{version}",
                    user_id="test_user",
                    content=f"Version {version} data",
                    memory_type="test",
                    level=MemoryLevel.LONG_TERM,
                    timestamp=datetime.now(),
                    importance=0.8,
                    access_count=0,
                    last_accessed=datetime.now(),
                    metadata={"version": version, "format": f"schema_{version}"}
                )
                success, _ = storage.store(entry)
                if not success:
                    compat_issues += 1

            passed = compat_issues == 0
            details = f"测试{len(versions)}个版本，兼容性问题{compat_issues}个"
            metrics = {"versions_tested": len(versions), "issues": compat_issues}

        else:
            passed = True
            details = "默认测试通过"
            metrics = {}

    except Exception as e:
        passed = False
        details = f"测试异常: {str(e)}"
        metrics = {"error": str(e)}

    return TestResult(
        name=test_case.name,
        passed=passed,
        score=1.0 if passed else 0.0,
        details=details,
        risk_level=test_case.risk_level,
        metrics=metrics
    )


def print_separator(char: str = "-", length: int = 70):
    """打印分隔线"""
    print(char * length)


def main():
    """主测试流程"""
    print("=" * 70)
    print("Day 66: 记忆模块持久化测试")
    print("测试架构师视角：验证记忆存储的可靠性、持久性和性能")
    print("=" * 70)
    print()

    # 初始化存储系统
    storage = MockMemoryStorage(failure_rate=0.05, storage_type=StorageType.FILE)
    results: List[TestResult] = []

    # 执行测试
    print_separator("=")
    print("【测试执行】")
    print_separator("=")

    for test_case in TEST_CASES:
        result = run_test_case(test_case, storage)
        results.append(result)

        status = "✅ 通过" if result.passed else "❌ 失败"
        print(f"\n{status} | {test_case.name} ({test_case.category})")
        print(f"       风险等级: {result.risk_level} | 得分: {result.score}")
        print(f"       详情: {result.details}")
        if result.metrics:
            print(f"       指标: {json.dumps(result.metrics, indent=2, default=str).replace(chr(10), chr(10)+'       ')}")

    # 汇总报告
    print("\n")
    print_separator("=")
    print("【测试汇总报告】")
    print_separator("=")

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    l1_issues = [r for r in results if r.risk_level == "L1" and not r.passed]
    l2_issues = [r for r in results if r.risk_level == "L2" and not r.passed]
    l3_issues = [r for r in results if r.risk_level == "L3" and not r.passed]

    print(f"总测试数: {total}")
    print(f"通过: {passed} | 失败: {failed} | 通过率: {passed/total*100:.1f}%")
    print()

    print("风险分布:")
    print(f"  🔴 L1阻断性风险: {len(l1_issues)}个")
    for issue in l1_issues:
        print(f"     - {issue.name}: {issue.details}")

    print(f"  🟡 L2高优先级风险: {len(l2_issues)}个")
    for issue in l2_issues:
        print(f"     - {issue.name}: {issue.details}")

    print(f"  🟢 L3一般风险: {len(l3_issues)}个")
    for issue in l3_issues:
        print(f"     - {issue.name}: {issue.details}")

    # 存储统计
    print("\n")
    print_separator("=")
    print("【存储系统统计】")
    print_separator("=")
    stats = storage.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    print("\n")
    print_separator("=")
    print("测试完成")
    print_separator("=")


if __name__ == "__main__":
    main()
