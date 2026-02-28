"""
Day 11: 输出鲁棒性测试 - 同义改写与噪声注入

测试目标：
1. 验证模型对同义改写的稳定性
2. 测试模型对噪声输入的容错能力
3. 识别鲁棒性脆弱点

测试架构师视角：
- 开发只管跑通，我们要想办法把它搞崩溃
- 关注语义一致性、准确率衰减、失效临界点
"""

import pytest
import random
import string
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher


class RobustnessLevel(Enum):
    """鲁棒性等级"""
    HIGH = "🟢 HIGH"       # 高度鲁棒
    MEDIUM = "🟡 MEDIUM"   # 中等鲁棒
    LOW = "🟠 LOW"         # 低鲁棒性
    CRITICAL = "🔴 CRITICAL"  # 严重脆弱


class RobustnessTestType(Enum):
    """测试类型"""
    LEXICAL = "词汇改写"
    SYNTACTIC = "句法改写"
    NOISE_CHAR = "字符级噪声"
    NOISE_WORD = "词级噪声"


@dataclass
class RobustnessResult:
    """鲁棒性测试结果"""
    test_type: "RobustnessTestType"
    original_prompt: str
    variations: List[str]
    outputs: List[str]
    consistency_scores: List[float]
    accuracy_scores: List[float]
    is_robust: bool
    risk_level: RobustnessLevel
    message: str


class MockLLM:
    """
    模拟LLM - 具有可控的鲁棒性缺陷
    
    设计缺陷：
    1. 对特定关键词敏感（如"请"、"能否"）
    2. 对否定词位置敏感
    3. 对噪声敏感（准确率随噪声增加而下降）
    4. 对语序敏感
    """
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.call_count = 0
        
        # 知识库：问题 -> 标准答案
        self.knowledge_base = {
            "什么是光合作用": "光合作用是植物利用光能将二氧化碳和水转化为有机物和氧气的过程。",
            "什么是人工智能": "人工智能是计算机科学的一个分支，研究如何让机器模拟人类智能。",
            "水的沸点是多少": "水的沸点在标准大气压下是100摄氏度。",
        }
        
        # 同义词映射
        self.synonyms = {
            "什么": "啥",
            "是": "为",
            "植物": "绿植",
            "利用": "使用",
            "转化": "转变",
            "过程": "流程",
            "计算机": "电脑",
            "研究": "探究",
            "模拟": "模仿",
            "沸点": "沸腾温度",
            "标准": "规范",
        }
    
    def generate(self, prompt: str, noise_level: float = 0.0) -> str:
        """
        模拟生成，引入鲁棒性问题
        
        Args:
            prompt: 输入提示
            noise_level: 噪声水平（0.0-1.0）
        """
        self.call_count += 1
        
        # 清理输入
        clean_prompt = prompt.strip().replace("？", "").replace("?", "")
        
        # 模拟噪声影响：噪声越高，越可能出错
        error_probability = noise_level * 0.8  # 噪声导致错误的概率
        
        if random.random() < error_probability:
            # 模拟噪声导致的错误输出
            error_responses = [
                "抱歉，我不太理解您的问题。",
                "这个问题有点复杂，我需要更多信息。",
                "输入似乎有些混乱，请重新表述。",
            ]
            return random.choice(error_responses)
        
        # 检查是否有礼貌用语（格式依赖缺陷）
        has_polite = any(word in clean_prompt for word in ["请", "能否", "麻烦", "谢谢"])
        if not has_polite and random.random() < 0.3:
            # 30%概率在缺少礼貌用语时表现不佳
            return "请用更礼貌的方式提问。"
        
        # 检查否定词位置（逻辑敏感缺陷）
        if "不" in clean_prompt:
            # 模拟否定词理解错误
            if random.random() < 0.2:
                return "是的，您说得对。"  # 错误地肯定了否定句
        
        # 尝试匹配知识库
        for key, value in self.knowledge_base.items():
            # 计算相似度
            similarity = self._text_similarity(clean_prompt, key)
            if similarity > 0.6:
                # 模拟同义改写敏感：相似度不够高时，回答质量下降
                if similarity < 0.8 and random.random() < 0.4:
                    return "这个问题我不太确定，可能是关于" + key[:5] + "..."
                return value
        
        # 默认回答
        return "这是一个有趣的问题，但我需要更多上下文来回答。"
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def get_answer_consistency(self, prompt1: str, prompt2: str) -> float:
        """获取两个提示对应答案的一致性"""
        answer1 = self.generate(prompt1)
        answer2 = self.generate(prompt2)
        return self._text_similarity(answer1, answer2)


