"""
Mid-Term Management Plan Schema Definitions.
中期経営計画書 13セクション構造のPydanticモデル定義。

各セクションは以下の構造を持つ:
- section_id: セクション番号 (1-13)
- section_title: セクションタイトル
- references: 参照する前セクションのID一覧
- narrative: ナラティブテキスト（コンサルレポート文体）
- data: 構造化JSONデータ
"""
from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Optional, Any, Literal
from enum import Enum
from datetime import datetime


# =============================================
# Section 1: Corporate Philosophy (理念)
# =============================================

class CorporatePhilosophy(BaseModel):
    """企業理念セクション"""
    mission: str = Field(..., description="ミッション（存在意義）")
    core_values: List[str] = Field(default=[], description="コアバリュー")
    management_philosophy: str = Field(default="", description="経営理念")
    founding_spirit: str = Field(default="", description="創業精神")
    stakeholder_promise: Dict[str, str] = Field(
        default_factory=dict,
        description="ステークホルダーへの約束（顧客/社員/株主/社会）"
    )

    @model_validator(mode='before')
    @classmethod
    def check_legacy_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # "mission_statement" -> "mission"
            if "mission" not in data and "mission_statement" in data:
                data["mission"] = data["mission_statement"]
        return data


# =============================================
# Section 2: Vision (ビジョン)
# =============================================

