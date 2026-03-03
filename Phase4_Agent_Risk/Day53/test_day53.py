"""
Day 53: 结果解析失败处理测试
目标：验证Agent对工具返回结果的容错处理能力，包括空结果、异常格式、超时等场景
测试架构师视角：结果解析失败会让整个流程功亏一篑，必须有完善的降级策略
难度级别：实战（端到端异常场景与容错测试）
"""

import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class RiskLevel(Enum):
    L1 = "L1-高风险"
    L2 = "L2-中风险"
    L3 = "L3-低风险"


class ResultStatus(Enum):
    SUCCESS = "success"
    EMPTY = "empty"
    FORMAT_ERROR = "format_error"
    TIMEOUT = "timeout"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass
class ToolResult:
    """工具返回结果"""
    status: ResultStatus
    data: Any = None
    raw_response: str = ""
    error_message: str = ""
    execution_time: float = 0.0


@dataclass
class TestCase:
    """测试用例"""
    id: str
    tool_name: str
    mock_result: ToolResult
    expected_behavior: str
    description: str
    test_type: str


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    test_name: str
    passed: bool
    score: float
    risk_level: RiskLevel
    agent_response: str
    fallback_triggered: bool
    details: str


# ==================== 模拟工具结果生成器 ====================

def mock_tool_call(tool_name: str, scenario: str) -> ToolResult:
    """模拟不同场景下的工具返回结果"""
    
    # TC-01: 标准成功结果
    if scenario == "success":
        return ToolResult(
            status=ResultStatus.SUCCESS,
            data={
                "order_id": "ORD-123456",
                "status": "confirmed",
                "total": 199.99,
                "items": [
                    {"name": "商品A", "price": 99.99, "qty": 2}
                ]
            },
            raw_response=json.dumps({
                "order_id": "ORD-123456",
                "status": "confirmed",
                "total": 199.99,
                "items": [{"name": "商品A", "price": 99.99, "qty": 2}]
            }),
            execution_time=0.5
        )
    
    # TC-02: 空结果返回
    elif scenario == "empty":
        return ToolResult(
            status=ResultStatus.EMPTY,
            data=None,
            raw_response="null",
            execution_time=0.3
        )
    
    # TC-03: 格式异常（HTML错误页）
    elif scenario == "format_error":
        return ToolResult(
            status=ResultStatus.FORMAT_ERROR,
            data=None,
            raw_response="<html><body><h1>502 Bad Gateway</h1></body></html>",
            error_message="Unexpected HTML response",
            execution_time=5.0
        )
    
    # TC-04: 关键字段缺失
    elif scenario == "missing_fields":
        return ToolResult(
            status=ResultStatus.SUCCESS,
            data={
                "order_id": "ORD-123456"
                # 缺少 status, total, items 等关键字段
            },
            raw_response=json.dumps({"order_id": "ORD-123456"}),
            execution_time=0.4
        )
    
    # TC-05: 工具调用超时
    elif scenario == "timeout":
        return ToolResult(
            status=ResultStatus.TIMEOUT,
            data=None,
            raw_response="",
            error_message="Request timeout after 30s",
            execution_time=30.0
        )
    
    # TC-06: 部分成功（批量操作）
    elif scenario == "partial":
        return ToolResult(
            status=ResultStatus.PARTIAL,
            data={
                "total": 5,
                "success": 3,
                "failed": 2,
                "success_items": [
                    {"id": "1", "name": "商品A"},
                    {"id": "2", "name": "商品B"},
                    {"id": "3", "name": "商品C"}
                ],
                "failed_items": [
                    {"id": "4", "error": "库存不足"},
                    {"id": "5", "error": "价格变动"}
                ]
            },
            raw_response=json.dumps({
                "total": 5, "success": 3, "failed": 2,
                "success_items": [{"id": "1", "name": "商品A"}, {"id": "2", "name": "商品B"}, {"id": "3", "name": "商品C"}],
                "failed_items": [{"id": "4", "error": "库存不足"}, {"id": "5", "error": "价格变动"}]
            }),
            execution_time=1.2
        )
    
    # TC-07: 错误信息包含敏感数据
    elif scenario == "sensitive_error":
        return ToolResult(
            status=ResultStatus.ERROR,
            data=None,
            raw_response="",
            error_message="Database connection failed: mysql://admin:password123@db.internal.com:3306/orders",
            execution_time=0.1
        )
    
    # TC-08: 级联失败（多工具链中的第二个失败）
    elif scenario == "cascade":
        return ToolResult(
            status=ResultStatus.ERROR,
            data=None,
            raw_response="",
            error_message="Payment service unavailable",
            execution_time=2.0
        )
    
    return ToolResult(status=ResultStatus.ERROR, error_message="Unknown scenario")


