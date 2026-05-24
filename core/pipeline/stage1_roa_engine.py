"""
Stage 1: ROA Deductive Engine
Financial analysis using DuPont decomposition to identify weak points.
This is a deterministic engine with optional AI-enhanced insights.
"""
from typing import Dict, Any, Optional, List
from core.pipeline.base_engine import DeterministicEngine, AIEngine, EngineConfig
from core.schemas.pipeline_stages import (
    Stage1Output, ROABreakdown, FinancialNode, FinancialHypothesis
)
from pydantic import BaseModel
import logging


class FinancialStatements(BaseModel):
    """Input financial data structure."""
    years: List[int]
    revenue: Dict[int, float]  # year -> value
    cost_of_goods_sold: Dict[int, float]
    operating_expenses: Dict[int, float]
    net_income: Dict[int, float]
    total_assets: Dict[int, float]
    total_equity: Dict[int, float]
    current_assets: Dict[int, float]
    current_liabilities: Dict[int, float]
    inventory: Dict[int, float]
    accounts_receivable: Dict[int, float]
    fixed_assets: Dict[int, float]


class ROAEngine(DeterministicEngine[Dict[str, Any], Stage1Output]):
    """
    ROA Deductive Engine - Stage 1 of the consulting pipeline.
    
    Performs DuPont analysis to decompose financial performance
    and identify weak points that require investigation.
    """
    
    STAGE_NUMBER = 1
    STAGE_NAME = "ROA Deductive Engine"
    
    def __init__(self, config: Optional[EngineConfig] = None, industry: str = "manufacturing", size: str = "medium"):
        super().__init__(config)
        self.industry = industry
        self.size = size
        self._load_benchmarks()
    
    def _load_benchmarks(self):
        """業界・規模別ベンチマークを動的にロード"""
        try:
            from core.industry_benchmarks import get_benchmark
            benchmark = get_benchmark(self.industry, self.size)
            self.BENCHMARKS = {
                "roa": benchmark.roa,
                "roe": benchmark.roe,
                "profit_margin": benchmark.profit_margin,
                "asset_turnover": benchmark.asset_turnover,
                "gross_margin": benchmark.gross_margin,
                "operating_margin": benchmark.operating_margin,
                "receivables_turnover": benchmark.receivables_turnover,
                "inventory_turnover": benchmark.inventory_turnover,
                "current_ratio": benchmark.current_ratio
            }
            self.benchmark_source = benchmark.source
        except ImportError:
            # フォールバック: 従来のハードコードベンチマーク
            self.BENCHMARKS = {
                "roa": 0.05,
                "roe": 0.10,
                "profit_margin": 0.05,
                "asset_turnover": 1.0,
                "gross_margin": 0.30,
                "operating_margin": 0.10,
                "receivables_turnover": 8.0,
                "inventory_turnover": 6.0,
                "current_ratio": 1.5
            }
            self.benchmark_source = "全業種平均（推定値）"
    
    async def compute(
        self,
        input_data: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]] = None
    ) -> Stage1Output:
        """
        Perform DuPont analysis on financial statements.
        """
        fs = input_data.get("financial_statements", {})
        years = fs.get("years", [])
        
        if not years:
            raise ValueError("No financial data years provided")
        
        latest_year = max(years)
        
        # Calculate core metrics for latest year
        revenue = fs.get("revenue", {}).get(str(latest_year), 0)
        net_income = fs.get("net_income", {}).get(str(latest_year), 0)
        total_assets = fs.get("total_assets", {}).get(str(latest_year), 0)
        total_equity = fs.get("total_equity", {}).get(str(latest_year), 0)
        cogs = fs.get("cost_of_goods_sold", {}).get(str(latest_year), 0)
        op_exp = fs.get("operating_expenses", {}).get(str(latest_year), 0)
        inventory = fs.get("inventory", {}).get(str(latest_year), 0)
        ar = fs.get("accounts_receivable", {}).get(str(latest_year), 0)
        fixed_assets = fs.get("fixed_assets", {}).get(str(latest_year), 0)
        
        # DuPont Decomposition
        profit_margin = self._safe_divide(net_income, revenue)
        asset_turnover = self._safe_divide(revenue, total_assets)
        financial_leverage = self._safe_divide(total_assets, total_equity)
        
        roa = profit_margin * asset_turnover
        roe = roa * financial_leverage
        
        # Sub-metrics
        gross_margin = self._safe_divide(revenue - cogs, revenue)
        operating_income = revenue - cogs - op_exp
        operating_margin = self._safe_divide(operating_income, revenue)
        net_margin = profit_margin
        
        receivables_turnover = self._safe_divide(revenue, ar) if ar > 0 else 0
        inventory_turnover = self._safe_divide(cogs, inventory) if inventory > 0 else 0
        fixed_asset_turnover = self._safe_divide(revenue, fixed_assets) if fixed_assets > 0 else 0
        
        roa_breakdown = ROABreakdown(
            roa=roa,
            roe=roe,
            profit_margin=profit_margin,
            asset_turnover=asset_turnover,
            financial_leverage=financial_leverage,
            gross_margin=gross_margin,
            operating_margin=operating_margin,
            net_margin=net_margin,
            receivables_turnover=receivables_turnover,
            inventory_turnover=inventory_turnover,
            fixed_asset_turnover=fixed_asset_turnover
        )
        
        # Identify weak nodes
        weak_nodes = self._identify_weak_nodes(roa_breakdown)
        
        # Generate hypotheses
        hypotheses = self._generate_hypotheses(weak_nodes, roa_breakdown)
        
        # Calculate year-over-year changes if multiple years available
        yoy_changes = {}
        if len(years) >= 2:
            prev_year = sorted(years)[-2]
            yoy_changes = self._calculate_yoy_changes(fs, latest_year, prev_year)
        
        return Stage1Output(
            analysis_years=years,
            roa_breakdown=roa_breakdown,
            year_over_year_changes=yoy_changes,
            weak_financial_nodes=weak_nodes,
            financial_hypotheses=hypotheses,
            suspected_problem_nodes=[n.metric_name for n in weak_nodes if n.severity in ["critical", "high"]],
            data_sources=["financial_statements"],
            confidence_score=0.85,
            analysis_summary=self._generate_summary(weak_nodes, hypotheses)
        )
    
    def _safe_divide(self, numerator: float, denominator: float) -> float:
        """Safe division to avoid divide by zero."""
        if denominator == 0:
            return 0.0
        return numerator / denominator
    
    def _identify_weak_nodes(self, breakdown: ROABreakdown) -> List[FinancialNode]:
        """Identify metrics that are below benchmarks."""
        weak_nodes = []
        
        metrics_to_check = [
            ("roa", breakdown.roa, "ROA (総資産利益率)"),
            ("roe", breakdown.roe, "ROE (自己資本利益率)"),
            ("profit_margin", breakdown.profit_margin, "売上高純利益率"),
            ("asset_turnover", breakdown.asset_turnover, "総資産回転率"),
            ("gross_margin", breakdown.gross_margin, "売上総利益率"),
            ("operating_margin", breakdown.operating_margin, "営業利益率"),
            ("receivables_turnover", breakdown.receivables_turnover, "売上債権回転率"),
            ("inventory_turnover", breakdown.inventory_turnover, "棚卸資産回転率"),
        ]
        
        for metric_key, value, label in metrics_to_check:
            benchmark = self.BENCHMARKS.get(metric_key, 0)
            if value is None:
                continue
                
            deviation = self._safe_divide(value - benchmark, benchmark) if benchmark != 0 else 0
            
            if deviation < -0.3:  # More than 30% below benchmark
                severity = "critical"
            elif deviation < -0.15:
                severity = "high"
            elif deviation < 0:
                severity = "medium"
            else:
                continue  # Not weak
            
            # Determine trend (would use historical data in production)
            trend = "stable"  # Placeholder
            
            weak_nodes.append(FinancialNode(
                id=metric_key,
                metric_name=label,
                current_value=value,
                benchmark_value=benchmark,
                deviation_percent=deviation * 100,
                severity=severity,
                trend=trend
            ))
        
        return weak_nodes
    
    def _generate_hypotheses(
        self, 
        weak_nodes: List[FinancialNode],
        breakdown: ROABreakdown
    ) -> List[FinancialHypothesis]:
        """Generate hypotheses based on weak nodes."""
        hypotheses = []
        
        # Profitability issues
        if any(n.id in ["gross_margin", "operating_margin", "profit_margin"] for n in weak_nodes):
            hypotheses.append(FinancialHypothesis(
                id="hyp_profitability_1",
                category="profitability",
                description="収益性の低下は、原価構造または価格設定の問題を示唆している可能性があります",
                severity="high",
                evidence=[n.metric_name for n in weak_nodes if n.id in ["gross_margin", "operating_margin"]],
                metrics_affected=["売上総利益率", "営業利益率"],
                suggested_investigation="原価構造の分析、競合他社との価格比較、製品ミックスの検証"
            ))
        
        # Efficiency issues
        if any(n.id in ["asset_turnover", "inventory_turnover", "receivables_turnover"] for n in weak_nodes):
            hypotheses.append(FinancialHypothesis(
                id="hyp_efficiency_1",
                category="efficiency",
                description="資産効率の低下は、過剰な在庫または売掛金回収の遅れを示唆しています",
                severity="high",
                evidence=[n.metric_name for n in weak_nodes if "回転" in n.metric_name],
                metrics_affected=["総資産回転率", "棚卸資産回転率", "売上債権回転率"],
                suggested_investigation="在庫管理プロセスの検証、売掛金年齢分析、与信管理の評価"
            ))
        
        # ROA specific issues
        if any(n.id == "roa" for n in weak_nodes):
            # Determine root cause: margin or turnover?
            margin_weak = any(n.id in ["profit_margin", "operating_margin"] for n in weak_nodes)
            turnover_weak = any(n.id == "asset_turnover" for n in weak_nodes)
            
            if margin_weak and turnover_weak:
                hypotheses.append(FinancialHypothesis(
                    id="hyp_roa_both",
                    category="profitability",
                    description="ROAの低下は利益率と資産効率の両方に起因しています。構造的な事業モデルの問題の可能性があります",
                    severity="critical",
                    evidence=["ROA", "売上高利益率", "総資産回転率"],
                    metrics_affected=["ROA"],
                    suggested_investigation="事業ポートフォリオ分析、競争力評価、コスト構造の全面見直し"
                ))
            elif margin_weak:
                hypotheses.append(FinancialHypothesis(
                    id="hyp_roa_margin",
                    category="profitability",
                    description="ROAの低下は主に利益率の問題に起因しています",
                    severity="high",
                    evidence=["ROA", "売上高利益率"],
                    metrics_affected=["ROA", "売上高利益率"],
                    suggested_investigation="価格戦略、コスト削減機会、製品ミックス最適化"
                ))
            elif turnover_weak:
                hypotheses.append(FinancialHypothesis(
                    id="hyp_roa_turnover",
                    category="efficiency",
                    description="ROAの低下は主に資産効率の問題に起因しています",
                    severity="high",
                    evidence=["ROA", "総資産回転率"],
                    metrics_affected=["ROA", "総資産回転率"],
                    suggested_investigation="運転資本管理、固定資産の有効活用、不良資産の特定"
                ))
        
        return hypotheses
    
    def _calculate_yoy_changes(
        self, 
        fs: Dict, 
        current_year: int, 
        prev_year: int
    ) -> Dict[str, float]:
        """Calculate year-over-year changes for key metrics."""
        changes = {}
        
        for metric in ["revenue", "net_income", "total_assets"]:
            current = fs.get(metric, {}).get(str(current_year), 0)
            previous = fs.get(metric, {}).get(str(prev_year), 0)
            if previous != 0:
                changes[metric] = (current - previous) / previous
        
        return changes
    
    def _generate_summary(
        self, 
        weak_nodes: List[FinancialNode], 
        hypotheses: List[FinancialHypothesis]
    ) -> str:
        """Generate analysis summary text."""
        critical_count = len([n for n in weak_nodes if n.severity == "critical"])
        high_count = len([n for n in weak_nodes if n.severity == "high"])
        
        summary_parts = []
        
        if critical_count > 0:
            summary_parts.append(f"クリティカルな問題が{critical_count}件検出されました")
        if high_count > 0:
            summary_parts.append(f"高優先度の問題が{high_count}件検出されました")
        
        if hypotheses:
            summary_parts.append(f"{len(hypotheses)}件の仮説を生成しました")
        
        if not summary_parts:
            return "財務指標は概ね健全な状態です"
        
        return "。".join(summary_parts) + "。詳細な調査が推奨されます。"


# Factory function for easy instantiation
def create_roa_engine(config: Optional[EngineConfig] = None) -> ROAEngine:
    """Create and return an ROA Engine instance."""
    return ROAEngine(config)
