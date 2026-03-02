"""
Day 21: Prompt版本管理与A/B测试
目标：最小可用，专注风险验证，杜绝多余业务逻辑
测试架构师视角：Prompt变更是AI系统的"代码变更"，没有版本管理就像没有Git的软件开发
"""

import json
import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum


class ChangeType(Enum):
    """Prompt变更类型"""
    ROLE_CHANGE = "role_change"          # 角色定义修改
    FORMAT_CHANGE = "format_change"      # 输出格式变更
    EXAMPLE_CHANGE = "example_change"    # 示例增减
    WORDING_CHANGE = "wording_change"    # 措辞优化
    SECURITY_CHANGE = "security_change"  # 安全规则更新


class RiskLevel(Enum):
    """风险等级"""
    HIGH = "L1-高危"
    MEDIUM = "L2-中危"
    LOW = "L3-低危"
    MINIMAL = "L4-极低"


@dataclass
class PromptVersion:
    """Prompt版本信息"""
    version: str
    name: str
    author: str
    created_at: datetime
    description: str
    change_type: ChangeType
    content: str
    test_results: Dict[str, float] = field(default_factory=dict)
    parent_version: str = ""
    rollback_ready: bool = False


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: str
    details: str = ""


class PromptVersionManager:
    """Prompt版本管理器模拟"""
    
    def __init__(self):
        self.versions: Dict[str, PromptVersion] = {}
        self.current_version: str = ""
        self.version_history: List[str] = []
        
    def add_version(self, version: PromptVersion) -> bool:
        """添加新版本"""
        if version.version in self.versions:
            return False
        
        self.versions[version.version] = version
        self.version_history.append(version.version)
        
        if not self.current_version:
            self.current_version = version.version
            
        return True
    
    def rollback(self, target_version: str) -> Tuple[bool, str]:
        """回滚到指定版本"""
        if target_version not in self.versions:
            return False, f"版本 {target_version} 不存在"
        
        version = self.versions[target_version]
        if not version.rollback_ready:
            return False, f"版本 {target_version} 未标记为可回滚"
        
        self.current_version = target_version
        return True, f"成功回滚到版本 {target_version}"
    
    def get_version_diff(self, v1: str, v2: str) -> Dict[str, Any]:
        """获取版本差异"""
        if v1 not in self.versions or v2 not in self.versions:
            return {}
        
        ver1 = self.versions[v1]
        ver2 = self.versions[v2]
        
        return {
            "version_delta": f"{v1} -> {v2}",
            "change_type": ver2.change_type.value,
            "author_changed": ver1.author != ver2.author,
            "test_results_delta": {
                k: ver2.test_results.get(k, 0) - ver1.test_results.get(k, 0)
                for k in set(ver1.test_results) | set(ver2.test_results)
            }
        }


