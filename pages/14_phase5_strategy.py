"""
STEP 10: Strategy Design
ガードレール設定 → 全社・事業・機能別戦略設計
"""
import streamlit as st
from core.auth import check_auth
from core.style_utils import load_custom_css
from core.pipeline.stage4_strategy import create_strategy_engine


def render_role_badge(role: str):
    colors = {
        "ai": ("🤖", "#4CAF50", "AI生成"),
        "human": ("👤", "#2196F3", "人間承認"),
        "collaborative": ("🤝", "#FF9800", "協働確認"),
    }
    icon, color, label = colors.get(role, ("❓", "#999", role))
    st.markdown(
        f'<span style="background:{color};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.75rem;margin-right:8px;">{icon} {label}</span>',
        unsafe_allow_html=True,
    )


def _get_ss() -> tuple:
    """Return (notes, client_row, client_id) from session state."""
    return (
        st.session_state.get("_s10_notes", {}),
        st.session_state.get("_s10_client_row", {}),
        st.session_state.get("_s10_client_id"),
    )


def app():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()

    if not check_auth():
        st.warning("ログインが必要です")
        return

    st.title("🎯 STEP 10: 戦略設計")
    st.markdown("ガードレール設定 → 全社戦略 → 事業戦略 → 機能別戦略の階層構築")
    st.divider()

    client_id = st.session_state.get("client_id")
    if not client_id:
        st.warning("⚠️ プロジェクトを選択してください")
        return

    import json as _json
    from core.supabase_client import get_supabase_client
    _sb = get_supabase_client()
    _res = _sb.table("clients").select("notes, name, industry, location").eq("id", client_id).single().execute()
    _client_row = _res.data or {}
    raw_notes = _client_row.get("notes")
    _notes = _json.loads(raw_notes) if isinstance(raw_notes, str) else (raw_notes or {})
    _steps = _notes.get("pipeline_steps", {})

    # Store in session state so render functions can access without NameError
    st.session_state["_s10_notes"] = _notes
    st.session_state["_s10_client_row"] = _client_row
    st.session_state["_s10_client_id"] = client_id

    if _steps.get("9") != "done":
        st.warning("⚠️ STEP 9（真因分析）を完了してから進んでください")
        return

    if "phase5_output" not in st.session_state:
        st.session_state.phase5_output = None
    if "segment_eval_output" not in st.session_state:
        st.session_state.segment_eval_output = None

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🛡️ ガードレール", "📊 セグメント評価", "🏢 全社戦略",
        "📋 事業戦略", "⚙️ 機能別戦略", "⚠️ リスク評価", "✅ 確認",
    ])

    with tab1:
        render_guardrails()
    with tab2:
        render_segment_evaluation()
    with tab3:
        render_corporate_strategy()
    with tab4:
        render_domain_strategies()
    with tab5:
        render_functional_strategies()
    with tab6:
        render_risk_assessment()
    with tab7:
        render_phase5_confirmation()


