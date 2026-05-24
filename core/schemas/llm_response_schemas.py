"""
LLM Response Schemas - OpenAI Structured Output互換の純粋なスキーマ定義。

StrategyModuleSchemaを継承するとmetaフィールド(default_factory)が
OpenAIのStructured Outputパーサーと互換性がないため、
LLMレスポンス用に別途定義する。

これらのスキーマは llm_client.py でのみ使用し、
結果をアプリケーション用スキーマにマッピングする。
"""
from pydantic import BaseModel, Field
from typing import List, Optional


# --- Strategy Options (for generate_strategy_options) ---

class LLMStrategyOption(BaseModel):
    id: str = Field(description="Unique ID for the option, e.g. 'opt-1'")
    name: str = Field(description="Short title of the strategy")
    description: str = Field(description="Detailed explanation of the strategy")
    rationale: str = Field(description="Why this solves the root cause")
    feasibility: str = Field(description="Low, Medium, High")
    impact: str = Field(description="Low, Medium, High")
    feasibility_score: int = Field(description="1-10 scale score")
    impact_score: int = Field(description="1-10 scale score")
    risk: str = Field(description="Key risks associated")
    time_horizon: str = Field(description="Short-term, Medium-term, Long-term")

class LLMStrategyOptionsResponse(BaseModel):
    selected_context_summary: str = Field(description="Summary of why these options were generated")
    options: List[LLMStrategyOption] = Field(description="List of strategy options")
    recommended_option_index: int = Field(default=0, description="Index of the recommended option")
    so_what_recommendation: str = Field(
        description=(
            "Single decisive recommendation: 2-3 sentences. "
            "Must name the recommended option, cite a specific metric, state why over the alternatives, "
            "and name the concrete first action. No hedging — use 断言形式."
        )
    )


# --- Internal Capability (for assess_internal_capabilities_llm) ---

class LLMCapabilityResponse(BaseModel):
    core_competencies: List[str] = Field(description="What the company does best (strengths)")
    resource_gaps: List[str] = Field(description="Missing resources preventing growth (weaknesses)")
    sustainable_advantages: List[str] = Field(default_factory=list, description="VRIO analysis results")
    process_maturity: str = Field(default="Developing", description="Ad-hoc, Developing, Defined, Managed, Optimized")


# --- External Intelligence (for analyze_external_environment_llm) ---

class LLMCompetitorInfo(BaseModel):
    name: str = Field(description="Competitor name")
    market_share: Optional[float] = Field(default=None, description="Estimated market share")
    strength: Optional[str] = Field(default=None, description="Key strength")
    weakness: Optional[str] = Field(default=None, description="Key weakness")

class LLMMarketStructureResponse(BaseModel):
    market_size_tam: Optional[float] = Field(default=None, description="Total Addressable Market size")
    market_growth_rate: Optional[float] = Field(default=None, description="Annual growth rate")
    competitors: List[LLMCompetitorInfo] = Field(default_factory=list, description="Competitor analysis")
    competitive_intensity: str = Field(default="Medium", description="Low, Medium, High")
    key_trends: List[str] = Field(default_factory=list, description="Major market trends")
    regulatory_risks: List[str] = Field(default_factory=list, description="Legal/compliance risks")
