import pytest
import asyncio
from unittest.mock import MagicMock, patch
from core.framework_evaluator import FrameworkEvaluator
from core.strategy_frameworks import FiveForces, PESTLEAnalysis

@pytest.mark.asyncio
def test_evaluate_five_forces_success():
    """Verify successful 5 Forces analysis"""
    async def _run():
        evaluator = FrameworkEvaluator()
        # Mock response needs to match structure expected by create_force helper
        # result_json.get(key, {}) -> so we need "threat_of_new_entrants": {...}
        custom_response = """
        {
            "threat_of_new_entrants": {"level": "high", "score": 4, "key_factors": ["Factor1"]},
            "bargaining_power_of_suppliers": {"level": "medium", "score": 3},
            "bargaining_power_of_buyers": {"level": "medium", "score": 3},
            "threat_of_substitutes": {"level": "medium", "score": 3},
            "competitive_rivalry": {"level": "medium", "score": 3},
            "overall_attractiveness": "low",
            "strategic_recommendations": ["Test Rec"]
        }
        """
        
        with patch("core.framework_evaluator.openai_client") as mock_openai:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = custom_response
            mock_openai.chat.completions.create.return_value = mock_response

            result = await evaluator.evaluate_five_forces(industry="Test Industry")
            
            assert result.analysis_status == "success"
            assert result.industry == "Test Industry"
            assert result.threat_of_new_entrants.score == 4
    
    asyncio.run(_run())

@pytest.mark.asyncio
def test_evaluate_five_forces_failure_retry():
    """Verify 5 Forces analysis retries on failure and returns failure status eventually"""
    async def _run():
        evaluator = FrameworkEvaluator()
        
        with patch("core.framework_evaluator.openai_client") as mock_openai:
            # Simulate exception
            mock_openai.chat.completions.create.side_effect = Exception("API Error")

            result = await evaluator.evaluate_five_forces(industry="Test Industry")
            
            assert mock_openai.chat.completions.create.call_count == 3
            assert result.analysis_status == "failure"
            assert "API Error" in result.error_message
            # Check if dummy data is populated correctly
            assert result.threat_of_new_entrants.key_factors[0].startswith("Error:")
    
    asyncio.run(_run())

@pytest.mark.asyncio
def test_evaluate_pestle_failure():
    """Verify PESTLE analysis handles failure"""
    async def _run():
        evaluator = FrameworkEvaluator()
        
        with patch("core.framework_evaluator.openai_client") as mock_openai:
            mock_openai.chat.completions.create.side_effect = Exception("PESTLE Error")

            result = await evaluator.evaluate_pestle(target_market="Japan")
            
            assert result.analysis_status == "failure"
            assert "PESTLE Error" in result.error_message
            
    asyncio.run(_run())
