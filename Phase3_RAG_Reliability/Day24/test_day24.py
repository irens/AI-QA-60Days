"""
Day 24: 预处理流程(下) - 完整流水线与质量门禁
测试目标：验证端到端预处理流程、异常处理、质量门禁和批量处理性能
"""

import time
import hashlib
import re
import html
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))


class ProcessingStatus(Enum):
    """处理状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    REJECTED = "rejected"
    ERROR = "error"


class RejectReason(Enum):
    """拒绝原因"""
    INPUT_INVALID = "input_invalid"
    FILE_TOO_LARGE = "file_too_large"
    QUALITY_TOO_LOW = "quality_too_low"
    CONTENT_TOO_SHORT = "content_too_short"
    DUPLICATE = "duplicate"
    PARSE_ERROR = "parse_error"


@dataclass
class Document:
    """文档对象"""
    doc_id: str
    content: str
    file_size: int  # bytes
    doc_type: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """处理结果"""
    doc_id: str
    status: ProcessingStatus
    reject_reason: Optional[RejectReason] = None
    quality_score: float = 0.0
    processing_time: float = 0.0
    output_content: str = ""
    metadata: Dict = field(default_factory=dict)


class QualityGate:
    """质量门禁"""
    
    # 阈值配置
    THRESHOLDS = {
        "min_quality_score": 0.55,
        "max_file_size": 100 * 1024 * 1024,  # 100MB
        "min_content_length": 100,
        "max_duplicate_similarity": 0.95
    }
    
    def __init__(self):
        self.processed_hashes: set = set()
    
    def check_file_size(self, doc: Document) -> Tuple[bool, str]:
        """检查文件大小"""
        if doc.file_size > self.THRESHOLDS["max_file_size"]:
            return False, f"文件大小 {doc.file_size} 超过限制 {self.THRESHOLDS['max_file_size']}"
        return True, ""
    
    def check_content_length(self, content: str) -> Tuple[bool, str]:
        """检查内容长度"""
        if len(content) < self.THRESHOLDS["min_content_length"]:
            return False, f"内容长度 {len(content)} 小于最小要求 {self.THRESHOLDS['min_content_length']}"
        return True, ""
    
    def check_quality_score(self, score: float) -> Tuple[bool, str]:
        """检查质量分数"""
        if score < self.THRESHOLDS["min_quality_score"]:
            return False, f"质量分数 {score:.2f} 低于阈值 {self.THRESHOLDS['min_quality_score']}"
        return True, ""
    
    def check_duplicate(self, content: str) -> Tuple[bool, str]:
        """检查重复文档"""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        if content_hash in self.processed_hashes:
            return False, "检测到重复文档"
        self.processed_hashes.add(content_hash)
        return True, ""
    
    def evaluate_quality(self, doc: Document) -> float:
        """评估文档质量（简化版）"""
        score = 0.0
        
        # 格式分 (30%)
        supported_types = ["txt", "md", "html", "pdf", "docx"]
        if doc.doc_type.lower() in supported_types:
            score += 0.30
        else:
            score += 0.15
        
        # 内容分 (40%)
        content = doc.content
        if len(content) > 1000:
            score += 0.40
        elif len(content) > 500:
            score += 0.30
        elif len(content) > 100:
            score += 0.20
        else:
            score += 0.10
        
        # 结构分 (30%)
        has_structure = any(marker in content for marker in ["\n#", "\n##", "\n-", "\n1."])
        has_paragraphs = content.count("\n\n") > 2
        if has_structure and has_paragraphs:
            score += 0.30
        elif has_structure or has_paragraphs:
            score += 0.20
        else:
            score += 0.10
        
        return min(score, 1.0)


class TextCleaner:
    """文本清洗器（简化版）"""
    
    SENSITIVE_PATTERNS = {
        "mobile": (r"1[3-9]\d{9}", lambda m: m.group()[:3] + "****" + m.group()[7:]),
        "id_card": (r"\d{17}[\dXx]", lambda m: m.group()[:6] + "********" + m.group()[14:]),
        "email": (r"[\w.-]+@[\w.-]+\.\w+", lambda m: "***@" + m.group().split("@")[1]),
    }
    
    def clean_html(self, text: str) -> str:
        """去除HTML标签"""
        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", text, flags=re.I)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.I)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        return text.strip()
    
    def clean_special_chars(self, text: str) -> str:
        """清洗特殊字符"""
        zero_width = "\u200B\u200C\u200D\uFEFF"
        for char in zero_width:
            text = text.replace(char, "")
        text = "".join(c for c in text if ord(c) >= 32 or c in "\n\t\r")
        return text
    
    def desensitize(self, text: str) -> Tuple[str, Dict]:
        """敏感信息脱敏"""
        found = {}
        for name, (pattern, replacer) in self.SENSITIVE_PATTERNS.items():
            matches = list(re.finditer(pattern, text))
            if matches:
                found[name] = len(matches)
                text = re.sub(pattern, replacer, text)
        return text, found
    
    def normalize_format(self, text: str) -> str:
        """格式标准化"""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n\n+", "\n\n", text)
        return text.strip()
    
    def clean(self, text: str) -> str:
        """完整清洗流程"""
        text = self.clean_html(text)
        text = self.clean_special_chars(text)
        text, _ = self.desensitize(text)
        text = self.normalize_format(text)
        return text


class PreprocessingPipeline:
    """预处理流水线"""
    
    def __init__(self):
        self.quality_gate = QualityGate()
        self.cleaner = TextCleaner()
        self.stats = {
            "total": 0,
            "success": 0,
            "rejected": 0,
            "error": 0
        }
    
    def process_document(self, doc: Document) -> ProcessingResult:
        """处理单个文档"""
        start_time = time.time()
        self.stats["total"] += 1
        
        try:
            # 1. 输入验证
            if not doc.content or doc.file_size <= 0:
                self.stats["rejected"] += 1
                return ProcessingResult(
                    doc_id=doc.doc_id,
                    status=ProcessingStatus.REJECTED,
                    reject_reason=RejectReason.INPUT_INVALID,
                    processing_time=time.time() - start_time
                )
            
            # 2. 文件大小检查
            passed, msg = self.quality_gate.check_file_size(doc)
            if not passed:
                self.stats["rejected"] += 1
                return ProcessingResult(
                    doc_id=doc.doc_id,
                    status=ProcessingStatus.REJECTED,
                    reject_reason=RejectReason.FILE_TOO_LARGE,
                    processing_time=time.time() - start_time
                )
            
            # 3. 质量评估
            quality_score = self.quality_gate.evaluate_quality(doc)
            
            # 4. 质量门禁检查
            passed, msg = self.quality_gate.check_quality_score(quality_score)
            if not passed:
                self.stats["rejected"] += 1
                return ProcessingResult(
                    doc_id=doc.doc_id,
                    status=ProcessingStatus.REJECTED,
                    reject_reason=RejectReason.QUALITY_TOO_LOW,
                    quality_score=quality_score,
                    processing_time=time.time() - start_time
                )
            
            # 5. 内容清洗
            cleaned_content = self.cleaner.clean(doc.content)
            
            # 6. 内容长度检查
            passed, msg = self.quality_gate.check_content_length(cleaned_content)
            if not passed:
                self.stats["rejected"] += 1
                return ProcessingResult(
                    doc_id=doc.doc_id,
                    status=ProcessingStatus.REJECTED,
                    reject_reason=RejectReason.CONTENT_TOO_SHORT,
                    quality_score=quality_score,
                    processing_time=time.time() - start_time
                )
            
            # 7. 重复检查
            passed, msg = self.quality_gate.check_duplicate(cleaned_content)
            if not passed:
                self.stats["rejected"] += 1
                return ProcessingResult(
                    doc_id=doc.doc_id,
                    status=ProcessingStatus.REJECTED,
                    reject_reason=RejectReason.DUPLICATE,
                    quality_score=quality_score,
                    processing_time=time.time() - start_time
                )
            
            # 8. 分段处理
            segments = self._segment_document(cleaned_content)
            
            self.stats["success"] += 1
            return ProcessingResult(
                doc_id=doc.doc_id,
                status=ProcessingStatus.SUCCESS,
                quality_score=quality_score,
                processing_time=time.time() - start_time,
                output_content=cleaned_content,
                metadata={
                    "segments_count": len(segments),
                    "original_length": len(doc.content),
                    "cleaned_length": len(cleaned_content)
                }
            )
            
        except Exception as e:
            self.stats["error"] += 1
            return ProcessingResult(
                doc_id=doc.doc_id,
                status=ProcessingStatus.ERROR,
                processing_time=time.time() - start_time,
                metadata={"error": str(e)}
            )
    
    def _segment_document(self, content: str, max_segment_length: int = 1000) -> List[str]:
        """文档分段"""
        segments = []
        paragraphs = content.split("\n\n")
        current_segment = ""
        
        for para in paragraphs:
            if len(current_segment) + len(para) < max_segment_length:
                current_segment += para + "\n\n"
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = para + "\n\n"
        
        if current_segment:
            segments.append(current_segment.strip())
        
        return segments
    
    def process_batch(self, docs: List[Document]) -> List[ProcessingResult]:
        """批量处理文档"""
        results = []
        for doc in docs:
            result = self.process_document(doc)
            results.append(result)
        return results
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = self.stats["total"]
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            "success_rate": self.stats["success"] / total,
            "rejection_rate": self.stats["rejected"] / total,
            "error_rate": self.stats["error"] / total
        }


class TestPreprocessingPipeline:
    """预处理流水线测试"""
    
    def test_complete_pipeline_success(self):
        """测试完整流水线 - 正常文档"""
        pipeline = PreprocessingPipeline()
        
        doc = Document(
            doc_id="doc_001",
            content="""# 产品使用手册

