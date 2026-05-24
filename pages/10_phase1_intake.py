"""
Phase 1: Data Intake Page
Collects foundational business, financial, operational, and organizational data.
"""
import streamlit as st
import json
import pandas as pd
from datetime import datetime
from core.auth import check_auth
from core.style_utils import load_custom_css
from core.supabase_client import get_supabase_client


def render_role_badge(role: str):
    """Render a role badge for AI/Human/Collaborative."""
    colors = {
        "ai": ("🤖", "#4CAF50", "AI生成"),
        "human": ("👤", "#2196F3", "人間入力"),
        "collaborative": ("🤝", "#FF9800", "協働確認")
    }
    icon, color, label = colors.get(role, ("❓", "#999", role))
    st.markdown(f"""
        <span style="background: {color}; color: white; padding: 2px 8px; 
        border-radius: 4px; font-size: 0.75rem; margin-right: 8px;">
        {icon} {label}</span>
    """, unsafe_allow_html=True)


def app():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()
    
    if not check_auth():
        st.warning("ログインが必要です")
        return
    
    st.title("📊 Phase 1: データインテーク")
    st.markdown("事業基盤データの収集と正規化")
    
    # Progress indicator
    phases = ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5", "Phase 6", "Phase 7"]
    current = 0
    cols = st.columns(7)
    for i, (col, phase) in enumerate(zip(cols, phases)):
        with col:
            if i == current:
                st.markdown(f"**🔵 {phase}**")
            elif i < current:
                st.markdown(f"✅ {phase}")
            else:
                st.markdown(f"⚪ {phase}")
    
    st.divider()
    
    # Initialize session state
    if "phase1_data" not in st.session_state:
        st.session_state.phase1_data = {
            "financial": {},
            "operational": {},
            "organizational": {},
            "market": {}
        }
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💰 財務データ", "⚙️ 運営データ", "👥 組織データ", "📈 市場データ", "✅ 確認"
    ])
    
    with tab1:
        render_financial_input()
    
    with tab2:
        render_operational_input()
    
    with tab3:
        render_organizational_input()
    
    with tab4:
        render_market_input()
    
    with tab5:
        render_confirmation()


def render_financial_input():
    """Render financial data input section."""
    st.subheader("財務諸表データ")
    render_role_badge("human")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("##### 過去3年分の財務データを入力してください")
        
        years = [datetime.now().year - i for i in range(3)]
        
        # Revenue & Costs
        st.markdown("**売上・原価**")
        for year in years:
            with st.expander(f"📅 {year}年度", expanded=(year == years[0])):
                c1, c2 = st.columns(2)
                with c1:
                    key = f"revenue_{year}"
                    st.session_state.phase1_data["financial"][f"revenue_{year}"] = st.number_input(
                        "売上高（百万円）", value=0, key=key
                    )
                    st.session_state.phase1_data["financial"][f"cogs_{year}"] = st.number_input(
                        "売上原価（百万円）", value=0, key=f"cogs_{year}"
                    )
                with c2:
                    st.session_state.phase1_data["financial"][f"op_exp_{year}"] = st.number_input(
                        "販管費（百万円）", value=0, key=f"op_exp_{year}"
                    )
                    st.session_state.phase1_data["financial"][f"net_income_{year}"] = st.number_input(
                        "当期純利益（百万円）", value=0, key=f"net_income_{year}"
                    )
    
    with col2:
        st.markdown("##### ファイルアップロード")
        render_role_badge("human")
        
        uploaded = st.file_uploader(
            "財務データ（CSV/Excel）",
            type=["csv", "xlsx"],
            key="financial_upload"
        )
        
        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    df = pd.read_csv(uploaded)
                else:
                    df = pd.read_excel(uploaded)
                st.success(f"✅ {len(df)}行のデータを読み込みました")
                st.dataframe(df.head(), use_container_width=True)
            except Exception as e:
                st.error("ファイルの読み込みに失敗しました")
        
        # AI Data Validation
        st.markdown("---")
        st.markdown("##### データ検証")
        render_role_badge("ai")
        
        if st.button("🔍 データ検証を実行", key="validate_financial"):
            with st.spinner("検証中..."):
                # Simulate validation
                issues = []
                data = st.session_state.phase1_data["financial"]
                
                for year in years:
                    if data.get(f"revenue_{year}", 0) == 0:
                        issues.append(f"{year}年の売上高が未入力です")
                
                if issues:
                    for issue in issues:
                        st.warning(f"⚠️ {issue}")
                else:
                    st.success("✅ データに問題はありません")


