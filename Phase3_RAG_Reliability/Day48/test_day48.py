"""
Day 48: LLM-as-a-Judge 偏见识别与缓解策略
目标：检测评委模型的各类偏见，验证缓解策略的有效性
测试架构师视角：评委模型的偏见会让评估结果系统性偏离真实质量
难度级别：实战 - 综合应用偏见检测与缓解技术
"""

import json
import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from enum import Enum


class RiskLevel(Enum):
    L1 = "L1-高风险"
    L2 = "L2-中风险"
    L3 = "L3-低风险"


@dataclass
class TestResult:
    name: str
    passed: bool
    score: float
    risk_level: RiskLevel
    details: Dict[str, Any] = field(default_factory=dict)


# 模拟评委模型的偏见配置
JUDGE_BIAS_PROFILES = {
    "gpt4": {
        "position_bias": 0.15,      # 位置偏见强度
        "verbosity_bias": 0.20,     # 冗长偏见强度
        "self_preference": 0.10,    # 自我增强偏见
        "domain_bias": {
            "tech": 0.0,
            "science": 0.0,
            "arts": -0.1,
            "sports": -0.15
        }
    },
    "claude3": {
        "position_bias": 0.10,
        "verbosity_bias": 0.15,
        "self_preference": 0.08,
        "domain_bias": {
            "tech": 0.0,
            "science": 0.0,
            "arts": 0.0,
            "sports": -0.05
        }
    },
    "gpt35": {
        "position_bias": 0.25,
        "verbosity_bias": 0.35,
        "self_preference": 0.20,
        "domain_bias": {
            "tech": 0.05,
            "science": -0.05,
            "arts": -0.1,
            "sports": -0.1
        }
    }
}


# 测试用例：成对比较
PAIRWISE_TEST_CASES = [
    {
        "id": 1,
        "question": "解释机器学习",
        "answer_a": {
            "text": "机器学习是AI的一个分支，使计算机能够从数据中学习。",
            "length": 30,
            "source": "model_a",
            "true_quality": 7.5
        },
        "answer_b": {
            "text": "机器学习是人工智能的核心技术之一，它使计算机系统能够通过数据和经验自动改进性能，无需显式编程。主要类型包括监督学习、无监督学习和强化学习。",
            "length": 80,
            "source": "model_b",
            "true_quality": 8.5
        }
    },
    {
        "id": 2,
        "question": "什么是区块链",
        "answer_a": {
            "text": "区块链是一种分布式账本技术，通过密码学确保数据安全和不可篡改。每个区块包含多笔交易，按时间顺序链接形成链条。",
            "length": 75,
            "source": "model_a",
            "true_quality": 8.0
        },
        "answer_b": {
            "text": "区块链是分布式账本。",
            "length": 12,
            "source": "model_b",
            "true_quality": 5.0
        }
    },
    {
        "id": 3,
        "question": "描述印象派绘画",
        "answer_a": {
            "text": "印象派是19世纪的艺术运动，强调光线和色彩的瞬间效果。",
            "length": 35,
            "source": "model_a",
            "true_quality": 7.0
        },
        "answer_b": {
            "text": "印象派绘画注重捕捉光线变化的瞬间印象，使用鲜明的色彩和松散的笔触。代表画家包括莫奈、雷诺阿和德加。",
            "length": 70,
            "source": "model_b",
            "true_quality": 8.0
        }
    }
]


# 不同领域的测试样本
DOMAIN_TEST_CASES = {
    "tech": [
        {"question": "什么是API？", "answer": "API是应用程序接口，允许不同软件组件相互通信。", "quality": 8},
        {"question": "解释云计算", "answer": "云计算是通过互联网提供计算服务。", "quality": 7}
    ],
    "science": [
        {"question": "什么是DNA？", "answer": "DNA是脱氧核糖核酸，携带遗传信息。", "quality": 8},
        {"question": "解释光合作用", "answer": "植物利用光能将CO2和水转化为葡萄糖。", "quality": 7}
    ],
    "arts": [
        {"question": "什么是文艺复兴？", "answer": "文艺复兴是14-17世纪欧洲的文化运动。", "quality": 7},
        {"question": "描述巴洛克艺术", "answer": "巴洛克艺术强调戏剧性、动感和华丽。", "quality": 8}
    ],
    "sports": [
        {"question": "足球的基本规则", "answer": "两队各11人，将球踢入对方球门得分。", "quality": 7},
        {"question": "什么是大满贯？", "answer": "在网球中，大满贯指赢得四大公开赛。", "quality": 8}
    ]
}


