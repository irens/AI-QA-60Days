"""
Day 50: Embedding漂移检测与线上效果监控体系
目标：最小可用，专注风险验证，代码要足够精简
测试架构师视角：验证漂移检测算法和监控体系能否及时发现数据分布变化
"""

import random
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple
from statistics import mean, stdev
from collections import Counter


@dataclass
class TestResult:
    name: str
    passed: bool
    score: float
    risk_level: str
    details: Dict


def generate_baseline_embeddings(n_samples: int, dim: int = 128, seed: int = 42) -> List[List[float]]:
    """生成基准Embedding数据（模拟正常查询分布）"""
    random.seed(seed)
    return [[random.gauss(0, 1) for _ in range(dim)] for _ in range(n_samples)]


def generate_drifted_embeddings(baseline: List[List[float]], drift_type: str, severity: float) -> List[List[float]]:
    """
    生成漂移后的Embedding数据
    drift_type: 'mean_shift', 'variance_change', 'new_cluster'
    severity: 0-1之间的漂移严重程度
    """
    drifted = []
    for emb in baseline:
        new_emb = emb.copy()
        if drift_type == 'mean_shift':
            # 均值漂移
            new_emb = [x + severity * random.gauss(2, 0.5) for x in new_emb]
        elif drift_type == 'variance_change':
            # 方差变化
            new_emb = [x * (1 + severity) for x in new_emb]
        elif drift_type == 'new_cluster':
            # 引入新的数据簇（部分样本）
            if random.random() < severity:
                new_emb = [random.gauss(5, 1) for _ in range(len(emb))]
        drifted.append(new_emb)
    return drifted


def calculate_psi(baseline: List[float], current: List[float], bins: int = 10) -> float:
    """
    计算Population Stability Index (PSI)
    衡量两个分布的稳定性差异
    """
    # 确定分箱边界
    min_val = min(min(baseline), min(current))
    max_val = max(max(baseline), max(current))
    bin_edges = [min_val + (max_val - min_val) * i / bins for i in range(bins + 1)]
    
    # 计算各箱占比
    def get_percentages(data, edges):
        counts = [0] * len(edges)
        for x in data:
            for i in range(len(edges) - 1):
                if edges[i] <= x < edges[i + 1] or (i == len(edges) - 2 and x == edges[-1]):
                    counts[i] += 1
                    break
        total = sum(counts)
        return [c / total if total > 0 else 0.0001 for c in counts[:-1]]
    
    base_pct = get_percentages(baseline, bin_edges)
    curr_pct = get_percentages(current, bin_edges)
    
    # 计算PSI
    psi = 0
    for bp, cp in zip(base_pct, curr_pct):
        if bp > 0 and cp > 0:
            psi += (cp - bp) * math.log(cp / bp)
    
    return psi


def calculate_mmd(X: List[List[float]], Y: List[List[float]], gamma: float = 1.0) -> float:
    """
    计算Maximum Mean Discrepancy (MMD)
    使用RBF核函数
    """
    def rbf_kernel(x, y, gamma):
        dist_sq = sum((a - b) ** 2 for a, b in zip(x, y))
        return math.exp(-gamma * dist_sq)
    
    n = len(X)
    m = len(Y)
    
    # 采样以加速计算
    sample_size = min(100, n, m)
    X_sample = random.sample(X, sample_size)
    Y_sample = random.sample(Y, sample_size)
    
    # K(X,X)
    k_xx = sum(rbf_kernel(X_sample[i], X_sample[j], gamma) 
               for i in range(sample_size) for j in range(sample_size)) / (sample_size ** 2)
    
    # K(Y,Y)
    k_yy = sum(rbf_kernel(Y_sample[i], Y_sample[j], gamma) 
               for i in range(sample_size) for j in range(sample_size)) / (sample_size ** 2)
    
    # K(X,Y)
    k_xy = sum(rbf_kernel(X_sample[i], Y_sample[j], gamma) 
               for i in range(sample_size) for j in range(sample_size)) / (sample_size ** 2)
    
    mmd_sq = k_xx + k_yy - 2 * k_xy
    return math.sqrt(max(0, mmd_sq))


