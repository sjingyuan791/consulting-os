"""
M&A Due Diligence Support Module for Consulting OS.
Provides financial DD, business DD, and valuation support.

M&A/DD支援モジュール:
- 財務DD（正常収益力分析）
- ビジネスDD（市場・競合・事業性）
- バリュエーション（DCF、マルチプル法）
- PMI計画（統合シナジー試算）
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class DealType(str, Enum):
    """M&A取引タイプ"""
    ACQUISITION = "acquisition"   # 買収
    MERGER = "merger"             # 合併
    SUCCESSION = "succession"     # 事業承継
    CARVE_OUT = "carve_out"       # カーブアウト


class RiskLevel(str, Enum):
    """リスクレベル"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ==========================================
# 財務DD
# ==========================================

class FinancialDDItem(BaseModel):
    """財務DDチェック項目"""
    category: str
    item: str
    finding: str = Field(default="")
    impact: str = Field(default="")
    adjustment_amount: float = Field(default=0.0, description="調整額（百万円）")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)


class NormalizedEarnings(BaseModel):
    """正常収益力"""
    reported_operating_profit: float = Field(description="表面営業利益")
    adjustments: List[Dict[str, float]] = Field(default=[], description="調整項目")
    normalized_operating_profit: float = Field(description="正常営業利益")
    normalized_ebitda: float = Field(description="正常EBITDA")
    depreciation: float = Field(default=0.0)
    
    # 調整理由
    adjustment_reasons: List[str] = Field(default=[])


class FinancialDDResult(BaseModel):
    """財務DD結果"""
    target_company: str
    assessment_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    
    # 正常収益力
    normalized_earnings: NormalizedEarnings
    
    # チェック項目
    dd_items: List[FinancialDDItem] = Field(default=[])
    
    # リスク要約
    high_risk_items: List[str] = Field(default=[])
    medium_risk_items: List[str] = Field(default=[])
    
    # 純資産調整
    reported_net_assets: float = Field(default=0.0)
    adjusted_net_assets: float = Field(default=0.0)
    net_asset_adjustments: List[Dict[str, float]] = Field(default=[])
    
    # 運転資本
    normalized_working_capital: float = Field(default=0.0)
    
    overall_assessment: str = Field(default="")


# ==========================================
# ビジネスDD
# ==========================================

class MarketAnalysis(BaseModel):
    """市場分析"""
    market_size: float = Field(default=0.0, description="市場規模（億円）")
    market_growth_rate: float = Field(default=0.0, description="市場成長率")
    market_trends: List[str] = Field(default=[])
    key_success_factors: List[str] = Field(default=[])


class CompetitiveAnalysis(BaseModel):
    """競合分析"""
    competitors: List[str] = Field(default=[])
    target_market_share: float = Field(default=0.0)
    competitive_position: str = Field(default="")
    competitive_advantages: List[str] = Field(default=[])
    competitive_threats: List[str] = Field(default=[])


class BusinessDDResult(BaseModel):
    """ビジネスDD結果"""
    target_company: str
    
    # 市場分析
    market_analysis: MarketAnalysis
    
    # 競合分析
    competitive_analysis: CompetitiveAnalysis
    
    # 顧客分析
    customer_concentration: float = Field(default=0.0, description="上位5社売上比率")
    customer_retention_rate: float = Field(default=0.0)
    
    # 事業リスク
    business_risks: List[str] = Field(default=[])
    
    # 成長ドライバー
    growth_drivers: List[str] = Field(default=[])
    
    # SWOT
    strengths: List[str] = Field(default=[])
    weaknesses: List[str] = Field(default=[])
    opportunities: List[str] = Field(default=[])
    threats: List[str] = Field(default=[])


# ==========================================
# バリュエーション
# ==========================================

