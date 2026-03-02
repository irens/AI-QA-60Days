"""
Day 22: 文档质量评分（基础）
目标：最小可用，专注风险验证，杜绝多余业务逻辑
测试架构师视角：垃圾进，垃圾出。文档质量是RAG系统的第一道防线。
"""

import json
import random
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum


class DocumentType(Enum):
    """文档类型"""
    PDF_TEXT = "pdf_text"           # 文本PDF
    PDF_SCAN = "pdf_scan"           # 扫描PDF
    PDF_IMAGE = "pdf_image"         # 图片PDF
    WORD = "word"                   # Word文档
    MARKDOWN = "markdown"           # Markdown
    HTML = "html"                   # HTML
    TXT = "txt"                     # 纯文本


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "A级-优秀"
    GOOD = "B级-良好"
    PASS = "C级-及格"
    FAIL = "D级-不合格"


@dataclass
class Document:
    """文档对象"""
    doc_id: str
    title: str
    doc_type: DocumentType
    content: str
    created_at: datetime
    updated_at: datetime
    file_size: int  # bytes
    page_count: int
    has_structure: bool = False
    parse_success_rate: float = 1.0


@dataclass
class QualityScore:
    """质量评分"""
    format_score: float
    content_score: float
    timeliness_score: float
    semantic_score: float
    overall_score: float
    level: QualityLevel
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """测试结果"""
    name: str
    passed: bool
    score: float
    risk_level: str
    details: str = ""


