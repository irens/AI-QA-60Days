"""
Day 46: LLM-as-a-Judge 评委模型选型与基准校准
目标：测试不同评委模型的能力差异，建立基准校准体系
测试架构师视角：评委模型选错，整个评估体系就崩塌了
难度级别：基础 - 建立评委模型选型的基础认知
"""

import json
import random
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


@dataclass
class JudgeModel:
    """评委模型定义"""
    name: str
    capability_level: int  # 1-5
    cost_per_call: float  # 美元/千次调用
    latency_ms: int
    bias_profile: Dict[str, float]  # 各类偏见倾向


# 定义常见评委模型
JUDGE_MODELS = {
    "gpt4": JudgeModel("GPT-4", 5, 0.03, 2000, {"position": 0.1, "verbosity": 0.15, "self": 0.05}),
    "claude3": JudgeModel("Claude-3", 4, 0.025, 1800, {"position": 0.12, "verbosity": 0.08, "self": 0.03}),
    "gpt35": JudgeModel("GPT-3.5", 3, 0.002, 800, {"position": 0.25, "verbosity": 0.30, "self": 0.10}),
    "local7b": JudgeModel("Local-7B", 2, 0.0001, 500, {"position": 0.35, "verbosity": 0.40, "self": 0.20}),
    "domain_expert": JudgeModel("Domain-Expert", 4, 0.015, 1200, {"position": 0.15, "verbosity": 0.12, "self": 0.08}),
}


# 测试数据集：问答对及人工标注质量标签
EVALUATION_DATASET = [
    {
        "id": 1,
        "question": "解释量子计算的基本原理",
        "answer": "量子计算利用量子叠加和纠缠原理，使量子比特能同时处于多个状态，从而实现并行计算。",
        "human_label": "excellent",  # excellent/good/fair/poor
        "domain": "science",
        "complexity": "high"
    },
    {
        "id": 2,
        "question": "什么是机器学习？",
        "answer": "机器学习是AI的一个分支，让计算机从数据中学习规律。",
        "human_label": "good",
        "domain": "technology",
        "complexity": "medium"
    },
    {
        "id": 3,
        "question": "如何制作蛋糕？",
        "answer": "蛋糕制作需要面粉、糖、鸡蛋和黄油，混合后烘烤。",
        "human_label": "fair",
        "domain": "cooking",
        "complexity": "low"
    },
    {
        "id": 4,
        "question": "解释区块链共识机制",
        "answer": "区块链共识机制是分布式系统中节点就数据状态达成一致的协议，常见有PoW和PoS。",
        "human_label": "good",
        "domain": "technology",
        "complexity": "high"
    },
    {
        "id": 5,
        "question": "推荐几本好书",
        "answer": "推荐《百年孤独》《1984》《三体》，涵盖魔幻现实、反乌托邦和科幻题材。",
        "human_label": "excellent",
        "domain": "general",
        "complexity": "medium"
    },
]


def mock_judge_score(judge: JudgeModel, item: Dict, criteria: str = "overall") -> Dict:
    """
    模拟评委模型评分
    基于模型能力等级和偏见倾向生成评分
    """
    base_quality = {"excellent": 9, "good": 7, "fair": 5, "poor": 3}[item["human_label"]]
    
    # 能力影响：能力越低，评分噪声越大
    noise = random.gauss(0, (6 - judge.capability_level) * 0.5)
    
    # 领域适配：专业模型在特定领域表现更好
    domain_bonus = 0
    if judge.name == "Domain-Expert" and item["domain"] in ["science", "technology"]:
        domain_bonus = 1.5
    
    # 复杂度影响：低能力模型在高复杂度任务上表现更差
    complexity_penalty = 0
    if item["complexity"] == "high" and judge.capability_level < 4:
        complexity_penalty = random.uniform(0.5, 2.0)
    
    score = max(1, min(10, base_quality + noise + domain_bonus - complexity_penalty))
    
    # 模拟评分置信度
    confidence = judge.capability_level / 5.0 + random.uniform(-0.1, 0.1)
    confidence = max(0.3, min(1.0, confidence))
    
    return {
        "score": round(score, 2),
        "confidence": round(confidence, 2),
        "criteria": criteria,
        "judge": judge.name
    }


