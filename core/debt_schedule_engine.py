from core.schemas.refinement_schema import AmortizationSchedule, AmortizationRow, FinancialModelAssumptions
from typing import List

def generate_amortization_schedule(
    assumptions: FinancialModelAssumptions,
    years_to_simulate: int = 3
) -> AmortizationSchedule:
    """
    Generate combined amortization schedule for Existing and New Debt.
    Returns year-by-year principal, interest, and balance.
    """
    rows = []
    
    # Existing Debt State
    # We assume 'existing_debt_balance' is the balance at start of Year 1.
    current_existing_balance = assumptions.existing_debt_balance
    existing_rate = assumptions.existing_debt_interest_rate
    existing_term = max(1, assumptions.existing_debt_remaining_years)
    
    # New Debt State
    current_new_balance = 0.0
    new_rate = assumptions.new_debt_interest_rate
    # Assume new debt is 7 year amortization or Interest Only? 
    # Let's assume 7 years linear principal for simplicity or "Equal Payment"?
    # Bank usually wants Equal Principal for corporate loans often, or Equal Payment.
    # Let's use Equal Principal for simplicity and safety (faster paydown).
    new_term_default = 7 
    
    total_interest_expense = 0.0
    
    for i in range(years_to_simulate):
        year_num = i + 1
        
        # --- Existing Debt ---
        # Equal Principal Amortization
        if current_existing_balance > 0:
            existing_principal_pay = min(current_existing_balance, assumptions.existing_debt_balance / existing_term)
            # Adjust if term is shorter than simulation? Yes, logical.
            # If term > 3, we pay 1/Term.
        else:
            existing_principal_pay = 0.0
            
        existing_interest = current_existing_balance * existing_rate
        
        # --- New Debt ---
        # Borrowing happens at BEGINNING or END? 
        # Usually Middle, so Interest is half-year? 
        # Let's assume Borrowing at Start of Year for simplicity of "Capital for Growth this year".
        
        new_borrowing = 0.0
        if i == 0: new_borrowing = assumptions.new_debt_borrowing_y1
        elif i == 1: new_borrowing = assumptions.new_debt_borrowing_y2
        elif i == 2: new_borrowing = assumptions.new_debt_borrowing_y3
        
        current_new_balance += new_borrowing
        
        # Amortization of New Debt
        # If we borrow Y1, do we start paying principal Y1? Usually grace period of 6mo-1yr.
        # Let's assume 1 year grace period for New Debt Principal.
        if i > 0 and current_new_balance > 0: 
            # Very simplified: 1/7th of cumulative balance? 
            # Complex if multiple tranches.
            # Let's approximate: 1/7th of balance.
            new_principal_pay = current_new_balance / new_term_default
        else:
            new_principal_pay = 0.0
            
        new_interest = current_new_balance * new_rate
        
        # --- Totals ---
        total_principal = existing_principal_pay + new_principal_pay
        total_interest = existing_interest + new_interest
        total_payment = total_principal + total_interest
        
        beginning = current_existing_balance + (current_new_balance - new_borrowing) # Before this year's actions? No.
        # Let's track Total Balance
        # Start Balance = (Existing End Prev) + (New End Prev)
        # We tracked them separately. 
        
        # Update Balances
        current_existing_balance -= existing_principal_pay
        current_new_balance -= new_principal_pay
        
        rows.append(AmortizationRow(
            year=year_num,
            beginning_balance=(current_existing_balance + existing_principal_pay) + (current_new_balance + new_principal_pay - new_borrowing), # Slightly messy calc check
            interest_payment=total_interest,
            principal_payment=total_principal,
            total_payment=total_payment,
            ending_balance=current_existing_balance + current_new_balance
        ))
        
        total_interest_expense += total_interest
        
    return AmortizationSchedule(
        rows=rows,
        total_interest=total_interest_expense
    )
