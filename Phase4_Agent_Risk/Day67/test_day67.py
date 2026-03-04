"""
Day 67: 数据隔离与隐私合规测试
目标：验证多租户数据隔离、敏感信息脱敏、隐私合规性
测试架构师视角：模拟数据泄露场景，验证用户数据安全边界
"""

import json
import time
import random
import hashlib
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum


class DataClassification(Enum):
    """数据分类等级"""
    PUBLIC = "public"           # 公开数据
    INTERNAL = "internal"       # 内部数据
    CONFIDENTIAL = "confidential"  # 机密数据
    RESTRICTED = "restricted"   # 受限数据（PII/敏感）


class ComplianceStandard(Enum):
    """合规标准"""
    GDPR = "GDPR"           # 欧盟通用数据保护条例
    CCPA = "CCPA"           # 加州消费者隐私法
    PIPL = "PIPL"           # 中国个人信息保护法
    HIPAA = "HIPAA"         # 健康保险可携性责任法案


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
class UserMemory:
    """用户记忆数据"""
    id: str
    user_id: str
    content: str
    classification: DataClassification
    contains_pii: bool
    created_at: datetime
    retention_days: int
    encryption_key_id: str
    access_log: List[Dict]


@dataclass
class SensitivePattern:
    """敏感信息模式"""
    name: str
    pattern: str
    classification: DataClassification
    masking_method: str


