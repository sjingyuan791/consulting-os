"""
sidebar.py — プロジェクト対応共通サイドバー
全既存ページから呼ばれる render_sidebar() を提供する。
"""
import json
import streamlit as st
from core.auth import logout_user

TOTAL_STEPS = 18

_PIPELINE = [
    # phase, step_id, name, page, icon
    ("データ収集",   1,  "決算書アップロード",    "pages/02_upload.py",               "📊"),
    ("データ収集",   2,  "外部環境調査・登録",    "pages/external_environment.py",    "🌍"),
    ("データ収集",   3,  "会社概要インプット",    "pages/10_phase1_intake.py",        "🏢"),
    ("環境分析",     4,  "財務・事業分析",        "pages/11_phase2_roa.py",           "📈"),
    ("環境分析",     5,  "内部環境調査項目示唆",  "pages/05_internal_survey_items.py", "💡"),
    ("環境分析",     6,  "内部環境分析登録",      "pages/06_internal_docs.py",         "📋"),
    ("方向性設定",   7,  "理念・ビジョン設定",    "pages/vision_mission.py",          "✨"),
    ("戦略分析",     8,  "SWOT分析",              "pages/04_swot_analysis.py",        "⚔️"),
    ("戦略分析",     9,  "真因分析",              "pages/12_phase3_rootcause.py",     "🔎"),
    ("戦略策定",    10,  "全社戦略仮説",          "pages/14_phase5_strategy.py",      "🧭"),
    ("戦略策定",    11,  "ドメイン設定",          "pages/domain_positioning.py",      "🗺️"),
    ("戦略策定",    12,  "ポジショニングマップ",  "pages/domain_positioning.py",      "📍"),
    ("機能別計画",  13,  "機能別戦略策定",        "pages/15_phase6_tactical.py",      "⚙️"),
    ("機能別計画",  14,  "機能別戦術策定",        "pages/16_phase7_plan.py",          "🛠️"),
    ("数値計画",    15,  "売上計画策定",          "pages/15_midterm_plan.py",         "💰"),
    ("数値計画",    16,  "CF計画策定",            "pages/17_financial_simulation.py", "💸"),
    ("数値計画",    17,  "3か年数値計画",         "pages/17_financial_simulation.py", "📅"),
    ("実行計画",    18,  "スケジュール策定",      "pages/09_execution.py",            "📋"),
]


def _load_pipeline_steps(client_id: str) -> dict:
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        return notes.get("pipeline_steps", {})
    except Exception:
        return {}


def render_topbar() -> None:
    """全ページ共通トップナビゲーションバー（サイドバーが見えなくても使える）。"""
    client_id   = st.session_state.get("client_id")
    client_name = st.session_state.get("client_name", "")

    if not client_id:
        return

    col_back, col_ws, col_name = st.columns([1, 1, 6])
    with col_back:
        if st.button("← 一覧", key="topbar_home", use_container_width=True):
            st.session_state.client_id = None
            st.session_state.client_name = None
            st.switch_page("app.py")
    with col_ws:
        if st.button("🗂 WS", key="topbar_ws", use_container_width=True):
            st.switch_page("pages/01_project_workspace.py")
    with col_name:
        st.markdown(
            f'<div style="padding:6px 0;font-size:0.85rem;color:#6b7280;">'
            f'◆ ConsultingOS &nbsp;›&nbsp; <b style="color:#1f2937;">{client_name}</b></div>',
            unsafe_allow_html=True,
        )
    st.divider()


def render_sidebar() -> None:
    """全ページ共通サイドバー。"""
    render_topbar()
    with st.sidebar:
        st.markdown("### ◆ Consulting OS")
        st.divider()

        # プロジェクトコンテキスト
        client_id = st.session_state.get("client_id")
        client_name = st.session_state.get("client_name")

        if client_id:
            # Resolve name if missing
            if not client_name:
                try:
                    from core.supabase_client import get_supabase_client
                    sb = get_supabase_client()
                    res = sb.table("clients").select("name").eq("id", client_id).single().execute()
                    if res.data:
                        client_name = res.data["name"]
                        st.session_state.client_name = client_name
                except Exception:
                    pass

            st.markdown(f"**📁 {client_name or client_id[:8]}**")

            # Progress bar
            cache_key = f"pipeline_{client_id}"
            if cache_key not in st.session_state:
                st.session_state[cache_key] = _load_pipeline_steps(client_id)
            steps = st.session_state[cache_key]
            done = sum(1 for v in steps.values() if v == "done")
            pct = int(done / TOTAL_STEPS * 100)
            st.progress(pct / 100, text=f"{done}/{TOTAL_STEPS} ステップ ({pct}%)")

            col_ws, col_ch = st.columns(2)
            with col_ws:
                if st.button("ワークスペース", key="sb_workspace", use_container_width=True):
                    st.switch_page("pages/01_project_workspace.py")
            with col_ch:
                if st.button("AIチャット", key="sb_chat", use_container_width=True):
                    st.switch_page("app.py")

            if st.button("← プロジェクト一覧", key="sb_home", use_container_width=True):
                st.session_state.client_id = None
                st.session_state.client_name = None
                st.switch_page("app.py")

        else:
            st.caption("プロジェクト未選択")
            if st.button("プロジェクト選択", key="sb_select", use_container_width=True):
                st.switch_page("app.py")

        st.divider()

        # Pipeline navigation
        st.markdown("**ステップナビ**")

        if client_id:
            # Current phase = phase of the first non-done step
            active_phase: str | None = None
            for phase, step_id, *_ in _PIPELINE:
                if steps.get(str(step_id), "not_started") != "done":
                    active_phase = phase
                    break

            # Group pipeline by phase (insertion order preserved)
            phase_groups: dict[str, list] = {}
            for phase, step_id, name, page, icon in _PIPELINE:
                phase_groups.setdefault(phase, []).append((step_id, name, page))

            for phase, items in phase_groups.items():
                phase_done = sum(1 for sid, *_ in items if steps.get(str(sid)) == "done")
                label = f"{phase} ({phase_done}/{len(items)})"
                with st.expander(label, expanded=(phase == active_phase)):
                    for step_id, name, page in items:
                        status = steps.get(str(step_id), "not_started")
                        status_icon = "✅" if status == "done" else ("🔵" if status == "in_progress" else "○")
                        try:
                            st.page_link(page, label=f"{status_icon} {step_id}. {name}")
                        except Exception:
                            st.markdown(f"&nbsp;&nbsp;{status_icon} {step_id}. {name}")
        else:
            st.caption("プロジェクトを選択するとステップが表示されます")

        st.divider()
        st.caption("ツール")
        st.page_link("pages/_18_ai_workspace.py", label="🤖 AI品質管理")
        st.page_link("pages/_19_document_manager.py", label="📄 ドキュメント管理")
        st.page_link("pages/_08_scenario_planning.py", label="🔮 シナリオ計画")
        st.page_link("pages/deliverable_export.py", label="📤 成果物エクスポート")

        st.divider()
        if st.session_state.get("user"):
            st.caption(st.session_state.user.email)
        if st.button("ログアウト", key="sb_logout"):
            logout_user()
