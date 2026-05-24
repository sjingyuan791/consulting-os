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
from core.llm_client import client as openai_client
from core.llm_router import LLMRouter
from core.rag_service import get_rag_service

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

SECTION_SYSTEM_PROMPT = """あなたは、一流の戦略コンサルティングファームのシニアパートナーです。
中期経営計画書を作成しています。

以下のルールに厳密に従ってください:
1. 各セクションは前のセクションの分析結果を論理的に参照し、因果連続性を保つこと
2. プロフェッショナルなコンサルティングレポートの文体で書くこと
3. 具体的かつ実行可能な内容にすること
4. 指定されたJSON形式で構造化データを出力すること
5. 日本語で出力すること"""


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
        self.typed_sections: Dict[str, Any] = {}
        
        # Initialize RAG Service
        self.rag_service = get_rag_service()

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
        system_msg = f"""{SECTION_SYSTEM_PROMPT}

## 承認済みコンテキスト（変更不可）
{context_str}

あなたは以下の2つをJSON形式で出力してください:
1. "narrative": プロフェッショナルなコンサルティングレポート形式のマークダウンテキスト（400-800文字）
2. "data": セクションの構造化データ（下記のスキーマに従う）
{schema_hint}"""
        
        user_msg = f"""
        セクション{chapter_id}「{sec_def['title']}」を作成してください。
        
        ## ユーザー指示
        {user_input if user_input else "標準的な内容で作成してください。"}
        
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
                narrative_prompt = f"""
                以下の構造化データに基づいて、セクション{chapter_id}「{sec_def['title']}」の
                プロフェッショナルなナラティブ（マークダウン形式）を執筆してください。
                
                ## データ
                {json.dumps(data_dict, ensure_ascii=False, default=str)}
                """
                
                narrative_resp = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SECTION_SYSTEM_PROMPT},
                        {"role": "user", "content": narrative_prompt}
                    ],
                    max_tokens=4096
                )
                narrative_text = narrative_resp.choices[0].message.content

            return self._make_section(chapter_id, narrative_text, data_dict)

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

        system_msg = f"""あなたは中期経営計画策定のパートナーです。
左ペインのエディタで作業中のユーザーと対話します。

## 承認済みコンテキスト
{context_str}

## 現在の状態
{current_str}
"""
        
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

        return f"""
# Mid-Term Management Plan Generation Task (Section {section_id}: {section_title})

You are a top-tier strategic management consultant.
Your task is to draft **Section {section_id}: {section_title}** of the Mid-Term Management Plan.

## 1. Context & Constraints (Guardrails)
{guardrails_context}

## 2. Previous Sections Summary (Logical Flow)
{previous_sections_summary}

## 3. Data Context (Pipeline & Research)
{pipeline_data_context}{rag_section}

## 4. Specific Instructions
{specific_instructions}

## Output Format
Return a valid JSON object complying with the `{SECTION_DEFINITIONS_WITH_SCHEMA[section_id-1]['schema'].__name__}` schema.
Ensure the "narrative" field contains a high-quality, professional markdown explanation.
"""

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
        data: Dict[str, Any]
    ) -> MidtermPlanSection:
        """MidtermPlanSectionを生成"""
        sec_def = SECTION_DEFINITIONS[section_id - 1]
        return MidtermPlanSection(
            section_id=sec_def["id"],
            section_title=sec_def["title"],
            section_title_en=sec_def["title_en"],
            references=sec_def["references"],
            narrative=narrative,
            data=data
        )

    async def _call_llm_for_section(
        self, 
        prompt: str, 
        expected_model: Optional[Any] = None
    ) -> MidtermPlanSection:
        """
        LLMを呼び出してセクションデータを生成し、指定されたモデルでパースしてセクションオブジェクトを返す。
        """
        try:
            model = LLMRouter.route("analysis")
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SECTION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=8192
            )
            
            content = response.choices[0].message.content
            result_json = json.loads(content)
            
            # ★ Unwrap if wrapped in class name (e.g. {"CorporatePhilosophy": {...}})
            if expected_model:
                model_name = expected_model.__name__
                if model_name in result_json and isinstance(result_json[model_name], dict):
                    # Unwrap logic
                    unwrapped = result_json[model_name]
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
                    narrative_prompt = f"""以下のセクション{section_id}「{SECTION_DEFINITIONS[section_id - 1]['title']}」の