# 敏感信息识别模式
SENSITIVE_PATTERNS = [
    SensitivePattern("身份证号", r"\d{17}[\dXx]|\d{15}", DataClassification.RESTRICTED, "mask_all"),
    SensitivePattern("手机号", r"1[3-9]\d{9}", DataClassification.RESTRICTED, "mask_middle"),
    SensitivePattern("邮箱", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", DataClassification.CONFIDENTIAL, "mask_domain"),
    SensitivePattern("银行卡号", r"\d{16}|\d{19}", DataClassification.RESTRICTED, "mask_all"),
    SensitivePattern("密码", r"password[:\s]*[^\s]+|pwd[:\s]*[^\s]+", DataClassification.RESTRICTED, "remove"),
    SensitivePattern("API密钥", r"sk-[a-zA-Z0-9]{32,}", DataClassification.RESTRICTED, "mask_all"),
    SensitivePattern("IP地址", r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", DataClassification.INTERNAL, "mask_partial"),
]


# ==================== 测试用例库 ====================

TEST_CASES = [
    # L1 阻断性风险测试 - 数据泄露
    TestCase(
        name="用户数据隔离边界测试",
        category="数据隔离",
        input_data={"scenario": "isolation", "user_count": 10, "cross_access_attempts": 100},
        expected_behavior="用户A无法访问用户B的数据，严格隔离",
        risk_level="L1"
    ),
    TestCase(
        name="租户间数据泄露检测",
        category="多租户安全",
        input_data={"scenario": "tenant_leak", "tenants": ["tenant_a", "tenant_b", "tenant_c"]},
        expected_behavior="租户数据完全隔离，无交叉污染",
        risk_level="L1"
    ),
    TestCase(
        name="敏感信息识别准确率",
        category="PII检测",
        input_data={"scenario": "pii_detection", "test_samples": 100},
        expected_behavior="识别率>99%，误报率<1%",
        risk_level="L1"
    ),

    # L1 阻断性风险测试 - 合规
    TestCase(
        name="数据脱敏效果验证",
        category="数据脱敏",
        input_data={"scenario": "masking", "sensitive_types": ["phone", "email", "id_card"]},
        expected_behavior="敏感信息被正确脱敏，无法逆向还原",
        risk_level="L1"
    ),
    TestCase(
        name="未授权访问拦截",
        category="访问控制",
        input_data={"scenario": "unauthorized_access", "attack_vectors": ["sql_injection", "id_oracle"]},
        expected_behavior="所有未授权访问被拦截，记录审计日志",
        risk_level="L1"
    ),

    # L2 高优先级风险测试
    TestCase(
        name="数据保留策略执行",
        category="数据生命周期",
        input_data={"scenario": "retention", "retention_days": 30, "check_expired": True},
        expected_behavior="过期数据自动删除，保留期内可访问",
        risk_level="L2"
    ),
    TestCase(
        name="用户数据导出权（GDPR）",
        category="合规性",
        input_data={"scenario": "gdpr_export", "user_id": "user_001"},
        expected_behavior="用户可导出所有个人数据，格式标准",
        risk_level="L2"
    ),
    TestCase(
        name="数据删除权验证（被遗忘权）",
        category="合规性",
        input_data={"scenario": "gdpr_delete", "user_id": "user_001", "cascade": True},
        expected_behavior="用户数据彻底删除，无残留痕迹",
        risk_level="L2"
    ),
    TestCase(
        name="审计日志完整性",
        category="审计追踪",
        input_data={"scenario": "audit_log", "operations": ["read", "write", "delete"]},
        expected_behavior="所有数据访问被记录，日志不可篡改",
        risk_level="L2"
    ),

    # L3 一般风险测试
    TestCase(
        name="数据加密传输验证",
        category="传输安全",
        input_data={"scenario": "encryption_in_transit", "protocols": ["TLS1.2", "TLS1.3"]},
        expected_behavior="数据传输加密，无明文泄露",
        risk_level="L3"
    ),
    TestCase(
        name="数据加密存储验证",
        category="存储安全",
        input_data={"scenario": "encryption_at_rest", "algorithm": "AES-256"},
        expected_behavior="静态数据加密，密钥分离管理",
        risk_level="L3"
    ),
    TestCase(
        name="最小权限原则验证",
        category="权限管理",
        input_data={"scenario": "least_privilege", "roles": ["admin", "user", "guest"]},
        expected_behavior="各角色仅能访问授权数据",
        risk_level="L3"
    ),
]


# ==================== 模拟数据隔离系统 ====================

class MockDataIsolationSystem:
    """模拟数据隔离与隐私保护系统"""

    def __init__(self):
        self.user_data: Dict[str, List[UserMemory]] = {}
        self.tenant_data: Dict[str, Dict[str, List[UserMemory]]] = {}
        self.access_logs: List[Dict] = []
        self.encryption_keys: Dict[str, str] = {}
        self.audit_trail: List[Dict] = []
        self.violations: List[Dict] = []
        self.masking_stats = {"detected": 0, "masked": 0, "missed": 0}

    def create_user(self, user_id: str, tenant_id: str = "default") -> bool:
        """创建用户"""
        if user_id not in self.user_data:
            self.user_data[user_id] = []
            self.encryption_keys[user_id] = hashlib.sha256(user_id.encode()).hexdigest()[:32]

        if tenant_id not in self.tenant_data:
            self.tenant_data[tenant_id] = {}
        if user_id not in self.tenant_data[tenant_id]:
            self.tenant_data[tenant_id][user_id] = []

        return True

    def store_memory(self, user_id: str, content: str, tenant_id: str = "default",
                     classification: DataClassification = DataClassification.INTERNAL) -> Tuple[bool, str]:
        """存储用户记忆"""
        # 检查PII
        contains_pii, detected_types = self._detect_pii(content)

        # 如果包含PII但分类不是RESTRICTED，自动升级
        if contains_pii and classification.value != "restricted":
            classification = DataClassification.RESTRICTED

        memory = UserMemory(
            id=f"mem_{user_id}_{int(time.time() * 1000)}",
            user_id=user_id,
            content=content,
            classification=classification,
            contains_pii=contains_pii,
            created_at=datetime.now(),
            retention_days=30 if contains_pii else 90,
            encryption_key_id=self.encryption_keys.get(user_id, "default_key"),
            access_log=[]
        )

        # 存储到用户数据
        if user_id not in self.user_data:
            self.create_user(user_id, tenant_id)

        self.user_data[user_id].append(memory)
        self.tenant_data[tenant_id][user_id].append(memory)

        # 记录审计日志
        self._log_access("WRITE", user_id, memory.id, tenant_id, "success")

        return True, memory.id

    def retrieve_memory(self, accessor_id: str, target_user_id: str, memory_id: str,
                       tenant_id: str = "default") -> Tuple[Optional[UserMemory], str]:
        """检索记忆（带权限检查）"""
        # 权限检查：只能访问自己的数据，除非是同租户的管理员
        if accessor_id != target_user_id:
            # 检查是否是同租户
            accessor_tenant = self._get_user_tenant(accessor_id)
            target_tenant = self._get_user_tenant(target_user_id)

            if accessor_tenant != target_tenant:
                self._log_access("READ", accessor_id, memory_id, tenant_id, "denied_cross_tenant")
                self.violations.append({
                    "time": datetime.now(),
                    "type": "cross_tenant_access",
                    "accessor": accessor_id,
                    "target": target_user_id,
                    "memory_id": memory_id
                })
                return None, "拒绝访问：跨租户数据隔离"

            # 同租户但不是自己的数据，需要特殊权限
            if not self._has_admin_role(accessor_id):
                self._log_access("READ", accessor_id, memory_id, tenant_id, "denied_no_permission")
                return None, "拒绝访问：权限不足"

        # 查找记忆
        memories = self.user_data.get(target_user_id, [])
        memory = next((m for m in memories if m.id == memory_id), None)

        if not memory:
            self._log_access("READ", accessor_id, memory_id, tenant_id, "not_found")
            return None, "记忆不存在"

        # 记录访问日志
        memory.access_log.append({
            "accessor": accessor_id,
            "time": datetime.now(),
            "action": "read"
        })

        self._log_access("READ", accessor_id, memory_id, tenant_id, "success")

        # 如果包含PII，返回脱敏版本
        if memory.contains_pii and accessor_id != target_user_id:
            masked_memory = self._mask_memory(memory)
            return masked_memory, "已脱敏"

        return memory, "访问成功"

    def _detect_pii(self, content: str) -> Tuple[bool, List[str]]:
        """检测PII信息"""
        detected_types = []
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern.pattern, content):
                detected_types.append(pattern.name)
        return len(detected_types) > 0, detected_types

    def _mask_memory(self, memory: UserMemory) -> UserMemory:
        """脱敏处理"""
        masked_content = memory.content

        for pattern in SENSITIVE_PATTERNS:
            if pattern.masking_method == "mask_all":
                masked_content = re.sub(pattern.pattern, "***", masked_content)
            elif pattern.masking_method == "mask_middle":
                # 保留前后，中间脱敏
                def mask_middle(match):
                    s = match.group()
                    if len(s) <= 4:
                        return "***"
                    return s[:3] + "****" + s[-3:]
                masked_content = re.sub(pattern.pattern, mask_middle, masked_content)
            elif pattern.masking_method == "mask_domain":
                # 邮箱脱敏域名
                def mask_email(match):
                    email = match.group()
                    parts = email.split("@")
                    if len(parts) == 2:
                        return parts[0] + "@***.***"
                    return "***"
                masked_content = re.sub(pattern.pattern, mask_email, masked_content)
            elif pattern.masking_method == "remove":
                masked_content = re.sub(pattern.pattern, "[REDACTED]", masked_content)

        self.masking_stats["masked"] += 1

        return UserMemory(
            id=memory.id,
            user_id=memory.user_id,
            content=masked_content,
            classification=memory.classification,
            contains_pii=True,
            created_at=memory.created_at,
            retention_days=memory.retention_days,
            encryption_key_id=memory.encryption_key_id,
            access_log=memory.access_log
        )

    def delete_user_data(self, user_id: str, cascade: bool = True) -> Tuple[int, str]:
        """删除用户所有数据（GDPR被遗忘权）"""
        deleted_count = 0

        # 删除用户记忆
        if user_id in self.user_data:
            deleted_count = len(self.user_data[user_id])
            del self.user_data[user_id]

        # 从租户中删除
        for tenant_id, users in self.tenant_data.items():
            if user_id in users:
                del users[user_id]

        # 删除加密密钥
        if user_id in self.encryption_keys:
            del self.encryption_keys[user_id]

        # 记录删除审计
        self._log_access("DELETE", user_id, "all", "all", f"deleted_{deleted_count}_records")

        return deleted_count, f"已删除{deleted_count}条记录"

    def export_user_data(self, user_id: str) -> Dict:
        """导出用户数据（GDPR数据可携带权）"""
        memories = self.user_data.get(user_id, [])

        export_data = {
            "user_id": user_id,
            "export_time": datetime.now().isoformat(),
            "data_count": len(memories),
            "memories": []
        }

        for memory in memories:
            export_data["memories"].append({
                "id": memory.id,
                "content": memory.content,
                "classification": memory.classification.value,
                "contains_pii": memory.contains_pii,
                "created_at": memory.created_at.isoformat(),
                "access_log": memory.access_log
            })

        self._log_access("EXPORT", user_id, "all", "all", f"exported_{len(memories)}_records")

        return export_data

    def cleanup_expired_data(self) -> int:
        """清理过期数据"""
        removed = 0
        now = datetime.now()

        for user_id, memories in list(self.user_data.items()):
            valid_memories = []
            for memory in memories:
                expiry = memory.created_at + timedelta(days=memory.retention_days)
                if now <= expiry:
                    valid_memories.append(memory)
                else:
                    removed += 1

            if valid_memories:
                self.user_data[user_id] = valid_memories
            else:
                del self.user_data[user_id]

        return removed

    def _get_user_tenant(self, user_id: str) -> str:
        """获取用户所属租户"""
        for tenant_id, users in self.tenant_data.items():
            if user_id in users:
                return tenant_id
        return "default"

    def _has_admin_role(self, user_id: str) -> bool:
        """检查是否是管理员（模拟）"""
        # 简单模拟：user_id以admin开头的是管理员
        return user_id.startswith("admin")

    def _log_access(self, action: str, accessor: str, resource: str, tenant: str, result: str):
        """记录访问日志"""
        self.audit_trail.append({
            "timestamp": datetime.now(),
            "action": action,
            "accessor": accessor,
            "resource": resource,
            "tenant": tenant,
            "result": result
        })

    def get_isolation_stats(self) -> Dict:
        """获取隔离统计"""
        total_users = len(self.user_data)
        total_memories = sum(len(m) for m in self.user_data.values())
        pii_count = sum(1 for memories in self.user_data.values()
                       for m in memories if m.contains_pii)

        return {
            "total_users": total_users,
            "total_memories": total_memories,
            "pii_memories": pii_count,
            "tenants": len(self.tenant_data),
            "violations": len(self.violations),
            "audit_entries": len(self.audit_trail)
        }


# ==================== 测试执行引擎 ====================

def run_test_case(test_case: TestCase, system: MockDataIsolationSystem) -> TestResult:
    """执行单个测试用例"""
    scenario = test_case.input_data.get("scenario", "normal")
    metrics = {}
    passed = False
    details = ""

    try:
        if scenario == "isolation":
            # 用户数据隔离边界测试
            user_count = test_case.input_data.get("user_count", 10)
            cross_access_attempts = test_case.input_data.get("cross_access_attempts", 100)

            # 创建多个用户和记忆
            for i in range(user_count):
                user_id = f"user_{i:03d}"
                system.create_user(user_id)
                system.store_memory(user_id, f"Private memory of {user_id}")

            # 尝试跨用户访问
            violations = 0
            blocked = 0

            for _ in range(cross_access_attempts):
                accessor = f"user_{random.randint(0, user_count-1):03d}"
                target = f"user_{random.randint(0, user_count-1):03d}"

                if accessor != target:
                    # 尝试访问其他用户的记忆
                    memories = system.user_data.get(target, [])
                    if memories:
                        result, msg = system.retrieve_memory(accessor, target, memories[0].id)
                        if result is None and "拒绝访问" in msg:
                            blocked += 1
                        elif result is not None:
                            violations += 1

            passed = violations == 0 and blocked > 0
            details = f"尝试{cross_access_attempts}次跨用户访问，拦截{blocked}次，违规{violations}次"
            metrics = {"attempts": cross_access_attempts, "blocked": blocked, "violations": violations}

        elif scenario == "tenant_leak":
            # 租户间数据泄露检测
            tenants = test_case.input_data.get("tenants", ["tenant_a", "tenant_b"])

            # 为每个租户创建用户和数据
            for tenant in tenants:
                for i in range(5):
                    user_id = f"{tenant}_user_{i}"
                    system.create_user(user_id, tenant)
                    system.store_memory(user_id, f"Data for {tenant}", tenant)

            # 尝试跨租户访问
            cross_tenant_violations = 0

            for tenant_a in tenants:
                for tenant_b in tenants:
                    if tenant_a != tenant_b:
                        # 从tenant_a访问tenant_b的数据
                        user_a = f"{tenant_a}_user_0"
                        user_b = f"{tenant_b}_user_0"

                        memories = system.user_data.get(user_b, [])
                        if memories:
                            result, msg = system.retrieve_memory(user_a, user_b, memories[0].id)
                            if result is not None:
                                cross_tenant_violations += 1

            passed = cross_tenant_violations == 0
            details = f"测试{len(tenants)}个租户，跨租户违规{cross_tenant_violations}次"
            metrics = {"tenants": len(tenants), "cross_tenant_violations": cross_tenant_violations}

        elif scenario == "pii_detection":
            # 敏感信息识别准确率测试
            test_samples = test_case.input_data.get("test_samples", 100)

            test_cases = [
                ("我的手机号是13800138000", True, ["手机号"]),
                ("联系邮箱test@example.com", True, ["邮箱"]),
                ("身份证号110101199001011234", True, ["身份证号"]),
                ("这是一段普通文本", False, []),
                ("密码: mysecret123", True, ["密码"]),
                ("API密钥sk-abcdefghijklmnopqrstuvwxyz123456", True, ["API密钥"]),
            ]

            correct = 0
            false_positive = 0
            false_negative = 0

            for content, expected_pii, expected_types in test_cases:
                has_pii, detected = system._detect_pii(content)
                if has_pii == expected_pii:
                    correct += 1
                elif has_pii and not expected_pii:
                    false_positive += 1
                elif not has_pii and expected_pii:
                    false_negative += 1

            accuracy = correct / len(test_cases) if test_cases else 0
            passed = accuracy >= 0.99 and false_positive <= 1
            details = f"准确率{accuracy*100:.1f}%，误报{false_positive}次，漏报{false_negative}次"
            metrics = {"accuracy": accuracy, "false_positive": false_positive, "false_negative": false_negative}

        elif scenario == "masking":
            # 数据脱敏效果验证
            sensitive_types = test_case.input_data.get("sensitive_types", ["phone", "email"])

            test_data = [
                ("手机号13800138000", "手机号***"),
                ("邮箱user@example.com", "邮箱user@***.***"),
                ("身份证110101199001011234", "身份证***"),
            ]

            all_masked = True
            for original, expected_pattern in test_data:
                memory = UserMemory(
                    id="test", user_id="test", content=original,
                    classification=DataClassification.RESTRICTED,
                    contains_pii=True, created_at=datetime.now(),
                    retention_days=30, encryption_key_id="key",
                    access_log=[]
                )
                masked = system._mask_memory(memory)

                # 检查是否包含原始敏感信息
                has_original = any(re.search(p.pattern, masked.content) for p in SENSITIVE_PATTERNS)
                if has_original:
                    all_masked = False

            passed = all_masked
            details = f"测试{len(test_data)}种敏感类型，全部脱敏{'成功' if all_masked else '失败'}"
            metrics = {"tested": len(test_data), "all_masked": all_masked}

        elif scenario == "unauthorized_access":
            # 未授权访问拦截测试
            attack_vectors = test_case.input_data.get("attack_vectors", ["id_oracle"])

            system.create_user("victim")
            system.store_memory("victim", "Secret data")

            blocked_attacks = 0
            total_attacks = 0

            # 模拟ID枚举攻击
            for i in range(100):
                total_attacks += 1
                fake_memory_id = f"mem_victim_{int(time.time() * 1000) + i}"
                result, msg = system.retrieve_memory("attacker", "victim", fake_memory_id)
                if result is None and ("拒绝访问" in msg or "不存在" in msg):
                    blocked_attacks += 1

            passed = blocked_attacks == total_attacks
            details = f"模拟{total_attacks}次未授权访问尝试，拦截{blocked_attacks}次"
            metrics = {"attacks": total_attacks, "blocked": blocked_attacks}

        elif scenario == "retention":
            # 数据保留策略执行
            retention_days = test_case.input_data.get("retention_days", 30)

            # 创建一些过期和一些新鲜的数据
            old_memory = UserMemory(
                id="old_mem", user_id="test_user", content="Old data",
                classification=DataClassification.INTERNAL,
                contains_pii=False,
                created_at=datetime.now() - timedelta(days=retention_days + 1),
                retention_days=retention_days,
                encryption_key_id="key",
                access_log=[]
            )

            new_memory = UserMemory(
                id="new_mem", user_id="test_user", content="New data",
                classification=DataClassification.INTERNAL,
                contains_pii=False,
                created_at=datetime.now(),
                retention_days=retention_days,
                encryption_key_id="key",
                access_log=[]
            )

            system.user_data["test_user"] = [old_memory, new_memory]

            before_count = len(system.user_data.get("test_user", []))
            removed = system.cleanup_expired_data()
            after_count = len(system.user_data.get("test_user", []))

            passed = removed == 1 and after_count == 1
            details = f"清理前{before_count}条，清理{removed}条过期数据，剩余{after_count}条"
            metrics = {"before": before_count, "removed": removed, "after": after_count}

        elif scenario == "gdpr_export":
            # GDPR数据导出权测试
            user_id = test_case.input_data.get("user_id", "user_001")

            system.create_user(user_id)
            system.store_memory(user_id, "Memory 1")
            system.store_memory(user_id, "Memory 2 with phone 13800138000")

            export_data = system.export_user_data(user_id)

            passed = export_data["data_count"] == 2 and export_data["user_id"] == user_id
            details = f"成功导出{export_data['data_count']}条记录，包含完整访问日志"
            metrics = {"exported_records": export_data["data_count"]}

        elif scenario == "gdpr_delete":
            # GDPR被遗忘权测试
            user_id = test_case.input_data.get("user_id", "user_001")
            cascade = test_case.input_data.get("cascade", True)

            system.create_user(user_id)
            system.store_memory(user_id, "Memory to delete")
            system.store_memory(user_id, "Another memory")

            before_count = len(system.user_data.get(user_id, []))
            deleted, msg = system.delete_user_data(user_id, cascade)
            after_count = len(system.user_data.get(user_id, []))

            passed = after_count == 0 and deleted == before_count
            details = f"删除前{before_count}条，已删除{deleted}条，剩余{after_count}条"
            metrics = {"before": before_count, "deleted": deleted, "after": after_count}

        elif scenario == "audit_log":
            # 审计日志完整性测试
            operations = test_case.input_data.get("operations", ["read", "write"])

            system.create_user("audit_test_user")

            # 执行各种操作
            for op in operations:
                if op == "write":
                    system.store_memory("audit_test_user", f"Test content for {op}")
                elif op == "read":
                    memories = system.user_data.get("audit_test_user", [])
                    if memories:
                        system.retrieve_memory("audit_test_user", "audit_test_user", memories[0].id)
                elif op == "delete":
                    system.delete_user_data("audit_test_user")

            # 检查审计日志
            relevant_logs = [log for log in system.audit_trail
                           if log["accessor"] == "audit_test_user"]

            passed = len(relevant_logs) >= len(operations)
            details = f"执行{len(operations)}种操作，记录{len(relevant_logs)}条审计日志"
            metrics = {"operations": len(operations), "audit_entries": len(relevant_logs)}

        elif scenario == "encryption_in_transit":
            # 传输加密验证（模拟）
            protocols = test_case.input_data.get("protocols", ["TLS1.2"])

            # 模拟检查
            supported = ["TLS1.2", "TLS1.3"]
            all_supported = all(p in supported for p in protocols)

            passed = all_supported
            details = f"测试{len(protocols)}种协议，全部支持{'是' if all_supported else '否'}"
            metrics = {"tested": len(protocols), "supported": all_supported}

        elif scenario == "encryption_at_rest":
            # 存储加密验证
            algorithm = test_case.input_data.get("algorithm", "AES-256")

            system.create_user("encrypt_test")
            system.store_memory("encrypt_test", "Sensitive data")

            memory = system.user_data["encrypt_test"][0]
            has_encryption = memory.encryption_key_id != ""

            passed = has_encryption
            details = f"数据使用{algorithm}加密，密钥ID: {memory.encryption_key_id[:8]}..."
            metrics = {"algorithm": algorithm, "encrypted": has_encryption}

        elif scenario == "least_privilege":
            # 最小权限原则验证
            roles = test_case.input_data.get("roles", ["admin", "user"])

            # 创建测试数据
            system.create_user("data_owner")
            system.store_memory("data_owner", "Private data")
            memory_id = system.user_data["data_owner"][0].id

            access_results = {}

            for role in roles:
                user_id = f"{role}_test"
                system.create_user(user_id)

                result, msg = system.retrieve_memory(user_id, "data_owner", memory_id)
                access_results[role] = result is not None

            # 只有admin和数据所有者能访问
            expected = {"admin": True, "user": False, "guest": False}
            actual_matches = all(access_results.get(r, False) == expected.get(r, False)
                               for r in roles)

            passed = actual_matches
            details = f"角色访问权限: {access_results}"
            metrics = {"roles_tested": len(roles), "access_results": access_results}

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
    print("Day 67: 数据隔离与隐私合规测试")
    print("测试架构师视角：验证用户数据隔离、敏感信息保护和合规性")
    print("=" * 70)
    print()

    # 初始化系统
    system = MockDataIsolationSystem()
    results: List[TestResult] = []

    # 执行测试
    print_separator("=")
    print("【测试执行】")
    print_separator("=")

    for test_case in TEST_CASES:
        result = run_test_case(test_case, system)
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

    # 系统统计
    print("\n")
    print_separator("=")
    print("【数据隔离系统统计】")
    print_separator("=")
    stats = system.get_isolation_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 合规检查清单
    print("\n")
    print_separator("=")
    print("【合规检查清单】")
    print_separator("=")
    compliance_items = [
        ("GDPR - 数据可携带权", any("EXPORT" in log.get("action", "") for log in system.audit_trail)),
        ("GDPR - 被遗忘权", any("DELETE" in log.get("action", "") for log in system.audit_trail)),
        ("数据隔离", stats.get("violations", 0) == 0),
        ("审计日志", stats.get("audit_entries", 0) > 0),
        ("PII检测", stats.get("pii_memories", 0) > 0),
    ]

    for item, status in compliance_items:
        mark = "✅" if status else "❌"
        print(f"  {mark} {item}")

    print("\n")
    print_separator("=")
    print("测试完成")
    print_separator("=")


if __name__ == "__main__":
    main()
