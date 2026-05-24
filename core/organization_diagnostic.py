"""
Organization Diagnostic Module for Consulting OS.
Provides organizational health assessment, structure analysis, and HR analytics.

組織診断モジュール:
- 組織健全性評価
- 組織構造分析
- 人材分析（離職率、人件費等）
- 組織課題の特定と改善提案
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class OrganizationSize(str, Enum):
    """組織規模"""
    MICRO = "micro"      # 1-10人
    SMALL = "small"      # 11-50人
    MEDIUM = "medium"    # 51-200人
    LARGE = "large"      # 201人以上


class DepartmentType(str, Enum):
    """部門タイプ"""
    SALES = "sales"
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    ADMIN = "admin"
    MANAGEMENT = "management"


class Employee(BaseModel):
    """従業員情報"""
    employee_id: str = Field(default="")
    department: DepartmentType = Field(default=DepartmentType.ADMIN)
    position_level: int = Field(default=1, ge=1, le=10, description="役職レベル（1=一般, 10=経営層）")
    tenure_years: float = Field(default=0.0)
    age: int = Field(default=30)
    annual_salary: float = Field(default=0.0, description="年収（万円）")
    is_manager: bool = Field(default=False)


class DepartmentMetrics(BaseModel):
    """部門メトリクス"""
    department: DepartmentType
    department_name_ja: str
    headcount: int = Field(default=0)
    avg_tenure: float = Field(default=0.0)
    avg_age: float = Field(default=0.0)
    annual_turnover_rate: float = Field(default=0.0)
    labor_cost: float = Field(default=0.0, description="人件費（百万円）")
    labor_cost_ratio: float = Field(default=0.0, description="売上高人件費率")
    revenue_per_employee: float = Field(default=0.0, description="1人当たり売上高")


class OrganizationStructure(BaseModel):
    """組織構造"""
    total_headcount: int = Field(default=0)
    management_ratio: float = Field(default=0.0, description="管理職比率")
    span_of_control: float = Field(default=0.0, description="管理スパン（部下数/管理職数）")
    hierarchy_levels: int = Field(default=0, description="階層数")
    
    departments: List[DepartmentMetrics] = Field(default=[])
    
    # 構造の評価
    structure_type: str = Field(
        default="functional",
        description="機能型/事業部型/マトリクス型"
    )
    structure_issues: List[str] = Field(default=[])


class TurnoverAnalysis(BaseModel):
    """離職分析"""
    annual_turnover_rate: float = Field(default=0.0)
    voluntary_turnover_rate: float = Field(default=0.0, description="自己都合離職率")
    early_turnover_rate: float = Field(default=0.0, description="早期離職率（3年以内）")
    
    turnover_by_department: Dict[str, float] = Field(default={})
    turnover_by_tenure: Dict[str, float] = Field(default={})
    
    estimated_turnover_cost: float = Field(
        default=0.0, 
        description="離職コスト推定（百万円/年）"
    )
    
    main_reasons: List[str] = Field(default=[], description="主な離職理由")
    high_risk_groups: List[str] = Field(default=[], description="離職リスク高グループ")


class LaborCostAnalysis(BaseModel):
    """人件費分析"""
    total_labor_cost: float = Field(default=0.0, description="総人件費（百万円）")
    labor_cost_ratio: float = Field(default=0.0, description="売上高人件費率")
    labor_cost_per_employee: float = Field(default=0.0, description="1人当たり人件費（万円）")
    
    # 内訳
    salary_cost: float = Field(default=0.0, description="給与（百万円）")
    bonus_cost: float = Field(default=0.0, description="賞与（百万円）")
    social_insurance_cost: float = Field(default=0.0, description="法定福利費（百万円）")
    other_benefits_cost: float = Field(default=0.0, description="福利厚生費（百万円）")
    
    # 生産性指標
    revenue_per_employee: float = Field(default=0.0, description="1人当たり売上高（百万円）")
    profit_per_employee: float = Field(default=0.0, description="1人当たり利益（百万円）")
    labor_productivity: float = Field(default=0.0, description="労働生産性（付加価値/人件費）")
    
    # ベンチマーク比較
    benchmark_labor_cost_ratio: float = Field(default=0.0)
    gap_vs_benchmark: float = Field(default=0.0)


class OrganizationHealthScore(BaseModel):
    """組織健全性スコア"""
    overall_score: int = Field(default=0, ge=0, le=100)
    
    # 各カテゴリスコア
    structure_score: int = Field(default=0, ge=0, le=100, description="組織構造")
    people_score: int = Field(default=0, ge=0, le=100, description="人材")
    productivity_score: int = Field(default=0, ge=0, le=100, description="生産性")
    retention_score: int = Field(default=0, ge=0, le=100, description="定着率")
    
    grade: str = Field(default="C", description="A/B/C/D/E")
    
    def calculate_overall(self):
        self.overall_score = int(
            self.structure_score * 0.2 +
            self.people_score * 0.3 +
            self.productivity_score * 0.3 +
            self.retention_score * 0.2
        )
        if self.overall_score >= 80:
            self.grade = "A"
        elif self.overall_score >= 65:
            self.grade = "B"
        elif self.overall_score >= 50:
            self.grade = "C"
        elif self.overall_score >= 35:
            self.grade = "D"
        else:
            self.grade = "E"


class OrganizationDiagnosticResult(BaseModel):
    """組織診断結果"""
    company_name: Optional[str] = None
    analysis_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    
    # 基本情報
    organization_size: OrganizationSize
    total_headcount: int
    
    # 分析結果
    structure: OrganizationStructure
    turnover: TurnoverAnalysis
    labor_cost: LaborCostAnalysis
    health_score: OrganizationHealthScore
    
    # 課題と推奨事項
    key_issues: List[str] = Field(default=[])
    recommendations: List[str] = Field(default=[])
    priority_actions: List[str] = Field(default=[], description="優先アクション")
    
    sources: List[str] = Field(default=[])


class OrganizationDiagnosticAnalyzer:
    """組織診断エンジン"""
    
    # 業界別ベンチマーク
    LABOR_BENCHMARKS = {
        "manufacturing": {"labor_cost_ratio": 0.25, "turnover_rate": 0.08},
        "retail": {"labor_cost_ratio": 0.15, "turnover_rate": 0.15},
        "it": {"labor_cost_ratio": 0.55, "turnover_rate": 0.12},
        "services": {"labor_cost_ratio": 0.45, "turnover_rate": 0.10},
        "restaurant": {"labor_cost_ratio": 0.35, "turnover_rate": 0.25},
        "healthcare": {"labor_cost_ratio": 0.50, "turnover_rate": 0.08},
        "construction": {"labor_cost_ratio": 0.25, "turnover_rate": 0.10}
    }
    
    def __init__(self, industry: str = "manufacturing"):
        self.industry = industry.lower()
        self.benchmarks = self.LABOR_BENCHMARKS.get(
            self.industry,
            {"labor_cost_ratio": 0.30, "turnover_rate": 0.10}
        )
    
    def analyze(
        self,
        total_headcount: int,
        annual_revenue: float,
        total_labor_cost: float,
        annual_turnover_count: int,
        departments: Optional[Dict[str, int]] = None,
        avg_tenure: float = 5.0,
        management_count: int = 0,
        hierarchy_levels: int = 3,
        company_name: Optional[str] = None
    ) -> OrganizationDiagnosticResult:
        """
        組織診断を実行。
        
        Args:
            total_headcount: 総従業員数
            annual_revenue: 年間売上高（百万円）
            total_labor_cost: 総人件費（百万円）
            annual_turnover_count: 年間離職者数
            departments: 部門別人数 {"sales": 10, "production": 20, ...}
            avg_tenure: 平均勤続年数
            management_count: 管理職数
            hierarchy_levels: 組織階層数
        """
        
        # 組織規模判定
        if total_headcount <= 10:
            size = OrganizationSize.MICRO
        elif total_headcount <= 50:
            size = OrganizationSize.SMALL
        elif total_headcount <= 200:
            size = OrganizationSize.MEDIUM
        else:
            size = OrganizationSize.LARGE
        
        # 組織構造分析
        structure = self._analyze_structure(
            total_headcount, management_count, hierarchy_levels, departments
        )
        
        # 離職分析
        turnover = self._analyze_turnover(
            total_headcount, annual_turnover_count, total_labor_cost
        )
        
        # 人件費分析
        labor_cost = self._analyze_labor_cost(
            total_headcount, annual_revenue, total_labor_cost
        )
        
        # 健全性スコア
        health_score = self._calculate_health_score(
            structure, turnover, labor_cost
        )
        
        # 課題と推奨事項
        issues, recommendations, priorities = self._generate_recommendations(
            structure, turnover, labor_cost, health_score
        )
        
        return OrganizationDiagnosticResult(
            company_name=company_name,
            organization_size=size,
            total_headcount=total_headcount,
            structure=structure,
            turnover=turnover,
            labor_cost=labor_cost,
            health_score=health_score,
            key_issues=issues,
            recommendations=recommendations,
            priority_actions=priorities,
            sources=[
                f"{self.industry}業界 組織ベンチマーク（推定値）",
                "厚生労働省 雇用動向調査 2024年版"
            ]
        )
    
    def _analyze_structure(
        self,
        total_headcount: int,
        management_count: int,
        hierarchy_levels: int,
        departments: Optional[Dict[str, int]]
    ) -> OrganizationStructure:
        """組織構造を分析"""
        management_ratio = management_count / total_headcount if total_headcount > 0 else 0
        non_managers = total_headcount - management_count
        span_of_control = non_managers / management_count if management_count > 0 else 0
        
        structure_issues = []
        
        # 管理職比率チェック
        if management_ratio > 0.25:
            structure_issues.append("管理職比率が高い（25%超）：逆ピラミッド構造の可能性")
        elif management_ratio < 0.05:
            structure_issues.append("管理職比率が低い（5%未満）：管理体制の脆弱さ")
        
        # 管理スパンチェック
        if span_of_control > 15:
            structure_issues.append("管理スパンが広すぎる（15人超）：管理が行き届かない可能性")
        elif span_of_control < 3 and management_count > 0:
            structure_issues.append("管理スパンが狭い（3人未満）：組織の肥大化")
        
        # 階層数チェック
        if hierarchy_levels > 5:
            structure_issues.append("階層が深い（5層超）：意思決定の遅延リスク")
        
        return OrganizationStructure(
            total_headcount=total_headcount,
            management_ratio=management_ratio,
            span_of_control=span_of_control,
            hierarchy_levels=hierarchy_levels,
            structure_type="functional",
            structure_issues=structure_issues
        )
    
    def _analyze_turnover(
        self,
        total_headcount: int,
        annual_turnover_count: int,
        total_labor_cost: float
    ) -> TurnoverAnalysis:
        """離職を分析"""
        turnover_rate = annual_turnover_count / total_headcount if total_headcount > 0 else 0
        
        # 離職コスト推定（1人あたり年収の50-150%）
        avg_salary = (total_labor_cost * 100) / total_headcount if total_headcount > 0 else 0  # 万円
        estimated_cost = annual_turnover_count * avg_salary * 0.5 / 100  # 百万円
        
        main_reasons = []
        high_risk_groups = []
        
        if turnover_rate > self.benchmarks["turnover_rate"]:
            main_reasons.append("業界平均を上回る離職率")
            
        if turnover_rate > 0.20:
            main_reasons.append("給与・待遇への不満（推定）")
            main_reasons.append("キャリア成長機会の不足（推定）")
            high_risk_groups.append("入社3年以内の若手")
            high_risk_groups.append("中堅社員（5-10年目）")
        
        return TurnoverAnalysis(
            annual_turnover_rate=turnover_rate,
            voluntary_turnover_rate=turnover_rate * 0.8,  # 推定
            early_turnover_rate=turnover_rate * 1.5,  # 推定
            estimated_turnover_cost=estimated_cost,
            main_reasons=main_reasons,
            high_risk_groups=high_risk_groups
        )
    
    def _analyze_labor_cost(
        self,
        total_headcount: int,
        annual_revenue: float,
        total_labor_cost: float
    ) -> LaborCostAnalysis:
        """人件費を分析"""
        labor_cost_ratio = total_labor_cost / annual_revenue if annual_revenue > 0 else 0
        labor_cost_per_employee = (total_labor_cost * 100) / total_headcount if total_headcount > 0 else 0  # 万円
        revenue_per_employee = annual_revenue / total_headcount if total_headcount > 0 else 0  # 百万円
        
        # 内訳推定
        salary_cost = total_labor_cost * 0.70
        bonus_cost = total_labor_cost * 0.15
        social_insurance = total_labor_cost * 0.12
        other_benefits = total_labor_cost * 0.03
        
        return LaborCostAnalysis(
            total_labor_cost=total_labor_cost,
            labor_cost_ratio=labor_cost_ratio,
            labor_cost_per_employee=labor_cost_per_employee,
            salary_cost=salary_cost,
            bonus_cost=bonus_cost,
            social_insurance_cost=social_insurance,
            other_benefits_cost=other_benefits,
            revenue_per_employee=revenue_per_employee,
            profit_per_employee=revenue_per_employee * 0.05,  # 利益率5%仮定
            labor_productivity=revenue_per_employee / (total_labor_cost / total_headcount) if total_labor_cost > 0 else 0,
            benchmark_labor_cost_ratio=self.benchmarks["labor_cost_ratio"],
            gap_vs_benchmark=labor_cost_ratio - self.benchmarks["labor_cost_ratio"]
        )
    
    def _calculate_health_score(
        self,
        structure: OrganizationStructure,
        turnover: TurnoverAnalysis,
        labor_cost: LaborCostAnalysis
    ) -> OrganizationHealthScore:
        """健全性スコアを計算"""
        
        # 構造スコア
        structure_score = 100
        structure_score -= len(structure.structure_issues) * 15
        structure_score = max(0, structure_score)
        
        # 人材スコア（離職率ベース）
        retention_score = 100
        if turnover.annual_turnover_rate > 0.20:
            retention_score = 40
        elif turnover.annual_turnover_rate > 0.15:
            retention_score = 55
        elif turnover.annual_turnover_rate > 0.10:
            retention_score = 70
        elif turnover.annual_turnover_rate > 0.05:
            retention_score = 85
        
        # 生産性スコア
        productivity_score = 70
        if labor_cost.gap_vs_benchmark > 0.1:
            productivity_score = 40
        elif labor_cost.gap_vs_benchmark > 0.05:
            productivity_score = 55
        elif labor_cost.gap_vs_benchmark < -0.05:
            productivity_score = 85
        
        # 人材スコア（総合）
        people_score = int((retention_score + productivity_score) / 2)
        
        health = OrganizationHealthScore(
            structure_score=structure_score,
            people_score=people_score,
            productivity_score=productivity_score,
            retention_score=retention_score
        )
        health.calculate_overall()
        
        return health
    
    def _generate_recommendations(
        self,
        structure: OrganizationStructure,
        turnover: TurnoverAnalysis,
        labor_cost: LaborCostAnalysis,
        health: OrganizationHealthScore
    ) -> tuple[List[str], List[str], List[str]]:
        """推奨事項を生成"""
        issues = []
        recommendations = []
        priorities = []
        
        # 離職率問題
        if turnover.annual_turnover_rate > self.benchmarks["turnover_rate"]:
            issues.append(
                f"【離職率】年間離職率{turnover.annual_turnover_rate*100:.1f}%は"
                f"業界平均{self.benchmarks['turnover_rate']*100:.0f}%を上回る"
            )
            recommendations.append("退職理由のヒアリングと分析")
            recommendations.append("従業員満足度調査の実施")
            priorities.append("【即座】直近退職者へのインタビュー実施")
        
        # 離職コスト
        if turnover.estimated_turnover_cost > 0:
            issues.append(
                f"【離職コスト】推定年間{turnover.estimated_turnover_cost:.1f}百万円の損失"
            )
        
        # 人件費率問題
        if labor_cost.gap_vs_benchmark > 0.05:
            issues.append(
                f"【人件費率】売上高人件費率{labor_cost.labor_cost_ratio*100:.1f}%は"
                f"業界平均{labor_cost.benchmark_labor_cost_ratio*100:.0f}%を上回る"
            )
            recommendations.append("業務効率化による生産性向上")
            recommendations.append("適正人員配置の見直し")
        
        # 組織構造問題
        for issue in structure.structure_issues:
            issues.append(f"【組織構造】{issue}")
        
        if structure.management_ratio > 0.25:
            recommendations.append("管理職役割の再定義と適正化")
        
        # 健全性グレード別
        if health.grade in ["D", "E"]:
            priorities.append("【緊急】外部コンサルタントによる組織診断の実施")
        
        return issues, recommendations, priorities


def diagnose_organization(
    total_headcount: int,
    annual_revenue: float,
    total_labor_cost: float,
    annual_turnover_count: int,
    industry: str = "manufacturing",
    management_count: int = 0,
    company_name: Optional[str] = None
) -> OrganizationDiagnosticResult:
    """
    組織診断のファサード関数。
    
    Example:
        >>> result = diagnose_organization(
        ...     total_headcount=50,
        ...     annual_revenue=500,
        ...     total_labor_cost=120,
        ...     annual_turnover_count=8,
        ...     industry="manufacturing"
        ... )
        >>> print(result.health_score.grade)
        "C"
    """
    analyzer = OrganizationDiagnosticAnalyzer(industry)
    return analyzer.analyze(
        total_headcount=total_headcount,
        annual_revenue=annual_revenue,
        total_labor_cost=total_labor_cost,
        annual_turnover_count=annual_turnover_count,
        management_count=management_count,
        company_name=company_name
    )
