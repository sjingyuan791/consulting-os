"""
Initiative-Based Financial Impact Model.
施策別インパクトモデル - 実務レベルの財務シミュレーション

特徴:
1. 施策タイプ別の計算ロジック（売上/コスト/投資）
2. 根拠の透明性（計算過程を全て記録）
3. 人間レビューポイント設計
4. 手動オーバーライド機能
"""
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from dataclasses import dataclass
from datetime import date
import math


# ==========================================
# 施策タイプ定義
# ==========================================

class InitiativeType(str, Enum):
    """施策タイプ"""
    SALES_PRICE = "sales_price"        # 単価向上
    SALES_VOLUME = "sales_volume"      # 数量拡大
    SALES_MIX = "sales_mix"            # ミックス改善
    NEW_CUSTOMER = "new_customer"      # 新規顧客獲得
    RETENTION = "retention"            # 既存顧客維持
    COST_FIXED = "cost_fixed"          # 固定費削減
    COST_VARIABLE = "cost_variable"    # 変動費削減
    INVESTMENT = "investment"          # 設備/システム投資
    WORKING_CAPITAL = "working_capital" # 運転資本改善
    OTHER = "other"                    # その他


class ConfidenceLevel(str, Enum):
    """確度レベル"""
    HIGH = "high"       # 90%+ 実績あり
    MEDIUM = "medium"   # 60-90% 根拠あり
    LOW = "low"         # 30-60% 推定
    UNCERTAIN = "uncertain"  # <30% 希望的観測


# ==========================================
# 施策モデル
# ==========================================

class InitiativeInput(BaseModel):
    """施策入力（人間が設定する部分）"""
    id: str
    name: str
    description: str
    initiative_type: InitiativeType
    
    # 売上施策パラメータ
    target_customers: int = Field(default=0, description="対象顧客数")
    conversion_rate: float = Field(default=0.0, ge=0, le=1, description="成約率 0-1")
    unit_price: float = Field(default=0.0, description="単価（円）")
    units_per_customer: float = Field(default=1.0, description="顧客あたり数量")
    margin_rate: float = Field(default=0.0, ge=0, le=1, description="粗利率 0-1")
    
    # コスト施策パラメータ
    current_cost: float = Field(default=0.0, description="現在コスト（円/年）")
    reduction_rate: float = Field(default=0.0, ge=0, le=1, description="削減率 0-1")
    
    # 投資施策パラメータ
    initial_investment: float = Field(default=0.0, description="初期投資額（円）")
    annual_benefit: float = Field(default=0.0, description="年間効果（円）")
    useful_life_years: int = Field(default=5, ge=1, description="耐用年数")
    
    # 運転資本パラメータ
    days_improvement: int = Field(default=0, description="改善日数（CCC短縮）")
    
    # 共通
    implementation_months: int = Field(default=6, description="効果発現までの月数")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
    
    # 人間によるオーバーライド
    manual_override_amount: Optional[float] = Field(default=None, description="手動上書き金額")
    override_reason: str = Field(default="", description="上書き理由")


class ImpactCalculation(BaseModel):
    """インパクト計算結果"""
    initiative_id: str
    initiative_name: str
    initiative_type: InitiativeType
    
    # 計算結果
    revenue_impact: float = Field(default=0, description="売上インパクト（円/年）")
    gross_profit_impact: float = Field(default=0, description="粗利インパクト（円/年）")
    cost_savings: float = Field(default=0, description="コスト削減額（円/年）")
    operating_profit_impact: float = Field(default=0, description="営業利益インパクト（円/年）")
    investment_required: float = Field(default=0, description="必要投資額（円）")
    
    # 時間軸
    first_year_impact: float = Field(default=0, description="初年度インパクト（部分年）")
    full_year_impact: float = Field(default=0, description="通年インパクト")
    
    # 回収
    payback_months: Optional[int] = Field(default=None, description="投資回収月数")
    roi: Optional[float] = Field(default=None, description="ROI %")
    
    # 確度調整
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    probability_weighted_impact: float = Field(default=0, description="確度調整後インパクト")
    
    # 根拠（透明性）
    calculation_steps: List[str] = Field(default=[], description="計算過程")
    assumptions: List[str] = Field(default=[], description="前提条件")
    risks: List[str] = Field(default=[], description="リスク要因")
    
    # レビューポイント
    human_review_required: bool = Field(default=False)
    review_points: List[str] = Field(default=[], description="人間確認ポイント")
    
    # オーバーライド
    was_overridden: bool = False
    override_reason: str = ""


