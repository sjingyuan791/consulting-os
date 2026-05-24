"""
Strategic Framework Analysis Prompts.
戦略フレームワーク分析用プロンプト定義。
"""

# =============================================================================
# PESTLE Analysis Prompt
# =============================================================================

PESTLE_ANALYSIS_SYSTEM_PROMPT = """あなたは一流の戦略コンサルタントです。
指定された市場・業界におけるマクロ環境分析（PESTLE分析）を行い、
ビジネス上の機会と脅威を特定する専門家です。"""

PESTLE_ANALYSIS_USER_PROMPT = """以下のターゲット市場および業界について、詳細なPESTLE分析を行ってください。

## 分析対象
- ターゲット市場: {target_market}
- 業界・業種: {industry}
{custom_context}

## 指示
1. 各要因（Political, Economic, Social, Technological, Legal, Environmental）について、具体的かつ最新のトレンドを分析せよ。
2. 日本国内の市場動向（人口動態、法改正、経済指標など）を重視せよ。
3. 単なる事実の羅列ではなく、「なぜその要因がこの業界にとって重要なのか」という含意（Implication）を記述せよ。
4. 各要因がビジネスにとって「機会（Opportunity）」なのか「脅威（Threat）」なのかを明確に判定せよ。

## 出力フォーマット (JSON)
以下のJSONスキーマに従って出力してください。
{{
  "political": [{{ "factor": "...", "description": "...", "impact": "high/medium/low", "trend": "improving/stable/worsening", "opportunity_or_threat": "opportunity/threat/neutral" }}],
  "economic": [...],
  "social": [...],
  "technological": [...],
  "legal": [...],
  "environmental": [...]
}}
"""

# =============================================================================
# Porter's 5 Forces Analysis Prompt
# =============================================================================

FIVE_FORCES_SYSTEM_PROMPT = """あなたは一流の業界アナリストです。
マイケル・ポーターの「5つの競争要因（5 Forces）」フレームワークを用いて、
業界の収益性と競争構造を分析する専門家です。"""

FIVE_FORCES_USER_PROMPT = """以下の業界について、5 Forces分析を行い、業界の魅力度と競争環境を評価してください。

## 分析対象
- 業界・業種: {industry}
{custom_context}

## 指示
1. 5つの競争要因それぞれについて、脅威レベル（High/Medium/Low）を判定せよ。
2. スコアは1（脅威が低い＝好ましい）から5（脅威が高い＝厳しい）の5段階で評価せよ。
3. 各要因の背後にある具体的なドライビングフォース（決定要因）を挙げよ。
4. 分析結果に基づき、この業界で勝ち残るための戦略的示唆（Strategic Recommendation）を提示せよ。

## 出力フォーマット (JSON)
以下のJSONスキーマに従って出力してください。
{{
  "threat_of_new_entrants": {{ "level": "high/medium/low", "score": 1-5, "key_factors": ["..."], "implications": "..." }},
  "bargaining_power_of_suppliers": {{ ... }},
  "bargaining_power_of_buyers": {{ ... }},
  "threat_of_substitutes": {{ ... }},
  "competitive_rivalry": {{ ... }},
  "overall_attractiveness": "high/medium/low",
  "strategic_recommendations": ["...", "..."]
}}
"""

# =============================================================================
# External Constraints Analysis Prompt
# =============================================================================

EXTERNAL_CONSTRAINTS_SYSTEM_PROMPT = """あなたは戦略的事業計画の策定を支援する「定量的市場アナリスト」です。
マクロ環境分析（PESTLE）と競争環境分析（5 Forces）の結果から、
事業計画の財務モデルに組み込むべき「外部制約条件（Constraints）」を抽出・推定する専門家です。"""

EXTERNAL_CONSTRAINTS_USER_PROMPT = """以下のPESTLE分析および5 Forces分析の結果に基づき、
この事業が直面する客観的な外部制約条件を推定し、JSON形式で出力してください。

## 入力データ
### PESTLE分析（マクロ環境）
{pestle_data}

### 5 Forces分析（競争環境）
{five_forces_data}

{custom_context}

## 指示
1. 市場成長率（Market Growth Rate）: 業界の平均的な成長率を推定せよ（保守的に）。
2. 需要の上限（Demand Ceiling）: もし市場規模の上限が推測できる場合は数値化せよ（不明な場合はnull）。
3. 競争密度（Competitive Density）: 競争の激しさを0.0（独占）〜1.0（完全競争/過当競争）で指数化せよ。
4. 価格圧力（Price Pressure）: 競合や顧客からの値下げ圧力を High/Medium/Low で判定せよ。
5. コストインフレ率（Cost Inflation）: 原材料や人件費の高騰トレンドを考慮したインフレ率を設定せよ（デフォルト0.02）。
6. 規制リスク（Regulatory Risk）: 法規制による事業制約のリスクを High/Medium/Low で判定せよ。

## 出力フォーマット (JSON)
{{
  "market_growth_rate": 0.05,
  "demand_ceiling": 1000000000,
  "competitive_density_index": 0.8,
  "price_pressure_level": "High",
  "cost_inflation_rate": 0.03,
  "regulatory_risk_level": "Medium"
}}
"""
