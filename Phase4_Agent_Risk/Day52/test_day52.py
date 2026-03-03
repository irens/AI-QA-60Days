"""
Day 52: 参数格式解析测试
目标：验证Agent生成的工具调用参数是否符合Schema规范，能否正确处理边界值和异常格式
测试架构师视角：参数解析错误是静默杀手，会产生错误结果但系统不会崩溃
难度级别：进阶（复杂场景与边界值测试）
"""

import json
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime


class RiskLevel(Enum):
    L1 = "L1-高风险"
    L2 = "L2-中风险"
    L3 = "L3-低风险"


@dataclass
class ParameterSchema:
    """参数Schema定义"""
    name: str
    param_type: str
    required: bool = True
    description: str = ""
    constraints: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.constraints is None:
            self.constraints = {}


@dataclass
class TestCase:
    """测试用例"""
    id: str
    user_input: str
    tool_name: str
    expected_params: Dict[str, Any]
    schema: List[ParameterSchema]
    description: str
    test_type: str  # boundary, format, security, normal


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    test_name: str
    passed: bool
    score: float
    risk_level: RiskLevel
    validation_errors: List[str]
    details: str


# ==================== Schema定义 ====================

CREATE_ORDER_SCHEMA = [
    ParameterSchema(
        name="product_id",
        param_type="string",
        required=True,
        description="商品ID，格式：PROD-8位字母数字",
        constraints={"pattern": r"^PROD-[A-Z0-9]{8}$"}
    ),
    ParameterSchema(
        name="quantity",
        param_type="integer",
        required=True,
        description="购买数量，范围1-999",
        constraints={"minimum": 1, "maximum": 999}
    ),
    ParameterSchema(
        name="price",
        param_type="number",
        required=True,
        description="单价，范围0.01-999999.99",
        constraints={"minimum": 0.01, "maximum": 999999.99}
    ),
    ParameterSchema(
        name="delivery_date",
        param_type="string",
        required=False,
        description="期望送达日期，格式：YYYY-MM-DD",
        constraints={"format": "date"}
    ),
    ParameterSchema(
        name="notes",
        param_type="string",
        required=False,
        description="订单备注，最长500字符",
        constraints={"maxLength": 500}
    ),
]

SEARCH_PRODUCT_SCHEMA = [
    ParameterSchema(
        name="keyword",
        param_type="string",
        required=False,
        description="搜索关键词",
        constraints={"maxLength": 100}
    ),
    ParameterSchema(
        name="category",
        param_type="string",
        required=False,
        description="商品分类",
        constraints={"enum": ["electronics", "clothing", "food", "books"]}
    ),
    ParameterSchema(
        name="price_range",
        param_type="object",
        required=False,
        description="价格区间",
        constraints={}
    ),
]


def mock_llm_parameter_extraction(user_input: str, tool_name: str, 
                                   schema: List[ParameterSchema]) -> Dict[str, Any]:
    """
    模拟LLM参数提取
    基于输入特征模拟不同质量的参数生成结果
    """
    params = {}
    
    # TC-01: 标准参数解析
    if tool_name == "create_order" and "iPhone" in user_input:
        params = {
            "product_id": "PROD-A1B2C3D4",
            "quantity": 2,
            "price": 8999.00,
            "delivery_date": "2024-03-15",
            "notes": "请尽快发货"
        }
    
    # TC-02: 必填参数缺失
    elif tool_name == "create_order" and "缺参数" in user_input:
        params = {
            "product_id": "PROD-A1B2C3D4",
            # 缺少 quantity 和 price
            "delivery_date": "2024-03-15"
        }
    
    # TC-03: 类型转换错误
    elif tool_name == "create_order" and "类型错误" in user_input:
        params = {
            "product_id": "PROD-A1B2C3D4",
            "quantity": "两个",  # 应该是整数
            "price": "8999元",   # 应该是数字
        }
    
    # TC-04: 数值边界溢出
    elif tool_name == "create_order" and "边界" in user_input:
        params = {
            "product_id": "PROD-A1B2C3D4",
            "quantity": 10000,      # 超出最大值999
            "price": 0.001,         # 低于最小值0.01
        }
    
    # TC-05: 日期格式多样性
    elif tool_name == "create_order" and "日期" in user_input:
        if "美式" in user_input:
            params = {
                "product_id": "PROD-A1B2C3D4",
                "quantity": 1,
                "price": 100.00,
                "delivery_date": "03/15/2024"  # MM/DD/YYYY 美式格式
            }
        elif "中式" in user_input:
            params = {
                "product_id": "PROD-A1B2C3D4",
                "quantity": 1,
                "price": 100.00,
                "delivery_date": "2024年3月15日"  # 中文格式
            }
        else:
            params = {
                "product_id": "PROD-A1B2C3D4",
                "quantity": 1,
                "price": 100.00,
                "delivery_date": "2024-03-15"  # 标准格式
            }
    
    # TC-06: 特殊字符/注入
    elif tool_name == "create_order" and "注入" in user_input:
        params = {
            "product_id": "PROD-A1B2C3D4",
            "quantity": 1,
            "price": 100.00,
            "notes": "'; DROP TABLE orders; --"  # SQL注入尝试
        }
    
    # TC-07: 字符串长度边界
    elif tool_name == "create_order" and "长备注" in user_input:
        params = {
            "product_id": "PROD-A1B2C3D4",
            "quantity": 1,
            "price": 100.00,
            "notes": "请尽快发货" * 100  # 超长字符串
        }
    
    # TC-08: 嵌套对象解析
    elif tool_name == "search_product" and "价格区间" in user_input:
        params = {
            "keyword": "手机",
            "category": "electronics",
            "price_range": {
                "min": 1000,
                "max": 5000
            }
        }
    
    # 默认情况
    else:
        params = {"product_id": "PROD-UNKNOWN"}
    
    return params