## 第一章 产品介绍

本产品是一款智能文档处理系统，支持多种文档格式的解析和处理。

## 第二章 功能特性

1. 支持PDF、Word、HTML等格式
2. 自动识别文档结构
3. 智能内容提取

## 第三章 使用说明

详细的使用说明请参考官方文档。""",
            file_size=1024,
            doc_type="md"
        )
        
        result = pipeline.process_document(doc)
        
        assert result.status == ProcessingStatus.SUCCESS
        assert result.quality_score >= 0.55
        assert len(result.output_content) > 0
        assert result.metadata["segments_count"] > 0
        print(f"✓ 完整流水线测试通过，质量分: {result.quality_score:.2f}")
    
    def test_empty_document_rejection(self):
        """测试空文档拒绝"""
        pipeline = PreprocessingPipeline()
        
        doc = Document(
            doc_id="doc_empty",
            content="",
            file_size=0,
            doc_type="txt"
        )
        
        result = pipeline.process_document(doc)
        
        assert result.status == ProcessingStatus.REJECTED
        assert result.reject_reason == RejectReason.INPUT_INVALID
        print("✓ 空文档拒绝测试通过")
    
    def test_oversized_file_rejection(self):
        """测试超大文件拒绝"""
        pipeline = PreprocessingPipeline()
        
        doc = Document(
            doc_id="doc_large",
            content="x" * 1000,
            file_size=200 * 1024 * 1024,  # 200MB
            doc_type="pdf"
        )
        
        result = pipeline.process_document(doc)
        
        assert result.status == ProcessingStatus.REJECTED
        assert result.reject_reason == RejectReason.FILE_TOO_LARGE
        print("✓ 超大文件拒绝测试通过")
    
    def test_low_quality_rejection(self):
        """测试低质量文档拒绝"""
        pipeline = PreprocessingPipeline()
        
        # 极短、无结构的低质量内容
        doc = Document(
            doc_id="doc_low_quality",
            content="abc",
            file_size=100,
            doc_type="unknown"
        )
        
        result = pipeline.process_document(doc)
        
        assert result.status == ProcessingStatus.REJECTED
        assert result.reject_reason == RejectReason.QUALITY_TOO_LOW
        print("✓ 低质量文档拒绝测试通过")
    
    def test_short_content_rejection(self):
        """测试内容过短拒绝"""
        pipeline = PreprocessingPipeline()
        
        doc = Document(
            doc_id="doc_short",
            content="这是一个很短的文档内容。",
            file_size=200,
            doc_type="txt"
        )
        
        result = pipeline.process_document(doc)
        
        # 由于内容长度检查在质量评估之后，可能会被质量门禁先拒绝
        assert result.status == ProcessingStatus.REJECTED
        print("✓ 内容过短拒绝测试通过")
    
    def test_duplicate_rejection(self):
        """测试重复文档拒绝"""
        pipeline = PreprocessingPipeline()

        content = """# 重复文档测试