構造化データに基づいて、プロフェッショナルなコンサルティングレポート形式の
ナラティブ（マークダウン形式、400-800文字）を日本語で執筆してください。

## データ
{json.dumps(data, ensure_ascii=False, indent=2, default=str)}
"""
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
            
            return self._make_section(section_id, narrative, data)

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
            """,
            specific_instructions="""
1. クライアントの掲げるミッション・目的を基に、格調高い企業理念体系を構築せよ。
2. ステークホルダー（顧客、社員、株主、社会）への約束を具体的に定義せよ。
3. もしガードレール情報が不足している場合は、一般的な優良企業の理念をベースに、クライアントの業種（不明な場合は一般論）に合わせた仮説を提示せよ。
4. 出力JSONの `mission` には最も重要な目的を記述せよ。
            """
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
            specific_instructions=f"""
1. {time_horizon}年後の「あるべき姿（将来像）」を鮮明に描け。
2. 定性的な状態目標だけでなく、可能な限り具体的なイメージ（市場地位、組織の状態、社会への影響）を記述せよ。
3. スローガンは社内外に訴求するキャッチーなものを考案せよ。
4. 数値目標（財務・非財務）のハイレベルな目標値を設定せよ（詳細は後のセクションで詰めるため、ここでは大枠で良い）。
            """
        )

        return await self._call_llm_for_section(prompt, VisionStatement)

    async def _generate_section_03_external(self) -> MidtermPlanSection:
        """セクション3: 外部環境分析"""
        external_data = self.pipeline_data.get("external", {})
        no_entry = self.guardrails.get("no_entry_markets", [])
        
        # Use Pre-generated Analyst Report
        agent_report = self.agent_reports.get("market", "")
        agent_insight = f"\n### Market Researcher Analysis\n{agent_report}\n" if agent_report else ""
        
        # RAG Context (Still useful to include raw chunks if available)
        rag_context = self._get_rag_context("外部環境 市場トレンド 競合 動向 PEST分析 機会 脅威")

        prompt = self._build_section_prompt(
            section_id=3,
            section_title="外部環境分析",
            previous_sections_summary=self._get_previous_sections_summary(3),
            pipeline_data_context=f"""
### 外部環境データ (Uploaded)
{json.dumps(external_data, ensure_ascii=False, default=str)[:3000]}

### 戦略的制約 (Guardrails)
- 参入しない市場: {', '.join(no_entry) if no_entry else 'なし'}

{agent_insight}
            """,
            specific_instructions="""
1. マクロ環境（PEST）、市場トレンド、競合環境を包括的に分析せよ。
2. 特にアップロードされたデータに基づき、市場規模や成長率について言及せよ。データがない場合は「要調査」としつつ一般的な業界動向を推測せよ。
3. 機会(Opportunities)と脅威(Threats)を明確に抽出せよ。
4. 競合他社の分析を含めよ。
5. 参考資料がある場合は、その内容も分析に反映せよ。
            """,
            rag_context=rag_context
        )

        return await self._call_llm_for_section(prompt, ExternalEnvironment)

    async def _generate_section_04_internal(self) -> MidtermPlanSection:
        """セクション4: 内部環境分析"""
        internal_data = self.pipeline_data.get("internal", {})
        financial_data = self.pipeline_data.get("financial", {})

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
### 内部データ (Internal/HR/Sales)
{json.dumps(internal_data, ensure_ascii=False, default=str)[:2500]}

### 財務データ (Financial)
{json.dumps(financial_data, ensure_ascii=False, default=str)[:2500]}

{agent_insight}
            """,
            specific_instructions="""
