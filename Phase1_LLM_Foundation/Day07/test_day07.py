"""
自动化测试脚本：Day 07 - 模型版本迭代与回归测试
目标：基准测试套件构建、版本对比、回归决策
风险视角：专注模型升级回归风险和版本对比盲区
"""

import os
import pytest
import json
import time
import random
import statistics
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict


class TestCategory(Enum):
    """测试用例分类"""
    CUSTOMER_SERVICE = "客服场景"
    CODE_GENERATION = "代码生成"
    CONTENT_CREATION = "文案创作"
    DATA_EXTRACTION = "数据提取"
    REASONING = "逻辑推理"


class RiskLevel(Enum):
    """风险等级"""
    CRITICAL = "🔴 CRITICAL"
    HIGH = "🟠 HIGH"
    MEDIUM = "🟡 MEDIUM"
    LOW = "🟢 LOW"
    PASS = "✅ PASS"


@dataclass
class TestCase:
    """测试用例数据类"""
    id: str
    category: TestCategory
    prompt: str
    expected_keywords: List[str]
    expected_format: Optional[str] = None
    difficulty: str = "medium"  # easy/medium/hard


@dataclass
class TestResult:
    """单个测试用例结果"""
    test_id: str
    category: TestCategory
    response: str
    latency_ms: float
    accuracy_score: float  # 0-1
    format_valid: bool
    safety_pass: bool
    timestamp: str


@dataclass
class VersionMetrics:
    """版本指标汇总"""
    version_name: str
    accuracy: float
    latency_p50: float
    latency_p95: float
    stability_score: float
    safety_score: float
    test_count: int
    pass_count: int
    timestamp: str
    
    def to_dict(self) -> Dict:
        return {
            "version_name": self.version_name,
            "accuracy": round(self.accuracy, 4),
            "latency_p50": round(self.latency_p50, 2),
            "latency_p95": round(self.latency_p95, 2),
            "stability_score": round(self.stability_score, 4),
            "safety_score": round(self.safety_score, 4),
            "test_count": self.test_count,
            "pass_count": self.pass_count,
            "pass_rate": round(self.pass_count / self.test_count, 4) if self.test_count > 0 else 0,
            "timestamp": self.timestamp
        }


@dataclass
class RegressionComparison:
    """回归对比结果"""
    metric: str
    baseline_value: float
    new_value: float
    change_percent: float
    threshold: float
    status: str  # PASS / WARNING / FAIL
    risk_level: RiskLevel


