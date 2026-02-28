"""
自动化测试脚本：Day 08 - A/B测试实验设计
目标：样本量计算、随机化分组、统计检验、实验健康度监控
风险视角：专注A/B测试实验设计缺陷和统计错误风险
"""

import os
import pytest
import json
import random
import hashlib
import math
import statistics
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict
import numpy as np


class MetricType(Enum):
    """指标类型"""
    CONTINUOUS = "continuous"  # 连续指标：延迟、准确率
    PROPORTION = "proportion"  # 比例指标：转化率、通过率


class TestResult(Enum):
    """检验结果"""
    SIGNIFICANT = "显著"  # 拒绝H0
    NOT_SIGNIFICANT = "不显著"  # 无法拒绝H0
    INSUFFICIENT = "样本不足"  # 未达到最小样本量


@dataclass
class SampleSizeResult:
    """样本量计算结果"""
    metric_name: str
    metric_type: MetricType
    baseline_value: float
    mde: float
    alpha: float
    power: float
    sample_size_per_group: int
    total_sample_size: int
    estimated_days: float


@dataclass
class User:
    """用户数据类"""
    user_id: str
    attributes: Dict[str, any]  # 用户属性（年龄、地域等）
    

@dataclass
class ExperimentGroup:
    """实验组"""
    name: str
    users: List[User]
    metrics: Dict[str, List[float]] = field(default_factory=dict)


@dataclass
class StatisticalTestResult:
    """统计检验结果"""
    metric_name: str
    control_mean: float
    treatment_mean: float
    difference: float
    relative_change: float
    p_value: float
    confidence_interval: Tuple[float, float]
    is_significant: bool
    effect_size: float  # Cohen's d
    sample_size_control: int
    sample_size_treatment: int