def validate_type(value: Any, expected_type: str) -> tuple[bool, str]:
    """验证类型"""
    type_mapping = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    
    if expected_type not in type_mapping:
        return True, ""
    
    expected = type_mapping[expected_type]
    if expected_type == "number":
        if not isinstance(value, expected):
            return False, f"类型错误：期望number，实际为{type(value).__name__}"
    elif expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return False, f"类型错误：期望integer，实际为{type(value).__name__}"
    else:
        if not isinstance(value, expected):
            return False, f"类型错误：期望{expected_type}，实际为{type(value).__name__}"
    
    return True, ""


def validate_constraints(value: Any, schema: ParameterSchema) -> List[str]:
    """验证约束条件"""
    errors = []
    constraints = schema.constraints or {}
    
    # pattern验证
    if "pattern" in constraints and isinstance(value, str):
        pattern = constraints["pattern"]
        if not re.match(pattern, value):
            errors.append(f"格式错误：'{value}' 不符合模式 '{pattern}'")
    
    # 数值范围验证
    if "minimum" in constraints:
        if isinstance(value, (int, float)) and value < constraints["minimum"]:
            errors.append(f"值过小：{value} < 最小值 {constraints['minimum']}")
    
    if "maximum" in constraints:
        if isinstance(value, (int, float)) and value > constraints["maximum"]:
            errors.append(f"值过大：{value} > 最大值 {constraints['maximum']}")
    
    # 字符串长度验证
    if "maxLength" in constraints and isinstance(value, str):
        if len(value) > constraints["maxLength"]:
            errors.append(f"字符串过长：{len(value)} > 最大长度 {constraints['maxLength']}")
    
    # 枚举验证
    if "enum" in constraints:
        if value not in constraints["enum"]:
            errors.append(f"非法枚举值：'{value}' 不在允许列表 {constraints['enum']} 中")
    
    # 日期格式验证
    if constraints.get("format") == "date" and isinstance(value, str):
        # 尝试多种日期格式
        date_formats = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"]
        valid = False
        for fmt in date_formats:
            try:
                datetime.strptime(value, fmt)
                valid = True
                break
            except ValueError:
                continue
        
        # 中文格式特殊处理
        if not valid:
            chinese_pattern = r"(\d{4})年(\d{1,2})月(\d{1,2})日"
            match = re.match(chinese_pattern, value)
            if match:
                valid = True
        
        if not valid:
            errors.append(f"日期格式错误：'{value}' 不是有效的日期格式")
    
    return errors


def validate_params(params: Dict[str, Any], schema: List[ParameterSchema]) -> List[str]:
    """完整参数验证"""
    errors = []
    schema_dict = {s.name: s for s in schema}
    
    # 检查必填参数
    for s in schema:
        if s.required and s.name not in params:
            errors.append(f"缺少必填参数：{s.name}")
    
    # 验证每个参数
    for name, value in params.items():
        if name not in schema_dict:
            errors.append(f"未知参数：{name}")
            continue
        
        s = schema_dict[name]
        
        # 类型验证
        type_valid, type_error = validate_type(value, s.param_type)
        if not type_valid:
            errors.append(type_error)
            continue
        
        # 约束验证
        constraint_errors = validate_constraints(value, s)
        errors.extend(constraint_errors)
    
    return errors


