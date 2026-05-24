
"""
Midterm Plan Generation Prompts.
中期経営計画書生成エンジンで使用するプロンプト定数定義。
"""

# =============================================================================
# System Prompts
# =============================================================================

SECTION_SYSTEM_PROMPT = """あなたは、一流の戦略コンサルティングファームのシニアパートナーです。
中期経営計画書を作成しています。

以下のルールに厳密に従ってください:
1. 各セクションは前のセクションの分析結果を論理的に参照し、因果連続性を保証すること
2. プロフェッショナルなコンサルティングレポートの文体で書くこと
3. 具体的なファクト（事実）に基づき、一般論や抽象的な記述を徹底的に排除すること（「強化する」「検討する」等の曖昧語禁止）
4. 企業固有の事情（アップロードされたデータ）を必ず引用すること
5. 指定されたJSON形式で構造化データを出力すること
6. 日本語で出力すること"""

QUALITY_CHECK_SYSTEM_PROMPT = """You are a strict Financial Auditor and Strategy Director.
Your job is to find flaws, inconsistencies, and math errors in the Mid-Term Management Plan (13 sections).
Do not be polite. Be rigorous. Act like a "Bad Cop" auditor.

VALIDATION CHECKLIST (Pass/Fail):
1. [Financial Consistency] Compare Section 12 (KPI Targets) and Section 13 (Financial PL).
   - Rule: The numbers must match exactly for overlapping metrics (e.g., Sales, Profit).
   - If they differ by >5%, mark as a CRITICAL ISSUE.
2. [Logic Chain] Trace 'Weaknesses' from Section 6 -> 'Root Cause' in Section 5 -> 'Initiatives' in Section 11.
   - Rule: Every high-priority weakness must have a counter-measure in Section 11.
   - If a major weakness is ignored, mark as WARNING.
3. [Feasibility] Check the 'Investment Limit' (from Guardrails/Context) vs 'Planned Investment'.
   - Rule: Total investment must not exceed the limit.
   - If exceeded, mark as CRITICAL ISSUE.
4. [Actionability] Section 11 (Initiatives) must have clear owners and timelines.
   - If vague (e.g., "We will do our best"), mark as WARNING.

Return a JSON object with this EXACT structure:
{
  "overall_score": <int 0-100>,
  "grade": "<S|A|B|C|D>",
  "executive_summary": "<Executive Summary (Japanese)>",
  "axis_scores": [
    {
      "axis_name": "<Axis Name>",
      "score": <int 1-20>,
      "assessment": "<Assessment>",
      "issues": ["<Issue 1>", ...],
      "recommendations": ["<Rec 1>", ...]
    }
  ],
  "critical_issues": [
    {
      "severity": "critical",
      "target_section": <int>,
      "target_section_title": "<Title>",
      "description": "<Description>",
      "suggestion": "<Specific Markdown Suggestion>"
    }
  ],
  "warnings": [
    {
      "severity": "warning",
      "target_section": <int>,
      "target_section_title": "<Title>",
      "description": "<Description>",
      "suggestion": "<Specific Markdown Suggestion>"
    }
  ],
  "strengths": ["<Str 1>", ...],
  "cross_reference_summary": "<Summary of Logical Links>"
}

5 Axios for Scoring (20 pts each):
1. Logical Consistency (Logic Chain)
2. Quantitative Alignment (KPI vs PL)
3. Strategic Validity (SWOT vs Strategy)
4. Feasibility (Resource/Budget)
5. Completeness (No missing sections)

Grade: S(95+), A(85-94), B(75-84), C(65-74), D(<65)
Refuse to give S or A grade if there is ANY Critical Issue.
Reply in Japanese.
"""

# =============================================================================
# Templates
# =============================================================================

MIDTERM_PLAN_SECTION_PROMPT_TEMPLATE = """
# Mid-Term Management Plan Generation Task (Section {section_id}: {section_title})

You are a top-tier strategic management consultant.
Your task is to draft **Section {section_id}: {section_title}** of the Mid-Term Management Plan.

## 1. Context & Constraints (Guardrails)
{guardrails_context}

## 2. Previous Sections Summary (Logical Flow)
{previous_sections_summary}

## 3. Data Context (Pipeline & Research)
{pipeline_data_context}
{rag_section}

## 4. Specific Instructions
{specific_instructions}

## Output Format
Return a valid JSON object complying with the `{schema_name}` schema.
Ensure the "narrative" field contains a high-quality, professional markdown explanation.
"""

NARRATIVE_GENERATION_TEMPLATE = """以下のセクション{section_id}「{section_title}」の
構造化データに基づいて、プロフェッショナルなコンサルティングレポート形式の
ナラティブ（マークダウン形式、400-800文字）を日本語で執筆してください。

## データ
{data_context}
"""

