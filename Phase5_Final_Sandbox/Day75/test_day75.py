"""
Day 75: 测试执行与数据收集(2) - 性能压测与安全扫描
目标：系统性能验证与安全风险评估
测试架构师视角：性能测试、压力测试、安全扫描、风险评估
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime
import random
import json


class MetricStatus(Enum):
    """指标状态"""
    PASSED = "✅ 通过"
    WARNING = "⚠️ 警告"
    FAILED = "❌ 失败"


class SecurityLevel(Enum):
    """安全等级"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    threshold: str
    actual_value: float
    unit: str
    status: MetricStatus


@dataclass
class SecurityFinding:
    """安全发现"""
    check_item: str
    level: SecurityLevel
    result: str
    description: str
    recommendation: str


@dataclass
class LoadTestResult:
    """负载测试结果"""
    concurrent_users: int
    avg_response_time: float
    error_rate: float
    throughput: float
    cpu_usage: float
    memory_usage: float


class PerformanceTester:
    """性能测试器"""

    def __init__(self, target_system: str):
        self.target_system = target_system
        self.baseline_metrics: List[PerformanceMetric] = []
        self.load_test_results: List[LoadTestResult] = []
        self.max_capacity: int = 0
        self.performance_inflection_point: int = 0

    def run_baseline_test(self) -> List[PerformanceMetric]:
        """运行基准测试"""
        # 模拟基准测试数据
        metrics = [
            PerformanceMetric("平均响应时间", "<200ms", 156, "ms", MetricStatus.PASSED),
            PerformanceMetric("P95响应时间", "<500ms", 380, "ms", MetricStatus.PASSED),
            PerformanceMetric("P99响应时间", "<1000ms", 720, "ms", MetricStatus.PASSED),
            PerformanceMetric("QPS", ">1000", 1250, "req/s", MetricStatus.PASSED),
            PerformanceMetric("错误率", "<0.1%", 0.05, "%", MetricStatus.PASSED),
            PerformanceMetric("CPU使用率", "<70%", 65, "%", MetricStatus.PASSED),
            PerformanceMetric("内存使用率", "<80%", 72, "%", MetricStatus.PASSED),
        ]
        self.baseline_metrics = metrics
        return metrics

    def run_load_test(self, concurrent_levels: List[int]) -> List[LoadTestResult]:
        """运行负载测试"""
        results = []

        for users in concurrent_levels:
            # 模拟负载测试数据
            # 随着并发增加，响应时间上升，错误率增加
            base_response = 100  # 基础响应时间ms
            response_time = base_response + (users * 0.2) + random.uniform(-10, 20)

            # 错误率在低并发时接近0，高并发时上升
            if users <= 500:
                error_rate = random.uniform(0, 0.05)
            elif users <= 1000:
                error_rate = random.uniform(0.05, 0.2)
            else:
                error_rate = random.uniform(0.2, 2.0)

            # 吞吐量先上升后趋于平稳
            throughput = min(users * 1.5, 1500) + random.uniform(-50, 50)

            # 资源使用
            cpu_usage = min(30 + (users * 0.04), 95) + random.uniform(-5, 5)
            memory_usage = min(40 + (users * 0.03), 90) + random.uniform(-3, 3)

            result = LoadTestResult(
                concurrent_users=users,
                avg_response_time=round(response_time, 1),
                error_rate=round(error_rate, 2),
                throughput=round(throughput, 0),
                cpu_usage=round(cpu_usage, 1),
                memory_usage=round(memory_usage, 1)
            )
            results.append(result)

        self.load_test_results = results

        # 分析最大承载和性能拐点
        self._analyze_capacity()

        return results

    def _analyze_capacity(self):
        """分析系统容量"""
        # 找到错误率超过1%或响应时间超过1000ms的点
        for i, result in enumerate(self.load_test_results):
            if result.error_rate > 1.0 or result.avg_response_time > 1000:
                self.max_capacity = result.concurrent_users
                self.performance_inflection_point = self.load_test_results[max(0, i-1)].concurrent_users
                return

        # 如果都满足，取最后一个
        if self.load_test_results:
            self.max_capacity = self.load_test_results[-1].concurrent_users
            self.performance_inflection_point = int(self.max_capacity * 0.8)

    def generate_performance_report(self) -> str:
        """生成性能测试报告"""
        lines = []

        # 基准测试
        lines.append("【步骤1】性能基准测试")
        lines.append("  基准测试结果:")
        lines.append("    ┌────────────────┬──────────┬──────────┬──────────┐")
        lines.append("    │ 指标           │ 基准值   │ 实际值   │ 状态     │")
        lines.append("    ├────────────────┼──────────┼──────────┼──────────┤")

        for metric in self.baseline_metrics:
            lines.append(f"    │ {metric.name:<14} │ {metric.threshold:<8} │ {metric.actual_value}{metric.unit:<4} │ {metric.status.value:<8} │")

        lines.append("    └────────────────┴──────────┴──────────┴──────────┘")
        lines.append("")

        # 压力测试
        lines.append("【步骤2】压力测试")
        lines.append("  压力测试结果:")
        lines.append(f"    并发用户数: {' → '.join(str(r.concurrent_users) for r in self.load_test_results)}")
        lines.append(f"    最大承载: {self.max_capacity}并发")
        lines.append(f"    性能拐点: {self.performance_inflection_point}并发 (响应时间急剧上升)")
        recommended = int(self.performance_inflection_point * 0.8)
        lines.append(f"    建议容量: {recommended}并发 (保留20%余量)")
        lines.append("")

        return "\n".join(lines)