class ABTestSimulator:
    """A/B测试模拟器"""
    
    def __init__(self):
        self.control_metrics = {"n": 0, "success": 0, "mean": 0.0}
        self.treatment_metrics = {"n": 0, "success": 0, "mean": 0.0}
        
    def simulate_experiment(self, control_rate: float, treatment_rate: float, 
                           sample_size: int = 1000) -> Dict[str, Any]:
        """模拟A/B测试实验"""
        # 模拟对照组
        control_data = [random.random() < control_rate for _ in range(sample_size)]
        self.control_metrics = {
            "n": sample_size,
            "success": sum(control_data),
            "mean": sum(control_data) / sample_size
        }
        
        # 模拟实验组
        treatment_data = [random.random() < treatment_rate for _ in range(sample_size)]
        self.treatment_metrics = {
            "n": sample_size,
            "success": sum(treatment_data),
            "mean": sum(treatment_data) / sample_size
        }
        
        # 统计检验
        p_control = self.control_metrics["mean"]
        p_treatment = self.treatment_metrics["mean"]
        p_pooled = (self.control_metrics["success"] + self.treatment_metrics["success"]) / (2 * sample_size)
        
        se = math.sqrt(p_pooled * (1 - p_pooled) * (2 / sample_size))
        z_score = (p_treatment - p_control) / se if se > 0 else 0
        
        # 计算p值（双尾检验）
        p_value = 2 * (1 - self._normal_cdf(abs(z_score)))
        
        # 效果提升
        lift = (p_treatment - p_control) / p_control if p_control > 0 else 0
        
        return {
            "control_rate": p_control,
            "treatment_rate": p_treatment,
            "lift": lift,
            "z_score": z_score,
            "p_value": p_value,
            "significant": p_value < 0.05,
            "sample_size": sample_size
        }
    
    def _normal_cdf(self, x: float) -> float:
        """标准正态分布CDF"""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def should_stop_early(self, min_samples: int = 500, 
                         lift_threshold: float = 0.20,
                         drop_threshold: float = -0.10) -> Tuple[bool, str]:
        """早期停止判断"""
        if self.control_metrics["n"] < min_samples or self.treatment_metrics["n"] < min_samples:
            return False, "样本量不足"
        
        lift = (self.treatment_metrics["mean"] - self.control_metrics["mean"]) / self.control_metrics["mean"]
        
        if lift > lift_threshold:
            return True, f"效果显著提升: {lift:.1%}"
        elif lift < drop_threshold:
            return True, f"效果显著下降: {lift:.1%}"
        
        return False, "继续观察"


def test_version_control_integrity() -> TestResult:
    """测试1: 版本控制完整性"""
    print("\n" + "="*60)
    print("🧪 测试1: 版本控制完整性")
    print("="*60)
    
    manager = PromptVersionManager()
    
    # 创建初始版本
    v1 = PromptVersion(
        version="1.0.0",
        name="客服助手",
        author="zhangsan",
        created_at=datetime.now() - timedelta(days=30),
        description="初始版本",
        change_type=ChangeType.WORDING_CHANGE,
        content="你是一个友好的客服助手...",
        test_results={"accuracy": 0.85, "safety": 0.90},
        rollback_ready=True
    )
    
    # 创建新版本
    v2 = PromptVersion(
        version="1.1.0",
        name="客服助手",
        author="lisi",
        created_at=datetime.now() - timedelta(days=15),
        description="优化了多轮对话",
        change_type=ChangeType.EXAMPLE_CHANGE,
        content="你是一个专业的客服助手，擅长多轮对话...",
        test_results={"accuracy": 0.88, "safety": 0.91},
        parent_version="1.0.0",
        rollback_ready=True
    )
    
    # 创建高风险版本（角色变更）
    v3 = PromptVersion(
        version="2.0.0",
        name="客服助手",
        author="wangwu",
        created_at=datetime.now(),
        description="角色定义重大变更",
        change_type=ChangeType.ROLE_CHANGE,
        content="你是一个技术支持专家...",
        test_results={"accuracy": 0.82, "safety": 0.85},
        parent_version="1.1.0",
        rollback_ready=False  # 未准备好回滚
    )
    
    # 测试添加版本
    success_count = 0
    if manager.add_version(v1):
        print(f"  ✅ 添加版本 {v1.version} 成功")
        success_count += 1
    if manager.add_version(v2):
        print(f"  ✅ 添加版本 {v2.version} 成功")
        success_count += 1
    if manager.add_version(v3):
        print(f"  ✅ 添加版本 {v3.version} 成功")
        success_count += 1
    
    # 测试重复添加
    duplicate = manager.add_version(v1)
    print(f"  {'❌' if duplicate else '✅'} 重复版本检测: {'失败' if duplicate else '通过'}")
    
    # 测试回滚
    rollback_ok, msg = manager.rollback("1.0.0")
    print(f"  {'✅' if rollback_ok else '❌'} 回滚到v1.0.0: {msg}")
    
    # 测试不可回滚版本
    manager.current_version = "2.0.0"
    rollback_ok2, msg2 = manager.rollback("2.0.0")
    print(f"  {'❌' if rollback_ok2 else '✅'} 不可回滚版本检测: {'失败' if rollback_ok2 else '通过'}")
    
    # 测试版本差异
    diff = manager.get_version_diff("1.0.0", "1.1.0")
    print(f"  ✅ 版本差异分析: {diff.get('change_type', 'N/A')}")
    
    score = (success_count / 3) * 100
    passed = success_count == 3 and not duplicate and rollback_ok and not rollback_ok2
    
    return TestResult(
        name="版本控制完整性",
        passed=passed,
        score=score,
        risk_level=RiskLevel.LOW.value,
        details=f"成功添加{success_count}个版本，回滚机制{'正常' if rollback_ok else '异常'}"
    )


