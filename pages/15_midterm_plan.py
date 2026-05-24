"""
Page 20: Mid-Term Management Plan Generator (Dual-Pane)
中期経営計画書生成ページ

AIと協働しながら中期経営計画を策定する1画面デュアルペインUI。
左ペイン：ドキュメントエディタ（チャプター単位）
右ペイン：AIチャット & コンテキストプレビュー
"""
import streamlit as st
import json
import os
import uuid
import asyncio
from datetime import datetime
from typing import Optional, List

from core.auth import check_auth
from core.style_utils import load_custom_css
import core.schemas.midterm_plan_schema
import core.midterm_plan_engine
import importlib
try:
    importlib.reload(core.schemas.midterm_plan_schema)
    importlib.reload(core.midterm_plan_engine)
    print("Reloaded midterm_plan_schema and engine")
except Exception as e:
    print(f"Failed to reload modules: {e}")

from core.midterm_plan_engine import create_midterm_plan_engine, SECTION_DEFINITIONS, MidtermPlanDocument, ChapterStatus, MidtermPlanSection
from core.schemas.midterm_plan_schema import ChapterState
from core.midterm_plan_store import save_midterm_plan, load_midterm_plan
from core.docx_writer import DocxWriter
from core.ppt_writer import PPTWriter

# --- Constants ---
PAGE_TITLE = "中期経営計画書 策定ワークスペース"

# UI Components
from pages.components.midterm_plan_ui import (
    SECTION_SHORT_LABELS,
    render_section_header,
    render_chapter_nav,
    render_audit_log,
    render_stats_dashboard,
    _get_status_icon,
    _get_status_label,
    render_diff_view
)
from core.financial_engine import run_financial_engine
import pandas as pd

def render_data_diagnosis(pipeline_data) -> Optional[list]:
    """
    サイドバーに財務診断とデータ不足提案を表示し、計算された指標を返す
    (Unified with core.financial_engine)
    """
    calculated_metrics = None
    
    with st.sidebar:
        st.divider()
        st.markdown("### 📊 データ診断")
        
        # 1. Financial Diagnosis
        financial_data = pipeline_data.get("financial", {})
        if financial_data:
            with st.expander("財務状況サマリー", expanded=False):
                try:
                    # Convert dict to DataFrame if needed
                    fin_records = []
                    if isinstance(financial_data, list):
                        if len(financial_data) > 0 and isinstance(financial_data[0], dict) and "records" in financial_data[0]:
                             # New Format: List of File Objects
                             target = next((f for f in financial_data if f.get("type") == "financial_standard"), financial_data[0])
                             fin_records = target.get("records", [])
                        else:
                             # Old Format: List of Records
                             fin_records = financial_data
                    elif isinstance(financial_data, dict) and "records" in financial_data:
                        fin_records = financial_data["records"]
                    else:
                        fin_records = [financial_data] if isinstance(financial_data, dict) else []

                    df = pd.DataFrame(fin_records) if fin_records else pd.DataFrame()

                    if not df.empty:
                        # Normalize first!
                        from core.normalizers import clean_financial_df
                        df = clean_financial_df(df)
                        
                        # Use Unified Engine
                        output = run_financial_engine(df)
                        metrics = output.metrics_history
                        
                        if metrics:
                            calculated_metrics = metrics
                            last = metrics[-1] # Most recent year
                            
                            # Display Key Metrics
                            st.metric("売上高成長率", f"{last.revenue_growth:.1%}")
                            st.metric("営業利益率", f"{last.operating_margin:.1%}")
                            if last.equity_ratio is not None:
                                st.metric("自己資本比率", f"{last.equity_ratio:.1%}")
                            
                            # Advanced Metrics (if available)
                            if last.simplified_cf is not None:
                                st.metric("簡易CF", f"{last.simplified_cf:,.0f}")
                            
                            # Simple Chart
                            chart_df = pd.DataFrame([m.model_dump() for m in metrics])
                            if not chart_df.empty:
                                st.caption("売上高推移")
                                st.line_chart(chart_df.set_index("year")["revenue"])
                        else:
                            st.warning("財務指標を計算できませんでした。")
                    else:
                        st.warning("財務データ形式が不正です。")
                except Exception as e:
                    st.error(f"財務診断エラー: {e}")
        else:
            st.info("財務データがアップロードされていません。")

        # 2. Start Missing Data Suggestions
        missing_items = []
        
        # Check Financials
        if not financial_data:
            missing_items.append("📄 財務データ (PL/BS)")
        
        # Check External
        ext_data = pipeline_data.get("external", {})
        if not ext_data:
            missing_items.append("📄 市場・競合データ")
            
        # Check Internal
        int_data = pipeline_data.get("internal", {})
        if not int_data:
            missing_items.append("📄 内部規定・組織図")
            
        if missing_items:
            st.warning(f"⚠️ 精度向上のため、以下のデータを追加してください:\n" + "\n".join([f"- {i}" for i in missing_items]))
            if st.button("データアップロード画面へ"):
                st.switch_page("pages/02_data_ingest.py")
        else:
            st.success("✅ データは充実しています")
            
    return calculated_metrics


def get_engine(client_id, pipeline_data, guardrails):
    return create_midterm_plan_engine(
        pipeline_data=pipeline_data,
        guardrails=guardrails,
        client_id=client_id
    )

def _build_downstream_map() -> dict:
    """SECTION_DEFINITIONSのreferencesを逆引きし、{section_id: [downstream_ids]}を生成"""
    downstream: dict = {d["id"]: [] for d in SECTION_DEFINITIONS}
    for sec_def in SECTION_DEFINITIONS:
        for upstream_id in sec_def["references"]:
            if upstream_id in downstream:
                downstream[upstream_id].append(sec_def["id"])
    return downstream

DOWNSTREAM_MAP = _build_downstream_map()

_FEEDBACK_TYPE_OPTIONS = {
    "direction_change": "方向性の変更",
    "fact_correction": "事実修正",
    "tone_adjustment": "トーン調整",
    "info_addition": "情報追加",
    "other": "その他",
}


async def run_generation(engine, section_id, locked_chapters, user_instruction, current_content):
    return await engine.generate_single_chapter(
        chapter_id=section_id,
        locked_chapters=locked_chapters,
        user_input=user_instruction,
        current_content=current_content
    )

async def run_chat(engine, message, locked_chapters, current_chapter):
    return await engine.chat_with_context(message, locked_chapters, current_chapter)





