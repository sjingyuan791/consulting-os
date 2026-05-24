"""
STEP 2-3: 外部環境調査
PEST分析・5フォース・競合分析を構造化入力し、AIが業界特化の調査内容を補完する。
保存データはProjectContextを通じて下流（SWOT・戦略仮説）に自動連携される。
"""
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.auth import check_auth
from core.style_utils import load_custom_css

st.set_page_config(
    page_title="外部環境調査 — Consulting OS",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_custom_css()

# ------------------------------------------------------------------ #
#  データ構造定義
# ------------------------------------------------------------------ #

_PEST_CATEGORIES = {
    "political":     {"label": "Political（政治）",     "icon": "🏛️", "color": "#dbeafe"},
    "economic":      {"label": "Economic（経済）",       "icon": "💹", "color": "#dcfce7"},
    "social":        {"label": "Social（社会）",         "icon": "👥", "color": "#fef3c7"},
    "technological": {"label": "Technology（技術）",     "icon": "💡", "color": "#f3e8ff"},
    "environmental": {"label": "Environmental（環境）",  "icon": "🌱", "color": "#d1fae5"},
    "legal":         {"label": "Legal（法規制）",        "icon": "⚖️", "color": "#fee2e2"},
}

_FORCES = {
    "rivalry":       {"label": "既存業者間の競争",     "icon": "⚔️"},
    "new_entrants":  {"label": "新規参入の脅威",       "icon": "🚪"},
    "substitutes":   {"label": "代替品・代替サービスの脅威", "icon": "🔄"},
    "supplier":      {"label": "売り手（サプライヤー）の交渉力", "icon": "🏭"},
    "buyer":         {"label": "買い手（顧客）の交渉力", "icon": "🛒"},
}

_EMPTY_PEST_ROW = {"事実・観察事項": "", "影響度": "中", "機会/脅威": "機会", "コメント・根拠": ""}

# ------------------------------------------------------------------ #
#  DB helpers
# ------------------------------------------------------------------ #

def _load_ext(client_id: str) -> dict:
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        return notes.get("external_environment", {})
    except Exception:
        return {}


def _load_ext_analysis(client_id: str) -> dict:
    """external_env キーから戦略的分析結果を読み込む。"""
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        return notes.get("external_env", {})
    except Exception:
        return {}


def _save_ext(client_id: str, data: dict, complete_steps: list[int] = None, ext_analysis: dict = None):
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        notes["external_environment"] = data
        if ext_analysis is not None:
            notes["external_env"] = ext_analysis
        if complete_steps:
            steps = notes.get("pipeline_steps", {})
            for s in complete_steps:
                steps[str(s)] = "done"
            notes["pipeline_steps"] = steps
            for s in complete_steps:
                cache_key = f"pipeline_{client_id}"
                if cache_key in st.session_state:
                    st.session_state[cache_key][str(s)] = "done"
        sb.table("clients").update({"notes": json.dumps(notes, ensure_ascii=False)}).eq("id", client_id).execute()
    except Exception as e:
        st.error(f"保存エラー: {e}")


# ------------------------------------------------------------------ #
#  AI 補完
# ------------------------------------------------------------------ #

def _ai_generate_pest(company_name: str, industry: str, client_id: str) -> dict:
    from openai import OpenAI
    from core.config import Config
    from core.project_context import ProjectContext

    ctx = ProjectContext.load(client_id)
    fin_ctx = ctx.to_prompt_text(scope="financial_only")

    ai = OpenAI(api_key=Config.OPENAI_API_KEY)

    system = f"""あなたは業界調査の専門コンサルタントです。
具体的な数値・事実・直近のトレンドに基づいてPEST分析を作成してください。
一般論ではなく、業種特有の具体的な事象を5〜7点ずつ挙げてください。
{fin_ctx}"""

    user = f"""【会社名】{company_name}  【業種】{industry}

PEST分析（PESTEL含む）を作成してください。
各カテゴリに3〜5件の項目を含め、影響度と機会/脅威を判定してください。

JSON形式で出力（他テキスト不要）:
{{
  "political": [
    {{"fact": "具体的事実（数値・法律名など）", "impact": "高|中|低", "type": "機会|脅威", "comment": "この会社への具体的影響"}}
  ],
  "economic": [...],
  "social": [...],
  "technological": [...],
  "environmental": [...],
  "legal": [...],
  "market_overview": {{
    "size": "市場規模（億円等）",
    "growth_rate": "成長率（%）",
    "key_trends": ["トレンド1", "トレンド2", "トレンド3"],
    "summary": "100字程度の業界概況"
  }}
}}"""

    resp = ai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


def _ai_generate_competitors(company_name: str, industry: str, client_id: str) -> list:
    from openai import OpenAI
    from core.config import Config
    from core.project_context import ProjectContext

    ctx = ProjectContext.load(client_id)
    ext_ctx = ctx.to_prompt_text(scope="financial_only")

    ai = OpenAI(api_key=Config.OPENAI_API_KEY)
    resp = ai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"業界調査の専門コンサルタント。{ext_ctx}"},
            {"role": "user", "content": f"""
{industry}業界（{company_name}の競合）の主要プレイヤーを5社挙げてください。

JSON配列で出力:
[
  {{
    "name": "会社名",
    "share": "推定シェア（%）",
    "strengths": "主な強み（1〜2文）",
    "weaknesses": "主な弱み（1〜2文）",
    "strategy": "競争戦略（1文）",
    "threat_level": "高|中|低"
  }}
]"""},
        ],
        max_tokens=1000,
        response_format={"type": "json_object"},
    )
    raw = json.loads(resp.choices[0].message.content)
    # モデルがリスト or {"competitors": [...]} で返す場合に対応
    if isinstance(raw, list):
        return raw
    return raw.get("competitors", raw.get("items", []))