def calculate_cohen_kappa(labels1: List, labels2: List) -> float:
    """计算Cohen's Kappa一致性系数"""
    n = len(labels1)
    if n == 0:
        return 0.0
    
    # 转换为分类标签
    label_map = {"excellent": 3, "good": 2, "fair": 1, "poor": 0}
    l1 = [label_map.get(str(l).lower(), 1) for l in labels1]
    l2 = [label_map.get(str(l).lower(), 1) for l in labels2]
    
    # 观察一致性
    agreements = sum(1 for a, b in zip(l1, l2) if a == b)
    po = agreements / n
    
    # 期望一致性（简化计算）
    pe = 0.25  # 假设四类均匀分布
    
    # Kappa
    kappa = (po - pe) / (1 - pe) if (1 - pe) > 0 else 0
    return round(kappa, 3)


def test_judge_capability_baseline() -> TestResult:
    """
    测试1: 评委能力基线测试
    对比不同模型在标准数据集上的表现
    """
    print("\n" + "="*70)
    print("🧪 测试1: 评委能力基线测试")
    print("="*70)
    print("目标：评估各评委模型在标准评测集上的准确性和稳定性\n")
    
    results = {}
    
    for judge_id, judge in JUDGE_MODELS.items():
        scores = []
        errors = []
        
        print(f"\n📊 评委模型: {judge.name}")
        print(f"   能力等级: {'⭐' * judge.capability_level}")
        print(f"   调用成本: ${judge.cost_per_call}/1K calls")
        
        for item in EVALUATION_DATASET:
            result = mock_judge_score(judge, item)
            scores.append(result["score"])
            
            # 计算与人工标注的误差
            expected = {"excellent": 9, "good": 7, "fair": 5, "poor": 3}[item["human_label"]]
            error = abs(result["score"] - expected)
            errors.append(error)
            
            print(f"   Q{item['id']}: 评分={result['score']:.1f}, 期望={expected}, 误差={error:.1f}")
        
        avg_score = sum(scores) / len(scores)
        avg_error = sum(errors) / len(errors)
        consistency = 1 - (max(scores) - min(scores)) / 10  # 评分范围越小越一致
        
        results[judge_id] = {
            "avg_score": round(avg_score, 2),
            "avg_error": round(avg_error, 2),
            "consistency": round(consistency, 2),
            "cost_efficiency": round((10 - avg_error) / judge.cost_per_call, 2)
        }
        
        print(f"   📈 平均误差: {avg_error:.2f}, 一致性: {consistency:.2f}")
    
    # 找出最佳模型
    best_model = min(results.items(), key=lambda x: x[1]["avg_error"])
    print(f"\n🏆 最佳准确性: {JUDGE_MODELS[best_model[0]].name} (误差: {best_model[1]['avg_error']})")
    
    best_efficiency = max(results.items(), key=lambda x: x[1]["cost_efficiency"])
    print(f"💰 最佳性价比: {JUDGE_MODELS[best_efficiency[0]].name} (效率: {best_efficiency[1]['cost_efficiency']:.1f})")
    
    # 判断测试是否通过
    passed = best_model[1]["avg_error"] < 2.0
    score = max(0, 10 - best_model[1]["avg_error"]) / 10
    
    return TestResult(
        name="评委能力基线测试",
        passed=passed,
        score=round(score, 2),
        risk_level=RiskLevel.L2 if not passed else RiskLevel.L3,
        details={"model_results": results, "best_model": best_model[0]}
    )