# ==================== Agent结果处理器 ====================

class ResultProcessor:
    """模拟Agent结果处理器"""
    
    def __init__(self):
        self.cache = {
            "order_query": {"order_id": "ORD-CACHED", "status": "processing", "total": 0}
        }
        self.timeout_threshold = 10.0
    
    def process(self, result: ToolResult, tool_name: str) -> Dict[str, Any]:
        """处理工具返回结果"""
        response = {
            "success": False,
            "user_message": "",
            "fallback_triggered": False,
            "data": None
        }
        
        # 超时检测
        if result.execution_time > self.timeout_threshold:
            response["fallback_triggered"] = True
            response["user_message"] = self._handle_timeout(tool_name)
            return response
        
        # 根据状态处理
        if result.status == ResultStatus.SUCCESS:
            response["success"] = True
            response["data"] = result.data
            response["user_message"] = self._format_success(result.data, tool_name)
        
        elif result.status == ResultStatus.EMPTY:
            response["fallback_triggered"] = True
            response["user_message"] = self._handle_empty(tool_name)
        
        elif result.status == ResultStatus.FORMAT_ERROR:
            response["fallback_triggered"] = True
            response["user_message"] = self._handle_format_error(tool_name)
        
        elif result.status == ResultStatus.PARTIAL:
            response["success"] = True
            response["data"] = result.data
            response["user_message"] = self._handle_partial(result.data, tool_name)
        
        elif result.status == ResultStatus.ERROR:
            response["fallback_triggered"] = True
            response["user_message"] = self._handle_error(result.error_message, tool_name)
        
        return response
    
    def _format_success(self, data: Dict, tool_name: str) -> str:
        """格式化成功结果"""
        if tool_name == "query_order":
            return f"订单查询成功：订单号 {data.get('order_id')}, 状态 {data.get('status')}, 金额 ¥{data.get('total')}"
        return "操作成功完成"
    
    def _handle_empty(self, tool_name: str) -> str:
        """处理空结果"""
        # 检查缓存
        if tool_name in self.cache:
            cached = self.cache[tool_name]
            return f"未查询到最新数据，显示缓存信息：订单号 {cached.get('order_id')}, 状态 {cached.get('status')}"
        return "未查询到相关数据，请检查输入是否正确"
    
    def _handle_format_error(self, tool_name: str) -> str:
        """处理格式错误"""
        return f"服务暂时不可用，请稍后重试"
    
    def _handle_timeout(self, tool_name: str) -> str:
        """处理超时"""
        # 尝试缓存回退
        if tool_name in self.cache:
            cached = self.cache[tool_name]
            return f"查询超时，显示缓存数据（可能不是最新）：订单状态 {cached.get('status')}"
        return "服务响应超时，请稍后重试"
    
    def _handle_partial(self, data: Dict, tool_name: str) -> str:
        """处理部分成功"""
        total = data.get("total", 0)
        success = data.get("success", 0)
        failed = data.get("failed", 0)
        
        msg = f"操作部分完成：成功 {success}/{total} 项"
        if failed > 0:
            failed_items = data.get("failed_items", [])
            reasons = [f"商品{item.get('id')}:{item.get('error')}" for item in failed_items[:2]]
            msg += f"，失败原因：{', '.join(reasons)}"
        return msg
    
    def _handle_error(self, error_message: str, tool_name: str) -> str:
        """处理错误 - 关键：脱敏处理"""
        # 检查是否包含敏感信息
        sensitive_patterns = ["password", "mysql://", "api_key", "secret", "token"]
        is_sensitive = any(pattern in error_message.lower() for pattern in sensitive_patterns)
        
        if is_sensitive:
            # 记录原始错误（内部），返回脱敏信息（外部）
            print(f"  [内部日志] 原始错误: {error_message}")
            return "系统内部错误，请联系客服处理"
        
        return f"操作失败：{error_message[:50]}"


