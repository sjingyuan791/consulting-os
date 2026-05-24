"""
Professional Chart Generator for Consulting OS Reports.
Generates Chart.js-based interactive charts for business reports.

プロフェッショナル品質のグラフ生成モジュール:
- 売上/利益推移グラフ（折れ線）
- 費用構成グラフ（円グラフ）
- 業界比較グラフ（棒グラフ）  
- シナリオ比較グラフ（複合）
- KPI達成率グラフ（ゲージ）
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


# ==========================================
# グラフデータモデル
# ==========================================

@dataclass
class ChartData:
    """グラフデータの基本構造"""
    labels: List[str]
    datasets: List[Dict[str, Any]]
    title: Optional[str] = None
    
    
@dataclass  
class ChartConfig:
    """グラフ設定"""
    chart_type: str  # 'line', 'bar', 'pie', 'doughnut', 'radar'
    width: int = 600
    height: int = 400
    show_legend: bool = True
    responsive: bool = True


# ==========================================
# Chart.js 用のカラーパレット（日本企業向け）
# ==========================================

CHART_COLORS = {
    "primary": "#1a365d",      # 紺色（メイン）
    "secondary": "#2c5282",    # 青
    "accent": "#38a169",       # 緑
    "warning": "#d69e2e",      # 黄
    "danger": "#c53030",       # 赤
    "gray": "#718096",         # グレー
    "light_blue": "#63b3ed",
    "light_green": "#68d391",
    "purple": "#805ad5",
}

# データセット用カラー配列
DATASET_COLORS = [
    {"bg": "rgba(26, 54, 93, 0.8)", "border": "#1a365d"},      # 紺
    {"bg": "rgba(56, 161, 105, 0.8)", "border": "#38a169"},    # 緑
    {"bg": "rgba(214, 158, 46, 0.8)", "border": "#d69e2e"},    # 黄
    {"bg": "rgba(128, 90, 213, 0.8)", "border": "#805ad5"},    # 紫
    {"bg": "rgba(99, 179, 237, 0.8)", "border": "#63b3ed"},    # 水色
]

# 円グラフ用カラー
PIE_COLORS = [
    "rgba(26, 54, 93, 0.9)",
    "rgba(56, 161, 105, 0.9)",
    "rgba(214, 158, 46, 0.9)",
    "rgba(197, 48, 48, 0.9)",
    "rgba(128, 90, 213, 0.9)",
    "rgba(99, 179, 237, 0.9)",
    "rgba(113, 128, 150, 0.9)",
]


# ==========================================
# グラフ生成関数
# ==========================================

def generate_chart_html(
    chart_id: str,
    chart_type: str,
    data: ChartData,
    config: Optional[ChartConfig] = None
) -> str:
    """
    Chart.js形式のHTMLを生成。
    
    Args:
        chart_id: グラフのDOM ID
        chart_type: 'line', 'bar', 'pie', 'doughnut', 'radar'
        data: グラフデータ
        config: グラフ設定
    
    Returns:
        HTML文字列（canvas + script）
    """
    cfg = config or ChartConfig(chart_type=chart_type)
    
    # データセット設定
    datasets_js = []
    for i, dataset in enumerate(data.datasets):
        color = DATASET_COLORS[i % len(DATASET_COLORS)]
        
        ds = {
            "label": dataset.get("label", f"データ{i+1}"),
            "data": dataset.get("data", []),
            "backgroundColor": dataset.get("backgroundColor", color["bg"]),
            "borderColor": dataset.get("borderColor", color["border"]),
            "borderWidth": dataset.get("borderWidth", 2),
        }
        
        if chart_type == "line":
            ds["fill"] = dataset.get("fill", False)
            ds["tension"] = 0.3
            
        datasets_js.append(ds)
    
    # Chart.js設定
    chart_config = {
        "type": chart_type,
        "data": {
            "labels": data.labels,
            "datasets": datasets_js
        },
        "options": {
            "responsive": cfg.responsive,
            "maintainAspectRatio": True,
            "plugins": {
                "legend": {
                    "display": cfg.show_legend,
                    "position": "bottom"
                },
                "title": {
                    "display": bool(data.title),
                    "text": data.title or "",
                    "font": {"size": 16, "weight": "bold"}
                }
            }
        }
    }
    
    # 軸設定（円グラフ以外）
    if chart_type not in ["pie", "doughnut"]:
        chart_config["options"]["scales"] = {
            "y": {
                "beginAtZero": True,
                "ticks": {"font": {"size": 12}}
            },
            "x": {
                "ticks": {"font": {"size": 12}}
            }
        }
    
    # JSON変換
    import json
    config_json = json.dumps(chart_config, ensure_ascii=False)
    
    return f"""
    <div style="margin: 30px 0; padding: 20px; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <canvas id="{chart_id}" width="{cfg.width}" height="{cfg.height}"></canvas>
    </div>
    <script>
        (function() {{
            const ctx = document.getElementById('{chart_id}').getContext('2d');
            new Chart(ctx, {config_json});
        }})();
    </script>
    """


def generate_revenue_trend_chart(
    years: List[int],
    revenues: List[float],
    profits: List[float],
    chart_id: str = "revenueTrendChart"
) -> str:
    """
    売上・利益推移グラフ（折れ線）。
    
    Args:
        years: 年度リスト
        revenues: 売上高リスト（百万円）
        profits: 営業利益リスト（百万円）
    """
    data = ChartData(
        labels=[f"{y}年度" for y in years],
        datasets=[
            {
                "label": "売上高",
                "data": revenues,
                "backgroundColor": "rgba(26, 54, 93, 0.2)",
                "borderColor": "#1a365d",
                "fill": True
            },
            {
                "label": "営業利益",
                "data": profits,
                "backgroundColor": "rgba(56, 161, 105, 0.2)",
                "borderColor": "#38a169",
                "fill": True
            }
        ],
        title="売上高・営業利益推移"
    )
    
    return generate_chart_html(chart_id, "line", data)


def generate_cost_breakdown_chart(
    cost_items: List[str],
    cost_values: List[float],
    chart_id: str = "costBreakdownChart"
) -> str:
    """
    費用構成グラフ（円グラフ）。
    
    Args:
        cost_items: 費目名リスト（「人件費」「原材料費」等）
        cost_values: 費用額リスト（万円）
    """
    data = ChartData(
        labels=cost_items,
        datasets=[{
            "data": cost_values,
            "backgroundColor": PIE_COLORS[:len(cost_items)]
        }],
        title="費用構成比"
    )
    
    config = ChartConfig(chart_type="doughnut", show_legend=True)
    return generate_chart_html(chart_id, "doughnut", data, config)


def generate_benchmark_comparison_chart(
    metrics: List[str],
    company_values: List[float],
    industry_values: List[float],
    chart_id: str = "benchmarkChart"
) -> str:
    """
    業界比較グラフ（棒グラフ）。
    
    Args:
        metrics: 指標名リスト
        company_values: 自社値リスト（%）
        industry_values: 業界平均値リスト（%）
    """
    data = ChartData(
        labels=metrics,
        datasets=[
            {
                "label": "当社",
                "data": company_values,
                "backgroundColor": "rgba(26, 54, 93, 0.8)",
                "borderColor": "#1a365d"
            },
            {
                "label": "業界平均",
                "data": industry_values,
                "backgroundColor": "rgba(113, 128, 150, 0.5)",
                "borderColor": "#718096"
            }
        ],
        title="業界ベンチマーク比較"
    )
    
    return generate_chart_html(chart_id, "bar", data)


def generate_scenario_comparison_chart(
    years: List[int],
    optimistic: List[float],
    standard: List[float],
    pessimistic: List[float],
    chart_id: str = "scenarioChart"
) -> str:
    """
    シナリオ比較グラフ（複合折れ線）。
    
    Args:
        years: 年度リスト
        optimistic: 楽観シナリオ値
        standard: 標準シナリオ値
        pessimistic: 悲観シナリオ値
    """
    data = ChartData(
        labels=[f"{y}年度" for y in years],
        datasets=[
            {
                "label": "楽観シナリオ",
                "data": optimistic,
                "borderColor": "#38a169",
                "backgroundColor": "rgba(56, 161, 105, 0.1)",
                "fill": True
            },
            {
                "label": "標準シナリオ",
                "data": standard,
                "borderColor": "#1a365d",
                "backgroundColor": "rgba(26, 54, 93, 0.1)",
                "fill": True
            },
            {
                "label": "悲観シナリオ",
                "data": pessimistic,
                "borderColor": "#c53030",
                "backgroundColor": "rgba(197, 48, 48, 0.1)",
                "fill": True
            }
        ],
        title="シナリオ別売上予測"
    )
    
    return generate_chart_html(chart_id, "line", data)


def generate_kpi_gauge_html(
    kpi_name: str,
    current_value: float,
    target_value: float,
    unit: str = "%",
    chart_id: str = "kpiGauge"
) -> str:
    """
    KPI達成率ゲージ（SVG）。
    
    Args:
        kpi_name: KPI名
        current_value: 現在値
        target_value: 目標値
        unit: 単位
    """
    achievement_rate = min(100, (current_value / target_value * 100)) if target_value > 0 else 0
    
    # 色の決定
    if achievement_rate >= 100:
        color = "#38a169"  # 緑
        status = "達成"
    elif achievement_rate >= 80:
        color = "#d69e2e"  # 黄
        status = "順調"
    else:
        color = "#c53030"  # 赤
        status = "要改善"
    
    # ゲージ角度計算（180度で100%）
    angle = min(180, achievement_rate * 1.8)
    
    return f"""
    <div style="text-align: center; margin: 20px 0;">
        <svg width="200" height="120" viewBox="0 0 200 120">
            <!-- 背景アーク -->
            <path d="M 20 100 A 80 80 0 0 1 180 100" 
                  fill="none" stroke="#e2e8f0" stroke-width="20" stroke-linecap="round"/>
            <!-- 達成アーク -->
            <path d="M 20 100 A 80 80 0 0 1 180 100" 
                  fill="none" stroke="{color}" stroke-width="20" stroke-linecap="round"
                  stroke-dasharray="{angle * 2.8}, 500"/>
            <!-- 中央値 -->
            <text x="100" y="85" text-anchor="middle" font-size="28" font-weight="bold" fill="{color}">
                {current_value:.1f}{unit}
            </text>
            <text x="100" y="110" text-anchor="middle" font-size="12" fill="#666">
                目標: {target_value:.1f}{unit} ({status})
            </text>
        </svg>
        <div style="font-weight: bold; color: #1a365d;">{kpi_name}</div>
    </div>
    """


def generate_kpi_dashboard(
    kpis: List[Dict[str, Any]]
) -> str:
    """
    複数KPIのダッシュボード表示。
    
    Args:
        kpis: KPIリスト [{"name": "ROA", "current": 5.5, "target": 8.0, "unit": "%"}, ...]
    """
    gauges = []
    for i, kpi in enumerate(kpis):
        gauge = generate_kpi_gauge_html(
            kpi_name=kpi.get("name", f"KPI{i+1}"),
            current_value=kpi.get("current", 0),
            target_value=kpi.get("target", 100),
            unit=kpi.get("unit", "%"),
            chart_id=f"kpiGauge_{i}"
        )
        gauges.append(gauge)
    
    # グリッドレイアウト
    return f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0;">
        {"".join(gauges)}
    </div>
    """