def test_domain_adaptation() -> TestResult:
    """
    测试2: 领域适配性测试
    验证评委在不同领域的表现差异
    """
    print("\n" + "="*70)
    print("🧪 测试2: 领域适配性测试")
    print("="*70)
    print("目标：评估评委模型在通用 vs 专业领域的表现差异\n")
    
    # 扩展测试集，增加专业领域内容
    domain_items = [
        {"id": 101, "question": "解释CRISPR基因编辑", "human_label": "excellent", "domain": "biotech", "complexity": "high"},
        {"id": 102, "question": "什么是Docker容器？", "human_label": "good", "domain": "devops", "complexity": "medium"},
        {"id": 103, "question": "如何煎鸡蛋？", "human_label": "fair", "domain": "cooking", "complexity": "low"},
    ]
    
    domain_performance = {}
    
    for judge_id, judge in JUDGE_MODELS.items():
        print(f"\n📊 {judge.name}:")
        domain_errors = {}
        
        for item in domain_items:
            result = mock_judge_score(judge, item)
            expected = {"excellent": 9, "good": 7, "fair": 5, "poor": 3}[item["human_label"]]
            error = abs(result["score"] - expected)
            
            if item["domain"] not in domain_errors:
                domain_errors[item["domain"]] = []
            domain_errors[item["domain"]].append(error)
            
            print(f"   {item['domain']:10s}: 评分={result['score']:.1f}, 误差={error:.1f}")
        
        # 计算各领域平均误差
        for domain, errors in domain_errors.items():
            avg_error = sum(errors) / len(errors)
            print(f"   📈 {domain}领域平均误差: {avg_error:.2f}")
            
            if domain not in domain_performance:
                domain_performance[domain] = {}
            domain_performance[domain][judge_id] = avg_error
    
    # 分析领域适配性
    print("\n📋 领域适配性分析:")
    for domain, performances in domain_performance.items():
        best_judge = min(performances.items(), key=lambda x: x[1])
        print(f"   {domain:10s}: 最佳评委={JUDGE_MODELS[best_judge[0]].name}, 误差={best_judge[1]:.2f}")
    
    # 检测适配性问题
    adaptation_issues = []
    for domain, performances in domain_performance.items():
        errors = list(performances.values())
        if max(errors) - min(errors) > 1.5:
            adaptation_issues.append(f"{domain}领域评委表现差异过大")
    
    passed = len(adaptation_issues) == 0
    score = 1.0 - len(adaptation_issues) * 0.2
    
    return TestResult(
        name="领域适配性测试",
        passed=passed,
        score=round(max(0, score), 2),
        risk_level=RiskLevel.L2 if adaptation_issues else RiskLevel.L3,
        details={"issues": adaptation_issues, "domain_performance": domain_performance}
    )


def test_human_judge_agreement() -> TestResult:
    """
    测试3: 人机一致性测试
    模拟人工标注与模型评分的一致性分析
    """
    print("\n" + "="*70)
    print("🧪 测试3: 人机一致性测试")
    print("="*70)
    print("目标：验证评委模型评分与人工标注的一致性\n")
    
    # 使用GPT-4作为参考评委
    judge = JUDGE_MODELS["gpt4"]
    
    human_labels = []
    judge_scores = []
    judge_labels = []
    
    print("📊 人机对比分析:")
    print(f"{'ID':<5} {'人工标签':<10} {'评委评分':<10} {'评委标签':<10} {'一致':<6}")
    print("-" * 55)
    
    for item in EVALUATION_DATASET:
        result = mock_judge_score(judge, item)
        
        # 将分数转换为标签
        if result["score"] >= 8:
            judge_label = "excellent"
        elif result["score"] >= 6:
            judge_label = "good"
        elif result["score"] >= 4:
            judge_label = "fair"
        else:
            judge_label = "poor"
        
        human_labels.append(item["human_label"])
        judge_scores.append(result["score"])
        judge_labels.append(judge_label)
        
        match = "✓" if item["human_label"] == judge_label else "✗"
        print(f"{item['id']:<5} {item['human_label']:<10} {result['score']:<10.1f} {judge_label:<10} {match:<6}")
    
    # 计算一致性指标
    agreement_rate = sum(1 for h, j in zip(human_labels, judge_labels) if h == j) / len(human_labels)
    kappa = calculate_cohen_kappa(human_labels, judge_labels)
    
    print(f"\n📈 一致性指标:")
    print(f"   一致率: {agreement_rate*100:.1f}%")
    print(f"   Cohen's Kappa: {kappa:.3f}")
    
    # 解释Kappa值
    if kappa >= 0.8:
        kappa_interp = "几乎完全一致"
    elif kappa >= 0.6:
        kappa_interp = "实质性一致"
    elif kappa >= 0.4:
        kappa_interp = "中等一致"
    else:
        kappa_interp = "一致性较差"
    print(f"   一致性等级: {kappa_interp}")
    
    # 分歧案例分析
    disagreements = [(i+1, h, j) for i, (h, j) in enumerate(zip(human_labels, judge_labels)) if h != j]
    if disagreements:
        print(f"\n⚠️  分歧案例 ({len(disagreements)}个):")
        for case in disagreements:
            print(f"   ID {case[0]}: 人工={case[1]}, 评委={case[2]}")
    
    # 校准建议
    print(f"\n🔧 校准建议:")
    if kappa < 0.6:
        print("   - 建议增加人工标注样本量进行模型微调")
        print("   - 考虑使用多评委投票机制")
        print("   - 对分歧案例进行人工复核")
    else:
        print("   - 当前一致性良好，可进入生产环境")
        print("   - 建议每周抽样10%进行人工复核")
    
    passed = kappa >= 0.6
    score = kappa
    
    return TestResult(
        name="人机一致性测试",
        passed=passed,
        score=round(score, 2),
        risk_level=RiskLevel.L1 if not passed else RiskLevel.L2,
        details={
            "agreement_rate": agreement_rate,
            "kappa": kappa,
            "disagreements": len(disagreements)
        }
    )