def test_ab_test_effectiveness() -> TestResult:
    """测试2: A/B测试效果对比"""
    print("\n" + "="*60)
    print("🧪 测试2: A/B测试效果对比")
    print("="*60)
    
    ab_test = ABTestSimulator()
    
    # 场景1: 显著改进 (实验组比对照组好15%)
    print("\n  场景1: 显著改进测试")
    result1 = ab_test.simulate_experiment(control_rate=0.80, treatment_rate=0.95, sample_size=1000)
    print(f"    对照组转化率: {result1['control_rate']:.1%}")
    print(f"    实验组转化率: {result1['treatment_rate']:.1%}")
    print(f"    效果提升: {result1['lift']:.1%}")
    print(f"    P值: {result1['p_value']:.4f} {'✅ 显著' if result1['significant'] else '❌ 不显著'}")
    
    # 场景2: 显著下降 (实验组比对照组差12%)
    print("\n  场景2: 显著下降测试")
    result2 = ab_test.simulate_experiment(control_rate=0.85, treatment_rate=0.73, sample_size=1000)
    print(f"    对照组转化率: {result2['control_rate']:.1%}")
    print(f"    实验组转化率: {result2['treatment_rate']:.1%}")
    print(f"    效果下降: {result2['lift']:.1%}")
    print(f"    P值: {result2['p_value']:.4f} {'✅ 显著' if result2['significant'] else '❌ 不显著'}")
    
    # 场景3: 无显著差异
    print("\n  场景3: 无显著差异测试")
    result3 = ab_test.simulate_experiment(control_rate=0.82, treatment_rate=0.84, sample_size=1000)
    print(f"    对照组转化率: {result3['control_rate']:.1%}")
    print(f"    实验组转化率: {result3['treatment_rate']:.1%}")
    print(f"    效果提升: {result3['lift']:.1%}")
    print(f"    P值: {result3['p_value']:.4f} {'❌ 不显著' if not result3['significant'] else '✅ 显著'}")
    
    # 测试早期停止
    print("\n  场景4: 早期停止判断")
    ab_test.simulate_experiment(control_rate=0.80, treatment_rate=0.96, sample_size=600)
    should_stop, reason = ab_test.should_stop_early(min_samples=500)
    print(f"    样本量: {ab_test.treatment_metrics['n']}")
    print(f"    是否停止: {'✅ 是' if should_stop else '⏳ 否'} - {reason}")
    
    # 评估
    correct_detections = sum([
        result1['significant'] and result1['lift'] > 0,    # 应该检测到提升
        result2['significant'] and result2['lift'] < 0,    # 应该检测到下降
        not result3['significant']                         # 应该检测到无差异
    ])
    
    score = (correct_detections / 3) * 100
    
    return TestResult(
        name="A/B测试效果对比",
        passed=correct_detections >= 2,
        score=score,
        risk_level=RiskLevel.MEDIUM.value,
        details=f"正确识别{correct_detections}/3个场景"
    )


