"""
Day 16: CO-STAR框架应用与维度质量测试
目标：最小可用，专注风险验证，杜绝多余业务逻辑
测试架构师视角：验证CO-STAR六个维度的设计选择对输出质量的影响
"""

import json
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
from difflib import SequenceMatcher


@dataclass
class CostarDimensionTest:
    """CO-STAR维度测试用例"""
    name: str
    dimension: str  # Context/Objective/Style/Tone/Audience/Response
    prompt: str
    input_text: str
    expected_patterns: List[str]  # 期望包含的模式
    forbidden_patterns: List[str]  # 不应出现的模式
    risk_level: str  # L1/L2/L3
    success_threshold: float = 0.7


@dataclass
class TestResult:
    """测试结果"""
    name: str
    dimension: str
    passed: bool
    score: float
    details: str
    risk_level: str


# ==================== CO-STAR Prompt模板库 ====================

# 基线Prompt（完整CO-STAR）
COSTAR_BASELINE = """【Context-背景】
用户是电商平台的新手商家，经营服装类目3个月，月均销售额5万元，主要困惑是如何提升转化率。

【Objective-目标】
请分析当前经营状况，并给出3条具体可执行的改进建议。

【Style-风格】
专业但易懂，像资深电商顾问一样。

【Tone-语气】
鼓励性、建设性，避免批评。

【Audience-受众】
有基本电商概念但缺乏实战经验的初学者。

【Response-响应格式】
JSON格式：
{
    "situation_analysis": "现状分析（100字以内）",
    "recommendations": ["建议1", "建议2", "建议3"],
    "priority": "最高优先级建议的编号"
}"""

# --- Context维度变体 ---
CONTEXT_MISSING = """【Objective-目标】
请分析当前经营状况，并给出3条具体可执行的改进建议。

【Style-风格】专业但易懂
【Tone-语气】鼓励性
【Audience-受众】初学者
【Response-响应格式】JSON格式"""

CONTEXT_REDUNDANT = """【Context-背景】
用户是电商平台的新手商家，经营服装类目3个月，月均销售额5万元，主要困惑是如何提升转化率。
用户每天早上9点开店，晚上10点关店，喜欢喝咖啡，养了一只猫叫咪咪，周末喜欢去公园散步。
用户毕业于某某大学，之前做过文员工作，现在全职做电商，梦想是开自己的品牌店。

【Objective-目标】请分析当前经营状况，并给出3条具体可执行的改进建议。
【Style-风格】专业但易懂
【Tone-语气】鼓励性
【Audience-受众】初学者
【Response-响应格式】JSON格式"""

CONTEXT_MISLEADING = """【Context-背景】
用户是月销500万的服装类目大卖家，已经经营5年，团队有50人。

【Objective-目标】
请分析当前经营状况，并给出3条具体可执行的改进建议。

【Style-风格】专业但易懂
【Tone-语气】鼓励性
【Audience-受众】初学者
【Response-响应格式】JSON格式"""

# --- Objective维度变体 ---
OBJECTIVE_VAGUE = """【Context-背景】用户是电商新手商家
【Objective-目标】分析一下
【Style-风格】专业
【Tone-语气】鼓励性
【Audience-受众】初学者
【Response-响应格式】JSON格式"""

OBJECTIVE_MULTIPLE = """【Context-背景】用户是电商新手商家
【Objective-目标】
1. 分析经营状况
2. 给出改进建议
3. 预测下月销售额
4. 设计营销方案
5. 优化供应链
【Style-风格】专业
【Tone-语气】鼓励性
【Audience-受众】初学者
【Response-响应格式】JSON格式"""

OBJECTIVE_CONFLICTING = """【Context-背景】用户是电商新手商家
【Objective-目标】
请详细分析经营状况（至少500字），但回答必须简洁（50字以内）。
【Style-风格】专业
【Tone-语气】鼓励性
【Audience-受众】初学者
【Response-响应格式】JSON格式"""

# --- Style维度变体 ---
STYLE_UNDEFINED = """【Context-背景】用户是电商新手商家
【Objective-目标】分析经营状况并给出3条建议
【Tone-语气】鼓励性
【Audience-受众】初学者
【Response-响应格式】JSON格式"""

STYLE_CONFLICTING = """【Context-背景】用户是电商新手商家
【Objective-目标】分析经营状况并给出3条建议
【Style-风格】既正式又随意，既学术又通俗
【Tone-语气】鼓励性
【Audience-受众】初学者
【Response-响应格式】JSON格式"""

