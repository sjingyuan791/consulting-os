"""
Loan Repayment Schedule & Restructuring Engine.
借入返済スケジュール・リスケシナリオ対応

特徴:
1. 既存借入条件登録
2. 元利返済計算（元金均等/元利均等）
3. リスケシナリオ（期間延長/据置/金利減免）
4. 返済可能額シミュレーション
5. 銀行別返済表出力
"""
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import date
from dateutil.relativedelta import relativedelta
import math


# ==========================================
# 定数・設定
# ==========================================

class RepaymentMethod(str, Enum):
    """返済方式"""
    EQUAL_PRINCIPAL = "equal_principal"  # 元金均等
    EQUAL_PAYMENT = "equal_payment"      # 元利均等
    BULLET = "bullet"                     # 一括返済
    INTEREST_ONLY = "interest_only"       # 利息のみ（据置）


class LoanType(str, Enum):
    """借入種別"""
    LONG_TERM = "long_term"           # 長期借入金
    SHORT_TERM = "short_term"         # 短期借入金
    REVOLVING = "revolving"           # 当座貸越
    EQUIPMENT = "equipment"           # 設備資金
    WORKING_CAPITAL = "working_capital"  # 運転資金
    GOVERNMENT = "government"         # 制度融資


class CollateralType(str, Enum):
    """担保種別"""
    UNSECURED = "unsecured"           # 無担保
    REAL_ESTATE = "real_estate"       # 不動産担保
    MACHINERY = "machinery"           # 機械担保
    INVENTORY = "inventory"           # 在庫担保
    RECEIVABLES = "receivables"       # 売掛金担保
    GUARANTEE = "guarantee"           # 保証協会保証


# ==========================================
# データモデル
# ==========================================

class LoanContract(BaseModel):
    """借入契約"""
    id: str
    bank_name: str
    loan_type: LoanType
    loan_name: str = ""
    
    # 契約条件
    original_amount: float = Field(description="当初借入額（円）")
    current_balance: float = Field(description="現在残高（円）")
    interest_rate: float = Field(ge=0, le=1, description="年利率 0.01=1%")
    
    # 返済条件
    repayment_method: RepaymentMethod = RepaymentMethod.EQUAL_PRINCIPAL
    repayment_start_date: str = Field(description="返済開始日 YYYY-MM")
    maturity_date: str = Field(description="最終返済日 YYYY-MM")
    monthly_payment: Optional[float] = Field(default=None, description="月次返済額（元利均等時）")
    
    # 担保・保証
    collateral_type: CollateralType = CollateralType.UNSECURED
    collateral_value: float = Field(default=0, description="担保評価額（円）")
    guarantor: str = Field(default="", description="保証人")
    guarantee_association: bool = Field(default=False, description="信用保証協会付")
    
    # 備考
    notes: str = ""


class MonthlyRepayment(BaseModel):
    """月次返済明細"""
    month: str  # YYYY-MM
    opening_balance: float
    principal: float
    interest: float
    total_payment: float
    closing_balance: float


class LoanRepaymentSchedule(BaseModel):
    """借入返済スケジュール"""
    loan_id: str
    bank_name: str
    loan_name: str
    loan_type: LoanType
    
    # 元条件
    original_amount: float
    interest_rate: float
    repayment_method: RepaymentMethod
    
    # スケジュール
    start_month: str
    end_month: str
    months: List[MonthlyRepayment]
    
    # サマリー
    total_principal: float = 0
    total_interest: float = 0
    total_payment: float = 0
    remaining_balance: float = 0


class RescheduleScenario(BaseModel):
    """リスケシナリオ"""
    scenario_name: str
    description: str = ""
    
    # 変更内容
    extension_months: int = Field(default=0, description="期間延長月数")
    grace_period_months: int = Field(default=0, description="据置期間月数")
    new_interest_rate: Optional[float] = Field(default=None, description="変更後金利")
    monthly_payment_cap: Optional[float] = Field(default=None, description="月次返済上限額")
    
    # 条件
    application_date: str = Field(default="", description="適用開始月 YYYY-MM")


class RescheduleResult(BaseModel):
    """リスケ結果"""
    loan_id: str
    original_schedule: LoanRepaymentSchedule
    new_schedule: LoanRepaymentSchedule
    scenario: RescheduleScenario
    
    # 比較
    monthly_payment_reduction: float = 0
    total_interest_increase: float = 0
    extension_months: int = 0
    
    # 評価
    feasibility: str = ""
    bank_negotiation_points: List[str] = []


