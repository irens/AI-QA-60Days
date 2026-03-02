"""
Day 23: 预处理流程(上) - 文本清洗与格式标准化
目标：最小可用，专注风险验证，杜绝多余业务逻辑
测试架构师视角：未经清洗的原始文档会将噪声、格式错误和敏感信息带入RAG系统。
"""

import re
import html
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: str
    details: str = ""


class TextCleaner:
    """文本清洗器"""
    
    # 敏感信息脱敏规则
    SENSITIVE_PATTERNS = {
        "mobile": (r"1[3-9]\d{9}", lambda m: m.group()[:3] + "****" + m.group()[7:]),
        "id_card": (r"\d{17}[\dXx]", lambda m: m.group()[:6] + "********" + m.group()[14:]),
        "email": (r"[\w.-]+@[\w.-]+\.\w+", lambda m: "***@" + m.group().split("@")[1]),
        "api_key": (r"sk-[a-zA-Z0-9]{20,}", lambda m: m.group()[:7] + "****"),
    }
    
    def clean_html(self, text: str) -> str:
        """去除HTML标签"""
        # 去除script和style
        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", text, flags=re.I)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.I)
        # 去除所有HTML标签
        text = re.sub(r"<[^>]+>", "", text)
        # 解码HTML实体
        text = html.unescape(text)
        return text.strip()
    
    def clean_special_chars(self, text: str) -> str:
        """清洗特殊字符"""
        # 零宽字符
        zero_width = "\u200B\u200C\u200D\uFEFF"
        for char in zero_width:
            text = text.replace(char, "")
        # 控制字符（保留换行和制表）
        text = "".join(c for c in text if ord(c) >= 32 or c in "\n\t\r")
        return text
    
    def desensitize(self, text: str) -> Tuple[str, Dict]:
        """敏感信息脱敏"""
        found = {}
        for name, (pattern, replacer) in self.SENSITIVE_PATTERNS.items():
            matches = list(re.finditer(pattern, text))
            if matches:
                found[name] = len(matches)
                text = re.sub(pattern, replacer, text)
        return text, found
    
    def normalize_format(self, text: str) -> str:
        """格式标准化"""
        # 统一换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # 英文标点转中文（可选）
        punct_map = {",": "，", ".": "。", "!": "！", "?": "？", ":": "：", ";": "；"}
        for en, cn in punct_map.items():
            text = text.replace(en, cn)
        # 压缩多余空格
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n\n+", "\n\n", text)
        return text.strip()
    
    def clean(self, text: str) -> Tuple[str, Dict]:
        """完整清洗流程"""
        stats = {"original_length": len(text)}
        
        # HTML清洗
        text = self.clean_html(text)
        stats["after_html"] = len(text)
        
        # 特殊字符清洗
        text = self.clean_special_chars(text)
        stats["after_special"] = len(text)
        
        # 敏感信息脱敏
        text, sensitive = self.desensitize(text)
        stats["sensitive_found"] = sensitive
        
        # 格式标准化
        text = self.normalize_format(text)
        stats["final_length"] = len(text)
        stats["retention_rate"] = stats["final_length"] / max(stats["original_length"], 1)
        
        return text, stats


def test_html_cleaning() -> TestResult:
    """测试1: HTML清洗"""
    print("\n" + "="*60)
    print("🧪 测试1: HTML清洗")
    print("="*60)
    
    cleaner = TextCleaner()
    
    test_cases = [
        ("<p>Hello World</p>", "Hello World"),
        ("<div><span>文本</span></div>", "文本"),
        ("<script>alert(1)</script>内容", "内容"),
        ("&lt;div&gt;HTML实体&lt;/div&gt;", "<div>HTML实体</div>"),
    ]
    
    passed = 0
    print("\n  HTML清洗测试:")
    for input_text, expected in test_cases:
        result = cleaner.clean_html(input_text)
        ok = result == expected
        passed += int(ok)
        status = "✅" if ok else "❌"
        print(f"    {status} 输入: {input_text[:30]:<30} → 输出: {result[:20]}")
    
    score = (passed / len(test_cases)) * 100
    return TestResult(
        name="HTML清洗",
        passed=passed >= 3,
        score=score,
        risk_level="L2-中危",
        details=f"通过 {passed}/{len(test_cases)}"
    )


def test_special_chars_cleaning() -> TestResult:
    """测试2: 特殊字符清洗"""
    print("\n" + "="*60)
    print("🧪 测试2: 特殊字符清洗")
    print("="*60)
    
    cleaner = TextCleaner()
    
    # 包含零宽字符的文本
    text_with_zwc = "Hello\u200BWorld\u200C测试\uFEFF"
    result = cleaner.clean_special_chars(text_with_zwc)
    
    print(f"\n  零宽字符清洗:")
    print(f"    原始长度: {len(text_with_zwc)}")
    print(f"    清洗后: {result}")
    print(f"    清洗后长度: {len(result)}")
    
    # 控制字符
    text_with_control = "Hello\x00World\x01测试"
    result2 = cleaner.clean_special_chars(text_with_control)
    
    print(f"\n  控制字符清洗:")
    print(f"    原始长度: {len(text_with_control)}")
    print(f"    清洗后: {result2}")
    print(f"    清洗后长度: {len(result2)}")
    
    passed = len(result) == 11 and len(result2) == 11  # "HelloWorld测试" = 11字符
    
    return TestResult(
        name="特殊字符清洗",
        passed=passed,
        score=100 if passed else 50,
        risk_level="L3-低危",
        details="零宽字符和控制字符清洗"
    )


