"""
Phase 6: HOW-Tree Tactical Generation
Generates tactical execution options via deductive HOW trees.
"""
import streamlit as st
import plotly.graph_objects as go
from core.auth import check_auth
from core.style_utils import load_custom_css
from core.pipeline.stage5_tactical import create_tactical_generator


def render_role_badge(role: str):
    colors = {
        "ai": ("🤖", "#4CAF50", "AI生成"),
        "human": ("👤", "#2196F3", "人間決定"),
        "collaborative": ("🤝", "#FF9800", "協働確認")
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
    
    st.title("🔧 Phase 6: HOW-Tree施策生成")
    st.markdown("戦略の施策オプションと実行計画への落とし込み")
    
    render_progress_bar(5)
    st.divider()
    
    if not st.session_state.get("phase5_complete"):
        st.warning("⚠️ Phase 5を完了してから進んでください")
        return
    
    if "phase6_output" not in st.session_state:
        st.session_state.phase6_output = None
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💡 施策オプション", "🌳 HOW-Tree", "📋 優先アクション", "📅 マイルストーン", "✅ 確認"
    ])
    
    with tab1:
        render_tactical_options()
    
    with tab2:
        render_how_trees()
    
    with tab3:
        render_prioritized_actions()
    
    with tab4:
        render_milestones()
    
    with tab5:
        render_phase6_confirmation()


def render_tactical_options():
    """Render tactical options section."""
    st.subheader("施策オプションの生成")
    render_role_badge("ai")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("🔧 施策を生成", type="primary"):
            with st.spinner("施策オプションを生成中..."):
                phase5_output = st.session_state.get("phase5_output")
                
                input_data = {
                    "stage4_output": {
                        "corporate_strategy": phase5_output.corporate_strategy.model_dump() if phase5_output else {},
                        "functional_strategies": [f.model_dump() for f in phase5_output.functional_strategies] if phase5_output else []
                    }
                }
                
                import asyncio
                engine = create_tactical_generator()
                try:
                    result = asyncio.run(engine.process(input_data))
                    st.session_state.phase6_output = result
                    st.success("✅ 施策生成完了")
                except Exception as e:
                    st.error(f"生成エラー: {type(e).__name__}")
    
    with col1:
        if not st.session_state.phase6_output:
            st.info("施策を生成してください")
            return
        
        output = st.session_state.phase6_output
        
        for opt_set in output.tactical_option_sets:
            st.markdown(f"##### {opt_set.strategy_name}")
            
            cols = st.columns(len(opt_set.options))
            for i, (col, opt) in enumerate(zip(cols, opt_set.options)):
                with col:
                    is_recommended = opt.id == opt_set.recommended_option
                    
                    if is_recommended:
                        st.markdown("⭐ **推奨**")
                    
                    with st.container():
                        st.markdown(f"**{opt.name}**")
                        st.write(opt.description[:80])
                        
                        # Metrics
                        st.metric("想定コスト", f"{opt.estimated_cost:.0f}百万円")
                        st.metric("期待効果", f"{opt.estimated_impact:.0%}")
                        
                        # Pros/Cons
                        with st.expander("詳細"):
                            st.markdown("**メリット:**")
                            for pro in opt.pros:
                                st.write(f"✅ {pro}")
                            st.markdown("**デメリット:**")
                            for con in opt.cons:
                                st.write(f"⚠️ {con}")
                        
                        # Selection
                        render_role_badge("human")
                        st.radio(
                            "選択",
                            ["未選択", "選択"],
                            key=f"opt_{opt.id}",
                            horizontal=True
                        )
            
            st.markdown("---")


def render_how_trees():
    """Render HOW tree visualization."""
    st.subheader("HOW-Tree構造")
    render_role_badge("ai")
    
    if not st.session_state.phase6_output:
        st.info("施策を生成してください")
        return
    
    output = st.session_state.phase6_output
    
    if not output.how_trees:
        st.info("HOW-Treeがありません")
        return
    
    for tree in output.how_trees[:3]:
        with st.expander(f"🌳 {tree.root_objective[:50]}...", expanded=True):
            # Create tree visualization
            fig = create_how_tree_chart(tree)
            st.plotly_chart(fig, use_container_width=True)
            
            # List leaf actions
            leaf_actions = tree.get_leaf_actions()
            if leaf_actions:
                st.markdown("**リーフアクション（具体的なタスク）:**")
                for leaf in leaf_actions[:5]:
                    st.write(f"→ {leaf.description}")


