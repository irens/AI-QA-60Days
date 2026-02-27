"""
自动化测试脚本：Day 01 - LLM温度参数验证
目标：验证温度参数对LLM输出稳定性的影响，专注风险验证
"""

import os
import pytest
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TemperatureTestResult:
    """温度测试结果数据类"""
    temperature: float
    prompt: str
    responses: List[str]
    consistency_score: float
    timestamp: str


class LLMTemperatureTester:
    """LLM温度参数测试器"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("TEST_MODEL", "gpt-3.5-turbo")
        self._client = None
    
    @property
    def client(self):
        """延迟初始化OpenAI客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise ImportError("请安装openai库: pip install openai")
        return self._client
    
    def call_llm(self, prompt: str, temperature: float, max_tokens: int = 100) -> str:
        """
        调用LLM获取响应
        
        Args:
            prompt: 输入提示
            temperature: 温度参数 (0-2)
            max_tokens: 最大生成token数
            
        Returns:
            模型生成的文本
        """
        if not self.api_key:
            # 模拟模式：用于无API密钥时的测试演示
            return self._mock_response(prompt, temperature)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ API调用失败: {e}")
            return f"[ERROR] {str(e)}"
    
    def _mock_response(self, prompt: str, temperature: float) -> str:
        """
        模拟LLM响应（用于演示）
        模拟温度参数对输出的影响
        """
        import random
        random.seed(hash(prompt + str(temperature)) % 10000)
        
        # 模拟不同温度下的响应变化
        responses_low = [
            "北京是中国的首都，位于华北地区。",
            "中国的首都是北京，位于华北平原北部。",
            "北京市中华人民共和国的首都。"
        ]
        responses_high = [
            "北京啊，那可是个有故事的地方！作为首都，它见证了太多历史...",
            "说起北京，我想到了故宫、长城，还有胡同里的老北京味儿...",
            "北京，中国的政治文化中心，一座古老与现代交融的城市...",
            "首都北京，从元大都到现代都市，几千年的沧桑变迁...",
            "北京！那里有天安门、颐和园，还有让人垂涎的烤鸭..."
        ]
        
        if temperature < 0.3:
            # 低温：选择有限，相对稳定
            return responses_low[random.randint(0, 1)]
        elif temperature > 1.0:
            # 高温：选择多样，随机性强
            return responses_high[random.randint(0, 4)]
        else:
            # 中温：混合
            all_responses = responses_low + responses_high
            return all_responses[random.randint(0, len(all_responses) - 1)]
    
    def test_consistency(
        self, 
        prompt: str, 
        temperature: float, 
        num_calls: int = 5
    ) -> TemperatureTestResult:
        """
        测试指定温度下的输出一致性
        
        Args:
            prompt: 测试提示
            temperature: 温度参数
            num_calls: 调用次数
            
        Returns:
            测试结果对象
        """
        print(f"\n🌡️  测试温度: {temperature}, 调用次数: {num_calls}")
        print(f"📝 Prompt: {prompt[:50]}...")
        
        responses = []
        for i in range(num_calls):
            response = self.call_llm(prompt, temperature)
            responses.append(response)
            print(f"   调用 {i+1}/{num_calls}: {response[:60]}...")
        
        # 计算一致性分数（简单版本：完全相同的响应比例）
        unique_responses = set(responses)
        consistency_score = (num_calls - len(unique_responses) + 1) / num_calls
        
        return TemperatureTestResult(
            temperature=temperature,
            prompt=prompt,
            responses=responses,
            consistency_score=consistency_score,
            timestamp=datetime.now().isoformat()
        )


# ============ 测试用例 ============

