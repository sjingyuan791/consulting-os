from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any

# --- Phase 2: Intelligence Schemas ---

# 1. Financial Analysis
class FinancialRecord(BaseModel):
    year: int
    sales: float
    gross_profit: float
    operating_profit: float
    ordinary_profit: float
    net_income: float
    total_assets: float
    net_assets: float
    current_assets: float
    current_liabilities: float
    cash_and_equivalents: float
    interest_bearing_debt: float

class FinancialMetrics(BaseModel):
    year: int
    sales_growth: Optional[float]
    gross_profit_margin: float
    operating_profit_margin: float
    roa: float
    equity_ratio: float
    current_ratio: float
    debt_equity_ratio: float

class FinancialHealthSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: List[FinancialRecord]
    metrics: List[FinancialMetrics]
    overall_assessment: str = Field(description="Summary of financial health")

# 2. Market / Sales Analysis
class SalesRecord(BaseModel):
    year_month: str
    customer_name: str
    product_name: str
    amount: float
    quantity: Optional[float] = None

class MarketStructureSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pestle_analysis: Dict[str, str] = Field(description="Political, Economic, Social, Technological, Legal, Environmental")
    competitor_analysis: List[str] = Field(description="Key competitors")
    customer_segments: List[str] = Field(description="Main customer segments")
    market_trends: str = Field(description="Overall market direction")

# 3. Internal Capability
class CapabilityMatrixSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strengths: List[str]
    weaknesses: List[str]
    vrio_analysis: Dict[str, str] = Field(description="Value, Rarity, Imitability, Organization")
    core_competencies: str
