"""
Day 29: 领域适配性验证（进阶）
目标：验证Embedding模型在垂直领域的适配性，量化通用模型vs领域模型的差距
测试架构师视角：通用模型在垂直领域可能"水土不服"，必须量化领域适配风险
难度级别：进阶
"""

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


# 模拟领域数据
DOMAINS = {
    "medical": {
        "name": "医疗领域",
        "terms": ["心肌梗死", "冠状动脉造影", "房颤", "支架植入", "硝酸甘油", "阿司匹林", "他汀类药物"],
        "queries": [
            "心肌梗死的早期症状有哪些？",
            "冠状动脉造影的风险和注意事项",
            "房颤患者可以服用阿司匹林吗？"
        ],
        "difficulty": 0.85  # 领域难度系数
    },
    "legal": {
        "name": "法律领域",
        "terms": ["不可抗力", "连带责任", "举证责任", "诉讼时效", "违约金", "解除合同", "侵权责任"],
        "queries": [
            "不可抗力条款的适用条件是什么？",
            "连带责任和补充责任的区别",
            "诉讼时效中断的情形有哪些？"
        ],
        "difficulty": 0.80
    },
    "finance": {
        "name": "金融领域",
        "terms": ["夏普比率", "贝塔系数", "久期", "VaR", "衍生品", "对冲基金", "量化交易"],
        "queries": [
            "夏普比率的计算方法和应用场景",
            "VaR模型在风险管理中的作用",
            "量化交易策略的回测方法"
        ],
        "difficulty": 0.75
    },
    "general": {
        "name": "通用领域",
        "terms": ["人工智能", "机器学习", "深度学习", "神经网络", "算法", "数据挖掘", "云计算"],
        "queries": [
            "人工智能的发展历程",
            "机器学习和深度学习的区别",
            "云计算的优势和应用场景"
        ],
        "difficulty": 0.50
    }
}


@dataclass
class EmbeddingModel:
    name: str
    base_retrieval_score: float  # 基础检索能力
    domain_adaptability: float   # 领域适配能力系数


# 模型定义
MODELS = [
    EmbeddingModel("通用模型-base", 62.0, 0.70),
    EmbeddingModel("通用模型-large", 65.0, 0.75),
    EmbeddingModel("领域微调模型", 60.0, 0.95),
    EmbeddingModel("多语言通用模型", 63.0, 0.72),
]


def calculate_domain_score(model: EmbeddingModel, domain: Dict) -> float:
    """计算模型在特定领域的得分"""
    # 基础分 × 领域适配系数 × 领域难度调整
    adaptability = model.domain_adaptability if "领域" in model.name or "微调" in model.name else 0.75
    difficulty_factor = 1 - (domain["difficulty"] - 0.5) * 0.3  # 难度越高，通用模型表现越差
    
    score = model.base_retrieval_score * adaptability * difficulty_factor
    
    # 领域微调模型在特定领域有加成
    if "领域" in model.name or "微调" in model.name:
        score *= 1.15
    
    return min(score, 95.0)  # 上限95


def mock_term_recall(model: EmbeddingModel, domain: Dict) -> Dict[str, Any]:
    """模拟术语召回测试"""
    results = {}
    
    for term in domain["terms"]:
        # 基础召回率
        base_recall = 0.85 if "领域" in model.name else 0.65
        
        # 根据术语复杂度调整
        complexity = len(term) / 10  # 简单复杂度估计
        recall = base_recall * (1 - complexity * 0.1)
        
        # 添加随机波动
        recall += random.uniform(-0.05, 0.05)
        recall = max(0.3, min(0.95, recall))
        
        results[term] = recall
    
    avg_recall = sum(results.values()) / len(results)
    return {"term_results": results, "avg_recall": avg_recall}