# ------------------------------------------------------------------ #
#  Tab 1: Strategic Guardrails
# ------------------------------------------------------------------ #
def render_guardrails():
    from core.strategic_guardrails_service import save_guardrails, get_latest_guardrails
    from core.schemas.strategy import GuardrailsSchema

    st.subheader("🛡️ 戦略的ガードレール")
    st.caption(
        "戦略策定における「譲れない制約条件」や「境界線」を定義します。"
        "設定した制約はAI戦略生成に自動反映されます。"
    )

    _notes, _client_row, client_id = _get_ss()

    # Load existing: notes first, fallback to Supabase table
    saved = _notes.get("guardrails") or {}
    if not saved and client_id:
        try:
            existing = get_latest_guardrails(client_id)
            if existing:
                saved = existing.model_dump()
        except Exception:
            pass

    with st.form("guardrails_form_step10"):
        st.subheader("1. 中核となる目的・アイデンティティ")
        mission_objective = st.text_area(
            "ミッション / 戦略目標",
            value=saved.get("mission_objective", ""),
            help="この中期経営計画の究極のゴールは何ですか？",
            height=100,
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            time_horizon = st.slider(
                "計画期間 (年)", min_value=1, max_value=10,
                value=int(saved.get("time_horizon_years", 3)),
            )
        with c2:
            investment_limit = st.slider(
                "最大投資可能額 (百万円)", min_value=0.0, max_value=5000.0, step=100.0,
                value=float(saved.get("investment_limit", 500.0)),
            )
        with c3:
            risk_opts = ["low", "medium", "high"]
            saved_risk = saved.get("risk_tolerance", "medium")
            if saved_risk not in risk_opts:
                saved_risk = "medium"
            risk_tolerance = st.selectbox(
                "リスク許容度", risk_opts,
                index=risk_opts.index(saved_risk),
                format_func=lambda x: {"low": "低リスク", "medium": "中程度", "high": "高リスク"}[x],
            )

        st.divider()
        st.subheader("2. 戦略的境界線（除外事項）")
        st.info("戦略とは「何をしないか」を決めることです。")

        boundaries = saved.get("strategic_boundaries") or {}
        no_entry_markets = st.text_area(
            "参入しない市場・セグメント（カンマ区切り）",
            value=", ".join(boundaries.get("no_entry_markets", [])),
            height=80,
        )
        excluded_models = st.text_area(
            "採用しないビジネスモデル・手法（カンマ区切り）",
            value=", ".join(boundaries.get("excluded_models", [])),
            height=80,
        )

        st.divider()
        st.subheader("3. 成功の定義")
        success_def = st.text_area(
            f"計画期間後の成功状態（あるべき姿）",
            value=saved.get("success_state_definition", ""),
            height=100,
        )

        submitted = st.form_submit_button("💾 ガードレールを保存", type="primary")

        if submitted:
            new_boundaries = {
                "no_entry_markets": [x.strip() for x in no_entry_markets.split(",") if x.strip()],
                "excluded_models": [x.strip() for x in excluded_models.split(",") if x.strip()],
            }
            schema = GuardrailsSchema(
                mission_objective=mission_objective,
                time_horizon_years=time_horizon,
                investment_limit=investment_limit,
                risk_tolerance=risk_tolerance,
                strategic_boundaries=new_boundaries,
                success_state_definition=success_def,
                decision_rules={},
            )

            # Save to strategic_guardrails table (best effort)
            if client_id:
                try:
                    save_guardrails(client_id, schema)
                except Exception:
                    pass

            # Save to clients.notes["guardrails"] (primary)
            try:
                import json as _json
                from core.supabase_client import get_supabase_client
                _sb = get_supabase_client()
                _res2 = _sb.table("clients").select("notes").eq("id", client_id).single().execute()
                _n2 = _json.loads(_res2.data.get("notes") or "{}") if isinstance(_res2.data.get("notes"), str) else (_res2.data.get("notes") or {})
                _n2["guardrails"] = schema.model_dump()
                _sb.table("clients").update({"notes": _json.dumps(_n2, ensure_ascii=False)}).eq("id", client_id).execute()
                st.session_state["_s10_notes"] = _n2
                st.success("✅ ガードレールを保存しました。「全社戦略」タブで戦略を生成してください。")
            except Exception as e:
                st.error(f"保存エラー: {e}")


# ------------------------------------------------------------------ #
#  Tab 2: Segment Evaluation
# ------------------------------------------------------------------ #
def render_segment_evaluation():
    from core.pipeline.segment_scoring_engine import run_segment_scoring, SCORING_AXES

    st.subheader("📊 セグメント評価")
    st.caption(
        "全パイプラインデータ（財務・SWOT・真因・外部環境・内部環境）を統合し、"
        "顧客・市場セグメントを8軸・100点で採点します。"
    )
    render_role_badge("ai")

    _notes, _client_row, client_id = _get_ss()

    # 既存の保存済みセグメント評価を読み込む
    if st.session_state.segment_eval_output is None:
        saved_eval = _notes.get("segment_evaluation")
        if saved_eval:
            try:
                from core.pipeline.segment_scoring_engine import SegmentEvaluation
                st.session_state.segment_eval_output = SegmentEvaluation.model_validate(saved_eval)
            except Exception:
                pass

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("🔍 セグメントを評価", type="primary"):
            guardrails = _notes.get("guardrails") or {}
            input_data = {
                "company_info": {
                    "name": _client_row.get("name", ""),
                    "industry": _client_row.get("industry", ""),
                    "location": _client_row.get("location", ""),
                },
                "financial_summary":  _notes.get("financial_summary", {}),
                "external_env":       _notes.get("external_env", {}),
                "swot":               _notes.get("swot_manual", {}),
                "internal_findings":  _notes.get("internal_findings", {}),
                "root_cause":         _notes.get("root_cause", {}),
                "guardrails":         guardrails,
                "strategy_design":    _notes.get("strategy_design", {}),
            }
            with st.spinner("セグメントを8軸で採点中..."):
                try:
                    result = run_segment_scoring(input_data)
                    st.session_state.segment_eval_output = result
                    # notes に保存
                    import json as _json
                    from core.supabase_client import get_supabase_client
                    _sb = get_supabase_client()
                    _res = _sb.table("clients").select("notes").eq("id", client_id).single().execute()
                    _n = _json.loads(_res.data.get("notes") or "{}") if isinstance(_res.data.get("notes"), str) else (_res.data.get("notes") or {})
                    _n["segment_evaluation"] = result.model_dump()
                    _sb.table("clients").update({"notes": _json.dumps(_n, ensure_ascii=False)}).eq("id", client_id).execute()
                    st.session_state["_s10_notes"] = _n
                    st.success("✅ セグメント評価完了")
                    st.rerun()
                except Exception as e:
                    st.error(f"評価エラー: {type(e).__name__}: {e}")
    with col_info:
        if not st.session_state.segment_eval_output:
            st.info("ガードレールを設定した後、「🔍 セグメントを評価」を実行してください。STEP 9（真因分析）完了後が最適です。")

    eval_result = st.session_state.segment_eval_output
    if not eval_result:
        return

    # ---- 総括 ----
    if eval_result.evaluation_summary:
        st.markdown(
            f'<div style="background:#f0f9ff;border-left:4px solid #0ea5e9;'
            f'border-radius:6px;padding:12px 16px;margin-bottom:1rem;">'
            f'{eval_result.evaluation_summary}</div>',
            unsafe_allow_html=True,
        )

    # ---- ランキングサマリー ----
    rec_color = {
        "focus":     ("#dcfce7", "#15803d", "🎯 最優先"),
        "maintain":  ("#dbeafe", "#1d4ed8", "🔄 維持"),
        "selective": ("#fef3c7", "#b45309", "⚖️ 選択的"),
        "exit":      ("#fee2e2", "#b91c1c", "🚫 撤退"),
    }

    st.markdown("### セグメント優先順位")
    for seg in sorted(eval_result.segments, key=lambda s: s.priority_rank):
        bg, fg, rec_label = rec_color.get(seg.recommendation, ("#f9fafb", "#374151", seg.recommendation))
        score_bar = int(seg.total_score)
        with st.container():
            hdr_col, score_col = st.columns([4, 1])
            with hdr_col:
                st.markdown(
                    f'<div style="background:{bg};border-radius:8px;padding:8px 14px;margin-bottom:2px;">'
                    f'<span style="font-weight:700;color:#111827;">#{seg.priority_rank} {seg.segment_name}</span>'
                    f'&nbsp;&nbsp;<span style="background:{fg};color:white;font-size:0.7rem;'
                    f'padding:1px 8px;border-radius:999px;">{rec_label}</span>'
                    f'<div style="font-size:0.8rem;color:#6b7280;margin-top:3px;">{seg.description}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with score_col:
                st.metric("スコア", f"{seg.total_score:.1f}")

        with st.expander(f"詳細: {seg.segment_name}"):
            # 軸別スコア
            st.markdown("**採点内訳（8軸）**")
            ax_label_map = {ax["id"]: ax["label"] for ax in SCORING_AXES}
            for ax in seg.axis_scores:
                ax_label = ax_label_map.get(ax.axis, ax.axis)
                bar_pct = ax.score
                st.markdown(
                    f'<div style="margin-bottom:6px;">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'font-size:0.78rem;margin-bottom:2px;">'
                    f'<span>{ax_label}</span><span style="font-weight:700;">{ax.score}/100</span></div>'
                    f'<div style="background:#e5e7eb;border-radius:999px;height:6px;">'
                    f'<div style="background:#6366f1;border-radius:999px;height:6px;width:{bar_pct}%"></div>'
                    f'</div>'
                    f'<div style="font-size:0.72rem;color:#6b7280;margin-top:1px;">{ax.rationale}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("---")
            rat_col, risk_col = st.columns(2)
            with rat_col:
                st.markdown("**戦略的根拠**")
                st.markdown(seg.strategic_rationale)
                if seg.quick_wins:
                    st.markdown("**クイックウィン**")
                    for qw in seg.quick_wins:
                        st.markdown(f"⚡ {qw}")
            with risk_col:
                if seg.key_risks:
                    st.markdown("**主要リスク**")
                    for kr in seg.key_risks:
                        st.markdown(f"⚠️ {kr}")

    # ---- 採点方法注記 ----
    if eval_result.scoring_methodology:
        st.caption(f"採点方法: {eval_result.scoring_methodology}")


# ------------------------------------------------------------------ #
#  Tab 3: Corporate Strategy
# ------------------------------------------------------------------ #
def render_corporate_strategy():
    st.subheader("全社戦略の策定")
    render_role_badge("ai")

    _notes, _client_row, client_id = _get_ss()

    col1, col2 = st.columns([3, 1])

    with col2:
        guardrails = _notes.get("guardrails") or {}
        if not guardrails:
            st.warning("先に「ガードレール」タブで制約条件を設定してください。")
        if st.button("🎯 戦略を生成", type="primary"):
            with st.spinner("クライアント固有の戦略を設計中..."):
                input_data = {
                    "company_info": {
                        "name": _client_row.get("name", ""),
                        "industry": _client_row.get("industry", ""),
                        "location": _client_row.get("location", ""),
                    },
                    "vision_mission":     _notes.get("vision_mission", {}),
                    "swot":               _notes.get("swot_manual", {}),
                    "root_cause":         _notes.get("root_cause", {}),
                    "financial_summary":  _notes.get("financial_summary", {}),
                    "internal_findings":  _notes.get("internal_findings", {}),
                    "external_env":       _notes.get("external_env", {}),
                    "guardrails":         guardrails,
                    "segment_evaluation": _notes.get("segment_evaluation"),
                }
                import asyncio
                engine = create_strategy_engine()
                try:
                    result = asyncio.run(engine.process(input_data))
                    st.session_state.phase5_output = result
                    st.success("✅ 戦略生成完了")
                except Exception as e:
                    st.error(f"生成エラー: {type(e).__name__}: {e}")

    with col1:
        if not st.session_state.phase5_output:
            st.info("「ガードレール」タブで制約条件を設定してから、戦略を生成してください。")
            return

        output = st.session_state.phase5_output
        corp = output.corporate_strategy

        st.markdown("##### 🌟 ビジョン")
        st.info(corp.vision)

        st.markdown("##### 🎯 ミッション")
        st.info(corp.mission)

        st.markdown("##### 💡 戦略インテント")
        st.success(corp.strategic_intent)

        st.markdown("##### 💎 コアバリュー")
        cols = st.columns(4)
        for i, value in enumerate(corp.core_values):
            with cols[i % 4]:
                st.markdown(f"**{value}**")

        st.markdown("##### 📈 ポートフォリオ方針")
        direction_labels = {
            "growth": "🚀 成長投資",
            "maintain": "🔄 維持・効率化",
            "harvest": "💰 収穫",
            "divest": "📉 撤退",
        }
        st.write(direction_labels.get(corp.portfolio_direction, corp.portfolio_direction))

        st.markdown("##### 📊 リソース配分優先順位")
        for i, priority in enumerate(corp.resource_allocation_priority, 1):
            st.write(f"{i}. {priority}")

        st.markdown("---")
        render_role_badge("human")
        st.markdown("##### 全社戦略の承認")
        st.radio(
            "全社戦略を承認しますか？",
            ["✅ 承認", "🔄 修正が必要", "❌ 再設計が必要"],
            key="corp_approval",
        )


# ------------------------------------------------------------------ #
#  Tab 3: Domain Strategies
# ------------------------------------------------------------------ #
def render_domain_strategies():
    st.subheader("事業戦略")
    render_role_badge("ai")

    if not st.session_state.phase5_output:
        st.info("まず「全社戦略」タブで戦略を生成してください。")
        return

    output = st.session_state.phase5_output

    for i, domain in enumerate(output.domain_strategies):
        with st.expander(f"📊 {domain.domain_name}", expanded=(i == 0)):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**戦略タイプ:** {domain.strategic_type}")
                st.markdown(f"**成長戦略:** {domain.growth_strategy}")
                st.markdown(f"**競争ポジション:** {domain.competitive_position}")
            with col2:
                st.markdown("**ターゲットセグメント:**")
                for seg in domain.target_segments:
                    st.write(f"- {seg}")

            st.markdown("**バリュープロポジション:**")
            st.info(domain.value_proposition)

            st.markdown("**競争優位性:**")
            for adv in domain.competitive_advantages:
                st.write(f"✓ {adv}")

            st.markdown("**KSF (Key Success Factors):**")
            for ksf in domain.key_success_factors:
                st.write(f"⭐ {ksf}")


# ------------------------------------------------------------------ #
#  Tab 4: Functional Strategies
# ------------------------------------------------------------------ #
def render_functional_strategies():
    st.subheader("機能別戦略")
    render_role_badge("ai")

    if not st.session_state.phase5_output:
        st.info("まず「全社戦略」タブで戦略を生成してください。")
        return

    output = st.session_state.phase5_output
    icon_map = {
        "sales": "💼", "marketing": "📣", "operations": "⚙️",
        "finance": "💰", "hr": "👥", "it": "💻", "rd": "🔬",
    }

    for func in output.functional_strategies:
        icon = icon_map.get(func.function, "📋")
        with st.expander(f"{icon} {func.function_name_ja}", expanded=False):
            st.markdown("**目標:**")
            for obj in func.objectives:
                st.write(f"🎯 {obj}")
            st.markdown("**主要施策:**")
            for init in func.key_initiatives:
                st.write(f"→ {init}")
            st.markdown("**成功指標:**")
            for metric in func.success_metrics:
                st.write(f"📊 {metric}")
            st.caption(f"タイムライン: {func.timeline}")


# ------------------------------------------------------------------ #
#  Tab 5: Risk Assessment
# ------------------------------------------------------------------ #
def render_risk_assessment():
    st.subheader("リスク評価")
    render_role_badge("ai")

    if not st.session_state.phase5_output:
        st.info("まず「全社戦略」タブで戦略を生成してください。")
        return

    output = st.session_state.phase5_output
    risk = output.risk_assessment

    if not risk:
        st.info("リスク評価データがありません。")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("##### ⚠️ 戦略リスク")
        for r in risk.strategic_risks:
            st.markdown(f"**{r.description}**")
            st.caption(f"発生確率: {r.probability} | 影響度: {r.impact}")
            st.write(f"対策: {r.mitigation_strategy}")
            st.markdown("---")
    with col2:
        st.markdown("##### 🔧 オペレーショナルリスク")
        for r in risk.operational_risks:
            st.markdown(f"**{r.description}**")
            st.caption(f"発生確率: {r.probability} | 影響度: {r.impact}")
            st.write(f"対策: {r.mitigation_strategy}")
            st.markdown("---")
    with col3:
        st.markdown("##### 💰 財務リスク")
        for r in risk.financial_risks:
            st.markdown(f"**{r.description}**")
            st.caption(f"発生確率: {r.probability} | 影響度: {r.impact}")
            st.write(f"対策: {r.mitigation_strategy}")

    st.markdown("---")
    risk_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    st.markdown(f"**総合リスクレベル:** {risk_color.get(risk.overall_risk_level, '⚪')} {risk.overall_risk_level}")


# ------------------------------------------------------------------ #
#  Tab 6: Confirmation
# ------------------------------------------------------------------ #
def render_phase5_confirmation():
    st.subheader("STEP 10 確認・承認")
    render_role_badge("collaborative")

    _notes, _client_row, client_id = _get_ss()

    if not st.session_state.phase5_output:
        st.warning("戦略を生成してから確認してください。")
        return

    # Show applied guardrails
    guardrails = _notes.get("guardrails") or {}
    if guardrails:
        with st.expander("🛡️ 適用されたガードレール制約", expanded=False):
            st.write(f"**ミッション目標:** {guardrails.get('mission_objective', '未設定')}")
            st.write(f"**計画期間:** {guardrails.get('time_horizon_years', 3)}年")
            st.write(f"**投資上限:** {guardrails.get('investment_limit', 0):.0f}百万円")
            risk_label = {"low": "低リスク", "medium": "中程度", "high": "高リスク"}
            st.write(f"**リスク許容度:** {risk_label.get(guardrails.get('risk_tolerance', 'medium'), '中程度')}")
            boundaries = guardrails.get("strategic_boundaries") or {}
            no_entry = boundaries.get("no_entry_markets", [])
            if no_entry:
                st.write(f"**参入禁止市場:** {', '.join(no_entry)}")
            st.write(f"**成功の定義:** {guardrails.get('success_state_definition', '未設定')}")

    output = st.session_state.phase5_output

    st.markdown("##### 戦略設計サマリー")
    st.info(output.strategy_rationale)

    st.markdown("##### 確定戦略")
    st.write(f"- 全社戦略: {output.corporate_strategy.strategic_intent[:60]}...")
    st.write(f"- 事業戦略: {len(output.domain_strategies)}事業")
    st.write(f"- 機能別戦略: {len(output.functional_strategies)}機能")

    st.markdown("---")
    st.warning("⚠️ **チェックポイント**: 戦略方針の承認が必要です。")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ 戦略方針を承認してSTEP 11へ", type="primary", use_container_width=True):
            try:
                import json as _json
                from core.supabase_client import get_supabase_client as _get_sb
                _sb2 = _get_sb()
                _res2 = _sb2.table("clients").select("notes").eq("id", client_id).single().execute()
                _n2 = _json.loads(_res2.data.get("notes") or "{}") if isinstance(_res2.data.get("notes"), str) else (_res2.data.get("notes") or {})
                _n2.setdefault("pipeline_steps", {})["10"] = "done"
                _n2["strategy_design"] = st.session_state.phase5_output.model_dump()
                _sb2.table("clients").update({"notes": _json.dumps(_n2, ensure_ascii=False)}).eq("id", client_id).execute()
                st.success("✅ STEP 10 完了！戦略方針が確定されました。")
                st.balloons()
            except Exception as _e:
                st.error(f"保存エラー: {_e}")


if __name__ == "__main__":
    app()