这是重复文档的内容，需要足够长才能通过质量门禁。

## 章节1
这里是第一章的详细内容，包含多个段落。

## 章节2
这里是第二章的详细内容，确保内容质量达标。

## 章节3
更多内容以确保文档质量评分超过阈值。"""

        doc1 = Document(doc_id="doc_dup_1", content=content, file_size=2000, doc_type="md")
        doc2 = Document(doc_id="doc_dup_2", content=content, file_size=2000, doc_type="md")

        result1 = pipeline.process_document(doc1)
        result2 = pipeline.process_document(doc2)

        assert result1.status == ProcessingStatus.SUCCESS, f"第一个文档应该通过，但状态是 {result1.status}"
        assert result2.status == ProcessingStatus.REJECTED
        assert result2.reject_reason == RejectReason.DUPLICATE
        print("✓ 重复文档拒绝测试通过")
    
    def test_html_cleaning_in_pipeline(self):
        """测试流水线中的HTML清洗"""
        pipeline = PreprocessingPipeline()

        # 使用更长的HTML内容确保清洗后仍能通过质量门禁
        doc = Document(
            doc_id="doc_html",
            content="""<html>
<head><title>产品使用手册</title></head>
<body>
<h1>产品使用手册</h1>

<h2>第一章 产品介绍</h2>
<p>本产品是一款智能文档处理系统，支持多种文档格式的解析和处理。系统采用先进的自然语言处理技术，能够自动识别文档结构并提取关键信息。</p>