# --- Tone维度变体 ---
TONE_EXTREME_CASUAL = """【Context-背景】用户是电商新手商家
【Objective-目标】分析经营状况并给出3条建议
【Style-风格】专业
【Tone-语气】超级随意，像兄弟聊天一样，多用网络用语和表情
【Audience-受众】初学者
【Response-响应格式】JSON格式"""

TONE_EXTREME_FORMAL = """【Context-背景】用户是电商新手商家
【Objective-目标】分析经营状况并给出3条建议
【Style-风格】专业
【Tone-语气】极其严肃正式，像法庭宣判一样
【Audience-受众】初学者
【Response-响应格式】JSON格式"""

TONE_INAPPROPRIATE = """【Context-背景】用户是电商新手商家，经营失败，情绪低落
【Objective-目标】分析经营状况并给出3条建议
【Style-风格】专业
【Tone-语气】嘲讽、挖苦、幸灾乐祸
【Audience-受众】初学者
【Response-响应格式】JSON格式"""

# --- Audience维度变体 ---
AUDIENCE_EXPERT = """【Context-背景】用户是电商新手商家
【Objective-目标】分析经营状况并给出3条建议
【Style-风格】专业
【Tone-语气】鼓励性
【Audience-受众】电商领域资深专家，熟悉ROI、CTR、CVR、GMV等专业指标
【Response-响应格式】JSON格式"""

AUDIENCE_CHILD = """【Context-背景】用户是电商新手商家
【Objective-目标】分析经营状况并给出3条建议
【Style-风格】专业
【Tone-语气】鼓励性
【Audience-受众】10岁儿童，没有任何商业概念
【Response-响应格式】JSON格式"""

# --- Response维度变体 ---
RESPONSE_NO_CONSTRAINT = """【Context-背景】用户是电商新手商家
【Objective-目标】分析经营状况并给出3条建议
【Style-风格】专业
【Tone-语气】鼓励性
【Audience-受众】初学者"""

RESPONSE_CONFLICTING_FORMAT = """【Context-背景】用户是电商新手商家
【Objective-目标】分析经营状况并给出3条建议
【Style-风格】专业
【Tone-语气】鼓励性
【Audience-受众】初学者
【Response-响应格式】
请以JSON格式输出，但同时要包含详细的段落说明，并且用表格展示数据。"""


# ==================== 测试用例库 ====================