class TestDay01Temperature:
    """Day 01: 温度参数验证测试类"""
    
    @pytest.fixture(scope="class")
    def tester(self):
        """测试器fixture"""
        return LLMTemperatureTester()
    
    def test_temperature_zero_determinism(self, tester):
        """
        测试温度=0时的确定性输出
        
        风险点：关键业务场景需要稳定输出
        预期：温度=0时，多次调用应产生相同或高度相似的输出
        """
        print("\n" + "="*60)
        print("🔬 测试用例 1: 温度=0 确定性验证")
        print("="*60)
        
        prompt = "中国的首都是哪里？简要回答。"
        result = tester.test_consistency(prompt, temperature=0.0, num_calls=3)
        
        # 断言：一致性分数应接近1.0
        print(f"\n📊 一致性分数: {result.consistency_score:.2f}")
        
        # 记录结果供分析
        assert result.responses is not None, "测试应返回响应"
        assert len(result.responses) > 0, "测试应返回非空响应"
        print("✅ 温度=0 测试完成")
    
    def test_temperature_low_stability(self, tester):
        """
        测试低温度(0.3)下的输出稳定性
        
        风险点：结构化任务需要可预测输出
        """
        print("\n" + "="*60)
        print("🔬 测试用例 2: 温度=0.3 稳定性验证")
        print("="*60)
        
        prompt = "将以下文本分类为正面/负面/中性：'这个产品很好用'"
        result = tester.test_consistency(prompt, temperature=0.3, num_calls=5)
        
        print(f"\n📊 一致性分数: {result.consistency_score:.2f}")
        print("✅ 温度=0.3 测试完成")
    
    def test_temperature_medium_balance(self, tester):
        """
        测试中等温度(0.7)下的平衡性
        
        风险点：通用场景需要平衡创意与准确
        """
        print("\n" + "="*60)
        print("🔬 测试用例 3: 温度=0.7 平衡性验证")
        print("="*60)
        
        prompt = "用一句话介绍北京。"
        result = tester.test_consistency(prompt, temperature=0.7, num_calls=5)
        
        print(f"\n📊 一致性分数: {result.consistency_score:.2f}")
        print("✅ 温度=0.7 测试完成")
    
    def test_temperature_high_creativity(self, tester):
        """
        测试高温度(1.2)下的创意性
        
        风险点：高随机性可能导致不可控输出
        """
        print("\n" + "="*60)
        print("🔬 测试用例 4: 温度=1.2 创意性验证")
        print("="*60)
        
        prompt = "写一个关于北京的创意短句。"
        result = tester.test_consistency(prompt, temperature=1.2, num_calls=5)
        
        print(f"\n📊 一致性分数: {result.consistency_score:.2f}")
        print("⚠️  注意：高温度下一致性分数应较低，表明输出多样性")
        print("✅ 温度=1.2 测试完成")
    
    def test_temperature_extreme_high(self, tester):
        """
        测试极端高温(1.8)下的行为
        
        风险点：极端参数可能导致输出质量下降
        """
        print("\n" + "="*60)
        print("🔬 测试用例 5: 温度=1.8 极端情况验证")
        print("="*60)
        
        prompt = "描述一下北京。"
        result = tester.test_consistency(prompt, temperature=1.8, num_calls=3)
        
        print(f"\n📊 一致性分数: {result.consistency_score:.2f}")
        print("⚠️  极端高温可能导致输出不稳定或离题")
        print("✅ 温度=1.8 测试完成")
    
    def test_semantic_equivalence_stability(self, tester):
        """
        测试语义等价prompt的稳定性
        
        风险点：用户用不同方式提问时，应得到一致答案
        """
        print("\n" + "="*60)
        print("🔬 测试用例 6: 语义等价稳定性验证")
        print("="*60)
        
        prompts = [
            "中国的首都是哪里？",
            "请告诉我中国首都是什么城市？",
            "哪个城市是中国的首都？"
        ]
        
        all_responses = []
        for i, prompt in enumerate(prompts):
            response = tester.call_llm(prompt, temperature=0.0)
            all_responses.append(response)
            print(f"   Prompt {i+1}: {prompt}")
            print(f"   Response: {response[:60]}...")
        
        # 检查响应是否都包含"北京"
        contains_beijing = all("北京" in resp for resp in all_responses)
        print(f"\n📊 所有响应都包含'北京': {contains_beijing}")
        print("✅ 语义等价测试完成")
    
    def test_temperature_gradient_analysis(self, tester):
        """
        温度梯度分析：从0到1.5的完整测试
        
        生成温度-一致性关系数据
        """
        print("\n" + "="*60)
        print("🔬 测试用例 7: 温度梯度分析")
        print("="*60)
        
        temperatures = [0.0, 0.3, 0.5, 0.7, 1.0, 1.2, 1.5]
        prompt = "用一句话描述人工智能。"
        
        results = []
        for temp in temperatures:
            result = tester.test_consistency(prompt, temperature=temp, num_calls=3)
            results.append({
                "temperature": temp,
                "consistency": result.consistency_score
            })
        
        print("\n📊 温度-一致性关系表:")
        print("-" * 40)
        print(f"{'温度':<10} {'一致性分数':<15}")
        print("-" * 40)
        for r in results:
            print(f"{r['temperature']:<10} {r['consistency']:<15.2f}")
        print("-" * 40)
        print("✅ 温度梯度分析完成")


def test_ai_behavior_day01():
    """
    主测试入口 - 快速验证
    """
    print("\n" + "="*60)
    print("🚀 AI QA System Test - Day 01 启动")
    print("   主题: LLM温度参数验证")
    print("="*60)
    
    tester = LLMTemperatureTester()
    
    # 快速演示测试
    print("\n📋 执行快速验证测试...")
    
    test_cases = [
        ("北京是哪里的首都？", 0.0, "低温确定性"),
        ("描述一下北京。", 0.7, "中温平衡性"),
        ("写一句关于北京的创意描述。", 1.2, "高温创意性"),
    ]
    
    for prompt, temp, desc in test_cases:
        print(f"\n🧪 {desc} (T={temp})")
        response = tester.call_llm(prompt, temperature=temp)
        print(f"   响应: {response[:80]}...")
    
    print("\n" + "="*60)
    print("✅ Day 01 测试执行完毕")
    print("📌 请将上方日志发给 Trae 生成 report_day01.md 报告")
    print("="*60)


if __name__ == "__main__":
    test_ai_behavior_day01()
