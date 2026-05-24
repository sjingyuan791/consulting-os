"""
Industry-Specific KPI Engines for Consulting OS.
Provides specialized analysis logic for each industry with unique KPIs.

業種固有KPIエンジン:
- 飲食業: 坪効率、F/L比率、客単価×回転率
- 医療業: 病床稼働率、診療単価、経営係数
- 建設業: 完工高、受注残高比率、工事粗利率
- 不動産業: NOI利回り、空室率、管理戸数単価
- 製造業: 設備稼働率、歩留まり、リードタイム
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod


# ==========================================
# 共通基盤
# ==========================================

class IndustryKPIResult(BaseModel):
    """業種固有KPI分析結果の基底クラス"""
    industry: str
    industry_name_ja: str
    analysis_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    
    # 総合評価
    overall_score: int = Field(default=0, ge=0, le=100)
    grade: str = Field(default="C")
    
    # 共通
    key_metrics: Dict[str, float] = Field(default={})
    benchmark_comparison: Dict[str, Dict[str, float]] = Field(default={})
    issues: List[str] = Field(default=[])
    recommendations: List[str] = Field(default=[])
    sources: List[str] = Field(default=[])


class IndustryKPIEngine(ABC):
    """業種固有KPIエンジンの抽象基底クラス"""
    
    @abstractmethod
    def analyze(self, data: Dict[str, Any]) -> IndustryKPIResult:
        pass


# ==========================================
# 飲食業 KPI Engine
# ==========================================

class RestaurantKPIs(BaseModel):
    """飲食業固有KPI"""
    # 坪効率系
    sales_per_tsubo: float = Field(default=0.0, description="坪月商（万円/坪）")
    seats_per_tsubo: float = Field(default=0.0, description="坪当たり席数")
    
    # F/L比率（原価率・人件費率）
    food_cost_ratio: float = Field(default=0.0, description="原価率(F)")
    labor_cost_ratio: float = Field(default=0.0, description="人件費率(L)")
    fl_ratio: float = Field(default=0.0, description="F/L比率")
    prime_cost: float = Field(default=0.0, description="プライムコスト")
    
    # 客単価×回転
    average_check: float = Field(default=0.0, description="客単価（円）")
    table_turnover: float = Field(default=0.0, description="回転率（回/日）")
    seats: int = Field(default=0, description="席数")
    daily_guests: int = Field(default=0, description="1日客数")
    
    # 営業効率
    sales_per_employee: float = Field(default=0.0, description="従業員1人当たり売上")
    break_even_point: float = Field(default=0.0, description="損益分岐点売上")
    
    # ベンチマーク評価
    fl_assessment: str = Field(default="", description="F/L評価")


class RestaurantAnalysisResult(IndustryKPIResult):
    """飲食業分析結果"""
    kpis: RestaurantKPIs = Field(default=RestaurantKPIs())
    business_type: str = Field(default="", description="業態（居酒屋/カフェ/ラーメン等）")


class RestaurantKPIEngine(IndustryKPIEngine):
    """飲食業KPIエンジン"""
    
    # 業態別ベンチマーク
    BENCHMARKS = {
        "izakaya": {
            "fl_ratio": 0.60, "food_cost": 0.30, "labor_cost": 0.30,
            "sales_per_tsubo": 25, "table_turnover": 1.5
        },
        "cafe": {
            "fl_ratio": 0.55, "food_cost": 0.25, "labor_cost": 0.30,
            "sales_per_tsubo": 20, "table_turnover": 2.0
        },
        "ramen": {
            "fl_ratio": 0.55, "food_cost": 0.32, "labor_cost": 0.23,
            "sales_per_tsubo": 35, "table_turnover": 3.0
        },
        "yakiniku": {
            "fl_ratio": 0.58, "food_cost": 0.35, "labor_cost": 0.23,
            "sales_per_tsubo": 40, "table_turnover": 1.2
        },
        "default": {
            "fl_ratio": 0.60, "food_cost": 0.30, "labor_cost": 0.30,
            "sales_per_tsubo": 25, "table_turnover": 1.5
        }
    }
    
    def analyze(
        self,
        monthly_sales: float,  # 月商（万円）
        floor_area_tsubo: float,  # 面積（坪）
        seats: int,
        food_cost: float,  # 原材料費（万円）
        labor_cost: float,  # 人件費（万円）
        rent: float,  # 家賃（万円）
        other_costs: float,  # その他経費（万円）
        daily_guests: int = 0,
        employees: int = 1,
        business_type: str = "default"
    ) -> RestaurantAnalysisResult:
        """飲食業KPI分析を実行"""
        
        bench = self.BENCHMARKS.get(business_type, self.BENCHMARKS["default"])
        
        # KPI計算
        sales_per_tsubo = monthly_sales / floor_area_tsubo if floor_area_tsubo > 0 else 0
        seats_per_tsubo = seats / floor_area_tsubo if floor_area_tsubo > 0 else 0
        
        food_cost_ratio = food_cost / monthly_sales if monthly_sales > 0 else 0
        labor_cost_ratio = labor_cost / monthly_sales if monthly_sales > 0 else 0
        fl_ratio = food_cost_ratio + labor_cost_ratio
        
        # 客単価・回転率計算
        days_per_month = 25  # 営業日数
        if daily_guests > 0:
            average_check = (monthly_sales * 10000) / (daily_guests * days_per_month)
            table_turnover = daily_guests / seats if seats > 0 else 0
        else:
            average_check = 0
            table_turnover = 0
        
        # 損益分岐点
        fixed_costs = rent + (other_costs * 0.7)  # 固定費推定
        variable_ratio = food_cost_ratio + (labor_cost_ratio * 0.5)
        break_even = fixed_costs / (1 - variable_ratio) if variable_ratio < 1 else 0
        
        # F/L評価
        if fl_ratio <= 0.55:
            fl_assessment = "優秀（55%以下）"
        elif fl_ratio <= 0.60:
            fl_assessment = "良好（55-60%）"
        elif fl_ratio <= 0.65:
            fl_assessment = "要改善（60-65%）"
        else:
            fl_assessment = "危険（65%超）"
        
        kpis = RestaurantKPIs(
            sales_per_tsubo=sales_per_tsubo,
            seats_per_tsubo=seats_per_tsubo,
            food_cost_ratio=food_cost_ratio,
            labor_cost_ratio=labor_cost_ratio,
            fl_ratio=fl_ratio,
            prime_cost=food_cost + labor_cost,
            average_check=average_check,
            table_turnover=table_turnover,
            seats=seats,
            daily_guests=daily_guests,
            sales_per_employee=monthly_sales / employees if employees > 0 else 0,
            break_even_point=break_even,
            fl_assessment=fl_assessment
        )
        
        # ベンチマーク比較
        benchmark_comparison = {
            "F/L比率": {
                "current": fl_ratio,
                "benchmark": bench["fl_ratio"],
                "gap": fl_ratio - bench["fl_ratio"]
            },
            "坪月商": {
                "current": sales_per_tsubo,
                "benchmark": bench["sales_per_tsubo"],
                "gap": sales_per_tsubo - bench["sales_per_tsubo"]
            },
            "回転率": {
                "current": table_turnover,
                "benchmark": bench["table_turnover"],
                "gap": table_turnover - bench["table_turnover"]
            }
        }
        
        # スコア計算
        score = 70
        if fl_ratio <= bench["fl_ratio"]:
            score += 15
        elif fl_ratio <= bench["fl_ratio"] + 0.05:
            score += 5
        else:
            score -= 10
        
        if sales_per_tsubo >= bench["sales_per_tsubo"]:
            score += 15
        elif sales_per_tsubo >= bench["sales_per_tsubo"] * 0.8:
            score += 5
        else:
            score -= 10
        
        score = max(0, min(100, score))
        grade = self._score_to_grade(score)
        
        # 課題・推奨事項
        issues, recommendations = self._generate_recommendations(
            kpis, bench, break_even, monthly_sales
        )
        
        return RestaurantAnalysisResult(
            industry="restaurant",
            industry_name_ja="飲食業",
            business_type=business_type,
            kpis=kpis,
            overall_score=score,
            grade=grade,
            key_metrics={
                "F/L比率": fl_ratio,
                "坪月商": sales_per_tsubo,
                "客単価": average_check,
                "回転率": table_turnover
            },
            benchmark_comparison=benchmark_comparison,
            issues=issues,
            recommendations=recommendations,
            sources=["日本フードサービス協会「外食産業市場動向調査」"]
        )
    
    def _score_to_grade(self, score: int) -> str:
        if score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        elif score >= 40:
            return "D"
        return "E"
    
    def _generate_recommendations(
        self, kpis: RestaurantKPIs, bench: Dict, break_even: float, sales: float
    ) -> tuple[List[str], List[str]]:
        issues = []
        recommendations = []
        
        if kpis.fl_ratio > bench["fl_ratio"]:
            issues.append(
                f"【F/L比率】{kpis.fl_ratio*100:.1f}%は目標{bench['fl_ratio']*100:.0f}%を超過"
            )
            if kpis.food_cost_ratio > bench["food_cost"]:
                recommendations.append("原価率改善: メニュー見直し、食材ロス削減、仕入れ交渉")
            if kpis.labor_cost_ratio > bench["labor_cost"]:
                recommendations.append("人件費改善: シフト最適化、オペレーション効率化")
        
        if kpis.sales_per_tsubo < bench["sales_per_tsubo"]:
            issues.append(
                f"【坪効率】坪月商{kpis.sales_per_tsubo:.0f}万円は目標{bench['sales_per_tsubo']}万円を下回る"
            )
            recommendations.append("坪効率向上: 客単価UP、回転率向上、営業時間見直し")
        
        if break_even > 0 and sales < break_even * 1.1:
            issues.append(
                f"【損益分岐】損益分岐点{break_even:.0f}万円に対し売上{sales:.0f}万円（余裕10%未満）"
            )
            recommendations.append("利益改善: 固定費削減、販促強化が急務")
        
        return issues, recommendations


# ==========================================
# 医療業 KPI Engine
# ==========================================

class HealthcareKPIs(BaseModel):
    """医療業固有KPI"""
    # 稼働・効率
    bed_occupancy_rate: float = Field(default=0.0, description="病床稼働率")
    average_length_of_stay: float = Field(default=0.0, description="平均在院日数")
    outpatient_per_day: int = Field(default=0, description="1日外来患者数")
    
    # 収益性
    revenue_per_bed: float = Field(default=0.0, description="病床当たり収益（百万円/年）")
    revenue_per_outpatient: float = Field(default=0.0, description="外来単価（円）")
    revenue_per_inpatient: float = Field(default=0.0, description="入院単価（円/日）")
    
    # 人員効率
    patients_per_nurse: float = Field(default=0.0, description="看護師1人当たり患者数")
    revenue_per_employee: float = Field(default=0.0, description="職員1人当たり収益")
    
    # 経営指標
    medical_fee_ratio: float = Field(default=0.0, description="医業収益率")
    personnel_expense_ratio: float = Field(default=0.0, description="人件費率")
    material_expense_ratio: float = Field(default=0.0, description="材料費率")


class HealthcareAnalysisResult(IndustryKPIResult):
    """医療業分析結果"""
    kpis: HealthcareKPIs = Field(default=HealthcareKPIs())
    facility_type: str = Field(default="", description="施設種別（病院/診療所等）")


class HealthcareKPIEngine(IndustryKPIEngine):
    """医療業KPIエンジン"""
    
    BENCHMARKS = {
        "hospital": {
            "bed_occupancy": 0.80, "avg_stay": 15.0, 
            "personnel_ratio": 0.55, "material_ratio": 0.25
        },
        "clinic": {
            "outpatient_per_day": 40,
            "personnel_ratio": 0.50, "material_ratio": 0.20
        }
    }
    
    def analyze(
        self,
        annual_revenue: float,  # 年間収益（百万円）
        beds: int = 0,
        bed_days_used: int = 0,  # 年間延べ入院日数
        outpatient_visits: int = 0,  # 年間外来患者数
        employees: int = 1,
        nurses: int = 0,
        personnel_cost: float = 0,  # 人件費（百万円）
        material_cost: float = 0,  # 材料費（百万円）
        facility_type: str = "hospital"
    ) -> HealthcareAnalysisResult:
        """医療業KPI分析"""
        
        bench = self.BENCHMARKS.get(facility_type, self.BENCHMARKS["hospital"])
        
        # 稼働率計算
        potential_bed_days = beds * 365 if beds > 0 else 1
        bed_occupancy = bed_days_used / potential_bed_days if beds > 0 else 0
        
        # 平均在院日数（仮定: 退院患者数 = 延べ日数 / 平均日数から逆算）
        avg_stay = 15.0  # デフォルト
        
        # 収益指標
        revenue_per_bed = annual_revenue / beds if beds > 0 else 0
        outpatient_per_day = outpatient_visits / 250 if outpatient_visits > 0 else 0  # 年間250日営業
        
        # 単価計算
        if bed_days_used > 0:
            inpatient_revenue = annual_revenue * 0.7  # 入院収益70%仮定
            revenue_per_inpatient = (inpatient_revenue * 1000000) / bed_days_used
        else:
            revenue_per_inpatient = 0
        
        if outpatient_visits > 0:
            outpatient_revenue = annual_revenue * 0.3
            revenue_per_outpatient = (outpatient_revenue * 1000000) / outpatient_visits
        else:
            revenue_per_outpatient = 0
        
        # 人員効率
        patients_per_nurse = bed_days_used / (nurses * 365) if nurses > 0 else 0
        revenue_per_employee = annual_revenue / employees if employees > 0 else 0
        
        # 経営比率
        personnel_ratio = personnel_cost / annual_revenue if annual_revenue > 0 else 0
        material_ratio = material_cost / annual_revenue if annual_revenue > 0 else 0
        medical_fee_ratio = 1 - personnel_ratio - material_ratio - 0.15  # その他15%仮定
        
        kpis = HealthcareKPIs(
            bed_occupancy_rate=bed_occupancy,
            average_length_of_stay=avg_stay,
            outpatient_per_day=int(outpatient_per_day),
            revenue_per_bed=revenue_per_bed,
            revenue_per_outpatient=revenue_per_outpatient,
            revenue_per_inpatient=revenue_per_inpatient,
            patients_per_nurse=patients_per_nurse,
            revenue_per_employee=revenue_per_employee,
            medical_fee_ratio=medical_fee_ratio,
            personnel_expense_ratio=personnel_ratio,
            material_expense_ratio=material_ratio
        )
        
        # スコア計算
        score = 70
        if bed_occupancy >= 0.80:
            score += 15
        elif bed_occupancy >= 0.70:
            score += 5
        else:
            score -= 10
        
        if personnel_ratio <= bench.get("personnel_ratio", 0.55):
            score += 10
        else:
            score -= 5
        
        score = max(0, min(100, score))
        
        return HealthcareAnalysisResult(
            industry="healthcare",
            industry_name_ja="医療・介護",
            facility_type=facility_type,
            kpis=kpis,
            overall_score=score,
            grade=self._score_to_grade(score),
            key_metrics={
                "病床稼働率": bed_occupancy,
                "人件費率": personnel_ratio,
                "職員1人当たり収益": revenue_per_employee
            },
            issues=[],
            recommendations=[],
            sources=["厚生労働省「医療経済実態調査」"]
        )
    
    def _score_to_grade(self, score: int) -> str:
        if score >= 85: return "A"
        elif score >= 70: return "B"
        elif score >= 55: return "C"
        elif score >= 40: return "D"
        return "E"


# ==========================================
# 建設業 KPI Engine
# ==========================================

class ConstructionKPIs(BaseModel):
    """建設業固有KPI"""
    # 受注・完工
    backlog_ratio: float = Field(default=0.0, description="受注残高比率（受注残/年商）")
    completion_rate: float = Field(default=0.0, description="完工高伸び率")
    order_completion_ratio: float = Field(default=0.0, description="受注/完工比率")
    
    # 利益率
    gross_profit_margin: float = Field(default=0.0, description="完成工事総利益率")
    operating_margin: float = Field(default=0.0, description="営業利益率")
    
    # 資金効率
    collection_period: float = Field(default=0.0, description="工事代金回収期間（日）")
    payment_period: float = Field(default=0.0, description="外注費支払期間（日）")
    cash_conversion_cycle: float = Field(default=0.0, description="キャッシュ・コンバージョン・サイクル")
    
    # 生産性
    revenue_per_employee: float = Field(default=0.0, description="技術者1人当たり完工高")
    subcontract_ratio: float = Field(default=0.0, description="外注比率")


class ConstructionAnalysisResult(IndustryKPIResult):
    """建設業分析結果"""
    kpis: ConstructionKPIs = Field(default=ConstructionKPIs())
    construction_type: str = Field(default="general", description="工事種別")


class ConstructionKPIEngine(IndustryKPIEngine):
    """建設業KPIエンジン"""
    
    BENCHMARKS = {
        "backlog_ratio": 0.8,  # 受注残高比率
        "gross_margin": 0.18,  # 完工粗利率
        "subcontract_ratio": 0.50,  # 外注比率
        "collection_period": 60,  # 回収期間
    }
    
    def analyze(
        self,
        completed_works: float,  # 完成工事高（百万円）
        order_backlog: float,  # 受注残高（百万円）
        gross_profit: float,  # 完成工事総利益（百万円）
        operating_profit: float,  # 営業利益（百万円）
        receivables: float,  # 完成工事未収金（百万円）
        subcontract_cost: float,  # 外注費（百万円）
        employees: int = 1,
        prev_year_completed: float = 0  # 前年完工高
    ) -> ConstructionAnalysisResult:
        """建設業KPI分析"""
        
        # KPI計算
        backlog_ratio = order_backlog / completed_works if completed_works > 0 else 0
        gross_margin = gross_profit / completed_works if completed_works > 0 else 0
        operating_margin = operating_profit / completed_works if completed_works > 0 else 0
        
        # 完工高伸び率
        completion_rate = 0
        if prev_year_completed > 0:
            completion_rate = (completed_works - prev_year_completed) / prev_year_completed
        
        # 回収期間
        daily_sales = completed_works / 365
        collection_period = receivables / daily_sales if daily_sales > 0 else 0
        
        # 外注比率
        subcontract_ratio = subcontract_cost / completed_works if completed_works > 0 else 0
        
        # 生産性
        revenue_per_employee = completed_works / employees if employees > 0 else 0
        
        kpis = ConstructionKPIs(
            backlog_ratio=backlog_ratio,
            completion_rate=completion_rate,
            order_completion_ratio=1 + completion_rate,
            gross_profit_margin=gross_margin,
            operating_margin=operating_margin,
            collection_period=collection_period,
            revenue_per_employee=revenue_per_employee,
            subcontract_ratio=subcontract_ratio
        )
        
        # スコア計算
        score = 70
        if backlog_ratio >= 0.8:
            score += 10
        elif backlog_ratio < 0.5:
            score -= 15
        
        if gross_margin >= 0.18:
            score += 15
        elif gross_margin < 0.12:
            score -= 10
        
        score = max(0, min(100, score))
        
        # 課題・推奨
        issues = []
        recommendations = []
        
        if backlog_ratio < 0.6:
            issues.append(f"【受注残】受注残高比率{backlog_ratio*100:.1f}%で将来の売上確保に懸念")
            recommendations.append("営業活動強化、新規顧客開拓")
        
        if gross_margin < 0.15:
            issues.append(f"【利益率】完工粗利{gross_margin*100:.1f}%は業界平均を下回る")
            recommendations.append("見積精度向上、原価管理徹底")
        
        if collection_period > 90:
            issues.append(f"【回収】工事代金回収{collection_period:.0f}日は長期化")
            recommendations.append("請求・回収プロセス改善")
        
        return ConstructionAnalysisResult(
            industry="construction",
            industry_name_ja="建設業",
            kpis=kpis,
            overall_score=score,
            grade=self._score_to_grade(score),
            key_metrics={
                "受注残高比率": backlog_ratio,
                "完工粗利率": gross_margin,
                "回収期間": collection_period
            },
            issues=issues,
            recommendations=recommendations,
            sources=["全国建設業協会「建設業経営分析」"]
        )
    
    def _score_to_grade(self, score: int) -> str:
        if score >= 85: return "A"
        elif score >= 70: return "B"
        elif score >= 55: return "C"
        elif score >= 40: return "D"
        return "E"


# ==========================================
# ファサード関数
# ==========================================

def analyze_restaurant(
    monthly_sales: float,
    floor_area_tsubo: float,
    seats: int,
    food_cost: float,
    labor_cost: float,
    rent: float,
    other_costs: float,
    daily_guests: int = 0,
    employees: int = 1,
    business_type: str = "default"
) -> RestaurantAnalysisResult:
    """飲食業KPI分析ファサード"""
    engine = RestaurantKPIEngine()
    return engine.analyze(
        monthly_sales=monthly_sales,
        floor_area_tsubo=floor_area_tsubo,
        seats=seats,
        food_cost=food_cost,
        labor_cost=labor_cost,
        rent=rent,
        other_costs=other_costs,
        daily_guests=daily_guests,
        employees=employees,
        business_type=business_type
    )


def analyze_healthcare(
    annual_revenue: float,
    beds: int = 0,
    bed_days_used: int = 0,
    outpatient_visits: int = 0,
    employees: int = 1,
    nurses: int = 0,
    personnel_cost: float = 0,
    material_cost: float = 0,
    facility_type: str = "hospital"
) -> HealthcareAnalysisResult:
    """医療業KPI分析ファサード"""
    engine = HealthcareKPIEngine()
    return engine.analyze(
        annual_revenue=annual_revenue,
        beds=beds,
        bed_days_used=bed_days_used,
        outpatient_visits=outpatient_visits,
        employees=employees,
        nurses=nurses,
        personnel_cost=personnel_cost,
        material_cost=material_cost,
        facility_type=facility_type
    )


def analyze_construction(
    completed_works: float,
    order_backlog: float,
    gross_profit: float,
    operating_profit: float,
    receivables: float,
    subcontract_cost: float,
    employees: int = 1,
    prev_year_completed: float = 0
) -> ConstructionAnalysisResult:
    """建設業KPI分析ファサード"""
    engine = ConstructionKPIEngine()
    return engine.analyze(
        completed_works=completed_works,
        order_backlog=order_backlog,
        gross_profit=gross_profit,
        operating_profit=operating_profit,
        receivables=receivables,
        subcontract_cost=subcontract_cost,
        employees=employees,
        prev_year_completed=prev_year_completed
    )
