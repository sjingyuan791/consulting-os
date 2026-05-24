"""
Phase 7: KPI, Financial Planning, and Mid-Term Plan Generator
Final phase for generating the complete management plan.
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from core.auth import check_auth
from core.style_utils import load_custom_css
from core.pipeline.stage6_kpi_financial import create_kpi_financial_engine
from core.pipeline.stage7_plan_generator import create_plan_generator


def render_role_badge(role: str):
    colors = {
        "ai": ("🤖", "#4CAF50", "AI生成"),
        "human": ("👤", "#2196F3", "最終承認"),
        "collaborative": ("🤝", "#FF9800", "パラメータ調整")
    }
    icon, color, label = colors.get(role, ("❓", "#999", role))
    st.markdown(f"""
        <span style="background: {color}; color: white; padding: 2px 8px; 
        border-radius: 4px; font-size: 0.75rem; margin-right: 8px;">
        {icon} {label}</span>
    """, unsafe_allow_html=True)


def render_progress_bar(current: int):
    phases = ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5", "Phase 6", "Phase 7"]
    cols = st.columns(7)
    for i, (col, phase) in enumerate(zip(cols, phases)):
        with col:
            if i == current:
                st.markdown(f"**🔵 {phase}**")
            elif i < current:
                st.markdown(f"✅ {phase}")
            else:
                st.markdown(f"⚪ {phase}")


def app():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()
    
    if not check_auth():
        st.warning("ログインが必要です")
        return
    
    st.title("📋 Phase 7: 中期経営計画生成")
    st.markdown("KPIアーキテクチャ、財務計画、最終計画書の生成")
    
    render_progress_bar(6)
    st.divider()
    
    if not st.session_state.get("phase6_complete"):
        st.warning("⚠️ Phase 6を完了してから進んでください")
        return
    
    if "phase7_kpi_output" not in st.session_state:
        st.session_state.phase7_kpi_output = None
    if "phase7_plan_output" not in st.session_state:
        st.session_state.phase7_plan_output = None
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 KPIアーキテクチャ", "💰 財務シミュレーション", "📈 感度分析", "📋 計画書生成", "✅ 最終確認"
    ])
    
    with tab1:
        render_kpi_architecture()
    
    with tab2:
        render_financial_simulation()
    
    with tab3:
        render_sensitivity_analysis()
    
    with tab4:
        render_plan_generation()
    
    with tab5:
        render_final_confirmation()


def render_kpi_architecture():
    """Render KPI architecture builder."""
    st.subheader("KPIアーキテクチャ構築")
    render_role_badge("ai")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("📊 KPI計画を生成", type="primary"):
            with st.spinner("KPIと財務計画を生成中..."):
                phase6_output = st.session_state.get("phase6_output")
                financial_data = st.session_state.get("phase_data", {}).get("financial", {})
                
                input_data = {
                    "financial_statements": financial_data,
                    "stage5_output": {
                        "prioritized_actions": [a.model_dump() for a in phase6_output.prioritized_actions] if phase6_output else [],
                        "milestones": [m.model_dump() for m in phase6_output.milestones] if phase6_output else []
                    }
                }
                
                import asyncio
                engine = create_kpi_financial_engine()
                try:
                    result = asyncio.run(engine.compute(input_data))
                    st.session_state.phase7_kpi_output = result
                    st.success("✅ KPI計画生成完了")
                except Exception as e:
                    st.error(f"生成エラー: {type(e).__name__}")
    
    with col1:
        if not st.session_state.phase7_kpi_output:
            st.info("KPI計画を生成してください")
            return
        
        output = st.session_state.phase7_kpi_output
        kpi_plan = output.kpi_plan
        
        # Balanced Scorecard visualization
        st.markdown("##### バランススコアカード")
        
        bsc = kpi_plan.balanced_scorecard
        themes_text = " | ".join(bsc.strategic_themes)
        st.info(f"**戦略テーマ:** {themes_text}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**💰 財務視点**")
            for kpi in kpi_plan.strategic_kpis:
                if kpi.category == "financial":
                    st.write(f"• {kpi.name_ja}")
            
            st.markdown("**⚙️ プロセス視点**")
            for kpi in kpi_plan.strategic_kpis:
                if kpi.category == "process":
                    st.write(f"• {kpi.name_ja}")
        
        with col2:
            st.markdown("**👥 顧客視点**")
            for kpi in kpi_plan.strategic_kpis:
                if kpi.category == "customer":
                    st.write(f"• {kpi.name_ja}")
            
            st.markdown("**📚 学習・成長視点**")
            for kpi in kpi_plan.strategic_kpis:
                if kpi.category == "learning":
                    st.write(f"• {kpi.name_ja}")
        
        # KPI details
        st.markdown("---")
        st.markdown("##### 戦略KPI詳細")
        render_role_badge("collaborative")
        
        for kpi in kpi_plan.strategic_kpis[:6]:
            with st.expander(f"📊 {kpi.name_ja}"):
                st.write(f"**定義:** {kpi.definition}")
                st.write(f"**算出方法:** {kpi.calculation_method}")
                st.write(f"**データソース:** {kpi.data_source}")
                st.write(f"**更新頻度:** {kpi.update_frequency}")
                st.write(f"**責任者:** {kpi.owner}")
                
                # Targets
                st.markdown("**目標値:**")
                for year, target in kpi.targets.items():
                    st.write(f"  - {year}年: {target}{kpi.unit}")


def render_financial_simulation():
    """Render financial simulation dashboard."""
    st.subheader("財務シミュレーション")
    render_role_badge("ai")
    
    if not st.session_state.phase7_kpi_output:
        st.info("KPI計画を生成してください")
        return
    
    output = st.session_state.phase7_kpi_output
    projection = output.financial_projection
    
    # Revenue projection chart
    st.markdown("##### 売上高予測")
    
    years = [p.year for p in projection.revenue_projection]
    baseline = [p.baseline for p in projection.revenue_projection]
    optimistic = [p.optimistic for p in projection.revenue_projection]
    pessimistic = [p.pessimistic for p in projection.revenue_projection]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=optimistic, mode='lines', name='楽観シナリオ', line=dict(dash='dash', color='green')))
    fig.add_trace(go.Scatter(x=years, y=baseline, mode='lines+markers', name='基準シナリオ', line=dict(color='blue', width=3)))
    fig.add_trace(go.Scatter(x=years, y=pessimistic, mode='lines', name='悲観シナリオ', line=dict(dash='dash', color='red')))
    fig.update_layout(height=350, title="売上高予測（百万円）", xaxis_title="年度", yaxis_title="売上高")
    st.plotly_chart(fig, use_container_width=True)
    
    # Profit projection
    st.markdown("##### 利益予測")
    
    profit_baseline = [p.baseline for p in projection.profit_projection]
    profit_optimistic = [p.optimistic for p in projection.profit_projection]
    profit_pessimistic = [p.pessimistic for p in projection.profit_projection]
    
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=years, y=profit_baseline, name='基準シナリオ', marker_color='blue'))
    fig2.add_trace(go.Scatter(x=years, y=profit_optimistic, mode='lines+markers', name='楽観', line=dict(color='green')))
    fig2.add_trace(go.Scatter(x=years, y=profit_pessimistic, mode='lines+markers', name='悲観', line=dict(color='red')))
    fig2.update_layout(height=300, title="利益予測（百万円）")
    st.plotly_chart(fig2, use_container_width=True)
    
    # Investment plan
    st.markdown("##### 投資計画")
    inv_plan = output.investment_plan
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("総投資額", f"{inv_plan.total_investment:.0f}百万円")
        
        st.markdown("**資金調達:**")
        for source in inv_plan.funding_sources:
            st.write(f"• {source.get('source')}: {source.get('amount'):.0f}百万円")
    
    with col2:
        inv_data = [{"項目": i.name, "金額": i.amount, "カテゴリ": i.category} for i in inv_plan.investments]
        fig3 = px.pie(inv_data, values='金額', names='項目', title='投資内訳')
        fig3.update_layout(height=300)
        st.plotly_chart(fig3, use_container_width=True)


def render_sensitivity_analysis():
    """Render sensitivity analysis."""
    st.subheader("感度分析")
    render_role_badge("ai")
    
    if not st.session_state.phase7_kpi_output:
        st.info("KPI計画を生成してください")
        return
    
    output = st.session_state.phase7_kpi_output
    sensitivity = output.sensitivity_analysis
    
    if not sensitivity:
        st.info("感度分析データがありません")
        return
    
    st.markdown("##### シナリオ別影響分析")
    
    for scenario in sensitivity.scenarios:
        impact_color = "🔴" if scenario.impact_on_profit < 0 else "🟢"
        
        with st.expander(f"{impact_color} {scenario.name}"):
            st.write(f"**説明:** {scenario.description}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("利益への影響", f"{scenario.impact_on_profit:+.0f}百万円")
            with col2:
                st.metric("CFへの影響", f"{scenario.impact_on_cash:+.0f}百万円")
            
            st.markdown("**変数変動:**")
            for var, change in scenario.variable_changes.items():
                st.write(f"• {var}: {change:+.0%}")
    
    # Critical thresholds
    st.markdown("---")
    st.markdown("##### 損益分岐点")
    
    thresholds = sensitivity.breakeven_thresholds
    col1, col2 = st.columns(2)
    with col1:
        st.warning(f"売上減少限界: {thresholds.get('revenue_decline', 0)*100:.0f}%")
    with col2:
        st.warning(f"コスト増加限界: {thresholds.get('cost_increase', 0)*100:.0f}%")


def render_plan_generation():
    """Render mid-term plan generation."""
    st.subheader("中期経営計画書の生成")
    render_role_badge("ai")
    
    if not st.session_state.phase7_kpi_output:
        st.warning("先にKPI計画を生成してください")
        return
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("📋 計画書を生成", type="primary"):
            with st.spinner("中期経営計画書を生成中..."):
                # Collect all phase outputs
                all_outputs = {
                    "stage1_output": st.session_state.get("phase2_output", {}),
                    "stage2_output": st.session_state.get("phase3_output", {}),
                    "stage3_output": st.session_state.get("phase4_output", {}),
                    "stage4_output": st.session_state.get("phase5_output", {}),
                    "stage5_output": st.session_state.get("phase6_output", {}),
                    "stage6_output": st.session_state.get("phase7_kpi_output", {}),
                    "client_name": st.session_state.get("client_name", "クライアント企業"),
                    "plan_period": "2025-2027"
                }
                
                import asyncio
                engine = create_plan_generator()
                try:
                    result = asyncio.run(engine.compute(all_outputs))
                    st.session_state.phase7_plan_output = result
                    st.success("✅ 計画書生成完了")
                except Exception as e:
                    st.error(f"生成エラー: {type(e).__name__}")
    
    with col1:
        if not st.session_state.phase7_plan_output:
            st.info("計画書を生成してください")
            return
        
        plan = st.session_state.phase7_plan_output
        
        # Executive Summary
        st.markdown("##### エグゼクティブサマリー")
        st.info(plan.executive_summary)
        
        # Plan structure preview
        st.markdown("---")
        st.markdown("##### 計画書構成")
        
        sections = [
            ("🎯 戦略概要", plan.strategy_section),
            ("📊 施策ロードマップ", plan.roadmap_section),
            ("💰 財務計画", plan.financial_section),
            ("📈 KPI計画", plan.kpi_section),
            ("⚠️ リスク管理", plan.risk_section)
        ]
        
        for title, section in sections:
            with st.expander(title):
                if isinstance(section, str):
                    st.write(section[:500] + "..." if len(section) > 500 else section)
                elif isinstance(section, dict):
                    st.json(section)


def render_final_confirmation():
    """Render final confirmation and approval."""
    st.subheader("最終確認・承認")
    render_role_badge("human")
    
    if not st.session_state.phase7_plan_output:
        st.warning("計画書を生成してから最終確認してください")
        return
    
    plan = st.session_state.phase7_plan_output
    
    st.markdown("##### 中期経営計画書サマリー")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**タイトル:** {plan.title}")
        st.write(f"**計画期間:** {plan.plan_period}")
        st.write(f"**生成日:** {plan.generated_at.strftime('%Y年%m月%d日')}")
    
    with col2:
        st.write(f"**バージョン:** {plan.version}")
        st.write(f"**ステータス:** ドラフト")
    
    # Final summary
    st.markdown("---")
    st.markdown("##### エグゼクティブサマリー")
    st.success(plan.executive_summary)
    
    # Export options
    st.markdown("---")
    st.markdown("##### エクスポートオプション")
    render_role_badge("collaborative")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📄 PDF出力", use_container_width=True):
            st.info("PDF生成機能（実装予定）")
    with col2:
        if st.button("📊 PowerPoint出力", use_container_width=True):
            st.info("PowerPoint生成機能（実装予定）")
    with col3:
        if st.button("📑 JSON出力", use_container_width=True):
            st.json(plan.model_dump(mode='json', exclude_none=True))
    
    # Final approval
    st.markdown("---")
    st.warning("⚠️ **最終チェックポイント**: 計画書の最終承認")
    
    approval_confirm = st.checkbox("上記の内容を確認し、中期経営計画として承認します", key="final_approval")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if approval_confirm:
            if st.button("✅ 中期経営計画を最終承認", type="primary", use_container_width=True):
                _cid7 = st.session_state.get("client_id")
                if _cid7:
                    try:
                        import json as _j7
                        from core.supabase_client import get_supabase_client as _gsb7
                        _sb7 = _gsb7()
                        _r7 = _sb7.table("clients").select("notes").eq("id", _cid7).single().execute()
                        _n7 = _j7.loads(_r7.data.get("notes") or "{}") if isinstance(_r7.data.get("notes"), str) else (_r7.data.get("notes") or {})
                        _n7.setdefault("pipeline_steps", {})["14"] = "done"
                        _sb7.table("clients").update({"notes": _j7.dumps(_n7, ensure_ascii=False)}).eq("id", _cid7).execute()
                        _ck7 = f"pipeline_{_cid7}"
                        if _ck7 in st.session_state:
                            st.session_state[_ck7]["14"] = "done"
                    except Exception:
                        pass
                st.session_state.pipeline_complete = True
                st.success("🎉 中期経営計画が正式に承認されました！")
                st.balloons()

                st.markdown("---")
                st.info("計画書はデータベースに保存されました。")
        else:
            st.button("✅ 中期経営計画を最終承認", type="secondary", disabled=True, use_container_width=True)
            st.caption("承認するには上のチェックボックスをオンにしてください")


if __name__ == "__main__":
    app()
