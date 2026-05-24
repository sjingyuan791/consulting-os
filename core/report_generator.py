"""
PDF Report Generator for Consulting OS.
Professional consulting report generation with Japanese business formatting.

経営診断レポート/中期経営計画書/月次報告書等のPDF生成:
- 経営診断報告書テンプレート
- 中期経営計画書テンプレート
- アクションプラン
- Chart.jsによるプロ品質グラフ
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import json

# Chart generator import
from core.chart_generator import (
    generate_revenue_trend_chart,
    generate_cost_breakdown_chart,
    generate_benchmark_comparison_chart,
    generate_scenario_comparison_chart,
    generate_kpi_dashboard,
    get_chart_js_header,
    format_currency_ja,
    format_percentage_ja,
    format_evaluation_mark
)


class ReportType(str, Enum):
    """レポートタイプ"""
    DIAGNOSTIC = "diagnostic"           # 経営診断報告書
    MID_TERM_PLAN = "mid_term_plan"     # 中期経営計画
    ACTION_PLAN = "action_plan"          # アクションプラン
    MONTHLY = "monthly"                  # 月次報告書
    DD_REPORT = "dd_report"             # DD報告書


class ReportSection(BaseModel):
    """レポートセクション"""
    title: str
    content: str
    charts: List[Dict[str, Any]] = Field(default=[])
    tables: List[Dict[str, Any]] = Field(default=[])
    page_break_after: bool = Field(default=False)


class ExecutiveSummary(BaseModel):
    """エグゼクティブサマリー"""
    overall_assessment: str = Field(default="", description="総合評価")
    key_findings: List[str] = Field(default=[], description="主要な発見事項")
    critical_issues: List[str] = Field(default=[], description="重要課題")
    recommendations: List[str] = Field(default=[], description="主要提言")
    expected_impact: str = Field(default="", description="期待される効果")


class FinancialSummaryTable(BaseModel):
    """財務サマリーテーブル"""
    years: List[int] = Field(default=[])
    revenue: List[float] = Field(default=[], description="売上高")
    operating_profit: List[float] = Field(default=[], description="営業利益")
    net_income: List[float] = Field(default=[], description="純利益")
    roa: List[float] = Field(default=[])
    roe: List[float] = Field(default=[])


class DiagnosticReportData(BaseModel):
    """経営診断報告書データ"""
    # 基本情報
    company_name: str
    report_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y年%m月%d日"))
    consultant_name: str = Field(default="")
    
    # エグゼクティブサマリー
    executive_summary: ExecutiveSummary
    
    # 財務分析
    financial_summary: FinancialSummaryTable
    financial_analysis: str = Field(default="")
    
    # 業界比較
    industry_benchmark: Dict[str, Dict[str, float]] = Field(default={})
    
    # 課題と提言
    issues_and_recommendations: List[Dict[str, str]] = Field(default=[])
    
    # アクションプラン
    action_items: List[Dict[str, Any]] = Field(default=[])


class MidTermPlanData(BaseModel):
    """中期経営計画書データ"""
    company_name: str
    plan_period: str = Field(default="2024年度〜2026年度")
    vision: str = Field(default="")
    
    # 数値目標
    target_revenue: float = Field(default=0.0)
    target_profit: float = Field(default=0.0)
    target_roa: float = Field(default=0.0)
    
    # 戦略
    key_strategies: List[str] = Field(default=[])
    
    # 年度別計画
    yearly_plans: List[Dict[str, Any]] = Field(default=[])
    
    # 投資計画
    investment_plan: List[Dict[str, Any]] = Field(default=[])
    
    # KPI
    kpis: List[Dict[str, Any]] = Field(default=[])


class ReportGenerator:
    """レポート生成エンジン"""
    
    # レポートテンプレート（HTML形式で生成、PDF変換は別途）
    DIAGNOSTIC_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        body {{
            font-family: 'Yu Gothic', 'Meiryo', sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px;
        }}
        .cover {{
            text-align: center;
            padding: 100px 0;
            page-break-after: always;
        }}
        .cover h1 {{
            font-size: 28px;
            border-bottom: 3px solid #1a365d;
            display: inline-block;
            padding-bottom: 10px;
        }}
        .cover .company {{
            font-size: 32px;
            margin: 40px 0;
            color: #1a365d;
        }}
        .cover .date {{
            margin-top: 60px;
            color: #666;
        }}
        h2 {{
            color: #1a365d;
            border-left: 4px solid #1a365d;
            padding-left: 15px;
            margin-top: 40px;
        }}
        h3 {{
            color: #2c5282;
            margin-top: 30px;
        }}
        .summary-box {{
            background: #f7fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .summary-box h3 {{
            margin-top: 0;
            color: #1a365d;
        }}
        .highlight {{
            background: #fff3cd;
            padding: 2px 6px;
            border-radius: 3px;
        }}
        .critical {{
            color: #c53030;
            font-weight: bold;
        }}
        .positive {{
            color: #2f855a;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #e2e8f0;
            padding: 12px;
            text-align: right;
        }}
        th {{
            background: #1a365d;
            color: white;
            text-align: center;
        }}
        tr:nth-child(even) {{
            background: #f7fafc;
        }}
        .action-item {{
            background: #ebf8ff;
            border-left: 4px solid #3182ce;
            padding: 15px;
            margin: 15px 0;
        }}
        .page-break {{
            page-break-after: always;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
        }}
    </style>
</head>
<body>
{content}
</body>
</html>
"""
    
    def generate_diagnostic_report(
        self,
        data: DiagnosticReportData
    ) -> str:
        """経営診断報告書HTMLを生成"""
        
        content = f"""
        <!-- 表紙 -->
        <div class="cover">
            <h1>経営診断報告書</h1>
            <div class="company">{data.company_name} 御中</div>
            <div class="date">{data.report_date}</div>
            <div style="margin-top: 80px;">
                {data.consultant_name or "Consulting OS"}
            </div>
        </div>
        
        <!-- エグゼクティブサマリー -->
        <h2>1. エグゼクティブサマリー</h2>
        
        <div class="summary-box">
            <h3>総合評価</h3>
            <p>{data.executive_summary.overall_assessment}</p>
        </div>
        
        <h3>主要な発見事項</h3>
        <ul>
        {"".join(f'<li>{item}</li>' for item in data.executive_summary.key_findings)}
        </ul>
        
        <h3>重要課題</h3>
        <ul>
        {"".join(f'<li class="critical">{item}</li>' for item in data.executive_summary.critical_issues)}
        </ul>
        
        <h3>主要提言</h3>
        <ul>
        {"".join(f'<li>{item}</li>' for item in data.executive_summary.recommendations)}
        </ul>
        
        <div class="page-break"></div>
        
        <!-- 財務分析 -->
        <h2>2. 財務分析</h2>
        
        {self._generate_financial_table(data.financial_summary)}
        
        {self._generate_revenue_chart(data.financial_summary)}
        
        <h3>分析コメント</h3>
        <p>{data.financial_analysis}</p>
        
        <!-- 業界比較 -->
        <h2>3. 業界ベンチマーク比較</h2>
        
        {self._generate_benchmark_table(data.industry_benchmark)}
        
        {self._generate_benchmark_chart(data.industry_benchmark)}
        
        <div class="page-break"></div>
        
        <!-- 課題と提言 -->
        <h2>4. 課題と提言</h2>
        
        {self._generate_issues_section(data.issues_and_recommendations)}
        
        <!-- アクションプラン -->
        <h2>5. アクションプラン</h2>
        
        {self._generate_action_plan(data.action_items)}
        
        <div class="footer">
            本報告書は {data.report_date} 時点の情報に基づいて作成されています。<br>
            Consulting OS により自動生成
        </div>
        """
        
        return self.DIAGNOSTIC_TEMPLATE.format(
            title=f"経営診断報告書 - {data.company_name}",
            content=content
        )
    
    def generate_mid_term_plan(
        self,
        data: MidTermPlanData
    ) -> str:
        """中期経営計画書HTMLを生成"""
        
        content = f"""
        <!-- 表紙 -->
        <div class="cover">
            <h1>中期経営計画書</h1>
            <div class="company">{data.company_name}</div>
            <div style="font-size: 20px; margin: 30px 0;">{data.plan_period}</div>
            <div class="date">{datetime.now().strftime("%Y年%m月")}</div>
        </div>
        
        <!-- ビジョン -->
        <h2>1. 経営ビジョン</h2>
        <div class="summary-box">
            <p style="font-size: 18px; text-align: center;">{data.vision}</p>
        </div>
        
        <!-- 数値目標 -->
        <h2>2. 数値目標</h2>
        <table>
            <tr>
                <th>指標</th>
                <th>現状</th>
                <th>目標（{data.plan_period.split('〜')[1] if '〜' in data.plan_period else '最終年度'}）</th>
            </tr>
            <tr>
                <td>売上高</td>
                <td>-</td>
                <td>{data.target_revenue:.0f}百万円</td>
            </tr>
            <tr>
                <td>営業利益</td>
                <td>-</td>
                <td>{data.target_profit:.0f}百万円</td>
            </tr>
            <tr>
                <td>ROA</td>
                <td>-</td>
                <td>{data.target_roa*100:.1f}%</td>
            </tr>
        </table>
        
        <!-- 重点戦略 -->
        <h2>3. 重点戦略</h2>
        <ul>
        {"".join(f'<li style="margin: 15px 0;"><strong>{i+1}. {strategy}</strong></li>' for i, strategy in enumerate(data.key_strategies))}
        </ul>
        
        <div class="page-break"></div>
        
        <!-- KPI -->
        <h2>4. KPI管理指標</h2>
        {self._generate_kpi_table(data.kpis)}
        
        <div class="footer">
            Consulting OS により自動生成
        </div>
        """
        
        return self.DIAGNOSTIC_TEMPLATE.format(
            title=f"中期経営計画書 - {data.company_name}",
            content=content
        )
    
    def _generate_financial_table(self, summary: FinancialSummaryTable) -> str:
        if not summary.years:
            return "<p>財務データが提供されていません</p>"
        
        rows = ""
        for i, year in enumerate(summary.years):
            rows += f"""
            <tr>
                <td>{year}年度</td>
                <td>{summary.revenue[i] if i < len(summary.revenue) else '-':.0f}</td>
                <td>{summary.operating_profit[i] if i < len(summary.operating_profit) else '-':.0f}</td>
                <td>{summary.roa[i]*100 if i < len(summary.roa) else '-':.1f}%</td>
            </tr>
            """
        
        return f"""
        <table>
            <tr>
                <th>年度</th>
                <th>売上高（百万円）</th>
                <th>営業利益（百万円）</th>
                <th>ROA</th>
            </tr>
            {rows}
        </table>
        """
    
    def _generate_benchmark_table(self, benchmarks: Dict) -> str:
        if not benchmarks:
            return "<p>ベンチマークデータが提供されていません</p>"
        
        rows = ""
        for metric, values in benchmarks.items():
            current = values.get("current", 0)
            benchmark = values.get("benchmark", 0)
            gap = values.get("gap", 0)
            status = "positive" if gap >= 0 else "critical"
            
            rows += f"""
            <tr>
                <td>{metric}</td>
                <td>{current:.2%}</td>
                <td>{benchmark:.2%}</td>
                <td class="{status}">{gap:+.2%}</td>
            </tr>
            """
        
        return f"""
        <table>
            <tr>
                <th>指標</th>
                <th>当社</th>
                <th>業界平均</th>
                <th>差異</th>
            </tr>
            {rows}
        </table>
        """
    
    def _generate_revenue_chart(self, summary: FinancialSummaryTable) -> str:
        """売上・利益推移グラフを生成"""
        if not summary.years or not summary.revenue:
            return ""
        
        return generate_revenue_trend_chart(
            years=summary.years,
            revenues=summary.revenue,
            profits=summary.operating_profit if summary.operating_profit else [0] * len(summary.years),
            chart_id="revenueTrendChart"
        )
    
    def _generate_benchmark_chart(self, benchmarks: Dict) -> str:
        """業界比較グラフを生成"""
        if not benchmarks:
            return ""
        
        metrics = list(benchmarks.keys())
        company_values = [benchmarks[m].get("current", 0) * 100 for m in metrics]
        industry_values = [benchmarks[m].get("benchmark", 0) * 100 for m in metrics]
        
        return generate_benchmark_comparison_chart(
            metrics=metrics,
            company_values=company_values,
            industry_values=industry_values,
            chart_id="benchmarkChart"
        )
    
    def _generate_issues_section(self, issues: List[Dict]) -> str:
        if not issues:
            return "<p>課題データが提供されていません</p>"
        
        content = ""
        for i, issue in enumerate(issues, 1):
            content += f"""
            <div class="action-item">
                <h4>課題{i}: {issue.get('issue', '未設定')}</h4>
                <p><strong>提言:</strong> {issue.get('recommendation', '未設定')}</p>
                <p><strong>期待効果:</strong> {issue.get('expected_impact', '未設定')}</p>
            </div>
            """
        
        return content
    
    def _generate_action_plan(self, actions: List[Dict]) -> str:
        if not actions:
            return "<p>アクションプランが提供されていません</p>"
        
        rows = ""
        for action in actions:
            priority = action.get("priority", "中")
            priority_class = "critical" if priority == "高" else ""
            
            rows += f"""
            <tr>
                <td class="{priority_class}">{priority}</td>
                <td>{action.get('action', '')}</td>
                <td>{action.get('owner', '')}</td>
                <td>{action.get('deadline', '')}</td>
            </tr>
            """
        
        return f"""
        <table>
            <tr>
                <th>優先度</th>
                <th>アクション</th>
                <th>担当</th>
                <th>期限</th>
            </tr>
            {rows}
        </table>
        """
    
    def _generate_kpi_table(self, kpis: List[Dict]) -> str:
        if not kpis:
            return "<p>KPIが設定されていません</p>"
        
        rows = ""
        for kpi in kpis:
            rows += f"""
            <tr>
                <td>{kpi.get('category', '')}</td>
                <td>{kpi.get('name', '')}</td>
                <td>{kpi.get('current', '')}</td>
                <td>{kpi.get('target', '')}</td>
            </tr>
            """
        
        return f"""
        <table>
            <tr>
                <th>カテゴリ</th>
                <th>KPI</th>
                <th>現状</th>
                <th>目標</th>
            </tr>
            {rows}
        </table>
        """