class SampleSizeCalculator:
    """样本量计算器"""
    
    @staticmethod
    def calculate_continuous(baseline_mean: float,
                            baseline_std: float,
                            mde_absolute: float,
                            alpha: float = 0.05,
                            power: float = 0.8) -> int:
        """
        连续指标样本量计算
        
        公式: n = 2 * (Z_(1-α/2) + Z_power)² * σ² / MDE²
        
        Args:
            baseline_mean: 对照组均值
            baseline_std: 对照组标准差
            mde_absolute: 绝对MDE（最小可检测效应）
            alpha: 显著性水平
            power: 统计功效
        
        Returns:
            每组所需样本量
        """
        # Z值计算（双侧检验）
        z_alpha = 1.96 if alpha == 0.05 else 2.576  # 95%或99%置信度
        z_beta = 0.84 if power == 0.8 else 1.28  # 80%或90%功效
        
        # 合并方差（假设两组方差相等）
        pooled_variance = 2 * (baseline_std ** 2)
        
        # 样本量计算
        n = ((z_alpha + z_beta) ** 2 * pooled_variance) / (mde_absolute ** 2)
        
        # 考虑20%流失率
        n_with_buffer = n / 0.8
        
        return int(math.ceil(n_with_buffer))
    
    @staticmethod
    def calculate_proportion(baseline_rate: float,
                            mde_relative: float,
                            alpha: float = 0.05,
                            power: float = 0.8) -> int:
        """
        比例指标样本量计算
        
        Args:
            baseline_rate: 对照组转化率（如0.15表示15%）
            mde_relative: 相对MDE（如0.1表示提升10%）
            alpha: 显著性水平
            power: 统计功效
        
        Returns:
            每组所需样本量
        """
        z_alpha = 1.96 if alpha == 0.05 else 2.576
        z_beta = 0.84 if power == 0.8 else 1.28
        
        p1 = baseline_rate
        p2 = baseline_rate * (1 + mde_relative)
        
        # 合并比例
        p_pooled = (p1 + p2) / 2
        
        # 样本量计算
        numerator = (z_alpha * math.sqrt(2 * p_pooled * (1 - p_pooled)) + 
                    z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        denominator = (p1 - p2) ** 2
        
        n = numerator / denominator if denominator > 0 else float('inf')
        
        # 考虑20%流失率
        n_with_buffer = n / 0.8
        
        return int(math.ceil(n_with_buffer))
    
    @staticmethod
    def estimate_experiment_duration(sample_size_per_group: int,
                                     daily_traffic: int,
                                     traffic_allocation: float = 0.5) -> float:
        """
        估算实验所需天数
        
        Args:
            sample_size_per_group: 每组所需样本量
            daily_traffic: 日活用户数
            traffic_allocation: 实验流量占比（如0.5表示50%流量参与实验）
        
        Returns:
            预计实验天数
        """
        # 每天进入实验的用户数
        daily_experiment_users = daily_traffic * traffic_allocation
        
        # 每组每天的用户数
        daily_per_group = daily_experiment_users / 2
        
        # 所需天数
        days = sample_size_per_group / daily_per_group
        
        return math.ceil(days)


class RandomizationEngine:
    """随机化引擎"""
    
    def __init__(self, salt: str = "ab_test_salt"):
        self.salt = salt
    
    def hash_randomize(self, user_id: str, 
                      num_groups: int = 2) -> int:
        """
        基于哈希的随机化
        
        Args:
            user_id: 用户ID
            num_groups: 分组数（通常为2）
        
        Returns:
            组索引（0表示对照组，1表示实验组）
        """
        # 使用用户ID + salt进行哈希
        hash_input = f"{user_id}:{self.salt}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        # 取模得到组索引
        group_index = hash_value % num_groups
        
        return group_index
    
    def stratified_randomize(self, user: User,
                            strata_vars: List[str],
                            num_groups: int = 2) -> int:
        """
        分层随机化
        
        确保各层（如年龄组、地域）内用户均匀分配
        
        Args:
            user: 用户对象
            strata_vars: 分层变量列表
            num_groups: 分组数
        
        Returns:
            组索引
        """
        # 构建分层标识
        strata_key = ":".join([str(user.attributes.get(var, "")) for var in strata_vars])
        
        # 在层内进行哈希随机化
        hash_input = f"{user.user_id}:{strata_key}:{self.salt}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        return hash_value % num_groups
    
    def assign_users(self, users: List[User],
                    method: str = "hash",
                    strata_vars: List[str] = None) -> Dict[str, ExperimentGroup]:
        """
        批量分配用户到实验组
        
        Args:
            users: 用户列表
            method: 随机化方法（hash/stratified）
            strata_vars: 分层变量（分层随机化时使用）
        
        Returns:
            实验组字典
        """
        groups = {
            "control": ExperimentGroup("control", []),
            "treatment": ExperimentGroup("treatment", [])
        }
        
        for user in users:
            if method == "stratified" and strata_vars:
                group_idx = self.stratified_randomize(user, strata_vars)
            else:
                group_idx = self.hash_randomize(user.user_id)
            
            group_name = "control" if group_idx == 0 else "treatment"
            groups[group_name].users.append(user)
        
        return groups


class StatisticalTester:
    """统计检验器"""
    
    @staticmethod
    def two_sample_t_test(control_values: List[float],
                         treatment_values: List[float],
                         alpha: float = 0.05) -> StatisticalTestResult:
        """
        双样本T检验
        
        用于连续指标（如延迟、准确率）的差异检验
        
        Args:
            control_values: 对照组数值列表
            treatment_values: 实验组数值列表
            alpha: 显著性水平
        
        Returns:
            统计检验结果
        """
        n1 = len(control_values)
        n2 = len(treatment_values)
        
        # 计算均值
        mean1 = statistics.mean(control_values)
        mean2 = statistics.mean(treatment_values)
        
        # 计算标准差
        std1 = statistics.stdev(control_values) if n1 > 1 else 0
        std2 = statistics.stdev(treatment_values) if n2 > 1 else 0
        
        # 合并标准误
        se = math.sqrt((std1**2 / n1) + (std2**2 / n2))
        
        # T统计量
        t_stat = (mean2 - mean1) / se if se > 0 else 0
        
        # 自由度（Welch's t-test）
        df = ((std1**2 / n1 + std2**2 / n2) ** 2) / \
             ((std1**2 / n1) ** 2 / (n1 - 1) + (std2**2 / n2) ** 2 / (n2 - 1)) if se > 0 else n1 + n2 - 2
        
        # p值（近似）
        # 使用标准正态分布近似（大样本时t分布接近正态）
        p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(t_stat) / math.sqrt(2))))
        
        # 置信区间
        z_alpha = 1.96  # 95% CI
        ci_lower = (mean2 - mean1) - z_alpha * se
        ci_upper = (mean2 - mean1) + z_alpha * se
        
        # Cohen's d（效应量）
        pooled_std = math.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2)) if (n1 + n2) > 2 else 1
        cohens_d = (mean2 - mean1) / pooled_std if pooled_std > 0 else 0
        
        return StatisticalTestResult(
            metric_name="continuous",
            control_mean=mean1,
            treatment_mean=mean2,
            difference=mean2 - mean1,
            relative_change=(mean2 - mean1) / mean1 if mean1 != 0 else 0,
            p_value=p_value,
            confidence_interval=(ci_lower, ci_upper),
            is_significant=p_value < alpha,
            effect_size=cohens_d,
            sample_size_control=n1,
            sample_size_treatment=n2
        )
    
    @staticmethod
    def chi_square_test(control_success: int, control_total: int,
                       treatment_success: int, treatment_total: int,
                       alpha: float = 0.05) -> Dict:
        """
        卡方检验
        
        用于比例指标（如转化率）的差异检验
        
        Args:
            control_success: 对照组成功数
            control_total: 对照组总数
            treatment_success: 实验组成功数
            treatment_total: 实验组总数
            alpha: 显著性水平
        
        Returns:
            检验结果字典
        """
        # 构建列联表
        control_failure = control_total - control_success
        treatment_failure = treatment_total - treatment_success
        
        # 计算期望频数
        total_success = control_success + treatment_success
        total_failure = control_failure + treatment_failure
        total = control_total + treatment_total
        
        expected_control_success = (control_total * total_success) / total
        expected_treatment_success = (treatment_total * total_success) / total
        expected_control_failure = (control_total * total_failure) / total
        expected_treatment_failure = (treatment_total * total_failure) / total
        
        # 卡方统计量
        def chi_square_cell(observed, expected):
            return ((observed - expected) ** 2) / expected if expected > 0 else 0
        
        chi2 = (chi_square_cell(control_success, expected_control_success) +
                chi_square_cell(treatment_success, expected_treatment_success) +
                chi_square_cell(control_failure, expected_control_failure) +
                chi_square_cell(treatment_failure, expected_treatment_failure))
        
        # p值（自由度=1）
        p_value = 1 - 0.5 * (1 + math.erf(math.sqrt(chi2 / 2)))
        
        # 转化率
        control_rate = control_success / control_total if control_total > 0 else 0
        treatment_rate = treatment_success / treatment_total if treatment_total > 0 else 0
        
        return {
            "metric_name": "proportion",
            "control_rate": control_rate,
            "treatment_rate": treatment_rate,
            "difference": treatment_rate - control_rate,
            "relative_change": (treatment_rate - control_rate) / control_rate if control_rate > 0 else 0,
            "chi2_statistic": chi2,
            "p_value": p_value,
            "is_significant": p_value < alpha,
            "sample_size_control": control_total,
            "sample_size_treatment": treatment_total
        }
    
    @staticmethod
    def bonferroni_correction(p_values: List[float], alpha: float = 0.05) -> List[bool]:
        """
        Bonferroni校正
        
        多重比较校正，降低假阳性率
        
        Args:
            p_values: p值列表
            alpha: 原始显著性水平
        
        Returns:
            校正后的显著性判断列表
        """
        m = len(p_values)
        corrected_alpha = alpha / m  # Bonferroni校正
        
        return [p < corrected_alpha for p in p_values]