1. 財務状況（売上、利益、財務健全性）と内部リソース（ヒト・モノ・情報）を分析せよ。
2. アップロードされた財務データに基づき、定量的な評価を行え。
3. 自社の強み(Strengths)と弱み(Weaknesses)を明確に抽出せよ。
4. コアコンピタンス（競合他社が模倣困難な核となる能力）を特定せよ。
5. 参考資料がある場合は、定量・定性情報の補強に使用せよ。
            """,
            rag_context=rag_context
        )

        return await self._call_llm_for_section(prompt, InternalEnvironment)

    async def _generate_section_05_root_cause(self) -> MidtermPlanSection:
        """セクション5: 根本原因分析"""
        external = self.typed_sections.get("external")
        internal = self.typed_sections.get("internal")
        
        # ★ BUG-6 FIX: 安全なアクセス（external/internalがNoneでもクラッシュしない）
        ext_summary = ""
        if external:
            opps = getattr(external, 'opportunities', []) or []
            threats = getattr(external, 'threats', []) or []
            ext_summary = f"機会: {','.join(opps)}\n脅威: {','.join(threats)}"
        
        int_summary = ""
        if internal:
            strengths = getattr(internal, 'strengths', []) or []
            weaknesses = getattr(internal, 'weaknesses', []) or []
            int_summary = f"強み: {','.join(strengths)}\n弱み: {','.join(weaknesses)}"

        # RAG Retrieval
        rag_context = self._get_rag_context("根本原因 経営課題 ボトルネック 組織風土 問題点")

        prompt = self._build_section_prompt(
            section_id=5,
            section_title="根本原因分析",
            previous_sections_summary=self._get_previous_sections_summary(5),
            pipeline_data_context=f"""
### 外部環境分析結果
{ext_summary}

### 内部環境分析結果
{int_summary}
            """,
            specific_instructions="""
1. 外部環境の「脅威」と内部環境の「弱み」の交点にある、経営課題の「根本原因(Root Cause)」を特定せよ。
2. 表面的な事象ではなく、構造的な問題（組織、プロセス、文化など）まで深掘せよ。
3. なぜその問題が起きているのかの因果連鎖を論理的に記述せよ。
4. 解決のための「レバレッジポイント（てこ）」を提示せよ。
            """,
            rag_context=rag_context
        )

        return await self._call_llm_for_section(prompt, RootCauseAnalysis)

    async def _generate_section_06_swot(self) -> MidtermPlanSection:
        """セクション6: SWOT分析"""
        external = self.typed_sections.get("external")
        internal = self.typed_sections.get("internal")
        root_cause = self.typed_sections.get("root_cause")
        
        # Guardrails for Context
        boundaries = self.guardrails.get("strategic_boundaries_json", {})

        prompt = self._build_section_prompt(
            section_id=6,
            section_title="SWOT分析",
            previous_sections_summary=self._get_previous_sections_summary(6),
            pipeline_data_context=f"""
### 外部環境 (Opp/Threats)
Opportunities: {external.opportunities if external else []}
Threats: {external.threats if external else []}

### 内部環境 (Str/Weak)
Strengths: {internal.strengths if internal else []}
Weaknesses: {internal.weaknesses if internal else []}

### 根本原因
{root_cause.priority_issues if root_cause else []}

### 戦略的境界線
{boundaries}
            """,
            specific_instructions="""
1. ここまでの分析結果を統合し、SWOTマトリクスを完成させよ。
2. 単なる羅列ではなく、重要度と緊急度が高い要素に絞り込め（各要素3-5つ）。
3. 「Synthesis（総合所見）」では、SWOT全体を俯瞰した戦略的示唆を記述せよ。
4. 根本原因分析の結果と矛盾がないように注意せよ。
            """
        )

        return await self._call_llm_for_section(prompt, SWOTAnalysis)

    async def _generate_section_07_cross_swot(self) -> MidtermPlanSection:
        """セクション7: クロスSWOT戦略"""
        swot = self.typed_sections.get("swot")
        
        prompt = self._build_section_prompt(
            section_id=7,
            section_title="クロスSWOT戦略",
            previous_sections_summary=self._get_previous_sections_summary(7),
            pipeline_data_context=f"""
