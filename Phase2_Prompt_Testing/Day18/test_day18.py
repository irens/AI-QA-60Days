"""
Day 18: 跨模型Few-shot迁移测试
目标：最小可用，专注风险验证，杜绝多余业务逻辑
测试架构师视角：验证同一套Few-shot示例在不同LLM模型上的迁移效果
"""

import json
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher
from enum import Enum


class ModelType(Enum):
    """模拟的LLM模型类型"""
    GPT4 = "gpt-4"
    GPT35 = "gpt-3.5-turbo"
    CLAUDE = "claude-3-sonnet"
    LLAMA = "llama-2-70b"


@dataclass
class FewShotExample:
    """Few-shot示例"""
    input: str
    output: str
    complexity: int  # 1-10
    format_type: str  # json/xml/markdown/text


@dataclass
class ModelCapability:
    """模型能力配置"""
    format_adherence: float  # 格式遵循能力 0-1
    fewshot_learning: float  # 少样本学习能力 0-1
    complex_reasoning: float  # 复杂推理能力 0-1
    chinese_understanding: float  # 中文理解能力 0-1
    context_window: int  # 上下文窗口大小


@dataclass
class TestResult:
    """测试结果"""
    name: str
    model: str
    passed: bool
    consistency_score: float
    details: Dict[str, Any]
    risk_level: str


# ==================== 模型能力配置（基于行业认知） ====================

MODEL_CAPABILITIES = {
    ModelType.GPT4: ModelCapability(
        format_adherence=0.95,
        fewshot_learning=0.95,
        complex_reasoning=0.95,
        chinese_understanding=0.92,
        context_window=128000
    ),
    ModelType.GPT35: ModelCapability(
        format_adherence=0.88,
        fewshot_learning=0.85,
        complex_reasoning=0.75,
        chinese_understanding=0.85,
        context_window=16000
    ),
    ModelType.CLAUDE: ModelCapability(
        format_adherence=0.92,
        fewshot_learning=0.90,
        complex_reasoning=0.92,
        chinese_understanding=0.90,
        context_window=200000
    ),
    ModelType.LLAMA: ModelCapability(
        format_adherence=0.70,
        fewshot_learning=0.75,
        complex_reasoning=0.65,
        chinese_understanding=0.60,
        context_window=8000
    ),
}


# ==================== Few-shot示例库 ====================

EXAMPLES = {
    "simple_json": [
        FewShotExample(
            input="评价：这家餐厅很棒",
            output='{"sentiment": "positive", "score": 0.9}',
            complexity=2,
            format_type="json"
        ),
        FewShotExample(
            input="评价：服务态度差",
            output='{"sentiment": "negative", "score": 0.8}',
            complexity=2,
            format_type="json"
        ),
    ],
    "complex_json": [
        FewShotExample(
            input="分析：产品功能丰富但学习曲线陡峭，适合专业用户",
            output='{"sentiment": "mixed", "pros": ["功能丰富"], "cons": ["学习曲线陡峭"], "target_user": "专业用户", "overall_score": 0.7}',
            complexity=7,
            format_type="json"
        ),
    ],
    "xml_format": [
        FewShotExample(
            input="提取实体：苹果公司发布了iPhone 15",
            output='<result><entity type="公司">苹果公司</entity><entity type="产品">iPhone 15</entity></result>',
            complexity=4,
            format_type="xml"
        ),
    ],
    "markdown_format": [
        FewShotExample(
            input="总结：本文讨论了AI在医疗领域的应用",
            output='## 总结\n- **主题**: AI医疗应用\n- **关键点**: 诊断辅助、药物研发',
            complexity=3,
            format_type="markdown"
        ),
    ],
    "chinese_complex": [
        FewShotExample(
            input="分析：这款产品性价比很高，虽然外观一般但功能强大，适合预算有限的学生群体",
            output='{"sentiment": "positive", "aspects": {"性价比": "高", "外观": "一般", "功能": "强大"}, "target": "学生群体", "recommendation": true}',
            complexity=6,
            format_type="json"
        ),
    ],
}


# ==================== 模拟模型响应 ====================