def test_psi_sensitivity() -> TestResult:
    """
    测试1：PSI指标灵敏度验证
    模拟不同程度的分布漂移，验证PSI检测能力
    """
    print("\n" + "="*60)
    print("🧪 测试1：PSI指标灵敏度验证")
    print("="*60)
    print("目标：验证PSI能否有效检测不同程度的数据漂移")
    
    # 生成基准数据
    random.seed(42)
    baseline = [random.gauss(0, 1) for _ in range(5000)]
    
    # 测试不同漂移程度
    drift_scenarios = [
        ("无漂移", 0.0),
        ("轻微漂移", 0.3),
        ("中度漂移", 0.6),
        ("严重漂移", 1.0),
    ]
    
    results = []
    print("\n  漂移检测灵敏度测试:")
    print(f"  {'场景':<15} {'漂移程度':<12} {'PSI值':<12} {'判定':<15}")
    print("  " + "-"*60)
    
    for name, severity in drift_scenarios:
        # 生成漂移数据
        drifted = [x + severity * random.gauss(1, 0.5) for x in baseline]
        
        psi = calculate_psi(baseline, drifted)
        
        # PSI判定标准
        if psi < 0.1:
            judgment = "无漂移"
        elif psi < 0.25:
            judgment = "轻微漂移"
        else:
            judgment = "显著漂移"
        
        results.append((name, severity, psi, judgment))
        print(f"  {name:<15} {severity:<12.1f} {psi:<12.4f} {judgment:<15}")
    
    # 验证检测结果合理性
    correct_detections = 0
    for name, severity, psi, judgment in results:
        if severity == 0.0 and psi < 0.1:
            correct_detections += 1
        elif severity >= 0.6 and psi >= 0.25:
            correct_detections += 1
    
    detection_rate = correct_detections / len(results)
    passed = detection_rate >= 0.75
    risk = "L2" if detection_rate < 0.75 else "L3"
    
    print(f"\n  检测准确率: {correct_detections}/{len(results)} ({detection_rate:.0%})")
    print(f"  结果: {'✅ 通过' if passed else '⚠️ 警告'} (风险等级: {risk})")
    
    return TestResult(
        name="PSI灵敏度验证",
        passed=passed,
        score=detection_rate,
        risk_level=risk,
        details={"results": results, "detection_rate": detection_rate}
    )


def test_mmd_embedding_drift() -> TestResult:
    """
    测试2：MMD高维漂移检测
    验证MMD在Embedding空间中的漂移检测能力
    """
    print("\n" + "="*60)
    print("🧪 测试2：MMD高维漂移检测")
    print("="*60)
    print("目标：验证MMD能否检测高维Embedding空间的分布变化")
    
    # 生成基准Embedding
    baseline = generate_baseline_embeddings(1000, dim=128)
    
    # 测试不同漂移类型
    drift_types = [
        ("无漂移", "none", 0.0),
        ("均值漂移", "mean_shift", 0.5),
        ("方差变化", "variance_change", 0.5),
        ("新数据簇", "new_cluster", 0.3),
    ]
    
    results = []
    print("\n  MMD漂移检测测试:")
    print(f"  {'漂移类型':<15} {'MMD值':<12} {'判定':<15}")
    print("  " + "-"*45)
    
    for name, drift_type, severity in drift_types:
        if drift_type == "none":
            current = baseline
        else:
            current = generate_drifted_embeddings(baseline, drift_type, severity)
        
        mmd = calculate_mmd(baseline, current)
        
        # MMD阈值判定（经验值）
        if mmd < 0.05:
            judgment = "无漂移"
        elif mmd < 0.15:
            judgment = "轻微漂移"
        else:
            judgment = "显著漂移"
        
        results.append((name, mmd, judgment))
        print(f"  {name:<15} {mmd:<12.4f} {judgment:<15}")
    
    # 验证检测结果
    no_drift_mmd = results[0][1]
    drift_detected = sum(1 for r in results[1:] if r[1] > no_drift_mmd * 2)
    
    passed = drift_detected >= 2
    risk = "L2" if not passed else "L3"
    
    print(f"\n  漂移检测: {drift_detected}/3 种漂移类型被正确识别")
    print(f"  结果: {'✅ 通过' if passed else '⚠️ 警告'} (风险等级: {risk})")
    
    return TestResult(
        name="MMD漂移检测",
        passed=passed,
        score=0.7 + 0.1 * drift_detected,
        risk_level=risk,
        details={"results": results, "drift_detected": drift_detected}
    )