def generate_diagnostic_report(
    company_name: str,
    overall_assessment: str,
    key_findings: List[str],
    critical_issues: List[str],
    recommendations: List[str],
    financial_data: Optional[Dict] = None,
    benchmark_data: Optional[Dict] = None,
    action_items: Optional[List[Dict]] = None
) -> str:
    """
    経営診断報告書HTML生成のファサード関数。
    
    Returns:
        str: HTML形式の報告書
    """
    data = DiagnosticReportData(
        company_name=company_name,
        executive_summary=ExecutiveSummary(
            overall_assessment=overall_assessment,
            key_findings=key_findings,
            critical_issues=critical_issues,
            recommendations=recommendations
        ),
        financial_summary=FinancialSummaryTable(**(financial_data or {})),
        industry_benchmark=benchmark_data or {},
        action_items=action_items or []
    )
    
    generator = ReportGenerator()
    return generator.generate_diagnostic_report(data)


def generate_mid_term_plan(
    company_name: str,
    vision: str,
    plan_period: str,
    target_revenue: float,
    target_profit: float,
    target_roa: float,
    key_strategies: List[str],
    kpis: Optional[List[Dict]] = None
) -> str:
    """
    中期経営計画書HTML生成のファサード関数。
    """
    data = MidTermPlanData(
        company_name=company_name,
        vision=vision,
        plan_period=plan_period,
        target_revenue=target_revenue,
        target_profit=target_profit,
        target_roa=target_roa,
        key_strategies=key_strategies,
        kpis=kpis or []
    )
    
    generator = ReportGenerator()
    return generator.generate_mid_term_plan(data)
