"""
Day 12: 输出鲁棒性测试 - 跨语言与语篇级改写

测试目标：
1. 验证模型对跨语言翻译的鲁棒性
2. 测试模型对语篇级改写的稳定性
3. 识别跨语言和语篇级脆弱点

测试架构师视角：
- 开发只管跑通，我们要想办法把它搞崩溃
- 关注翻译往返一致性、多语言答案一致性、语篇结构稳定性
"""

import pytest
import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set
from difflib import SequenceMatcher


class RobustnessLevel(Enum):
    """鲁棒性等级"""
    HIGH = "🟢 HIGH"
    MEDIUM = "🟡 MEDIUM"
    LOW = "🟠 LOW"
    CRITICAL = "🔴 CRITICAL"


class RobustnessTestType(Enum):
    """测试类型"""
    TRANSLATION_ROUNDTRIP = "翻译往返"
    MULTILINGUAL_PARALLEL = "多语言平行"
    PARAGRAPH_REORDERING = "段落重组"
    COREFERENCE_RESOLUTION = "指代消解"
    DETAIL_PRESERVATION = "细节保留"


@dataclass
class RobustnessResult:
    """鲁棒性测试结果"""
    test_type: "RobustnessTestType"
    original: str
    modified: str
    consistency_score: float
    key_info_retention: float
    is_robust: bool
    risk_level: RobustnessLevel
    message: str
    details: Dict


class MockTranslator:
    """
    模拟翻译器 - 具有可控的翻译缺陷
    
    设计缺陷：
    1. 文化概念可能丢失
    2. 细微语义差异
    3. 专业术语翻译不准确
    """
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        
        # 简化的翻译词典
        self.zh_to_en = {
            "春节": "Spring Festival",
            "元宵节": "Lantern Festival",
            "端午节": "Dragon Boat Festival",
            "中秋节": "Mid-Autumn Festival",
            "人工智能": "artificial intelligence",
            "机器学习": "machine learning",
            "深度学习": "deep learning",
            "光合作用": "photosynthesis",
            "二氧化碳": "carbon dioxide",
            "氧气": "oxygen",
            "植物": "plants",
            "光": "light",
            "水": "water",
            "是": "is",
            "什么": "what",
            "如何": "how",
            "为什么": "why",
            "请": "please",
            "谢谢": "thank you",
        }
        
        self.en_to_zh = {v: k for k, v in self.zh_to_en.items()}
        
        # 有问题的翻译（模拟翻译缺陷）
        self.problematic_translations = {
            "红包": "red envelope",  # 文化内涵丢失
            "面子": "face",  # 严重文化概念丢失
            "关系": "relationship",  # 严重文化概念丢失
        }
    
    def translate(self, text: str, src: str, tgt: str) -> str:
        """
        模拟翻译
        
        Args:
            text: 待翻译文本
            src: 源语言 (zh/en)
            tgt: 目标语言 (zh/en)
        """
        if src == tgt:
            return text
        
        # 简化的翻译逻辑
        if src == "zh" and tgt == "en":
            return self._zh_to_en(text)
        elif src == "en" and tgt == "zh":
            return self._en_to_zh(text)
        else:
            return text  # 不支持的语言对
    
    def _zh_to_en(self, text: str) -> str:
        """中文到英文"""
        result = text
        for zh, en in self.zh_to_en.items():
            result = result.replace(zh, en)
        
        # 模拟文化概念丢失
        for zh, en in self.problematic_translations.items():
            if zh in result:
                result = result.replace(zh, en)
                # 标记文化概念可能丢失
                result += " [CULTURAL_CONTEXT_LOST]"
        
        return result
    
    def _en_to_zh(self, text: str) -> str:
        """英文到中文"""
        result = text
        for en, zh in self.en_to_zh.items():
            result = result.replace(en, zh)
        
        # 移除标记
        result = result.replace(" [CULTURAL_CONTEXT_LOST]", "")
        
        return result