class VisionStatement(BaseModel):
    """ビジョンセクション"""
    vision_statement: str = Field(..., description="ビジョンステートメント")
    target_year: int = Field(..., description="ビジョン達成目標年")
    quantitative_goals: List[str] = Field(default=[], description="定量目標")
    qualitative_goals: List[str] = Field(default=[], description="定性目標")
    desired_state: str = Field(default="", description="ありたい姿")
    gap_from_current: str = Field(default="", description="現状とのギャップ")

    @model_validator(mode='before')
    @classmethod
    def fix_imperfect_output(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. vision_statement missing -> Deep Search for longest string
            if "vision_statement" not in data:
                # Try known keys first
                candidates = []
                if "slogan" in data and isinstance(data["slogan"], str): candidates.append(data["slogan"])
                if "vision" in data and isinstance(data["vision"], str): candidates.append(data["vision"])
                
                # Deep search in dict
                def extract_strings(d):
                    for k, v in d.items():
                        if isinstance(v, str):
                            candidates.append(v)
                        elif isinstance(v, dict):
                            extract_strings(v)
                
                extract_strings(data)
                
                if candidates:
                    # Pick the longest string as it's likely the full statement
                    data["vision_statement"] = max(candidates, key=len)
                else:
                    data["vision_statement"] = "Vision statement generation failed."

            # 2. target_year missing -> use current year + 3
            if "target_year" not in data:
                data["target_year"] = datetime.now().year + 3

            # 3. quantitative_goals & qualitative_goals: dict -> list[str]
            for field in ["quantitative_goals", "qualitative_goals"]:
                if field in data and isinstance(data[field], dict):
                    try:
                        data[field] = [f"{k}: {v}" for k, v in data[field].items()]
                    except Exception:
                        data[field] = []
        return data


# =============================================
# Section 3: External Environment Analysis
# =============================================

class PESTItem(BaseModel):
    """PEST分析の個別項目"""
    factor: str = Field(..., description="要因名")
    description: str = Field(default="", description="詳細説明")
    impact: Literal["positive", "negative", "neutral"] = Field(default="neutral")
    significance: Literal["high", "medium", "low"] = Field(default="medium")

class CompetitorProfile(BaseModel):
    """競合プロファイル"""
    name: str = Field(..., description="競合名")
    strengths: List[str] = Field(default=[])
    weaknesses: List[str] = Field(default=[])
    market_share: Optional[float] = None
    strategy_summary: str = Field(default="")

class ExternalEnvironment(BaseModel):
    """外部環境分析セクション"""
    macro_environment: Dict[str, List[PESTItem]] = Field(
        default_factory=lambda: {
            "political": [], "economic": [], "social": [], "technological": []
        },
        description="PEST分析"
    )
    industry_trends: List[str] = Field(default=[], description="業界トレンド")
    market_size: Optional[str] = Field(default=None, description="市場規模")
    market_growth_rate: Optional[str] = Field(default=None, description="市場成長率")
    competitors: List[CompetitorProfile] = Field(default=[], description="競合分析")
    opportunities: List[str] = Field(default=[], description="機会")
    threats: List[str] = Field(default=[], description="脅威")
    key_success_factors: List[str] = Field(default=[], description="業界KSF")

    @model_validator(mode='before')
    @classmethod
    def normalize_pest(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "macro_environment" in data and isinstance(data["macro_environment"], dict):
                for key in ["political", "economic", "social", "technological"]:
                    if key in data["macro_environment"]:
                        val = data["macro_environment"][key]
                        # Case 1: val is simply a string -> convert to list of PESTItem dict
                        if isinstance(val, str):
                            data["macro_environment"][key] = [
                                {"factor": "Key Trend", "description": val}
                            ]
                        # Case 2: val is a list
                        elif isinstance(val, list):
                            new_list = []
                            for item in val:
                                if isinstance(item, str):
                                    # string -> PESTItem dict
                                    new_list.append({"factor": "Trend", "description": item})
                                elif isinstance(item, dict):
                                    new_list.append(item)
                            data["macro_environment"][key] = new_list
        return data


# =============================================
# Section 4: Internal Environment Analysis
# =============================================

class ResourceAssessment(BaseModel):
    """経営資源評価"""
    category: str = Field(..., description="資源カテゴリ（人的/物的/財務/情報/知的）")
    current_state: str = Field(default="")
    assessment: Literal["strong", "adequate", "weak"] = Field(default="adequate")
    key_issues: List[str] = Field(default=[])

class InternalEnvironment(BaseModel):
    """内部環境分析セクション"""
    company_overview: str = Field(default="", description="企業概要")
    financial_health_summary: str = Field(default="", description="財務健全性サマリー")
    core_competencies: List[str] = Field(default=[], description="コアコンピタンス")
    strengths: List[str] = Field(default=[], description="強み")
    weaknesses: List[str] = Field(default=[], description="弱み")
    resource_assessment: List[ResourceAssessment] = Field(
        default=[], description="経営資源評価"
    )
    value_chain_analysis: Dict[str, str] = Field(
        default_factory=dict, description="バリューチェーン分析"
    )
    organizational_capabilities: List[str] = Field(
        default=[], description="組織能力"
    )

    @model_validator(mode='before')
    @classmethod
    def normalize_internal_lists(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field in ["strengths", "weaknesses", "core_competencies", "organizational_capabilities"]:
                if field in data and isinstance(data[field], list):
                     new_list = []
                     for item in data[field]:
                         if isinstance(item, str):
                             new_list.append(item)
                         elif isinstance(item, dict):
                             vals = [str(v) for v in item.values() if isinstance(v, (str, int, float))]
                             if vals: new_list.append(" ".join(vals))
                     data[field] = new_list
        return data


# =============================================
# Section 5: Root Cause Analysis (根本原因分析)
# =============================================

class RootCauseItem(BaseModel):
    """根本原因の個別項目"""
    cause_id: str = Field(..., description="原因ID")
    description: str = Field(..., description="原因の説明")
    category: str = Field(default="", description="カテゴリ（財務/営業/組織/外部）")
    evidence: List[str] = Field(default=[], description="根拠・エビデンス")
    impact_areas: List[str] = Field(default=[], description="影響範囲")
    severity: Literal["critical", "high", "medium", "low"] = Field(default="medium")
    addressability: Literal["high", "medium", "low"] = Field(default="medium")

class RootCauseAnalysis(BaseModel):
    """根本原因分析セクション"""
    primary_symptom: str = Field(..., description="主要症状")
    causal_chain_summary: str = Field(default="", description="因果連鎖の要約")
    root_causes: List[RootCauseItem] = Field(default=[], description="根本原因リスト")
    priority_issues: List[str] = Field(default=[], description="優先課題")
    leverage_points: List[str] = Field(default=[], description="レバレッジポイント")

    @model_validator(mode='before')
    @classmethod
    def normalize_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. root_causes: list[str] -> list[RootCauseItem]
            if "root_causes" in data and isinstance(data["root_causes"], list):
                new_causes = []
                for idx, item in enumerate(data["root_causes"]):
                    # Generate ID
                    cid = f"RC-{idx+1:02d}"
                    
                    if isinstance(item, str):
                        new_causes.append({
                            "cause_id": cid,
                            "description": item,
                            "category": "Uncategorized",
                            "severity": "medium",
                            "addressability": "medium"
                        })
                    elif isinstance(item, dict):
                        # Fix for item={"cause": "..."} missing "cause_id", "description"
                        # Map "cause" -> "description"
                        if "description" not in item:
                            if "cause" in item:
                                item["description"] = item["cause"]
                            elif "issue" in item:
                                item["description"] = item["issue"]
                        
                        # Inject cause_id if missing
                        if "cause_id" not in item:
                            item["cause_id"] = cid
                            
                        # Ensure default fields
                        if "category" not in item: item["category"] = "Uncategorized"
                        if "severity" not in item: item["severity"] = "medium"
                        if "addressability" not in item: item["addressability"] = "medium"
                        
                        new_causes.append(item)
                    else:
                        new_causes.append(item)
                data["root_causes"] = new_causes

            # 2. primary_symptom missing -> infer
            if "primary_symptom" not in data or not data["primary_symptom"]:
                if data.get("root_causes") and len(data["root_causes"]) > 0:
                    first = data["root_causes"][0]
                    desc = first.get("description", "") if isinstance(first, dict) else str(first)
                    data["primary_symptom"] = f"Main Issue: {desc[:50]}..."
                else:
                    data["primary_symptom"] = "詳細はナラティブを参照してください。"
        # 3. leverage_points: dict based list -> list[str]
            if "leverage_points" in data and isinstance(data["leverage_points"], list):
                new_points = []
                for item in data["leverage_points"]:
                    if isinstance(item, str):
                        new_points.append(item)
                    elif isinstance(item, dict):
                        # extract 'point', 'description', 'text', 'value', 'leverage_point'
                        found = False
                        for k in ['point', 'description', 'text', 'value', 'leverage_point']:
                            if k in item and isinstance(item[k], str):
                                new_points.append(item[k])
                                found = True
                                break
                        if not found:
                            # Fallback: join values
                            vals = [str(v) for v in item.values() if isinstance(v, (str, int, float))]
                            if vals:
                                new_points.append(" ".join(vals))
                data["leverage_points"] = new_points
        return data


# =============================================
# Section 6: SWOT Analysis
# =============================================

class SWOTAnalysis(BaseModel):
    """SWOT分析セクション"""
    strengths: List[str] = Field(default=[], description="強み (S)")
    weaknesses: List[str] = Field(default=[], description="弱み (W)")
    opportunities: List[str] = Field(default=[], description="機会 (O)")
    threats: List[str] = Field(default=[], description="脅威 (T)")
    synthesis: str = Field(
        default="",
        description="SWOT総合所見（外部/内部環境分析・根本原因分析との整合性を示す）"
    )

    @model_validator(mode='before')
    @classmethod
    def normalize_lists(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field in ["strengths", "weaknesses", "opportunities", "threats"]:
                if field in data and isinstance(data[field], list):
                    new_list = []
                    for item in data[field]:
                        if isinstance(item, str):
                            new_list.append(item)
                        elif isinstance(item, dict):
                            # Extract string from dict (e.g., {"description": "...", "id": "..."})
                            candidates = []
                            for k in ["description", "text", "summary", "content"]:
                                if k in item and isinstance(item[k], str):
                                    candidates.append(item[k])
                            
                            if candidates:
                                new_list.append(candidates[0])
                            else:
                                # Fallback: values join
                                vals = [str(v) for v in item.values() if isinstance(v, (str, int, float))]
                                if vals:
                                    new_list.append(" ".join(vals))
                    data[field] = new_list
        return data


# =============================================
# Section 7: Cross SWOT Strategy
# =============================================

class CrossSWOTOption(BaseModel):
    """クロスSWOT戦略オプション"""
    strategy_name: str = Field(..., description="戦略名")
    description: str = Field(default="", description="戦略の説明")
    rationale: str = Field(default="", description="策定根拠")
    referenced_swot: List[str] = Field(
        default=[], description="参照したSWOT要素"
    )

class CrossSWOTStrategy(BaseModel):
    """クロスSWOT戦略セクション"""
    so_strategies: List[CrossSWOTOption] = Field(
        default=[], description="積極攻勢戦略 (S×O)"
    )
    wo_strategies: List[CrossSWOTOption] = Field(
        default=[], description="弱点克服戦略 (W×O)"
    )
    st_strategies: List[CrossSWOTOption] = Field(
        default=[], description="差別化戦略 (S×T)"
    )
    wt_strategies: List[CrossSWOTOption] = Field(
        default=[], description="防衛・撤退戦略 (W×T)"
    )
    strategic_priority: List[str] = Field(
        default=[], description="戦略優先順位"
    )


# =============================================
# Section 8: Corporate Strategy (全社戦略)
# =============================================

class CorporateStrategySection(BaseModel):
    """全社戦略セクション"""
    strategic_intent: str = Field(..., description="戦略意図")
    growth_direction: Literal[
        "market_penetration", "market_development",
        "product_development", "diversification", "restructuring"
    ] = Field(default="market_penetration", description="成長方向性（アンゾフマトリクス）")
    portfolio_strategy: str = Field(
        default="", description="事業ポートフォリオ戦略"
    )
    resource_allocation_policy: str = Field(
        default="", description="経営資源配分方針"
    )
    synergy_strategy: str = Field(default="", description="シナジー戦略")
    long_term_goals: List[str] = Field(default=[], description="長期目標")
    core_values_alignment: str = Field(
        default="",
        description="理念・ビジョンとの整合性"
    )

    @model_validator(mode='before')
    @classmethod
    def flatten_dicts(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Check all string fields, if they are dicts, convert to json string or values join
            for field in ["resource_allocation_policy", "portfolio_strategy", "synergy_strategy", "core_values_alignment", "strategic_intent"]:
                if field in data and isinstance(data[field], dict):
                    # Join values with newline
                    try:
                        data[field] = "\n".join([f"{k}: {v}" for k, v in data[field].items()])
                    except Exception:
                        data[field] = str(data[field])
        return data


# =============================================
# Section 9: Business Domain Strategy (事業ドメイン戦略)
# =============================================

class DomainStrategyItem(BaseModel):
    """個別事業ドメイン戦略"""
    domain_name: str = Field(..., description="事業ドメイン名")
    target_market: str = Field(default="", description="ターゲット市場")
    competitive_strategy: Literal[
        "cost_leadership", "differentiation", "focus", "hybrid"
    ] = Field(default="differentiation", description="競争戦略タイプ")
    value_proposition: str = Field(default="", description="価値提案")
    target_segments: List[str] = Field(default=[], description="ターゲットセグメント")
    competitive_advantages: List[str] = Field(default=[], description="競争優位性")
    growth_strategy: str = Field(default="", description="成長戦略")

class BusinessDomainStrategy(BaseModel):
    """事業ドメイン戦略セクション"""
    domains: List[DomainStrategyItem] = Field(
        default=[], description="事業ドメイン一覧"
    )
    portfolio_positioning: str = Field(
        default="", description="ポートフォリオ上のポジショニング"
    )
    cross_domain_synergies: List[str] = Field(
        default=[], description="ドメイン間シナジー"
    )

    @model_validator(mode='before')
    @classmethod
    def normalize_domain_lists(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "cross_domain_synergies" in data and isinstance(data["cross_domain_synergies"], list):
                 new_list = []
                 for item in data["cross_domain_synergies"]:
                     if isinstance(item, str):
                         new_list.append(item)
                     elif isinstance(item, dict):
                         vals = [str(v) for v in item.values() if isinstance(v, (str, int, float))]
                         if vals: new_list.append(" ".join(vals))
                 data["cross_domain_synergies"] = new_list
        return data


# =============================================
# Section 10: Functional Strategies (機能別戦略)
# =============================================

class FunctionalStrategyItem(BaseModel):
    """個別機能戦略"""
    function_name: str = Field(..., description="機能名（営業/マーケティング/生産/人事/財務/IT）")
    objectives: List[str] = Field(default=[], description="目標")
    key_initiatives: List[str] = Field(default=[], description="主要施策")
    resource_requirements: str = Field(default="", description="必要資源")
    success_metrics: List[str] = Field(default=[], description="成功指標")
    timeline: str = Field(default="", description="スケジュール")

class FunctionalStrategies(BaseModel):
    """機能別戦略セクション"""
    strategies: List[FunctionalStrategyItem] = Field(
        default=[], description="機能別戦略一覧"
    )
    cross_functional_priorities: List[str] = Field(
        default=[], description="横断的優先事項"
    )

    @model_validator(mode='before')
    @classmethod
    def normalize_functional(cls, data: Any) -> Any:
        if isinstance(data, dict):
             if "cross_functional_priorities" in data and isinstance(data["cross_functional_priorities"], dict):
                 try:
                     # Convert dict to list of strings "Key: Value"
                     data["cross_functional_priorities"] = [f"{k}: {v}" for k, v in data["cross_functional_priorities"].items()]
                 except Exception:
                     pass

             # 2. strategies: dict -> list[FunctionalStrategyItem]
             if "strategies" in data and isinstance(data["strategies"], dict):
                 new_strategies = []
                 for func_name, details in data["strategies"].items():
                     if isinstance(details, dict):
                         # If key is function name, inject it
                         if "function_name" not in details:
                             details["function_name"] = func_name
                         new_strategies.append(details)
                 data["strategies"] = new_strategies
        return data


# =============================================
# Section 11: Strategic Initiatives (施策)
# =============================================

class InitiativeItem(BaseModel):
    """個別施策"""
    initiative_id: str = Field(..., description="施策ID")
    title: str = Field(..., description="施策タイトル")
    description: str = Field(default="", description="詳細説明")
    owner: str = Field(default="", description="責任者")
    priority: Literal["high", "medium", "low"] = Field(default="medium")
    timeline: str = Field(default="", description="実施期間")
    estimated_cost: Optional[float] = Field(default=None, description="見込みコスト（万円）")
    expected_impact: str = Field(default="", description="期待効果")
    linked_strategy: str = Field(
        default="", description="紐づく戦略（セクション8-10への参照）"
    )
    linked_root_cause: str = Field(
        default="", description="対処する根本原因（セクション5への参照）"
    )
    kpi_link: str = Field(default="", description="測定KPI（セクション12への参照）")

class StrategicInitiatives(BaseModel):
    """施策セクション"""
    initiatives: List[InitiativeItem] = Field(default=[], description="施策一覧")
    implementation_phases: List[Dict[str, Any]] = Field(
        default=[], description="実行フェーズ"
    )
    quick_wins: List[str] = Field(default=[], description="クイックウィン")
    total_investment: Optional[float] = Field(
        default=None, description="総投資額（万円）"
    )

    @model_validator(mode='before')
    @classmethod
    def normalize_initiatives(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "initiatives" in data and isinstance(data["initiatives"], list):
                for idx, init in enumerate(data["initiatives"]):
                    if isinstance(init, dict):
                        # 1. name -> title
                        if "title" not in init and "name" in init:
                            init["title"] = init["name"]
                        
                        # 2. initiative_id missing
                        if "initiative_id" not in init:
                            init["initiative_id"] = f"SI-{idx+1:02d}"
                            
                        # 3. priority case sensitivity
                        if "priority" in init and isinstance(init["priority"], str):
                            init["priority"] = init["priority"].lower()
                            if init["priority"] not in ["high", "medium", "low"]:
                                init["priority"] = "medium"
                        
                        # 4. Missing required fields fallback
                        if "title" not in init: init["title"] = "Untitled Initiative"
            
            # 5. quick_wins: dict based list -> list[str]
            if "quick_wins" in data and isinstance(data["quick_wins"], list):
                new_qw = []
                for item in data["quick_wins"]:
                    if isinstance(item, str):
                        new_qw.append(item)
                    elif isinstance(item, dict):
                        # extract values
                        vals = [str(v) for v in item.values() if isinstance(v, (str, int, float))]
                        if vals:
                            new_qw.append(" ".join(vals))
                data["quick_wins"] = new_qw
        return data


# =============================================
# Section 12: KPI Architecture
# =============================================

class KPIItem(BaseModel):
    """個別KPI"""
    kpi_id: str = Field(default="", description="KPI ID")
    name: str = Field(..., description="KPI名")
    category: Literal["financial", "customer", "process", "learning"] = Field(
        default="financial", description="BSCカテゴリ"
    )
    definition: str = Field(default="", description="KPI定義")
    calculation_method: str = Field(default="", description="算出方法")
    unit: str = Field(default="", description="単位")
    current_value: Optional[float] = Field(default=None, description="現在値")
    targets: Dict[str, float] = Field(
        default_factory=dict, description="年度別目標値 (例: {'Y1': 100, 'Y2': 120})"
    )
    data_source: str = Field(default="", description="データソース")
    owner: str = Field(default="", description="責任者")
    linked_initiative: str = Field(
        default="", description="紐づく施策（セクション11への参照）"
    )
    monitoring_frequency: str = Field(default="monthly", description="モニタリング頻度")

    @model_validator(mode='before')
    @classmethod
    def set_kpi_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. Generate kpi_id if missing
            if not data.get("kpi_id"):
                import uuid
                data["kpi_id"] = f"KPI-{str(uuid.uuid4())[:4].upper()}"
            
            # 2. Relax category validation
            if "category" in data and data["category"] not in ["financial", "customer", "process", "learning"]:
                data["category"] = "financial"  # Default
                
        return data

class KPIArchitecture(BaseModel):
    """KPIアーキテクチャセクション"""
    strategic_kpis: List[KPIItem] = Field(default=[], description="戦略KPI")
    operational_kpis: List[KPIItem] = Field(default=[], description="業務KPI")
    balanced_scorecard: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "financial": [], "customer": [], "process": [], "learning": []
        },
        description="バランススコアカード"
    )
    review_cadence: str = Field(
        default="月次レビュー、四半期全体振り返り", description="レビューサイクル"
    )

    @model_validator(mode='before')
    @classmethod
    def normalize_bsc(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "balanced_scorecard" in data and isinstance(data["balanced_scorecard"], dict):
                for key in data["balanced_scorecard"]:
                     val = data["balanced_scorecard"][key]
                     if isinstance(val, list):
                         new_list = []
                         for item in val:
                             if isinstance(item, str):
                                 new_list.append(item)
                             elif isinstance(item, dict):
                                 vals = [str(v) for v in item.values() if isinstance(v, (str, int, float))]
                                 if vals: new_list.append(" ".join(vals))
                         data["balanced_scorecard"][key] = new_list
            
            # Helper: Ensure strategic_kpis exists if user put it in 'kpis'
            if "strategic_kpis" not in data and "kpis" in data:
                 data["strategic_kpis"] = data["kpis"]
                 
        return data


# =============================================
# Section 13: Financial & Numerical Plan (数値計画)
# =============================================

class YearlyFinancials(BaseModel):
    """年度別財務数値"""
    year: int
    revenue: float = Field(..., description="売上高（百万円）")
    cost_of_goods: Optional[float] = Field(default=None, description="売上原価")
    gross_profit: Optional[float] = Field(default=None, description="粗利益")
    operating_expenses: Optional[float] = Field(default=None, description="販管費")
    operating_profit: Optional[float] = Field(default=None, description="営業利益")
    net_profit: Optional[float] = Field(default=None, description="純利益")
    key_assumptions: List[str] = Field(default=[], description="主要前提条件")

class FinancialNumericalPlan(BaseModel):
    """数値計画セクション"""
    plan_period_years: int = Field(default=3, description="計画期間（年）")
    base_year: int = Field(..., description="基準年")
    projections: List[YearlyFinancials] = Field(
        default=[], description="年度別財務計画"
    )
    investment_plan_summary: str = Field(
        default="", description="投資計画サマリー"
    )
    funding_plan: str = Field(default="", description="資金調達計画")
    sensitivity_scenarios: List[Dict[str, Any]] = Field(
        default=[], description="感度分析シナリオ"
    )
    revenue_cagr: Optional[float] = Field(default=None, description="売上CAGR")
    profit_cagr: Optional[float] = Field(default=None, description="利益CAGR")
    kpi_financial_linkage: str = Field(
        default="",
        description="KPIと数値計画の連動説明（セクション12への参照）"
    )

    @model_validator(mode='before')
    @classmethod
    def set_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "base_year" not in data:
                data["base_year"] = datetime.now().year
            
            # Reduce dicts to strings for specific fields
            for field in ["funding_plan", "investment_plan_summary", "kpi_financial_linkage"]:
                if field in data and isinstance(data[field], dict):
                    try:
                         data[field] = "\n".join([f"{k}: {v}" for k, v in data[field].items()])
                    except Exception:
                        data[field] = str(data[field])
        return data


# =============================================
# Unified Section Wrapper & Document
# =============================================

class ChapterStatus(str, Enum):
    DRAFT = "DRAFT"
    AI_GENERATED = "AI_GENERATED"
    HUMAN_MODIFIED = "HUMAN_MODIFIED"
    APPROVED = "APPROVED"
    LOCKED = "LOCKED"

class ChapterState(BaseModel):
    """チャプターの状態管理"""
    status: ChapterStatus = Field(default=ChapterStatus.DRAFT, description="ステータス")
    version: int = Field(default=1, description="バージョン")
    approved_by: Optional[str] = Field(default=None, description="承認者")
    approved_at: Optional[str] = Field(default=None, description="承認日時")
    context_snapshot: Optional[str] = Field(default=None, description="ロック時のコンテキストスナップショット")


class MidtermPlanSection(BaseModel):
    """中期経営計画の1セクション（汎用ラッパー）"""
    section_id: int = Field(..., ge=1, le=13, description="セクション番号")
    section_title: str = Field(..., description="セクションタイトル")
    section_title_en: str = Field(default="", description="英語タイトル")
    references: List[int] = Field(
        default=[], description="参照する前セクションID一覧"
    )
    narrative: str = Field(default="", description="ナラティブテキスト")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="構造化JSONデータ"
    )
    chapter_state: ChapterState = Field(
        default_factory=ChapterState, description="チャプター状態"
    )


# Section titles mapping
SECTION_DEFINITIONS = [
    {"id": 1, "title": "企業理念", "title_en": "Corporate Philosophy",
     "references": []},
    {"id": 2, "title": "ビジョン", "title_en": "Vision",
     "references": [1]},
    {"id": 3, "title": "外部環境分析", "title_en": "External Environment Analysis",
     "references": []},
    {"id": 4, "title": "内部環境分析", "title_en": "Internal Environment Analysis",
     "references": []},
    {"id": 5, "title": "根本原因分析", "title_en": "Root Cause Analysis",
     "references": [3, 4]},
    {"id": 6, "title": "SWOT分析", "title_en": "SWOT Analysis",
     "references": [3, 4, 5]},
    {"id": 7, "title": "クロスSWOT戦略", "title_en": "Cross SWOT Strategy",
     "references": [6]},
    {"id": 8, "title": "全社戦略", "title_en": "Corporate Strategy",
     "references": [1, 2, 5, 7]},
    {"id": 9, "title": "事業ドメイン戦略", "title_en": "Business Domain Strategy",
     "references": [8, 7]},
    {"id": 10, "title": "機能別戦略", "title_en": "Functional Strategies",
     "references": [8, 9]},
    {"id": 11, "title": "施策", "title_en": "Strategic Initiatives",
     "references": [5, 7, 8, 9, 10]},
    {"id": 12, "title": "KPIアーキテクチャ", "title_en": "KPI Architecture",
     "references": [8, 9, 10, 11]},
    {"id": 13, "title": "数値計画", "title_en": "Financial and Numerical Plan",
     "references": [11, 12]},
]


class DependencyEdge(BaseModel):
    """依存関係のエッジ"""
    from_section: int = Field(..., description="参照元セクションID")
    to_section: int = Field(..., description="参照先セクションID")
    relationship: str = Field(default="references", description="関係タイプ")
    description: str = Field(default="", description="依存関係の説明")


class LogicalDependencyMap(BaseModel):
    """セクション間の論理依存マップ"""
    edges: List[DependencyEdge] = Field(default=[], description="依存関係エッジ一覧")
    critical_path: List[int] = Field(
        default=[], description="クリティカルパス（セクションID順）"
    )
    
    @classmethod
    def build_from_definitions(cls) -> "LogicalDependencyMap":
        """SECTION_DEFINITIONSから依存マップを構築"""
        edges = []
        for sec_def in SECTION_DEFINITIONS:
            for ref_id in sec_def["references"]:
                edges.append(DependencyEdge(
                    from_section=sec_def["id"],
                    to_section=ref_id,
                    relationship="references",
                    description=f"{sec_def['title']}は{SECTION_DEFINITIONS[ref_id - 1]['title']}を参照"
                ))
        # Critical path: the longest dependency chain
        critical_path = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
        return cls(edges=edges, critical_path=critical_path)

    def to_mermaid(self) -> str:
        """Mermaidダイアグラム文字列を生成"""
        lines = ["graph TD"]
        # Node definitions
        for sec_def in SECTION_DEFINITIONS:
            node_id = f"S{sec_def['id']}"
            label = f"{sec_def['id']}. {sec_def['title']}"
            lines.append(f"    {node_id}[\"{label}\"]")
        # Edge definitions
        for edge in self.edges:
            lines.append(f"    S{edge.to_section} --> S{edge.from_section}")
        return "\n".join(lines)


# =============================================
# Section 14: Quality Check (品質チェック)
# =============================================

class QAAxisScore(BaseModel):
    """品質チェック 個別軸スコア"""
    axis_name: str = Field(..., description="評価軸名")
    score: int = Field(..., ge=1, le=20, description="スコア (1-20)")
    assessment: str = Field(default="", description="評価コメント")
    issues: List[str] = Field(default=[], description="検出された問題")
    recommendations: List[str] = Field(default=[], description="推奨事項")

class QAIssueItem(BaseModel):
    """品質チェック 指摘事項"""
    severity: str = Field(..., description="重要度: critical / warning / info")
    target_section: int = Field(..., ge=1, le=13, description="対象セクションID")
    target_section_title: str = Field(default="", description="対象セクション名")
    description: str = Field(..., description="指摘内容")
    suggestion: str = Field(default="", description="改善案（修正テキスト）")

class QualityCheckResult(BaseModel):
    """品質チェック結果"""
    overall_score: int = Field(default=0, ge=0, le=100, description="総合スコア (0-100)")
    grade: str = Field(default="", description="総合評価 (S/A/B/C/D)")
    executive_summary: str = Field(default="", description="エグゼクティブサマリー")
    
    # 5軸評価
    axis_scores: List[QAAxisScore] = Field(default=[], description="5軸評価スコア")
    
    # 指摘事項（重要度別）
    critical_issues: List[QAIssueItem] = Field(default=[], description="要修正（致命的）")
    warnings: List[QAIssueItem] = Field(default=[], description="改善推奨")
    strengths: List[str] = Field(default=[], description="強み・良い点")
    
    # クロスリファレンス
    cross_reference_summary: str = Field(default="", description="章間整合性サマリー")
    
    checked_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="チェック実行日時"
    )


class MidtermPlanDocument(BaseModel):
    """中期経営計画書の完全なドキュメント"""
    document_id: str = Field(default="", description="ドキュメントID")
    client_id: str = Field(default="", description="クライアントID")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="作成日時"
    )
    plan_period: str = Field(default="3年", description="計画期間")
    
    # 13 Sections
    sections: List[MidtermPlanSection] = Field(
        default=[], description="13セクション"
    )
    
    # Typed section data
    corporate_philosophy: Optional[CorporatePhilosophy] = None
    vision: Optional[VisionStatement] = None
    external_environment: Optional[ExternalEnvironment] = None
    internal_environment: Optional[InternalEnvironment] = None
    root_cause_analysis: Optional[RootCauseAnalysis] = None
    swot_analysis: Optional[SWOTAnalysis] = None
    cross_swot_strategy: Optional[CrossSWOTStrategy] = None
    corporate_strategy: Optional[CorporateStrategySection] = None
    business_domain_strategy: Optional[BusinessDomainStrategy] = None
    functional_strategies: Optional[FunctionalStrategies] = None
    strategic_initiatives: Optional[StrategicInitiatives] = None
    kpi_architecture: Optional[KPIArchitecture] = None
    financial_plan: Optional[FinancialNumericalPlan] = None
    
    # Dependency map
    dependency_map: Optional[LogicalDependencyMap] = None
    
    # Quality Check Result
    quality_check: Optional[QualityCheckResult] = None

    def validate_section_order(self) -> bool:
        """セクションが1-13の正しい順序であることを検証"""
        if len(self.sections) != 13:
            return False
        for i, section in enumerate(self.sections):
            if section.section_id != i + 1:
                return False
        return True

    def validate_references(self) -> List[str]:
        """参照整合性を検証し、エラーリストを返す"""
        errors = []
        section_ids = {s.section_id for s in self.sections}
        for section in self.sections:
            for ref_id in section.references:
                if ref_id not in section_ids:
                    errors.append(
                        f"Section {section.section_id} references non-existent section {ref_id}"
                    )
                if ref_id >= section.section_id:
                    errors.append(
                        f"Section {section.section_id} references later section {ref_id} (forward reference)"
                    )
        return errors

