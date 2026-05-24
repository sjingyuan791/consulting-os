from typing import List, Dict, Any
from core.schemas.refinement_schema import SimulationYear, CashflowProjection, FinancialModelAssumptions

def calculate_cashflow(
    sim_years: List[SimulationYear], 
    assumptions: FinancialModelAssumptions,
    initial_cash: float,
    existing_debt_service: float = 0.0,
    debt_service_schedule: List[float] = None # List of Total Service per year
) -> List[CashflowProjection]:
    """
    Calculate 3-year cashflow projection based on P/L simulation and assumptions.
    """
    results = []
    current_cash = initial_cash

    for i, year_data in enumerate(sim_years):
        # 1. Operating Cash Flow (Indirect Method: Net Profit + D&A - Delta WC)
        
        # Calculate Working Capital
        # Receivables = Revenue * (Days / 365)
        wc_days = assumptions.working_capital
        receivables = year_data.revenue * (wc_days.payment_terms_days / 365.0)
        inventory = year_data.cogs * (wc_days.inventory_days / 365.0)
        # Payables? Schema didn't ask for Payables Days yet, but we should probably add or assume same as usage?
        # User prompt: "- payment_terms_days, - inventory_days, - prepaid_accrued_items"
        # Let's assume accounts_payable = 0 for now or assume inventory is financed? 
        # Standard: Payables = COGS * (Payables Days / 365). 
        # Missing field. Let's assume net against Receivables/Inventory or 0 constant.
        # User defined: prepaid_accrued_items_days. 
        # Prepaid = Opex * (Days/365)?
        prepaid = year_data.opex * (wc_days.prepaid_accrued_items_days / 365.0)
        
        current_wc = receivables + inventory + prepaid
        
        # Delta WC
        if i == 0:
            # First year delta from "initial" which we don't strictly have detailed breakdown of.
            # Assume previous WC was proportional to previous revenue?
            # Approximation: Delta WC = Current WC * GrowthRate / (1+GrowthRate)? 
            # Or just assume previous WC was 0 if startup?
            # Better: Previous WC = Current WC / (1+growth)
            prev_wc = current_wc / (1 + assumptions.revenue_growth_rate_y1)
            wc_change = current_wc - prev_wc
        else:
            wc_change = current_wc - prev_wc_balance
            
        prev_wc_balance = current_wc # Store for next loop
        
        # Depreciation (Back-calculated from EBITDA - OP)
        depreciation = year_data.ebitda - year_data.operating_profit
        
        # OCF
        operating_cf = year_data.net_profit + depreciation - wc_change
        
        # 2. Investment Cash Flow
        inv_amount = 0.0
        if i == 0: inv_amount = assumptions.investment_amount_y1
        elif i == 1: inv_amount = assumptions.investment_amount_y2
        elif i == 2: inv_amount = assumptions.investment_amount_y3
        
        investment_cf = -inv_amount
        
        # 3. Financing Cash Flow
        # Use existing_debt_service logic placeholder or integrate with Debt Schedule?
        # Ideally we receive 'debt_service' as input or calculate it.
        # Function signature has `existing_debt_service: float`.
        # Plus new debt borrowing/repayment?
        # Let's use the explicit borrowing assumptions if any.
        
        new_borrowing = 0.0
        if i == 0: new_borrowing = assumptions.new_debt_borrowing_y1
        elif i == 1: new_borrowing = assumptions.new_debt_borrowing_y2
        elif i == 2: new_borrowing = assumptions.new_debt_borrowing_y3
        
        # Debt Service Logic
        if debt_service_schedule and i < len(debt_service_schedule):
            total_debt_service = debt_service_schedule[i]
        else:
            # Fallback for compatibility or basic mode
            total_debt_service = existing_debt_service
            
        financing_cf = new_borrowing - total_debt_service
        
        # Net Change
        net_change = operating_cf + investment_cf + financing_cf
        current_cash += net_change
        
        results.append(CashflowProjection(
            operating_cf=operating_cf,
            investment_cf=investment_cf,
            financing_cf=financing_cf,
            ending_cash=current_cash,
            free_cash_flow=operating_cf + investment_cf
        ))
        
    return results
