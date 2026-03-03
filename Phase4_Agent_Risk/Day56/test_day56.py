"""
Day 56: 上下文管理与长对话稳定性测试
目标：验证Agent在资源约束下保持上下文完整性和有效性的能力
测试架构师视角：上下文窗口是有限的资源，长对话必然导致"失忆"，我们要量化这种风险
难度级别：实战 - 综合场景验证
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime


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


class ContextManager:
    """上下文管理器 - 模拟不同策略的上下文管理"""
    
    def __init__(
        self,
        max_tokens: int = 1000,
        strategy: str = "sliding_window",
        protect_system: bool = True
    ):
        self.max_tokens = max_tokens
        self.strategy = strategy
        self.protect_system = protect_system
        self.system_message = ""
        self.history: List[Dict[str, Any]] = []
        self.key_facts: Dict[str, Any] = {}  # 关键事实存储
        self.current_tokens = 0
        
    def set_system_message(self, message: str):
        """设置系统消息"""
        self.system_message = message
        self._recalculate_tokens()
        
    def add_message(self, role: str, content: str, entities: Dict[str, Any] = None):
        """添加消息到上下文"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "entities": entities or {}
        }
        self.history.append(message)
        
        # 提取关键事实
        if entities:
            self.key_facts.update(entities)
        
        # 管理上下文窗口
        self._manage_context()
        
        return message
    
    def _estimate_tokens(self, text: str) -> int:
        """估算Token数（简化版：1个汉字≈1.5token，英文单词≈1token）"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        return int(chinese_chars * 1.5 + english_words * 1.2) + 4  # 加上消息格式开销
    
    def _recalculate_tokens(self):
        """重新计算总Token数"""
        total = self._estimate_tokens(self.system_message)
        for msg in self.history:
            total += self._estimate_tokens(msg["content"])
        self.current_tokens = total
        return total
    
    def _manage_context(self):
        """管理上下文窗口"""
        self._recalculate_tokens()
        
        if self.current_tokens <= self.max_tokens:
            return
        
        # 根据策略处理超出的上下文
        if self.strategy == "truncate":
            # 截断法：直接删除最早的消息
            while self.current_tokens > self.max_tokens and len(self.history) > 1:
                removed = self.history.pop(0)
                self.current_tokens -= self._estimate_tokens(removed["content"])
                
        elif self.strategy == "sliding_window":
            # 滑动窗口：保留最近N轮
            max_rounds = 10
            while len(self.history) > max_rounds * 2:  # 每轮包含user和assistant
                removed = self.history.pop(0)
                self.current_tokens -= self._estimate_tokens(removed["content"])
                
        elif self.strategy == "summarize":
            # 摘要法：对早期消息生成摘要
            if len(self.history) > 10:
                # 模拟摘要（保留关键实体）
                old_messages = self.history[:-10]
                self.history = self.history[-10:]
                
                # 生成摘要
                summary_entities = {}
                for msg in old_messages:
                    if msg.get("entities"):
                        summary_entities.update(msg["entities"])
                
                summary = f"[摘要] 之前对话中提到的关键信息: {json.dumps(summary_entities, ensure_ascii=False)}"
                self.history.insert(0, {
                    "role": "system",
                    "content": summary,
                    "timestamp": datetime.now().isoformat(),
                    "is_summary": True
                })
                self._recalculate_tokens()
    
    def get_context(self) -> List[Dict[str, Any]]:
        """获取当前上下文"""
        context = []
        if self.system_message and self.protect_system:
            context.append({"role": "system", "content": self.system_message})
        context.extend(self.history)
        return context
    
    def get_token_count(self) -> int:
        """获取当前Token数"""
        return self.current_tokens
    
    def get_history_length(self) -> int:
        """获取历史消息数"""
        return len(self.history)
    
    def check_fact_retention(self, fact_key: str) -> bool:
        """检查关键事实是否保留"""
        # 检查key_facts
        if fact_key in self.key_facts:
            return True
        
        # 检查历史消息
        for msg in self.history:
            if fact_key in msg.get("content", ""):
                return True
            if msg.get("entities") and fact_key in msg.get("entities", {}):
                return True
        
        return False


def test_context_window_boundary() -> TestResult:
    """测试1: 上下文窗口边界"""
    print("\n" + "="*60)
    print("🧪 测试1: 上下文窗口边界")
    print("="*60)
    print("目标: 验证Token接近上限时系统是否优雅处理")
    
    # 创建小窗口管理器
    cm = ContextManager(max_tokens=500, strategy="truncate")
    cm.set_system_message("你是一个酒店预订助手。")
    
    print(f"\n系统消息: '{cm.system_message}'")
    print(f"最大Token限制: {cm.max_tokens}")
    
    # 持续添加消息直到接近上限
    print("\n持续添加消息:")
    for i in range(20):
        cm.add_message("user", f"这是第{i+1}轮对话，我想预订酒店，城市是北京，日期是2024年1月{i+1}日")
        cm.add_message("assistant", f"收到，已记录您的需求。当前Token使用: {cm.get_token_count()}")
        
        if i < 3 or i >= 17 or cm.get_token_count() > cm.max_tokens * 0.8:
            print(f"  轮{i+1}: Token={cm.get_token_count()}, 历史长度={cm.get_history_length()}")
        elif i == 3:
            print(f"  ... (中间轮次省略) ...")
    
    final_tokens = cm.get_token_count()
    final_history = cm.get_history_length()
    
    print(f"\n最终结果:")
    print(f"  Token使用: {final_tokens}/{cm.max_tokens}")
    print(f"  历史消息: {final_history}条")
    
    # 验证
    within_limit = final_tokens <= cm.max_tokens
    handled_gracefully = final_history < 40  # 应该有所截断
    
    print(f"\n✅ 验证结果:")
    print(f"  - Token在限制内: {'✓' if within_limit else '✗'} ({final_tokens}/{cm.max_tokens})")
    print(f"  - 优雅处理溢出: {'✓' if handled_gracefully else '✗'} (历史{final_history}条)")
    
    passed = within_limit
    score = 100 if within_limit else max(0, 100 - (final_tokens - cm.max_tokens) / 10)
    
    return TestResult(
        name="上下文窗口边界",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L1,
        details={
            "max_tokens": cm.max_tokens,
            "final_tokens": final_tokens,
            "final_history": final_history,
            "overflow": max(0, final_tokens - cm.max_tokens)
        }
    )


def test_long_dialogue_stability() -> TestResult:
    """测试2: 长对话稳定性"""
    print("\n" + "="*60)
    print("🧪 测试2: 长对话稳定性")
    print("="*60)
    print("目标: 验证50轮对话后关键信息是否保留")
    
    cm = ContextManager(max_tokens=2000, strategy="summarize")
    cm.set_system_message("你是客服助手，请记住用户的关键信息。")
    
    # 记录关键事实
    key_facts = {
        "user_name": "张三",
        "vip_level": "金牌会员",
        "preferred_city": "上海",
        "allergy": "花生过敏"
    }
    
    print(f"\n关键事实: {key_facts}")
    print("\n进行50轮对话:")
    
    # 第一轮：记录关键事实
    cm.add_message("user", f"我叫{key_facts['user_name']}，是{key_facts['vip_level']}，{key_facts['allergy']}", key_facts)
    cm.add_message("assistant", "已记录您的信息")
    
    # 中间48轮：普通对话
    for i in range(24):
        cm.add_message("user", f"咨询问题{i+1}: 这个产品有货吗？价格多少？")
        cm.add_message("assistant", f"回复{i+1}: 有货，价格是{(i+1)*100}元")
        if (i + 1) % 10 == 0:
            print(f"  已完成 {(i+1)*2}/50 轮")
    
    # 最后一轮：检查关键事实
    cm.add_message("user", "我是谁？我有什么过敏？")
    
    print(f"\n对话完成:")
    print(f"  总轮次: 50")
    print(f"  Token使用: {cm.get_token_count()}")
    print(f"  历史长度: {cm.get_history_length()}")
    
    # 检查关键事实保留情况
    retention_results = {}
    for key, value in key_facts.items():
        retained = cm.check_fact_retention(key)
        retention_results[key] = retained
    
    print(f"\n关键事实保留情况:")
    for key, retained in retention_results.items():
        status = "✓" if retained else "✗"
        print(f"  {key}: {status}")
    
    # 验证
    retention_rate = sum(retention_results.values()) / len(retention_results)
    passed = retention_rate >= 0.5  # 至少保留50%
    score = retention_rate * 100
    
    print(f"\n✅ 验证结果:")
    print(f"  - 事实保留率: {retention_rate*100:.0f}%")
    print(f"  - 通过阈值: ≥50%")
    print(f"  - 结果: {'✓ 通过' if passed else '✗ 失败'}")
    
    return TestResult(
        name="长对话稳定性",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L1,
        details={
            "total_turns": 50,
            "retention_rate": retention_rate,
            "retention_details": retention_results
        }
    )


def test_system_message_protection() -> TestResult:
    """测试3: 系统消息保留"""
    print("\n" + "="*60)
    print("🧪 测试3: 系统消息保留")
    print("="*60)
    print("目标: 验证系统指令在上下文溢出时是否被保留")
    
    # 测试有保护的版本
    cm_protected = ContextManager(max_tokens=800, strategy="truncate", protect_system=True)
    system_msg = "你是酒店预订助手，必须遵守以下规则：1.不透露用户信息 2.不推荐竞品"
    cm_protected.set_system_message(system_msg)
    
    print(f"\n系统消息: '{system_msg[:50]}...'")
    print(f"保护策略: {'启用' if cm_protected.protect_system else '禁用'}")
    
    # 添加大量消息
    print("\n添加消息直到触发截断:")
    for i in range(30):
        cm_protected.add_message("user", f"用户消息{i+1}: 详细描述各种需求和问题")
        cm_protected.add_message("assistant", f"助手回复{i+1}: 详细回答用户的问题")
        if cm_protected.get_token_count() > cm_protected.max_tokens * 0.9:
            print(f"  触发截断于第{i+1}轮")
            break
    
    # 检查系统消息是否保留
    context = cm_protected.get_context()
    system_preserved = any(
        msg.get("role") == "system" and system_msg[:20] in msg.get("content", "")
        for msg in context
    )
    
    print(f"\n验证结果:")
    print(f"  最终Token: {cm_protected.get_token_count()}")
    print(f"  上下文长度: {len(context)}")
    print(f"  系统消息保留: {'✓' if system_preserved else '✗'}")
    
    # 测试无保护的版本（对比）
    cm_unprotected = ContextManager(max_tokens=800, strategy="truncate", protect_system=False)
    cm_unprotected.set_system_message(system_msg)
    for i in range(30):
        cm_unprotected.add_message("user", f"用户消息{i+1}")
        cm_unprotected.add_message("assistant", f"助手回复{i+1}")
        if cm_unprotected.get_token_count() > cm_unprotected.max_tokens * 0.9:
            break
    
    context_unprotected = cm_unprotected.get_context()
    system_lost = not any(
        msg.get("role") == "system" for msg in context_unprotected
    )
    
    print(f"\n对比测试(无保护):")
    print(f"  系统消息丢失: {'✓(预期)' if system_lost else '✗'}")
    
    passed = system_preserved
    score = 100 if passed else 0
    
    return TestResult(
        name="系统消息保留",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L1,
        details={
            "system_protected": system_preserved,
            "protection_enabled": cm_protected.protect_system,
            "final_tokens": cm_protected.get_token_count()
        }
    )


def test_topic_switch_cleanup() -> TestResult:
    """测试4: 话题切换清理"""
    print("\n" + "="*60)
    print("🧪 测试4: 话题切换清理")
    print("="*60)
    print("目标: 验证话题跳转后旧话题上下文是否正确清理")
    
    cm = ContextManager(max_tokens=1000, strategy="sliding_window")
    
    # 话题1：酒店预订
    print("\n[话题1] 酒店预订:")
    hotel_entities = {"topic": "hotel", "city": "北京", "date": "2024-01-15"}
    cm.add_message("user", "我想订北京的酒店", hotel_entities)
    cm.add_message("assistant", "好的，北京酒店")
    cm.add_message("user", "要五星级", {"level": "5-star"})
    cm.add_message("assistant", "收到，五星级")
    print(f"  已添加酒店预订对话")
    print(f"  当前实体: {cm.key_facts}")
    
    # 话题切换：机票预订
    print("\n[话题切换] 转为机票预订:")
    flight_entities = {"topic": "flight", "from": "北京", "to": "上海"}
    cm.add_message("user", "不订酒店了，改订机票", flight_entities)
    cm.add_message("assistant", "好的，转为机票预订")
    cm.add_message("user", "明天起飞", {"date": "2024-01-16"})
    cm.add_message("assistant", "收到，明天")
    print(f"  已添加机票预订对话")
    print(f"  当前实体: {cm.key_facts}")
    
    # 检查话题隔离
    context = cm.get_context()
    has_hotel = any("酒店" in msg.get("content", "") for msg in context)
    has_flight = any("机票" in msg.get("content", "") for msg in context)
    
    print(f"\n话题隔离检查:")
    print(f"  包含酒店话题: {'✓' if has_hotel else '✗'}")
    print(f"  包含机票话题: {'✓' if has_flight else '✗'}")
    
    # 检查实体管理
    topic_switched = cm.key_facts.get("topic") == "flight"
    old_topic_cleared = "city" not in cm.key_facts or cm.key_facts.get("topic") != "hotel"
    
    print(f"  话题已切换: {'✓' if topic_switched else '✗'}")
    print(f"  旧话题清理: {'✓' if old_topic_cleared else '✗'}")
    
    # 验证
    passed = topic_switched
    score = 100 if passed else 50
    
    return TestResult(
        name="话题切换清理",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L2,
        details={
            "has_hotel_context": has_hotel,
            "has_flight_context": has_flight,
            "topic_switched": topic_switched,
            "current_entities": cm.key_facts
        }
    )


def test_long_distance_reference() -> TestResult:
    """测试5: 长距离引用"""
    print("\n" + "="*60)
    print("🧪 测试5: 长距离引用")
    print("="*60)
    print("目标: 验证能否引用10轮前的信息")
    
    cm = ContextManager(max_tokens=2000, strategy="summarize")
    
    # 第1轮：记录重要信息
    print("\n[第1轮] 记录关键信息:")
    important_info = {"booking_id": "BK123456", "user_id": "USER789", "amount": 1500}
    cm.add_message("user", f"我要预订，订单号是{important_info['booking_id']}", important_info)
    cm.add_message("assistant", "已记录订单信息")
    print(f"  记录: {important_info}")
    
    # 中间8轮：其他对话
    print("\n[第2-9轮] 中间对话:")
    for i in range(8):
        cm.add_message("user", f"咨询其他问题{i+1}")
        cm.add_message("assistant", f"回答其他问题{i+1}")
    print(f"  已完成8轮其他对话")
    
    # 第10轮：引用早期信息
    print("\n[第10轮] 尝试引用早期信息:")
    cm.add_message("user", "我刚才的订单号是多少？")
    
    # 检查早期信息是否可访问
    booking_id_retained = cm.check_fact_retention("booking_id")
    user_id_retained = cm.check_fact_retention("user_id")
    amount_retained = cm.check_fact_retention("amount")
    
    print(f"  booking_id保留: {'✓' if booking_id_retained else '✗'}")
    print(f"  user_id保留: {'✓' if user_id_retained else '✗'}")
    print(f"  amount保留: {'✓' if amount_retained else '✗'}")
    
    print(f"\n上下文状态:")
    print(f"  Token使用: {cm.get_token_count()}")
    print(f"  历史长度: {cm.get_history_length()}")
    print(f"  关键事实: {cm.key_facts}")
    
    # 验证
    retention_count = sum([booking_id_retained, user_id_retained, amount_retained])
    passed = booking_id_retained  # 至少订单ID要保留
    score = retention_count / 3 * 100
    
    print(f"\n✅ 验证结果:")
    print(f"  - 保留字段: {retention_count}/3")
    print(f"  - 核心字段(booking_id): {'✓' if booking_id_retained else '✗'}")
    print(f"  - 结果: {'✓ 通过' if passed else '✗ 失败'}")
    
    return TestResult(
        name="长距离引用",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L2,
        details={
            "distance": "10轮",
            "retention_count": retention_count,
            "booking_id_retained": booking_id_retained,
            "key_facts": cm.key_facts
        }
    )


def test_context_compression() -> TestResult:
    """测试6: 上下文压缩"""
    print("\n" + "="*60)
    print("🧪 测试6: 上下文压缩")
    print("="*60)
    print("目标: 验证摘要压缩后关键实体是否保留")
    
    cm = ContextManager(max_tokens=1000, strategy="summarize")
    
    # 添加多轮对话
    print("\n添加15轮详细对话:")
    entities_list = [
        {"city": "北京", "hotel": "希尔顿"},
        {"date": "2024-01-15", "nights": 3},
        {"room_type": "豪华套房", "price": 1200},
        {"guest_name": "张三", "phone": "13800138000"},
        {"breakfast": True, "smoking": False}
    ]
    
    for i, entities in enumerate(entities_list):
        cm.add_message("user", f"详细信息{i+1}: " + json.dumps(entities, ensure_ascii=False), entities)
        cm.add_message("assistant", f"确认信息{i+1}")
    
    # 添加更多对话触发摘要
    print("添加更多对话触发摘要...")
    for i in range(10):
        cm.add_message("user", f"额外对话{i+1}")
        cm.add_message("assistant", f"额外回复{i+1}")
    
    print(f"\n压缩后状态:")
    print(f"  Token使用: {cm.get_token_count()}/{cm.max_tokens}")
    print(f"  历史长度: {cm.get_history_length()}")
    
    # 检查所有关键实体是否保留
    all_entities = {}
    for e in entities_list:
        all_entities.update(e)
    
    print(f"\n关键实体保留检查:")
    retention = {}
    for key in all_entities:
        retained = cm.check_fact_retention(key)
        retention[key] = retained
        status = "✓" if retained else "✗"
        print(f"  {key}: {status}")
    
    retention_rate = sum(retention.values()) / len(retention)
    
    # 检查是否有摘要消息
    has_summary = any(
        msg.get("is_summary") or "[摘要]" in msg.get("content", "")
        for msg in cm.history
    )
    
    print(f"\n摘要检查:")
    print(f"  存在摘要消息: {'✓' if has_summary else '✗'}")
    print(f"  实体保留率: {retention_rate*100:.0f}%")
    
    # 验证
    passed = retention_rate >= 0.6  # 至少60%保留
    score = retention_rate * 100
    
    print(f"\n✅ 验证结果:")
    print(f"  - 保留率: {retention_rate*100:.0f}%")
    print(f"  - 通过阈值: ≥60%")
    print(f"  - 结果: {'✓ 通过' if passed else '✗ 失败'}")
    
    return TestResult(
        name="上下文压缩",
        passed=passed,
        score=score,
        risk_level=RiskLevel.L2,
        details={
            "has_summary": has_summary,
            "retention_rate": retention_rate,
            "total_entities": len(all_entities),
            "retained_entities": sum(retention.values())
        }
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📊 测试汇总报告 - Day 56: 上下文管理与长对话稳定性")
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
                print(f"   - {r.name}")
    else:
        print("✅ 未发现高风险问题")
    
    # 策略建议
    print("\n" + "="*70)
    print("💡 上下文管理策略建议")
    print("="*70)
    
    strategies = {
        "truncate": "截断法",
        "sliding_window": "滑动窗口",
        "summarize": "摘要法"
    }
    
    print("\n不同策略适用场景:")
    print("  • 截断法: 适用于短对话，实现简单")
    print("  • 滑动窗口: 适用于中等长度对话，平衡简单和效果")
    print("  • 摘要法: 适用于长对话，保留关键信息")
    
    print("\n优化建议:")
    if total_score < 70:
        print("• 上下文管理存在严重问题，建议:")
        print("  - 增加关键事实提取和独立存储")
        print("  - 实现系统消息强制保留机制")
        print("  - 引入外部记忆存储(RAG)")
    elif total_score < 85:
        print("• 上下文管理基本可用，建议:")
        print("  - 优化摘要算法，提高关键信息保留率")
        print("  - 增加话题检测和上下文分段")
    else:
        print("• 上下文管理良好，建议:")
        print("  - 持续监控长对话场景")
        print("  - 考虑引入更智能的压缩算法")
    
    print("\n" + "="*70)
    print("请将以上测试结果贴回给Trae，生成详细的质量分析报告")
    print("="*70)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 56: 上下文管理与长对话稳定性")
    print("="*70)
    print("\n测试目标: 验证Agent在资源约束下的上下文管理能力")
    print("测试架构师视角: 上下文窗口是有限的资源，长对话必然导致'失忆'")
    
    results = [
        test_context_window_boundary(),
        test_long_dialogue_stability(),
        test_system_message_protection(),
        test_topic_switch_cleanup(),
        test_long_distance_reference(),
        test_context_compression()
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