class ImpactSummary(BaseModel):
    """インパクトサマリー"""
    total_revenue_impact: float = 0
    total_gross_profit_impact: float = 0
    total_cost_savings: float = 0
    total_operating_profit_impact: float = 0
    total_investment_required: float = 0
    
    # 確度別
    high_confidence_impact: float = 0
    medium_confidence_impact: float = 0
    low_confidence_impact: float = 0
    
    # 施策数
    initiative_count: int = 0
    initiatives_requiring_review: int = 0
    
    # ROI
    overall_roi: Optional[float] = None
    overall_payback_months: Optional[int] = None


class ImpactModelResult(BaseModel):
    """インパクトモデル結果"""
    base_revenue: float
    base_operating_profit: float
    calculations: List[ImpactCalculation]
    summary: ImpactSummary
    
    # 予測財務
    projected_revenue: float = 0
    projected_operating_profit: float = 0
    projected_revenue_growth: float = 0
    projected_profit_growth: float = 0
    
    # 注意事項
    warnings: List[str] = []
    assumptions_summary: List[str] = []


# ==========================================
# インパクト計算エンジン
# ==========================================

class InitiativeImpactEngine:
    """施策別インパクト計算エンジン"""
    
    # 確度別の確率ウェイト
    CONFIDENCE_WEIGHTS = {
        ConfidenceLevel.HIGH: 0.90,
        ConfidenceLevel.MEDIUM: 0.70,
        ConfidenceLevel.LOW: 0.45,
        ConfidenceLevel.UNCERTAIN: 0.25,
    }
    
    def __init__(self, base_revenue: float, base_operating_profit: float):
        """
        Args:
            base_revenue: 基準売上高（円）
            base_operating_profit: 基準営業利益（円）
        """
        self.base_revenue = base_revenue
        self.base_operating_profit = base_operating_profit
    
    def calculate_all(
        self,
        initiatives: List[InitiativeInput],
        target_year_months: int = 12
    ) -> ImpactModelResult:
        """
        全施策のインパクトを計算。
        
        Args:
            initiatives: 施策リスト
            target_year_months: 対象期間（月）
        """
        calculations = []
        warnings = []
        assumptions = []
        
        for init in initiatives:
            calc = self._calculate_single(init, target_year_months)
            calculations.append(calc)
            
            if calc.human_review_required:
                warnings.append(f"施策「{init.name}」は人間レビューが必要です")
        
        # サマリー計算
        summary = self._calculate_summary(calculations)
        
        # 予測財務
        projected_revenue = self.base_revenue + summary.total_revenue_impact
        projected_op = self.base_operating_profit + summary.total_operating_profit_impact
        
        # 全体ROI
        if summary.total_investment_required > 0:
            summary.overall_roi = (summary.total_operating_profit_impact / summary.total_investment_required) * 100
            if summary.total_operating_profit_impact > 0:
                summary.overall_payback_months = int(
                    summary.total_investment_required / (summary.total_operating_profit_impact / 12)
                )
        
        return ImpactModelResult(
            base_revenue=self.base_revenue,
            base_operating_profit=self.base_operating_profit,
            calculations=calculations,
            summary=summary,
            projected_revenue=projected_revenue,
            projected_operating_profit=projected_op,
            projected_revenue_growth=(projected_revenue / self.base_revenue - 1) * 100 if self.base_revenue > 0 else 0,
            projected_profit_growth=(projected_op / self.base_operating_profit - 1) * 100 if self.base_operating_profit > 0 else 0,
            warnings=warnings,
            assumptions_summary=assumptions,
        )
    
    def _calculate_single(
        self,
        init: InitiativeInput,
        target_months: int
    ) -> ImpactCalculation:
        """単一施策のインパクト計算"""
        
        calc = ImpactCalculation(
            initiative_id=init.id,
            initiative_name=init.name,
            initiative_type=init.initiative_type,
            confidence=init.confidence,
        )
        
        # 手動オーバーライドチェック
        if init.manual_override_amount is not None:
            calc.operating_profit_impact = init.manual_override_amount
            calc.full_year_impact = init.manual_override_amount
            calc.was_overridden = True
            calc.override_reason = init.override_reason
            calc.calculation_steps.append(f"手動設定値: {init.manual_override_amount:,.0f}円")
            calc.calculation_steps.append(f"理由: {init.override_reason}")
        else:
            # タイプ別計算
            if init.initiative_type in [InitiativeType.SALES_PRICE, InitiativeType.SALES_VOLUME, 
                                         InitiativeType.NEW_CUSTOMER, InitiativeType.RETENTION]:
                self._calc_sales_initiative(init, calc)
            
            elif init.initiative_type in [InitiativeType.COST_FIXED, InitiativeType.COST_VARIABLE]:
                self._calc_cost_initiative(init, calc)
            
            elif init.initiative_type == InitiativeType.INVESTMENT:
                self._calc_investment_initiative(init, calc)
            
            elif init.initiative_type == InitiativeType.WORKING_CAPITAL:
                self._calc_wc_initiative(init, calc)
            
            else:
                calc.review_points.append("施策タイプが不明なため、手動入力が必要です")
                calc.human_review_required = True
        
        # 効果発現期間の調整
        if init.implementation_months > 0 and target_months <= 12:
            effective_months = max(0, target_months - init.implementation_months)
            ratio = effective_months / target_months
            calc.first_year_impact = calc.full_year_impact * ratio
            calc.calculation_steps.append(
                f"初年度調整: {init.implementation_months}ヶ月後から効果発現 → "
                f"年間の{ratio*100:.0f}%が初年度インパクト"
            )
        else:
            calc.first_year_impact = calc.full_year_impact
        
        # 確度調整
        weight = self.CONFIDENCE_WEIGHTS.get(init.confidence, 0.5)
        calc.probability_weighted_impact = calc.operating_profit_impact * weight
        calc.calculation_steps.append(
            f"確度調整: {init.confidence.value} (×{weight:.0%}) → "
            f"{calc.probability_weighted_impact:,.0f}円"
        )
        
        # レビュー判定
        if init.confidence == ConfidenceLevel.UNCERTAIN:
            calc.human_review_required = True
            calc.review_points.append("確度が低い施策です。前提条件を再確認してください。")
        
        if calc.operating_profit_impact > self.base_operating_profit * 0.3:
            calc.human_review_required = True
            calc.review_points.append("インパクトが大きい施策です（営業利益の30%超）。実現可能性を確認してください。")
        
        return calc
    
    def _calc_sales_initiative(self, init: InitiativeInput, calc: ImpactCalculation):
        """売上施策の計算"""
        
        # 売上 = 顧客数 × 成約率 × 単価 × 数量
        revenue = init.target_customers * init.conversion_rate * init.unit_price * init.units_per_customer
        gross_profit = revenue * init.margin_rate
        
        calc.revenue_impact = revenue
        calc.gross_profit_impact = gross_profit
        calc.operating_profit_impact = gross_profit  # 簡略化（販管費増加は考慮せず）
        calc.full_year_impact = gross_profit
        
        # 計算過程を記録
        calc.calculation_steps = [
            f"対象顧客数: {init.target_customers:,}人",
            f"成約率: {init.conversion_rate:.1%}",
            f"単価: {init.unit_price:,.0f}円",
            f"顧客あたり数量: {init.units_per_customer:.1f}",
            f"売上 = {init.target_customers:,} × {init.conversion_rate:.1%} × {init.unit_price:,.0f} × {init.units_per_customer:.1f}",
            f"売上インパクト: {revenue:,.0f}円/年",
            f"粗利率: {init.margin_rate:.1%}",
            f"粗利インパクト: {gross_profit:,.0f}円/年",
        ]
        
        # 前提条件
        calc.assumptions = [
            "成約率は過去実績または業界平均を参考",
            "単価は現行価格を維持と仮定",
            "販管費の増加は考慮していない",
        ]
        
        # リスク
        if init.conversion_rate > 0.3:
            calc.risks.append(f"成約率{init.conversion_rate:.0%}は楽観的な可能性があります")
    
    def _calc_cost_initiative(self, init: InitiativeInput, calc: ImpactCalculation):
        """コスト削減施策の計算"""
        
        savings = init.current_cost * init.reduction_rate
        
        calc.cost_savings = savings
        calc.operating_profit_impact = savings
        calc.full_year_impact = savings
        
        calc.calculation_steps = [
            f"現在コスト: {init.current_cost:,.0f}円/年",
            f"削減率: {init.reduction_rate:.1%}",
            f"削減額 = {init.current_cost:,.0f} × {init.reduction_rate:.1%}",
            f"コスト削減インパクト: {savings:,.0f}円/年",
        ]
        
        calc.assumptions = [
            "削減後もサービス品質は維持と仮定",
            "人員削減の場合、退職金等一時コストは別途考慮",
        ]
        
        if init.reduction_rate > 0.3:
            calc.risks.append(f"削減率{init.reduction_rate:.0%}は達成困難な可能性があります")
            calc.review_points.append("30%超の削減は実現可能性を詳細検討してください")
    
    def _calc_investment_initiative(self, init: InitiativeInput, calc: ImpactCalculation):
        """投資施策の計算"""
        
        calc.investment_required = init.initial_investment
        calc.operating_profit_impact = init.annual_benefit
        calc.full_year_impact = init.annual_benefit
        
        # 減価償却考慮
        annual_depreciation = init.initial_investment / init.useful_life_years
        net_benefit = init.annual_benefit - annual_depreciation
        
        calc.calculation_steps = [
            f"初期投資: {init.initial_investment:,.0f}円",
            f"年間効果: {init.annual_benefit:,.0f}円/年",
            f"耐用年数: {init.useful_life_years}年",
            f"年間減価償却: {annual_depreciation:,.0f}円",
            f"純効果（減価償却後）: {net_benefit:,.0f}円/年",
        ]
        
        # 投資回収期間
        if init.annual_benefit > 0:
            payback = init.initial_investment / init.annual_benefit
            calc.payback_months = int(payback * 12)
            calc.roi = (init.annual_benefit / init.initial_investment) * 100
            calc.calculation_steps.append(f"投資回収期間: {calc.payback_months}ヶ月")
            calc.calculation_steps.append(f"ROI: {calc.roi:.1f}%")
        
        calc.assumptions = [
            "年間効果は安定的に発生すると仮定",
            "追加の運用コストは含まない",
        ]
        
        if calc.payback_months and calc.payback_months > 36:
            calc.risks.append("投資回収が3年超かかります")
            calc.review_points.append("回収期間が長いため、資金繰りへの影響を確認してください")
    
    def _calc_wc_initiative(self, init: InitiativeInput, calc: ImpactCalculation):
        """運転資本改善施策の計算"""
        
        # 日商 × 改善日数 = 運転資本改善額
        daily_sales = self.base_revenue / 365
        wc_improvement = daily_sales * init.days_improvement
        
        # 金利効果（年2%と仮定）
        interest_saving = wc_improvement * 0.02
        
        calc.operating_profit_impact = interest_saving
        calc.full_year_impact = interest_saving
        
        calc.calculation_steps = [
            f"日商: {daily_sales:,.0f}円",
            f"CCC改善日数: {init.days_improvement}日",
            f"運転資本改善額: {wc_improvement:,.0f}円",
            f"金利効果（年2%想定）: {interest_saving:,.0f}円/年",
        ]
        
        calc.assumptions = [
            "金利は年2%と仮定",
            "運転資本改善額は資金繰り改善に直結",
        ]
    
    def _calculate_summary(self, calculations: List[ImpactCalculation]) -> ImpactSummary:
        """サマリー計算"""
        summary = ImpactSummary()
        summary.initiative_count = len(calculations)
        
        for calc in calculations:
            summary.total_revenue_impact += calc.revenue_impact
            summary.total_gross_profit_impact += calc.gross_profit_impact
            summary.total_cost_savings += calc.cost_savings
            summary.total_operating_profit_impact += calc.operating_profit_impact
            summary.total_investment_required += calc.investment_required
            
            if calc.human_review_required:
                summary.initiatives_requiring_review += 1
            
            # 確度別集計
            if calc.confidence == ConfidenceLevel.HIGH:
                summary.high_confidence_impact += calc.operating_profit_impact
            elif calc.confidence == ConfidenceLevel.MEDIUM:
                summary.medium_confidence_impact += calc.operating_profit_impact
            else:
                summary.low_confidence_impact += calc.operating_profit_impact
        
        return summary