class ExperimentHealthMonitor:
    """实验健康度监控器"""
    
    @staticmethod
    def check_srm(control_size: int, treatment_size: int,
                 expected_ratio: float = 0.5,
                 alpha: float = 0.01) -> Dict:
        """
        SRM (Sample Ratio Mismatch) 检测
        
        检测分组比例是否偏离预期，发现随机化问题
        
        Args:
            control_size: 对照组样本量
            treatment_size: 实验组样本量
            expected_ratio: 预期对照组比例
            alpha: 显著性水平
        
        Returns:
            SRM检测结果
        """
        total = control_size + treatment_size
        observed_ratio = control_size / total if total > 0 else 0
        
        # 卡方检验检测比例偏离
        expected_control = total * expected_ratio
        expected_treatment = total * (1 - expected_ratio)
        
        chi2 = ((control_size - expected_control) ** 2 / expected_control +
                (treatment_size - expected_treatment) ** 2 / expected_treatment)
        
        # p值
        p_value = 1 - 0.5 * (1 + math.erf(math.sqrt(chi2 / 2)))
        
        is_srm = p_value < alpha
        
        return {
            "is_srm": is_srm,
            "p_value": p_value,
            "observed_ratio": observed_ratio,
            "expected_ratio": expected_ratio,
            "control_size": control_size,
            "treatment_size": treatment_size,
            "severity": "HIGH" if is_srm else "OK"
        }
    
    @staticmethod
    def check_guardrail_metrics(control_metrics: Dict[str, float],
                               treatment_metrics: Dict[str, float],
                               thresholds: Dict[str, float]) -> List[Dict]:
        """
        护栏指标检查
        
        检查必须保护的指标是否退化
        
        Args:
            control_metrics: 对照组指标
            treatment_metrics: 实验组指标
            thresholds: 各指标的退化阈值
        
        Returns:
            护栏检查结果列表
        """
        alerts = []
        
        for metric_name, threshold in thresholds.items():
            control_val = control_metrics.get(metric_name, 0)
            treatment_val = treatment_metrics.get(metric_name, 0)
            
            # 计算变化
            if control_val > 0:
                change_pct = (treatment_val - control_val) / control_val
            else:
                change_pct = 0
            
            # 检查是否超过阈值
            is_violation = change_pct < -threshold  # 负向变化超过阈值
            
            alerts.append({
                "metric_name": metric_name,
                "control_value": control_val,
                "treatment_value": treatment_val,
                "change_pct": change_pct,
                "threshold": threshold,
                "is_violation": is_violation,
                "severity": "CRITICAL" if is_violation else "OK"
            })
        
        return alerts
    
    @staticmethod
    def should_stop_early(current_sample_size: int,
                         min_sample_size: int,
                         guardrail_violations: List[Dict]) -> Tuple[bool, str]:
        """
        是否应该提前停止实验
        
        Args:
            current_sample_size: 当前样本量
            min_sample_size: 最小样本量
            guardrail_violations: 护栏违规列表
        
        Returns:
            (是否应该停止, 原因)
        """
        # 护栏违规必须停止
        critical_violations = [v for v in guardrail_violations if v["severity"] == "CRITICAL"]
        if critical_violations:
            return True, f"护栏指标严重违规: {', '.join([v['metric_name'] for v in critical_violations])}"
        
        # 未达到最小样本量不能停止
        if current_sample_size < min_sample_size:
            return False, f"样本量不足 ({current_sample_size}/{min_sample_size})"
        
        return False, "实验正常进行中"