class DCFValuation(BaseModel):
    """DCF法バリュエーション"""
    projection_years: int = Field(default=5)
    
    # キャッシュフロー予測
    fcf_projections: List[float] = Field(default=[], description="各年FCF")
    terminal_value: float = Field(default=0.0)
    
    # 割引率
    wacc: float = Field(default=0.0, description="加重平均資本コスト")
    terminal_growth_rate: float = Field(default=0.0, description="永久成長率")
    
    # 企業価値
    enterprise_value: float = Field(default=0.0)
    equity_value: float = Field(default=0.0)
    
    # 感度分析
    sensitivity_matrix: Dict[str, Dict[str, float]] = Field(default={})


class MultiplesValuation(BaseModel):
    """マルチプル法バリュエーション"""
    # EV/EBITDA
    ebitda: float = Field(default=0.0)
    ev_ebitda_multiple: float = Field(default=0.0)
    ev_by_ebitda: float = Field(default=0.0)
    
    # EV/Sales
    revenue: float = Field(default=0.0)
    ev_sales_multiple: float = Field(default=0.0)
    ev_by_sales: float = Field(default=0.0)
    
    # PER
    net_income: float = Field(default=0.0)
    per_multiple: float = Field(default=0.0)
    equity_by_per: float = Field(default=0.0)
    
    # 類似会社
    comparable_companies: List[str] = Field(default=[])


class ValuationResult(BaseModel):
    """バリュエーション結果"""
    target_company: str
    valuation_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    
    # DCF法
    dcf: DCFValuation
    
    # マルチプル法
    multiples: MultiplesValuation
    
    # 価値レンジ
    ev_low: float = Field(default=0.0)
    ev_mid: float = Field(default=0.0)
    ev_high: float = Field(default=0.0)
    
    equity_low: float = Field(default=0.0)
    equity_mid: float = Field(default=0.0)
    equity_high: float = Field(default=0.0)
    
    # 純有利子負債
    net_debt: float = Field(default=0.0)
    
    methodology_notes: str = Field(default="")


# ==========================================
# PMI計画
# ==========================================

class SynergyItem(BaseModel):
    """シナジー項目"""
    category: str  # revenue/cost
    description: str
    annual_impact: float = Field(description="年間効果（百万円）")
    realization_timeline: str = Field(default="", description="実現時期")
    probability: float = Field(default=0.5, ge=0.0, le=1.0)
    required_investment: float = Field(default=0.0, description="必要投資")


class PMIPlan(BaseModel):
    """PMI計画"""
    # シナジー
    revenue_synergies: List[SynergyItem] = Field(default=[])
    cost_synergies: List[SynergyItem] = Field(default=[])
    
    total_synergy_annual: float = Field(default=0.0)
    probability_weighted_synergy: float = Field(default=0.0)
    
    # 統合コスト
    integration_costs: List[Dict[str, float]] = Field(default=[])
    total_integration_cost: float = Field(default=0.0)
    
    # 統合リスク
    integration_risks: List[str] = Field(default=[])
    
    # マイルストーン
    day_1_actions: List[str] = Field(default=[])
    day_30_actions: List[str] = Field(default=[])
    day_100_actions: List[str] = Field(default=[])


# ==========================================
# DD支援エンジン
# ==========================================