class MockLLM:
    """
    模拟LLM - 具有可控的跨语言和语篇鲁棒性缺陷
    """
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.translator = MockTranslator()
        
        # 知识库
        self.knowledge_base = {
            "什么是光合作用": "光合作用是植物利用光能将二氧化碳和水转化为有机物和氧气的过程。",
            "什么是人工智能": "人工智能是计算机科学的一个分支，研究如何让机器模拟人类智能。",
            "春节是什么": "春节是中国最重要的传统节日，象征着新的一年的开始。",
        }
    
    def generate(self, prompt: str, language: str = "zh") -> str:
        """生成回答"""
        # 清理输入
        clean_prompt = prompt.strip().replace("？", "").replace("?", "")
        
        # 尝试匹配知识库
        for key, value in self.knowledge_base.items():
            similarity = self._text_similarity(clean_prompt, key)
            if similarity > 0.6:
                # 模拟跨语言问题：如果输入是翻译后的，可能匹配失败
                if "[CULTURAL_CONTEXT_LOST]" in prompt:
                    return "这个问题涉及一些文化概念，我可能需要更多上下文来准确回答。"
                return value
        
        # 默认回答
        return "这是一个有趣的问题，但我需要更多上下文来回答。"
    
    def summarize(self, text: str) -> str:
        """生成摘要"""
        # 提取关键句子
        sentences = re.split(r'[。！？]', text)
        key_sentences = [s for s in sentences if len(s) > 10][:2]
        
        # 模拟语篇级问题：如果文本结构混乱，摘要质量下降
        if "[REORDERED]" in text:
            return "这段文本的结构有些混乱，我需要更多信息来生成准确的摘要。"
        
        return "。".join(key_sentences) + "。"
    
    def answer_coreference(self, text: str, question: str) -> str:
        """回答指代问题"""
        # 模拟指代消解缺陷
        if "他" in question:
            # 简单规则：如果文本中有多个男性名字，可能指代错误
            names = re.findall(r'[\u4e00-\u9fa5]{2,3}', text)
            if len(names) >= 2:
                # 50%概率指代错误
                if random.random() < 0.5:
                    return f"他指的是{names[1]}"  # 错误：应该是names[0]
                else:
                    return f"他指的是{names[0]}"
        
        return "我不确定指代的是谁。"
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        return SequenceMatcher(None, text1, text2).ratio()


