"""
Financial Simulation Dashboard.
財務シミュレーションダッシュボード

機能:
1. 施策別インパクト分析
2. 月次CFシミュレーション
3. 借入返済スケジュール
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from core.auth import check_auth
from core.style_utils import load_custom_css
from core.initiative_impact_model import (
    InitiativeInput, InitiativeType, ConfidenceLevel,
    calculate_initiative_impact, format_impact_report
)
from core.monthly_cashflow_simulation import (
    simulate_monthly_cashflow, format_cashflow_table, CashFlowDrivers
)
from core.loan_repayment_engine import (
    calculate_loan_schedule, simulate_reschedule, format_loan_schedule,
    LoanContract, LoanType, RepaymentMethod
)


def app():
    check_auth()
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()

    # ---- ステップバッジ ----
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:0.5rem;">
        <div style="background:#fef3c7;color:#92400e;font-size:0.72rem;font-weight:700;
                    padding:3px 10px;border-radius:999px;letter-spacing:0.06em;">
            STEP 16 CF計画策定
        </div>
        <div style="background:#fef3c7;color:#92400e;font-size:0.72rem;font-weight:700;
                    padding:3px 10px;border-radius:999px;letter-spacing:0.06em;">
            STEP 17 3か年数値計画
        </div>
        <div style="font-size:0.8rem;color:#9ca3af;">数値計画フェーズ</div>
    </div>
    """, unsafe_allow_html=True)

    st.title("📊 財務シミュレーション")
    st.caption("STEP 16: 月次CF計画　／　STEP 17: 3か年PL・BS・CF計画")

    # サイドバー: 基本情報
    with st.sidebar:
        st.header("📋 基本情報")

        base_revenue = st.number_input(
            "年間売上高（万円）",
            min_value=0,
            value=10000,
            step=1000,
            help="直近決算の売上高"
        ) * 10000

        base_op_profit = st.number_input(
            "年間営業利益（万円）",
            min_value=-10000,
            value=500,
            step=100
        ) * 10000

        opening_cash = st.number_input(
            "現預金残高（万円）",
            min_value=0,
            value=2000,
            step=100
        ) * 10000

        industry = st.selectbox(
            "業種",
            ["製造業", "小売業", "建設業", "サービス業", "飲食業", "default"]
        )

    # メインタブ
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 施策インパクト",
        "💰 月次CF  ← STEP 16",
        "🏦 借入返済",
        "📊 統合ビュー",
        "📅 3か年計画  ← STEP 17",
    ])
    
    # ==========================================
    # TAB 1: 施策インパクト
    # ==========================================
    with tab1:
        st.header("施策別インパクト分析")
        st.info("💡 各施策の効果を **根拠付き** で計算します")
        
        # 施策追加フォーム
        with st.expander("➕ 施策を追加", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                init_name = st.text_input("施策名", placeholder="例: 新規顧客開拓")
                init_type = st.selectbox(
                    "施策タイプ",
                    [t.value for t in InitiativeType],
                    format_func=lambda x: {
                        "sales_price": "💹 単価向上",
                        "sales_volume": "📦 数量拡大",
                        "new_customer": "🎯 新規顧客獲得",
                        "retention": "🔄 既存顧客維持",
                        "cost_fixed": "✂️ 固定費削減",
                        "cost_variable": "📉 変動費削減",
                        "investment": "🏭 設備投資",
                        "working_capital": "💵 運転資本改善",
                        "other": "📋 その他"
                    }.get(x, x)
                )
            
            with col2:
                confidence = st.selectbox(
                    "確度",
                    [c.value for c in ConfidenceLevel],
                    format_func=lambda x: {
                        "high": "🟢 高 (90%+)",
                        "medium": "🟡 中 (60-90%)",
                        "low": "🟠 低 (30-60%)",
                        "uncertain": "🔴 不確実 (<30%)"
                    }.get(x, x)
                )
                impl_months = st.slider("効果発現までの月数", 0, 12, 3)
            
            # タイプ別パラメータ
            st.subheader("詳細パラメータ")
            
            if init_type in ["sales_price", "sales_volume", "new_customer", "retention"]:
                c1, c2, c3, c4 = st.columns(4)
                target_customers = c1.number_input("対象顧客数", 0, 10000, 100)
                conversion_rate = c2.slider("成約率 (%)", 0, 100, 10) / 100
                unit_price = c3.number_input("単価（万円）", 0, 10000, 50) * 10000
                margin_rate = c4.slider("粗利率 (%)", 0, 100, 30) / 100
                
            elif init_type in ["cost_fixed", "cost_variable"]:
                c1, c2 = st.columns(2)
                current_cost = c1.number_input("現在コスト（万円/年）", 0, 100000, 1000) * 10000
                reduction_rate = c2.slider("削減率 (%)", 0, 50, 10) / 100
                
            elif init_type == "investment":
                c1, c2, c3 = st.columns(3)
                initial_investment = c1.number_input("初期投資（万円）", 0, 100000, 500) * 10000
                annual_benefit = c2.number_input("年間効果（万円）", 0, 100000, 200) * 10000
                useful_life = c3.number_input("耐用年数", 1, 20, 5)
            
            if st.button("➕ 施策を追加", type="primary"):
                if "initiatives" not in st.session_state:
                    st.session_state.initiatives = []
                
                # 施策を作成
                init = InitiativeInput(
                    id=str(len(st.session_state.initiatives) + 1),
                    name=init_name or f"施策{len(st.session_state.initiatives) + 1}",
                    description="",
                    initiative_type=InitiativeType(init_type),
                    confidence=ConfidenceLevel(confidence),
                    implementation_months=impl_months,
                )
                
                # タイプ別パラメータ設定
                if init_type in ["sales_price", "sales_volume", "new_customer", "retention"]:
                    init.target_customers = target_customers
                    init.conversion_rate = conversion_rate
                    init.unit_price = unit_price
                    init.margin_rate = margin_rate
                elif init_type in ["cost_fixed", "cost_variable"]:
                    init.current_cost = current_cost
                    init.reduction_rate = reduction_rate
                elif init_type == "investment":
                    init.initial_investment = initial_investment
                    init.annual_benefit = annual_benefit
                    init.useful_life_years = useful_life
                
                st.session_state.initiatives.append(init)
                st.success(f"✅ 「{init.name}」を追加しました")
                st.rerun()
        
        # 施策一覧表示
        if "initiatives" in st.session_state and st.session_state.initiatives:
            st.subheader("📋 登録済み施策")
            
            for i, init in enumerate(st.session_state.initiatives):
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    col1.write(f"**{init.name}** ({init.initiative_type.value})")
                    col2.write(f"確度: {init.confidence.value}")
                    if col3.button("🗑️", key=f"del_{i}"):
                        st.session_state.initiatives.pop(i)
                        st.rerun()
            
            # 計算実行
            if st.button("🔄 インパクト計算", type="primary"):
                result = calculate_initiative_impact(
                    base_revenue=base_revenue,
                    base_operating_profit=base_op_profit,
                    initiatives=st.session_state.initiatives
                )
                st.session_state.impact_result = result
        
        # 結果表示
        if "impact_result" in st.session_state:
            result = st.session_state.impact_result
            
            st.divider()
            st.subheader("📊 分析結果")
            
            # KPIカード
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "売上インパクト",
                    f"{result.summary.total_revenue_impact / 10000:,.0f}万円",
                    f"+{result.projected_revenue_growth:.1f}%"
                )
            
            with col2:
                st.metric(
                    "営業利益インパクト",
                    f"{result.summary.total_operating_profit_impact / 10000:,.0f}万円",
                    f"+{result.projected_profit_growth:.1f}%"
                )
            
            with col3:
                st.metric(
                    "必要投資",
                    f"{result.summary.total_investment_required / 10000:,.0f}万円"
                )
            
            with col4:
                if result.summary.overall_roi:
                    st.metric("ROI", f"{result.summary.overall_roi:.1f}%")
                else:
                    st.metric("ROI", "-")
            
            # 確度別内訳
            st.subheader("確度別インパクト")
            conf_data = pd.DataFrame({
                "確度": ["高確度", "中確度", "低確度"],
                "金額（万円）": [
                    result.summary.high_confidence_impact / 10000,
                    result.summary.medium_confidence_impact / 10000,
                    result.summary.low_confidence_impact / 10000,
                ]
            })
            
            fig = px.bar(conf_data, x="確度", y="金額（万円）", 
                        color="確度", 
                        color_discrete_map={"高確度": "green", "中確度": "orange", "低確度": "red"})
            st.plotly_chart(fig, use_container_width=True)
            
            # 施策詳細
            st.subheader("📋 施策別詳細")
            for calc in result.calculations:
                with st.expander(f"{calc.initiative_name} - {calc.operating_profit_impact / 10000:,.0f}万円/年"):
                    
                    # 計算過程
                    st.markdown("**計算根拠:**")
                    for step in calc.calculation_steps:
                        st.write(f"- {step}")
                    
                    # レビューポイント
                    if calc.human_review_required:
                        st.warning("⚠️ 人間確認が必要です")
                        for rp in calc.review_points:
                            st.write(f"  - {rp}")
    
    # ==========================================
    # TAB 2: 月次CF
    # ==========================================
    with tab2:
        st.header("月次資金繰りシミュレーション")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("入金条件")
            collection_days = st.slider("売掛金回収日数", 0, 90, 30)
            cash_sales_ratio = st.slider("現金売上比率 (%)", 0, 100, 10) / 100
        
        with col2:
            st.subheader("支払条件")
            payment_days = st.slider("買掛金支払日数", 0, 90, 30)
            cogs_ratio = st.slider("売上原価率 (%)", 0, 100, 60) / 100
        
        col3, col4 = st.columns(2)
        
        with col3:
            monthly_fixed = st.number_input("月間固定費（万円）", 0, 10000, 300) * 10000
            monthly_personnel = st.number_input("月間人件費（万円）", 0, 10000, 200) * 10000
        
        with col4:
            monthly_loan = st.number_input("月間借入返済（万円）", 0, 1000, 50) * 10000
            start_month = st.selectbox("開始月", range(1, 13), index=3)
        
        if st.button("📊 CF予測を実行", type="primary"):
            forecast = simulate_monthly_cashflow(
                annual_sales=base_revenue,
                cogs_ratio=cogs_ratio,
                collection_days=collection_days,
                payment_days=payment_days,
                monthly_fixed_costs=monthly_fixed,
                monthly_personnel_costs=monthly_personnel,
                monthly_loan_repayment=monthly_loan,
                opening_cash=opening_cash,
                industry=industry,
                start_year=2024,
                start_month=start_month,
                num_months=12
            )
            st.session_state.cf_forecast = forecast
            _cid16 = st.session_state.get("client_id")
            if _cid16:
                try:
                    import json as _j16
                    from core.supabase_client import get_supabase_client as _gsb16
                    _sb16 = _gsb16()
                    _r16 = _sb16.table("clients").select("notes").eq("id", _cid16).single().execute()
                    _n16 = _j16.loads(_r16.data.get("notes") or "{}") if isinstance(_r16.data.get("notes"), str) else (_r16.data.get("notes") or {})
                    _n16.setdefault("pipeline_steps", {})["16"] = "done"
                    _sb16.table("clients").update({"notes": _j16.dumps(_n16, ensure_ascii=False)}).eq("id", _cid16).execute()
                    _ck16 = f"pipeline_{_cid16}"
                    if _ck16 in st.session_state:
                        st.session_state[_ck16]["16"] = "done"
                except Exception:
                    pass
        
        if "cf_forecast" in st.session_state:
            forecast = st.session_state.cf_forecast
            
            # サマリー
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("総入金", f"{forecast.total_inflow / 10000:,.0f}万円")
            with col2:
                st.metric("総支出", f"{forecast.total_outflow / 10000:,.0f}万円")
            with col3:
                color = "normal" if forecast.net_cf_total >= 0 else "inverse"
                st.metric("純CF", f"{forecast.net_cf_total / 10000:,.0f}万円")
            with col4:
                color = "normal" if forecast.lowest_balance >= 0 else "inverse"
                st.metric(
                    "最低残高",
                    f"{forecast.lowest_balance / 10000:,.0f}万円",
                    f"({forecast.lowest_balance_month})"
                )
            
            # 警告
            if forecast.negative_months:
                st.error(f"⚠️ 資金ショート警告: {', '.join(forecast.negative_months)}")
            
            # グラフ
            cf_df = pd.DataFrame([{
                "月": m.month,
                "入金": m.total_cash_inflow / 10000,
                "支出": -m.total_operating_outflow / 10000,
                "返済": -m.total_financing_outflow / 10000,
                "残高": m.closing_cash / 10000,
            } for m in forecast.months])
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=cf_df["月"], y=cf_df["入金"], name="入金", marker_color="green"))
            fig.add_trace(go.Bar(x=cf_df["月"], y=cf_df["支出"], name="支出", marker_color="red"))
            fig.add_trace(go.Bar(x=cf_df["月"], y=cf_df["返済"], name="返済", marker_color="orange"))
            fig.add_trace(go.Scatter(x=cf_df["月"], y=cf_df["残高"], name="残高", 
                                     mode="lines+markers", line=dict(color="blue", width=3)))
            
            fig.update_layout(title="月次資金繰り予測", barmode="relative", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # テーブル
            with st.expander("📋 詳細テーブル"):
                detail_df = pd.DataFrame([{
                    "月": m.month,
                    "売上": f"{m.sales/10000:,.0f}",
                    "入金": f"{m.total_cash_inflow/10000:,.0f}",
                    "支出": f"{m.total_operating_outflow/10000:,.0f}",
                    "返済": f"{m.total_financing_outflow/10000:,.0f}",
                    "NetCF": f"{m.net_cf/10000:,.0f}",
                    "残高": f"{m.closing_cash/10000:,.0f}",
                    "警告": m.warning_message or "-"
                } for m in forecast.months])
                st.dataframe(detail_df, use_container_width=True)
    
    # ==========================================
    # TAB 3: 借入返済
    # ==========================================
    with tab3:
        st.header("借入返済スケジュール")
        
        # 借入登録
        with st.expander("➕ 借入を登録", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                bank_name = st.text_input("銀行名", placeholder="〇〇銀行")
                current_balance = st.number_input("現在残高（万円）", 0, 100000, 5000) * 10000
            
            with col2:
                interest_rate = st.number_input("金利 (%)", 0.0, 20.0, 1.5, step=0.1) / 100
                maturity = st.date_input("最終返済日", value=date(2030, 3, 31))
            
            with col3:
                repay_method = st.selectbox(
                    "返済方式",
                    ["equal_principal", "equal_payment"],
                    format_func=lambda x: "元金均等" if x == "equal_principal" else "元利均等"
                )
            
            if st.button("➕ 借入を登録"):
                if "loans" not in st.session_state:
                    st.session_state.loans = []
                
                st.session_state.loans.append({
                    "bank_name": bank_name or f"銀行{len(st.session_state.loans) + 1}",
                    "current_balance": current_balance,
                    "interest_rate": interest_rate,
                    "maturity_date": maturity.strftime("%Y-%m"),
                    "repayment_method": repay_method,
                })
                st.success("✅ 借入を登録しました")
                st.rerun()
        
        # 借入一覧
        if "loans" in st.session_state and st.session_state.loans:
            st.subheader("📋 登録済み借入")
            
            total_balance = sum(l["current_balance"] for l in st.session_state.loans)
            st.metric("借入残高合計", f"{total_balance / 10000:,.0f}万円")
            
            for i, loan in enumerate(st.session_state.loans):
                with st.expander(f"{loan['bank_name']} - {loan['current_balance']/10000:,.0f}万円"):
                    st.write(f"金利: {loan['interest_rate']*100:.2f}%")
                    st.write(f"最終返済: {loan['maturity_date']}")
                    
                    # スケジュール計算
                    schedule = calculate_loan_schedule(
                        bank_name=loan["bank_name"],
                        current_balance=loan["current_balance"],
                        interest_rate=loan["interest_rate"],
                        maturity_date=loan["maturity_date"],
                        repayment_method=loan["repayment_method"],
                        start_month=date.today().strftime("%Y-%m")
                    )
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("月次返済", f"{schedule.months[0].total_payment/10000:,.1f}万円")
                    col2.metric("総返済額", f"{schedule.total_payment/10000:,.0f}万円")
                    col3.metric("支払利息", f"{schedule.total_interest/10000:,.0f}万円")
                    
                    # リスケシミュレーション
                    st.subheader("🔄 リスケシナリオ")
                    
                    rc1, rc2, rc3 = st.columns(3)
                    ext_months = rc1.number_input("期間延長（月）", 0, 60, 12, key=f"ext_{i}")
                    grace_months = rc2.number_input("据置期間（月）", 0, 24, 0, key=f"grace_{i}")
                    new_rate = rc3.number_input("変更後金利 (%)", 0.0, 10.0, loan["interest_rate"]*100, key=f"rate_{i}") / 100
                    
                    if st.button("シミュレーション実行", key=f"resim_{i}"):
                        res = simulate_reschedule(
                            bank_name=loan["bank_name"],
                            current_balance=loan["current_balance"],
                            interest_rate=loan["interest_rate"],
                            maturity_date=loan["maturity_date"],
                            extension_months=ext_months,
                            grace_period_months=grace_months,
                            new_interest_rate=new_rate if new_rate != loan["interest_rate"] else None
                        )
                        
                        st.success(f"月次返済: {res.monthly_payment_reduction/10000:+,.1f}万円軽減")
                        st.info(f"総利息増加: {res.total_interest_increase/10000:,.0f}万円")
                        
                        for point in res.bank_negotiation_points:
                            st.write(f"📌 {point}")
    
    # ==========================================
    # TAB 4: 統合ビュー
    # ==========================================
    with tab4:
        st.header("📊 統合財務ビュー")
        
        if all(k in st.session_state for k in ["impact_result", "cf_forecast"]):
            impact = st.session_state.impact_result
            cf = st.session_state.cf_forecast
            
            # 統合KPI
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("売上予測", f"{impact.projected_revenue/10000:,.0f}万円")
            with col2:
                st.metric("営業利益予測", f"{impact.projected_operating_profit/10000:,.0f}万円")
            with col3:
                st.metric("年間CF", f"{cf.net_cf_total/10000:,.0f}万円")
            with col4:
                loan_total = sum(l["current_balance"] for l in st.session_state.get("loans", []))
                st.metric("借入残高", f"{loan_total/10000:,.0f}万円")
            
            # 施策推奨
            st.subheader("🎯 施策推奨")
            
            high_impact = [c for c in impact.calculations 
                          if c.confidence.value in ["high", "medium"] and c.operating_profit_impact > 0]
            high_impact.sort(key=lambda x: x.operating_profit_impact, reverse=True)
            
            for i, calc in enumerate(high_impact[:3], 1):
                st.success(f"**{i}. {calc.initiative_name}** - 年間 {calc.operating_profit_impact/10000:,.0f}万円")
            
            # 資金繰り警告
            if cf.negative_months:
                st.error(f"⚠️ 資金ショートリスク: {', '.join(cf.negative_months)}")
                st.write("**対策案:**")
                st.write("- 入金サイト短縮の交渉")
                st.write("- 支払サイト延長の交渉")
                st.write("- 緊急融資の検討")
        else:
            st.info("各タブでシミュレーションを実行してください")

    # ==========================================
    # TAB 5: 3か年数値計画 (STEP 17)
    # ==========================================
    with tab5:
        _render_three_year_plan(client_id=st.session_state.get("client_id"), base_revenue=base_revenue, base_op_profit=base_op_profit)


def _render_three_year_plan(client_id: str | None, base_revenue: float, base_op_profit: float):
    """STEP 17 — 3か年PL・BS・CF計画タブ。"""
    import json
    import plotly.graph_objects as go

    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:1rem;">
        <div style="background:#fef3c7;color:#92400e;font-size:0.72rem;font-weight:700;
                    padding:3px 10px;border-radius:999px;">STEP 17</div>
        <span style="font-size:1.1rem;font-weight:700;color:#111827;">3か年数値計画</span>
        <span style="font-size:0.8rem;color:#9ca3af;">PL / BS / CF の3年間シミュレーション</span>
    </div>
    """, unsafe_allow_html=True)

    # ---- 前提条件の入力 ----
    with st.expander("📋 前提条件の設定", expanded=True):
        st.markdown("**ベースライン（直近実績）**")
        bc1, bc2, bc3, bc4 = st.columns(4)
        with bc1:
            base_rev_man = st.number_input("売上高（万円）", value=int(base_revenue / 10000), step=500, key="ty_rev")
        with bc2:
            base_cogs_rate = st.slider("売上原価率（%）", 0, 100, 65, key="ty_cogs") / 100
        with bc3:
            base_sga_rate = st.slider("販管費率（%）", 0, 50, 20, key="ty_sga") / 100
        with bc4:
            base_dep = st.number_input("減価償却費（万円/年）", value=200, step=50, key="ty_dep")

        st.markdown("**成長・改善前提（各年度）**")
        gc1, gc2, gc3 = st.columns(3)
        with gc1:
            st.caption("Year 1")
            y1_rev_g    = st.number_input("売上成長率（%）", value=5.0,  step=0.5, key="y1_g",   format="%.1f") / 100
            y1_cogs_imp = st.number_input("原価率改善（pp）", value=0.0, step=0.5, key="y1_co",  format="%.1f") / 100
            y1_capex    = st.number_input("設備投資（万円）", value=500,  step=100, key="y1_cap")
            y1_borr     = st.number_input("新規借入（万円）", value=0,    step=100, key="y1_bo")
            y1_repay    = st.number_input("借入返済（万円）", value=500,  step=100, key="y1_re")
        with gc2:
            st.caption("Year 2")
            y2_rev_g    = st.number_input("売上成長率（%）", value=8.0,  step=0.5, key="y2_g",   format="%.1f") / 100
            y2_cogs_imp = st.number_input("原価率改善（pp）", value=1.0, step=0.5, key="y2_co",  format="%.1f") / 100
            y2_capex    = st.number_input("設備投資（万円）", value=300,  step=100, key="y2_cap")
            y2_borr     = st.number_input("新規借入（万円）", value=0,    step=100, key="y2_bo")
            y2_repay    = st.number_input("借入返済（万円）", value=500,  step=100, key="y2_re")
        with gc3:
            st.caption("Year 3")
            y3_rev_g    = st.number_input("売上成長率（%）", value=10.0, step=0.5, key="y3_g",   format="%.1f") / 100
            y3_cogs_imp = st.number_input("原価率改善（pp）", value=1.5, step=0.5, key="y3_co",  format="%.1f") / 100
            y3_capex    = st.number_input("設備投資（万円）", value=200,  step=100, key="y3_cap")
            y3_borr     = st.number_input("新規借入（万円）", value=0,    step=100, key="y3_bo")
            y3_repay    = st.number_input("借入返済（万円）", value=500,  step=100, key="y3_re")

        base_equity_man  = st.number_input("純資産（万円、直近）", value=3000, step=200, key="ty_eq")
        base_debt_man    = st.number_input("有利子負債（万円、直近）", value=5000, step=200, key="ty_debt")
        base_assets_man  = st.number_input("総資産（万円、直近）", value=10000, step=500, key="ty_assets")

    # ---- 計算 ----
    def _pl(rev_g, cogs_imp, prev_rev, prev_eq):
        rev    = prev_rev * (1 + rev_g)
        cogs_r = max(0, base_cogs_rate - cogs_imp)
        cogs   = rev * cogs_r
        gross  = rev - cogs
        sga    = rev * base_sga_rate
        op_pf  = gross - sga
        ord_pf = op_pf * 0.95
        net_pf = ord_pf * 0.7   # 実効税率30%想定
        return dict(
            rev=rev, cogs=cogs, gross=gross, sga=sga,
            op_pf=op_pf, ord_pf=ord_pf, net_pf=net_pf,
        )

    base_rev_yen = base_rev_man * 10_000
    params = [
        (y1_rev_g, y1_cogs_imp, y1_capex * 10_000, y1_borr * 10_000, y1_repay * 10_000),
        (y2_rev_g, y2_cogs_imp, y2_capex * 10_000, y2_borr * 10_000, y2_repay * 10_000),
        (y3_rev_g, y3_cogs_imp, y3_capex * 10_000, y3_borr * 10_000, y3_repay * 10_000),
    ]

    rows, prev_rev, prev_eq, prev_debt, prev_assets = [], base_rev_yen, base_equity_man * 10_000, base_debt_man * 10_000, base_assets_man * 10_000
    for yr, (rg, ci, capex, borr, repay) in enumerate(params, 1):
        pl = _pl(rg, ci, prev_rev, prev_eq)
        dep = base_dep * 10_000
        op_cf   = pl["net_pf"] + dep
        inv_cf  = -capex
        fin_cf  = borr - repay
        net_cf  = op_cf + inv_cf + fin_cf
        new_equity = prev_eq + pl["net_pf"]
        new_debt   = prev_debt + borr - repay
        new_assets = prev_assets + pl["net_pf"] + dep - capex + borr - repay
        roa = pl["net_pf"] / new_assets * 100 if new_assets else 0
        eq_ratio = new_equity / new_assets * 100 if new_assets else 0
        op_margin = pl["op_pf"] / pl["rev"] * 100 if pl["rev"] else 0

        rows.append({
            "年度": f"Year {yr}",
            "売上高": pl["rev"],
            "売上原価": pl["cogs"],
            "売上総利益": pl["gross"],
            "販管費": pl["sga"],
            "営業利益": pl["op_pf"],
            "経常利益": pl["ord_pf"],
            "当期純利益": pl["net_pf"],
            "純資産": new_equity,
            "有利子負債": new_debt,
            "総資産": new_assets,
            "営業CF": op_cf,
            "投資CF": inv_cf,
            "財務CF": fin_cf,
            "期末現預金増減": net_cf,
            "ROA(%)": round(roa, 2),
            "自己資本比率(%)": round(eq_ratio, 2),
            "営業利益率(%)": round(op_margin, 2),
        })
        prev_rev, prev_eq, prev_debt, prev_assets = pl["rev"], new_equity, new_debt, new_assets

    # ---- 表示 ----
    # KPIカード
    st.markdown("#### KPIサマリー")
    k1, k2, k3, k4 = st.columns(4)
    final = rows[-1]
    k1.metric("3年後 売上高", f"{final['売上高']/10000:,.0f}万円",
              f"+{(final['売上高']/base_rev_yen - 1)*100:.1f}%" if base_rev_yen else None)
    k2.metric("3年後 営業利益率", f"{final['営業利益率(%)']:.1f}%",
              f"{final['営業利益率(%)'] - (base_op_profit/base_rev_yen*100 if base_rev_yen else 0):+.1f}pp")
    k3.metric("3年後 ROA", f"{final['ROA(%)']:.1f}%")
    k4.metric("3年後 自己資本比率", f"{final['自己資本比率(%)']:.1f}%")

    # PL テーブル
    st.markdown("#### 損益計算書（PL）3か年計画　（単位：万円）")
    pl_keys = ["年度", "売上高", "売上原価", "売上総利益", "販管費", "営業利益", "経常利益", "当期純利益"]
    pl_df = pd.DataFrame([{k: (f"{r[k]/10000:,.0f}" if isinstance(r[k], float) else r[k]) for k in pl_keys} for r in rows])
    st.dataframe(pl_df.set_index("年度"), use_container_width=True)

    # BS テーブル
    st.markdown("#### 貸借対照表（BS）3か年計画　（単位：万円）")
    bs_keys = ["年度", "総資産", "純資産", "有利子負債", "自己資本比率(%)"]
    bs_df = pd.DataFrame([{k: (f"{r[k]/10000:,.0f}" if k not in ("年度", "自己資本比率(%)") else (r[k] if k == "年度" else f"{r[k]:.1f}%")) for k in bs_keys} for r in rows])
    st.dataframe(bs_df.set_index("年度"), use_container_width=True)

    # CF テーブル
    st.markdown("#### キャッシュフロー（CF）3か年計画　（単位：万円）")
    cf_keys = ["年度", "営業CF", "投資CF", "財務CF", "期末現預金増減"]
    cf_df = pd.DataFrame([{k: (f"{r[k]/10000:,.0f}" if isinstance(r[k], float) else r[k]) for k in cf_keys} for r in rows])
    st.dataframe(cf_df.set_index("年度"), use_container_width=True)

    # 売上・営業利益のウォーターフォール的グラフ
    st.markdown("#### 売上高・営業利益 推移")
    years = ["現状"] + [r["年度"] for r in rows]
    revs  = [base_rev_yen] + [r["売上高"] for r in rows]
    profs = [base_op_profit] + [r["営業利益"] for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=years, y=[v / 10_000 for v in revs],
        name="売上高（万円）", marker_color="#6366f1", opacity=0.8,
    ))
    fig.add_trace(go.Scatter(
        x=years, y=[v / 10_000 for v in profs],
        name="営業利益（万円）", mode="lines+markers",
        line=dict(color="#10b981", width=3),
        marker=dict(size=10),
    ))
    fig.update_layout(
        height=350, barmode="group",
        yaxis_title="万円",
        legend=dict(orientation="h", y=1.1),
        font=dict(family="Inter, Noto Sans JP, sans-serif"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 保存
    st.divider()
    sc1, sc2 = st.columns([2, 1])
    with sc1:
        st.caption("計画を保存するとSTEP 17を完了としてマークします。")
    with sc2:
        if st.button("💾 3か年計画を保存 → STEP 17 完了",
                     type="primary", use_container_width=True, key="save_3yr"):
            if client_id:
                try:
                    from core.supabase_client import get_supabase_client
                    sb = get_supabase_client()
                    res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
                    notes = json.loads(res.data.get("notes") or "{}")
                    notes["three_year_plan"] = {
                        "rows": rows,
                        "saved_at": pd.Timestamp.now().isoformat(),
                    }
                    steps = notes.get("pipeline_steps", {})
                    steps["17"] = "done"
                    notes["pipeline_steps"] = steps
                    sb.table("clients").update({"notes": json.dumps(notes, ensure_ascii=False)}).eq("id", client_id).execute()
                    st.session_state[f"pipeline_{client_id}"] = steps
                    st.success("✅ 3か年計画を保存しました。STEP 17 完了！")
                except Exception as e:
                    st.error(f"保存エラー: {e}")
            else:
                st.warning("プロジェクトを選択してください。")


if __name__ == "__main__":
    app()
