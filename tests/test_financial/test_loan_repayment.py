"""
Test Loan Repayment Engine.
借入返済エンジンのテスト
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.loan_repayment_engine import (
    LoanContract, LoanType, RepaymentMethod, CollateralType,
    LoanRepaymentEngine, LoanRepaymentSchedule,
    RescheduleScenario, RepaymentCapacityAnalysis
)


class TestLoanContract:
    """LoanContract モデルのテスト"""
    
    def test_loan_creation(self):
        """借入データの作成"""
        loan = LoanContract(
            id="loan_001",
            bank_name="〇〇銀行",
            loan_type=LoanType.LONG_TERM,
            original_amount=50_000_000,
            current_balance=45_000_000,
            interest_rate=0.015,
            repayment_method=RepaymentMethod.EQUAL_PRINCIPAL,
            repayment_start_date="2020-04",
            maturity_date="2030-03",
        )
        
        assert loan.bank_name == "〇〇銀行"
        assert loan.current_balance == 45_000_000
        assert loan.interest_rate == 0.015
        assert loan.repayment_method == RepaymentMethod.EQUAL_PRINCIPAL
    
    def test_equal_payment_method(self):
        """元利均等返済の設定"""
        loan = LoanContract(
            id="loan_002",
            bank_name="△△銀行",
            loan_type=LoanType.LONG_TERM,
            original_amount=30_000_000,
            current_balance=30_000_000,
            interest_rate=0.02,
            repayment_method=RepaymentMethod.EQUAL_PAYMENT,
            repayment_start_date="2024-04",
            maturity_date="2028-03",
        )
        
        assert loan.repayment_method == RepaymentMethod.EQUAL_PAYMENT


class TestLoanRepaymentEngine:
    """LoanRepaymentEngine のテスト"""
    
    def test_equal_principal_schedule(self):
        """元金均等返済スケジュール"""
        loan = LoanContract(
            id="loan_001",
            bank_name="テスト銀行",
            loan_type=LoanType.LONG_TERM,
            original_amount=12_000_000,
            current_balance=12_000_000,
            interest_rate=0.012,
            repayment_method=RepaymentMethod.EQUAL_PRINCIPAL,
            repayment_start_date="2024-04",
            maturity_date="2026-03",  # 2年 = 24ヶ月
        )
        
        engine = LoanRepaymentEngine()
        schedule = engine.calculate_schedule(loan, months_to_calculate=24)
        
        assert isinstance(schedule, LoanRepaymentSchedule)
        assert len(schedule.months) > 0
    
    def test_interest_decreasing(self):
        """利息が時間とともに減少すること"""
        loan = LoanContract(
            id="loan_002",
            bank_name="テスト銀行",
            loan_type=LoanType.LONG_TERM,
            original_amount=10_000_000,
            current_balance=10_000_000,
            interest_rate=0.02,
            repayment_method=RepaymentMethod.EQUAL_PRINCIPAL,
            repayment_start_date="2024-04",
            maturity_date="2025-03",  # 1年
        )
        
        engine = LoanRepaymentEngine()
        schedule = engine.calculate_schedule(loan, months_to_calculate=12)
        
        if len(schedule.months) >= 2:
            interests = [m.interest for m in schedule.months]
            # 利息は時間とともに減少（元金均等の場合）
            assert interests[0] >= interests[-1]
    
    def test_balance_reaches_zero(self):
        """最終的に残高がゼロになること"""
        loan = LoanContract(
            id="loan_003",
            bank_name="テスト銀行",
            loan_type=LoanType.LONG_TERM,
            original_amount=10_000_000,
            current_balance=10_000_000,
            interest_rate=0.015,
            repayment_method=RepaymentMethod.EQUAL_PRINCIPAL,
            repayment_start_date="2024-04",
            maturity_date="2025-03",  # 1年
        )
        
        engine = LoanRepaymentEngine()
        schedule = engine.calculate_schedule(loan, months_to_calculate=12)
        
        # 最終月の残高がゼロに近い
        if schedule.months:
            final_balance = schedule.months[-1].closing_balance
            assert final_balance <= 1  # 誤差許容


class TestRescheduleScenario:
    """リスケシナリオのテスト"""
    
    def test_extension_scenario(self):
        """期間延長シナリオ"""
        loan = LoanContract(
            id="loan_004",
            bank_name="テスト銀行",
            loan_type=LoanType.LONG_TERM,
            original_amount=20_000_000,
            current_balance=20_000_000,
            interest_rate=0.015,
            repayment_method=RepaymentMethod.EQUAL_PRINCIPAL,
            repayment_start_date="2024-04",
            maturity_date="2025-03",  # 1年
        )
        
        scenario = RescheduleScenario(
            scenario_name="期間延長",
            description="返済期間を1年延長",
            extension_months=12,
            application_date="2024-04",
        )
        
        engine = LoanRepaymentEngine()
        result = engine.apply_reschedule(loan, scenario)
        
        assert result is not None
        # リスケ後は期間が長くなる
        assert len(result.new_schedule.months) > len(result.original_schedule.months)
    
    def test_grace_period_scenario(self):
        """据置期間シナリオ"""
        loan = LoanContract(
            id="loan_005",
            bank_name="テスト銀行",
            loan_type=LoanType.LONG_TERM,
            original_amount=10_000_000,
            current_balance=10_000_000,
            interest_rate=0.02,
            repayment_method=RepaymentMethod.EQUAL_PRINCIPAL,
            repayment_start_date="2024-04",
            maturity_date="2025-03",
        )
        
        scenario = RescheduleScenario(
            scenario_name="据置期間",
            description="6ヶ月据置",
            grace_period_months=6,
            application_date="2024-04",
        )
        
        engine = LoanRepaymentEngine()
        result = engine.apply_reschedule(loan, scenario)
        
        # リスケ結果が存在する
        assert result is not None


class TestRepaymentCapacityAnalysis:
    """返済可能額分析のテスト"""
    
    def test_capacity_analysis(self):
        """返済可能額の計算"""
        engine = LoanRepaymentEngine()
        
        analysis = engine.analyze_repayment_capacity(
            operating_profit=15_000_000,
            depreciation=2_000_000,
            net_income=10_000_000,
            total_debt=50_000_000,
            annual_debt_service=8_000_000,
        )
        
        assert isinstance(analysis, RepaymentCapacityAnalysis)
        assert analysis.ebitda > 0
        assert analysis.debt_payback_years > 0


class TestEdgeCases:
    """エッジケースのテスト"""
    
    def test_zero_interest_rate(self):
        """金利ゼロの場合"""
        loan = LoanContract(
            id="loan_zero",
            bank_name="無利子銀行",
            loan_type=LoanType.GOVERNMENT,
            original_amount=10_000_000,
            current_balance=10_000_000,
            interest_rate=0.0,
            repayment_method=RepaymentMethod.EQUAL_PRINCIPAL,
            repayment_start_date="2024-04",
            maturity_date="2025-03",
        )
        
        engine = LoanRepaymentEngine()
        schedule = engine.calculate_schedule(loan, months_to_calculate=12)
        
        # 全ての利息がゼロ
        for m in schedule.months:
            assert m.interest == 0
    
    def test_very_short_term(self):
        """超短期借入"""
        loan = LoanContract(
            id="loan_short",
            bank_name="短期銀行",
            loan_type=LoanType.SHORT_TERM,
            original_amount=1_000_000,
            current_balance=1_000_000,
            interest_rate=0.01,
            repayment_method=RepaymentMethod.EQUAL_PRINCIPAL,
            repayment_start_date="2024-04",
            maturity_date="2024-06",  # 3ヶ月
        )
        
        engine = LoanRepaymentEngine()
        schedule = engine.calculate_schedule(loan, months_to_calculate=3)
        
        assert len(schedule.months) <= 3