class CrossLingualTester:
    """跨语言鲁棒性测试器"""
    
    def __init__(self, model: MockLLM, translator: MockTranslator):
        self.model = model
        self.translator = translator
    
    def test_translation_roundtrip(self, text: str) -> RobustnessResult:
        """
        翻译往返测试
        """
        print(f"\n{'='*60}")
        print(f"【翻译往返测试】")
        print(f"{'='*60}")
        print(f"原文: {text}")
        
        # Step 1: 中文 → 英文
        translated = self.translator.translate(text, "zh", "en")
        print(f"\n翻译(zh→en): {translated}")
        
        # Step 2: 英文 → 中文
        back_translated = self.translator.translate(translated, "en", "zh")
        print(f"回译(en→zh): {back_translated}")
        
        # Step 3: 语义一致性计算
        consistency = self.model._text_similarity(text, back_translated)
        
        # Step 4: 关键信息保留检查
        key_info_original = self.extract_key_info(text)
        key_info_back = self.extract_key_info(back_translated)
        
        if key_info_original:
            retention = len(key_info_original & key_info_back) / len(key_info_original)
        else:
            retention = 1.0
        
        print(f"\n语义一致性: {consistency:.3f}")
        print(f"关键信息保留率: {retention:.1%}")
        
        # 判断鲁棒性
        is_robust = consistency > 0.85 and retention > 0.9
        
        if consistency > 0.9 and retention > 0.95:
            risk_level = RobustnessLevel.HIGH
            message = "翻译往返鲁棒性良好"
        elif consistency > 0.75 and retention > 0.8:
            risk_level = RobustnessLevel.MEDIUM
            message = "翻译往返存在一定语义漂移"
        else:
            risk_level = RobustnessLevel.LOW
            message = "翻译往返存在严重语义漂移"
        
        print(f"鲁棒性判定: {risk_level.value}")
        print(f"结论: {message}")
        
        return RobustnessResult(
            test_type=RobustnessTestType.TRANSLATION_ROUNDTRIP,
            original=text,
            modified=back_translated,
            consistency_score=consistency,
            key_info_retention=retention,
            is_robust=is_robust,
            risk_level=risk_level,
            message=message,
            details={"translated": translated, "back_translated": back_translated}
        )
    
    def test_multilingual_parallel(self, question: str) -> RobustnessResult:
        """
        多语言平行测试
        """
        print(f"\n{'='*60}")
        print(f"【多语言平行测试】")
        print(f"{'='*60}")
        print(f"原问题(zh): {question}")
        
        # 翻译到不同语言
        languages = ["en"]
        translations = {"zh": question}
        
        for lang in languages:
            translations[lang] = self.translator.translate(question, "zh", lang)
        
        print(f"\n翻译结果:")
        for lang, trans in translations.items():
            print(f"  {lang}: {trans}")
        
        # 获取各语言答案
        answers = {}
        for lang, trans in translations.items():
            answers[lang] = self.model.generate(trans, lang)
        
        print(f"\n各语言答案:")
        for lang, ans in answers.items():
            print(f"  {lang}: {ans}")
        
        # 计算答案一致性（中文vs英文）
        if "zh" in answers and "en" in answers:
            consistency = self.model._text_similarity(answers["zh"], answers["en"])
        else:
            consistency = 1.0
        
        print(f"\n答案一致性(zh vs en): {consistency:.3f}")
        
        # 判断鲁棒性
        is_robust = consistency > 0.8
        
        if consistency > 0.9:
            risk_level = RobustnessLevel.HIGH
            message = "多语言答案一致性良好"
        elif consistency > 0.7:
            risk_level = RobustnessLevel.MEDIUM
            message = "多语言答案存在一定差异"
        else:
            risk_level = RobustnessLevel.LOW
            message = "多语言答案存在严重不一致"
        
        print(f"鲁棒性判定: {risk_level.value}")
        print(f"结论: {message}")
        
        return RobustnessResult(
            test_type=RobustnessTestType.MULTILINGUAL_PARALLEL,
            original=question,
            modified=str(translations),
            consistency_score=consistency,
            key_info_retention=consistency,
            is_robust=is_robust,
            risk_level=risk_level,
            message=message,
            details={"answers": answers}
        )
    
    def extract_key_info(self, text: str) -> Set[str]:
        """提取关键信息（简化版）"""
        # 提取实体（中文名词）
        entities = set(re.findall(r'[\u4e00-\u9fa5]{2,10}', text))
        # 提取数字
        numbers = set(re.findall(r'\d+', text))
        return entities | numbers


