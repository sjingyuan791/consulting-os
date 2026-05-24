from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum

class ProvenanceType(str, Enum):
    FINANCIAL_DATA = "financial_data"
    INTERNAL_DATA = "internal_data"
    EXTERNAL_DATA = "external_data"
    ASSUMPTION = "assumption"
    DERIVED = "derived"

class Provenance(BaseModel):
    source_tag: ProvenanceType
    source_detail: str = Field(..., description="Specific file or data point source")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")

class BusinessModel(BaseModel):
    model_name: str = Field(..., description="Name of the single primary business model (in Japanese)")
    description: str = Field(..., description="Concise description of the model (in Japanese)")
    revenue_drivers: List[str] = Field(..., description="List of primary revenue drivers (in Japanese)")
    customer_segments: List[str] = Field(..., description="Target customer segments (in Japanese)")
    value_proposition: str = Field(..., description="Core value proposition (in Japanese)")
    operating_constraints: List[str] = Field(..., description="Key operating constraints (in Japanese)")
    provenance: Provenance

class RevenueComponent(BaseModel):
    name: str = Field(..., description="Name of the component (e.g., 'Volume', 'Price')")
    description: str
    variable_name: str = Field(..., description="Variable name used in equation")
    provenance: Provenance

class RevenueLogic(BaseModel):
    equation: str = Field(..., description="Latex or text representation: Revenue = A * B * ...")
    components: List[RevenueComponent]
    description: str = Field(..., description="Explanation of the revenue logic (in Japanese)")

class KPINode(BaseModel):
    name: str = Field(..., description="KPI Name (in Japanese)")
    definition: str = Field(..., description="KPI Definition (in Japanese)")
    unit: str
    measurement_frequency: str = Field(..., description="e.g. Monthly, Quarterly (in Japanese)")
    target_value_3y: Optional[float] = None
    current_value: Optional[float] = None
    children: List['KPINode'] = []
    provenance: Provenance

class WorkingCapitalAssumptions(BaseModel):
    payment_terms_days: float = Field(30.0, description="Receivables collection period (days)")
    inventory_days: float = Field(30.0, description="Inventory holding period (days)")
    prepaid_accrued_items_days: float = Field(0.0, description="Prepaid/Accrued items (days)")

class FinancialModelAssumptions(BaseModel):
    revenue_growth_rate_y1: float = Field(..., description="Year 1 revenue growth rate (0.05 = 5%)")
    revenue_growth_rate_y2: float
    revenue_growth_rate_y3: float
    gross_margin_rate: float
    opex_growth_rate: float
    investment_amount_y1: float
    investment_amount_y2: float
    investment_amount_y3: float
    tax_rate: float = 0.3
    working_capital: WorkingCapitalAssumptions = Field(default_factory=WorkingCapitalAssumptions)
    
    # Debt Information (for amortization calculation)
    existing_debt_balance: float = Field(0.0, description="Remaining principal of existing loans")
    existing_debt_interest_rate: float = Field(0.02, description="Annual interest rate of existing debt")
    existing_debt_remaining_years: int = Field(5, description="Years remaining on existing debt")
    
    new_debt_interest_rate: float = Field(0.03, description="Interest rate for new debt")
    new_debt_borrowing_y1: float = 0.0
    new_debt_borrowing_y2: float = 0.0
    new_debt_borrowing_y3: float = 0.0
    
    provenance: Provenance

class AmortizationRow(BaseModel):
    year: int
    beginning_balance: float
    interest_payment: float
    principal_payment: float
    total_payment: float
    ending_balance: float

class AmortizationSchedule(BaseModel):
    rows: List[AmortizationRow]
    total_interest: float

class SimulationYear(BaseModel):
    year: int
    revenue: float
    cogs: float
    gross_profit: float
    opex: float
    ebitda: float
    operating_profit: float
    net_profit: float
    cash_flow: float

class FinancialSimulation(BaseModel):
    is_verified: bool = Field(..., description="True if based on verified financial data")
    years: List[SimulationYear]
    assumptions_used: FinancialModelAssumptions

class Milestone(BaseModel):
    name: str
    date: str
    kpi_target: str

class Initiative(BaseModel):
    name: str
    owner: str
    timeline_start: str
    timeline_end: str
    expected_revenue_impact: str = Field(..., description="Qualitative or formulaic impact description")
    expected_cost_impact: str
    investment_required: str
    roi_estimate: str
    dependencies: List[str]
    risk_factors: List[str]
    milestones: List[Milestone] = []
    provenance: Provenance

class ExecutionRoadmap(BaseModel):
    initiatives: List[Initiative]

class MissingInput(BaseModel):
    field_name: str
    reason: str
    impact: str


class ExternalConstraints(BaseModel):
    market_growth_rate: float = Field(..., description="Estimated annual market growth rate (0.05 = 5%)")
    demand_ceiling: Optional[float] = Field(None, description="Maximum total addressable market size if known")
    competitive_density_index: float = Field(..., description="0-1 scale (1=Highly Competitive)")
    price_pressure_level: str = Field(..., description="High/Medium/Low")
    cost_inflation_rate: float = Field(0.02, description="Annual cost increase rate")
    regulatory_risk_level: str = Field("Low", description="High/Medium/Low")

class SimulationTrace(BaseModel):
    inputs_used: List[str]
    formulas_applied: List[str]
    scenario_parameters: Dict[str, Any]
    generated_timestamp: str

class DecisionGradeStatus(BaseModel):
    status: str = Field(..., description="'approved', 'blocked', or 'warning'")
    blocking_reasons: List[str] = []
    warnings: List[str] = []

class CashflowProjection(BaseModel):
    operating_cf: float
    investment_cf: float
    financing_cf: float
    ending_cash: float
    free_cash_flow: float

class DebtCapacity(BaseModel):
    dscr: float = Field(..., description="Debt Service Coverage Ratio")
    max_additional_debt: float
    safe_debt_level: float
    interest_coverage_ratio: float

class ScenarioSimulation(BaseModel):
    scenario_name: str
    years: List[SimulationYear]
    cashflow: List[CashflowProjection]
    debt_capacity: List[DebtCapacity]
    assumptions_modified: FinancialModelAssumptions
    amortization_schedule: Optional[AmortizationSchedule] = None

class RefinedStrategicPlan(BaseModel):
    business_model: BusinessModel
    revenue_logic: RevenueLogic
    kpi_tree: KPINode
    financial_assumptions: FinancialModelAssumptions
    
    # Financials
    # Legacy field, kept for backward compatibility but refined logic uses scenarios
    simulation: Optional[FinancialSimulation] = None 
    
    # New Multi-Scenario Simulations
    scenarios: List[ScenarioSimulation] = []
    
    forecast_source: str = Field("assumption_only", description="'deterministic_engine' or 'assumption_only'")
    simulation_trace: Optional[SimulationTrace] = None
    
    execution_roadmap: ExecutionRoadmap
    
    missing_inputs: List[MissingInput] = []
    falsification_conditions: List[str] = Field(default=[], description="Conditions that would prove this plan wrong (in Japanese)")
    confidence_level: float = Field(0.0, description="Overall plan confidence 0-1")
    consistency_findings: List[str] = Field(default=[], description="Structural weaknesses identified in original draft (in Japanese)")
    
    external_constraints: Optional[ExternalConstraints] = None
    decision_grade_status: Optional[DecisionGradeStatus] = None
    
    financials_verified: bool = Field(False, description="Whether financial data was verified during refinement")
