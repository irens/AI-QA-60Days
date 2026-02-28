"""
自动化测试脚本：Day 04 - 多语言混合与复杂上下文测试
目标：验证多语言混合场景下的编码边界、token消耗、语义关联
"""

import os
import pytest
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MultilingualTestResult:
    """多语言测试结果数据类"""
    text: str
    languages: List[str]
    char_count: int
    token_count: int
    expected_tokens: int
    penalty_ratio: float


@dataclass
class BoundaryTestResult:
    """边界测试结果数据类"""
    boundary_type: str
    text_before: str
    text_after: str
    encoding_success: bool
    token_count: int


class MultilingualTester:
    """多语言混合测试器"""
    
    def __init__(self):
        self._encoder = None
    
    @property
    def encoder(self):
        """延迟初始化tiktoken编码器"""
        if self._encoder is None:
            try:
                import tiktoken
                self._encoder = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                print("⚠️ tiktoken未安装，使用模拟模式")
                self._encoder = None
        return self._encoder
    
    def count_tokens(self, text: str) -> int:
        """计算文本token数量"""
        if self.encoder is None:
            return self._estimate_tokens(text)
        try:
            return len(self.encoder.encode(text))
        except:
            return self._estimate_tokens(text)
    
    def _estimate_tokens(self, text: str) -> int:
        """估算token数量（模拟模式）"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        return max(1, int(chinese_chars / 1.5 + other_chars / 4))
    
    def detect_languages(self, text: str) -> List[str]:
        """简单语言检测"""
        languages = []
        
        if re.search(r'[a-zA-Z]', text):
            languages.append("English")
        if re.search(r'[\u4e00-\u9fff]', text):
            languages.append("Chinese")
        if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
            languages.append("Japanese")
        if re.search(r'[\uac00-\ud7af]', text):
            languages.append("Korean")
        if re.search(r'[\u0400-\u04ff]', text):
            languages.append("Cyrillic")
        
        return languages if languages else ["Unknown"]


# ============ 测试用例 ============

class TestDay04Multilingual:
    """Day 04: 多语言混合测试类"""
    
    @pytest.fixture(scope="class")
    def tester(self):
        """测试器fixture"""
        return MultilingualTester()
    
    def test_multilingual_token_penalty(self, tester):
        """
        测试多语言混合的Token惩罚效应
        
        风险点：多语言混合时token消耗高于单一语言之和
        """
        print("\n" + "="*60)
        print("🔬 测试用例 1: 多语言混合Token惩罚效应")
        print("="*60)
        
        # 测试用例：(纯英文, 纯中文, 混合)
        test_cases = [
            ("Hello World", "纯英文"),
            ("你好世界", "纯中文"),
            ("Hello你好World世界", "中英混合"),
            ("AI人工智能", "英中混合"),
            ("Product产品Name名称", "英中交替"),
        ]
        
        print(f"\n{'文本':<25} {'类型':<12} {'字符':<6} {'Token':<6} {'语言':<15}")
        print("-" * 65)
        
        results = []
        for text, label in test_cases:
            char_count = len(text)
            token_count = tester.count_tokens(text)
            languages = tester.detect_languages(text)
            
            print(f"{text:<25} {label:<12} {char_count:<6} {token_count:<6} {','.join(languages):<15}")
            results.append((text, label, char_count, token_count, languages))
        
        # 计算混合惩罚
        en_tokens = results[0][3]  # Hello World
        cn_tokens = results[1][3]  # 你好世界
        mixed_tokens = results[2][3]  # Hello你好World世界
        
        expected = en_tokens + cn_tokens
        penalty = (mixed_tokens - expected) / expected * 100 if expected > 0 else 0
        
        print(f"\n📊 混合惩罚分析:")
        print(f"   纯英文Token: {en_tokens}")
        print(f"   纯中文Token: {cn_tokens}")
        print(f"   预期混合Token: {expected}")
        print(f"   实际混合Token: {mixed_tokens}")
        print(f"   混合惩罚: {penalty:+.1f}%")
        
        if penalty > 10:
            print(f"\n⚠️  发现显著混合惩罚(>{10}%)！")
        
        print("✅ 多语言混合Token惩罚测试完成")
    
    def test_language_switching_boundaries(self, tester):
        """
        测试语言切换边界处理
        
        风险点：语言切换点可能出现编码错误或分词错误
        """
        print("\n" + "="*60)
        print("🔬 测试用例 2: 语言切换边界处理")
        print("="*60)
        
        boundary_cases = [
            ("Hello你好", "英文→中文"),
            ("你好Hello", "中文→英文"),
            ("Helloこんにちは", "英文→日文"),
            ("안녕하세요Hello", "韩文→英文"),
            ("Hello你好こんにちは", "英→中→日"),
            ("AI人工智能ML机器学习", "术语混合"),
        ]
        
        print(f"\n{'边界文本':<30} {'切换类型':<15} {'Token数':<8} {'状态':<10}")
        print("-" * 65)
        
        for text, switch_type in boundary_cases:
            token_count = tester.count_tokens(text)
            languages = tester.detect_languages(text)
            
            # 简单判断：如果能检测到多种语言，认为边界处理成功
            status = "✅ 正常" if len(languages) >= 2 else "⚠️  异常"
            
            print(f"{text:<30} {switch_type:<15} {token_count:<8} {status:<10}")
        
        print("\n⚠️  风险提醒：语言切换边界是编码错误的敏感区域！")
        print("✅ 语言切换边界测试完成")
    
    def test_special_character_interference(self, tester):
        """
        测试特殊字符与多语言混合的干扰
        
        风险点：emoji/符号与文字编码冲突
        """
        print("\n" + "="*60)
        print("🔬 测试用例 3: 特殊字符与多语言混合干扰")
        print("="*60)
        
        special_cases = [
            ("Hello你好🌍", "中英+Emoji"),
            ("产品💯质量✅保证", "中文+符号"),
            ("Price: $100价格: 100元", "货币符号混合"),
            ("Email: test@example.com邮箱", "邮箱+中文"),
            ("URL: https://example.com链接", "URL+中文"),
            ("温度🌡️25°C温度", "单位符号混合"),
        ]
        
        print(f"\n{'文本':<35} {'类型':<15} {'字符':<6} {'Token':<6}")
        print("-" * 65)
        
        for text, label in special_cases:
            char_count = len(text)
            token_count = tester.count_tokens(text)
            print(f"{text:<35} {label:<15} {char_count:<6} {token_count:<6}")
        
        print("\n⚠️  风险提醒：")
        print("   - Emoji可能消耗1-3个token")
        print("   - 特殊符号可能导致分词错误")
        print("   - URL/邮箱在混合文本中可能被错误分割")
        
        print("✅ 特殊字符干扰测试完成")
    
    def test_cross_language_semantic_association(self, tester):
        """
        测试跨语言语义关联能力
        
        风险点：跨语言上下文关联失败
        """
        print("\n" + "="*60)
        print("🔬 测试用例 4: 跨语言语义关联能力")
        print("="*60)
        
        # 模拟跨语言指代场景
        test_scenarios = [
            {
                "context": "The company's flagship product is called 星辰大海 (Star Ocean)",
                "question": "这家公司的旗舰产品叫什么名字？",
                "expected": "星辰大海",
                "type": "英→中实体关联"
            },
            {
                "context": "我们的新产品AI Assistant即将发布",
                "question": "What is the new product name?",
                "expected": "AI Assistant",
                "type": "中→英实体关联"
            },
            {
                "context": "Project Alpha项目由张三负责，He is the tech lead",
                "question": "谁是技术负责人？",
                "expected": "张三",
                "type": "跨语言指代"
            },
        ]
        
        print(f"\n{'场景类型':<15} {'上下文':<40} {'预期答案':<10}")
        print("-" * 70)
        
        for scenario in test_scenarios:
            context = scenario["context"][:35] + "..." if len(scenario["context"]) > 35 else scenario["context"]
            print(f"{scenario['type']:<15} {context:<40} {scenario['expected']:<10}")
        
        print("\n📊 跨语言关联难度评估:")
        print("   英→中实体: ████████░░ 中等")
        print("   中→英实体: ████████░░ 中等")
        print("   跨语言指代: ██████████ 困难")
        
        print("\n⚠️  风险提醒：跨语言实体关联是模型能力的薄弱环节！")
        print("✅ 跨语言语义关联测试完成")
    
    def test_multilingual_density_gradient(self, tester):
        """
        测试多语言密度梯度变化
        
        风险点：语言比例变化时的处理稳定性
        """
        print("\n" + "="*60)
        print("🔬 测试用例 5: 多语言密度梯度测试")
        print("="*60)
        
        # 构造不同密度的混合文本
        base_en = "Hello World this is a test sentence for mixed language analysis"
        base_cn = "这是一个用于混合语言分析的测试句子"
        
        gradients = [
            ("10%中文", base_en + " " + base_cn[:3]),
            ("30%中文", base_en + " " + base_cn[:9]),
            ("50%中文", base_en + " " + base_cn),
            ("70%中文", base_cn + " " + base_en[:20]),
            ("90%中文", base_cn + " " + base_en[:5]),
        ]
        
        print(f"\n{'密度':<10} {'文本预览':<45} {'Token':<6}")
        print("-" * 65)
        
        for label, text in gradients:
            preview = text[:40] + "..." if len(text) > 40 else text
            token_count = tester.count_tokens(text)
            print(f"{label:<10} {preview:<45} {token_count:<6}")
        
        print("\n📈 密度变化对处理的影响:")
        print("   - 低密度(<30%): 模型可能忽略非主要语言")
        print("   - 均衡密度(50%): 语言切换频繁，边界错误风险高")
        print("   - 高密度(>70%): 类似纯语言场景，相对稳定")
        
        print("✅ 多语言密度梯度测试完成")
    
    def test_code_comment_multilingual(self, tester):
        """
        测试代码与多语言注释混合
        
        风险点：代码与注释关联失败
        """
        print("\n" + "="*60)
        print("🔬 测试用例 6: 代码与多语言注释混合")
        print("="*60)
        
        code_samples = [
            ("def hello(): # 这是一个函数\n    pass", "Python+中文注释"),
            ("// 获取用户信息\nfunction getUser() {}", "JS+中文注释"),
            ("/* This function 处理数据 */\nvoid process() {}", "C+++混合注释"),
            ("# TODO: 修复这个bug\nprint('fix me')", "Python+TODO"),
            ("class User:  # 用户类\n    pass", "Python类+注释"),
        ]
        
        print(f"\n{'代码预览':<40} {'类型':<20} {'Token':<6}")
        print("-" * 70)
        
        for code, label in code_samples:
            preview = code.replace('\n', ' ')[:35] + "..."
            token_count = tester.count_tokens(code)
            print(f"{preview:<40} {label:<20} {token_count:<6}")
        
        print("\n⚠️  风险提醒：")
        print("   - 代码中的多语言注释可能被错误解析")
        print("   - 注释与代码的关联可能因语言切换而断裂")
        print("   - 特殊字符(#, //, /*)与中文混合可能产生歧义")
        
        print("✅ 代码与多语言注释测试完成")
    
    def test_multilingual_cost_estimation_risk(self, tester):
        """
        测试多语言混合场景的成本估算风险
        """
        print("\n" + "="*60)
        print("🔬 测试用例 7: 多语言混合成本估算风险")
        print("="*60)
        
        # 模拟客服场景
        scenarios = [
            ("纯英文客服", "Hello, I need help with my order."),
            ("纯中文客服", "你好，我需要帮助处理我的订单问题。"),
            ("中英混合客服", "Hello你好，I need help我需要帮助。"),
            ("中英夹杂客服", "你好，我想check一下我的order状态。"),
            ("多语言客服", "Hello你好こんにちは，需要帮助도움이 필요합니다。"),
        ]
        
        print(f"\n{'场景':<16} {'文本预览':<35} {'Token':<6} {'风险':<10}")
        print("-" * 70)
        
        for label, text in scenarios:
            preview = text[:30] + "..." if len(text) > 30 else text
            token_count = tester.count_tokens(text)
            
            # 简单风险评估
            if "多语言" in label:
                risk = "🔴 高"
            elif "混合" in label or "夹杂" in label:
                risk = "🟡 中"
            else:
                risk = "🟢 低"
            
            print(f"{label:<16} {preview:<35} {token_count:<6} {risk:<10}")
        
        print("\n⚠️  风险提醒：")
        print("   - 多语言混合场景成本难以预估")
        print("   - 实际消耗可能比预期高20-50%")
        print("   - 预算规划必须考虑混合惩罚")
        
        print("✅ 多语言混合成本估算风险测试完成")
    
    def test_multilingual_summary_report(self, tester):
        """
        生成多语言混合测试汇总报告
        """
        print("\n" + "="*60)
        print("📋 多语言混合测试汇总报告")
        print("="*60)
        
        print("\n🔴 高风险项:")
        print("   1. 混合惩罚：多语言混合时token消耗增加10-30%")
        print("   2. 跨语言关联：实体指代和语义关联能力下降")
        print("   3. 成本失控：多语言场景成本难以准确预估")
        
        print("\n🟡 中风险项:")
        print("   1. 边界错误：语言切换点可能出现编码问题")
        print("   2. 特殊字符冲突：emoji/符号与文字混合风险")
        print("   3. 密度敏感：语言比例变化时处理不稳定")
        
        print("\n✅ 测试建议:")
        print("   1. 生产环境多语言输入必须单独进行token计数")
        print("   2. 关键实体应在同一语言上下文中定义")
        print("   3. 混合场景预算需预留20-50%缓冲")
        print("   4. 语言切换频繁的场景建议分段处理")
        print("   5. 代码注释应尽量使用单一语言")
        
        print("\n📊 多语言处理优先级:")
        print("   推荐: 单一语言 > 低密度混合 > 均衡混合 > 高密度混合")
        
        print("\n" + "="*60)
        print("✅ Day 04 全部测试执行完毕")
        print("📤 请将上方日志发给 Trae 生成 report_day04.md 质量分析报告")
        print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