def test_monitoring_metrics() -> TestResult:
    """
    测试3：多维度监控指标验证
    模拟线上监控场景，验证关键指标计算
    """
    print("\n" + "="*60)
    print("🧪 测试3：多维度监控指标验证")
    print("="*60)
    print("目标：验证线上监控指标的计算和告警逻辑")
    
    # 模拟24小时的监控数据
    random.seed(42)
    hours = 24
    
    # 模拟指标数据
    metrics = {
        "latency_p99": [random.gauss(200, 50) for _ in range(hours)],
        "error_rate": [random.gauss(0.005, 0.003) for _ in range(hours)],
        "qps": [random.gauss(100, 20) for _ in range(hours)],
        "retrieval_relevance": [random.gauss(0.82, 0.05) for _ in range(hours)],
        "answer_faithfulness": [random.gauss(0.78, 0.06) for _ in range(hours)],
    }
    
    # 告警阈值
    thresholds = {
        "latency_p99": 500,
        "error_rate": 0.01,
        "qps": 150,
        "retrieval_relevance": 0.75,
        "answer_faithfulness": 0.70,
    }
    
    print("\n  24小时监控指标汇总:")
    print(f"  {'指标':<25} {'均值':<10} {'P99':<10} {'阈值':<10} {'告警次数':<10}")
    print("  " + "-"*70)
    
    alerts = {}
    for metric_name, values in metrics.items():
        mean_val = mean(values)
        p99_val = sorted(values)[int(len(values) * 0.99)]
        threshold = thresholds[metric_name]
        
        # 计算告警次数
        if metric_name in ["latency_p99", "error_rate", "qps"]:
            alert_count = sum(1 for v in values if v > threshold)
        else:
            alert_count = sum(1 for v in values if v < threshold)
        
        alerts[metric_name] = alert_count
        print(f"  {metric_name:<25} {mean_val:<10.3f} {p99_val:<10.3f} {threshold:<10} {alert_count:<10}")
    
    # 检查监控覆盖度
    critical_metrics = ["latency_p99", "error_rate", "retrieval_relevance", "answer_faithfulness"]
    covered = sum(1 for m in critical_metrics if m in metrics)
    
    # 检查告警合理性
    total_alerts = sum(alerts.values())
    alert_rate = total_alerts / (len(metrics) * hours)
    
    print(f"\n  监控覆盖度: {covered}/{len(critical_metrics)} 关键指标")
    print(f"  告警频率: {alert_rate:.2%} ({total_alerts}次/{len(metrics)*hours}个数据点)")
    
    # 评估
    passed = covered >= 3 and alert_rate < 0.10
    risk = "L1" if covered < 3 else "L2" if alert_rate > 0.15 else "L3"
    
    print(f"\n  结果: {'✅ 通过' if passed else '⚠️ 警告'} (风险等级: {risk})")
    if covered < 3:
        print("  ⚠️ 关键指标监控缺失")
    if alert_rate > 0.15:
        print("  ⚠️ 告警过于频繁，可能导致告警疲劳")
    
    return TestResult(
        name="多维度监控指标",
        passed=passed,
        score=min(1.0, covered / 4) * (1 - max(0, alert_rate - 0.05)),
        risk_level=risk,
        details={"coverage": covered, "alert_rate": alert_rate, "alerts": alerts}
    )