# ==========================================
# ファサード関数
# ==========================================

def calculate_initiative_impact(
    base_revenue: float,
    base_operating_profit: float,
    initiatives: List[InitiativeInput],
    target_months: int = 12
) -> ImpactModelResult:
    """
    施策別インパクトを計算。
    
    Example:
        >>> initiatives = [
        ...     InitiativeInput(
        ...         id="1", name="新規顧客開拓",
        ...         initiative_type=InitiativeType.NEW_CUSTOMER,
        ...         target_customers=100, conversion_rate=0.1,
        ...         unit_price=500000, margin_rate=0.3,
        ...         confidence=ConfidenceLevel.MEDIUM
        ...     )
        ... ]
        >>> result = calculate_initiative_impact(1_000_000_000, 50_000_000, initiatives)
    """
    engine = InitiativeImpactEngine(base_revenue, base_operating_profit)
    return engine.calculate_all(initiatives, target_months)


def format_impact_report(result: ImpactModelResult) -> str:
    """インパクトレポートをテキスト形式で出力"""
    lines = [
        "=" * 60,
        "施策別インパクト分析レポート",
        "=" * 60,
        "",
        f"【基準値】",
        f"  売上高: {result.base_revenue:,.0f}円",
        f"  営業利益: {result.base_operating_profit:,.0f}円",
        "",
        f"【予測値】",
        f"  売上高: {result.projected_revenue:,.0f}円 (+{result.projected_revenue_growth:.1f}%)",
        f"  営業利益: {result.projected_operating_profit:,.0f}円 (+{result.projected_profit_growth:.1f}%)",
        "",
        f"【サマリー】",
        f"  施策数: {result.summary.initiative_count}件",
        f"  売上インパクト合計: {result.summary.total_revenue_impact:,.0f}円",
        f"  営業利益インパクト合計: {result.summary.total_operating_profit_impact:,.0f}円",
        f"  必要投資額合計: {result.summary.total_investment_required:,.0f}円",
    ]
    
    if result.summary.overall_roi:
        lines.append(f"  全体ROI: {result.summary.overall_roi:.1f}%")
    if result.summary.overall_payback_months:
        lines.append(f"  投資回収期間: {result.summary.overall_payback_months}ヶ月")
    
    lines.append("")
    lines.append(f"【確度別内訳】")
    lines.append(f"  高確度: {result.summary.high_confidence_impact:,.0f}円")
    lines.append(f"  中確度: {result.summary.medium_confidence_impact:,.0f}円")
    lines.append(f"  低確度: {result.summary.low_confidence_impact:,.0f}円")
    
    lines.append("")
    lines.append("【施策詳細】")
    
    for calc in result.calculations:
        lines.append("")
        lines.append(f"  ■ {calc.initiative_name}")
        lines.append(f"    タイプ: {calc.initiative_type.value}")
        lines.append(f"    営業利益インパクト: {calc.operating_profit_impact:,.0f}円/年")
        lines.append(f"    確度: {calc.confidence.value}")
        
        if calc.human_review_required:
            lines.append(f"    ⚠️ レビュー必要")
            for rp in calc.review_points:
                lines.append(f"      - {rp}")
        
        lines.append("    計算過程:")
        for step in calc.calculation_steps[:5]:
            lines.append(f"      {step}")
    
    if result.warnings:
        lines.append("")
        lines.append("【警告】")
        for w in result.warnings:
            lines.append(f"  ⚠️ {w}")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)
