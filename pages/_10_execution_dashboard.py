import streamlit as st
import pandas as pd
from core.supabase_client import get_supabase_client
from core.execution_monitoring_engine import trigger_monitoring_run
from core.style_utils import load_custom_css

st.set_page_config(page_title="Execution Dashboard", layout="wide")

def load_latest_execution_run(client_id):
    sb = get_supabase_client()
    # Join capability usually requires multiple queries in Supabase simple client, or use view.
    # We'll fetch strategy run first for client, then execution runs.
    
    # 1. Fetch latest Strategy Run
    run_res = sb.table("strategy_runs").select("id").eq("client_id", client_id).order("created_at", desc=True).limit(1).execute()
    if not run_res.data:
        return None
        
    sid = run_res.data[0]['id']
    
    # 2. Fetch latest Execution Run for that Strategy
    exec_res = sb.table("strategy_execution_runs").select("*").eq("strategy_run_id", sid).order("created_at", desc=True).limit(1).execute()
    return exec_res.data[0] if exec_res.data else None

def load_monitoring_history(execution_run_id):
    sb = get_supabase_client()
    res = sb.table("monitoring_runs").select("*").eq("execution_run_id", execution_run_id).order("created_at", desc=True).execute()
    return res.data

def main():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()
    if "user" not in st.session_state:
        st.warning("Login required.")
        st.stop()
        
    client_id = st.session_state.get("client_id")
    if not client_id:
        st.warning("Select client.")
        st.stop()
        
    st.title("実行ダッシュボード (モニタリング)")
    
    exec_run = load_latest_execution_run(client_id)
    if not exec_run:
        st.info("No Execution Plan active. Go to Decision Workspace.")
        st.stop()
        
    # Context Header
    st.caption(f"Tracking Execution Run: {exec_run['id']}")
    
    targets = exec_run.get("assumed_kpi_targets_json", {})
    roadmap = exec_run.get("execution_roadmap_json", {})
    
    # --- Tab Layout ---
    tab_plan, tab_monitor, tab_actions = st.tabs(["📅 ロードマップ", "📈 KPIモニタリング", "🛡️ 是正アクション"])
    
    with tab_plan:
        st.subheader("実行ロードマップ")
        actions = roadmap.get("actions", [])
        if actions:
            df = pd.DataFrame(actions)
            st.dataframe(df[["title", "phase", "status"]], use_container_width=True)
        else:
            st.warning("No actions defined.")
            
    with tab_monitor:
        st.subheader("予実管理 (Target vs Actual)")
        
        # 1. Input Actuals
        st.markdown("#### 実績入力")
        current_year = st.selectbox("Year", ["2025", "2026"])
        
        target_map = targets.get(current_year, {})
        if not target_map:
            st.warning(f"No targets set for {current_year}")
        else:
            with st.form("actuals_form"):
                actuals = {}
                c1, c2 = st.columns(2)
                
                # Dynamic inputs based on saved targets
                keys = list(target_map.keys())
                half = len(keys)//2
                
                with c1:
                    for k in keys[:half]:
                        target_val = target_map[k]
                        actuals[k] = st.number_input(f"{k} (Target: {target_val})", value=float(target_val))
                with c2:
                    for k in keys[half:]:
                        target_val = target_map[k]
                        actuals[k] = st.number_input(f"{k} (Target: {target_val})", value=float(target_val))
                        
                if st.form_submit_button("実績を登録して差異分析を実行"):
                    # Process
                    with st.spinner("Analyzing..."):
                        run_id = exec_run['id']
                        kpi_payload = {current_year: actuals}
                        result = trigger_monitoring_run(run_id, kpi_payload, st.session_state.user.id)
                        st.success("Analysis Complete!")
                        st.json(result.get("gap_analysis_json"))
                        
        # 2. History
        st.divider()
        st.subheader("モニタリング履歴")
        history = load_monitoring_history(exec_run['id'])
        for item in history:
            with st.expander(f"Analysis: {item['created_at']}", expanded=False):
                st.json(item["gap_analysis_json"])

    with tab_actions:
        st.subheader("推奨される是正アクション")
        # In a real app, this would query all action items tagged 'corrective'
        st.info("Actions generated from Gap Analysis will appear here.")
        
if __name__ == "__main__":
    main()
