"""
Pipeline Stage Schemas - Data models for 7-stage consulting pipeline.
All stage inputs and outputs are defined here for type safety and validation.
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from uuid import UUID
from enum import Enum


# =============================================
# Enums and Constants
# =============================================

class PipelineStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class CheckpointStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVISION_REQUESTED = "REVISION_REQUESTED"


class CheckpointType(str, Enum):
    ROOT_CAUSE_CONFIRMATION = "root_cause_confirmation"
    STRATEGY_DIRECTION = "strategy_direction"
    TACTICAL_PRIORITIZATION = "tactical_prioritization"


# =============================================
# Stage 1: ROA Deductive Engine
# =============================================

class ROABreakdown(BaseModel):
    """DuPont Analysis Structure"""
    roa: float = Field(..., description="Return on Assets")
    roe: float = Field(..., description="Return on Equity")
    profit_margin: float = Field(..., description="売上高利益率")
    asset_turnover: float = Field(..., description="総資産回転率")
    financial_leverage: float = Field(..., description="財務レバレッジ")
    
    # Sub-components
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    receivables_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    fixed_asset_turnover: Optional[float] = None


class FinancialNode(BaseModel):
    """A weak point in financial analysis"""
    id: str
    metric_name: str
    current_value: float
    benchmark_value: Optional[float] = None
    deviation_percent: Optional[float] = None
    severity: Literal["critical", "high", "medium", "low"]
    trend: Literal["improving", "stable", "declining"]


class FinancialHypothesis(BaseModel):
    """Generated financial issue hypothesis"""
    id: str
    category: Literal["profitability", "efficiency", "liquidity", "solvency"]
    description: str
    severity: Literal["critical", "high", "medium", "low"]
    evidence: List[str]
    metrics_affected: List[str]
    suggested_investigation: str


class Stage1Output(BaseModel):
    """Stage 1: ROA Deductive Engine Output"""
    run_id: Optional[str] = None
    analysis_years: List[int]
    
    # ROA Decomposition
    roa_breakdown: ROABreakdown
    year_over_year_changes: Optional[Dict[str, float]] = None
    
    # Identified Issues
    weak_financial_nodes: List[FinancialNode]
    financial_hypotheses: List[FinancialHypothesis]
    suspected_problem_nodes: List[str]
    
    # Metadata
    data_sources: List[str] = []
    confidence_score: float = 0.0
    analysis_summary: str = ""


# =============================================
# Stage 2: Root Cause Inductive Engine
# =============================================

class CausalNode(BaseModel):
    """Node in causal graph"""
    id: str
    label: str
    node_type: Literal["symptom", "intermediate", "root_cause", "external"]
    category: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    description: Optional[str] = None


class CausalEdge(BaseModel):
    """Edge in causal graph"""
    source: str
    target: str
    relationship: Literal["causes", "amplifies", "inhibits", "correlates"]
    strength: float = Field(..., ge=-1.0, le=1.0)
    evidence: str = ""
    confidence: float = 0.5


class CausalMap(BaseModel):
    """Complete causal graph structure"""
    nodes: List[CausalNode]
    edges: List[CausalEdge]
    
    def get_root_causes(self) -> List[CausalNode]:
        return [n for n in self.nodes if n.node_type == "root_cause"]


class RootCause(BaseModel):
    """Identified root cause with supporting evidence"""
    id: str
    description: str
    category: str  # e.g., "operational", "market", "organizational"
    confidence: float
    supporting_evidence: List[str]
    impact_scope: List[str]
    addressability: Literal["high", "medium", "low"]
    priority_rank: int = 0


class CausalChain(BaseModel):
    """Chain of causation from root to symptom"""
    chain_id: str
    nodes: List[str]  # node IDs in order
    total_strength: float
    description: str


class Stage2Output(BaseModel):
    """Stage 2: Root Cause Inductive Engine Output"""
    run_id: Optional[str] = None
    
    # Causal Structure
    causal_map: CausalMap
    primary_root_cause: RootCause
    secondary_causes: List[RootCause]
    
    # Analysis Details
    causal_chains: List[CausalChain] = []
    feedback_loops: List[Dict[str, Any]] = []
    leverage_points: List[str] = []
    
    confidence_score: float = 0.0
    analysis_summary: str = ""


# =============================================
# Stage 3: Hypothesis Verification Planner
# =============================================

class DataRequirement(BaseModel):
    """Required additional data for verification"""
    id: str
    data_type: str
    description: str
    source: str
    priority: Literal["critical", "important", "nice_to_have"]
    acquisition_method: str
    estimated_effort: str = ""


class InterviewQuestion(BaseModel):
    """Structured interview question"""
    id: str
    target_role: str  # e.g., "経営者", "営業部長"
    question: str
    hypothesis_link: str
    expected_insight: str
    follow_up_questions: List[str] = []


class ValidationMethod(BaseModel):
    """Method to validate a hypothesis"""
    id: str
    hypothesis_id: str
    method_type: Literal["quantitative", "qualitative", "mixed"]
    description: str
    success_criteria: str
    data_requirements: List[str]
    estimated_duration: str = ""


class HypothesisVerification(BaseModel):
    """Full verification plan for a single hypothesis"""
    hypothesis_id: str
    hypothesis_description: str
    verification_approach: str
    required_data: List[str]
    validation_methods: List[str]
    success_criteria: str
    estimated_confidence_if_verified: float


class Stage3Output(BaseModel):
    """Stage 3: Hypothesis Verification Planner Output"""
    run_id: Optional[str] = None
    
    hypotheses_to_verify: List[HypothesisVerification]
    required_additional_data: List[DataRequirement]
    interview_questions: List[InterviewQuestion]
    validation_methods: List[ValidationMethod]
    
    verification_timeline: str = ""
    resource_requirements: Dict[str, Any] = {}
    
    confidence_score: float = 0.0


# =============================================
# Stage 4: Strategy Design Engine
# =============================================

class CorporateStrategy(BaseModel):
    """全社戦略"""
    vision: str
    mission: str
    strategic_intent: str
    core_values: List[str] = []
    portfolio_direction: Literal["growth", "maintain", "harvest", "divest"]
    resource_allocation_priority: List[str]
    long_term_goals: List[str] = []


class DomainStrategy(BaseModel):
    """事業戦略"""
    domain_id: str
    domain_name: str
    competitive_position: str
    strategic_type: Literal["cost_leadership", "differentiation", "focus", "hybrid"]
    target_segments: List[str]
    value_proposition: str
    competitive_advantages: List[str]
    growth_strategy: Literal["market_penetration", "market_development", "product_development", "diversification"]
    key_success_factors: List[str] = []


class FunctionalStrategy(BaseModel):
    """機能別戦略"""
    function_id: str
    function: Literal["sales", "marketing", "operations", "finance", "hr", "rd", "it"]
    function_name_ja: str
    objectives: List[str]
    key_initiatives: List[str]
    resource_requirements: Dict[str, Any] = {}
    success_metrics: List[str]
    timeline: str = ""


class RiskItem(BaseModel):
    """Strategic risk item"""
    id: str
    description: str
    probability: Literal["high", "medium", "low"]
    impact: Literal["high", "medium", "low"]
    mitigation_strategy: str


class RiskAssessment(BaseModel):
    """Overall risk assessment"""
    strategic_risks: List[RiskItem]
    operational_risks: List[RiskItem]
    financial_risks: List[RiskItem]
    overall_risk_level: Literal["high", "medium", "low"]


class Stage4Output(BaseModel):
    """Stage 4: Strategy Design Engine Output"""
    run_id: Optional[str] = None
    
    corporate_strategy: CorporateStrategy
    domain_strategies: List[DomainStrategy]
    functional_strategies: List[FunctionalStrategy]
    
    strategy_rationale: str = ""
    risk_assessment: Optional[RiskAssessment] = None
    
    confidence_score: float = 0.0


# =============================================
# Stage 5: HOW-Tree Tactical Generator
# =============================================

class TacticalOption(BaseModel):
    """Single tactical option"""
    id: str
    name: str
    description: str
    pros: List[str]
    cons: List[str]
    estimated_cost: float
    estimated_impact: float
    implementation_difficulty: Literal["low", "medium", "high"]
    time_to_value: str
    dependencies: List[str] = []


class TacticalOptionSet(BaseModel):
    """Set of options for a strategy"""
    strategy_link: str
    strategy_name: str
    options: List[TacticalOption]
    recommended_option: str
    recommendation_rationale: str


class HOWNode(BaseModel):
    """Node in HOW tree"""
    id: str
    parent_id: Optional[str] = None
    level: int
    description: str
    owner: Optional[str] = None
    deadline: Optional[str] = None
    kpi: Optional[str] = None
    status: str = "planned"
    children_ids: List[str] = []


class HOWTree(BaseModel):
    """Complete HOW decomposition tree"""
    tree_id: str
    root_objective: str
    strategy_link: str
    nodes: List[HOWNode]
    
    def get_leaf_actions(self) -> List[HOWNode]:
        parent_ids = {n.parent_id for n in self.nodes if n.parent_id}
        return [n for n in self.nodes if n.id not in parent_ids]


class PrioritizedAction(BaseModel):
    """Prioritized action item"""
    id: str
    action: str
    priority_score: float
    impact: float
    effort: float
    quickwin: bool = False
    owner: Optional[str] = None
    timeline: str = ""


class Milestone(BaseModel):
    """Implementation milestone"""
    id: str
    name: str
    target_date: str
    deliverables: List[str]
    dependencies: List[str] = []
    owner: Optional[str] = None


class Stage5Output(BaseModel):
    """Stage 5: HOW-Tree Tactical Generator Output"""
    run_id: Optional[str] = None
    
    tactical_option_sets: List[TacticalOptionSet]
    how_trees: List[HOWTree]
    prioritized_actions: List[PrioritizedAction]
    milestones: List[Milestone]
    
    quick_wins: List[str] = []
    implementation_phases: List[Dict[str, Any]] = []
    
    confidence_score: float = 0.0


# =============================================
# Stage 6: KPI & Financial Planning
# =============================================

class KPIDefinition(BaseModel):
    """KPI definition with targets"""
    id: str
    name: str
    name_ja: str
    category: Literal["financial", "customer", "process", "learning"]
    definition: str
    calculation_method: str
    unit: str
    targets: Dict[int, float]  # year -> target value
    data_source: str
    owner: str
    update_frequency: str = "monthly"


class BalancedScorecard(BaseModel):
    """Balanced Scorecard structure"""
    financial_kpis: List[str]
    customer_kpis: List[str]
    process_kpis: List[str]
    learning_kpis: List[str]
    strategic_themes: List[str]


class KPIPlan(BaseModel):
    """Complete KPI plan"""
    strategic_kpis: List[KPIDefinition]
    operational_kpis: List[KPIDefinition]
    balanced_scorecard: BalancedScorecard


class YearlyProjection(BaseModel):
    """Financial projection for a single year"""
    year: int
    baseline: float
    optimistic: float
    pessimistic: float
    key_drivers: List[str]
    assumptions: List[str] = []


class FinancialProjection(BaseModel):
    """Complete financial projection"""
    projection_years: int
    base_year: int
    
    revenue_projection: List[YearlyProjection]
    cost_projection: List[YearlyProjection]
    profit_projection: List[YearlyProjection]
    cash_flow_projection: List[YearlyProjection]
    
    key_assumptions: List[str]
    sensitivity_factors: List[str] = []


class InvestmentItem(BaseModel):
    """Investment requirement"""
    id: str
    name: str
    category: str
    amount: float
    timing: str
    expected_roi: Optional[float] = None
    payback_period: Optional[str] = None


class InvestmentPlan(BaseModel):
    """Investment planning"""
    total_investment: float
    investments: List[InvestmentItem]
    funding_sources: List[Dict[str, Any]]
    investment_timeline: Dict[int, float]  # year -> amount


class SensitivityScenario(BaseModel):
    """Sensitivity analysis scenario"""
    name: str
    description: str
    variable_changes: Dict[str, float]
    impact_on_profit: float
    impact_on_cash: float


class SensitivityAnalysis(BaseModel):
    """Sensitivity analysis results"""
    scenarios: List[SensitivityScenario]
    critical_variables: List[str]
    breakeven_thresholds: Dict[str, float]


class Stage6Output(BaseModel):
    """Stage 6: KPI & Financial Planning Output"""
    run_id: Optional[str] = None
    
    kpi_plan: KPIPlan
    financial_projection: FinancialProjection
    investment_plan: InvestmentPlan
    sensitivity_analysis: Optional[SensitivityAnalysis] = None
    
    confidence_score: float = 0.0


# =============================================
# Stage 7: Mid-Term Management Plan Generator
# =============================================

class ExternalAnalysis(BaseModel):
    """External environment analysis section"""
    market_overview: str
    industry_trends: List[str]
    competitive_landscape: str
    opportunities: List[str]
    threats: List[str]
    pest_analysis: Optional[Dict[str, List[str]]] = None


class InternalAnalysis(BaseModel):
    """Internal analysis section"""
    company_overview: str
    strengths: List[str]
    weaknesses: List[str]
    core_competencies: List[str]
    resource_assessment: Dict[str, str]


class RootCauseSection(BaseModel):
    """Root cause analysis section"""
    primary_issues: List[str]
    causal_analysis_summary: str
    priority_areas: List[str]


class StrategySection(BaseModel):
    """Strategy framework section"""
    vision_statement: str
    mission_statement: str
    strategic_objectives: List[str]
    key_strategies: List[Dict[str, str]]


class TacticalRoadmapSection(BaseModel):
    """Tactical roadmap section"""
    year1_priorities: List[str]
    year2_priorities: List[str]
    year3_priorities: List[str]
    key_milestones: List[Dict[str, str]]
    resource_allocation: Dict[str, float]


class KPIDashboardSection(BaseModel):
    """KPI dashboard plan section"""
    key_metrics: List[Dict[str, Any]]
    monitoring_frequency: str
    review_process: str


class FinancialPlanSection(BaseModel):
    """Financial plan section"""
    revenue_targets: Dict[int, float]
    profit_targets: Dict[int, float]
    investment_summary: str
    funding_requirements: str


class RiskManagementSection(BaseModel):
    """Risk management section"""
    key_risks: List[Dict[str, str]]
    mitigation_strategies: List[str]
    contingency_plans: List[str]


class GovernanceSection(BaseModel):
    """Implementation governance section"""
    steering_committee: List[str]
    review_cadence: str
    reporting_structure: str
    escalation_process: str


class Appendix(BaseModel):
    """Plan appendix"""
    title: str
    content_type: str
    content: Any


class MidTermManagementPlan(BaseModel):
    """Stage 7: Complete Mid-Term Management Plan"""
    run_id: Optional[str] = None
    client_id: Optional[str] = None
    version: int = 1
    
    # Document Metadata
    plan_title: str = "中期経営計画"
    plan_period: str  # e.g., "2026-2030"
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Plan Sections
    executive_summary: str
    external_environment_analysis: ExternalAnalysis
    internal_analysis: InternalAnalysis
    root_cause_analysis: RootCauseSection
    strategy_framework: StrategySection
    tactical_roadmap: TacticalRoadmapSection
    kpi_dashboard_plan: KPIDashboardSection
    financial_plan: FinancialPlanSection
    risk_management: RiskManagementSection
    implementation_governance: GovernanceSection
    
    # Appendices
    appendices: List[Appendix] = []
    
    confidence_score: float = 0.0


# Type alias for stage outputs
Stage7Output = MidTermManagementPlan
