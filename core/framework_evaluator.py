"""
Framework Evaluator.
戦略フレームワークの動的評価エンジン。
"""
import json
import logging
from typing import Dict, Any, Optional

from core.llm_client import client as openai_client
from core.llm_router import LLMRouter
from core.strategy_frameworks import (
    FiveForces, PESTLEAnalysis, 
    ForceAssessment, PESTFactor, ThreatLevel
)

from core.prompts.framework_prompts import (
    PESTLE_ANALYSIS_SYSTEM_PROMPT, PESTLE_ANALYSIS_USER_PROMPT,
    FIVE_FORCES_SYSTEM_PROMPT, FIVE_FORCES_USER_PROMPT,
    EXTERNAL_CONSTRAINTS_SYSTEM_PROMPT, EXTERNAL_CONSTRAINTS_USER_PROMPT
)
from core.schemas.refinement_schema import ExternalConstraints

logger = logging.getLogger(__name__)

class FrameworkEvaluator:
    """LLMを用いたフレームワーク動的評価クラス"""

    async def evaluate_pestle(
        self, 
        target_market: str = "日本", 
        industry: str = "",
        custom_context: str = ""
    ) -> PESTLEAnalysis:
        """PESTLE分析を実行"""
        for attempt in range(3):
            try:
                model = LLMRouter.route("analysis")
                
                prompt = PESTLE_ANALYSIS_USER_PROMPT.format(
                    target_market=target_market,
                    industry=industry,
                    custom_context=f"\n## 追加コンテキスト\n{custom_context}" if custom_context else ""
                )
    
                response = openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": PESTLE_ANALYSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3, # 分析なので低めに設定
                    max_tokens=4096
                )
    
                result_json = json.loads(response.choices[0].message.content)
                
                # Parse into Pydantic Model
                pestle = PESTLEAnalysis(
                    target_market=target_market,
                    analysis_status="success"
                )
    
                # Map JSON fields to Schema
                for category in ["political", "economic", "social", "technological", "legal", "environmental"]:
                    items = result_json.get(category, [])
                    parsed_items = []
                    for item in items:
                        parsed_items.append(PESTFactor(
                            factor=item.get("factor", ""),
                            description=item.get("description", ""),
                            impact=item.get("impact", "medium"),
                            trend=item.get("trend", "stable"),
                            opportunity_or_threat=item.get("opportunity_or_threat", "neutral")
                        ))
                    setattr(pestle, category, parsed_items)
    
                # Extract key opportunities and threats
                all_factors = (
                    pestle.political + pestle.economic + pestle.social +
                    pestle.technological + pestle.legal + pestle.environmental
                )
                pestle.key_opportunities = [f.factor for f in all_factors if f.opportunity_or_threat == "opportunity"]
                pestle.key_threats = [f.factor for f in all_factors if f.opportunity_or_threat == "threat"]
                pestle.sources = ["AI Market Analysis (Powered by OpenAI)"]
    
                return pestle
    
            except Exception as e:
                logger.warning(f"PESTLE analysis failed (Attempt {attempt+1}/3): {e}")
                if attempt == 2:
                    # Final failure
                    return PESTLEAnalysis(
                        target_market=target_market,
                        analysis_status="failure",
                        error_message=str(e),
                        political=[PESTFactor(factor="Analysis Failed", description=str(e))] # Minimal valid data
                    )

    async def evaluate_five_forces(
        self, 
        industry: str,
        custom_context: str = ""
    ) -> FiveForces:
        """5 Forces分析を実行"""
        for attempt in range(3):
            try:
                model = LLMRouter.route("analysis")
                
                prompt = FIVE_FORCES_USER_PROMPT.format(
                    industry=industry,
                    custom_context=f"\n## 追加コンテキスト\n{custom_context}" if custom_context else ""
                )
    
                response = openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": FIVE_FORCES_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=4096
                )
    
                result_json = json.loads(response.choices[0].message.content)
    
                # Helper to create ForceAssessment
                def create_force(key: str) -> ForceAssessment:
                    data = result_json.get(key, {})
                    return ForceAssessment(
                        level=data.get("level", "medium"),
                        score=data.get("score", 3),
                        key_factors=data.get("key_factors", []),
                        implications=data.get("implications", "")
                    )
    
                five_forces = FiveForces(
                    industry=industry,
                    threat_of_new_entrants=create_force("threat_of_new_entrants"),
                    bargaining_power_of_suppliers=create_force("bargaining_power_of_suppliers"),
                    bargaining_power_of_buyers=create_force("bargaining_power_of_buyers"),
                    threat_of_substitutes=create_force("threat_of_substitutes"),
                    competitive_rivalry=create_force("competitive_rivalry"),
                    overall_attractiveness=result_json.get("overall_attractiveness", "medium"),
                    strategic_recommendations=result_json.get("strategic_recommendations", []),
                    sources=["AI Industry Analysis"],
                    analysis_status="success"
                )
                
                # Recalculate overall score to ensure consistency
                five_forces.calculate_overall()
    
                return five_forces
    
            except Exception as e:
                logger.warning(f"5 Forces analysis failed (Attempt {attempt+1}/3): {e}")
                if attempt == 2:
                     # Final failure
                    dummy_force = ForceAssessment(level=ThreatLevel.MEDIUM, score=3, key_factors=[f"Error: {str(e)}"])
                    return FiveForces(
                        industry=industry,
                        threat_of_new_entrants=dummy_force,
                        bargaining_power_of_suppliers=dummy_force,
                        bargaining_power_of_buyers=dummy_force,
                        threat_of_substitutes=dummy_force,
                        competitive_rivalry=dummy_force,
                        analysis_status="failure",
                        error_message=str(e)
                    )

    async def evaluate_external_constraints(
        self,
        pestle_data: PESTLEAnalysis,
        five_forces_data: FiveForces,
        custom_context: str = ""
    ) -> ExternalConstraints:
        """マクロ環境・競争環境から外部制約条件を抽出"""
        for attempt in range(3):
            try:
                model = LLMRouter.route("analysis")
                
                prompt = EXTERNAL_CONSTRAINTS_USER_PROMPT.format(
                    pestle_data=pestle_data.model_dump_json(indent=2),
                    five_forces_data=five_forces_data.model_dump_json(indent=2),
                    custom_context=f"\n## 追加コンテキスト\n{custom_context}" if custom_context else ""
                )
    
                response = openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": EXTERNAL_CONSTRAINTS_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2, # Deterministic requirement
                    max_tokens=2048
                )
    
                result_json = json.loads(response.choices[0].message.content)
                return ExternalConstraints(**result_json)
    
            except Exception as e:
                logger.warning(f"External constraints analysis failed (Attempt {attempt+1}/3): {e}")
                if attempt == 2:
                    # Fallback to default constraints if AI fails
                    return ExternalConstraints(
                        market_growth_rate=0.01,
                        competitive_density_index=0.5,
                        price_pressure_level="Medium",
                        cost_inflation_rate=0.02,
                        regulatory_risk_level="Medium"
                    )