def mock_model_response(
    model: ModelType,
    examples: List[FewShotExample],
    query: str,
    expected_format: str = "json"
) -> Dict[str, Any]:
    """
    模拟不同模型的Few-shot响应
    基于模型能力和示例复杂度返回不同质量的结果
    """
    cap = MODEL_CAPABILITIES[model]
    
    # 计算示例整体复杂度
    avg_complexity = sum(e.complexity for e in examples) / len(examples) if examples else 5
    format_match = all(e.format_type == expected_format for e in examples)
    
    # 基础质量分
    base_quality = cap.fewshot_learning * 0.4 + cap.format_adherence * 0.3
    
    # 复杂度惩罚（弱模型处理复杂示例质量下降）
    complexity_penalty = max(0, (avg_complexity - 5) * (1 - cap.complex_reasoning) * 0.1)
    
    # 格式不匹配惩罚
    format_penalty = 0.2 if not format_match else 0
    
    # 中文理解惩罚
    chinese_penalty = 0.1 if any('\u4e00' <= c <= '\u9fff' for c in query) and cap.chinese_understanding < 0.8 else 0
    
    final_quality = max(0, base_quality - complexity_penalty - format_penalty - chinese_penalty)
    
    # 模拟输出
    output = {}
    
    # 格式遵循
    if expected_format == "json":
        if cap.format_adherence > 0.8 and final_quality > 0.6:
            output = {"sentiment": "positive", "confidence": round(final_quality, 2)}
        elif cap.format_adherence > 0.6:
            output = {"sentiment": "positive"}  # 缺少字段
        else:
            output = "sentiment: positive"  # 格式失效，返回文本
    
    elif expected_format == "xml":
        if cap.format_adherence > 0.8:
            output = "<result><entity>示例</entity></result>"
        else:
            output = "entity: 示例"  # XML格式失效
    
    elif expected_format == "markdown":
        if cap.format_adherence > 0.7:
            output = "## 结果\n- 要点1\n- 要点2"
        else:
            output = "结果：要点1，要点2"  # Markdown失效
    
    return {
        "output": output,
        "quality": final_quality,
        "format_followed": cap.format_adherence > 0.8,
        "model": model.value
    }


def calculate_consistency(outputs: List[Dict[str, Any]]) -> float:
    """计算多模型输出一致性"""
    if len(outputs) < 2:
        return 1.0
    
    # 简化：比较输出字符串的相似度
    similarities = []
    for i in range(len(outputs)):
        for j in range(i + 1, len(outputs)):
            out_i = json.dumps(outputs[i]["output"], sort_keys=True) if isinstance(outputs[i]["output"], dict) else str(outputs[i]["output"])
            out_j = json.dumps(outputs[j]["output"], sort_keys=True) if isinstance(outputs[j]["output"], dict) else str(outputs[j]["output"])
            sim = SequenceMatcher(None, out_i, out_j).ratio()
            similarities.append(sim)
    
    return sum(similarities) / len(similarities) if similarities else 1.0


def calculate_quality_decay(baseline_quality: float, target_quality: float) -> float:
    """计算质量衰减系数"""
    return target_quality / baseline_quality if baseline_quality > 0 else 0


# ==================== 测试执行函数 ====================

