
import sys
import os
import unittest
# Mock the supabase client because we want to test the widget logic processing the response, 
# but getting real data is also fine if we have seeded data.
# The user wants "High Quality" so let's try to run against the real DB if possible, 
# or Mock if it's safer/faster.
# Given we seeded data, let's try to fetch REAL data if environment variables are set.
# However, usually tests in this environment are safer with mocks or isolated logic.
# Let's use Mocks for stability and speed, validating the parsing logic.

from unittest.mock import MagicMock, patch

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from core import dashboard_widgets

class TestDashboardWidgets(unittest.TestCase):
    
    @patch('core.supabase_client.get_supabase_client')
    def test_get_swot_data(self, mock_get_client):
        # Setup Mock Response
        mock_supabase = MagicMock()
        mock_get_client.return_value = mock_supabase
        
        # Simulate Section 6 Data
        mock_response = MagicMock()
        mock_response.data = [{
            "document_json": {
                "sections": [
                    {
                        "section_id": 6, 
                        "data": {
                            "strengths": ["S1", "S2"],
                            "weaknesses": ["W1"],
                            "opportunities": ["O1"],
                            "threats": ["T1"]
                        }
                    }
                ]
            }
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        # Execute
        result = dashboard_widgets.get_swot_data("test_client")
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(len(result["strengths"]), 2)
        self.assertEqual(result["strengths"][0], "S1")
        print("✅ get_swot_data passed")

    @patch('core.supabase_client.get_supabase_client')
    def test_get_key_goals(self, mock_get_client):
        mock_supabase = MagicMock()
        mock_get_client.return_value = mock_supabase
        
        # Simulate Section 2 Data
        mock_response = MagicMock()
        mock_response.data = [{
            "document_json": {
                "sections": [
                    {
                        "section_id": 2, 
                        "data": {
                            "quantitative_goals": ["Goal 1", "Goal 2"]
                        }
                    }
                ]
            }
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = dashboard_widgets.get_key_goals("test_client")
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "Goal 1")
        print("✅ get_key_goals passed")

    @patch('core.supabase_client.get_supabase_client')
    def test_get_financial_plan_summary(self, mock_get_client):
        mock_supabase = MagicMock()
        mock_get_client.return_value = mock_supabase
        
        # Simulate Section 13 Data
        mock_response = MagicMock()
        mock_response.data = [{
            "document_json": {
                "sections": [
                    {
                        "section_id": 13, 
                        "data": {
                            "base_year": 2024,
                            "revenue_cagr": 10.5,
                            "profit_cagr": 5.2,
                            "projections": [
                                {"year": 2025, "revenue": 100, "operating_profit": 10},
                                {"year": 2027, "revenue": 150, "operating_profit": 20} # Target year
                            ]
                        }
                    }
                ]
            }
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = dashboard_widgets.get_financial_plan_summary("test_client")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["target_year"], 2027)
        self.assertEqual(result["revenue"], 150)
        self.assertEqual(result["revenue_cagr"], 10.5)
        print("✅ get_financial_plan_summary passed")

    @patch('core.supabase_client.get_supabase_client')
    def test_check_critical_issues(self, mock_get_client):
        mock_supabase = MagicMock()
        mock_get_client.return_value = mock_supabase
        
        mock_response = MagicMock()
        mock_response.data = [{
            "quality_check_json": {
                "critical_issues": [
                    {"description": "Critical Issue 1"}
                ]
            }
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = dashboard_widgets.check_critical_issues("test_client")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["description"], "Critical Issue 1")
        print("✅ check_critical_issues passed")

if __name__ == "__main__":
    unittest.main()
