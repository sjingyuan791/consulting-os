import pandas as pd
from typing import List, Optional
from pydantic import BaseModel, Field
from core.schemas.common import StrategyModuleSchema

# Re-use the existing basic metrics if available, or define a richer schema here.
# For the Strategy Formulation Engine, we need a robust schema.

class FinancialHealthCheck(BaseModel):
    """
    Represents a single year's health check or an aggregated view.
    財務ヘルスチェック（基本指標＋銀行指標）
    """
    year: int
    revenue: float
    gross_profit: float
    operating_profit: float
    ordinary_profit: float
    net_income: float
    
    # Advanced Metrics
    simplified_cf: Optional[float] = Field(default=None, description="簡易CF (当期純利益+減価償却費-年間返済額)")
    break_even_sales: Optional[float] = Field(default=None, description="損益分岐点売上高")
    break_even_ratio: Optional[float] = Field(default=None, description="損益分岐点比率")
    labor_productivity: Optional[float] = Field(default=None, description="労働生産性 (売上総利益/従業員数)")
    labor_share: Optional[float] = Field(default=None, description="労働分配率 (人件費/売上総利益)")
    
    # Ratios - 収益性
    gross_margin: float = Field(description="Gross Profit / Revenue")
    operating_margin: float = Field(description="Operating Profit / Revenue")
    ordinary_profit_margin: Optional[float] = Field(default=None, description="経常利益率 (Ordinary Profit / Revenue)")
    net_margin: float = Field(description="Net Income / Revenue")
    
    # Efficiency - 効率性
    roa: Optional[float] = Field(default=None, description="Return on Assets")
    roe: Optional[float] = Field(default=None, description="Return on Equity")
    total_asset_turnover: Optional[float] = Field(default=None, description="総資本回転率 (回) (売上高/総資産)")
    receivables_turnover_months: Optional[float] = Field(default=None, description="売上債権回転期間 (月)")
    inventory_turnover_months: Optional[float] = Field(default=None, description="棚卸資産回転期間 (月)")
    payables_turnover_months: Optional[float] = Field(default=None, description="買入債務回転期間 (月)")
    
    # Stability - 安全性
    equity_ratio: Optional[float] = Field(default=None, description="Equity / Total Assets")
    current_ratio: Optional[float] = Field(default=None, description="Current Assets / Current Liabilities")
    fixed_ratio: Optional[float] = Field(default=None, description="固定比率 (固定資産/純資産)")
    debt_monthly_sales_ratio: Optional[float] = Field(default=None, description="借入金月商倍率 (有利子負債 / 月商)")
    
    # Bank Metrics - 銀行格付け用指標
    quick_ratio: Optional[float] = Field(default=None, description="当座比率 (現預金+売掛金)/流動負債")
    fixed_long_term_ratio: Optional[float] = Field(default=None, description="固定長期適合率 固定資産/(純資産+固定負債)")
    interest_coverage: Optional[float] = Field(default=None, description="インタレストカバレッジ 営業利益/支払利息")
    debt_equity_ratio: Optional[float] = Field(default=None, description="D/Eレシオ 有利子負債/純資産")
    
    # Growth (vs prev year)
    revenue_growth: Optional[float] = None
    operating_profit_growth: Optional[float] = None

class FinancialEngineOutput(StrategyModuleSchema):
    metrics_history: List[FinancialHealthCheck]
    average_revenue_growth_3y: Optional[float] = None
    average_operating_margin_3y: Optional[float] = None
    overall_health_score: Optional[int] = Field(default=None, description="0-100 score based on benchmarks")