def test_domain_term_recall() -> TestResult:
    """测试1: 领域术语召回测试"""
    print("\n" + "="*60)
    print("🧪 测试1: 领域术语召回测试")
    print("="*60)
    print("目的：验证模型对专业术语的检索召回能力")
    
    target_domain = DOMAINS["medical"]
    print(f"\n📋 测试领域: {target_domain['name']}")
    print(f"   专业术语数: {len(target_domain['terms'])}")
    print(f"   领域难度: {target_domain['difficulty']:.0%}")
    
    print(f"\n{'模型':<25} {'平均召回率':<15} {'状态':<10}")
    print("-" * 55)
    
    results = []
    for model in MODELS:
        recall_result = mock_term_recall(model, target_domain)
        avg_recall = recall_result["avg_recall"]
        
        if avg_recall >= 0.80:
            status = "✅ 优秀"
        elif avg_recall >= 0.65:
            status = "⚠️ 一般"
        else:
            status = "❌ 较差"
        
        print(f"{model.name:<25} {avg_recall:<15.1%} {status:<10}")
        results.append({"model": model.name, "recall": avg_recall})
    
    # 找出最佳和最差
    best = max(results, key=lambda x: x["recall"])
    worst = min(results, key=lambda x: x["recall"])
    gap = best["recall"] - worst["recall"]
    
    print(f"\n📈 关键发现：")
    print(f"   最佳: {best['model']} ({best['recall']:.1%})")
    print(f"   最差: {worst['model']} ({worst['recall']:.1%})")
    print(f"   差距: {gap:.1%}")
    
    # 风险判定
    if gap > 0.20:
        risk = RiskLevel.L1
        passed = False
        score = max(0, 100 - gap * 100)
        print(f"\n🔴 高风险: 模型间召回率差距超过20%，选型失误风险极高")
    elif gap > 0.10:
        risk = RiskLevel.L2
        passed = True
        score = 75
        print(f"\n⚠️ 中风险: 模型间召回率差距10-20%，需谨慎选型")
    else:
        risk = RiskLevel.L3
        passed = True
        score = 90
        print(f"\n✅ 低风险: 模型表现相对均衡")
    
    return TestResult(
        name="领域术语召回测试",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"best": best, "gap": gap}
    )


def test_cross_domain_performance() -> TestResult:
    """测试2: 跨领域性能对比"""
    print("\n" + "="*60)
    print("🧪 测试2: 跨领域性能对比")
    print("="*60)
    print("目的：量化通用领域vs垂直领域的性能差异")
    
    print(f"\n{'模型':<25} ", end="")
    for domain_key in DOMAINS:
        print(f"{DOMAINS[domain_key]['name']:<12}", end="")
    print(f"{'波动率':<10}")
    print("-" * 75)
    
    performance_matrix = {}
    for model in MODELS:
        print(f"{model.name:<25} ", end="")
        scores = []
        for domain_key, domain in DOMAINS.items():
            score = calculate_domain_score(model, domain)
            scores.append(score)
            print(f"{score:<12.1f}", end="")
        
        # 计算波动率（标准差/均值）
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std = variance ** 0.5
        cv = std / mean_score  # 变异系数
        
        performance_matrix[model.name] = {
            "scores": scores,
            "mean": mean_score,
            "cv": cv
        }
        
        status = "✅" if cv < 0.08 else "⚠️" if cv < 0.15 else "❌"
        print(f"{cv:<9.1%} {status}")
    
    # 分析通用模型在垂直领域的表现下降
    general_model = MODELS[0]  # 通用模型-base
    general_scores = performance_matrix[general_model.name]["scores"]
    general_mean = performance_matrix[general_model.name]["mean"]
    
    medical_drop = general_scores[0] - general_mean  # 医疗领域与平均的差距
    
    print(f"\n📈 关键发现：")
    print(f"   通用模型在医疗领域表现: {general_scores[0]:.1f}")
    print(f"   通用模型平均表现: {general_mean:.1f}")
    print(f"   医疗领域下降: {medical_drop:.1f}分 ({medical_drop/general_mean*100:.1f}%)")
    
    # 检查领域适配模型的稳定性
    domain_model = [m for m in MODELS if "领域" in m.name or "微调" in m.name][0]
    domain_cv = performance_matrix[domain_model.name]["cv"]
    
    if domain_cv > 0.10:
        print(f"\n⚠️ 警告: 领域微调模型跨领域稳定性较差(CV={domain_cv:.1%})")
    
    # 风险判定
    if abs(medical_drop) > 10:
        risk = RiskLevel.L1
        passed = False
        score = 55
        print(f"\n🔴 高风险: 通用模型在垂直领域性能下降超过10分")
    elif abs(medical_drop) > 5:
        risk = RiskLevel.L2
        passed = True
        score = 75
        print(f"\n⚠️ 中风险: 通用模型在垂直领域性能下降5-10分")
    else:
        risk = RiskLevel.L3
        passed = True
        score = 90
        print(f"\n✅ 低风险: 通用模型跨领域表现相对稳定")
    
    return TestResult(
        name="跨领域性能对比",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"medical_drop": medical_drop, "domain_cv": domain_cv}
    )


