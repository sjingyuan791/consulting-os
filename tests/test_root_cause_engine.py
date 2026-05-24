import pytest
import asyncio
from unittest.mock import MagicMock, patch
from core.root_cause_engine import build_issue_tree, IssueTreeSchema

@pytest.mark.asyncio
def test_build_issue_tree_structure():
    """Verify build_issue_tree returns valid schema structure using mock LLM"""
    
    async def _run_test():
        # Mock inputs
        fin_mock = {"overall_health_score": 35, "issues": ["Revenue Decline"]}
        mkt_mock = {"trends": ["Market Shrinking"]}
        int_mock = {"weaknesses": ["Legacy Systems"]}

        # Mock OpenAI client response
        mock_json = """
        {
            "root_issue": "How to reverse revenue decline?",
            "primary_symptom": "Decreasing Sales",
            "likely_root_causes": ["Product Obsolescence", "Inefficient Sales"],
            "tree_structure": {
                "id": "root",
                "label": "How to reverse revenue decline?",
                "children": [
                    {
                        "id": "1", 
                        "label": "Increase Sales Volume", 
                        "children": []
                    },
                    {
                        "id": "2", 
                        "label": "Increase Unit Price", 
                        "children": []
                    }
                ]
            }
        }
        """

        with patch("core.root_cause_engine.openai_client") as mock_openai:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = mock_json
            mock_openai.chat.completions.create.return_value = mock_response

            # Execute
            result = await build_issue_tree(fin_mock, mkt_mock, int_mock)

            # Assertions
            assert isinstance(result, IssueTreeSchema)
            assert result.root_issue == "How to reverse revenue decline?"
            assert result.primary_symptom == "Decreasing Sales"
            assert len(result.likely_root_causes) == 2
            assert result.tree_structure.id == "root"
            assert len(result.tree_structure.children) == 2

    asyncio.run(_run_test())
