#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 80: 安全扫描与可观测性集成(2) - 监控仪表盘与告警
测试架构师视角：构建AI系统的可观测性体系
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
import random
import json
from datetime import datetime, timedelta


class MetricType(Enum):
    """指标类型"""
    COUNTER = "计数器"
    GAUGE = "仪表盘"
    HISTOGRAM = "直方图"


class AlertSeverity(Enum):
    """告警级别"""
    P0 = "P0-紧急"
    P1 = "P1-严重"
    P2 = "P2-警告"
    P3 = "P3-提示"


@dataclass
class Metric:
    """监控指标"""
    name: str
    metric_type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: str
    level: str
    service: str
    message: str
    trace_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class Span:
    """链路跨度"""
    span_id: str
    parent_id: Optional[str]
    operation: str
    duration_ms: int
    status: str = "success"


@dataclass
class Trace:
    """链路追踪"""
    trace_id: str
    spans: List[Span] = field(default_factory=list)


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric_name: str
    condition: str
    threshold: float
    duration: str
    severity: AlertSeverity


@dataclass
class Alert:
    """告警实例"""
    rule_name: str
    severity: AlertSeverity
    message: str
    value: float
    timestamp: str
    suggestions: List[str] = field(default_factory=list)


class MetricsCollector:
    """指标采集器"""
    
    def __init__(self):
        self.metrics: List[Metric] = []
    
    def collect_llm_metrics(self) -> List[Metric]:
        """采集LLM相关指标"""
        metrics = [
            Metric("llm_request_duration", MetricType.HISTOGRAM, 450, 
                  {"model": "gpt-4", "quantile": "p50"}),
            Metric("llm_request_duration", MetricType.HISTOGRAM, 1200, 
                  {"model": "gpt-4", "quantile": "p99"}),
            Metric("llm_tokens_total", MetricType.COUNTER, 125000, 
                  {"model": "gpt-4", "type": "total"}),
            Metric("llm_active_sessions", MetricType.GAUGE, 320, {}),
            Metric("llm_requests_per_second", MetricType.GAUGE, 1250, {}),
            Metric("llm_error_rate", MetricType.GAUGE, 0.5, {}),
        ]
        self.metrics.extend(metrics)
        return metrics
    
    def collect_system_metrics(self) -> List[Metric]:
        """采集系统指标"""
        metrics = [
            Metric("cpu_usage_percent", MetricType.GAUGE, 65, {}),
            Metric("memory_usage_percent", MetricType.GAUGE, 72, {}),
            Metric("disk_io_utilization", MetricType.GAUGE, 35, {}),
            Metric("network_bytes_per_sec", MetricType.GAUGE, 1024000, {}),
        ]
        self.metrics.extend(metrics)
        return metrics
    
    def collect_security_metrics(self) -> List[Metric]:
        """采集安全指标"""
        metrics = [
            Metric("llm_prompt_injection_attempts", MetricType.COUNTER, 3, 
                  {"severity": "high"}),
            Metric("llm_sensitive_data_detected", MetricType.COUNTER, 5, 
                  {"severity": "medium"}),
            Metric("llm_security_events", MetricType.COUNTER, 8, 
                  {"severity": "low"}),
        ]
        self.metrics.extend(metrics)
        return metrics


class LogCollector:
    """日志采集器"""
    
    def __init__(self):
        self.logs: List[LogEntry] = []
    
    def collect_logs(self) -> List[LogEntry]:
        """采集日志"""
        logs = [
            LogEntry(
                timestamp=datetime.now().isoformat(),
                level="INFO",
                service="llm-gateway",
                message="Request processed successfully",
                trace_id="trace-001",
                metadata={"model": "gpt-4", "tokens": 350, "duration_ms": 1200}
            ),
            LogEntry(
                timestamp=datetime.now().isoformat(),
                level="WARN",
                service="llm-security",
                message="Potential prompt injection detected",
                trace_id="trace-002",
                metadata={"pattern": "ignore previous instructions", "blocked": True}
            ),
            LogEntry(
                timestamp=datetime.now().isoformat(),
                level="ERROR",
                service="llm-service",
                message="Model inference timeout",
                trace_id="trace-003",
                metadata={"model": "gpt-4", "timeout_ms": 30000}
            ),
        ]
        self.logs.extend(logs)
        return logs