class MADDSupportEngine:
    """M&A DD支援エンジン"""
    
    # 業界別EV/EBITDAマルチプル
    INDUSTRY_MULTIPLES = {
        "manufacturing": {"ev_ebitda": 6.0, "ev_sales": 0.8},
        "retail": {"ev_ebitda": 7.0, "ev_sales": 0.5},
        "it": {"ev_ebitda": 12.0, "ev_sales": 3.0},
        "services": {"ev_ebitda": 8.0, "ev_sales": 1.5},
        "healthcare": {"ev_ebitda": 10.0, "ev_sales": 1.2},
        "construction": {"ev_ebitda": 5.0, "ev_sales": 0.4},
        "restaurant": {"ev_ebitda": 6.5, "ev_sales": 0.6}
    }
    
    def perform_financial_dd(
        self,
        target_company: str,
        reported_revenue: float,
        reported_operating_profit: float,
        depreciation: float,
        extraordinary_items: float = 0,
        owner_compensation: float = 0,
        related_party_transactions: float = 0,
        net_assets: float = 0
    ) -> FinancialDDResult:
        """財務DDを実行"""
        
        adjustments = []
        adjustment_reasons = []
        
        # 役員報酬調整
        if owner_compensation > reported_revenue * 0.05:
            excess = owner_compensation - (reported_revenue * 0.03)
            adjustments.append({"役員報酬調整": excess})
            adjustment_reasons.append(f"役員報酬を市場水準（売上高の3%）に調整: +{excess:.1f}百万円")
        
        # 非経常項目調整
        if extraordinary_items != 0:
            adjustments.append({"非経常項目": -extraordinary_items})
            adjustment_reasons.append(f"非経常項目を除外: {-extraordinary_items:+.1f}百万円")
        
        # 関連当事者取引調整
        if related_party_transactions != 0:
            adjustments.append({"関連当事者取引": related_party_transactions * 0.1})
            adjustment_reasons.append("関連当事者取引を市場価格に調整")
        
        total_adjustment = sum(list(adj.values())[0] for adj in adjustments)
        normalized_op = reported_operating_profit + total_adjustment
        normalized_ebitda = normalized_op + depreciation
        
        normalized = NormalizedEarnings(
            reported_operating_profit=reported_operating_profit,
            adjustments=adjustments,
            normalized_operating_profit=normalized_op,
            normalized_ebitda=normalized_ebitda,
            depreciation=depreciation,
            adjustment_reasons=adjustment_reasons
        )
        
        # DDチェック項目
        dd_items = [
            FinancialDDItem(
                category="売上高",
                item="売上計上基準",
                finding="検証が必要",
                risk_level=RiskLevel.MEDIUM
            ),
            FinancialDDItem(
                category="資産",
                item="棚卸資産の評価",
                finding="適正性の確認が必要",
                risk_level=RiskLevel.MEDIUM
            ),
            FinancialDDItem(
                category="負債",
                item="簿外債務",
                finding="未計上債務の有無確認",
                risk_level=RiskLevel.HIGH
            )
        ]
        
        return FinancialDDResult(
            target_company=target_company,
            normalized_earnings=normalized,
            dd_items=dd_items,
            high_risk_items=["簿外債務の確認"],
            medium_risk_items=["売上計上基準", "棚卸資産評価"],
            reported_net_assets=net_assets,
            adjusted_net_assets=net_assets,
            overall_assessment=f"正常EBITDA {normalized_ebitda:.1f}百万円をベースに評価を推奨"
        )
    
    def perform_valuation(
        self,
        target_company: str,
        normalized_ebitda: float,
        revenue: float,
        net_income: float,
        net_debt: float,
        industry: str = "manufacturing",
        wacc: float = 0.08,
        terminal_growth: float = 0.01
    ) -> ValuationResult:
        """バリュエーションを実行"""
        
        multiples = self.INDUSTRY_MULTIPLES.get(
            industry.lower(),
            self.INDUSTRY_MULTIPLES["manufacturing"]
        )
        
        # マルチプル法
        ev_by_ebitda = normalized_ebitda * multiples["ev_ebitda"]
        ev_by_sales = revenue * multiples["ev_sales"]
        
        mult_val = MultiplesValuation(
            ebitda=normalized_ebitda,
            ev_ebitda_multiple=multiples["ev_ebitda"],
            ev_by_ebitda=ev_by_ebitda,
            revenue=revenue,
            ev_sales_multiple=multiples["ev_sales"],
            ev_by_sales=ev_by_sales,
            net_income=net_income,
            per_multiple=12.0,
            equity_by_per=net_income * 12.0
        )
        
        # 簡易DCF（5年予測）
        fcf_base = normalized_ebitda * 0.7  # FCF = EBITDA * 70%仮定
        fcf_projections = [fcf_base * (1.03 ** i) for i in range(1, 6)]
        terminal_value = fcf_projections[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
        
        # 現在価値計算
        pv_fcf = sum(fcf / ((1 + wacc) ** (i+1)) for i, fcf in enumerate(fcf_projections))
        pv_terminal = terminal_value / ((1 + wacc) ** 5)
        ev_dcf = pv_fcf + pv_terminal
        
        dcf_val = DCFValuation(
            projection_years=5,
            fcf_projections=fcf_projections,
            terminal_value=terminal_value,
            wacc=wacc,
            terminal_growth_rate=terminal_growth,
            enterprise_value=ev_dcf,
            equity_value=ev_dcf - net_debt
        )
        
        # 価値レンジ
        ev_values = [ev_by_ebitda, ev_by_sales, ev_dcf]
        ev_mid = sum(ev_values) / len(ev_values)
        ev_low = min(ev_values) * 0.9
        ev_high = max(ev_values) * 1.1
        
        return ValuationResult(
            target_company=target_company,
            dcf=dcf_val,
            multiples=mult_val,
            ev_low=ev_low,
            ev_mid=ev_mid,
            ev_high=ev_high,
            equity_low=ev_low - net_debt,
            equity_mid=ev_mid - net_debt,
            equity_high=ev_high - net_debt,
            net_debt=net_debt,
            methodology_notes=f"EV/EBITDA {multiples['ev_ebitda']}x, DCF(WACC {wacc*100:.1f}%)の加重平均"
        )
    
    def create_pmi_plan(
        self,
        revenue_synergy_items: List[Dict[str, Any]],
        cost_synergy_items: List[Dict[str, Any]]
    ) -> PMIPlan:
        """PMI計画を生成"""
        
        revenue_synergies = [
            SynergyItem(**item) for item in revenue_synergy_items
        ] if revenue_synergy_items else []
        
        cost_synergies = [
            SynergyItem(**item) for item in cost_synergy_items
        ] if cost_synergy_items else []
        
        total_synergy = (
            sum(s.annual_impact for s in revenue_synergies) +
            sum(s.annual_impact for s in cost_synergies)
        )
        
        prob_weighted = (
            sum(s.annual_impact * s.probability for s in revenue_synergies) +
            sum(s.annual_impact * s.probability for s in cost_synergies)
        )
        
        return PMIPlan(
            revenue_synergies=revenue_synergies,
            cost_synergies=cost_synergies,
            total_synergy_annual=total_synergy,
            probability_weighted_synergy=prob_weighted,
            day_1_actions=[
                "経営方針・ビジョンの共有",
                "組織体制・指揮命令系統の明確化",
                "従業員向けコミュニケーション"
            ],
            day_30_actions=[
                "事業・財務状況の詳細把握",
                "シナジー実現計画の具体化",
                "IT/システム統合計画策定"
            ],
            day_100_actions=[
                "シナジー施策の本格実行",
                "営業・購買の統合効果創出",
                "コスト削減施策の実行"
            ]
        )


def perform_ma_dd(
    target_company: str,
    revenue: float,
    operating_profit: float,
    depreciation: float,
    net_assets: float,
    net_debt: float,
    industry: str = "manufacturing"
) -> Dict[str, Any]:
    """
    M&A DD簡易実行のファサード関数。
    
    Returns:
        Dict containing financial_dd and valuation results
    """
    engine = MADDSupportEngine()
    
    financial_dd = engine.perform_financial_dd(
        target_company=target_company,
        reported_revenue=revenue,
        reported_operating_profit=operating_profit,
        depreciation=depreciation,
        net_assets=net_assets
    )
    
    valuation = engine.perform_valuation(
        target_company=target_company,
        normalized_ebitda=financial_dd.normalized_earnings.normalized_ebitda,
        revenue=revenue,
        net_income=operating_profit * 0.7,
        net_debt=net_debt,
        industry=industry
    )
    
    return {
        "financial_dd": financial_dd,
        "valuation": valuation
    }
