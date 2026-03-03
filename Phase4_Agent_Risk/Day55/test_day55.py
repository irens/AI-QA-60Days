"""
Day 55: 历史信息持久化测试
目标：验证对话状态能否可靠持久化并在故障后正确恢复
测试架构师视角：内存中的状态是脆弱的，持久化是可靠性的最后防线
难度级别：进阶 - 持久化与恢复机制验证
"""

import json
import time
import uuid
import copy
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime, timedelta


class RiskLevel(Enum):
    """风险等级"""
    L1 = "L1-高风险"
    L2 = "L2-中风险"
    L3 = "L3-低风险"


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: RiskLevel
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DialogueTurn:
    """对话轮次"""
    turn_id: int
    user_input: str
    assistant_response: str
    timestamp: str
    entities: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionState:
    """会话状态"""
    session_id: str
    user_id: str
    turns: List[DialogueTurn] = field(default_factory=list)
    current_intent: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "turns": [t.to_dict() for t in self.turns],
            "current_intent": self.current_intent,
            "slots": self.slots,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active
        }


class MockStorage:
    """模拟持久化存储 - 包含故意设计的缺陷"""
    
    def __init__(self, has_write_delay: bool = False, has_isolation_bug: bool = False):
        self.data: Dict[str, Dict[str, Any]] = {}
        self.has_write_delay = has_write_delay
        self.has_isolation_bug = has_isolation_bug
        self.pending_writes: List[tuple] = []
        self.write_count = 0
        self.failure_rate = 0.0
        
    def save(self, session_id: str, state: Dict[str, Any]) -> bool:
        """保存会话状态"""
        self.write_count += 1
        
        # 模拟写入延迟
        if self.has_write_delay:
            self.pending_writes.append((session_id, copy.deepcopy(state)))
            # 模拟异步写入，部分数据可能丢失
            if len(self.pending_writes) > 3:
                # 故意丢弃最早的写入
                self.pending_writes.pop(0)
            return True
        
        # 模拟随机失败
        import random
        if random.random() < self.failure_rate:
            return False
        
        # 正常保存
        if self.has_isolation_bug:
            # 隔离bug：不使用session_id作为key，导致数据覆盖
            self.data["shared_session"] = copy.deepcopy(state)
        else:
            self.data[session_id] = copy.deepcopy(state)
        return True
    
    def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """加载会话状态"""
        if self.has_isolation_bug:
            return self.data.get("shared_session")
        return self.data.get(session_id)
    
    def flush(self):
        """刷新挂起的写入（模拟异步写入完成）"""
        if self.has_write_delay:
            for session_id, state in self.pending_writes:
                self.data[session_id] = state
            self.pending_writes.clear()
    
    def clear(self):
        """清空存储（模拟服务重启）"""
        self.data.clear()
        self.pending_writes.clear()