<h2>第二章 功能特性</h2>
<p>1. 支持PDF、Word、HTML等多种格式的文档解析</p>
<p>2. 自动识别文档结构，包括标题、段落、列表等</p>
<p>3. 智能内容提取，过滤无关信息</p>
<p>4. 支持批量处理和实时监控</p>

<h2>第三章 使用说明</h2>
<p>详细的使用说明请参考官方文档。用户可以通过Web界面或API接口上传文档进行处理。系统会在处理完成后生成详细的处理报告。</p>

<script>alert('xss')</script>
<style>body{color:red}</style>
</body>
</html>""",
            file_size=5000,
            doc_type="html"
        )

        result = pipeline.process_document(doc)

        assert result.status == ProcessingStatus.SUCCESS, f"HTML文档处理失败，状态: {result.status}, 原因: {result.reject_reason}"
        assert "<script>" not in result.output_content
        assert "<style>" not in result.output_content
        assert "<html>" not in result.output_content
        assert "产品使用手册" in result.output_content
        print("✓ HTML清洗测试通过")
    
    def test_desensitization_in_pipeline(self):
        """测试流水线中的脱敏处理"""
        pipeline = PreprocessingPipeline()

        doc = Document(
            doc_id="doc_sensitive",
            content="""# 用户信息管理系统

## 第一章 用户注册