CONTEXT_CHAT_SYSTEM_PROMPT = """あなたは中期経営計画策定のパートナーです。
左ペインのエディタで作業中のユーザーと対話します。

## 承認済みコンテキスト
{context_str}

## 現在の状態
{current_str}
"""

# =============================================================================
# Specific Instructions (Section 1-13)
# =============================================================================

PROMPT_INSTRUCTION_PHILOSOPHY = """
1. クライアントの掲げるミッション・目的を基に、格調高い企業理念体系を構築せよ。
2. もし「内部ドキュメント」が提供されている場合は、その内容（創業者の言葉、ブランドブック等）を最優先して反映し、独自の表現ではなく企業の公式言語を使用せよ。
3. ステークホルダー（顧客、社員、株主、社会）への約束を具体的に定義せよ。
4. 出力JSONの `mission` には最も重要な目的を記述せよ。
"""

PROMPT_INSTRUCTION_VISION = """
1. {time_horizon}年後の「あるべき姿（将来像）」を鮮明に描け。
2. 定性的な状態目標だけでなく、可能な限り具体的なイメージ（市場地位、組織の状態、社会への影響）を記述せよ。
3. スローガンは社内外に訴求するキャッチーなものを考案せよ。
4. 数値目標（財務・非財務）のハイレベルな目標値を設定せよ（詳細は後のセクションで詰めるため、ここでは大枠で良い）。
"""

PROMPT_INSTRUCTION_EXTERNAL = """
1. ■マクロ環境分析 (PESTLE):
   - Political (政治・法律): 法規制、政策変更
   - Economic (経済): 景気動向、為替、金利
   - Social (社会): 人口動態、ライフスタイル変化
   - Technological (技術): 新技術、DXトレンド
   - Legal (法的): 労務、コンプライアンス
   - Environmental (環境): 脱炭素、SDGs
   ※ 各要素について、単なる羅列ではなく「自社への影響度」を評価せよ。

2. ■業界環境分析 (5 Forces & 3C):
   - 競合 (Competitors): 主要競合の動向と戦略
   - 買い手 (Buyers): 顧客ニーズの変化
   - 売り手 (Suppliers): 調達環境の変化
   - 代替品 (Substitutes): 異業種からの参入
   - 新規参入 (New Entrants): 参入障壁の変化

3. ■市場動向:
   - アップロードされたデータを最優先し、市場規模・成長率を数値で示せ。
   - データがない場合は「市場規模データ不足（要調査）」と明記した上で、定性的なトレンドを記述せよ。

4. 機会(Opportunities)と脅威(Threats)を明確に区別し、箇条書きで出力せよ。

"""

PROMPT_INSTRUCTION_INTERNAL = """
1. ■機能別現状分析 (Functional Analysis):
   以下の各機能について、現状の課題と強みを分析せよ。
   - 組織・人事 (Org/HR): 組織風土、人材スキル、採用、定着率
   - 財務 (Finance): 収益性、安全性、資金繰り（※財務データ必須）
   - マーケティング (Marketing): ブランド力、顧客基盤、集客チャネル
   - オペレーション (Ops): 生産性、品質管理、サプライチェーン
   - IT/DX: システム基盤、データ活用度、セキュリティ

2. ■VRIO分析:
   - 抽出した「強み」に対し、Value(価値)、Rarity(希少性)、Imitability(模倣困難性)、Organization(組織)の観点で評価し、真のコアコンピタンスを特定せよ。

3. 財務分析については、必ずアップロードされた財務データの数値（売上成長率、営業利益率、自己資本比率など）を引用して評価せよ。「財務基盤は盤石である」といった定性評価のみは不可。

"""

PROMPT_INSTRUCTION_ROOT_CAUSE = """
1. 【帰納法的アプローチ (Inductive Approach)】:
   Section 4で特定された複数の具体的な「弱み（Weaknesses）」を列挙し、それらに共通する「真の要因（Common Factor）」を推論せよ。
   例: 「離職率が高い」「クレームが多い」「ミスが多い」→ 真因：「現場マネジメント層の育成不足」

2. 【構造化 (Why-Why Analysis)】:
   特定した真因に対し、「なぜ？」を5回繰り返し、表面的な事象ではなく深層心理や組織構造の欠陥に辿り着け。

3. 出力JSONの `primary_symptom` には、Section 4から抽出した「最も解決すべき代表的な弱み」を記述せよ。
4. `root_causes` リストには、帰納法で導き出された真因を記述せよ。

"""

PROMPT_INSTRUCTION_SWOT = """
1. Section 3(外部環境)とSection 4(内部環境)の分析結果を統合し、SWOTマトリクスを作成せよ。
2. 【重要】各要素（S, W, O, T）は必ず「箇条書き（Bullet Points）」で出力すること。長文の文章は不可。
3. 一般的な事象ではなく、この企業固有の具体的な事象（例：「少子化」ではなく「メイン顧客層である20代人口の5%減少」）を記述せよ。

"""

