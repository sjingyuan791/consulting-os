"""
Mid-Term Management Plan Engine.
中期経営計画書のコアエンジン。

13セクションを順次生成し、各セクション間の論理的因果連続性を保証する。
既存パイプライン（Stage1-6）の出力データとGuardrails情報を活用する。
"""
import json
import uuid
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

from core.schemas.midterm_plan_schema import (
    MidtermPlanDocument, MidtermPlanSection, LogicalDependencyMap,
    CorporatePhilosophy, VisionStatement, ExternalEnvironment,
    InternalEnvironment, RootCauseAnalysis, SWOTAnalysis,
    CrossSWOTStrategy, CorporateStrategySection, BusinessDomainStrategy,
    FunctionalStrategies, StrategicInitiatives, KPIArchitecture,
    FinancialNumericalPlan, SECTION_DEFINITIONS,
    PESTItem, CompetitorProfile, ResourceAssessment, RootCauseItem,
    CrossSWOTOption, DomainStrategyItem, FunctionalStrategyItem,
    InitiativeItem, KPIItem, YearlyFinancials,
    ChapterStatus, ChapterState,
    QualityCheckResult, QAAxisScore, QAIssueItem
)
from core.schemas.refinement_schema import (
    RefinedStrategicPlan, FinancialSimulation, SimulationYear, FinancialModelAssumptions,
    ExternalConstraints, SimulationTrace, DecisionGradeStatus
)
from core.quality_gate_enhanced import check_strategic_refinement_quality
from core.llm_client import client as openai_client
from core.llm_router import LLMRouter
from core.llm_router import LLMRouter
from core.rag_service import get_rag_service
from core.framework_evaluator import FrameworkEvaluator

# Extended Definitions including Schema Classes
SECTION_DEFINITIONS_WITH_SCHEMA = [
    {"id": 1, "title": "企業理念", "title_en": "Corporate Philosophy", "references": [], "schema": CorporatePhilosophy},
    {"id": 2, "title": "ビジョン", "title_en": "Vision", "references": [1], "schema": VisionStatement},
    {"id": 3, "title": "外部環境分析", "title_en": "External Environment Analysis", "references": [], "schema": ExternalEnvironment},
    {"id": 4, "title": "内部環境分析", "title_en": "Internal Environment Analysis", "references": [], "schema": InternalEnvironment},
    {"id": 5, "title": "根本原因分析", "title_en": "Root Cause Analysis", "references": [3, 4], "schema": RootCauseAnalysis},
    {"id": 6, "title": "SWOT分析", "title_en": "SWOT Analysis", "references": [3, 4, 5], "schema": SWOTAnalysis},
    {"id": 7, "title": "クロスSWOT戦略", "title_en": "Cross SWOT Strategy", "references": [6], "schema": CrossSWOTStrategy},
    {"id": 8, "title": "全社戦略", "title_en": "Corporate Strategy", "references": [1, 2, 5, 7], "schema": CorporateStrategySection},
    {"id": 9, "title": "事業ドメイン戦略", "title_en": "Business Domain Strategy", "references": [8, 7], "schema": BusinessDomainStrategy},
    {"id": 10, "title": "機能別戦略", "title_en": "Functional Strategies", "references": [8, 9], "schema": FunctionalStrategies},
    {"id": 11, "title": "施策", "title_en": "Strategic Initiatives", "references": [5, 7, 8, 9, 10], "schema": StrategicInitiatives},
    {"id": 12, "title": "KPIアーキテクチャ", "title_en": "KPI Architecture", "references": [8, 9, 10, 11], "schema": KPIArchitecture},
    {"id": 13, "title": "数値計画", "title_en": "Financial and Numerical Plan", "references": [11, 12], "schema": FinancialNumericalPlan},
]
from core.agents.analysts import FinancialAnalyst, MarketResearcher, InternalAuditor
from core.agents.strategist import StrategyDirector, DevilsAdvocate

SECTION_ID_TO_MODEL = {
    1: CorporatePhilosophy,
    2: VisionStatement,
    3: ExternalEnvironment,
    4: InternalEnvironment,
    5: RootCauseAnalysis,
    6: SWOTAnalysis,
    7: CrossSWOTStrategy,
    8: CorporateStrategySection,
    9: BusinessDomainStrategy,
    10: FunctionalStrategies,
    11: StrategicInitiatives,
    12: KPIArchitecture,
    13: FinancialNumericalPlan
}

logger = logging.getLogger(__name__)


# =============================================
# Section-level LLM Prompts
# =============================================

from core.prompts.midterm_plan_prompts import (
    SECTION_SYSTEM_PROMPT,
    MIDTERM_PLAN_SECTION_PROMPT_TEMPLATE,
    QUALITY_CHECK_SYSTEM_PROMPT,
    NARRATIVE_GENERATION_TEMPLATE,
    CONTEXT_CHAT_SYSTEM_PROMPT,
    PROMPT_INSTRUCTION_PHILOSOPHY,
    PROMPT_INSTRUCTION_VISION,
    PROMPT_INSTRUCTION_EXTERNAL,
    PROMPT_INSTRUCTION_INTERNAL,
    PROMPT_INSTRUCTION_ROOT_CAUSE,
    PROMPT_INSTRUCTION_SWOT,
    PROMPT_INSTRUCTION_CROSS_SWOT,
    PROMPT_INSTRUCTION_CORPORATE_STRATEGY,
    PROMPT_INSTRUCTION_DOMAIN_STRATEGY,
    PROMPT_INSTRUCTION_FUNCTIONAL,
    PROMPT_INSTRUCTION_INITIATIVES,
    PROMPT_INSTRUCTION_KPI,
    PROMPT_INSTRUCTION_FINANCIAL
)


# NOTE: グローバル関数版は削除済み。インスタンスメソッド self._build_section_prompt() を使用すること。