class SecurityScanner:
    """安全扫描器"""

    def __init__(self, target_system: str):
        self.target_system = target_system
        self.findings: List[SecurityFinding] = []

    def run_security_scan(self) -> List[SecurityFinding]:
        """运行安全扫描"""
        # 模拟安全扫描结果
        findings = [
            SecurityFinding(
                "Prompt注入防护",
                SecurityLevel.HIGH,
                "✅ 通过",
                "输入过滤机制有效，恶意Prompt被正确拦截",
                "保持现有防护措施"
            ),
            SecurityFinding(
                "SQL注入防护",
                SecurityLevel.HIGH,
                "✅ 通过",
                "使用参数化查询，无SQL注入风险",
                "保持现有防护措施"
            ),
            SecurityFinding(
                "XSS防护",
                SecurityLevel.HIGH,
                "✅ 通过",
                "输出内容正确编码，无XSS漏洞",
                "保持现有防护措施"
            ),
            SecurityFinding(
                "敏感信息泄露",
                SecurityLevel.HIGH,
                "⚠️ 警告",
                "应用日志中包含用户手机号明文",
                "对日志中的敏感信息进行脱敏处理"
            ),
            SecurityFinding(
                "越权访问",
                SecurityLevel.MEDIUM,
                "✅ 通过",
                "权限校验完整，无法越权访问",
                "保持现有防护措施"
            ),
            SecurityFinding(
                "依赖漏洞",
                SecurityLevel.MEDIUM,
                "⚠️ 警告",
                "发现3个低危CVE：CVE-2024-XXX1, CVE-2024-XXX2, CVE-2024-XXX3",
                "更新依赖版本到最新稳定版"
            ),
        ]
        self.findings = findings
        return findings

    def generate_security_report(self) -> str:
        """生成安全扫描报告"""
        lines = []
        lines.append("【步骤3】安全扫描")
        lines.append("  安全扫描结果:")
        lines.append("    ┌─────────────────────┬────────┬─────────────────────────────┐")
        lines.append("    │ 检查项              │ 等级   │ 结果                        │")
        lines.append("    ├─────────────────────┼────────┼─────────────────────────────┤")

        for finding in self.findings:
            result_short = finding.result + " - " + finding.description[:15]
            lines.append(f"    │ {finding.check_item:<19} │ {finding.level.value:<6} │ {result_short:<27} │")

        lines.append("    └─────────────────────┴────────┴─────────────────────────────┘")
        lines.append("")

        return "\n".join(lines)