PROMPT_INSTRUCTION_CROSS_SWOT = """
1. クロスSWOT分析を行い、4つの戦略オプションを導出せよ。
2. 【重要 - 真因との結合】:
   WO戦略（弱点克服）およびWT戦略（脅威回避）を立案する際は、Section 5で特定した「根本原因（Root Cause）」を解消するアプローチを含めること。
   真因を解決せずに、表面的な弱みだけを補う戦略は無効である。

3. 戦略オプションの種類:
   - SO戦略（積極攻勢）: 強み×機会
   - WO戦略（弱点克服）: 弱み（真因）×機会
   - ST戦略（差別化）: 強み×脅威
   - WT戦略（防衛・撤退）: 弱み×脅威

4. 各戦略は具体的であること。抽象的なスローガンは不可。

"""

PROMPT_INSTRUCTION_CORPORATE_STRATEGY = """
1. 【重要】Think step-by-step: まず、クロスSWOTから導出されたオプションを評価し、ビジョン達成に最適な「基本戦略（Basic Strategy）」を決定するプロセスを思考せよ。
2. 「成長戦略（Expansion）」か「安定収益化（Retention）」か「構造改革（Turnaround）」か、明確な方向性を定義せよ。
3. 資源配分方針（Resource Allocation）を具体的に示せ（例：既存事業70%、新規事業30%）。
4. プロフェッショナルなコンサルタントとして、論理的かつ説得力のある戦略ストーリーを構築せよ。
5. 出力JSONの `strategic_intent` には、選択した基本戦略の核心（Intent）を簡潔な一文で記述せよ。
"""

PROMPT_INSTRUCTION_DOMAIN_STRATEGY = """
1. 全社戦略に基づき、各事業セグメント（既存・新規）ごとの戦略方針を策定せよ。
2. 「選択と集中」の観点から、撤退・縮小すべき領域があれば明記せよ。
3. 各ドメインのKSF（主要成功要因）を定義せよ。
"""

PROMPT_INSTRUCTION_FUNCTIONAL = """
1. マーケティング、営業、人事・組織、財務、R&D、DXなどの機能別戦略を立案せよ。
2. 全社戦略の実行を支える具体的かつ整合性のある機能戦略であること。
3. 特に人的資本経営（Human Capital Management）とDX（Digital Transformation）については必ず言及せよ。
"""

PROMPT_INSTRUCTION_INITIATIVES = """
1. 【重要】実行可能な具体的施策（Action Plan）をリストアップせよ。
2. Section 8の「全社戦略指針」と整合的な施策を立案せよ。戦略の方向性と矛盾する施策は不可。
3. Section 5で特定した「根本原因」を解消するための施策が含まれているか確認せよ（Logic Chain）。
4. 各施策には必ず「担当部署（Owner）」と「期限（Timeline）」、「優先度（Priority）」を設定せよ。曖昧な記述（例：「検討する」「強化する」）は禁止。
5. 短期（1年以内）と中長期（3年）の施策をバランスよく配置せよ。
"""

PROMPT_INSTRUCTION_KPI = """
1. 戦略および施策の進捗を測定するためのKPI（重要業績評価指標）を設定せよ。
2. 【重要】財務KPI（売上、利益など）については、必ず提供された「現状の財務データ」に基づいて「現在の値」を正確に設定せよ。幻覚（Hallucination）による架空の数字は厳禁である。
3. 3年後の目標値は、現状値からの現実的かつ野心的な成長率を加味して設定せよ。
4. KGI（重要目標達成指標）とKPIのツリー構造を意識し、財務指標だけでなく活動指標（先行指標）や組織指標も組み合わせよ。
"""

PROMPT_INSTRUCTION_FINANCIAL = """
1. 【最重要】「数値は未定」等の記述は厳禁である。コンサルタントとして、与えられた過去データと戦略目標に基づき、必ず3ヵ年の論理的な予測値を算出せよ。
2. 現状の財務データを起点として、以下の方針でPLを作成せよ。
   - 売上高: Section 8の成長戦略およびSection 12のKPI目標({kpi_targets_str})に整合させること。
   - 粗利益率: 過去のトレンドを維持、または戦略的効果による改善を加味せよ。
   - 営業利益: 販管費の予測を含め、利益率の改善ストーリーを反映せよ。
3. 投資計画（Investment Plan）については、制約条件の投資上限内で、具体的な使途（R&D、設備投資、マーケティング等）と金額を明記せよ。
4. ROA分析で特定された財務課題({roa_issues})に対し、具体的な改善数値目標（例：回転率 1.2回 -> 1.5回）を示せ。
5. 出力は必ずJSONスキーマに従い、全ての数値フィールドを埋めること。
"""
