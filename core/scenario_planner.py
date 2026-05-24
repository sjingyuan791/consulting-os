"""
Scenario Planning Engine for SME Strategy.
Provides Best/Base/Worst case analysis with probability-weighted outcomes.
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ScenarioType(str, Enum):
    BEST = "best"
    BASE = "base"
    WORST = "worst"


class ScenarioAssumption(BaseModel):
    """1つのシナリオ前提条件"""
    variable: str = Field(..., description="変数名（例：売上成長率）")
    base_value: float = Field(..., description="現在値/基準値")
    scenario_value: float = Field(..., description="シナリオでの値")
    rationale: str = Field(default="", description="この前提の根拠")
    source: str = Field(default="", description="データ出典")


class ScenarioCase(BaseModel):
    """1つのシナリオケース"""
    scenario_type: ScenarioType
    name: str = Field(..., description="シナリオ名（例：楽観シナリオ）")
    description: str = Field(default="", description="シナリオの説明")
    probability: float = Field(
        default=0.33, 
        ge=0.0, 
        le=1.0, 
        description="発生確率"
    )
    
    # 主要前提条件
    revenue_growth_rate: float = Field(..., description="売上成長率")
    cost_change_rate: float = Field(default=0.0, description="コスト変動率")
    investment_amount: float = Field(default=0.0, description="投資額（百万円）")
    
    # 予測結果
    projected_revenue: float = Field(default=0.0, description="予測売上高")
    projected_profit: float = Field(default=0.0, description="予測利益")
    projected_roa: float = Field(default=0.0, description="予測ROA")
    
    # 詳細前提条件
    assumptions: List[ScenarioAssumption] = Field(default=[])
    
    # リスク要因
    key_risks: List[str] = Field(default=[], description="主要リスク要因")
    key_opportunities: List[str] = Field(default=[], description="主要機会")


class ScenarioAnalysis(BaseModel):
    """シナリオプランニング完全結果"""
    base_year: int = Field(..., description="基準年度")
    target_year: int = Field(..., description="目標年度")
    
    # 3シナリオ
    best_case: ScenarioCase
    base_case: ScenarioCase
    worst_case: ScenarioCase
    
    # 統合分析
    expected_value_revenue: float = Field(
        default=0.0, 
        description="確率加重期待売上高"
    )
    expected_value_profit: float = Field(
        default=0.0, 
        description="確率加重期待利益"
    )
    risk_adjusted_roi: float = Field(
        default=0.0, 
        description="リスク調整済みROI"
    )
    
    # 感度分析
    sensitivity_factors: Dict[str, float] = Field(
        default={}, 
        description="主要変数の感度（1%変動あたりの利益影響）"
    )
    
    # 推奨事項
    strategic_implications: List[str] = Field(
        default=[], 
        description="戦略的含意"
    )
    
    def get_all_cases(self) -> List[ScenarioCase]:
        """全シナリオをリストで返す"""
        return [self.best_case, self.base_case, self.worst_case]


class ScenarioPlanner:
    """シナリオプランニングエンジン"""
    
    # 業界別デフォルトシナリオパラメータ
    SCENARIO_PARAMS = {
        "manufacturing": {
            "best": {"revenue_growth": 0.15, "cost_change": -0.03},
            "base": {"revenue_growth": 0.05, "cost_change": 0.02},
            "worst": {"revenue_growth": -0.05, "cost_change": 0.05}
        },
        "retail": {
            "best": {"revenue_growth": 0.12, "cost_change": -0.02},
            "base": {"revenue_growth": 0.03, "cost_change": 0.02},
            "worst": {"revenue_growth": -0.08, "cost_change": 0.04}
        },
        "construction": {
            "best": {"revenue_growth": 0.10, "cost_change": -0.02},
            "base": {"revenue_growth": 0.02, "cost_change": 0.03},
            "worst": {"revenue_growth": -0.10, "cost_change": 0.06}
        },
        "services": {
            "best": {"revenue_growth": 0.20, "cost_change": -0.05},
            "base": {"revenue_growth": 0.08, "cost_change": 0.02},
            "worst": {"revenue_growth": -0.03, "cost_change": 0.05}
        },
        "it": {
            "best": {"revenue_growth": 0.30, "cost_change": -0.05},
            "base": {"revenue_growth": 0.12, "cost_change": 0.03},
            "worst": {"revenue_growth": 0.0, "cost_change": 0.08}
        },
        "wholesale": {
            "best": {"revenue_growth": 0.10, "cost_change": -0.02},
            "base": {"revenue_growth": 0.03, "cost_change": 0.02},
            "worst": {"revenue_growth": -0.07, "cost_change": 0.04}
        }
    }
    
    def __init__(self, industry: str = "manufacturing"):
        self.industry = industry.lower()
        self.params = self.SCENARIO_PARAMS.get(
            self.industry, 
            self.SCENARIO_PARAMS["manufacturing"]
        )
    
    def generate_scenarios(
        self,
        base_revenue: float,
        base_cost: float,
        base_assets: float,
        base_year: int,
        target_year: int,
        custom_assumptions: Optional[Dict] = None
    ) -> ScenarioAnalysis:
        """
        3シナリオを生成。
        
        Args:
            base_revenue: 基準売上高（百万円）
            base_cost: 基準コスト（百万円）
            base_assets: 基準総資産（百万円）
            base_year: 基準年度
            target_year: 目標年度
            custom_assumptions: カスタム前提条件
        
        Returns:
            ScenarioAnalysis: 完全なシナリオ分析結果
        """
        years = target_year - base_year
        
        # カスタム前提条件でオーバーライド
        params = self.params.copy()
        if custom_assumptions:
            for scenario in ["best", "base", "worst"]:
                if scenario in custom_assumptions:
                    params[scenario].update(custom_assumptions[scenario])
        
        # Best Case
        best_growth = params["best"]["revenue_growth"]
        best_cost_change = params["best"]["cost_change"]
        best_revenue = base_revenue * ((1 + best_growth) ** years)
        best_cost = base_cost * ((1 + best_cost_change) ** years)
        best_profit = best_revenue - best_cost
        best_roa = best_profit / base_assets if base_assets > 0 else 0
        
        best_case = ScenarioCase(
            scenario_type=ScenarioType.BEST,
            name="楽観シナリオ",
            description=f"市場拡大と効率化が進行し、年率{best_growth*100:.0f}%成長を達成",
            probability=0.20,
            revenue_growth_rate=best_growth,
            cost_change_rate=best_cost_change,
            projected_revenue=best_revenue,
            projected_profit=best_profit,
            projected_roa=best_roa,
            key_opportunities=["市場シェア拡大", "新規顧客獲得", "価格引き上げ余地"],
            assumptions=[
                ScenarioAssumption(
                    variable="売上成長率",
                    base_value=0.0,
                    scenario_value=best_growth,
                    rationale=f"{self.industry}業界の上位25%企業の成長率",
                    source="中小企業庁調査2024年版"
                )
            ]
        )
        
        # Base Case
        base_growth = params["base"]["revenue_growth"]
        base_cost_change = params["base"]["cost_change"]
        proj_revenue = base_revenue * ((1 + base_growth) ** years)
        proj_cost = base_cost * ((1 + base_cost_change) ** years)
        proj_profit = proj_revenue - proj_cost
        proj_roa = proj_profit / base_assets if base_assets > 0 else 0
        
        base_case_obj = ScenarioCase(
            scenario_type=ScenarioType.BASE,
            name="基本シナリオ",
            description=f"現状トレンドが継続し、年率{base_growth*100:.0f}%成長",
            probability=0.50,
            revenue_growth_rate=base_growth,
            cost_change_rate=base_cost_change,
            projected_revenue=proj_revenue,
            projected_profit=proj_profit,
            projected_roa=proj_roa,
            assumptions=[
                ScenarioAssumption(
                    variable="売上成長率",
                    base_value=0.0,
                    scenario_value=base_growth,
                    rationale=f"{self.industry}業界の中央値成長率",
                    source="中小企業庁調査2024年版"
                )
            ]
        )
        
        # Worst Case
        worst_growth = params["worst"]["revenue_growth"]
        worst_cost_change = params["worst"]["cost_change"]
        worst_revenue = base_revenue * ((1 + worst_growth) ** years)
        worst_cost = base_cost * ((1 + worst_cost_change) ** years)
        worst_profit = worst_revenue - worst_cost
        worst_roa = worst_profit / base_assets if base_assets > 0 else 0
        
        worst_case = ScenarioCase(
            scenario_type=ScenarioType.WORST,
            name="悲観シナリオ",
            description=f"市場縮小とコスト上昇により、収益が{abs(worst_growth)*100:.0f}%減少",
            probability=0.30,
            revenue_growth_rate=worst_growth,
            cost_change_rate=worst_cost_change,
            projected_revenue=worst_revenue,
            projected_profit=worst_profit,
            projected_roa=worst_roa,
            key_risks=["市場縮小", "競合激化", "コスト上昇", "人材流出"],
            assumptions=[
                ScenarioAssumption(
                    variable="売上成長率",
                    base_value=0.0,
                    scenario_value=worst_growth,
                    rationale="景気後退時の下位25%企業の動向",
                    source="中小企業庁調査2024年版"
                )
            ]
        )
        
        # 期待値計算
        expected_revenue = (
            best_case.probability * best_revenue +
            base_case_obj.probability * proj_revenue +
            worst_case.probability * worst_revenue
        )
        expected_profit = (
            best_case.probability * best_profit +
            base_case_obj.probability * proj_profit +
            worst_case.probability * worst_profit
        )
        
        # 感度分析（売上1%変動あたりの利益影響）
        margin = (proj_revenue - proj_cost) / proj_revenue if proj_revenue > 0 else 0
        sensitivity_factors = {
            "売上高": proj_revenue * 0.01 * margin,  # 1%売上変動の利益影響
            "原価率": -proj_cost * 0.01,  # 1%原価上昇の利益影響
            "販管費": -base_cost * 0.1 * 0.01  # 1%販管費変動の影響
        }
        
        # 戦略的含意
        implications = self._generate_implications(
            best_profit, proj_profit, worst_profit, expected_profit
        )
        
        return ScenarioAnalysis(
            base_year=base_year,
            target_year=target_year,
            best_case=best_case,
            base_case=base_case_obj,
            worst_case=worst_case,
            expected_value_revenue=expected_revenue,
            expected_value_profit=expected_profit,
            risk_adjusted_roi=(expected_profit / base_assets * 100) if base_assets > 0 else 0,
            sensitivity_factors=sensitivity_factors,
            strategic_implications=implications
        )
    
    def _generate_implications(
        self, 
        best_profit: float, 
        base_profit: float, 
        worst_profit: float,
        expected_profit: float
    ) -> List[str]:
        """シナリオ結果から戦略的含意を導出"""
        implications = []
        
        # 利益の変動幅分析
        profit_range = best_profit - worst_profit
        if profit_range > base_profit * 2:
            implications.append(
                "【リスク警告】シナリオ間の利益変動が大きく、事業リスクが高い。"
                "リスクヘッジ策の検討を推奨。"
            )
        
        # 最悪ケースの深刻度
        if worst_profit < 0:
            implications.append(
                "【重要】悲観シナリオでは赤字となる可能性あり。"
                "コスト構造の見直しまたは固定費削減策が必要。"
            )
        
        # 期待値の評価
        if expected_profit > base_profit:
            implications.append(
                "期待利益は基本シナリオを上回っており、"
                "適度なリスクテイクは合理的。"
            )
        else:
            implications.append(
                "期待利益が基本シナリオを下回っており、"
                "保守的な戦略を推奨。"
            )
        
        return implications


def run_scenario_analysis(
    base_revenue: float,
    base_cost: float,
    base_assets: float,
    industry: str = "manufacturing",
    base_year: int = 2024,
    target_year: int = 2027
) -> ScenarioAnalysis:
    """
    シナリオ分析を実行するファサード関数。
    
    Example:
        >>> result = run_scenario_analysis(1000, 800, 500, "manufacturing", 2024, 2027)
        >>> print(result.expected_value_profit)
    """
    planner = ScenarioPlanner(industry)
    return planner.generate_scenarios(
        base_revenue=base_revenue,
        base_cost=base_cost,
        base_assets=base_assets,
        base_year=base_year,
        target_year=target_year
    )