def test_desensitization() -> TestResult:
    """测试3: 敏感信息脱敏"""
    print("\n" + "="*60)
    print("🧪 测试3: 敏感信息脱敏")
    print("="*60)
    
    cleaner = TextCleaner()
    
    test_cases = [
        ("联系电话：13812345678", "mobile"),
        ("身份证：110101199001011234", "id_card"),
        ("邮箱：user@example.com", "email"),
        ("API密钥：sk-abcdefghijklmnopqrst", "api_key"),
    ]
    
    print("\n  敏感信息脱敏测试:")
    found_all = {}
    for text, expected_type in test_cases:
        result, found = cleaner.desensitize(text)
        has_type = expected_type in found
        status = "✅" if has_type else "❌"
        print(f"    {status} {expected_type}: {text}")
        print(f"       → {result}")
        found_all.update(found)
    
    passed = len(found_all) >= 3
    
    return TestResult(
        name="敏感信息脱敏",
        passed=passed,
        score=(len(found_all) / 4) * 100,
        risk_level="L1-高危",
        details=f"检测到 {len(found_all)} 类敏感信息"
    )


def test_format_normalization() -> TestResult:
    """测试4: 格式标准化"""
    print("\n" + "="*60)
    print("🧪 测试4: 格式标准化")
    print("="*60)
    
    cleaner = TextCleaner()
    
    text = "Hello   World\r\n\n\n测试内容..."
    result = cleaner.normalize_format(text)
    
    print(f"\n  格式标准化测试:")
    print(f"    原始: {repr(text)}")
    print(f"    结果: {repr(result)}")
    
    # 检查：多余空格被压缩、换行统一
    passed = "   " not in result and "\r" not in result
    
    return TestResult(
        name="格式标准化",
        passed=passed,
        score=100 if passed else 50,
        risk_level="L3-低危",
        details="空格压缩和换行统一"
    )


def test_full_cleaning_pipeline() -> TestResult:
    """测试5: 完整清洗流水线"""
    print("\n" + "="*60)
    print("🧪 测试5: 完整清洗流水线")
    print("="*60)
    
    cleaner = TextCleaner()
    
    # 复杂的脏数据
    dirty_text = """<div class="content">
        <script>var x=1;</script>
        <p>联系电话：13812345678，邮箱：test@example.com</p>
        <p>API密钥：sk-abcdefghijklmnopqrstuvwxyz</p>
    </div>"""
    
    result, stats = cleaner.clean(dirty_text)
    
    print("\n  完整清洗流水线测试:")
    print(f"    原始长度: {stats['original_length']}")
    print(f"    HTML清洗后: {stats['after_html']}")
    print(f"    特殊字符清洗后: {stats['after_special']}")
    print(f"    最终长度: {stats['final_length']}")
    print(f"    信息保留率: {stats['retention_rate']:.1%}")
    print(f"\n    检测到的敏感信息: {stats['sensitive_found']}")
    print(f"\n    清洗结果预览:")
    print(f"    {result[:100]}...")
    
    # 验证：敏感信息已脱敏
    has_mobile = "13812345678" in result
    has_email = "test@example.com" in result
    has_api_key = "sk-abcdefghijklmnopqrstuvwxyz" in result
    
    passed = not has_mobile and not has_email and not has_api_key
    
    return TestResult(
        name="完整清洗流水线",
        passed=passed,
        score=100 if passed else 60,
        risk_level="L1-高危",
        details=f"信息保留率 {stats['retention_rate']:.1%}"
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
    
    high_risk = sum(1 for r in results if "L1" in r.risk_level and not r.passed)
    
    print(f"\nL1高危风险: {high_risk}项")
    
    print("\n" + "="*70)
    print("🔧 文本清洗流水线评级")
    print("="*70)
    
    if avg_score >= 85:
        grade = "A级 - 优秀"
    elif avg_score >= 70:
        grade = "B级 - 良好"
    elif avg_score >= 55:
        grade = "C级 - 及格"
    else:
        grade = "D级 - 危险"
    
    print(f"  评级: {grade}")
    
    print("\n" + "="*70)
    print("✅ 测试执行完毕，请将上方日志发给 Trae 生成详细报告。")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 23: 预处理流程(上)")
    print("="*70)
    print("\n测试架构师视角：未经清洗的原始文档会将噪声、格式错误和敏感信息带入RAG系统。")
    print("="*70)
    
    results = [
        test_html_cleaning(),
        test_special_chars_cleaning(),
        test_desensitization(),
        test_format_normalization(),
        test_full_cleaning_pipeline()
    ]
    
    print_summary(results)


if __name__ == "__main__":
    run_all_tests()
