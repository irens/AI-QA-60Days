# Day 80: 安全扫描与可观测性集成(2) - 监控仪表盘与告警

## 🎯 学习目标

掌握可观测性系统的搭建方法，能够设计并实现针对AI系统的监控仪表盘和告警策略。

## 📚 理论基础

### 1. 可观测性三大支柱

```
可观测性体系
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   ┌─────────────┐    ┌─────────────┐    ┌───────────┐  │
│   │   Metrics   │    │    Logs     │    │  Traces   │  │
│   │   (指标)    │    │   (日志)    │    │  (链路)   │  │
│   └──────┬──────┘    └──────┬──────┘    └─────┬─────┘  │
│          │                  │                  │        │
│          └──────────────────┼──────────────────┘        │
│                             ↓                          │
│                    ┌─────────────────┐                 │
│                    │   Dashboards    │                 │
│                    │    (仪表盘)      │                 │
│                    └────────┬────────┘                 │
│                             ↓                          │
│                    ┌─────────────────┐                 │
│                    │    Alerts       │                 │
│                    │    (告警)       │                 │
│                    └─────────────────┘                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 1.1 Metrics（指标）

**定义**：可聚合的数值数据，用于度量系统状态和性能。

**指标类型**：
- **Counter（计数器）**：单调递增的累计值（如请求总数）
- **Gauge（仪表盘）**：可增可减的瞬时值（如当前连接数）
- **Histogram（直方图）**：采样分布（如响应时间分布）
- **Summary（摘要）**：类似直方图，但计算分位数

**AI系统关键指标**：

| 指标类别 | 指标名称 | 说明 | 示例 |
|---------|---------|------|------|
| 性能指标 | llm_request_duration | LLM请求耗时 | P50: 500ms, P99: 2000ms |
| | llm_tokens_per_second | 生成速率 | 50 tokens/s |
| 质量指标 | llm_response_quality_score | 响应质量评分 | 0-100分 |
| | llm_hallucination_rate | 幻觉率 | < 5% |
| 成本指标 | llm_token_usage | Token消耗 | 1000 tokens/请求 |
| | llm_api_cost | API调用成本 | $0.002/1K tokens |
| 安全指标 | llm_prompt_injection_attempts | 注入攻击尝试 | 10次/小时 |
| | llm_sensitive_data_detected | 敏感数据检测 | 5次/天 |

#### 1.2 Logs（日志）

**定义**：离散的事件记录，包含时间戳和上下文信息。

**日志级别**：
- **DEBUG**：调试信息，详细追踪
- **INFO**：正常运行信息
- **WARN**：警告，可能的问题
- **ERROR**：错误，功能受影响
- **FATAL**：严重错误，系统不可用

**AI系统日志规范**：

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "service": "llm-service",
  "trace_id": "abc123",
  "span_id": "def456",
  "user_id": "user_123",
  "session_id": "sess_456",
  "event": "llm_request",
  "model": "gpt-4",
  "prompt_tokens": 150,
  "completion_tokens": 200,
  "total_tokens": 350,
  "duration_ms": 1200,
  "status": "success"
}
```

#### 1.3 Traces（链路追踪）

**定义**：请求在分布式系统中的完整调用链。

**核心概念**：
- **Trace（链路）**：完整请求链路
- **Span（跨度）**：单个操作单元
- **Parent-Child**：调用关系

**AI系统链路示例**：

```
Trace: 用户查询请求
├── Span: API Gateway (2ms)
├── Span: 认证服务 (15ms)
├── Span: RAG检索 (150ms)
│   ├── Span: 查询理解 (20ms)
│   ├── Span: 向量检索 (80ms)
│   └── Span: 结果排序 (50ms)
├── Span: LLM生成 (800ms)
└── Span: 后处理 (30ms)
```

### 2. 监控仪表盘设计

#### 2.1 分层监控视图

**业务层仪表盘**：
- 用户活跃度
- 查询类型分布
- 用户满意度评分
- 业务转化率

**应用层仪表盘**：
- 请求QPS/延迟
- 错误率
- 模型调用分布
- Token消耗趋势

**系统层仪表盘**：
- CPU/内存/磁盘
- 网络IO
- 数据库连接池
- 缓存命中率

#### 2.2 关键仪表盘组件