def _ai_generate_five_forces(company_name: str, industry: str, client_id: str) -> dict:
    from openai import OpenAI
    from core.config import Config

    ai = OpenAI(api_key=Config.OPENAI_API_KEY)
    resp = ai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "業界構造分析の専門コンサルタント。"},
            {"role": "user", "content": f"""
{industry}業界（{company_name}）の5フォース分析を作成してください。

JSON形式:
{{
  "rivalry":      {{"score": 1〜5, "summary": "1〜2文の根拠付き説明"}},
  "new_entrants": {{"score": 1〜5, "summary": "..."}},
  "substitutes":  {{"score": 1〜5, "summary": "..."}},
  "supplier":     {{"score": 1〜5, "summary": "..."}},
  "buyer":        {{"score": 1〜5, "summary": "..."}},
  "overall_attractiveness": "高|中|低",
  "overall_comment": "業界の総合的な収益性・魅力度についての2〜3文コメント"
}}
スコアは1=弱い脅威/競争力、5=強い脅威/競争力。"""},
        ],
        max_tokens=800,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


# ------------------------------------------------------------------ #
#  UI helpers
# ------------------------------------------------------------------ #

def _five_forces_radar(forces_data: dict):
    """5フォースのレーダーチャートを描画する。"""
    labels = [v["label"] for v in _FORCES.values()]
    scores = [forces_data.get(k, {}).get("score", 3) for k in _FORCES]
    scores.append(scores[0])  # close the polygon
    labels.append(labels[0])

    fig = go.Figure(go.Scatterpolar(
        r=scores,
        theta=labels,
        fill="toself",
        fillcolor="rgba(99,102,241,0.15)",
        line=dict(color="#6366f1", width=2),
        marker=dict(size=6, color="#6366f1"),
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 5], tickfont=dict(size=9)),
            angularaxis=dict(tickfont=dict(size=10)),
        ),
        showlegend=False,
        height=380,
        margin=dict(l=60, r=60, t=40, b=40),
        paper_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True)