### SWOT分析結果
Strengths: {swot.strengths if swot else []}
Weaknesses: {swot.weaknesses if swot else []}
Opportunities: {swot.opportunities if swot else []}
Threats: {swot.threats if swot else []}
            """,
            specific_instructions="""
1. 強み×機会(SO)、強み×脅威(ST)、弱み×機会(WO)、弱み×脅威(WT)の4視点で戦略オプションを立案せよ。
2. 各戦略は具体的かつ実行可能なものとし、論理的根拠（Rationale）を明記せよ。
3. 最も優先すべき戦略（Strategic Priority）を選択せよ。
4. ガードレールや企業理念と整合していることを確認せよ。
            """
        )

        return await self._call_llm_for_section(prompt, CrossSWOTStrategy)

    async def _generate_section_08_corporate_strategy(self) -> MidtermPlanSection:
        """セクション8: 全社戦略"""
        cross_swot = self.typed_sections.get("cross_swot")
        vision = self.typed_sections.get("vision")

        # Agents: Strategy Director & Devils Advocate
        try:
            # Prepare Actual Reports (CONNECTING THE DOTS)
            financial_report = self.agent_reports.get("financial", "財務データなし")
            market_report = self.agent_reports.get("market", "市場データなし")
            internal_report = self.agent_reports.get("internal", "内部データなし")
            
            # 1. Strategy Director generates draft
            sd_result = await self.strategy_director.run({
                "financial_report": financial_report, 
                "market_report": market_report,
                "internal_report": internal_report
            })
            draft_strategy = sd_result.narrative
            
            # 2. Devils Advocate critiques
            da_result = await self.devils_advocate.run({
                "draft_strategy": draft_strategy,
                "financial_constraints": str(self.guardrails.get("investment_limit", 0))
            })
            criticism = da_result.narrative
            
            agent_insight = f"\n### Strategy Director's Proposal\n{draft_strategy}\n\n### Devil's Advocate Review\n{criticism}\n"
        except Exception as e:
            logger.warning(f"Strategy Agents failed: {e}")
            agent_insight = ""

        prompt = self._build_section_prompt(
            section_id=8,
            section_title="全社戦略",
            previous_sections_summary=self._get_previous_sections_summary(8),
            pipeline_data_context=f"""
### ビジョン
{vision.vision_statement if vision else ""}

### クロスSWOT戦略
{cross_swot.strategic_priority if cross_swot else []}

{agent_insight}
            """,
            specific_instructions="""
1. 全社的な戦略意図（Strategic Intent）を定義せよ。
2. 事業ポートフォリオの方向性（成長・維持・撤退）を明確にせよ。
3. 経営資源（ヒト・モノ・カネ）の再配分方針を策定し、投資上限内で実現可能な計画とせよ。
4. ビジョン達成に向けた長期的なマイルストーンを設定せよ。
            """
        )

        return await self._call_llm_for_section(prompt, CorporateStrategySection)

    async def _generate_section_09_domain_strategy(self) -> MidtermPlanSection:
        """セクション9: 事業ドメイン戦略"""
        corp_strategy = self.typed_sections.get("corporate_strategy")
        cross_swot = self.typed_sections.get("cross_swot")

        # RAG Retrieval
        rag_context = self._get_rag_context("事業戦略 ターゲット市場 顧客ニーズ 競争優位 製品サービス")
        
        prompt = self._build_section_prompt(
            section_id=9,
            section_title="事業ドメイン戦略",
            previous_sections_summary=self._get_previous_sections_summary(9),
            pipeline_data_context=f"""
### 全社戦略方針
成長方向性: {corp_strategy.growth_direction if corp_strategy else ""}
ポートフォリオ戦略: {corp_strategy.portfolio_strategy if corp_strategy else ""}

### クロスSWOT戦略オプション
{cross_swot.strategic_priority if cross_swot else []}
            """,
            specific_instructions="""