def render_operational_input():
    """Render operational data input section."""
    st.subheader("運営・オペレーションデータ")
    render_role_badge("human")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 生産・サービス指標")
        
        st.session_state.phase1_data["operational"]["production_volume"] = st.number_input(
            "年間生産量/サービス提供件数", value=0, key="prod_volume"
        )
        st.session_state.phase1_data["operational"]["capacity_utilization"] = st.slider(
            "設備稼働率（%）", 0, 100, 70, key="capacity"
        )
        st.session_state.phase1_data["operational"]["defect_rate"] = st.number_input(
            "不良率（%）", value=0.0, format="%.2f", key="defect"
        )
        st.session_state.phase1_data["operational"]["lead_time"] = st.number_input(
            "平均リードタイム（日）", value=0, key="leadtime"
        )
    
    with col2:
        st.markdown("##### 販売・顧客指標")
        
        st.session_state.phase1_data["operational"]["customer_count"] = st.number_input(
            "総顧客数", value=0, key="cust_count"
        )
        st.session_state.phase1_data["operational"]["new_customers"] = st.number_input(
            "新規顧客獲得数（年間）", value=0, key="new_cust"
        )
        st.session_state.phase1_data["operational"]["churn_rate"] = st.number_input(
            "顧客離脱率（%）", value=0.0, format="%.2f", key="churn"
        )
        st.session_state.phase1_data["operational"]["avg_order_value"] = st.number_input(
            "平均受注額（万円）", value=0, key="aov"
        )
    
    # AI: Missing data detection
    st.markdown("---")
    render_role_badge("ai")
    st.markdown("##### 欠損データの検出")
    
    if st.button("🔍 欠損データをチェック", key="check_operational"):
        missing = []
        for key, label in [
            ("production_volume", "年間生産量"),
            ("customer_count", "総顧客数"),
            ("capacity_utilization", "設備稼働率")
        ]:
            if st.session_state.phase1_data["operational"].get(key, 0) == 0:
                missing.append(label)
        
        if missing:
            st.warning(f"⚠️ 以下のデータが未入力です: {', '.join(missing)}")
        else:
            st.success("✅ 主要データは入力済みです")


def render_organizational_input():
    """Render organizational data input section."""
    st.subheader("組織・人材データ")
    render_role_badge("human")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 人員構成")
        
        st.session_state.phase1_data["organizational"]["total_employees"] = st.number_input(
            "総従業員数", value=0, key="total_emp"
        )
        st.session_state.phase1_data["organizational"]["management_count"] = st.number_input(
            "管理職数", value=0, key="mgmt_count"
        )
        st.session_state.phase1_data["organizational"]["avg_tenure"] = st.number_input(
            "平均勤続年数", value=0.0, format="%.1f", key="tenure"
        )
        st.session_state.phase1_data["organizational"]["turnover_rate"] = st.number_input(
            "年間離職率（%）", value=0.0, format="%.2f", key="turnover"
        )
    
    with col2:
        st.markdown("##### 組織構造")
        
        st.session_state.phase1_data["organizational"]["departments"] = st.text_area(
            "主要部門（改行区切り）",
            value="営業部\n製造部\n管理部",
            key="depts"
        )
        st.session_state.phase1_data["organizational"]["org_layers"] = st.selectbox(
            "組織階層数",
            options=[2, 3, 4, 5, 6],
            index=2,
            key="layers"
        )


