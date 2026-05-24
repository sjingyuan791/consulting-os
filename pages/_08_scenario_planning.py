import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from core.auth import check_auth
from core.analytics_prediction import predict_future_performance
from core.style_utils import load_custom_css

def app():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()
    
    if not check_auth():
        st.warning("ログインしてください。")
        return

    st.title("シナリオ・プランニング (未来予測)")
    
    # Check Data
    if "data_financials" not in st.session_state:
        # Try to fetch from DB if not in session
        if "client_id" in st.session_state and st.session_state.client_id:
            from core.repos.dataset_repo import DatasetRepo
            repo = DatasetRepo()
            cur_fin = repo.get_current_dataset_version(st.session_state.client_id, "financial")
            if cur_fin and cur_fin.get("normalized_json"):
                 st.session_state["data_financials"] = cur_fin["normalized_json"]
        
    if "data_financials" not in st.session_state:
        st.warning("財務データがありません。Analysisページで診断を実行するか、データをアップロードしてください。")
        return
        
    
    raw_data = st.session_state["data_financials"]
    fin_records = []

    # Handle various data structures (Migration from raw list to file-obj list)
    if isinstance(raw_data, list):
        if len(raw_data) > 0 and isinstance(raw_data[0], dict) and "records" in raw_data[0]:
            # Case: List of File Objects (New Upload Format)
            # Inspect all files, prioritize 'financial_standard'
            target_data = next((f for f in raw_data if f.get("type") == "financial_standard"), raw_data[0])
            fin_records = target_data.get("records", [])
        else:
            # Case: List of Records (Legacy)
            fin_records = raw_data
    elif isinstance(raw_data, dict):
        if "records" in raw_data:
             # Case: Single File Object
             fin_records = raw_data["records"]
        else:
             # Case: Dict of records? (Unlikely but fallback)
             fin_records = [raw_data]

    df_fin = pd.DataFrame(fin_records)
    
    if df_fin.empty:
        st.warning("財務データが空です。")
        return

    from core.normalizers import clean_financial_df
    
    # Normalize Columns (Japanese -> English)
    if not df_fin.empty:
        df_fin = clean_financial_df(df_fin)
        
    # Ensure necessary columns exist (Backfill for Lite Template)
    if "gross_profit" not in df_fin.columns:
        if "operating_profit" in df_fin.columns:
            # Fallback: Assume all costs are Variable (COGS) -> Gross Profit = Operating Profit (SGA=0)
            # This allows the simulator to function with 'Variable Cost' sensitivity
            df_fin["gross_profit"] = df_fin["operating_profit"] 
        else:
            # If neither exists (unlikely given validator), set to 0
            df_fin["gross_profit"] = 0
            
    if "operating_profit" not in df_fin.columns:
         df_fin["operating_profit"] = 0

    # --- 1. Base Forecast (Prediction) ---
    st.subheader("1. AI予測 (現状維持シナリオ)")
    st.write("過去の成長率(CAGR)に基づき、今後3年間の業績を予測します。")
    
    # Ensure 'year' column exists (clean_financial_df handles normalization of '年度' -> 'year')
    if "year" not in df_fin.columns:
        st.error("年次データ('year' または '年度')が見つかりません。")
        return

    forecast_years = st.slider("予測年数", 1, 5, 3)
    df_forecast = predict_future_performance(df_fin, years_to_predict=forecast_years)
    
    # Combine History + Forecast
    df_fin['type'] = 'Actual'
    df_combined = pd.concat([df_fin, df_forecast], ignore_index=True)
    
    # Visualization
    fig_pred = px.line(df_combined, x="year", y="sales", color='type', markers=True, title="売上高予測")
    st.plotly_chart(fig_pred, use_container_width=True)
    
    with st.expander("予測詳細データ"):
        st.dataframe(df_combined[['year', 'type', 'sales', 'gross_profit', 'operating_profit']])

    st.divider()

    # --- 2. Scenario Simulator (What-If) ---
    st.subheader("2. シナリオ・シミュレーター (What-If分析)")
    st.info("変数を調整して、利益へのインパクトをシミュレーションします。")

    # Get latest year data as base
    base_year_row = df_fin.sort_values("year").iloc[-1]
    base_year = int(base_year_row['year'])
    base_sales = base_year_row['sales']
    base_gp = base_year_row['gross_profit']
    base_op = base_year_row['operating_profit']
    base_fixed_costs = base_gp - base_op # Roughly fixed costs estimate
    base_variable_costs = base_sales - base_gp
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown(f"**基準年: {base_year}年度**")
        st.write("---")
        st.write("**変数設定 (対前年比)**")
        
        delta_price = st.slider("販売単価 (%)", -20, 20, 0, help="価格を上げると数量が減る可能性がありますが、ここでは独立変数として扱います")
        delta_vol = st.slider("販売数量 (%)", -20, 20, 0)
        delta_v_cost = st.slider("変動原価 (%)", -20, 20, 0, help="仕入原価など")
        delta_f_cost = st.slider("固定費 (%)", -20, 20, 0, help="人件費、家賃など")
        
    with col2:
        # Calculation
        # Assumptions:
        # New Sales = Base Sales * (1 + price%) * (1 + vol%)
        # New Variable Cost = Base Var Cost * (1 + v_cost%) * (1 + vol%)
        # New Fixed Cost = Base Fix Cost * (1 + f_cost%)
        
        sim_sales = base_sales * (1 + delta_price/100) * (1 + delta_vol/100)
        sim_vc = base_variable_costs * (1 + delta_v_cost/100) * (1 + delta_vol/100)
        sim_fc = base_fixed_costs * (1 + delta_f_cost/100)
        
        sim_gp = sim_sales - sim_vc
        sim_op = sim_gp - sim_fc
        
        # Visualize Waterfall or Bar comparison
        compare_data = pd.DataFrame({
            "Metric": ["売上高", "売上高", "営業利益", "営業利益"],
            "Scenario": ["現状", "シミュレーション", "現状", "シミュレーション"],
            "Value": [base_sales, sim_sales, base_op, sim_op]
        })
        
        fig_sim = px.bar(compare_data, x="Metric", y="Value", color="Scenario", barmode="group",
                         title=f"シミュレーション結果 (営業利益: {sim_op:,.0f})")
        
        # Color logic: Green if OP increased, Red if decreased
        op_diff = sim_op - base_op
        color = "green" if op_diff >= 0 else "red"
        
        st.plotly_chart(fig_sim, use_container_width=True)
        
        st.markdown(f"### 営業利益インパクト: :{color}[{op_diff:+,.0f}]")
        st.caption("※ 簡易シミュレーションのため、税金や営業外損益は考慮していません。")

    st.divider()
    st.markdown("### Next Step")
    st.write("このシミュレーション結果に基づき、具体的なアクションプランを作成しましょう。")
    if st.button("計画策定へ移動"):
        st.switch_page("pages/07_plan_generator.py")

if __name__ == "__main__":
    app()