def test_multi_judge_voting() -> TestResult:
    """
    测试4: 多评委投票机制测试
    验证不同投票策略的效果
    """
    print("\n" + "="*70)
    print("🧪 测试4: 多评委投票机制测试")
    print("="*70)
    print("目标：评估多评委投票对准确性和成本的影响\n")
    
    # 选择3个评委组成委员会
    committee = ["gpt4", "claude3", "gpt35"]
    
    voting_strategies = {
        "简单多数": "majority",
        "加权投票": "weighted",
        "一致性过滤": "consensus"
    }
    
    strategy_results = {}
    
    for strategy_name, strategy_type in voting_strategies.items():
        print(f"\n📊 投票策略: {strategy_name}")
        
        correct = 0
        total_cost = 0
        
        for item in EVALUATION_DATASET:
            votes = []
            for judge_id in committee:
                judge = JUDGE_MODELS[judge_id]
                result = mock_judge_score(judge, item)
                votes.append((judge_id, result["score"]))
                total_cost += judge.cost_per_call
            
            # 应用投票策略
            if strategy_type == "majority":
                # 简单多数：取平均分的四舍五入
                avg_score = sum(v for _, v in votes) / len(votes)
                final_score = round(avg_score)
            
            elif strategy_type == "weighted":
                # 加权投票：按能力等级加权
                weights = {jid: JUDGE_MODELS[jid].capability_level for jid in committee}
                total_weight = sum(weights.values())
                weighted_sum = sum(v * weights[jid] for jid, v in votes)
                final_score = round(weighted_sum / total_weight)
            
            else:  # consensus
                # 一致性过滤：只有差异小于阈值才通过
                scores = [v for _, v in votes]
                if max(scores) - min(scores) <= 2:
                    final_score = round(sum(scores) / len(scores))
                else:
                    final_score = -1  # 标记为需要人工复核
            
            # 检查准确性
            expected = {"excellent": 9, "good": 7, "fair": 5, "poor": 3}[item["human_label"]]
            if abs(final_score - expected) <= 1:
                correct += 1
        
        accuracy = correct / len(EVALUATION_DATASET)
        avg_cost = total_cost / len(EVALUATION_DATASET)
        
        strategy_results[strategy_name] = {
            "accuracy": round(accuracy, 2),
            "total_cost": round(total_cost, 3),
            "avg_cost": round(avg_cost, 4)
        }
        
        print(f"   准确率: {accuracy*100:.1f}%")
        print(f"   总成本: ${total_cost:.3f}")
        print(f"   单条成本: ${avg_cost:.4f}")
    
    # 推荐最优策略
    print(f"\n🏆 策略对比:")
    print(f"{'策略':<12} {'准确率':<10} {'单条成本':<12} {'性价比':<10}")
    print("-" * 50)
    for name, res in strategy_results.items():
        efficiency = res["accuracy"] / res["avg_cost"] if res["avg_cost"] > 0 else 0
        print(f"{name:<12} {res['accuracy']*100:<9.0f}% ${res['avg_cost']:<11.4f} {efficiency:<10.1f}")
    
    # 找出最佳策略
    best_strategy = max(strategy_results.items(), key=lambda x: x[1]["accuracy"])
    print(f"\n✅ 推荐策略: {best_strategy[0]} (准确率 {best_strategy[1]['accuracy']*100:.0f}%)")
    
    passed = best_strategy[1]["accuracy"] >= 0.7
    score = best_strategy[1]["accuracy"]
    
    return TestResult(
        name="多评委投票机制测试",
        passed=passed,
        score=round(score, 2),
        risk_level=RiskLevel.L2 if not passed else RiskLevel.L3,
        details={"strategies": strategy_results, "best": best_strategy[0]}
    )


