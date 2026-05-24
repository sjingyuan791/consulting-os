"""
Monthly Cash Flow Simulation Engine.
月次CFシミュレーション - 入金/支払サイト反映、季節変動対応

特徴:
1. 売上→入金変換（回収サイト反映）
2. 仕入→支払変換（支払サイト反映）
3. 季節変動係数設定
4. 月次CF計算表生成
5. 資金ショート警告機能
"""
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import math


# ==========================================
# 定数・設定
# ==========================================

# 季節変動パターン（業種別）
SEASONALITY_PATTERNS = {
    "製造業": [0.9, 0.9, 1.1, 1.0, 1.0, 1.0, 0.9, 0.8, 1.0, 1.1, 1.1, 1.2],
    "小売業": [1.3, 0.8, 0.9, 0.9, 0.9, 1.0, 1.1, 1.0, 0.9, 0.9, 1.0, 1.3],
    "建設業": [0.7, 0.8, 1.2, 1.1, 1.0, 1.0, 0.9, 0.9, 1.0, 1.1, 1.1, 1.2],
    "サービス業": [0.9, 0.9, 1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 1.0, 1.0, 1.0, 1.1],
    "飲食業": [0.9, 0.8, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.1, 1.2],
    "default": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
}


# ==========================================
# データモデル
# ==========================================

class CashFlowDrivers(BaseModel):
    """CFドライバー設定"""
    # 売上・入金
    annual_sales: float = Field(description="年間売上高（円）")
    collection_days: int = Field(default=30, ge=0, description="売掛金回収日数")
    cash_sales_ratio: float = Field(default=0.1, ge=0, le=1, description="現金売上比率")
    
    # 仕入・支払
    cogs_ratio: float = Field(default=0.6, ge=0, le=1, description="売上原価率")
    payment_days: int = Field(default=30, ge=0, description="買掛金支払日数")
    cash_purchase_ratio: float = Field(default=0.1, ge=0, le=1, description="現金仕入比率")
    
    # 固定費
    monthly_fixed_costs: float = Field(default=0, description="月間固定費（円）")
    monthly_personnel_costs: float = Field(default=0, description="月間人件費（円）")
    
    # 借入返済
    monthly_loan_repayment: float = Field(default=0, description="月間借入返済額（円）")
    
    # 季節変動
    industry: str = Field(default="default", description="業種")
    custom_seasonality: Optional[List[float]] = Field(default=None, description="カスタム季節変動")
    
    # 初期残高
    opening_cash: float = Field(default=0, description="期首現預金残高（円）")
    
    # 運転資本
    initial_receivables: float = Field(default=0, description="期首売掛金残高（円）")
    initial_payables: float = Field(default=0, description="期首買掛金残高（円）")


class MonthlyLoanPayment(BaseModel):
    """月別借入返済"""
    bank_name: str
    loan_type: str = ""  # 長期/短期
    principal: float = 0  # 元金返済
    interest: float = 0   # 利息支払
    balance_after: float = 0  # 返済後残高


class MonthlyCashFlow(BaseModel):
    """月次CF"""
    month: str  # YYYY-MM
    month_number: int  # 1-12
    
    # 売上・入金
    sales: float = 0
    cash_sales: float = 0
    collection_from_receivables: float = 0
    total_cash_inflow: float = 0
    
    # 仕入・支払
    cogs: float = 0
    cash_purchases: float = 0
    payment_of_payables: float = 0
    fixed_costs: float = 0
    personnel_costs: float = 0
    total_operating_outflow: float = 0
    
    # 借入返済
    loan_principal: float = 0
    loan_interest: float = 0
    total_financing_outflow: float = 0
    loan_details: List[MonthlyLoanPayment] = []
    
    # CF計算
    operating_cf: float = 0
    financing_cf: float = 0
    net_cf: float = 0
    
    # 残高
    opening_cash: float = 0
    closing_cash: float = 0
    
    # 売掛・買掛残高
    receivables_balance: float = 0
    payables_balance: float = 0
    
    # 警告
    is_negative: bool = False
    warning_message: str = ""