def check_security_risks(params: Dict[str, Any]) -> List[str]:
    """安全检查"""
    risks = []
    
    # SQL注入检测
    sql_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\s+\d+=\d+)",
        r"(\bAND\s+\d+=\d+)",
    ]
    
    # XSS检测
    xss_patterns = [
        r"(<script[^>]*>)",
        r"(javascript:)",
        r"(on\w+\s*=)",
    ]
    
    def check_value(value: Any, path: str = ""):
        if isinstance(value, str):
            # SQL注入检查
            for pattern in sql_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    risks.append(f"{path}: 疑似SQL注入风险 - '{value[:50]}...'")
                    break
            
            # XSS检查
            for pattern in xss_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    risks.append(f"{path}: 疑似XSS攻击风险 - '{value[:50]}...'")
                    break
        
        elif isinstance(value, dict):
            for k, v in value.items():
                check_value(v, f"{path}.{k}" if path else k)
    
    for key, val in params.items():
        check_value(val, key)
    
    return risks


# ==================== 测试用例定义 ====================

TEST_CASES = [
    TestCase(
        id="TC-01",
        user_input="我要买2台iPhone，单价8999元，希望3月15日送达",
        tool_name="create_order",
        expected_params={"product_id": "PROD-A1B2C3D4", "quantity": 2, "price": 8999.00},
        schema=CREATE_ORDER_SCHEMA,
        description="标准参数解析 - 所有参数正确",
        test_type="normal"
    ),
    TestCase(
        id="TC-02",
        user_input="缺参数测试：只提供商品ID",
        tool_name="create_order",
        expected_params={"product_id": "PROD-A1B2C3D4"},
        schema=CREATE_ORDER_SCHEMA,
        description="必填参数缺失 - 缺少quantity和price",
        test_type="boundary"
    ),
    TestCase(
        id="TC-03",
        user_input="类型错误测试：数量写中文",
        tool_name="create_order",
        expected_params={},
        schema=CREATE_ORDER_SCHEMA,
        description="类型转换错误 - 字符串代替数字",
        test_type="boundary"
    ),
    TestCase(
        id="TC-04",
        user_input="边界测试：数量10000，价格0.001",
        tool_name="create_order",
        expected_params={"quantity": 10000, "price": 0.001},
        schema=CREATE_ORDER_SCHEMA,
        description="数值边界溢出 - 超出允许范围",
        test_type="boundary"
    ),
    TestCase(
        id="TC-05",
        user_input="日期格式测试：美式格式03/15/2024",
        tool_name="create_order",
        expected_params={"delivery_date": "03/15/2024"},
        schema=CREATE_ORDER_SCHEMA,
        description="日期格式多样性 - 美式日期格式",
        test_type="format"
    ),
    TestCase(
        id="TC-06",
        user_input="注入测试：备注包含SQL注入",
        tool_name="create_order",
        expected_params={},
        schema=CREATE_ORDER_SCHEMA,
        description="特殊字符/注入 - SQL注入尝试",
        test_type="security"
    ),
    TestCase(
        id="TC-07",
        user_input="长备注测试：超长字符串",
        tool_name="create_order",
        expected_params={},
        schema=CREATE_ORDER_SCHEMA,
        description="字符串长度边界 - 超出最大长度限制",
        test_type="boundary"
    ),
    TestCase(
        id="TC-08",
        user_input="搜索手机，electronics分类，价格区间1000-5000",
        tool_name="search_product",
        expected_params={"keyword": "手机", "category": "electronics", "price_range": {"min": 1000, "max": 5000}},
        schema=SEARCH_PRODUCT_SCHEMA,
        description="嵌套对象解析 - 复杂参数结构",
        test_type="normal"
    ),
]