```
┌────────────────────────────────────────────────────────────┐
│  AI系统监控仪表盘                                           │
├────────────────────────────────────────────────────────────┤
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│ │   QPS       │  │  平均延迟   │  │   错误率    │         │
│ │   1,250     │  │   450ms    │  │   0.5%     │         │
│ │   ↑ 12%    │  │   ↑ 5%     │  │   ↓ 0.1%   │         │
│ └─────────────┘  └─────────────┘  └─────────────┘         │
├────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┐  ┌─────────────────────────┐  │
│ │    延迟分布直方图        │  │    Token消耗趋势        │  │
│ │                         │  │                         │  │
│ │  ████████░░░░░░░░░░    │  │    ╱╲    ╱╲            │  │
│ │  P50: 300ms            │  │   ╱  ╲  ╱  ╲           │  │
│ │  P99: 1200ms           │  │  ╱    ╲╱    ╲____      │  │
│ └─────────────────────────┘  └─────────────────────────┘  │
├────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┐  ┌─────────────────────────┐  │
│ │    模型调用分布          │  │    安全事件告警         │  │
│ │                         │  │                         │  │
│ │  GPT-4    ████████ 60% │  │ 🔴 注入攻击: 3次       │  │
│ │  Claude   ████     25% │  │ 🟡 敏感数据: 5次       │  │
│ │  其他     ██       15% │  │ 🟢 正常              │  │
│ └─────────────────────────┘  └─────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### 3. 告警策略设计

#### 3.1 告警级别

| 级别 | 名称 | 响应时间 | 通知方式 | 示例 |
|-----|------|---------|---------|------|
| P0 | 紧急 | 5分钟 | 电话+短信+邮件 | 服务完全不可用 |
| P1 | 严重 | 15分钟 | 短信+邮件+IM | 错误率>10% |
| P2 | 警告 | 1小时 | 邮件+IM | 延迟超过阈值 |
| P3 | 提示 | 1天 | 邮件 | 资源使用率偏高 |

#### 3.2 告警规则设计

**静态阈值告警**：
```yaml
alerts:
  - name: 高错误率
    condition: error_rate > 5%
    duration: 5m
    severity: P1
    
  - name: 高延迟
    condition: p99_latency > 2000ms
    duration: 10m
    severity: P2
```

**动态阈值告警（异常检测）**：
```yaml
alerts:
  - name: 异常流量
    condition: current_qps > avg_qps_7d * 2
    severity: P1
    
  - name: 异常延迟
    condition: current_latency > percentile(latency_7d, 95)
    severity: P2
```

**智能告警（基于ML）**：
```python
# 多指标关联告警
alert_conditions = {
    "服务降级": {
        "conditions": [
            "error_rate > 1%",
            "latency_p99 > 1000ms",
            "cpu_usage > 80%"
        ],
        "logic": "AND",
        "severity": "P1"
    }
}
```

#### 3.3 告警抑制与降噪

**告警抑制规则**：
- 父告警触发时，抑制子告警
- 维护窗口期间，抑制相关告警
- 相同问题在5分钟内只发送一次告警

**告警聚合**：
```python
# 将多个相关告警聚合为一条
alert_group = {
    "title": "数据库集群异常",
    "affected_services": ["db-primary", "db-replica-1", "db-replica-2"],
    "common_symptom": "连接超时",
    "suggested_action": "检查数据库负载"
}
```

### 4. 监控工具栈

#### 4.1 开源方案

| 组件 | 工具 | 用途 |
|-----|------|------|
| 指标采集 | Prometheus | 时序数据收集 |
| 日志收集 | Loki / ELK | 日志聚合与查询 |
| 链路追踪 | Jaeger / Zipkin | 分布式追踪 |
| 可视化 | Grafana | 仪表盘展示 |
| 告警管理 | Alertmanager | 告警路由与通知 |

#### 4.2 云原生方案

| 云厂商 | 方案名称 | 特点 |
|-------|---------|------|
| AWS | CloudWatch + X-Ray | 与AWS服务深度集成 |
| Azure | Application Insights | .NET生态友好 |
| GCP | Cloud Monitoring + Trace | 强大的数据分析 |
| 阿里云 | ARMS + SLS | 国内生态完善 |

## 🔧 实战示例

### 示例1：Prometheus指标定义

```yaml
# AI系统指标定义
metrics:
  # LLM请求延迟
  - name: llm_request_duration_seconds
    type: histogram
    labels: [model, status]
    buckets: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
  
  # Token消耗
  - name: llm_tokens_total
    type: counter
    labels: [model, token_type]
  
  # 安全事件
  - name: llm_security_events_total
    type: counter
    labels: [event_type, severity]
  
  # 活跃会话数
  - name: llm_active_sessions
    type: gauge