def test_cross_model_consistency() -> List[TestResult]:
    """测试1：跨模型一致性测试"""
    print("\n" + "="*70)
    print("🧪 测试1：跨模型一致性测试 (Cross-Model Consistency)")
    print("="*70)
    
    examples = EXAMPLES["simple_json"]
    query = "评价：这个产品质量很好"
    
    results = []
    outputs = []
    
    print("\n📊 同一示例集在不同模型上的表现：")
    for model in ModelType:
        response = mock_model_response(model, examples, query, "json")
        outputs.append(response)
        
        status = "✅" if response["format_followed"] else "❌"
        print(f"   {status} {model.value:20s}: 质量={response['quality']:.2f}, 格式遵循={response['format_followed']}")
        print(f"      输出: {response['output']}")
    
    # 计算一致性
    consistency = calculate_consistency(outputs)
    print(f"\n📈 跨模型一致性: {consistency:.2f}")
    
    # 识别最佳和最差模型
    best = max(outputs, key=lambda x: x["quality"])
    worst = min(outputs, key=lambda x: x["quality"])
    decay = calculate_quality_decay(best["quality"], worst["quality"])
    
    print(f"   最佳模型: {best['model']} (质量={best['quality']:.2f})")
    print(f"   最差模型: {worst['model']} (质量={worst['quality']:.2f})")
    print(f"   质量衰减系数: {decay:.2f}")
    
    passed = consistency > 0.85 and decay > 0.80
    
    return [TestResult(
        name="跨模型一致性测试",
        model="all",
        passed=passed,
        consistency_score=consistency,
        details={
            "consistency": consistency,
            "quality_decay": decay,
            "best_model": best["model"],
            "worst_model": worst["model"],
            "outputs": outputs
        },
        risk_level="L1" if consistency < 0.75 else "L2" if consistency < 0.85 else "L3"
    )]


def test_format_compatibility() -> List[TestResult]:
    """测试2：格式兼容性测试"""
    print("\n" + "="*70)
    print("🧪 测试2：格式兼容性测试 (Format Compatibility)")
    print("="*70)
    
    formats = ["json", "xml", "markdown"]
    test_cases = {
        "json": (EXAMPLES["simple_json"], "评价：测试"),
        "xml": (EXAMPLES["xml_format"], "提取实体：测试公司"),
        "markdown": (EXAMPLES["markdown_format"], "总结：测试文章"),
    }
    
    results = []
    
    for fmt in formats:
        print(f"\n📋 格式: {fmt.upper()}")
        examples, query = test_cases[fmt]
        
        format_follow_rates = []
        for model in ModelType:
            response = mock_model_response(model, examples, query, fmt)
            followed = response["format_followed"]
            format_follow_rates.append(1.0 if followed else 0.0)
            
            status = "✅" if followed else "❌"
            output_str = str(response['output'])
            print(f"   {status} {model.value:20s}: {output_str[:50]}...")
        
        follow_rate = sum(format_follow_rates) / len(format_follow_rates)
        print(f"\n   格式遵循率: {follow_rate:.1%}")
        
        passed = follow_rate > 0.90
        results.append(TestResult(
            name=f"{fmt.upper()}格式兼容性",
            model="all",
            passed=passed,
            consistency_score=follow_rate,
            details={"format": fmt, "follow_rate": follow_rate},
            risk_level="L1" if follow_rate < 0.80 else "L2" if follow_rate < 0.90 else "L3"
        ))
    
    return results


def test_complexity_migration() -> List[TestResult]:
    """测试3：复杂度分层迁移测试"""
    print("\n" + "="*70)
    print("🧪 测试3：复杂度分层迁移测试 (Complexity Migration)")
    print("="*70)
    
    complexity_levels = [
        ("简单", EXAMPLES["simple_json"], 2),
        ("中等", EXAMPLES["chinese_complex"], 6),
        ("复杂", EXAMPLES["complex_json"], 7),
    ]
    
    query = "分析：这是一个测试查询"
    results = []
    
    for level_name, examples, complexity in complexity_levels:
        print(f"\n📊 复杂度: {level_name} (评分: {complexity}/10)")
        
        model_qualities = {}
        for model in ModelType:
            cap = MODEL_CAPABILITIES[model]
            response = mock_model_response(model, examples, query, "json")
            model_qualities[model.value] = response["quality"]
            
            # 判断是否超出能力边界
            if complexity > 5 and cap.complex_reasoning < 0.8:
                warning = " ⚠️ 可能超出能力边界"
            else:
                warning = ""
            
            print(f"   {model.value:20s}: 质量={response['quality']:.2f}{warning}")
        
        # 计算质量方差（一致性指标）
        qualities = list(model_qualities.values())
        variance = sum((q - sum(qualities)/len(qualities))**2 for q in qualities) / len(qualities)
        
        print(f"   质量方差: {variance:.4f} {'✅ 稳定' if variance < 0.05 else '⚠️ 波动大'}")
        
        passed = variance < 0.05
        results.append(TestResult(
            name=f"{level_name}复杂度迁移",
            model="all",
            passed=passed,
            consistency_score=1 - variance * 10,
            details={
                "complexity": complexity,
                "qualities": model_qualities,
                "variance": variance
            },
            risk_level="L1" if variance > 0.1 else "L2" if variance > 0.05 else "L3"
        ))
    
    return results


