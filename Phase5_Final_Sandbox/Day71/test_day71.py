"""
Day 71: 端到端测试方案设计(1) - 需求分析与风险识别
目标：系统化识别测试需求与评估业务风险
测试架构师视角：建立需求分析框架，应用FMEA风险识别方法
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class RiskLevel(Enum):
    """风险等级"""
    CRITICAL = "🔴 L1 阻断性"
    HIGH = "🟡 L2 高优先级"
    MEDIUM = "🟠 L3 中优先级"
    LOW = "🟢 L4 一般"


class RequirementType(Enum):
    """需求类型"""
    BUSINESS = "业务需求"
    USER = "用户需求"
    SYSTEM = "系统需求"
    TEST = "测试需求"


@dataclass
class Requirement:
    """需求定义"""
    id: str
    type: RequirementType
    description: str
    priority: str
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Risk:
    """风险定义"""
    id: str
    description: str
    severity: int  # 1-10
    occurrence: int  # 1-10
    detection: int  # 1-10
    level: RiskLevel
    mitigation: str

    @property
    def rpn(self) -> int:
        """风险优先级数 Risk Priority Number"""
        return self.severity * self.occurrence * self.detection


@dataclass
class TestNeed:
    """测试需求"""
    id: str
    source_req: str
    description: str
    test_type: str
    priority: str


class EndToEndTestPlanner:
    """端到端测试规划器"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.requirements: List[Requirement] = []
        self.risks: List[Risk] = []
        self.test_needs: List[TestNeed] = []

    def add_requirement(self, req: Requirement):
        """添加需求"""
        self.requirements.append(req)

    def add_risk(self, risk: Risk):
        """添加风险"""
        self.risks.append(risk)

    def add_test_need(self, need: TestNeed):
        """添加测试需求"""
        self.test_needs.append(need)

    def analyze_requirements(self) -> Dict[str, int]:
        """分析需求分布"""
        stats = {req_type.value: 0 for req_type in RequirementType}
        for req in self.requirements:
            stats[req.type.value] += 1
        return stats

    def assess_risks(self) -> Dict[str, List[Risk]]:
        """评估风险分布"""
        categorized = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        for risk in self.risks:
            if risk.rpn >= 400:
                categorized["critical"].append(risk)
            elif risk.rpn >= 200:
                categorized["high"].append(risk)
            elif risk.rpn >= 100:
                categorized["medium"].append(risk)
            else:
                categorized["low"].append(risk)
        return categorized

    def get_top_risks(self, n: int = 5) -> List[Risk]:
        """获取Top N风险"""
        return sorted(self.risks, key=lambda r: r.rpn, reverse=True)[:n]

    def generate_report(self) -> str:
        """生成分析报告"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"Day 71: 端到端测试方案设计(1) - 需求分析与风险识别")
        lines.append("测试架构师视角：系统化识别测试需求与评估业务风险")
        lines.append("=" * 70)
        lines.append("")

        # 步骤1: 需求分析
        lines.append("【步骤1】需求收集与分析")
        req_stats = self.analyze_requirements()
        lines.append(f"  业务需求: {req_stats.get('业务需求', 0)}个")
        lines.append(f"  用户需求: {req_stats.get('用户需求', 0)}个")
        lines.append(f"  系统需求: {req_stats.get('系统需求', 0)}个")
        lines.append(f"  测试需求: {len(self.test_needs)}个测试需求点")
        lines.append("")

        # 步骤2: 风险识别
        lines.append("【步骤2】风险识别与评估")
        risk_stats = self.assess_risks()
        total_risks = sum(len(v) for v in risk_stats.values())
        lines.append(f"  识别风险: {total_risks}个")
        lines.append(f"  极高风险(RPN>400): {len(risk_stats['critical'])}个")
        lines.append(f"  高风险(RPN 200-400): {len(risk_stats['high'])}个")
        lines.append(f"  中风险(RPN 100-200): {len(risk_stats['medium'])}个")
        lines.append(f"  低风险(RPN<100): {len(risk_stats['low'])}个")
        lines.append("")

        # 步骤3: 风险排序
        lines.append("【步骤3】风险优先级排序")
        lines.append(f"  Top {min(3, len(self.risks))} 风险:")
        for i, risk in enumerate(self.get_top_risks(3), 1):
            lines.append(f"    {i}. [RPN={risk.rpn}] {risk.description}")
            lines.append(f"       严重程度:{risk.severity}, 概率:{risk.occurrence}, 检测难度:{risk.detection}")
        lines.append("")

        # 结论
        lines.append("【结论】需求分析与风险识别完成")
        critical_count = len(risk_stats['critical'])
        high_count = len(risk_stats['high'])
        if critical_count > 0 or high_count > 0:
            lines.append(f"  关键测试重点: 支付流程、数据一致性、库存管理")
            lines.append(f"  建议测试投入: 60%资源覆盖高风险区域")
        else:
            lines.append("  整体风险可控，按常规测试流程执行")
        lines.append("")

        return "\n".join(lines)


def create_sample_project() -> EndToEndTestPlanner:
    """创建示例项目"""
    planner = EndToEndTestPlanner("电商平台端到端测试")

    # 添加业务需求
    business_reqs = [
        Requirement("BR-001", RequirementType.BUSINESS, "用户注册与登录流程", "P0",
                   ["支持手机号/邮箱注册", "支持第三方登录"]),
        Requirement("BR-002", RequirementType.BUSINESS, "商品浏览与搜索", "P0",
                   ["支持关键词搜索", "支持分类筛选"]),
        Requirement("BR-003", RequirementType.BUSINESS, "购物车管理", "P0",
                   ["支持增删改查", "支持批量操作"]),
        Requirement("BR-004", RequirementType.BUSINESS, "订单创建与支付", "P0",
                   ["支持多种支付方式", "订单状态正确流转"]),
        Requirement("BR-005", RequirementType.BUSINESS, "订单履约与售后", "P1",
                   ["物流信息同步", "支持退款退货"]),
    ]
    for req in business_reqs:
        planner.add_requirement(req)

    # 添加用户需求
    user_reqs = [
        Requirement("UR-001", RequirementType.USER, "新用户快速注册", "P0"),
        Requirement("UR-002", RequirementType.USER, "老用户一键登录", "P0"),
        Requirement("UR-003", RequirementType.USER, "精准商品搜索", "P0"),
        Requirement("UR-004", RequirementType.USER, "便捷购物车操作", "P0"),
        Requirement("UR-005", RequirementType.USER, "安全支付体验", "P0"),
    ]
    for req in user_reqs:
        planner.add_requirement(req)

    # 添加系统需求
    system_reqs = [
        Requirement("SR-001", RequirementType.SYSTEM, "用户服务", "P0"),
        Requirement("SR-002", RequirementType.SYSTEM, "商品服务", "P0"),
        Requirement("SR-003", RequirementType.SYSTEM, "订单服务", "P0"),
        Requirement("SR-004", RequirementType.SYSTEM, "支付服务", "P0"),
        Requirement("SR-005", RequirementType.SYSTEM, "库存服务", "P0"),
        Requirement("SR-006", RequirementType.SYSTEM, "物流服务", "P1"),
        Requirement("SR-007", RequirementType.SYSTEM, "消息服务", "P1"),
        Requirement("SR-008", RequirementType.SYSTEM, "搜索服务", "P0"),
        Requirement("SR-009", RequirementType.SYSTEM, "推荐服务", "P2"),
        Requirement("SR-010", RequirementType.SYSTEM, "营销服务", "P2"),
        Requirement("SR-011", RequirementType.SYSTEM, "风控服务", "P0"),
        Requirement("SR-012", RequirementType.SYSTEM, "监控服务", "P1"),
    ]
    for req in system_reqs:
        planner.add_requirement(req)

    # 添加测试需求
    test_needs = [
        TestNeed("TN-001", "BR-001", "用户注册流程验证", "E2E", "P0"),
        TestNeed("TN-002", "BR-001", "登录鉴权验证", "API", "P0"),
        TestNeed("TN-003", "BR-002", "搜索功能验证", "E2E", "P0"),
        TestNeed("TN-004", "BR-002", "搜索结果准确性", "API", "P0"),
        TestNeed("TN-005", "BR-003", "购物车操作验证", "E2E", "P0"),
        TestNeed("TN-006", "BR-003", "购物车数据一致性", "API", "P0"),
        TestNeed("TN-007", "BR-004", "订单创建流程", "E2E", "P0"),
        TestNeed("TN-008", "BR-004", "支付流程验证", "E2E", "P0"),
        TestNeed("TN-009", "BR-004", "支付安全验证", "Security", "P0"),
        TestNeed("TN-010", "BR-004", "订单状态流转", "API", "P0"),
        TestNeed("TN-011", "BR-005", "物流信息同步", "Integration", "P1"),
        TestNeed("TN-012", "BR-005", "退款流程验证", "E2E", "P1"),
    ]
    for need in test_needs:
        planner.add_test_need(need)

    # 添加风险 (使用FMEA方法)
    risks = [
        Risk("R-001", "支付流程中断", 9, 8, 10, RiskLevel.CRITICAL,
             "核心支付链路端到端测试+熔断降级测试"),
        Risk("R-002", "订单数据丢失", 9, 7, 8, RiskLevel.CRITICAL,
             "数据持久化测试+备份恢复测试"),
        Risk("R-003", "库存超卖", 8, 6, 8, RiskLevel.HIGH,
             "并发库存扣减测试+分布式锁验证"),
        Risk("R-004", "用户信息泄露", 9, 5, 7, RiskLevel.HIGH,
             "安全渗透测试+敏感数据加密验证"),
        Risk("R-005", "搜索返回错误结果", 7, 6, 6, RiskLevel.MEDIUM,
             "搜索结果准确性测试+排序算法验证"),
        Risk("R-006", "购物车数据不一致", 7, 5, 7, RiskLevel.MEDIUM,
             "缓存一致性测试+数据库同步验证"),
        Risk("R-007", "第三方登录失败", 6, 7, 5, RiskLevel.MEDIUM,
             "OAuth流程测试+降级方案验证"),
        Risk("R-008", "物流信息延迟", 5, 8, 4, RiskLevel.LOW,
             "异步消息测试+超时处理验证"),
        Risk("R-009", "推荐算法偏差", 4, 6, 6, RiskLevel.LOW,
             "A/B测试+推荐效果评估"),
        Risk("R-010", "营销优惠券计算错误", 6, 5, 5, RiskLevel.MEDIUM,
             "价格计算测试+边界值测试"),
        Risk("R-011", "高并发下系统崩溃", 9, 6, 6, RiskLevel.HIGH,
             "压力测试+容量规划测试"),
        Risk("R-012", "数据库连接池耗尽", 8, 5, 7, RiskLevel.HIGH,
             "连接池监控测试+优雅降级测试"),
        Risk("R-013", "缓存雪崩", 7, 5, 8, RiskLevel.MEDIUM,
             "缓存预热测试+过期策略测试"),
        Risk("R-014", "消息队列堆积", 6, 7, 5, RiskLevel.MEDIUM,
             "消息堆积监控+消费速率测试"),
        Risk("R-015", "接口响应超时", 5, 8, 4, RiskLevel.LOW,
             "超时配置测试+熔断机制测试"),
    ]
    for risk in risks:
        planner.add_risk(risk)

    return planner


def main():
    """主函数"""
    planner = create_sample_project()
    report = planner.generate_report()
    print(report)


if __name__ == "__main__":
    main()