def mock_judge_pairwise(answer_a: Dict, answer_b: Dict, judge_id: str, order: str = "ab") -> Dict:
    """
    模拟评委进行成对比较
    考虑各种偏见因素
    """
    bias = JUDGE_BIAS_PROFILES[judge_id]
    
    # 基础评分基于真实质量
    quality_a = answer_a["true_quality"]
    quality_b = answer_b["true_quality"]
    
    # 应用位置偏见
    if order == "ab":
        # A在前，B在后
        quality_a += bias["position_bias"] * random.uniform(0.5, 1.5)
        quality_b -= bias["position_bias"] * random.uniform(0.5, 1.5) * 0.5
    else:
        # B在前，A在后
        quality_b += bias["position_bias"] * random.uniform(0.5, 1.5)
        quality_a -= bias["position_bias"] * random.uniform(0.5, 1.5) * 0.5
    
    # 应用冗长偏见
    len_a, len_b = answer_a["length"], answer_b["length"]
    if len_a > len_b:
        quality_a += bias["verbosity_bias"] * math.log(len_a / len_b + 1)
    else:
        quality_b += bias["verbosity_bias"] * math.log(len_b / len_a + 1)
    
    # 添加随机噪声
    quality_a += random.gauss(0, 0.5)
    quality_b += random.gauss(0, 0.5)
    
    # 判断胜者
    if quality_a > quality_b:
        winner = "A"
        margin = quality_a - quality_b
    else:
        winner = "B"
        margin = quality_b - quality_a
    
    return {
        "winner": winner,
        "margin": round(margin, 2),
        "score_a": round(quality_a, 2),
        "score_b": round(quality_b, 2),
        "order": order
    }


def mock_judge_single(answer: Dict, judge_id: str, domain: str = "general") -> float:
    """模拟评委对单个回答评分"""
    bias = JUDGE_BIAS_PROFILES[judge_id]
    
    base_score = answer.get("quality", 7.0)
    
    # 应用冗长偏见
    length = answer.get("length", 50)
    base_score += bias["verbosity_bias"] * math.log(length / 50 + 1)
    
    # 应用领域偏见
    if domain in bias["domain_bias"]:
        base_score += bias["domain_bias"][domain]
    
    # 添加噪声
    base_score += random.gauss(0, 0.5)
    
    return round(max(1, min(10, base_score)), 2)


def calculate_correlation(x: List[float], y: List[float]) -> float:
    """计算皮尔逊相关系数"""
    n = len(x)
    if n == 0:
        return 0.0
    
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denominator = math.sqrt(sum((xi - mean_x) ** 2 for xi in x)) * math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
    
    if denominator == 0:
        return 0.0
    
    return round(numerator / denominator, 3)


def test_position_bias() -> TestResult:
    """
    测试1: 位置偏见检测
    交换回答顺序，观察评分变化
    """
    print("\n" + "="*70)
    print("🧪 测试1: 位置偏见检测")
    print("="*70)
    print("目标：检测评委模型是否存在位置偏见\n")
    
    judge_id = "gpt35"  # 使用偏见较强的模型
    
    print("📊 顺序交换实验:")
    print(f"{'用例':<6} {'真实质量(A/B)':<18} {'AB顺序胜者':<12} {'BA顺序胜者':<12} {'一致？':<8}")
    print("-" * 65)
    
    consistency_count = 0
    flip_cases = []
    
    for case in PAIRWISE_TEST_CASES:
        # 顺序 A-B
        result_ab = mock_judge_pairwise(case["answer_a"], case["answer_b"], judge_id, "ab")
        # 顺序 B-A
        result_ba = mock_judge_pairwise(case["answer_a"], case["answer_b"], judge_id, "ba")
        
        consistent = result_ab["winner"] == result_ba["winner"]
        if consistent:
            consistency_count += 1
        else:
            flip_cases.append(case["id"])
        
        true_quality = f"{case['answer_a']['true_quality']:.1f}/{case['answer_b']['true_quality']:.1f}"
        status = "✓" if consistent else "✗"
        
        print(f"{case['id']:<6} {true_quality:<18} {result_ab['winner']:<12} {result_ba['winner']:<12} {status:<8}")
    
    consistency_rate = consistency_count / len(PAIRWISE_TEST_CASES)
    position_bias_rate = 1 - consistency_rate
    
    print(f"\n📈 位置偏见分析:")
    print(f"   一致性率: {consistency_rate*100:.1f}%")
    print(f"   位置偏见率: {position_bias_rate*100:.1f}%")
    
    if flip_cases:
        print(f"   ⚠️  顺序翻转用例: {flip_cases}")
    
    # 缓解策略建议
    print(f"\n🔧 缓解策略:")
    if position_bias_rate > 0.1:
        print("   1. 多次评估取平均（交换顺序）")
        print("   2. 随机化回答顺序")
        print("   3. 使用位置平衡的平均分")
    else:
        print("   ✅ 位置偏见在可接受范围内")
    
    passed = position_bias_rate < 0.15
    score = 1 - position_bias_rate
    
    return TestResult(
        name="位置偏见检测",
        passed=passed,
        score=round(score, 2),
        risk_level=RiskLevel.L2 if position_bias_rate > 0.2 else RiskLevel.L3,
        details={
            "consistency_rate": consistency_rate,
            "position_bias_rate": position_bias_rate,
            "flip_cases": flip_cases
        }
    )


