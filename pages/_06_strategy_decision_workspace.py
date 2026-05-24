import streamlit as st
import json
import pandas as pd
import plotly.express as px
import time

from core.supabase_client import get_supabase_client
from core.decision_execution_service import run_execution_phase
from core.schemas.execution import StrategyDecisionSchema
from core.schemas.strategy import StrategyOptionItem
from core.style_utils import load_custom_css

st.set_page_config(page_title="Strategy Decision Workspace", layout="wide")

def load_latest_strategy_run(client_id):
    sb = get_supabase_client()
    res = sb.table("strategy_runs").select("*").eq("client_id", client_id).order("created_at", desc=True).limit(1).execute()
    return res.data[0] if res.data else None

def save_decision(strategy_run_id, selected_options_meta, decision_rationale, strategic_exclusions, assumed_targets, user_id):
    sb = get_supabase_client()
    data = {
        "strategy_run_id": strategy_run_id,
        "selected_options_json": selected_options_meta, # List of {option_id, weight, phase}
        "decision_rationale_json": {
            "text": decision_rationale,
            "strategic_exclusions": strategic_exclusions
        },
        "assumed_kpi_targets_json": assumed_targets,
        "decided_by": user_id
    }
    res = sb.table("strategy_decisions").insert(data).execute()
    return res.data[0]['id']

def visualize_lineage(run_data):
    with st.expander("🔗 Data Lineage & Provenance", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Run ID:** `{run_data.get('id')}`")
            st.markdown(f"**Module Version:** `{run_data.get('module_version_hash')}`")
        with c2:
            st.json(run_data.get("decision_lineage_json", {}))

def main():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()
    if "user" not in st.session_state:
        st.warning("Please login first.")
        st.stop()
    client_id = st.session_state.get("client_id")
    if not client_id:
        st.warning("Select client.")
        st.stop()
        
    st.title("戦略決定ワークスペース (Advanced)")
    st.caption("Phase 6: Multi-Scenario Decision & KPI Targeting")

    run = load_latest_strategy_run(client_id)
    if not run:
        st.info("No strategy run found.")
        st.stop()
        
    package = run.get("final_strategy_package_json", {})
    raw_options = package.get("strategy_options", {}).get("options", [])
    options_data = [StrategyOptionItem(**opt) for opt in raw_options] if raw_options else []
    
    if not options_data:
        st.error("No options available.")
        st.stop()

    # --- Multi-Option Selection ---
    st.subheader("1. 戦略ポートフォリオの選択")
    st.info("実行計画に含める戦略案を選択してください。")
    
    selected_ids = []
    
    # Grid Layout for Cards
    cols = st.columns(3)
    for idx, opt in enumerate(options_data):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(f"**{opt.name}**")
                st.caption(f"効果(Impact): {opt.impact} | リスク(Risk): {opt.risk}")
                if st.checkbox("Include", key=f"chk_{opt.id}"):
                    selected_ids.append(opt.id)

    if not selected_ids:
        st.stop()

    # --- 2. Portfolio Configuration (Weights & Phases) ---
    st.divider()
    st.subheader("2. 実行ポートフォリオの構成")
    
    selected_options_meta = []
    
    for opt_id in selected_ids:
        opt = next(o for o in options_data if o.id == opt_id)
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.markdown(f"**{opt.name}**")
            with c2:
                weight = st.slider(f"投資配分 (Weight)", 0.1, 1.0, 1.0, key=f"w_{opt_id}")
            with c3:
                phase = st.number_input(f"開始フェーズ", min_value=1, max_value=3, value=1, key=f"p_{opt_id}")
            
            
            # --- Portfolio Summary & Validation ---
            selected_options_meta.append({
                "option_id": opt_id, 
                "option_name": opt.name, # For display
                "weight": weight, 
                "phase": phase
            })

    # --- Portfolio Validation Table ---
    if selected_options_meta:
        st.markdown("#### ポートフォリオ概要")
        df_port = pd.DataFrame(selected_options_meta)
        st.dataframe(df_port[["option_name", "weight", "phase"]], use_container_width=True)
        
        total_weight = df_port["weight"].sum()
        if not (0.99 <= total_weight <= 1.01):
            st.error(f"⚠️ 投資配分の合計が 100% (1.0) になるように調整してください。現在: {total_weight:.2f}")
            st.stop()
        else:
            st.success(f"投資配分合計: {total_weight:.2f} (OK)")
            
        # Risk Calculation (Weighted)
        # Mock risk level mapping
        risk_map = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
        weighted_risk = 0
        for item in selected_options_meta:
            opt = next(o for o in options_data if o.id == item["option_id"])
            r_val = risk_map.get(getattr(opt, "risk_level", "Medium"), 2)
            weighted_risk += r_val * item["weight"]
            
        st.metric("予測ポートフォリオ・リスクレベル", f"{weighted_risk:.1f} / 4.0")

    # --- 3. Set Assumed Targets ---
    st.divider()
    st.subheader("3. KPI目標設定 (前提条件)")
    
    # Simulation years hardcoded for MVP
    years = ["2025", "2026", "2027"]
    assumed_targets = {}
    
    cols_years = st.columns(len(years))
    for i, year in enumerate(years):
        with cols_years[i]:
            st.markdown(f"**{year}年度 目標**")
            rev = st.number_input(f"売上高 ($M) {year}", value=100.0, key=f"t_rev_{year}")
            op = st.number_input(f"営業利益率 (%) {year}", value=15.0, key=f"t_op_{year}")
            assumed_targets[year] = {"revenue_mil": rev, "op_margin_pct": op}

    # --- 4. Rationale & Confirm ---
    st.divider()
    rationale = st.text_area("決定理由 (このポートフォリオを選んだ理由)")
    exclusions = st.text_area("戦略的除外事項 (やらないこと・捨てること)", help="戦略とは『何をやらないか』を決めることです。リソースを集中させるために意図的に捨てた選択肢や市場、顧客セグメントを記述してください。")
    
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
        
    if st.button("ポートフォリオを確定して計画を作成", type="primary", disabled=st.session_state.is_processing):
        st.session_state.is_processing = True
        try:
            with st.spinner("Saving & Generating..."):
                # 1. Save Decision
                dec_id = save_decision(
                    run["id"], 
                    selected_options_meta, 
                    rationale,
                    exclusions,
                    assumed_targets, 
                    st.session_state.user.id
                )
                
                # 2. Trigger Execution
                res = run_execution_phase(run["id"], dec_id)
                
                # 3. Complete
                st.success("実行計画が作成されました！")
                st.subheader("Results")
                st.json(res.get("execution_roadmap_json", {}))
                visualize_lineage(res)
                
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            st.session_state.is_processing = False

if __name__ == "__main__":
    main()