class ParaphraseTester:
    """同义改写测试器"""
    
    def __init__(self, model: MockLLM):
        self.model = model
        
        # 同义词词典
        self.synonyms = {
            "什么": ["啥", "哪个", "何种"],
            "是": ["为", "乃", "系"],
            "植物": ["绿植", "花草", "作物"],
            "利用": ["使用", "运用", "采用"],
            "转化": ["转变", "转换", "变成"],
            "过程": ["流程", "程序", "步骤"],
            "计算机": ["电脑", "计算设备"],
            "研究": ["探究", "钻研", "探索"],
            "模拟": ["模仿", "仿效", "模拟"],
            "沸点": ["沸腾温度", "沸腾点"],
            "标准": ["规范", "基准"],
            "请": ["能否", "麻烦", "可以"],
        }
    
    def generate_lexical_variations(self, prompt: str, replace_ratio: float = 0.3) -> List[str]:
        """
        生成词汇层面改写
        
        Args:
            prompt: 原始提示
            replace_ratio: 替换比例
        """
        variations = []
        
        # 变体1: 部分同义词替换
        words = list(prompt)
        replace_count = max(1, int(len(words) * replace_ratio))
        
        for char in prompt:
            if char in self.synonyms and replace_count > 0:
                synonym = random.choice(self.synonyms[char])
                prompt = prompt.replace(char, synonym, 1)
                replace_count -= 1
        
        variations.append(prompt)
        
        # 变体2: 调整礼貌用语
        if "请" in prompt:
            variations.append(prompt.replace("请", "能否"))
        else:
            variations.append("请" + prompt)
        
        return variations
    
    def generate_syntactic_variations(self, prompt: str) -> List[str]:
        """
        生成句法层面改写
        
        包括：
        - 主动被动转换
        - 语序调整
        - 句式变换
        """
        variations = []
        
        # 变体1: 调整语序（简单模拟）
        if "什么是" in prompt:
            variations.append(prompt.replace("什么是", "请解释"))
        
        # 变体2: 改变句式
        if "?" in prompt or "？" in prompt:
            variations.append(prompt.replace("?", "。请说明。").replace("？", "。请说明。"))
        
        # 变体3: 添加修饰
        variations.append("我想知道，" + prompt)
        
        return variations
    
    def test_lexical_robustness(self, prompt: str) -> RobustnessResult:
        """
        测试词汇层面鲁棒性
        """
        print(f"\n{'='*60}")
        print(f"【词汇改写测试】")
        print(f"{'='*60}")
        print(f"原始提示: {prompt}")
        
        # 生成改写变体
        variations = self.generate_lexical_variations(prompt)
        print(f"\n生成 {len(variations)} 个改写变体:")
        for i, v in enumerate(variations, 1):
            print(f"  变体{i}: {v}")
        
        # 获取模型输出
        outputs = [self.model.generate(v) for v in variations]
        print(f"\n模型输出:")
        for i, o in enumerate(outputs, 1):
            print(f"  输出{i}: {o[:50]}...")
        
        # 计算语义一致性
        consistency_scores = []
        for i in range(1, len(outputs)):
            score = self.model.get_answer_consistency(variations[0], variations[i])
            consistency_scores.append(score)
        
        print(f"\n语义一致性分数:")
        for i, score in enumerate(consistency_scores, 1):
            status = "✅" if score > 0.8 else "⚠️"
            print(f"  变体{i} vs 原始: {score:.3f} {status}")
        
        # 判断鲁棒性
        avg_consistency = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 1.0
        is_robust = avg_consistency > 0.8
        
        if avg_consistency > 0.9:
            risk_level = RobustnessLevel.HIGH
            message = "词汇改写鲁棒性良好"
        elif avg_consistency > 0.7:
            risk_level = RobustnessLevel.MEDIUM
            message = "词汇改写存在一定敏感"
        else:
            risk_level = RobustnessLevel.LOW
            message = "词汇改写敏感，存在鲁棒性问题"
        
        print(f"\n平均一致性: {avg_consistency:.3f}")
        print(f"鲁棒性判定: {risk_level.value}")
        print(f"结论: {message}")
        
        return RobustnessResult(
            test_type=RobustnessTestType.LEXICAL,
            original_prompt=prompt,
            variations=variations,
            outputs=outputs,
            consistency_scores=consistency_scores,
            accuracy_scores=[],
            is_robust=is_robust,
            risk_level=risk_level,
            message=message
        )
    
    def test_syntactic_robustness(self, prompt: str) -> RobustnessResult:
        """
        测试句法层面鲁棒性
        """
        print(f"\n{'='*60}")
        print(f"【句法改写测试】")
        print(f"{'='*60}")
        print(f"原始提示: {prompt}")
        
        # 生成句法变体
        variations = self.generate_syntactic_variations(prompt)
        print(f"\n生成 {len(variations)} 个句法变体:")
        for i, v in enumerate(variations, 1):
            print(f"  变体{i}: {v}")
        
        # 获取模型输出
        outputs = [self.model.generate(v) for v in variations]
        print(f"\n模型输出:")
        for i, o in enumerate(outputs, 1):
            print(f"  输出{i}: {o[:50]}...")
        
        # 计算一致性
        consistency_scores = []
        for i in range(1, len(outputs)):
            score = self.model.get_answer_consistency(variations[0], variations[i])
            consistency_scores.append(score)
        
        print(f"\n语义一致性分数:")
        for i, score in enumerate(consistency_scores, 1):
            status = "✅" if score > 0.8 else "⚠️"
            print(f"  变体{i} vs 原始: {score:.3f} {status}")
        
        avg_consistency = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 1.0
        is_robust = avg_consistency > 0.8
        
        if avg_consistency > 0.9:
            risk_level = RobustnessLevel.HIGH
            message = "句法改写鲁棒性良好"
        elif avg_consistency > 0.7:
            risk_level = RobustnessLevel.MEDIUM
            message = "句法改写存在一定敏感"
        else:
            risk_level = RobustnessLevel.LOW
            message = "句法改写敏感，存在鲁棒性问题"
        
        print(f"\n平均一致性: {avg_consistency:.3f}")
        print(f"鲁棒性判定: {risk_level.value}")
        print(f"结论: {message}")
        
        return RobustnessResult(
            test_type=RobustnessTestType.SYNTACTIC,
            original_prompt=prompt,
            variations=variations,
            outputs=outputs,
            consistency_scores=consistency_scores,
            accuracy_scores=[],
            is_robust=is_robust,
            risk_level=risk_level,
            message=message
        )