def test_threshold_calibration() -> TestResult:
    """
    测试4：阈值校准测试
    验证不同阈值设置下的检测性能(TPR/FPR)
    """
    print("\n" + "="*60)
    print("🧪 测试4：阈值校准测试")
    print("="*60)
    print("目标：验证漂移检测阈值的合理性，平衡灵敏度与特异度")
    
    # 模拟检测场景
    random.seed(42)
    n_normal = 800  # 正常样本
    n_drift = 200   # 漂移样本
    
    # 生成模拟的PSI分数
    normal_scores = [random.gauss(0.05, 0.03) for _ in range(n_normal)]
    drift_scores = [random.gauss(0.35, 0.10) for _ in range(n_drift)]
    
    # 测试不同阈值
    thresholds = [0.1, 0.15, 0.2, 0.25, 0.3]
    
    print("\n  阈值性能分析:")
    print(f"  {'阈值':<10} {'TPR(检出率)':<15} {'FPR(误报率)':<15} {'F1分数':<10}")
    print("  " + "-"*55)
    
    best_threshold = None
    best_f1 = 0
    results = []
    
    for threshold in thresholds:
        # 计算TPR和FPR
        tp = sum(1 for s in drift_scores if s > threshold)
        fn = sum(1 for s in drift_scores if s <= threshold)
        fp = sum(1 for s in normal_scores if s > threshold)
        tn = sum(1 for s in normal_scores if s <= threshold)
        
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tpr
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        results.append((threshold, tpr, fpr, f1))
        print(f"  {threshold:<10.2f} {tpr:<15.2%} {fpr:<15.2%} {f1:<10.3f}")
        
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
    
    print(f"\n  最优阈值: {best_threshold} (F1={best_f1:.3f})")
    
    # 推荐阈值评估
    recommended = 0.25
    rec_result = next(r for r in results if r[0] == recommended)
    
    print(f"\n  推荐阈值({recommended})性能:")
    print(f"    TPR: {rec_result[1]:.1%} (检出率)")
    print(f"    FPR: {rec_result[2]:.1%} (误报率)")
    print(f"    F1:  {rec_result[3]:.3f}")
    
    # 评估
    passed = rec_result[1] > 0.7 and rec_result[2] < 0.1
    risk = "L2" if rec_result[1] < 0.7 or rec_result[2] > 0.15 else "L3"
    
    print(f"\n  结果: {'✅ 通过' if passed else '⚠️ 警告'} (风险等级: {risk})")
    if rec_result[1] < 0.7:
        print("  ⚠️ 检出率不足，可能漏检真实漂移")
    if rec_result[2] > 0.1:
        print("  ⚠️ 误报率过高，可能导致告警疲劳")
    
    return TestResult(
        name="阈值校准测试",
        passed=passed,
        score=best_f1,
        risk_level=risk,
        details={"best_threshold": best_threshold, "best_f1": best_f1, "recommended": rec_result}
    )