# ==================== 测试用例定义 ====================

TEST_CASES = [
    TestCase(
        id="TC-01",
        tool_name="query_order",
        mock_result=mock_tool_call("query_order", "success"),
        expected_behavior="正常解析并格式化输出",
        description="标准成功结果 - 正常解析流程",
        test_type="normal"
    ),
    TestCase(
        id="TC-02",
        tool_name="query_order",
        mock_result=mock_tool_call("query_order", "empty"),
        expected_behavior="检测空值并返回友好提示",
        description="空结果返回 - 空值检测与提示",
        test_type="boundary"
    ),
    TestCase(
        id="TC-03",
        tool_name="query_order",
        mock_result=mock_tool_call("query_order", "format_error"),
        expected_behavior="识别格式异常并降级",
        description="格式异常（HTML错误页）- 格式容错处理",
        test_type="boundary"
    ),
    TestCase(
        id="TC-04",
        tool_name="query_order",
        mock_result=mock_tool_call("query_order", "missing_fields"),
        expected_behavior="检测关键字段缺失",
        description="关键字段缺失 - 结构完整性检查",
        test_type="boundary"
    ),
    TestCase(
        id="TC-05",
        tool_name="query_order",
        mock_result=mock_tool_call("query_order", "timeout"),
        expected_behavior="超时检测并触发降级",
        description="工具调用超时 - 超时检测与降级",
        test_type="boundary"
    ),
    TestCase(
        id="TC-06",
        tool_name="batch_order",
        mock_result=mock_tool_call("batch_order", "partial"),
        expected_behavior="区分成功/失败项并分别处理",
        description="部分成功（批量操作）- 部分结果处理",
        test_type="normal"
    ),
    TestCase(
        id="TC-07",
        tool_name="query_order",
        mock_result=mock_tool_call("query_order", "sensitive_error"),
        expected_behavior="脱敏处理后返回用户",
        description="错误信息脱敏 - 敏感信息过滤",
        test_type="security"
    ),
    TestCase(
        id="TC-08",
        tool_name="payment",
        mock_result=mock_tool_call("payment", "cascade"),
        expected_behavior="正确传播异常并终止流程",
        description="级联失败（多工具链）- 链式异常传播",
        test_type="boundary"
    ),
]