1. クライアントの主力事業および成長事業について、それぞれ個別のドメイン戦略を策定せよ。
2. 各事業の「ターゲット市場」、「競争戦略（差別化/コスト/集中）」、「顧客への提供価値(Value Proposition)」を明確に定義せよ。
3. 全社戦略で定めたポートフォリオ方針と整合するように記述せよ。
            """
        )

        return await self._call_llm_for_section(prompt, BusinessDomainStrategy)

    async def _generate_section_10_functional(self) -> MidtermPlanSection:
        """セクション10: 機能別戦略"""
        corp_strategy = self.typed_sections.get("corporate_strategy")
        domain_strategy = self.typed_sections.get("domain_strategy")
        
        # Guardrails (Investment Limit)
        inv_limit = self.guardrails.get("investment_limit", 0)

        # RAG Retrieval
        rag_context = self._get_rag_context("機能別戦略 営業 マーケティング 人事 技術 DX 財務")
        
        prompt = self._build_section_prompt(
            section_id=10,
            section_title="機能別戦略",
            previous_sections_summary=self._get_previous_sections_summary(10),
            pipeline_data_context=f"""
### 全社戦略・資源配分
{corp_strategy.resource_allocation_policy if corp_strategy else ""}

### 投資上限
{inv_limit}百万円
            """,
            specific_instructions="""
1. 事業戦略を実行するために必要な「機能別戦略（営業、マーケティング、人事、技術/製造、財務・IT）」を策定せよ。
2. 各機能について、具体的な目標(Objectives)と主要施策(Key Initiatives)を定義せよ。
3. 成功指標(Success Metrics)は定量的かつ測定可能なものを設定せよ。
4. 全社で共通して取り組むべき優先事項（DX、人材育成など）も明記せよ。
            """
        )

        return await self._call_llm_for_section(prompt, FunctionalStrategies)

    async def _generate_section_11_initiatives(self) -> MidtermPlanSection:
        """セクション11: 施策"""
        root_cause = self.typed_sections.get("root_cause")

        # RAG Retrieval
        rag_context = self._get_rag_context("施策 アクションプラン 改善案 具体策 成功事例")
        
        prompt = self._build_section_prompt(
            section_id=11,
            section_title="施策",
            previous_sections_summary=self._get_previous_sections_summary(11),
            pipeline_data_context=f"""
### 根本原因分析の結果
主要症状: {root_cause.primary_symptom if root_cause else ""}
レバレッジポイント: {root_cause.leverage_points if root_cause else []}
            """,
            specific_instructions="""
1. 全社戦略・機能別戦略を実現するための具体的なアクションプラン（施策）をリストアップせよ。
2. 各施策には明確な優先順位(High/Medium/Low)を付与し、その理由も考慮せよ。
3. 特に「Phase 1（初年度前半）」に取り組むべきクイックウィン（早期に成果が出る施策）を特定せよ。
4. 各施策がどの戦略目標や根本原因の解決に紐づくかを意識せよ。
            """,
            rag_context=rag_context
        )

        return await self._call_llm_for_section(prompt, StrategicInitiatives)

    async def _generate_section_12_kpi(self) -> MidtermPlanSection:
        """セクション12: KPIアーキテクチャ"""
        corp_strategy = self.typed_sections.get("corporate_strategy")
        initiatives = self.typed_sections.get("initiatives")
        
        prompt = self._build_section_prompt(
            section_id=12,
            section_title="KPIアーキテクチャ",
            previous_sections_summary=self._get_previous_sections_summary(12),
            pipeline_data_context=f"""
### 全社戦略目標
{corp_strategy.long_term_goals if corp_strategy else []}

### 重要施策 (High Priority)
{[i.title for i in getattr(initiatives, 'initiatives', []) if getattr(i, 'priority', '') == 'high'] if initiatives else []}
            """,
            specific_instructions="""
1. 全社戦略目標の達成度を測るための「戦略KPI（最重要指標）」を設定せよ（財務・顧客・プロセス・学習の4視点からバランスよく）。
2. 各KPIについて、具体的な定義と3年間の目標値（仮説で良いので具体的な数値）を設定せよ。
3. バランススコアカード(BSC)の4視点に分類し、経営のバランスを確保せよ。
4. KGI（重要目標達成指標）とKPI（重要業績評価指標）の連動性を意識せよ。