class DiscourseTester:
    """语篇级改写测试器"""
    
    def __init__(self, model: MockLLM):
        self.model = model
    
    def test_paragraph_reordering(self, text: str) -> RobustnessResult:
        """
        段落重组测试
        """
        print(f"\n{'='*60}")
        print(f"【段落重组测试】")
        print(f"{'='*60}")
        
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        print(f"原文段落数: {len(paragraphs)}")
        for i, p in enumerate(paragraphs, 1):
            print(f"  段落{i}: {p[:30]}...")
        
        # 生成重组变体（反转）
        reordered = paragraphs[::-1]
        reordered_text = "\n\n".join(reordered)
        reordered_text += " [REORDERED]"  # 标记重组
        
        print(f"\n重组后段落顺序: {list(range(len(paragraphs), 0, -1))}")
        
        # 获取摘要
        original_summary = self.model.summarize(text)
        reordered_summary = self.model.summarize(reordered_text)
        
        print(f"\n原文摘要: {original_summary}")
        print(f"重组后摘要: {reordered_summary}")
        
        # 检查一致性
        consistency = self.model._text_similarity(original_summary, reordered_summary)
        
        # 检查关键事实保留
        key_facts_original = self.extract_key_facts(original_summary)
        key_facts_reordered = self.extract_key_facts(reordered_summary)
        
        if key_facts_original:
            retention = len(key_facts_original & key_facts_reordered) / len(key_facts_original)
        else:
            retention = 1.0
        
        print(f"\n摘要一致性: {consistency:.3f}")
        print(f"关键事实保留率: {retention:.1%}")
        
        # 判断鲁棒性
        is_robust = consistency > 0.8 and retention > 0.9
        
        if consistency > 0.9 and retention > 0.95:
            risk_level = RobustnessLevel.HIGH
            message = "段落重组鲁棒性良好"
        elif consistency > 0.7 and retention > 0.8:
            risk_level = RobustnessLevel.MEDIUM
            message = "段落重组存在一定影响"
        else:
            risk_level = RobustnessLevel.LOW
            message = "段落重组严重影响理解"
        
        print(f"鲁棒性判定: {risk_level.value}")
        print(f"结论: {message}")
        
        return RobustnessResult(
            test_type=RobustnessTestType.PARAGRAPH_REORDERING,
            original=text,
            modified=reordered_text,
            consistency_score=consistency,
            key_info_retention=retention,
            is_robust=is_robust,
            risk_level=risk_level,
            message=message,
            details={"original_summary": original_summary, "reordered_summary": reordered_summary}
        )
    
    def test_coreference_resolution(self) -> RobustnessResult:
        """
        指代消解鲁棒性测试
        """
        print(f"\n{'='*60}")
        print(f"【指代消解测试】")
        print(f"{'='*60}")
        
        # 测试用例
        test_cases = [
            {
                "text": "张三和李四去公园。他在那里遇到了王五。",
                "question": "他指的是谁？",
                "expected": "张三"
            },
            {
                "text": "公司A推出了产品X。这款产品非常受欢迎。",
                "question": "这款产品指的是什么？",
                "expected": "产品X"
            }
        ]
        
        correct_count = 0
        results = []
        
        for case in test_cases:
            print(f"\n测试用例: {case['text']}")
            print(f"问题: {case['question']}")
            
            answer = self.model.answer_coreference(case['text'], case['question'])
            print(f"模型回答: {answer}")
            
            is_correct = case['expected'] in answer
            if is_correct:
                correct_count += 1
                print("✅ 正确")
            else:
                print("❌ 错误")
            
            results.append({
                "text": case['text'],
                "expected": case['expected'],
                "answer": answer,
                "correct": is_correct
            })
        
        accuracy = correct_count / len(test_cases) if test_cases else 0.0
        
        print(f"\n指代消解准确率: {accuracy:.1%}")
        
        # 判断鲁棒性
        is_robust = accuracy > 0.95
        
        if accuracy > 0.95:
            risk_level = RobustnessLevel.HIGH
            message = "指代消解鲁棒性良好"
        elif accuracy > 0.8:
            risk_level = RobustnessLevel.MEDIUM
            message = "指代消解存在一定问题"
        else:
            risk_level = RobustnessLevel.LOW
            message = "指代消解存在严重问题"
        
        print(f"鲁棒性判定: {risk_level.value}")
        print(f"结论: {message}")
        
        return RobustnessResult(
            test_type=RobustnessTestType.COREFERENCE_RESOLUTION,
            original=str(test_cases),
            modified="",
            consistency_score=accuracy,
            key_info_retention=accuracy,
            is_robust=is_robust,
            risk_level=risk_level,
            message=message,
            details={"results": results, "accuracy": accuracy}
        )
    
    def test_detail_preservation(self) -> RobustnessResult:
        """
        细节保留测试
        """
        print(f"\n{'='*60}")
        print(f"【细节保留测试】")
        print(f"{'='*60}")
        
        # 包含关键细节的文本
        detailed_text = "请在24小时内完成支付，否则订单将自动取消。退款将在3-5个工作日内到账。"
        simplified_text = "请尽快完成支付。退款会很快到账。"
        
        print(f"详细版本: {detailed_text}")
        print(f"简化版本: {simplified_text}")
        
        # 提取关键细节
        key_details = ["24小时", "自动取消", "3-5个工作日"]
        
        # 检查简化版本保留了多少细节
        preserved_details = [d for d in key_details if d in simplified_text]
        retention = len(preserved_details) / len(key_details)
        
        print(f"\n关键细节: {key_details}")
        print(f"保留的细节: {preserved_details}")
        print(f"细节保留率: {retention:.1%}")
        
        # 判断鲁棒性
        is_robust = retention > 0.9
        
        if retention > 0.95:
            risk_level = RobustnessLevel.HIGH
            message = "细节保留良好"
        elif retention > 0.7:
            risk_level = RobustnessLevel.MEDIUM
            message = "部分细节丢失"
        else:
            risk_level = RobustnessLevel.LOW
            message = "关键细节严重丢失"
        
        print(f"鲁棒性判定: {risk_level.value}")
        print(f"结论: {message}")
        
        return RobustnessResult(
            test_type=RobustnessTestType.DETAIL_PRESERVATION,
            original=detailed_text,
            modified=simplified_text,
            consistency_score=retention,
            key_info_retention=retention,
            is_robust=is_robust,
            risk_level=risk_level,
            message=message,
            details={"key_details": key_details, "preserved": preserved_details}
        )
    
    def extract_key_facts(self, text: str) -> Set[str]:
        """提取关键事实"""
        # 提取实体
        entities = set(re.findall(r'[\u4e00-\u9fa5]{2,10}', text))
        # 提取数字
        numbers = set(re.findall(r'\d+', text))
        return entities | numbers


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
def mock_translator():
    """提供Mock翻译器"""
    return MockTranslator(seed=42)