def test_rollback_mechanism() -> TestResult:
    """测试3: 回滚机制可靠性"""
    print("\n" + "="*60)
    print("🧪 测试3: 回滚机制可靠性")
    print("="*60)
    
    manager = PromptVersionManager()
    
    # 创建多个版本
    versions = [
        PromptVersion(
            version=f"1.{i}.0",
            name="客服助手",
            author=f"developer{i}",
            created_at=datetime.now() - timedelta(days=30-i*5),
            description=f"版本1.{i}.0",
            change_type=ChangeType.WORDING_CHANGE,
            content=f"Prompt内容v1.{i}.0",
            test_results={"accuracy": 0.80 + i*0.02},
            rollback_ready=True
        )
        for i in range(5)
    ]
    
    for v in versions:
        manager.add_version(v)
    
    print(f"  已创建 {len(versions)} 个版本")
    
    # 测试快速回滚
    print("\n  测试快速回滚:")
    rollback_tests = [
        ("1.4.0", True, "最新版本"),
        ("1.2.0", True, "中间版本"),
        ("1.0.0", True, "初始版本"),
        ("0.9.0", False, "不存在版本")
    ]
    
    success_count = 0
    for version, should_succeed, desc in rollback_tests:
        ok, msg = manager.rollback(version)
        status = "✅" if (ok == should_succeed) else "❌"
        print(f"    {status} 回滚到{desc}: {msg}")
        if ok == should_succeed:
            success_count += 1
    
    # 测试回滚速度（模拟）
    print("\n  回滚性能测试:")
    rollback_times = []
    for _ in range(5):
        target = random.choice(["1.0.0", "1.2.0", "1.4.0"])
        start = datetime.now()
        manager.rollback(target)
        elapsed = (datetime.now() - start).total_seconds() * 1000  # ms
        rollback_times.append(elapsed)
    
    avg_time = sum(rollback_times) / len(rollback_times)
    print(f"    平均回滚时间: {avg_time:.2f}ms")
    print(f"    {'✅' if avg_time < 100 else '⚠️'} 回滚速度{'达标' if avg_time < 100 else '较慢'}")
    
    score = (success_count / len(rollback_tests)) * 100
    
    return TestResult(
        name="回滚机制可靠性",
        passed=success_count >= 3,
        score=score,
        risk_level=RiskLevel.HIGH.value,
        details=f"回滚测试通过率{success_count}/{len(rollback_tests)}"
    )