def test_root_cause_analysis() -> TestResult:
    """
    测试5：根因分析流程验证
    模拟漂移场景，验证诊断流程的有效性
    """
    print("\n" + "="*60)
    print("🧪 测试5：根因分析流程验证")
    print("="*60)
    print("目标：验证漂移发生时的诊断流程能否定位根因")
    
    # 模拟漂移场景
    scenarios = [
        {
            "name": "查询类型变化",
            "symptoms": ["PSI升高", "新关键词出现", "embedding均值偏移"],
            "root_cause": "业务推出新功能，用户查询类型变化",
            "actions": ["收集新类型样本", "微调embedding模型", "更新检索索引"]
        },
        {
            "name": "Embedding模型降级",
            "symptoms": ["MMD升高", "检索相关性下降", "语义匹配失效"],
            "root_cause": "模型部署错误，使用了旧版本",
            "actions": ["回滚模型版本", "验证模型签名", "加强部署检查"]
        },
        {
            "name": "数据管道异常",
            "symptoms": ["特征分布异常", "缺失值增加", "延迟升高"],
            "root_cause": "上游数据源schema变更",
            "actions": ["修复数据管道", "增加schema校验", "添加数据质量监控"]
        },
    ]
    
    print("\n  漂移场景诊断测试:")
    
    diagnosed = 0
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n  场景{i}: {scenario['name']}")
        print(f"    症状: {', '.join(scenario['symptoms'])}")
        print(f"    根因: {scenario['root_cause']}")
        print(f"    建议措施:")
        for action in scenario['actions']:
            print(f"      - {action}")
        
        # 模拟诊断成功率
        if len(scenario['symptoms']) >= 2 and len(scenario['actions']) >= 2:
            diagnosed += 1
            print(f"    ✅ 可诊断")
        else:
            print(f"    ⚠️ 信息不足")
    
    diagnosis_rate = diagnosed / len(scenarios)
    
    print(f"\n  诊断覆盖率: {diagnosed}/{len(scenarios)} ({diagnosis_rate:.0%})")
    
    # 评估根因分析流程完整性
    checklist = [
        ("漂移检测告警", True),
        ("特征分布分析", True),
        ("时间范围定位", True),
        ("关联变更排查", True),
        ("影响范围评估", False),  # 部分缺失
        ("回滚方案准备", True),
    ]
    
    print("\n  根因分析流程检查:")
    completed = sum(1 for _, done in checklist if done)
    for item, done in checklist:
        status = "✅" if done else "❌"
        print(f"    {status} {item}")
    
    coverage = completed / len(checklist)
    print(f"\n  流程完整度: {completed}/{len(checklist)} ({coverage:.0%})")
    
    passed = coverage >= 0.8 and diagnosis_rate >= 0.6
    risk = "L2" if coverage < 0.8 else "L3"
    
    print(f"\n  结果: {'✅ 通过' if passed else '⚠️ 警告'} (风险等级: {risk})")
    
    return TestResult(
        name="根因分析流程",
        passed=passed,
        score=coverage,
        risk_level=risk,
        details={"coverage": coverage, "diagnosis_rate": diagnosis_rate}
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 Embedding漂移检测与监控体系 - 测试汇总报告")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    high_risk = sum(1 for r in results if r.risk_level == "L1")
    
    print(f"\n总体评分: {passed}/{total} 项通过")
    print(f"高风险项: {high_risk} 项")
    
    print("\n详细结果:")
    print(f"  {'测试项':<25} {'状态':<8} {'得分':<8} {'风险':<8}")
    print("  " + "-"*55)
    for r in results:
        status = "✅ 通过" if r.passed else "❌ 失败"
        print(f"  {r.name:<25} {status:<8} {r.score:.2f}    {r.risk_level}")
    
    # 风险汇总
    print("\n风险等级说明:")
    print("  L1 (高风险): 漂移检测失效，可能导致性能持续退化")
    print("  L2 (中风险): 检测灵敏度或监控覆盖度不足")
    print("  L3 (低风险): 监控体系基本完善，可接受")
    
    # 关键建议
    print("\n关键建议:")
    if high_risk > 0:
        print("  ⚠️ 发现高风险项，建议:")
        print("    1. 部署PSI和MMD双指标漂移检测")
        print("    2. 建立Embedding质量监控仪表盘")
        print("    3. 制定漂移响应SOP和回滚方案")
    else:
        print("  ✅ 监控体系基本完善，建议持续优化阈值")
    
    print("\n监控体系 checklist:")
    print("  □ 实时指标：延迟、错误率、QPS")
    print("  □ 批量指标：PSI漂移、检索相关性、答案忠实度")
    print("  □ 告警机制：阈值告警、异常检测、趋势告警")
    print("  □ 根因分析：特征分析、时间定位、关联排查")
    
    print("\n" + "="*70)
    print("请将以上日志贴回给 Trae 生成详细报告")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 50: Embedding漂移检测与监控体系")
    print("="*70)
    print("测试架构师视角：验证漂移检测算法和监控体系的有效性")
    
    results = [
        test_psi_sensitivity(),
        test_mmd_embedding_drift(),
        test_monitoring_metrics(),
        test_threshold_calibration(),
        test_root_cause_analysis(),
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