TEST_CASES = [
    # --- Context维度测试 ---
    CostarDimensionTest(
        name="上下文完整",
        dimension="Context",
        prompt=COSTAR_BASELINE,
        input_text="请帮我分析",
        expected_patterns=["转化率", "新手", "服装"],
        forbidden_patterns=[],
        risk_level="L3",
        success_threshold=0.8
    ),
    CostarDimensionTest(
        name="上下文缺失",
        dimension="Context",
        prompt=CONTEXT_MISSING,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=["假设", "可能", "也许"],
        risk_level="L2",
        success_threshold=0.6
    ),
    CostarDimensionTest(
        name="上下文冗余",
        dimension="Context",
        prompt=CONTEXT_REDUNDANT,
        input_text="请帮我分析",
        expected_patterns=["转化率", "销售额"],
        forbidden_patterns=["喝咖啡", "咪咪", "公园散步"],
        risk_level="L2",
        success_threshold=0.7
    ),
    CostarDimensionTest(
        name="上下文偏差",
        dimension="Context",
        prompt=CONTEXT_MISLEADING,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=["500万", "50人团队", "5年"],
        risk_level="L1",
        success_threshold=0.9
    ),
    
    # --- Objective维度测试 ---
    CostarDimensionTest(
        name="目标明确",
        dimension="Objective",
        prompt=COSTAR_BASELINE,
        input_text="请帮我分析",
        expected_patterns=["建议1", "建议2", "建议3"],
        forbidden_patterns=[],
        risk_level="L3",
        success_threshold=0.8
    ),
    CostarDimensionTest(
        name="目标模糊",
        dimension="Objective",
        prompt=OBJECTIVE_VAGUE,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=[],
        risk_level="L2",
        success_threshold=0.5
    ),
    CostarDimensionTest(
        name="多重目标",
        dimension="Objective",
        prompt=OBJECTIVE_MULTIPLE,
        input_text="请帮我分析",
        expected_patterns=["供应链", "营销方案"],
        forbidden_patterns=[],
        risk_level="L2",
        success_threshold=0.6
    ),
    CostarDimensionTest(
        name="目标冲突",
        dimension="Objective",
        prompt=OBJECTIVE_CONFLICTING,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=[],
        risk_level="L1",
        success_threshold=0.5
    ),
    
    # --- Style维度测试 ---
    CostarDimensionTest(
        name="风格明确",
        dimension="Style",
        prompt=COSTAR_BASELINE,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=[],
        risk_level="L3",
        success_threshold=0.7
    ),
    CostarDimensionTest(
        name="风格未定义",
        dimension="Style",
        prompt=STYLE_UNDEFINED,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=[],
        risk_level="L3",
        success_threshold=0.6
    ),
    CostarDimensionTest(
        name="风格冲突",
        dimension="Style",
        prompt=STYLE_CONFLICTING,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=[],
        risk_level="L2",
        success_threshold=0.5
    ),
    
    # --- Tone维度测试 ---
    CostarDimensionTest(
        name="语气适切",
        dimension="Tone",
        prompt=COSTAR_BASELINE,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=["笨蛋", "失败", "糟糕"],
        risk_level="L3",
        success_threshold=0.8
    ),
    CostarDimensionTest(
        name="语气过于随意",
        dimension="Tone",
        prompt=TONE_EXTREME_CASUAL,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=["哈哈", "😂", "老铁"],
        risk_level="L2",
        success_threshold=0.6
    ),
    CostarDimensionTest(
        name="语气不适当",
        dimension="Tone",
        prompt=TONE_INAPPROPRIATE,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=["活该", "蠢", "笑死"],
        risk_level="L1",
        success_threshold=0.9
    ),
    
    # --- Audience维度测试 ---
    CostarDimensionTest(
        name="受众适配_初学者",
        dimension="Audience",
        prompt=COSTAR_BASELINE,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=["CVR", "GMV", "ROI"],
        risk_level="L3",
        success_threshold=0.7
    ),
    CostarDimensionTest(
        name="受众错配_专家术语",
        dimension="Audience",
        prompt=AUDIENCE_EXPERT,
        input_text="请帮我分析",
        expected_patterns=["ROI", "CTR", "CVR"],
        forbidden_patterns=[],
        risk_level="L2",
        success_threshold=0.6
    ),
    CostarDimensionTest(
        name="受众错配_儿童化",
        dimension="Audience",
        prompt=AUDIENCE_CHILD,
        input_text="请帮我分析",
        expected_patterns=["就像", "游戏", "玩具"],
        forbidden_patterns=["转化率", "供应链"],
        risk_level="L2",
        success_threshold=0.5
    ),
    
    # --- Response维度测试 ---
    CostarDimensionTest(
        name="格式约束明确",
        dimension="Response",
        prompt=COSTAR_BASELINE,
        input_text="请帮我分析",
        expected_patterns=["situation_analysis", "recommendations", "priority"],
        forbidden_patterns=[],
        risk_level="L3",
        success_threshold=0.9
    ),
    CostarDimensionTest(
        name="格式无约束",
        dimension="Response",
        prompt=RESPONSE_NO_CONSTRAINT,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=[],
        risk_level="L2",
        success_threshold=0.4
    ),
    CostarDimensionTest(
        name="格式冲突",
        dimension="Response",
        prompt=RESPONSE_CONFLICTING_FORMAT,
        input_text="请帮我分析",
        expected_patterns=[],
        forbidden_patterns=[],
        risk_level="L1",
        success_threshold=0.3
    ),
]


# ==================== 模拟LLM响应生成器 ====================

