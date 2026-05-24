"""
Stage 7: Mid-Term Management Plan Generator
Compiles all stage outputs into a comprehensive management plan document.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from core.pipeline.base_engine import DeterministicEngine, EngineConfig
from core.schemas.pipeline_stages import (
    MidTermManagementPlan,
    ExternalAnalysis, InternalAnalysis, RootCauseSection,
    StrategySection, TacticalRoadmapSection, KPIDashboardSection,
    FinancialPlanSection, RiskManagementSection, GovernanceSection,
    Appendix, Stage1Output, Stage2Output, Stage4Output, Stage5Output, Stage6Output
)
import json


class PlanGeneratorEngine(DeterministicEngine[Dict[str, Any], MidTermManagementPlan]):
    """
    Mid-Term Management Plan Generator - Stage 7 of the consulting pipeline.
    
    Compiles outputs from all previous stages into a comprehensive
    mid-term management plan document.
    """
    
    STAGE_NUMBER = 7
    STAGE_NAME = "Mid-Term Plan Generator"
    
    async def compute(
        self,
        input_data: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]] = None
    ) -> MidTermManagementPlan:
        """
        Compile all stage outputs into a management plan.
        """
        # Extract outputs from previous stages
        stage1 = input_data.get("stage1_output", {})
        stage2 = input_data.get("stage2_output", {})
        stage3 = input_data.get("stage3_output", {})
        stage4 = input_data.get("stage4_output", {})
        stage5 = input_data.get("stage5_output", {})
        stage6 = input_data.get("stage6_output", {})
        
        client_id = input_data.get("client_id", "")
        market_data = input_data.get("market_data", {})
        operational_data = input_data.get("operational_data", {})
        
        # Determine plan period
        current_year = datetime.now().year
        plan_period = f"{current_year}-{current_year + 4}"
        
        # Build plan sections
        external_analysis = self._build_external_analysis(market_data)
        internal_analysis = self._build_internal_analysis(stage1, operational_data)
        root_cause_section = self._build_root_cause_section(stage2)
        strategy_section = self._build_strategy_section(stage4)
        roadmap_section = self._build_roadmap_section(stage5)
        kpi_section = self._build_kpi_section(stage6)
        financial_section = self._build_financial_section(stage6)
        risk_section = self._build_risk_section(stage4)
        governance_section = self._build_governance_section()
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            root_cause_section, strategy_section, financial_section
        )
        
        return MidTermManagementPlan(
            client_id=client_id,
            version=1,
            plan_period=plan_period,
            executive_summary=executive_summary,
            external_environment_analysis=external_analysis,
            internal_analysis=internal_analysis,
            root_cause_analysis=root_cause_section,
            strategy_framework=strategy_section,
            tactical_roadmap=roadmap_section,
            kpi_dashboard_plan=kpi_section,
            financial_plan=financial_section,
            risk_management=risk_section,
            implementation_governance=governance_section,
            appendices=[],
            confidence_score=0.85
        )
    
    def _build_external_analysis(self, market_data: Dict) -> ExternalAnalysis:
        """Build external environment analysis section."""
        return ExternalAnalysis(
            market_overview=market_data.get("overview", "市場環境の分析が必要です"),
            industry_trends=market_data.get("trends", [
                "デジタルトランスフォーメーションの加速",
                "サステナビリティへの関心増大",
                "労働力不足の深刻化"
            ]),
            competitive_landscape=market_data.get("competitive", "競合分析が必要です"),
            opportunities=market_data.get("opportunities", [
                "新市場への展開機会",
                "デジタル化による効率化"
            ]),
            threats=market_data.get("threats", [
                "新規参入者の増加",
                "原材料コストの上昇"
            ]),
            pest_analysis={
                "political": ["規制緩和の動向"],
                "economic": ["金利動向", "為替リスク"],
                "social": ["消費者嗜好の変化"],
                "technological": ["AI・自動化技術の進展"]
            }
        )
    
    def _build_internal_analysis(
        self, 
        stage1: Dict,
        operational_data: Dict
    ) -> InternalAnalysis:
        """Build internal analysis section."""
        weak_nodes = stage1.get("weak_financial_nodes", [])
        hypotheses = stage1.get("financial_hypotheses", [])
        
        weaknesses = [h.get("description", "") for h in hypotheses[:3]]
        
        return InternalAnalysis(
            company_overview=operational_data.get("overview", "会社概要"),
            strengths=operational_data.get("strengths", [
                "熟練した人材",
                "安定した顧客基盤"
            ]),
            weaknesses=weaknesses or ["収益性の改善余地", "オペレーション効率化の必要性"],
            core_competencies=operational_data.get("competencies", [
                "高品質な製品・サービス",
                "顧客との長期関係構築力"
            ]),
            resource_assessment={
                "human": "人材リソースの評価が必要",
                "financial": stage1.get("analysis_summary", "財務分析完了"),
                "technological": "技術リソースの評価が必要",
                "organizational": "組織能力の評価が必要"
            }
        )
    
    def _build_root_cause_section(self, stage2: Dict) -> RootCauseSection:
        """Build root cause analysis section."""
        primary = stage2.get("primary_root_cause", {})
        secondary = stage2.get("secondary_causes", [])
        
        primary_issues = [primary.get("description", "根本原因の分析が必要")]
        primary_issues.extend([s.get("description", "") for s in secondary[:2]])
        
        return RootCauseSection(
            primary_issues=primary_issues,
            causal_analysis_summary=stage2.get("analysis_summary", "因果分析サマリー"),
            priority_areas=stage2.get("leverage_points", ["優先領域の特定が必要"])
        )
    
    def _build_strategy_section(self, stage4: Dict) -> StrategySection:
        """Build strategy framework section."""
        corporate = stage4.get("corporate_strategy", {})
        domain = stage4.get("domain_strategies", [])
        functional = stage4.get("functional_strategies", [])
        
        key_strategies = []
        for d in domain[:2]:
            key_strategies.append({
                "name": d.get("domain_name", "事業戦略"),
                "description": d.get("value_proposition", "")
            })
        for f in functional[:3]:
            key_strategies.append({
                "name": f.get("function_name_ja", f.get("function", "")),
                "description": ", ".join(f.get("key_initiatives", [])[:2])
            })
        
        return StrategySection(
            vision_statement=corporate.get("vision", "ビジョンの策定が必要です"),
            mission_statement=corporate.get("mission", "ミッションの策定が必要です"),
            strategic_objectives=corporate.get("long_term_goals", [
                "持続的な収益成長",
                "組織能力の強化",
                "顧客満足度の向上"
            ]),
            key_strategies=key_strategies or [{"name": "戦略", "description": "戦略策定が必要"}]
        )
    
    def _build_roadmap_section(self, stage5: Dict) -> TacticalRoadmapSection:
        """Build tactical roadmap section."""
        actions = stage5.get("prioritized_actions", [])
        milestones = stage5.get("milestones", [])
        phases = stage5.get("implementation_phases", [])
        
        # Split actions by year (simplistic)
        year1 = [a.get("action", "") for a in actions[:4] if a.get("quickwin", False) or a.get("priority_score", 0) > 0.7]
        year2 = [a.get("action", "") for a in actions[4:7]]
        year3 = [a.get("action", "") for a in actions[7:10]]
        
        milestone_dicts = [{"name": m.get("name", ""), "date": m.get("target_date", "")} for m in milestones[:5]]
        
        return TacticalRoadmapSection(
            year1_priorities=year1 or ["1年目の優先施策を策定中"],
            year2_priorities=year2 or ["2年目の施策を策定中"],
            year3_priorities=year3 or ["3年目の施策を策定中"],
            key_milestones=milestone_dicts or [{"name": "マイルストーン策定中", "date": "TBD"}],
            resource_allocation=stage5.get("resource_allocation", {"year1": 0.4, "year2": 0.35, "year3": 0.25})
        )
    
    def _build_kpi_section(self, stage6: Dict) -> KPIDashboardSection:
        """Build KPI dashboard section."""
        kpi_plan = stage6.get("kpi_plan", {})
        strategic_kpis = kpi_plan.get("strategic_kpis", [])
        operational_kpis = kpi_plan.get("operational_kpis", [])
        
        key_metrics = []
        for kpi in strategic_kpis[:5]:
            key_metrics.append({
                "name": kpi.get("name_ja", kpi.get("name", "")),
                "category": kpi.get("category", ""),
                "targets": kpi.get("targets", {}),
                "owner": kpi.get("owner", "")
            })
        
        return KPIDashboardSection(
            key_metrics=key_metrics or [{"name": "KPI策定中", "category": "financial", "targets": {}, "owner": ""}],
            monitoring_frequency="月次",
            review_process="月次経営会議でのレビュー、四半期毎の戦略レビュー会議"
        )
    
    def _build_financial_section(self, stage6: Dict) -> FinancialPlanSection:
        """Build financial plan section."""
        projection = stage6.get("financial_projection", {})
        investment = stage6.get("investment_plan", {})
        
        revenue = projection.get("revenue_projection", [])
        profit = projection.get("profit_projection", [])
        
        revenue_targets = {p.get("year"): p.get("baseline") for p in revenue}
        profit_targets = {p.get("year"): p.get("baseline") for p in profit}
        
        total_investment = investment.get("total_investment", 0)
        
        return FinancialPlanSection(
            revenue_targets=revenue_targets or {2026: 0, 2027: 0, 2028: 0},
            profit_targets=profit_targets or {2026: 0, 2027: 0, 2028: 0},
            investment_summary=f"総投資額: {total_investment:,.0f}百万円" if total_investment else "投資計画策定中",
            funding_requirements=investment.get("funding_notes", "資金調達計画策定中")
        )
    
    def _build_risk_section(self, stage4: Dict) -> RiskManagementSection:
        """Build risk management section."""
        risk_assessment = stage4.get("risk_assessment", {})
        
        key_risks = []
        for risk_type in ["strategic_risks", "operational_risks", "financial_risks"]:
            for risk in risk_assessment.get(risk_type, [])[:2]:
                key_risks.append({
                    "type": risk_type.replace("_risks", ""),
                    "description": risk.get("description", ""),
                    "impact": risk.get("impact", "medium")
                })
        
        return RiskManagementSection(
            key_risks=key_risks or [{"type": "strategic", "description": "リスク評価中", "impact": "medium"}],
            mitigation_strategies=[
                "定期的なリスクレビューの実施",
                "早期警戒指標のモニタリング",
                "コンティンジェンシープランの整備"
            ],
            contingency_plans=[
                "売上減少時の固定費削減計画",
                "主要サプライヤー障害時の代替調達計画"
            ]
        )
    
    def _build_governance_section(self) -> GovernanceSection:
        """Build implementation governance section."""
        return GovernanceSection(
            steering_committee=["CEO", "CFO", "COO", "事業部長"],
            review_cadence="月次定例会議、四半期戦略レビュー",
            reporting_structure="各部門長 → COO → 経営会議",
            escalation_process="リスク発生時は24時間以内にCEOへ報告"
        )
    
    def _generate_executive_summary(
        self,
        root_cause: RootCauseSection,
        strategy: StrategySection,
        financial: FinancialPlanSection
    ) -> str:
        """Generate executive summary."""
        issues = ", ".join(root_cause.primary_issues[:2])
        vision = strategy.vision_statement
        
        summary = f"""本中期経営計画は、{root_cause.priority_areas[0] if root_cause.priority_areas else '経営課題'}への対応を軸に策定しました。

【主要課題】
{issues}

【ビジョン】
{vision}

【戦略の方向性】
{chr(10).join(['- ' + s.get('name', '') + ': ' + s.get('description', '')[:50] for s in strategy.key_strategies[:3]])}

【財務目標】
{financial.investment_summary}

本計画の実行により、持続的な成長と企業価値の向上を目指します。"""
        
        return summary


# Factory function
def create_plan_generator(config: Optional[EngineConfig] = None) -> PlanGeneratorEngine:
    """Create and return a Plan Generator Engine instance."""
    return PlanGeneratorEngine(config)
