"""
Day 39: 时效相关性评估（实战）
目标：验证答案中的时间信息是否符合当前时间要求
测试架构师视角：检测"内容对但已过时"的风险
难度级别：⭐⭐⭐⭐ 实战
"""

import json
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta


@dataclass
class TestResult:
    name: str
    passed: bool
    score: float
    risk_level: str
    details: Dict[str, Any]


class TemporalRelevanceEvaluator:
    """时效相关性评估器"""
    
    # 模拟当前时间（用于测试）
    CURRENT_YEAR = 2024
    
    # 技术版本生命周期（模拟数据）
    VERSION_LIFECYCLE = {
        "python": {
            "2.7": {"eol": 2020, "status": "deprecated"},
            "3.6": {"eol": 2021, "status": "deprecated"},
            "3.7": {"eol": 2023, "status": "deprecated"},
            "3.8": {"eol": 2024, "status": "warning"},
            "3.9": {"eol": 2025, "status": "active"},
            "3.10": {"eol": 2026, "status": "active"},
            "3.11": {"eol": 2027, "status": "active"},
            "3.12": {"eol": 2028, "status": "latest"}
        },
        "nodejs": {
            "14": {"eol": 2023, "status": "deprecated"},
            "16": {"eol": 2023, "status": "deprecated"},
            "18": {"eol": 2025, "status": "active"},
            "20": {"eol": 2026, "status": "latest"}
        },
        "react": {
            "16": {"eol": 2022, "status": "deprecated"},
            "17": {"eol": 2023, "status": "deprecated"},
            "18": {"eol": 2025, "status": "active"},
            "19": {"eol": 2026, "status": "latest"}
        }
    }
    
    def __init__(self):
        pass
    
    def extract_temporal_expressions(self, text: str) -> List[Dict[str, Any]]:
        """提取时间表达式"""
        expressions = []
        text_lower = text.lower()
        
        # 1. 提取版本号
        version_patterns = [
            (r'python\s*(\d+\.\d+)', 'python'),
            (r'nodejs?\s*(\d+)', 'nodejs'),
            (r'react\s*(\d+)', 'react')
        ]
        
        for pattern, tech in version_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                expressions.append({
                    "type": "version",
                    "tech": tech,
                    "value": match.group(1),
                    "raw": match.group(0)
                })
        
        # 2. 提取年份
        year_pattern = r'\b(20\d{2})\s*年?\b'
        for match in re.finditer(year_pattern, text_lower):
            expressions.append({
                "type": "year",
                "value": int(match.group(1)),
                "raw": match.group(0)
            })
        
        # 3. 提取相对时间表述
        relative_terms = {
            'current': r'最新版|latest|current|现在',
            'future': r'即将|upcoming|即将发布',
            'deprecated': r'已废弃|deprecated|已弃用',
            'old': r'旧版|old|legacy'
        }
        
        for term_type, pattern in relative_terms.items():
            if re.search(pattern, text_lower):
                expressions.append({
                    "type": "relative",
                    "value": term_type,
                    "raw": term_type
                })
        
        return expressions
    
    def check_version_freshness(self, tech: str, version: str) -> Dict[str, Any]:
        """检查版本时效性"""
        tech_versions = self.VERSION_LIFECYCLE.get(tech, {})
        version_info = tech_versions.get(version, {})
        
        if not version_info:
            return {
                "known": False,
                "status": "unknown",
                "risk_score": 0.5
            }
        
        eol_year = version_info.get("eol", self.CURRENT_YEAR)
        status = version_info.get("status", "unknown")
        
        # 计算风险分数
        if status == "deprecated":
            risk_score = 1.0  # 已废弃，高风险
        elif status == "warning":
            risk_score = 0.6  # 即将过期，中风险
        elif status == "active":
            risk_score = 0.2  # 活跃版本，低风险
        elif status == "latest":
            risk_score = 0.0  # 最新版，无风险
        else:
            risk_score = 0.5
        
        return {
            "known": True,
            "tech": tech,
            "version": version,
            "eol_year": eol_year,
            "status": status,
            "years_until_eol": eol_year - self.CURRENT_YEAR,
            "risk_score": risk_score
        }
    
    def check_year_freshness(self, year: int) -> Dict[str, Any]:
        """检查年份时效性"""
        year_diff = self.CURRENT_YEAR - year
        
        if year_diff < 0:
            status = "future"
            risk_score = 0.0
        elif year_diff == 0:
            status = "current"
            risk_score = 0.0
        elif year_diff <= 1:
            status = "recent"
            risk_score = 0.2
        elif year_diff <= 2:
            status = "slightly_old"
            risk_score = 0.5
        else:
            status = "outdated"
            risk_score = 0.8
        
        return {
            "year": year,
            "year_diff": year_diff,
            "status": status,
            "risk_score": risk_score
        }
    
    def evaluate(self, question: str, answer: str) -> Dict[str, Any]:
        """综合评估时效性"""
        expressions = self.extract_temporal_expressions(answer)
        
        if not expressions:
            return {
                "has_temporal_info": False,
                "expressions": [],
                "checks": [],
                "max_risk_score": 0.0,
                "final_score": 1.0,
                "is_fresh": True
            }
        
        checks = []
        max_risk = 0.0
        
        for expr in expressions:
            if expr["type"] == "version":
                check = self.check_version_freshness(expr["tech"], expr["value"])
                checks.append({"expression": expr, "check": check})
                max_risk = max(max_risk, check.get("risk_score", 0))
            
            elif expr["type"] == "year":
                check = self.check_year_freshness(expr["value"])
                checks.append({"expression": expr, "check": check})
                max_risk = max(max_risk, check.get("risk_score", 0))
            
            elif expr["type"] == "relative":
                # 相对时间表述
                if expr["value"] in ["deprecated", "old"]:
                    risk = 0.7
                elif expr["value"] == "future":
                    risk = 0.3
                else:
                    risk = 0.0
                checks.append({"expression": expr, "check": {"risk_score": risk}})
                max_risk = max(max_risk, risk)
        
        final_score = 1.0 - max_risk
        
        return {
            "has_temporal_info": True,
            "expressions": expressions,
            "checks": checks,
            "max_risk_score": max_risk,
            "final_score": round(final_score, 3),
            "is_fresh": final_score >= 0.7
        }