def test_chinese_compatibility() -> List[TestResult]:
    """测试4：中文示例专项测试"""
    print("\n" + "="*70)
    print("🧪 测试4：中文示例专项测试 (Chinese Compatibility)")
    print("="*70)
    
    examples = EXAMPLES["chinese_complex"]
    query = "分析：这款手机电池续航一般但拍照效果很好"
    
    print("\n📊 中文复杂示例在各模型上的表现：")
    
    results = []
    chinese_scores = {}
    
    for model in ModelType:
        cap = MODEL_CAPABILITIES[model]
        response = mock_model_response(model, examples, query, "json")
        chinese_scores[model.value] = response["quality"]
        
        # 中文理解能力警告
        if cap.chinese_understanding < 0.7:
            warning = " 🔴 中文理解能力弱"
        elif cap.chinese_understanding < 0.85:
            warning = " 🟡 中文理解能力一般"
        else:
            warning = " 🟢 中文理解能力强"
        
        print(f"   {model.value:20s}: 质量={response['quality']:.2f}{warning}")
    
    # 计算中文一致性
    scores = list(chinese_scores.values())
    min_score = min(scores)
    max_score = max(scores)
    chinese_consistency = min_score / max_score if max_score > 0 else 0
    
    print(f"\n📈 中文示例一致性: {chinese_consistency:.2f}")
    print(f"   最低质量: {min_score:.2f}, 最高质量: {max_score:.2f}")
    
    passed = chinese_consistency > 0.80
    
    return [TestResult(
        name="中文示例兼容性",
        model="all",
        passed=passed,
        consistency_score=chinese_consistency,
        details={
            "chinese_scores": chinese_scores,
            "consistency": chinese_consistency,
            "min_score": min_score,
            "max_score": max_score
        },
        risk_level="L1" if chinese_consistency < 0.70 else "L2" if chinese_consistency < 0.80 else "L3"
    )]


def test_fallback_strategy() -> List[TestResult]:
    """测试5：降级策略验证"""
    print("\n" + "="*70)
    print("🧪 测试5：降级策略验证 (Fallback Strategy)")
    print("="*70)
    
    # 模拟弱模型（Llama）遇到复杂示例的场景
    complex_examples = EXAMPLES["complex_json"]
    query = "分析：这是一个复杂的多维度评价"
    
    print("\n📊 弱模型(Llama)处理复杂示例的降级策略：")
    
    # 策略1：直接处理
    direct_response = mock_model_response(ModelType.LLAMA, complex_examples, query, "json")
    print(f"\n   策略1 - 直接处理:")
    print(f"      输出: {direct_response['output']}")
    print(f"      质量: {direct_response['quality']:.2f}")
    print(f"      格式遵循: {direct_response['format_followed']}")
    
    # 策略2：简化示例
    simple_examples = EXAMPLES["simple_json"]
    simplified_response = mock_model_response(ModelType.LLAMA, simple_examples, query, "json")
    print(f"\n   策略2 - 使用简化示例:")
    print(f"      输出: {simplified_response['output']}")
    print(f"      质量: {simplified_response['quality']:.2f}")
    print(f"      格式遵循: {simplified_response['format_followed']}")
    
    # 策略3：0-shot + 明确指令
    zero_shot_response = mock_model_response(ModelType.LLAMA, [], query, "json")
    print(f"\n   策略3 - 0-shot + 明确指令:")
    print(f"      输出: {zero_shot_response['output']}")
    print(f"      质量: {zero_shot_response['quality']:.2f}")
    
    # 评估最佳策略
    strategies = [
        ("直接处理", direct_response['quality']),
        ("简化示例", simplified_response['quality']),
        ("0-shot", zero_shot_response['quality']),
    ]
    best_strategy = max(strategies, key=lambda x: x[1])
    
    print(f"\n✅ 最佳策略: {best_strategy[0]} (质量={best_strategy[1]:.2f})")
    
    # 降级有效性判断
    fallback_effective = simplified_response['quality'] > direct_response['quality'] or zero_shot_response['quality'] > direct_response['quality']
    
    passed = fallback_effective
    
    return [TestResult(
        name="降级策略有效性",
        model="llama-2-70b",
        passed=passed,
        consistency_score=best_strategy[1],
        details={
            "strategies": {name: quality for name, quality in strategies},
            "best_strategy": best_strategy[0],
            "fallback_effective": fallback_effective
        },
        risk_level="L2" if not fallback_effective else "L3"
    )]


