from typing import List, Optional
from pydantic import BaseModel, Field
from core.schemas.common import StrategyModuleSchema

class ResourceItem(BaseModel):
    name: str
    category: str # 'Human', 'Financial', 'Physical', 'Intellectual'
    quality: str = "Medium" # Low, Medium, High

class CapabilityMatrixSchema(StrategyModuleSchema):
    # Core Competencies (Strengths)
    core_competencies: List[str] = Field(default=[], description="What the company does best")
    
    # Weaknesses / Gaps
    resource_gaps: List[str] = Field(default=[], description="Missing resources preventing growth")
    
    # VRIO Analysis (Value, Rarity, Imitability, Organization)
    sustainable_advantages: List[str] = []
    
    # Operational Efficiency
    process_maturity: str = Field(default="Developing", description="Ad-hoc, Developing, Defined, Managed, Optimized")

def assess_internal_capabilities(
    financial_score: int = 50,
    sales_strengths: List[str] = [],
    resources: List[dict] = [],
    internal_documents: List[dict] = [] # Added for unstructured data
) -> CapabilityMatrixSchema:
    """
    Synthesizes financial health, sales performance, and internal documents into a capability assessment using LLM.
    """
    from core.llm_client import assess_internal_capabilities_llm
    
    try:
        # Prepare context
        doc_texts = []
        if isinstance(internal_documents, dict) and "content" in internal_documents:
             doc_texts.append(internal_documents["content"])
        elif isinstance(internal_documents, list):
            for d in internal_documents:
                if isinstance(d, dict) and "content" in d:
                    doc_texts.append(d["content"])
                else:
                     doc_texts.append(str(d))
        
        doc_context = "\n".join(doc_texts)[:10000] # Limit context size
        
        return assess_internal_capabilities_llm(
            financial_score=financial_score,
            sales_strengths=sales_strengths,
            resources=resources,
            doc_context=doc_context
        )
    except Exception as e:
        import logging
        logging.error(f"Internal capability LLM failed: {e}")
        # Fallback to Heuristic
        competencies = []
        gaps = []
        
        if financial_score > 70: competencies.append("財務基盤が強固")
        if financial_score < 40: gaps.append("財務安定性の欠如")
        if sales_strengths: competencies.extend([f"強力な販売チャネル: {s}" for s in sales_strengths])
        
        return CapabilityMatrixSchema(
            core_competencies=competencies,
            resource_gaps=gaps,
            process_maturity="Developing (Log Error)"
        )

if __name__ == "__main__":
    # Mock
    pass