class TraceCollector:
    """链路追踪采集器"""
    
    def __init__(self):
        self.traces: List[Trace] = []
    
    def collect_traces(self) -> List[Trace]:
        """采集链路"""
        trace = Trace(
            trace_id="trace-abc-123",
            spans=[
                Span("span-1", None, "API Gateway", 2),
                Span("span-2", "span-1", "Auth Service", 15),
                Span("span-3", "span-1", "RAG Retrieval", 150),
                Span("span-4", "span-3", "Vector Search", 80),
                Span("span-5", "span-1", "LLM Generation", 800),
                Span("span-6", "span-1", "Post Processing", 30),
            ]
        )
        self.traces.append(trace)
        return [trace]


class DashboardGenerator:
    """仪表盘生成器"""
    
    def __init__(self, metrics: List[Metric]):
        self.metrics = metrics
    
    def generate_dashboard(self) -> str:
        """生成仪表盘视图"""
        # 提取关键指标
        qps = next((m for m in self.metrics if m.name == "llm_requests_per_second"), None)
        latency_p50 = next((m for m in self.metrics 
                           if m.name == "llm_request_duration" and 
                           m.labels.get("quantile") == "p50"), None)
        latency_p99 = next((m for m in self.metrics 
                           if m.name == "llm_request_duration" and 
                           m.labels.get("quantile") == "p99"), None)
        error_rate = next((m for m in self.metrics if m.name == "llm_error_rate"), None)
        active_sessions = next((m for m in self.metrics if m.name == "llm_active_sessions"), None)
        total_tokens = next((m for m in self.metrics if m.name == "llm_tokens_total"), None)
        
        # 安全指标
        injection_attempts = next((m for m in self.metrics 
                                  if m.name == "llm_prompt_injection_attempts"), None)
        sensitive_data = next((m for m in self.metrics 
                              if m.name == "llm_sensitive_data_detected"), None)
        
        dashboard = f"""
  仪表盘组件:
    ┌────────────────────────────────────────────┐
    │  实时QPS: {qps.value if qps else 'N/A':>6}    平均延迟: {latency_p50.value if latency_p50 else 'N/A':>4}ms      │
    │  错误率: {error_rate.value if error_rate else 'N/A':>5}%      活跃会话: {active_sessions.value if active_sessions else 'N/A':>4}        │
    ├────────────────────────────────────────────┤
    │  延迟分布直方图          Token消耗趋势       │
    │  P50: {latency_p50.value if latency_p50 else 'N/A':>4}ms           总计: {total_tokens.value if total_tokens else 'N/A':>6} tokens  │
    │  P99: {latency_p99.value if latency_p99 else 'N/A':>4}ms           GPT-4: 75K (60%)         │
    ├────────────────────────────────────────────┤
    │  安全事件统计                                │
    │  注入尝试: {injection_attempts.value if injection_attempts else 0}次        敏感数据: {sensitive_data.value if sensitive_data else 0}次        │
    └────────────────────────────────────────────┘
"""
        return dashboard