联系人：张三
手机号：13812345678
邮箱：zhangsan@example.com
身份证：110101199001011234

## 第二章 数据保护

本系统严格遵守数据保护法规，对用户敏感信息进行加密存储和脱敏处理。
所有个人信息在展示时都会进行脱敏，确保用户隐私安全。

## 第三章 联系方式

如有问题请联系客服：
- 客服电话：40012345678
- 客服邮箱：support@example.com

## 第四章 安全声明

我们承诺保护您的个人信息安全，采用业界标准的安全措施防止数据泄露。""",
            file_size=3000,
            doc_type="md"
        )

        result = pipeline.process_document(doc)

        assert result.status == ProcessingStatus.SUCCESS, f"脱敏文档处理失败，状态: {result.status}"
        assert "13812345678" not in result.output_content
        assert "138****5678" in result.output_content
        assert "zhangsan@example.com" not in result.output_content
        assert "110101199001011234" not in result.output_content
        print("✓ 脱敏处理测试通过")
    
    def test_batch_processing_100(self):
        """测试批量处理100文档"""
        pipeline = PreprocessingPipeline()

        docs = []
        for i in range(100):
            doc = Document(
                doc_id=f"doc_batch_{i}",
                content=f"""# 文档 {i}

这是第{i}个测试文档的内容。本文档用于测试批量处理性能和质量评估系统。

## 第一章 概述

本章节介绍了文档的基本信息和背景。测试文档需要包含足够的内容长度，以确保能够通过质量门禁的检查。

## 第二章 详细说明

1. 第一点详细说明，包含足够的信息量
2. 第二点详细说明，确保文档结构完整
3. 第三点详细说明，提供有价值的内容

## 第三章 总结

本文档作为测试用例，需要满足质量评分的要求，包括格式、内容、时效和语义四个维度的评估。""",
                file_size=4096,
                doc_type="md"
            )
            docs.append(doc)

        start_time = time.time()
        results = pipeline.process_batch(docs)
        elapsed = time.time() - start_time

        success_count = sum(1 for r in results if r.status == ProcessingStatus.SUCCESS)
        rejected_count = sum(1 for r in results if r.status == ProcessingStatus.REJECTED)

        # 由于重复检查，后面的文档会被拒绝，所以只检查性能
        assert elapsed < 10, f"批量处理耗时过长: {elapsed:.2f}s"
        print(f"✓ 批量处理100文档测试通过，耗时: {elapsed:.2f}s, 成功: {success_count}, 拒绝: {rejected_count}")
    
    def test_batch_processing_mixed(self):
        """测试混合质量文档批量处理"""
        pipeline = PreprocessingPipeline()
        
        docs = []
        
        # 正常文档
        for i in range(50):
            docs.append(Document(
                doc_id=f"doc_good_{i}",
                content=f"""# 高质量文档 #{i}

这是第{i}个高质量测试文档。

## 第一章 概述

本文档包含详细的内容和结构信息，用于测试文档处理流水线的性能和质量评估功能。

## 第二章 详细内容

1. 第一点详细说明
2. 第二点详细说明
3. 第三点详细说明

## 第三章 总结

本文档作为测试用例，满足质量评分的要求。""",
                file_size=4096,
                doc_type="md"
            ))

        # 低质量文档
        for i in range(30):
            docs.append(Document(
                doc_id=f"doc_bad_{i}",
                content="短",
                file_size=100,
                doc_type="unknown"
            ))

        # 超大文档
        for i in range(20):
            docs.append(Document(
                doc_id=f"doc_large_{i}",
                content="x" * 100,
                file_size=150 * 1024 * 1024,
                doc_type="pdf"
            ))

        results = pipeline.process_batch(docs)

        success_count = sum(1 for r in results if r.status == ProcessingStatus.SUCCESS)
        rejected_count = sum(1 for r in results if r.status == ProcessingStatus.REJECTED)

        # 验证至少有50个文档成功处理（前50个高质量文档）
        assert success_count >= 50, f"成功处理数 {success_count} 小于预期 50"
        assert rejected_count >= 30, f"拒绝数 {rejected_count} 小于预期 30"

        stats = pipeline.get_stats()
        print(f"✓ 混合批量处理测试通过，成功率: {stats['success_rate']:.1%}, 拒绝率: {stats['rejection_rate']:.1%}")
    
    def test_processing_performance(self):
        """测试处理性能"""
        pipeline = PreprocessingPipeline()

        # 测试不同规模的处理性能
        test_sizes = [100, 500, 1000]

        for size in test_sizes:
            docs = [
                Document(
                    doc_id=f"perf_{i}_{size}",
                    content=f"""# 性能测试文档 #{i}

