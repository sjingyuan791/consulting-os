import streamlit as st
import pandas as pd
from core.supabase_client import get_supabase_client
from core.strategic_guardrails_service import save_guardrails, get_latest_guardrails
from core.schemas.strategy import GuardrailsSchema
from core.sidebar import render_sidebar
from core.style_utils import load_custom_css

st.set_page_config(page_title="Strategic Guardrails", layout="wide",
    initial_sidebar_state="expanded")

def app():
    load_custom_css()
    render_sidebar()
    
    if "user" not in st.session_state:
        st.warning("Please login first.")
        st.stop()
        
    client_id = st.session_state.get("client_id")
    if not client_id:
        st.warning("Select client.")
        st.stop()

    st.title("戦略的ガードレール (Phase 1)")
    st.caption("戦略策定における「譲れない制約条件」や「境界線」を定義します。")
    
    # Load existing
    existing = get_latest_guardrails(client_id)
    
    with st.form("guardrails_form"):
        st.subheader("1. 中核となる目的・アイデンティティ")
        mission_objective = st.text_area("ミッション / 戦略目標", 
                                         value=existing.mission_objective if existing else "",
                                         help="この中期経営計画の究極のゴールは何ですか？")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            time_horizon = st.slider("計画期間 (年)", min_value=1, max_value=10, 
                                           value=existing.time_horizon_years if existing else 3)
        with c2:
            investment_limit = st.slider("最大投資可能額 (百万円)", min_value=0.0, max_value=5000.0, step=100.0,
                                               value=float(existing.investment_limit) if existing and existing.investment_limit else 500.0)
        with c3:
            risk_options = ["low", "medium", "high"]
            default_risk_idx = risk_options.index(existing.risk_tolerance) if existing and existing.risk_tolerance in risk_options else 1
            risk_tolerance = st.selectbox("リスク許容度", risk_options, index=default_risk_idx, format_func=lambda x: x.capitalize())
            
        st.divider()
        st.subheader("2. 戦略的境界線 (除外事項)")
        st.info("戦略とは「何をしないか」を決めることです。")
        
        # Simple text input for now, parsed to list/dict later if needed
        # Or structured expander
        
        no_entry_markets = st.text_area("参入しない市場・セグメント (カンマ区切り)", 
                                        value=", ".join(existing.strategic_boundaries.get("no_entry_markets", [])) if existing else "")
        
        excluded_models = st.text_area("採用しないビジネスモデル・手法",
                                       value=", ".join(existing.strategic_boundaries.get("excluded_models", [])) if existing else "")
        
        st.divider()
        st.subheader("3. 成功の定義")
        success_def = st.text_area("3年後の成功状態（あるべき姿）", 
                                   value=existing.success_state_definition if existing else "")
        
        st.write("---")
        submitted = st.form_submit_button("戦略的ガードレールを保存", type="primary")
        
        if submitted:
            # Parse lists
            boundaries = {
                "no_entry_markets": [x.strip() for x in no_entry_markets.split(",") if x.strip()],
                "excluded_models": [x.strip() for x in excluded_models.split(",") if x.strip()]
            }
            
            schema = GuardrailsSchema(
                mission_objective=mission_objective,
                time_horizon_years=time_horizon,
                investment_limit=investment_limit,
                risk_tolerance=risk_tolerance,
                strategic_boundaries=boundaries,
                success_state_definition=success_def,
                decision_rules={} # Placeholder for now
            )
            
            save_guardrails(client_id, schema)
            st.success("ガードレール設定を保存しました！ 今後の分析において、この制約条件が適用されます。")

if __name__ == "__main__":
    app()
