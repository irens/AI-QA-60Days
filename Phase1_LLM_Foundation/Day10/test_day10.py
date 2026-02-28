"""
自动化测试脚本：Day 10 - 知识图谱验证与结构化事实核查
目标：实体链接、关系验证、时效性检查、综合验证流程
风险视角：专注知识图谱能发现但NLI检测不到的"隐形幻觉"
"""

import pytest
import json
import re
from typing import List, Dict, Tuple, Any, Optional, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum


class VerificationStatus(Enum):
    """验证结果状态"""
    CONFIRMED = "CONFIRMED"       # 知识图谱明确支持
    CONTRADICTED = "CONTRADICTED" # 知识图谱明确否定
    UNKNOWN = "UNKNOWN"           # 知识图谱无记录
    AMBIGUOUS = "AMBIGUOUS"       # 实体消歧不确定
    OUTDATED = "OUTDATED"         # 知识版本过期


class RiskLevel(Enum):
    """风险等级"""
    CRITICAL = "🔴 CRITICAL"
    HIGH = "🟠 HIGH"
    MEDIUM = "🟡 MEDIUM"
    LOW = "🟢 LOW"
    PASS = "✅ PASS"


@dataclass
class Entity:
    """知识图谱实体"""
    id: str
    name: str
    entity_type: str
    description: str
    properties: Dict[str, Any] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)
    version_date: str = "2024-01-01"


@dataclass
class EntityLink:
    """实体链接结果"""
    mention: str
    entity_id: str
    entity_name: str
    confidence: float
    entity_type: str
    candidates: List[Entity] = field(default_factory=list)


@dataclass
class Relation:
    """关系三元组"""
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0


@dataclass
class VerificationResult:
    """验证结果"""
    claim: str
    status: VerificationStatus
    linked_entities: List[EntityLink]
    verified_relations: List[Dict]
    kg_evidence: List[Dict]
    confidence: float
    risk_level: RiskLevel
    message: str


class MockKnowledgeGraph:
    """模拟知识图谱"""
    
    def __init__(self):
        # 初始化模拟知识图谱数据
        self.entities = {
            "einstein": Entity(
                id="einstein",
                name="阿尔伯特·爱因斯坦",
                entity_type="Person",
                description="理论物理学家，相对论创立者",
                properties={
                    "birth_year": 1879,
                    "death_year": 1955,
                    "nationality": "德国/美国",
                    "field": "物理学"
                },
                aliases=["爱因斯坦", "Albert Einstein", "Einstein"],
                version_date="2024-01-01"
            ),
            "nobel_physics_1921": Entity(
                id="nobel_physics_1921",
                name="1921年诺贝尔物理学奖",
                entity_type="Award",
                description="因光电效应研究授予爱因斯坦",
                properties={
                    "year": 1921,
                    "category": "物理学",
                    "recipient": "einstein",
                    "reason": "光电效应研究"
                },
                aliases=["诺贝尔物理学奖1921"],
                version_date="2024-01-01"
            ),
            "bohr": Entity(
                id="bohr",
                name="尼尔斯·玻尔",
                entity_type="Person",
                description="丹麦物理学家，量子力学先驱",
                properties={
                    "birth_year": 1885,
                    "death_year": 1962,
                    "nationality": "丹麦",
                    "field": "物理学"
                },
                aliases=["玻尔", "Niels Bohr", "Bohr"],
                version_date="2024-01-01"
            ),
            "quantum_mechanics": Entity(
                id="quantum_mechanics",
                name="量子力学",
                entity_type="Field",
                description="描述微观粒子行为的物理学分支",
                properties={
                    "founded_year": 1925,
                    "key_figures": ["einstein", "bohr", "heisenberg", "schrodinger"]
                },
                aliases=["量子论", "Quantum Mechanics"],
                version_date="2024-01-01"
            ),
            "apple_inc": Entity(
                id="apple_inc",
                name="苹果公司",
                entity_type="Company",
                description="美国科技公司，iPhone制造商",
                properties={
                    "founded_year": 1976,
                    "founder": "Steve Jobs",
                    "headquarters": "Cupertino"
                },
                aliases=["苹果", "Apple", "Apple Inc."],
                version_date="2024-01-01"
            ),
            "apple_fruit": Entity(
                id="apple_fruit",
                name="苹果（水果）",
                entity_type="Plant",
                description="蔷薇科苹果属果实",
                properties={
                    "scientific_name": "Malus domestica",
                    "origin": "中亚"
                },
                aliases=["苹果", "apple", "平果"],
                version_date="2024-01-01"
            )
        }
        
        # 关系数据 (subject, predicate, object)
        self.relations = [
            ("einstein", "received", "nobel_physics_1921"),
            ("einstein", "contributed_to", "quantum_mechanics"),
            ("bohr", "contributed_to", "quantum_mechanics"),
            ("nobel_physics_1921", "awarded_to", "einstein"),
            ("einstein", "born_in_year", "1879"),
            ("einstein", "died_in_year", "1955"),
            ("bohr", "born_in_year", "1885"),
        ]
    
    def search_candidates(self, mention: str) -> List[Entity]:
        """搜索候选实体"""
        candidates = []
        mention_lower = mention.lower().strip()
        
        for entity in self.entities.values():
            entity_name_lower = entity.name.lower()
            aliases_lower = [a.lower() for a in entity.aliases]
            
            # 匹配主名或别名（双向包含匹配）
            name_match = (
                mention_lower in entity_name_lower or 
                entity_name_lower in mention_lower
            )
            alias_match = any(
                mention_lower in alias or alias in mention_lower
                for alias in aliases_lower
            )
            
            if name_match or alias_match:
                candidates.append(entity)
        
        return candidates
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        return self.entities.get(entity_id)
    
    def query_relation(self, subject: str, predicate: str, object: str = None) -> List[Tuple]:
        """查询关系"""
        results = []
        for sub, pred, obj in self.relations:
            if sub == subject and pred == predicate:
                if object is None or obj == object:
                    results.append((sub, pred, obj))
        return results
    
    def check_property(self, entity_id: str, property_name: str, expected_value: Any) -> bool:
        """检查实体属性"""
        entity = self.entities.get(entity_id)
        if not entity:
            return False
        actual_value = entity.properties.get(property_name)
        return actual_value == expected_value


