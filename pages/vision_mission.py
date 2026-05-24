"""
STEP 7: 理念・ビジョン・ミッション設定
経営の根幹となる理念・ビジョン・ミッション・バリューを設定し、AIによる提案も受けられる。
"""
import json
import streamlit as st
from core.auth import check_auth
from core.style_utils import load_custom_css

st.set_page_config(
    page_title="理念・ビジョン設定 — Consulting OS",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_custom_css()


# ------------------------------------------------------------------ #
#  DB helpers
# ------------------------------------------------------------------ #
def _load_vision_data(client_id: str) -> dict:
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        return notes.get("vision_mission", {})
    except Exception:
        return {}


def _save_vision_data(client_id: str, data: dict):
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        notes["vision_mission"] = data
        # Mark step 7 as done
        steps = notes.get("pipeline_steps", {})
        steps["7"] = "done"
        notes["pipeline_steps"] = steps
        sb.table("clients").update({"notes": json.dumps(notes, ensure_ascii=False)}).eq("id", client_id).execute()
        # Update session cache
        cache_key = f"pipeline_{client_id}"
        if cache_key in st.session_state:
            st.session_state[cache_key] = steps
    except Exception as e:
        st.error(f"保存エラー: {e}")


def _get_ai_suggestions(client_id: str, company_name: str, industry: str, existing: dict) -> str:
    """
    AIによる理念・ビジョン提案を生成する。
    ProjectContextを使って財務・外部環境データを自動注入する。
    """
    try:
        from openai import OpenAI
        from core.config import Config
        from core.project_context import ProjectContext

        # プロジェクトコンテキストを集約（財務・外部環境データを含む）
        ctx = ProjectContext.load(client_id)
        context_text = ctx.to_prompt_text(scope="financial_only")

        ai = OpenAI(api_key=Config.OPENAI_API_KEY)

        system_prompt = f"""あなたは一流の経営コンサルタントです。
クライアントの財務状況・事業環境データを踏まえた上で、
実態に即した経営理念・ビジョン・ミッション・バリューを提案してください。
{context_text}"""

        user_prompt = f"""以下の情報をもとに、経営理念・ビジョン・ミッション・バリューの案を提案してください。

会社名: {company_name}
業種: {industry}
現在の理念（あれば）: {existing.get('philosophy') or '未設定'}
現在のビジョン（あれば）: {existing.get('vision') or '未設定'}

【出力形式】

**【経営理念の案】**
（20〜40字程度、会社の存在意義・価値観）

**【ビジョンの案】**
（3〜5年後の具体的なTo-Be状態。財務データ・業界動向を踏まえた実現可能な姿）

**【ミッションの案】**
（社会・顧客・ステークホルダーへの使命）

**【バリューの案（3〜5項目）】**
・
・
・

**【財務・事業状況を踏まえた設定のポイント】**
（具体的な財務指標や業界トレンドを引用しながらアドバイス）"""

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
        <div style="background:#fef3c7;color:#b45309;font-size:0.72rem;font-weight:700;padding:3px 10px;border-radius:999px;letter-spacing:0.06em;">
            STEP 7
        </div>
        <div style="font-size:0.8rem;color:#9ca3af;">方向性設定フェーズ</div>
    </div>
    """, unsafe_allow_html=True)

    st.title("✨ 理念・ビジョン・ミッション設定")
    st.markdown("経営の根幹となる方向性を定義します。AIによる提案も活用できます。")

    # Load existing data
    data = _load_vision_data(client_id)

    # Get company info for AI
    industry = ""
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("industry").eq("id", client_id).single().execute()
        industry = res.data.get("industry", "") if res.data else ""
    except Exception:
        pass

    st.divider()

    # ---- Input form ----
    tab_input, tab_ai, tab_preview = st.tabs(["✏️ 入力・編集", "🤖 AI提案", "👁️ プレビュー"])

    with tab_input:
        with st.form("vision_form"):
            st.subheader("経営理念")
            st.caption("会社の存在意義・根本的な価値観（20〜50字程度）")
            philosophy = st.text_area(
                "経営理念",
                value=data.get("philosophy", ""),
                height=80,
                placeholder="例：人と技術の力で、社会に新たな価値を生み出し続ける",
                label_visibility="collapsed",
            )

            st.subheader("ビジョン（将来像）")
            st.caption("3〜5年後に目指す姿・To-Be状態")
            vision = st.text_area(
                "ビジョン",
                value=data.get("vision", ""),
                height=100,
                placeholder="例：2028年までに業界トップ3のシェアを獲得し、顧客満足度No.1を実現する",
                label_visibility="collapsed",
            )

            st.subheader("ミッション（使命）")
            st.caption("会社が社会・顧客・ステークホルダーに対して果たす使命")
            mission = st.text_area(
                "ミッション",
                value=data.get("mission", ""),
                height=100,
                placeholder="例：高品質な製品とサービスを通じて、お客様の課題を解決し生活を豊かにする",
                label_visibility="collapsed",
            )

            st.subheader("バリュー（行動指針）")
            st.caption("社員が日々の仕事で体現すべき価値観・行動指針（改行区切りで複数入力）")
            values_text = st.text_area(
                "バリュー",
                value=data.get("values", ""),
                height=120,
                placeholder="例：\n・誠実に行動する\n・挑戦を恐れない\n・チームで成果を出す",
                label_visibility="collapsed",
            )

            st.subheader("補足メモ")
            notes_text = st.text_area(
                "補足・背景・経緯など",
                value=data.get("notes_text", ""),
                height=80,
                label_visibility="collapsed",
            )

            c1, c2 = st.columns([1, 3])
            with c1:
                submitted = st.form_submit_button("💾 保存する", type="primary", use_container_width=True)

            if submitted:
                save_data = {
                    "philosophy": philosophy,
                    "vision": vision,
                    "mission": mission,
                    "values": values_text,
                    "notes_text": notes_text,
                }
                _save_vision_data(client_id, save_data)
                st.success("✅ 保存しました。STEP 7 が完了となりました。")
                st.balloons()

    with tab_ai:
        st.subheader("🤖 AIによる理念・ビジョン提案")
        st.markdown("会社情報をもとにAIが理念・ビジョン・ミッション・バリューの案を提案します。")

        col_info, col_btn = st.columns([3, 1])
        with col_info:
            st.info(f"**プロジェクト:** {client_name}　|　**業種:** {industry or '未設定'}")
        with col_btn:
            generate = st.button("🤖 提案を生成", type="primary", use_container_width=True, key="gen_vision")

        if generate:
            with st.spinner("AIが提案を生成中..."):
                suggestion = _get_ai_suggestions(client_id, client_name, industry, data)
            st.markdown("---")
            st.markdown("#### 提案内容")
            st.markdown(suggestion)
            st.markdown("---")
            st.info("💡 上記の提案を参考に「入力・編集」タブで内容を入力・調整してください。")

        if "last_vision_suggestion" in st.session_state:
            st.markdown("#### 前回の提案")
            st.markdown(st.session_state.last_vision_suggestion)

    with tab_preview:
        st.subheader("プレビュー")
        if not any([data.get("philosophy"), data.get("vision"), data.get("mission")]):
            st.info("「入力・編集」タブで内容を入力すると、ここにプレビューが表示されます。")
        else:
            # Reload fresh data
            data = _load_vision_data(client_id)

            st.markdown(f"""
<div style="background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:2rem;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
    <div style="text-align:center;margin-bottom:2rem;">
        <div style="font-size:1.5rem;font-weight:800;color:#111827;">{client_name}</div>
        <div style="font-size:0.85rem;color:#9ca3af;">経営理念・ビジョン・ミッション</div>
    </div>
    <div style="margin-bottom:1.5rem;">
        <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#6366f1;margin-bottom:6px;">経営理念</div>
        <div style="font-size:1.2rem;font-weight:700;color:#111827;line-height:1.5;">{data.get('philosophy') or '—'}</div>
    </div>
    <div style="margin-bottom:1.5rem;">
        <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#0ea5e9;margin-bottom:6px;">ビジョン</div>
        <div style="font-size:1rem;color:#374151;line-height:1.6;">{data.get('vision') or '—'}</div>
    </div>
    <div style="margin-bottom:1.5rem;">
        <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#10b981;margin-bottom:6px;">ミッション</div>
        <div style="font-size:1rem;color:#374151;line-height:1.6;">{data.get('mission') or '—'}</div>
    </div>
    <div>
        <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#f59e0b;margin-bottom:6px;">バリュー</div>
        <div style="font-size:0.95rem;color:#374151;white-space:pre-line;line-height:1.8;">{data.get('values') or '—'}</div>
    </div>
</div>
""", unsafe_allow_html=True)

    st.divider()
    nav1, nav2 = st.columns(2)
    with nav1:
        st.page_link("pages/04_swot_analysis.py", label="次へ: STEP 8 SWOT分析 →")
    with nav2:
        st.page_link("pages/01_project_workspace.py", label="← ワークスペースに戻る")


main()
