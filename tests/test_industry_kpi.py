"""
Test Industry KPI Engines.
業種別KPIエンジンのテスト
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.industry_kpi_engines import (
    RestaurantKPIEngine, RestaurantAnalysisResult, RestaurantKPIs,
    HealthcareKPIEngine, HealthcareAnalysisResult, HealthcareKPIs,
    IndustryKPIResult
)


class TestRestaurantKPIEngine:
    """RestaurantKPIEngine のテスト"""
    
    def test_engine_creation(self):
        """エンジンの作成"""
        engine = RestaurantKPIEngine()
        
        assert engine is not None
        assert hasattr(engine, 'BENCHMARKS')
    
    def test_basic_analysis(self):
        """基本的な分析"""
        engine = RestaurantKPIEngine()
        
        result = engine.analyze(
            monthly_sales=500,  # 500万円
            floor_area_tsubo=20,  # 20坪
            seats=40,
            food_cost=150,  # 150万円
            labor_cost=150,  # 150万円
            rent=50,  # 50万円
            other_costs=50,  # 50万円
            daily_guests=100,
            employees=5,
            business_type="izakaya"
        )
        
        assert isinstance(result, RestaurantAnalysisResult)
        assert result.kpis is not None
    
    def test_sales_per_tsubo_calculation(self):
        """坪月商の計算"""
        engine = RestaurantKPIEngine()
        
        result = engine.analyze(
            monthly_sales=500,
            floor_area_tsubo=20,
            seats=40,
            food_cost=150,
            labor_cost=150,
            rent=50,
            other_costs=50,
        )
        
        # 坪月商 = 500万 / 20坪 = 25万円/坪
        assert result.kpis.sales_per_tsubo == pytest.approx(25.0, rel=0.01)
    
    def test_fl_ratio_calculation(self):
        """F/L比率の計算"""
        engine = RestaurantKPIEngine()
        
        result = engine.analyze(
            monthly_sales=500,
            floor_area_tsubo=20,
            seats=40,
            food_cost=150,  # 30%
            labor_cost=150,  # 30%
            rent=50,
            other_costs=50,
        )
        
        # F/L比率 = (150 + 150) / 500 = 0.60
        assert result.kpis.fl_ratio == pytest.approx(0.60, rel=0.01)
    
    def test_table_turnover(self):
        """回転率の計算"""
        engine = RestaurantKPIEngine()
        
        result = engine.analyze(
            monthly_sales=500,
            floor_area_tsubo=20,
            seats=40,
            food_cost=150,
            labor_cost=150,
            rent=50,
            other_costs=50,
            daily_guests=80,  # 1日80人
        )
        
        # 回転率 = 80人 / 40席 = 2.0
        assert result.kpis.table_turnover == pytest.approx(2.0, rel=0.01)
    
    def test_break_even_calculation(self):
        """損益分岐点の計算"""
        engine = RestaurantKPIEngine()
        
        result = engine.analyze(
            monthly_sales=500,
            floor_area_tsubo=20,
            seats=40,
            food_cost=150,
            labor_cost=150,
            rent=50,
            other_costs=50,
        )
        
        # 損益分岐点が計算されている
        assert result.kpis.break_even_point > 0
    
    def test_different_business_types(self):
        """異なる業態のテスト"""
        engine = RestaurantKPIEngine()
        
        for business_type in ["izakaya", "cafe", "ramen"]:
            result = engine.analyze(
                monthly_sales=300,
                floor_area_tsubo=15,
                seats=25,
                food_cost=90,
                labor_cost=90,
                rent=30,
                other_costs=30,
                business_type=business_type
            )
            
            assert result is not None
            assert result.business_type == business_type
    
    def test_recommendations_generated(self):
        """改善提案の生成"""
        engine = RestaurantKPIEngine()
        
        # F/L比率が高いケース
        result = engine.analyze(
            monthly_sales=300,
            floor_area_tsubo=20,
            seats=40,
            food_cost=120,  # 40% - 高い
            labor_cost=120,  # 40% - 高い
            rent=50,
            other_costs=50,
            business_type="izakaya"
        )
        
        # 提案が生成されている
        assert len(result.recommendations) > 0


class TestHealthcareKPIEngine:
    """HealthcareKPIEngine のテスト"""
    
    def test_engine_creation(self):
        """エンジンの作成"""
        engine = HealthcareKPIEngine()
        
        assert engine is not None
        assert hasattr(engine, 'BENCHMARKS')
    
    def test_hospital_analysis(self):
        """病院の分析"""
        engine = HealthcareKPIEngine()
        
        result = engine.analyze(
            annual_revenue=500,  # 5億円
            beds=50,
            bed_days_used=14000,  # 年間延べ入院日数
            outpatient_visits=30000,
            employees=80,
            nurses=30,
            personnel_cost=280,  # 2.8億円
            material_cost=125,  # 1.25億円
            facility_type="hospital"
        )
        
        assert isinstance(result, HealthcareAnalysisResult)
        assert result.kpis is not None
    
    def test_bed_occupancy_calculation(self):
        """病床稼働率の計算"""
        engine = HealthcareKPIEngine()
        
        result = engine.analyze(
            annual_revenue=500,
            beds=50,
            bed_days_used=14600,  # 50床 × 365日 × 80%
            outpatient_visits=30000,
            employees=80,
            facility_type="hospital"
        )
        
        # 稼働率 = 14600 / (50 × 365) ≈ 0.80
        expected_occupancy = 14600 / (50 * 365)
        assert result.kpis.bed_occupancy_rate == pytest.approx(expected_occupancy, rel=0.05)
    
    def test_clinic_analysis(self):
        """診療所の分析"""
        engine = HealthcareKPIEngine()
        
        result = engine.analyze(
            annual_revenue=100,  # 1億円
            beds=0,  # 無床
            outpatient_visits=20000,
            employees=10,
            nurses=3,
            personnel_cost=55,
            material_cost=25,
            facility_type="clinic"
        )
        
        assert result is not None
        assert result.facility_type == "clinic"
    
    def test_personnel_expense_ratio(self):
        """人件費率の計算"""
        engine = HealthcareKPIEngine()
        
        result = engine.analyze(
            annual_revenue=500,
            beds=50,
            bed_days_used=14000,
            employees=80,
            personnel_cost=275,  # 55%
            material_cost=125,
            facility_type="hospital"
        )
        
        # 人件費率 = 275 / 500 = 0.55
        assert result.kpis.personnel_expense_ratio == pytest.approx(0.55, rel=0.01)


class TestEdgeCases:
    """エッジケースのテスト"""
    
    def test_restaurant_zero_sales(self):
        """売上ゼロの飲食店"""
        engine = RestaurantKPIEngine()
        
        result = engine.analyze(
            monthly_sales=0,
            floor_area_tsubo=20,
            seats=40,
            food_cost=0,
            labor_cost=100,  # 固定費のみ
            rent=50,
            other_costs=50,
        )
        
        # ゼロ除算エラーなく処理
        assert result is not None
    
    def test_healthcare_no_beds(self):
        """無床診療所"""
        engine = HealthcareKPIEngine()
        
        result = engine.analyze(
            annual_revenue=80,
            beds=0,
            outpatient_visits=15000,
            employees=8,
            facility_type="clinic"
        )
        
        assert result is not None
        # 病床関連KPIはゼロまたは計算されない
        assert result.kpis.bed_occupancy_rate == 0 or result.kpis.bed_occupancy_rate is None
