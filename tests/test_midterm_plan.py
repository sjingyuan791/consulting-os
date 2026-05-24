"""
Tests for Mid-Term Management Plan Engine.
中期経営計画書生成エンジンのテスト。
"""
import pytest
import asyncio
import json
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.schemas.midterm_plan_schema import (
    MidtermPlanDocument, MidtermPlanSection, LogicalDependencyMap,
    CorporatePhilosophy, VisionStatement, ExternalEnvironment,
    InternalEnvironment, RootCauseAnalysis, SWOTAnalysis,
    CrossSWOTStrategy, CorporateStrategySection, BusinessDomainStrategy,
    FunctionalStrategies, StrategicInitiatives, KPIArchitecture,
    FinancialNumericalPlan, SECTION_DEFINITIONS,
    PESTItem, RootCauseItem, CrossSWOTOption, KPIItem, YearlyFinancials
)
from core.midterm_plan_engine import MidtermPlanEngine, create_midterm_plan_engine
from core.midterm_plan_narrative import MidtermPlanNarrative, generate_midterm_plan_report


def run_async(coro):
    """Helper to run async coroutine in sync test"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =============================================
# Schema Validation Tests
# =============================================

class TestSchemaValidation:
    """スキーマバリデーションテスト"""

    def test_corporate_philosophy_creation(self):
        """企業理念モデルが正しく作成できること"""
        phil = CorporatePhilosophy(
            mission="テスト用ミッション",
            core_values=["誠実", "革新"],
            management_philosophy="テスト経営理念"
        )
        assert phil.mission == "テスト用ミッション"
        assert len(phil.core_values) == 2

    def test_vision_statement_creation(self):
        """ビジョンモデルが正しく作成できること"""
        vision = VisionStatement(
            vision_statement="テストビジョン",
            target_year=2029,
            quantitative_goals=["売上10億達成"]
        )
        assert vision.target_year == 2029
        assert len(vision.quantitative_goals) == 1

    def test_external_environment_creation(self):
        """外部環境分析モデルが正しく作成できること"""
        ext = ExternalEnvironment(
            opportunities=["DX推進"],
            threats=["競争激化"]
        )
        assert len(ext.opportunities) == 1
        assert len(ext.threats) == 1
        assert "political" in ext.macro_environment

    def test_internal_environment_creation(self):
        """内部環境分析モデルが正しく作成できること"""
        internal = InternalEnvironment(
            strengths=["技術力"],
            weaknesses=["人材不足"]
        )
        assert len(internal.strengths) == 1

    def test_root_cause_analysis_creation(self):
        """根本原因分析モデルが正しく作成できること"""
        rca = RootCauseAnalysis(
            primary_symptom="収益性低下",
            root_causes=[
                RootCauseItem(
                    cause_id="RC-01",
                    description="コスト構造の問題",
                    severity="critical"
                )
            ]
        )
        assert rca.root_causes[0].severity == "critical"

    def test_swot_analysis_creation(self):
        """SWOT分析モデルが正しく作成できること"""
        swot = SWOTAnalysis(
            strengths=["技術力"],
            weaknesses=["人材不足"],
            opportunities=["DX推進"],
            threats=["競争激化"]
        )
        assert len(swot.strengths) == 1

    def test_cross_swot_creation(self):
        """クロスSWOT戦略モデルが正しく作成できること"""
        cs = CrossSWOTStrategy(
            so_strategies=[
                CrossSWOTOption(strategy_name="攻勢戦略", description="テスト")
            ]
        )
        assert len(cs.so_strategies) == 1

    def test_kpi_architecture_creation(self):
        """KPIアーキテクチャモデルが正しく作成できること"""
        kpi = KPIArchitecture(
            strategic_kpis=[
                KPIItem(
                    kpi_id="KPI-01",
                    name="売上成長率",
                    category="financial",
                    targets={"Y1": 5.0}
                )
            ]
        )
        assert kpi.strategic_kpis[0].targets["Y1"] == 5.0

    def test_financial_plan_creation(self):
        """数値計画モデルが正しく作成できること"""
        fp = FinancialNumericalPlan(
            base_year=2025,
            projections=[
                YearlyFinancials(year=2026, revenue=1050.0)
            ]
        )
        assert fp.projections[0].year == 2026

    def test_all_13_section_definitions_exist(self):
        """13セクション定義が全て存在すること"""
        assert len(SECTION_DEFINITIONS) == 13
        for i, sd in enumerate(SECTION_DEFINITIONS):
            assert sd["id"] == i + 1
            assert "title" in sd
            assert "title_en" in sd
            assert "references" in sd


# =============================================
# Dependency Map Tests
# =============================================

class TestDependencyMap:
    """依存マップテスト"""

    def test_build_from_definitions(self):
        """定義から依存マップが正しく構築されること"""
        dep_map = LogicalDependencyMap.build_from_definitions()
        assert len(dep_map.edges) > 0
        assert len(dep_map.critical_path) == 13

    def test_no_forward_references(self):
        """前方参照が存在しないこと"""
        for sec_def in SECTION_DEFINITIONS:
            for ref_id in sec_def["references"]:
                assert ref_id < sec_def["id"], (
                    f"Section {sec_def['id']} has forward reference to {ref_id}"
                )

    def test_mermaid_output(self):
        """Mermaid出力が正しい形式であること"""
        dep_map = LogicalDependencyMap.build_from_definitions()
        mermaid = dep_map.to_mermaid()
        assert "graph TD" in mermaid
        assert "S1" in mermaid
        assert "S13" in mermaid

    def test_section_1_has_no_references(self):
        """セクション1は参照を持たないこと"""
        assert SECTION_DEFINITIONS[0]["references"] == []

    def test_section_13_references_11_and_12(self):
        """セクション13はセクション11と12を参照すること"""
        refs = SECTION_DEFINITIONS[12]["references"]
        assert 11 in refs
        assert 12 in refs


# =============================================
# Document Validation Tests
# =============================================

class TestDocumentValidation:
    """ドキュメントバリデーションテスト"""

    def _make_sample_sections(self) -> list:
        """テスト用13セクションを生成"""
        sections = []
        for sd in SECTION_DEFINITIONS:
            sections.append(MidtermPlanSection(
                section_id=sd["id"],
                section_title=sd["title"],
                section_title_en=sd["title_en"],
                references=sd["references"],
                narrative=f"テストナラティブ: {sd['title']}",
                data={"test": True}
            ))
        return sections

    def test_valid_section_order(self):
        """正しいセクション順序が認識されること"""
        doc = MidtermPlanDocument(sections=self._make_sample_sections())
        assert doc.validate_section_order()

    def test_invalid_section_order(self):
        """不正なセクション順序が検出されること"""
        sections = self._make_sample_sections()
        sections[0], sections[1] = sections[1], sections[0]  # Swap 1 and 2
        doc = MidtermPlanDocument(sections=sections)
        assert not doc.validate_section_order()

    def test_valid_references(self):
        """正しい参照が検証されること"""
        doc = MidtermPlanDocument(sections=self._make_sample_sections())
        errors = doc.validate_references()
        assert len(errors) == 0

    def test_forward_reference_detected(self):
        """前方参照が検出されること"""
        sections = self._make_sample_sections()
        # Add forward reference to section 1
        sections[0].references = [5]
        doc = MidtermPlanDocument(sections=sections)
        errors = doc.validate_references()
        assert len(errors) > 0
        assert "forward reference" in errors[0].lower()


# =============================================
# Engine Tests
# =============================================

class TestMidtermPlanEngine:
    """エンジンテスト"""

    def test_engine_creation(self):
        """エンジンが正しく作成できること"""
        engine = create_midterm_plan_engine(
            pipeline_data={"test": True},
            guardrails={"mission_objective": "テスト"},
            client_id="test-client"
        )
        assert engine.client_id == "test-client"

    def test_generate_full_plan_without_pipeline(self):
        """パイプラインデータなしでも計画書が生成できること（フォールバック）"""
        engine = create_midterm_plan_engine(
            pipeline_data={},
            guardrails={
                "mission_objective": "テストミッション",
                "success_state_definition": "テストビジョン",
                "time_horizon_years": 3
            },
            client_id="test-client-001"
        )

        doc = run_async(engine.generate_full_plan())

        assert doc is not None
        assert len(doc.sections) == 13
        assert doc.validate_section_order()
        assert len(doc.validate_references()) == 0

    def test_section_narrative_not_empty(self):
        """全セクションのナラティブが空でないこと"""
        engine = create_midterm_plan_engine(
            guardrails={"mission_objective": "テスト"}
        )
        doc = run_async(engine.generate_full_plan())

        for section in doc.sections:
            assert section.narrative, f"Section {section.section_id} has empty narrative"

    def test_section_data_not_empty(self):
        """全セクションのデータが空でないこと"""
        engine = create_midterm_plan_engine(
            guardrails={"mission_objective": "テスト"}
        )
        doc = run_async(engine.generate_full_plan())

        for section in doc.sections:
            assert section.data, f"Section {section.section_id} has empty data"

    def test_dependency_map_generation(self):
        """依存マップが正しく生成されること"""
        engine = create_midterm_plan_engine()
        dep_map = engine.build_dependency_map()
        assert len(dep_map.edges) > 0

    def test_progress_callback(self):
        """プログレスコールバックが呼び出されること"""
        progress_calls = []

        def callback(pct, msg):
            progress_calls.append((pct, msg))

        engine = create_midterm_plan_engine(
            guardrails={"mission_objective": "テスト"}
        )
        doc = run_async(engine.generate_full_plan(progress_callback=callback))

        assert len(progress_calls) > 0
        # Last call should be 100%
        assert progress_calls[-1][0] == 100

    def test_with_pipeline_data(self):
        """パイプラインデータありで計画書が生成できること"""
        pipeline_data = {
            "stage1_output": {
                "analysis_summary": "財務分析のサマリー"
            },
            "stage2_output": {
                "primary_root_cause": {
                    "description": "テスト根本原因",
                    "category": "operational",
                    "supporting_evidence": ["エビデンス1"],
                    "impact_scope": ["売上"]
                },
                "secondary_causes": [],
                "leverage_points": ["レバレッジ1"]
            },
            "internal_capability": {
                "strengths": ["強み1", "強み2"],
                "weaknesses": ["弱み1"],
                "core_competencies": ["コンピタンス1"]
            },
            "external_intelligence": {
                "opportunities": ["機会1"],
                "threats": ["脅威1"]
            },
            "financial_health": {
                "overall_health_score": 65
            }
        }

        engine = create_midterm_plan_engine(
            pipeline_data=pipeline_data,
            guardrails={"mission_objective": "パイプラインテスト"},
            client_id="pipeline-test"
        )
        doc = run_async(engine.generate_full_plan())

        assert len(doc.sections) == 13
        # Check pipeline data is reflected
        swot_section = doc.sections[5]  # Section 6
        assert "強み1" in swot_section.narrative or "強み1" in json.dumps(swot_section.data, ensure_ascii=False)


# =============================================
# Narrative Tests
# =============================================

class TestMidtermPlanNarrative:
    """ナラティブ生成テスト"""

    def _make_sample_document(self) -> MidtermPlanDocument:
        """テスト用ドキュメントを生成"""
        engine = create_midterm_plan_engine(
            guardrails={"mission_objective": "ナラティブテスト"}
        )
        return run_async(engine.generate_full_plan())

    def test_markdown_generation(self):
        """Markdown出力が正しく生成されること"""
        doc = self._make_sample_document()
        narrator = MidtermPlanNarrative(doc)
        md = narrator.generate_full_markdown()

        assert "# 中期経営計画書" in md
        assert "## 目次" in md
        assert "1. 企業理念" in md
        assert "13." in md  # Section 13 exists

    def test_executive_summary_generation(self):
        """エグゼクティブサマリーが生成されること"""
        doc = self._make_sample_document()
        narrator = MidtermPlanNarrative(doc)
        summary = narrator.generate_executive_summary()

        assert "エグゼクティブサマリー" in summary

    def test_json_output(self):
        """JSON出力が正しい構造を持つこと"""
        doc = self._make_sample_document()
        narrator = MidtermPlanNarrative(doc)
        json_output = narrator.generate_json_output()

        assert "document_id" in json_output
        assert "sections" in json_output
        assert len(json_output["sections"]) == 13

    def test_facade_function(self):
        """ファサード関数が3形式出力を返すこと"""
        doc = self._make_sample_document()
        report = generate_midterm_plan_report(doc)

        assert "markdown" in report
        assert "json" in report
        assert "executive_summary" in report
        assert "dependency_mermaid" in report

    def test_dependency_mermaid_in_markdown(self):
        """Markdown内に依存マップMermaidが含まれること"""
        doc = self._make_sample_document()
        narrator = MidtermPlanNarrative(doc)
        md = narrator.generate_full_markdown()

        assert "```mermaid" in md
        assert "graph TD" in md


    def test_dependency_mermaid_in_markdown(self):
        """Markdown内に依存マップMermaidが含まれること"""
        doc = self._make_sample_document()
        narrator = MidtermPlanNarrative(doc)
        md = narrator.generate_full_markdown()

        assert "```mermaid" in md
        assert "graph TD" in md


# =============================================
# Context Lock Tests
# =============================================

class TestContextLock:
    """コンテキストロック機能テスト"""

    def test_build_prompt_context(self):
        """LOCKED章からコンテキストが正しく構築されること"""
        engine = create_midterm_plan_engine()
        # Create locked section
        sec1 = MidtermPlanSection(
            section_id=1, section_title="S1", narrative="N1", data={"d": 1}, references=[]
        )
        sec1.chapter_state.status = "LOCKED" # String matching Enum
        sec1.chapter_state.context_snapshot = "Snapshot1"
        
        ctx = engine.build_prompt_context([sec1])
        assert "Snapshot1" in ctx
        assert "Section 1" in ctx

    @patch("core.midterm_plan_engine.openai_client")
    def test_generate_single_chapter_mock(self, mock_client):
        """単一チャプター生成がLLMを呼び出して正常終了すること"""
        # Mock structured output
        mock_parsed = MagicMock()
        mock_parsed.choices[0].message.parsed = CorporatePhilosophy(mission="M", core_values=[])
        mock_client.beta.chat.completions.parse.return_value = mock_parsed
        
        # Mock narrative output
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Narrative"
        mock_client.chat.completions.create.return_value = mock_resp
        
        engine = create_midterm_plan_engine()
        sec = run_async(engine.generate_single_chapter(1, []))
        
        assert sec.section_id == 1
        assert sec.narrative == "Narrative"
        assert sec.data["mission"] == "M"

    @patch("core.midterm_plan_engine.openai_client")
    def test_chat_with_context(self, mock_client):
        """チャット機能がコンテキストを受け取って応答すること"""
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Response"
        mock_client.chat.completions.create.return_value = mock_resp
        
        engine = create_midterm_plan_engine()
        resp = run_async(engine.chat_with_context("Hi", [], None))
        assert resp == "Response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