def _pest_editor(category: str, meta: dict, existing_rows: list) -> list:
    """PEST の1カテゴリを st.data_editor で編集する。"""
    st.markdown(
        f'<div style="background:{meta["color"]};border-radius:8px;padding:8px 14px;'
        f'font-size:0.82rem;font-weight:700;margin-bottom:6px;">'
        f'{meta["icon"]} {meta["label"]}</div>',
        unsafe_allow_html=True,
    )
    df = pd.DataFrame(
        existing_rows if existing_rows else [dict(_EMPTY_PEST_ROW)],
        columns=list(_EMPTY_PEST_ROW.keys()),
    )
    edited = st.data_editor(
        df,
        key=f"pest_{category}",
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "事実・観察事項": st.column_config.TextColumn("事実・観察事項", width="large"),
            "影響度": st.column_config.SelectboxColumn("影響度", options=["高", "中", "低"], width="small"),
            "機会/脅威": st.column_config.SelectboxColumn("機会/脅威", options=["機会", "脅威", "両面"], width="small"),
            "コメント・根拠": st.column_config.TextColumn("コメント・根拠", width="large"),
        },
        hide_index=True,
    )
    return edited.to_dict("records")


def _ai_rows_to_df_rows(ai_items: list) -> list:
    """AI出力をdata_editor形式に変換する。"""
    rows = []
    for item in ai_items:
        rows.append({
            "事実・観察事項": item.get("fact", ""),
            "影響度": item.get("impact", "中"),
            "機会/脅威": item.get("type", "機会"),
            "コメント・根拠": item.get("comment", ""),
        })
    return rows