class ABTestExperiment:
    """A/B测试实验主类"""
    
    def __init__(self, experiment_name: str):
        self.experiment_name = experiment_name
        self.sample_calculator = SampleSizeCalculator()
        self.randomizer = RandomizationEngine()
        self.tester = StatisticalTester()
        self.monitor = ExperimentHealthMonitor()
        
        self.groups: Dict[str, ExperimentGroup] = {}
        self.results: Dict[str, any] = {}
    
    def design_experiment(self, metrics_config: List[Dict],
                         daily_traffic: int = 10000) -> Dict:
        """
        设计实验 - 计算样本量和时长
        
        Args:
            metrics_config: 指标配置列表
            daily_traffic: 日活用户数
        
        Returns:
            实验设计方案
        """
        print(f"\n📐 实验设计: {self.experiment_name}")
        print("=" * 60)
        
        sample_size_results = []
        max_sample_size = 0
        
        for config in metrics_config:
            metric_name = config["name"]
            metric_type = config["type"]
            
            if metric_type == MetricType.CONTINUOUS:
                n = self.sample_calculator.calculate_continuous(
                    baseline_mean=config["baseline_mean"],
                    baseline_std=config["baseline_std"],
                    mde_absolute=config["mde"]
                )
            else:  # PROPORTION
                n = self.sample_calculator.calculate_proportion(
                    baseline_rate=config["baseline_rate"],
                    mde_relative=config["mde"]
                )
            
            days = self.sample_calculator.estimate_experiment_duration(
                sample_size_per_group=n,
                daily_traffic=daily_traffic
            )
            
            result = SampleSizeResult(
                metric_name=metric_name,
                metric_type=metric_type,
                baseline_value=config.get("baseline_mean") or config.get("baseline_rate"),
                mde=config["mde"],
                alpha=0.05,
                power=0.8,
                sample_size_per_group=n,
                total_sample_size=n * 2,
                estimated_days=days
            )
            
            sample_size_results.append(result)
            max_sample_size = max(max_sample_size, n)
            
            print(f"\n   📊 {metric_name}")
            print(f"      类型: {metric_type.value}")
            print(f"      基线: {result.baseline_value}")
            print(f"      MDE: {result.mde}")
            print(f"      每组样本量: {n}")
            print(f"      预计天数: {days}天")
        
        # 取最大样本量作为实验要求
        total_days = self.sample_calculator.estimate_experiment_duration(
            max_sample_size, daily_traffic
        )
        
        design = {
            "experiment_name": self.experiment_name,
            "sample_size_per_group": max_sample_size,
            "total_sample_size": max_sample_size * 2,
            "estimated_days": total_days,
            "daily_traffic": daily_traffic,
            "metrics": [{
                "name": r.metric_name,
                "sample_size": r.sample_size_per_group,
                "days": r.estimated_days
            } for r in sample_size_results]
        }
        
        print(f"\n   📋 实验方案总结")
        print(f"      每组最小样本量: {max_sample_size}")
        print(f"      总样本量: {max_sample_size * 2}")
        print(f"      预计实验时长: {total_days}天")
        
        return design
    
    def run_experiment(self, num_users: int = 10000,
                      treatment_effect: Dict[str, float] = None) -> Dict:
        """
        运行模拟实验
        
        Args:
            num_users: 模拟用户数
            treatment_effect: 实验组效果（如{"accuracy": 0.05}表示准确率+5%）
        
        Returns:
            实验结果
        """
        print(f"\n🧪 运行实验: {self.experiment_name}")
        print("=" * 60)
        
        treatment_effect = treatment_effect or {}
        
        # 1. 生成模拟用户
        users = self._generate_mock_users(num_users)
        print(f"   生成用户: {len(users)}人")
        
        # 2. 随机化分组
        self.groups = self.randomizer.assign_users(users, method="hash")
        control_size = len(self.groups["control"].users)
        treatment_size = len(self.groups["treatment"].users)
        print(f"   分组结果: 对照组{control_size}人, 实验组{treatment_size}人")
        
        # 3. SRM检测
        srm_result = self.monitor.check_srm(control_size, treatment_size)
        if srm_result["is_srm"]:
            print(f"   ⚠️  SRM警告: 分组比例异常 (p={srm_result['p_value']:.4f})")
        else:
            print(f"   ✅ SRM检查通过")
        
        # 4. 模拟指标数据
        self._simulate_metrics(treatment_effect)
        
        # 5. 统计检验
        test_results = self._analyze_results()
        
        # 6. 生成报告
        report = self._generate_report(test_results, srm_result)
        
        return report
    
    def _generate_mock_users(self, num_users: int) -> List[User]:
        """生成模拟用户"""
        users = []
        for i in range(num_users):
            user_id = f"user_{i:06d}"
            attributes = {
                "age_group": random.choice(["18-25", "26-35", "36-45", "46+"]),
                "region": random.choice(["north", "south", "east", "west"]),
                "device": random.choice(["ios", "android", "web"])
            }
            users.append(User(user_id, attributes))
        return users
    
    def _simulate_metrics(self, treatment_effect: Dict[str, float]):
        """模拟指标数据"""
        # 模拟准确率（连续指标）
        baseline_accuracy = 0.85
        baseline_std = 0.05
        
        control_accuracy = [random.gauss(baseline_accuracy, baseline_std) 
                           for _ in self.groups["control"].users]
        
        accuracy_effect = treatment_effect.get("accuracy", 0)
        treatment_accuracy = [random.gauss(baseline_accuracy + accuracy_effect, baseline_std) 
                             for _ in self.groups["treatment"].users]
        
        self.groups["control"].metrics["accuracy"] = control_accuracy
        self.groups["treatment"].metrics["accuracy"] = treatment_accuracy
        
        # 模拟延迟（连续指标）
        baseline_latency = 500  # ms
        latency_std = 50
        
        control_latency = [random.gauss(baseline_latency, latency_std) 
                          for _ in self.groups["control"].users]
        
        latency_effect = treatment_effect.get("latency", 0)
        treatment_latency = [random.gauss(baseline_latency + latency_effect, latency_std) 
                            for _ in self.groups["treatment"].users]
        
        self.groups["control"].metrics["latency"] = control_latency
        self.groups["treatment"].metrics["latency"] = treatment_latency
        
        # 模拟转化率（比例指标）
        baseline_conversion = 0.15
        conversion_effect = treatment_effect.get("conversion", 0)
        
        control_conversions = sum(random.random() < baseline_conversion 
                                 for _ in self.groups["control"].users)
        treatment_conversions = sum(random.random() < (baseline_conversion + conversion_effect) 
                                   for _ in self.groups["treatment"].users)
        
        self.groups["control"].metrics["conversions"] = control_conversions
        self.groups["treatment"].metrics["conversions"] = treatment_conversions
    
    def _analyze_results(self) -> List[Dict]:
        """分析实验结果"""
        results = []
        
        # 准确率T检验
        accuracy_result = self.tester.two_sample_t_test(
            self.groups["control"].metrics["accuracy"],
            self.groups["treatment"].metrics["accuracy"]
        )
        accuracy_result.metric_name = "accuracy"
        results.append(accuracy_result)
        
        # 延迟T检验
        latency_result = self.tester.two_sample_t_test(
            self.groups["control"].metrics["latency"],
            self.groups["treatment"].metrics["latency"]
        )
        latency_result.metric_name = "latency"
        results.append(latency_result)
        
        # 转化率卡方检验
        conversion_result = self.tester.chi_square_test(
            self.groups["control"].metrics["conversions"],
            len(self.groups["control"].users),
            self.groups["treatment"].metrics["conversions"],
            len(self.groups["treatment"].users)
        )
        results.append(conversion_result)
        
        return results
    
    def _generate_report(self, test_results: List, srm_result: Dict) -> Dict:
        """生成实验报告"""
        print(f"\n📊 实验结果分析")
        print("-" * 60)
        
        significant_count = 0
        for result in test_results:
            if hasattr(result, 'metric_name'):
                # T检验结果
                is_sig = result.is_significant
                icon = "✅" if is_sig else "❌"
                direction = "↑" if result.difference > 0 else "↓"
                
                print(f"   {icon} {result.metric_name:15s}: "
                      f"{result.control_mean:.4f} → {result.treatment_mean:.4f} "
                      f"({direction}{result.relative_change*100:+.2f}%) "
                      f"p={result.p_value:.4f}")
                
                if is_sig:
                    significant_count += 1
            else:
                # 卡方检验结果
                is_sig = result["is_significant"]
                icon = "✅" if is_sig else "❌"
                direction = "↑" if result["difference"] > 0 else "↓"
                
                print(f"   {icon} {result['metric_name']:15s}: "
                      f"{result['control_rate']:.2%} → {result['treatment_rate']:.2%} "
                      f"({direction}{result['relative_change']*100:+.2f}%) "
                      f"p={result['p_value']:.4f}")
                
                if is_sig:
                    significant_count += 1
        
        # 多重比较校正
        p_values = [r.p_value if hasattr(r, 'p_value') else r["p_value"] for r in test_results]
        corrected_significance = self.tester.bonferroni_correction(p_values)
        
        print(f"\n   📋 统计摘要")
        print(f"      检验指标数: {len(test_results)}")
        print(f"      显著指标数(校正前): {significant_count}")
        print(f"      显著指标数(Bonferroni校正后): {sum(corrected_significance)}")
        print(f"      SRM检测: {'通过' if not srm_result['is_srm'] else '异常'}")
        
        report = {
            "experiment_name": self.experiment_name,
            "test_results": test_results,
            "srm_result": srm_result,
            "significant_count": significant_count,
            "bonferroni_corrected": sum(corrected_significance),
            "recommendation": "建议发布" if significant_count > 0 and not srm_result["is_srm"] else "需谨慎"
        }
        
        return report