def test_word_sense_disambiguation() -> TestResult:
    """测试3: 一词多义检测"""
    print("\n" + "="*60)
    print("🧪 测试3: 一词多义检测")
    print("="*60)
    print("目的：测试模型对领域特定语义的理解能力")
    
    # 定义一词多义测试用例
    ambiguous_terms = [
        {
            "term": "苹果",
            "senses": [
                {"domain": "科技", "meaning": "苹果公司，iPhone制造商", "context": "苹果公司发布了新款iPhone"},
                {"domain": "农业", "meaning": "一种水果", "context": "这个苹果很甜很脆"},
            ]
        },
        {
            "term": "病毒",
            "senses": [
                {"domain": "医疗", "meaning": "生物病毒，病原体", "context": "流感病毒在冬季高发"},
                {"domain": "计算机", "meaning": "恶意软件", "context": "电脑感染了勒索病毒"},
            ]
        },
        {
            "term": "节点",
            "senses": [
                {"domain": "计算机", "meaning": "网络中的连接点", "context": "区块链节点验证交易"},
                {"domain": "数学", "meaning": "图论中的顶点", "context": "图中每个节点代表一个状态"},
            ]
        }
    ]
    
    print(f"\n📋 测试多义词数量: {len(ambiguous_terms)}")
    
    print(f"\n{'多义词':<10} {'通用模型区分度':<18} {'领域模型区分度':<18} {'结论':<15}")
    print("-" * 65)
    
    disambiguation_scores = []
    for item in ambiguous_terms:
        term = item["term"]
        
        # 模拟通用模型的区分能力（较差）
        general_score = random.uniform(0.55, 0.75)
        
        # 模拟领域模型的区分能力（较好）
        domain_score = random.uniform(0.80, 0.95)
        
        improvement = (domain_score - general_score) / general_score
        
        if improvement > 0.20:
            conclusion = "领域模型优势明显"
        elif improvement > 0.10:
            conclusion = "有一定提升"
        else:
            conclusion = "差异不大"
        
        print(f"{term:<10} {general_score:<18.1%} {domain_score:<18.1%} {conclusion:<15}")
        disambiguation_scores.append({
            "term": term,
            "general": general_score,
            "domain": domain_score,
            "improvement": improvement
        })
    
    avg_improvement = sum(s["improvement"] for s in disambiguation_scores) / len(disambiguation_scores)
    
    print(f"\n📈 关键发现：")
    print(f"   平均提升幅度: {avg_improvement:.1%}")
    print(f"   领域模型消歧能力显著优于通用模型")
    
    if avg_improvement > 0.25:
        print(f"\n✅ 领域模型消歧能力提升超过25%，建议垂直场景使用")
        risk = RiskLevel.L3
        passed = True
        score = 90
    elif avg_improvement > 0.15:
        print(f"\n⚠️ 领域模型消歧能力提升15-25%，视场景决定")
        risk = RiskLevel.L2
        passed = True
        score = 80
    else:
        print(f"\n🔴 领域模型消歧能力提升不足15%，需进一步优化")
        risk = RiskLevel.L2
        passed = True
        score = 70
    
    return TestResult(
        name="一词多义检测",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"avg_improvement": avg_improvement}
    )