```

### 示例2：Grafana仪表盘配置

```json
{
  "dashboard": {
    "title": "AI系统监控",
    "panels": [
      {
        "title": "请求QPS",
        "type": "stat",
        "targets": [{
          "expr": "rate(llm_requests_total[5m])"
        }]
      },
      {
        "title": "延迟分布",
        "type": "heatmap",
        "targets": [{
          "expr": "llm_request_duration_seconds_bucket"
        }]
      },
      {
        "title": "Token消耗趋势",
        "type": "graph",
        "targets": [{
          "expr": "sum(rate(llm_tokens_total[5m])) by (model)"
        }]
      }
    ]
  }
}
```

### 示例3：告警规则配置

```yaml
groups:
  - name: llm_alerts
    rules:
      - alert: 高错误率
        expr: rate(llm_requests_total{status="error"}[5m]) / rate(llm_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: P1
        annotations:
          summary: "LLM服务错误率过高"
          description: "错误率超过5%，当前值: {{ $value }}"
      
      - alert: 高延迟
        expr: histogram_quantile(0.99, rate(llm_request_duration_seconds_bucket[5m])) > 2
        for: 10m
        labels:
          severity: P2
        annotations:
          summary: "LLM响应延迟过高"
          description: "P99延迟超过2秒"
      
      - alert: 安全事件
        expr: increase(llm_security_events_total{severity="high"}[1h]) > 10
        for: 5m
        labels:
          severity: P1
        annotations:
          summary: "检测到大量安全事件"
          description: "1小时内高危安全事件超过10次"
```

## 🧪 实验验证任务

请运行本目录下的 `test_day80.py`，观察监控仪表盘与告警策略的工作流程。

### 3.1 运行命令

```bash
python test_day80.py
```

### 3.2 预期输出

```
======================================================================
Day 80: 安全扫描与可观测性集成(2) - 监控仪表盘与告警
测试架构师视角：构建AI系统的可观测性体系
======================================================================

【步骤1】可观测性数据收集
  Metrics指标:
    ✓ llm_request_duration: 采集成功
    ✓ llm_tokens_total: 采集成功
    ✓ llm_active_sessions: 采集成功
    ✓ llm_security_events: 采集成功

  Logs日志:
    ✓ 应用日志: 1000条/分钟
    ✓ 访问日志: 5000条/分钟
    ✓ 安全日志: 50条/分钟

  Traces链路:
    ✓ 采样率: 10%
    ✓ 平均跨度数: 8个/请求

【步骤2】监控仪表盘生成
  仪表盘组件:
    ┌────────────────────────────────────────────┐
    │  实时QPS: 1,250    平均延迟: 450ms         │
    │  错误率: 0.5%      活跃会话: 320           │
    ├────────────────────────────────────────────┤
    │  延迟分布直方图      Token消耗趋势         │
    │  P50: 300ms         总计: 125K tokens     │
    │  P99: 1200ms        GPT-4: 75K (60%)      │
    ├────────────────────────────────────────────┤
    │  安全事件统计                                │
    │  注入尝试: 3次      敏感数据: 5次          │
    └────────────────────────────────────────────┘

【步骤3】告警规则评估
  告警规则检查:
    [正常] 高错误率: 当前0.5% < 阈值5%
    [警告] 高延迟: 当前P99=1200ms > 阈值1000ms
    [正常] 安全事件: 当前3次/小时 < 阈值10次

  触发告警:
    🟡 [P2] 高延迟告警
       详情: P99延迟1200ms超过阈值
       建议: 检查模型负载，考虑扩容

【步骤4】告警通知发送
  通知渠道:
    ✓ 邮件: 已发送给oncall@company.com
    ✓ 企业微信: 已发送到运维群
    ✓ PagerDuty: P2事件已创建

【结论】可观测性体系运行正常
  数据采集: 正常
  仪表盘: 正常
  告警: 1个P2警告（高延迟）
  整体状态: 健康（需关注延迟趋势）
  建议: 监控延迟变化，如持续升高需扩容
```

## 📖 扩展阅读

1. **Google SRE Book** - 监控与告警章节
2. **Prometheus官方文档** - https://prometheus.io/docs/
3. **Grafana最佳实践** - https://grafana.com/docs/
4. **OpenTelemetry** - 可观测性标准 https://opentelemetry.io/

## 💡 关键要点

1. **三大支柱缺一不可**：Metrics、Logs、Traces各有侧重，需配合使用
2. **告警不是越多越好**：避免告警疲劳，聚焦关键指标
3. **可观测性驱动开发**：在设计阶段就考虑监控埋点
4. **成本与精度平衡**：合理设置采样率，控制存储成本
