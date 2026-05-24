"""
Phase 4: Hypothesis Verification Planner
Designs validation activities for root cause hypotheses.
"""
import streamlit as st
from core.auth import check_auth
from core.style_utils import load_custom_css
from core.pipeline.stage3_verification import create_verification_planner


def render_role_badge(role: str):
    colors = {
        "ai": ("🤖", "#4CAF50", "AI生成"),
        "human": ("👤", "#2196F3", "人間実施"),
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
    
    st.title("🔬 Phase 4: 仮説検証計画")
    st.markdown("根本原因仮説のための検証アクティビティ設計")
    
    render_progress_bar(3)
    st.divider()
    
    if not st.session_state.get("phase3_complete"):
        st.warning("⚠️ Phase 3を完了してから進んでください")
        return
    
    if "phase4_output" not in st.session_state:
        st.session_state.phase4_output = None
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 データ要件", "🎤 インタビュー計画", "📊 検証方法", "✅ 確認"
    ])
    
    with tab1:
        render_data_requirements()
    
    with tab2:
        render_interview_planning()
    
    with tab3:
        render_validation_methods()
    
    with tab4:
        render_phase4_confirmation()


def render_data_requirements():
    """Render data requirements section."""
    st.subheader("追加データ要件の生成")
    render_role_badge("ai")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("📋 検証計画を生成", type="primary"):
            with st.spinner("検証計画を生成中..."):
                phase3_output = st.session_state.get("phase3_output")
                
                previous_output = {
                    "primary_root_cause": phase3_output.primary_root_cause.model_dump() if phase3_output else {},
                    "secondary_causes": [c.model_dump() for c in phase3_output.secondary_causes] if phase3_output else []
                }
                
                import asyncio
                engine = create_verification_planner()
                try:
                    result = asyncio.run(engine.process({}, previous_output))
                    st.session_state.phase4_output = result
                    st.success("✅ 検証計画生成完了")
                except Exception as e:
                    st.error(f"生成エラー: {type(e).__name__}")
    
    with col1:
        if not st.session_state.phase4_output:
            st.info("検証計画を生成してください")
            return
        
        output = st.session_state.phase4_output
        
        # Priority grouping
        critical = [d for d in output.required_additional_data if d.priority == "critical"]
        important = [d for d in output.required_additional_data if d.priority == "important"]
        nice_to_have = [d for d in output.required_additional_data if d.priority == "nice_to_have"]
        
        if critical:
            st.markdown("##### 🔴 必須データ (Critical)")
            for req in critical:
                with st.expander(f"📊 {req.data_type}"):
                    st.write(f"**説明:** {req.description}")
                    st.write(f"**ソース:** {req.source}")
                    st.write(f"**取得方法:** {req.acquisition_method}")
                    st.write(f"**想定工数:** {req.estimated_effort}")
                    
                    render_role_badge("human")
                    st.checkbox("データ収集完了", key=f"data_{req.id}")
        
        if important:
            st.markdown("##### 🟠 重要データ (Important)")
            for req in important:
                with st.expander(f"📊 {req.data_type}"):
                    st.write(f"**説明:** {req.description}")
                    st.checkbox("データ収集完了", key=f"data_{req.id}")


def render_interview_planning():
    """Render interview planning section."""
    st.subheader("インタビュー計画")
    render_role_badge("ai")
    
    if not st.session_state.phase4_output:
        st.info("検証計画を生成してください")
        return
    
    output = st.session_state.phase4_output
    
    # Group by target role
    questions_by_role = {}
    for q in output.interview_questions:
        if q.target_role not in questions_by_role:
            questions_by_role[q.target_role] = []
        questions_by_role[q.target_role].append(q)
    
    for role, questions in questions_by_role.items():
        st.markdown(f"##### 👤 {role}")
        
        for q in questions[:3]:  # Limit display
            with st.expander(q.question[:50] + "..."):
                st.markdown(f"**質問:** {q.question}")
                st.markdown(f"**期待インサイト:** {q.expected_insight}")
                
                if q.follow_up_questions:
                    st.markdown("**フォローアップ質問:**")
                    for fq in q.follow_up_questions:
                        st.write(f"- {fq}")
                
                # Human feedback
                st.markdown("---")
                render_role_badge("human")
                st.text_area("インタビュー結果メモ", key=f"interview_{q.id}", height=80)
        
        st.markdown("---")


def render_validation_methods():
    """Render validation methods section."""
    st.subheader("検証方法")
    render_role_badge("ai")
    
    if not st.session_state.phase4_output:
        st.info("検証計画を生成してください")
        return
    
    output = st.session_state.phase4_output
    
    # Group by method type
    quant_methods = [m for m in output.validation_methods if m.method_type == "quantitative"]
    qual_methods = [m for m in output.validation_methods if m.method_type == "qualitative"]
    mixed_methods = [m for m in output.validation_methods if m.method_type == "mixed"]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("##### 📊 定量的検証")
        for m in quant_methods[:2]:
            with st.container():
                st.markdown(f"**{m.description}**")
                st.caption(f"成功基準: {m.success_criteria}")
                st.caption(f"所要時間: {m.estimated_duration}")
    
    with col2:
        st.markdown("##### 🎤 定性的検証")
        for m in qual_methods[:2]:
            with st.container():
                st.markdown(f"**{m.description}**")
                st.caption(f"成功基準: {m.success_criteria}")
    
    with col3:
        st.markdown("##### 🔄 混合検証")
        for m in mixed_methods[:2]:
            with st.container():
                st.markdown(f"**{m.description}**")
                st.caption(f"成功基準: {m.success_criteria}")
    
    # Timeline
    st.markdown("---")
    st.markdown("##### ⏱️ 想定スケジュール")
    st.info(output.verification_timeline)


def render_phase4_confirmation():
    """Render Phase 4 confirmation."""
    st.subheader("Phase 4 確認")
    render_role_badge("collaborative")
    
    if not st.session_state.phase4_output:
        st.warning("検証計画を生成してから確認してください")
        return
    
    output = st.session_state.phase4_output
    
    st.markdown("##### 検証計画サマリー")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("必要データ項目", len(output.required_additional_data))
    with col2:
        st.metric("インタビュー質問数", len(output.interview_questions))
    with col3:
        st.metric("検証方法", len(output.validation_methods))
    
    st.markdown("##### 想定リソース")
    res = output.resource_requirements
    st.write(f"- 想定工数: {res.get('estimated_person_days', 'N/A')}人日")
    st.write(f"- 必要ロール: {', '.join(res.get('required_roles', []))}")
    
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ 検証計画を承認してPhase 5へ", type="primary", use_container_width=True):
            st.session_state.phase4_complete = True
            st.success("✅ Phase 4 完了！")
            st.balloons()


if __name__ == "__main__":
    app()