def mock_llm_response(prompt: str, input_text: str) -> str:
    """
    模拟LLM响应生成
    基于Prompt特征生成合理的模拟响应
    """
    response_parts = []
    
    # 检测Context维度
    if "月均销售额5万元" in prompt and "新手商家" in prompt:
        response_parts.append("""{"situation_analysis": "作为经营3个月的新手商家，月均5万销售额表现不错，但转化率仍有提升空间", "recommendations": ["优化商品详情页图片质量", "设置新客优惠券提升首单转化", "分析竞品定价策略"], "priority": "1"}""")
    elif "Context-背景" not in prompt or prompt.find("Context-背景") > prompt.find("Objective-目标"):
        # Context缺失或顺序错误
        response_parts.append("""{"situation_analysis": "由于缺少具体背景信息，我假设您是电商新手", "recommendations": ["建议1", "建议2", "建议3"], "priority": "1"}""")
    elif "500万" in prompt and "50人" in prompt:
        # Context偏差 - 产生幻觉
        response_parts.append("""{"situation_analysis": "作为月销500万的大卖家，您应该关注规模化运营", "recommendations": ["扩大团队规模", "开拓新渠道", "优化供应链"], "priority": "1"}""")
    elif "喝咖啡" in prompt and "咪咪" in prompt:
        # Context冗余 - 可能包含无关信息
        response_parts.append("""{"situation_analysis": "经营3个月的新手商家，月均5万。顺便说，养猫可以缓解工作压力哦", "recommendations": ["建议1", "建议2", "建议3"], "priority": "1"}""")
    
    # 检测Objective维度
    if "目标】分析一下" in prompt:
        # 目标模糊
        response_parts.append("""{"situation_analysis": "电商行业竞争激烈", "recommendations": ["多学习", "多实践", "多观察"], "priority": "1"}""")
    elif "详细分析" in prompt and "简洁" in prompt:
        # 目标冲突 - 可能产生混乱输出
        response_parts.append("""分析：您的经营状况...（此处省略详细分析）总之建议：1.优化 2.推广 3.服务""")
    elif "供应链" in prompt and "营销方案" in prompt:
        # 多重目标
        response_parts.append("""{"situation_analysis": "多方面需要改进", "recommendations": ["优化供应链降低成本", "设计营销活动", "预测销售额", "分析经营状况", "其他建议"], "priority": "1"}""")
    
    # 检测Tone维度
    if "嘲讽" in prompt or "挖苦" in prompt:
        return "哈哈，5万月销还好意思问？我养猫的收入都比你高！😂 建议：1.别做了 2.找个班上 3.省省吧"
    elif "超级随意" in prompt:
        return "老铁！5万月销还行吧😂 听我说：1.整点好图 2.发优惠券 3.看看对手咋定价 冲！"
    elif "极其严肃" in prompt:
        return "经分析，汝之经营状况堪忧。兹提出三条建议：一、优化详情页；二、设置优惠；三、分析竞品。此判决不可上诉。"
    
    # 检测Audience维度
    if "10岁儿童" in prompt:
        return """{"situation_analysis": "就像你卖 lemonade 一样，有人来看但是没买", "recommendations": ["把你的摊位装饰得更漂亮", "给第一次买的人打折", "看看隔壁摊位卖多少钱"], "priority": "1"}"""
    elif "资深专家" in prompt:
        return """{"situation_analysis": "当前CVR约X%，低于行业均值，GMV增长放缓", "recommendations": ["A/B测试详情页提升CTR", "优化ROI结构", "提升CVR转化漏斗"], "priority": "1"}"""
    
    # 检测Response维度
    if "Response-响应格式" not in prompt:
        # 无格式约束
        return "根据分析，您的店铺经营3个月月销5万，建议：1.优化图片 2.设置优惠 3.分析竞品"
    elif "JSON格式" in prompt and "表格" in prompt:
        # 格式冲突
        return """分析结果：
表格：
| 项目 | 内容 |
| 现状 | 新手商家 |
| 建议 | 优化图片 |

JSON:
{"analysis": "...", "recommendations": []}"""
    
    # 默认响应
    if not response_parts:
        return """{"situation_analysis": "经营3个月月均5万，转化率有提升空间", "recommendations": ["优化商品详情页", "设置新客优惠", "分析竞品定价"], "priority": "1"}"""
    
    return response_parts[0]


# ==================== 测试执行引擎 ====================

def check_patterns(text: str, patterns: List[str]) -> Tuple[int, int]:
    """检查文本中包含/不包含指定模式的情况"""
    found = sum(1 for p in patterns if p.lower() in text.lower())
    return found, len(patterns)


def calculate_similarity(text1: str, text2: str) -> float:
    """计算两段文本的相似度"""
    return SequenceMatcher(None, text1, text2).ratio()


def validate_json_output(text: str) -> Tuple[bool, str]:
    """验证JSON输出格式"""
    try:
        # 尝试提取JSON部分
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            # 检查必要字段
            required_fields = ["situation_analysis", "recommendations", "priority"]
            missing = [f for f in required_fields if f not in data]
            if missing:
                return False, f"缺少必要字段: {missing}"
            return True, "JSON格式正确"
        return False, "未找到JSON内容"
    except json.JSONDecodeError as e:
        return False, f"JSON解析错误: {e}"


