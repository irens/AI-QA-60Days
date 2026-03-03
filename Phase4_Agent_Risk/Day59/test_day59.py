"""
Day 59: Agent审计日志系统测试
目标：验证审计日志的完整性、安全性和合规性
测试架构师视角：审计日志缺失 = 无法定责 = 合规风险
难度级别：实战
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from enum import Enum


class RiskLevel(Enum):
    """风险等级"""
    CRITICAL = "L1"
    HIGH = "L2"
    MEDIUM = "L3"
    LOW = "L4"


@dataclass
class AuditLogEntry:
    """审计日志条目"""
    timestamp: str
    action_type: str
    actor: str
    target: str
    result: str
    request_id: str
    session_id: Optional[str] = None
    client_info: Optional[Dict] = None
    input_params: Optional[Dict] = None
    output_result: Optional[Any] = None
    duration_ms: Optional[int] = None
    risk_score: Optional[float] = None
    seq_no: Optional[int] = None
    hash: Optional[str] = None
    prev_hash: Optional[str] = None


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: str
    details: Dict[str, Any] = field(default_factory=dict)


class AuditLogValidator:
    """审计日志验证器"""
    
    # 必填字段
    REQUIRED_FIELDS = ["timestamp", "action_type", "actor", "target", "result", "request_id"]
    
    # 敏感信息模式
    SENSITIVE_PATTERNS = {
        "id_card": r"\d{17}[\dXx]|\d{15}",
        "phone": r"1[3-9]\d{9}",
        "bank_card": r"\d{16,19}",
        "password": r"password[\"'\s]*[:=][\"'\s]*[^\s&]+",
        "token": r"[Bb]earer\s+[a-zA-Z0-9_-]{20,}",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    }
    
    # 高风险操作类型
    HIGH_RISK_ACTIONS = ["transfer", "delete", "update_permission", "access_sensitive_data"]
    
    def __init__(self):
        self.issues: List[str] = []
    
    def validate_completeness(self, log: AuditLogEntry) -> Dict[str, Any]:
        """验证日志完整性"""
        missing_fields = []
        log_dict = log.__dict__
        
        for field in self.REQUIRED_FIELDS:
            if field not in log_dict or log_dict[field] is None:
                missing_fields.append(field)
        
        return {
            "is_complete": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "completeness_score": (len(self.REQUIRED_FIELDS) - len(missing_fields)) / len(self.REQUIRED_FIELDS) * 100
        }
    
    def validate_sensitive_data(self, log: AuditLogEntry) -> Dict[str, Any]:
        """验证敏感信息泄露"""
        leaked_fields = []
        log_dict = log.__dict__
        
        # 检查所有字符串字段
        for key, value in log_dict.items():
            if isinstance(value, str):
                for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
                    if re.search(pattern, value):
                        leaked_fields.append(f"{key}包含{pattern_name}")
            elif isinstance(value, dict):
                value_str = json.dumps(value)
                for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
                    if re.search(pattern, value_str):
                        leaked_fields.append(f"{key}包含{pattern_name}")
        
        return {
            "is_clean": len(leaked_fields) == 0,
            "leaked_fields": leaked_fields,
            "leak_count": len(leaked_fields)
        }
    
    def validate_chain_integrity(self, logs: List[AuditLogEntry]) -> Dict[str, Any]:
        """验证日志链完整性（防篡改）"""
        issues = []
        
        # 1. 检查时间戳顺序
        timestamps = []
        for log in logs:
            if log.timestamp:
                try:
                    ts = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
                    timestamps.append((log.seq_no, ts))
                except:
                    issues.append(f"seq_no {log.seq_no} 时间戳格式错误")
        
        if timestamps:
            sorted_ts = sorted(timestamps, key=lambda x: x[1])
            if timestamps != sorted_ts:
                issues.append("时间戳顺序异常，可能存在日志删除或插入")
        
        # 2. 检查序列号连续性
        seq_nos = sorted([log.seq_no for log in logs if log.seq_no is not None])
        if seq_nos:
            expected = list(range(min(seq_nos), max(seq_nos) + 1))
            missing = set(expected) - set(seq_nos)
            if missing:
                issues.append(f"序列号不连续，缺失: {missing}")
        
        # 3. 检查哈希链
        for i in range(1, len(logs)):
            curr_log = logs[i]
            prev_log = logs[i-1]
            
            if curr_log.prev_hash and prev_log.hash:
                if curr_log.prev_hash != prev_log.hash:
                    issues.append(f"哈希链断裂在 seq_no {prev_log.seq_no} 和 {curr_log.seq_no} 之间")
        
        return {
            "is_intact": len(issues) == 0,
            "issues": issues,
            "total_logs": len(logs)
        }
    
    def validate_traceability(self, logs: List[AuditLogEntry], request_id: str) -> Dict[str, Any]:
        """验证操作链可追溯性"""
        related_logs = [log for log in logs if log.request_id == request_id]
        
        if not related_logs:
            return {
                "is_traceable": False,
                "chain_length": 0,
                "has_start": False,
                "has_end": False
            }
        
        # 检查是否有开始和结束
        action_types = [log.action_type for log in related_logs]
        has_start = any("start" in a or "begin" in a for a in action_types)
        has_end = any("end" in a or "complete" in a or "finish" in a for a in action_types)
        
        return {
            "is_traceable": len(related_logs) >= 1,
            "chain_length": len(related_logs),
            "has_start": has_start,
            "has_end": has_end,
            "actions": action_types
        }
    
    def validate_high_risk_operation(self, log: AuditLogEntry) -> Dict[str, Any]:
        """验证高风险操作审计"""
        is_high_risk = log.action_type in self.HIGH_RISK_ACTIONS
        
        if not is_high_risk:
            return {"is_high_risk": False, "audit_complete": True}
        
        # 高风险操作需要额外的审计字段
        required_for_high_risk = ["risk_score", "duration_ms"]
        missing = []
        log_dict = log.__dict__
        
        for field in required_for_high_risk:
            if field not in log_dict or log_dict[field] is None:
                missing.append(field)
        
        return {
            "is_high_risk": True,
            "audit_complete": len(missing) == 0,
            "missing_fields": missing
        }


def generate_complete_audit_log() -> AuditLogEntry:
    """生成完整的审计日志"""
    return AuditLogEntry(
        timestamp="2024-01-15T10:00:00.123Z",
        action_type="query",
        actor="user_12345",
        target="weather_api",
        result="success",
        request_id="req_abc123",
        session_id="sess_xyz789",
        client_info={"ip": "192.168.1.1", "device": "mobile", "version": "1.2.3"},
        input_params={"city": "北京", "date": "today"},
        output_result={"weather": "sunny", "temp": "22C"},
        duration_ms=150,
        risk_score=0.1,
        seq_no=1,
        hash="a1b2c3d4",
        prev_hash="00000000"
    )


def generate_missing_field_log() -> AuditLogEntry:
    """生成缺少必填字段的日志"""
    return AuditLogEntry(
        timestamp="2024-01-15T10:00:01Z",
        action_type="query",
        actor="user_12345",
        target="weather_api",
        result="success",
        request_id=None,  # 缺失！
        seq_no=2
    )


def generate_sensitive_data_log() -> AuditLogEntry:
    """生成包含敏感信息的日志"""
    return AuditLogEntry(
        timestamp="2024-01-15T10:00:02Z",
        action_type="login",
        actor="user_12345",
        target="auth_system",
        result="success",
        request_id="req_def456",
        input_params={
            "username": "zhangsan",
            "password": "MySecret123!",  # 敏感信息！
            "phone": "13800138000"  # 敏感信息！
        },
        seq_no=3
    )


def generate_high_risk_incomplete_log() -> AuditLogEntry:
    """生成高风险操作但审计不完整的日志"""
    return AuditLogEntry(
        timestamp="2024-01-15T10:00:03Z",
        action_type="transfer",  # 高风险操作
        actor="user_12345",
        target="bank_api",
        result="success",
        request_id="req_ghi789",
        input_params={"amount": 10000, "to_account": "****5678"},
        # 缺少 risk_score 和 duration_ms
        seq_no=4
    )


def generate_log_chain() -> List[AuditLogEntry]:
    """生成完整的日志链（用于完整性测试）"""
    logs = []
    prev_hash = "00000000"
    
    for i in range(1, 6):
        log_data = {
            "timestamp": f"2024-01-15T10:00:0{i}Z",
            "action_type": "query",
            "actor": "user_12345",
            "target": f"api_{i}",
            "result": "success",
            "request_id": f"req_{i:03d}",
            "seq_no": i
        }
        
        # 计算哈希
        hash_content = json.dumps(log_data, sort_keys=True)
        curr_hash = hashlib.sha256(hash_content.encode()).hexdigest()[:8]
        
        log = AuditLogEntry(
            **log_data,
            hash=curr_hash,
            prev_hash=prev_hash
        )
        logs.append(log)
        prev_hash = curr_hash
    
    return logs


def generate_tampered_log_chain() -> List[AuditLogEntry]:
    """生成被篡改的日志链"""
    logs = generate_log_chain()
    # 篡改第3条日志的时间戳
    logs[2].timestamp = "2024-01-15T09:59:00Z"  # 时间倒流
    return logs


def generate_broken_hash_chain() -> List[AuditLogEntry]:
    """生成哈希链断裂的日志"""
    logs = generate_log_chain()
    # 修改第3条日志的prev_hash
    logs[2].prev_hash = "wrong_hash"
    return logs


def test_log_completeness() -> TestResult:
    """测试1: 审计日志完整性验证"""
    print("\n" + "="*60)
    print("🧪 测试1: 审计日志完整性验证")
    print("="*60)
    
    validator = AuditLogValidator()
    
    # 测试完整日志
    complete_log = generate_complete_audit_log()
    result_complete = validator.validate_completeness(complete_log)
    
    print("完整日志验证:")
    print(f"  完整性: {'✅ 通过' if result_complete['is_complete'] else '❌ 失败'}")
    print(f"  完整度评分: {result_complete['completeness_score']:.0f}%")
    
    # 测试不完整日志
    incomplete_log = generate_missing_field_log()
    result_incomplete = validator.validate_completeness(incomplete_log)
    
    print("\n不完整日志验证:")
    print(f"  完整性: {'✅ 通过' if result_incomplete['is_complete'] else '❌ 失败'}")
    print(f"  缺失字段: {result_incomplete['missing_fields']}")
    print(f"  完整度评分: {result_incomplete['completeness_score']:.0f}%")
    
    passed = result_complete['is_complete'] and not result_incomplete['is_complete']
    return TestResult(
        name="审计日志完整性验证",
        passed=passed,
        score=100 if passed else 50,
        risk_level="L1" if not passed else "L3",
        details={
            "complete_log_score": result_complete['completeness_score'],
            "incomplete_log_detected": not result_incomplete['is_complete']
        }
    )


def test_required_field_detection() -> TestResult:
    """测试2: 必填字段缺失检测"""
    print("\n" + "="*60)
    print("🧪 测试2: 必填字段缺失检测")
    print("="*60)
    
    validator = AuditLogValidator()
    
    print(f"必填字段列表: {validator.REQUIRED_FIELDS}")
    
    # 测试各种缺失场景
    test_cases = [
        ("缺少request_id", generate_missing_field_log()),
        ("完整日志", generate_complete_audit_log())
    ]
    
    all_detected = True
    for name, log in test_cases:
        result = validator.validate_completeness(log)
        status = "✅ 完整" if result['is_complete'] else f"❌ 缺失: {result['missing_fields']}"
        print(f"  {name}: {status}")
        
        if name.startswith("缺少") and result['is_complete']:
            all_detected = False
    
    return TestResult(
        name="必填字段缺失检测",
        passed=all_detected,
        score=100 if all_detected else 0,
        risk_level="L1" if not all_detected else "L2",
        details={"all_missing_detected": all_detected}
    )


def test_sensitive_data_detection() -> TestResult:
    """测试3: 敏感信息脱敏验证"""
    print("\n" + "="*60)
    print("🧪 测试3: 敏感信息脱敏验证")
    print("="*60)
    
    validator = AuditLogValidator()
    
    # 测试包含敏感信息的日志
    sensitive_log = generate_sensitive_data_log()
    result = validator.validate_sensitive_data(sensitive_log)
    
    print("敏感信息检测:")
    print(f"  输入参数: {sensitive_log.input_params}")
    print(f"  是否干净: {'✅ 是' if result['is_clean'] else '❌ 否'}")
    print(f"  泄露字段数: {result['leak_count']}")
    
    if result['leaked_fields']:
        print("  检测到的泄露:")
        for field in result['leaked_fields']:
            print(f"    - {field}")
    
    detected = not result['is_clean'] and result['leak_count'] > 0
    print(f"\n敏感信息检测: {'✅ 正确识别' if detected else '❌ 未识别'}")
    
    return TestResult(
        name="敏感信息脱敏验证",
        passed=detected,
        score=100 if detected else 0,
        risk_level="L1" if not detected else "L2",
        details={
            "leak_detected": detected,
            "leak_count": result['leak_count']
        }
    )


def test_tamper_detection() -> TestResult:
    """测试4: 日志篡改检测"""
    print("\n" + "="*60)
    print("🧪 测试4: 日志篡改检测")
    print("="*60)
    
    validator = AuditLogValidator()
    
    # 测试正常日志链
    normal_chain = generate_log_chain()
    result_normal = validator.validate_chain_integrity(normal_chain)
    
    print("正常日志链验证:")
    print(f"  完整性: {'✅ 通过' if result_normal['is_intact'] else '❌ 失败'}")
    print(f"  日志数量: {result_normal['total_logs']}")
    
    # 测试时间戳篡改
    tampered_chain = generate_tampered_log_chain()
    result_tampered = validator.validate_chain_integrity(tampered_chain)
    
    print("\n时间戳篡改检测:")
    print(f"  篡改后时间戳: {tampered_chain[2].timestamp}")
    print(f"  完整性: {'✅ 通过' if result_tampered['is_intact'] else '❌ 检测到异常'}")
    if result_tampered['issues']:
        print(f"  检测到问题: {result_tampered['issues']}")
    
    # 测试哈希链断裂
    broken_chain = generate_broken_hash_chain()
    result_broken = validator.validate_chain_integrity(broken_chain)
    
    print("\n哈希链断裂检测:")
    print(f"  完整性: {'✅ 通过' if result_broken['is_intact'] else '❌ 检测到异常'}")
    if result_broken['issues']:
        print(f"  检测到问题: {result_broken['issues']}")
    
    detected = not result_tampered['is_intact'] or not result_broken['is_intact']
    return TestResult(
        name="日志篡改检测",
        passed=detected,
        score=100 if detected else 0,
        risk_level="L1" if not detected else "L2",
        details={
            "tamper_detected": detected,
            "timestamp_anomaly": not result_tampered['is_intact'],
            "hash_break_detected": not result_broken['is_intact']
        }
    )


def test_traceability() -> TestResult:
    """测试5: 操作链可追溯性验证"""
    print("\n" + "="*60)
    print("🧪 测试5: 操作链可追溯性验证")
    print("="*60)
    
    validator = AuditLogValidator()
    
    # 生成具有相同request_id的日志链
    logs = []
    base_time = datetime(2024, 1, 15, 10, 0, 0)
    request_id = "req_trace_001"
    
    actions = ["query_start", "retrieve_context", "call_tool", "generate_answer", "query_complete"]
    for i, action in enumerate(actions):
        log = AuditLogEntry(
            timestamp=(base_time.replace(second=i)).isoformat() + "Z",
            action_type=action,
            actor="user_12345",
            target="rag_system",
            result="success",
            request_id=request_id,
            seq_no=i+1
        )
        logs.append(log)
    
    result = validator.validate_traceability(logs, request_id)
    
    print(f"Request ID: {request_id}")
    print(f"操作链长度: {result['chain_length']}")
    print(f"操作列表: {result['actions']}")
    print(f"可追溯性: {'✅ 良好' if result['is_traceable'] else '❌ 不足'}")
    print(f"有开始标记: {'✅' if result['has_start'] else '❌'}")
    print(f"有结束标记: {'✅' if result['has_end'] else '❌'}")
    
    traceable = result['is_traceable'] and result['has_start'] and result['has_end']
    return TestResult(
        name="操作链可追溯性验证",
        passed=traceable,
        score=100 if traceable else 60,
        risk_level="L2" if not traceable else "L3",
        details={
            "chain_length": result['chain_length'],
            "has_start": result['has_start'],
            "has_end": result['has_end']
        }
    )


def test_high_risk_audit() -> TestResult:
    """测试6: 高风险操作审计完整性"""
    print("\n" + "="*60)
    print("🧪 测试6: 高风险操作审计完整性")
    print("="*60)
    
    validator = AuditLogValidator()
    
    print(f"高风险操作类型: {validator.HIGH_RISK_ACTIONS}")
    
    # 测试高风险操作（不完整审计）
    high_risk_log = generate_high_risk_incomplete_log()
    result = validator.validate_high_risk_operation(high_risk_log)
    
    print(f"\n操作类型: {high_risk_log.action_type}")
    print(f"是否高风险: {'✅ 是' if result['is_high_risk'] else '❌ 否'}")
    print(f"审计完整: {'✅ 是' if result['audit_complete'] else '❌ 否'}")
    
    if not result['audit_complete']:
        print(f"缺失字段: {result['missing_fields']}")
    
    # 测试普通操作
    normal_log = generate_complete_audit_log()
    result_normal = validator.validate_high_risk_operation(normal_log)
    
    print(f"\n普通操作类型: {normal_log.action_type}")
    print(f"是否高风险: {'✅ 是' if result_normal['is_high_risk'] else '❌ 否'}")
    
    # 验证是否正确识别高风险操作和缺失字段
    correct_identification = (
        result['is_high_risk'] and 
        not result['audit_complete'] and 
        not result_normal['is_high_risk']
    )
    
    print(f"\n高风险识别准确性: {'✅ 正确' if correct_identification else '❌ 错误'}")
    
    return TestResult(
        name="高风险操作审计完整性",
        passed=correct_identification,
        score=100 if correct_identification else 50,
        risk_level="L2" if not correct_identification else "L3",
        details={
            "high_risk_detected": result['is_high_risk'],
            "audit_complete": result['audit_complete']
        }
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 Agent审计日志系统测试汇总报告")
    print("="*70)
    
    total_score = sum(r.score for r in results) / len(results)
    passed_count = sum(1 for r in results if r.passed)
    l1_risks = sum(1 for r in results if r.risk_level == "L1")
    l2_risks = sum(1 for r in results if r.risk_level == "L2")
    
    print(f"\n总体评分: {total_score:.1f}/100")
    print(f"通过测试: {passed_count}/{len(results)}")
    print(f"高风险项: {l1_risks}个 | 中风险项: {l2_risks}个")
    
    print("\n详细结果:")
    print("-" * 70)
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"{status} {r.name:30s} | 评分: {r.score:3.0f} | 风险: {r.risk_level}")
    
    print("\n" + "="*70)
    print("关键发现:")
    if l1_risks > 0:
        print("⚠️  发现高风险问题！审计日志系统存在严重缺陷，合规风险极高。")
        print("   建议立即修复日志完整性验证和篡改检测机制。")
    elif total_score < 80:
        print("⚠️  审计日志系统质量一般，建议优化敏感信息检测和高风险操作审计。")
    else:
        print("✅ 审计日志系统质量良好，具备基本的完整性、安全性和可追溯性。")
    print("="*70)
    
    return total_score


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 59: Agent审计日志系统")
    print("="*70)
    print("测试架构师视角: 审计日志缺失 = 无法定责 = 合规风险")
    
    results = [
        test_log_completeness(),
        test_required_field_detection(),
        test_sensitive_data_detection(),
        test_tamper_detection(),
        test_traceability(),
        test_high_risk_audit()
    ]
    
    final_score = print_summary(results)
    
    print("\n✅ 测试执行完毕，请将上方日志发给 Trae 生成报告。")
    return final_score


if __name__ == "__main__":
    run_all_tests()