def test_cost_efficiency_analysis() -> TestResult:
    """
    测试5: 成本效益分析
    评估不同配置下的质量-成本平衡点
    """
    print("\n" + "="*70)
    print("🧪 测试5: 成本效益分析")
    print("="*70)
    print("目标：找到质量与成本的最优平衡点\n")
    
    # 模拟不同评估规模
    scales = [100, 1000, 10000]
    
    configurations = {
        "单一GPT-4": ["gpt4"],
        "单一GPT-3.5": ["gpt35"],
        "双评委(GPT-4+Claude)": ["gpt4", "claude3"],
        "三评委委员会": ["gpt4", "claude3", "gpt35"],
        "分层评估": ["gpt35", "gpt4"]  # GPT-3.5初筛 + GPT-4复核
    }
    
    print("📊 不同规模下的成本效益分析:\n")
    
    for scale in scales:
        print(f"📈 评估规模: {scale} 条/天")
        print(f"{'配置':<20} {'日成本':<12} {'预估准确率':<12} {'成本效益':<10}")
        print("-" * 60)
        
        for config_name, judges in configurations.items():
            # 计算日成本
            daily_cost = sum(JUDGE_MODELS[j].cost_per_call for j in judges) * scale / 1000
            
            # 预估准确率（基于评委能力）
            avg_capability = sum(JUDGE_MODELS[j].capability_level for j in judges) / len(judges)
            estimated_accuracy = 0.5 + avg_capability * 0.1  # 简化公式
            
            # 分层评估特殊处理
            if config_name == "分层评估":
                # 假设30%需要GPT-4复核
                daily_cost = (JUDGE_MODELS["gpt35"].cost_per_call * scale + 
                             JUDGE_MODELS["gpt4"].cost_per_call * scale * 0.3) / 1000
                estimated_accuracy = 0.82
            
            efficiency = estimated_accuracy / daily_cost if daily_cost > 0 else 0
            
            print(f"{config_name:<20} ${daily_cost:<11.2f} {estimated_accuracy*100:<11.0f}% {efficiency:<10.2f}")
        
        print()
    
    # 推荐配置
    print("🔧 配置建议:")
    print("   小规模 (<500条/天): 单一GPT-4，追求最高准确性")
    print("   中规模 (500-5000条/天): 双评委投票，平衡质量与成本")
    print("   大规模 (>5000条/天): 分层评估，GPT-3.5初筛+GPT-4复核")
    
    return TestResult(
        name="成本效益分析",
        passed=True,
        score=0.85,
        risk_level=RiskLevel.L3,
        details={"configurations": list(configurations.keys())}
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 Day 46 测试汇总报告")
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
    
    print(f"\n📈 统计:")
    print(f"   通过: {passed}/{total}")
    print(f"   平均得分: {avg_score:.2f}")
    print(f"   高风险项: {high_risk}个")
    
    if high_risk > 0:
        print(f"\n⚠️  关键风险提醒:")
        for r in results:
            if r.risk_level == RiskLevel.L1:
                print(f"   - {r.name}: 需要立即处理")
    
    print("\n" + "="*70)
    print("💡 下一步行动:")
    print("   1. 根据测试结果选择适合的评委模型配置")
    print("   2. 建立人机一致性校准流程")
    print("   3. 设计多评委投票机制")
    print("   4. 进入 Day 47: 评估Prompt设计与评分标准")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 46")
    print("   LLM-as-a-Judge 评委模型选型与基准校准")
    print("="*70)
    
    random.seed(46)  # 固定随机种子保证可重复性
    
    results = [
        test_judge_capability_baseline(),
        test_domain_adaptation(),
        test_human_judge_agreement(),
        test_multi_judge_voting(),
        test_cost_efficiency_analysis(),
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
