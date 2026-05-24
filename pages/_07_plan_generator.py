import streamlit as st
import time
import os
import uuid
from core.auth import check_auth
from core.chapter_generator import ChapterGenerator
from core.docx_writer import DocxWriter
from core.ppt_writer import PPTWriter
from core.style_utils import load_custom_css

def app():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()
    
    if not check_auth():
        st.warning("ログインしてください。")
        return

    st.title("経営計画・資料作成 (Plan Generator)")
    
    # --- 1. Load Data ---
    client_id = st.session_state.get("client_id")
    if not client_id:
        st.warning("クライアントが選択されていません。")
        st.stop()
    
    # Try to get from session, otherwise fetch from DB
    if "strategy_context" not in st.session_state:
        from core.repos.strategy_run_repo import StrategyRunRepo
        from core.models import StrategyContext, DiagnosisReport
        
        repo = StrategyRunRepo()
        current_run = repo.get_current_strategy_run(client_id)
        
        if current_run:
            # Rehydrate from DB JSON
            try:
                pkg = current_run.get("final_strategy_package_json", {})
                
                # Reconstruct StrategyContext from Analysis Results
                # parsing the package back into Pydantic models helps, or accessing dict directly
                
                # 1. Financial Summary
                fin_health = pkg.get("financial_health", {})
                fin_score = fin_health.get("overall_health_score", 0)
                fin_summary = f"Overall Health Score: {fin_score}. "
                if fin_health.get("meta", {}).get("rules_fired"):
                    fin_summary += "Signals: " + ", ".join(fin_health["meta"]["rules_fired"])
                
                # 2. Internal/Sales Summary
                internal = pkg.get("internal_capability", {})
                comps = internal.get("core_competencies", [])
                gaps = internal.get("resource_gaps", [])
                sales_summary = f"Competencies: {', '.join(comps)}. Gaps: {', '.join(gaps)}."
                
                # 3. Market Summary
                external = pkg.get("external_intelligence", {})
                opps = external.get("opportunities", [])
                threats = external.get("threats", [])
                market_summary = f"Opportunities: {', '.join(opps)}. Threats: {', '.join(threats)}."
                
                # 4. Company Summary (Placeholder or from Client Name)
                # We might need to fetch client name, but for now generic
                company_summary = f"Strategic Analysis for Client {client_id[:8]}"
                
                # Construct
                ctx = StrategyContext(
                    company_summary=company_summary,
                    financial_summary=fin_summary,
                    sales_summary=sales_summary,
                    market_summary=market_summary,
                    kpi_tree=pkg.get("root_cause_diagnosis", {}).get("causal_structure", {}),
                    risks=threats,
                    opportunities=opps
                )
                
                st.session_state["strategy_context"] = ctx
                
                # Store Full Package for Writers
                st.session_state["strategy_package"] = pkg
                
                st.toast("戦略データを読み込みました。")
            except Exception as e:
                 st.error(f"戦略コンテキストの復元に失敗しました: {e}")
        else:
             st.warning("分析データが見つかりません。まずは「Analysis Pipeline」を実行してください。")
             if st.button("分析ページへ移動"):
                 st.switch_page("pages/03_analysis.py")
             return

    ctx = st.session_state["strategy_context"]
    # We use pkg dict for PPT writer now
    pkg = st.session_state.get("strategy_package")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. 詳細事業計画書 (Word)")
        st.info("銀行提出や社内稟議に使用できる、詳細な5章構成の事業計画ドキュメントを生成します。")
        if st.button("事業計画書を作成 (Word)", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            generator = ChapterGenerator(ctx, full_package=pkg)
            
            def update_progress(p, msg):
                progress_bar.progress(p)
                status_text.text(msg)
                
            full_content = generator.generate_full_plan_content(update_progress)
            
            # Write to Docx
            status_text.text("ドキュメントを生成中...")
            writer = DocxWriter()
            writer.add_title(f"経営改善計画書: {ctx.company_summary}")
            
            for chapter_title, sections in full_content.items():
                writer.add_chapter(chapter_title)
                for section_title, content in sections.items():
                    writer.add_section(section_title)
                    writer.add_content_from_markdown(content)
            
            if not os.path.exists("artifacts_out"):
                os.makedirs("artifacts_out")
            
            fname = f"Plan_{st.session_state.client_id}_{uuid.uuid4().hex[:8]}.docx"
            fpath = os.path.join("artifacts_out", fname)
            writer.save(fpath)
            
            progress_bar.progress(100)
            status_text.text("完了しました！")
            
            with open(fpath, "rb") as f:
                st.download_button("事業計画書をダウンロード", f, file_name=fname)

    with col2:
        st.subheader("2. 戦略プレゼン資料 (PowerPoint)")
        st.info("キックオフや役員報告に使用できる、要点を絞ったプロフェッショナルなスライド資料を生成します。")
        if st.button("スライド資料を作成 (PPT)"):
            if not pkg:
                st.error("スライド生成には分析パッケージが必要です。")
            else:
                with st.spinner("スライドを生成中..."):
                    ppt_writer = PPTWriter()
                    ppt_writer.create_slides(ctx, pkg)
                    
                    if not os.path.exists("artifacts_out"):
                        os.makedirs("artifacts_out")
                        
                    fname_ppt = f"Slides_{st.session_state.client_id}_{uuid.uuid4().hex[:8]}.pptx"
                    fpath_ppt = os.path.join("artifacts_out", fname_ppt)
                    ppt_writer.save(fpath_ppt)
                    
                    st.success("スライド生成完了！")
                    with open(fpath_ppt, "rb") as f:
                        st.download_button("PPTをダウンロード", f, file_name=fname_ppt)

if __name__ == "__main__":
    app()