def create_how_tree_chart(tree):
    """Create HOW tree visualization."""
    fig = go.Figure()
    
    # Calculate positions
    nodes_by_level = {}
    for node in tree.nodes:
        level = node.level
        if level not in nodes_by_level:
            nodes_by_level[level] = []
        nodes_by_level[level].append(node)
    
    positions = {}
    max_width = max(len(nodes) for nodes in nodes_by_level.values())
    
    for level, nodes in nodes_by_level.items():
        y = 1 - level * 0.3
        width = len(nodes)
        for i, node in enumerate(nodes):
            x = (i - (width - 1) / 2) / max(max_width, 1) * 0.8 + 0.5
            positions[node.id] = (x, y)
    
    # Draw edges
    for node in tree.nodes:
        if node.parent_id and node.parent_id in positions:
            x0, y0 = positions[node.parent_id]
            x1, y1 = positions.get(node.id, (0.5, 0.5))
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1],
                mode='lines',
                line=dict(color='#888', width=1),
                hoverinfo='none',
                showlegend=False
            ))
    
    # Draw nodes
    node_x, node_y, node_text, node_color = [], [], [], []
    for node in tree.nodes:
        if node.id in positions:
            x, y = positions[node.id]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node.description[:25])
            
            # Color by level
            colors = ["#2962FF", "#4CAF50", "#FF9800", "#9C27B0"]
            node_color.append(colors[min(node.level, len(colors) - 1)])
    
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        marker=dict(size=30, color=node_color),
        text=node_text,
        textposition="bottom center",
        textfont=dict(size=9),
        hoverinfo='text',
        showlegend=False
    ))
    
    fig.update_layout(
        showlegend=False,
        height=350,
        xaxis=dict(visible=False, range=[0, 1]),
        yaxis=dict(visible=False, range=[0, 1.1]),
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)"
    )
    
    return fig


def render_prioritized_actions():
    """Render prioritized actions."""
    st.subheader("優先順位付きアクション")
    render_role_badge("ai")
    
    if not st.session_state.phase6_output:
        st.info("施策を生成してください")
        return
    
    output = st.session_state.phase6_output
    
    # Quick wins
    if output.quick_wins:
        st.markdown("##### ⚡ クイックウィン")
        for qw in output.quick_wins:
            st.success(f"🎯 {qw}")
    
    # Prioritized list
    st.markdown("##### 📋 優先アクションリスト")
    
    for i, action in enumerate(output.prioritized_actions[:10], 1):
        with st.expander(f"{i}. {action.action[:50]}...", expanded=(i <= 3)):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("優先度スコア", f"{action.priority_score:.2f}")
            with col2:
                st.metric("期待効果", f"{action.impact:.0%}")
            with col3:
                st.metric("必要工数", f"{action.effort:.0%}")
            
            st.write(f"**担当:** {action.owner}")
            st.write(f"**タイムライン:** {action.timeline}")
            
            if action.quickwin:
                st.success("⚡ クイックウィン対象")


def render_milestones():
    """Render milestones and timeline."""
    st.subheader("マイルストーン計画")
    render_role_badge("ai")
    
    if not st.session_state.phase6_output:
        st.info("施策を生成してください")
        return
    
    output = st.session_state.phase6_output
    
    # Milestone timeline
    for ms in output.milestones:
        st.markdown(f"##### 📍 {ms.name}")
        st.write(f"**目標日:** {ms.target_date}")
        
        st.markdown("**成果物:**")
        for d in ms.deliverables:
            st.write(f"  - {d}")
        
        st.markdown("---")
    
    # Implementation phases
    st.markdown("##### 📅 実行フェーズ")
    
    for phase in output.implementation_phases:
        with st.expander(f"Phase {phase.get('phase')}: {phase.get('name')}"):
            st.write(f"**期間:** {phase.get('duration')}")
            st.write(f"**フォーカス:** {phase.get('focus')}")
            st.write(f"**リソース配分:** {phase.get('resource_allocation', 0):.0%}")
            
            if phase.get("actions"):
                st.markdown("**主要アクション:**")
                for act in phase.get("actions", [])[:3]:
                    st.write(f"→ {act}")


def render_phase6_confirmation():
    """Render Phase 6 confirmation."""
    st.subheader("Phase 6 確認")
    render_role_badge("collaborative")
    
    if not st.session_state.phase6_output:
        st.warning("施策を生成してから確認してください")
        return
    
    output = st.session_state.phase6_output
    
    st.markdown("##### 施策計画サマリー")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("施策オプション", len(output.tactical_option_sets))
    with col2:
        st.metric("HOW-Tree", len(output.how_trees))
    with col3:
        st.metric("優先アクション", len(output.prioritized_actions))
    with col4:
        st.metric("マイルストーン", len(output.milestones))
    
    st.markdown("##### クイックウィン")
    for qw in output.quick_wins:
        st.write(f"⚡ {qw}")
    
    # Checkpoint
    st.markdown("---")
    st.warning("⚠️ **チェックポイント**: 施策優先度の確認が必要です。")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ 施策計画を承認してPhase 7へ", type="primary", use_container_width=True):
            _cid6 = st.session_state.get("client_id")
            if _cid6:
                try:
                    import json as _j6
                    from core.supabase_client import get_supabase_client as _gsb6
                    _sb6 = _gsb6()
                    _r6 = _sb6.table("clients").select("notes").eq("id", _cid6).single().execute()
                    _n6 = _j6.loads(_r6.data.get("notes") or "{}") if isinstance(_r6.data.get("notes"), str) else (_r6.data.get("notes") or {})
                    _n6.setdefault("pipeline_steps", {})["13"] = "done"
                    _sb6.table("clients").update({"notes": _j6.dumps(_n6, ensure_ascii=False)}).eq("id", _cid6).execute()
                    _ck6 = f"pipeline_{_cid6}"
                    if _ck6 in st.session_state:
                        st.session_state[_ck6]["13"] = "done"
                except Exception:
                    pass
            st.session_state.phase6_complete = True
            st.success("✅ Phase 6 完了！")
            st.balloons()


if __name__ == "__main__":
    app()