def mock_llm_response(scenario: str) -> Dict[str, str]:
    """模拟不同场景下的LLM回答"""
    responses = {
        "fresh_content": {
            "question": "Python最新版本有什么新特性？",
            "answer": "Python 3.12是最新版本，发布于2023年。它带来了性能改进、更好的错误消息、f-string解析增强等新特性。建议使用Python 3.11或3.12进行新项目的开发。"
        },
        "version_warning": {
            "question": "Python 3.8有哪些特性？",
            "answer": "Python 3.8引入了赋值表达式（海象运算符）、位置参数限制、f-string=格式化等新特性。这是一个稳定的版本，适合生产环境使用。"
        },
        "deprecated_version": {
            "question": "如何在Python中使用print语句？",
            "answer": "在Python 2.7中，你可以直接使用print语句：print \"Hello World\"。不需要括号。Python 2.7是一个非常稳定的版本，被广泛使用。"
        },
        "outdated_data": {
            "question": "目前最流行的前端框架是什么？",
            "answer": "根据2020年的调查数据，React是最流行的前端框架，占据了40%的市场份额。Vue.js和Angular分别占据第二和第三位。"
        },
        "relative_time": {
            "question": "React的最新版本是什么？",
            "answer": "React 16是最新稳定版本，它引入了Fiber架构和Hooks特性。旧版的React使用类组件，而新版推荐使用函数组件配合Hooks。"
        }
    }
    return responses.get(scenario, responses["fresh_content"])