class RepaymentCapacityAnalysis(BaseModel):
    """返済能力分析"""
    # 収益ベース
    operating_profit: float
    depreciation: float
    ebitda: float
    
    # 簡易CF
    simple_cf: float  # 当期純利益 + 減価償却
    
    # 返済能力
    annual_repayment_capacity: float
    monthly_repayment_capacity: float
    
    # 現在の返済負担
    annual_debt_service: float
    monthly_debt_service: float
    
    # 余力
    annual_surplus: float
    monthly_surplus: float
    
    # 返済年数
    debt_payback_years: float
    
    # 判定
    is_sustainable: bool
    assessment: str
    recommendations: List[str]


class AllLoansSchedule(BaseModel):
    """全借入スケジュール"""
    schedules: List[LoanRepaymentSchedule]
    
    # 合計
    total_current_balance: float = 0
    total_monthly_payment: float = 0
    total_annual_payment: float = 0
    
    # 銀行別
    by_bank: Dict[str, Dict[str, float]] = {}
    
    # 月別合計
    monthly_totals: Dict[str, Dict[str, float]] = {}


# ==========================================
# 返済スケジュール計算エンジン
# ==========================================

class LoanRepaymentEngine:
    """借入返済計算エンジン"""
    
    def calculate_schedule(
        self,
        loan: LoanContract,
        start_month: Optional[str] = None,
        months_to_calculate: int = 60
    ) -> LoanRepaymentSchedule:
        """
        返済スケジュールを計算。
        
        Args:
            loan: 借入契約
            start_month: 計算開始月（省略時は返済開始日）
            months_to_calculate: 計算月数
        """
        # 開始月
        if start_month:
            current_date = date.fromisoformat(start_month + "-01")
        else:
            current_date = date.fromisoformat(loan.repayment_start_date + "-01")
        
        # 終了月
        maturity = date.fromisoformat(loan.maturity_date + "-01")
        
        # 残存月数
        remaining_months = (maturity.year - current_date.year) * 12 + (maturity.month - current_date.month) + 1
        remaining_months = min(remaining_months, months_to_calculate)
        
        balance = loan.current_balance
        monthly_rate = loan.interest_rate / 12
        
        months: List[MonthlyRepayment] = []
        
        for i in range(remaining_months):
            month_date = current_date + relativedelta(months=i)
            month_str = month_date.strftime("%Y-%m")
            
            if balance <= 0:
                break
            
            opening = balance
            interest = balance * monthly_rate
            
            if loan.repayment_method == RepaymentMethod.EQUAL_PRINCIPAL:
                # 元金均等
                principal = loan.current_balance / remaining_months
                total = principal + interest
                
            elif loan.repayment_method == RepaymentMethod.EQUAL_PAYMENT:
                # 元利均等
                if loan.monthly_payment:
                    total = loan.monthly_payment
                else:
                    # PMT計算
                    if monthly_rate > 0:
                        total = balance * (monthly_rate * (1 + monthly_rate) ** remaining_months) / \
                                ((1 + monthly_rate) ** remaining_months - 1)
                    else:
                        total = balance / remaining_months
                principal = total - interest
                
            elif loan.repayment_method == RepaymentMethod.INTEREST_ONLY:
                # 利息のみ（据置）
                principal = 0
                total = interest
                
            elif loan.repayment_method == RepaymentMethod.BULLET:
                # 一括返済
                if i == remaining_months - 1:
                    principal = balance
                    total = principal + interest
                else:
                    principal = 0
                    total = interest
            else:
                principal = balance / remaining_months
                total = principal + interest
            
            # 最終月調整
            if principal > balance:
                principal = balance
                total = principal + interest
            
            closing = balance - principal
            balance = closing
            
            months.append(MonthlyRepayment(
                month=month_str,
                opening_balance=opening,
                principal=principal,
                interest=interest,
                total_payment=total,
                closing_balance=closing,
            ))
        
        # サマリー
        total_principal = sum(m.principal for m in months)
        total_interest = sum(m.interest for m in months)
        total_payment = sum(m.total_payment for m in months)
        
        return LoanRepaymentSchedule(
            loan_id=loan.id,
            bank_name=loan.bank_name,
            loan_name=loan.loan_name,
            loan_type=loan.loan_type,
            original_amount=loan.original_amount,
            interest_rate=loan.interest_rate,
            repayment_method=loan.repayment_method,
            start_month=months[0].month if months else "",
            end_month=months[-1].month if months else "",
            months=months,
            total_principal=total_principal,
            total_interest=total_interest,
            total_payment=total_payment,
            remaining_balance=months[-1].closing_balance if months else loan.current_balance,
        )
    
    def apply_reschedule(
        self,
        loan: LoanContract,
        scenario: RescheduleScenario
    ) -> RescheduleResult:
        """
        リスケシナリオを適用。
        """
        # 元スケジュール
        original = self.calculate_schedule(loan)
        
        # リスケ後の借入条件を作成
        new_loan = loan.model_copy()
        
        # 金利変更
        if scenario.new_interest_rate is not None:
            new_loan.interest_rate = scenario.new_interest_rate
        
        # 期間延長
        if scenario.extension_months > 0:
            orig_maturity = date.fromisoformat(loan.maturity_date + "-01")
            new_maturity = orig_maturity + relativedelta(months=scenario.extension_months)
            new_loan.maturity_date = new_maturity.strftime("%Y-%m")
        
        # 返済上限
        if scenario.monthly_payment_cap:
            new_loan.monthly_payment = scenario.monthly_payment_cap
            new_loan.repayment_method = RepaymentMethod.EQUAL_PAYMENT
        
        # 据置期間
        if scenario.grace_period_months > 0:
            # 据置期間中は利息のみ返済
            grace_loan = new_loan.model_copy()
            grace_loan.repayment_method = RepaymentMethod.INTEREST_ONLY
            grace_loan.maturity_date = (
                date.fromisoformat(scenario.application_date + "-01" if scenario.application_date else loan.repayment_start_date + "-01")
                + relativedelta(months=scenario.grace_period_months)
            ).strftime("%Y-%m")
            
            grace_schedule = self.calculate_schedule(grace_loan, scenario.application_date, scenario.grace_period_months)
            
            # 据置後は通常返済
            new_start = (date.fromisoformat(grace_schedule.end_month + "-01") + relativedelta(months=1)).strftime("%Y-%m")
        
        # 新スケジュール
        new_schedule = self.calculate_schedule(new_loan)
        
        # 比較
        orig_monthly = original.months[0].total_payment if original.months else 0
        new_monthly = new_schedule.months[0].total_payment if new_schedule.months else 0
        
        return RescheduleResult(
            loan_id=loan.id,
            original_schedule=original,
            new_schedule=new_schedule,
            scenario=scenario,
            monthly_payment_reduction=orig_monthly - new_monthly,
            total_interest_increase=new_schedule.total_interest - original.total_interest,
            extension_months=scenario.extension_months,
            feasibility="リスケ適用後、月次返済が軽減されます" if new_monthly < orig_monthly else "条件変更後も返済負担は変わりません",
            bank_negotiation_points=[
                f"月次返済額: {orig_monthly:,.0f}円 → {new_monthly:,.0f}円",
                f"総支払利息増加: {new_schedule.total_interest - original.total_interest:,.0f}円",
                "返済継続意思と経営改善計画の提示を推奨",
            ],
        )
    
    def analyze_repayment_capacity(
        self,
        operating_profit: float,
        depreciation: float,
        net_income: float,
        total_debt: float,
        annual_debt_service: float
    ) -> RepaymentCapacityAnalysis:
        """
        返済能力を分析。
        """
        ebitda = operating_profit + depreciation
        simple_cf = net_income + depreciation
        
        # 返済能力（簡易CF × 70%を返済可能額と仮定）
        annual_capacity = simple_cf * 0.7
        monthly_capacity = annual_capacity / 12
        
        # 余力
        annual_surplus = annual_capacity - annual_debt_service
        monthly_surplus = annual_surplus / 12
        
        # 返済年数
        payback_years = total_debt / simple_cf if simple_cf > 0 else 999
        
        # 判定
        is_sustainable = annual_surplus > 0 and payback_years < 10
        
        if annual_surplus > annual_debt_service * 0.3:
            assessment = "返済能力に余裕あり"
        elif annual_surplus > 0:
            assessment = "返済可能だが余裕なし"
        else:
            assessment = "返済能力不足 - リスケ検討要"
        
        # 推奨
        recommendations = []
        if payback_years > 10:
            recommendations.append(f"債務償還年数{payback_years:.1f}年 - 10年超のため融資困難")
        if annual_surplus < 0:
            shortage = abs(annual_surplus)
            recommendations.append(f"年間{shortage:,.0f}円の資金ショート - 収益改善またはリスケ必要")
        if ebitda < annual_debt_service:
            recommendations.append("EBITDAが返済額を下回っています - 抜本的な経営改善が必要")
        
        if not recommendations:
            recommendations.append("返済能力は健全です")
        
        return RepaymentCapacityAnalysis(
            operating_profit=operating_profit,
            depreciation=depreciation,
            ebitda=ebitda,
            simple_cf=simple_cf,
            annual_repayment_capacity=annual_capacity,
            monthly_repayment_capacity=monthly_capacity,
            annual_debt_service=annual_debt_service,
            monthly_debt_service=annual_debt_service / 12,
            annual_surplus=annual_surplus,
            monthly_surplus=monthly_surplus,
            debt_payback_years=payback_years,
            is_sustainable=is_sustainable,
            assessment=assessment,
            recommendations=recommendations,
        )