def run_test(tc: TestCase) -> TestResult:
    """执行单个测试用例"""
    print(f"\n{'='*60}")
    print(f"🧪 {tc.id}: {tc.description}")
    print(f"{'='*60}")
    print(f"用户输入: {tc.user_input}")
    print(f"目标工具: {tc.tool_name}")
    
    # 模拟LLM参数提取
    params = mock_llm_parameter_extraction(tc.user_input, tc.tool_name, tc.schema)
    print(f"\n提取参数:")
    print(json.dumps(params, indent=2, ensure_ascii=False))
    
    # 参数验证
    validation_errors = validate_params(params, tc.schema)
    
    # 安全检查
    security_risks = check_security_risks(params)
    
    # 计算得分
    total_checks = len(tc.schema)
    passed_checks = total_checks - len(validation_errors)
    base_score = passed_checks / total_checks if total_checks > 0 else 0
    
    # 根据测试类型调整评分
    if tc.test_type == "security" and security_risks:
        base_score = 0
    
    # 判断测试结果
    passed = len(validation_errors) == 0 and len(security_risks) == 0
    
    # 确定风险等级
    if security_risks:
        risk_level = RiskLevel.L1
    elif any("必填" in e for e in validation_errors):
        risk_level = RiskLevel.L2
    elif validation_errors:
        risk_level = RiskLevel.L2
    else:
        risk_level = RiskLevel.L3
    
    # 生成详情
    details = []
    if validation_errors:
        details.append(f"验证错误: {len(validation_errors)}项")
        for err in validation_errors[:3]:
            details.append(f"  - {err}")
    
    if security_risks:
        details.append(f"安全风险: {len(security_risks)}项")
        for risk in security_risks:
            details.append(f"  - {risk}")
    
    if not details:
        details.append("所有参数验证通过")
    
    status = "✅ 通过" if passed else "❌ 失败"
    print(f"\n结果: {status}")
    print(f"评分: {base_score:.2f}")
    print(f"风险: {risk_level.value}")
    print(f"详情: {'; '.join(details[:3])}")
    
    return TestResult(
        test_id=tc.id,
        test_name=tc.description,
        passed=passed,
        score=base_score,
        risk_level=risk_level,
        validation_errors=validation_errors + security_risks,
        details="; ".join(details)
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📊 参数格式解析测试 - 汇总报告")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    avg_score = sum(r.score for r in results) / total
    
    # 按类型统计
    type_stats = {}
    for tc, result in zip(TEST_CASES, results):
        t = tc.test_type
        if t not in type_stats:
            type_stats[t] = {"total": 0, "passed": 0}
        type_stats[t]["total"] += 1
        if result.passed:
            type_stats[t]["passed"] += 1
    
    # 风险分布
    l1_count = sum(1 for r in results if r.risk_level == RiskLevel.L1)
    l2_count = sum(1 for r in results if r.risk_level == RiskLevel.L2)
    l3_count = sum(1 for r in results if r.risk_level == RiskLevel.L3)
    
    print(f"\n📈 测试统计")
    print(f"  总用例数: {total}")
    print(f"  通过: {passed} | 失败: {failed}")
    print(f"  通过率: {passed/total*100:.1f}%")
    print(f"  平均得分: {avg_score:.2f}")
    
    print(f"\n📂 按类型统计")
    for t, stats in type_stats.items():
        rate = stats["passed"]/stats["total"]*100
        print(f"  {t}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")
    
    print(f"\n⚠️ 风险分布")
    print(f"  {RiskLevel.L1.value}: {l1_count} 项")
    print(f"  {RiskLevel.L2.value}: {l2_count} 项")
    print(f"  {RiskLevel.L3.value}: {l3_count} 项")
    
    print(f"\n📋 详细结果")
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"  {status} {r.test_id}: {r.test_name[:30]}... | "
              f"得分:{r.score:.2f} | {r.risk_level.value}")
    
    print("\n" + "="*70)
    print("💡 关键发现")
    print("="*70)
    
    if l1_count > 0:
        print("🔴 发现高风险安全问题：")
        for r in results:
            if r.risk_level == RiskLevel.L1:
                print(f"   - {r.test_id}: 存在安全风险")
    
    if type_stats.get("boundary", {}).get("passed", 0) < type_stats.get("boundary", {}).get("total", 1):
        print("🟡 边界值处理存在问题，建议加强参数校验")
    
    if type_stats.get("format", {}).get("passed", 0) < type_stats.get("format", {}).get("total", 1):
        print("🟡 日期/时间格式兼容性需改进")
    
    print("\n" + "="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 52: 参数格式解析测试")
    print("="*70)
    print("\n测试目标：验证Agent参数提取的准确性和安全性")
    
    results = []
    for tc in TEST_CASES:
        result = run_test(tc)
        results.append(result)
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
