"""
AI Collaboration Workspace.
AI協働ワークスペース

機能:
1. AI提案のファクトチェック表示
2. 人間承認フロー
3. 修正・コメント機能
4. 監査ログ
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import json

from core.auth import check_auth
from core.style_utils import load_custom_css
from core.ai_quality_assurance import (
    validate_ai_response, FactCheckReport,
    HumanApprovalManager, format_fact_check_report
)
from core.ai_collaboration_manager import (
    AICollaborationManager, create_collaboration_session,
    quick_validate, format_verified_response_for_ui
)


def render_trust_badge(score: float) -> str:
    """信頼度バッジをレンダリング"""
    if score >= 90:
        return "🟢 高信頼"
    elif score >= 70:
        return "🟡 中信頼"
    elif score >= 50:
        return "🟠 要確認"
    else:
        return "🔴 低信頼"


def render_fact_check_card(report: FactCheckReport):
    """ファクトチェックカードをレンダリング"""
    # ヘッダー
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader("🔍 ファクトチェック結果")
    
    with col2:
        trust_badge = render_trust_badge(report.trust_score)
        st.markdown(f"**信頼度: {trust_badge}**")
    
    with col3:
        st.metric("スコア", f"{report.trust_score:.0f}/100")
    
    # サマリー
    st.info(report.summary)
    
    # 検証統計
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("検証済み", report.verified_count, help="ソースデータで確認された引用")
    col2.metric("未検証", report.unverified_count, help="自動検証対象外の引用")
    col3.metric("不一致", report.mismatch_count, help="ソースデータと異なる引用")
    col4.metric("⚠️ ハルシネ", report.hallucination_count, help="ソースに存在しない情報")
    
    # 重大な問題
    if report.critical_issues:
        st.error("**⚠️ 重大な問題:**")
        for issue in report.critical_issues:
            st.write(f"- {issue}")
    
    # 警告
    if report.warnings:
        with st.expander(f"⚠️ 警告 ({len(report.warnings)}件)"):
            for warning in report.warnings:
                st.warning(warning)
    
    # レビューポイント
    if report.review_points:
        st.markdown("**📋 確認ポイント:**")
        for point in report.review_points:
            st.write(f"- {point}")
    
    # 推奨
    st.success(f"**推奨:** {report.recommendation}")


def app():
    check_auth()
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()
    
    st.title("🤖 AI協働ワークスペース")
    st.caption("AI提案を検証・承認し、コンサルタント品質を保証")
    
    # セッション初期化
    if "ai_session" not in st.session_state:
        # サンプルソースデータ
        st.session_state.source_data = {
            "roa": 3.2,
            "roe": 8.5,
            "revenue": 100000000,
            "operating_profit": 5000000,
            "net_income": 3000000,
            "total_assets": 80000000,
            "net_assets": 35000000,
            "売上高": 100000000,
            "営業利益": 5000000,
            "純資産": 35000000,
        }
        st.session_state.ai_session = create_collaboration_session(st.session_state.source_data)
        st.session_state.approval_manager = HumanApprovalManager()
    
    # サイドバー: ソースデータ
    with st.sidebar:
        st.header("📊 ソースデータ")
        
        with st.expander("財務データを編集"):
            revenue = st.number_input("売上高（万円）", value=10000) * 10000
            op_profit = st.number_input("営業利益（万円）", value=500) * 10000
            roa = st.number_input("ROA (%)", value=3.2)
            
            if st.button("データを更新"):
                st.session_state.source_data.update({
                    "revenue": revenue,
                    "operating_profit": op_profit,
                    "roa": roa,
                    "売上高": revenue,
                    "営業利益": op_profit,
                })
                st.session_state.ai_session = create_collaboration_session(st.session_state.source_data)
                st.success("✅ 更新しました")
        
        st.divider()
        
        # セッション統計
        st.header("📈 セッション統計")
        summary = st.session_state.ai_session.get_session_summary()
        st.metric("処理レスポンス", summary["total_responses"])
        st.metric("承認済み", summary["approved_responses"])
        st.metric("保留中", summary["pending_approvals"])
        st.metric("平均信頼度", f"{summary['average_trust_score']:.1f}")
    
    # メインタブ
    tab1, tab2, tab3, tab4 = st.tabs([
        "✏️ 検証ワークスペース",
        "📋 承認キュー",
        "📜 監査ログ",
        "📖 使い方ガイド"
    ])
    
    # ==========================================
    # TAB 1: 検証ワークスペース
    # ==========================================
    with tab1:
        st.header("AI提案を検証")
        
        # AI回答入力
        ai_content = st.text_area(
            "AI生成コンテンツ",
            height=200,
            placeholder="""例:
