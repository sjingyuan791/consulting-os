"""
Owner Compensation Analysis for SME.
Analyzes executive compensation levels relative to industry norms
and calculates adjusted profitability metrics.

中小企業オーナー企業向け役員報酬分析モジュール。
役員報酬の適正水準分析、実質利益算出、業界比較を提供。
"""
from typing import Dict, Optional, List
from pydantic import BaseModel, Field
from core.industry_benchmarks import get_benchmark, INDUSTRY_NAMES_JA


class CompensationMetrics(BaseModel):
    """役員報酬メトリクス"""
    total_executive_compensation: float = Field(..., description="役員報酬総額（百万円）")
    number_of_executives: int = Field(default=1, description="役員数")
    average_compensation: float = Field(default=0.0, description="役員1人あたり平均報酬")
    compensation_to_revenue_ratio: float = Field(default=0.0, description="売上高に対する役員報酬率")


class AdjustedProfitability(BaseModel):
    """報酬調整後の収益性指標"""
    reported_operating_profit: float = Field(..., description="計上営業利益")
    adjusted_operating_profit: float = Field(..., description="調整後営業利益（適正報酬ベース）")
    adjustment_amount: float = Field(..., description="役員報酬調整額")
    
    reported_operating_margin: float = Field(default=0.0)
    adjusted_operating_margin: float = Field(default=0.0)
    
    explanation: str = Field(default="", description="調整の説明")


class IndustryComparison(BaseModel):
    """業界比較結果"""
    industry_name: str
    industry_avg_compensation_ratio: float
    company_compensation_ratio: float
    deviation_percent: float
    assessment: str  # "適正", "過大", "過少"
    source: str


class OwnerCompensationAnalysis(BaseModel):
    """オーナー報酬分析完全結果"""
    company_name: Optional[str] = None
    analysis_year: int
    
    # 基本メトリクス
    metrics: CompensationMetrics
    
    # 収益性調整
    adjusted_profitability: AdjustedProfitability
    
    # 業界比較
    industry_comparison: IndustryComparison
    
    # 適正報酬の推定
    estimated_fair_compensation: float = Field(
        default=0.0, 
        description="業界水準に基づく適正役員報酬（推定）"
    )
    
    # 推奨事項
    recommendations: List[str] = Field(default=[])
    
    # 銀行目線での評価（融資審査観点）
    banker_view: str = Field(
        default="", 
        description="金融機関視点での評価コメント"
    )