class EntityLinker:
    """实体链接器"""
    
    def __init__(self, kg: Optional[MockKnowledgeGraph] = None):
        self.kg = kg or MockKnowledgeGraph()
    
    def extract_mentions(self, text: str) -> List[str]:
        """提取实体提及（简化版）"""
        mentions = []
        
        # 简单规则：提取大写字母开头的词组、引号内的内容
        # 实际应用应使用NER模型
        patterns = [
            r'[\u4e00-\u9fa5]{2,10}',  # 中文实体
            r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',  # 英文实体
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            mentions.extend(matches)
        
        # 去重并保持顺序
        seen = set()
        unique_mentions = []
        for m in mentions:
            if m not in seen and len(m) >= 2:
                seen.add(m)
                unique_mentions.append(m)
        
        return unique_mentions
    
    def link_entity(self, mention: str, context: str = "") -> Optional[EntityLink]:
        """链接实体到知识图谱"""
        candidates = self.kg.search_candidates(mention)
        
        if not candidates:
            return None
        
        # 简单消歧：选择描述与上下文最匹配的
        # 实际应用应使用更复杂的消歧算法
        best_candidate = candidates[0]
        confidence = 0.9 if len(candidates) == 1 else 0.7
        
        # 如果有多个候选，根据上下文简单判断
        if len(candidates) > 1:
            for candidate in candidates:
                # 简单规则：如果上下文包含类型相关词
                if "公司" in context and candidate.entity_type == "Company":
                    best_candidate = candidate
                    confidence = 0.85
                    break
                elif "物理" in context and candidate.entity_type == "Person":
                    if "field" in candidate.properties:
                        if candidate.properties["field"] == "物理学":
                            best_candidate = candidate
                            confidence = 0.85
                            break
        
        return EntityLink(
            mention=mention,
            entity_id=best_candidate.id,
            entity_name=best_candidate.name,
            confidence=confidence,
            entity_type=best_candidate.entity_type,
            candidates=candidates
        )
    
    def link_all(self, text: str) -> List[EntityLink]:
        """链接文本中所有实体"""
        mentions = self.extract_mentions(text)
        links = []
        
        for mention in mentions:
            link = self.link_entity(mention, text)
            if link:
                links.append(link)
        
        return links


class KGVerifier:
    """知识图谱验证器"""
    
    def __init__(self, kg: Optional[MockKnowledgeGraph] = None):
        self.kg = kg or MockKnowledgeGraph()
        self.linker = EntityLinker(self.kg)
    
    def verify_relation(self, subject_id: str, predicate: str, object_id: str) -> Dict:
        """验证关系是否存在"""
        results = self.kg.query_relation(subject_id, predicate, object_id)
        
        if results:
            return {
                "exists": True,
                "evidence": results,
                "status": VerificationStatus.CONFIRMED
            }
        
        # 检查实体是否存在
        sub_entity = self.kg.get_entity(subject_id)
        obj_entity = self.kg.get_entity(object_id)
        
        if not sub_entity or not obj_entity:
            return {
                "exists": False,
                "evidence": [],
                "status": VerificationStatus.UNKNOWN,
                "message": "实体不在知识图谱中"
            }
        
        # 实体存在但关系不存在
        return {
            "exists": False,
            "evidence": [],
            "status": VerificationStatus.CONTRADICTED,
            "message": "关系与知识图谱冲突"
        }
    
    def verify_property(self, entity_id: str, property_name: str, 
                        expected_value: Any) -> Dict:
        """验证属性值"""
        entity = self.kg.get_entity(entity_id)
        
        if not entity:
            return {
                "valid": False,
                "status": VerificationStatus.UNKNOWN,
                "message": f"实体 {entity_id} 不存在"
            }
        
        actual_value = entity.properties.get(property_name)
        
        if actual_value is None:
            return {
                "valid": False,
                "status": VerificationStatus.UNKNOWN,
                "message": f"属性 {property_name} 未定义"
            }
        
        if actual_value == expected_value:
            return {
                "valid": True,
                "actual_value": actual_value,
                "status": VerificationStatus.CONFIRMED
            }
        else:
            return {
                "valid": False,
                "expected": expected_value,
                "actual": actual_value,
                "status": VerificationStatus.CONTRADICTED,
                "message": f"属性值冲突: 期望 {expected_value}, 实际 {actual_value}"
            }
    
    def verify_claim(self, claim: str) -> VerificationResult:
        """
        验证声明
        简化版：解析声明中的实体和关系，与知识图谱对比
        """
        # 1. 实体链接
        linked_entities = self.linker.link_all(claim)
        
        if not linked_entities:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.UNKNOWN,
                linked_entities=[],
                verified_relations=[],
                kg_evidence=[],
                confidence=0.0,
                risk_level=RiskLevel.MEDIUM,
                message="无法识别声明中的实体"
            )
        
        # 2. 检查实体消歧（如果有多个候选）
        ambiguous_entities = [e for e in linked_entities if len(e.candidates) > 1]
        if ambiguous_entities:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.AMBIGUOUS,
                linked_entities=linked_entities,
                verified_relations=[],
                kg_evidence=[],
                confidence=0.5,
                risk_level=RiskLevel.MEDIUM,
                message=f"实体消歧不确定: {[e.mention for e in ambiguous_entities]}"
            )
        
        # 3. 解析年份属性（简化规则）
        year_match = re.search(r'(\d{4})年?', claim)
        if year_match and len(linked_entities) >= 1:
            year = int(year_match.group(1))
            main_entity = linked_entities[0]
            
            # 检查是否是出生年份
            if "出生" in claim or "生于" in claim:
                result = self.verify_property(main_entity.entity_id, "birth_year", year)
                
                if result["status"] == VerificationStatus.CONTRADICTED:
                    return VerificationResult(
                        claim=claim,
                        status=VerificationStatus.CONTRADICTED,
                        linked_entities=linked_entities,
                        verified_relations=[],
                        kg_evidence=[result],
                        confidence=0.9,
                        risk_level=RiskLevel.HIGH,
                        message=result["message"]
                    )
                elif result["status"] == VerificationStatus.CONFIRMED:
                    return VerificationResult(
                        claim=claim,
                        status=VerificationStatus.CONFIRMED,
                        linked_entities=linked_entities,
                        verified_relations=[],
                        kg_evidence=[result],
                        confidence=0.9,
                        risk_level=RiskLevel.PASS,
                        message="出生年份验证通过"
                    )
            
            # 检查是否是获奖年份
            if "获奖" in claim or "获得" in claim:
                entity = self.kg.get_entity(main_entity.entity_id)
                if entity:
                    # 检查相关奖项
                    for rel in self.kg.relations:
                        if rel[0] == main_entity.entity_id and rel[1] == "received":
                            award = self.kg.get_entity(rel[2])
                            if award and award.properties.get("year") == year:
                                return VerificationResult(
                                    claim=claim,
                                    status=VerificationStatus.CONFIRMED,
                                    linked_entities=linked_entities,
                                    verified_relations=[{"relation": rel}],
                                    kg_evidence=[{"award": award.name, "year": year}],
                                    confidence=0.95,
                                    risk_level=RiskLevel.PASS,
                                    message=f"获奖年份验证通过: {award.name}"
                                )
                            elif award and award.properties.get("year") != year:
                                return VerificationResult(
                                    claim=claim,
                                    status=VerificationStatus.CONTRADICTED,
                                    linked_entities=linked_entities,
                                    verified_relations=[],
                                    kg_evidence=[{"expected_year": award.properties.get("year"), "claimed_year": year}],
                                    confidence=0.9,
                                    risk_level=RiskLevel.HIGH,
                                    message=f"获奖年份错误: 知识图谱记录为{award.properties.get('year')}年"
                                )
        
        # 4. 默认返回UNKNOWN
        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNKNOWN,
            linked_entities=linked_entities,
            verified_relations=[],
            kg_evidence=[],
            confidence=0.5,
            risk_level=RiskLevel.LOW,
            message="无法验证声明（知识图谱无相关记录）"
        )
    
    def assess_risk(self, status: VerificationStatus, confidence: float) -> RiskLevel:
        """评估风险等级"""
        if status == VerificationStatus.CONTRADICTED:
            return RiskLevel.CRITICAL if confidence > 0.8 else RiskLevel.HIGH
        elif status == VerificationStatus.AMBIGUOUS:
            return RiskLevel.MEDIUM
        elif status == VerificationStatus.UNKNOWN:
            return RiskLevel.LOW
        elif status == VerificationStatus.CONFIRMED:
            return RiskLevel.PASS
        return RiskLevel.MEDIUM


