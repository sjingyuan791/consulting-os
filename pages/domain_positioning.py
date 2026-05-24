"""
STEP 11 & 12: ドメイン設定 & ポジショニングマップ
事業ドメインの定義と競合とのポジショニングを可視化する。
"""
import json
import streamlit as st
import plotly.graph_objects as go
from core.auth import check_auth
from core.style_utils import load_custom_css

st.set_page_config(
    page_title="ドメイン・ポジショニング — Consulting OS",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_custom_css()


# ------------------------------------------------------------------ #
#  DB helpers
# ------------------------------------------------------------------ #
def _load_domain_data(client_id: str) -> dict:
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        return notes.get("domain_positioning", {})
    except Exception:
        return {}


def _save_domain_data(client_id: str, data: dict, mark_steps: list[int] = None):
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        notes["domain_positioning"] = data
        if mark_steps:
            steps = notes.get("pipeline_steps", {})
            for s in mark_steps:
                steps[str(s)] = "done"
            notes["pipeline_steps"] = steps
            cache_key = f"pipeline_{client_id}"
            if cache_key in st.session_state:
                st.session_state[cache_key] = steps
        sb.table("clients").update({"notes": json.dumps(notes, ensure_ascii=False)}).eq("id", client_id).execute()
    except Exception as e:
        st.error(f"保存エラー: {e}")


def _get_ai_domain_suggestion(client_id: str, company_name: str, industry: str, vision: str) -> str:
    """
    AIによるドメイン・ポジショニング提案を生成する。
    SWOT・真因・戦略仮説・財務データを自動注入する。
    """
    try:
        from openai import OpenAI
        from core.config import Config
        from core.project_context import ProjectContext

        # 上流の全コンテキストを集約（SWOT・真因・戦略仮説・財務・外部環境）
        ctx = ProjectContext.load(client_id)
        context_text = ctx.to_prompt_text(scope="strategy_only")

        ai = OpenAI(api_key=Config.OPENAI_API_KEY)

        system_prompt = f"""あなたは一流の経営コンサルタントです。
SWOT分析・真因分析・戦略仮説・財務データ・外部環境を踏まえた上で、
論理的整合性のある事業ドメインとポジショニングを提案してください。
{context_text}"""

        user_prompt = f"""以下の情報をもとに、事業ドメイン設定とポジショニング戦略を提案してください。

会社名: {company_name}
業種: {industry}
ビジョン: {vision or '未設定'}

**【注意】** 上記のプロジェクトコンテキスト（SWOT・真因・戦略仮説）と整合するドメイン設定を提案すること。

【出力形式】

**【ドメイン定義（誰に・何を・どのように）】**
- 顧客（誰に）:
- 提供価値（何を）:
- 提供方法（どのように）:

**【ドメイン文（一文）】**

**【競争優位の源泉】**
（SWOT・内部能力を根拠に記述）

**【推奨ポジショニング軸（2軸）】**
- X軸: （根拠付きで）
- Y軸: （根拠付きで）

**【競合との差別化ポイント】**
（競合データを引用して具体的に）

**【SWOT・戦略仮説との整合性チェック】**
（上流分析との論理的つながりを確認）"""

        response = ai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI提案の生成に失敗しました: {e}"


# ------------------------------------------------------------------ #
#  Positioning map
# ------------------------------------------------------------------ #
def _render_positioning_map(data: dict, company_name: str):
    """Plotlyでポジショニングマップを描画する。"""
    x_axis = data.get("x_axis_label", "価格（低←→高）")
    y_axis = data.get("y_axis_label", "品質（低↓↑高）")
    competitors = data.get("competitors", [])

    fig = go.Figure()

    # Quadrant backgrounds
    fig.add_shape(type="rect", x0=-10, y0=0, x1=0, y1=10,
                  fillcolor="rgba(239,246,255,0.5)", line_width=0)
    fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=10,
                  fillcolor="rgba(240,253,244,0.5)", line_width=0)
    fig.add_shape(type="rect", x0=-10, y0=-10, x1=0, y1=0,
                  fillcolor="rgba(255,251,235,0.5)", line_width=0)
    fig.add_shape(type="rect", x0=0, y0=-10, x1=10, y1=0,
                  fillcolor="rgba(255,241,242,0.5)", line_width=0)

    # Axes
    fig.add_shape(type="line", x0=-10, y0=0, x1=10, y1=0,
                  line=dict(color="#e5e7eb", width=1))
    fig.add_shape(type="line", x0=0, y0=-10, x1=0, y1=10,
                  line=dict(color="#e5e7eb", width=1))

    # Plot self (company)
    self_x = data.get("self_x", 3)
    self_y = data.get("self_y", 4)
    fig.add_trace(go.Scatter(
        x=[self_x], y=[self_y],
        mode="markers+text",
        marker=dict(size=18, color="#4f46e5", symbol="star"),
        text=[f"★ {company_name}"],
        textposition="top center",
        name=company_name,
        textfont=dict(size=12, color="#4f46e5"),
    ))

    # Plot competitors
    for comp in competitors:
        fig.add_trace(go.Scatter(
            x=[comp.get("x", 0)], y=[comp.get("y", 0)],
            mode="markers+text",
            marker=dict(size=14, color="#ef4444"),
            text=[comp.get("name", "競合")],
            textposition="top center",
            name=comp.get("name", "競合"),
            textfont=dict(size=10, color="#374151"),
        ))

    fig.update_layout(
        xaxis=dict(range=[-10, 10], title=x_axis, zeroline=False,
                   tickvals=[-10, -5, 0, 5, 10], gridcolor="#f3f4f6"),
        yaxis=dict(range=[-10, 10], title=y_axis, zeroline=False,
                   tickvals=[-10, -5, 0, 5, 10], gridcolor="#f3f4f6"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=500,
        showlegend=True,
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.9)"),
        font=dict(family="Inter, Noto Sans JP, sans-serif"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------------ #
#  Main
# ------------------------------------------------------------------ #
def main():
    from core.sidebar import render_sidebar
    render_sidebar()

    if not check_auth():
        st.warning("ログインが必要です。")
        return

    client_id = st.session_state.get("client_id")
    client_name = st.session_state.get("client_name", "プロジェクト")

    if not client_id:
        st.warning("プロジェクトが選択されていません。")
        if st.button("← プロジェクト一覧へ"):
            st.switch_page("app.py")
        return

    # Step badge
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
        <div style="background:#d1fae5;color:#065f46;font-size:0.72rem;font-weight:700;padding:3px 10px;border-radius:999px;letter-spacing:0.06em;">
            STEP 11 & 12
        </div>
        <div style="font-size:0.8rem;color:#9ca3af;">戦略策定フェーズ</div>
    </div>
    """, unsafe_allow_html=True)

    st.title("🗺️ ドメイン設定 & ポジショニングマップ")
    st.markdown("事業ドメインを明確に定義し、競合との差異化ポジションを可視化します。")

    data = _load_domain_data(client_id)

    # Get industry & vision for AI
    industry, vision = "", ""
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res_c = sb.table("clients").select("industry, notes").eq("id", client_id).single().execute()
        if res_c.data:
            industry = res_c.data.get("industry", "")
            notes_json = json.loads(res_c.data.get("notes") or "{}")
            vision = notes_json.get("vision_mission", {}).get("vision", "")
    except Exception:
        pass

    tab_domain, tab_positioning, tab_ai = st.tabs(["🗺️ ドメイン設定", "📍 ポジショニングマップ", "🤖 AI提案"])

    # ---- Tab 1: Domain ----
    with tab_domain:
        st.subheader("事業ドメイン定義")
        st.markdown("「誰に・何を・どのように」の3軸でドメインを定義します。")

        with st.form("domain_form"):
            c1, c2 = st.columns(2)
            with c1:
                customer = st.text_area(
                    "👥 顧客（誰に）",
                    value=data.get("customer", ""),
                    height=80,
                    placeholder="例：中小製造業（売上10〜100億円）の経営者・製造責任者",
                )
                value_prop = st.text_area(
                    "💎 提供価値（何を）",
                    value=data.get("value_prop", ""),
                    height=80,
                    placeholder="例：現場改善ノウハウと最新デジタル技術を組み合わせたコスト削減・品質向上ソリューション",
                )
            with c2:
                method = st.text_area(
                    "⚙️ 提供方法（どのように）",
                    value=data.get("method", ""),
                    height=80,
                    placeholder="例：専任コンサルタントによる伴走支援とSaaSツールの組み合わせ",
                )
                domain_statement = st.text_area(
                    "📝 ドメイン文（一文で）",
                    value=data.get("domain_statement", ""),
                    height=80,
                    placeholder="例：製造業の経営者に対して、現場改善×DXで競争力を高めるコンサルティングを提供する",
                )

            competitive_source = st.text_area(
                "🏆 競争優位の源泉",
                value=data.get("competitive_source", ""),
                height=80,
                placeholder="例：20年の製造業特化ノウハウ × AIツール × 低コスト地域拠点網",
            )
            scope_note = st.text_area(
                "📌 スコープ（やること・やらないこと）",
                value=data.get("scope_note", ""),
                height=80,
                placeholder="やること: ...\nやらないこと: ...",
            )

            d1, _ = st.columns([1, 3])
            with d1:
                if st.form_submit_button("💾 保存する", type="primary", use_container_width=True):
                    data.update({
                        "customer": customer,
                        "value_prop": value_prop,
                        "method": method,
                        "domain_statement": domain_statement,
                        "competitive_source": competitive_source,
                        "scope_note": scope_note,
                    })
                    _save_domain_data(client_id, data, mark_steps=[11])
                    st.success("✅ ドメイン設定を保存しました (STEP 11 完了)。")

    # ---- Tab 2: Positioning map ----
    with tab_positioning:
        st.subheader("ポジショニングマップ")
        st.markdown("競合との差異化ポジションを2軸のマップで可視化します。")

        with st.expander("軸の設定", expanded=True):
            pc1, pc2 = st.columns(2)
            with pc1:
                x_label = st.text_input("X軸ラベル", value=data.get("x_axis_label", "価格（低←→高）"))
            with pc2:
                y_label = st.text_input("Y軸ラベル", value=data.get("y_axis_label", "品質（低↓↑高）"))

        with st.expander("自社のポジション", expanded=True):
            sc1, sc2 = st.columns(2)
            with sc1:
                self_x = st.slider("X軸（自社）", -10, 10, int(data.get("self_x", 3)), key="self_x_sl")
            with sc2:
                self_y = st.slider("Y軸（自社）", -10, 10, int(data.get("self_y", 4)), key="self_y_sl")

        with st.expander("競合の追加・編集"):
            st.markdown("競合企業名とポジションを入力してください（最大8社）。")
            competitors = data.get("competitors", [])

            # Add new competitor
            nc1, nc2, nc3, nc4 = st.columns([2, 1, 1, 1])
            with nc1:
                new_comp_name = st.text_input("競合名", key="new_comp_name", placeholder="A社")
            with nc2:
                new_comp_x = st.number_input("X", -10, 10, 0, key="new_comp_x")
            with nc3:
                new_comp_y = st.number_input("Y", -10, 10, 0, key="new_comp_y")
            with nc4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("追加", key="add_comp"):
                    if new_comp_name:
                        competitors.append({"name": new_comp_name, "x": new_comp_x, "y": new_comp_y})
                        data["competitors"] = competitors
                        _save_domain_data(client_id, data)
                        st.rerun()

            if competitors:
                st.markdown("**登録済み競合:**")
                for i, comp in enumerate(competitors):
                    cc1, cc2, cc3, cc4 = st.columns([2, 1, 1, 1])
                    with cc1:
                        st.text(comp["name"])
                    with cc2:
                        st.text(f"X: {comp['x']}")
                    with cc3:
                        st.text(f"Y: {comp['y']}")
                    with cc4:
                        if st.button("削除", key=f"del_comp_{i}"):
                            competitors.pop(i)
                            data["competitors"] = competitors
                            _save_domain_data(client_id, data)
                            st.rerun()

        # Save axis and self position
        if st.button("📍 マップを更新・保存", type="primary", key="save_map"):
            data.update({
                "x_axis_label": x_label,
                "y_axis_label": y_label,
                "self_x": self_x,
                "self_y": self_y,
            })
            _save_domain_data(client_id, data, mark_steps=[12])
            st.success("✅ ポジショニングマップを保存しました (STEP 12 完了)。")
            st.rerun()

        # Draw map
        st.markdown("#### ポジショニングマップ")
        map_data = dict(data)
        map_data["x_axis_label"] = x_label
        map_data["y_axis_label"] = y_label
        map_data["self_x"] = self_x
        map_data["self_y"] = self_y
        _render_positioning_map(map_data, client_name)

        # Legend tips
        st.markdown("""
        <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:1rem;font-size:0.82rem;color:#6b7280;">
            ★ = 自社ポジション　　● = 競合ポジション<br>
            X軸・Y軸は自社の差別化戦略に応じて自由に設定できます。
        </div>
        """, unsafe_allow_html=True)

    # ---- Tab 3: AI suggestion ----
    with tab_ai:
        st.subheader("🤖 AI によるドメイン・ポジショニング提案")
        st.info(f"**プロジェクト:** {client_name}　|　**業種:** {industry or '未設定'}　|　**ビジョン:** {vision[:40] + '...' if len(vision) > 40 else vision or '未設定'}")

        if st.button("🤖 AIに提案してもらう", type="primary", key="gen_domain"):
            with st.spinner("AI が分析・提案中..."):
                suggestion = _get_ai_domain_suggestion(client_id, client_name, industry, vision)
            st.markdown("---")
            st.markdown(suggestion)
            st.info("💡 上記を参考に「ドメイン設定」「ポジショニングマップ」タブで入力してください。")

    st.divider()
    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        st.page_link("pages/14_phase5_strategy.py", label="← STEP 10 全社戦略仮説")
    with nav2:
        st.page_link("pages/01_project_workspace.py", label="🏠 ワークスペース")
    with nav3:
        st.page_link("pages/15_phase6_tactical.py", label="次へ: STEP 13 機能別戦略 →")


main()