class TestDataCollector:
    """测试数据收集器"""

    def __init__(self):
        self.performance_data: Dict[str, Any] = {}
        self.security_data: Dict[str, Any] = {}
        self.collected_at: Optional[str] = None

    def collect_performance_data(self, tester: PerformanceTester):
        """收集性能数据"""
        self.performance_data = {
            "baseline_metrics": [
                {
                    "name": m.name,
                    "threshold": m.threshold,
                    "actual": m.actual_value,
                    "unit": m.unit,
                    "status": m.status.value
                } for m in tester.baseline_metrics
            ],
            "load_test_results": [
                {
                    "concurrent_users": r.concurrent_users,
                    "avg_response_time": r.avg_response_time,
                    "error_rate": r.error_rate,
                    "throughput": r.throughput,
                    "cpu_usage": r.cpu_usage,
                    "memory_usage": r.memory_usage
                } for r in tester.load_test_results
            ],
            "capacity_analysis": {
                "max_capacity": tester.max_capacity,
                "inflection_point": tester.performance_inflection_point,
                "recommended_capacity": int(tester.performance_inflection_point * 0.8)
            }
        }

    def collect_security_data(self, scanner: SecurityScanner):
        """收集安全数据"""
        self.security_data = {
            "findings": [
                {
                    "check_item": f.check_item,
                    "level": f.level.value,
                    "result": f.result,
                    "description": f.description,
                    "recommendation": f.recommendation
                } for f in scanner.findings
            ],
            "summary": {
                "total": len(scanner.findings),
                "high_risk": len([f for f in scanner.findings if f.level == SecurityLevel.HIGH]),
                "medium_risk": len([f for f in scanner.findings if f.level == SecurityLevel.MEDIUM]),
                "low_risk": len([f for f in scanner.findings if f.level == SecurityLevel.LOW]),
                "passed": len([f for f in scanner.findings if "通过" in f.result]),
                "warnings": len([f for f in scanner.findings if "警告" in f.result]),
                "failed": len([f for f in scanner.findings if "失败" in f.result])
            }
        }

    def export_data(self, filepath: str):
        """导出收集的数据"""
        self.collected_at = datetime.now().isoformat()
        data = {
            "collected_at": self.collected_at,
            "performance": self.performance_data,
            "security": self.security_data
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def generate_console_report(tester: PerformanceTester, scanner: SecurityScanner, collector: TestDataCollector) -> str:
    """生成控制台报告"""
    lines = []
    lines.append("=" * 70)
    lines.append("Day 75: 测试执行与数据收集(2) - 性能压测与安全扫描")
    lines.append("测试架构师视角：系统性能验证与安全风险评估")
    lines.append("=" * 70)
    lines.append("")

    # 性能测试报告
    lines.append(tester.generate_performance_report())

    # 安全扫描报告
    lines.append(scanner.generate_security_report())

    # 数据收集
    lines.append("【步骤4】数据收集与报告")
    lines.append("  收集数据:")
    lines.append(f"    性能指标: {len(tester.baseline_metrics)}项")
    lines.append(f"    资源监控: 4项")

    warning_count = len([f for f in scanner.findings if "警告" in f.result])
    lines.append(f"    安全漏洞: {warning_count}个(低危)")
    lines.append("    扫描日志: 已保存")
    lines.append("")

    # 结论
    lines.append("【结论】性能与安全测试完成")

    # 性能状态
    failed_metrics = [m for m in tester.baseline_metrics if m.status == MetricStatus.FAILED]
    if failed_metrics:
        lines.append(f"  性能状态: {len(failed_metrics)}项指标未达标")
    else:
        lines.append("  性能状态: 符合SLA要求")

    # 安全状态
    if warning_count > 0:
        lines.append(f"  安全状态: {warning_count}个低危问题需修复")
    else:
        lines.append("  安全状态: 无安全问题")

    lines.append("  建议: 修复日志脱敏问题，更新依赖版本")
    lines.append("")

    return "\n".join(lines)


def main():
    """主函数"""
    target = "电商平台"

    # 性能测试
    tester = PerformanceTester(target)
    tester.run_baseline_test()
    tester.run_load_test([100, 500, 1000, 2000])

    # 安全扫描
    scanner = SecurityScanner(target)
    scanner.run_security_scan()

    # 数据收集
    collector = TestDataCollector()
    collector.collect_performance_data(tester)
    collector.collect_security_data(scanner)

    # 生成报告
    report = generate_console_report(tester, scanner, collector)
    print(report)

    # 导出数据
    import os
    output_path = os.path.join(os.path.dirname(__file__), "test_data_day75.json")
    collector.export_data(output_path)
    print(f"测试数据已导出: {output_path}")


if __name__ == "__main__":
    main()