def run_financial_engine(df: pd.DataFrame) -> FinancialEngineOutput:
    """
    Processes the standardized financial dataframe and returns a structured health assessment.
    """
    if df.empty:
        return FinancialEngineOutput(metrics_history=[])

    # Ensure sorting
    if 'year' in df.columns:
        df = df.sort_values('year')
        
    metrics_list = []
    
    # Pre-calc growth
    df['revenue_growth'] = df['sales'].pct_change().fillna(0) if 'sales' in df.columns else 0
    df['op_growth'] = df['operating_profit'].pct_change().fillna(0) if 'operating_profit' in df.columns else 0

    for i, row in df.iterrows():
        sales = row.get('sales', 0) or 0
        gp = row.get('gross_profit', 0) or 0
        op = row.get('operating_profit', 0) or 0
        ord_p = row.get('ordinary_profit', 0) or 0
        ni = row.get('net_income', 0) or 0
        cogs = row.get('cost_of_goods_sold', 0) or 0
        sga = row.get('sga_expense', 0) or 0
        
        # --- gross_profit フォールバック計算 ---
        if gp == 0 and sales > 0:
            if cogs > 0:
                gp = sales - cogs
            elif op != 0 and sga > 0:
                gp = op + sga
        
        assets = row.get('total_assets', 0) or 0
        equity = row.get('net_assets', 0) or 0
        curr_assets = row.get('current_assets', 0) or 0
        curr_liab = row.get('current_liabilities', 0) or 0
        
        # 銀行指標用データ
        cash = row.get('cash_and_equivalents', row.get('cash', row.get('現預金', 0))) or 0
        receivables = row.get('receivables', row.get('売掛金', 0)) or 0
        inventory = row.get('inventory', row.get('棚卸資産', 0)) or 0
        payables = row.get('payables', row.get('買掛金', 0)) or 0
        
        fixed_assets = row.get('fixed_assets', row.get('固定資産', 0)) or 0
        long_term_debt = row.get('long_term_debt', row.get('長期借入金', 0)) or 0
        interest_expense = row.get('interest_expense', row.get('支払利息', 0)) or 0
        total_debt = row.get('interest_bearing_debt', row.get('有利子負債合計', 0)) or 0
        
        # New Inputs for Advanced Metrics
        depreciation = row.get('depreciation', row.get('減価償却費', 0)) or 0
        repayment = row.get('annual_repayment', row.get('年間返済額', 0)) or 0
        employee_count = row.get('employee_count', row.get('従業員数', 0)) or 0
        personnel_cost = row.get('personnel_cost', row.get('人件費', 0)) or 0
        
        # 1. Simplified CF
        simplified_cf = ni + depreciation - repayment
        
        # 2. Break-even Analysis (Simplified)
        fixed_cost = (gp - op) + interest_expense
        marginal_profit_ratio = (gp / sales) if sales > 0 else 0
        
        break_even_sales = None
        break_even_ratio = None
        if marginal_profit_ratio > 0:
            break_even_sales = fixed_cost / marginal_profit_ratio
            if sales > 0:
                break_even_ratio = break_even_sales / sales

        # 3. Productivity
        labor_productivity = (gp / employee_count) if employee_count > 0 else None
        labor_share = (personnel_cost / gp) if gp > 0 else None

        # Avoid division by zero
        safe_div = lambda n, d: n / d if d and d != 0 else None
        
        # 4. Efficiency Metrics
        avg_monthly_sales = sales / 12 if sales > 0 else 0
        receivables_turnover_months = safe_div(receivables, avg_monthly_sales)
        inventory_turnover_months = safe_div(inventory, avg_monthly_sales)
        payables_turnover_months = safe_div(payables, avg_monthly_sales)
        total_asset_turnover = safe_div(sales, assets)
        
        # 5. Safety Metrics
        fixed_ratio = safe_div(fixed_assets, equity)
        debt_monthly_sales_ratio = safe_div(total_debt, avg_monthly_sales)

        m = FinancialHealthCheck(
            year=int(row.get('year', 0)),
            revenue=sales,
            gross_profit=gp,
            operating_profit=op,
            ordinary_profit=ord_p,
            net_income=ni,
            
            # Advanced Metrics
            simplified_cf=simplified_cf,
            break_even_sales=break_even_sales,
            break_even_ratio=break_even_ratio,
            labor_productivity=labor_productivity,
            labor_share=labor_share,

            # 収益性
            gross_margin=safe_div(gp, sales) or 0,
            operating_margin=safe_div(op, sales) or 0,
            ordinary_profit_margin=safe_div(ord_p, sales),
            net_margin=safe_div(ni, sales) or 0,
            
            # 効率性
            roa=safe_div(ni, assets),
            roe=safe_div(ni, equity),
            total_asset_turnover=total_asset_turnover,
            receivables_turnover_months=receivables_turnover_months,
            inventory_turnover_months=inventory_turnover_months,
            payables_turnover_months=payables_turnover_months,
            
            # 安全性
            equity_ratio=safe_div(equity, assets),
            current_ratio=safe_div(curr_assets, curr_liab),
            fixed_ratio=fixed_ratio,
            debt_monthly_sales_ratio=debt_monthly_sales_ratio,
            
            # 銀行指標
            quick_ratio=safe_div(cash + receivables, curr_liab),
            fixed_long_term_ratio=safe_div(fixed_assets, equity + long_term_debt) if (equity + long_term_debt) > 0 else None,
            interest_coverage=safe_div(op, interest_expense) if interest_expense > 0 else None,
            debt_equity_ratio=safe_div(total_debt, equity),
            
            # 成長性
            revenue_growth=row.get('revenue_growth', 0),
            operating_profit_growth=row.get('op_growth', 0)
        )
        metrics_list.append(m)
        
    # Calculate 3y Averages if enough data
    avg_growth = None
    avg_margin = None
    
    if len(metrics_list) >= 3:
        recent = metrics_list[-3:]
        avg_growth = sum([m.revenue_growth for m in recent if m.revenue_growth is not None]) / 3
        avg_margin = sum([m.operating_margin for m in recent]) / 3
        
    # Comprehensive Scoring Logic with penalty for bad metrics
    score = 50
    rules_fired = []
    
    # --- Growth Scoring ---
    if avg_growth is not None:
        if avg_growth > 0.10:
            score += 15
            rules_fired.append("高成長（年率10%以上）")
        elif avg_growth > 0.05:
            score += 10
            rules_fired.append("成長基調（年率5%以上）")
        elif avg_growth > 0.0:
            score += 5
        elif avg_growth > -0.05:
            score -= 10
            rules_fired.append("⚠️ 売上微減傾向（年率0〜-5%）")
        elif avg_growth > -0.10:
            score -= 15
            rules_fired.append("🔴 売上減少（年率-5〜-10%）")
        else:
            score -= 20
            rules_fired.append("🔴 売上大幅減少（年率-10%以下）")
    
    # --- Profitability Scoring ---
    if avg_margin is not None:
        if avg_margin > 0.10:
            score += 15
            rules_fired.append("高利益率（営業利益率10%以上）")
        elif avg_margin > 0.05:
            score += 10
        elif avg_margin > 0.0:
            score += 0  # Neutral
        elif avg_margin > -0.05:
            score -= 10
            rules_fired.append("⚠️ 営業赤字傾向")
        elif avg_margin > -0.15:
            score -= 15
            rules_fired.append("🔴 営業赤字（利益率-5〜-15%）")
        else:
            score -= 25
            rules_fired.append("🔴 深刻な営業赤字（利益率-15%以下）")
    
    # --- Balance Sheet Health ---
    if metrics_list:
        latest = metrics_list[-1]
        if latest.equity_ratio is not None:
            if latest.equity_ratio > 0.5:
                score += 10
                rules_fired.append("自己資本比率健全（50%以上）")
            elif latest.equity_ratio > 0.3:
                score += 5
            elif latest.equity_ratio > 0.1:
                score -= 5
                rules_fired.append("⚠️ 自己資本比率低水準（10〜30%）")
            else:
                score -= 15
                rules_fired.append("🔴 債務超過リスク（自己資本比率10%未満）")
        
        # Current Ratio
        if latest.current_ratio is not None:
            if latest.current_ratio < 1.0:
                score -= 10
                rules_fired.append("🔴 流動比率100%未満（短期支払能力に懸念）")
            elif latest.current_ratio < 1.2:
                score -= 5
                rules_fired.append("⚠️ 流動比率低水準（100〜120%）")
    
    # Clamp score between 0-100
    score = max(0, min(100, score))
    
    output = FinancialEngineOutput(
        metrics_history=metrics_list,
        average_revenue_growth_3y=avg_growth,
        average_operating_margin_3y=avg_margin,
        overall_health_score=score
    )
    
    # Populate meta.rules_fired for UI display
    output.meta.rules_fired = rules_fired
    
    return output