# ==========================================
# ファサード関数
# ==========================================

def calculate_loan_schedule(
    bank_name: str,
    current_balance: float,
    interest_rate: float,
    maturity_date: str,
    repayment_method: str = "equal_principal",
    start_month: Optional[str] = None
) -> LoanRepaymentSchedule:
    """
    借入返済スケジュールを計算。
    
    Example:
        >>> schedule = calculate_loan_schedule(
        ...     bank_name="〇〇銀行",
        ...     current_balance=50_000_000,
        ...     interest_rate=0.015,
        ...     maturity_date="2030-03",
        ...     start_month="2024-04"
        ... )
    """
    method = RepaymentMethod(repayment_method) if isinstance(repayment_method, str) else repayment_method
    
    loan = LoanContract(
        id="loan_1",
        bank_name=bank_name,
        loan_type=LoanType.LONG_TERM,
        original_amount=current_balance,
        current_balance=current_balance,
        interest_rate=interest_rate,
        repayment_method=method,
        repayment_start_date=start_month or date.today().strftime("%Y-%m"),
        maturity_date=maturity_date,
    )
    
    engine = LoanRepaymentEngine()
    return engine.calculate_schedule(loan, start_month)


def simulate_reschedule(
    bank_name: str,
    current_balance: float,
    interest_rate: float,
    maturity_date: str,
    extension_months: int = 0,
    grace_period_months: int = 0,
    new_interest_rate: Optional[float] = None
) -> RescheduleResult:
    """
    リスケシナリオをシミュレーション。
    """
    loan = LoanContract(
        id="loan_1",
        bank_name=bank_name,
        loan_type=LoanType.LONG_TERM,
        original_amount=current_balance,
        current_balance=current_balance,
        interest_rate=interest_rate,
        repayment_method=RepaymentMethod.EQUAL_PRINCIPAL,
        repayment_start_date=date.today().strftime("%Y-%m"),
        maturity_date=maturity_date,
    )
    
    scenario = RescheduleScenario(
        scenario_name="リスケシナリオ",
        extension_months=extension_months,
        grace_period_months=grace_period_months,
        new_interest_rate=new_interest_rate,
    )
    
    engine = LoanRepaymentEngine()
    return engine.apply_reschedule(loan, scenario)