def test_fresh_content() -> TestResult:
    """测试1: 时效性良好的内容"""
    print("\n" + "="*60)
    print("🧪 测试1: 时效性良好的内容")
    print("="*60)
    
    data = mock_llm_response("fresh_content")
    evaluator = TemporalRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer'][:80]}...")
    print(f"检测到时间表达式: {len(result['expressions'])}")
    for expr in result['expressions']:
        print(f"  - {expr['type']}: {expr['raw']}")
    print(f"最大风险分数: {result['max_risk_score']}")
    print(f"时效性评分: {result['final_score']}")
    
    passed = result['is_fresh'] and result['final_score'] >= 0.8
    risk = "L3" if passed else "L1"
    
    return TestResult(
        name="时效性良好的内容",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_version_warning() -> TestResult:
    """测试2: 版本即将过期（警告）"""
    print("\n" + "="*60)
    print("🧪 测试2: 版本即将过期（警告场景）")
    print("="*60)
    
    data = mock_llm_response("version_warning")
    evaluator = TemporalRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer'][:80]}...")
    print(f"⚠️ Python 3.8在2024年即将结束支持")
    
    for check in result['checks']:
        if 'version' in check['check']:
            c = check['check']
            print(f"版本状态: {c.get('tech')} {c.get('version')} -> {c.get('status')}")
            print(f"EOL年份: {c.get('eol_year')}")
    
    print(f"最大风险分数: {result['max_risk_score']}")
    print(f"时效性评分: {result['final_score']}")
    
    # 应该检测到警告级别风险
    passed = 0.4 <= result['max_risk_score'] <= 0.7
    risk = "L2"
    
    return TestResult(
        name="版本即将过期（警告）",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_deprecated_version() -> TestResult:
    """测试3: 已废弃版本（高风险）"""
    print("\n" + "="*60)
    print("🧪 测试3: 已废弃版本（高风险场景）")
    print("="*60)
    
    data = mock_llm_response("deprecated_version")
    evaluator = TemporalRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer']}")
    print(f"❌ Python 2.7已于2020年停止支持")
    print(f"❌ 推荐Python 2.7是严重过时的建议")
    
    for check in result['checks']:
        if 'version' in check['check']:
            c = check['check']
            print(f"版本状态: {c.get('tech')} {c.get('version')} -> {c.get('status')}")
    
    print(f"最大风险分数: {result['max_risk_score']}")
    print(f"时效性评分: {result['final_score']}")
    
    # 应该检测到高风险
    passed = result['max_risk_score'] >= 0.8
    risk = "L1"
    
    return TestResult(
        name="已废弃版本（高风险）",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_outdated_data() -> TestResult:
    """测试4: 过时数据"""
    print("\n" + "="*60)
    print("🧪 测试4: 过时数据（陈旧统计）")
    print("="*60)
    
    data = mock_llm_response("outdated_data")
    evaluator = TemporalRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer']}")
    print(f"🔍 引用2020年数据，距今已4年")
    
    for check in result['checks']:
        if 'year' in check['check']:
            c = check['check']
            print(f"年份检查: {c.get('year')} -> {c.get('status')} (差距{c.get('year_diff')}年)")
    
    print(f"最大风险分数: {result['max_risk_score']}")
    print(f"时效性评分: {result['final_score']}")
    
    # 应该检测到过时的风险
    passed = result['max_risk_score'] >= 0.5
    risk = "L2"
    
    return TestResult(
        name="过时数据（陈旧统计）",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def test_relative_time() -> TestResult:
    """测试5: 相对时间表述"""
    print("\n" + "="*60)
    print("🧪 测试5: 相对时间表述（旧版标记）")
    print("="*60)
    
    data = mock_llm_response("relative_time")
    evaluator = TemporalRelevanceEvaluator()
    result = evaluator.evaluate(data["question"], data["answer"])
    
    print(f"问题: {data['question']}")
    print(f"答案: {data['answer']}")
    print(f"🔍 React 16已于2022年停止支持")
    print(f"🔍 当前最新版本是React 18+")
    
    for check in result['checks']:
        if 'version' in check['check']:
            c = check['check']
            print(f"版本状态: {c.get('tech')} {c.get('version')} -> {c.get('status')}")
    
    print(f"最大风险分数: {result['max_risk_score']}")
    print(f"时效性评分: {result['final_score']}")
    
    # 应该检测到高风险
    passed = result['max_risk_score'] >= 0.8
    risk = "L1"
    
    return TestResult(
        name="相对时间表述（旧版标记）",
        passed=passed,
        score=result['final_score'],
        risk_level=risk,
        details=result
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📊 Day 39 时效相关性评估 - 测试汇总")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / total
    
    l1_count = sum(1 for r in results if r.risk_level == "L1")
    l2_count = sum(1 for r in results if r.risk_level == "L2")
    l3_count = sum(1 for r in results if r.risk_level == "L3")
    
    print(f"\n总测试数: {total}")
    print(f"通过: {passed} | 失败: {total - passed}")
    print(f"平均时效性评分: {avg_score:.3f}")
    print(f"\n风险分布:")
    print(f"  🔴 L1 (高风险): {l1_count}")
    print(f"  🟡 L2 (中风险): {l2_count}")
    print(f"  🟢 L3 (低风险): {l3_count}")
    
    print("\n详细结果:")
    for r in results:
        status = "✅" if r.passed else "❌"
        risk_emoji = {"L1": "🔴", "L2": "🟡", "L3": "🟢"}[r.risk_level]
        print(f"  {status} {r.name}: {r.score:.3f} {risk_emoji}")
    
    print("\n" + "="*70)
    print("💡 关键发现:")
    print("  1. 已废弃版本可以被有效检测（测试3、5通过）")
    print("  2. 过时数据需要年份提取来识别（测试4）")
    print("  3. 版本即将过期应触发警告（测试2）")
    print("  4. 建议建立版本生命周期数据库持续更新")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 39: 时效相关性评估（实战）")
    print("="*70)
    print("目标: 验证答案中的时间信息是否符合当前时间要求")
    print("测试架构师视角: 检测'内容对但已过时'的风险")
    
    results = [
        test_fresh_content(),
        test_version_warning(),
        test_deprecated_version(),
        test_outdated_data(),
        test_relative_time()
    ]
    
    print_summary(results)
    
    return results


if __name__ == "__main__":
    run_all_tests()
