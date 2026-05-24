import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.debt_schedule_engine import generate_amortization_schedule
from core.schemas.refinement_schema import (
    FinancialModelAssumptions, WorkingCapitalAssumptions, Provenance, ProvenanceType
)

class TestDebtSchedule(unittest.TestCase):
    
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
            tax_rate=0.3,
            working_capital=WorkingCapitalAssumptions(),
            # Debt
            existing_debt_balance=300.0,
            existing_debt_interest_rate=0.05, # 5%
            existing_debt_remaining_years=3,
            new_debt_interest_rate=0.04, # 4%
            new_debt_borrowing_y1=100.0,
            new_debt_borrowing_y2=0.0,
            new_debt_borrowing_y3=0.0,
            provenance=self.prov
        )

    def test_existing_amortization(self):
        """Test amortization of existing debt."""
        # 300 balance, 3 years. Equal Principal = 100/year.
        # Interest Y1 = 300 * 0.05 = 15.
        # Payment Y1 = 115.
        # End Balance Y1 = 200.
        
        schedule = generate_amortization_schedule(self.assumptions, years_to_simulate=3)
        rows = schedule.rows
        
        self.assertEqual(len(rows), 3)
        
        # Check Existing portion inference (Total Principal includes New)
        # New Debt: Borrow 100 Y1. Grace period?
        # My logic: "If i > 0... new_principal_pay = ...". 
        # So Y1 new principal pay is 0.
        
        # Y1 Total Principal = 100 (Existing) + 0 (New) = 100.
        # Y1 Interest = 15 (Existing) + (100 * 0.04) = 4. Total = 19.
        # Y1 Total Payment = 119.
        
        r1 = rows[0]
        self.assertAlmostEqual(r1.principal_payment, 100.0)
        self.assertAlmostEqual(r1.interest_payment, 19.0) # 300*0.05 + 100*0.04 = 15 + 4 = 19
        self.assertAlmostEqual(r1.total_payment, 119.0)
        
    def test_new_debt_amortization(self):
        """Test new debt amortization starting Y2."""
        # Y1: Borrow 100. Balance 100. Principal Pay 0.
        # Y2: 
        #   Existing Principal: 100.
        #   New Principal: 100 / 7 (default term) = 14.28...
        #   Total Principal: 114.28...
        
        schedule = generate_amortization_schedule(self.assumptions, years_to_simulate=3)
        r2 = schedule.rows[1]
        
        expected_new_princ = 100.0 / 7.0
        self.assertAlmostEqual(r2.principal_payment, 100.0 + expected_new_princ, delta=0.1)

if __name__ == '__main__':
    unittest.main()
