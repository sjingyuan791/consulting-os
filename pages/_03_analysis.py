import streamlit as st
import pandas as pd
import json
import asyncio
import plotly.express as px
import plotly.graph_objects as go
from core.auth import check_auth

# Repos & Pipeline
from core.repos.dataset_repo import DatasetRepo
from core.repos.analysis_run_repo import AnalysisRunRepo
from core.repos.strategy_run_repo import StrategyRunRepo
from core.pipeline_runner import run_strategy_pipeline
from core.style_utils import load_custom_css

import datetime

def app():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()

    if not check_auth():
        st.warning("Please login.")
        return

    st.title("Strategic Analysis")
    
    client_id = st.session_state.get("client_id")
    if not client_id:
        st.warning("クライアントが選択されていません。")
        st.stop()
    
    repo_ds = DatasetRepo()
    repo_strat = StrategyRunRepo()

    # Get Last Analysis Date
    latest_run = repo_strat.get_current_strategy_run(client_id)
    if latest_run:
        try:
            # Parse ISO string (e.g., 2023-10-27T10:00:00+00:00)
            dt_str = latest_run["created_at"]
            dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            dt_jst = dt + datetime.timedelta(hours=9)
            st.caption(f"最終分析実行日: {dt_jst.strftime('%Y/%m/%d %H:%M')}")
        except Exception:
            pass

    # Check Active Data
    v_fin = repo_ds.get_current_dataset_version(client_id, "financial")
    v_int = repo_ds.get_current_dataset_version(client_id, "internal") # Sales
    v_int_docs = repo_ds.get_current_dataset_version(client_id, "internal_docs") # Docs
    v_ext = repo_ds.get_current_dataset_version(client_id, "external") # Ext JSON/API
    v_ext_docs = repo_ds.get_current_dataset_version(client_id, "external_docs") # Ext Docs
    
    if not v_fin and not v_int and not v_int_docs:
        st.info("有効なデータが見つかりません。「データ入力・整備」ページでデータを登録してください。")
        if st.button("データ入力へ移動"):
             st.switch_page("pages/02_upload.py")
        return

    # Data Loading & Layout
    
    def status_card(title, version_info, version_docs=None):
        is_ready = version_info is not None or version_docs is not None
        color = "var(--success-color)" if is_ready else "var(--secondary-color)"
        bg_color = "#ECFDF5" if is_ready else "#F1F5F9"
        icon = "✅" if is_ready else "⬜"
        
        v_texts = []
        if version_info: v_texts.append(f"Data v{version_info['version']}")
        if version_docs: v_texts.append(f"Docs v{version_docs['version']}")
        status_text = ", ".join(v_texts) if v_texts else "Not Registered"
        
        st.markdown(f"""
        <div style="
            border: 1px solid {color};
            background-color: {bg_color};
            padding: 1rem;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 1rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        ">
            <div style="font-size: 1.5rem;">{icon}</div>
            <div>
                <div style="font-weight: 600; color: var(--primary-color);">{title}</div>
                <div style="font-size: 0.875rem; color: var(--secondary-color);">{status_text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1: status_card("財務データ (Financial)", v_fin)
    with c2: status_card("内部データ (Internal)", v_int, v_int_docs)
    with c3: status_card("外部データ (External)", v_ext, v_ext_docs)

    # Guardrails Check (Phase 1)
    from core.strategic_guardrails_service import get_latest_guardrails
    guardrails = get_latest_guardrails(client_id)
    if not guardrails:
        st.warning("⚠️ 戦略的ガードレール（制約条件）が定義されていません。分析の前に設定が必要です。")
        if st.button("ガードレール設定へ移動"):
             st.switch_page("pages/01_strategic_guardrails.py")
        return
        
    st.success(f"✅ Guardrails Active: {guardrails.mission_objective}")

    # Prepare Inputs
    financial_data = v_fin.get("normalized_json", []) if v_fin else []
    
    # Pipeline Runner
    st.divider()
    if st.button("AI分析を実行する (Run Analysis)", type="primary", use_container_width=True):
        with st.spinner("思考中... ファイナンシャル・ヘルス診断、ケイパビリティ分析、戦略仮説の構築を行っています..."):
            try:
                # Prepare Args
                dvs = {"_client_id": client_id}
                if v_fin: dvs["financial"] = v_fin.get("version")
                if v_int: dvs["internal"] = v_int.get("version")
                if v_int_docs: dvs["internal_docs"] = v_int_docs.get("version")
                if v_ext: dvs["external"] = v_ext.get("version")
                if v_ext_docs: dvs["external_docs"] = v_ext_docs.get("version")
                
                # Fix: Extract records from file objects if necessary
                fin_records = []
                if financial_data:
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

                from core.normalizers import clean_financial_df
                df_fin = pd.DataFrame(fin_records) if fin_records else pd.DataFrame()
                if not df_fin.empty:
                    df_fin = clean_financial_df(df_fin)
                
                # Merge Sales Transaction & Internal Docs
                sales_data = {}
                if v_int: 
                    sales_data = {"summary": {}, "transactions": v_int.get("normalized_json", [])}
                if v_int_docs:
                    # Ingest document content into sales_data structure for downstream processing
                    sales_data["documents"] = v_int_docs.get("normalized_json", {})
                
                # Merge External JSON & External Docs
                market_data = v_ext.get("normalized_json", {}) if v_ext else {}
                if v_ext_docs:
                    market_data["documents"] = v_ext_docs.get("normalized_json", {})
                
                # EXECUTE
                # EXECUTE
                package = asyncio.run(run_strategy_pipeline(
                    client_context={
                        "risk_tolerance": guardrails.risk_tolerance,
                        "constraints": {
                            "budget": guardrails.investment_limit,
                            "must_haves": guardrails.strategic_boundaries.get("must_haves", []),
                            "must_not_haves": guardrails.strategic_boundaries.get("must_not_haves", [])
                        }, 
                        "resources": [],
                        "guardrails": guardrails # Pass full schema object
                    },
                    financial_df_latest=df_fin,
                    sales_data_latest=sales_data,
                    market_data=market_data,
                    dataset_versions=dvs
                ))
                
                st.session_state["final_strategy_package"] = package.dict()
                
                # Persist
                repo_run = AnalysisRunRepo()
                run_id = repo_run.create_analysis_run(
                    client_id=client_id,
                    dataset_version_set=dvs,
                    financial_metrics=package.financial_health.dict(),
                    sales_metrics=package.internal_capability.dict(), 
                    internal_capability=package.internal_capability.dict(),
                    external_intelligence=package.external_intelligence.dict(),
                    created_by=st.session_state.user.id if "user" in st.session_state else None
                )
                st.session_state["current_analysis_run_id"] = run_id
                
                # Persist Strategy
                repo_strat = StrategyRunRepo()
                strat_run_id = repo_strat.create_strategy_run(
                    client_id=client_id,
                    analysis_run_id=run_id,
                    guardrails=package.guardrails.dict(),
                    final_strategy_package=package.dict(),
                    meta=package.meta.dict(),
                    created_by=st.session_state.user.id if "user" in st.session_state else None
                )
                st.session_state["current_strategy_run_id"] = strat_run_id
                
                st.success("分析完了！戦略案が生成されました。")
                
            except Exception as e:
                import logging, traceback
                logging.exception("Pipeline execution failed")
                st.error(f"分析処理中にエラーが発生しました: {str(e)}")
                with st.expander("エラー詳細（デバッグ用）"):
                    st.code(traceback.format_exc())

    # Dashboard
    if "final_strategy_package" in st.session_state:
        pkg = st.session_state["final_strategy_package"]
        fh = pkg.get("financial_health", {})
        
        st.markdown("### 📊 分析レポート (Dashboard)")
        
        # 1. High-Level Metrics
        m1, m2, m3 = st.columns(3)
        health_score = fh.get("overall_health_score", 0) or 0
        with m1:
            # Color-code the score
            if health_score >= 70:
                delta_label = "↑ Good"
            elif health_score >= 40:
                delta_label = "→ Normal"
            else:
                delta_label = "↓ Warning"
            st.metric("総合健全性スコア", health_score, delta_label)
        with m2:
            gr = fh.get('average_revenue_growth_3y') or 0
            delta_color = "normal" if gr >= 0 else "inverse"
            st.metric("3年平均売上成長率", f"{gr:.1%}", f"{gr:.1%}", delta_color=delta_color)
        with m3:
            om = fh.get('average_operating_margin_3y') or 0
            delta_color = "normal" if om >= 0 else "inverse"
            st.metric("3年平均営業利益率", f"{om:.1%}", f"{om:.1%}", delta_color=delta_color)
             
        # 2. Detailed Tabs
        tab_diag, tab_detail_fin, tab_cap, tab_strat, tab_logic = st.tabs([
            "財務健全性診断 (概要)", 
            "財務分析詳細 (Five-Way)",
            "内部リソース評価", 
            "AI戦略立案 (Action)", 
            "詳細ロジック (Internal)"
        ])
        
        with tab_diag:
            # --- Financial Cockpit ---
            latest = fh.get("metrics_history", [])[-1] if fh.get("metrics_history") else {}
            
            # 1. Key Performance Indicators (Cards)
            st.markdown("#### 💎 重要経営指標 (KPI)")
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            with kpi1:
                cf = latest.get("simplified_cf")
                val = f"{cf:,.0f}" if cf is not None else "N/A"
                st.metric("簡易キャッシュフロー", val, help="当期純利益 + 減価償却費 - 年間返済額")
            with kpi2:
                be_ratio = latest.get("break_even_ratio")
                val = f"{be_ratio:.1%}" if be_ratio is not None else "N/A"
                delta_color = "inverse" # Lower is better
                st.metric("損益分岐点比率", val, delta_color=delta_color, help="損益分岐点売上高 / 売上高 (低いほど安全)")
            with kpi3:
                prod = latest.get("labor_productivity")
                val = f"{prod:,.0f}" if prod is not None else "N/A"
                st.metric("労働生産性 (一人当たり粗利)", val)
            with kpi4:
                share = latest.get("labor_share")
                val = f"{share:.1%}" if share is not None else "N/A"
                st.metric("労働分配率", val, help="適正範囲: 40-60%目安")
                
            st.divider()
            
            # 2. Break-even Chart
            c_chart, c_detail = st.columns([2, 1])
            with c_chart:
                st.markdown("#### ⚖️ 損益分岐点分析")
                if latest.get("break_even_sales") and latest.get("revenue"):
                    # BEP Chart Logic
                    sales = latest["revenue"]
                    be_sales = latest["break_even_sales"]
                    
                    # Create range for chart
                    max_x = max(sales, be_sales) * 1.2
                    x_vals = [0, max_x]
                    
                    # Cost Line (Fixed + Variable)
                    # Fixed + (Var/Sales)*X
                    # We need fixed cost and variable ratio again? 
                    # Or just plot lines intersecting at BEP.
                    # BEP = Fixed / (1 - VariableRatio)
                    # At BEP, Sales = Cost.
                    # At 0 Sales, Cost = Fixed Cost.
                    
                    # Back-calculate Fixed Cost from BEP
                    # Sales * Ratio = Variable Cost
                    # Sales - Variable - Fixed = Profit
                    # At BEP: BEP - Var(BEP) - Fixed = 0
                    
                    # Let's simple plot:
                    # 1. Sales Line (y=x)
                    # 2. Total Cost Line (Intercept=Fixed, Intersects Sales at BEP)
                    
                    fig = go.Figure()
                    
                    # Sales Line
                    fig.add_trace(go.Scatter(x=x_vals, y=x_vals, name="売上高", line=dict(color="blue", width=3)))
                    
                    # Cost Line
                    # Slope = (BEP_Sales - Fixed) / BEP_Sales ? No.
                    # At x=BEP, y=BEP.
                    # At x=0, y=Fixed Cost.
                    # We assume Fixed Cost is constant.
                    # We can visualize Total Cost line. 
                    # But we don't strictly have Fixed Cost in `latest` dict unless we added it.
                    # We can infer it: BEP * (1-VarRatio) = Fixed ???
                    # Let's simplify: Visualize Revenue vs Expenses Bar or just BEP marker.
                    
                    # Simpler Layout: Bar Chart of BEP vs Actual
                    df_bep = pd.DataFrame({
                        "Metric": ["実際の売上", "損益分岐点"],
                        "Value": [sales, be_sales],
                        "Color": ["blue", "red"]
                    })
                    fig_bep = px.bar(df_bep, x="Value", y="Metric", orientation='h', text_auto=True, color="Color", title="損益分岐点との比較")
                    fig_bep.update_layout(showlegend=False)
                    st.plotly_chart(fig_bep, use_container_width=True)
                    
                else:
                    st.info("データ不足のため損益分岐点を描画できません（変動費・固定費の算出不能）")

            with c_detail:
                st.markdown("#### 🔍 検出シグナル")
                rules = fh.get("meta", {}).get("rules_fired", [])
                if rules:
                    for rule in rules:
                        if "🔴" in rule: st.error(rule)
                        elif "⚠️" in rule: st.warning(rule)
                        else: st.success(rule)
                else:
                    st.caption("特筆すべきシグナルなし")

            st.divider()

            # 3. Traditional Financial Metrics Table
            metrics_history = fh.get("metrics_history", [])
            if metrics_history:
                st.markdown("#### 📈 財務指標推移 (詳細)")
                rows = []
                for m in metrics_history:
                    rows.append({
                        "年度": m.get("year", "N/A"),
                        "売上高": f"{m.get('revenue', 0):,.0f}",
                        "営業利益": f"{m.get('operating_profit', 0):,.0f}",
                        "簡易CF": f"{m.get('simplified_cf', 0):,.0f}" if m.get('simplified_cf') is not None else "-",
                        "自己資本比率": f"{m.get('equity_ratio', 0):.1%}" if m.get('equity_ratio') is not None else "-",
                        "労働生産性": f"{m.get('labor_productivity', 0):,.0f}" if m.get('labor_productivity') is not None else "-"
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("財務データがありません。")

                
        with tab_detail_fin:
            st.markdown("### 📑 総合財務分析シート (5-Way Analysis)")
            metrics_history = fh.get("metrics_history", [])
            if metrics_history:
                # Transpose for easier viewing (Metrics as rows, Years as columns)
                years = sorted([m.get("year") for m in metrics_history])
                
                def get_val(metric_key, fmt="{:,.0f}"):
                    row_data = {}
                    for m in metrics_history:
                        y = m.get("year")
                        v = m.get(metric_key)
                        if v is None:
                            row_data[y] = "-"
                        else:
                            try:
                                row_data[y] = fmt.format(v) if fmt else v
                            except:
                                row_data[y] = v
                    return row_data

                # Define sections and metrics
                sections = [
                    ("収益性 (Profitability)", [
                        ("売上高", "revenue", "{:,.0f}"),
                        ("売上総利益", "gross_profit", "{:,.0f}"),
                        ("営業利益", "operating_profit", "{:,.0f}"),
                        ("経常利益", "ordinary_profit", "{:,.0f}"),
                        ("税引後当期純利益", "net_income", "{:,.0f}"),
                        ("売上高総利益率", "gross_margin", "{:.1%}"),
                        ("売上高営業利益率", "operating_margin", "{:.1%}"),
                        ("売上高経常利益率", "ordinary_profit_margin", "{:.1%}"),
                        ("売上高当期純利益率", "net_margin", "{:.1%}"),
                    ]),
                    ("効率性 (Efficiency)", [
                        ("総資本回転率(回)", "total_asset_turnover", "{:.2f}"),
                        ("売上債権回転期間(月)", "receivables_turnover_months", "{:.1f}"),
                        ("棚卸資産回転期間(月)", "inventory_turnover_months", "{:.1f}"),
                        ("買入債務回転期間(月)", "payables_turnover_months", "{:.1f}"),
                        ("ROA (総資産利益率)", "roa", "{:.1%}"),
                        ("ROE (自己資本利益率)", "roe", "{:.1%}"),
                    ]),
                    ("安全性 (Safety)", [
                        ("流動比率", "current_ratio", "{:.1%}"),
                        ("当座比率", "quick_ratio", "{:.1%}"),
                        ("固定比率", "fixed_ratio", "{:.1%}"),
                        ("固定長期適合率", "fixed_long_term_ratio", "{:.1%}"),
                        ("自己資本比率", "equity_ratio", "{:.1%}"),
                        ("借入金月商倍率(倍)", "debt_monthly_sales_ratio", "{:.1f}"),
                    ]),
                    ("生産性 (Productivity)", [
                        ("労働生産性(円/人)", "labor_productivity", "{:,.0f}"),
                        ("労働分配率", "labor_share", "{:.1%}"),
                    ]),
                    ("キャッシュフロー (Cash Flow)", [
                        ("簡易CF(千円)", "simplified_cf", "{:,.0f}"),
                    ])
                ]

                # Build DataFrame
                rows_list = []
                for sec_name, items in sections:
                    rows_list.append({"指標区分": f"--- {sec_name} ---", **{y: "" for y in years}})
                    for label, key, fmt in items:
                        row = {"指標区分": label}
                        vals = get_val(key, fmt)
                        row.update(vals)
                        rows_list.append(row)
                
                df_detail = pd.DataFrame(rows_list)
                st.dataframe(
                    df_detail,
                    column_config={
                        "指標区分": st.column_config.TextColumn("指標区分", width="medium"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("財務データがありません。")

        with tab_cap:
            ic = pkg.get("internal_capability", {})
            c1, c2 = st.columns(2)
            with c1:
                st.success("**強み・コアコンピタンス**")
                comps = ic.get("core_competencies", [])
                if comps:
                    for c in comps:
                        st.write(f"- {c}")
                else:
                    st.caption("データ不足のため分析結果がありません。内部文書をアップロードしてください。")
            with c2:
                st.error("**課題・リソース不足**")
                gaps = ic.get("resource_gaps", [])
                if gaps:
                    for g in gaps:
                        st.write(f"- {g}")
                else:
                    st.caption("データ不足のため分析結果がありません。")
            
            # Show sustainable advantages if available
            sa = ic.get("sustainable_advantages", [])
            if sa:
                st.markdown("**持続的競争優位性 (VRIO分析)**")
                for s in sa:
                    st.write(f"- {s}")

        with tab_strat:
            st.markdown("#### AIが推奨する戦略オプション")

            strat_opts = pkg.get("strategy_options", {})
            so_what = strat_opts.get("so_what_recommendation", "")
            rec_idx = strat_opts.get("recommended_option_index", 0)
            ctx_summary = strat_opts.get("selected_context_summary", "")
            opts = strat_opts.get("options", [])

            # ── So What（最優先表示）──────────────────────────────
            if so_what:
                st.markdown("""
                <div style="background:#1e3a5f;border-left:5px solid #3b82f6;border-radius:10px;
                            padding:1.1rem 1.4rem;margin-bottom:1rem;">
                  <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.12em;
                              text-transform:uppercase;color:#93c5fd;margin-bottom:6px;">
                    ◆ So What — コンサルタントの結論
                  </div>
                  <div style="font-size:0.95rem;color:#f1f5f9;line-height:1.7;">
                """ + so_what.replace("\n", "<br>") + """
                  </div>
                </div>
                """, unsafe_allow_html=True)
            elif ctx_summary:
                st.info(f"**分析サマリー**: {ctx_summary}")

            if not opts:
                st.warning("戦略オプションが生成されていません。AI分析を再実行してください。")
            else:
                if ctx_summary and so_what:
                    with st.expander("分析コンテキストサマリー", expanded=False):
                        st.caption(ctx_summary)

                for i, opt in enumerate(opts):
                    is_rec = (i == rec_idx)
                    label = (
                        f"⭐ 【推奨】戦略案 {i+1}: {opt.get('name')} "
                        f"(実現可能性: {opt.get('feasibility_score')} / 影響度: {opt.get('impact_score')})"
                        if is_rec else
                        f"戦略案 {i+1}: {opt.get('name')} "
                        f"(実現可能性: {opt.get('feasibility_score')} / 影響度: {opt.get('impact_score')})"
                    )
                    with st.expander(label, expanded=is_rec):
                        if is_rec:
                            st.markdown(
                                '<span style="background:#1d4ed8;color:#fff;padding:2px 8px;'
                                'border-radius:4px;font-size:0.72rem;font-weight:700;">推奨案</span>',
                                unsafe_allow_html=True
                            )
                        st.markdown(f"**概要**: {opt.get('description')}")
                        st.caption(f"**選定理由**: {opt.get('rationale')}")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.caption(f"タイムライン: {opt.get('time_horizon', '—')}")
                        with c2:
                            st.warning(f"リスク: {opt.get('risk')}")

            st.divider()
            if st.button("SWOT 分析へ →", type="primary"):
                st.switch_page("pages/04_swot_analysis.py")

        with tab_logic:
            st.json(pkg)
            
    # --- Action Button to Draft ---
    st.divider()
    c_nav1, c_nav2 = st.columns([2, 1])
    with c_nav1:
        st.info("💡 分析が完了しました。この結果に基づき、中期経営計画書の策定に進んでください。")
    with c_nav2:
        if st.button("➡️ 中期経営計画を策定する", type="primary", use_container_width=True):
            st.switch_page("pages/15_midterm_plan.py")
    
    # --- Upload Data History Section ---
    st.divider()
    st.markdown("### 📁 登録済みデータ一覧")
    
    dataset_types = [
        ("financial", "📊 財務データ"),
        ("internal", "📋 売上・取引データ"),
        ("internal_docs", "📄 内部文書"),
        ("external", "🌐 外部データ"),
        ("external_docs", "📰 外部文書"),
    ]
    
    has_any_data = False
    for ds_type, ds_label in dataset_types:
        version = repo_ds.get_current_dataset_version(client_id, ds_type)
        if version:
            has_any_data = True
            created_at = version.get("created_at", "N/A")
            # Parse timestamp
            try:
                dt = datetime.datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                dt_jst = dt + datetime.timedelta(hours=9)
                ts_str = dt_jst.strftime('%Y/%m/%d %H:%M')
            except Exception:
                ts_str = str(created_at)[:19] if created_at else "N/A"
            
            ver_num = version.get("version", "?")
            source = version.get("source_type", "upload")
            
            st.markdown(f"""
            <div style="
                border: 1px solid #E2E8F0;
                padding: 0.75rem 1rem;
                border-radius: 8px;
                margin-bottom: 0.5rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #F8FAFC;
            ">
                <div>
                    <strong>{ds_label}</strong>
                    <span style="color: #64748B; font-size: 0.85rem; margin-left: 0.5rem;">v{ver_num}</span>
                </div>
                <div style="font-size: 0.85rem; color: #64748B;">
                    🕐 {ts_str} | ソース: {source}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    if not has_any_data:
        st.info("まだデータが登録されていません。「データ入力・整備」ページからアップロードしてください。")

if __name__ == "__main__":
    app()
