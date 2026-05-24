"""
外部環境分析の拡張スキーマ。
STEP 2 で生成される戦略的外部環境分析の出力型定義。
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class BusinessImpactItem(BaseModel):
    axis: str = ""
    description: str = ""
    direction: str = "positive"  # "positive" | "negative" | "mixed"
    magnitude: str = "medium"   # "high" | "medium" | "low"
    time_horizon: str = "medium_term"  # "short_term" | "medium_term" | "long_term"
    evidence: str = ""


class MacroSummary(BaseModel):
    tailwinds: List[str] = Field(default_factory=list)
    headwinds: List[str] = Field(default_factory=list)
    price_setting_structure: str = ""
    irreversible_conditions: List[str] = Field(default_factory=list)
    essence_of_environment: str = ""


class IndustryProfitDriver(BaseModel):
    driver: str = ""
    importance: str = "medium"  # "high" | "medium" | "low"
    description: str = ""


class IndustryProfitStructure(BaseModel):
    revenue_model: str = ""
    cost_structure_summary: str = ""
    key_profit_drivers: List[IndustryProfitDriver] = Field(default_factory=list)
    margin_benchmarks: str = ""
    value_chain_bottleneck: str = ""
    disruption_risk: str = ""


class EnhancedForceDetail(BaseModel):
    score: int = 3  # 1-5
    summary: str = ""
    key_players: List[str] = Field(default_factory=list)
    trend: str = ""  # "increasing" | "stable" | "decreasing"
    strategic_implication: str = ""


class EnhancedFiveForces(BaseModel):
    rivalry: EnhancedForceDetail = Field(default_factory=EnhancedForceDetail)
    new_entrants: EnhancedForceDetail = Field(default_factory=EnhancedForceDetail)
    substitutes: EnhancedForceDetail = Field(default_factory=EnhancedForceDetail)
    supplier: EnhancedForceDetail = Field(default_factory=EnhancedForceDetail)
    buyer: EnhancedForceDetail = Field(default_factory=EnhancedForceDetail)
    overall_attractiveness: str = "中"
    overall_comment: str = ""
    structural_insight: str = ""


class ExternalEnvAnalysis(BaseModel):
    business_impact: List[BusinessImpactItem] = Field(default_factory=list)
    macro_summary: MacroSummary = Field(default_factory=MacroSummary)
    industry_profit_structure: IndustryProfitStructure = Field(default_factory=IndustryProfitStructure)
    enhanced_five_forces: EnhancedFiveForces = Field(default_factory=EnhancedFiveForces)
    confidence_score: float = 0.8