class CashFlowForecast(BaseModel):
    """CF予測結果"""
    start_month: str
    end_month: str
    months: List[MonthlyCashFlow]
    
    # サマリー
    total_inflow: float = 0
    total_outflow: float = 0
    net_cf_total: float = 0
    lowest_balance: float = 0
    lowest_balance_month: str = ""
    
    # 危険月
    negative_months: List[str] = []
    warning_count: int = 0
    
    # ドライバー
    drivers: CashFlowDrivers
    
    # 人間確認ポイント
    review_points: List[str] = []


# ==========================================
# 月次CFシミュレーションエンジン
# ==========================================

class MonthlyCashFlowEngine:
    """月次CFシミュレーションエンジン"""
    
    def __init__(self, drivers: CashFlowDrivers):
        self.drivers = drivers
        self.seasonality = self._get_seasonality()
    
    def _get_seasonality(self) -> List[float]:
        """季節変動係数を取得"""
        if self.drivers.custom_seasonality:
            return self.drivers.custom_seasonality
        return SEASONALITY_PATTERNS.get(
            self.drivers.industry, 
            SEASONALITY_PATTERNS["default"]
        )
    
    def simulate(
        self,
        start_year: int,
        start_month: int,
        num_months: int = 12,
        loan_schedule: Optional[List[Dict[str, Any]]] = None
    ) -> CashFlowForecast:
        """
        月次CFを予測。
        
        Args:
            start_year: 開始年
            start_month: 開始月
            num_months: 予測月数
            loan_schedule: 借入返済スケジュール
        """
        months: List[MonthlyCashFlow] = []
        
        # 初期残高
        current_cash = self.drivers.opening_cash
        receivables = self.drivers.initial_receivables
        payables = self.drivers.initial_payables
        
        # 月次売上（基準）
        monthly_base_sales = self.drivers.annual_sales / 12
        monthly_base_cogs = monthly_base_sales * self.drivers.cogs_ratio
        
        # 売掛金キュー（回収サイト用）
        receivables_queue = []  # [(amount, months_until_collection)]
        payables_queue = []     # [(amount, months_until_payment)]
        
        # 初期売掛金は1ヶ月後に入金と仮定
        if receivables > 0:
            months_to_collect = max(1, self.drivers.collection_days // 30)
            receivables_queue.append((receivables, months_to_collect))
        
        # 初期買掛金は1ヶ月後に支払と仮定
        if payables > 0:
            months_to_pay = max(1, self.drivers.payment_days // 30)
            payables_queue.append((payables, months_to_pay))
        
        for i in range(num_months):
            # 月を計算
            current_date = date(start_year, start_month, 1) + relativedelta(months=i)
            month_str = current_date.strftime("%Y-%m")
            month_num = current_date.month
            
            # 季節変動適用
            seasonality = self.seasonality[month_num - 1]
            monthly_sales = monthly_base_sales * seasonality
            monthly_cogs = monthly_sales * self.drivers.cogs_ratio
            
            # === 入金計算 ===
            cash_sales = monthly_sales * self.drivers.cash_sales_ratio
            credit_sales = monthly_sales * (1 - self.drivers.cash_sales_ratio)
            
            # 今月の売掛金をキューに追加
            months_to_collect = max(1, self.drivers.collection_days // 30)
            receivables_queue.append((credit_sales, months_to_collect))
            
            # キューから今月入金分を取得
            collection = 0
            new_receivables_queue = []
            for amount, months_left in receivables_queue:
                if months_left <= 1:
                    collection += amount
                else:
                    new_receivables_queue.append((amount, months_left - 1))
            receivables_queue = new_receivables_queue
            
            total_inflow = cash_sales + collection
            
            # 売掛金残高
            receivables_balance = sum(amt for amt, _ in receivables_queue)
            
            # === 支払計算 ===
            cash_purchases = monthly_cogs * self.drivers.cash_purchase_ratio
            credit_purchases = monthly_cogs * (1 - self.drivers.cash_purchase_ratio)
            
            # 今月の買掛金をキューに追加
            months_to_pay = max(1, self.drivers.payment_days // 30)
            payables_queue.append((credit_purchases, months_to_pay))
            
            # キューから今月支払分を取得
            payment = 0
            new_payables_queue = []
            for amount, months_left in payables_queue:
                if months_left <= 1:
                    payment += amount
                else:
                    new_payables_queue.append((amount, months_left - 1))
            payables_queue = new_payables_queue
            
            # 買掛金残高
            payables_balance = sum(amt for amt, _ in payables_queue)
            
            # 営業支出
            operating_outflow = (
                cash_purchases + 
                payment + 
                self.drivers.monthly_fixed_costs + 
                self.drivers.monthly_personnel_costs
            )
            
            # === 借入返済 ===
            loan_principal = 0
            loan_interest = 0
            loan_details = []
            
            if loan_schedule:
                for loan in loan_schedule:
                    # 銀行名と月次返済を取得
                    bank = loan.get("bank_name", "不明")
                    monthly_p = loan.get("monthly_principal", 0)
                    monthly_i = loan.get("monthly_interest", 0)
                    
                    loan_principal += monthly_p
                    loan_interest += monthly_i
                    
                    loan_details.append(MonthlyLoanPayment(
                        bank_name=bank,
                        loan_type=loan.get("loan_type", ""),
                        principal=monthly_p,
                        interest=monthly_i,
                    ))
            else:
                loan_principal = self.drivers.monthly_loan_repayment * 0.8  # 概算：元金80%
                loan_interest = self.drivers.monthly_loan_repayment * 0.2   # 概算：利息20%
            
            financing_outflow = loan_principal + loan_interest
            
            # === CF計算 ===
            operating_cf = total_inflow - operating_outflow
            financing_cf = -financing_outflow
            net_cf = operating_cf + financing_cf
            
            # === 残高計算 ===
            opening = current_cash
            closing = current_cash + net_cf
            current_cash = closing
            
            # 警告
            is_negative = closing < 0
            warning = ""
            if is_negative:
                warning = f"資金ショート: {abs(closing):,.0f}円不足"
            elif closing < monthly_base_sales * 0.5:
                warning = f"残高注意: 月商の50%未満"
            
            # 月次データ作成
            mcf = MonthlyCashFlow(
                month=month_str,
                month_number=month_num,
                sales=monthly_sales,
                cash_sales=cash_sales,
                collection_from_receivables=collection,
                total_cash_inflow=total_inflow,
                cogs=monthly_cogs,
                cash_purchases=cash_purchases,
                payment_of_payables=payment,
                fixed_costs=self.drivers.monthly_fixed_costs,
                personnel_costs=self.drivers.monthly_personnel_costs,
                total_operating_outflow=operating_outflow,
                loan_principal=loan_principal,
                loan_interest=loan_interest,
                total_financing_outflow=financing_outflow,
                loan_details=loan_details,
                operating_cf=operating_cf,
                financing_cf=financing_cf,
                net_cf=net_cf,
                opening_cash=opening,
                closing_cash=closing,
                receivables_balance=receivables_balance,
                payables_balance=payables_balance,
                is_negative=is_negative,
                warning_message=warning,
            )
            
            months.append(mcf)
        
        # サマリー
        total_inflow = sum(m.total_cash_inflow for m in months)
        total_outflow = sum(m.total_operating_outflow + m.total_financing_outflow for m in months)
        net_cf_total = sum(m.net_cf for m in months)
        
        # 最低残高月
        lowest_month = min(months, key=lambda m: m.closing_cash)
        
        # 危険月
        negative_months = [m.month for m in months if m.is_negative]
        warning_count = sum(1 for m in months if m.warning_message)
        
        # レビューポイント
        review_points = []
        if negative_months:
            review_points.append(f"⚠️ 資金ショートが予測されます: {', '.join(negative_months)}")
        if self.drivers.collection_days > 60:
            review_points.append("回収サイトが長い（60日超）。回収短縮の検討を推奨。")
        if self.drivers.payment_days < 30:
            review_points.append("支払サイトが短い（30日未満）。交渉余地の検討を推奨。")
        
        return CashFlowForecast(
            start_month=months[0].month,
            end_month=months[-1].month,
            months=months,
            total_inflow=total_inflow,
            total_outflow=total_outflow,
            net_cf_total=net_cf_total,
            lowest_balance=lowest_month.closing_cash,
            lowest_balance_month=lowest_month.month,
            negative_months=negative_months,
            warning_count=warning_count,
            drivers=self.drivers,
            review_points=review_points,
        )


# ==========================================
# ファサード関数
# ==========================================

def simulate_monthly_cashflow(
    annual_sales: float,
    cogs_ratio: float = 0.6,
    collection_days: int = 30,
    payment_days: int = 30,
    monthly_fixed_costs: float = 0,
    monthly_personnel_costs: float = 0,
    monthly_loan_repayment: float = 0,
    opening_cash: float = 0,
    industry: str = "default",
    start_year: int = 2024,
    start_month: int = 4,
    num_months: int = 12
) -> CashFlowForecast:
    """
    月次CFをシミュレーション。
    
    Example:
        >>> result = simulate_monthly_cashflow(
        ...     annual_sales=1_000_000_000,
        ...     collection_days=45,
        ...     payment_days=30,
        ...     monthly_fixed_costs=5_000_000,
        ...     opening_cash=20_000_000,
        ...     industry="製造業"
        ... )
    """
    drivers = CashFlowDrivers(
        annual_sales=annual_sales,
        cogs_ratio=cogs_ratio,
        collection_days=collection_days,
        payment_days=payment_days,
        monthly_fixed_costs=monthly_fixed_costs,
        monthly_personnel_costs=monthly_personnel_costs,
        monthly_loan_repayment=monthly_loan_repayment,
        opening_cash=opening_cash,
        industry=industry,
    )
    
    engine = MonthlyCashFlowEngine(drivers)
    return engine.simulate(start_year, start_month, num_months)


def format_cashflow_table(forecast: CashFlowForecast) -> str:
    """CFテーブルをテキスト形式で出力"""
    lines = [
        "=" * 80,
        "月次資金繰り予測表",
        "=" * 80,
        f"期間: {forecast.start_month} ～ {forecast.end_month}",
        f"業種: {forecast.drivers.industry}",
        f"回収サイト: {forecast.drivers.collection_days}日 / 支払サイト: {forecast.drivers.payment_days}日",
        "",
    ]
    
    # ヘッダー
    lines.append(f"{'月':<8} {'売上':>12} {'入金':>12} {'支出':>12} {'返済':>10} {'NetCF':>12} {'残高':>12} {'警告'}")
    lines.append("-" * 80)
    
    for m in forecast.months:
        warn = "⚠️" if m.warning_message else ""
        lines.append(
            f"{m.month:<8} "
            f"{m.sales:>12,.0f} "
            f"{m.total_cash_inflow:>12,.0f} "
            f"{m.total_operating_outflow:>12,.0f} "
            f"{m.total_financing_outflow:>10,.0f} "
            f"{m.net_cf:>12,.0f} "
            f"{m.closing_cash:>12,.0f} "
            f"{warn}"
        )
    
    lines.append("-" * 80)
    lines.append("")
    lines.append(f"【サマリー】")
    lines.append(f"  総入金: {forecast.total_inflow:,.0f}円")
    lines.append(f"  総支出: {forecast.total_outflow:,.0f}円")
    lines.append(f"  純CF: {forecast.net_cf_total:,.0f}円")
    lines.append(f"  最低残高: {forecast.lowest_balance:,.0f}円 ({forecast.lowest_balance_month})")
    
    if forecast.negative_months:
        lines.append("")
        lines.append(f"【⚠️ 資金ショート警告】")
        lines.append(f"  危険月: {', '.join(forecast.negative_months)}")
    
    if forecast.review_points:
        lines.append("")
        lines.append(f"【確認ポイント】")
        for rp in forecast.review_points:
            lines.append(f"  ・{rp}")
    
    lines.append("")
    lines.append("=" * 80)
    
    return "\n".join(lines)
