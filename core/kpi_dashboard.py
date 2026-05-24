"""
KPI Dashboard Data Module for Consulting OS.
Provides structured dashboard data for real-time monitoring.

KPIダッシュボードモジュール:
- 経営ダッシュボード
- 財務ダッシュボード
- 営業ダッシュボード
- 組織ダッシュボード
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, date
from dataclasses import dataclass


class TrendDirection(str, Enum):
    """トレンド方向"""
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


class KPIStatus(str, Enum):
    """KPIステータス"""
    GOOD = "good"         # 目標達成
    WARNING = "warning"   # 要注意
    CRITICAL = "critical" # 要改善


class KPICard(BaseModel):
    """KPIカード（単一指標）"""
    kpi_id: str
    name: str
    value: float
    unit: str = Field(default="")
    
    # 比較
    target: Optional[float] = None
    previous_value: Optional[float] = None
    
    # 推移
    change_percent: Optional[float] = None
    trend: TrendDirection = Field(default=TrendDirection.FLAT)
    
    # 状態
    status: KPIStatus = Field(default=KPIStatus.GOOD)
    
    # 表示
    format_type: str = Field(default="number", description="number/percent/currency")


class ChartData(BaseModel):
    """チャートデータ"""
    chart_type: str = Field(description="line/bar/pie/gauge")
    title: str
    labels: List[str] = Field(default=[])
    datasets: List[Dict[str, Any]] = Field(default=[])
    options: Dict[str, Any] = Field(default={})


class DashboardSection(BaseModel):
    """ダッシュボードセクション"""
    section_id: str
    title: str
    kpi_cards: List[KPICard] = Field(default=[])
    charts: List[ChartData] = Field(default=[])


class ExecutiveDashboard(BaseModel):
    """経営ダッシュボード"""
    company_name: Optional[str] = None
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # サマリーKPI
    revenue: KPICard
    operating_profit: KPICard
    operating_margin: KPICard
    cash_balance: KPICard
    
    # セクション
    financial_section: DashboardSection
    sales_section: DashboardSection
    organization_section: DashboardSection
    
    # アラート
    alerts: List[str] = Field(default=[])


class DashboardGenerator:
    """ダッシュボード生成エンジン"""
    
    def generate_executive_dashboard(
        self,
        revenue: float,
        operating_profit: float,
        cash_balance: float,
        prev_revenue: float = 0,
        prev_operating_profit: float = 0,
        target_revenue: Optional[float] = None,
        target_operating_profit: Optional[float] = None,
        employee_count: int = 0,
        turnover_rate: float = 0,
        sales_pipeline: float = 0,
        monthly_data: Optional[List[Dict[str, float]]] = None,
        company_name: Optional[str] = None
    ) -> ExecutiveDashboard:
        """経営ダッシュボードを生成"""
        
        # 営業利益率
        operating_margin = operating_profit / revenue if revenue > 0 else 0
        
        # 変化率
        revenue_change = (revenue - prev_revenue) / prev_revenue if prev_revenue > 0 else 0
        profit_change = (operating_profit - prev_operating_profit) / prev_operating_profit if prev_operating_profit > 0 else 0
        
        # サマリーKPI
        revenue_kpi = KPICard(
            kpi_id="revenue",
            name="売上高",
            value=revenue,
            unit="百万円",
            target=target_revenue,
            previous_value=prev_revenue,
            change_percent=revenue_change * 100,
            trend=self._get_trend(revenue_change),
            status=self._get_status_vs_target(revenue, target_revenue),
            format_type="currency"
        )
        
        profit_kpi = KPICard(
            kpi_id="operating_profit",
            name="営業利益",
            value=operating_profit,
            unit="百万円",
            target=target_operating_profit,
            previous_value=prev_operating_profit,
            change_percent=profit_change * 100,
            trend=self._get_trend(profit_change),
            status=self._get_status_vs_target(operating_profit, target_operating_profit),
            format_type="currency"
        )
        
        margin_kpi = KPICard(
            kpi_id="operating_margin",
            name="営業利益率",
            value=operating_margin * 100,
            unit="%",
            target=5.0,  # 5%を目標
            status=KPIStatus.GOOD if operating_margin >= 0.05 else KPIStatus.WARNING if operating_margin >= 0.02 else KPIStatus.CRITICAL,
            format_type="percent"
        )
        
        cash_kpi = KPICard(
            kpi_id="cash_balance",
            name="現預金残高",
            value=cash_balance,
            unit="百万円",
            status=KPIStatus.GOOD if cash_balance > revenue * 0.1 else KPIStatus.WARNING,
            format_type="currency"
        )
        
        # 財務セクション
        financial_section = DashboardSection(
            section_id="financial",
            title="財務状況",
            kpi_cards=[
                revenue_kpi,
                profit_kpi,
                margin_kpi,
                KPICard(
                    kpi_id="roa",
                    name="ROA",
                    value=0,  # 計算には総資産が必要
                    unit="%",
                    format_type="percent"
                )
            ],
            charts=[
                self._create_monthly_chart(monthly_data) if monthly_data else ChartData(
                    chart_type="line",
                    title="月次売上推移",
                    labels=[],
                    datasets=[]
                )
            ]
        )
        
        # 営業セクション
        sales_section = DashboardSection(
            section_id="sales",
            title="営業状況",
            kpi_cards=[
                KPICard(
                    kpi_id="pipeline",
                    name="営業パイプライン",
                    value=sales_pipeline,
                    unit="百万円",
                    format_type="currency"
                ),
                KPICard(
                    kpi_id="pipeline_coverage",
                    name="パイプラインカバレッジ",
                    value=(sales_pipeline / (revenue / 12)) if revenue > 0 else 0,
                    unit="x",
                    status=KPIStatus.GOOD if sales_pipeline > revenue / 4 else KPIStatus.WARNING
                )
            ]
        )
        
        # 組織セクション
        organization_section = DashboardSection(
            section_id="organization",
            title="組織状況",
            kpi_cards=[
                KPICard(
                    kpi_id="headcount",
                    name="従業員数",
                    value=employee_count,
                    unit="名"
                ),
                KPICard(
                    kpi_id="turnover_rate",
                    name="離職率",
                    value=turnover_rate * 100,
                    unit="%",
                    status=KPIStatus.GOOD if turnover_rate < 0.10 else KPIStatus.WARNING if turnover_rate < 0.15 else KPIStatus.CRITICAL,
                    format_type="percent"
                ),
                KPICard(
                    kpi_id="revenue_per_employee",
                    name="1人当たり売上高",
                    value=revenue / employee_count if employee_count > 0 else 0,
                    unit="百万円",
                    format_type="currency"
                )
            ]
        )
        
        # アラート生成
        alerts = []
        if operating_margin < 0.03:
            alerts.append("⚠️ 営業利益率が3%未満です。収益性改善が必要です。")
        if cash_balance < revenue * 0.05:
            alerts.append("🔴 現預金残高が月商0.5ヶ月分未満です。資金繰りに注意してください。")
        if turnover_rate > 0.15:
            alerts.append("⚠️ 離職率が15%を超えています。組織課題の確認を推奨します。")
        if revenue_change < -0.10:
            alerts.append("🔴 売上が前期比10%以上減少しています。")
        
        return ExecutiveDashboard(
            company_name=company_name,
            revenue=revenue_kpi,
            operating_profit=profit_kpi,
            operating_margin=margin_kpi,
            cash_balance=cash_kpi,
            financial_section=financial_section,
            sales_section=sales_section,
            organization_section=organization_section,
            alerts=alerts
        )
    
    def _get_trend(self, change: float) -> TrendDirection:
        if change > 0.01:
            return TrendDirection.UP
        elif change < -0.01:
            return TrendDirection.DOWN
        return TrendDirection.FLAT
    
    def _get_status_vs_target(
        self, 
        value: float, 
        target: Optional[float]
    ) -> KPIStatus:
        if target is None:
            return KPIStatus.GOOD
        
        achievement = value / target if target > 0 else 0
        if achievement >= 0.95:
            return KPIStatus.GOOD
        elif achievement >= 0.80:
            return KPIStatus.WARNING
        return KPIStatus.CRITICAL
    
    def _create_monthly_chart(
        self, 
        monthly_data: List[Dict[str, float]]
    ) -> ChartData:
        labels = [d.get("month", "") for d in monthly_data]
        revenue_data = [d.get("revenue", 0) for d in monthly_data]
        profit_data = [d.get("profit", 0) for d in monthly_data]
        
        return ChartData(
            chart_type="line",
            title="月次業績推移",
            labels=labels,
            datasets=[
                {"label": "売上高", "data": revenue_data, "borderColor": "#3182ce"},
                {"label": "営業利益", "data": profit_data, "borderColor": "#38a169"}
            ]
        )


class FinancialDashboard(BaseModel):
    """財務ダッシュボード"""
    pl_section: DashboardSection
    bs_section: DashboardSection
    cf_section: DashboardSection
    ratio_section: DashboardSection


class SalesDashboard(BaseModel):
    """営業ダッシュボード"""
    pipeline_section: DashboardSection
    performance_section: DashboardSection
    forecast_section: DashboardSection


# ==========================================
# ファサード関数
# ==========================================

def generate_executive_dashboard(
    revenue: float,
    operating_profit: float,
    cash_balance: float,
    prev_revenue: float = 0,
    prev_operating_profit: float = 0,
    target_revenue: Optional[float] = None,
    employee_count: int = 0,
    turnover_rate: float = 0,
    sales_pipeline: float = 0,
    company_name: Optional[str] = None
) -> ExecutiveDashboard:
    """
    経営ダッシュボードを生成。
    
    Args:
        revenue: 売上高（百万円）
        operating_profit: 営業利益（百万円）
        cash_balance: 現預金残高（百万円）
        prev_revenue: 前期売上高
        prev_operating_profit: 前期営業利益
        target_revenue: 目標売上高
        employee_count: 従業員数
        turnover_rate: 離職率
        sales_pipeline: 営業パイプライン
        company_name: 企業名
    
    Example:
        >>> dashboard = generate_executive_dashboard(
        ...     revenue=500, operating_profit=25, cash_balance=50,
        ...     prev_revenue=480, employee_count=30
        ... )
        >>> print(dashboard.revenue.status)
    """
    generator = DashboardGenerator()
    return generator.generate_executive_dashboard(
        revenue=revenue,
        operating_profit=operating_profit,
        cash_balance=cash_balance,
        prev_revenue=prev_revenue,
        prev_operating_profit=prev_operating_profit,
        target_revenue=target_revenue,
        employee_count=employee_count,
        turnover_rate=turnover_rate,
        sales_pipeline=sales_pipeline,
        company_name=company_name
    )


def export_dashboard_json(dashboard: ExecutiveDashboard) -> Dict[str, Any]:
    """ダッシュボードをJSON形式でエクスポート"""
    return dashboard.model_dump()