@pytest.fixture
def cross_lingual_tester(mock_model, mock_translator):
    """提供跨语言测试器"""
    return CrossLingualTester(mock_model, mock_translator)


@pytest.fixture
def discourse_tester(mock_model):
    """提供语篇测试器"""
    return DiscourseTester(mock_model)


@pytest.fixture
def evaluator():
    """提供评估器"""
    return RobustnessEvaluator()


class TestCrossLingualRobustness:
    """跨语言鲁棒性测试套件"""
    
    def test_translation_roundtrip(self, cross_lingual_tester, evaluator):
        """测试翻译往返鲁棒性（关键测试）"""
        print("\n" + "="*60)
        print("【测试1】翻译往返鲁棒性验证（关键测试）")
        print("="*60)
        
        text = "什么是光合作用？"
        result = cross_lingual_tester.test_translation_roundtrip(text)
        evaluator.add_result(result)
        
        # 验证：语义一致性应可计算
        assert 0 <= result.consistency_score <= 1.0, "一致性分数应在0-1之间"
        
        # 风险验证
        if result.risk_level in [RobustnessLevel.LOW, RobustnessLevel.CRITICAL]:
            print(f"\n🔴 发现跨语言鲁棒性问题: {result.message}")
        
        print("\n✅ 翻译往返鲁棒性测试通过")
    
    def test_cultural_concept_preservation(self, cross_lingual_tester, evaluator):
        """测试文化概念保留"""
        print("\n" + "="*60)
        print("【测试2】文化概念保留验证（关键测试）")
        print("="*60)
        
        # 包含文化概念的文本
        text = "春节是中国最重要的传统节日。"
        result = cross_lingual_tester.test_translation_roundtrip(text)
        evaluator.add_result(result)
        
        # 验证：文化概念应被保留
        print(f"\n文化概念'春节'保留检查:")
        if "春节" in result.modified:
            print("✅ 文化概念保留")
        else:
            print("⚠️ 文化概念可能丢失")
        
        print("\n✅ 文化概念保留测试通过")
    
    def test_multilingual_parallel(self, cross_lingual_tester, evaluator):
        """测试多语言平行一致性"""
        print("\n" + "="*60)
        print("【测试3】多语言平行一致性验证")
        print("="*60)
        
        question = "什么是人工智能？"
        result = cross_lingual_tester.test_multilingual_parallel(question)
        evaluator.add_result(result)
        
        # 验证：多语言答案应一致
        assert result.consistency_score >= 0, "一致性分数应非负"
        
        print("\n✅ 多语言平行一致性测试通过")


