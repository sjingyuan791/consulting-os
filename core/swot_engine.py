from typing import List, Dict, Any
from core.schemas.intelligence import MarketStructureSchema, CapabilityMatrixSchema
from core.schemas.strategy import SWOTSchema, CrossSWOTSchema, StrategyOptionItem, CrossRef, IssueNode
import json

class SWOTEngine:
    def __init__(self):
        pass

    def generate_swot(
        self,
        market: MarketStructureSchema,
        capability: CapabilityMatrixSchema,
        issue_tree: IssueNode
    ) -> SWOTSchema:
        """
        Synthesizes SWOT from Market (O/T) and Capability (S/W) analysis, 
        enriched by the Issue Tree (Root Causes).
        """
        
        # 1. Strengths & Weaknesses (Internal)
        strengths = capability.strengths
        weaknesses = capability.weaknesses
        
        # 2. Opportunities & Threats (External)
        # Combine trends, competitor gaps (O), and competitor threats (T)
        opportunities = []
        threats = []
        
        # Parse PESTLE for O/T
        if market.pestle_analysis:
            for k, v in market.pestle_analysis.items():
                # Heuristic: Positive words -> Opportunity, Negative -> Threat
                # This is a simplification; in production, use LLM to classify.
                # For now, we list them generally or use a prompt if we had LLM access here.
                # We will append raw insights for now.
                pass

        # 3. Use Market Trends directly
        if market.market_trends:
            opportunities.append(f"Trend: {market.market_trends}")

        return SWOTSchema(
            strengths=strengths,
            weaknesses=weaknesses,
            opportunities=opportunities,
            threats=threats
        )

    def generate_cross_swot(
        self,
        swot: SWOTSchema,
        options: List[StrategyOptionItem]
    ) -> CrossSWOTSchema:
        """
        Maps existing Strategy Options to the Cross-SWOT Matrix (SO, WO, ST, WT).
        This does NOT generate new options, but categorizes existing ones.
        """
        
        so, wo, st, wt = [], [], [], []
        
        for opt in options:
            # Heuristic mapping based on Strategy Name / Description words.
            # In a real system, the Strategy Generation phase should explicitly tag the quadrant.
            # Or we use an LLM here to classify. 
            # For this MVP, we will use a simple keyword match or default to SO/WO based on type.
            
            desc = opt.description.lower() + opt.name.lower()
            ref = CrossRef(option_id=opt.id, rationale=opt.rationale)
            
            if "growth" in desc or "expand" in desc or "new" in desc:
                # Likely Opportunity-driven
                if "leverage" in desc or "existing" in desc:
                    so.append(ref) # Strength x Opportunity
                else:
                    wo.append(ref) # Weakness x Opportunity (Needs fix to capture)
            elif "cost" in desc or "efficiency" in desc:
                # Likely Weakness-driven (Fixing internal)
                wo.append(ref)
            elif "risk" in desc or "defend" in desc:
                st.append(ref) # Strength x Threat
            else:
                # Default fallback
                so.append(ref)

        return CrossSWOTSchema(
            so_strategies=so,
            wo_strategies=wo,
            st_strategies=st,
            wt_strategies=wt
        )

# Singleton or Service
def run_swot_analysis(
    market: MarketStructureSchema,
    capability: CapabilityMatrixSchema,
    issue_tree: IssueNode,
    options: List[StrategyOptionItem]
) -> Dict[str, Any]:
    
    engine = SWOTEngine()
    swot = engine.generate_swot(market, capability, issue_tree)
    cross = engine.generate_cross_swot(swot, options)
    
    return {
        "swot": swot,
        "cross_swot": cross
    }
