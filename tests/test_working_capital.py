import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.cashflow_engine import calculate_cashflow
from core.schemas.refinement_schema import (
    FinancialModelAssumptions, SimulationYear, WorkingCapitalAssumptions, Provenance, ProvenanceType
)

class TestWorkingCapital(unittest.TestCase):
    
    def setUp(self):
        self.prov = Provenance(source_tag=ProvenanceType.ASSUMPTION, source_detail="Test", confidence=1.0)
        
        self.assumptions = FinancialModelAssumptions(
            revenue_growth_rate_y1=0.1,
            revenue_growth_rate_y2=0.1,
            revenue_growth_rate_y3=0.1,
            gross_margin_rate=0.5,
            opex_growth_rate=0.05,
            investment_amount_y1=0,
            investment_amount_y2=0,
            investment_amount_y3=0,
            tax_rate=0.0, # Simplification
            working_capital=WorkingCapitalAssumptions(
                payment_terms_days=36.5, # 10% of year
                inventory_days=0,
                prepaid_accrued_items_days=0
            ),
            provenance=self.prov
        )
        
        # Create dummy simulation years
        self.sim_years = []
        rev = 1000
        for i in range(3):
            rev *= 1.1 # 1100, 1210, ...
            self.sim_years.append(SimulationYear(
                year=2025+i,
                revenue=rev,
                cogs=rev*0.5,
                gross_profit=rev*0.5,
                opex=0,
                ebitda=rev*0.5,
                operating_profit=rev*0.5,
                net_profit=rev*0.5, # Tax 0
                cash_flow=0
            ))

    def test_receivables_impact(self):
        """Test that Receivables reduces OCF."""
        # Receivables Days = 36.5 (10% of year)
        # Year 1 Revenue = 1100. Receivables = 110.
        # WC Change:
        # Prev WC (derived) = Current WC / (1+g) = 110 / 1.1 = 100.
        # Change = 110 - 100 = 10.
        # OCF = Net Profit (550) + Dep (0) - Change (10) = 540.
        
        cf = calculate_cashflow(self.sim_years, self.assumptions, initial_cash=1000)
        
        self.assertAlmostEqual(cf[0].operating_cf, 540.0, delta=1.0)
        
    def test_inventory_impact(self):
        """Test Inventory impact."""
        self.assumptions.working_capital.payment_terms_days = 0
        self.assumptions.working_capital.inventory_days = 73.0 # 20% of year
        # COGS = 50% of Rev.
        # Year 1: Rev 1100. COGS 550. Inventory = 550 * 0.2 = 110.
        # Prev WC = 110 / 1.1 = 100.
        # Change = 10.
        # OCF = 550 - 10 = 540.
        
        cf = calculate_cashflow(self.sim_years, self.assumptions, initial_cash=1000)
        self.assertAlmostEqual(cf[0].operating_cf, 540.0, delta=1.0)

if __name__ == '__main__':
    unittest.main()