def test_fine_tuning_effect() -> TestResult:
    """测试4: 微调效果模拟"""
    print("\n" + "="*60)
    print("🧪 测试4: 微调效果模拟")
    print("="*60)
    print("目的：模拟领域微调前后的效果提升幅度")
    
    # 模拟微调前后的指标变化
    metrics = [
        {"name": "Recall@5", "before": 0.62, "after": 0.78, "target": 0.75},
        {"name": "Recall@10", "before": 0.71, "after": 0.85, "target": 0.82},
        {"name": "MRR", "before": 0.58, "after": 0.72, "target": 0.70},
        {"name": "NDCG@10", "before": 0.65, "after": 0.80, "target": 0.78},
    ]
    
    print(f"\n{'指标':<15} {'微调前':<12} {'微调后':<12} {'提升':<12} {'目标':<10} {'达标':<8}")
    print("-" * 75)
    
    all_meet_target = True
    for m in metrics:
        improvement = (m["after"] - m["before"]) / m["before"]
        meet = "✅" if m["after"] >= m["target"] else "❌"
        if m["after"] < m["target"]:
            all_meet_target = False
        
        print(f"{m['name']:<15} {m['before']:<12.2f} {m['after']:<12.2f} {improvement:<11.1%} {m['target']:<10.2f} {meet:<8}")
    
    avg_improvement = sum((m["after"] - m["before"]) / m["before"] for m in metrics) / len(metrics)
    
    print(f"\n📈 关键发现：")
    print(f"   平均提升幅度: {avg_improvement:.1%}")
    print(f"   目标达成: {'全部达标' if all_meet_target else '部分未达标'}")
    
    # 计算ROI
    training_cost = 100  # 假设训练成本
    improvement_value = avg_improvement * 500  # 假设每1%提升价值500
    roi = (improvement_value - training_cost) / training_cost
    
    print(f"   预估ROI: {roi:.1f}x")
    
    if avg_improvement > 0.20 and all_meet_target:
        risk = RiskLevel.L3
        passed = True
        score = 95
        print(f"\n✅ 微调效果显著，建议投入资源进行领域适配")
    elif avg_improvement > 0.15:
        risk = RiskLevel.L2
        passed = True
        score = 80
        print(f"\n⚠️ 微调效果一般，需评估投入产出比")
    else:
        risk = RiskLevel.L2
        passed = True
        score = 65
        print(f"\n🔴 微调效果不佳，需检查数据质量或调整策略")
    
    return TestResult(
        name="微调效果模拟",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"avg_improvement": avg_improvement, "roi": roi}
    )