class MidtermPlanEngine:
    """
    中期経営計画書生成エンジン。
    
    13セクションを順次生成し、各セクション間の論理的因果連続性を保証する。
    """
    
    SECTION_ID_TO_KEY = {
        1: "philosophy",
        2: "vision",
        3: "external",
        4: "internal",
        5: "root_cause",
        6: "swot",
        7: "cross_swot",
        8: "corporate_strategy",
        9: "domain_strategy",
        10: "functional",
        11: "initiatives",
        12: "kpi",
        13: "financial"
    }

    def __init__(
        self,
        pipeline_data: Optional[Dict[str, Any]] = None,
        guardrails: Optional[Dict[str, Any]] = None,
        client_id: str = ""
    ):
        """
        Args:
            pipeline_data: 既存パイプライン(Stage1-6)の出力データ
            guardrails: GuardrailsSchema相当のデータ
            client_id: クライアントID
        """
        self.pipeline_data = pipeline_data or {}
        self.guardrails = guardrails or {}
        self.client_id = client_id
        self.generated_sections: List[MidtermPlanSection] = []
        self.generated_sections: List[MidtermPlanSection] = []
        self.typed_sections: Dict[str, Any] = {}
        
        # Refinement schemas
        from core.schemas.refinement_schema import (
            RefinedStrategicPlan, FinancialSimulation, SimulationYear, FinancialModelAssumptions
        )
        self.RefinedStrategicPlan = RefinedStrategicPlan
        
        # Initialize RAG Service
        self.rag_service = get_rag_service()
        
        # Initialize Framework Evaluator
        self.framework_evaluator = FrameworkEvaluator()

        # Initialize Agents (Phase 2: Multi-Agent System)
        self.financial_analyst = FinancialAnalyst(client_id)
        self.market_researcher = MarketResearcher(client_id)
        self.internal_auditor = InternalAuditor(client_id)
        self.strategy_director = StrategyDirector(client_id)
        self.devils_advocate = DevilsAdvocate(client_id)
        
        # Store agent outputs to prevent pipeline disconnection
        # Store agent outputs to prevent pipeline disconnection
        self.agent_reports: Dict[str, str] = {}
        
        # Validation errors for debugging
        self.validation_errors: List[str] = []

    async def _run_analysts(self):
        """Phase 1: Run 3 Analysts in parallel to gather deep insights."""
        logger.info("Starting Analyst Phase...")
        
        # Prepare contexts
        external_data = self.pipeline_data.get("external", {})
        internal_data = self.pipeline_data.get("internal", {})
        financial_data = self.pipeline_data.get("financial", {})
        industry = self.pipeline_data.get("industry", "General")
        
        rag_query_ext = "外部環境 市場トレンド 競合 動向 PEST分析 機会 脅威"
        rag_query_int = "内部環境 自社の強み 弱み 組織課題 リソース ヒト・モノ・カネ"
        
        # Define tasks
        async def run_market():
            try:
                rag_context = self._get_rag_context(rag_query_ext)
                res = await self.market_researcher.run({
                    "external_data": external_data,
                    "industry": industry,
                    "rag_context": rag_context
                })
                return "market", res.narrative
            except Exception as e:
                logger.error(f"MarketResearcher failed: {e}")
                return "market", ""

        async def run_internal():
            try:
                # rag_context = self._get_rag_context(rag_query_int) # Internal might not need much external RAG
                res = await self.internal_auditor.run({
                    "internal_data": internal_data,
                    "financial_data": financial_data
                })
                return "internal", res.narrative
            except Exception as e:
                logger.error(f"InternalAuditor failed: {e}")
                return "internal", ""

        async def run_financial():
            try:
                res = await self.financial_analyst.run({
                    "financial_data": financial_data
                })
                return "financial", res.narrative
            except Exception as e:
                logger.error(f"FinancialAnalyst failed: {e}")
                return "financial", ""

        # Execute in parallel
        results = await asyncio.gather(run_market(), run_internal(), run_financial())
        
        for key, report in results:
            self.agent_reports[key] = report
            logger.info(f"Analyst Report Generated: {key} ({len(report)} chars)")

    # =============================================
    # Main Entry Point
    # =============================================

    async def generate_full_plan(
        self,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> MidtermPlanDocument:
        """
        13セクション全体を順次生成する。
        Phase 1: Analysts (Parallel)
        Phase 2: Strategy & Drafting (Sequential)
        """
        self.generated_sections = []
        self.typed_sections = {}
        
        # Phase 1: Run Analysts
        if progress_callback:
            progress_callback(5, "The Boardroom: 3人の専門分析官が分析中...")
        
        await self._run_analysts()

        generators = [
            self._generate_section_01_philosophy,
            self._generate_section_02_vision,
            self._generate_section_03_external,
            self._generate_section_04_internal,
            self._generate_section_05_root_cause,
            self._generate_section_06_swot,
            self._generate_section_07_cross_swot,
            self._generate_section_08_corporate_strategy,
            self._generate_section_09_domain_strategy,
            self._generate_section_10_functional,
            self._generate_section_11_initiatives,
            self._generate_section_12_kpi,
            self._generate_section_13_financial,
        ]

        for i, gen_func in enumerate(generators):
            sec_def = SECTION_DEFINITIONS[i]
            if progress_callback:
                pct = int((i / 13) * 100)
                progress_callback(pct, f"セクション{sec_def['id']}: {sec_def['title']} を生成中...")

            try:
                section = await gen_func()
                self.generated_sections.append(section)
                
                # ★ BUG-2 FIX: typed_sectionsに型付きデータを格納（セクション間データ連携の要）
                self._store_typed_section(sec_def["id"], section)
                
                logger.info(f"Section {sec_def['id']} generated: {sec_def['title']}")
            except Exception as e:
                logger.error(f"Section {sec_def['id']} generation failed: {e}")
                # Generate a fallback section
                fallback = MidtermPlanSection(
                    section_id=sec_def["id"],
                    section_title=sec_def["title"],
                    section_title_en=sec_def["title_en"],
                    references=sec_def["references"],
                    narrative=f"※ このセクションの生成中にエラーが発生しました: {str(e)}",
                    data={}
                )
                self.generated_sections.append(fallback)

        if progress_callback:
            progress_callback(100, "計画書の生成が完了しました。")

        # Build document
        doc = MidtermPlanDocument(
            document_id=str(uuid.uuid4()),
            client_id=self.client_id,
            plan_period="3年",
            sections=self.generated_sections,
            corporate_philosophy=self.typed_sections.get("philosophy"),
            vision=self.typed_sections.get("vision"),
            external_environment=self.typed_sections.get("external"),
            internal_environment=self.typed_sections.get("internal"),
            root_cause_analysis=self.typed_sections.get("root_cause"),
            swot_analysis=self.typed_sections.get("swot"),
            cross_swot_strategy=self.typed_sections.get("cross_swot"),
            corporate_strategy=self.typed_sections.get("corporate_strategy"),
            business_domain_strategy=self.typed_sections.get("domain_strategy"),
            functional_strategies=self.typed_sections.get("functional"),
            strategic_initiatives=self.typed_sections.get("initiatives"),
            kpi_architecture=self.typed_sections.get("kpi"),
            financial_plan=self.typed_sections.get("financial"),
            dependency_map=LogicalDependencyMap.build_from_definitions()
        )

        return doc

    # =============================================
    # Context Lock & Dual Pane Support
    # =============================================

    def build_prompt_context(self, locked_chapters: List[MidtermPlanSection]) -> str:
        """LOCKED章のスナップショットからプロンプト用コンテキストを構築"""
        context_parts = []
        for chapter in locked_chapters:
            # LOCKED状態でもスナップショットが無い場合（移行時など）は現在値を使用
            if chapter.chapter_state and chapter.chapter_state.context_snapshot:
                content = chapter.chapter_state.context_snapshot
            else:
                content = f"{chapter.narrative}\n\nData: {json.dumps(chapter.data, ensure_ascii=False, default=str)}"
            
            context_parts.append(f"### Section {chapter.section_id}: {chapter.section_title}\n{content}")
        
        return "\n\n".join(context_parts)

    async def generate_single_chapter(
        self,
        chapter_id: int,
        locked_chapters: List[MidtermPlanSection],
        user_input: str = "",
        current_content: Optional[MidtermPlanSection] = None
    ) -> MidtermPlanSection:
        """
        単一チャプターを生成する（コンテキストロック対応）。
        ユーザー指示がある場合はLLMを使用して生成する。
        """
        sec_def = SECTION_DEFINITIONS[chapter_id - 1]
        section_model = SECTION_ID_TO_MODEL.get(chapter_id)
        
        # 1. コンテキスト構築
        context_str = self.build_prompt_context(locked_chapters)
        
        # 2. スキーマ情報をプロンプトに含める
        schema_hint = ""
        if section_model:
            try:
                schema_hint = f"\n## 出力JSONスキーマ\n```json\n{json.dumps(section_model.model_json_schema(), ensure_ascii=False, indent=2)}\n```"
            except Exception:
                schema_hint = ""
        
        # 3. プロンプト構築
        feedback_context = ""
        feedback_list = []
        if current_content and hasattr(current_content, "feedback_history"):
            # Unresolved feedback only
            unresolved = [f for f in current_content.feedback_history if not f.resolved]
            if unresolved:
                feedback_list = [f"- {f.content}" for f in unresolved]
                feedback_str = "\n".join(feedback_list)
                feedback_context = f"\n\n## 過去のフィードバック (修正指示)\n以下の以前のフィードバックを必ず反映して修正してください:\n{feedback_str}"

        system_msg = f"""{SECTION_SYSTEM_PROMPT}

## 承認済みコンテキスト（変更不可）
{context_str}

你是以下の2つをJSON形式で出力してください:
1. "narrative": プロフェッショナルなコンサルティングレポート形式のマークダウンテキスト（400-800文字）
2. "data": セクションの構造化データ（下記のスキーマに従う）
{schema_hint}"""
        
        user_msg = f"""
        セクション{chapter_id}「{sec_def['title']}」を作成してください。
        
        ## ユーザー指示
        {user_input if user_input else "標準的な内容で作成してください。"}
        {feedback_context}
        
        ## 前回の内容（参考）
        {current_content.narrative if current_content else "なし"}
        
        JSON形式で {{ "narrative": "...", "data": {{...}} }} を出力してください。
        """

        # 4. LLM生成 (JSON mode - Dict型を含むスキーマでも安全)
        try:
            model = LLMRouter.route("analysis")
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=8192
            )
            
            result = json.loads(response.choices[0].message.content)
            narrative_text = result.get("narrative", "")
            
            # ★ フラットJSON対応: "data"キーがなければnarrative以外を全てdataとして扱う
            if "data" in result and isinstance(result["data"], dict):
                data_dict = result["data"]
            else:
                data_dict = {k: v for k, v in result.items() if k != "narrative"}
            
            # ナラティブが空の場合はデータから生成
            if not narrative_text and data_dict:
                narrative_prompt = NARRATIVE_GENERATION_TEMPLATE.format(
                    section_id=chapter_id,
                    section_title=sec_def['title'],
                    data_context=json.dumps(data_dict, ensure_ascii=False, default=str)
                )
                
                narrative_resp = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SECTION_SYSTEM_PROMPT},
                        {"role": "user", "content": narrative_prompt}
                    ],
                    max_tokens=4096
                )
                narrative_text = narrative_resp.choices[0].message.content

            # Preserve feedback history
            preserved_feedback = []
            if current_content and hasattr(current_content, "feedback_history"):
                preserved_feedback = current_content.feedback_history

            # Preserve ai_draft_snapshot: 初回生成時のみ設定。再生成時は既存スナップショットを引き継ぐ
            existing_snapshot = getattr(current_content, "ai_draft_snapshot", None) if current_content else None
            snapshot = existing_snapshot if existing_snapshot else narrative_text

            return self._make_section(
                chapter_id, narrative_text, data_dict,
                feedback_history=preserved_feedback,
                ai_draft_snapshot=snapshot
            )

        except Exception as e:
            logger.error(f"Generate single chapter failed: {e}")
            raise e

    async def chat_with_context(
        self,
        user_message: str,
        locked_chapters: List[MidtermPlanSection],
        current_chapter: Optional[MidtermPlanSection]
    ) -> str:
        """右ペインのAIチャット応答"""
        context_str = self.build_prompt_context(locked_chapters)
        
        current_str = ""
        if current_chapter:
            current_str = f"## 現在編集中のチャプター (Section {current_chapter.section_id})\n{current_chapter.narrative}"

        system_msg = CONTEXT_CHAT_SYSTEM_PROMPT.format(
            context_str=context_str,
            current_str=current_str
        )
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content

    # =============================================
    # Dependency Map
    # =============================================

    def build_dependency_map(self) -> LogicalDependencyMap:
        """論理依存マップを構築"""
        return LogicalDependencyMap.build_from_definitions()

    # =============================================
    # Helper Methods
    # =============================================

    # ★ BUG-2 FIX: セクション生成結果をtyped_sectionsに格納するメソッド
    SECTION_ID_TO_KEY = {
        1: "philosophy", 2: "vision", 3: "external", 4: "internal",
        5: "root_cause", 6: "swot", 7: "cross_swot", 8: "corporate_strategy",
        9: "domain_strategy", 10: "functional", 11: "initiatives",
        12: "kpi", 13: "financial"
    }

    def _store_typed_section(self, section_id: int, section: MidtermPlanSection) -> None:
        """
        セクション生成結果をtyped_sectionsに型付きオブジェクトとして格納する。
        これにより後続セクションが前セクションのデータにアクセスできる。
        """
        key = self.SECTION_ID_TO_KEY.get(section_id)
        if not key:
            return
        
        model_class = SECTION_ID_TO_MODEL.get(section_id)
        if model_class and section.data:
            try:
                typed_obj = model_class(**section.data)
                self.typed_sections[key] = typed_obj
                logger.info(f"Stored typed section: {key} ({model_class.__name__})")
            except Exception as e:
                err_msg = f"Failed to parse section {section_id} data into {model_class.__name__}: {e}"
                logger.warning(err_msg)
                self.validation_errors.append(err_msg)
                # データのパースに失敗しても、rawデータをNoneとして格納しない
        else:
            logger.debug(f"No data to store for section {section_id} ({key})")

    def _build_section_prompt(
        self,
        section_id: int,
        section_title: str,
        previous_sections_summary: str,
        pipeline_data_context: str,
        specific_instructions: str,
        rag_context: str = ""
    ) -> str:
        """
        各セクション生成用のプロンプトを構築するヘルパーメソッド。
        
        Args:
            section_id: セクション番号
            section_title: セクションタイトル
            previous_sections_summary: 前工程の要約
            pipeline_data_context: パイプラインデータや検索結果
            specific_instructions: このセクション固有の生成指示
            rag_context: RAG検索結果（オプション）
        """
        guardrails_context = json.dumps(self.guardrails, ensure_ascii=False, default=str)
        
        rag_section = ""
        if rag_context:
            rag_section = f"\n\n### 参考資料 (RAG Retrieval)\n{rag_context}"

        return MIDTERM_PLAN_SECTION_PROMPT_TEMPLATE.format(
            section_id=section_id,
            section_title=section_title,
            guardrails_context=guardrails_context,
            previous_sections_summary=previous_sections_summary,
            pipeline_data_context=pipeline_data_context,
            rag_section=rag_section,
            specific_instructions=specific_instructions,
            schema_name=SECTION_DEFINITIONS_WITH_SCHEMA[section_id-1]['schema'].__name__
        )

    def _get_previous_sections_summary(self, section_id: int) -> str:
        """指定セクションが参照すべき前セクションの要約を生成"""
        sec_def = SECTION_DEFINITIONS_WITH_SCHEMA[section_id - 1]
        ref_ids = sec_def["references"]

        if not ref_ids:
            return "（このセクションは最初のセクションです。前セクションの参照はありません。）"

        summaries = []
        for ref_id in ref_ids:
            ref_section = next(
                (s for s in self.generated_sections if s.section_id == ref_id),
                None
            )
            if ref_section:
                # Truncate narrative to keep prompt size manageable
                narrative_preview = ref_section.narrative[:500]
                summaries.append(
                    f"### セクション{ref_id}: {ref_section.section_title}\n"
                    f"{narrative_preview}\n"
                    f"構造化データ: {json.dumps(ref_section.data, ensure_ascii=False, default=str)[:800]}"
                )
        
        return "\n\n".join(summaries) if summaries else "（参照データなし）"

    def _get_rag_context(self, query: str) -> str:
        """RAGサービスを使用してコンテキストを取得"""
        try:
            # get_context() は文字列を返す（rag_query()はRAGResponseオブジェクトを返すため使わない）
            context = self.rag_service.get_context(self.client_id, query)
            return context if context else ""
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return ""

    def _get_pipeline_context(self, context_keys: List[str]) -> str:
        """パイプラインデータから指定キーのコンテキストを取得"""
        parts = []
        for key in context_keys:
            if key in self.pipeline_data:
                data = self.pipeline_data[key]
                if isinstance(data, dict):
                    parts.append(f"### {key}\n{json.dumps(data, ensure_ascii=False, default=str)[:1000]}")
                else:
                    parts.append(f"### {key}\n{str(data)[:1000]}")
        return "\n\n".join(parts) if parts else "（パイプラインデータなし）"

    def _make_section(
        self,
        section_id: int,
        narrative: str,
        data: Dict[str, Any],
        metadata: Optional[Any] = None,  # GenerationMetadata
        feedback_history: Optional[List[Any]] = None,
        ai_draft_snapshot: Optional[str] = None
    ) -> MidtermPlanSection:
        """MidtermPlanSectionを生成"""
        sec_def = SECTION_DEFINITIONS[section_id - 1]

        return MidtermPlanSection(
            section_id=sec_def["id"],
            section_title=sec_def["title"],
            section_title_en=sec_def["title_en"],
            references=sec_def["references"],
            narrative=narrative,
            data=data,
            generation_metadata=metadata,
            feedback_history=feedback_history or [],
            ai_draft_snapshot=ai_draft_snapshot
        )

    async def _call_sdk_writer_for_section(
        self,
        chapter_id: int,
        prompt: str,
        pipeline_run_id: Optional[str] = None,
    ) -> MidtermPlanSection:
        """
        SDK Writer Agent で章を生成するメソッド。
        use_sdk=True のときに _call_llm_for_section から呼ばれる。

        不変条件: WriterAgentOutput.missing_inputs がある場合は ValueError を送出し、
        推測で埋めない。呼び出し元がエラーハンドリングすること。
        """
        from core.agents_sdk.runner import SDKRunner
        from core.agents_sdk.agents_definitions import create_writer_agent
        from core.agents_sdk.schemas import WriterAgentOutput

        run_id = pipeline_run_id or getattr(self, "pipeline_run_id", None)
        runner = SDKRunner(
            pipeline_run_id=run_id,
            stage_number=7,
            stage_name="midterm_plan_writer",
        )
        agent = create_writer_agent()
        result = await runner.run(
            agent,
            f"章ID={chapter_id}:\n\n{prompt}",
            context_vars={"chapter_id": chapter_id},
        )

        output: WriterAgentOutput = result.final_output

        if output.missing_inputs:
            raise ValueError(
                f"WriterAgent: section {chapter_id} has missing_inputs: "
                f"{output.missing_inputs}"
            )

        # SECTION_DEFINITIONS_WITH_SCHEMA からタイトル等を取得
        sec_def = next(
            (s for s in SECTION_DEFINITIONS_WITH_SCHEMA if s["id"] == chapter_id),
            {"title": f"章{chapter_id}", "title_en": f"Section {chapter_id}",
             "references": []},
        )

        from core.schemas.midterm_plan_schema import GenerationMetadata
        from datetime import datetime as _dt
        metadata = GenerationMetadata(
            model_used="gpt-4o-sdk",
            generated_at=_dt.now().isoformat(),
            prompt_tokens=0,
            completion_tokens=0,
            finish_reason="sdk",
        )

        return MidtermPlanSection(
            section_id=chapter_id,
            section_title=sec_def["title"],
            section_title_en=sec_def["title_en"],
            references=sec_def["references"],
            narrative=output.narrative,
            data=output.data,
            generation_metadata=metadata,
        )

    async def _call_llm_for_section(
        self,
        prompt: str,
        expected_model: Optional[Any] = None,
        use_sdk: bool = False,
        chapter_id: Optional[int] = None,
        pipeline_run_id: Optional[str] = None,
    ) -> MidtermPlanSection:
        """
        LLMを呼び出してセクションデータを生成し、指定されたモデルでパースしてセクションオブジェクトを返す。

        use_sdk=True の場合は _call_sdk_writer_for_section へ委譲する。
        chapter_id が必要（use_sdk=True 時）。
        """
        if use_sdk and chapter_id is not None:
            return await self._call_sdk_writer_for_section(
                chapter_id=chapter_id,
                prompt=prompt,
                pipeline_run_id=pipeline_run_id,
            )

        try:
            model_name = LLMRouter.route("analysis")
            messages = [
                {"role": "system", "content": SECTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
            
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=8192
            )
            
            # --- Audit Metadata Capture ---
            from core.schemas.midterm_plan_schema import GenerationMetadata
            from datetime import datetime
            
            usage_dict = {}
            if response.usage:
                usage_dict = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
            gen_metadata = GenerationMetadata(
                model_name=response.model, # Actual model used (e.g., gpt-4o-2024-05-13)
                prompt_snapshot=json.dumps(messages, ensure_ascii=False),
                generated_at=datetime.now().isoformat(),
                usage=usage_dict,
                finish_reason=response.choices[0].finish_reason,
                system_fingerprint=response.system_fingerprint
            )
            # ------------------------------
            
            content = response.choices[0].message.content
            result_json = json.loads(content)
            
            # ★ Unwrap if wrapped in class name (e.g. {"CorporatePhilosophy": {...}})
            if expected_model:
                unwrap_name = expected_model.__name__
                if unwrap_name in result_json and isinstance(result_json[unwrap_name], dict):
                    # Unwrap logic
                    unwrapped = result_json[unwrap_name]
                    # Merge narrative if it exists at top level or inside
                    if "narrative" in result_json and "narrative" not in unwrapped:
                        unwrapped["narrative"] = result_json["narrative"]
                    result_json = unwrapped

            # ★ LLMレスポンスの柔軟なパーシング
            # LLMは2つの形式で返す可能性がある:
            #   形式1 (nested): {"narrative": "...", "data": {"mission": "...", ...}}
            #   形式2 (flat):   {"narrative": "...", "mission": "...", "core_values": [...]}
            narrative = result_json.get("narrative", "")
            
            if "data" in result_json and isinstance(result_json["data"], dict):
                # 形式1: nested — data キーが明示的に存在する
                data = result_json["data"]
            else:
                # 形式2: flat — narrative 以外の全フィールドを data として抽出
                data = {k: v for k, v in result_json.items() if k != "narrative"}
                if not data and not narrative:
                    # JSON全体がデータの場合（narrativeすら無い）
                    data = result_json
            
            # Find section ID from expected_model or context (Reverse lookup is tricky, so rely on caller logic or data)
            # However, the caller usually expects MidtermPlanSection.
            # We need to look up the section ID corresponding to the expected_model.
            
            section_id = 0
            for sec in SECTION_DEFINITIONS_WITH_SCHEMA:
                if sec["schema"] == expected_model:
                    section_id = sec["id"]
                    break
            
            # If expected_model provided, validate data
            if expected_model and data:
                try:
                    # Validate against Pydantic model
                    validated_data = expected_model(**data)
                    data = validated_data.model_dump()
                except Exception as e:
                    logger.warning(f"Data validation failed for {expected_model.__name__}: {e}")
            
            # ★ BUG-10 FIX: narrativeが空の場合、構造化データからナラティブを自動生成
            if not narrative and data:
                try:
                    narrative_prompt = NARRATIVE_GENERATION_TEMPLATE.format(
                        section_id=section_id,
                        section_title=SECTION_DEFINITIONS[section_id - 1]['title'],
                        data_context=json.dumps(data, ensure_ascii=False, indent=2, default=str)
                    )
                    narrative_resp = openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": SECTION_SYSTEM_PROMPT},
                            {"role": "user", "content": narrative_prompt}
                        ],
                        max_tokens=4096
                    )
                    narrative = narrative_resp.choices[0].message.content
                    logger.info(f"Auto-generated narrative for section {section_id} ({len(narrative)} chars)")
                except Exception as e:
                    logger.warning(f"Narrative auto-generation failed for section {section_id}: {e}")
                    narrative = f"## {SECTION_DEFINITIONS[section_id - 1]['title']}\n\n（データは正常に生成されましたが、ナラティブの自動生成に失敗しました。構造化データをご確認ください。）"
            
            # ★ DEBUG INJECTION (Force visualization of raw content if still empty)
            if not narrative:
                narrative = f"DEBUG: Narrative is empty. Raw content head (first 500 chars):\n{content[:500]}..."
            
            # _call_llm_for_section は generate_full_plan から呼ばれる初回生成なので
            # ai_draft_snapshot = narrative (初回スナップショット)
            return self._make_section(section_id, narrative, data, metadata=gen_metadata, ai_draft_snapshot=narrative)

        except Exception as e:
            logger.error(f"Generate section failed: {e}")
            # ★ BUG-3/7 FIX: expected_modelからsection_idを安全に取得
            fallback_id = 1  # デフォルト安全値
            if expected_model:
                for sec in SECTION_DEFINITIONS_WITH_SCHEMA:
                    if sec["schema"] == expected_model:
                        fallback_id = sec["id"]
                        break
            return self._make_section(fallback_id, f"※ セクション生成エラー: {str(e)}", {})

    # =============================================
    # Section Generators (1-13)
    # =============================================

    async def _generate_section_01_philosophy(self) -> MidtermPlanSection:
        """セクション1: 企業理念"""
        # Data Context
        mission = self.guardrails.get("mission_objective", "")
        values = self.guardrails.get("core_values", []) # This might be string or list depending on schema
        if isinstance(values, str):
            values = [v.strip() for v in values.split(",")]
        
        founding_spirit = self.guardrails.get("founding_spirit", "")
        management_philosophy = self.guardrails.get("management_philosophy", "")
        
        # Internal Docs (e.g. Brand Book, History)
        internal_docs = self.pipeline_data.get("internal_docs", [])
        
        # Build prompt
        prompt = self._build_section_prompt(
            section_id=1,
            section_title="企業理念",
            previous_sections_summary="なし（最初のセクション）",
            pipeline_data_context=f"""
### 戦略的ガードレール (Mission/Values)
- ミッション・目的: {mission}
- コアバリュー: {', '.join(values) if values else '未定義'}
- 創業の精神: {founding_spirit}
- 経営哲学: {management_philosophy}

### 内部ドキュメント (Brand Book/History)
{json.dumps(internal_docs, ensure_ascii=False, default=str)[:3000]}
            """,
            specific_instructions=PROMPT_INSTRUCTION_PHILOSOPHY
        )

        return await self._call_llm_for_section(prompt, CorporatePhilosophy)

    async def _generate_section_02_vision(self) -> MidtermPlanSection:
        """セクション2: ビジョン"""
        # Context
        philosophy_sec = self.typed_sections.get("philosophy")
        mission = philosophy_sec.mission if philosophy_sec and philosophy_sec.mission else "（未定義）"
        
        success_def = self.guardrails.get("success_state_definition", "（未定義）")
        time_horizon = self.guardrails.get("time_horizon_years", 3)
        
        prompt = self._build_section_prompt(
            section_id=2,
            section_title="ビジョン",
            previous_sections_summary=f"企業理念: {mission}",
            pipeline_data_context=f"""
### 戦略的ガードレール (Vision)
- 成功の定義(3年後): {success_def}
- 計画期間: {time_horizon}年
            """,
            specific_instructions=PROMPT_INSTRUCTION_VISION.format(time_horizon=time_horizon)
        )

        return await self._call_llm_for_section(prompt, VisionStatement)

    async def _generate_section_03_external(self) -> MidtermPlanSection:
        """セクション3: 外部環境分析"""
        external_data = self.pipeline_data.get("external", {})
        external_docs = self.pipeline_data.get("external_docs", [])
        
        no_entry = self.guardrails.get("no_entry_markets", [])
        
        # Use Pre-generated Analyst Report
        agent_report = self.agent_reports.get("market", "")
        agent_insight = f"\n### Market Researcher Analysis\n{agent_report}\n" if agent_report else ""
        
        # RAG Context (Still useful to include raw chunks if available)
        rag_context = self._get_rag_context("外部環境 市場トレンド 競合 動向 PEST分析 機会 脅威")
        
        # ★ Dynamic Framework Evaluation (Async)
        industry = self.pipeline_data.get("industry", "General")
        target_market = self.pipeline_data.get("target_market", "日本")
        
        # Execute Framework Analysis
        pestle_result, five_forces_result = await asyncio.gather(
            self.framework_evaluator.evaluate_pestle(target_market=target_market, industry=industry, custom_context=rag_context),
            self.framework_evaluator.evaluate_five_forces(industry=industry, custom_context=rag_context)
        )
        
        pipeline_data_context = f"""
### 外部環境データ (Auto-Fetch)
{json.dumps(external_data, ensure_ascii=False, default=str)[:2000]}

### 外部環境レポート (Reports/Docs)
{json.dumps(external_docs, ensure_ascii=False, default=str)[:5000]}

### PESTLE分析 (AI Generated)
{json.dumps(pestle_result.model_dump(), ensure_ascii=False, default=str)}

### 5 Forces分析 (AI Generated)
{json.dumps(five_forces_result.model_dump(), ensure_ascii=False, default=str)}

### 戦略的制約 (Guardrails)
- 参入しない市場: {', '.join(no_entry) if no_entry else 'なし'}

{agent_insight}
        """

        prompt = self._build_section_prompt(
            section_id=3,
            section_title="外部環境分析",
            previous_sections_summary=self._get_previous_sections_summary(3),
            pipeline_data_context=pipeline_data_context,
            specific_instructions=PROMPT_INSTRUCTION_EXTERNAL,
            rag_context=rag_context
        )

        return await self._call_llm_for_section(prompt, ExternalEnvironment)

    async def _generate_section_04_internal(self) -> MidtermPlanSection:
        """セクション4: 内部環境分析"""
        internal_data = self.pipeline_data.get("internal", {})
        financial_data = self.pipeline_data.get("financial", {})
        internal_docs = self.pipeline_data.get("internal_docs", [])

        # ★ ROA Analysis Integration (from Stage 1)
        roa_analysis = self.pipeline_data.get("stage_history", {}).get("1", {})
        roa_insight = ""
        if roa_analysis:
            breakdown = roa_analysis.get("roa_breakdown")
            weak_nodes = roa_analysis.get("weak_financial_nodes", [])
            hypotheses = roa_analysis.get("financial_hypotheses", [])
            
            roa_insight = f"""
### 財務デュポン分析 (ROA) 結果
- ROA: {breakdown.get('roa', 0):.2%} (vs Benchmark)
- 売上高純利益率: {breakdown.get('profit_margin', 0):.2%}
- 総資産回転率: {breakdown.get('asset_turnover', 0):.2f}回

**特定された弱点:**
{', '.join([n['metric_name'] for n in weak_nodes])}

**財務仮説:**
{', '.join([h['description'] for h in hypotheses])}
"""

        # Use Pre-generated Analyst Report
        agent_report = self.agent_reports.get("internal", "")
        agent_insight = f"\n### Internal Auditor Analysis\n{agent_report}\n" if agent_report else ""

        # RAG Context
        rag_context = self._get_rag_context("内部環境 自社の強み 弱み 組織課題 リソース ヒト・モノ・カネ")

        prompt = self._build_section_prompt(
            section_id=4,
            section_title="内部環境分析",
            previous_sections_summary=self._get_previous_sections_summary(4),
            pipeline_data_context=f"""
### 内部データ (Sales/HR)
{json.dumps(internal_data, ensure_ascii=False, default=str)[:2500]}

### 内部ドキュメント (Docs/Reports)
{json.dumps(internal_docs, ensure_ascii=False, default=str)[:5000]}

### 財務データ (Financial)
{json.dumps(financial_data, ensure_ascii=False, default=str)[:3000]}

{roa_insight}

{agent_insight}
            """,
            specific_instructions=PROMPT_INSTRUCTION_INTERNAL,
            rag_context=rag_context
        )

        return await self._call_llm_for_section(prompt, InternalEnvironment)

    async def _generate_section_05_root_cause(self) -> MidtermPlanSection:
        """セクション5: 根本原因分析"""
        internal_sec = self.typed_sections.get("internal")
        weaknesses = internal_sec.weaknesses if internal_sec else []
        
        # Inject Internal Data/Docs for deep-dive
        internal_data = self.pipeline_data.get("internal", {})
        internal_docs = self.pipeline_data.get("internal_docs", [])

        prompt = self._build_section_prompt(
            section_id=5,
            section_title="根本原因分析",
            previous_sections_summary=self._get_previous_sections_summary(5),
            pipeline_data_context=f"""
### 内部環境の弱み (Section 4 Summary)
{json.dumps(weaknesses, ensure_ascii=False, default=str)}

### 内部データ (Deep Dive Context)
{json.dumps(internal_data, ensure_ascii=False, default=str)[:2000]}

### 内部ドキュメント (Surveys/Reports)
{json.dumps(internal_docs, ensure_ascii=False, default=str)[:3000]}
            """,
            specific_instructions=PROMPT_INSTRUCTION_ROOT_CAUSE
        )
        return await self._call_llm_for_section(prompt, RootCauseAnalysis)

    async def _generate_section_06_swot(self) -> MidtermPlanSection:
        """セクション6: SWOT分析"""
        # Context from External (3) and Internal (4)
        ext_sec = self.typed_sections.get("external")
        int_sec = self.typed_sections.get("internal")
        
        opportunities = ext_sec.opportunities if ext_sec else []
        threats = ext_sec.threats if ext_sec else []
        strengths = int_sec.strengths if int_sec else []
        weaknesses = int_sec.weaknesses if int_sec else []
        
        prompt = self._build_section_prompt(
            section_id=6,
            section_title="SWOT分析",
            previous_sections_summary=self._get_previous_sections_summary(6),
            pipeline_data_context=f"""
### 外部環境
Opportunity: {json.dumps(opportunities, ensure_ascii=False, default=str)}
Threat: {json.dumps(threats, ensure_ascii=False, default=str)}

### 内部環境
Strength: {json.dumps(strengths, ensure_ascii=False, default=str)}
Weakness: {json.dumps(weaknesses, ensure_ascii=False, default=str)}
            """,
            specific_instructions=PROMPT_INSTRUCTION_SWOT
        )
        return await self._call_llm_for_section(prompt, SWOTAnalysis)

    async def _generate_section_07_cross_swot(self) -> MidtermPlanSection:
        """セクション7: クロスSWOT戦略"""
        swot_sec = self.typed_sections.get("swot")
        
        prompt = self._build_section_prompt(
            section_id=7,
            section_title="クロスSWOT戦略",
            previous_sections_summary=self._get_previous_sections_summary(7),
            pipeline_data_context=f"### SWOT分析結果\n{json.dumps(swot_sec.model_dump() if swot_sec else {}, ensure_ascii=False, default=str)}",
            specific_instructions=PROMPT_INSTRUCTION_CROSS_SWOT
        )
        return await self._call_llm_for_section(prompt, CrossSWOTStrategy)

    async def _generate_section_08_corporate_strategy(self) -> MidtermPlanSection:
        """セクション8: 全社戦略"""
        # Context
        cross_swot = self.typed_sections.get("cross_swot")
        # vision = self.typed_sections.get("vision") # BUG FIX: Typed object doesn't have narrative
        
        # Get Vision Section for narrative
        vision_section = next((s for s in self.generated_sections if s.section_id == 2), None)
        vision_narrative = vision_section.narrative if vision_section else ""
        
        # Consultant Persona for Strategy
        agent_report = self.agent_reports.get("strategy", "")
        agent_insight = f"\n### Strategy Director Insight\n{agent_report}\n" if agent_report else ""

        prompt = self._build_section_prompt(
            section_id=8,
            section_title="全社戦略",
            previous_sections_summary=self._get_previous_sections_summary(8),
            pipeline_data_context=f"""
### ビジョン
{vision_narrative}

### クロスSWOTオプション
{json.dumps(cross_swot.model_dump() if cross_swot else {}, ensure_ascii=False, default=str)[:2000]}

{agent_insight}
            """,
            specific_instructions=PROMPT_INSTRUCTION_CORPORATE_STRATEGY
        )
        return await self._call_llm_for_section(prompt, CorporateStrategySection)

    async def _generate_section_09_domain_strategy(self) -> MidtermPlanSection:
        """セクション9: 事業ドメイン戦略"""
        corp_strategy = self.typed_sections.get("corporate_strategy")
        
        prompt = self._build_section_prompt(
            section_id=9,
            section_title="事業ドメイン戦略",
            previous_sections_summary=self._get_previous_sections_summary(9),
            pipeline_data_context=f"### 全社戦略\n{corp_strategy.strategic_intent if corp_strategy else ''}",
            specific_instructions=PROMPT_INSTRUCTION_DOMAIN_STRATEGY
        )
        return await self._call_llm_for_section(prompt, BusinessDomainStrategy)

    async def _generate_section_10_functional(self) -> MidtermPlanSection:
        """セクション10: 機能別戦略"""
        internal_data = self.pipeline_data.get("internal", {})
        internal_docs = self.pipeline_data.get("internal_docs", [])

        prompt = self._build_section_prompt(
            section_id=10,
            section_title="機能別戦略",
            previous_sections_summary=self._get_previous_sections_summary(10),
            pipeline_data_context=f"""
### 内部データ (HR/Org/Sales)
{json.dumps(internal_data, ensure_ascii=False, default=str)[:2000]}

### 内部ドキュメント (Docs)
{json.dumps(internal_docs, ensure_ascii=False, default=str)[:3000]}
            """,
            specific_instructions=PROMPT_INSTRUCTION_FUNCTIONAL
        )
        return await self._call_llm_for_section(prompt, FunctionalStrategies)

    async def _generate_section_11_initiatives(self) -> MidtermPlanSection:
        """セクション11: 施策"""
        # Context: Needs strong link to Weaknesses (5/6) and Strategy (8/9)
        root_cause = self.typed_sections.get("root_cause")
        corp_strategy = self.typed_sections.get("corporate_strategy")
        
        prompt = self._build_section_prompt(
            section_id=11,
            section_title="施策",
            previous_sections_summary=self._get_previous_sections_summary(11),
            pipeline_data_context=f"""
### 全社戦略指針 (Section 8)
{corp_strategy.strategic_intent if corp_strategy else ""}

### 解決すべき根本原因 (Section 5)
{json.dumps(root_cause.model_dump() if root_cause else {}, ensure_ascii=False, default=str)[:1500]}
            """,
            specific_instructions=PROMPT_INSTRUCTION_INITIATIVES
        )
        return await self._call_llm_for_section(prompt, StrategicInitiatives)

    async def _generate_section_12_kpi(self) -> MidtermPlanSection:
        """セクション12: KPIアーキテクチャ"""
        # Context: Initiatives (11)
        initiatives = self.typed_sections.get("initiatives")
        financial_data = self.pipeline_data.get("financial", {})
        
        prompt = self._build_section_prompt(
            section_id=12,
            section_title="KPIアーキテクチャ",
            previous_sections_summary=self._get_previous_sections_summary(12),
            pipeline_data_context=f"""
### 現状の財務データ (Baseline)
{json.dumps(financial_data, ensure_ascii=False, default=str)[:1000]}

### 施策リスト
{json.dumps(initiatives.model_dump() if initiatives else {}, ensure_ascii=False, default=str)[:2000]}
            """,
            specific_instructions=PROMPT_INSTRUCTION_KPI
        )
        return await self._call_llm_for_section(prompt, KPIArchitecture)

    async def _generate_section_13_financial(self) -> MidtermPlanSection:
        """セクション13: 数値計画"""
        # Pipeline Data (Financial)
        financial_data = self.pipeline_data.get("financial", {})
        
        corp_strategy = self.typed_sections.get("corporate_strategy")        
        # Guardrails
        inv_limit = self.guardrails.get("investment_limit", 0)

        # ★ KPI Integration (Section 12)
        kpi_section = self.typed_sections.get("kpi")
        kpi_targets_str = ""
        if kpi_section:
            strat_kpis = getattr(kpi_section, "strategic_kpis", [])
            lines = []
            for k in strat_kpis:
                t = k.targets
                lines.append(f"- {k.name}: current={k.current_value}, targets={t}")
            kpi_targets_str = "\n".join(lines)

        # ★ ROA Analysis Integration
        roa_analysis = self.pipeline_data.get("stage_history", {}).get("1", {})
        roa_issues = ""
        if roa_analysis:
            weak_nodes = roa_analysis.get("weak_financial_nodes", [])
            roa_issues = "、".join([n['metric_name'] for n in weak_nodes])

        # Agent: Financial Analyst (Pre-generated)
        agent_report = self.agent_reports.get("financial", "")
        agent_insight = f"\n### Financial Analyst Report\n{agent_report}\n" if agent_report else ""
        
        prompt = self._build_section_prompt(
            section_id=13,
            section_title="数値計画",
            previous_sections_summary=self._get_previous_sections_summary(13),
            pipeline_data_context=f"""
### 現状の財務データ (Uploaded)
{json.dumps(financial_data, ensure_ascii=False, default=str)[:5000]}

### 全社戦略方針
成長方向性: {corp_strategy.growth_direction if corp_strategy else ""}
資源配分: {corp_strategy.resource_allocation_policy if corp_strategy else ""}

### 重要KPI目標 (Section 12)
{kpi_targets_str}

### 改善すべき財務課題 (ROA Stage 1)
{roa_issues}

### 制約条件
投資上限: {inv_limit}百万円

{agent_insight}
            """,
            specific_instructions=PROMPT_INSTRUCTION_FINANCIAL.format(kpi_targets_str=kpi_targets_str, roa_issues=roa_issues)
        )

        return await self._call_llm_for_section(prompt, FinancialNumericalPlan)

    # =============================================
    # §14: Quality Check (品質チェック)
    # =============================================

    async def run_quality_check(self, doc: MidtermPlanDocument) -> QualityCheckResult:
        """
        全13セクションを横断的にAIがレビューし5軸評価を行う。
        
        評価軸:
            1. 論理的一貫性 (20点)
            2. 数値整合性 (20点)
            3. SWOT→戦略の妥当性 (20点)
            4. 実現可能性 (20点)
            5. 欠落・矛盾検出 (20点)
        """
        # Build full plan text for AI review
        plan_text_parts = []
        for section in doc.sections:
            section_header = f"## §{section.section_id} {section.section_title}"
            narrative_part = section.narrative or "(未作成)"
            data_part = json.dumps(section.data, ensure_ascii=False, default=str)[:2000] if section.data else ""
            plan_text_parts.append(f"{section_header}\n{narrative_part}\n➡️ Data: {data_part}")
        
        full_plan_text = "\n\n---\n\n".join(plan_text_parts)

        system_msg = QUALITY_CHECK_SYSTEM_PROMPT

        user_msg = f"""以下の中期経営計画書の品質チェックを実施してください。

{full_plan_text}"""

        try:
            model = LLMRouter.route("analysis")
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=8192
            )
            
            result_json = json.loads(response.choices[0].message.content)
            
            # Parse into structured result
            axis_scores = [
                QAAxisScore(**a) for a in result_json.get("axis_scores", [])
            ]
            critical_issues = [
                QAIssueItem(**i) for i in result_json.get("critical_issues", [])
            ]
            warnings = [
                QAIssueItem(**w) for w in result_json.get("warnings", [])
            ]
            
            qa_result = QualityCheckResult(
                overall_score=result_json.get("overall_score", 0),
                grade=result_json.get("grade", "C"),
                executive_summary=result_json.get("executive_summary", ""),
                axis_scores=axis_scores,
                critical_issues=critical_issues,
                warnings=warnings,
                strengths=result_json.get("strengths", []),
                cross_reference_summary=result_json.get("cross_reference_summary", "")
            )
            
            logger.info(f"Quality check completed: {qa_result.overall_score}/100 ({qa_result.grade})")
            return qa_result
            
        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            raise e

    # =============================================
    # Refinement Process (Step 1351)
    # =============================================

    async def run_strategic_refinement(self, doc: MidtermPlanDocument) -> RefinedStrategicPlan:
        """
        AIドラフトを「意思決定レベル」の戦略計画に昇華させる修正プロセス。
        7つのステップでビジネスモデル、収益ロジック、KPI、財務、実行計画を再構築する。
        """
        # 1. Check Data Verification Status
        financial_data = self.pipeline_data.get("financial", {})
        financials_verified = self._verify_financial_data_sufficiency(financial_data)
        
        # 1.5 External Constraints Analysis & Frameworks
        # (Ideally we reuse existing sections, but for refinement we re-evaluate for freshness/json-structure)
        framework_evaluator = FrameworkEvaluator()
        industry = self.pipeline_data.get("industry", "General")
        
        # Concurrently run frameworks to get constraints
        pestle_res, five_forces_res = await asyncio.gather(
            framework_evaluator.evaluate_pestle(target_market="Japan", industry=industry),
            framework_evaluator.evaluate_five_forces(industry=industry)
        )
        external_constraints = await framework_evaluator.evaluate_external_constraints(
            pestle_data=pestle_res, 
            five_forces_data=five_forces_res
        )

        # 2. Build Prompt Context
        full_plan_text = ""
        for section in doc.sections:
            full_plan_text += f"\n## §{section.section_id} {section.section_title}\n{section.narrative}\n"
            if section.data:
                full_plan_text += f"Data: {json.dumps(section.data, ensure_ascii=False, default=str)[:1000]}\n"
        
        # 3. Guardrail Instructions
        guardrail_instruction = ""
        if financials_verified:
            guardrail_instruction = """
            [GUARDRAIL: VERIFIED FINANCIALS MODE]
            User has provided verified financial data.
            - You MUST output specific `FinancialModelAssumptions` based on historical trends and strategy.
            - You MUST ensure growth rates and margins are realistic.
            """
        else:
            guardrail_instruction = """
            [GUARDRAIL: UNVERIFIED FINANCIALS MODE]
            CRITICAL: User has NOT provided sufficient financial data.
            - You MUST NOT output fake numeric forecasts. 
            - In `FinancialModelAssumptions`, output 0.0 or ranges, but set `provenance` to 'assumption'.
            - The Python engine will suppress the simulation table.
            """

        internal_docs = self.pipeline_data.get("internal_docs", [])
        
        prompt = f"""
        You are a top-tier Strategic Consultant and Systems Architect.
        Refine the following Mid-term Management Plan Draft into a "Decision-Grade" plan.
        
        **CRITICAL INSTRUCTION: OUTPUT MUST BE IN JAPANESE.**
        While the JSON keys must remain in English (matching the schema), ALL text values (descriptions, names, strategies, reasoning) MUST be in Japanese.
        
        ## Input Draft
        {full_plan_text[:30000]} # Truncate if too long

        ## Internal Docs Context
        {json.dumps(internal_docs, ensure_ascii=False, default=str)[:3000]}
        
        ## External Constraints (MUST BE RESPECTED)
        {external_constraints.model_dump_json(indent=2)}

        ## 7-Step Refinement Protocol
        1. **Business Model Fix**: Identify the single primary business model.
        2. **Revenue Logic Integration**: Define `Revenue = Volume x Price x Frequency x Capacity`.
            - MUST incorporate `market_growth_rate` and `price_pressure_level` from constraints.
        3. **KPI Architecture**: Rebuild KGI -> Financial -> Operational -> Action KPIs.
        4. **Financial Modeling**: output structured assumptions.
        5. **Strategy Quantification**: Estimate impact of initiatives.
        6. **Execution Architecture**: Define roadmap with owners and milestones.
        7. **Output**: Return strictly valid JSON matching `RefinedStrategicPlan` schema.

        {guardrail_instruction}
        
        ## Constraint on Provenance
        For every major field, you must provide a `provenance` object indicating if it came from
        'financial_data', 'internal_data', 'external_data', or is a 'derived'/'assumption'.
        
        ## REQUIRED JSON STRUCTURE
        Your output MUST strictly follow this Pydantic schema:
        ```json
        {RefinedStrategicPlan.model_json_schema()}
        ```
        Ensure all required fields like `business_model`, `revenue_logic`, `kpi_tree` are present.
        **ALL TEXT VALUES MUST BE IN JAPANESE.**
        """

        # 4. Call LLM
        try:
            model_name = LLMRouter.route("analysis") # Use strongest model
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a detailed Strategic Planner. JSON output only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2, # Low temp for deterministic logic
                max_tokens=8192
            )
            
            result_json = json.loads(response.choices[0].message.content)
            
            # 5. Parse into Pydantic
            from pydantic import ValidationError
            try:
                refined_plan = RefinedStrategicPlan(**result_json)
            except ValidationError as ve:
                logger.error(f"Pydantic Validation Error in Refinement: {ve}")
                # Log the raw JSON for debugging
                logger.error(f"Raw JSON from LLM: {json.dumps(result_json, ensure_ascii=False)[:1000]}...")
                raise ve
            except Exception as e:
                logger.error(f"Unexpected error in Refinement: {e}")
                raise e
            
            # 5.5 Inject Constraints & Forecast Source
            refined_plan.external_constraints = external_constraints
            refined_plan.forecast_source = "deterministic_engine" if financials_verified else "assumption_only"
            
            # 6. Post-Process: Deterministic Financial Simulation (if verified)
            refined_plan.financials_verified = financials_verified
            if financials_verified:
                scenarios = await self._run_deterministic_simulation(
                    refined_plan.financial_assumptions, 
                    financial_data,
                    constraints=external_constraints,
                    roadmap=refined_plan.execution_roadmap
                )
                refined_plan.scenarios = scenarios
                
                # Legacy support: Use Base Case for 'simulation' field
                # Find base case (usually first or by name)
                base_case = next((s for s in scenarios if "Base" in s.scenario_name), scenarios[0])
                
                # Convert ScenarioSimulation back to FinancialSimulation for legacy field if needed
                # FinancialSimulation expects 'years', 'assumptions_used'
                # The 'years' in ScenarioSimulation are SimulationYear objects, same type.
                
                # Create a bare bones FinancialSimulation from base case
                try:
                    from core.schemas.refinement_schema import FinancialSimulation
                    refined_plan.simulation = FinancialSimulation(
                        is_verified=True,
                        years=base_case.years,
                        assumptions_used=refined_plan.financial_assumptions # Original assumptions
                    )
                except Exception as ex:
                    logger.warning(f"Legacy simulation field population failed: {ex}")
                    refined_plan.simulation = None
                
                # Trace
                refined_plan.simulation_trace = SimulationTrace(
                    inputs_used=["Financial Data", "External Constraints", "Roadmap"],
                    formulas_applied=["Compounded Growth", "Margin constraints", "Cashflow Analysis", "Debt Capacity"],
                    scenario_parameters=refined_plan.financial_assumptions.model_dump(),
                    generated_timestamp=datetime.now().isoformat()
                )
            else:
                refined_plan.simulation = None
                refined_plan.scenarios = []
                refined_plan.simulation_trace = None
            
            # 7. Quality Gate (Decision-Grade Status)
            refined_plan.decision_grade_status = check_strategic_refinement_quality(refined_plan)
            
            return refined_plan
            
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            raise e

    def _verify_financial_data_sufficiency(self, financial_data: Dict[str, Any]) -> bool:
        """Check if minimum required fields exist for simulation"""
        # Simplistic check: is it not empty?
        if not financial_data:
            return False
        return True

    async def _run_deterministic_simulation(
        self, 
        assumptions: "FinancialModelAssumptions", 
        base_data: Dict[str, Any],
        constraints: "ExternalConstraints" = None,
        roadmap: "ExecutionRoadmap" = None
    ) -> List[Any]: # Returns List[ScenarioSimulation]
        """
        Run Base, Downside, and Severe Downside simulations with detailed Debt Schedule.
        """
        from core.schemas.refinement_schema import SimulationYear, ScenarioSimulation
        from core.cashflow_engine import calculate_cashflow
        from core.debt_capacity_engine import calculate_debt_capacity
        from core.debt_schedule_engine import generate_amortization_schedule
        
        # 1. Base Scenario
        base_years = self._run_single_scenario(assumptions, base_data, constraints, roadmap, modifier=1.0)
        
        # Debt Schedule
        base_amort = generate_amortization_schedule(assumptions, years_to_simulate=3)
        base_debt_service = [r.total_payment for r in base_amort.rows]
        
        base_cf = calculate_cashflow(
            base_years, 
            assumptions, 
            initial_cash=1000, 
            debt_service_schedule=base_debt_service
        )
        base_debt_cap = calculate_debt_capacity(base_cf)
        
        base_scenario = ScenarioSimulation(
            scenario_name="Base Case (Planned)",
            years=base_years,
            cashflow=base_cf,
            debt_capacity=[base_debt_cap],
            assumptions_modified=assumptions,
            amortization_schedule=base_amort
        )
        
        # 2. Downside Scenario (Growth -20%, Margin -5%)
        downside_assumptions = assumptions.model_copy(deep=True)
        downside_assumptions.revenue_growth_rate_y1 *= 0.8
        downside_assumptions.revenue_growth_rate_y2 *= 0.8
        downside_assumptions.revenue_growth_rate_y3 *= 0.8
        downside_assumptions.gross_margin_rate *= 0.95
        
        downside_years = self._run_single_scenario(downside_assumptions, base_data, constraints, roadmap, modifier=0.8)
        
        # Debt Schedule (Assumptions might change if new_borrowing is dynamic, but we assume fixed borrowing plan for now)
        downside_amort = generate_amortization_schedule(downside_assumptions, years_to_simulate=3)
        downside_debt_service = [r.total_payment for r in downside_amort.rows]
        
        downside_cf = calculate_cashflow(
            downside_years, 
            downside_assumptions, 
            initial_cash=1000,
            debt_service_schedule=downside_debt_service
        )
        downside_debt_cap = calculate_debt_capacity(downside_cf)
        
        downside_scenario = ScenarioSimulation(
            scenario_name="Downside Case (Growth misses by 20%)",
            years=downside_years,
            cashflow=downside_cf,
            debt_capacity=[downside_debt_cap],
            assumptions_modified=downside_assumptions,
            amortization_schedule=downside_amort
        )
        
        # 3. Severe Downside (Market Shock: Growth / 2, Margin -10pts)
        severe_assumptions = assumptions.model_copy(deep=True)
        severe_assumptions.revenue_growth_rate_y1 *= 0.5
        severe_assumptions.revenue_growth_rate_y2 *= 0.5
        severe_assumptions.revenue_growth_rate_y3 *= 0.5
        severe_assumptions.gross_margin_rate -= 0.1
        
        severe_years = self._run_single_scenario(severe_assumptions, base_data, constraints, roadmap, modifier=0.5)
        
        severe_amort = generate_amortization_schedule(severe_assumptions, years_to_simulate=3)
        severe_debt_service = [r.total_payment for r in severe_amort.rows]
        
        severe_cf = calculate_cashflow(
            severe_years, 
            severe_assumptions, 
            initial_cash=1000,
            debt_service_schedule=severe_debt_service
        )
        severe_debt_cap = calculate_debt_capacity(severe_cf)
        
        severe_scenario = ScenarioSimulation(
            scenario_name="Severe Downside (Market Shock)",
            years=severe_years,
            cashflow=severe_cf,
            debt_capacity=[severe_debt_cap],
            assumptions_modified=severe_assumptions,
            amortization_schedule=severe_amort
        )
        
        return [base_scenario, downside_scenario, severe_scenario]

    def apply_refinement_to_document(self, plan_doc: "MidtermPlanDocument", refined_plan: RefinedStrategicPlan) -> "MidtermPlanDocument":
        """
        RefinedStrategicPlanの内容を、MidtermPlanDocumentの各セクション(9, 11, 12, 13)に反映させる。
        """
        if not refined_plan:
            return plan_doc
            
        logger.info("Applying refinement to plan document sections...")
        
        # 1. Section 9: Business Domain Strategy (事業ドメイン戦略)
        # ----------------------------------------------------------------
        sec9 = next((s for s in plan_doc.sections if s.section_id == 9), None)
        if sec9 and refined_plan.business_model:
            bm = refined_plan.business_model
            # Create a DomainStrategyItem from BusinessModel
            from core.schemas.midterm_plan_schema import DomainStrategyItem
            
            # Since BusinessModel is single, we treat it as the primary domain
            primary_domain = DomainStrategyItem(
                domain_name=bm.model_name,
                target_market=", ".join(bm.customer_segments),
                value_proposition=bm.value_proposition,
                competitive_strategy="differentiation", # Default or infer?
                target_segments=bm.customer_segments,
                growth_strategy=bm.description
            )
            
            # Merge or Replace? Strategy: Replace domains list with this primary one + existing if distinct?
            # For simplicity and "Decision-Grade" authority, we replace/prepend.
            # Let's clean the list and add this as the core domain.
            sec9.data["domains"] = [primary_domain.model_dump()]
            sec9.chapter_state.version += 1
            sec9.chapter_state.status = ChapterStatus.AI_GENERATED
            
        # 2. Section 12: KPI Architecture (KPIアーキテクチャ)
        # ----------------------------------------------------------------
        sec12 = next((s for s in plan_doc.sections if s.section_id == 12), None)
        if sec12 and refined_plan.kpi_tree:
            # Flatten KPI Tree to List[KPIItem]
            from core.schemas.midterm_plan_schema import KPIItem
            
            kpi_list = []
            
            def flatten_kpi(node, category="financial"):
                kpi = KPIItem(
                    name=node.name,
                    definition=node.definition,
                    category=category,
                    unit=node.unit,
                    monitoring_frequency=node.measurement_frequency,
                    current_value=node.current_value
                )
                if node.target_value_3y:
                    kpi.targets = {"Y3": node.target_value_3y}
                kpi_list.append(kpi.model_dump())
                
                for child in node.children:
                    # Infer category for children?
                    child_cat = "process" if category == "financial" else "learning"
                    flatten_kpi(child, category=child_cat)
            
            flatten_kpi(refined_plan.kpi_tree, "financial")
            
            sec12.data["strategic_kpis"] = kpi_list
            sec12.chapter_state.version += 1
            sec12.chapter_state.status = ChapterStatus.AI_GENERATED

        # 3. Section 13: Financial & Numerical Plan (数値計画)
        # ----------------------------------------------------------------
        sec13 = next((s for s in plan_doc.sections if s.section_id == 13), None)
        if sec13 and refined_plan.scenarios:
            # Use Base Case for projections
            base_case = next((s for s in refined_plan.scenarios if "Base" in s.scenario_name), refined_plan.scenarios[0])
            
            from core.schemas.midterm_plan_schema import YearlyFinancials
            
            projections = []
            for year_sim in base_case.years:
                yf = YearlyFinancials(
                    year=year_sim.year,
                    revenue=year_sim.revenue,
                    cost_of_goods=year_sim.cogs,
                    gross_profit=year_sim.gross_profit,
                    operating_expenses=year_sim.opex,
                    operating_profit=year_sim.operating_profit,
                    net_profit=year_sim.net_profit
                )
                projections.append(yf.model_dump())
            
            sec13.data["projections"] = projections
            
            # Investment Plan Summary
            inv_sum = f"Y1: {refined_plan.financial_assumptions.investment_amount_y1}, Y2: {refined_plan.financial_assumptions.investment_amount_y2}, Y3: {refined_plan.financial_assumptions.investment_amount_y3}"
            sec13.data["investment_plan_summary"] = inv_sum
            
            sec13.chapter_state.version += 1
            sec13.chapter_state.status = ChapterStatus.AI_GENERATED
            
        # 4. Section 11: Strategic Initiatives (施策) - Roadmap
        # ----------------------------------------------------------------
        sec11 = next((s for s in plan_doc.sections if s.section_id == 11), None)
        if sec11 and refined_plan.execution_roadmap:
            # Update implementation phases or initiatives?
            # ExecutionRoadmap has 'initiatives' list.
            from core.schemas.midterm_plan_schema import InitiativeItem
            
            new_initiatives = []
            for idx, init in enumerate(refined_plan.execution_roadmap.initiatives):
                item = InitiativeItem(
                    initiative_id=f"SI-REF-{idx+1:02d}",
                    title=init.name,
                    owner=init.owner,
                    timeline=f"{init.timeline_start} - {init.timeline_end}",
                    expected_impact=init.expected_revenue_impact,
                    description=f"ROI: {init.roi_estimate}. Investment: {init.investment_required}"
                )
                new_initiatives.append(item.model_dump())
            
            if new_initiatives:
                sec11.data["initiatives"] = new_initiatives
                sec11.chapter_state.version += 1
                sec11.chapter_state.status = ChapterStatus.AI_GENERATED

        return plan_doc

    def _run_single_scenario(self, assumptions, base_data, constraints, roadmap, modifier=1.0) -> List[Any]: # List[SimulationYear]
        # 1. Extract Base Data
        latest_rev = 0
        latest_cogs = 0
        latest_opex = 0
        
        # Simple extraction from 'financial' data
        if isinstance(base_data, list) and len(base_data) > 0:
            sorted_data = sorted(base_data, key=lambda x: x.get('year', 0))
            latest_year_data = sorted_data[-1]
            latest_rev = latest_year_data.get('sales', 0) or latest_year_data.get('revenue', 0) or 0
            latest_cogs = latest_year_data.get('cogs', 0) or latest_year_data.get('cost_of_goods_sold', 0) or 0
            latest_gross = latest_year_data.get('gross_profit', 0) or 0
            latest_opex = latest_year_data.get('sga', 0) or latest_year_data.get('opex', 0) or 0
            
            # Fallbacks
            if latest_cogs == 0 and latest_gross > 0:
                latest_cogs = latest_rev - latest_gross
            if latest_opex == 0 and latest_gross > 0:
                op = latest_year_data.get('operating_profit', 0) or 0
                latest_opex = latest_gross - op
                
        if latest_rev == 0:
            latest_rev = 1000 # Dummy
            
        current_rev = latest_rev
        current_cogs = latest_cogs or (latest_rev * 0.4) # Default
        current_opex = latest_opex or (latest_rev * 0.3) # Default
        
        from core.schemas.refinement_schema import SimulationYear
        
        sim_years = []
        base_year_num = datetime.now().year
        
        growth_rates = [
            assumptions.revenue_growth_rate_y1, 
            assumptions.revenue_growth_rate_y2, 
            assumptions.revenue_growth_rate_y3
        ]
        
        investments = [
            assumptions.investment_amount_y1,
            assumptions.investment_amount_y2,
            assumptions.investment_amount_y3
        ]

        for i in range(3):
            rate = growth_rates[i]
            
            # Revenue
            next_rev = current_rev * (1 + rate)
            
            # COGS (derived from margin or kept proportional?)
            # Use gross_margin_rate from assumption
            gross_margin = assumptions.gross_margin_rate
            next_gross_profit = next_rev * gross_margin
            next_cogs = next_rev - next_gross_profit
            
            # OPEX (Growth rate)
            next_opex = current_opex * (1 + assumptions.opex_growth_rate)
            
            # EBITDA
            next_ebitda = next_gross_profit - next_opex + 0 
            
            # Operating Profit
            next_op = next_gross_profit - next_opex
            
            # Net Profit (Tax)
            tax = max(0, next_op * assumptions.tax_rate)
            next_net = next_op - tax
            
            # Cash Flow (Simplified: Earnings - Investment)
            inv = investments[i]
            next_cf = next_net - inv 
            
            # Store
            sim_years.append(SimulationYear(
                year=base_year_num + i + 1,
                revenue=next_rev,
                cogs=next_cogs,
                gross_profit=next_gross_profit,
                opex=next_opex,
                ebitda=next_ebitda,
                operating_profit=next_op,
                net_profit=next_net,
                cash_flow=next_cf
            ))
            
            # Update current for next iteration
            current_rev = next_rev
            current_opex = next_opex # COGS resets based on margin
            
        return sim_years


# =============================================
# Factory Function
# =============================================

def create_midterm_plan_engine(
    pipeline_data: Optional[Dict[str, Any]] = None,
    guardrails: Optional[Dict[str, Any]] = None,
    client_id: str = ""
) -> MidtermPlanEngine:
    """MidtermPlanEngineのファクトリー関数"""
    return MidtermPlanEngine(
        pipeline_data=pipeline_data,
        guardrails=guardrails,
        client_id=client_id
    )
