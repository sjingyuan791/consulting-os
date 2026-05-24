
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# 1. Setup Mocks BEFORE importing app
# Streamlit
mock_st = MagicMock()
sys.modules["streamlit"] = mock_st

# Core modules
mock_auth = MagicMock()
sys.modules["core.auth"] = mock_auth
sys.modules["core.style_utils"] = MagicMock()
sys.modules["core.sidebar"] = MagicMock()

# We also need to mock core.dashboard_widgets because app imports it
mock_widgets = MagicMock()
sys.modules["core.dashboard_widgets"] = mock_widgets

# 2. Import app
import app

class TestAppDashboard(unittest.TestCase):
    
    def setUp(self):
        # Reset mocks before each test
        mock_st.reset_mock()
        mock_auth.reset_mock()
        mock_widgets.reset_mock()
        
        # Setup session state
        mock_st.session_state = {
            "user": MagicMock(),
            "client_id": "test_client_id",
            "workspace_id": "test_ws_id"
        }
        
        # Helper to make st.columns return N mocks
        def columns_side_effect(n):
            if isinstance(n, int):
                return [MagicMock() for _ in range(n)]
            elif isinstance(n, list):
                return [MagicMock() for _ in range(len(n))]
            return [MagicMock(), MagicMock()] # Fallback
            
        mock_st.columns.side_effect = columns_side_effect

    def test_app_main_flow(self):
        """Smoke test for app.py main function"""
        
        # Setup Auth to True
        mock_auth.check_auth.return_value = True
        
        # Setup Data Mocks (Happy Path)
        mock_widgets.get_analysis_summary.return_value = {"score": 80, "summary": "Good status."}
        mock_widgets.get_swot_data.return_value = {
            "strengths": ["S1"], "weaknesses": ["W1"], 
            "opportunities": ["O1"], "threats": ["T1"]
        }
        mock_widgets.get_key_goals.return_value = ["Goal 1"]
        mock_widgets.get_financial_plan_summary.return_value = {
            "base_year": 2024, "target_year": 2027, 
            "revenue": 1000, "operating_profit": 200, 
            "revenue_cagr": 10.0, "profit_cagr": 12.0
        }
        mock_widgets.get_strategic_kpis.return_value = [
            {"name": "KPI1", "current_value": 100, "unit": "%", "targets": {"Y1": 110}}
        ]
        mock_widgets.check_critical_issues.return_value = [{"target_section": 1, "target_section_title": "Phil", "description": "Issue"}]
        
        # Run Main
        try:
            app.main()
        except Exception as e:
            self.fail(f"app.main() raised Exception: {e}")
        
        # Verify Key Streamlit Calls
        # Check columns call to Verify Layout (Financial Snapshot)
        # We expect at least one call to columns(2)
        mock_st.columns.assert_any_call(2) 
        
        # Verify Metric calls
        # Note: st.metric might be called on the return value of st.columns
        # mocking is tricky for return values of return values, but we can check if get_analysis_summary was called.
        mock_widgets.get_analysis_summary.assert_called_with("test_client_id")
        
        print("✅ app.py (Dashboard) Smoke Test Passed")

    def test_app_no_data(self):
        """Test with empty data"""
        mock_auth.check_auth.return_value = True
        
        # Return None for all
        mock_widgets.get_analysis_summary.return_value = None
        mock_widgets.get_swot_data.return_value = None
        mock_widgets.get_key_goals.return_value = []
        mock_widgets.get_financial_plan_summary.return_value = None
        mock_widgets.get_strategic_kpis.return_value = []
        mock_widgets.check_critical_issues.return_value = []
             
        try:
            app.main()
        except Exception as e:
            self.fail(f"app.main() raised Exception with empty data: {e}")
        
        print("✅ app.py (Empty Data) Smoke Test Passed")

if __name__ == "__main__":
    unittest.main()