当社のROAは3.2%【財務データ:2024年度】で、業界平均4.5%【業界基準:中小企業庁】を下回っています。
売上高は1億円【財務データ:2024年度】で、営業利益率は5%【計算:500万÷1億】です。
""",
            help="AI生成のテキストを貼り付けてください。【財務データ】【業界基準】等の引用タグが検証対象です。"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            content_type = st.selectbox(
                "コンテンツタイプ",
                ["strategy_proposal", "action_plan", "diagnosis", "forecast"],
                format_func=lambda x: {
                    "strategy_proposal": "📋 戦略提案",
                    "action_plan": "🎯 アクションプラン",
                    "diagnosis": "🔍 診断レポート",
                    "forecast": "📊 予測・シミュレーション"
                }.get(x, x)
            )
        
        with col2:
            auto_approve = st.checkbox(
                "高信頼度なら自動承認",
                value=False,
                help="信頼度90%以上の場合、自動的に承認します"
            )
        
        if st.button("🔍 検証を実行", type="primary", disabled=not ai_content):
            with st.spinner("ファクトチェック中..."):
                response = st.session_state.ai_session.process_response(
                    ai_content=ai_content,
                    content_type=content_type,
                    auto_approve_if_safe=auto_approve
                )
                st.session_state.current_response = response
        
        # 検証結果表示
        if "current_response" in st.session_state:
            response = st.session_state.current_response
            
            st.divider()
            
            # ステータスバナー
            ui_data = format_verified_response_for_ui(response)
            
            if response.is_approved:
                st.success(f"{ui_data['status_icon']} {ui_data['status_text']} - クライアントに表示可能")
            elif response.requires_human_review:
                st.warning(f"{ui_data['status_icon']} {ui_data['status_text']} - 承認が必要です")
            else:
                st.error(f"{ui_data['status_icon']} {ui_data['status_text']}")
            
            # バッジ表示
            badges_html = " ".join([
                f'<span style="background:{b["color"]}; color:white; padding:2px 8px; border-radius:12px; margin-right:4px; font-size:12px;">{b["name"]}</span>'
                for b in ui_data["badges"]
            ])
            st.markdown(badges_html, unsafe_allow_html=True)
            
            # ファクトチェック詳細
            if response.fact_check:
                render_fact_check_card(response.fact_check)
            
            # 承認アクション
            if response.requires_human_review and not response.is_approved:
                st.divider()
                st.subheader("📝 承認アクション")
                
                reviewer_name = st.text_input("レビュアー名", placeholder="田中コンサルタント")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("✅ 承認", type="primary", disabled=not reviewer_name):
                        st.session_state.ai_session.approve_response(
                            response.approval_request_id,
                            reviewer_name,
                            "確認OK"
                        )
                        st.success("✅ 承認しました")
                        st.rerun()
                
                with col2:
                    reject_reason = st.text_input("却下理由", placeholder="理由を入力")
                    if st.button("❌ 却下", disabled=not (reviewer_name and reject_reason)):
                        st.session_state.ai_session.reject_response(
                            response.approval_request_id,
                            reviewer_name,
                            reject_reason
                        )
                        st.error("❌ 却下しました")
                        st.rerun()
                
                with col3:
                    st.markdown("**修正して承認:**")
                    modified_content = st.text_area(
                        "修正内容",
                        value=response.content,
                        height=100,
                        key="modified_content"
                    )
                    modify_reason = st.text_input("修正理由", placeholder="修正理由を入力")
                    
                    if st.button("📝 修正承認", disabled=not (reviewer_name and modify_reason)):
                        new_response = st.session_state.ai_session.modify_and_approve(
                            response.approval_request_id,
                            reviewer_name,
                            modified_content,
                            modify_reason
                        )
                        if new_response:
                            st.session_state.current_response = new_response
                            st.success("✅ 修正して承認しました")
                            st.rerun()
    
    # ==========================================
    # TAB 2: 承認キュー
    # ==========================================
    with tab2:
        st.header("📋 保留中の承認")
        
        pending = st.session_state.ai_session.get_pending_approvals()
        
        if not pending:
            st.info("保留中の承認リクエストはありません")
        else:
            for req in pending:
                with st.expander(f"📄 {req.content_type} - {req.request_id}"):
                    st.write(f"**作成日時:** {req.created_at}")
                    st.write(f"**サマリー:** {req.content_summary}")
                    
                    if req.fact_check_report:
                        st.write(f"**信頼度:** {req.fact_check_report.trust_score:.0f}/100")
                    
                    if req.key_decisions:
                        st.write("**確認ポイント:**")
                        for kd in req.key_decisions:
                            st.write(f"- {kd}")
                    
                    # クイック承認
                    col1, col2 = st.columns(2)
                    reviewer = col1.text_input("レビュアー", key=f"rev_{req.request_id}")
                    
                    if col2.button("✅ 承認", key=f"approve_{req.request_id}", disabled=not reviewer):
                        st.session_state.ai_session.approve_response(req.request_id, reviewer)
                        st.rerun()
    
    # ==========================================
    # TAB 3: 監査ログ
    # ==========================================
    with tab3:
        st.header("📜 監査ログ")
        
        audit_log = st.session_state.ai_session.export_audit_log()
        
        if not audit_log:
            st.info("監査ログはまだありません")
        else:
            # フィルター
            action_filter = st.multiselect(
                "アクションでフィルタ",
                ["ai_generated", "approved", "rejected", "modified"],
                default=[]
            )
            
            filtered_log = audit_log
            if action_filter:
                filtered_log = [l for l in audit_log if l["action"] in action_filter]
            
            # テーブル表示
            log_df = pd.DataFrame(filtered_log)
            if not log_df.empty:
                display_cols = ["timestamp", "action", "actor", "content_type", "summary"]
                available_cols = [c for c in display_cols if c in log_df.columns]
                st.dataframe(log_df[available_cols], use_container_width=True)
            
            # エクスポート
            if st.button("📥 CSVエクスポート"):
                csv = pd.DataFrame(audit_log).to_csv(index=False)
                st.download_button(
                    label="ダウンロード",
                    data=csv,
                    file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    # ==========================================
    # TAB 4: 使い方ガイド
    # ==========================================
    with tab4:
        st.header("📖 AI協働ワークスペースの使い方")
        
        st.markdown("""
        ## 🎯 目的
        
        AI生成コンテンツの品質を保証し、**「ハルシネーション（嘘）を防ぐ」**ためのワークスペースです。
        
        ---
        
        ## 🔄 ワークフロー
        
        ```
        1. AI生成 → 2. 自動ファクトチェック → 3. 人間レビュー → 4. 承認/却下 → 5. クライアント表示
        ```
        
        ---
        
        ## 📋 引用タグの書き方
        
        AI回答に以下のタグを含めると、自動検証されます：
        
        | タグ | 例 | 検証 |
        |------|-----|------|
        | 【財務データ:年度】 | ROAは3.2%【財務データ:2024年度】 | ソースデータと照合 |
        | 【業界基準:出典】 | 業界平均4.5%【業界基準:中小企業庁】 | ベンチマークと照合 |
        | 【計算:式】 | 利益率5%【計算:500万÷1億】 | 手動確認 |
        | 【推論:根拠】 | コスト削減が必要【推論:利益率低下】 | 手動確認 |
        
        ---
        
        ## 🚦 信頼度スコア
        
        | スコア | バッジ | 意味 |
        |--------|--------|------|
        | 90+ | 🟢 高信頼 | 自動承認可能 |
        | 70-89 | 🟡 中信頼 | 軽微な確認推奨 |
        | 50-69 | 🟠 要確認 | 人間レビュー必須 |
        | 0-49 | 🔴 低信頼 | ハルシネーションの可能性 |
        
        ---
        
        ## 👥 責任の明確化
        
        - **AI生成**: 自動ログ記録
        - **人間承認**: レビュアー名を記録
        - **修正**: 修正履歴を保存
        
        これにより「誰が何を判断したか」を追跡可能です。
        """)


if __name__ == "__main__":
    app()