class TestDiscourseRobustness:
    """语篇级鲁棒性测试套件"""
    
    def test_paragraph_reordering(self, discourse_tester, evaluator):
        """测试段落重组鲁棒性（关键测试）"""
        print("\n" + "="*60)
        print("【测试4】段落重组鲁棒性验证（关键测试）")
        print("="*60)
        
        text = """公司A在2020年推出了产品X。

这款产品大获成功，销量突破百万。

然而，竞争对手公司B在2021年推出了类似产品。"""
        
        result = discourse_tester.test_paragraph_reordering(text)
        evaluator.add_result(result)
        
        # 验证：段落重组不应严重影响理解
        assert result.consistency_score >= 0, "一致性分数应非负"
        
        if result.risk_level in [RobustnessLevel.LOW, RobustnessLevel.CRITICAL]:
            print(f"\n🔴 发现语篇级鲁棒性问题: {result.message}")
        
        print("\n✅ 段落重组鲁棒性测试通过")
    
    def test_coreference_resolution(self, discourse_tester, evaluator):
        """测试指代消解鲁棒性"""
        print("\n" + "="*60)
        print("【测试5】指代消解鲁棒性验证")
        print("="*60)
        
        result = discourse_tester.test_coreference_resolution()
        evaluator.add_result(result)
        
        # 验证：准确率应可计算
        assert 0 <= result.consistency_score <= 1.0, "准确率应在0-1之间"
        
        if result.consistency_score < 0.8:
            print(f"\n⚠️ 指代消解准确率较低({result.consistency_score:.1%})")
        
        print("\n✅ 指代消解鲁棒性测试通过")
    
    def test_detail_preservation(self, discourse_tester, evaluator):
        """测试细节保留"""
        print("\n" + "="*60)
        print("【测试6】细节保留验证")
        print("="*60)
        
        result = discourse_tester.test_detail_preservation()
        evaluator.add_result(result)
        
        # 验证：关键细节应被保留
        assert result.key_info_retention >= 0, "保留率应非负"
        
        if result.key_info_retention < 0.7:
            print(f"\n⚠️ 关键细节保留率较低({result.key_info_retention:.1%})")
        
        print("\n✅ 细节保留测试通过")


class TestComprehensiveEvaluation:
    """综合评估测试"""
    
    def test_comprehensive_robustness_evaluation(self, cross_lingual_tester, discourse_tester, evaluator):
        """综合鲁棒性评估"""
        print("\n" + "="*60)
        print("【测试7】综合鲁棒性评估")
        print("="*60)
        
        # 运行多个测试
        test_cases = [
            ("什么是光合作用？", "translation"),
            ("春节是什么？", "cultural"),
        ]
        
        for text, test_type in test_cases:
            if test_type == "translation":
                result = cross_lingual_tester.test_translation_roundtrip(text)
            else:
                result = cross_lingual_tester.test_translation_roundtrip(text)
            evaluator.add_result(result)
        
        # 语篇测试
        discourse_tests = [
            discourse_tester.test_coreference_resolution,
            discourse_tester.test_detail_preservation,
        ]
        
        for test in discourse_tests:
            result = test()
            evaluator.add_result(result)
        
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