def format_loan_schedule(schedule: LoanRepaymentSchedule) -> str:
    """返済スケジュールをテキスト形式で出力"""
    lines = [
        "=" * 70,
        f"借入返済スケジュール: {schedule.bank_name} - {schedule.loan_name or schedule.loan_type.value}",
        "=" * 70,
        f"借入残高: {schedule.original_amount:,.0f}円",
        f"金利: {schedule.interest_rate*100:.2f}%",
        f"返済方式: {schedule.repayment_method.value}",
        f"期間: {schedule.start_month} ～ {schedule.end_month}",
        "",
        f"{'月':<8} {'期首残高':>14} {'元金':>12} {'利息':>10} {'返済額':>12} {'期末残高':>14}",
        "-" * 70,
    ]
    
    for m in schedule.months[:24]:  # 最初の24ヶ月
        lines.append(
            f"{m.month:<8} "
            f"{m.opening_balance:>14,.0f} "
            f"{m.principal:>12,.0f} "
            f"{m.interest:>10,.0f} "
            f"{m.total_payment:>12,.0f} "
            f"{m.closing_balance:>14,.0f}"
        )
    
    if len(schedule.months) > 24:
        lines.append(f"... 以下 {len(schedule.months) - 24} ヶ月省略 ...")
    
    lines.append("-" * 70)
    lines.append(f"【合計】元金: {schedule.total_principal:,.0f}円 / 利息: {schedule.total_interest:,.0f}円 / 総返済: {schedule.total_payment:,.0f}円")
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)