# ============ pytest 测试用例 ============

class TestDay08ABTesting:
    """Day 08: A/B测试实验设计测试类"""
    
    @pytest.fixture(scope="class")
    def experiment(self):
        """实验fixture"""
        return ABTestExperiment("llm_model_ab_test")
    
    def test_sample_size_calculation(self):
        """
        测试样本量计算
        
        风险点：样本量不足导致统计功效不足
        验证：样本量计算公式正确性
        """
        calculator = SampleSizeCalculator()
        
        # 连续指标样本量
        n_continuous = calculator.calculate_continuous(
            baseline_mean=0.85,
            baseline_std=0.05,
            mde_absolute=0.02
        )
        
        # 断言：样本量合理
        assert n_continuous > 100, "连续指标样本量过小"
        assert n_continuous < 10000, "连续指标样本量过大"
        
        # 比例指标样本量
        n_proportion = calculator.calculate_proportion(
            baseline_rate=0.15,
            mde_relative=0.10
        )
        
        # 断言：样本量合理
        assert n_proportion > 100, "比例指标样本量过小"
        assert n_proportion < 50000, "比例指标样本量过大"
        
        print(f"\n✅ 样本量计算测试通过: 连续指标n={n_continuous}, 比例指标n={n_proportion}")
    
    def test_randomization_consistency(self):
        """
        测试随机化一致性
        
        风险点：同一用户多次分配结果不一致
        验证：哈希随机化的一致性
        """
        randomizer = RandomizationEngine()
        
        user_id = "user_12345"
        
        # 多次随机化同一用户
        assignments = [randomizer.hash_randomize(user_id) for _ in range(10)]
        
        # 断言：分配结果一致
        assert all(a == assignments[0] for a in assignments), "随机化不一致"
        
        # 断言：分布均匀
        test_users = [f"user_{i}" for i in range(1000)]
        group_0 = sum(1 for u in test_users if randomizer.hash_randomize(u) == 0)
        group_1 = sum(1 for u in test_users if randomizer.hash_randomize(u) == 1)
        
        ratio = group_0 / (group_0 + group_1)
        assert 0.45 < ratio < 0.55, f"分组比例不均衡: {ratio:.2%}"
        
        print(f"\n✅ 随机化一致性测试通过: 分组比例 {ratio:.1%}")
    
    def test_statistical_test_accuracy(self):
        """
        测试统计检验准确性
        
        风险点：统计检验方法错误导致假阳性/假阴性
        验证：T检验和卡方检验正确性
        """
        tester = StatisticalTester()
        
        # 测试T检验 - 有明显差异的数据
        control = [0.80, 0.82, 0.79, 0.81, 0.83] * 20  # 均值0.81
        treatment = [0.85, 0.87, 0.86, 0.88, 0.84] * 20  # 均值0.86
        
        result = tester.two_sample_t_test(control, treatment)
        
        # 断言：检测到显著差异
        assert result.is_significant, "应检测到显著差异"
        assert result.difference > 0, "实验组应优于对照组"
        
        # 测试卡方检验
        chi2_result = tester.chi_square_test(
            control_success=80, control_total=100,
            treatment_success=90, treatment_total=100
        )
        
        # 断言：转化率差异被检测
        assert chi2_result["treatment_rate"] > chi2_result["control_rate"]
        
        print(f"\n✅ 统计检验测试通过: T检验p={result.p_value:.4f}, 卡方检验p={chi2_result['p_value']:.4f}")
    
    def test_srm_detection(self):
        """
        测试SRM检测
        
        风险点：分组比例失衡未被发现
        验证：SRM检测能发现比例异常
        """
        monitor = ExperimentHealthMonitor()
        
        # 正常分组
        normal_result = monitor.check_srm(500, 500)
        assert not normal_result["is_srm"], "正常分组不应触发SRM"
        
        # 异常分组（严重失衡）
        abnormal_result = monitor.check_srm(700, 300)
        assert abnormal_result["is_srm"], "异常分组应触发SRM"
        
        print(f"\n✅ SRM检测测试通过: 正常分组p={normal_result['p_value']:.4f}, 异常分组p={abnormal_result['p_value']:.4f}")
    
    def test_full_experiment_workflow(self, experiment):
        """
        测试完整实验流程
        
        风险点：实验流程各环节集成失败
        验证：从设计到分析的完整流程
        """
        # 1. 实验设计
        metrics_config = [
            {
                "name": "accuracy",
                "type": MetricType.CONTINUOUS,
                "baseline_mean": 0.85,
                "baseline_std": 0.05,
                "mde": 0.02
            },
            {
                "name": "conversion",
                "type": MetricType.PROPORTION,
                "baseline_rate": 0.15,
                "mde": 0.10
            }
        ]
        
        design = experiment.design_experiment(metrics_config, daily_traffic=1000)
        
        # 断言：设计方案完整
        assert "sample_size_per_group" in design
        assert "estimated_days" in design
        
        # 2. 运行实验（模拟有正向效果）
        report = experiment.run_experiment(
            num_users=2000,
            treatment_effect={"accuracy": 0.03}  # 准确率+3%
        )
        
        # 断言：实验结果完整
        assert "test_results" in report
        assert "srm_result" in report
        
        print(f"\n✅ 完整实验流程测试通过: 实验时长{design['estimated_days']}天")


