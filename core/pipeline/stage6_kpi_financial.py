"""
Stage 6: KPI & Financial Planning Engine
Generates KPI architecture and financial projections.
"""
from typing import Dict, Any, Optional, List
from core.pipeline.base_engine import DeterministicEngine, EngineConfig
from core.schemas.pipeline_stages import (
    Stage6Output, KPIPlan, KPIDefinition, BalancedScorecard,
    FinancialProjection, YearlyProjection,
    InvestmentPlan, InvestmentItem,
    SensitivityAnalysis, SensitivityScenario
)
from datetime import datetime


class KPIFinancialEngine(DeterministicEngine[Dict[str, Any], Stage6Output]):
    """
    KPI & Financial Planning Engine - Stage 6 of the consulting pipeline.
    
    Generates comprehensive KPI architecture using balanced scorecard
    and creates financial projections with sensitivity analysis.
    """
    
    STAGE_NUMBER = 6
    STAGE_NAME = "KPI & Financial Planning"
    
    # Standard KPI templates by category
    KPI_TEMPLATES = {
        "financial": [
            ("売上高成長率", "revenue_growth", "%", "年間売上高の前年比増減率"),
            ("営業利益率", "operating_margin", "%", "営業利益 ÷ 売上高 × 100"),
            ("ROE", "roe", "%", "当期純利益 ÷ 自己資本 × 100"),
            ("キャッシュフロー", "cash_flow", "百万円", "営業キャッシュフロー"),
        ],
        "customer": [
            ("顧客満足度", "customer_satisfaction", "点", "顧客満足度調査スコア"),
            ("顧客維持率", "customer_retention", "%", "継続顧客数 ÷ 前期顧客数 × 100"),
            ("新規顧客獲得数", "new_customers", "件", "新規獲得顧客数"),
            ("NPS", "nps", "点", "ネットプロモータースコア"),
        ],
        "process": [
            ("生産性", "productivity", "%", "生産性指標の前年比改善率"),
            ("品質スコア", "quality_score", "%", "品質基準達成率"),
            ("リードタイム", "lead_time", "日", "受注から納品までの平均日数"),
            ("業務効率化率", "efficiency", "%", "業務時間削減率"),
        ],
        "learning": [
            ("従業員エンゲージメント", "engagement", "%", "従業員エンゲージメントスコア"),
            ("研修受講率", "training_rate", "%", "計画研修の受講完了率"),
            ("離職率", "turnover_rate", "%", "年間離職率（低いほど良い）"),
            ("イノベーション指標", "innovation", "件", "新規提案・改善件数"),
        ]
    }
    
    async def compute(
        self,
        input_data: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]] = None
    ) -> Stage6Output:
        """
        Generate KPI architecture and financial projections.
        """
        # Extract context
        stage5_output = previous_output or input_data.get("stage5_output", {})
        financial_data = input_data.get("financial_statements", {})
        
        prioritized_actions = stage5_output.get("prioritized_actions", [])
        milestones = stage5_output.get("milestones", [])
        
        # Generate KPI plan
        kpi_plan = self._generate_kpi_plan(prioritized_actions)
        
        # Generate financial projections
        financial_projection = self._generate_financial_projection(
            financial_data, prioritized_actions
        )
        
        # Generate investment plan
        investment_plan = self._generate_investment_plan(prioritized_actions)
        
        # Generate sensitivity analysis
        sensitivity = self._generate_sensitivity_analysis(financial_projection)
        
        return Stage6Output(
            kpi_plan=kpi_plan,
            financial_projection=financial_projection,
            investment_plan=investment_plan,
            sensitivity_analysis=sensitivity,
            confidence_score=0.85
        )
    
    def _generate_kpi_plan(
        self,
        actions: List[Dict]
    ) -> KPIPlan:
        """Generate comprehensive KPI plan."""
        current_year = datetime.now().year
        
        strategic_kpis = []
        operational_kpis = []
        
        # Generate strategic KPIs (top-level)
        for category, templates in self.KPI_TEMPLATES.items():
            for name, key, unit, definition in templates[:2]:
                # Generate targets for 3 years
                base_target = 5 if "成長" in name or "率" in name else 100
                targets = {
                    current_year + 1: base_target * 1.0,
                    current_year + 2: base_target * 1.1,
                    current_year + 3: base_target * 1.2
                }
                
                kpi = KPIDefinition(
                    id=f"kpi_{key}",
                    name=key,
                    name_ja=name,
                    category=category,
                    definition=definition,
                    calculation_method=definition,
                    unit=unit,
                    targets=targets,
                    data_source="財務システム" if category == "financial" else "業務システム",
                    owner="経営企画部" if category == "financial" else f"{category}担当部門",
                    update_frequency="月次" if category in ["financial", "process"] else "四半期"
                )
                strategic_kpis.append(kpi)
        
        # Generate operational KPIs (action-specific)
        for i, action in enumerate(actions[:5]):
            action_text = action.get("action", "") if isinstance(action, dict) else str(action)
            kpi = KPIDefinition(
                id=f"kpi_operational_{i+1}",
                name=f"action_kpi_{i+1}",
                name_ja=f"{action_text[:20]}進捗率",
                category="process",
                definition=f"{action_text}の実行進捗",
                calculation_method="完了タスク数 ÷ 計画タスク数 × 100",
                unit="%",
                targets={
                    current_year + 1: 100
                },
                data_source="プロジェクト管理ツール",
                owner=action.get("owner", "担当者") if isinstance(action, dict) else "担当者",
                update_frequency="週次"
            )
            operational_kpis.append(kpi)
        
        # Create balanced scorecard structure
        scorecard = BalancedScorecard(
            financial_kpis=[k.id for k in strategic_kpis if k.category == "financial"],
            customer_kpis=[k.id for k in strategic_kpis if k.category == "customer"],
            process_kpis=[k.id for k in strategic_kpis if k.category == "process"],
            learning_kpis=[k.id for k in strategic_kpis if k.category == "learning"],
            strategic_themes=["収益性向上", "顧客価値創造", "業務効率化", "組織能力強化"]
        )
        
        return KPIPlan(
            strategic_kpis=strategic_kpis,
            operational_kpis=operational_kpis,
            balanced_scorecard=scorecard
        )
    
    def _generate_financial_projection(
        self,
        financial_data: Dict,
        actions: List[Dict]
    ) -> FinancialProjection:
        """Generate financial projections."""
        current_year = datetime.now().year
        
        # Get base values from financial data
        base_revenue = financial_data.get("revenue", {}).get(str(current_year), 1000)
        base_cost = financial_data.get("cost_of_goods_sold", {}).get(str(current_year), 700)
        base_profit = base_revenue - base_cost
        
        # Estimate impact from actions
        total_impact = sum(
            a.get("impact", 0.5) if isinstance(a, dict) else 0.5 
            for a in actions[:5]
        ) / 5
        
        growth_rate = 0.03 + (total_impact * 0.05)  # 3% base + action impact
        
        # Generate projections
        revenue_projection = []
        cost_projection = []
        profit_projection = []
        cash_flow_projection = []
        
        for i in range(1, 4):  # 3 years
            year = current_year + i
            growth_factor = (1 + growth_rate) ** i
            
            revenue_projection.append(YearlyProjection(
                year=year,
                baseline=base_revenue * growth_factor,
                optimistic=base_revenue * growth_factor * 1.1,
                pessimistic=base_revenue * growth_factor * 0.9,
                key_drivers=["市場成長", "シェア拡大", "価格戦略"],
                assumptions=["市場成長率2%", "シェア維持"]
            ))
            
            cost_projection.append(YearlyProjection(
                year=year,
                baseline=base_cost * growth_factor * 0.98,  # Slight efficiency gain
                optimistic=base_cost * growth_factor * 0.95,
                pessimistic=base_cost * growth_factor * 1.02,
                key_drivers=["コスト削減施策", "原材料価格"],
                assumptions=["インフレ率1%", "効率化2%"]
            ))
            
            profit_proj = (base_revenue * growth_factor) - (base_cost * growth_factor * 0.98)
            profit_projection.append(YearlyProjection(
                year=year,
                baseline=profit_proj,
                optimistic=profit_proj * 1.15,
                pessimistic=profit_proj * 0.85,
                key_drivers=["売上成長", "コスト管理"],
                assumptions=["マージン改善"]
            ))
            
            cash_flow_projection.append(YearlyProjection(
                year=year,
                baseline=profit_proj * 0.8,  # Operating cash flow
                optimistic=profit_proj * 0.9,
                pessimistic=profit_proj * 0.7,
                key_drivers=["運転資本管理", "設備投資"],
                assumptions=["運転資本効率維持"]
            ))
        
        return FinancialProjection(
            projection_years=3,
            base_year=current_year,
            revenue_projection=revenue_projection,
            cost_projection=cost_projection,
            profit_projection=profit_projection,
            cash_flow_projection=cash_flow_projection,
            key_assumptions=[
                "市場成長率: 年2%",
                "価格競争力の維持",
                "コスト効率化: 年2%改善",
                "為替レート: 安定"
            ],
            sensitivity_factors=["売上高", "原材料費", "人件費", "為替"]
        )
    
    def _generate_investment_plan(
        self,
        actions: List[Dict]
    ) -> InvestmentPlan:
        """Generate investment plan."""
        investments = []
        total = 0
        current_year = datetime.now().year
        
        investment_categories = [
            ("システム投資", "IT", 50),
            ("人材育成投資", "HR", 30),
            ("設備投資", "Operations", 40),
            ("マーケティング投資", "Marketing", 20)
        ]
        
        for i, (name, category, base_amount) in enumerate(investment_categories):
            amount = base_amount * (1.2 if i < 2 else 1.0)  # First two get more
            total += amount
            
            investments.append(InvestmentItem(
                id=f"inv_{i+1}",
                name=name,
                category=category,
                amount=amount,
                timing=f"Year {i // 2 + 1}",
                expected_roi=15 + (i * 5),  # 15-30%
                payback_period=f"{18 + (i * 6)}ヶ月"
            ))
        
        return InvestmentPlan(
            total_investment=total,
            investments=investments,
            funding_sources=[
                {"source": "自己資金", "amount": total * 0.6},
                {"source": "借入", "amount": total * 0.3},
                {"source": "補助金", "amount": total * 0.1}
            ],
            investment_timeline={
                current_year + 1: total * 0.5,
                current_year + 2: total * 0.35,
                current_year + 3: total * 0.15
            }
        )
    
    def _generate_sensitivity_analysis(
        self,
        projection: FinancialProjection
    ) -> SensitivityAnalysis:
        """Generate sensitivity analysis."""
        base_profit = projection.profit_projection[0].baseline
        
        scenarios = [
            SensitivityScenario(
                name="売上10%減少",
                description="市場縮小または競争激化により売上が10%減少",
                variable_changes={"revenue": -0.10},
                impact_on_profit=base_profit * -0.25,
                impact_on_cash=base_profit * -0.20
            ),
            SensitivityScenario(
                name="原材料費15%上昇",
                description="サプライチェーン問題により原材料費が上昇",
                variable_changes={"material_cost": 0.15},
                impact_on_profit=base_profit * -0.15,
                impact_on_cash=base_profit * -0.12
            ),
            SensitivityScenario(
                name="人件費10%上昇",
                description="人材確保のための賃上げ",
                variable_changes={"labor_cost": 0.10},
                impact_on_profit=base_profit * -0.10,
                impact_on_cash=base_profit * -0.08
            ),
            SensitivityScenario(
                name="売上5%増加 & コスト3%削減",
                description="施策が順調に進んだ場合",
                variable_changes={"revenue": 0.05, "cost": -0.03},
                impact_on_profit=base_profit * 0.20,
                impact_on_cash=base_profit * 0.18
            )
        ]
        
        return SensitivityAnalysis(
            scenarios=scenarios,
            critical_variables=["売上高", "原材料費", "人件費"],
            breakeven_thresholds={
                "revenue_decline": -0.15,
                "cost_increase": 0.20
            }
        )


# Factory function
def create_kpi_financial_engine(config: Optional[EngineConfig] = None) -> KPIFinancialEngine:
    """Create and return a KPI Financial Engine instance."""
    return KPIFinancialEngine(config)