# ==========================================
# ヘルパー関数：日本語数値フォーマット
# ==========================================

def format_currency_ja(value: float, unit: str = "万円") -> str:
    """
    日本語通貨フォーマット。
    
    Examples:
        format_currency_ja(12345) -> "1億2,345万円"
        format_currency_ja(1234567, "円") -> "1,234,567円"
    """
    if value >= 10000 and unit == "万円":
        # 億単位に変換
        oku = value / 10000
        if oku >= 1:
            return f"{oku:,.1f}億円"
    
    return f"¥{value:,.0f}{unit}" if unit == "円" else f"{value:,.0f}{unit}"


def format_percentage_ja(value: float, include_sign: bool = False) -> str:
    """
    日本語パーセント表示。
    
    Examples:
        format_percentage_ja(0.055) -> "5.5%"
        format_percentage_ja(0.12, True) -> "+12.0%"
    """
    pct = value * 100 if abs(value) <= 1 else value
    
    if include_sign and pct > 0:
        return f"+{pct:.1f}%"
    return f"{pct:.1f}%"


def format_evaluation_mark(value: float, thresholds: Tuple[float, float, float] = (80, 60, 40)) -> str:
    """
    評価マーク（◎○△×）を返す。
    
    Args:
        value: 評価値（0-100）
        thresholds: (優良, 良好, 要改善) の閾値
    
    Returns:
        評価マーク
    """
    excellent, good, fair = thresholds
    
    if value >= excellent:
        return "◎"
    elif value >= good:
        return "○"
    elif value >= fair:
        return "△"
    else:
        return "×"


# ==========================================
# Chart.jsライブラリ読み込み用HTML
# ==========================================

CHARTJS_CDN = """
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
"""

def get_chart_js_header() -> str:
    """Chart.jsのCDN読み込みタグを返す"""
    return CHARTJS_CDN