# 主执行入口
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 08: A/B测试实验设计")
    print("="*70)
    print("\n测试内容:")
    print("  1. 样本量计算验证")
    print("  2. 随机化分组验证")
    print("  3. 统计检验验证")
    print("  4. 实验健康度监控")
    print("\n" + "-"*70)
    
    # 创建实验并运行完整流程
    experiment = ABTestExperiment("llm_model_upgrade_ab_test")
    
    # 实验设计
    metrics_config = [
        {
            "name": "accuracy",
            "type": MetricType.CONTINUOUS,
            "baseline_mean": 0.85,
            "baseline_std": 0.05,
            "mde": 0.02  # 检测2%的准确率提升
        },
        {
            "name": "latency",
            "type": MetricType.CONTINUOUS,
            "baseline_mean": 500,
            "baseline_std": 50,
            "mde": 30  # 检测30ms的延迟变化
        },
        {
            "name": "conversion",
            "type": MetricType.PROPORTION,
            "baseline_rate": 0.15,
            "mde": 0.10  # 检测10%的相对转化率提升
        }
    ]
    
    design = experiment.design_experiment(metrics_config, daily_traffic=5000)
    
    # 运行多个实验场景
    scenarios = [
        ("无效果", {"accuracy": 0, "latency": 0, "conversion": 0}),
        ("轻微改善", {"accuracy": 0.02, "latency": -20, "conversion": 0.05}),
        ("显著改善", {"accuracy": 0.05, "latency": -50, "conversion": 0.15}),
    ]
    
    print("\n" + "="*70)
    print("🧪 多场景实验模拟")
    print("="*70)
    
    for scenario_name, effects in scenarios:
        print(f"\n【场景: {scenario_name}】")
        exp = ABTestExperiment(f"ab_test_{scenario_name}")
        report = exp.run_experiment(num_users=2000, treatment_effect=effects)
    
    print("\n" + "="*70)
    print("✅ 测试执行完毕，请将上方日志发给 Trae 生成详细报告。")
    print("="*70)