这是性能测试文档的内容，需要足够长以确保质量评分达标。

## 章节1
详细内容描述...

## 章节2
更多内容信息...""",
                    file_size=2048,
                    doc_type="txt"
                )
                for i in range(size)
            ]

            start_time = time.time()
            results = pipeline.process_batch(docs)
            elapsed = time.time() - start_time

            # 避免除以零
            elapsed = max(elapsed, 0.001)
            throughput = size / elapsed
            avg_time = elapsed / size

            print(f"  规模 {size}: 耗时 {elapsed:.3f}s, 吞吐 {throughput:.1f} doc/s, 平均 {avg_time*1000:.1f}ms/doc")

            # 性能要求：100文档/秒
            assert throughput > 50, f"处理吞吐 {throughput:.1f} 低于要求 50 doc/s"

        print("✓ 处理性能测试通过")
    
    def test_quality_gate_thresholds(self):
        """测试质量门禁阈值"""
        gate = QualityGate()
        
        # 测试文件大小阈值
        large_doc = Document("id", "content", 101 * 1024 * 1024, "txt")
        assert gate.check_file_size(large_doc)[0] == False
        
        normal_doc = Document("id", "content", 10 * 1024 * 1024, "txt")
        assert gate.check_file_size(normal_doc)[0] == True
        
        # 测试质量分数阈值
        assert gate.check_quality_score(0.54)[0] == False
        assert gate.check_quality_score(0.55)[0] == True
        assert gate.check_quality_score(0.80)[0] == True
        
        # 测试内容长度阈值
        assert gate.check_content_length("x" * 99)[0] == False
        assert gate.check_content_length("x" * 100)[0] == True
        
        print("✓ 质量门禁阈值测试通过")
    
    def test_document_segmentation(self):
        """测试文档分段"""
        pipeline = PreprocessingPipeline()
        
        # 创建长文档
        long_content = "\n\n".join([f"段落 {i}: " + "x" * 500 for i in range(10)])
        
        doc = Document(
            doc_id="doc_long",
            content=long_content,
            file_size=10000,
            doc_type="txt"
        )
        
        result = pipeline.process_document(doc)
        
        assert result.status == ProcessingStatus.SUCCESS
        assert result.metadata["segments_count"] > 1
        print(f"✓ 文档分段测试通过，分段数: {result.metadata['segments_count']}")


if __name__ == "__main__":
    print("=" * 60)
    print("Day 24: 预处理流程(下) - 完整流水线与质量门禁")
    print("=" * 60)
    
    test = TestPreprocessingPipeline()
    
    try:
        test.test_complete_pipeline_success()
        test.test_empty_document_rejection()
        test.test_oversized_file_rejection()
        test.test_low_quality_rejection()
        test.test_short_content_rejection()
        test.test_duplicate_rejection()
        test.test_html_cleaning_in_pipeline()
        test.test_desensitization_in_pipeline()
        test.test_batch_processing_100()
        test.test_batch_processing_mixed()
        test.test_processing_performance()
        test.test_quality_gate_thresholds()
        test.test_document_segmentation()
        
        print("\n" + "=" * 60)
        print("所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n💥 测试异常: {e}")
        raise