IMPORTANT: Output must include "strategic_kpis" list in the "data" field.
Example structure for data:
{
  "strategic_kpis": [
    {
      "kpi_id": "KPI-001",
      "name": "売上高CAGR",
      "category": "financial",
      "current_value": 100,
      "targets": {"Y1": 110, "Y2": 125, "Y3": 150}
    }
  ],
  "balanced_scorecard": {
    "financial": ["売上高", "営業利益率"],
    "customer": ["顧客満足度"]
  }
}
            """
        )

        return await self._call_llm_for_section(prompt, KPIArchitecture)

    async def _generate_section_13_financial(self) -> MidtermPlanSection:
        """セクション13: 数値計画"""
        # Pipeline Data (Financial)
        financial_data = self.pipeline_data.get("financial", {})
        
        corp_strategy = self.typed_sections.get("corporate_strategy")        
        # Guardrails
        inv_limit = self.guardrails.get("investment_limit", 0)

        # Agent: Financial Analyst (Pre-generated)
        agent_report = self.agent_reports.get("financial", "")
        agent_insight = f"\n### Financial Analyst Report\n{agent_report}\n" if agent_report else ""
        
        prompt = self._build_section_prompt(
            section_id=13,
            section_title="数値計画",
            previous_sections_summary=self._get_previous_sections_summary(13),
            pipeline_data_context=f"""
### 現状の財務データ (Uploaded)
{json.dumps(financial_data, ensure_ascii=False, default=str)[:1000]}

### 全社戦略方針
成長方向性: {corp_strategy.growth_direction if corp_strategy else ""}
資源配分: {corp_strategy.resource_allocation_policy if corp_strategy else ""}

### 制約条件
投資上限: {inv_limit}百万円

{agent_insight}
            """,
            specific_instructions="""
1. 現状の財務データを起点として、3ヵ年のPL（損益計算書）予測を作成せよ。
2. 売上高、粗利益、営業利益、純利益を年度ごとに算出しよ。
3. 成長率は全社戦略の目標と整合させつつ、現実的な値を設定せよ。
4. 投資計画（Investment Plan）は、ガードレールの投資上限を超えない範囲で策定し、その資金調達（Funding Plan）についても言及せよ。
5. 感度分析（Sensitivity Scenarios）として、楽観・悲観シナリオも提示せよ。
            """
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

        system_msg = """You are an expert management consultant and quality assurance reviewer.
You will review a complete Mid-Term Management Plan (13 sections) and evaluate it across 5 axes.

Return a JSON object with this EXACT structure:
{
  "overall_score": <int 0-100>,
  "grade": "<S|A|B|C|D>",
  "executive_summary": "<総評 2-3文>",
  "axis_scores": [
    {
      "axis_name": "<軸名>",
      "score": <int 1-20>,
      "assessment": "<評価コメント>",
      "issues": ["<問題1>", ...],
      "recommendations": ["<推奨事項1>", ...]
    }
  ],
  "critical_issues": [
    {
      "severity": "critical",
      "target_section": <int 1-13>,
      "target_section_title": "<セクション名>",
      "description": "<指摘内容>",
      "suggestion": "<具体的な修正案テキスト>"
    }
  ],
  "warnings": [
    {
      "severity": "warning",
      "target_section": <int 1-13>,
      "target_section_title": "<セクション名>",
      "description": "<指摘内容>",
      "suggestion": "<改善案>"
    }
  ],
  "strengths": ["<強み1>", "<強み2>", ...],
  "cross_reference_summary": "<章間整合性サマリー>"
}

5軸の評価基準:
1. 論理的一貫性 (20点): 理念→ビジョン→戦略→施策→KPIの因果関係が明確か
2. 数値整合性 (20点): KPI目標値と数値計画の整合、投資額と成果のバランス
3. SWOT→戦略の妥当性 (20点): SWOT分析の結論が戦略に反映されているか
4. 実現可能性 (20点): 内部環境（リソース）と施策の現実性
5. 欠落・矛盾検出 (20点): 章間の矛盾や抜け漏れ

Grade: S(90+), A(80-89), B(70-79), C(60-69), D(<60)
日本語で回答してください。"""

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
