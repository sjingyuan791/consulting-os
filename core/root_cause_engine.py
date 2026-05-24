import json
import logging
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from core.schemas.common import StrategyModuleSchema
from core.llm_client import client as openai_client
from core.llm_router import LLMRouter

logger = logging.getLogger(__name__)

# We use a recursive structure for the Issue Tree
class IssueNode(BaseModel):
    id: str
    label: str
    type: str = "issue" # issue, question, hypothesis
    children: List['IssueNode'] = []
    data: Optional[Dict[str, Any]] = {}

class IssueTreeSchema(StrategyModuleSchema):
    root_issue: str = Field(..., description="The primary strategic question (e.g., 'How to reverse profit decline?')")
    tree_structure: IssueNode = Field(..., description="The full hierarchical tree")
    
    # Analysis of the Situation
    primary_symptom: str
    likely_root_causes: List[str] = Field(default=[], description="Top 3 likely root causes identified")

async def build_issue_tree(
    financial_health: Any, # FinancialEngineOutput
    market_structure: Any, # MarketStructureSchema
    internal_capability: Any # CapabilityMatrixSchema
) -> IssueTreeSchema:
    """
    Synthesizes all analysis inputs to form a MECE Issue Tree using LLM.
    Returns an IssueTreeSchema object.
    """
    try:
        # 1. Prepare Data Context
        fin_ctx = json.dumps(financial_health, default=str, ensure_ascii=False) if financial_health else "データなし"
        mkt_ctx = json.dumps(market_structure, default=str, ensure_ascii=False) if market_structure else "データなし"
        int_ctx = json.dumps(internal_capability, default=str, ensure_ascii=False) if internal_capability else "データなし"

        # 2. Build Prompt
        system_prompt = """あなたは世界最高峰の戦略コンサルタントです。
提供された財務・市場・内部環境の分析データに基づき、企業の課題を解決するための「論点（イシュー）」を構造化してください。
論理的思考（ロジカルシンキング）を駆使し、MECE（漏れなくダブりなく）なロジックツリーを構築してください。

## 出力要件
- JSON形式で出力すること。
- `root_issue`: 最も上位の問い（例：「全社利益を最大化するには？」）
- `primary_symptom`: 解決すべき主要な症状（例：「営業利益率の低下」）
- `likely_root_causes`: データから推察される有力な根本原因トップ3
- `tree_structure`: 以下の構造を持つIssueNodeオブジェクト
  - id: 階層ID (例: "1", "1.1", "1.2")
  - label: 論点または仮説
  - children: 子ノードのリスト（再帰的構造）
"""

        user_prompt = f"""
## 分析データ入力

### 1. 財務健全性診断
{fin_ctx[:2000]}

### 2. 市場環境 (5 Forces / PEST)
{mkt_ctx[:2000]}

### 3. 内部リソース (VRIO)
{int_ctx[:2000]}

上記の状況に基づき、この企業が直面している本質的な課題を特定し、イシューツリーを作成してください。
"""

        # 3. Call LLM
        model = LLMRouter.route("analysis")
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=4096
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # 4. Parse & Validate
        return IssueTreeSchema(**data)

    except Exception as e:
        logger.error(f"Failed to build issue tree: {e}")
        # Fallback ensuring structure is valid
        return IssueTreeSchema(
            root_issue="分析エラーが発生しました",
            tree_structure=IssueNode(id="root", label="Error", children=[]),
            primary_symptom="Unknown",
            likely_root_causes=["System Error"]
        )

# Recursive model update for Pydantic
IssueNode.model_rebuild()

if __name__ == "__main__":
    import asyncio
    
    # Mock inputs
    fin_mock = {"overall_health_score": 35, "issues": ["Revenue Decline", "High Cost"]}
    mkt_mock = {"trends": ["Market Shrinking"]}
    int_mock = {"weaknesses": ["Legacy Systems"]}

    async def main():
        print("Generating Issue Tree...")
        tree = await build_issue_tree(fin_mock, mkt_mock, int_mock)
        print(tree.model_dump_json(indent=2))

    asyncio.run(main())