class BenchmarkSuite:
    """基准测试套件管理器"""
    
    def __init__(self, suite_name: str = "default"):
        self.suite_name = suite_name
        self.test_cases: List[TestCase] = []
        self.results: Dict[str, List[TestResult]] = defaultdict(list)
        self.suite_dir = f"./benchmark_suites/{suite_name}"
        os.makedirs(self.suite_dir, exist_ok=True)
    
    def load_golden_dataset(self) -> List[TestCase]:
        """加载黄金数据集"""
        # 模拟黄金数据集 - 覆盖5大核心场景
        test_cases = [
            # 客服场景
            TestCase("CS-001", TestCategory.CUSTOMER_SERVICE, 
                    "如何重置密码？", ["密码", "重置", "设置"]),
            TestCase("CS-002", TestCategory.CUSTOMER_SERVICE,
                    "订单什么时候发货？", ["订单", "发货", "物流"]),
            TestCase("CS-003", TestCategory.CUSTOMER_SERVICE,
                    "如何申请退款？", ["退款", "申请", "退货"]),
            
            # 代码生成
            TestCase("CODE-001", TestCategory.CODE_GENERATION,
                    "用Python写一个快速排序", ["def", "quicksort", "sort"], "python"),
            TestCase("CODE-002", TestCategory.CODE_GENERATION,
                    "写一个判断质数的函数", ["def", "prime", "return"], "python"),
            TestCase("CODE-003", TestCategory.CODE_GENERATION,
                    "用JavaScript实现防抖函数", ["function", "debounce", "setTimeout"], "javascript"),
            
            # 文案创作
            TestCase("CONTENT-001", TestCategory.CONTENT_CREATION,
                    "写一段产品推广文案，推广一款智能手表", ["智能", "手表", "功能"]),
            TestCase("CONTENT-002", TestCategory.CONTENT_CREATION,
                    "为咖啡店写一句slogan", ["咖啡", "slogan", "品牌"]),
            
            # 数据提取
            TestCase("DATA-001", TestCategory.DATA_EXTRACTION,
                    "从以下文本中提取姓名和电话：联系人：张三，电话：13800138000",
                    ["张三", "13800138000"], "json"),
            TestCase("DATA-002", TestCategory.DATA_EXTRACTION,
                    "提取日期：会议定于2024年3月15日下午2点", ["2024", "3月", "15日"]),
            
            # 逻辑推理
            TestCase("REASON-001", TestCategory.REASONING,
                    "如果所有的A都是B，所有的B都是C，那么A和C的关系是？", ["A", "C", "属于"]),
            TestCase("REASON-002", TestCategory.REASONING,
                    "三个开关控制三个灯泡，最少需要进房间几次才能确定对应关系？", ["1次", "一次", "开关"]),
        ]
        
        self.test_cases = test_cases
        print(f"✅ 加载黄金数据集: {len(test_cases)} 条测试用例")
        for cat in TestCategory:
            count = sum(1 for tc in test_cases if tc.category == cat)
            print(f"   - {cat.value}: {count}条")
        
        return test_cases
    
    def run_test(self, version_name: str, simulate_degradation: Dict = None) -> VersionMetrics:
        """
        运行基准测试
        
        Args:
            version_name: 版本名称
            simulate_degradation: 模拟退化 {"accuracy": -0.1, "latency": 1.5}
        """
        print(f"\n🧪 运行基准测试: {version_name}")
        print("-" * 50)
        
        if not self.test_cases:
            self.load_golden_dataset()
        
        simulate_degradation = simulate_degradation or {}
        results = []
        
        for tc in self.test_cases:
            # 模拟测试结果
            result = self._simulate_test_execution(tc, simulate_degradation)
            results.append(result)
        
        self.results[version_name] = results
        
        # 计算指标
        metrics = self._calculate_metrics(version_name, results)
        
        print(f"   测试完成: {metrics.pass_count}/{metrics.test_count} 通过")
        print(f"   准确率: {metrics.accuracy:.2%}")
        print(f"   P50延迟: {metrics.latency_p50:.0f}ms")
        print(f"   P95延迟: {metrics.latency_p95:.0f}ms")
        
        return metrics
    
    def _simulate_test_execution(self, test_case: TestCase, 
                                 degradation: Dict) -> TestResult:
        """模拟测试执行"""
        random.seed(hash(test_case.id) % 10000)
        
        # 基础准确率
        base_accuracy = 0.85
        category_factor = {
            TestCategory.CUSTOMER_SERVICE: 0.05,
            TestCategory.CODE_GENERATION: -0.05,
            TestCategory.CONTENT_CREATION: 0.0,
            TestCategory.DATA_EXTRACTION: 0.03,
            TestCategory.REASONING: -0.08
        }
        
        accuracy = base_accuracy + category_factor.get(test_case.category, 0)
        accuracy += random.uniform(-0.05, 0.05)  # 随机波动
        
        # 应用退化模拟
        accuracy += degradation.get("accuracy", 0)
        accuracy = max(0, min(1, accuracy))
        
        # 模拟延迟
        base_latency = 500  # ms
        latency = base_latency + random.gauss(0, 50)
        latency *= degradation.get("latency", 1.0)
        latency = max(100, latency)
        
        # 模拟响应
        response = self._generate_mock_response(test_case)
        
        # 格式验证
        format_valid = self._check_format(response, test_case.expected_format)
        
        # 安全检查
        safety_pass = random.random() > 0.05  # 95%通过率
        
        return TestResult(
            test_id=test_case.id,
            category=test_case.category,
            response=response,
            latency_ms=latency,
            accuracy_score=accuracy,
            format_valid=format_valid,
            safety_pass=safety_pass,
            timestamp=datetime.now().isoformat()
        )
    
    def _generate_mock_response(self, test_case: TestCase) -> str:
        """生成模拟响应"""
        responses = {
            TestCategory.CUSTOMER_SERVICE: [
                f"关于{test_case.prompt[:10]}...，您可以按照以下步骤操作：...",
                f"您好，{test_case.prompt[:10]}...的解决方法如下：..."
            ],
            TestCategory.CODE_GENERATION: [
                f"```python\ndef solution():\n    # {test_case.prompt[:20]}\n    pass\n```",
                f"```javascript\nfunction solution() {{\n    // {test_case.prompt[:20]}\n}}\n```"
            ],
            TestCategory.CONTENT_CREATION: [
                f"为您生成的文案：{test_case.prompt[:15]}...",
                f"创意方案：{test_case.prompt[:15]}..."
            ],
            TestCategory.DATA_EXTRACTION: [
                '{"name": "张三", "phone": "13800138000"}',
                '提取结果：姓名-张三，电话-13800138000'
            ],
            TestCategory.REASONING: [
                f"推理过程：{test_case.prompt[:20]}...答案是...",
                f"分析：{test_case.prompt[:20]}...结论为..."
            ]
        }
        
        return random.choice(responses.get(test_case.category, ["默认响应"]))
    
    def _check_format(self, response: str, expected_format: Optional[str]) -> bool:
        """检查格式合规性"""
        if expected_format is None:
            return True
        
        if expected_format == "json":
            return response.strip().startswith("{") or "json" in response.lower()
        elif expected_format in ["python", "javascript"]:
            return f"```{expected_format}" in response.lower() or f"```{expected_format[:2]}" in response.lower()
        return True
    
    def _calculate_metrics(self, version_name: str, results: List[TestResult]) -> VersionMetrics:
        """计算版本指标"""
        if not results:
            raise ValueError("无测试结果")
        
        accuracies = [r.accuracy_score for r in results]
        latencies = [r.latency_ms for r in results]
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        
        return VersionMetrics(
            version_name=version_name,
            accuracy=statistics.mean(accuracies),
            latency_p50=sorted_latencies[n // 2],
            latency_p95=sorted_latencies[int(n * 0.95)],
            stability_score=1.0 - statistics.stdev(accuracies),  # 稳定性与准确率方差负相关
            safety_score=sum(1 for r in results if r.safety_pass) / len(results),
            test_count=len(results),
            pass_count=sum(1 for r in results if r.accuracy_score > 0.7 and r.safety_pass),
            timestamp=datetime.now().isoformat()
        )
    
    def save_suite(self):
        """保存测试套件"""
        filepath = os.path.join(self.suite_dir, "suite_config.json")
        data = {
            "suite_name": self.suite_name,
            "test_cases": [
                {
                    "id": tc.id,
                    "category": tc.category.value,
                    "prompt": tc.prompt,
                    "expected_keywords": tc.expected_keywords,
                    "expected_format": tc.expected_format,
                    "difficulty": tc.difficulty
                }
                for tc in self.test_cases
            ]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath


class RegressionTester:
    """回归测试器"""
    
    def __init__(self):
        # 默认回归阈值
        self.thresholds = {
            "accuracy": {"max_degradation": 0.05, "weight": 1.0},  # 准确率下降<5%
            "latency_p50": {"max_degradation": 0.20, "weight": 0.8},  # P50延迟增加<20%
            "latency_p95": {"max_degradation": 0.30, "weight": 0.8},  # P95延迟增加<30%
            "stability_score": {"max_degradation": 0.10, "weight": 0.6},  # 稳定性下降<10%
            "safety_score": {"max_degradation": 0.0, "weight": 1.0},  # 安全性不允许下降
        }
    
    def compare_versions(self, baseline: VersionMetrics, 
                        new_version: VersionMetrics) -> List[RegressionComparison]:
        """
        对比两个版本
        
        Returns:
            回归对比结果列表
        """
        print(f"\n📊 版本对比: {baseline.version_name} vs {new_version.version_name}")
        print("=" * 70)
        
        comparisons = []
        
        for metric, threshold in self.thresholds.items():
            baseline_val = getattr(baseline, metric)
            new_val = getattr(new_version, metric)
            
            # 计算变化百分比
            if metric.startswith("latency"):
                # 延迟是越小越好，增加为负向变化
                change_pct = (new_val - baseline_val) / baseline_val
                max_deg = threshold["max_degradation"]
                status = "FAIL" if change_pct > max_deg else ("WARNING" if change_pct > max_deg * 0.5 else "PASS")
            else:
                # 其他指标是越大越好，下降为负向变化
                change_pct = (new_val - baseline_val) / baseline_val if baseline_val > 0 else 0
                max_deg = -threshold["max_degradation"]
                status = "FAIL" if change_pct < max_deg else ("WARNING" if change_pct < max_deg * 0.5 else "PASS")
            
            # 风险等级
            if status == "FAIL":
                risk = RiskLevel.CRITICAL if metric in ["accuracy", "safety_score"] else RiskLevel.HIGH
            elif status == "WARNING":
                risk = RiskLevel.MEDIUM
            else:
                risk = RiskLevel.PASS
            
            comp = RegressionComparison(
                metric=metric,
                baseline_value=baseline_val,
                new_value=new_val,
                change_percent=change_pct * 100,
                threshold=threshold["max_degradation"] * 100,
                status=status,
                risk_level=risk
            )
            comparisons.append(comp)
            
            icon = "❌" if status == "FAIL" else ("⚠️" if status == "WARNING" else "✅")
            print(f"   {icon} {metric:20s}: {baseline_val:8.2f} → {new_val:8.2f} "
                  f"({change_pct*100:+6.1f}%) | {risk.value}")
        
        return comparisons
    
    def should_block_release(self, comparisons: List[RegressionComparison]) -> Tuple[bool, str]:
        """
        判断是否应阻塞发布
        
        Returns:
            (should_block, reason)
        """
        critical_failures = [c for c in comparisons 
                           if c.status == "FAIL" and c.metric in ["accuracy", "safety_score"]]
        high_failures = [c for c in comparisons 
                        if c.status == "FAIL" and c.risk_level == RiskLevel.HIGH]
        
        if critical_failures:
            reasons = ", ".join([f"{c.metric}退化{c.change_percent:.1f}%" for c in critical_failures])
            return True, f"关键指标严重退化: {reasons}"
        
        if len(high_failures) >= 2:
            return True, f"多个高优先级指标退化"
        
        return False, "通过回归测试"
    
    def generate_recommendation(self, comparisons: List[RegressionComparison],
                               baseline: VersionMetrics,
                               new_version: VersionMetrics) -> Dict:
        """生成发布建议"""
        should_block, reason = self.should_block_release(comparisons)
        
        improvements = [c for c in comparisons if c.change_percent > 0 and not c.metric.startswith("latency")]
        degradations = [c for c in comparisons if c.status in ["WARNING", "FAIL"]]
        
        recommendation = {
            "should_release": not should_block,
            "block_reason": reason if should_block else None,
            "risk_level": self._assess_overall_risk(comparisons),
            "improvements": [{"metric": c.metric, "change": f"{c.change_percent:+.1f}%"} for c in improvements],
            "degradations": [{"metric": c.metric, "change": f"{c.change_percent:+.1f}%", "severity": c.status} for c in degradations],
            "recommendation": self._generate_advice(should_block, improvements, degradations)
        }
        
        return recommendation
    
    def _assess_overall_risk(self, comparisons: List[RegressionComparison]) -> str:
        """评估整体风险等级"""
        critical_count = sum(1 for c in comparisons if c.risk_level == RiskLevel.CRITICAL)
        high_count = sum(1 for c in comparisons if c.risk_level == RiskLevel.HIGH)
        
        if critical_count > 0:
            return "CRITICAL"
        elif high_count > 0:
            return "HIGH"
        elif any(c.risk_level == RiskLevel.MEDIUM for c in comparisons):
            return "MEDIUM"
        return "LOW"
    
    def _generate_advice(self, should_block: bool, improvements: List, degradations: List) -> str:
        """生成建议文本"""
        if should_block:
            return "❌ 不建议发布：存在关键指标退化，请修复后重新测试"
        
        if not degradations:
            return "✅ 建议全量发布：所有指标正常或改善"
        
        if len(improvements) > len(degradations):
            return "⚠️ 建议灰度发布：整体改善但存在部分退化，建议小流量验证"
        
        return "⚠️ 建议观察发布：存在轻微退化，建议加强监控后发布"


class ModelVersionTester:
    """模型版本测试主类"""
    
    def __init__(self):
        self.benchmark = BenchmarkSuite("llm_regression")
        self.regression = RegressionTester()
    
    def run_full_regression_test(self):
        """运行完整回归测试"""
        print("\n" + "="*70)
        print("🚀 模型版本回归测试启动")
        print("="*70)
        
        # 1. 加载黄金数据集
        self.benchmark.load_golden_dataset()
        
        # 2. 运行基线版本测试
        baseline_metrics = self.benchmark.run_test(
            version_name="gpt-3.5-turbo-0613",
            simulate_degradation={}
        )
        
        # 3. 运行新版本测试（模拟不同退化场景）
        test_scenarios = [
            ("gpt-3.5-turbo-1106-正常", {}),
            ("gpt-3.5-turbo-1106-轻微退化", {"accuracy": -0.03, "latency": 1.1}),
            ("gpt-3.5-turbo-1106-严重退化", {"accuracy": -0.08, "latency": 1.5}),
        ]
        
        results = []
        for version_name, degradation in test_scenarios:
            new_metrics = self.benchmark.run_test(version_name, degradation)
            
            # 4. 版本对比
            comparisons = self.regression.compare_versions(baseline_metrics, new_metrics)
            
            # 5. 生成建议
            recommendation = self.regression.generate_recommendation(
                comparisons, baseline_metrics, new_metrics
            )
            
            results.append({
                "version": version_name,
                "metrics": new_metrics,
                "comparisons": comparisons,
                "recommendation": recommendation
            })
        
        # 6. 生成报告
        self._generate_report(baseline_metrics, results)
        
        return results
    
    def _generate_report(self, baseline: VersionMetrics, results: List[Dict]):
        """生成测试报告"""
        print("\n" + "="*70)
        print("📋 回归测试报告")
        print("="*70)
        
        # 基线信息
        print(f"\n【基线版本】{baseline.version_name}")
        print(f"   准确率: {baseline.accuracy:.2%}")
        print(f"   P50延迟: {baseline.latency_p50:.0f}ms")
        print(f"   P95延迟: {baseline.latency_p95:.0f}ms")
        print(f"   稳定性: {baseline.stability_score:.2%}")
        print(f"   安全性: {baseline.safety_score:.2%}")
        
        # 各版本对比结果
        print(f"\n【版本对比结果】")
        for result in results:
            rec = result["recommendation"]
            status_icon = "✅" if rec["should_release"] else "❌"
            print(f"\n   {status_icon} {result['version']}")
            print(f"      整体风险: {rec['risk_level']}")
            print(f"      建议: {rec['recommendation']}")
            
            if rec["improvements"]:
                print(f"      改善项: {', '.join([i['metric'] for i in rec['improvements']])}")
            if rec["degradations"]:
                print(f"      退化项: {', '.join([d['metric'] for d in rec['degradations']])}")
        
        # 总结
        passed = sum(1 for r in results if r["recommendation"]["should_release"])
        print(f"\n【测试总结】")
        print(f"   测试版本数: {len(results)}")
        print(f"   通过数: {passed}")
        print(f"   阻塞数: {len(results) - passed}")
        
        print("\n" + "="*70)
        print("✅ 测试执行完毕，请将上方日志发给 Trae 生成详细报告。")
        print("="*70)


# ============ pytest 测试用例 ============

class TestDay07ModelRegression:
    """Day 07: 模型版本回归测试类"""
    
    @pytest.fixture(scope="class")
    def tester(self):
        """测试器fixture"""
        return ModelVersionTester()
    
    def test_benchmark_suite_loading(self, tester):
        """
        测试基准套件加载
        
        风险点：测试用例覆盖不足导致回归盲区
        验证：黄金数据集完整加载
        """
        test_cases = tester.benchmark.load_golden_dataset()
        
        # 断言：测试用例数量充足
        assert len(test_cases) >= 10, "测试用例数量不足"
        
        # 断言：覆盖所有核心场景
        categories = set(tc.category for tc in test_cases)
        assert len(categories) >= 3, "测试场景覆盖不足"
        
        # 断言：每个用例有关键词预期
        for tc in test_cases:
            assert len(tc.expected_keywords) > 0, f"{tc.id} 无预期关键词"
        
        print(f"\n✅ 基准套件加载测试通过: {len(test_cases)}条用例")
    
    def test_baseline_execution(self, tester):
        """
        测试基线版本执行
        
        风险点：基线测试失败导致无法对比
        验证：基线版本测试成功完成
        """
        tester.benchmark.load_golden_dataset()
        metrics = tester.benchmark.run_test("baseline-test")
        
        # 断言：指标计算成功
        assert metrics.accuracy > 0, "准确率计算失败"
        assert metrics.latency_p50 > 0, "延迟计算失败"
        assert metrics.test_count > 0, "测试计数失败"
        
        # 断言：基线质量合理
        assert 0.5 < metrics.accuracy < 1.0, "准确率超出合理范围"
        assert 100 < metrics.latency_p50 < 5000, "延迟超出合理范围"
        
        print(f"\n✅ 基线执行测试通过: 准确率{metrics.accuracy:.2%}")
    
    def test_regression_comparison(self, tester):
        """
        测试回归对比功能
        
        风险点：无法正确识别版本退化
        验证：退化场景被正确标记
        """
        tester.benchmark.load_golden_dataset()
        
        # 基线版本
        baseline = tester.benchmark.run_test("baseline", {})
        
        # 退化版本
        degraded = tester.benchmark.run_test("degraded", {"accuracy": -0.1})
        
        # 对比
        comparisons = tester.regression.compare_versions(baseline, degraded)
        
        # 断言：准确率退化被检测
        accuracy_comp = next(c for c in comparisons if c.metric == "accuracy")
        assert accuracy_comp.change_percent < 0, "准确率退化未检测"
        assert accuracy_comp.status in ["WARNING", "FAIL"], "退化未标记"
        
        # 断言：阻塞判断正确
        should_block, reason = tester.regression.should_block_release(comparisons)
        assert should_block or any(c.status == "WARNING" for c in comparisons), "退化未触发告警"
        
        print(f"\n✅ 回归对比测试通过: 准确率退化{accuracy_comp.change_percent:.1f}%")
    
    def test_release_decision(self, tester):
        """
        测试发布决策逻辑
        
        风险点：错误允许退化版本发布
        验证：严重退化版本被阻塞
        """
        # 模拟严重退化对比结果
        mock_comparisons = [
            RegressionComparison("accuracy", 0.85, 0.75, -11.8, 5.0, "FAIL", RiskLevel.CRITICAL),
            RegressionComparison("latency_p50", 500, 600, 20.0, 20.0, "FAIL", RiskLevel.HIGH),
        ]
        
        should_block, reason = tester.regression.should_block_release(mock_comparisons)
        
        # 断言：严重退化应阻塞发布
        assert should_block, "严重退化未阻塞发布"
        assert "accuracy" in reason, "阻塞原因未提及关键指标"
        
        print(f"\n✅ 发布决策测试通过: 正确阻塞严重退化版本")
    
    def test_full_workflow(self, tester):
        """
        测试完整工作流程
        
        风险点：各环节集成失败
        验证：从测试到决策的完整流程
        """
        results = tester.run_full_regression_test()
        
        # 断言：所有版本测试完成
        assert len(results) > 0, "无测试结果"
        
        # 断言：每个结果有建议
        for result in results:
            assert "recommendation" in result, "无发布建议"
            assert "should_release" in result["recommendation"], "建议不完整"
        
        print("\n✅ 完整工作流程测试通过")


# 主执行入口
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 07: 模型版本迭代与回归测试")
    print("="*70)
    print("\n测试内容:")
    print("  1. 基准测试套件构建")
    print("  2. 版本对比与回归检测")
    print("  3. 发布决策建议生成")
    print("\n" + "-"*70)
    
    # 创建测试器并执行完整测试流程
    tester = ModelVersionTester()
    tester.run_full_regression_test()