def test_verbosity_bias() -> TestResult:
    """
    测试2: 冗长偏见检测
    对比不同长度回答的评分差异
    """
    print("\n" + "="*70)
    print("🧪 测试2: 冗长偏见检测")
    print("="*70)
    print("目标：检测评委是否偏好更长的回答\n")
    
    # 生成不同长度但相同质量的回答
    test_answers = []
    base_quality = 7.0
    
    for length in [20, 50, 100, 200, 500]:
        test_answers.append({
            "length": length,
            "quality": base_quality,  # 真实质量相同
            "text": "内容 " * (length // 5)
        })
    
    judge_id = "gpt35"
    
    print("📊 长度-评分相关性测试:")
    print(f"{'长度(字)':<10} {'真实质量':<10} {'评委评分':<10} {'偏差':<10}")
    print("-" * 45)
    
    lengths = []
    scores = []
    
    for ans in test_answers:
        score = mock_judge_single(ans, judge_id)
        lengths.append(ans["length"])
        scores.append(score)
        bias = score - ans["quality"]
        print(f"{ans['length']:<10} {ans['quality']:<10.1f} {score:<10.1f} {bias:+.1f}")
    
    # 计算相关性
    correlation = calculate_correlation(lengths, scores)
    
    print(f"\n📈 冗长偏见分析:")
    print(f"   长度-评分相关系数: {correlation:.3f}")
    
    if abs(correlation) > 0.3:
        print(f"   ⚠️  检测到显著冗长偏见")
    else:
        print(f"   ✅ 冗长偏见不显著")
    
    # 缓解策略
    print(f"\n🔧 缓解策略:")
    print("   1. 信息密度评估：评分 / log(长度)")
    print("   2. 长度标准化：对超长回答施加惩罚")
    print("   3. 多维度评估：区分信息量和冗余度")
    
    passed = abs(correlation) < 0.4
    score = 1 - abs(correlation)
    
    return TestResult(
        name="冗长偏见检测",
        passed=passed,
        score=round(score, 2),
        risk_level=RiskLevel.L2 if abs(correlation) > 0.5 else RiskLevel.L3,
        details={"correlation": correlation, "lengths": lengths, "scores": scores}
    )


def test_self_preference_bias() -> TestResult:
    """
    测试3: 自我增强偏见检测
    测试评委对自生成内容的偏好
    """
    print("\n" + "="*70)
    print("🧪 测试3: 自我增强偏见检测")
    print("="*70)
    print("目标：检测评委是否偏好与自己风格相似的内容\n")
    
    # 模拟不同来源的回答
    answers = [
        {"text": "GPT风格回答：详细、结构化", "source": "gpt", "length": 60, "quality": 7.5},
        {"text": "Claude风格回答：平衡、安全", "source": "claude", "length": 55, "quality": 7.5},
        {"text": "人类风格回答：自然、口语化", "source": "human", "length": 50, "quality": 7.5},
    ]
    
    print("📊 来源偏好测试:")
    print(f"{'评委':<10} {'GPT回答':<10} {'Claude回答':<12} {'人类回答':<10} {'自偏好率':<10}")
    print("-" * 60)
    
    self_preference_results = {}
    
    for judge_id in ["gpt4", "claude3"]:
        scores = {}
        for ans in answers:
            score = mock_judge_single(ans, judge_id)
            scores[ans["source"]] = score
        
        # 计算自偏好率
        if judge_id == "gpt4":
            self_score = scores["gpt"]
            others_avg = (scores["claude"] + scores["human"]) / 2
        else:  # claude3
            self_score = scores["claude"]
            others_avg = (scores["gpt"] + scores["human"]) / 2
        
        preference_rate = (self_score - others_avg) / 10  # 归一化
        self_preference_results[judge_id] = {
            "scores": scores,
            "preference_rate": preference_rate
        }
        
        print(f"{judge_id:<10} {scores['gpt']:<10.1f} {scores['claude']:<12.1f} {scores['human']:<10.1f} {preference_rate*100:+.1f}%")
    
    # 分析
    avg_preference = sum(r["preference_rate"] for r in self_preference_results.values()) / len(self_preference_results)
    
    print(f"\n📈 自我增强偏见分析:")
    print(f"   平均自偏好率: {avg_preference*100:+.1f}%")
    
    if avg_preference > 0.1:
        print(f"   ⚠️  检测到显著自我增强偏见")
    else:
        print(f"   ✅ 自我增强偏见不显著")
    
    # 缓解策略
    print(f"\n🔧 缓解策略:")
    print("   1. 盲测：隐藏回答来源信息")
    print("   2. 多评委交叉验证")
    print("   3. 去除最高最低分，取平均")
    print("   4. 定期使用人工标注校准")
    
    passed = avg_preference < 0.15
    score = 1 - avg_preference
    
    return TestResult(
        name="自我增强偏见检测",
        passed=passed,
        score=round(score, 2),
        risk_level=RiskLevel.L2 if avg_preference > 0.2 else RiskLevel.L3,
        details={"self_preference_results": self_preference_results, "avg_preference": avg_preference}
    )


def test_domain_bias() -> TestResult:
    """
    测试4: 领域偏见检测
    测试评委在不同领域的表现差异
    """
    print("\n" + "="*70)
    print("🧪 测试4: 领域偏见检测")
    print("="*70)
    print("目标：检测评委是否存在领域偏见\n")
    
    judge_id = "gpt35"
    
    print("📊 跨领域评分对比:")
    print(f"{'领域':<12} {'样本数':<8} {'平均评分':<10} {'真实质量':<10} {'偏差':<10}")
    print("-" * 55)
    
    domain_scores = {}
    
    for domain, cases in DOMAIN_TEST_CASES.items():
        scores = []
        true_qualities = []
        
        for case in cases:
            score = mock_judge_single(case, judge_id, domain)
            scores.append(score)
            true_qualities.append(case["quality"])
        
        avg_score = sum(scores) / len(scores)
        avg_true = sum(true_qualities) / len(true_qualities)
        bias = avg_score - avg_true
        
        domain_scores[domain] = {
            "avg_score": avg_score,
            "avg_true": avg_true,
            "bias": bias
        }
        
        print(f"{domain:<12} {len(cases):<8} {avg_score:<10.1f} {avg_true:<10.1f} {bias:+.1f}")
    
    # 计算领域间差异
    biases = [abs(s["bias"]) for s in domain_scores.values()]
    max_bias = max(biases)
    avg_bias = sum(biases) / len(biases)
    
    print(f"\n📈 领域偏见分析:")
    print(f"   最大领域偏差: {max_bias:.1f}分")
    print(f"   平均领域偏差: {avg_bias:.1f}分")
    
    if max_bias > 0.5:
        print(f"   ⚠️  检测到显著领域偏见")
        most_biased = max(domain_scores.items(), key=lambda x: abs(x[1]["bias"]))
        print(f"   最受影响领域: {most_biased[0]} (偏差: {most_biased[1]['bias']:+.1f})")
    else:
        print(f"   ✅ 领域偏见不显著")
    
    # 缓解策略
    print(f"\n🔧 缓解策略:")
    print("   1. 领域专家校准")
    print("   2. 领域特定评分标准")
    print("   3. 分层评估：不同领域使用不同评委")
    print("   4. 领域权重调整")
    
    passed = max_bias < 0.8
    score = 1 - max_bias / 3
    
    return TestResult(
        name="领域偏见检测",
        passed=passed,
        score=round(max(0, score), 2),
        risk_level=RiskLevel.L2 if max_bias > 1.0 else RiskLevel.L3,
        details={"domain_scores": domain_scores, "max_bias": max_bias}
    )


def test_bias_mitigation_strategies() -> TestResult:
    """
    测试5: 偏见缓解策略验证
    测试各种缓解技术的有效性
    """
    print("\n" + "="*70)
    print("🧪 测试5: 偏见缓解策略验证")
    print("="*70)
    print("目标：验证偏见缓解技术的有效性\n")
    
    # 原始偏见水平（模拟）
    original_biases = {
        "position": 0.20,
        "verbosity": 0.30,
        "self_preference": 0.15
    }
    
    # 缓解策略效果
    mitigation_strategies = {
        "无缓解": {
            "position": 1.0,
            "verbosity": 1.0,
            "self_preference": 1.0
        },
        "位置平衡": {
            "position": 0.3,  # 减少70%
            "verbosity": 1.0,
            "self_preference": 1.0
        },
        "长度标准化": {
            "position": 1.0,
            "verbosity": 0.4,  # 减少60%
            "self_preference": 1.0
        },
        "盲测+多评委": {
            "position": 0.8,
            "verbosity": 0.9,
            "self_preference": 0.2  # 减少80%
        },
        "综合策略": {
            "position": 0.25,
            "verbosity": 0.35,
            "self_preference": 0.15
        }
    }
    
    print("📊 缓解策略效果对比:")
    print(f"{'策略':<15} {'位置偏见':<12} {'冗长偏见':<12} {'自偏好':<12} {'综合改善':<10}")
    print("-" * 65)
    
    strategy_results = {}
    
    for strategy_name, effectiveness in mitigation_strategies.items():
        remaining_biases = {
            "position": original_biases["position"] * effectiveness["position"],
            "verbosity": original_biases["verbosity"] * effectiveness["verbosity"],
            "self_preference": original_biases["self_preference"] * effectiveness["self_preference"]
        }
        
        total_original = sum(original_biases.values())
        total_remaining = sum(remaining_biases.values())
        improvement = (total_original - total_remaining) / total_original
        
        strategy_results[strategy_name] = {
            "remaining_biases": remaining_biases,
            "improvement": improvement
        }
        
        print(f"{strategy_name:<15} {remaining_biases['position']:<12.2f} "
              f"{remaining_biases['verbosity']:<12.2f} {remaining_biases['self_preference']:<12.2f} "
              f"{improvement*100:<9.0f}%")
    
    # 推荐策略
    best_strategy = max(strategy_results.items(), key=lambda x: x[1]["improvement"])
    
    print(f"\n🏆 推荐策略: {best_strategy[0]}")
    print(f"   综合改善: {best_strategy[1]['improvement']*100:.0f}%")
    
    # 实施建议
    print(f"\n🔧 实施建议:")
    print("   1. 立即实施:")
    print("      - 位置平衡：所有成对比较交换顺序进行")
    print("      - 长度标准化：评分时考虑信息密度")
    print("   2. 中期实施:")
    print("      - 多评委系统：至少3个独立评委")
    print("      - 盲测机制：隐藏回答来源")
    print("   3. 长期监控:")
    print("      - 建立偏见监控仪表盘")
    print("      - 定期人工审核校准")
    
    passed = best_strategy[1]["improvement"] > 0.5
    score = best_strategy[1]["improvement"]
    
    return TestResult(
        name="偏见缓解策略验证",
        passed=passed,
        score=round(score, 2),
        risk_level=RiskLevel.L3,
        details={"strategy_results": strategy_results, "best_strategy": best_strategy[0]}
    )


def test_comprehensive_bias_assessment() -> TestResult:
    """
    测试6: 综合偏见评估
    多维度偏见检测与量化
    """
    print("\n" + "="*70)
    print("🧪 测试6: 综合偏见评估")
    print("="*70)
    print("目标：全面评估评委模型的偏见状况\n")
    
    # 综合偏见评分卡
    bias_dimensions = {
        "位置偏见": {"score": 0.15, "threshold": 0.10, "weight": 0.25},
        "冗长偏见": {"score": 0.25, "threshold": 0.20, "weight": 0.25},
        "自我偏好": {"score": 0.12, "threshold": 0.15, "weight": 0.20},
        "领域偏见": {"score": 0.20, "threshold": 0.15, "weight": 0.20},
        "语言偏见": {"score": 0.08, "threshold": 0.10, "weight": 0.10}
    }
    
    print("📊 偏见评分卡:")
    print(f"{'偏见维度':<12} {'当前水平':<10} {'阈值':<10} {'状态':<8} {'权重':<8}")
    print("-" * 55)
    
    total_weighted_bias = 0
    high_risk_biases = []
    
    for dimension, data in bias_dimensions.items():
        status = "⚠️ 超标" if data["score"] > data["threshold"] else "✅ 正常"
        weighted = data["score"] * data["weight"]
        total_weighted_bias += weighted
        
        if data["score"] > data["threshold"]:
            high_risk_biases.append(dimension)
        
        print(f"{dimension:<12} {data['score']:<10.2f} {data['threshold']:<10.2f} {status:<8} {data['weight']:<8.0%}")
    
    # 综合评分
    overall_score = 1 - total_weighted_bias
    
    print(f"\n📈 综合评估:")
    print(f"   加权偏见指数: {total_weighted_bias:.3f}")
    print(f"   综合健康度: {overall_score*100:.1f}%")
    
    if high_risk_biases:
        print(f"   ⚠️  高风险偏见维度: {', '.join(high_risk_biases)}")
    else:
        print(f"   ✅ 所有偏见维度均在可控范围内")
    
    # 风险等级判定
    if overall_score > 0.8:
        risk_level = "低风险"
        risk_enum = RiskLevel.L3
    elif overall_score > 0.6:
        risk_level = "中风险"
        risk_enum = RiskLevel.L2
    else:
        risk_level = "高风险"
        risk_enum = RiskLevel.L1
    
    print(f"   风险等级: {risk_level}")
    
    # 治理建议
    print(f"\n🔧 偏见治理路线图:")
    print("   Phase 1 (1-2周): 实施位置平衡和长度标准化")
    print("   Phase 2 (1个月): 部署多评委盲测系统")
    print("   Phase 3 (持续): 建立偏见监控和定期校准机制")
    
    passed = overall_score > 0.7
    
    return TestResult(
        name="综合偏见评估",
        passed=passed,
        score=round(overall_score, 2),
        risk_level=risk_enum,
        details={
            "bias_dimensions": bias_dimensions,
            "high_risk_biases": high_risk_biases,
            "overall_score": overall_score
        }
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 Day 48 测试汇总报告")
    print("="*70)
    
    print(f"\n{'测试项':<25} {'状态':<8} {'得分':<8} {'风险等级':<12}")
    print("-" * 60)
    
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{r.name:<25} {status:<8} {r.score:<8.2f} {r.risk_level.value:<12}")
    
    # 统计
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    avg_score = sum(r.score for r in results) / total
    
    high_risk = sum(1 for r in results if r.risk_level == RiskLevel.L1)
    medium_risk = sum(1 for r in results if r.risk_level == RiskLevel.L2)
    
    print(f"\n📈 统计:")
    print(f"   通过: {passed}/{total}")
    print(f"   平均得分: {avg_score:.2f}")
    print(f"   高风险项: {high_risk}个")
    print(f"   中风险项: {medium_risk}个")
    
    if high_risk > 0:
        print(f"\n⚠️  关键风险提醒:")
        for r in results:
            if r.risk_level == RiskLevel.L1:
                print(f"   - {r.name}: 需要立即处理")
    
    print("\n" + "="*70)
    print("💡 Day 46-48 LLM-as-a-Judge 学习路径总结:")
    print("="*70)
    print("\n📚 已完成:")
    print("   Day 46: 评委模型选型与基准校准")
    print("          └─ 模型能力对比、人机一致性、成本效益")
    print("   Day 47: 评估Prompt设计与评分标准")
    print("          └─ 标准清晰度、维度完整性、格式稳定性")
    print("   Day 48: 偏见识别与缓解策略")
    print("          └─ 位置/冗长/自我/领域偏见检测与缓解")
    print("\n🎯 关键产出:")
    print("   1. 评委模型选型决策框架")
    print("   2. 高质量评估Prompt模板")
    print("   3. 偏见检测与缓解方案")
    print("\n🚀 下一步:")
    print("   进入 Day 49: A/B测试与线上效果监控")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 48")
    print("   LLM-as-a-Judge 偏见识别与缓解策略")
    print("="*70)
    
    random.seed(48)  # 固定随机种子保证可重复性
    
    results = [
        test_position_bias(),
        test_verbosity_bias(),
        test_self_preference_bias(),
        test_domain_bias(),
        test_bias_mitigation_strategies(),
        test_comprehensive_bias_assessment(),
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