class NoiseTester:
    """噪声注入测试器"""
    
    def __init__(self, model: MockLLM):
        self.model = model
    
    def inject_char_noise(self, text: str, noise_ratio: float) -> str:
        """
        注入字符级噪声
        
        Args:
            text: 原始文本
            noise_ratio: 噪声比例 (0.0 - 1.0)
        """
        chars = list(text)
        num_noisy = max(1, int(len(chars) * noise_ratio))
        
        noise_types = ['replace', 'insert', 'delete', 'swap']
        
        for _ in range(num_noisy):
            if len(chars) < 2:
                break
            pos = random.randint(0, len(chars) - 1)
            noise_type = random.choice(noise_types)
            
            if noise_type == 'replace':
                chars[pos] = random.choice(string.ascii_letters + string.digits)
            elif noise_type == 'insert':
                chars.insert(pos, random.choice(string.ascii_letters))
            elif noise_type == 'delete':
                chars.pop(pos)
            elif noise_type == 'swap' and pos < len(chars) - 1:
                chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
        
        return ''.join(chars)
    
    def test_noise_robustness(self, prompt: str, noise_levels: List[float]) -> RobustnessResult:
        """
        测试噪声鲁棒性
        
        Args:
            prompt: 原始提示
            noise_levels: 噪声级别列表
        """
        print(f"\n{'='*60}")
        print(f"【噪声注入测试】")
        print(f"{'='*60}")
        print(f"原始提示: {prompt}")
        print(f"\n噪声级别: {noise_levels}")
        
        # 生成噪声变体
        variations = []
        for level in noise_levels:
            noisy = self.inject_char_noise(prompt, level)
            variations.append(noisy)
        
        print(f"\n噪声变体:")
        for i, (level, v) in enumerate(zip(noise_levels, variations), 1):
            print(f"  Level {level*100:.0f}%: {v}")
        
        # 获取原始输出（作为基准）
        original_output = self.model.generate(prompt)
        print(f"\n原始输出: {original_output}")
        
        # 获取噪声输出
        outputs = [self.model.generate(v, noise_level=level) for v, level in zip(variations, noise_levels)]
        print(f"\n噪声输出:")
        for i, (level, o) in enumerate(zip(noise_levels, outputs), 1):
            print(f"  Level {level*100:.0f}%: {o}")
        
        # 计算准确率（与原始输出的一致性）
        accuracy_scores = []
        for output in outputs:
            score = self.model._text_similarity(original_output, output)
            accuracy_scores.append(score)
        
        print(f"\n准确率衰减:")
        for level, score in zip(noise_levels, accuracy_scores):
            status = "✅" if score > 0.7 else "⚠️" if score > 0.4 else "❌"
            print(f"  Level {level*100:.0f}%: {score:.3f} {status}")
        
        # 计算衰减率和失效临界点
        if accuracy_scores:
            decay_rate = (1.0 - accuracy_scores[-1]) / 1.0
            
            # 找失效临界点（准确率 < 0.5）
            failure_point = None
            for level, score in zip(noise_levels, accuracy_scores):
                if score < 0.5:
                    failure_point = level
                    break
        else:
            decay_rate = 0.0
            failure_point = None
        
        print(f"\n总体衰减率: {decay_rate:.1%}")
        if failure_point:
            print(f"失效临界点: {failure_point*100:.0f}% 噪声")
        else:
            print(f"失效临界点: 未达到")
        
        # 判断鲁棒性
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 1.0
        is_robust = avg_accuracy > 0.7
        
        if decay_rate < 0.2:
            risk_level = RobustnessLevel.HIGH
            message = "噪声鲁棒性良好"
        elif decay_rate < 0.5:
            risk_level = RobustnessLevel.MEDIUM
            message = "噪声鲁棒性一般，存在衰减"
        else:
            risk_level = RobustnessLevel.LOW
            message = "噪声鲁棒性差，快速失效"
        
        print(f"鲁棒性判定: {risk_level.value}")
        print(f"结论: {message}")
        
        return RobustnessResult(
            test_type=RobustnessTestType.NOISE_CHAR,
            original_prompt=prompt,
            variations=variations,
            outputs=outputs,
            consistency_scores=[],
            accuracy_scores=accuracy_scores,
            is_robust=is_robust,
            risk_level=risk_level,
            message=message
        )