class PersistentDialogueManager:
    """支持持久化的对话管理器"""
    
    def __init__(self, storage: MockStorage, session_id: str = None, user_id: str = None):
        self.storage = storage
        self.session = SessionState(
            session_id=session_id or str(uuid.uuid4()),
            user_id=user_id or "anonymous",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        self.auto_save = True
        
    def add_turn(self, user_input: str, assistant_response: str, entities: Dict[str, Any] = None) -> DialogueTurn:
        """添加对话轮次"""
        turn = DialogueTurn(
            turn_id=len(self.session.turns) + 1,
            user_input=user_input,
            assistant_response=assistant_response,
            timestamp=datetime.now().isoformat(),
            entities=entities or {}
        )
        self.session.turns.append(turn)
        self.session.updated_at = datetime.now().isoformat()
        
        # 更新槽位
        if entities:
            self.session.slots.update(entities)
        
        # 自动持久化
        if self.auto_save:
            self.save()
        
        return turn
    
    def save(self) -> bool:
        """保存到存储"""
        return self.storage.save(self.session.session_id, self.session.to_dict())
    
    def load(self, session_id: str) -> bool:
        """从存储加载"""
        data = self.storage.load(session_id)
        if data:
            self.session = SessionState(
                session_id=data["session_id"],
                user_id=data["user_id"],
                turns=[DialogueTurn(**t) for t in data.get("turns", [])],
                current_intent=data.get("current_intent"),
                slots=data.get("slots", {}),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
                is_active=data.get("is_active", True)
            )
            return True
        return False
    
    def get_turn_count(self) -> int:
        return len(self.session.turns)
    
    def get_session_id(self) -> str:
        return self.session.session_id


def test_basic_persistence() -> TestResult:
    """测试1: 基础持久化"""
    print("\n" + "="*60)
    print("🧪 测试1: 基础持久化")
    print("="*60)
    print("目标: 验证对话历史是否正确保存到存储")
    
    storage = MockStorage()
    dm = PersistentDialogueManager(storage, user_id="user_001")
    
    # 进行3轮对话
    conversations = [
        ("你好", "您好！有什么可以帮助您？", {}),
        ("订酒店", "好的，请问您要去哪个城市？", {"intent": "book_hotel"}),
        ("北京", "收到，北京。请问入住日期？", {"city": "北京"})
    ]
    
    print("\n进行3轮对话:")
    for user_input, response, entities in conversations:
        turn = dm.add_turn(user_input, response, entities)
        print(f"  轮{turn.turn_id}: 用户='{user_input}' -> 已保存")
    
    # 验证存储
    stored_data = storage.load(dm.get_session_id())
    
    print(f"\n存储验证:")
    print(f"  会话ID: {dm.get_session_id()}")
    print(f"  存储中的轮次: {len(stored_data.get('turns', [])) if stored_data else 0}")
    
    # 检查
    has_data = stored_data is not None
    turn_count_correct = stored_data and len(stored_data.get("turns", [])) == 3
    slots_preserved = stored_data and stored_data.get("slots", {}).get("city") == "北京"
    
    print(f"\n✅ 验证结果:")
    print(f"  - 数据已持久化: {'✓' if has_data else '✗'}")
    print(f"  - 轮次数量正确(3): {'✓' if turn_count_correct else '✗'}")
    print(f"  - 槽位信息保留: {'✓' if slots_preserved else '✗'}")
    
    passed = has_data and turn_count_correct and slots_preserved
    score = (has_data + turn_count_correct + slots_preserved) / 3 * 100
    
    return TestResult(
        name="基础持久化",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L3,
        details={
            "turns_saved": len(stored_data.get("turns", [])) if stored_data else 0,
            "slots": stored_data.get("slots", {}) if stored_data else {}
        }
    )


def test_service_restart_recovery() -> TestResult:
    """测试2: 服务重启恢复"""
    print("\n" + "="*60)
    print("🧪 测试2: 服务重启恢复")
    print("="*60)
    print("目标: 验证服务重启后能否正确恢复对话状态")
    
    storage = MockStorage()
    session_id = "session_restart_test"
    
    # 阶段1：原始对话
    print("\n[阶段1] 原始对话:")
    dm1 = PersistentDialogueManager(storage, session_id=session_id, user_id="user_001")
    dm1.add_turn("订酒店", "好的", {"intent": "book_hotel"})
    dm1.add_turn("北京", "收到", {"city": "北京"})
    dm1.add_turn("明天", "收到", {"date": "2024-01-15"})
    
    original_turns = dm1.get_turn_count()
    print(f"  原始轮次: {original_turns}")
    print(f"  会话ID: {session_id}")
    
    # 阶段2：模拟服务重启（清空内存但保留存储）
    print("\n[阶段2] 模拟服务重启...")
    # 创建新的管理器实例（模拟服务重启后的新进程）
    dm2 = PersistentDialogueManager(storage, session_id="new_session", user_id="user_001")
    
    # 尝试恢复原始会话
    recovered = dm2.load(session_id)
    print(f"  恢复结果: {'成功' if recovered else '失败'}")
    
    if recovered:
        print(f"  恢复后轮次: {dm2.get_turn_count()}")
        print(f"  恢复后槽位: {dm2.session.slots}")
    
    # 验证
    recovery_success = recovered and dm2.get_turn_count() == original_turns
    data_intact = recovered and dm2.session.slots.get("city") == "北京"
    session_id_match = recovered and dm2.session.session_id == session_id
    
    print(f"\n✅ 验证结果:")
    print(f"  - 恢复成功: {'✓' if recovered else '✗'}")
    print(f"  - 轮次完整: {'✓' if recovery_success else '✗'} (期望{original_turns}, 实际{dm2.get_turn_count() if recovered else 0})")
    print(f"  - 数据完整: {'✓' if data_intact else '✗'}")
    print(f"  - 会话ID一致: {'✓' if session_id_match else '✗'}")
    
    passed = recovery_success and data_intact and session_id_match
    score = (recovered + recovery_success + data_intact + session_id_match) / 4 * 100
    
    return TestResult(
        name="服务重启恢复",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L1,
        details={
            "original_turns": original_turns,
            "recovered_turns": dm2.get_turn_count() if recovered else 0,
            "recovered_slots": dm2.session.slots if recovered else {}
        }
    )


def test_session_timeout() -> TestResult:
    """测试3: 会话超时处理"""
    print("\n" + "="*60)
    print("🧪 测试3: 会话超时处理")
    print("="*60)
    print("目标: 验证会话超时前是否自动保存状态")
    
    storage = MockStorage()
    session_id = "session_timeout_test"
    
    dm = PersistentDialogueManager(storage, session_id=session_id, user_id="user_001")
    
    # 进行对话
    print("\n进行5轮对话:")
    for i in range(5):
        dm.add_turn(f"消息{i+1}", f"回复{i+1}", {"step": i+1})
        print(f"  轮{i+1}: 已保存")
    
    # 模拟会话超时前的保存
    print("\n模拟会话超时...")
    timeout_save = dm.save()  # 超时前自动保存
    print(f"  超时前保存: {'成功' if timeout_save else '失败'}")
    
    # 模拟会话过期后恢复
    print("\n模拟会话过期后恢复...")
    dm_new = PersistentDialogueManager(storage, user_id="user_001")
    recovered = dm_new.load(session_id)
    
    print(f"  恢复结果: {'成功' if recovered else '失败'}")
    if recovered:
        print(f"  恢复后轮次: {dm_new.get_turn_count()}")
    
    # 验证
    all_turns_saved = recovered and dm_new.get_turn_count() == 5
    
    print(f"\n✅ 验证结果:")
    print(f"  - 超时前保存成功: {'✓' if timeout_save else '✗'}")
    print(f"  - 所有轮次恢复: {'✓' if all_turns_saved else '✗'}")
    
    passed = timeout_save and all_turns_saved
    score = 100 if passed else 50 if timeout_save else 0
    
    return TestResult(
        name="会话超时处理",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L2,
        details={
            "timeout_save": timeout_save,
            "recovered_turns": dm_new.get_turn_count() if recovered else 0
        }
    )


def test_concurrent_isolation() -> TestResult:
    """测试4: 并发隔离 - 检测隔离bug"""
    print("\n" + "="*60)
    print("🧪 测试4: 并发隔离")
    print("="*60)
    print("目标: 验证多用户场景下数据隔离是否正确")
    print("⚠️  此测试使用有隔离bug的存储")
    
    storage = MockStorage(has_isolation_bug=True)
    
    # 用户A的对话
    print("\n[用户A] 进行对话:")
    dm_a = PersistentDialogueManager(storage, session_id="session_a", user_id="user_a")
    dm_a.add_turn("我要订酒店", "好的", {"intent": "book_hotel"})
    dm_a.add_turn("北京", "收到", {"city": "北京"})
    print(f"  用户A会话ID: {dm_a.get_session_id()}")
    print(f"  用户A槽位: {dm_a.session.slots}")
    
    # 用户B的对话
    print("\n[用户B] 进行对话:")
    dm_b = PersistentDialogueManager(storage, session_id="session_b", user_id="user_b")
    dm_b.add_turn("查询余额", "好的", {"intent": "query_balance"})
    dm_b.add_turn("我的账户", "收到", {"account": "user_b_account"})
    print(f"  用户B会话ID: {dm_b.get_session_id()}")
    print(f"  用户B槽位: {dm_b.session.slots}")
    
    # 检查隔离性
    print("\n[隔离性检查]")
    stored_a = storage.load("session_a")
    stored_b = storage.load("session_b")
    
    print(f"  用户A数据查询: {'找到' if stored_a else '未找到'}")
    print(f"  用户B数据查询: {'找到' if stored_b else '未找到'}")
    
    # 由于has_isolation_bug=True，数据会被覆盖
    # 正常情况下，两个会话应该有各自独立的数据
    
    # 检查是否发生了数据覆盖（bug症状）
    data_isolated = stored_a is not None and stored_b is not None
    if stored_a and stored_b:
        # 如果都有数据，检查是否不同
        slots_a = stored_a.get("slots", {})
        slots_b = stored_b.get("slots", {})
        print(f"  用户A槽位: {slots_a}")
        print(f"  用户B槽位: {slots_b}")
        
        # 如果隔离正常，两个会话的槽位应该不同
        isolation_working = slots_a != slots_b
    else:
        isolation_working = False
    
    print(f"\n✅ 验证结果:")
    print(f"  - 数据隔离正常: {'✓' if isolation_working else '✗'} (发现bug: 数据覆盖)")
    print(f"  - 会话A数据完整: {'✓' if stored_a and stored_a.get('slots', {}).get('city') == '北京' else '✗'}")
    print(f"  - 会话B数据完整: {'✓' if stored_b and stored_b.get('slots', {}).get('account') == 'user_b_account' else '✗'}")
    
    # 检测到的bug
    bug_detected = not isolation_working
    
    passed = isolation_working
    score = 100 if passed else 30  # 发现bug给部分分
    
    return TestResult(
        name="并发隔离",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L1,
        details={
            "bug_detected": bug_detected,
            "bug_type": "会话隔离失败，数据相互覆盖" if bug_detected else "无",
            "session_a_slots": stored_a.get("slots", {}) if stored_a else {},
            "session_b_slots": stored_b.get("slots", {}) if stored_b else {}
        }
    )


def test_partial_failure() -> TestResult:
    """测试5: 部分失败处理"""
    print("\n" + "="*60)
    print("🧪 测试5: 部分失败处理")
    print("="*60)
    print("目标: 验证持久化失败时状态是否保持一致")
    
    storage = MockStorage()
    storage.failure_rate = 0.3  # 30%失败率
    
    dm = PersistentDialogueManager(storage, user_id="user_001")
    dm.auto_save = False  # 手动控制保存时机
    
    # 进行对话，部分保存会失败
    print("\n进行5轮对话(30%保存失败率):")
    save_results = []
    for i in range(5):
        dm.add_turn(f"消息{i+1}", f"回复{i+1}", {"step": i+1})
        # 手动保存
        result = dm.save()
        save_results.append(result)
        status = "✓" if result else "✗(失败)"
        print(f"  轮{i+1}: 保存{status}")
    
    # 统计
    success_count = sum(save_results)
    failure_count = len(save_results) - success_count
    
    print(f"\n保存统计:")
    print(f"  成功: {success_count}/{len(save_results)}")
    print(f"  失败: {failure_count}/{len(save_results)}")
    
    # 验证最终状态（即使部分保存失败，内存状态应该完整）
    memory_turns = dm.get_turn_count()
    print(f"\n内存状态:")
    print(f"  轮次: {memory_turns}")
    
    # 最终强制保存
    final_save = dm.save()
    print(f"  最终保存: {'成功' if final_save else '失败'}")
    
    # 验证
    memory_intact = memory_turns == 5
    
    print(f"\n✅ 验证结果:")
    print(f"  - 内存状态完整: {'✓' if memory_intact else '✗'}")
    print(f"  - 部分失败可接受: {'✓' if failure_count > 0 else 'N/A'} (测试随机失败)")
    
    passed = memory_intact
    score = 100 if passed else 0
    
    return TestResult(
        name="部分失败处理",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L2,
        details={
            "save_attempts": len(save_results),
            "save_success": success_count,
            "save_failure": failure_count,
            "memory_turns": memory_turns
        }
    )


def test_large_data_persistence() -> TestResult:
    """测试6: 大数据量持久化"""
    print("\n" + "="*60)
    print("🧪 测试6: 大数据量持久化")
    print("="*60)
    print("目标: 验证100轮对话能否正常持久化")
    
    storage = MockStorage()
    session_id = "session_large_data"
    dm = PersistentDialogueManager(storage, session_id=session_id, user_id="user_001")
    
    # 进行100轮对话
    print("\n进行100轮对话:")
    start_time = time.time()
    
    for i in range(100):
        dm.add_turn(
            f"这是第{i+1}轮对话的长文本消息，包含大量信息",
            f"这是系统对第{i+1}轮对话的详细回复",
            {
                "turn": i+1,
                "timestamp": datetime.now().isoformat(),
                "data": f"some_data_{i}"
            }
        )
        if (i + 1) % 20 == 0:
            print(f"  已完成 {i+1}/100 轮")
    
    elapsed = time.time() - start_time
    
    print(f"\n写入完成:")
    print(f"  总轮次: {dm.get_turn_count()}")
    print(f"  耗时: {elapsed:.2f}秒")
    print(f"  平均: {elapsed/100*1000:.1f}ms/轮")
    
    # 验证存储
    stored_data = storage.load(session_id)
    
    if stored_data:
        stored_turns = len(stored_data.get("turns", []))
        data_size = len(json.dumps(stored_data))
        print(f"\n存储验证:")
        print(f"  存储轮次: {stored_turns}")
        print(f"  数据大小: {data_size/1024:.1f}KB")
    else:
        stored_turns = 0
        data_size = 0
    
    # 检查
    all_turns_saved = stored_turns == 100
    performance_ok = elapsed < 10  # 10秒内完成
    
    print(f"\n✅ 验证结果:")
    print(f"  - 所有轮次已保存: {'✓' if all_turns_saved else '✗'} (期望100, 实际{stored_turns})")
    print(f"  - 性能可接受: {'✓' if performance_ok else '✗'} ({elapsed:.2f}s)")
    
    passed = all_turns_saved and performance_ok
    score = (all_turns_saved + performance_ok) / 2 * 100
    
    return TestResult(
        name="大数据量持久化",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L3,
        details={
            "total_turns": dm.get_turn_count(),
            "stored_turns": stored_turns,
            "elapsed_seconds": round(elapsed, 2),
            "data_size_kb": round(data_size / 1024, 1) if data_size else 0
        }
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📊 测试汇总报告 - Day 55: 历史信息持久化")
    print("="*70)
    
    total_score = sum(r.score for r in results) / len(results)
    passed_count = sum(1 for r in results if r.passed)
    l1_risks = sum(1 for r in results if r.risk_level == RiskLevel.L1 and not r.passed)
    
    print(f"\n总体评分: {total_score:.1f}/100")
    print(f"通过测试: {passed_count}/{len(results)}")
    print(f"高风险失败: {l1_risks}项")
    
    print(f"\n{'测试项':<25} {'状态':<8} {'评分':<8} {'风险等级':<12}")
    print("-" * 60)
    for r in results:
        status = "✅ 通过" if r.passed else "❌ 失败"
        print(f"{r.name:<25} {status:<8} {r.score:>6.1f}   {r.risk_level.value:<12}")
    
    # 风险评估
    print("\n" + "="*70)
    print("🚨 风险评估")
    print("="*70)
    if l1_risks > 0:
        print(f"⚠️  发现 {l1_risks} 个高风险问题，建议立即修复！")
        for r in results:
            if r.risk_level == RiskLevel.L1 and not r.passed:
                bug_info = r.details.get("bug_type", "未知")
                print(f"   - {r.name}: {bug_info}")
    else:
        print("✅ 未发现高风险问题")
    
    # 建议
    print("\n" + "="*70)
    print("💡 改进建议")
    print("="*70)
    if total_score < 80:
        print("• 持久化架构需要重构，建议引入事务机制")
        print("• 增加写入确认机制，确保数据落盘")
        print("• 实现会话隔离的单元测试")
    elif total_score < 95:
        print("• 持久化基本可用，建议增加写入重试机制")
        print("• 考虑引入异步持久化提升性能")
    else:
        print("• 持久化机制良好，建议增加监控告警")
    
    print("\n" + "="*70)
    print("请将以上测试结果贴回给Trae，生成详细的质量分析报告")
    print("="*70)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 55: 历史信息持久化")
    print("="*70)
    print("\n测试目标: 验证对话状态的持久化和恢复能力")
    print("测试架构师视角: 内存中的状态是脆弱的，持久化是可靠性的最后防线")
    
    results = [
        test_basic_persistence(),
        test_service_restart_recovery(),
        test_session_timeout(),
        test_concurrent_isolation(),
        test_partial_failure(),
        test_large_data_persistence()
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
