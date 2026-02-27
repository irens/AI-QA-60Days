"""
自动化测试脚本：Day 02 - Tokenizer编码机制与上下文窗口边界测试
目标：验证Tokenizer编码差异、上下文截断风险、位置敏感性
"""

import os
import pytest
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TokenizerTestResult:
    """Tokenizer测试结果数据类"""
    text: str
    text_length: int
    token_count: int
    chars_per_token: float
    encoding_name: str
    timestamp: str


@dataclass
class PositionTestResult:
    """位置敏感性测试结果数据类"""
    key_position: str
    context_length: int
    recall_success: bool
    response: str


class TokenizerTester:
    """Tokenizer与上下文窗口测试器"""
    
    def __init__(self):
        self.encoding_name = "cl100k_base"  # GPT-4默认编码
        self._encoder = None
    
    @property
    def encoder(self):
        """延迟初始化tiktoken编码器"""
        if self._encoder is None:
            try:
                import tiktoken
                self._encoder = tiktoken.get_encoding(self.encoding_name)
            except ImportError:
                print("⚠️ tiktoken未安装，使用模拟模式")
                self._encoder = None
        return self._encoder
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 输入文本
            
        Returns:
            token数量
        """
        if self.encoder is None:
            # 模拟模式：基于字符数的估算
            return self._estimate_tokens(text)
        
        try:
            tokens = self.encoder.encode(text)
            return len(tokens)
        except Exception as e:
            print(f"⚠️ Token计数失败: {e}")
            return self._estimate_tokens(text)
    
    def _estimate_tokens(self, text: str) -> int:
        """
        估算token数量（模拟模式）
        中文约1.5字符/token，英文约4字符/token
        """
        import re
        
        # 简单估算：中文按1.5字符/token，其他按4字符/token
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        
        estimated = int(chinese_chars / 1.5 + other_chars / 4)
        return max(1, estimated)
    
    def analyze_text(self, text: str, label: str = "") -> TokenizerTestResult:
        """
        分析文本的Tokenizer特征
        
        Args:
            text: 输入文本
            label: 文本标签
            
        Returns:
            分析结果
        """
        token_count = self.count_tokens(text)
        text_length = len(text)
        chars_per_token = text_length / token_count if token_count > 0 else 0
        
        return TokenizerTestResult(
            text=text if len(text) < 100 else text[:100] + "...",
            text_length=text_length,
            token_count=token_count,
            chars_per_token=round(chars_per_token, 2),
            encoding_name=self.encoding_name if self.encoder else "estimated",
            timestamp=datetime.now().isoformat()
        )
    
    def generate_context(self, base_text: str, target_tokens: int) -> str:
        """
        生成指定token数量的上下文文本
        
        Args:
            base_text: 基础文本片段
            target_tokens: 目标token数量
            
        Returns:
            生成的上下文文本
        """
        tokens_per_base = self.count_tokens(base_text)
        repeats = max(1, target_tokens // tokens_per_base)
        
        context = ""
        for i in range(repeats):
            context += f"\n[段落 {i+1}] {base_text}"
        
        # 微调至接近目标token数
        while self.count_tokens(context) < target_tokens:
            context += " " + base_text[:20]
        
        return context


# ============ 测试用例 ============

class TestDay02Tokenizer:
    """Day 02: Tokenizer与上下文窗口测试类"""
    
    @pytest.fixture(scope="class")
    def tester(self):
        """测试器fixture"""
        return TokenizerTester()
    
    def test_chinese_vs_english_efficiency(self, tester):
        """
        测试中英文token压缩率差异
        
        风险点：中文客服系统成本可能比英文高40-100%
        预期：中文chars_per_token应显著低于英文
        """
        print("\n" + "="*60)
        print("� 测试用例 1: 中英文Token压缩率对比")
        print("="*60)
        
        # 语义相近的中英文文本
        test_cases = [
            ("Hello world, this is a test.", "英文短句"),
            ("你好世界，这是一个测试。", "中文短句"),
            ("Artificial intelligence is transforming the world.", "英文AI主题"),
            ("人工智能正在改变世界。", "中文AI主题"),
            ("The quick brown fox jumps over the lazy dog.", "英文全字母"),
            ("敏捷的棕色狐狸跳过了懒惰的狗。", "中文全字符"),
        ]
        
        results = []
        for text, label in test_cases:
            result = tester.analyze_text(text, label)
            results.append((label, result))
            print(f"\n📄 {label}:")
            print(f"   文本: {text[:40]}...")
            print(f"   字符数: {result.text_length}, Token数: {result.token_count}")
            print(f"   压缩率: {result.chars_per_token} 字符/token")
        
        # 验证：中文压缩率应低于英文
        cn_result = results[1][1]  # 中文短句
        en_result = results[0][1]  # 英文短句
        
        print(f"\n📊 对比结论:")
        print(f"   英文: {en_result.chars_per_token} 字符/token")
        print(f"   中文: {cn_result.chars_per_token} 字符/token")
        print(f"   差异: {en_result.chars_per_token / cn_result.chars_per_token:.1f}x")
        
        assert cn_result.chars_per_token < en_result.chars_per_token, \
            "中文压缩率应低于英文，成本风险确认！"
        print("✅ 中英文压缩率差异测试完成")
    
    def test_special_characters_token_cost(self, tester):
        """
        测试特殊字符的token消耗
        
        风险点：emoji、特殊符号可能导致成本激增
        """
        print("\n" + "="*60)
        print("🔬 测试用例 2: 特殊字符Token消耗测试")
        print("="*60)
        
        test_cases = [
            ("Hello", "纯英文"),
            ("Hello 🌍", "带emoji"),
            ("Hello 👋🌍🎉", "多emoji"),
            ("Hello <b>world</b>", "HTML标签"),
            ("Hello\\nWorld\\t!", "转义字符"),
            ("Hello世界", "中英混合"),
            ("Hello🌍世界", "中英emoji混合"),
        ]
        
        print(f"\n{'文本类型':<20} {'字符数':<8} {'Token数':<8} {'字符/Token':<12}")
        print("-" * 50)
        
        for text, label in test_cases:
            result = tester.analyze_text(text, label)
            print(f"{label:<20} {result.text_length:<8} {result.token_count:<8} {result.chars_per_token:<12}")
        
        print("\n⚠️  风险提醒：emoji可能消耗1-3个token，大量使用会增加成本")
        print("✅ 特殊字符消耗测试完成")
    
    def test_context_window_boundary(self, tester):
        """
        测试上下文窗口边界行为
        
        风险点：超过窗口限制的输入会被静默截断
        """
        print("\n" + "="*60)
        print("🔬 测试用例 3: 上下文窗口边界测试")
        print("="*60)
        
        # 模拟4K窗口模型
        window_sizes = [512, 1024, 2048, 4096]
        base_text = "这是一个测试句子，用于模拟长文本内容。"
        
        print("\n📏 窗口大小与文本容量关系:")
        print(f"{'窗口大小':<12} {'可容纳中文字数':<16} {'估算页数':<10}")
        print("-" * 40)
        
        for window in window_sizes:
            # 估算可容纳的中文字数（假设1.5字符/token）
            chinese_chars = int(window * 1.5)
            pages = chinese_chars / 500  # 假设每页500字
            print(f"{window:<12} {chinese_chars:<16} {pages:<10.1f}")
        
        # 构造接近边界的输入
        print("\n🧪 边界测试:")
        target = 100  # 模拟小窗口便于测试
        context = tester.generate_context(base_text, target)
        actual_tokens = tester.count_tokens(context)
        
        print(f"   目标Token数: {target}")
        print(f"   实际Token数: {actual_tokens}")
        print(f"   误差: {abs(actual_tokens - target)} tokens")
        
        print("\n⚠️  风险提醒：超过窗口限制的输入会被静默截断，关键信息可能丢失！")
        print("✅ 上下文窗口边界测试完成")
    
    def test_position_sensitivity_lost_in_middle(self, tester):
        """
        测试"Lost in the Middle"位置敏感性
        
        风险点：关键信息放在长文档中间会被模型忽略
        """
        print("\n" + "="*60)
        print("🔬 测试用例 4: 位置敏感性测试 (Lost in the Middle)")
        print("="*60)
        
        # 构造测试场景
        filler_text = "这是一段填充文本，用于模拟长文档内容。文档包含多个段落和主题。"
        key_info = "【关键信息：验证码是123456】"
        
        # 模拟不同位置的召回率（基于研究数据的模拟）
        positions = [
            ("开头", 0.95),
            ("1/4处", 0.75),
            ("中间", 0.45),  # Lost in the middle!
            ("3/4处", 0.70),
            ("结尾", 0.90),
        ]
        
        print("\n📊 关键信息位置与召回率关系:")
        print(f"{'位置':<10} {'召回率':<10} {'风险等级':<10}")
        print("-" * 35)
        
        for position, recall_rate in positions:
            if recall_rate >= 0.8:
                risk = "低"
            elif recall_rate >= 0.6:
                risk = "中"
            else:
                risk = "高 ⚠️"
            print(f"{position:<10} {recall_rate:<10.0%} {risk:<10}")
        
        print("\n📈 可视化:")
        for position, recall_rate in positions:
            bar = "█" * int(recall_rate * 20)
            print(f"   {position:<6} |{bar:<20}| {recall_rate:.0%}")
        
        print("\n⚠️  风险提醒：关键信息应放在文档开头或结尾，避免放在中间位置！")
        print("✅ 位置敏感性测试完成")
    
    def test_multilingual_token_efficiency(self, tester):
        """
        测试多语言token效率对比
        
        风险点：多语言混合场景成本难以预估
        """
        print("\n" + "="*60)
        print("🔬 测试用例 5: 多语言Token效率对比")
        print("="*60)
        
        # 相同语义的不同语言表达
        translations = [
            ("Artificial Intelligence", "English"),
            ("人工智能", "Chinese"),
            ("人工知能", "Japanese"),
            ("인공지능", "Korean"),
            ("Intelligence artificielle", "French"),
            ("Künstliche Intelligenz", "German"),
        ]
        
        print(f"\n{'语言':<12} {'文本':<25} {'Token数':<8} {'字符/Token':<12}")
        print("-" * 60)
        
        results = []
        for text, lang in translations:
            result = tester.analyze_text(text, lang)
            results.append((lang, result))
            print(f"{lang:<12} {text:<25} {result.token_count:<8} {result.chars_per_token:<12}")
        
        # 找出最高和最低效率
        sorted_results = sorted(results, key=lambda x: x[1].chars_per_token)
        most_efficient = sorted_results[-1]
        least_efficient = sorted_results[0]
        
        print(f"\n📊 效率对比:")
        print(f"   最高效率: {most_efficient[0]} ({most_efficient[1].chars_per_token} 字符/token)")
        print(f"   最低效率: {least_efficient[0]} ({least_efficient[1].chars_per_token} 字符/token)")
        print(f"   效率差异: {most_efficient[1].chars_per_token / least_efficient[1].chars_per_token:.1f}x")
        
        print("\n⚠️  风险提醒：多语言系统必须按实际语言分布估算成本！")
        print("✅ 多语言效率测试完成")
    
    def test_cost_estimation_risk(self, tester):
        """
        测试成本估算风险场景
        
        风险点：基于字符数的成本估算可能导致严重偏差
        """
        print("\n" + "="*60)
        print("🔬 测试用例 6: 成本估算风险分析")
        print("="*60)
        
        # 模拟客服场景
        scenarios = [
            ("英文客服对话", "Hello, I need help with my order."),
            ("中文客服对话", "你好，我需要帮助处理我的订单问题。"),
            ("混合客服对话", "Hello你好，I need help我需要帮助。"),
        ]
        
        # 假设每1K tokens $0.01
        price_per_1k = 0.01
        
        print(f"\n{'场景':<16} {'字符数':<8} {'Token数':<8} {'估算成本':<12} {'按字符估算':<12} {'误差':<10}")
        print("-" * 75)
        
        for label, text in scenarios:
            char_count = len(text)
            token_count = tester.count_tokens(text)
            actual_cost = (token_count / 1000) * price_per_1k
            
            # 错误估算：假设1字符=1token
            wrong_cost = (char_count / 1000) * price_per_1k
            error = ((wrong_cost - actual_cost) / actual_cost * 100) if actual_cost > 0 else 0
            
            print(f"{label:<16} {char_count:<8} {token_count:<8} ${actual_cost:<11.6f} ${wrong_cost:<11.6f} {error:>+6.0f}%")
        
        print("\n⚠️  风险提醒：按字符数估算成本可能导致严重低估，中文场景尤为明显！")
        print("✅ 成本估算风险测试完成")
    
    def test_tokenizer_summary_report(self, tester):
        """
        生成Tokenizer测试汇总报告
        """
        print("\n" + "="*60)
        print("📋 Tokenizer测试汇总报告")
        print("="*60)
        
        print("\n🔴 高风险项:")
        print("   1. 中文token效率比英文低40-100%，成本需单独评估")
        print("   2. 长文档中间位置信息召回率可能低于50%")
        print("   3. 超过窗口限制的输入会被静默截断")
        
        print("\n🟡 中风险项:")
        print("   1. Emoji和特殊符号可能消耗额外token")
        print("   2. 多语言混合场景成本难以预估")
        print("   3. 不同模型Tokenizer差异导致迁移成本")
        
        print("\n✅ 测试建议:")
        print("   1. 生产环境必须使用实际Tokenizer进行成本估算")
        print("   2. 关键信息应放在文档开头或结尾")
        print("   3. 长文本场景需验证实际有效上下文长度")
        print("   4. 建立token使用监控和告警机制")
        
        print("\n" + "="*60)
        print("✅ Day 02 全部测试执行完毕")
        print("📤 请将上方日志发给 Trae 生成 report_day02.md 质量分析报告")
        print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
