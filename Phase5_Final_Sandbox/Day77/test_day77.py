"""
Day 77: 性能压测深度实践(2) - 资源监控与瓶颈定位
目标：从指标异常到根因定位的系统化方法
测试架构师视角：资源监控、瓶颈识别、根因分析
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import Enum
import random


class MetricStatus(Enum):
    """指标状态"""
    NORMAL = "正常"
    WARNING = "警告"
    CRITICAL = "严重"


@dataclass
class Metric:
    """监控指标"""
    name: str
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    status: MetricStatus = MetricStatus.NORMAL


@dataclass
class Bottleneck:
    """性能瓶颈"""
    resource: str
    confidence: int  # 置信度 0-100
    root_causes: List[str]
    recommendations: List[str]


class ResourceMonitor:
    """资源监控器"""

    def __init__(self):
        self.app_metrics: List[Metric] = []
        self.system_metrics: List[Metric] = []
        self.middleware_metrics: List[Metric] = []

    def collect_app_metrics(self) -> List[Metric]:
        """采集应用层指标"""
        metrics = [
            Metric("平均响应时间", 245, "ms", 200, 500),
            Metric("P95响应时间", 580, "ms", 500, 1000),
            Metric("QPS", 850, "req/s", 1000, 500),
            Metric("错误率", 0.3, "%", 0.5, 1.0)
        ]

        for m in metrics:
            if m.value >= m.threshold_critical:
                m.status = MetricStatus.CRITICAL
            elif m.value >= m.threshold_warning:
                m.status = MetricStatus.WARNING

        self.app_metrics = metrics
        return metrics

    def collect_system_metrics(self) -> List[Metric]:
        """采集系统层指标"""
        metrics = [
            Metric("CPU使用率", 78, "%", 70, 85),
            Metric("内存使用率", 65, "%", 80, 90),
            Metric("磁盘I/O", 45, "%", 70, 85),
            Metric("网络带宽", 55, "%", 70, 85)
        ]

        for m in metrics:
            if m.value >= m.threshold_critical:
                m.status = MetricStatus.CRITICAL
            elif m.value >= m.threshold_warning:
                m.status = MetricStatus.WARNING

        self.system_metrics = metrics
        return metrics

    def collect_middleware_metrics(self) -> List[Metric]:
        """采集中间件指标"""
        metrics = [
            Metric("数据库连接池", 85, "%", 80, 95),
            Metric("Redis命中率", 72, "%", 70, 50),
            Metric("MQ堆积", 1200, "条", 5000, 10000)
        ]

        for m in metrics:
            if m.name == "Redis命中率":
                # 命中率是越高越好，反向判断
                if m.value <= 50:
                    m.status = MetricStatus.CRITICAL
                elif m.value <= 70:
                    m.status = MetricStatus.WARNING
            else:
                if m.value >= m.threshold_critical:
                    m.status = MetricStatus.CRITICAL
                elif m.value >= m.threshold_warning:
                    m.status = MetricStatus.WARNING

        self.middleware_metrics = metrics
        return metrics

    def get_all_metrics(self) -> Dict[str, List[Metric]]:
        """获取所有指标"""
        return {
            "app": self.app_metrics,
            "system": self.system_metrics,
            "middleware": self.middleware_metrics
        }


class BottleneckAnalyzer:
    """瓶颈分析器"""

    def __init__(self, monitor: ResourceMonitor):
        self.monitor = monitor
        self.bottlenecks: List[Bottleneck] = []

    def use_analysis(self) -> Dict[str, Dict]:
        """USE方法分析"""
        results = {}

        # 分析CPU
        cpu_metric = next((m for m in self.monitor.system_metrics if m.name == "CPU使用率"), None)
        if cpu_metric:
            results["CPU"] = {
                "utilization": cpu_metric.value,
                "saturation": "中等" if cpu_metric.value < 80 else "高",
                "errors": "无",
                "status": cpu_metric.status.value
            }

        # 分析数据库连接池
        db_metric = next((m for m in self.monitor.middleware_metrics if m.name == "数据库连接池"), None)
        if db_metric:
            results["数据库连接"] = {
                "utilization": db_metric.value,
                "saturation": "高" if db_metric.value > 80 else "低",
                "errors": "无",
                "status": db_metric.status.value
            }

        return results

    def identify_bottlenecks(self) -> List[Bottleneck]:
        """识别性能瓶颈"""
        bottlenecks = []

        # 检查数据库连接池
        db_metric = next((m for m in self.monitor.middleware_metrics if m.name == "数据库连接池"), None)
        if db_metric and db_metric.status != MetricStatus.NORMAL:
            bottlenecks.append(Bottleneck(
                resource="数据库连接池饱和",
                confidence=85,
                root_causes=[
                    "1. 慢查询导致连接长时间占用",
                    "2. 连接池配置偏小(100)",
                    "3. 缺少连接超时配置"
                ],
                recommendations=[
                    "高优先级: 优化慢查询SQL，添加索引",
                    "高优先级: 增加连接池大小到200",
                    "中优先级: 配置连接超时和重试机制"
                ]
            ))

        # 检查响应时间
        latency_metric = next((m for m in self.monitor.app_metrics if m.name == "平均响应时间"), None)
        if latency_metric and latency_metric.status != MetricStatus.NORMAL:
            bottlenecks.append(Bottleneck(
                resource="响应时间超标",
                confidence=75,
                root_causes=[
                    "1. 数据库查询慢",
                    "2. 缺少缓存层",
                    "3. 同步处理阻塞"
                ],
                recommendations=[
                    "高优先级: 引入Redis缓存热点数据",
                    "中优先级: 订单处理异步化",
                    "低优先级: 数据库读写分离"
                ]
            ))

        self.bottlenecks = bottlenecks
        return bottlenecks


def generate_monitoring_report() -> str:
    """生成监控报告"""
    lines = []
    lines.append("=" * 70)
    lines.append("Day 77: 性能压测深度实践(2) - 资源监控与瓶颈定位")
    lines.append("测试架构师视角：从指标异常到根因定位的系统化方法")
    lines.append("=" * 70)
    lines.append("")

    # 初始化监控器
    monitor = ResourceMonitor()

    # 步骤1: 资源监控数据采集
    lines.append("【步骤1】资源监控数据采集")
    lines.append("")

    app_metrics = monitor.collect_app_metrics()
    lines.append("  应用层指标:")
    for m in app_metrics:
        status_icon = "⚠️" if m.status == MetricStatus.WARNING else "❌" if m.status == MetricStatus.CRITICAL else "✓"
        if m.status != MetricStatus.NORMAL:
            lines.append(f"    {m.name}: {m.value}{m.unit} ({status_icon} 超过{m.threshold_warning}{m.unit}阈值)")
        else:
            lines.append(f"    {m.name}: {m.value}{m.unit}")
    lines.append("")

    system_metrics = monitor.collect_system_metrics()
    lines.append("  系统层指标:")
    for m in system_metrics:
        status_icon = "⚠️" if m.status == MetricStatus.WARNING else "❌" if m.status == MetricStatus.CRITICAL else "✓"
        if m.status != MetricStatus.NORMAL:
            lines.append(f"    {m.name}: {m.value}{m.unit} ({status_icon} 接近阈值)")
        else:
            lines.append(f"    {m.name}: {m.value}{m.unit}")
    lines.append("")

    middleware_metrics = monitor.collect_middleware_metrics()
    lines.append("  中间件指标:")
    for m in middleware_metrics:
        status_icon = "⚠️" if m.status == MetricStatus.WARNING else "❌" if m.status == MetricStatus.CRITICAL else "✓"
        if m.name == "数据库连接池":
            lines.append(f"    {m.name}: {m.value}/100 ({status_icon} 接近上限)")
        elif m.name == "Redis命中率":
            lines.append(f"    {m.name}: {m.value}%")
        else:
            lines.append(f"    {m.name}: {m.value}{m.unit}")
    lines.append("")

    # 步骤2: 瓶颈识别分析
    lines.append("【步骤2】瓶颈识别分析")
    lines.append("  使用USE方法分析:")

    analyzer = BottleneckAnalyzer(monitor)
    use_results = analyzer.use_analysis()

    for resource, result in use_results.items():
        lines.append(f"    {resource}: 利用率{result['utilization']}%({result['status']}), 饱和度{result['saturation']}, 错误{result['errors']}")

    bottlenecks = analyzer.identify_bottlenecks()
    if bottlenecks:
        lines.append("")
        lines.append(f"  主要瓶颈: {bottlenecks[0].resource}")
        lines.append(f"  置信度: {bottlenecks[0].confidence}%")
    lines.append("")

    # 步骤3: 根因定位
    lines.append("【步骤3】根因定位")
    if bottlenecks:
        bottleneck = bottlenecks[0]
        lines.append("  根因分析:")
        for cause in bottleneck.root_causes:
            lines.append(f"    {cause}")
        lines.append("")

        lines.append("  优化建议:")
        for rec in bottleneck.recommendations:
            lines.append(f"    {rec}")
    lines.append("")

    # 结论
    lines.append("【结论】瓶颈定位完成")
    if bottlenecks:
        lines.append(f"  主要瓶颈: {bottlenecks[0].resource}")
        lines.append(f"  根因: 慢查询 + 连接池配置不足")
        lines.append(f"  预计优化效果: 响应时间降低40-50%")
    else:
        lines.append("  未发现明显性能瓶颈")
    lines.append("")

    return "\n".join(lines)


def main():
    """主函数"""
    report = generate_monitoring_report()
    print(report)


if __name__ == "__main__":
    main()