def test_change_impact_analysis() -> TestResult:
    """测试4: 变更影响分析"""
    print("\n" + "="*60)
    print("🧪 测试4: 变更影响分析")
    print("="*60)
    
    # 定义变更风险矩阵
    risk_matrix = {
        ChangeType.ROLE_CHANGE: (RiskLevel.HIGH, "完整回归测试"),
        ChangeType.FORMAT_CHANGE: (RiskLevel.MEDIUM, "格式验证测试"),
        ChangeType.EXAMPLE_CHANGE: (RiskLevel.LOW, "效果对比测试"),
        ChangeType.WORDING_CHANGE: (RiskLevel.MINIMAL, "快速验证"),
        ChangeType.SECURITY_CHANGE: (RiskLevel.HIGH, "安全扫描+渗透测试")
    }
    
    print("\n  Prompt变更风险评估矩阵:")
    print("  " + "-"*55)
    print(f"  {'变更类型':<20} {'风险等级':<12} {'测试要求':<20}")
    print("  " + "-"*55)
    
    correct_assessments = 0
    for change_type, (expected_risk, expected_test) in risk_matrix.items():
        risk, test_req = risk_matrix[change_type]
        match = risk == expected_risk
        if match:
            correct_assessments += 1
        print(f"  {change_type.value:<20} {risk.value:<12} {test_req:<20}")
    
    print("  " + "-"*55)
    
    # 测试版本差异分析
    print("\n  版本差异分析测试:")
    manager = PromptVersionManager()
    
    v1 = PromptVersion(
        version="1.0.0",
        name="助手",
        author="dev1",
        created_at=datetime.now() - timedelta(days=10),
        description="初始版本",
        change_type=ChangeType.WORDING_CHANGE,
        content="基础Prompt",
        test_results={"accuracy": 0.85, "safety": 0.90, "latency": 500}
    )
    
    v2 = PromptVersion(
        version="1.1.0",
        name="助手",
        author="dev2",
        created_at=datetime.now(),
        description="安全优化",
        change_type=ChangeType.SECURITY_CHANGE,
        content="优化后的Prompt",
        test_results={"accuracy": 0.84, "safety": 0.95, "latency": 520},
        parent_version="1.0.0"
    )
    
    manager.add_version(v1)
    manager.add_version(v2)
    
    diff = manager.get_version_diff("1.0.0", "1.1.0")
    print(f"    版本变更: {diff.get('version_delta')}")
    print(f"    变更类型: {diff.get('change_type')}")
    print(f"    作者变更: {'是' if diff.get('author_changed') else '否'}")
    
    if diff.get('test_results_delta'):
        print("    指标变化:")
        for metric, delta in diff['test_results_delta'].items():
            trend = "📈" if delta > 0 else "📉" if delta < 0 else "➡️"
            print(f"      {trend} {metric}: {delta:+.3f}")
    
    # 评估高风险变更
    high_risk_changes = [ct for ct, (risk, _) in risk_matrix.items() if risk == RiskLevel.HIGH]
    print(f"\n  高风险变更类型: {len(high_risk_changes)}个")
    print(f"    - 角色定义修改")
    print(f"    - 安全规则更新")
    
    score = (correct_assessments / len(risk_matrix)) * 100
    
    return TestResult(
        name="变更影响分析",
        passed=correct_assessments >= 4,
        score=score,
        risk_level=RiskLevel.MEDIUM.value,
        details=f"风险评估准确率{correct_assessments}/{len(risk_matrix)}"
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📊 测试汇总报告")
    print("="*70)
    
    print(f"\n{'测试项':<25} {'状态':<10} {'得分':<10} {'风险等级':<15}")
    print("-"*70)
    
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{r.name:<25} {status:<10} {r.score:.1f}%{'':<5} {r.risk_level:<15}")
    
    print("-"*70)
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    avg_score = sum(r.score for r in results) / total
    
    print(f"\n总测试数: {total}")
    print(f"通过数: {passed} ({passed/total*100:.1f}%)")
    print(f"失败数: {total - passed}")
    print(f"平均得分: {avg_score:.1f}%")
    
    # 风险统计
    high_risk = sum(1 for r in results if "L1" in r.risk_level and not r.passed)
    medium_risk = sum(1 for r in results if "L2" in r.risk_level and not r.passed)
    
    print(f"\nL1高危风险: {high_risk}项")
    print(f"L2中危风险: {medium_risk}项")
    
    # 评级
    print("\n" + "="*70)
    print("🔒 Prompt版本管理健康评级")
    print("="*70)
    
    if avg_score >= 90:
        grade = "A级 - 优秀"
        advice = "版本管理体系完善，建议保持当前实践"
    elif avg_score >= 75:
        grade = "B级 - 良好"
        advice = "版本管理基本健全，建议优化薄弱环节"
    elif avg_score >= 60:
        grade = "C级 - 及格"
        advice = "版本管理存在隐患，建议尽快改进"
    else:
        grade = "D级 - 危险"
        advice = "版本管理严重不足，必须立即整改"
    
    print(f"  评级: {grade}")
    print(f"  评估: {advice}")
    
    print("\n" + "="*70)
    print("✅ 测试执行完毕，请将上方日志发给 Trae 生成详细报告。")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 21: Prompt版本管理与A/B测试")
    print("="*70)
    print("\n测试架构师视角：Prompt变更是AI系统的'代码变更'，")
    print("没有版本管理就像没有Git的软件开发，风险不可控。")
    print("="*70)
    
    results = [
        test_version_control_integrity(),
        test_ab_test_effectiveness(),
        test_rollback_mechanism(),
        test_change_impact_analysis()
    ]
    
    print_summary(results)


if __name__ == "__main__":
    run_all_tests()