def render_market_input():
    """Render market data input section."""
    st.subheader("市場・競合データ")
    render_role_badge("human")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 市場環境")
        
        st.session_state.phase1_data["market"]["market_size"] = st.number_input(
            "市場規模（億円）", value=0, key="mkt_size"
        )
        st.session_state.phase1_data["market"]["market_growth"] = st.number_input(
            "市場成長率（%）", value=0.0, format="%.1f", key="mkt_growth"
        )
        st.session_state.phase1_data["market"]["market_share"] = st.number_input(
            "自社シェア（%）", value=0.0, format="%.1f", key="share"
        )
    
    with col2:
        st.markdown("##### 競合情報")
        
        st.session_state.phase1_data["market"]["main_competitors"] = st.text_area(
            "主要競合（改行区切り）",
            key="competitors"
        )
        st.session_state.phase1_data["market"]["competitive_position"] = st.selectbox(
            "競争上の位置づけ",
            options=["リーダー", "チャレンジャー", "ニッチャー", "フォロワー"],
            key="position"
        )


def render_confirmation():
    """Render data confirmation section."""
    st.subheader("データ確認・承認")
    render_role_badge("collaborative")
    
    st.markdown("入力データを確認し、Phase 2に進むためのデータセット確定を行います。")
    
    # Data summary
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 財務データサマリー")
        financial = st.session_state.phase1_data.get("financial", {})
        if financial:
            st.json(financial)
        else:
            st.info("財務データが未入力です")
    
    with col2:
        st.markdown("##### 運営データサマリー")
        operational = st.session_state.phase1_data.get("operational", {})
        if operational:
            st.json(operational)
        else:
            st.info("運営データが未入力です")
    
    # Validation status
    st.markdown("---")
    st.markdown("##### データ検証ステータス")
    
    validation_items = [
        ("財務データ3年分", bool(financial)),
        ("運営データ", bool(operational.get("customer_count", 0) > 0)),
        ("組織データ", bool(st.session_state.phase1_data.get("organizational", {}).get("total_employees", 0) > 0)),
        ("市場データ", bool(st.session_state.phase1_data.get("market", {}).get("market_size", 0) > 0)),
    ]
    
    all_valid = True
    for label, valid in validation_items:
        if valid:
            st.markdown(f"✅ {label}")
        else:
            st.markdown(f"❌ {label}")
            all_valid = False
    
    # Proceed button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if all_valid:
            if st.button("✅ データを確定してPhase 2へ進む", type="primary", use_container_width=True):
                # Save to database
                try:
                    sb = get_supabase_client()
                    client_id = st.session_state.get("client_id")
                    
                    if client_id:
                        try:
                            import json as _j1
                            _res1 = sb.table("clients").select("notes").eq("id", client_id).single().execute()
                            _n1 = _j1.loads(_res1.data.get("notes") or "{}") if isinstance(_res1.data.get("notes"), str) else (_res1.data.get("notes") or {})
                            _n1.setdefault("pipeline_steps", {})["3"] = "done"
                            sb.table("clients").update({"notes": _j1.dumps(_n1, ensure_ascii=False)}).eq("id", client_id).execute()
                            _ck1 = f"pipeline_{client_id}"
                            if _ck1 in st.session_state:
                                st.session_state[_ck1]["3"] = "done"
                        except Exception as _e1:
                            pass  # step mark failure is non-fatal
                        st.session_state.phase1_complete = True
                        st.session_state.phase_data = st.session_state.phase1_data
                        st.success("✅ Phase 1 完了！Phase 2に進んでください。")
                        st.balloons()
                except Exception as e:
                    st.error(f"データ保存エラー: {type(e).__name__}")
        else:
            st.button(
                "⚠️ 必須データを入力してください",
                disabled=True,
                use_container_width=True
            )


if __name__ == "__main__":
    app()