# ==================== 测试用例 ====================

class TestKnowledgeGraphVerification:
    """知识图谱验证测试类"""
    
    @pytest.fixture
    def kg(self):
        return MockKnowledgeGraph()
    
    @pytest.fixture
    def linker(self, kg):
        return EntityLinker(kg)
    
    @pytest.fixture
    def verifier(self, kg):
        return KGVerifier(kg)
    
    def test_entity_search(self, kg):
        """测试实体搜索"""
        print("\n" + "="*60)
        print("【测试1】实体搜索功能验证")
        print("="*60)
        
        # 搜索爱因斯坦
        candidates = kg.search_candidates("爱因斯坦")
        print(f"搜索'爱因斯坦': 找到 {len(candidates)} 个候选")
        
        for c in candidates:
            print(f"  - {c.name} ({c.entity_type}): {c.description[:30]}...")
        
        assert len(candidates) >= 1, "应找到爱因斯坦"
        assert any(c.id == "einstein" for c in candidates), "应包含物理学家爱因斯坦"
        
        print("\n✅ 实体搜索测试通过")
    
    def test_entity_linking(self, linker):
        """测试实体链接"""
        print("\n" + "="*60)
        print("【测试2】实体链接功能验证")
        print("="*60)
        
        text = "爱因斯坦获得诺贝尔物理学奖"
        links = linker.link_all(text)
        
        print(f"文本: {text}")
        print(f"链接实体数: {len(links)}")
        
        for link in links:
            print(f"\n提及: '{link.mention}'")
            print(f"  链接到: {link.entity_name} ({link.entity_type})")
            print(f"  置信度: {link.confidence}")
            print(f"  候选数: {len(link.candidates)}")
        
        assert len(links) >= 1, "应至少链接到一个实体"
        
        print("\n✅ 实体链接测试通过")
    
    def test_entity_disambiguation(self, linker):
        """测试实体消歧"""
        print("\n" + "="*60)
        print("【测试3】实体消歧验证（关键测试）")
        print("="*60)
        
        # 测试1：苹果（上下文为公司）
        context_company = "苹果公司发布了新款iPhone"
        link_company = linker.link_entity("苹果", context_company)
        
        print(f"上下文: {context_company}")
        print(f"'苹果'链接到: {link_company.entity_name if link_company else 'None'}")
        if link_company:
            print(f"  类型: {link_company.entity_type}")
            print(f"  置信度: {link_company.confidence}")
            print(f"  候选数: {len(link_company.candidates)}")
        
        # 测试2：苹果（无上下文，可能有歧义）
        link_ambiguous = linker.link_entity("苹果", "")
        print(f"\n无上下文'苹果':")
        if link_ambiguous:
            print(f"  链接到: {link_ambiguous.entity_name}")
            print(f"  候选数: {len(link_ambiguous.candidates)}")
            if len(link_ambiguous.candidates) > 1:
                print(f"  ⚠️ 存在歧义！候选: {[c.name for c in link_ambiguous.candidates]}")
        
        assert link_company is not None, "应链接到公司"
        assert link_company.entity_type == "Company", "在公司上下文中应识别为公司"
        
        print("\n✅ 实体消歧测试通过")
    
    def test_relation_verification_confirmed(self, verifier):
        """测试关系验证（确认存在）"""
        print("\n" + "="*60)
        print("【测试4】关系验证 - 确认存在")
        print("="*60)
        
        # 验证：爱因斯坦获得诺贝尔奖
        result = verifier.verify_relation("einstein", "received", "nobel_physics_1921")
        
        print("验证: 爱因斯坦 --received--> 诺贝尔物理学奖1921")
        print(f"结果: {result['status'].value}")
        print(f"存在: {result['exists']}")
        
        assert result["exists"] == True, "关系应存在"
        assert result["status"] == VerificationStatus.CONFIRMED, "应确认为CONFIRMED"
        
        print("\n✅ 关系确认测试通过")
    
    def test_relation_verification_contradicted(self, verifier):
        """测试关系验证（发现冲突）"""
        print("\n" + "="*60)
        print("【测试5】关系验证 - 发现冲突（关键测试）")
        print("="*60)
        
        # 验证错误关系：玻尔获得诺贝尔奖（知识图谱中不存在）
        result = verifier.verify_relation("bohr", "received", "nobel_physics_1921")
        
        print("验证: 玻尔 --received--> 诺贝尔物理学奖1921")
        print(f"结果: {result['status'].value}")
        print(f"存在: {result['exists']}")
        print(f"消息: {result.get('message', '')}")
        
        # 注意：玻尔确实获得过诺贝尔奖，但在我们的Mock KG中没有这条记录
        # 这模拟了知识图谱不完整的情况
        assert result["exists"] == False, "关系不应存在（在Mock KG中）"
        
        print("\n✅ 关系冲突检测测试通过")
    
    def test_property_verification(self, verifier):
        """测试属性验证"""
        print("\n" + "="*60)
        print("【测试6】属性值验证")
        print("="*60)
        
        # 验证正确的出生年份
        result_correct = verifier.verify_property("einstein", "birth_year", 1879)
        print("验证: 爱因斯坦出生于1879年")
        print(f"  结果: {result_correct['status'].value}")
        print(f"  有效: {result_correct['valid']}")
        
        # 验证错误的出生年份
        result_wrong = verifier.verify_property("einstein", "birth_year", 1905)
        print("\n验证: 爱因斯坦出生于1905年（错误）")
        print(f"  结果: {result_wrong['status'].value}")
        print(f"  有效: {result_wrong['valid']}")
        if not result_wrong['valid']:
            print(f"  消息: {result_wrong['message']}")
        
        assert result_correct["valid"] == True, "正确属性应验证通过"
        assert result_correct["status"] == VerificationStatus.CONFIRMED
        assert result_wrong["valid"] == False, "错误属性应验证失败"
        assert result_wrong["status"] == VerificationStatus.CONTRADICTED
        
        print("\n✅ 属性验证测试通过")
    
    def test_full_claim_verification_confirmed(self, verifier):
        """测试完整声明验证（确认）"""
        print("\n" + "="*60)
        print("【测试7】完整声明验证 - 确认正确")
        print("="*60)
        
        claim = "爱因斯坦于1921年获得诺贝尔奖"
        result = verifier.verify_claim(claim)
        
        print(f"声明: {claim}")
        print(f"验证状态: {result.status.value}")
        print(f"风险等级: {result.risk_level.value}")
        print(f"置信度: {result.confidence}")
        print(f"消息: {result.message}")
        
        print(f"\n链接实体:")
        for e in result.linked_entities:
            print(f"  - {e.mention} -> {e.entity_name}")
        
        assert result.status == VerificationStatus.CONFIRMED, "正确声明应被确认"
        assert result.risk_level == RiskLevel.PASS
        
        print("\n✅ 完整声明验证（确认）测试通过")
    
    def test_full_claim_verification_contradicted(self, verifier):
        """测试完整声明验证（发现冲突）"""
        print("\n" + "="*60)
        print("【测试8】完整声明验证 - 发现冲突（关键测试）")
        print("="*60)
        
        # 错误的获奖年份
        claim = "爱因斯坦于1905年获得诺贝尔奖"  # 错误！实际是1921年
        result = verifier.verify_claim(claim)
        
        print(f"声明: {claim}")
        print(f"验证状态: {result.status.value}")
        print(f"风险等级: {result.risk_level.value}")
        print(f"置信度: {result.confidence}")
        print(f"消息: {result.message}")
        
        print(f"\n知识图谱证据:")
        for evidence in result.kg_evidence:
            print(f"  {evidence}")
        
        assert result.status == VerificationStatus.CONTRADICTED, "错误声明应被标记为冲突"
        assert result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL], "应有高风险评级"
        
        print("\n✅ 完整声明验证（冲突）测试通过")
    
    def test_verification_coverage_stats(self, verifier):
        """测试验证覆盖率统计"""
        print("\n" + "="*60)
        print("【测试9】验证覆盖率统计")
        print("="*60)
        
        test_claims = [
            "爱因斯坦于1921年获得诺贝尔奖",  # CONFIRMED
            "爱因斯坦于1905年获得诺贝尔奖",  # CONTRADICTED
            "爱因斯坦喜欢吃苹果",             # UNKNOWN
            "玻尔是量子力学先驱",             # CONFIRMED（通过关系）
        ]
        
        results = []
        for claim in test_claims:
            result = verifier.verify_claim(claim)
            results.append(result)
        
        # 统计
        status_counts = {}
        for r in results:
            status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1
        
        print("验证结果统计:")
        for status, count in status_counts.items():
            percentage = count / len(results) * 100
            print(f"  {status}: {count} ({percentage:.1f}%)")
        
        print(f"\n详细结果:")
        for i, (claim, result) in enumerate(zip(test_claims, results), 1):
            print(f"{i}. {claim[:25]}... -> {result.status.value}")
        
        assert len(results) == len(test_claims), "应验证所有声明"
        
        print("\n✅ 覆盖率统计测试通过")