# ==================== 主测试入口 ====================

def run_all_tests():
    """运行所有跨模型迁移测试"""
    print("\n" + "="*80)
    print("🚀 AI QA System Test - Day 18: 跨模型Few-shot迁移测试")
    print("="*80)
    print("\n测试架构师视角：验证同一套Few-shot示例在不同LLM模型上的迁移效果")
    print("测试模型: GPT-4, GPT-3.5, Claude-3, Llama-2-70b")
    
    # 执行所有测试
    all_results = []
    all_results.extend(test_cross_model_consistency())
    all_results.extend(test_format_compatibility())
    all_results.extend(test_complexity_migration())
    all_results.extend(test_chinese_compatibility())
    all_results.extend(test_fallback_strategy())
    
    # 汇总报告
    print("\n" + "="*80)
    print("📋 测试汇总报告")
    print("="*80)
    
    passed_count = sum(1 for r in all_results if r.passed)
    total_count = len(all_results)
    
    print(f"\n✅ 通过: {passed_count}/{total_count}")
    print(f"❌ 失败: {total_count - passed_count}/{total_count}")
    
    print("\n📊 各测试项结果:")
    for r in all_results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        risk_icon = "🔴" if r.risk_level == "L1" else "🟡" if r.risk_level == "L2" else "🟢"
        print(f"   {status} [{risk_icon} {r.risk_level}] {r.name}: 一致性={r.consistency_score:.2f}")
    
    # 风险汇总
    l1_count = sum(1 for r in all_results if r.risk_level == "L1")
    l2_count = sum(1 for r in all_results if r.risk_level == "L2")
    l3_count = sum(1 for r in all_results if r.risk_level == "L3")
    
    print(f"\n⚠️ 风险分布:")
    print(f"   🔴 L1 (高风险): {l1_count}项")
    print(f"   🟡 L2 (中风险): {l2_count}项")
    print(f"   🟢 L3 (低风险): {l3_count}项")
    
    # 关键发现
    print("\n🔍 关键发现:")
    
    # 找出一致性最低的模型组合
    consistency_result = next((r for r in all_results if r.name == "跨模型一致性测试"), None)
    if consistency_result:
        print(f"   • 跨模型一致性: {consistency_result.consistency_score:.2f}")
        print(f"     最佳模型: {consistency_result.details.get('best_model')}")
        print(f"     最差模型: {consistency_result.details.get('worst_model')}")
    
    # 中文兼容性
    chinese_result = next((r for r in all_results if r.name == "中文示例兼容性"), None)
    if chinese_result:
        print(f"   • 中文示例一致性: {chinese_result.consistency_score:.2f}")
    
    # 格式兼容性
    json_result = next((r for r in all_results if r.name == "JSON格式兼容性"), None)
    if json_result:
        print(f"   • JSON格式遵循率: {json_result.consistency_score:.1%}")
    
    # 降级策略
    fallback_result = next((r for r in all_results if r.name == "降级策略有效性"), None)
    if fallback_result:
        print(f"   • 最佳降级策略: {fallback_result.details.get('best_strategy')}")
    
    print("\n" + "="*80)
    print("✅ 测试执行完毕，请将上方日志发给 Trae 生成报告。")
    print("="*80)
    
    return all_results


if __name__ == "__main__":
    run_all_tests()
