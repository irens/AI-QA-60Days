"""
Day 74: 测试执行与数据收集(1) - 功能测试执行策略
目标：系统化执行测试用例并管理测试数据
测试架构师视角：测试执行生命周期、缺陷管理、数据收集
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import json
import random


class TestPriority(Enum):
    """测试优先级"""
    P0 = "P0-致命"
    P1 = "P1-严重"
    P2 = "P2-一般"
    P3 = "P3-轻微"


class TestStatus(Enum):
    """测试状态"""
    PASSED = "通过"
    FAILED = "失败"
    SKIPPED = "跳过"
    BLOCKED = "阻塞"


class DefectSeverity(Enum):
    """缺陷严重程度"""
    CRITICAL = "P0-致命"
    HIGH = "P1-严重"
    MEDIUM = "P2-一般"
    LOW = "P3-轻微"


@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    priority: TestPriority
    steps: List[str]
    expected_result: str
    status: TestStatus = TestStatus.PASSED
    actual_result: str = ""
    execution_time: float = 0.0


@dataclass
class Defect:
    """缺陷"""
    id: str
    title: str
    severity: DefectSeverity
    description: str
    reproduction_steps: List[str]
    expected_behavior: str
    actual_behavior: str
    environment: str
    reporter: str
    created_at: str = ""


@dataclass
class TestExecutionResult:
    """测试执行结果"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    blocked: int = 0
    defects: List[Defect] = field(default_factory=list)
    execution_logs: List[Dict] = field(default_factory=list)


