from core.schemas.refinement_schema import CashflowProjection, DebtCapacity

def calculate_debt_capacity(
    cashflows: list[CashflowProjection],
    interest_rate: float = 0.03, # 3% default
    repayment_years: int = 7
) -> DebtCapacity:
    """
    Calculate Debt Service Coverage Ratio (DSCR) and Max Additional Debt.
    """
    if not cashflows:
        return DebtCapacity(
            dscr=0.0,
            max_additional_debt=0.0,
            safe_debt_level=0.0,
            interest_coverage_ratio=0.0
        )

    # Use Average Free Cash Flow (FCF) over 3 years as basis for capacity
    avg_fcf = sum(cf.free_cash_flow for cf in cashflows) / len(cashflows)
    
    # Existing Service (Assumed already subtracted in FCF? NO, FCF is Operating + Investing. Financing is separate.)
    # Financing CF includes existing debt service.
    # DSCR = (Operating CF) / (Total Debt Service)
    # But wait, FCF is usually available for debt service *new*.
    # Let's say DSCR on *existing* debt.
    
    # We need Total Debt Service amount. 
    # In `cashflow_engine`, we subtracted `financing_cf`. Let's assume financing_cf IS the service.
    # financing_cf is negative.
    
    avg_existing_service = abs(sum(cf.financing_cf for cf in cashflows) / len(cashflows))
    
    # Operating CF available for service
    avg_ocf = sum(cf.operating_cf for cf in cashflows) / len(cashflows)
    
    if avg_existing_service > 0:
        dscr = avg_ocf / avg_existing_service
    else:
        dscr = 99.9 # Infinite coverage if no debt
        
    # Max Additional Debt Capacity
    # Bank usually wants DSCR >= 1.2 *after* new debt.
    # Available for Service = Avg OCF / 1.2
    # Additional Service Capacity = (Available) - (Existing Service)
    
    required_dscr = 1.5 # Conservative
    max_service_capacity = avg_ocf / required_dscr
    additional_service_room = max(0, max_service_capacity - avg_existing_service)
    
    # Convert annual service room to principal amount (PMT formula simplified)
    # PMT = P * r / (1 - (1+r)^-n)
    # P = PMT * (1 - (1+r)^-n) / r
    if interest_rate > 0:
        factor = (1 - (1 + interest_rate) ** -repayment_years) / interest_rate
        max_additional_debt = additional_service_room * factor
    else:
        max_additional_debt = additional_service_room * repayment_years
        
    safe_debt_level = max_additional_debt * 0.8 # Buffer
    
    # Interest Coverage Ratio = Operating Income / Interest Expense
    # We don't have explicit interest expense here easily without parsing assumptions better.
    # Placeholder
    icr = 0.0
    
    return DebtCapacity(
        dscr=dscr,
        max_additional_debt=max_additional_debt,
        safe_debt_level=safe_debt_level,
        interest_coverage_ratio=icr
    )
