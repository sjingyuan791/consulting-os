"""
STEP 8: SWOT分析
財務・外部環境・内部能力・理念・ビジョンを統合して SWOT を生成・編集・保存する。
上流データを自動注入し、生成結果は下流（真因・戦略仮説）に自動連携される。
"""
import json
import streamlit as st
from core.auth import check_auth
from core.style_utils import load_custom_css

st.set_page_config(
    page_title="SWOT分析 — Consulting OS",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_custom_css()


# ------------------------------------------------------------------ #
#  DB helpers
# ------------------------------------------------------------------ #

def _load_swot(client_id: str) -> dict:
    """clients.notesからSWOTデータを読む。"""
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        return notes.get("swot_manual", {})
    except Exception:
        return {}


def _save_swot(client_id: str, swot_data: dict):
    """SWOTデータをclients.notesに保存し、STEP 8を完了にする。"""
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        notes["swot_manual"] = swot_data
        # STEP 8 完了
        steps = notes.get("pipeline_steps", {})
        steps["8"] = "done"
        notes["pipeline_steps"] = steps
        sb.table("clients").update({"notes": json.dumps(notes, ensure_ascii=False)}).eq("id", client_id).execute()
        # キャッシュ更新
        cache_key = f"pipeline_{client_id}"
        if cache_key in st.session_state:
            st.session_state[cache_key] = steps
    except Exception as e:
        st.error(f"保存エラー: {e}")


def _ai_generate_swot(client_id: str, company_name: str, industry: str) -> dict:
    """
    ProjectContextを全量注入してAI SWOT を生成する。
    STEP1-7の全データを活用。
    """
    from core.project_context import ProjectContext
    from openai import OpenAI
    from core.config import Config

    ctx = ProjectContext.load(client_id)
    context_text = ctx.to_prompt_text(scope="full")
    available = ctx.available_context_label()

    ai = OpenAI(api_key=Config.OPENAI_API_KEY)

    system_prompt = f"""あなたは一流の経営コンサルタントです。
提供されたプロジェクトデータ（財務・外部環境・内部能力・理念・ビジョン）を必ず参照し、
根拠のある具体的なSWOT分析を作成してください。
推測・一般論は避け、データに基づいた事実と仮説を明確に区別して記述してください。
{context_text}"""

    user_prompt = f"""【企業情報】
会社名: {company_name}
業種: {industry}
活用可能なデータ: {available}

上記のプロジェクトコンテキストに基づき、SWOT分析を作成してください。
各項目は3〜5点、具体的な数値・事実を含めてください。

必ず以下のJSON形式で回答してください（他のテキストは含めないこと）:
{{
  "strengths": ["強み1（根拠：具体的データ）", "強み2", "強み3"],
  "weaknesses": ["弱み1（根拠：具体的データ）", "弱み2", "弱み3"],
  "opportunities": ["機会1（根拠：市場データ・トレンド）", "機会2", "機会3"],
  "threats": ["脅威1（根拠：競合・環境データ）", "脅威2", "脅威3"],
  "so_strategy": "強み×機会の主要戦略（1文）",
  "st_strategy": "強み×脅威の主要戦略（1文）",
  "wo_strategy": "弱み×機会の主要戦略（1文）",
  "wt_strategy": "弱み×脅威の主要戦略（1文）",
  "key_issue": "最重要課題（1文）",
  "context_used": "{available}"
}}"""

    response = ai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    return json.loads(raw)


# ------------------------------------------------------------------ #
#  UI helpers
# ------------------------------------------------------------------ #

def _swot_quadrant_editor(label: str, color: str, key: str, items: list) -> list:
    """SWOTの1象限を表示・編集するUI。テキストエリアで複数行編集。"""
    st.markdown(
        f'<div style="background:{color};border-radius:10px;padding:10px 14px 4px;'
        f'font-size:0.8rem;font-weight:700;color:#374151;margin-bottom:6px;">'
        f'{label}</div>',
        unsafe_allow_html=True,
    )
    current_text = "\n".join(items) if items else ""
    edited = st.text_area(
        label,
        value=current_text,
        height=140,
        key=key,
        label_visibility="collapsed",
        placeholder="1行1項目で入力。AIで自動生成することもできます。",
    )
    return [line.strip() for line in edited.splitlines() if line.strip()]


def _context_badge(ctx_summary: dict):
    """注入されているコンテキストのバッジを表示する。"""
    items = []
    colors = {
        "has_financial": ("#dcfce7", "#15803d", "📊 財務"),
        "has_external":  ("#dbeafe", "#1d4ed8", "🌍 外部環境"),
        "has_internal":  ("#fef3c7", "#b45309", "🏭 内部能力"),
        "has_vision":    ("#f3e8ff", "#7e22ce", "✨ 理念・ビジョン"),
        "has_swot":      ("#fee2e2", "#b91c1c", "⚔️ SWOT"),
    }
    for k, (bg, fg, label) in colors.items():
        if ctx_summary.get(k):
            items.append(
                f'<span style="background:{bg};color:{fg};font-size:0.7rem;font-weight:700;'
                f'padding:2px 8px;border-radius:999px;margin-right:4px;">{label}</span>'
            )
    if items:
        st.markdown(
            '<div style="margin-bottom:1rem;">注入中のコンテキスト: ' + "".join(items) + "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("上流データが未登録です。STEP 1〜7 を完了するとAI精度が上がります。")


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
        <div style="background:#fee2e2;color:#b91c1c;font-size:0.72rem;font-weight:700;
                    padding:3px 10px;border-radius:999px;letter-spacing:0.06em;">STEP 8</div>
        <div style="font-size:0.8rem;color:#9ca3af;">戦略分析フェーズ</div>
    </div>
    """, unsafe_allow_html=True)

    st.title("⚔️ SWOT分析")
    st.markdown("上流の財務・外部環境・内部能力・理念ビジョンを統合してSWOTを作成します。")

    # コンテキスト状況を表示
    from core.project_context import ProjectContext
    ctx = ProjectContext.load(client_id)
    _context_badge(ctx.to_summary_dict())

    industry = ctx.industry or ""

    # 既存SWOTデータ読み込み
    swot = _load_swot(client_id)

    tab_generate, tab_edit, tab_cross = st.tabs(["🤖 AI生成", "✏️ 編集・確認", "🔀 クロスSWOT戦略"])

    # ---- Tab 1: AI Generate ----
    with tab_generate:
        st.subheader("AIによるSWOT自動生成")
        st.markdown(f"**活用可能なコンテキスト:** {ctx.available_context_label()}")

        # コンテキストプレビュー
        with st.expander("注入されるコンテキストを確認"):
            st.code(ctx.to_prompt_text(scope="full"), language="markdown")

        if st.button("🤖 SWOT を AI 生成する", type="primary", key="gen_swot"):
            with st.spinner("上流データを統合してSWOTを生成中..."):
                try:
                    result = _ai_generate_swot(client_id, client_name, industry)
                    # セッションに一時保存
                    st.session_state["swot_ai_result"] = result
                    st.success("✅ 生成完了。「編集・確認」タブで内容を確認・修正してください。")
                except Exception as e:
                    st.error(f"生成エラー: {e}")

        if "swot_ai_result" in st.session_state:
            r = st.session_state["swot_ai_result"]
            st.markdown("---")
            st.markdown("#### 生成結果プレビュー")

            p1, p2 = st.columns(2)
            with p1:
                st.markdown("**💪 強み (S)**")
                for item in r.get("strengths", []):
                    st.markdown(f"- {item}")
                st.markdown("**⚠️ 弱み (W)**")
                for item in r.get("weaknesses", []):
                    st.markdown(f"- {item}")
            with p2:
                st.markdown("**🌟 機会 (O)**")
                for item in r.get("opportunities", []):
                    st.markdown(f"- {item}")
                st.markdown("**⚡ 脅威 (T)**")
                for item in r.get("threats", []):
                    st.markdown(f"- {item}")

            if r.get("key_issue"):
                st.info(f"**最重要課題:** {r['key_issue']}")

            st.markdown("---")
            if st.button("💾 この内容を採用して保存", type="primary", key="adopt_ai_swot"):
                _save_swot(client_id, r)
                # session_stateに反映
                st.session_state["swot_working"] = r
                del st.session_state["swot_ai_result"]
                st.success("✅ 保存しました。STEP 8 完了。")
                st.rerun()

    # ---- Tab 2: Edit ----
    with tab_edit:
        st.subheader("SWOT 編集・保存")

        # 作業用データ（AI生成 or 既存）
        working = st.session_state.get("swot_working", swot)

        st.markdown("各象限を直接編集できます。1行1項目で入力してください。")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            s_items = _swot_quadrant_editor(
                "💪 強み（Strengths）— 内部・ポジティブ",
                "#f0fdf4", "edit_s", working.get("strengths", [])
            )
            o_items = _swot_quadrant_editor(
                "🌟 機会（Opportunities）— 外部・ポジティブ",
                "#eff6ff", "edit_o", working.get("opportunities", [])
            )
        with col2:
            w_items = _swot_quadrant_editor(
                "⚠️ 弱み（Weaknesses）— 内部・ネガティブ",
                "#fef2f2", "edit_w", working.get("weaknesses", [])
            )
            t_items = _swot_quadrant_editor(
                "⚡ 脅威（Threats）— 外部・ネガティブ",
                "#fffbeb", "edit_t", working.get("threats", [])
            )

        st.markdown("---")
        st.markdown("#### 最重要課題（Key Issue）")
        key_issue = st.text_input(
            "最重要課題",
            value=working.get("key_issue", ""),
            placeholder="例：原価率上昇と市場競争激化により収益性が悪化している",
            label_visibility="collapsed",
        )

        ec1, _ = st.columns([1, 3])
        with ec1:
            if st.button("💾 保存する", type="primary", use_container_width=True, key="save_swot_edit"):
                save_data = {
                    "strengths": s_items,
                    "weaknesses": w_items,
                    "opportunities": o_items,
                    "threats": t_items,
                    "key_issue": key_issue,
                    "so_strategy": working.get("so_strategy", ""),
                    "st_strategy": working.get("st_strategy", ""),
                    "wo_strategy": working.get("wo_strategy", ""),
                    "wt_strategy": working.get("wt_strategy", ""),
                }
                _save_swot(client_id, save_data)
                st.session_state["swot_working"] = save_data
                st.success("✅ SWOT分析を保存しました。STEP 8 完了。")
                st.balloons()

    # ---- Tab 3: Cross SWOT ----
    with tab_cross:
        st.subheader("クロスSWOT 戦略マトリクス")
        st.markdown("4象限の掛け合わせから戦略の方向性を導き出します。")

        current = st.session_state.get("swot_working", swot)

        if not any([
            current.get("strengths"), current.get("weaknesses"),
            current.get("opportunities"), current.get("threats"),
        ]):
            st.info("まず「AI生成」または「編集・確認」タブでSWOTを作成・保存してください。")
            return

        # 既存のクロスSWOT戦略を表示・編集
        st.markdown("---")
        quad_defs = [
            ("so_strategy", "🟢 SO戦略（強み × 機会）", "強みを活かして機会を掴む積極攻勢策", "#f0fdf4"),
            ("st_strategy", "🔵 ST戦略（強み × 脅威）", "強みで脅威を回避・最小化する差別化策", "#eff6ff"),
            ("wo_strategy", "🟡 WO戦略（弱み × 機会）", "機会を活かして弱みを補強する改善策", "#fffbeb"),
            ("wt_strategy", "🔴 WT戦略（弱み × 脅威）", "弱みと脅威から身を守る防衛・撤退策", "#fef2f2"),
        ]

        updated_cross = dict(current)

        c1, c2 = st.columns(2)
        cols = [c1, c2, c1, c2]
        for col, (key, title, hint, bg) in zip(cols, quad_defs):
            with col:
                with st.container():
                    st.markdown(
                        f'<div style="background:{bg};border-radius:10px;padding:10px 14px 4px;'
                        f'font-size:0.85rem;font-weight:700;margin-bottom:4px;">{title}</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption(hint)
                    val = st.text_area(
                        title,
                        value=current.get(key, ""),
                        height=80,
                        key=f"cross_{key}",
                        label_visibility="collapsed",
                        placeholder=f"例: {hint}",
                    )
                    updated_cross[key] = val

        st.markdown("---")

        # AI クロスSWOT生成
        if st.button("🤖 クロスSWOT戦略を AI 生成", key="gen_cross"):
            s = current.get("strengths", [])
            w = current.get("weaknesses", [])
            o = current.get("opportunities", [])
            t = current.get("threats", [])

            from openai import OpenAI
            from core.config import Config
            ai = OpenAI(api_key=Config.OPENAI_API_KEY)

            system_prompt = ctx.to_prompt_text(scope="strategy_only")

            prompt = f"""以下のSWOT分析結果をもとに、4象限のクロスSWOT戦略を生成してください。

強み: {'; '.join(s)}
弱み: {'; '.join(w)}
機会: {'; '.join(o)}
脅威: {'; '.join(t)}

JSONで出力してください:
{{
  "so_strategy": "強み×機会の積極策（2〜3文）",
  "st_strategy": "強み×脅威の差別化策（2〜3文）",
  "wo_strategy": "弱み×機会の改善策（2〜3文）",
  "wt_strategy": "弱み×脅威の防衛策（2〜3文）"
}}"""

            with st.spinner("クロスSWOT戦略を生成中..."):
                resp = ai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt or "あなたは一流の経営コンサルタントです。"},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=800,
                    response_format={"type": "json_object"},
                )
                cross_result = json.loads(resp.choices[0].message.content)
                updated_cross.update(cross_result)
                st.session_state["swot_working"] = updated_cross
                st.rerun()

        cc1, _ = st.columns([1, 3])
        with cc1:
            if st.button("💾 クロスSWOTを保存", type="primary", use_container_width=True, key="save_cross"):
                _save_swot(client_id, updated_cross)
                st.session_state["swot_working"] = updated_cross
                st.success("✅ クロスSWOT戦略を保存しました。")

    st.divider()
    n1, n2, n3 = st.columns(3)
    with n1:
        st.page_link("pages/vision_mission.py", label="← STEP 7 理念・ビジョン")
    with n2:
        st.page_link("pages/01_project_workspace.py", label="🏠 ワークスペース")
    with n3:
        st.page_link("pages/12_phase3_rootcause.py", label="次へ: STEP 9 真因分析 →")


if __name__ == "__main__":
    app = main
main()
