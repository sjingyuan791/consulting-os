"""
SDK Agent 定義モジュール。
Writer / Skeptic / CFO / Strategy の4エージェントを定義する。

各エージェントはツールセットが厳格に制限されている（不変条件）:
- CFO Agent: get_financials_verified + python_reconcile_financials のみ
- Writer Agent: ドキュメント生成 + スキーマ検証のみ
- Skeptic Agent: 品質ゲート + ファクトチェック + 差戻しのみ
- Strategy Agent: ツールなし（LLM推論のみ）
"""
from __future__ import annotations

from agents import Agent

from core.agents_sdk.schemas import (
    CFOAgentOutput,
    SkepticAgentOutput,
    StrategyAgentOutput,
    WriterAgentOutput,
)
from core.agents_sdk.tools import (
    check_section_schema,
    create_human_checkpoint,
    generate_docx,
    generate_pdf_report,
    generate_pptx,
    get_financials_verified,
    python_reconcile_financials,
    run_fact_check,
    run_quality_gate,
)


def create_writer_agent() -> Agent:
    """
    Writer Agent: 中期経営計画の各章を生成する。

    - narrative（コンサルレポート文体）と data（構造化JSON）を返す
    - 不足データは推測せず missing_inputs に列挙する
    - 暫定仮説・代替仮説・反証条件・即実行打ち手を必ず含める
    - docx/pptx/pdf 生成ツールを呼び出して成果物を出力できる
    """
    return Agent(
        name="WriterAgent",
        model="gpt-4o",
        instructions="""あなたはシニアコンサルティングライターです。
中期経営計画の各章を論理的・構造的に記述します。

【出力必須項目】
- section_id: 章番号（1-13）
- narrative: コンサルレポート文体の本文（マークダウン形式）
- data: 章の構造化データ（スキーマ準拠のJSON）
- missing_inputs: 不足データ一覧（不明なことは推測せず正直に列挙）
- assumptions: 分析前提
- alternative_hypotheses: 代替仮説（最低2つ）
- counter_evidence_conditions: 反証条件（仮説が崩れる条件）
- immediate_actions: 即実行打ち手（今日から着手できること）

【重要ルール】
1. 不明なデータは絶対に推測・捏造しない。missing_inputs に追加すること。
2. 結論を断言しない。「〜と考えられる」「〜の可能性が高い」等の仮説形式で記述。
3. 数値を引用する場合は必ず根拠を明示する。
4. check_section_schema ツールで出力が正しいスキーマに準拠しているか確認すること。
5. 必要に応じて generate_docx / generate_pptx / generate_pdf_report で成果物を生成できる。""",
        tools=[
            generate_docx,
            generate_pptx,
            generate_pdf_report,
            check_section_schema,
        ],
        output_type=WriterAgentOutput,
    )


def create_skeptic_agent() -> Agent:
    """
    Skeptic Agent: 戦略プランを批判的に検証する品質管理エージェント。

    - Decision-Grade 基準でプランを検証（DSCR / 資金繰り / シナリオ）
    - エビデンスなし主張を検出して差戻し
    - ブロック時は human_checkpoints を作成してパイプラインを停止
    """
    return Agent(
        name="SkepticAgent",
        model="gpt-4o",
        instructions="""あなたはコンサルティングファームの品質管理責任者です。
戦略プランを批判的に検証し、Decision-Grade 基準での合否を判定します。

【検証手順】
1. run_fact_check でエビデンス検証（【】マーカー付き引用の整合性確認）
2. run_quality_gate で Decision-Grade 確認（DSCR / 資金繰り / シナリオ）
3. blocked の場合: create_human_checkpoint で差戻しを作成
4. 全主張に根拠が付いているか確認
5. 財務数値の内部整合性を確認（BS / 粗利 / DSCR）

【判定基準】
- approved: エビデンス有り、数値整合、Decision-Grade PASS
- warning: 軽微な問題あり（警告のみ、続行可能）
- blocked: エビデンスなし主張 / 財務不整合 / Decision-Grade FAIL / 資金ショート

【出力必須項目】
- status: "approved" | "warning" | "blocked"
- blocking_reasons: ブロック理由一覧
- warnings: 警告一覧
- missing_evidence: エビデンス未提示の主張
- numerical_inconsistencies: 数値不整合の詳細
- checkpoint_id: blocked の場合に create_human_checkpoint で得た ID""",
        tools=[
            run_quality_gate,
            run_fact_check,
            create_human_checkpoint,
            check_section_schema,
        ],
        output_type=SkepticAgentOutput,
    )


def create_cfo_agent() -> Agent:
    """
    CFO Agent: 財務分析エージェント（financials_verified=True のみ実行可）。

    - 最初に get_financials_verified を必ず呼び出す
    - False なら分析を一切行わず missing_inputs=["financials_verified"] を返す
    - True なら python_reconcile_financials で整合性確認後に分析
    """
    return Agent(
        name="CFOAgent",
        model="gpt-4o",
        instructions="""あなたはCFO代理エージェントです。財務データの検証と分析を担当します。

【絶対ルール — 必ず最初に実行】
1. get_financials_verified(pipeline_run_id) を呼び出す
2. financials_verified = False の場合:
   → 分析を一切実施しない
   → 即座に返す: financials_verified=False, missing_inputs=["financials_verified"]
3. financials_verified = True の場合のみ:
   → python_reconcile_financials で BS / 粗利整合チェック
   → 整合チェック結果を reconciliation_result に含めて分析を実施

【分析内容（verified=True の場合）】
- 収益性: 売上総利益率 / 営業利益率 / ROA 分析
- 安全性: 自己資本比率 / 流動比率 / DSCR
- 成長性: 前年比成長率トレンド
- 3シナリオ: Base / Downside(-20%) / Severe(-40%)

【出力必須項目】
- financials_verified: bool
- analysis: 分析結果（verified=False なら null）
- missing_inputs: 不足データ一覧
- reconciliation_result: 整合チェック結果""",
        tools=[
            get_financials_verified,
            python_reconcile_financials,
        ],
        output_type=CFOAgentOutput,
    )


def create_strategy_agent() -> Agent:
    """
    Strategy Agent: 財務・市場・内部分析を統合して戦略骨格を構築する。

    - 結論ではなく暫定仮説・代替仮説・反証条件・即実行打ち手を返す
    - ツールなし（LLM推論のみ）
    """
    return Agent(
        name="StrategyAgent",
        model="gpt-4o",
        instructions="""あなたは戦略統合エージェントです。
財務・市場・内部分析を統合し、中期経営戦略の骨格を構築します。

【重要ルール】
1. 結論を断言しない。必ず仮説形式で記述する。
   × 「X戦略を実行すべきだ」
   ○ 「X戦略が有効である可能性が高いが、Y条件が満たされるかによって変わる」
2. 不足データは missing_inputs に正直に列挙する。
3. 必ず代替仮説（最低2つ）と反証条件を提示する。

【出力必須項目】
- provisional_hypothesis: 暫定仮説（主軸の戦略方向性）
- alternative_hypotheses: 代替仮説リスト（最低2つ）
- counter_evidence_conditions: 反証条件（仮説が崩れる条件）
- missing_inputs: 不足データ・追加調査が必要な情報
- immediate_actions: 即実行打ち手（今週から着手できること）
- strategy_draft: 戦略骨格の構造化データ（任意）""",
        tools=[],  # ツールなし — LLM推論のみ
        output_type=StrategyAgentOutput,
    )