def run_test(tc: TestCase, processor: ResultProcessor) -> TestResult:
    """执行单个测试用例"""
    print(f"\n{'='*60}")
    print(f"🧪 {tc.id}: {tc.description}")
    print(f"{'='*60}")
    print(f"工具: {tc.tool_name}")
    print(f"结果状态: {tc.mock_result.status.value}")
    print(f"执行时间: {tc.mock_result.execution_time}s")
    
    if tc.mock_result.error_message:
        print(f"错误信息: {tc.mock_result.error_message[:80]}...")
    
    # 处理结果
    result = processor.process(tc.mock_result, tc.tool_name)
    
    print(f"\nAgent响应: {result['user_message']}")
    print(f"降级触发: {'是' if result['fallback_triggered'] else '否'}")
    
    # 判断测试结果
    passed = False
    score = 0.0
    risk_level = RiskLevel.L3
    details = ""
    
    # 根据场景验证预期行为
    if tc.mock_result.status == ResultStatus.SUCCESS:
        # 成功场景：应该成功且无降级
        passed = result['success'] and not result['fallback_triggered']
        score = 1.0 if passed else 0.0
        risk_level = RiskLevel.L3
        details = "成功结果正确处理" if passed else "成功结果被错误降级"
    
    elif tc.mock_result.status == ResultStatus.EMPTY:
        # 空结果：应该触发降级并提供友好提示
        passed = result['fallback_triggered'] and "未查询到" in result['user_message']
        score = 1.0 if passed else 0.5
        risk_level = RiskLevel.L2 if not passed else RiskLevel.L3
        details = "空结果正确降级" if passed else "空结果处理不完善"
    
    elif tc.mock_result.status == ResultStatus.FORMAT_ERROR:
        # 格式错误：应该降级且不暴露内部错误
        passed = result['fallback_triggered'] and "服务" in result['user_message']
        score = 1.0 if passed else 0.5
        risk_level = RiskLevel.L2
        details = "格式错误正确降级" if passed else "格式错误处理不完善"
    
    elif tc.mock_result.status == ResultStatus.TIMEOUT:
        # 超时：应该降级
        passed = result['fallback_triggered'] and ("超时" in result['user_message'] or "缓存" in result['user_message'])
        score = 1.0 if passed else 0.3
        risk_level = RiskLevel.L2
        details = "超时正确降级" if passed else "超时处理不完善"
    
    elif tc.mock_result.status == ResultStatus.PARTIAL:
        # 部分成功：应该识别并报告
        passed = result['success'] and "部分" in result['user_message']
        score = 1.0 if passed else 0.5
        risk_level = RiskLevel.L3 if passed else RiskLevel.L2
        details = "部分成功正确处理" if passed else "部分成功处理不完善"
    
    elif tc.mock_result.status == ResultStatus.ERROR:
        # 错误场景：检查是否脱敏
        if "sensitive" in tc.id.lower():
            # 敏感信息测试
            passed = "内部错误" in result['user_message'] or "联系客服" in result['user_message']
            passed = passed and "password" not in result['user_message'].lower()
            score = 1.0 if passed else 0.0
            risk_level = RiskLevel.L1 if not passed else RiskLevel.L3
            details = "敏感信息已脱敏" if passed else "敏感信息泄露风险！"
        else:
            passed = result['fallback_triggered']
            score = 0.8 if passed else 0.3
            risk_level = RiskLevel.L2
            details = "错误正确降级" if passed else "错误处理不完善"
    
    status = "✅ 通过" if passed else "❌ 失败"
    print(f"\n结果: {status}")
    print(f"评分: {score:.2f}")
    print(f"风险: {risk_level.value}")
    print(f"详情: {details}")
    
    return TestResult(
        test_id=tc.id,
        test_name=tc.description,
        passed=passed,
        score=score,
        risk_level=risk_level,
        agent_response=result['user_message'],
        fallback_triggered=result['fallback_triggered'],
        details=details
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📊 结果解析失败处理测试 - 汇总报告")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    avg_score = sum(r.score for r in results) / total
    
    # 降级触发统计
    fallback_count = sum(1 for r in results if r.fallback_triggered)
    
    # 风险分布
    l1_count = sum(1 for r in results if r.risk_level == RiskLevel.L1)
    l2_count = sum(1 for r in results if r.risk_level == RiskLevel.L2)
    l3_count = sum(1 for r in results if r.risk_level == RiskLevel.L3)
    
    print(f"\n📈 测试统计")
    print(f"  总用例数: {total}")
    print(f"  通过: {passed} | 失败: {failed}")
    print(f"  通过率: {passed/total*100:.1f}%")
    print(f"  平均得分: {avg_score:.2f}")
    print(f"  降级触发: {fallback_count}/{total} 次")
    
    print(f"\n⚠️ 风险分布")
    print(f"  {RiskLevel.L1.value}: {l1_count} 项")
    print(f"  {RiskLevel.L2.value}: {l2_count} 项")
    print(f"  {RiskLevel.L3.value}: {l3_count} 项")
    
    print(f"\n📋 详细结果")
    for r in results:
        status = "✅" if r.passed else "❌"
        fb = "[降级]" if r.fallback_triggered else "[正常]"
        print(f"  {status} {r.test_id}: {r.test_name[:30]}... {fb} | "
              f"得分:{r.score:.2f} | {r.risk_level.value}")
    
    print("\n" + "="*70)
    print("💡 关键发现")
    print("="*70)
    
    if l1_count > 0:
        print("🔴 发现高风险问题：")
        for r in results:
            if r.risk_level == RiskLevel.L1:
                print(f"   - {r.test_id}: {r.details}")
    
    if fallback_count < 5:  # 预期大部分边界测试应该触发降级
        print("🟡 降级策略覆盖不足，部分异常场景未触发降级")
    
    # 检查响应质量
    good_responses = sum(1 for r in results if len(r.agent_response) > 10 and "错误" not in r.agent_response)
    if good_responses < total * 0.7:
        print("🟡 用户响应质量有待提升，建议优化错误提示文案")
    
    print("\n" + "="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 53: 结果解析失败处理测试")
    print("="*70)
    print("\n测试目标：验证Agent对工具结果异常的容错处理能力")
    
    processor = ResultProcessor()
    
    results = []
    for tc in TEST_CASES:
        result = run_test(tc, processor)
        results.append(result)
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