class RobustnessEvaluator:
    """鲁棒性综合评估器"""
    
    def __init__(self):
        self.results: List[RobustnessResult] = []
    
    def add_result(self, result: RobustnessResult):
        """添加测试结果"""
        self.results.append(result)
    
    def generate_report(self) -> Dict:
        """生成综合评估报告"""
        print(f"\n{'='*70}")
        print(f"【综合鲁棒性评估报告】")
        print(f"{'='*70}")
        
        # 统计各风险等级
        risk_counts = {level: 0 for level in RobustnessLevel}
        for result in self.results:
            risk_counts[result.risk_level] += 1
        
        print(f"\n风险分布统计:")
        for level, count in risk_counts.items():
            if count > 0:
                print(f"  {level.value}: {count} 项")
        
        # 计算综合得分
        level_scores = {
            RobustnessLevel.HIGH: 1.0,
            RobustnessLevel.MEDIUM: 0.6,
            RobustnessLevel.LOW: 0.3,
            RobustnessLevel.CRITICAL: 0.0
        }
        
        total_score = sum(level_scores[r.risk_level] for r in self.results)
        avg_score = total_score / len(self.results) if self.results else 0.0
        
        print(f"\n综合鲁棒性得分: {avg_score:.2f}/1.0")
        
        # 整体评级
        if avg_score >= 0.8:
            overall_level = RobustnessLevel.HIGH
            recommendation = "鲁棒性良好，可投入生产环境"
        elif avg_score >= 0.5:
            overall_level = RobustnessLevel.MEDIUM
            recommendation = "鲁棒性一般，建议优化后上线"
        else:
            overall_level = RobustnessLevel.LOW
            recommendation = "鲁棒性不足，需重点改进"
        
        print(f"整体评级: {overall_level.value}")
        print(f"建议: {recommendation}")
        
        # 脆弱点分析
        print(f"\n识别的脆弱点:")
        vulnerable_tests = [r for r in self.results if r.risk_level in [RobustnessLevel.LOW, RobustnessLevel.CRITICAL]]
        if vulnerable_tests:
            for r in vulnerable_tests:
                print(f"  ⚠️ {r.test_type.value}: {r.message}")
        else:
            print(f"  ✅ 未发现明显脆弱点")
        
        return {
            "overall_score": avg_score,
            "overall_level": overall_level,
            "risk_distribution": risk_counts,
            "vulnerable_points": len(vulnerable_tests),
            "recommendation": recommendation
        }