def run_dimension_test(test_case: CostarDimensionTest) -> TestResult:
    """执行单个维度测试"""
    # 生成模拟响应
    response = mock_llm_response(test_case.prompt, test_case.input_text)
    
    score = 0.0
    details = []
    
    # 检查期望模式
    if test_case.expected_patterns:
        found, total = check_patterns(response, test_case.expected_patterns)
        pattern_score = found / total if total > 0 else 1.0
        score += pattern_score * 0.4
        details.append(f"期望模式: {found}/{total}")
    else:
        score += 0.4
        details.append("期望模式: 无特定要求")
    
    # 检查禁止模式
    if test_case.forbidden_patterns:
        found, total = check_patterns(response, test_case.forbidden_patterns)
        forbidden_score = (total - found) / total if total > 0 else 1.0
        score += forbidden_score * 0.3
        details.append(f"禁止模式: 发现{found}个违规")
    else:
        score += 0.3
        details.append("禁止模式: 无限制")
    
    # Response格式特殊验证
    if test_case.dimension == "Response":
        is_valid, msg = validate_json_output(response)
        if is_valid:
            score += 0.3
        else:
            score += 0.1
        details.append(f"格式验证: {msg}")
    else:
        score += 0.3
        details.append("格式验证: 跳过")
    
    passed = score >= test_case.success_threshold
    
    return TestResult(
        name=test_case.name,
        dimension=test_case.dimension,
        passed=passed,
        score=round(score, 2),
        details=" | ".join(details),
        risk_level=test_case.risk_level
    )


def print_separator(char: str = "-", length: int = 70):
    """打印分隔线"""
    print(char * length)


def main():
    """主测试流程"""
    print("=" * 70)
    print("CO-STAR框架维度质量测试")
    print("测试架构师视角：验证六个维度的设计选择对输出质量的影响")
    print("=" * 70)
    print()
    
    results: List[TestResult] = []
    
    # 按维度分组执行测试
    dimensions = ["Context", "Objective", "Style", "Tone", "Audience", "Response"]
    
    for dim in dimensions:
        dim_tests = [t for t in TEST_CASES if t.dimension == dim]
        if not dim_tests:
            continue
        
        print_separator("=")
        print(f"【{dim}维度测试】")
        print_separator("=")
        
        for test_case in dim_tests:
            result = run_dimension_test(test_case)
            results.append(result)
            
            status = "✅ 通过" if result.passed else "❌ 失败"
            if result.risk_level == "L2" and not result.passed:
                status = "⚠️  风险"
            
            print(f"  {status} | {result.name}")
            print(f"       得分: {result.score} (阈值: {test_case.success_threshold}) | 风险: {result.risk_level}")
            print(f"       详情: {result.details}")
            print()
    
    # 汇总报告
    print_separator("=")
    print("【测试汇总报告】")
    print_separator("=")
    
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    
    l1_issues = [r for r in results if r.risk_level == "L1" and not r.passed]
    l2_issues = [r for r in results if r.risk_level == "L2" and not r.passed]
    l3_issues = [r for r in results if r.risk_level == "L3" and not r.passed]
    
    print(f"总测试数: {total}")
    print(f"通过: {passed} | 失败: {failed} | 通过率: {passed/total*100:.1f}%")
    print()
    
    print("风险分布:")
    print(f"  🔴 L1阻断性风险: {len(l1_issues)}个")
    for issue in l1_issues:
        print(f"     - {issue.name} (得分: {issue.score})")
    
    print(f"  🟡 L2高优先级风险: {len(l2_issues)}个")
    for issue in l2_issues:
        print(f"     - {issue.name} (得分: {issue.score})")
    
    print(f"  🟢 L3一般风险: {len(l3_issues)}个")
    for issue in l3_issues:
        print(f"     - {issue.name} (得分: {issue.score})")
    
    print()
    print_separator("=")
    print("【维度优化建议】")
    print_separator("=")
    
    if l1_issues:
        print("🔴 高优先级修复（阻断发布）:")
        for issue in l1_issues:
            if issue.dimension == "Context":
                print(f"   - {issue.name}: 补充准确的背景信息，避免上下文偏差")
            elif issue.dimension == "Objective":
                print(f"   - {issue.name}: 使用SMART原则明确目标，消除冲突")
            elif issue.dimension == "Tone":
                print(f"   - {issue.name}: 增加语气边界约束，添加内容安全过滤")
            elif issue.dimension == "Response":
                print(f"   - {issue.name}: 统一格式要求，使用JSON Schema约束")
    
    if l2_issues:
        print("\n🟡 中优先级优化（建议修复）:")
        for issue in l2_issues:
            if issue.dimension == "Context":
                print(f"   - {issue.name}: 精简背景信息，保留关键上下文")
            elif issue.dimension == "Objective":
                print(f"   - {issue.name}: 分解多目标，设置优先级")
            elif issue.dimension == "Style":
                print(f"   - {issue.name}: 提供参考样本，明确风格定义")
            elif issue.dimension == "Audience":
                print(f"   - {issue.name}: 校准受众定位，调整内容难度")
    
    print()
    print_separator("=")
    print("测试完成")
    print_separator("=")


if __name__ == "__main__":
    main()