def app():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()

    if not check_auth():
        st.warning("ログインしてください。")
        return

    # Check for selected client
    client_id = st.session_state.get("client_id")
    if not client_id:
        st.warning("クライアントが選択されていません。サイドバーまたはホーム画面からクライアントを選択してください。")
        if st.button("ホームへ戻る"):
            st.switch_page("pages/00_home.py")
        return

    # --- clients.notes 読み込み（パイプラインデータの一次ソース） ---
    import json as _json
    from core.supabase_client import get_supabase_client as _get_sb_notes
    _sb_notes = _get_sb_notes()
    _notes_res = _sb_notes.table("clients").select("notes, name, industry, location").eq("id", client_id).single().execute()
    _client_row = _notes_res.data or {}
    _raw_notes = _client_row.get("notes")
    _notes = _json.loads(_raw_notes) if isinstance(_raw_notes, str) else (_raw_notes or {})
    _steps = _notes.get("pipeline_steps", {})

    # STEP 14 完了チェック
    if _steps.get("14") != "done":
        st.warning("⚠️ STEP 14（機能別戦術策定）を完了してから中期経営計画の策定に進んでください。")
        return

    # --- Session State Initialization ---
    if "midterm_current_section" not in st.session_state:
        st.session_state["midterm_current_section"] = 1
    
    if "midterm_chat_history" not in st.session_state:
        st.session_state["midterm_chat_history"] = []

    # Initialize Document: DB読み込み → なければ新規作成
    if "midterm_plan_document" not in st.session_state:
        # client_id is already guaranteed to be set above
        
        # まずDBから読み込み
        loaded_doc = load_midterm_plan(client_id)
        if loaded_doc:
            doc = loaded_doc
            st.toast("💾 保存済みの計画書を読み込みました", icon="✅")
        else:
            doc = MidtermPlanDocument(
                document_id=str(uuid.uuid4()),
                client_id=client_id,
                plan_period="3年",
                sections=[
                    MidtermPlanSection(
                        section_id=d["id"],
                        section_title=d["title"],
                        section_title_en=d["title_en"],
                        references=d["references"],
                        narrative=""
                    ) for d in SECTION_DEFINITIONS
                ]
            )
        st.session_state["midterm_plan_document"] = doc

    doc: MidtermPlanDocument = st.session_state["midterm_plan_document"]
    # client_id = st.session_state.get("client_id") # Already set
    
    # --- パイプラインデータ組み立て（clients.notes 優先、DatasetRepo フォールバック） ---
    from core.strategic_guardrails_service import get_latest_guardrails
    from core.repos.dataset_repo import DatasetRepo

    # 1. Guardrails: notes["guardrails"] → strategic_guardrails テーブル の順で取得
    guardrails = _notes.get("guardrails") or {}
    if not guardrails:
        try:
            guardrails_obj = get_latest_guardrails(client_id)
            guardrails = guardrails_obj.model_dump() if guardrails_obj else {}
        except Exception:
            guardrails = {}

    # 2. Pipeline Data: clients.notes（STEP 1〜14の成果物）を一次ソースとする
    pipeline_data: dict = {
        "industry":      _client_row.get("industry") or "General",
        "target_market": _client_row.get("location") or "日本",
        # 18ステップパイプラインの成果物
        "financial":     _notes.get("financial_summary") or {},
        "external":      _notes.get("external_env") or _notes.get("external_environment") or {},
        "internal":      _notes.get("internal_findings") or {},
        "swot":          _notes.get("swot_manual") or {},
        "root_cause":    _notes.get("root_cause") or {},
        "strategy":      _notes.get("strategy_design") or {},
    }

    # DatasetRepo フォールバック（notes に値がない項目のみ補完）
    try:
        dataset_repo = DatasetRepo()
        if not pipeline_data["financial"]:
            v_fin = dataset_repo.get_current_dataset_version(client_id, "financial")
            if v_fin:
                pipeline_data["financial"] = v_fin.get("normalized_json", {})
        if not pipeline_data["internal"]:
            v_int = dataset_repo.get_current_dataset_version(client_id, "internal")
            if v_int:
                pipeline_data["internal"] = v_int.get("normalized_json", {})
        if not pipeline_data["external"]:
            v_ext = dataset_repo.get_current_dataset_version(client_id, "external")
            if v_ext:
                pipeline_data["external"] = v_ext.get("normalized_json", {})
        # internal_docs / external_docs は notes に格納されないため DatasetRepo のみ
        v_int_docs = dataset_repo.get_current_dataset_version(client_id, "internal_docs")
        if v_int_docs:
            pipeline_data["internal_docs"] = v_int_docs.get("normalized_json", [])
        v_ext_docs = dataset_repo.get_current_dataset_version(client_id, "external_docs")
        if v_ext_docs:
            pipeline_data["external_docs"] = v_ext_docs.get("normalized_json", [])
    except Exception as _dr_err:
        print(f"DatasetRepo fallback failed: {_dr_err}")

    # --- Financial Diagnosis & Data Suggestions (Sidebar) ---
    latest_metrics = render_data_diagnosis(pipeline_data)
    
    # Auto-save diagnosis if updated
    if latest_metrics:
        # Check if changed to avoid redundant saves (simple length check or deep compare)
        # Deep compare: Serialize to dict list
        new_dump = [m.model_dump() for m in latest_metrics]
        old_dump = [m.model_dump() for m in doc.financial_diagnosis] if doc.financial_diagnosis else []
        
        if new_dump != old_dump:
            doc.financial_diagnosis = latest_metrics
            save_midterm_plan(client_id, doc)
            # st.toast("📊 財務診断結果を保存しました") # Optional noise reduction

    engine = get_engine(client_id, pipeline_data, guardrails)

    # --- Header ---
    st.markdown(f"### 📋 {PAGE_TITLE}")

    # --- Stats Dashboard ---
    render_stats_dashboard(doc)

    # --- Chapter Navigation ---
    render_chapter_nav(doc, st.session_state["midterm_current_section"])
    
    # Hidden number input for JS-driven chapter change (fallback)
    # Use selectbox + prev/next buttons for reliable navigation
    nav_col_prev, nav_col_select, nav_col_next = st.columns([1, 6, 1])
    with nav_col_prev:
        if st.button("◀", use_container_width=True, key="nav_prev", help="前のチャプター"):
            if st.session_state["midterm_current_section"] > 1:
                # Auto-save on chapter switch
                save_midterm_plan(client_id, doc)
                st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                st.session_state["midterm_current_section"] -= 1
                st.rerun()
    with nav_col_select:
        prev_section = st.session_state["midterm_current_section"]
        def _nav_format(x):
            if x == 14:
                qa_icon = "✅" if doc.quality_check else "⏳"
                return f"§14  🔍 品質チェック（QAレビュー）  —  {qa_icon}"
            return f"§{x}  {doc.sections[x-1].section_title}  —  {_get_status_icon(doc.sections[x-1].chapter_state.status)} {_get_status_label(doc.sections[x-1].chapter_state.status)}"
        selected_nav = st.selectbox(
            "チャプター選択",
            options=range(1, 15),
            format_func=_nav_format,
            index=st.session_state["midterm_current_section"] - 1,
            key="nav_select",
            label_visibility="collapsed"
        )
        # Auto-save on chapter switch via selectbox
        if selected_nav != prev_section:
            save_midterm_plan(client_id, doc)
            st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
        st.session_state["midterm_current_section"] = selected_nav
    with nav_col_next:
        if st.button("▶", use_container_width=True, key="nav_next", help="次のチャプター"):
            if st.session_state["midterm_current_section"] < 14:
                # Auto-save on chapter switch
                save_midterm_plan(client_id, doc)
                st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                st.session_state["midterm_current_section"] += 1
                st.rerun()

    # §14 = 品質チェックモード
    is_qa_mode = selected_nav == 14
    current_section = doc.sections[min(selected_nav, 13) - 1] if not is_qa_mode else None
    is_locked = current_section.chapter_state.status == ChapterStatus.LOCKED if current_section else False

    # --- Batch Generation (Collapsed) ---
    with st.expander("⚙️ 初期セットアップ＆一括生成", expanded=all(not s.narrative for s in doc.sections)):
        st.caption("AIに初期ドラフトを一括生成させ、その後デュアルペインで詳細を詰めると効率的です。")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            input_mission = st.text_area("企業ミッション", value=guardrails.get("mission_objective", ""), height=70, key="setup_mission")
            input_values = st.text_area("コアバリュー", value=",".join(guardrails.get("core_values", [])), height=70, key="setup_values")
        with col_s2:
            input_vision = st.text_area("将来ビジョン", value=guardrails.get("success_state_definition", ""), height=70, key="setup_vision")
            input_horizon = st.number_input("計画期間 (年)", value=guardrails.get("time_horizon_years", 3), min_value=1, max_value=10, key="setup_horizon")

        if st.button("🚀 全チャプターの初期ドラフトを一括生成", type="primary", use_container_width=True):
            updated_guardrails = guardrails.copy()
            updated_guardrails["mission_objective"] = input_mission
            updated_guardrails["success_state_definition"] = input_vision
            updated_guardrails["core_values"] = [v.strip() for v in input_values.split(",") if v.strip()]
            updated_guardrails["time_horizon_years"] = input_horizon
            
            engine = get_engine(client_id, pipeline_data, updated_guardrails)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(pct, msg):
                progress_bar.progress(min(pct, 100))
                status_text.text(msg)
            
            try:
                loop = asyncio.new_event_loop()
                generated_doc = loop.run_until_complete(
                    engine.generate_full_plan(progress_callback=update_progress)
                )
                loop.close()
                
                for section in generated_doc.sections:
                    section.chapter_state.status = ChapterStatus.AI_GENERATED
                
                st.session_state["midterm_plan_document"] = generated_doc
                
                # --- Debug Log (UI: Pipeline Health) ---
                with st.expander("🛠️ パイプライン健全性診断 (Pipeline Health)", expanded=True):
                    st.markdown("### 📊 生成統計")
                    st.write(f"Generated Sections: {len(generated_doc.sections)}")
                    
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        st.markdown("#### 1. Input Data (Pipeline)")
                        # Show data size for each key
                        st.json({k: f"{len(str(v))} chars" for k, v in engine.pipeline_data.items()})
                        
                        st.markdown("#### 2. Agent Reports (Phase 1)")
                        # Show report length
                        st.json({k: f"{len(v)} chars" for k, v in engine.agent_reports.items()})

                    with col_d2:
                        st.markdown("#### 3. Data Connection (Typed Sections)")
                        # Show stored keys implies successful connection
                        st.write(f"Stored Keys: {list(engine.typed_sections.keys())}")
                        
                        if engine.validation_errors:
                            st.error(f"❌ Validation Errors ({len(engine.validation_errors)})")
                            for err in engine.validation_errors:
                                st.code(err, language="text")
                        
                    st.markdown("#### 4. Section Details")
                    for s in generated_doc.sections:
                        status_icon = "✅" if len(s.narrative) > 0 else "⚠️"
                        st.write(f"{status_icon} Section {s.section_id}: {len(s.narrative)} chars, Status: {s.chapter_state.status}")
                        if not s.narrative:
                            st.warning(f"  └─ EMPTY! (Check LLM Response)")
                # -----------------

                if save_midterm_plan(client_id, generated_doc):
                    st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                    st.success("✅ 全チャプターの生成が完了しました！")
                    # 保存成功を確認してもらうため、あえてrerunせずに留まる、あるいはrerun後に表示する工夫が必要
                    # ここではrerunして、main側でロードされたデータを表示させるのが正しいフロー。
                    # しかし「表示されない」問題をデバッグするため、rerunを一時的にコメントアウトしてデータを確認してもらう。
                    st.info("データを確認してください。問題なければリロードします。")
                    # st.rerun() 
                else:
                    st.error("⚠️ データの生成は完了しましたが、データベースへの保存に失敗しました。")
                
            except Exception as e:
                import traceback
                st.error(f"生成エラー: {e}")
                st.code(traceback.format_exc())

    # =================================================
    # §14 MODE: Quality Check & Strategic Refinement
    # =================================================
    if is_qa_mode:
        st.info("💡 全チャプターの入力を完了した後、AIコーチによる品質チェックと戦略精緻化を実行してください。")

        tab_qa, tab_refine, tab_done = st.tabs(["🔍 品質チェック", "💎 戦略精緻化 (Decision-Grade)", "✅ STEP 15 完了"])
        
        with tab_qa:
            st.markdown("### 🔍 品質チェック（QAレビュー）")
            # QA Control
            qa_btn_col1, qa_btn_col2 = st.columns([1, 2])
            with qa_btn_col1:
                if st.button("AI品質レビューを実行", type="primary", key="run_qa"):
                    with st.spinner("AIコーチが全セクションを精査しています..."):
                        # Generate full QA
                        loop = asyncio.new_event_loop()
                        qa_result = loop.run_until_complete(engine.run_quality_check(doc))
                        loop.close()
                        
                        # Update doc
                        doc.quality_check = qa_result
                        save_midterm_plan(client_id, doc)
                        st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                        st.success("品質チェックが完了しました！")
                        st.rerun()
            with qa_btn_col2:
                if doc.quality_check:
                    st.caption(f"最終チェック: {doc.quality_check.checked_at[:19]}")

            # Display QA Result
            if doc.quality_check:
                qa = doc.quality_check
                
                # Grade color
                grade_colors = {"S": "#059669", "A": "#2563EB", "B": "#7C3AED", "C": "#D97706", "D": "#DC2626"}
                grade_color = grade_colors.get(qa.grade, "#64748B")
                
                # Score + Grade header
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:24px;padding:20px;background:linear-gradient(135deg,#0F172A,#1E293B);border-radius:16px;margin:16px 0;">
                    <div style="text-align:center;min-width:100px;">
                        <div style="font-size:3rem;font-weight:800;color:{grade_color};">{qa.grade}</div>
                        <div style="font-size:0.85rem;color:#94A3B8;">Grade</div>
                    </div>
                    <div style="text-align:center;min-width:100px;">
                        <div style="font-size:3rem;font-weight:800;color:white;">{qa.overall_score}</div>
                        <div style="font-size:0.85rem;color:#94A3B8;">/100</div>
                    </div>
                    <div style="flex:1;padding-left:16px;border-left:1px solid #334155;">
                        <div style="color:#E2E8F0;font-size:0.95rem;line-height:1.6;">{qa.executive_summary}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 5-Axis Scores (bar chart style)
                st.markdown("#### 📊 5軸評価")
                for axis in qa.axis_scores:
                    pct = int(axis.score / 20 * 100)
                    bar_color = "#059669" if pct >= 80 else "#2563EB" if pct >= 60 else "#D97706" if pct >= 40 else "#DC2626"
                    st.markdown(f"""
                    <div style="margin:8px 0;">
                        <div style="display:flex;justify-content:space-between;align-items:baseline;">
                            <span style="font-weight:600;color:#E2E8F0;">{axis.axis_name}</span>
                            <span style="font-weight:700;color:{bar_color};">{axis.score}/20</span>
                        </div>
                        <div style="background:#1E293B;border-radius:4px;height:8px;margin:4px 0;">
                            <div style="background:{bar_color};width:{pct}%;height:100%;border-radius:4px;transition:width 0.5s;"></div>
                        </div>
                        <div style="color:#94A3B8;font-size:0.8rem;">{axis.assessment}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Strengths
                if qa.strengths:
                    with st.expander(f"✅ 強み ({len(qa.strengths)}件)", expanded=True):
                        for s in qa.strengths:
                            st.markdown(f"- {s}")
                
                # Critical Issues
                if qa.critical_issues:
                    with st.expander(f"❌ 要修正 ({len(qa.critical_issues)}件)", expanded=True):
                        for idx, issue in enumerate(qa.critical_issues):
                            st.markdown(f"**§{issue.target_section} {issue.target_section_title}**: {issue.description}")
                            if issue.suggestion:
                                st.code(issue.suggestion, language="markdown")
                                if st.button(f"✏️ §{issue.target_section}に修正を適用", key=f"fix_critical_{idx}"):
                                    target = doc.sections[issue.target_section - 1]
                                    target.narrative = target.narrative + f"\n\n---\n### 🔧 QA修正（自動適用）\n{issue.suggestion}"
                                    target.chapter_state.status = ChapterStatus.HUMAN_MODIFIED
                                    target.chapter_state.context_snapshot = None
                                    save_midterm_plan(client_id, doc)
                                    st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                                    st.toast(f"§{issue.target_section}に修正を適用しました", icon="✏️")
                                    st.rerun()
                
                # Warnings
                if qa.warnings:
                    with st.expander(f"⚠️ 改善推奨 ({len(qa.warnings)}件)", expanded=False):
                        for idx, warn in enumerate(qa.warnings):
                            st.markdown(f"**§{warn.target_section} {warn.target_section_title}**: {warn.description}")
                            if warn.suggestion:
                                st.code(warn.suggestion, language="markdown")
                                if st.button(f"✏️ §{warn.target_section}に改善案を適用", key=f"fix_warning_{idx}"):
                                    target = doc.sections[warn.target_section - 1]
                                    target.narrative = target.narrative + f"\n\n---\n### 💡 QA改善（自動適用）\n{warn.suggestion}"
                                    target.chapter_state.status = ChapterStatus.HUMAN_MODIFIED
                                    target.chapter_state.context_snapshot = None
                                    save_midterm_plan(client_id, doc)
                                    st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                                    st.toast(f"§{warn.target_section}に改善案を適用しました", icon="💡")
                                    st.rerun()
                
                # Cross Reference
                if qa.cross_reference_summary:
                    with st.expander("🔗 章間整合性", expanded=False):
                        st.markdown(qa.cross_reference_summary)

        with tab_refine:
            st.markdown("### 💎 戦略精緻化モジュール (Strategic Refinement)")
            st.caption("AIが「戦略コンサルタント」として、ビジネスモデルの整合性、KPIツリー、財務シミュレーションを再構築します。")
            
            if st.button("戦略精緻化を実行 (Deep Think)", type="primary", key="run_refine"):
                with st.spinner("戦略ロジックを再構築中... (これには時間がかかります)"):
                    try:
                        # Need asyncio loop for async call
                        loop = asyncio.new_event_loop()
                        refined_plan = loop.run_until_complete(engine.run_strategic_refinement(doc))
                        loop.close()
                        
                        # Save to session state
                        st.session_state["refined_plan"] = refined_plan.model_dump()
                        st.success("戦略計画が「意思決定レベル」に昇華されました。")
                    except Exception as e:
                        st.error(f"Refinement Failed: {e}")
            
            if "refined_plan" in st.session_state:
                # Re-hydrate Pydantic model
                from core.schemas.refinement_schema import RefinedStrategicPlan
                plan = RefinedStrategicPlan(**st.session_state["refined_plan"])
                
                # --- Decision-Grade Gate Status ---
                if plan.decision_grade_status:
                    # Status Display
                    status = plan.decision_grade_status
                    if status.status == "approved":
                        st.success("🏆 Decision-Grade認定: この戦略は論理的整合性と財務的裏付けがあります")
                    elif status.status == "warning":
                        st.warning("⚠️ 要注意 (Warning): 承認可能ですが、いくつかの懸念事項があります")
                        for w in status.warnings:
                            st.write(f"- {w}")
                    else:
                        st.error("🚫 ブロック: 以下の理由によりDecision-Gradeを満たしていません")
                        for r in status.blocking_reasons:
                            st.write(f"- {r}")
                        if status.warnings:
                            st.markdown("---")
                            st.write("その他警告事項:")
                            for w in status.warnings:
                                st.write(f"- {w}")
                
                # --- External Constraints ---
                if plan.external_constraints:
                    with st.expander("🌍 外部環境制約 (External Constraints)", expanded=False):
                        cols = st.columns(3)
                        cols[0].metric("市場成長率", f"{plan.external_constraints.market_growth_rate:.1%}")
                        cols[1].metric("競争密度", f"{plan.external_constraints.competitive_density_index:.2f}")
                        cols[2].metric("価格圧力", plan.external_constraints.price_pressure_level)
                        st.caption("※これらの制約は収益シミュレーションに強制適用されています。")
                        st.json(plan.external_constraints.model_dump())

                # 1. Verification Status
                if plan.financials_verified:
                    st.info("✅ 財務データ検証済み: 信頼性の高いシミュレーションが生成されました。")
                else:
                    st.warning("⚠️ 財務データ未検証: 数値は「仮説」に基づいています。シミュレーションは抑制されました。")

                # 2. Business Model & Revenue Logic
                with st.expander("📊 ビジネスモデル & 収益ロジック", expanded=True):
                    st.subheader(plan.business_model.model_name)
                    st.write(plan.business_model.description)
                    st.markdown(f"**価値提案:** {plan.business_model.value_proposition}")
                    
                    st.markdown("#### 収益方程式 (Revenue Equation)")
                    st.code(plan.revenue_logic.equation, language="latex")
                    st.caption(plan.revenue_logic.description)

                # 3. KPI Tree
                with st.expander("🌳 KPIアーキテクチャ", expanded=True):
                    st.markdown(f"**KGI:** {plan.kpi_tree.name} - {plan.kpi_tree.definition}")
                    def render_kpi_node(node, level=0):
                        indent = "&nbsp;" * (level * 4)
                        icon = "🎯" if level == 0 else "💰" if level == 1 else "⚙️" if level == 2 else "📝"
                        val_str = f"(Target: {node.target_value_3y})" if node.target_value_3y else ""
                        st.markdown(f"{indent}{icon} **{node.name}**: {node.definition} {val_str}", unsafe_allow_html=True)
                        for child in node.children:
                            render_kpi_node(child, level + 1)
                    render_kpi_node(plan.kpi_tree)

                # 4. Capital Feasibility Analysis (Verified Gate)
                if plan.financials_verified and plan.scenarios:
                    import pandas as pd
                    st.markdown("### 💰 資本フィージビリティ分析 (Capital Feasibility)")
                    
                    tabs = st.tabs(["📊 シナリオ比較", "💵 キャッシュフロー予測", "🏦 借入余力 (Debt Capacity)"])
                    
                    # Tab 1: Scenarios
                    with tabs[0]:
                        st.caption("市場環境の変化に応じた3つのシナリオを分析します。")
                        
                        # Compare Revenue & Ending Cash across scenarios
                        sc_data = []
                        for sc in plan.scenarios:
                            # Sum of 3 years or Final Year? Let's show Final Year Rev and Min Cash
                            final_rev = sc.years[-1].revenue
                            min_cash = min(cf.ending_cash for cf in sc.cashflow)
                            dscr = sc.debt_capacity[0].dscr if sc.debt_capacity else 0
                            sc_data.append({
                                "Scenario": sc.scenario_name,
                                "Year 3 Revenue": f"¥{final_rev:,.0f}",
                                "Min Cash Balance": f"¥{min_cash:,.0f}",
                                "DSCR": f"{dscr:.2f}x"
                            })
                        st.table(sc_data)
                        
                        # Charts for Base Case
                        base = next((s for s in plan.scenarios if "Base" in s.scenario_name), plan.scenarios[0])
                        st.markdown(f"**📉 {base.scenario_name} Trend**")
                        
                        rows = []
                        for y in base.years:
                            rows.append(y.model_dump())
                        df_sim = pd.DataFrame(rows).set_index("year")
                        st.line_chart(df_sim[["revenue", "operating_profit", "cash_flow"]])

                    # Tab 2: Cashflow
                    with tabs[1]:
                        st.caption(f"Base Case: {base.scenario_name} のCashflow詳細")
                        
                        # Show WC Assumptions
                        wc = base.assumptions_modified.working_capital
                        with st.expander("🔄 運転資本（Working Capital）前提", expanded=False):
                            c1, c2, c3 = st. columns(3)
                            c1.metric("回収サイト (Receivables)", f"{wc.payment_terms_days} days")
                            c2.metric("在庫回転期間 (Inventory)", f"{wc.inventory_days} days")
                            c3.metric("前払/未払 (Accrued)", f"{wc.prepaid_accrued_items_days} days")
                            st.caption("※ 上記サイクルに基づき、Operating Cashflowの増減（ΔWC）が計算されています。")
                        
                        cf_rows = []
                        for i, cf in enumerate(base.cashflow):
                            cf_rows.append({
                                "Year": base.years[i].year,
                                "Operating CF": cf.operating_cf,
                                "Investment CF": cf.investment_cf,
                                "Financing CF": cf.financing_cf,
                                "Free Cash Flow": cf.free_cash_flow,
                                "Ending Cash": cf.ending_cash
                            })
                        df_cf = pd.DataFrame(cf_rows).set_index("Year")
                        st.dataframe(df_cf.style.format("¥{:,.0f}"))
                        
                        # Highlight Shortfall
                        min_cash = df_cf["Ending Cash"].min()
                        if min_cash < 0:
                            st.error(f"⚠️ 資金ショートが発生します: 最低残高 ¥{min_cash:,.0f}")
                        else:
                            st.success(f"✅ 資金繰りは安定しています: 最低残高 ¥{min_cash:,.0f}")

                    # Tab 3: Debt Capacity
                    with tabs[2]:
                        if base.debt_capacity and len(base.debt_capacity) > 0:
                            dc = base.debt_capacity[0]
                            c1, c2 = st.columns(2)
                            c1.metric("DSCR (償還確実性)", f"{dc.dscr:.2f}x", delta="Safe > 1.2" if dc.dscr >= 1.2 else "Risk < 1.0", delta_color="normal" if dc.dscr >= 1.2 else "inverse")
                            c1.caption("営業キャッシュフロー ÷ 既存債務返済額")
                            
                            c2.metric("最大追加借入余力", f"¥{dc.max_additional_debt:,.0f}")
                            c2.caption("DSCR 1.5xを維持できる追加借入枠")
                            
                            st.info(f"推奨借入上限 (安全圏): ¥{dc.safe_debt_level:,.0f}")
                        
                        # Amortization Schedule
                        if base.amortization_schedule:
                            st.markdown("#### 📅 借入金返済予定表 (Amortization Schedule)")
                            rows = [r.model_dump() for r in base.amortization_schedule.rows]
                            st.dataframe(pd.DataFrame(rows).set_index("year").style.format("¥{:,.0f}"))
                            st.caption(f"Interest Rate (Existing): {base.assumptions_modified.existing_debt_interest_rate:.1%} / (New): {base.assumptions_modified.new_debt_interest_rate:.1%}")

                # 5. Roadmap
                with st.expander("🛣️ 実行ロードマップ", expanded=True):
                    # Gantt-like viz using timeline
                    roadmap_data = []
                    for init in plan.execution_roadmap.initiatives:
                        roadmap_data.append({
                            "Task": init.name, 
                            "Start": init.timeline_start, 
                            "Finish": init.timeline_end, 
                            "Owner": init.owner
                        })
                    st.table(roadmap_data)
                    
                # 6. Weaknesses
                if plan.consistency_findings:
                    st.error("🚨 検出された構造的弱点")
                    for issue in plan.consistency_findings:
                        st.write(f"- {issue}")
                
                # --- Reflect Button ---
                st.divider()
                c1, c2 = st.columns([0.7, 0.3])
                c1.info("💡 この精緻化結果を、元の計画書（セクション9, 11, 12, 13）に上書き反映しますか？")
                if c2.button("🔄 計画書に反映する", type="primary", key="reflect_refinement_btn"):
                    try:
                        # doc is available from the outer scope (MidtermPlanDocument)
                        updated_doc = engine.apply_refinement_to_document(doc, plan)
                        save_midterm_plan(client_id, updated_doc)
                        st.success("計画書に精緻化結果を反映しました！")
                        st.balloons()
                        import time
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error applying refinement: {e}")

        # ------------------------------------------------------------------ #
        #  STEP 15 完了タブ
        # ------------------------------------------------------------------ #
        with tab_done:
            st.subheader("✅ STEP 15 完了")
            st.caption("中期経営計画書のドラフトが完成したらSTEPを完了してください。")

            # 完成状況サマリー
            filled = sum(1 for s in doc.sections if s.narrative and len(s.narrative) > 50)
            locked = sum(1 for s in doc.sections if s.chapter_state.status == ChapterStatus.LOCKED)
            total = len(doc.sections)

            c1, c2, c3 = st.columns(3)
            c1.metric("記述済みセクション", f"{filled}/{total}")
            c2.metric("承認（LOCKED）", f"{locked}/{total}")
            c3.metric("品質チェック", "✅ 実施済み" if doc.quality_check else "⏳ 未実施")

            # 利用データソースサマリー
            st.markdown("---")
            st.markdown("##### 利用したパイプラインデータ")
            src_items = {
                "財務サマリー (STEP 4)":  bool(pipeline_data.get("financial")),
                "外部環境 (STEP 2)":      bool(pipeline_data.get("external")),
                "内部環境 (STEP 5-6)":    bool(pipeline_data.get("internal")),
                "SWOT分析 (STEP 8)":      bool(pipeline_data.get("swot")),
                "真因分析 (STEP 9)":      bool(pipeline_data.get("root_cause")),
                "戦略設計 (STEP 10)":     bool(pipeline_data.get("strategy")),
                "ガードレール (STEP 10)": bool(guardrails),
            }
            for label, ok in src_items.items():
                st.write(f"{'✅' if ok else '⚠️'} {label}{'（データあり）' if ok else '（未入力）'}")

            st.markdown("---")
            already_done = _steps.get("15") == "done"
            if already_done:
                st.success("✅ STEP 15 は完了済みです。")
            else:
                st.warning("計画書のドラフトが完成したら下のボタンで完了を記録してください。")
                if st.button("✅ 中期経営計画書を確定してSTEP 15 完了", type="primary"):
                    try:
                        import json as _j15
                        _res15 = _get_sb_notes().table("clients").select("notes").eq("id", client_id).single().execute()
                        _n15 = _j15.loads(_res15.data.get("notes") or "{}") if isinstance(_res15.data.get("notes"), str) else (_res15.data.get("notes") or {})
                        _n15.setdefault("pipeline_steps", {})["15"] = "done"
                        _get_sb_notes().table("clients").update({"notes": _j15.dumps(_n15, ensure_ascii=False)}).eq("id", client_id).execute()
                        st.success("🎉 STEP 15 完了！")
                        st.balloons()
                    except Exception as _e15:
                        st.error(f"保存エラー: {_e15}")

    else:
        # =================================================
        # DUAL PANE LAYOUT (§1-13)
        # =================================================
        left_col, right_col = st.columns([1.2, 1.0], gap="medium")

        # ==========================================
        # LEFT PANE: Document Workspace
        # ==========================================
        with left_col:
            # --- 下流セクション波及アラート ---
            if "_downstream_alert" in st.session_state:
                alert = st.session_state.pop("_downstream_alert")
                affected_lines = "、".join([f"§{a['id']} {a['title']}" for a in alert["affected"]])
                st.warning(
                    f"§{alert['source_id']} {alert['source_title']} を承認しました。"
                    f"下流セクション（{affected_lines}）の内容が影響を受ける可能性があります。"
                )
                if st.button("影響セクションをAIで更新", key="downstream_regen_btn"):
                    locked_chapters = [s for s in doc.sections if s.chapter_state.status == ChapterStatus.LOCKED]
                    with st.spinner("影響セクションを再生成中..."):
                        loop = asyncio.new_event_loop()
                        for a in alert["affected"]:
                            sid = a["id"]
                            target = doc.sections[sid - 1]
                            new_sec = loop.run_until_complete(
                                run_generation(engine, sid, locked_chapters, "", target)
                            )
                            target.narrative = new_sec.narrative
                            target.data = new_sec.data
                            target.chapter_state.status = ChapterStatus.AI_GENERATED
                            if not target.ai_draft_snapshot:
                                target.ai_draft_snapshot = new_sec.narrative
                        loop.close()
                    save_midterm_plan(client_id, doc)
                    st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                    st.toast(f"{len(alert['affected'])}セクションを再生成しました", icon="✨")
                    st.rerun()

            # Section Header
            render_section_header(current_section)
            
            # --- Editor Area ---
            if is_locked:
                # Locked: Read-only with styled container
                st.markdown(f'<div class="locked-content">{current_section.narrative}</div>', unsafe_allow_html=True)
                
                with st.expander("📊 構造化データ確認"):
                    st.json(current_section.data)
                
                # Audit Log
                render_audit_log(current_section)
                
                # Unlock button
                st.markdown("")
                col_unlock, col_download = st.columns([1, 1])
                with col_unlock:
                    if st.button("🔓 アンロックして再編集", use_container_width=True):
                        current_section.chapter_state.status = ChapterStatus.HUMAN_MODIFIED
                        current_section.chapter_state.context_snapshot = None
                        save_midterm_plan(client_id, doc)
                        st.rerun()
                with col_download:
                    st.download_button(
                        "📥 Markdownで保存",
                        data=current_section.narrative,
                        file_name=f"section_{current_section.section_id}.md",
                        use_container_width=True
                    )
            else:
                # Editable: Tab-based Edit/Preview
                tab_edit, tab_preview, tab_feedback = st.tabs(["✏️ 編集", "👁️ プレビュー", "💬 フィードバック"])
                
                with tab_edit:
                    # --- Diff表示トグル（AI生成後に編集した場合のみ表示）---
                    if (current_section.ai_draft_snapshot
                            and current_section.narrative != current_section.ai_draft_snapshot):
                        show_diff = st.checkbox(
                            "変更差分を表示（AI生成原文 vs 現在版）",
                            key=f"diff_toggle_{current_section.section_id}"
                        )
                        if show_diff:
                            render_diff_view(current_section.ai_draft_snapshot, current_section.narrative)

                    new_narrative = st.text_area(
                        "内容を記述 (Markdown対応)",
                        value=current_section.narrative,
                        height=380,
                        key=f"narrative_editor_{current_section.section_id}",
                        label_visibility="collapsed",
                        placeholder=f"§{current_section.section_id} {current_section.section_title} の内容を記述してください...\n\nMarkdown記法が使えます：\n# 見出し\n- 箇条書き\n**太字** など"
                    )
                    if new_narrative != current_section.narrative:
                        current_section.narrative = new_narrative
                        current_section.chapter_state.status = ChapterStatus.HUMAN_MODIFIED
                    
                    # Data Editor (compact)
                    with st.expander("📊 構造化データ (JSON)"):
                        new_data_str = st.text_area(
                            "JSON Data",
                            value=json.dumps(current_section.data, ensure_ascii=False, indent=2, default=str),
                            height=160,
                            key=f"data_editor_{current_section.section_id}",
                            label_visibility="collapsed"
                        )
                        try:
                            current_section.data = json.loads(new_data_str)
                        except:
                            st.error("JSON形式が不正です")
                
                with tab_preview:
                    if current_section.narrative:
                        st.markdown(f'<div class="preview-panel">', unsafe_allow_html=True)
                        st.markdown(current_section.narrative)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.info("まだ内容がありません。「✏️ 編集」タブで内容を入力するか、AIに生成を依頼してください。")
                        
                with tab_feedback:
                    st.markdown("### 💬 フィードバック履歴")
                    
                    # Display History
                    if current_section.feedback_history:
                        for fb in current_section.feedback_history:
                            status_icon = "✅" if fb.resolved else "🔴"
                            status_color = "#10B981" if fb.resolved else "#EF4444"
                            type_label = _FEEDBACK_TYPE_OPTIONS.get(fb.feedback_type or "", "")
                            type_badge = (
                                f'<span style="background:#334155;color:#94A3B8;'
                                f'padding:1px 6px;border-radius:4px;font-size:0.72rem;margin-left:6px;">'
                                f'{type_label}</span>'
                            ) if type_label else ""
                            regen_badge = (
                                '<span style="background:#1e3a5f;color:#60a5fa;'
                                'padding:1px 6px;border-radius:4px;font-size:0.72rem;margin-left:4px;">'
                                '再生成済</span>'
                            ) if fb.resulted_in_regeneration else ""
                            st.markdown(f"""
                            <div style="background:#1E293B;padding:12px;border-radius:8px;margin-bottom:8px;border-left:4px solid {status_color};">
                                <div style="display:flex;justify-content:space-between;font-size:0.8rem;color:#94A3B8;">
                                    <span>{fb.timestamp[:16].replace('T', ' ')}{type_badge}{regen_badge}</span>
                                    <span>{status_icon}</span>
                                </div>
                                <div style="margin-top:4px;white-space:pre-wrap;">{fb.content}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("フィードバックはまだありません。")
                        
                    st.divider()

                    # Add New Feedback
                    selected_fb_type = st.selectbox(
                        "修正カテゴリ",
                        options=list(_FEEDBACK_TYPE_OPTIONS.keys()),
                        format_func=lambda x: _FEEDBACK_TYPE_OPTIONS[x],
                        key=f"fb_type_{current_section.section_id}",
                    )
                    new_feedback = st.text_area(
                        "修正理由 / 指示",
                        height=100,
                        key=f"fb_input_{current_section.section_id}",
                        placeholder="例: このセクションの結論が弱いです。もっと具体的な数値目標を追加してください。"
                    )

                    col_fb_add, col_fb_refine = st.columns([1, 1])
                    with col_fb_add:
                        if st.button("💬 フィードバックを追加 (保存のみ)", use_container_width=True, key=f"btn_fb_add_{current_section.section_id}", disabled=not new_feedback):
                            from core.schemas.midterm_plan_schema import FeedbackItem

                            item = FeedbackItem(
                                content=new_feedback,
                                feedback_type=selected_fb_type,
                                provided_by="consultant",
                                resulted_in_regeneration=False
                            )
                            current_section.feedback_history.append(item)
                            save_midterm_plan(client_id, doc)
                            st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                            st.toast("フィードバックを保存しました", icon="💾")
                            st.rerun()

                    with col_fb_refine:
                        if st.button("🤖 フィードバックを反映して再生成", type="primary", use_container_width=True, key=f"btn_fb_refine_{current_section.section_id}", disabled=not new_feedback):
                             from core.schemas.midterm_plan_schema import FeedbackItem

                             # 1. Add Feedback
                             item = FeedbackItem(
                                 content=new_feedback,
                                 feedback_type=selected_fb_type,
                                 provided_by="consultant",
                                 resulted_in_regeneration=True
                             )
                             current_section.feedback_history.append(item)
                             save_midterm_plan(client_id, doc) # Save first
                             
                             # 2. Trigger Generation
                             with st.spinner("フィードバックを反映して再生成中..."):
                                locked_chapters = [s for s in doc.sections if s.chapter_state.status == ChapterStatus.LOCKED]
                                # We pass empty user_instruction because the engine will pick up feedback_history from current_section
                                loop = asyncio.new_event_loop()
                                new_section = loop.run_until_complete(
                                    run_generation(engine, current_section.section_id, locked_chapters, "", current_section)
                                )
                                loop.close()
                                
                                # 3. Update Content
                                current_section.narrative = new_section.narrative
                                current_section.data = new_section.data
                                current_section.chapter_state.status = ChapterStatus.AI_GENERATED
                                
                                # 4. Mark used feedback as resolved?
                                # Ideally yes, but maybe user wants to verify first. 
                                # Let's mark the one just added as resolved? Or keep all unresolved until user manually resolves?
                                # Engine Logic filters "unresolved". So if we don't resolve, it will assume it persists.
                                # For "Refine", we assume immediate attempt to resolve.
                                # Let's NOT mark resolved automatically yet, allows iterative refinement.
                                
                                save_midterm_plan(client_id, doc)
                                st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                                st.toast("再生成が完了しました！", icon="✨")
                                st.rerun()
                
                # --- AI Instruction & Action Bar ---
                st.markdown("")
                
                # AI instruction input
                ai_instruction = st.text_input(
                    "🤖 AI への指示",
                    placeholder="例: もっと具体的に書いて / 競合分析を反映して / 数値目標を入れて",
                    key=f"ai_instruction_{current_section.section_id}",
                    label_visibility="collapsed"
                )
                
                # Action buttons
                col_ai, col_approve, col_download = st.columns([2, 2, 1])
                
                with col_ai:
                    ai_btn_label = "🤖 AI⽣成" if not current_section.narrative else "🤖 AIで更新"
                    if st.button(ai_btn_label, use_container_width=True, type="secondary"):
                        with st.spinner("AIが生成中..."):
                            locked_chapters = [s for s in doc.sections if s.chapter_state.status == ChapterStatus.LOCKED]
                            user_instruction = ai_instruction or ""
                            
                            loop = asyncio.new_event_loop()
                            new_section = loop.run_until_complete(
                                run_generation(engine, current_section.section_id, locked_chapters, user_instruction, current_section)
                            )
                            loop.close()
                            
                            current_section.narrative = new_section.narrative
                            current_section.data = new_section.data
                            current_section.chapter_state.status = ChapterStatus.AI_GENERATED
                            # 初回生成時のみスナップショットを保存（再生成時は既存を維持）
                            if not current_section.ai_draft_snapshot:
                                current_section.ai_draft_snapshot = new_section.narrative

                            # AI更新後にDB自動保存
                            save_midterm_plan(client_id, doc)
                            st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                            st.rerun()
                
                with col_approve:
                    if st.button("✅ 承認してロック", type="primary", use_container_width=True, disabled=not current_section.narrative):
                        current_section.chapter_state.status = ChapterStatus.LOCKED
                        current_section.chapter_state.approved_at = datetime.now().isoformat()
                        current_section.chapter_state.context_snapshot = f"{current_section.narrative}\n\nData: {json.dumps(current_section.data, ensure_ascii=False, default=str)}"

                        # DB保存
                        save_midterm_plan(client_id, doc)
                        st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                        st.toast("💾 承認・保存しました", icon="✅")

                        # 下流セクション波及チェック
                        affected_ids = DOWNSTREAM_MAP.get(current_section.section_id, [])
                        if affected_ids:
                            affected_with_content = [
                                doc.sections[sid - 1] for sid in affected_ids
                                if doc.sections[sid - 1].narrative
                            ]
                            if affected_with_content:
                                st.session_state["_downstream_alert"] = {
                                    "source_id": current_section.section_id,
                                    "source_title": current_section.section_title,
                                    "affected": [
                                        {"id": s.section_id, "title": s.section_title}
                                        for s in affected_with_content
                                    ],
                                }

                        # Auto-advance to next unlocked chapter
                        if st.session_state["midterm_current_section"] < 13:
                            st.session_state["midterm_current_section"] += 1
                        st.rerun()
                
                with col_download:
                    col_save, col_dl = st.columns(2)
                    with col_save:
                        if st.button("💾", use_container_width=True, help="手動保存"):
                            save_midterm_plan(client_id, doc)
                            st.session_state["midterm_last_saved"] = datetime.now().strftime("%H:%M:%S")
                            st.toast("💾 保存しました", icon="✅")
                            st.rerun()
                    with col_dl:
                        st.download_button(
                            "📥",
                            data=current_section.narrative or "",
                            file_name=f"section_{current_section.section_id}.md",
                            help="Markdownで保存"
                        )
                
                # Audit Log
                render_audit_log(current_section)

        # ==========================================
        # RIGHT PANE: AI Collaboration
        # ==========================================
        with right_col:
            # Locked context with progress
            locked_chapters = [s for s in doc.sections if s.chapter_state.status == ChapterStatus.LOCKED]
            locked_pct = int(len(locked_chapters) / len(doc.sections) * 100)
            
            with st.expander(f"📦 承認済みコンテキスト ({len(locked_chapters)}/13 — {locked_pct}%)", expanded=False):
                if not locked_chapters:
                    st.caption("承認済みチャプターはまだありません。チャプターを承認すると、後続チャプターのAI生成時にコンテキストとして自動注入されます。")
                else:
                    for lc in locked_chapters:
                        preview_text = lc.narrative[:100].replace("\n", " ") + "..." if len(lc.narrative) > 100 else lc.narrative.replace("\n", " ")
                        st.markdown(f"""
                        <div class="context-card">
                            <p class="context-card-title">§{lc.section_id} {lc.section_title}</p>
                            <p class="context-card-preview">{preview_text}</p>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Dependencies info
            refs = current_section.references if hasattr(current_section, 'references') else []
            if refs:
                ref_names = []
                for r in refs:
                    if isinstance(r, int) and 1 <= r <= 13:
                        ref_section = doc.sections[r - 1]
                        ref_status = _get_status_icon(ref_section.chapter_state.status)
                        ref_names.append(f"{ref_status} §{r} {SECTION_SHORT_LABELS[r-1]}")
                    elif isinstance(r, str):
                        ref_names.append(f"📊 {r}")
                if ref_names:
                    st.caption(f"📎 参照: {' / '.join(ref_names)}")

            # Chat Interface
            st.markdown("#### 💬 AIコンサルタント")
            
            chat_container = st.container(height=480)
            
            with chat_container:
                if not st.session_state["midterm_chat_history"]:
                    st.markdown("""
                    <div style="text-align:center; padding:40px 20px; color:#94A3B8;">
                        <div style="font-size:2rem; margin-bottom:8px;">💬</div>
                        <div style="font-size:0.85rem;">AIコンサルタントに質問や指示ができます</div>
                        <div style="font-size:0.75rem; margin-top:4px;">例: 「この章の論点を整理して」「業界データを反映して」</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                for msg in st.session_state["midterm_chat_history"]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            # Chat Input
            if prompt := st.chat_input("AIに質問・指示する...", key="midterm_chat_input"):
                st.session_state["midterm_chat_history"].append({"role": "user", "content": prompt})
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(prompt)

                with chat_container:
                    with st.chat_message("assistant"):
                        with st.spinner("考え中..."):
                            loop = asyncio.new_event_loop()
                            response_text = loop.run_until_complete(
                                run_chat(engine, prompt, locked_chapters, current_section)
                            )
                            loop.close()
                            st.markdown(response_text)
                
                st.session_state["midterm_chat_history"].append({"role": "assistant", "content": response_text})
            
            # Quick actions for chat
            st.caption("クイックアクション:")
            qa_col1, qa_col2 = st.columns(2)
            with qa_col1:
                if st.button("🔍 論点整理", use_container_width=True, key="qa_issues", type="secondary"):
                    quick_prompt = f"§{current_section.section_id} {current_section.section_title} の主要論点を整理し、検討すべきポイントを教えてください。"
                    st.session_state["midterm_chat_history"].append({"role": "user", "content": quick_prompt})
                    with chat_container:
                        with st.chat_message("assistant"):
                            with st.spinner("考え中..."):
                                loop = asyncio.new_event_loop()
                                response_text = loop.run_until_complete(
                                    run_chat(engine, quick_prompt, locked_chapters, current_section)
                                )
                                loop.close()
                                st.markdown(response_text)
                    st.session_state["midterm_chat_history"].append({"role": "assistant", "content": response_text})
                    st.rerun()
            with qa_col2:
                if st.button("📝 改善提案", use_container_width=True, key="qa_improve", type="secondary"):
                    quick_prompt = f"現在の§{current_section.section_id}の内容を確認し、改善すべき点を具体的に提案してください。"
                    st.session_state["midterm_chat_history"].append({"role": "user", "content": quick_prompt})
                    with chat_container:
                        with st.chat_message("assistant"):
                            with st.spinner("考え中..."):
                                loop = asyncio.new_event_loop()
                                response_text = loop.run_until_complete(
                                    run_chat(engine, quick_prompt, locked_chapters, current_section)
                                )
                                loop.close()
                                st.markdown(response_text)
                    st.session_state["midterm_chat_history"].append({"role": "assistant", "content": response_text})
                    st.rerun()



    # ==========================================
    # Sidebar: Export Tools
    # ==========================================
    with st.sidebar:
        st.divider()
        st.subheader("📤 計画書エクスポート")
        
        # DOCX Export
        if st.button("📝 Word (DOCX)", key="btn_export_docx", use_container_width=True):
            try:
                writer = DocxWriter()
                writer.add_title(f"Mid-term Management Plan: {doc.client_id}")
                for section in doc.sections:
                    if section.narrative:
                        writer.add_chapter(f"{section.section_id}. {section.section_title}")
                        writer.add_content_from_markdown(section.narrative)
                
                if not os.path.exists("artifacts_out"):
                    os.makedirs("artifacts_out")
                fname = f"Plan_{doc.client_id}_{datetime.now().strftime('%Y%m%d')}.docx"
                fpath = os.path.join("artifacts_out", fname)
                writer.save(fpath)
                
                with open(fpath, "rb") as f:
                    st.download_button("📥 Download DOCX", f, file_name=fname, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_docx_sidebar")
            except Exception as e:
                st.error(f"Error: {e}")

        # PPTX Export
        if st.button("📊 PowerPoint (PPTX)", key="btn_export_pptx", use_container_width=True):
            try:
                writer = PPTWriter()
                writer.create_slides_from_midterm_plan(doc)
                
                if not os.path.exists("artifacts_out"):
                    os.makedirs("artifacts_out")
                fname = f"Plan_{doc.client_id}_{datetime.now().strftime('%Y%m%d')}.pptx"
                fpath = os.path.join("artifacts_out", fname)
                writer.save(fpath)
                
                with open(fpath, "rb") as f:
                    st.download_button("📥 Download PPTX", f, file_name=fname, mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", key="dl_pptx_sidebar")
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Chat history clear
        st.divider()
        if st.button("🗑️ チャット履歴クリア", key="clear_chat", use_container_width=True, type="secondary"):
            st.session_state["midterm_chat_history"] = []
            st.rerun()

if __name__ == "__main__":
    app()