def _impact_badge(level: str) -> str:
    colors = {"高": ("#fee2e2", "#b91c1c"), "中": ("#fef3c7", "#b45309"), "低": ("#f3f4f6", "#6b7280")}
    bg, fg = colors.get(level, colors["中"])
    return f'<span style="background:{bg};color:{fg};font-size:0.68rem;font-weight:700;padding:1px 7px;border-radius:999px;">{level}</span>'


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

    # 業種取得
    industry = ""
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        r = sb.table("clients").select("industry").eq("id", client_id).single().execute()
        industry = r.data.get("industry", "") if r.data else ""
    except Exception:
        pass

    # STEP バッジ
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
        <div style="background:#dbeafe;color:#1d4ed8;font-size:0.72rem;font-weight:700;
                    padding:3px 10px;border-radius:999px;">STEP 2-3</div>
        <div style="font-size:0.8rem;color:#9ca3af;">データ収集フェーズ</div>
    </div>
    """, unsafe_allow_html=True)

    st.title("🌍 外部環境調査")
    st.markdown("PEST分析・5フォース・競合分析を構造化入力します。AIが業界特化の内容を自動補完します。")

    # 既存データ読み込み
    ext = _load_ext(client_id)

    # AI生成結果をセッションにキャッシュ
    if "ext_ai_pest" not in st.session_state:
        st.session_state.ext_ai_pest = {}
    if "ext_ai_forces" not in st.session_state:
        st.session_state.ext_ai_forces = {}
    if "ext_ai_competitors" not in st.session_state:
        st.session_state.ext_ai_competitors = []
    if "ext_ai_analysis" not in st.session_state:
        st.session_state.ext_ai_analysis = {}

    # 保存済み戦略的分析を読み込む
    saved_analysis = _load_ext_analysis(client_id)

    tab_overview, tab_pest, tab_impact, tab_forces, tab_competitors, tab_essence, tab_save = st.tabs([
        "📊 市場概況", "🔬 PEST分析", "📈 事業影響・マクロ総括",
        "🏭 業界収益・5フォース", "🏢 競合分析", "🎯 外部環境の本質", "💾 保存・確認"
    ])

    # ============================================================
    # Tab 1: 市場概況
    # ============================================================
    with tab_overview:
        st.subheader("市場概況・マクロ環境サマリー")

        ai_mkt = st.session_state.ext_ai_pest.get("market_overview", {})
        saved_mkt = ext.get("market_overview", {})
        mkt = ai_mkt if ai_mkt else saved_mkt

        col_gen, col_gen2, _ = st.columns([1, 1, 2])
        with col_gen:
            if st.button("🤖 AI で市場概況を生成", type="primary", key="gen_overview"):
                with st.spinner("市場調査中..."):
                    try:
                        result = _ai_generate_pest(client_name, industry, client_id)
                        st.session_state.ext_ai_pest = result
                        st.success("生成完了。各タブで内容を確認・編集してください。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成エラー: {e}")
        with col_gen2:
            if st.button("🔍 外部環境を戦略的に分析", key="gen_strategic_analysis"):
                pest_w = st.session_state.get("ext_pest_working", ext.get("pest", {}))
                forces_w = st.session_state.get("ext_forces_working", ext.get("five_forces", {}))
                mkt_w = st.session_state.get("ext_mkt_working", ext.get("market_overview", {}))
                with st.spinner("戦略的外部環境分析を生成中..."):
                    try:
                        from core.pipeline.external_env_engine import run_external_env_analysis
                        result = run_external_env_analysis({
                            "company_info": {"name": client_name, "industry": industry},
                            "market_overview": mkt_w,
                            "pest": pest_w,
                            "five_forces": forces_w,
                        })
                        st.session_state.ext_ai_analysis = result.model_dump()
                        st.success("分析完了。「事業影響・マクロ総括」「業界収益・5フォース」「外部環境の本質」タブで確認できます。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"分析エラー: {e}")

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            mkt_size = st.text_input("市場規模", value=mkt.get("size", ""), placeholder="例: 約1.2兆円（2024年）")
            mkt_growth = st.text_input("成長率（年率）", value=mkt.get("growth_rate", ""), placeholder="例: +3.5%")
        with c2:
            mkt_summary = st.text_area(
                "業界概況サマリー",
                value=mkt.get("summary", ""),
                height=100,
                placeholder="業界全体の状況を2〜3文で記述",
            )

        st.markdown("**主要トレンド（1行1項目）**")
        trends_default = "\n".join(mkt.get("key_trends", []))
        trends_text = st.text_area("主要トレンド", value=trends_default, height=100, label_visibility="collapsed")
        trends = [t.strip() for t in trends_text.splitlines() if t.strip()]

        # セッションに市場概況を保持
        st.session_state["ext_mkt_working"] = {
            "size": mkt_size,
            "growth_rate": mkt_growth,
            "summary": mkt_summary,
            "key_trends": trends,
        }

    # ============================================================
    # Tab 2: PEST分析
    # ============================================================
    with tab_pest:
        st.subheader("PEST(EL)分析")
        st.caption("各カテゴリの項目を入力または編集してください。行を追加・削除できます。")

        if not st.session_state.ext_ai_pest and not ext.get("pest"):
            st.info("「市場概況」タブの「AI で市場概況を生成」ボタンで、全カテゴリを一括生成できます。")

        pest_results = {}
        # 2列レイアウトで6カテゴリ
        cats = list(_PEST_CATEGORIES.items())
        for i in range(0, len(cats), 2):
            c1, c2 = st.columns(2, gap="large")
            for col, (cat_key, meta) in zip([c1, c2], cats[i:i+2]):
                with col:
                    # AI生成分 or 保存済みデータをdata_editor形式に変換
                    ai_rows = _ai_rows_to_df_rows(st.session_state.ext_ai_pest.get(cat_key, []))
                    saved_rows = ext.get("pest", {}).get(cat_key, [])
                    init_rows = ai_rows if ai_rows else saved_rows
                    pest_results[cat_key] = _pest_editor(cat_key, meta, init_rows)

        st.session_state["ext_pest_working"] = pest_results

    # ============================================================
    # Tab 3: 事業影響・マクロ総括
    # ============================================================
    with tab_impact:
        st.subheader("事業影響分析・マクロ総括")
        st.caption("PEST分析と5フォースから導出された戦略的外部環境分析です。「市場概況」タブの「外部環境を戦略的に分析」ボタンで生成してください。")

        analysis_src = st.session_state.ext_ai_analysis if st.session_state.ext_ai_analysis else saved_analysis

        if not analysis_src:
            st.info("「市場概況」タブの「🔍 外部環境を戦略的に分析」ボタンで分析を生成してください。PEST分析・5フォースの入力後に実行することを推奨します。")
        else:
            # 事業影響
            st.markdown("### 📌 事業影響分析")
            impact_items = analysis_src.get("business_impact", [])
            if impact_items:
                direction_icon = {"positive": "🟢", "negative": "🔴", "mixed": "🟡"}
                magnitude_color = {"high": "#fee2e2", "medium": "#fef3c7", "low": "#f3f4f6"}
                horizon_ja = {"short_term": "短期", "medium_term": "中期", "long_term": "長期"}
                for item in impact_items:
                    direction = item.get("direction", "mixed")
                    magnitude = item.get("magnitude", "medium")
                    horizon = item.get("time_horizon", "medium_term")
                    bg = magnitude_color.get(magnitude, "#f9fafb")
                    evidence_html = (
                        f'<div style="font-size:0.75rem;color:#6b7280;margin-top:4px;">根拠: {item.get("evidence","")}</div>'
                        if item.get("evidence") else ""
                    )
                    st.markdown(
                        f'<div style="background:{bg};border-radius:8px;padding:10px 14px;margin-bottom:8px;">'
                        f'<div style="font-size:0.78rem;font-weight:700;color:#374151;margin-bottom:4px;">'
                        f'{direction_icon.get(direction,"🟡")} {item.get("axis","")} '
                        f'<span style="font-weight:400;color:#6b7280;">| 影響度:{magnitude} | {horizon_ja.get(horizon,"中期")}</span></div>'
                        f'<div style="font-size:0.85rem;color:#1f2937;">{item.get("description","")}</div>'
                        f'{evidence_html}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("---")
            # マクロ総括
            st.markdown("### 🌐 マクロ総括")
            macro = analysis_src.get("macro_summary", {})
            if macro:
                col_tw, col_hw = st.columns(2)
                with col_tw:
                    st.markdown("**追い風要因（Tailwinds）**")
                    for tw in macro.get("tailwinds", []):
                        st.markdown(f"- ✅ {tw}")
                with col_hw:
                    st.markdown("**向かい風要因（Headwinds）**")
                    for hw in macro.get("headwinds", []):
                        st.markdown(f"- ⚠️ {hw}")

                st.markdown("**価格設定構造**")
                st.markdown(macro.get("price_setting_structure", ""))

                irreversibles = macro.get("irreversible_conditions", [])
                if irreversibles:
                    st.markdown("**不可逆的変化（構造的シフト）**")
                    for ir in irreversibles:
                        st.markdown(f"- 🔒 {ir}")

    # ============================================================
    # Tab 4: 業界収益・5フォース（拡張版）
    # ============================================================
    with tab_forces:
        st.subheader("業界収益構造・5フォース分析")

        col_gen5, _ = st.columns([1, 3])
        with col_gen5:
            if st.button("🤖 AI で5フォースを生成", type="primary", key="gen_forces"):
                with st.spinner("業界構造を分析中..."):
                    try:
                        result = _ai_generate_five_forces(client_name, industry, client_id)
                        st.session_state.ext_ai_forces = result
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成エラー: {e}")

        st.markdown("---")

        ai_f = st.session_state.ext_ai_forces
        saved_f = ext.get("five_forces", {})
        forces_src = ai_f if ai_f else saved_f

        # 業界収益構造（戦略的分析から）
        analysis_src2 = st.session_state.ext_ai_analysis if st.session_state.ext_ai_analysis else saved_analysis
        if analysis_src2.get("industry_profit_structure"):
            prof = analysis_src2["industry_profit_structure"]
            with st.expander("📊 業界収益構造分析", expanded=True):
                p1, p2 = st.columns(2)
                with p1:
                    st.markdown("**収益モデル**")
                    st.markdown(prof.get("revenue_model", "—"))
                    st.markdown("**コスト構造**")
                    st.markdown(prof.get("cost_structure_summary", "—"))
                with p2:
                    st.markdown("**収益性ベンチマーク**")
                    st.markdown(prof.get("margin_benchmarks", "—"))
                    st.markdown("**バリューチェーンのボトルネック**")
                    st.markdown(prof.get("value_chain_bottleneck", "—"))
                drivers = prof.get("key_profit_drivers", [])
                if drivers:
                    st.markdown("**利益ドライバー**")
                    imp_color = {"high": "#fee2e2", "medium": "#fef3c7", "low": "#f3f4f6"}
                    for d in drivers:
                        bg = imp_color.get(d.get("importance", "medium"), "#f9fafb")
                        st.markdown(
                            f'<div style="background:{bg};border-radius:6px;padding:6px 12px;margin-bottom:4px;">'
                            f'<b>{d.get("driver","")}</b> — {d.get("description","")}</div>',
                            unsafe_allow_html=True,
                        )
                if prof.get("disruption_risk"):
                    st.warning(f"⚡ 破壊リスク: {prof['disruption_risk']}")

        st.markdown("---")
        st.markdown("### Porter's Five Forces")

        # 全体評価
        if forces_src.get("overall_comment"):
            overall_color = {"高": "#dcfce7", "中": "#fef3c7", "低": "#fee2e2"}.get(
                forces_src.get("overall_attractiveness", "中"), "#f9fafb"
            )
            st.markdown(
                f'<div style="background:{overall_color};border-radius:10px;padding:12px 16px;margin-bottom:1rem;">'
                f'<b>業界魅力度: {forces_src.get("overall_attractiveness","—")}</b><br>'
                f'{forces_src.get("overall_comment","")}</div>',
                unsafe_allow_html=True,
            )

        # 戦略的示唆（enhanced_five_forces から）
        if analysis_src2.get("enhanced_five_forces", {}).get("structural_insight"):
            st.info(f"🎯 構造的示唆: {analysis_src2['enhanced_five_forces']['structural_insight']}")

        chart_col, edit_col = st.columns([1, 2])
        with chart_col:
            _five_forces_radar(forces_src)

        forces_working = {}
        with edit_col:
            for key, meta in _FORCES.items():
                src = forces_src.get(key, {})
                # 戦略的分析の拡張データ
                enhanced_src = analysis_src2.get("enhanced_five_forces", {}).get(key, {})
                with st.container():
                    st.markdown(f"**{meta['icon']} {meta['label']}**")
                    fc1, fc2 = st.columns([1, 3])
                    with fc1:
                        score = st.slider(
                            "強度", 1, 5,
                            int(src.get("score", 3)),
                            key=f"force_{key}_score",
                            label_visibility="collapsed",
                        )
                    with fc2:
                        note = st.text_input(
                            "根拠・コメント",
                            value=src.get("summary", ""),
                            key=f"force_{key}_note",
                            placeholder="具体的な根拠・事実を入力",
                            label_visibility="collapsed",
                        )
                    forces_working[key] = {"score": score, "summary": note}
                    if enhanced_src.get("strategic_implication"):
                        st.caption(f"→ 戦略含意: {enhanced_src['strategic_implication']}")
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        forces_working["overall_attractiveness"] = forces_src.get("overall_attractiveness", "中")
        forces_working["overall_comment"] = forces_src.get("overall_comment", "")
        st.session_state["ext_forces_working"] = forces_working

    # ============================================================
    # Tab 4: 競合分析
    # ============================================================
    with tab_competitors:
        st.subheader("主要競合分析")

        col_genC, _ = st.columns([1, 3])
        with col_genC:
            if st.button("🤖 AI で競合を生成", type="primary", key="gen_comp"):
                with st.spinner("競合情報を収集中..."):
                    try:
                        result = _ai_generate_competitors(client_name, industry, client_id)
                        st.session_state.ext_ai_competitors = result
                        st.rerun()
                    except Exception as e:
                        st.error(f"生成エラー: {e}")

        st.markdown("---")

        ai_comps = st.session_state.ext_ai_competitors
        saved_comps = ext.get("competitors", [])
        init_comps = ai_comps if ai_comps else saved_comps

        comp_df = pd.DataFrame(
            init_comps if init_comps else [
                {"name": "", "share": "", "strengths": "", "weaknesses": "", "strategy": "", "threat_level": "中"}
            ],
        )
        # 必要なカラムが揃っているか保証
        for col in ["name", "share", "strengths", "weaknesses", "strategy", "threat_level"]:
            if col not in comp_df.columns:
                comp_df[col] = ""

        edited_comps = st.data_editor(
            comp_df[["name", "share", "strengths", "weaknesses", "strategy", "threat_level"]],
            key="comp_editor",
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "name":         st.column_config.TextColumn("会社名", width="medium"),
                "share":        st.column_config.TextColumn("推定シェア", width="small"),
                "strengths":    st.column_config.TextColumn("強み", width="large"),
                "weaknesses":   st.column_config.TextColumn("弱み", width="large"),
                "strategy":     st.column_config.TextColumn("競争戦略", width="large"),
                "threat_level": st.column_config.SelectboxColumn("脅威度", options=["高", "中", "低"], width="small"),
            },
            hide_index=True,
        )
        st.session_state["ext_comps_working"] = edited_comps.to_dict("records")

        # 脅威度サマリー
        if not edited_comps.empty:
            high_threat = edited_comps[edited_comps["threat_level"] == "高"]["name"].tolist()
            if high_threat:
                st.warning(f"⚠️ 脅威度「高」の競合: {', '.join(str(n) for n in high_threat if n)}")

    # ============================================================
    # Tab 6: 外部環境の本質
    # ============================================================
    with tab_essence:
        st.subheader("外部環境の本質")
        st.caption("すべての外部環境分析を1文に凝縮した「経営判断の核心」です。")

        analysis_essence = st.session_state.ext_ai_analysis if st.session_state.ext_ai_analysis else saved_analysis
        essence = ""
        if analysis_essence:
            essence = analysis_essence.get("macro_summary", {}).get("essence_of_environment", "")

        if essence:
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#ede9fe,#dbeafe);'
                f'border-left:5px solid #6366f1;border-radius:12px;'
                f'padding:28px 32px;margin:16px 0;font-size:1.25rem;'
                f'font-weight:700;color:#1e1b4b;line-height:1.6;">'
                f'"{essence}"'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.markdown("---")

            # 支持する根拠をサマリー表示
            macro_e = analysis_essence.get("macro_summary", {})
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                st.markdown("**この本質を支持する追い風**")
                for tw in macro_e.get("tailwinds", [])[:3]:
                    st.markdown(f"✅ {tw}")
            with col_e2:
                st.markdown("**この本質を支持する向かい風**")
                for hw in macro_e.get("headwinds", [])[:3]:
                    st.markdown(f"⚠️ {hw}")

            irr = macro_e.get("irreversible_conditions", [])
            if irr:
                st.markdown("**不可逆的条件（変えられない前提）**")
                for ir in irr:
                    st.markdown(f"🔒 {ir}")

            eff = analysis_essence.get("enhanced_five_forces", {})
            if eff.get("structural_insight"):
                st.markdown("**業界構造から見た示唆**")
                st.info(eff["structural_insight"])
        else:
            st.info("「市場概況」タブの「🔍 外部環境を戦略的に分析」ボタンを実行すると、この画面にワンセンテンスの本質が表示されます。")

            # 手入力フォールバック
            st.markdown("---")
            st.markdown("**手動で記述する場合**")
            manual_essence = st.text_area(
                "外部環境の本質（1文）",
                value=saved_analysis.get("macro_summary", {}).get("essence_of_environment", "") if saved_analysis else "",
                height=80,
                placeholder="例: デジタル化による構造変化と人口減少に伴う市場縮小が同時進行する中、顧客接点の差別化が競争優位の決定的要因になった。",
                label_visibility="collapsed",
            )
            if manual_essence:
                st.session_state["ext_manual_essence"] = manual_essence

    # ============================================================
    # Tab 7: 保存・確認
    # ============================================================
    with tab_save:
        st.subheader("入力内容の確認・保存")
        st.markdown("全タブの内容を一括保存します。保存後、STEP 8 SWOT分析のAI生成に自動で活用されます。")

        # サマリー表示
        pest_w = st.session_state.get("ext_pest_working", {})
        forces_w = st.session_state.get("ext_forces_working", {})
        comps_w = st.session_state.get("ext_comps_working", [])
        mkt_w = st.session_state.get("ext_mkt_working", {})

        total_pest = sum(len([r for r in rows if r.get("事実・観察事項")]) for rows in pest_w.values())
        total_comps = len([c for c in comps_w if c.get("name")])
        forces_done = sum(1 for k in _FORCES if forces_w.get(k, {}).get("summary"))

        analysis_w = st.session_state.get("ext_ai_analysis", saved_analysis)
        has_analysis = bool(analysis_w.get("macro_summary", {}).get("essence_of_environment"))

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("PEST項目数", total_pest)
        m2.metric("5フォース入力済み", f"{forces_done}/5")
        m3.metric("競合登録数", total_comps)
        m4.metric("市場概況", "✅" if mkt_w.get("size") else "未入力")
        m5.metric("戦略的分析", "✅ 完了" if has_analysis else "未生成")

        st.markdown("---")

        # PEST サマリービュー
        if total_pest > 0:
            with st.expander("PEST分析サマリー"):
                for cat_key, meta in _PEST_CATEGORIES.items():
                    rows = [r for r in pest_w.get(cat_key, []) if r.get("事実・観察事項")]
                    if rows:
                        st.markdown(f"**{meta['icon']} {meta['label']}**")
                        for r in rows:
                            col_a, col_b = st.columns([6, 1])
                            with col_a:
                                st.markdown(f"- {r['事実・観察事項']}")
                            with col_b:
                                st.markdown(_impact_badge(r.get("影響度", "中")), unsafe_allow_html=True)

        # 保存ボタン
        st.markdown("---")
        bc1, bc2, _ = st.columns([1, 1, 2])
        with bc1:
            if st.button("💾 全データを保存", type="primary", use_container_width=True, key="save_all_ext"):
                save_data = {
                    "market_overview": mkt_w,
                    "pest": pest_w,
                    "five_forces": forces_w,
                    "competitors": comps_w,
                }
                # 戦略的分析（手動本質テキストがあればマージ）
                ext_analysis_to_save = dict(analysis_w) if analysis_w else {}
                manual_essence = st.session_state.get("ext_manual_essence", "")
                if manual_essence and not ext_analysis_to_save.get("macro_summary", {}).get("essence_of_environment"):
                    macro_s = ext_analysis_to_save.setdefault("macro_summary", {})
                    macro_s["essence_of_environment"] = manual_essence

                _save_ext(client_id, save_data, complete_steps=[2, 3],
                          ext_analysis=ext_analysis_to_save if ext_analysis_to_save else None)
                # ProjectContext キャッシュをクリアして次回再読み込み
                pck = f"pipeline_{client_id}"
                if pck in st.session_state:
                    del st.session_state[pck]
                st.success("✅ 外部環境データを保存しました。STEP 2・3 完了。")
                st.balloons()
        with bc2:
            if st.button("♻️ AI生成をクリア", use_container_width=True, key="clear_ai_ext"):
                st.session_state.ext_ai_pest = {}
                st.session_state.ext_ai_forces = {}
                st.session_state.ext_ai_competitors = []
                st.session_state.ext_ai_analysis = {}
                st.rerun()

    st.divider()
    n1, n2, n3 = st.columns(3)
    with n1:
        st.page_link("pages/01_project_workspace.py", label="← ワークスペース")
    with n2:
        st.page_link("pages/10_phase1_intake.py", label="← STEP 3 会社概要インプット")
    with n3:
        st.page_link("pages/04_swot_analysis.py", label="次へ: STEP 8 SWOT分析 →")


main()