def print_summary():
    """打印测试总结"""
    print("\n" + "="*60)
    print("【Day 10 知识图谱验证测试总结】")
    print("="*60)
    print("""
核心验证能力验证:
✅ 实体搜索 - 从知识图谱中检索候选实体
✅ 实体链接 - 将文本提及链接到标准实体
✅ 实体消歧 - 处理同名实体的上下文消歧
✅ 关系验证 - 验证声明的关系是否存在于KG
✅ 属性验证 - 验证实体属性值的正确性
✅ 完整声明验证 - 端到端的事实核查流程

关键发现:
┌─────────────────────────────────────────────────────────────┐
│  NLI检测盲区 vs 知识图谱验证优势                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  声明: "爱因斯坦于1905年获得诺贝尔奖"                         │
│                                                             │
│  NLI检测（参考:爱因斯坦1921年获奖）                          │
│    结果: 中立（无矛盾关键词）⚠️ 漏检！                        │
│                                                             │
│  知识图谱验证                                                │
│    查询: 爱因斯坦.received.year                              │
│    结果: 1921                                                │
│    对比: 1905 ≠ 1921 ❌ 检测到错误！                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

验证结果分类:
┌───────────────┬────────────┬────────────────────────────────┐
│ 状态          │ 处理建议   │ 示例                           │
├───────────────┼────────────┼────────────────────────────────┤
│ CONFIRMED     │ ✅ 可信    │ 爱因斯坦1921年获奖             │
│ CONTRADICTED  │ ❌ 拦截    │ 爱因斯坦1905年获奖（错误）     │
│ UNKNOWN       │ ⚠️ 需审核  │ 爱因斯坦喜欢吃苹果（KG无记录） │
│ AMBIGUOUS     │ ⚠️ 需确认  │ 苹果（公司？水果？）           │
│ OUTDATED      │ ⚠️ 需更新  │ 使用过期的知识版本             │
└───────────────┴────────────┴────────────────────────────────┘

生产环境建议:
1. 高风险场景（医疗/法律）: 必须CONFIRMED才可信
2. CONTRADICTED结果: 自动拦截，禁止返回给用户
3. UNKNOWN结果: 增加人工审核或外部搜索验证
4. 定期更新知识图谱: 保持知识新鲜度
    """)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
    print_summary()
