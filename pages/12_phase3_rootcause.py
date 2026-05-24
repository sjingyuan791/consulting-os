"""
Phase 3: Root Cause Analysis
Identifies structural root causes using inductive reasoning and causal mapping.
"""
import streamlit as st
import plotly.graph_objects as go
from core.auth import check_auth
from core.style_utils import load_custom_css
from core.pipeline.stage2_root_cause import create_root_cause_engine


def render_role_badge(role: str):
    """Render a role badge for AI/Human/Collaborative."""
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
    
    st.title("🔍 Phase 3: 根本原因分析")
    st.markdown("帰納的推論による構造的根本原因の特定")
    
    render_progress_bar(2)
    st.divider()
    
    # STEP 8（SWOT分析）完了チェック
    client_id = st.session_state.get("client_id")
    if not client_id:
        st.warning("⚠️ プロジェクトを選択してください")
        return

    import json as _json
    from core.supabase_client import get_supabase_client
    _sb = get_supabase_client()
    _res = _sb.table("clients").select("notes, name, industry, location").eq("id", client_id).single().execute()
    _client_row = _res.data or {}
    _notes = _json.loads(_client_row.get("notes") or "{}") if isinstance(_client_row.get("notes"), str) else (_client_row.get("notes") or {})
    _steps = _notes.get("pipeline_steps", {})

    if _steps.get("8") != "done":
        st.warning("⚠️ STEP 8（SWOT分析）を完了してから進んでください")
        return

    # Initialize
    if "phase3_output" not in st.session_state:
        st.session_state.phase3_output = None
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺️ 因果マップ", "🎯 根本原因", "🔗 因果連鎖", "✅ 確認"
    ])
    
    with tab1:
        render_causal_map()
    
    with tab2:
        render_root_causes()
    
    with tab3:
        render_causal_chains()
    
    with tab4:
        render_phase3_confirmation()


def render_causal_map():
    """Render causal map visualization."""
    st.subheader("因果マップ構築")
    render_role_badge("ai")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("🔍 因果分析を実行", type="primary"):
            with st.spinner("クライアント固有の根本原因を分析中..."):
                input_data = {
                    "company_info": {
                        "name":     _client_row.get("name", ""),
                        "industry": _client_row.get("industry", ""),
                        "location": _client_row.get("location", ""),
                    },
                    "financial_analysis": _notes.get("financial_summary", {}),
                    "swot":              _notes.get("swot_manual", {}),
                    "internal_findings": _notes.get("internal_findings", {}),
                    "external_env":      _notes.get("external_env", {}),
                    "vision_mission":    _notes.get("vision_mission", {}),
                }

                import asyncio
                engine = create_root_cause_engine()
                try:
                    result = asyncio.run(engine.process(input_data))
                    st.session_state.phase3_output = result
                    st.success("✅ 分析完了")
                except Exception as e:
                    st.error(f"分析エラー: {type(e).__name__}: {e}")
    
    with col1:
        if st.session_state.phase3_output:
            output = st.session_state.phase3_output
            fig = create_causal_map_chart(output.causal_map)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("因果分析を実行してください")


def create_causal_map_chart(causal_map):
    """Create interactive causal map visualization."""
    import networkx as nx
    
    G = nx.DiGraph()
    
    for node in causal_map.nodes:
        G.add_node(node.id, label=node.label, node_type=node.node_type)
    
    for edge in causal_map.edges:
        G.add_edge(edge.source, edge.target, weight=edge.strength)
    
    # Layout
    pos = nx.spring_layout(G, seed=42, k=2)
    
    # Edge traces
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Node traces
    node_x, node_y, node_text, node_color = [], [], [], []
    color_map = {"root_cause": "#FF5722", "intermediate": "#FFC107", "symptom": "#2196F3", "external": "#9E9E9E"}
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_data = G.nodes[node]
        node_text.append(node_data.get('label', node)[:30])
        node_color.append(color_map.get(node_data.get('node_type', 'intermediate'), '#999'))
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=node_text,
        textposition="bottom center",
        marker=dict(
            size=20,
            color=node_color,
            line=dict(width=2, color='white')
        )
    )
    
    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20, l=5, r=5, t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        height=500,
                        title="因果マップ（🔴根本原因 🟡中間 🔵症状）"
                    ))
    return fig


