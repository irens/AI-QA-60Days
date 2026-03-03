"""
Day 54: 多轮对话状态一致性测试
目标：验证Agent在多轮对话中状态管理的正确性和一致性
测试架构师视角：状态不一致是Agent系统的"癌症"，必须严格验证
难度级别：基础 - 核心概念验证
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class Intent(Enum):
    """用户意图枚举"""
    BOOK_HOTEL = "book_hotel"
    MODIFY_DATE = "modify_date"
    CANCEL = "cancel"
    QUERY_BALANCE = "query_balance"
    MAKE_PAYMENT = "make_payment"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """风险等级"""
    L1 = "L1-高风险"
    L2 = "L2-中风险"
    L3 = "L3-低风险"


@dataclass
class DialogueState:
    """对话状态"""
    current_intent: Optional[Intent] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
    last_updated: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_intent": self.current_intent.value if self.current_intent else None,
            "slots": self.slots,
            "turn_count": self.turn_count,
            "last_updated": self.last_updated
        }


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: RiskLevel
    details: Dict[str, Any] = field(default_factory=dict)


class DialogueManager:
    """模拟对话管理器 - 包含故意设计的状态管理缺陷"""
    
    def __init__(self, has_async_bug: bool = False, has_rollback_bug: bool = False):
        self.state = DialogueState()
        self.has_async_bug = has_async_bug
        self.has_rollback_bug = has_rollback_bug
        self.state_history: List[DialogueState] = []
        self.pending_updates: List[Dict[str, Any]] = []
        
    def process_input(self, user_input: str, entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理用户输入并更新状态"""
        self.state.turn_count += 1
        self.state.last_updated = datetime.now().isoformat()
        
        # 保存当前状态（用于回滚）
        self._save_state_snapshot()
        
        # 意图识别
        intent = self._recognize_intent(user_input)
        
        # 处理不同意图
        if intent == Intent.CANCEL:
            return self._handle_cancel()
        
        # 更新意图（可能覆盖旧意图）
        old_intent = self.state.current_intent
        self.state.current_intent = intent
        
        # 更新槽位
        if entities:
            if self.has_async_bug and self.pending_updates:
                # 模拟异步更新bug：延迟应用更新
                self.pending_updates.append(entities)
            else:
                self.state.slots.update(entities)
        
        # 记录历史
        self.state.history.append({
            "turn": self.state.turn_count,
            "input": user_input,
            "intent": intent.value,
            "entities": entities or {}
        })
        
        return {
            "intent": intent.value,
            "state": self.state.to_dict(),
            "old_intent": old_intent.value if old_intent else None
        }
    
    def _recognize_intent(self, user_input: str) -> Intent:
        """简单的意图识别"""
        input_lower = user_input.lower()
        if "订酒店" in user_input or "book hotel" in input_lower:
            return Intent.BOOK_HOTEL
        elif "改" in user_input or "modify" in input_lower:
            return Intent.MODIFY_DATE
        elif "取消" in user_input or "cancel" in input_lower:
            return Intent.CANCEL
        elif "余额" in user_input or "balance" in input_lower:
            return Intent.QUERY_BALANCE
        elif "支付" in user_input or "pay" in input_lower:
            return Intent.MAKE_PAYMENT
        return Intent.UNKNOWN
    
    def _save_state_snapshot(self):
        """保存状态快照"""
        import copy
        snapshot = DialogueState(
            current_intent=self.state.current_intent,
            slots=copy.deepcopy(self.state.slots),
            history=copy.deepcopy(self.state.history),
            turn_count=self.state.turn_count,
            last_updated=self.state.last_updated
        )
        self.state_history.append(snapshot)
    
    def _handle_cancel(self) -> Dict[str, Any]:
        """处理取消/回滚"""
        if not self.state_history:
            return {"success": False, "error": "No state to rollback"}
        
        if self.has_rollback_bug:
            # 模拟回滚bug：只回滚部分状态
            old_state = self.state_history[-1]
            self.state.slots = old_state.slots
            # 故意不回滚意图
            return {
                "success": True,
                "rolled_back_to_turn": old_state.turn_count,
                "bug": "Intent not rolled back"
            }
        
        # 正常回滚
        old_state = self.state_history.pop()
        self.state = old_state
        return {
            "success": True,
            "rolled_back_to_turn": old_state.turn_count
        }
    
    def apply_tool_result(self, tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """应用工具调用结果到状态"""
        if tool_name == "query_balance":
            # 更新余额到状态
            self.state.slots["balance"] = result.get("balance", 0)
            self.state.slots["balance_updated_at"] = datetime.now().isoformat()
            return {"updated": True, "slot": "balance"}
        elif tool_name == "book_hotel":
            self.state.slots["booking_confirmed"] = result.get("success", False)
            return {"updated": True, "slot": "booking_confirmed"}
        return {"updated": False}
    
    def get_state(self) -> DialogueState:
        """获取当前状态"""
        return self.state


def test_basic_state_tracking() -> TestResult:
    """测试1: 基础状态追踪"""
    print("\n" + "="*60)
    print("🧪 测试1: 基础状态追踪")
    print("="*60)
    print("目标: 验证多轮对话中状态是否正确累积")
    
    dm = DialogueManager()
    
    # 第一轮：订酒店
    result1 = dm.process_input("我想订酒店", {"city": "北京", "date": "2024-01-15"})
    print(f"\n第1轮 - 输入: '我想订酒店'")
    print(f"  意图: {result1['intent']}")
    print(f"  槽位: {result1['state']['slots']}")
    
    # 第二轮：修改日期
    result2 = dm.process_input("改成明天", {"date": "2024-01-16"})
    print(f"\n第2轮 - 输入: '改成明天'")
    print(f"  意图: {result2['intent']}")
    print(f"  槽位: {result2['state']['slots']}")
    
    # 第三轮：确认
    result3 = dm.process_input("确认预订")
    print(f"\n第3轮 - 输入: '确认预订'")
    print(f"  意图: {result3['intent']}")
    print(f"  槽位: {result3['state']['slots']}")
    
    # 验证
    final_state = dm.get_state()
    checks = [
        final_state.turn_count == 3,
        final_state.slots.get("city") == "北京",
        final_state.slots.get("date") == "2024-01-16",
        len(final_state.history) == 3
    ]
    
    passed = all(checks)
    score = sum(checks) / len(checks) * 100
    
    print(f"\n✅ 验证结果:")
    print(f"  - 轮次计数正确: {'✓' if final_state.turn_count == 3 else '✗'}")
    print(f"  - 城市信息保留: {'✓' if final_state.slots.get('city') == '北京' else '✗'}")
    print(f"  - 日期更新正确: {'✓' if final_state.slots.get('date') == '2024-01-16' else '✗'}")
    print(f"  - 历史记录完整: {'✓' if len(final_state.history) == 3 else '✗'}")
    
    return TestResult(
        name="基础状态追踪",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L2,
        details={"turns": final_state.turn_count, "slots": final_state.slots}
    )


def test_intent_change() -> TestResult:
    """测试2: 意图变更处理"""
    print("\n" + "="*60)
    print("🧪 测试2: 意图变更处理")
    print("="*60)
    print("目标: 验证用户改变意图时，新意图是否正确覆盖旧意图")
    
    dm = DialogueManager()
    
    # 第一轮：查询余额
    result1 = dm.process_input("查询余额")
    print(f"\n第1轮 - 输入: '查询余额'")
    print(f"  当前意图: {result1['intent']}")
    
    # 第二轮：改为订酒店（意图变更）
    result2 = dm.process_input("还是订酒店吧", {"city": "上海"})
    print(f"\n第2轮 - 输入: '还是订酒店吧'")
    print(f"  旧意图: {result2['old_intent']}")
    print(f"  新意图: {result2['intent']}")
    
    # 验证
    final_state = dm.get_state()
    checks = [
        result1['intent'] == "query_balance",
        result2['intent'] == "book_hotel",
        result2['old_intent'] == "query_balance",
        final_state.current_intent == Intent.BOOK_HOTEL
    ]
    
    passed = all(checks)
    score = sum(checks) / len(checks) * 100
    
    print(f"\n✅ 验证结果:")
    print(f"  - 第一轮意图正确: {'✓' if result1['intent'] == 'query_balance' else '✗'}")
    print(f"  - 意图变更成功: {'✓' if result2['intent'] == 'book_hotel' else '✗'}")
    print(f"  - 旧意图被记录: {'✓' if result2['old_intent'] == 'query_balance' else '✗'}")
    print(f"  - 最终状态正确: {'✓' if final_state.current_intent == Intent.BOOK_HOTEL else '✗'}")
    
    return TestResult(
        name="意图变更处理",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L1,
        details={"intent_change": f"{result2['old_intent']} -> {result2['intent']}"}
    )


def test_slot_update() -> TestResult:
    """测试3: 槽位值更新"""
    print("\n" + "="*60)
    print("🧪 测试3: 槽位值更新")
    print("="*60)
    print("目标: 验证同一槽位多次更新时，新值是否正确覆盖旧值")
    
    dm = DialogueManager()
    
    # 连续修改日期
    updates = [
        ("订明天", {"date": "2024-01-15"}),
        ("改到后天", {"date": "2024-01-16"}),
        ("还是大后天吧", {"date": "2024-01-17"})
    ]
    
    print("\n连续修改日期:")
    for i, (input_text, entities) in enumerate(updates, 1):
        result = dm.process_input(input_text, entities)
        print(f"  第{i}次: '{input_text}' -> 日期={result['state']['slots'].get('date')}")
    
    # 验证最终日期
    final_state = dm.get_state()
    correct_date = final_state.slots.get("date") == "2024-01-17"
    
    print(f"\n✅ 验证结果:")
    print(f"  - 最终日期正确(2024-01-17): {'✓' if correct_date else '✗'}")
    print(f"  - 实际值: {final_state.slots.get('date')}")
    
    return TestResult(
        name="槽位值更新",
        passed=correct_date,
        score=100 if correct_date else 0,
        risk_level=RiskLevel.L1,
        details={"final_date": final_state.slots.get("date")}
    )


def test_state_rollback() -> TestResult:
    """测试4: 状态回滚测试 - 检测回滚bug"""
    print("\n" + "="*60)
    print("🧪 测试4: 状态回滚测试")
    print("="*60)
    print("目标: 验证取消操作能否正确恢复到之前的状态")
    print("⚠️  此测试使用有bug的对话管理器")
    
    # 使用有回滚bug的管理器
    dm = DialogueManager(has_rollback_bug=True)
    
    # 第一轮：订酒店
    result1 = dm.process_input("订酒店", {"city": "北京", "date": "2024-01-15"})
    print(f"\n第1轮 - 输入: '订酒店'")
    print(f"  意图: {result1['intent']}")
    print(f"  槽位: {result1['state']['slots']}")
    
    # 第二轮：修改日期
    result2 = dm.process_input("改成明天", {"date": "2024-01-16"})
    print(f"\n第2轮 - 输入: '改成明天'")
    print(f"  意图: {result2['intent']}")
    print(f"  槽位: {result2['state']['slots']}")
    
    # 第三轮：取消（应该回滚到第1轮状态）
    result3 = dm.process_input("取消")
    print(f"\n第3轮 - 输入: '取消'")
    print(f"  回滚结果: {result3}")
    
    # 验证回滚后的状态
    final_state = dm.get_state()
    print(f"\n回滚后状态:")
    print(f"  意图: {final_state.current_intent.value if final_state.current_intent else None}")
    print(f"  槽位: {final_state.slots}")
    
    # 检查回滚是否正确
    # 注意：由于has_rollback_bug=True，意图不会被回滚
    intent_correct = final_state.current_intent == Intent.BOOK_HOTEL
    date_correct = final_state.slots.get("date") == "2024-01-15"
    city_correct = final_state.slots.get("city") == "北京"
    
    print(f"\n✅ 验证结果:")
    print(f"  - 意图回滚正确: {'✓' if intent_correct else '✗'} (发现bug: 意图未回滚)")
    print(f"  - 日期回滚正确: {'✓' if date_correct else '✗'}")
    print(f"  - 城市信息保留: {'✓' if city_correct else '✗'}")
    
    # 即使有意图bug，槽位应该正确回滚
    passed = date_correct and city_correct
    score = (date_correct + city_correct + intent_correct) / 3 * 100
    
    return TestResult(
        name="状态回滚测试",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L1,
        details={
            "bug_detected": not intent_correct,
            "bug_type": "意图未回滚",
            "expected_intent": "book_hotel",
            "actual_intent": final_state.current_intent.value if final_state.current_intent else None
        }
    )


def test_tool_result_sync() -> TestResult:
    """测试5: 工具结果同步"""
    print("\n" + "="*60)
    print("🧪 测试5: 工具结果同步")
    print("="*60)
    print("目标: 验证工具调用结果是否正确更新到状态中")
    
    dm = DialogueManager()
    
    # 查询余额
    result1 = dm.process_input("查询余额")
    print(f"\n第1轮 - 输入: '查询余额'")
    print(f"  意图: {result1['intent']}")
    
    # 模拟工具调用结果
    tool_result = {"balance": 5000, "currency": "CNY"}
    sync_result = dm.apply_tool_result("query_balance", tool_result)
    print(f"\n工具调用: query_balance")
    print(f"  返回结果: {tool_result}")
    print(f"  同步状态: {sync_result}")
    
    # 进行支付
    result2 = dm.process_input("支付1000元", {"amount": 1000})
    print(f"\n第2轮 - 输入: '支付1000元'")
    print(f"  意图: {result2['intent']}")
    
    # 验证余额是否被正确使用
    final_state = dm.get_state()
    balance = final_state.slots.get("balance")
    has_balance = balance is not None
    balance_correct = balance == 5000
    
    print(f"\n✅ 验证结果:")
    print(f"  - 余额已同步到状态: {'✓' if has_balance else '✗'}")
    print(f"  - 余额值正确(5000): {'✓' if balance_correct else '✗'}")
    print(f"  - 实际余额: {balance}")
    
    passed = has_balance and balance_correct
    score = 100 if passed else 50 if has_balance else 0
    
    return TestResult(
        name="工具结果同步",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L1,
        details={"balance": balance, "tool_synced": has_balance}
    )


def test_long_dialogue_stability() -> TestResult:
    """测试6: 长对话状态稳定性"""
    print("\n" + "="*60)
    print("🧪 测试6: 长对话状态稳定性")
    print("="*60)
    print("目标: 验证20轮对话后状态是否仍保持一致")
    
    dm = DialogueManager()
    
    # 模拟20轮对话
    inputs = [
        ("订酒店", {"city": "北京"}),
        ("改到上海", {"city": "上海"}),
        ("明天入住", {"date": "2024-01-15"}),
        ("改到后天", {"date": "2024-01-16"}),
        ("要双人间", {"room_type": "double"}),
        ("改成单人间", {"room_type": "single"}),
        ("查询价格", {}),
        ("有优惠吗", {}),
        ("确认预订", {}),
        ("取消", {}),
        ("重新订", {"city": "广州"}),
        ("大后天", {"date": "2024-01-17"}),
        ("豪华套房", {"room_type": "suite"}),
        ("含早餐", {"breakfast": True}),
        ("无烟房", {"smoking": False}),
        ("高楼层", {"floor": "high"}),
        ("靠近电梯", {"location": "near_elevator"}),
        ("查询余额", {}),
        ("支付", {"amount": 1500}),
        ("确认", {})
    ]
    
    print(f"\n模拟20轮对话:")
    for i, (input_text, entities) in enumerate(inputs, 1):
        result = dm.process_input(input_text, entities)
        if i <= 5 or i >= 18:  # 只显示前5轮和后3轮
            print(f"  轮{i}: '{input_text}' -> 意图={result['intent']}")
        elif i == 6:
            print(f"  ... (中间轮次省略) ...")
    
    # 验证最终状态
    final_state = dm.get_state()
    checks = [
        final_state.turn_count == 20,
        final_state.slots.get("city") == "广州",
        final_state.slots.get("date") == "2024-01-17",
        final_state.slots.get("room_type") == "suite",
        len(final_state.history) == 20
    ]
    
    passed = all(checks)
    score = sum(checks) / len(checks) * 100
    
    print(f"\n✅ 验证结果:")
    print(f"  - 轮次计数正确(20): {'✓' if final_state.turn_count == 20 else '✗'}")
    print(f"  - 最终城市(广州): {'✓' if final_state.slots.get('city') == '广州' else '✗'}")
    print(f"  - 最终日期(2024-01-17): {'✓' if final_state.slots.get('date') == '2024-01-17' else '✗'}")
    print(f"  - 房型(suite): {'✓' if final_state.slots.get('room_type') == 'suite' else '✗'}")
    print(f"  - 历史完整(20条): {'✓' if len(final_state.history) == 20 else '✗'}")
    
    return TestResult(
        name="长对话状态稳定性",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L2,
        details={
            "total_turns": final_state.turn_count,
            "final_slots": {k: v for k, v in list(final_state.slots.items())[:5]}
        }
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📊 测试汇总报告 - Day 54: 多轮对话状态一致性")
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
                print(f"   - {r.name}: {r.details}")
    else:
        print("✅ 未发现高风险问题")
    
    # 建议
    print("\n" + "="*70)
    print("💡 改进建议")
    print("="*70)
    if total_score < 80:
        print("• 状态管理机制需要重构，建议引入事务性状态更新")
        print("• 增加状态变更日志，便于问题追溯")
        print("• 实现完整的状态回滚机制")
    elif total_score < 95:
        print("• 状态管理基本可用，建议增加并发控制")
        print("• 考虑引入状态版本控制")
    else:
        print("• 状态管理良好，建议持续监控长对话场景")
    
    print("\n" + "="*70)
    print("请将以上测试结果贴回给Trae，生成详细的质量分析报告")
    print("="*70)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 54: 多轮对话状态一致性")
    print("="*70)
    print("\n测试目标: 验证Agent在多轮对话中的状态管理能力")
    print("测试架构师视角: 状态不一致是Agent系统的'癌症'")
    
    results = [
        test_basic_state_tracking(),
        test_intent_change(),
        test_slot_update(),
        test_state_rollback(),
        test_tool_result_sync(),
        test_long_dialogue_stability()
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
