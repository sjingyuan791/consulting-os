"""
Sales KPI Analyzer for Consulting OS.
Provides comprehensive sales process analysis, KPI design, and performance tracking.

営業力強化のためのKPI分析モジュール:
- 営業プロセス分析（ファネル分析）
- 営業KPI設計と目標設定
- 営業パフォーマンス評価
- 改善施策の提案
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class SalesStage(str, Enum):
    """営業プロセスステージ"""
    LEAD = "lead"                    # リード獲得
    QUALIFICATION = "qualification"  # 見込み客認定
    MEETING = "meeting"              # 商談/面談
    PROPOSAL = "proposal"            # 提案
    NEGOTIATION = "negotiation"      # 交渉
    CLOSING = "closing"              # 成約
    DELIVERY = "delivery"            # 納品/サービス提供


class FunnelStage(BaseModel):
    """ファネルの各ステージ"""
    stage: SalesStage
    stage_name_ja: str
    count: int = Field(default=0, description="件数")
    value: float = Field(default=0.0, description="金額（百万円）")
    conversion_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="次ステージへの転換率")
    avg_days: float = Field(default=0.0, description="平均滞留日数")


class SalesFunnelAnalysis(BaseModel):
    """営業ファネル分析"""
    analysis_period: str = Field(default="", description="分析期間")
    stages: List[FunnelStage] = Field(default=[])
    
    # ファネル全体指標
    total_leads: int = Field(default=0)
    total_closed: int = Field(default=0)
    overall_conversion_rate: float = Field(default=0.0)
    avg_sales_cycle_days: float = Field(default=0.0, description="平均営業サイクル日数")
    
    # ボトルネック識別
    bottleneck_stage: Optional[str] = Field(default=None, description="最大のボトルネック")
    bottleneck_reason: str = Field(default="")
    
    def calculate_metrics(self):
        """メトリクスを計算"""
        if self.stages and self.stages[0].count > 0:
            self.total_leads = self.stages[0].count
            
            # 成約数を取得
            closing_stages = [s for s in self.stages if s.stage == SalesStage.CLOSING]
            if closing_stages:
                self.total_closed = closing_stages[0].count
            
            self.overall_conversion_rate = (
                self.total_closed / self.total_leads 
                if self.total_leads > 0 else 0
            )
            
            # 平均サイクル日数
            self.avg_sales_cycle_days = sum(s.avg_days for s in self.stages)
            
            # ボトルネック特定（最低転換率のステージ）
            if self.stages:
                min_stage = min(
                    [s for s in self.stages if s.conversion_rate < 1.0], 
                    key=lambda x: x.conversion_rate,
                    default=None
                )
                if min_stage:
                    self.bottleneck_stage = min_stage.stage_name_ja
                    self.bottleneck_reason = f"転換率{min_stage.conversion_rate*100:.1f}%"


class SalesKPI(BaseModel):
    """営業KPI"""
    kpi_name: str
    kpi_name_ja: str
    current_value: float
    target_value: float
    unit: str = Field(default="")
    achievement_rate: float = Field(default=0.0)
    trend: str = Field(default="stable", description="improving/stable/declining")
    priority: str = Field(default="medium", description="high/medium/low")
    
    def calculate_achievement(self):
        if self.target_value > 0:
            self.achievement_rate = self.current_value / self.target_value


class SalesKPISet(BaseModel):
    """営業KPIセット"""
    # 量的KPI
    lead_count: SalesKPI = Field(
        default=SalesKPI(
            kpi_name="lead_count",
            kpi_name_ja="リード獲得数",
            current_value=0,
            target_value=0,
            unit="件/月"
        )
    )
    meeting_count: SalesKPI = Field(
        default=SalesKPI(
            kpi_name="meeting_count",
            kpi_name_ja="商談数",
            current_value=0,
            target_value=0,
            unit="件/月"
        )
    )
    proposal_count: SalesKPI = Field(
        default=SalesKPI(
            kpi_name="proposal_count",
            kpi_name_ja="提案数",
            current_value=0,
            target_value=0,
            unit="件/月"
        )
    )
    closed_count: SalesKPI = Field(
        default=SalesKPI(
            kpi_name="closed_count",
            kpi_name_ja="成約数",
            current_value=0,
            target_value=0,
            unit="件/月"
        )
    )
    
    # 質的KPI
    conversion_rate: SalesKPI = Field(
        default=SalesKPI(
            kpi_name="conversion_rate",
            kpi_name_ja="成約率",
            current_value=0,
            target_value=0,
            unit="%"
        )
    )
    avg_deal_size: SalesKPI = Field(
        default=SalesKPI(
            kpi_name="avg_deal_size",
            kpi_name_ja="平均受注単価",
            current_value=0,
            target_value=0,
            unit="万円"
        )
    )
    sales_cycle_days: SalesKPI = Field(
        default=SalesKPI(
            kpi_name="sales_cycle_days",
            kpi_name_ja="営業サイクル日数",
            current_value=0,
            target_value=0,
            unit="日"
        )
    )
    customer_acquisition_cost: SalesKPI = Field(
        default=SalesKPI(
            kpi_name="cac",
            kpi_name_ja="顧客獲得コスト",
            current_value=0,
            target_value=0,
            unit="万円"
        )
    )
    
    # 生産性KPI
    revenue_per_rep: SalesKPI = Field(
        default=SalesKPI(
            kpi_name="revenue_per_rep",
            kpi_name_ja="営業1人当たり売上",
            current_value=0,
            target_value=0,
            unit="万円/月"
        )
    )
    activities_per_rep: SalesKPI = Field(
        default=SalesKPI(
            kpi_name="activities_per_rep",
            kpi_name_ja="営業1人当たり活動量",
            current_value=0,
            target_value=0,
            unit="件/日"
        )
    )


class SalesTeamMember(BaseModel):
    """営業チームメンバー"""
    name: str
    role: str = Field(default="営業担当")
    leads_handled: int = Field(default=0)
    meetings_held: int = Field(default=0)
    deals_closed: int = Field(default=0)
    revenue_generated: float = Field(default=0.0, description="百万円")
    performance_score: float = Field(default=0.0, ge=0.0, le=100.0)


class SalesPerformanceAnalysis(BaseModel):
    """営業パフォーマンス分析結果"""
    analysis_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    analysis_period: str = Field(default="")
    
    # ファネル分析
    funnel: SalesFunnelAnalysis
    
    # KPIセット
    kpis: SalesKPISet
    
    # チーム分析
    team_size: int = Field(default=0)
    team_members: List[SalesTeamMember] = Field(default=[])
    top_performer: Optional[str] = Field(default=None)
    
    # ベンチマーク比較
    benchmark_comparison: Dict[str, Dict[str, float]] = Field(
        default={},
        description="KPI名: {current, benchmark, gap}"
    )
    
    # 課題と推奨施策
    issues: List[str] = Field(default=[])
    recommendations: List[str] = Field(default=[])
    
    sources: List[str] = Field(default=[])


class SalesKPIAnalyzer:
    """営業KPI分析エンジン"""
    
    # 業界別営業KPIベンチマーク
    INDUSTRY_BENCHMARKS = {
        "manufacturing": {
            "conversion_rate": 0.25,  # 25%
            "avg_deal_size": 500,     # 500万円
            "sales_cycle_days": 90,
            "revenue_per_rep": 500,   # 500万円/月
            "activities_per_rep": 5
        },
        "it": {
            "conversion_rate": 0.20,
            "avg_deal_size": 300,
            "sales_cycle_days": 60,
            "revenue_per_rep": 400,
            "activities_per_rep": 8
        },
        "retail": {
            "conversion_rate": 0.30,
            "avg_deal_size": 50,
            "sales_cycle_days": 7,
            "revenue_per_rep": 300,
            "activities_per_rep": 15
        },
        "services": {
            "conversion_rate": 0.22,
            "avg_deal_size": 200,
            "sales_cycle_days": 45,
            "revenue_per_rep": 350,
            "activities_per_rep": 6
        },
        "restaurant": {
            "conversion_rate": 0.60,  # 来店客ベース
            "avg_deal_size": 0.3,     # 3000円
            "sales_cycle_days": 1,
            "revenue_per_rep": 150,
            "activities_per_rep": 30
        }
    }
    
    def __init__(self, industry: str = "manufacturing"):
        self.industry = industry.lower()
        self.benchmarks = self.INDUSTRY_BENCHMARKS.get(
            self.industry,
            self.INDUSTRY_BENCHMARKS["manufacturing"]
        )
    
    def analyze_funnel(
        self,
        leads: int,
        qualified: int,
        meetings: int,
        proposals: int,
        negotiations: int,
        closed: int,
        total_days: int = 90
    ) -> SalesFunnelAnalysis:
        """ファネル分析を実行"""
        stages = [
            FunnelStage(
                stage=SalesStage.LEAD,
                stage_name_ja="リード獲得",
                count=leads,
                conversion_rate=qualified/leads if leads > 0 else 0,
                avg_days=total_days * 0.1
            ),
            FunnelStage(
                stage=SalesStage.QUALIFICATION,
                stage_name_ja="見込み客認定",
                count=qualified,
                conversion_rate=meetings/qualified if qualified > 0 else 0,
                avg_days=total_days * 0.15
            ),
            FunnelStage(
                stage=SalesStage.MEETING,
                stage_name_ja="商談/面談",
                count=meetings,
                conversion_rate=proposals/meetings if meetings > 0 else 0,
                avg_days=total_days * 0.2
            ),
            FunnelStage(
                stage=SalesStage.PROPOSAL,
                stage_name_ja="提案",
                count=proposals,
                conversion_rate=negotiations/proposals if proposals > 0 else 0,
                avg_days=total_days * 0.25
            ),
            FunnelStage(
                stage=SalesStage.NEGOTIATION,
                stage_name_ja="交渉",
                count=negotiations,
                conversion_rate=closed/negotiations if negotiations > 0 else 0,
                avg_days=total_days * 0.2
            ),
            FunnelStage(
                stage=SalesStage.CLOSING,
                stage_name_ja="成約",
                count=closed,
                conversion_rate=1.0,
                avg_days=total_days * 0.1
            )
        ]
        
        analysis = SalesFunnelAnalysis(stages=stages)
        analysis.calculate_metrics()
        
        return analysis
    
    def analyze_performance(
        self,
        funnel_data: Dict[str, int],
        current_revenue: float,
        team_size: int,
        avg_deal_size: float,
        period: str = "2024年1-3月"
    ) -> SalesPerformanceAnalysis:
        """総合的な営業パフォーマンス分析"""
        
        # ファネル分析
        funnel = self.analyze_funnel(
            leads=funnel_data.get("leads", 0),
            qualified=funnel_data.get("qualified", 0),
            meetings=funnel_data.get("meetings", 0),
            proposals=funnel_data.get("proposals", 0),
            negotiations=funnel_data.get("negotiations", 0),
            closed=funnel_data.get("closed", 0)
        )
        
        # KPI計算
        kpis = SalesKPISet()
        
        # 量的KPI
        kpis.lead_count.current_value = funnel_data.get("leads", 0)
        kpis.meeting_count.current_value = funnel_data.get("meetings", 0)
        kpis.proposal_count.current_value = funnel_data.get("proposals", 0)
        kpis.closed_count.current_value = funnel_data.get("closed", 0)
        
        # 質的KPI
        kpis.conversion_rate.current_value = funnel.overall_conversion_rate * 100
        kpis.conversion_rate.target_value = self.benchmarks["conversion_rate"] * 100
        kpis.conversion_rate.calculate_achievement()
        
        kpis.avg_deal_size.current_value = avg_deal_size
        kpis.avg_deal_size.target_value = self.benchmarks["avg_deal_size"]
        kpis.avg_deal_size.calculate_achievement()
        
        kpis.sales_cycle_days.current_value = funnel.avg_sales_cycle_days
        kpis.sales_cycle_days.target_value = self.benchmarks["sales_cycle_days"]
        
        # 生産性KPI
        if team_size > 0:
            kpis.revenue_per_rep.current_value = (current_revenue * 100) / team_size  # 万円
            kpis.revenue_per_rep.target_value = self.benchmarks["revenue_per_rep"]
            kpis.revenue_per_rep.calculate_achievement()
        
        # ベンチマーク比較
        benchmark_comparison = {
            "成約率": {
                "current": kpis.conversion_rate.current_value,
                "benchmark": self.benchmarks["conversion_rate"] * 100,
                "gap": kpis.conversion_rate.current_value - self.benchmarks["conversion_rate"] * 100
            },
            "平均受注単価": {
                "current": avg_deal_size,
                "benchmark": self.benchmarks["avg_deal_size"],
                "gap": avg_deal_size - self.benchmarks["avg_deal_size"]
            }
        }
        
        # 課題と推奨事項
        issues, recommendations = self._identify_issues_and_recommendations(
            funnel, kpis, team_size
        )
        
        return SalesPerformanceAnalysis(
            analysis_period=period,
            funnel=funnel,
            kpis=kpis,
            team_size=team_size,
            benchmark_comparison=benchmark_comparison,
            issues=issues,
            recommendations=recommendations,
            sources=[
                f"{self.industry}業界 営業KPIベンチマーク（推定値）"
            ]
        )
    
    def _identify_issues_and_recommendations(
        self,
        funnel: SalesFunnelAnalysis,
        kpis: SalesKPISet,
        team_size: int
    ) -> tuple[List[str], List[str]]:
        """課題と推奨事項を特定"""
        issues = []
        recommendations = []
        
        # 成約率チェック
        if kpis.conversion_rate.current_value < self.benchmarks["conversion_rate"] * 100:
            gap = self.benchmarks["conversion_rate"] * 100 - kpis.conversion_rate.current_value
            issues.append(
                f"【成約率低下】成約率が業界平均を{gap:.1f}%下回っています"
            )
            recommendations.append(
                "営業スキル研修の実施（ヒアリング力、提案力向上）"
            )
        
        # ボトルネックチェック
        if funnel.bottleneck_stage:
            issues.append(
                f"【ボトルネック】{funnel.bottleneck_stage}ステージで停滞"
                f"（{funnel.bottleneck_reason}）"
            )
            recommendations.append(
                f"{funnel.bottleneck_stage}プロセスの見直しと改善"
            )
        
        # 生産性チェック
        if kpis.revenue_per_rep.achievement_rate < 0.8:
            issues.append(
                f"【生産性低下】営業1人当たり売上が目標の{kpis.revenue_per_rep.achievement_rate*100:.0f}%"
            )
            recommendations.append(
                "CRM/SFA導入による業務効率化"
            )
            recommendations.append(
                "営業活動の可視化と行動量管理"
            )
        
        # リード数チェック
        expected_leads = kpis.closed_count.current_value / funnel.overall_conversion_rate if funnel.overall_conversion_rate > 0 else 0
        if kpis.lead_count.current_value < expected_leads * 1.2:
            recommendations.append(
                "リード獲得施策の強化（Web、展示会、紹介制度）"
            )
        
        return issues, recommendations


def analyze_sales_performance(
    funnel_data: Dict[str, int],
    current_revenue: float,
    team_size: int,
    avg_deal_size: float,
    industry: str = "manufacturing"
) -> SalesPerformanceAnalysis:
    """
    営業パフォーマンス分析のファサード関数。
    
    Args:
        funnel_data: ファネルデータ {"leads": 100, "qualified": 80, ...}
        current_revenue: 期間売上（百万円）
        team_size: 営業チーム人数
        avg_deal_size: 平均受注単価（万円）
        industry: 業界
    
    Example:
        >>> result = analyze_sales_performance(
        ...     funnel_data={"leads": 100, "qualified": 80, "meetings": 50, 
        ...                  "proposals": 30, "negotiations": 20, "closed": 10},
        ...     current_revenue=50,
        ...     team_size=5,
        ...     avg_deal_size=500,
        ...     industry="manufacturing"
        ... )
        >>> print(result.funnel.overall_conversion_rate)
        0.10
    """
    analyzer = SalesKPIAnalyzer(industry)
    return analyzer.analyze_performance(
        funnel_data=funnel_data,
        current_revenue=current_revenue,
        team_size=team_size,
        avg_deal_size=avg_deal_size
    )