class AlertManager:
    """告警管理器"""
    
    def __init__(self, metrics: List[Metric]):
        self.metrics = {m.name: m for m in metrics}
        self.alert_rules = self._load_alert_rules()
        self.alerts: List[Alert] = []
    
    def _load_alert_rules(self) -> List[AlertRule]:
        """加载告警规则"""
        return [
            AlertRule(
                name="高错误率",
                metric_name="llm_error_rate",
                condition=">",
                threshold=5.0,
                duration="5m",
                severity=AlertSeverity.P1
            ),
            AlertRule(
                name="高延迟",
                metric_name="llm_request_duration",
                condition=">",
                threshold=1000.0,
                duration="10m",
                severity=AlertSeverity.P2
            ),
            AlertRule(
                name="安全事件",
                metric_name="llm_prompt_injection_attempts",
                condition=">",
                threshold=10.0,
                duration="1h",
                severity=AlertSeverity.P1
            ),
        ]
    
    def evaluate_rules(self) -> List[Alert]:
        """评估告警规则"""
        print("  告警规则检查:")
        
        for rule in self.alert_rules:
            metric = self.metrics.get(rule.metric_name)
            if not metric:
                continue
            
            triggered = False
            if rule.condition == ">":
                triggered = metric.value > rule.threshold
            elif rule.condition == "<":
                triggered = metric.value < rule.threshold
            
            status = "警告" if triggered else "正常"
            print(f"    [{status}] {rule.name}: 当前{metric.value}{rule.condition}阈值{rule.threshold}")
            
            if triggered:
                suggestions = self._get_suggestions(rule.name)
                alert = Alert(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=f"{rule.name}: 当前值{metric.value}超过阈值{rule.threshold}",
                    value=metric.value,
                    timestamp=datetime.now().isoformat(),
                    suggestions=suggestions
                )
                self.alerts.append(alert)
        
        return self.alerts
    
    def _get_suggestions(self, rule_name: str) -> List[str]:
        """获取处理建议"""
        suggestions = {
            "高错误率": ["检查模型服务状态", "查看错误日志", "考虑降级策略"],
            "高延迟": ["检查模型负载", "考虑扩容", "优化提示词长度"],
            "安全事件": ["检查攻击来源", "加强输入过滤", "更新安全规则"],
        }
        return suggestions.get(rule_name, ["联系运维团队"])
    
    def send_notifications(self):
        """发送告警通知"""
        print("\n【步骤4】告警通知发送")
        print("  通知渠道:")
        
        for alert in self.alerts:
            print(f"    ✓ 邮件: 已发送给oncall@company.com [{alert.severity.value}]")
            print(f"    ✓ 企业微信: 已发送到运维群")
            if alert.severity in [AlertSeverity.P0, AlertSeverity.P1]:
                print(f"    ✓ PagerDuty: {alert.severity.value}事件已创建")


def main():
    """主函数"""
    print("=" * 70)
    print("Day 80: 安全扫描与可观测性集成(2) - 监控仪表盘与告警")
    print("测试架构师视角：构建AI系统的可观测性体系")
    print("=" * 70)
    print()
    
    # 步骤1：数据采集
    print("【步骤1】可观测性数据收集")
    
    metrics_collector = MetricsCollector()
    llm_metrics = metrics_collector.collect_llm_metrics()
    system_metrics = metrics_collector.collect_system_metrics()
    security_metrics = metrics_collector.collect_security_metrics()
    
    print("  Metrics指标:")
    print("    ✓ llm_request_duration: 采集成功")
    print("    ✓ llm_tokens_total: 采集成功")
    print("    ✓ llm_active_sessions: 采集成功")
    print("    ✓ llm_security_events: 采集成功")
    
    log_collector = LogCollector()
    logs = log_collector.collect_logs()
    print("\n  Logs日志:")
    print("    ✓ 应用日志: 1000条/分钟")
    print("    ✓ 访问日志: 5000条/分钟")
    print("    ✓ 安全日志: 50条/分钟")
    
    trace_collector = TraceCollector()
    traces = trace_collector.collect_traces()
    print("\n  Traces链路:")
    print("    ✓ 采样率: 10%")
    print(f"    ✓ 平均跨度数: {len(traces[0].spans) if traces else 0}个/请求")
    print()
    
    # 步骤2：仪表盘生成
    print("【步骤2】监控仪表盘生成")
    dashboard_gen = DashboardGenerator(metrics_collector.metrics)
    dashboard = dashboard_gen.generate_dashboard()
    print(dashboard)
    
    # 步骤3：告警评估
    print("【步骤3】告警规则评估")
    alert_manager = AlertManager(metrics_collector.metrics)
    alerts = alert_manager.evaluate_rules()
    
    if alerts:
        print("\n  触发告警:")
        for alert in alerts:
            print(f"    🟡 [{alert.severity.value}] {alert.rule_name}")
            print(f"       详情: {alert.message}")
            print(f"       建议: {alert.suggestions[0]}")
    else:
        print("\n  ✅ 所有指标正常，无告警")
    
    print()
    
    # 步骤4：通知发送
    if alerts:
        alert_manager.send_notifications()
    else:
        print("【步骤4】告警通知发送")
        print("  无告警，无需发送通知")
    
    print()
    
    # 结论
    print("【结论】可观测性体系运行正常")
    print("  数据采集: 正常")
    print("  仪表盘: 正常")
    if alerts:
        print(f"  告警: {len(alerts)}个{alerts[0].severity.value}（需关注）")
        print("  整体状态: 健康（需关注延迟趋势）")
        print("  建议: 监控延迟变化，如持续升高需扩容")
    else:
        print("  告警: 无")
        print("  整体状态: 健康")
        print("  建议: 继续保持监控")


if __name__ == "__main__":
    main()