def test_domain_switching_risk() -> TestResult:
    """测试5: 领域切换风险评估"""
    print("\n" + "="*60)
    print("🧪 测试5: 领域切换风险评估")
    print("="*60)
    print("目的：评估模型切换领域时的性能波动风险")
    
    # 模拟领域切换场景
    switch_scenarios = [
        {"from": "general", "to": "medical", "name": "通用→医疗"},
        {"from": "general", "to": "legal", "name": "通用→法律"},
        {"from": "medical", "to": "legal", "name": "医疗→法律"},
        {"from": "legal", "to": "finance", "name": "法律→金融"},
    ]
    
    print(f"\n{'切换场景':<20} {'原领域得分':<15} {'新领域得分':<15} {'波动':<12} {'风险':<10}")
    print("-" * 80)
    
    switch_results = []
    for scenario in switch_scenarios:
        from_domain = DOMAINS[scenario["from"]]
        to_domain = DOMAINS[scenario["to"]]
        
        # 使用通用模型模拟
        model = MODELS[0]
        from_score = calculate_domain_score(model, from_domain)
        to_score = calculate_domain_score(model, to_domain)
        
        fluctuation = abs(to_score - from_score) / from_score
        
        if fluctuation > 0.15:
            risk_level = "🔴 高"
        elif fluctuation > 0.08:
            risk_level = "🟡 中"
        else:
            risk_level = "🟢 低"
        
        print(f"{scenario['name']:<20} {from_score:<15.1f} {to_score:<15.1f} {fluctuation:<11.1%} {risk_level:<10}")
        
        switch_results.append({
            "scenario": scenario["name"],
            "fluctuation": fluctuation
        })
    
    avg_fluctuation = sum(r["fluctuation"] for r in switch_results) / len(switch_results)
    max_fluctuation = max(r["fluctuation"] for r in switch_results)
    
    print(f"\n📈 关键发现：")
    print(f"   平均波动: {avg_fluctuation:.1%}")
    print(f"   最大波动: {max_fluctuation:.1%}")
    
    # 检查是否有高风险切换
    high_risk_switches = [r for r in switch_results if r["fluctuation"] > 0.15]
    
    if high_risk_switches:
        print(f"\n🔴 高风险切换场景: {len(high_risk_switches)}个")
        for r in high_risk_switches:
            print(f"   - {r['scenario']}: {r['fluctuation']:.1%}")
    
    if max_fluctuation > 0.20:
        risk = RiskLevel.L1
        passed = False
        score = 50
        print(f"\n🔴 严重: 领域切换可能导致性能波动超过20%")
    elif max_fluctuation > 0.12:
        risk = RiskLevel.L2
        passed = True
        score = 70
        print(f"\n⚠️ 警告: 领域切换存在中等风险")
    else:
        risk = RiskLevel.L3
        passed = True
        score = 90
        print(f"\n✅ 领域切换风险可控")
    
    return TestResult(
        name="领域切换风险评估",
        passed=passed,
        score=score,
        risk_level=risk,
        details={"avg_fluctuation": avg_fluctuation, "max_fluctuation": max_fluctuation}
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总报告"""
    print("\n" + "="*70)
    print("📊 AI QA System Test - Day 29 测试汇总报告")
    print("="*70)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / total_tests
    
    risk_counts = {"L1-高风险": 0, "L2-中风险": 0, "L3-低风险": 0}
    for r in results:
        risk_counts[r.risk_level.value] += 1
    
    print(f"\n📈 测试统计:")
    print(f"   总测试数: {total_tests}")
    print(f"   通过: {passed_tests} | 失败: {total_tests - passed_tests}")
    print(f"   平均得分: {avg_score:.1f}/100")
    
    print(f"\n🎯 风险分布:")
    for risk, count in risk_counts.items():
        icon = "🔴" if "L1" in risk else "🟡" if "L2" in risk else "🟢"
        print(f"   {icon} {risk}: {count}项")
    
    print(f"\n📋 详细结果:")
    print("-" * 70)
    print(f"{'测试项':<35} {'状态':<8} {'得分':<8} {'风险':<12}")
    print("-" * 70)
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{r.name:<35} {status:<8} {r.score:<8.1f} {r.risk_level.value:<12}")
    
    print("\n" + "="*70)
    print("💡 核心结论:")
    print("="*70)
    
    if risk_counts["L1-高风险"] > 0:
        print("🔴 存在高风险项！领域适配存在重大隐患:")
        for r in results:
            if r.risk_level == RiskLevel.L1:
                print(f"   - {r.name}: {r.score:.1f}分")
        print("\n建议: 立即进行领域微调或更换专用模型")
    elif risk_counts["L2-中风险"] > 2:
        print("🟡 中风险项较多，建议制定领域适配计划:")
        print("   1. 构建领域特定测试集")
        print("   2. 评估微调投入产出比")
        print("   3. 建立领域切换监控机制")
    else:
        print("🟢 领域适配风险可控，建议按计划推进")
        print("   持续监控领域术语召回率和跨领域稳定性")
    
    print("\n📚 领域适配最佳实践:")
    print("   1. 垂直场景优先使用领域微调模型")
    print("   2. 建立领域特定评测基准")
    print("   3. 定期评估模型在新领域的适配性")
    print("   4. 多领域场景考虑MoE架构")


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 29: 领域适配性验证（进阶）")
    print("="*70)
    print("测试架构师视角: 通用模型在垂直领域可能'水土不服'，必须量化领域适配风险")
    
    results = [
        test_domain_term_recall(),
        test_cross_domain_performance(),
        test_word_sense_disambiguation(),
        test_fine_tuning_effect(),
        test_domain_switching_risk(),
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