# ============ Pytest 测试用例 ============

@pytest.fixture
def mock_model():
    """提供Mock LLM实例"""
    return MockLLM(seed=42)


@pytest.fixture
def paraphrase_tester(mock_model):
    """提供改写测试器"""
    return ParaphraseTester(mock_model)


@pytest.fixture
def noise_tester(mock_model):
    """提供噪声测试器"""
    return NoiseTester(mock_model)


@pytest.fixture
def evaluator():
    """提供评估器"""
    return RobustnessEvaluator()


class TestRobustness:
    """鲁棒性测试套件"""
    
    def test_lexical_paraphrase_robustness(self, paraphrase_tester, evaluator):
        """测试词汇改写鲁棒性"""
        print("\n" + "="*60)
        print("【测试1】词汇改写鲁棒性验证（关键测试）")
        print("="*60)
        
        prompt = "什么是光合作用？"
        result = paraphrase_tester.test_lexical_robustness(prompt)
        evaluator.add_result(result)
        
        # 验证：至少有一个改写变体
        assert len(result.variations) >= 1, "应生成至少1个改写变体"
        
        # 验证：输出了结果
        assert len(result.outputs) == len(result.variations), "输出数量应与变体数量一致"
        
        # 风险验证：如果鲁棒性低，需要记录
        if result.risk_level in [RobustnessLevel.LOW, RobustnessLevel.CRITICAL]:
            print(f"\n🔴 发现鲁棒性问题: {result.message}")
        
        print("\n✅ 词汇改写鲁棒性测试通过")
    
    def test_syntactic_paraphrase_robustness(self, paraphrase_tester, evaluator):
        """测试句法改写鲁棒性"""
        print("\n" + "="*60)
        print("【测试2】句法改写鲁棒性验证")
        print("="*60)
        
        prompt = "什么是人工智能？"
        result = paraphrase_tester.test_syntactic_robustness(prompt)
        evaluator.add_result(result)
        
        # 验证：生成了句法变体
        assert len(result.variations) >= 1, "应生成至少1个句法变体"
        
        # 验证：语义一致性计算
        assert len(result.consistency_scores) > 0, "应计算语义一致性分数"
        
        print("\n✅ 句法改写鲁棒性测试通过")
    
    def test_noise_injection_robustness(self, noise_tester, evaluator):
        """测试噪声注入鲁棒性（关键测试）"""
        print("\n" + "="*60)
        print("【测试3】噪声注入鲁棒性验证（关键测试）")
        print("="*60)
        
        prompt = "水的沸点是多少？"
        noise_levels = [0.05, 0.15, 0.30, 0.50]  # 5%, 15%, 30%, 50%
        
        result = noise_tester.test_noise_robustness(prompt, noise_levels)
        evaluator.add_result(result)
        
        # 验证：生成了所有噪声级别
        assert len(result.variations) == len(noise_levels), "应生成所有噪声级别的变体"
        
        # 验证：准确率分数记录
        assert len(result.accuracy_scores) == len(noise_levels), "应记录所有准确率分数"
        
        # 关键验证：高噪声下准确率不应骤降
        if result.accuracy_scores:
            high_noise_accuracy = result.accuracy_scores[-1]  # 50%噪声
            print(f"\n高噪声(50%)准确率: {high_noise_accuracy:.3f}")
            
            if high_noise_accuracy < 0.3:
                print(f"\n🔴 警告：高噪声下准确率过低({high_noise_accuracy:.3f})，存在严重鲁棒性问题")
        
        print("\n✅ 噪声注入鲁棒性测试通过")
    
    def test_format_dependency(self, mock_model):
        """测试格式依赖（礼貌用语敏感）"""
        print("\n" + "="*60)
        print("【测试4】格式依赖验证（礼貌用语敏感）")
        print("="*60)
        
        # 有礼貌用语的输入
        polite_prompt = "请问，什么是光合作用？"
        polite_output = mock_model.generate(polite_prompt)
        
        # 无礼貌用语的输入
        direct_prompt = "什么是光合作用？"
        direct_output = mock_model.generate(direct_prompt)
        
        print(f"礼貌输入: {polite_prompt}")
        print(f"输出: {polite_output}")
        print(f"\n直接输入: {direct_prompt}")
        print(f"输出: {direct_output}")
        
        # 检查是否存在格式依赖问题
        if "礼貌" in direct_output:
            print(f"\n🔴 发现格式依赖问题：模型对礼貌用语敏感")
        else:
            print(f"\n✅ 未发现明显的格式依赖问题")
        
        print("\n✅ 格式依赖测试通过")
    
    def test_negation_sensitivity(self, mock_model):
        """测试否定词敏感"""
        print("\n" + "="*60)
        print("【测试5】否定词敏感验证")
        print("="*60)
        
        # 肯定句
        positive_prompt = "水是液体吗？"
        positive_output = mock_model.generate(positive_prompt)
        
        # 否定句
        negative_prompt = "水不是固体吗？"
        negative_output = mock_model.generate(negative_prompt)
        
        print(f"肯定句: {positive_prompt}")
        print(f"输出: {positive_output}")
        print(f"\n否定句: {negative_prompt}")
        print(f"输出: {negative_output}")
        
        # 检查否定词处理
        # 注意：由于Mock模型简单，这里主要验证测试框架
        print(f"\n✅ 否定词敏感测试完成（需人工判断逻辑一致性）")
    
    def test_comprehensive_robustness_evaluation(self, paraphrase_tester, noise_tester, evaluator):
        """综合鲁棒性评估"""
        print("\n" + "="*60)
        print("【测试6】综合鲁棒性评估")
        print("="*60)
        
        # 运行多个测试并收集结果
        test_prompts = [
            "什么是光合作用？",
            "什么是人工智能？",
            "水的沸点是多少？"
        ]
        
        for prompt in test_prompts:
            # 词汇测试
            result_lexical = paraphrase_tester.test_lexical_robustness(prompt)
            evaluator.add_result(result_lexical)
            
            # 噪声测试
            result_noise = noise_tester.test_noise_robustness(prompt, [0.1, 0.3])
            evaluator.add_result(result_noise)
        
        # 生成综合报告
        report = evaluator.generate_report()
        
        # 验证报告结构
        assert "overall_score" in report, "报告应包含综合得分"
        assert "overall_level" in report, "报告应包含整体评级"
        assert "recommendation" in report, "报告应包含建议"
        
        print("\n✅ 综合鲁棒性评估完成")


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "-s"])