class TestExecutor:
    """测试执行器"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.test_cases: List[TestCase] = []
        self.result = TestExecutionResult()
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def add_test_case(self, tc: TestCase):
        """添加测试用例"""
        self.test_cases.append(tc)

    def prepare_environment(self) -> bool:
        """准备测试环境"""
        # 模拟环境检查
        return True

    def execute_test(self, tc: TestCase) -> TestStatus:
        """执行单个测试用例"""
        # 模拟测试执行
        # 根据优先级和随机因素决定结果
        if tc.priority == TestPriority.P0:
            # P0用例90%通过率
            status = TestStatus.PASSED if random.random() < 0.9 else TestStatus.FAILED
        elif tc.priority == TestPriority.P1:
            # P1用例93%通过率
            status = TestStatus.PASSED if random.random() < 0.93 else TestStatus.FAILED
        elif tc.priority == TestPriority.P2:
            # P2用例90%通过率
            status = TestStatus.PASSED if random.random() < 0.9 else TestStatus.FAILED
        else:
            # P3用例95%通过率
            status = TestStatus.PASSED if random.random() < 0.95 else TestStatus.FAILED

        tc.status = status
        tc.execution_time = round(random.uniform(0.5, 3.0), 2)
        return status

    def run_all_tests(self):
        """运行所有测试"""
        self.start_time = datetime.now()

        for tc in self.test_cases:
            status = self.execute_test(tc)
            self.result.total += 1

            if status == TestStatus.PASSED:
                self.result.passed += 1
            elif status == TestStatus.FAILED:
                self.result.failed += 1
                # 为失败的测试创建缺陷
                defect = self.create_defect_from_failure(tc)
                self.result.defects.append(defect)
            elif status == TestStatus.SKIPPED:
                self.result.skipped += 1
            else:
                self.result.blocked += 1

            # 记录执行日志
            log = {
                "test_id": tc.id,
                "test_name": tc.name,
                "status": status.value,
                "execution_time": tc.execution_time,
                "timestamp": datetime.now().isoformat()
            }
            self.result.execution_logs.append(log)

        self.end_time = datetime.now()

    def create_defect_from_failure(self, tc: TestCase) -> Defect:
        """从测试失败创建缺陷"""
        defect_titles = {
            TestPriority.P0: "支付后订单状态未更新",
            TestPriority.P1: "优惠券计算精度错误",
            TestPriority.P2: "搜索结果显示延迟",
            TestPriority.P3: "提示文字显示不完整"
        }

        severity_map = {
            TestPriority.P0: DefectSeverity.CRITICAL,
            TestPriority.P1: DefectSeverity.HIGH,
            TestPriority.P2: DefectSeverity.MEDIUM,
            TestPriority.P3: DefectSeverity.LOW
        }

        defect_id = f"DEF-{len(self.result.defects) + 1:03d}"
        return Defect(
            id=defect_id,
            title=defect_titles.get(tc.priority, "未知缺陷"),
            severity=severity_map.get(tc.priority, DefectSeverity.LOW),
            description=f"执行测试 {tc.name} 时发现缺陷",
            reproduction_steps=tc.steps,
            expected_behavior=tc.expected_result,
            actual_behavior="实际结果与预期不符",
            environment="测试环境 v1.0",
            reporter="测试工程师",
            created_at=datetime.now().isoformat()
        )

    def get_statistics_by_priority(self) -> Dict[str, Dict[str, int]]:
        """按优先级统计"""
        stats = {}
        for priority in TestPriority:
            cases = [tc for tc in self.test_cases if tc.priority == priority]
            stats[priority.value] = {
                "total": len(cases),
                "passed": len([c for c in cases if c.status == TestStatus.PASSED]),
                "failed": len([c for c in cases if c.status == TestStatus.FAILED]),
                "skipped": len([c for c in cases if c.status == TestStatus.SKIPPED])
            }
        return stats

    def generate_report(self) -> str:
        """生成执行报告"""
        lines = []
        lines.append("=" * 70)
        lines.append("Day 74: 测试执行与数据收集(1) - 功能测试执行策略")
        lines.append("测试架构师视角：系统化执行测试用例并管理测试数据")
        lines.append("=" * 70)
        lines.append("")

        # 步骤1: 准备阶段
        lines.append("【步骤1】测试执行准备")
        if self.prepare_environment():
            lines.append("  ✓ 环境健康检查通过")
        lines.append(f"  ✓ 测试数据准备完成: {len(self.test_cases)}条测试数据")
        lines.append("  ✓ 测试工具配置完成")
        lines.append("")

        # 步骤2: 执行阶段
        lines.append("【步骤2】测试用例执行")
        lines.append("  执行统计:")
        lines.append("    ┌──────────┬────────┬────────┬────────┬────────┐")
        lines.append("    │ 优先级   │ 总数   │ 通过   │ 失败   │ 跳过   │")
        lines.append("    ├──────────┼────────┼────────┼────────┼────────┤")

        stats = self.get_statistics_by_priority()
        total_stats = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}

        for priority in TestPriority:
            p_stats = stats[priority.value]
            lines.append(f"    │ {priority.value:<8} │ {p_stats['total']:<6} │ {p_stats['passed']:<6} │ {p_stats['failed']:<6} │ {p_stats['skipped']:<6} │")
            total_stats["total"] += p_stats["total"]
            total_stats["passed"] += p_stats["passed"]
            total_stats["failed"] += p_stats["failed"]
            total_stats["skipped"] += p_stats["skipped"]

        lines.append("    ├──────────┼────────┼────────┼────────┼────────┤")
        lines.append(f"    │ {'总计':<8} │ {total_stats['total']:<6} │ {total_stats['passed']:<6} │ {total_stats['failed']:<6} │ {total_stats['skipped']:<6} │")
        lines.append("    └──────────┴────────┴────────┴────────┴────────┘")

        pass_rate = (total_stats["passed"] / total_stats["total"] * 100) if total_stats["total"] > 0 else 0
        lines.append(f"  通过率: {pass_rate:.1f}%")
        lines.append("")

        # 步骤3: 缺陷记录
        lines.append("【步骤3】缺陷记录与管理")
        lines.append("  缺陷统计:")

        defects_by_severity = {}
        for defect in self.result.defects:
            severity = defect.severity.value
            if severity not in defects_by_severity:
                defects_by_severity[severity] = []
            defects_by_severity[severity].append(defect)

        for severity in ["P0-致命", "P1-严重", "P2-一般", "P3-轻微"]:
            if severity in defects_by_severity:
                defects = defects_by_severity[severity]
                for defect in defects:
                    lines.append(f"    {severity}: [{defect.id}] {defect.title}")

        if not self.result.defects:
            lines.append("    未发现缺陷")
        lines.append("")

        # 步骤4: 数据收集
        lines.append("【步骤4】测试数据收集")
        lines.append("  数据收集统计:")
        lines.append(f"    执行日志: {len(self.result.execution_logs)}条")
        lines.append(f"    性能数据: {len(self.result.execution_logs)}条")
        lines.append(f"    截图记录: {len(self.result.defects)}张(失败用例)")
        lines.append("    环境快照: 1份")
        lines.append("")

        # 结论
        lines.append("【结论】功能测试执行完成")
        lines.append(f"  总用例: {total_stats['total']}, 通过: {total_stats['passed']}, 失败: {total_stats['failed']}")
        defect_density = (len(self.result.defects) / total_stats["total"] * 100) if total_stats["total"] > 0 else 0
        lines.append(f"  缺陷密度: {defect_density:.0f}%")
        lines.append("  测试数据已归档: test_data_day74.json")
        lines.append("")

        return "\n".join(lines)

    def export_test_data(self, filepath: str):
        """导出测试数据"""
        data = {
            "project": self.project_name,
            "execution_time": datetime.now().isoformat(),
            "summary": {
                "total": self.result.total,
                "passed": self.result.passed,
                "failed": self.result.failed,
                "skipped": self.result.skipped
            },
            "defects": [
                {
                    "id": d.id,
                    "title": d.title,
                    "severity": d.severity.value
                } for d in self.result.defects
            ],
            "logs": self.result.execution_logs
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def create_sample_test_suite() -> TestExecutor:
    """创建示例测试套件"""
    executor = TestExecutor("电商平台功能测试")

    # P0用例 - 致命
    p0_cases = [
        TestCase("TC-P0-001", "用户注册流程", TestPriority.P0,
                ["打开注册页面", "填写手机号", "获取验证码", "提交注册"],
                "注册成功，跳转首页"),
        TestCase("TC-P0-002", "用户登录", TestPriority.P0,
                ["打开登录页", "输入账号密码", "点击登录"],
                "登录成功，显示用户信息"),
        TestCase("TC-P0-003", "商品搜索", TestPriority.P0,
                ["输入关键词", "点击搜索"],
                "显示搜索结果"),
        TestCase("TC-P0-004", "加入购物车", TestPriority.P0,
                ["选择商品", "点击加入购物车"],
                "商品成功加入购物车"),
        TestCase("TC-P0-005", "订单创建", TestPriority.P0,
                ["进入购物车", "选择商品", "点击结算"],
                "订单创建成功"),
        TestCase("TC-P0-006", "支付流程", TestPriority.P0,
                ["选择支付方式", "确认支付"],
                "支付成功，订单状态更新"),
        TestCase("TC-P0-007", "订单查询", TestPriority.P0,
                ["进入订单列表", "查看订单详情"],
                "显示正确订单信息"),
        TestCase("TC-P0-008", "库存扣减", TestPriority.P0,
                ["下单购买", "检查库存"],
                "库存正确扣减"),
        TestCase("TC-P0-009", "退款申请", TestPriority.P0,
                ["进入订单", "申请退款"],
                "退款申请提交成功"),
        TestCase("TC-P0-010", "物流跟踪", TestPriority.P0,
                ["查看订单", "点击物流信息"],
                "显示物流轨迹"),
    ]

    # P1用例 - 严重
    p1_cases = [
        TestCase(f"TC-P1-{i:03d}", f"核心功能用例{i}", TestPriority.P1,
                ["步骤1", "步骤2", "步骤3"], "预期结果")
        for i in range(1, 16)
    ]

    # P2用例 - 一般
    p2_cases = [
        TestCase(f"TC-P2-{i:03d}", f"一般功能用例{i}", TestPriority.P2,
                ["步骤1", "步骤2"], "预期结果")
        for i in range(1, 21)
    ]

    # P3用例 - 轻微
    p3_cases = [
        TestCase(f"TC-P3-{i:03d}", f"体验优化用例{i}", TestPriority.P3,
                ["步骤1"], "预期结果")
        for i in range(1, 6)
    ]

    for case in p0_cases + p1_cases + p2_cases + p3_cases:
        executor.add_test_case(case)

    return executor


def main():
    """主函数"""
    executor = create_sample_test_suite()

    # 运行测试
    executor.run_all_tests()

    # 生成报告
    report = executor.generate_report()
    print(report)

    # 导出测试数据
    import os
    output_path = os.path.join(os.path.dirname(__file__), "test_data_day74.json")
    executor.export_test_data(output_path)
    print(f"测试数据已导出: {output_path}")


if __name__ == "__main__":
    main()
