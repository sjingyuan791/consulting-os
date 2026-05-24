from typing import List, Optional
from pydantic import BaseModel, Field
from core.schemas.common import StrategyModuleSchema

class CompetitorInfo(BaseModel):
    name: str
    market_share: Optional[float] = None
    strength: Optional[str] = None
    weakness: Optional[str] = None

class MarketStructureSchema(StrategyModuleSchema):
    # Market Overview
    market_size_tam: Optional[float] = Field(default=None, description="Total Addressable Market size (Currency)")
    market_growth_rate: Optional[float] = Field(default=None, description="Annual growth rate (0.05 = 5%)")
    
    # Competitive Landscape
    competitors: List[CompetitorInfo] = []
    competitive_intensity: str = Field(default="Medium", description="Low, Medium, High")
    
    # PESTLE / Trends
    key_trends: List[str] = Field(default=[], description="Major market trends")
    regulatory_risks: List[str] = []

def analyze_external_environment(
    market_data_text: str = "",
    competitors_list: List[dict] = [],
    external_documents: List[dict] = [] # Added for unstructured data
) -> MarketStructureSchema:
    """
    Parses unstructured text, structured lists, and documents into a MarketStructureSchema using LLM.
    """
    from core.llm_client import analyze_external_environment_llm
    
    try:
        # Prepare Context
        doc_texts = [market_data_text] if market_data_text else []
        
        if isinstance(external_documents, dict) and "content" in external_documents:
             doc_texts.append(external_documents["content"])
        elif isinstance(external_documents, list):
            for d in external_documents:
                if isinstance(d, dict) and "content" in d:
                    doc_texts.append(d["content"])
                else:
                     doc_texts.append(str(d))
                     
        full_context = "\n---\n".join(doc_texts)[:15000] # Limit size

        return analyze_external_environment_llm(
            context_text=full_context,
            competitors_list=competitors_list
        )
        
    except Exception as e:
        import logging
        logging.error(f"External analysis LLM failed: {e}")
        
        # Fallback Logic
        comps = [CompetitorInfo(**c) for c in competitors_list]
        intensity = "高" if len(comps) > 5 else "中"
        if len(comps) < 2: intensity = "低"

        return MarketStructureSchema(
            competitors=comps,
            competitive_intensity=intensity,
            key_trends=["デジタルトランスフォーメーション (DX)"] if not market_data_text else [],
            market_size_tam=None,
            market_growth_rate=None
        )

if __name__ == "__main__":
    pass
