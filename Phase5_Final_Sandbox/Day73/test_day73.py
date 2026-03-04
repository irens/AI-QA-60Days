"""
Day 73: 端到端测试方案设计(3) - 资源规划与测试计划文档
目标：系统化规划测试资源并生成完整测试计划
测试架构师视角：工作量估算、资源分配、进度计划、风险应对
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os


@dataclass
class TaskEstimate:
    """任务估算"""
    name: str
    optimistic: int  # 乐观估计(天)
    most_likely: int  # 最可能(天)
    pessimistic: int  # 悲观估计(天)

    @property
    def expected(self) -> float:
        """预期工期 = (乐观 + 4×最可能 + 悲观) / 6"""
        return (self.optimistic + 4 * self.most_likely + self.pessimistic) / 6

    @property
    def std_deviation(self) -> float:
        """标准差 = (悲观 - 乐观) / 6"""
        return (self.pessimistic - self.optimistic) / 6


@dataclass
class Resource:
    """资源定义"""
    role: str
    count: int
    allocation: float  # 投入比例 0-1

    @property
    def person_months(self) -> float:
        """人月数"""
        return self.count * self.allocation


@dataclass
class Milestone:
    """里程碑"""
    name: str
    week: int
    deliverables: List[str]


@dataclass
class RiskPlan:
    """风险应对计划"""
    risk: str
    level: str
    mitigation: str


@dataclass
class ExitCriteria:
    """退出标准"""
    dimension: str
    criteria: str
    measurement: str


class TestPlanGenerator:
    """测试计划生成器"""

    def __init__(self, project_name: str, version: str = "1.0"):
        self.project_name = project_name
        self.version = version
        self.tasks: List[TaskEstimate] = []
        self.resources: List[Resource] = []
        self.milestones: List[Milestone] = []
        self.risks: List[RiskPlan] = []
        self.exit_criteria: List[ExitCriteria] = []

    def add_task(self, task: TaskEstimate):
        """添加任务"""
        self.tasks.append(task)

    def add_resource(self, resource: Resource):
        """添加资源"""
        self.resources.append(resource)

    def add_milestone(self, milestone: Milestone):
        """添加里程碑"""
        self.milestones.append(milestone)

    def add_risk(self, risk: RiskPlan):
        """添加风险"""
        self.risks.append(risk)

    def add_exit_criteria(self, criteria: ExitCriteria):
        """添加退出标准"""
        self.exit_criteria.append(criteria)

    def calculate_total_effort(self) -> float:
        """计算总工作量"""
        return sum(task.expected for task in self.tasks)

    def calculate_total_resources(self) -> float:
        """计算总资源"""
        return sum(r.person_months for r in self.resources)

    def generate_console_report(self) -> str:
        """生成控制台报告"""
        lines = []
        lines.append("=" * 70)
        lines.append("Day 73: 端到端测试方案设计(3) - 资源规划与测试计划文档")
        lines.append("测试架构师视角：系统化规划测试资源并生成完整测试计划")
        lines.append("=" * 70)
        lines.append("")

        # 步骤1: 工作量估算
        lines.append("【步骤1】工作量估算")
        lines.append("  三点估算结果:")
        lines.append("    ┌────────────────┬────────┬──────────┬────────┬──────────┐")
        lines.append("    │ 活动           │ 乐观   │ 最可能   │ 悲观   │ 预期工期 │")
        lines.append("    ├────────────────┼────────┼──────────┼────────┼──────────┤")

        for task in self.tasks:
            lines.append(f"    │ {task.name:<14} │ {task.optimistic}天    │ {task.most_likely}天      │ {task.pessimistic}天    │ {task.expected:.1f}天    │")

        total = self.calculate_total_effort()
        lines.append("    ├────────────────┼────────┼──────────┼────────┼──────────┤")
        lines.append(f"    │ 总计           │        │          │        │ {total:.0f}天     │")
        lines.append("    └────────────────┴────────┴──────────┴────────┴──────────┘")
        lines.append("")

        # 步骤2: 资源分配
        lines.append("【步骤2】资源分配")
        lines.append("  人力资源规划:")
        for resource in self.resources:
            lines.append(f"    {resource.role}: {resource.count}人 × {resource.allocation*100:.0f}% = {resource.person_months:.1f}人月")
        total_resource = self.calculate_total_resources()
        lines.append("    " + "-" * 35)
        lines.append(f"    总计: {total_resource:.1f}人月")
        lines.append("")

        # 步骤3: 进度计划
        lines.append("【步骤3】进度计划")
        lines.append("  里程碑计划:")
        for ms in self.milestones:
            lines.append(f"    Week {ms.week}: {ms.name}")
        lines.append("")

        # 步骤4: 风险应对
        lines.append("【步骤4】风险应对")
        lines.append("  风险应对计划:")
        lines.append("    ┌─────────────────────┬────────┬─────────────────────────────┐")
        lines.append("    │ 风险                │ 等级   │ 应对措施                    │")
        lines.append("    ├─────────────────────┼────────┼─────────────────────────────┤")

        for risk in self.risks:
            lines.append(f"    │ {risk.risk:<19} │ {risk.level:<6} │ {risk.mitigation:<27} │")

        lines.append("    └─────────────────────┴────────┴─────────────────────────────┘")
        lines.append("")

        # 步骤5: 生成文档
        lines.append("【步骤5】生成测试计划文档")
        lines.append("  文档结构:")
        sections = [
            "1. 引言",
            "2. 测试范围",
            "3. 测试策略",
            "4. 测试资源",
            "5. 测试进度",
            "6. 风险管理",
            "7. 退出标准",
            "8. 交付物"
        ]
        for section in sections:
            lines.append(f"    ✓ {section}")
        lines.append("")

        # 结论
        lines.append("【结论】测试计划生成完成")
        lines.append(f"  总工期: {total:.0f}天 (6周)")
        lines.append(f"  总资源: {total_resource:.1f}人月")
        lines.append("  关键路径: 测试设计 → 用例开发 → 测试执行")
        lines.append("  输出文档: test_plan_day73.md")
        lines.append("")

        return "\n".join(lines)

    def generate_markdown_plan(self) -> str:
        """生成Markdown格式的测试计划文档"""
        lines = []
        lines.append(f"# {self.project_name} - 测试计划")
        lines.append(f"")
        lines.append(f"**版本**: {self.version}  ")
        lines.append(f"**日期**: {datetime.now().strftime('%Y-%m-%d')}  ")
        lines.append(f"**状态**: 已评审")
        lines.append(f"")
        lines.append("---")
        lines.append(f"")

        # 1. 引言
        lines.append("## 1. 引言")
        lines.append(f"")
        lines.append("### 1.1 文档目的")
        lines.append("本文档定义了端到端测试的范围、策略、资源和进度计划，确保测试活动有序进行。")
        lines.append(f"")
        lines.append("### 1.2 项目背景")
        lines.append(f"项目名称: {self.project_name}  ")
        lines.append("测试目标: 验证系统核心业务流程的正确性、稳定性和性能")
        lines.append(f"")

        # 2. 测试范围
        lines.append("## 2. 测试范围")
        lines.append(f"")
        lines.append("### 2.1 测试对象")
        lines.append("- 用户注册与登录系统")
        lines.append("- 商品搜索与浏览系统")
        lines.append("- 购物车与订单系统")
        lines.append("- 支付与结算系统")
        lines.append("- 订单履约与售后系统")
        lines.append(f"")
        lines.append("### 2.2 测试范围 (In Scope)")
        lines.append("- 功能测试：核心业务场景100%覆盖")
        lines.append("- 集成测试：服务间接口验证")
        lines.append("- 性能测试：关键接口响应时间<200ms")
        lines.append("- 安全测试：支付流程安全扫描")
        lines.append(f"")
        lines.append("### 2.3 非测试范围 (Out of Scope)")
        lines.append("- 第三方服务的深度压力测试")
        lines.append("- 非核心功能的UI细节测试")
        lines.append(f"")

        # 3. 测试策略
        lines.append("## 3. 测试策略")
        lines.append(f"")
        lines.append("### 3.1 测试类型")
        lines.append("| 测试类型 | 占比 | 工具 | 优先级 |")
        lines.append("|---------|------|------|--------|")
        lines.append("| 单元测试 | 40% | pytest | P0 |")
        lines.append("| API测试 | 35% | REST Assured | P0 |")
        lines.append("| E2E测试 | 25% | Playwright | P0 |")
        lines.append(f"")
        lines.append("### 3.2 自动化策略")
        lines.append("- P0用例：100%自动化")
        lines.append("- P1用例：80%自动化")
        lines.append("- P2用例：视ROI决定")
        lines.append(f"")

        # 4. 测试资源
        lines.append("## 4. 测试资源")
        lines.append(f"")
        lines.append("### 4.1 人力资源")
        lines.append("| 角色 | 人数 | 投入比例 | 人月数 |")
        lines.append("|------|------|---------|--------|")
        for resource in self.resources:
            lines.append(f"| {resource.role} | {resource.count} | {resource.allocation*100:.0f}% | {resource.person_months:.1f} |")
        lines.append(f"")
        lines.append(f"**总计: {self.calculate_total_resources():.1f}人月**")
        lines.append(f"")

        # 5. 测试进度
        lines.append("## 5. 测试进度")
        lines.append(f"")
        lines.append("### 5.1 里程碑")
        lines.append("| 周次 | 里程碑 | 交付物 |")
        lines.append("|------|--------|--------|")
        for ms in self.milestones:
            deliverables = ", ".join(ms.deliverables)
            lines.append(f"| Week {ms.week} | {ms.name} | {deliverables} |")
        lines.append(f"")
        lines.append("### 5.2 工作量估算")
        lines.append("| 活动 | 乐观 | 最可能 | 悲观 | 预期工期 |")
        lines.append("|------|------|--------|------|---------|")
        for task in self.tasks:
            lines.append(f"| {task.name} | {task.optimistic}天 | {task.most_likely}天 | {task.pessimistic}天 | {task.expected:.1f}天 |")
        lines.append(f"| **总计** | | | | **{self.calculate_total_effort():.0f}天** |")
        lines.append(f"")

        # 6. 风险管理
        lines.append("## 6. 风险管理")
        lines.append(f"")
        lines.append("| 风险 | 等级 | 应对措施 |")
        lines.append("|------|------|---------|")
        for risk in self.risks:
            lines.append(f"| {risk.risk} | {risk.level} | {risk.mitigation} |")
        lines.append(f"")

        # 7. 退出标准
        lines.append("## 7. 退出标准")
        lines.append(f"")
        lines.append("### 7.1 准入标准")
        lines.append("- 代码完成度≥90%")
        lines.append("- 单元测试通过率≥90%")
        lines.append("- 测试环境就绪")
        lines.append(f"")
        lines.append("### 7.2 准出标准")
        lines.append("| 维度 | 标准 | 测量方法 |")
        lines.append("|------|------|---------|")
        for criteria in self.exit_criteria:
            lines.append(f"| {criteria.dimension} | {criteria.criteria} | {criteria.measurement} |")
        lines.append(f"")

        # 8. 交付物
        lines.append("## 8. 交付物")
        lines.append(f"")
        lines.append("- 测试计划文档")
        lines.append("- 测试用例集")
        lines.append("- 测试执行报告")
        lines.append("- 缺陷报告")
        lines.append("- 风险评估报告")
        lines.append("- 自动化测试脚本")
        lines.append(f"")

        return "\n".join(lines)


def create_sample_plan() -> TestPlanGenerator:
    """创建示例测试计划"""
    generator = TestPlanGenerator("电商平台端到端测试", "1.0")

    # 添加任务估算
    tasks = [
        TaskEstimate("测试计划", 2, 3, 5),
        TaskEstimate("测试设计", 3, 5, 8),
        TaskEstimate("用例开发", 5, 8, 12),
        TaskEstimate("环境搭建", 2, 3, 5),
        TaskEstimate("测试执行", 5, 7, 10),
        TaskEstimate("报告输出", 1, 2, 3),
    ]
    for task in tasks:
        generator.add_task(task)

    # 添加资源
    resources = [
        Resource("测试经理", 1, 0.2),
        Resource("高级测试工程师", 2, 1.0),
        Resource("初级测试工程师", 2, 0.8),
        Resource("开发支持", 1, 0.3),
    ]
    for resource in resources:
        generator.add_resource(resource)

    # 添加里程碑
    milestones = [
        Milestone("测试计划评审通过", 1, ["测试计划文档"]),
        Milestone("测试设计完成", 2, ["测试用例设计文档"]),
        Milestone("核心用例开发完成", 3, ["自动化脚本", "测试数据"]),
        Milestone("环境就绪，开始执行", 4, ["环境配置文档"]),
        Milestone("测试执行完成", 5, ["测试执行报告"]),
        Milestone("报告输出，项目结项", 6, ["最终测试报告"]),
    ]
    for ms in milestones:
        generator.add_milestone(ms)

    # 添加风险
    risks = [
        RiskPlan("人员变动", "高", "知识文档化，交叉培训"),
        RiskPlan("需求变更", "高", "敏捷迭代，自动化优先"),
        RiskPlan("环境不稳定", "中", "容器化，监控告警"),
        RiskPlan("第三方依赖延迟", "中", "Mock服务，提前联调"),
        RiskPlan("自动化脚本维护", "中", "代码审查，模块化设计"),
    ]
    for risk in risks:
        generator.add_risk(risk)

    # 添加退出标准
    exit_criteria = [
        ExitCriteria("覆盖率", "代码覆盖率≥80%，需求覆盖率100%", "覆盖率工具、需求追溯矩阵"),
        ExitCriteria("缺陷率", "严重缺陷=0，高优先级缺陷<3个", "缺陷管理系统"),
        ExitCriteria("通过率", "测试用例通过率≥95%", "测试报告"),
        ExitCriteria("稳定性", "连续3轮测试无新增严重缺陷", "趋势分析"),
        ExitCriteria("性能", "响应时间<200ms，吞吐量达标", "性能测试报告"),
    ]
    for criteria in exit_criteria:
        generator.add_exit_criteria(criteria)

    return generator


def main():
    """主函数"""
    generator = create_sample_plan()

    # 打印控制台报告
    console_report = generator.generate_console_report()
    print(console_report)

    # 生成Markdown文档
    md_content = generator.generate_markdown_plan()
    output_path = os.path.join(os.path.dirname(__file__), "test_plan_day73.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"测试计划文档已生成: {output_path}")


if __name__ == "__main__":
    main()
