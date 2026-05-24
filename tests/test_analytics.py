import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.analytics_prediction import calculate_cagr, predict_future_performance
from core.analytics_financial import calculate_financial_metrics

class TestAnalytics(unittest.TestCase):
    
    def test_cagr(self):
        # 100 -> 121 over 2 years = 10%
        res = calculate_cagr(100, 121, 2)
        self.assertAlmostEqual(res, 0.1, places=2)
        
    def test_prediction_linear(self):
        # 2020: 100, 2021: 110, 2022: 120 -> 2023 should be 130
        data = {
            "year": [2020, 2021, 2022],
            "sales": [100.0, 110.0, 120.0],
            "gross_profit": [50.0, 55.0, 60.0],
            "operating_profit": [10.0, 11.0, 12.0],
            "net_income": [5.0, 6.0, 7.0]
        }
        df = pd.DataFrame(data)
        forecast = predict_future_performance(df, years_to_predict=1)
        
        self.assertEqual(len(forecast), 1)
        self.assertEqual(forecast.iloc[0]["year"], 2023)
        self.assertAlmostEqual(forecast.iloc[0]["sales"], 130.0, delta=0.1)

    def test_financial_metrics(self):
        # Basic check ensuring no division by zero crash
        data = {
            "year": [2020],
            "sales": [100],
            "gross_profit": [40],
            "operating_profit": [10],
            "ordinary_profit": [10],
            "net_income": [5],
            "total_assets": [200],
            "net_assets": [100],
            "current_assets": [50],
            "current_liabilities": [50],
            "cash_and_equivalents": [20],
            "interest_bearing_debt": [10]
        }
        df = pd.DataFrame(data)
        metrics = calculate_financial_metrics(df)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].gross_profit_margin, 0.4)

if __name__ == '__main__':
    unittest.main()
