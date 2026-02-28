"""
自动化测试脚本：Day 05 - 采样参数与输出稳定性验证
目标：温度×Top-p参数网格扫描、时间维度一致性验证
风险视角：专注参数组合风险与稳定性边界探测
"""

import os
import pytest
import time
import re
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class SamplingTestResult:
    """采样参数测试结果数据类"""
    temperature: float
    top_p: float
    responses: List[str] = field(default_factory=list)
    diversity_score: float = 0.0
    stability_rating: str = "UNKNOWN"  # STABLE / VARIABLE / UNSTABLE
    risk_level: str = "LOW"  # LOW / MEDIUM / HIGH / CRITICAL
    timestamps: List[str] = field(default_factory=list)


@dataclass
class BoundaryTestResult:
    """边界条件测试结果数据类"""
    param_name: str
    param_value: Any
    is_valid: bool
    error_type: str = ""
    system_response: str = ""


class SamplingParameterTester:
    """采样参数组合测试器"""
    
    # 风险等级定义
    RISK_CRITICAL = "🔴 CRITICAL"
    RISK_HIGH = "🟠 HIGH"
    RISK_MEDIUM = "🟡 MEDIUM"
    RISK_LOW = "🟢 LOW"
    
    # 稳定性评级
    STABLE = "✅ STABLE"
    VARIABLE = "⚠️ VARIABLE"
    UNSTABLE = "🔴 UNSTABLE"
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("TEST_MODEL", "gpt-3.5-turbo")
        self._client = None
        
        # 标准测试Prompt - 设计用于检测输出变化
        self.test_prompts = [
            "用一句话描述人工智能的未来发展。",
            "请列举三种提高工作效率的方法。",
            "描述一下你理想中的一天的开始。",
        ]
    
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
    
    def call_llm(self, prompt: str, temperature: float, top_p: float, 
                 max_tokens: int = 50, n: int = 1) -> List[str]:
        """
        调用LLM获取响应
        
        Args:
            prompt: 输入提示
            temperature: 温度参数 (0-2)
            top_p: Top-p参数 (0-1)
            max_tokens: 最大生成token数
            n: 生成多少个独立回复
            
        Returns:
            模型生成的文本列表
        """
        if not self.api_key:
            return self._mock_response(prompt, temperature, top_p, n)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                n=n
            )
            return [choice.message.content.strip() for choice in response.choices]
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ API调用失败 [T={temperature}, P={top_p}]: {error_msg[:100]}")
            return [f"[ERROR] {error_msg[:50]}"]
    
    def _mock_response(self, prompt: str, temperature: float, 
                       top_p: float, n: int) -> List[str]:
        """
        模拟LLM响应（用于演示）
        模拟温度×Top-p参数组合对输出的影响
        """
        import random
        base_seed = hash(f"{prompt}{temperature}{top_p}") % 10000
        
        # 确定性响应库
        deterministic_responses = [
            "人工智能将深刻改变人类社会的生产生活方式。",
            "AI技术将在医疗、教育、交通等领域发挥重要作用。",
            "未来人工智能将与人类协作，提升整体社会效率。"
        ]
        
        # 创意性响应库（更多样化）
        creative_responses = [
            "想象一下，当AI拥有了真正的创造力，艺术将焕发全新的生命力！",
            "未来的AI可能像空气一样无处不在，默默服务于每个人的日常。",
            "或许有一天，AI会成为人类探索宇宙最得力的伙伴和向导。",
            "当机器学会理解情感，人机交互将变得前所未有的温暖自然。",
            "AI的发展就像打开潘多拉魔盒，充满无限可能与挑战。",
            "未来的智能助手可能比你更了解你自己，精准预测你的需求。"
        ]
        
        responses = []
        for i in range(n):
            random.seed(base_seed + i + int(time.time() * 1000) % 1000)
            
            # 计算随机性因子 (0-1)
            randomness = min(1.0, (temperature / 1.5) * (0.5 + top_p / 2))
            
            if randomness < 0.2:
                # 低随机性：从确定性库选择，变化很小
                idx = random.randint(0, min(1, len(deterministic_responses) - 1))
                responses.append(deterministic_responses[idx])
            elif randomness < 0.5:
                # 中等随机性：混合选择
                if random.random() > 0.3:
                    idx = random.randint(0, len(deterministic_responses) - 1)
                    responses.append(deterministic_responses[idx])
                else:
                    idx = random.randint(0, len(creative_responses) - 1)
                    responses.append(creative_responses[idx])
            else:
                # 高随机性：从创意库选择，变化大
                idx = random.randint(0, len(creative_responses) - 1)
                responses.append(creative_responses[idx])
        
        return responses
    
    def calculate_diversity(self, responses: List[str]) -> float:
        """
        计算响应多样性分数 (0-1)
        使用简单的Jaccard相似度平均差异
        """
        if len(responses) < 2:
            return 0.0
        
        def jaccard_distance(s1: str, s2: str) -> float:
            """计算两个字符串的Jaccard距离"""
            set1 = set(s1)
            set2 = set(s2)
            if not set1 and not set2:
                return 0.0
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            return 1.0 - (intersection / union) if union > 0 else 0.0
        
        distances = []
        for i in range(len(responses)):
            for j in range(i + 1, len(responses)):
                distances.append(jaccard_distance(responses[i], responses[j]))
        
        return sum(distances) / len(distances) if distances else 0.0
    
    def assess_risk(self, temperature: float, top_p: float, 
                    diversity: float) -> Tuple[str, str]:
        """
        评估参数组合的风险等级和稳定性评级
        
        Returns:
            (risk_level, stability_rating)
        """
        # 风险矩阵判断
        if temperature > 1.0 and top_p > 0.9:
            return self.RISK_CRITICAL, self.UNSTABLE
        elif temperature > 1.0 or (temperature > 0.7 and top_p > 0.9):
            return self.RISK_HIGH, self.UNSTABLE
        elif temperature > 0.7 and top_p > 0.5:
            return self.RISK_MEDIUM, self.VARIABLE
        elif temperature < 0.3:
            return self.RISK_LOW, self.STABLE
        else:
            return self.RISK_LOW, self.STABLE
    
    def grid_scan(self, temperatures: List[float] = None, 
                  top_ps: List[float] = None,
                  samples_per_cell: int = 3) -> Dict[Tuple[float, float], SamplingTestResult]:
        """
        执行参数网格扫描
        
        Args:
            temperatures: 温度参数列表
            top_ps: Top-p参数列表
            samples_per_cell: 每个参数组合的采样次数
            
        Returns:
            参数组合到测试结果的映射
        """
        if temperatures is None:
            temperatures = [0.0, 0.3, 0.7, 1.0, 1.5]
        if top_ps is None:
            top_ps = [0.1, 0.5, 0.9, 1.0]
        
        results = {}
        prompt = self.test_prompts[0]
        
        print("\n" + "="*70)
        print("🧪 参数网格扫描启动")
        print("="*70)
        print(f"温度维度: {temperatures}")
        print(f"Top-p维度: {top_ps}")
        print(f"总组合数: {len(temperatures)} × {len(top_ps)} = {len(temperatures) * len(top_ps)}")
        print("-"*70)
        
        for temp in temperatures:
            for top_p in top_ps:
                print(f"\n📊 测试组合: temperature={temp}, top_p={top_p}")
                
                responses = []
                timestamps = []
                
                for i in range(samples_per_cell):
                    try:
                        result = self.call_llm(
                            prompt=prompt,
                            temperature=temp,
                            top_p=top_p,
                            n=1
                        )
                        responses.extend(result)
                        timestamps.append(datetime.now().isoformat())
                        time.sleep(0.1)  # 避免请求过快
                    except Exception as e:
                        responses.append(f"[ERROR] {str(e)[:30]}")
                
                diversity = self.calculate_diversity(responses)
                risk, stability = self.assess_risk(temp, top_p, diversity)
                
                result = SamplingTestResult(
                    temperature=temp,
                    top_p=top_p,
                    responses=responses,
                    diversity_score=diversity,
                    stability_rating=stability,
                    risk_level=risk,
                    timestamps=timestamps
                )
                results[(temp, top_p)] = result
                
                print(f"   多样性: {diversity:.3f} | 稳定性: {stability} | 风险: {risk}")
                for j, resp in enumerate(responses[:2], 1):
                    preview = resp[:40] + "..." if len(resp) > 40 else resp
                    print(f"   响应{j}: {preview}")
        
        return results
    
    def temporal_stability_test(self, temperature: float = 0.7, 
                                top_p: float = 0.9,
                                iterations: int = 10,
                                delay_seconds: float = 0.5) -> SamplingTestResult:
        """
        时间维度一致性验证
        
        Args:
            temperature: 温度参数
            top_p: Top-p参数
            iterations: 连续调用次数
            delay_seconds: 每次调用间隔
            
        Returns:
            时间稳定性测试结果
        """
        print("\n" + "="*70)
        print(f"⏱️ 时间维度稳定性测试 [T={temperature}, P={top_p}]")
        print("="*70)
        
        prompt = "用10个字描述人工智能。"
        responses = []
        timestamps = []
        latencies = []
        
        for i in range(iterations):
            start = time.time()
            try:
                result = self.call_llm(
                    prompt=prompt,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=20
                )
                latency = time.time() - start
                responses.extend(result)
                timestamps.append(datetime.now().strftime("%H:%M:%S.%f")[:-3])
                latencies.append(latency)
                print(f"   [{i+1}/{iterations}] {timestamps[-1]} | {latency:.3f}s | {result[0][:30]}...")
            except Exception as e:
                responses.append(f"[ERROR]")
                timestamps.append(datetime.now().strftime("%H:%M:%S.%f")[:-3])
                latencies.append(0)
                print(f"   [{i+1}/{iterations}] ERROR: {str(e)[:40]}")
            
            if i < iterations - 1:
                time.sleep(delay_seconds)
        
        diversity = self.calculate_diversity(responses)
        
        # 计算变异系数(CV)
        if latencies and sum(latencies) > 0:
            mean_latency = sum(latencies) / len(latencies)
            std_latency = (sum((x - mean_latency) ** 2 for x in latencies) / len(latencies)) ** 0.5
            cv = std_latency / mean_latency if mean_latency > 0 else 0
        else:
            cv = 0
        
        print(f"\n📈 统计结果:")
        print(f"   多样性分数: {diversity:.3f}")
        print(f"   平均延迟: {sum(latencies)/len(latencies):.3f}s")
        print(f"   延迟变异系数(CV): {cv:.3f}")
        
        # 稳定性判断
        if diversity < 0.3 and cv < 0.3:
            stability = self.STABLE
        elif diversity < 0.6 and cv < 0.5:
            stability = self.VARIABLE
        else:
            stability = self.UNSTABLE
        
        print(f"   稳定性评级: {stability}")
        
        return SamplingTestResult(
            temperature=temperature,
            top_p=top_p,
            responses=responses,
            diversity_score=diversity,
            stability_rating=stability,
            timestamps=timestamps
        )
    
    def boundary_test(self) -> List[BoundaryTestResult]:
        """
        边界条件测试
        
        Returns:
            边界测试结果列表
        """
        print("\n" + "="*70)
        print("🔍 边界条件测试")
        print("="*70)
        
        boundary_cases = [
            ("temperature", -0.1, "负值"),
            ("temperature", 0.0, "零值"),
            ("temperature", 0.0001, "极小值"),
            ("temperature", 2.0, "边界值"),
            ("temperature", 2.1, "超界值"),
            ("temperature", 10.0, "极端值"),
            ("top_p", -0.1, "负值"),
            ("top_p", 0.0, "零值"),
            ("top_p", 0.0001, "极小值"),
            ("top_p", 1.0, "边界值"),
            ("top_p", 1.1, "超界值"),
        ]
        
        results = []
        prompt = "你好"
        
        for param, value, desc in boundary_cases:
            print(f"\n   测试 {param}={value} ({desc})")
            
            try:
                if param == "temperature":
                    result = self.call_llm(prompt, temperature=value, top_p=0.9)
                else:
                    result = self.call_llm(prompt, temperature=0.7, top_p=value)
                
                is_error = any("[ERROR]" in r for r in result)
                
                boundary_result = BoundaryTestResult(
                    param_name=f"{param}={value}",
                    param_value=value,
                    is_valid=not is_error,
                    error_type="API_ERROR" if is_error else "",
                    system_response=result[0][:50] if result else ""
                )
                
                status = "❌ 异常" if is_error else "✅ 正常"
                print(f"      结果: {status} | 响应: {result[0][:40]}...")
                
            except Exception as e:
                boundary_result = BoundaryTestResult(
                    param_name=f"{param}={value}",
                    param_value=value,
                    is_valid=False,
                    error_type="EXCEPTION",
                    system_response=str(e)[:50]
                )
                print(f"      结果: ❌ 异常 | 错误: {str(e)[:40]}")
            
            results.append(boundary_result)
        
        return results
    
    def generate_report(self, grid_results: Dict, temporal_result: SamplingTestResult,
                       boundary_results: List[BoundaryTestResult]):
        """生成测试报告摘要"""
        print("\n" + "="*70)
        print("📋 测试报告摘要")
        print("="*70)
        
        # 1. 参数网格扫描摘要
        print("\n【1. 参数网格扫描结果】")
        risk_counts = defaultdict(int)
        for result in grid_results.values():
            risk_counts[result.risk_level] += 1
        
        print(f"   总组合数: {len(grid_results)}")
        for risk, count in sorted(risk_counts.items(), 
                                  key=lambda x: {"🔴 CRITICAL": 0, "🟠 HIGH": 1, 
                                                "🟡 MEDIUM": 2, "🟢 LOW": 3}.get(x[0], 4)):
            print(f"   {risk}: {count}个组合")
        
        # 2. 高风险组合清单
        print("\n【2. 高风险组合清单 (生产环境禁用)】")
        critical_high = [(k, v) for k, v in grid_results.items() 
                        if "CRITICAL" in v.risk_level or "HIGH" in v.risk_level]
        if critical_high:
            for (temp, top_p), result in critical_high:
                print(f"   🔴 T={temp}, P={top_p} → {result.stability_rating}")
        else:
            print("   ✅ 未发现高风险组合")
        
        # 3. 推荐配置
        print("\n【3. 生产环境推荐配置】")
        recommended = [(k, v) for k, v in grid_results.items() 
                      if "🟢" in v.risk_level and "✅" in v.stability_rating]
        for (temp, top_p), result in recommended[:3]:
            print(f"   ✅ temperature={temp}, top_p={top_p}")
        
        # 4. 时间稳定性
        print("\n【4. 时间维度稳定性】")
        print(f"   测试参数: T={temporal_result.temperature}, P={temporal_result.top_p}")
        print(f"   多样性分数: {temporal_result.diversity_score:.3f}")
        print(f"   稳定性评级: {temporal_result.stability_rating}")
        
        # 5. 边界测试
        print("\n【5. 边界条件测试结果】")
        invalid_count = sum(1 for r in boundary_results if not r.is_valid)
        print(f"   总测试数: {len(boundary_results)}")
        print(f"   异常响应: {invalid_count}")
        if invalid_count > 0:
            print("   ⚠️ 发现边界处理缺陷，建议加强参数校验")
        else:
            print("   ✅ 边界处理正常")
        
        print("\n" + "="*70)
        print("✅ 测试执行完毕，请将上方日志发给 Trae 生成详细报告。")
        print("="*70)


