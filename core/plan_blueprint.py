from typing import List, Dict, Optional
from pydantic import BaseModel

class PlanSection(BaseModel):
    title: str
    instruction_type: str = "narrative" # narrative, financial_table, list, strategy_card
    content_prompt: str # Prompt instruction for narrative, or Header for deterministic
    required_context: List[str] = [] 
    data_source: Optional[str] = None # Dot notation path in package, e.g. "financial_simulation"

class PlanChapter(BaseModel):
    title: str
    sections: List[PlanSection]

class PlanBlueprint:
    @staticmethod
    def get_standard_blueprint() -> List[PlanChapter]:
        return [
            PlanChapter(
                title="1. Executive Summary",
                sections=[
                    PlanSection(
                        title="1.1 Overview", 
                        instruction_type="narrative",
                        content_prompt="Summarize the company's current situation and the strategic plan at a high level.",
                        required_context=["company_summary", "issue_definition", "financial_health"]
                    ),
                    PlanSection(
                        title="1.2 Key Objectives", 
                        instruction_type="list",
                        content_prompt="Key Strategic Objectives",
                        data_source="execution_roadmap.objectives_placeholder" # We might need to derive this or use narrative if data missing
                    )
                ]
            ),
            PlanChapter(
                title="2. Internal Analysis",
                sections=[
                    PlanSection(
                        title="2.1 Financial Performance", 
                        instruction_type="financial_table",
                        content_prompt="Recent Financial Performance",
                        data_source="financial_health.metrics_history"
                    ),
                    PlanSection(
                        title="2.2 Operational Issues", 
                        instruction_type="narrative",
                        content_prompt="Discuss operational inefficiencies based on the diagnosis.", 
                        required_context=["kpi_tree", "internal_capability"]
                    )
                ]
            ),
            PlanChapter(
                title="3. External Environment",
                sections=[
                    PlanSection(
                        title="3.1 Market Trends", 
                        instruction_type="list",
                        content_prompt="Market Opportunities & Threats", 
                        data_source="external_intelligence" # Custom renderer for opportunities/threats
                    ),
                    PlanSection(
                        title="3.2 Competitor Landscape", 
                        instruction_type="narrative",
                        content_prompt="Analyze potential threats and competitive advantages.",
                        required_context=["market_summary"]
                    )
                ]
            ),
            PlanChapter(
                title="4. Strategic Initiatives",
                sections=[
                    PlanSection(
                        title="4.1 Core Strategy", 
                        instruction_type="strategy_card",
                        content_prompt="Selected Strategy Overview", 
                        data_source="selected_strategy"
                    ),
                    PlanSection(
                        title="4.2 Action Plan", 
                        instruction_type="roadmap_list",
                        content_prompt="Detailed Action Plan", 
                        data_source="execution_roadmap"
                    )
                ]
            ),
            PlanChapter(
                title="5. Financial Projections",
                sections=[
                    PlanSection(
                        title="5.1 Sales Forecast", 
                        instruction_type="narrative",
                        content_prompt="Project sales growth based on initiatives.",
                        required_context=["financial_simulation"]
                    ),
                    PlanSection(
                        title="5.2 Profit Plan (Simulation)", 
                        instruction_type="financial_table",
                        content_prompt="Projected P&L (3 Years)", 
                        data_source="financial_simulation"
                    )
                ]
            )
        ]
