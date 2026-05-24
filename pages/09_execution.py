import streamlit as st
import pandas as pd
import uuid
import json
import plotly.express as px
from datetime import datetime
from core.auth import check_auth
from core.models import ActionItem, KPIItem, KPIActual, MonthlyReview
from core.repos.execution_repo import get_execution_repo, ExecutionRepo
from core.llm_client import generate_monthly_review_analysis
from core.style_utils import load_custom_css


def _load_execution_run(client_id: str):
    """strategy_execution_runs から最新レコードを取得。テーブル非存在時は None を返す。"""
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        run_res = sb.table("strategy_runs").select("id").eq("client_id", client_id).order("created_at", desc=True).limit(1).execute()
        if not run_res.data:
            return None
        sid = run_res.data[0]["id"]
        exec_res = sb.table("strategy_execution_runs").select("*").eq("strategy_run_id", sid).order("created_at", desc=True).limit(1).execute()
        return exec_res.data[0] if exec_res.data else None
    except Exception:
        return None


def _load_monitoring_history(execution_run_id: str) -> list:
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("monitoring_runs").select("*").eq("execution_run_id", execution_run_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []

def app():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()
    
    if not check_auth():
        st.warning("ログインしてください。")
        return
    
    client_id = st.session_state.get("client_id")
    if not client_id:
        st.warning("クライアントが選択されていません。")
        st.stop()
    user_id = st.session_state.user.id if st.session_state.get("user") else None
    st.title("🚀 STEP 18: 実行計画・モニタリング (PDCA)")

    # STEP 17 完了チェック
    import json as _json
    from core.supabase_client import get_supabase_client as _get_sb
    _sb = _get_sb()
    _res = _sb.table("clients").select("notes").eq("id", client_id).single().execute()
    _notes = _json.loads(_res.data.get("notes") or "{}") if isinstance(_res.data.get("notes"), str) else (_res.data.get("notes") or {})
    _steps = _notes.get("pipeline_steps", {})
    if _steps.get("17") != "done":
        st.warning("⚠️ STEP 17（3か年数値計画）を完了してから進んでください。")
        return

    # Load State from Supabase
    repo = get_execution_repo()
    state = repo.load_state(client_id)

    tab_actions, tab_kpi, tab_review, tab_monitor, tab_done = st.tabs([
        "📋 アクション管理", "📊 KPI管理", "🔄 月次振り返り", "🖥️ モニタリング", "✅ STEP完了",
    ])
    
    # --- Tab 1: Action Tracker ---
    with tab_actions:
        st.subheader("アクション管理")
        
        # Add New Action
        with st.expander("新規アクション追加"):
            with st.form("new_action"):
                c1, c2 = st.columns(2)
                title = c1.text_input("アクション名 *")
                owner = c2.text_input("担当者")
                objective = st.text_area("目的 / 仮説")
                
                c3, c4, c5 = st.columns(3)
                priority = c3.selectbox("優先度", ["High", "Medium", "Low"], index=1)
                impact = c4.slider("インパクト (1-5)", 1, 5, 3)
                effort = c5.slider("工数 (1-5)", 1, 5, 3)
                
                tags_str = st.text_input("タグ (カンマ区切り)")
                
                due = st.date_input("期限")
                
                if st.form_submit_button("アクションを追加"):
                    if not title.strip():
                        st.warning("アクション名は必須です。")
                    else:
                        tag_list = [t.strip() for t in tags_str.split(",") if t.strip()]
                        new_action = ActionItem(
                            id=str(uuid.uuid4())[:8],
                            title=title.strip(),
                            objective=objective,
                            owner=owner,
                            due_date=str(due),
                            priority=priority,
                            impact=impact,
                            effort=effort,
                            tags=tag_list
                        )
                        state.actions.append(new_action)
                        repo.add_action(client_id, new_action, user_id)
                        st.success("アクションを追加しました")
                        st.rerun()

        # Matrix Visualization (Plotly)
        if state.actions:
            st.markdown("### インパクト × 工数 マトリクス")
            
            # Prepare data
            matrix_data = []
            for a in state.actions:
                if a.status != "Done": # Only active actions
                    matrix_data.append({
                        "Title": a.title,
                        "Impact": a.impact,
                        "Effort": a.effort,
                        "Priority": a.priority,
                        "Owner": a.owner
                    })
            
            if matrix_data:
                df_matrix = pd.DataFrame(matrix_data)
                
                fig = px.scatter(
                    df_matrix, 
                    x="Effort", 
                    y="Impact", 
                    color="Priority",
                    hover_data=["Title", "Owner"],
                    size=[10]*len(df_matrix), # Consistent size
                    color_discrete_map={"High": "red", "Medium": "orange", "Low": "blue"},
                    title="Action Priority Matrix"
                )
                
                # Enhance layout
                fig.update_layout(
                    xaxis_title="工数 (低 -> 高)",
                    yaxis_title="インパクト (低 -> 高)",
                    xaxis=dict(range=[0.5, 5.5], dtick=1),
                    yaxis=dict(range=[0.5, 5.5], dtick=1),
                    shapes=[
                        # Quick Wins Box (High Impact, Low Effort)
                        dict(type="rect", x0=0.5, y0=3.5, x1=2.5, y1=5.5, 
                             line=dict(color="green", width=2, dash="dot"))
                    ]
                )
                fig.add_annotation(x=1.5, y=5.2, text="Quick Wins (狙い目)", showarrow=False, font=dict(color="green", size=14))
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Quick Wins List
                quick_wins = [a for a in state.actions if a.impact >= 4 and a.effort <= 2 and a.status != "Done"]
                if quick_wins:
                    st.success(f"**Quick Wins (狙い目) を検出 ({len(quick_wins)}):**")
                    for qw in quick_wins:
                        st.write(f"- {qw.title} (Imp:{qw.impact}, Eff:{qw.effort})")
            
            st.divider()

        # List Actions (Filterable)
        if state.actions:
            st.subheader("アクション一覧")
            for action in state.actions:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    c1.markdown(f"**{action.title}**")
                    if action.tags:
                        c1.caption(f"Tags: {', '.join(action.tags)}")
                    
                    # Editable Status & Priority
                    col_s, col_p = c2.columns(2)
                    new_status = col_s.selectbox("ステータス", ["Not Started", "In Progress", "Done", "Delayed"], 
                                             key=f"status_{action.id}", 
                                             index=["Not Started", "In Progress", "Done", "Delayed"].index(action.status),
                                             label_visibility="collapsed")
                    
                    new_priority = col_p.selectbox("優先度", ["High", "Medium", "Low"],
                                                   key=f"prio_{action.id}",
                                                   index=["High", "Medium", "Low"].index(action.priority),
                                                   label_visibility="collapsed")
                    
                    if new_status != action.status or new_priority != action.priority:
                        action.status = new_status
                        action.priority = new_priority
                        repo.update_action(action.id, {"status": new_status, "priority": new_priority})
                        st.rerun()
                        
                    c3.write(f"**期限:** {action.due_date}")
                    c4.metric("Imp/Eff", f"{action.impact}/{action.effort}")
        else:
            st.info("アクションはまだありません。")

    # --- Tab 2: KPI Registry ---
    with tab_kpi:
        st.subheader("KPI管理")
        
        with st.expander("新規 KPI 定義"):
            with st.form("new_kpi"):
                k_name = st.text_input("KPI名 *")
                k_def = st.text_area("定義")
                k_unit = st.text_input("単位 (例: %, 百万円)")
                
                if st.form_submit_button("KPIを作成"):
                    if not k_name.strip():
                        st.warning("KPI名は必須です。")
                    else:
                        new_kpi = KPIItem(
                            id=str(uuid.uuid4())[:8],
                            name=k_name.strip(),
                            definition=k_def,
                            unit=k_unit
                        )
                        state.kpis.append(new_kpi)
                        kpi_id = repo.add_kpi(client_id, new_kpi, user_id)
                        if kpi_id:
                            new_kpi.id = kpi_id[:8]  # Update with DB ID
                        st.rerun()
        
        # List KPIs and Edit Targets
        if state.kpis:
            st.markdown("### KPIモニタリング")
            for kpi in state.kpis:
                with st.expander(f"{kpi.name} ({kpi.unit})"):
                    # Target Setting with Date Input
                    st.write("目標設定")
                    c1, c2, c3 = st.columns([2, 2, 1])
                    # Date input for Month
                    t_date = c1.date_input("対象月", key=f"td_{kpi.id}")
                    t_month_str = t_date.strftime("%Y-%m")
                    t_val = c2.number_input("目標値", key=f"tv_{kpi.id}")
                    
                    if c3.button("保存", key=f"btn_t_{kpi.id}"):
                        kpi.targets[t_month_str] = t_val
                        repo.set_kpi_target(kpi.id, t_month_str, t_val)
                        st.success("保存しました")
                    
                    # Show current Targets/Actuals table
                    data = []
                    all_months = sorted(list(set(list(kpi.targets.keys()) + list(kpi.actuals.keys()))))
                    for m in all_months:
                        tgt = kpi.targets.get(m, "-")
                        act = kpi.actuals.get(m, KPIActual(year_month=m, value=0)).value if m in kpi.actuals else "-"
                        data.append({"月": m, "目標": tgt, "実績": act})
                    
                    st.dataframe(data)

    # --- Tab 3: Monthly Review ---
    with tab_review:
        st.subheader("月次振り返りサイクル")
        
        # Review Month Selection
        m_date = st.date_input("振り返り対象月", value=datetime.now())
        review_month = m_date.strftime("%Y-%m")
        st.caption(f"対象: **{review_month}**")
        
        st.markdown("#### 1. 実績入力")
        # Grid input for all KPIs for this month
        if not state.kpis:
            st.warning("'KPI管理' タブでKPIを定義してください。")
        else:
            with st.form("input_actuals"):
                input_values = {}
                for kpi in state.kpis:
                    curr_val = 0.0
                    if review_month in kpi.actuals:
                        curr_val = kpi.actuals[review_month].value
                    input_values[kpi.id] = st.number_input(f"{kpi.name} ({kpi.unit})", value=curr_val)
                
                if st.form_submit_button("実績を保存"):
                    for kid, val in input_values.items():
                        k = next(x for x in state.kpis if x.id == kid)
                        k.actuals[review_month] = KPIActual(year_month=review_month, value=val)
                        repo.set_kpi_actual(kid, review_month, val)
                    st.success("実績を更新しました")
            
            st.markdown("#### 2. レポート生成")
            if st.button("AIで分析・レポート生成", type="primary", disabled=len(state.kpis)==0):
                # Calculate Gaps
                gaps = {}
                alerts = []
                metrics_summary = []
                
                for kpi in state.kpis:
                    if review_month in kpi.actuals and review_month in kpi.targets:
                        act = kpi.actuals[review_month].value
                        tgt = kpi.targets[review_month]
                        gap = act - tgt
                        gaps[kpi.id] = gap
                        
                        if tgt > 0 and (gap / tgt) < -0.1: # 10% miss
                            alerts.append(f"{kpi.name} missed target by {abs(gap/tgt)*100:.1f}%")
                        
                        metrics_summary.append(f"- {kpi.name}: Target {tgt}, Actual {act}, Gap {gap}")
                
                # Call LLM
                context_str = st.session_state.get("strategy_context", {}).model_dump_json() if "strategy_context" in st.session_state else "No Strategy Context"
                review_input_json = json.dumps({
                    "month": review_month,
                    "alerts": alerts,
                    "metrics": metrics_summary
                })
                
                with st.spinner("AIパートナーが分析中..."):
                    analysis_raw = generate_monthly_review_analysis(review_input_json, context_str)
                    try:
                        analysis_data = json.loads(analysis_raw)
                    except:
                        analysis_data = {"summary": analysis_raw, "updated_hypotheses": [], "suggested_actions": []}
                    
                    review = MonthlyReview(
                        year_month=review_month,
                        kpi_gaps=gaps,
                        alerts=alerts,
                        summary=analysis_data.get("summary", ""),
                        updated_hypotheses=analysis_data.get("updated_hypotheses", []),
                        suggested_actions=analysis_data.get("suggested_actions", [])
                    )
                    state.reviews.append(review)
                    repo.save_review(client_id, review, user_id)
                    st.success("レポート生成完了！")
                    st.rerun()

            # Show Latest Review
            curr_review = next((r for r in state.reviews if r.year_month == review_month), None)
            if curr_review:
                st.info(f"サマリー: {curr_review.summary}")
                if curr_review.alerts:
                    st.error(f"アラート: {', '.join(curr_review.alerts)}")
                
                st.markdown("##### 仮説の更新")
                for h in curr_review.updated_hypotheses:
                    st.write(f"- {h}")
                    
                st.markdown("##### 提案アクション")
                for a in curr_review.suggested_actions:
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"- {a}")
                    if c2.button("追加", key=f"add_rec_{hash(a)}"):
                        new_a = ActionItem(
                            id=str(uuid.uuid4())[:8], 
                            title=a, 
                            objective="From Monthly Review", 
                            status="Not Started",
                            tags=["suggested_action"],
                            impact=3, effort=3, priority="Medium"
                        )
                        state.actions.append(new_a)
                        repo.add_action(client_id, new_a, user_id)
                        st.toast("アクションを追加しました")

                # Link to Re-Diagnosis (PDCA)
                st.divider()
                st.markdown("#### PDCA サイクル")
                st.write("このレビュー結果に基づき、戦略コンテキストを更新して再診断を行います。")

                if st.button("コンテキスト更新 & 再診断へ"):
                    update_msg = f"\n\n[Monthly Review {review_month}]\nSummary: {curr_review.summary}\nAlerts: {curr_review.alerts}\nHypothesis Updates: {curr_review.updated_hypotheses}"
                    st.session_state["monthly_review_summary"] = update_msg
                    st.success("再診断画面へ移動します...")
                    st.switch_page("pages/03_analysis.py")

    # ------------------------------------------------------------------ #
    #  Tab 4: Monitoring Dashboard (integrated from _10_execution_dashboard.py)
    # ------------------------------------------------------------------ #
    with tab_monitor:
        st.subheader("🖥️ 実行モニタリングダッシュボード")

        exec_run = _load_execution_run(client_id)

        if exec_run:
            # --- Full dashboard mode (strategy_execution_runs exists) ---
            st.caption(f"Execution Run: `{exec_run['id']}`")
            targets = exec_run.get("assumed_kpi_targets_json") or {}
            roadmap = exec_run.get("execution_roadmap_json") or {}

            dash_tab1, dash_tab2, dash_tab3 = st.tabs(["📅 ロードマップ", "📈 KPI予実管理", "🛡️ 是正アクション"])

            with dash_tab1:
                st.subheader("実行ロードマップ")
                actions_list = roadmap.get("actions", [])
                if actions_list:
                    df = pd.DataFrame(actions_list)
                    cols_to_show = [c for c in ["title", "phase", "status"] if c in df.columns]
                    st.dataframe(df[cols_to_show], use_container_width=True)
                else:
                    st.info("ロードマップデータが見つかりません。")

            with dash_tab2:
                st.subheader("予実管理 (Target vs Actual)")
                st.markdown("#### 実績入力")
                current_year = st.selectbox("年度", ["2025", "2026", "2027"], key="mon_year")
                target_map = targets.get(current_year, {})

                if not target_map:
                    st.warning(f"{current_year}年度の目標値が設定されていません。")
                else:
                    with st.form("actuals_form_mon"):
                        actuals: dict = {}
                        keys = list(target_map.keys())
                        half = len(keys) // 2
                        c1, c2 = st.columns(2)
                        with c1:
                            for k in keys[:half]:
                                tv = target_map[k]
                                actuals[k] = st.number_input(f"{k} (目標: {tv})", value=float(tv), key=f"mon_{k}_l")
                        with c2:
                            for k in keys[half:]:
                                tv = target_map[k]
                                actuals[k] = st.number_input(f"{k} (目標: {tv})", value=float(tv), key=f"mon_{k}_r")

                        if st.form_submit_button("実績を登録して差異分析を実行"):
                            try:
                                from core.execution_monitoring_engine import trigger_monitoring_run
                                kpi_payload = {current_year: actuals}
                                result = trigger_monitoring_run(exec_run["id"], kpi_payload, user_id or "")
                                st.success("差異分析完了！")
                                gap = result.get("gap_analysis_json", {})
                                if gap:
                                    st.json(gap)
                            except Exception as e:
                                st.error(f"分析エラー: {type(e).__name__}: {e}")

                st.divider()
                st.subheader("モニタリング履歴")
                history = _load_monitoring_history(exec_run["id"])
                if history:
                    for item in history:
                        with st.expander(f"分析: {item.get('created_at', '')[:16]}", expanded=False):
                            st.json(item.get("gap_analysis_json", {}))
                else:
                    st.info("モニタリング履歴がありません。")

            with dash_tab3:
                st.subheader("推奨される是正アクション")
                history = _load_monitoring_history(exec_run["id"])
                found_actions = False
                for item in history:
                    gap = item.get("gap_analysis_json", {})
                    rec_actions = gap.get("recommended_actions", [])
                    if rec_actions:
                        found_actions = True
                        st.caption(f"（{item.get('created_at', '')[:10]}の分析より）")
                        for act in rec_actions:
                            c1, c2 = st.columns([5, 1])
                            c1.write(f"- {act}")
                            if c2.button("追加", key=f"add_corr_{hash(act)}"):
                                new_corr = ActionItem(
                                    id=str(uuid.uuid4())[:8],
                                    title=act,
                                    objective="是正アクション（差異分析より）",
                                    status="Not Started",
                                    tags=["corrective"],
                                    impact=3, effort=3, priority="High",
                                )
                                repo.add_action(client_id, new_corr, user_id)
                                st.toast("アクションを追加しました")
                        break
                if not found_actions:
                    st.info("差異分析を実行すると是正アクションが表示されます。")

        else:
            # --- Fallback mode: summarize from execution repo ---
            st.info("戦略実行プランが未作成のため、現在のアクション・KPIサマリーを表示します。")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### アクションサマリー")
                if state.actions:
                    status_counts = {}
                    for a in state.actions:
                        status_counts[a.status] = status_counts.get(a.status, 0) + 1
                    for s, cnt in status_counts.items():
                        st.write(f"- {s}: {cnt}件")
                    high_impact = [a for a in state.actions if a.impact >= 4 and a.status != "Done"]
                    if high_impact:
                        st.markdown("**高インパクトアクション（未完了）:**")
                        for a in high_impact[:5]:
                            st.write(f"  → {a.title}（期限: {a.due_date}）")
                else:
                    st.caption("アクションがまだ登録されていません。")

            with col2:
                st.markdown("#### KPIサマリー")
                if state.kpis:
                    for kpi in state.kpis[:6]:
                        months_with_both = [
                            m for m in kpi.targets
                            if m in kpi.actuals
                        ]
                        if months_with_both:
                            latest = sorted(months_with_both)[-1]
                            tgt = kpi.targets[latest]
                            act = kpi.actuals[latest].value
                            delta = act - tgt
                            st.metric(
                                f"{kpi.name} ({latest})",
                                f"{act} {kpi.unit}",
                                delta=f"{delta:+.1f}",
                                delta_color="normal",
                            )
                        else:
                            st.metric(f"{kpi.name}", "実績未入力")
                else:
                    st.caption("KPIがまだ登録されていません。")

    # ------------------------------------------------------------------ #
    #  Tab 5: STEP Completion
    # ------------------------------------------------------------------ #
    with tab_done:
        st.subheader("✅ STEP 18 完了")

        # Show summary
        done_count = sum(1 for a in state.actions if a.status == "Done")
        total_count = len(state.actions)
        kpi_count = len(state.kpis)
        review_count = len(state.reviews)

        col1, col2, col3 = st.columns(3)
        col1.metric("アクション完了", f"{done_count}/{total_count}")
        col2.metric("KPI登録数", kpi_count)
        col3.metric("月次振り返り", f"{review_count}回")

        st.markdown("---")
        already_done = _steps.get("18") == "done"
        if already_done:
            st.success("✅ STEP 18 は完了済みです。")
        else:
            st.warning("⚠️ 実行計画の策定とKPI登録が完了したら、下のボタンでSTEPを完了してください。")
            if st.button("✅ 実行計画を確定してSTEP 18 完了", type="primary"):
                try:
                    import json as _j2
                    _res2 = _get_sb().table("clients").select("notes").eq("id", client_id).single().execute()
                    _n2 = _j2.loads(_res2.data.get("notes") or "{}") if isinstance(_res2.data.get("notes"), str) else (_res2.data.get("notes") or {})
                    _n2.setdefault("pipeline_steps", {})["18"] = "done"
                    _get_sb().table("clients").update({"notes": _j2.dumps(_n2, ensure_ascii=False)}).eq("id", client_id).execute()
                    st.success("🎉 STEP 18 完了！全18ステップが完了しました。")
                    st.balloons()
                except Exception as e:
                    st.error(f"保存エラー: {e}")

if __name__ == "__main__":
    app()