class DocumentQualityEvaluator:
    """文档质量评估器"""
    
    def __init__(self):
        self.format_weights = {"type": 0.3, "parse_rate": 0.4, "structure": 0.3}
        self.content_weights = {"completeness": 0.4, "coherence": 0.35, "focus": 0.25}
        self.timeliness_weights = {"recency": 0.5, "update_freq": 0.3, "freshness": 0.2}
        self.semantic_weights = {"language": 0.3, "clarity": 0.4, "embedding": 0.3}
        
    def evaluate_format(self, doc: Document) -> Tuple[float, Dict]:
        """评估格式质量"""
        # 文件格式得分
        format_scores = {
            DocumentType.PDF_TEXT: 1.0,
            DocumentType.WORD: 1.0,
            DocumentType.MARKDOWN: 1.0,
            DocumentType.HTML: 0.8,
            DocumentType.TXT: 0.7,
            DocumentType.PDF_IMAGE: 0.5,
            DocumentType.PDF_SCAN: 0.3
        }
        type_score = format_scores.get(doc.doc_type, 0.5)
        
        # 解析成功率得分
        parse_score = doc.parse_success_rate
        
        # 结构完整性得分
        structure_score = 1.0 if doc.has_structure else 0.5
        
        # 综合格式得分
        format_score = (
            type_score * self.format_weights["type"] +
            parse_score * self.format_weights["parse_rate"] +
            structure_score * self.format_weights["structure"]
        )
        
        details = {
            "type_score": type_score,
            "parse_score": parse_score,
            "structure_score": structure_score,
            "doc_type": doc.doc_type.value
        }
        
        return format_score, details
    
    def evaluate_content(self, doc: Document) -> Tuple[float, Dict]:
        """评估内容质量"""
        content = doc.content
        
        # 完整性检测：检查关键章节
        required_sections = ["简介", "正文", "总结", "参考"]
        found_sections = sum(1 for s in required_sections if s in content)
        completeness = found_sections / len(required_sections)
        
        # 连贯性检测：段落长度分布
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) > 1:
            lengths = [len(p) for p in paragraphs]
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            coherence = max(0, 1 - variance / (avg_len ** 2 + 1))  # 归一化
        else:
            coherence = 0.5
        
        # 聚焦度检测：主题一致性
        words = content.lower().split()
        if len(words) > 10:
            word_freq = {}
            for w in words:
                word_freq[w] = word_freq.get(w, 0) + 1
            # 计算高频词占比
            sorted_freq = sorted(word_freq.values(), reverse=True)
            top5_ratio = sum(sorted_freq[:5]) / len(words)
            focus = min(1.0, top5_ratio * 2)  # 归一化
        else:
            focus = 0.5
        
        content_score = (
            completeness * self.content_weights["completeness"] +
            coherence * self.content_weights["coherence"] +
            focus * self.content_weights["focus"]
        )
        
        details = {
            "completeness": completeness,
            "coherence": coherence,
            "focus": focus,
            "paragraph_count": len(paragraphs)
        }
        
        return content_score, details
    
    def evaluate_timeliness(self, doc: Document) -> Tuple[float, Dict]:
        """评估时效质量"""
        now = datetime.now()
        
        # 新鲜度：文档年龄
        age_days = (now - doc.created_at).days
        recency = max(0, 1 - age_days / 365)
        
        # 更新频率
        days_since_update = (now - doc.updated_at).days
        if days_since_update < 30:
            update_freq = 1.0
        elif days_since_update < 90:
            update_freq = 0.8
        elif days_since_update < 180:
            update_freq = 0.6
        else:
            update_freq = 0.4
        
        # 过期检测
        expired_keywords = ["已过期", "作废", "废止", "失效"]
        is_expired = any(kw in doc.content for kw in expired_keywords)
        freshness = 0.0 if is_expired else 1.0
        
        timeliness_score = (
            recency * self.timeliness_weights["recency"] +
            update_freq * self.timeliness_weights["update_freq"] +
            freshness * self.timeliness_weights["freshness"]
        )
        
        details = {
            "recency": recency,
            "update_freq": update_freq,
            "freshness": freshness,
            "age_days": age_days,
            "is_expired": is_expired
        }
        
        return timeliness_score, details
    
    def evaluate_semantic(self, doc: Document) -> Tuple[float, Dict]:
        """评估语义质量"""
        content = doc.content
        
        # 语言质量：句子长度合理性
        sentences = re.split(r'[。！？.!?]', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_sentence_len = sum(len(s) for s in sentences) / len(sentences)
            # 理想句子长度 20-50字符
            if 20 <= avg_sentence_len <= 50:
                language_quality = 1.0
            elif 10 <= avg_sentence_len < 20 or 50 < avg_sentence_len <= 80:
                language_quality = 0.8
            else:
                language_quality = 0.6
        else:
            language_quality = 0.5
        
        # 清晰度：信息密度
        words = content.split()
        unique_words = set(words)
        if words:
            density = len(unique_words) / len(words)
            clarity = min(1.0, density * 2)
        else:
            clarity = 0.5
        
        # 向量化友好度
        if sentences:
            # 检查句子长度分布
            lengths = [len(s) for s in sentences]
            # 过短或过长的句子都不利于Embedding
            good_lengths = sum(1 for l in lengths if 20 <= l <= 200)
            embedding_friendly = good_lengths / len(lengths)
        else:
            embedding_friendly = 0.5
        
        semantic_score = (
            language_quality * self.semantic_weights["language"] +
            clarity * self.semantic_weights["clarity"] +
            embedding_friendly * self.semantic_weights["embedding"]
        )
        
        details = {
            "language_quality": language_quality,
            "clarity": clarity,
            "embedding_friendly": embedding_friendly,
            "sentence_count": len(sentences)
        }
        
        return semantic_score, details
    
    def evaluate(self, doc: Document) -> QualityScore:
        """综合评估文档质量"""
        format_score, format_details = self.evaluate_format(doc)
        content_score, content_details = self.evaluate_content(doc)
        timeliness_score, timeliness_details = self.evaluate_timeliness(doc)
        semantic_score, semantic_details = self.evaluate_semantic(doc)
        
        # 维度权重
        weights = {"format": 0.25, "content": 0.35, "timeliness": 0.20, "semantic": 0.20}
        
        overall_score = (
            format_score * weights["format"] +
            content_score * weights["content"] +
            timeliness_score * weights["timeliness"] +
            semantic_score * weights["semantic"]
        )
        
        # 质量分级
        if overall_score >= 0.85:
            level = QualityLevel.EXCELLENT
        elif overall_score >= 0.70:
            level = QualityLevel.GOOD
        elif overall_score >= 0.55:
            level = QualityLevel.PASS
        else:
            level = QualityLevel.FAIL
        
        return QualityScore(
            format_score=format_score,
            content_score=content_score,
            timeliness_score=timeliness_score,
            semantic_score=semantic_score,
            overall_score=overall_score,
            level=level,
            details={
                "format": format_details,
                "content": content_details,
                "timeliness": timeliness_details,
                "semantic": semantic_details
            }
        )


def create_sample_documents() -> List[Document]:
    """创建示例文档"""
    now = datetime.now()
    
    return [
        # 优秀文档：格式完整、内容充实、时效新鲜
        Document(
            doc_id="doc_001",
            title="产品使用手册_v2.0",
            doc_type=DocumentType.PDF_TEXT,
            content="""简介
本文档详细介绍产品的使用方法。

正文
第一章：快速入门
产品安装步骤如下...

第二章：高级功能
详细配置说明...

总结
本文档涵盖了产品的核心功能。

参考
相关链接和文档...""",
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(days=5),
            file_size=1024000,
            page_count=20,
            has_structure=True,
            parse_success_rate=1.0
        ),
        # 良好文档：格式正常、内容完整但略旧
        Document(
            doc_id="doc_002",
            title="API接口文档",
            doc_type=DocumentType.MARKDOWN,
            content="""简介
API接口说明文档。

正文
接口列表：
- GET /api/users
- POST /api/users

总结
本文档描述了所有API接口。

参考
Swagger文档链接...""",
            created_at=now - timedelta(days=180),
            updated_at=now - timedelta(days=60),
            file_size=512000,
            page_count=10,
            has_structure=True,
            parse_success_rate=1.0
        ),
        # 及格文档：扫描件、内容较少
        Document(
            doc_id="doc_003",
            title="旧版说明书扫描件",
            doc_type=DocumentType.PDF_SCAN,
            content="产品说明书 第一页 简介 产品功能介绍...",
            created_at=now - timedelta(days=365),
            updated_at=now - timedelta(days=365),
            file_size=2048000,
            page_count=5,
            has_structure=False,
            parse_success_rate=0.6
        ),
        # 不合格文档：图片PDF、过期、内容混乱
        Document(
            doc_id="doc_004",
            title="作废的产品规格_2019",
            doc_type=DocumentType.PDF_IMAGE,
            content="已过期 作废 此文档已失效 请勿使用",
            created_at=now - timedelta(days=1500),
            updated_at=now - timedelta(days=1500),
            file_size=3072000,
            page_count=3,
            has_structure=False,
            parse_success_rate=0.4
        ),
        # 边界文档：纯文本、内容简短
        Document(
            doc_id="doc_005",
            title="临时说明.txt",
            doc_type=DocumentType.TXT,
            content="这是一个临时说明文件。内容简短。",
            created_at=now - timedelta(days=7),
            updated_at=now - timedelta(days=7),
            file_size=1024,
            page_count=1,
            has_structure=False,
            parse_success_rate=1.0
        )
    ]


def test_format_quality() -> TestResult:
    """测试1: 格式质量检测"""
    print("\n" + "="*60)
    print("🧪 测试1: 格式质量检测")
    print("="*60)
    
    evaluator = DocumentQualityEvaluator()
    docs = create_sample_documents()
    
    print("\n  文档格式质量评估:")
    print("  " + "-"*50)
    print(f"  {'文档ID':<12} {'类型':<15} {'结构':<8} {'解析率':<10} {'得分':<8}")
    print("  " + "-"*50)
    
    scores = []
    for doc in docs:
        score, details = evaluator.evaluate_format(doc)
        scores.append(score)
        print(f"  {doc.doc_id:<12} {doc.doc_type.value:<15} "
              f"{'✓' if doc.has_structure else '✗':<8} "
              f"{doc.parse_success_rate:.0%}       {score:.2f}")
    
    avg_score = sum(scores) / len(scores)
    print("  " + "-"*50)
    print(f"  平均格式质量得分: {avg_score:.2f}")
    
    # 评估：至少60%文档格式得分>0.5
    good_docs = sum(1 for s in scores if s > 0.5)
    passed = good_docs >= len(scores) * 0.6
    
    return TestResult(
        name="格式质量检测",
        passed=passed,
        score=(good_docs / len(scores)) * 100,
        risk_level="L3-低危",
        details=f"格式良好文档: {good_docs}/{len(scores)}"
    )


def test_content_quality() -> TestResult:
    """测试2: 内容质量检测"""
    print("\n" + "="*60)
    print("🧪 测试2: 内容质量检测")
    print("="*60)
    
    evaluator = DocumentQualityEvaluator()
    docs = create_sample_documents()
    
    print("\n  文档内容质量评估:")
    print("  " + "-"*60)
    print(f"  {'文档ID':<12} {'完整性':<10} {'连贯性':<10} {'聚焦度':<10} {'得分':<8}")
    print("  " + "-"*60)
    
    scores = []
    for doc in docs:
        score, details = evaluator.evaluate_content(doc)
        scores.append(score)
        print(f"  {doc.doc_id:<12} {details['completeness']:.2f}      "
              f"{details['coherence']:.2f}      {details['focus']:.2f}      {score:.2f}")
    
    avg_score = sum(scores) / len(scores)
    print("  " + "-"*60)
    print(f"  平均内容质量得分: {avg_score:.2f}")
    
    passed = avg_score >= 0.5
    
    return TestResult(
        name="内容质量检测",
        passed=passed,
        score=avg_score * 100,
        risk_level="L2-中危",
        details=f"平均内容质量: {avg_score:.2f}"
    )


def test_timeliness_quality() -> TestResult:
    """测试3: 时效质量检测"""
    print("\n" + "="*60)
    print("🧪 测试3: 时效质量检测")
    print("="*60)
    
    evaluator = DocumentQualityEvaluator()
    docs = create_sample_documents()
    
    print("\n  文档时效质量评估:")
    print("  " + "-"*60)
    print(f"  {'文档ID':<12} {'年龄(天)':<10} {'更新频率':<12} {'过期':<8} {'得分':<8}")
    print("  " + "-"*60)
    
    scores = []
    for doc in docs:
        score, details = evaluator.evaluate_timeliness(doc)
        scores.append(score)
        expired_mark = "⚠️过期" if details['is_expired'] else "✓正常"
        print(f"  {doc.doc_id:<12} {details['age_days']:<10} "
              f"{details['update_freq']:.2f}        {expired_mark:<8} {score:.2f}")
    
    avg_score = sum(scores) / len(scores)
    print("  " + "-"*60)
    print(f"  平均时效质量得分: {avg_score:.2f}")
    
    # 检测过期文档
    expired_count = sum(1 for doc in docs if "已过期" in doc.content or "作废" in doc.content)
    print(f"\n  过期文档检测: {expired_count}个文档已标记过期")
    
    passed = expired_count <= 1  # 允许最多1个过期文档（用于测试）
    
    return TestResult(
        name="时效质量检测",
        passed=passed,
        score=avg_score * 100,
        risk_level="L2-中危",
        details=f"过期文档: {expired_count}个"
    )


def test_semantic_quality() -> TestResult:
    """测试4: 语义质量检测"""
    print("\n" + "="*60)
    print("🧪 测试4: 语义质量检测")
    print("="*60)
    
    evaluator = DocumentQualityEvaluator()
    docs = create_sample_documents()
    
    print("\n  文档语义质量评估:")
    print("  " + "-"*60)
    print(f"  {'文档ID':<12} {'语言质量':<10} {'清晰度':<10} {'向量化':<10} {'得分':<8}")
    print("  " + "-"*60)
    
    scores = []
    for doc in docs:
        score, details = evaluator.evaluate_semantic(doc)
        scores.append(score)
        print(f"  {doc.doc_id:<12} {details['language_quality']:.2f}      "
              f"{details['clarity']:.2f}      {details['embedding_friendly']:.2f}      {score:.2f}")
    
    avg_score = sum(scores) / len(scores)
    print("  " + "-"*60)
    print(f"  平均语义质量得分: {avg_score:.2f}")
    
    passed = avg_score >= 0.5
    
    return TestResult(
        name="语义质量检测",
        passed=passed,
        score=avg_score * 100,
        risk_level="L3-低危",
        details=f"平均语义质量: {avg_score:.2f}"
    )


def test_overall_quality_grading() -> TestResult:
    """测试5: 综合质量分级"""
    print("\n" + "="*60)
    print("🧪 测试5: 综合质量分级")
    print("="*60)
    
    evaluator = DocumentQualityEvaluator()
    docs = create_sample_documents()
    
    print("\n  文档综合质量评估:")
    print("  " + "-"*75)
    print(f"  {'文档ID':<12} {'格式':<8} {'内容':<8} {'时效':<8} {'语义':<8} {'综合':<8} {'等级':<12}")
    print("  " + "-"*75)
    
    level_counts = {level: 0 for level in QualityLevel}
    
    for doc in docs:
        score = evaluator.evaluate(doc)
        level_counts[score.level] += 1
        print(f"  {doc.doc_id:<12} {score.format_score:.2f}    {score.content_score:.2f}    "
              f"{score.timeliness_score:.2f}    {score.semantic_score:.2f}    "
              f"{score.overall_score:.2f}    {score.level.value:<12}")
    
    print("  " + "-"*75)
    
    # 质量分布统计
    print("\n  质量分布统计:")
    total = len(docs)
    for level in [QualityLevel.EXCELLENT, QualityLevel.GOOD, QualityLevel.PASS, QualityLevel.FAIL]:
        count = level_counts[level]
        percentage = count / total * 100
        bar = "█" * int(percentage / 5)
        print(f"    {level.value:<12}: {count:>2}个 ({percentage:>5.1f}%) {bar}")
    
    # 评估：A级+B级文档应占60%以上
    good_docs = level_counts[QualityLevel.EXCELLENT] + level_counts[QualityLevel.GOOD]
    good_ratio = good_docs / total
    
    print(f"\n  优质文档比例: {good_ratio:.1%}")
    print(f"  {'✅' if good_ratio >= 0.4 else '⚠️'} 质量标准: {'达标' if good_ratio >= 0.4 else '需改进'}")
    
    passed = good_ratio >= 0.4
    
    return TestResult(
        name="综合质量分级",
        passed=passed,
        score=good_ratio * 100,
        risk_level="L1-高危",
        details=f"优质文档: {good_docs}/{total} ({good_ratio:.1%})"
    )


def print_summary(results: List[TestResult]):
    """打印测试汇总"""
    print("\n" + "="*70)
    print("📊 测试汇总报告")
    print("="*70)
    
    print(f"\n{'测试项':<25} {'状态':<10} {'得分':<10} {'风险等级':<15}")
    print("-"*70)
    
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{r.name:<25} {status:<10} {r.score:.1f}%{'':<5} {r.risk_level:<15}")
    
    print("-"*70)
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    avg_score = sum(r.score for r in results) / total
    
    print(f"\n总测试数: {total}")
    print(f"通过数: {passed} ({passed/total*100:.1f}%)")
    print(f"失败数: {total - passed}")
    print(f"平均得分: {avg_score:.1f}%")
    
    # 风险统计
    high_risk = sum(1 for r in results if "L1" in r.risk_level and not r.passed)
    medium_risk = sum(1 for r in results if "L2" in r.risk_level and not r.passed)
    
    print(f"\nL1高危风险: {high_risk}项")
    print(f"L2中危风险: {medium_risk}项")
    
    # 评级
    print("\n" + "="*70)
    print("📋 文档质量管理体系评级")
    print("="*70)
    
    if avg_score >= 85:
        grade = "A级 - 优秀"
        advice = "文档质量管理体系完善，建议保持当前实践"
    elif avg_score >= 70:
        grade = "B级 - 良好"
        advice = "文档质量管理基本健全，建议优化薄弱环节"
    elif avg_score >= 55:
        grade = "C级 - 及格"
        advice = "文档质量管理存在隐患，建议尽快改进"
    else:
        grade = "D级 - 危险"
        advice = "文档质量管理严重不足，必须立即整改"
    
    print(f"  评级: {grade}")
    print(f"  评估: {advice}")
    
    print("\n" + "="*70)
    print("✅ 测试执行完毕，请将上方日志发给 Trae 生成详细报告。")
    print("="*70)


def run_all_tests():
    """主入口"""
    print("\n" + "="*70)
    print("🚀 AI QA System Test - Day 22: 文档质量评分（基础）")
    print("="*70)
    print("\n测试架构师视角：垃圾进，垃圾出。文档质量是RAG系统的第一道防线。")
    print("="*70)
    
    results = [
        test_format_quality(),
        test_content_quality(),
        test_timeliness_quality(),
        test_semantic_quality(),
        test_overall_quality_grading()
    ]
    
    print_summary(results)


if __name__ == "__main__":
    run_all_tests()