def render_root_causes():
    """Render identified root causes."""
    st.subheader("根本原因の特定")
    render_role_badge("ai")
    
    if not st.session_state.phase3_output:
        st.info("因果分析を実行してください")
        return
    
    output = st.session_state.phase3_output
    
    # Primary root cause
    st.markdown("##### 🎯 主要根本原因")
    primary = output.primary_root_cause
    
    with st.expander(f"🔴 {primary.description}", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("確信度", f"{primary.confidence:.0%}")
        with col2:
            st.metric("カテゴリ", primary.category)
        with col3:
            st.metric("対処可能性", primary.addressability)
        
        st.markdown("**裏付けエビデンス:**")
        for ev in primary.supporting_evidence:
            st.write(f"- {ev}")
        
        st.markdown("**影響範囲:**")
        st.write(", ".join(primary.impact_scope[:5]))
    
    # Secondary causes
    if output.secondary_causes:
        st.markdown("##### 📌 副次的原因")
        for cause in output.secondary_causes:
            with st.expander(f"🟠 {cause.description}"):
                st.write(f"確信度: {cause.confidence:.0%} | カテゴリ: {cause.category}")
    
    # Human decision
    st.markdown("---")
    render_role_badge("human")
    st.markdown("##### 根本原因の最終決定")
    
    decision = st.radio(
        "主要根本原因として採用しますか？",
        options=[
            f"✅ 「{primary.description[:30]}...」を採用",
            "🔄 別の原因を選択",
            "✏️ 修正して採用"
        ],
        key="root_cause_decision"
    )
    
    if decision == "✏️ 修正して採用":
        st.session_state.modified_root_cause = st.text_area(
            "修正後の根本原因記述",
            value=primary.description,
            key="modified_cause"
        )


def render_causal_chains():
    """Render causal chains."""
    st.subheader("因果連鎖の可視化")
    render_role_badge("ai")
    
    if not st.session_state.phase3_output:
        st.info("因果分析を実行してください")
        return
    
    output = st.session_state.phase3_output
    
    if not output.causal_chains:
        st.info("因果連鎖が特定されていません")
        return
    
    for chain in output.causal_chains:
        st.markdown(f"**{chain.chain_id}:** {chain.description}")
        
        # Visual chain
        chain_html = " → ".join([f"[{n}]" for n in chain.nodes[:5]])
        st.code(chain_html)
        
        st.caption(f"連鎖強度: {chain.total_strength:.2f}")
        st.markdown("---")
    
    # Leverage points
    st.markdown("##### ⚡ レバレッジポイント")
    render_role_badge("ai")
    
    for lp in output.leverage_points:
        st.write(f"- {lp}")


def render_phase3_confirmation():
    """Render Phase 3 confirmation."""
    st.subheader("Phase 3 確認・承認")
    render_role_badge("collaborative")
    
    if not st.session_state.phase3_output:
        st.warning("因果分析を実行してから確認してください")
        return
    
    output = st.session_state.phase3_output
    
    st.markdown("##### 分析サマリー")
    st.info(output.analysis_summary)
    
    st.markdown("##### 確定根本原因")
    modified = st.session_state.get("modified_root_cause")
    final_cause = modified if modified else output.primary_root_cause.description
    st.success(f"🎯 {final_cause}")
    
    st.markdown("##### レバレッジポイント")
    for lp in output.leverage_points:
        st.write(f"- {lp}")
    
    # Checkpoint approval
    st.markdown("---")
    st.warning("⚠️ **チェックポイント**: Phase 4に進む前に、根本原因の確認が必要です。")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ 根本原因を承認してSTEP 10へ", type="primary", use_container_width=True):
            try:
                import json as _json2
                from core.supabase_client import get_supabase_client as _get_sb
                _sb2 = _get_sb()
                _res2 = _sb2.table("clients").select("notes").eq("id", client_id).single().execute()
                _n2 = _json2.loads(_res2.data.get("notes") or "{}") if isinstance(_res2.data.get("notes"), str) else (_res2.data.get("notes") or {})
                _n2.setdefault("pipeline_steps", {})["9"] = "done"
                _n2["root_cause"] = {
                    "confirmed_description": final_cause,
                    "primary": output.primary_root_cause.model_dump() if output.primary_root_cause else {},
                    "secondary": [c.model_dump() for c in output.secondary_causes],
                    "leverage_points": output.leverage_points,
                }
                _sb2.table("clients").update({"notes": _json2.dumps(_n2, ensure_ascii=False)}).eq("id", client_id).execute()
                _cache_key = f"pipeline_{client_id}"
                if _cache_key in st.session_state:
                    st.session_state[_cache_key]["9"] = "done"
                st.session_state.phase3_complete = True
                st.session_state.confirmed_root_cause = final_cause
                st.success("✅ STEP 9 完了！根本原因が確定されました。")
                st.balloons()
            except Exception as _e:
                st.error(f"保存エラー: {_e}")


if __name__ == "__main__":
    app()