class OwnerCompensationAnalyzer:
    """オーナー報酬分析エンジン"""
    
    def __init__(self, industry: str = "manufacturing", size: str = "medium"):
        self.industry = industry.lower()
        self.size = size.lower()
        self._load_benchmarks()
    
    def _load_benchmarks(self):
        """業界ベンチマークをロード"""
        benchmark = get_benchmark(self.industry, self.size)
        self.industry_comp_ratio = benchmark.owner_compensation_ratio
        self.source = benchmark.source
    
    def analyze(
        self,
        revenue: float,
        operating_profit: float,
        executive_compensation: float,
        number_of_executives: int = 1,
        analysis_year: int = 2024,
        company_name: Optional[str] = None
    ) -> OwnerCompensationAnalysis:
        """
        オーナー報酬分析を実行。
        
        Args:
            revenue: 売上高（百万円）
            operating_profit: 営業利益（百万円）
            executive_compensation: 役員報酬総額（百万円）
            number_of_executives: 役員数
            analysis_year: 分析対象年度
            company_name: 企業名（オプション）
        
        Returns:
            OwnerCompensationAnalysis: 完全な分析結果
        """
        # 基本メトリクス計算
        comp_ratio = executive_compensation / revenue if revenue > 0 else 0
        avg_comp = executive_compensation / number_of_executives if number_of_executives > 0 else 0
        
        metrics = CompensationMetrics(
            total_executive_compensation=executive_compensation,
            number_of_executives=number_of_executives,
            average_compensation=avg_comp,
            compensation_to_revenue_ratio=comp_ratio
        )
        
        # 適正報酬の推定（業界平均ベース）
        estimated_fair_comp = revenue * self.industry_comp_ratio
        adjustment_amount = executive_compensation - estimated_fair_comp
        
        # 調整後収益性
        adjusted_op = operating_profit + adjustment_amount
        reported_margin = operating_profit / revenue if revenue > 0 else 0
        adjusted_margin = adjusted_op / revenue if revenue > 0 else 0
        
        # 調整説明文生成
        if adjustment_amount > 0:
            explanation = (
                f"役員報酬が業界平均より{adjustment_amount:.1f}百万円高いため、"
                f"調整後営業利益は{adjusted_op:.1f}百万円となります。"
                "【計算】調整後利益 = 営業利益 + (実際報酬 - 適正報酬)"
            )
        elif adjustment_amount < 0:
            explanation = (
                f"役員報酬が業界平均より{abs(adjustment_amount):.1f}百万円低いです。"
                "オーナーの貢献が利益に含まれている可能性があります。"
            )
        else:
            explanation = "役員報酬は業界平均とほぼ同水準です。"
        
        adjusted_profitability = AdjustedProfitability(
            reported_operating_profit=operating_profit,
            adjusted_operating_profit=adjusted_op,
            adjustment_amount=adjustment_amount,
            reported_operating_margin=reported_margin,
            adjusted_operating_margin=adjusted_margin,
            explanation=explanation
        )
        
        # 業界比較
        deviation = (comp_ratio - self.industry_comp_ratio) / self.industry_comp_ratio * 100 if self.industry_comp_ratio > 0 else 0
        
        if deviation > 30:
            assessment = "過大"
        elif deviation < -30:
            assessment = "過少"
        else:
            assessment = "適正"
        
        industry_name = INDUSTRY_NAMES_JA.get(self.industry, self.industry)
        
        industry_comparison = IndustryComparison(
            industry_name=industry_name,
            industry_avg_compensation_ratio=self.industry_comp_ratio,
            company_compensation_ratio=comp_ratio,
            deviation_percent=deviation,
            assessment=assessment,
            source=self.source
        )
        
        # 推奨事項
        recommendations = self._generate_recommendations(
            assessment, adjustment_amount, avg_comp, adjusted_margin
        )
        
        # 銀行目線評価
        banker_view = self._generate_banker_view(
            adjusted_margin, assessment, adjustment_amount
        )
        
        return OwnerCompensationAnalysis(
            company_name=company_name,
            analysis_year=analysis_year,
            metrics=metrics,
            adjusted_profitability=adjusted_profitability,
            industry_comparison=industry_comparison,
            estimated_fair_compensation=estimated_fair_comp,
            recommendations=recommendations,
            banker_view=banker_view
        )
    
    def _generate_recommendations(
        self, 
        assessment: str,
        adjustment_amount: float,
        avg_compensation: float,
        adjusted_margin: float
    ) -> List[str]:
        """推奨事項を生成"""
        recs = []
        
        if assessment == "過大":
            recs.append(
                f"【報酬見直し検討】役員報酬が業界水準を大幅に上回っています。"
                f"融資審査では{adjustment_amount:.1f}百万円の調整が加えられる可能性があります。"
            )
        elif assessment == "過少":
            recs.append(
                "【報酬増額検討】役員報酬が業界水準を下回っています。"
                "適正報酬への増額により、節税効果が得られる可能性があります。"
            )
        
        if adjusted_margin < 0.03:
            recs.append(
                "【収益性改善必要】調整後営業利益率が3%未満です。"
                "本業の収益力強化が最優先課題です。"
            )
        
        if avg_compensation > 50:  # 5000万円以上
            recs.append(
                "【税務リスク】役員報酬が高水準のため、"
                "税務調査で過大役員報酬として否認されるリスクがあります。"
            )
        
        return recs
    
    def _generate_banker_view(
        self,
        adjusted_margin: float,
        assessment: str,
        adjustment_amount: float
    ) -> str:
        """金融機関視点での評価コメント"""
        comments = []
        
        if assessment == "過大":
            comments.append(
                f"融資審査において、役員報酬{abs(adjustment_amount):.1f}百万円を"
                "実質利益として加算評価する可能性があります。"
            )
        
        if adjusted_margin >= 0.05:
            comments.append("調整後収益性は良好であり、返済能力に問題ありません。")
        elif adjusted_margin >= 0.02:
            comments.append("調整後収益性は許容範囲ですが、改善の余地があります。")
        else:
            comments.append("調整後でも収益性が低く、融資審査では慎重な評価となります。")
        
        return " ".join(comments)


def analyze_owner_compensation(
    revenue: float,
    operating_profit: float,
    executive_compensation: float,
    industry: str = "manufacturing",
    size: str = "medium",
    number_of_executives: int = 1,
    analysis_year: int = 2024
) -> OwnerCompensationAnalysis:
    """
    オーナー報酬分析のファサード関数。
    
    Example:
        >>> result = analyze_owner_compensation(
        ...     revenue=500,
        ...     operating_profit=20,
        ...     executive_compensation=40,
        ...     industry="manufacturing"
        ... )
        >>> print(result.industry_comparison.assessment)
        "過大"
    """
    analyzer = OwnerCompensationAnalyzer(industry, size)
    return analyzer.analyze(
        revenue=revenue,
        operating_profit=operating_profit,
        executive_compensation=executive_compensation,
        number_of_executives=number_of_executives,
        analysis_year=analysis_year
    )