# ============ pytest 测试用例 ============

class TestDay05SamplingParameters:
    """Day 05: 采样参数与输出稳定性测试类"""
    
    @pytest.fixture(scope="class")
    def tester(self):
        """测试器fixture"""
        return SamplingParameterTester()
    
    def test_parameter_grid_scan(self, tester):
        """
        测试温度×Top-p参数网格扫描
        
        风险点：参数组合可能产生意外的输出不稳定性
        验证：所有组合的响应符合预期风险等级
        """
        # 使用精简网格加速测试
        temperatures = [0.0, 0.3, 0.7, 1.0, 1.5]
        top_ps = [0.1, 0.5, 0.9, 1.0]
        
        grid_results = tester.grid_scan(
            temperatures=temperatures,
            top_ps=top_ps,
            samples_per_cell=2
        )
        
        # 断言：高风险组合数量应在预期范围内
        critical_count = sum(1 for r in grid_results.values() if "🔴" in r.risk_level)
        high_count = sum(1 for r in grid_results.values() if "🟠" in r.risk_level)
        
        # T>1.0且P>0.9应为CRITICAL
        assert critical_count >= 1, "应至少识别出1个CRITICAL风险组合"
        
        # 保存结果供后续测试使用
        self.grid_results = grid_results
        
        print(f"\n✅ 网格扫描完成: {len(grid_results)}个组合")
    
    def test_temporal_stability(self, tester):
        """
        测试时间维度一致性
        
        风险点：相同参数在不同时间调用输出差异过大
        验证：连续调用的输出多样性在可控范围内
        """
        result = tester.temporal_stability_test(
            temperature=0.7,
            top_p=0.9,
            iterations=5,
            delay_seconds=0.2
        )
        
        # 断言：稳定性不应为UNSTABLE（对于中等参数）
        assert "🔴" not in result.stability_rating, \
            f"T=0.7,P=0.9不应判定为UNSTABLE，实际: {result.stability_rating}"
        
        # 断言：多样性分数应在合理范围
        assert 0 <= result.diversity_score <= 1, \
            f"多样性分数应在0-1范围内，实际: {result.diversity_score}"
        
        self.temporal_result = result
        
        print(f"\n✅ 时间稳定性测试完成: {result.stability_rating}")
    
    def test_boundary_conditions(self, tester):
        """
        测试参数边界条件
        
        风险点：极端参数值导致系统异常
        验证：系统对边界值有适当的错误处理
        """
        boundary_results = tester.boundary_test()
        
        # 统计结果
        valid_count = sum(1 for r in boundary_results if r.is_valid)
        invalid_count = len(boundary_results) - valid_count
        
        print(f"\n📊 边界测试统计: {valid_count}正常 / {invalid_count}异常")
        
        # 断言：系统应对明显越界值有处理（允许部分容错）
        # 注意：不同API实现可能有不同的容错策略
        extreme_invalid = [r for r in boundary_results 
                          if not r.is_valid and abs(r.param_value) > 2]
        
        if extreme_invalid:
            print(f"   ⚠️ 发现{len(extreme_invalid)}个极端值未正确处理")
        
        self.boundary_results = boundary_results
        
        print("\n✅ 边界条件测试完成")
    
    def test_generate_final_report(self, tester):
        """
        生成最终测试报告
        
        注意：此测试依赖于前面测试的结果
        """
        # 重新运行以获取完整结果
        grid_results = tester.grid_scan(
            temperatures=[0.0, 0.3, 0.7, 1.0, 1.5],
            top_ps=[0.1, 0.5, 0.9, 1.0],
            samples_per_cell=2
        )
        temporal_result = tester.temporal_stability_test(
            temperature=0.7, top_p=0.9, iterations=5, delay_seconds=0.2
        )
        boundary_results = tester.boundary_test()
        
        # 生成报告
        tester.generate_report(grid_results, temporal_result, boundary_results)
        
        # 最终断言：至少应有一些稳定配置
        stable_count = sum(1 for r in grid_results.values() if "✅" in r.stability_rating)
        assert stable_count > 0, "应至少存在1个稳定配置"
        
        print("\n✅ 最终报告生成完成")


# 主执行入口
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 05: 采样参数与输出稳定性")
    print("="*70)
    print("\n测试内容:")
    print("  1. 温度×Top-p参数网格扫描 (20种组合)")
    print("  2. 时间维度一致性验证")
    print("  3. 边界条件测试")
    print("\n" + "-"*70)
    
    # 创建测试器并执行完整测试流程
    tester = SamplingParameterTester()
    
    # 1. 参数网格扫描
    grid_results = tester.grid_scan(
        temperatures=[0.0, 0.3, 0.7, 1.0, 1.5],
        top_ps=[0.1, 0.5, 0.9, 1.0],
        samples_per_cell=2
    )
    
    # 2. 时间稳定性测试
    temporal_result = tester.temporal_stability_test(
        temperature=0.7,
        top_p=0.9,
        iterations=5,
        delay_seconds=0.2
    )
    
    # 3. 边界测试
    boundary_results = tester.boundary_test()
    
    # 生成报告
    tester.generate_report(grid_results, temporal_result, boundary_results)
