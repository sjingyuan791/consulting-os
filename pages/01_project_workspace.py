"""
Project Workspace — 18ステップ・コンサルティングパイプライン
プロジェクト選択後のメインコックピット画面。
"""
import json
import streamlit as st
from html import escape
from core.auth import check_auth
from core.executive_decision_board import build_decision_board
from core.style_utils import load_custom_css

st.set_page_config(
    page_title="Project Workspace — Consulting OS",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_custom_css()

# ------------------------------------------------------------------ #
#  パイプライン定義（18ステップ）
# ------------------------------------------------------------------ #
PHASES = [
    {
        "id": "phase1",
        "name": "データ収集",
        "icon": "📥",
        "color": "#6366f1",
        "steps": [
            {"id": 1,  "name": "決算書アップロード",     "icon": "📊", "page": "pages/02_upload.py",            "desc": "PL/BS/CFをアップロードまたは手入力"},
            {"id": 2,  "name": "外部環境調査・登録",     "icon": "🌍", "page": "pages/external_environment.py",  "desc": "PEST・5フォース・競合分析を構造化入力"},
            {"id": 3,  "name": "会社概要インプット",     "icon": "🏢", "page": "pages/10_phase1_intake.py",     "desc": "会社概要・事業内容をアップロードまたはMDで入力"},
        ],
    },
    {
        "id": "phase2",
        "name": "環境分析",
        "icon": "🔍",
        "color": "#0ea5e9",
        "steps": [
            {"id": 4,  "name": "財務・事業分析",         "icon": "📈", "page": "pages/11_phase2_roa.py",        "desc": "財務分析・ROA分解・収益構造の把握"},
            {"id": 5,  "name": "内部環境調査項目示唆",   "icon": "💡", "page": "pages/05_internal_survey_items.py", "desc": "AIが財務分析から調査すべき内部環境項目を提案"},
            {"id": 6,  "name": "内部環境分析登録",       "icon": "📋", "page": "pages/06_internal_docs.py",         "desc": "ヒアリング結果・社内文書をSTEP 5項目にひも付けて登録"},
        ],
    },
    {
        "id": "phase3",
        "name": "方向性設定",
        "icon": "🎯",
        "color": "#f59e0b",
        "steps": [
            {"id": 7,  "name": "理念・ビジョン設定",     "icon": "✨", "page": "pages/vision_mission.py",       "desc": "経営理念・ビジョン・ミッションを設定"},
        ],
    },
    {
        "id": "phase4",
        "name": "戦略分析",
        "icon": "⚔️",
        "color": "#ef4444",
        "steps": [
            {"id": 8,  "name": "SWOT分析",               "icon": "⚔️", "page": "pages/04_swot_analysis.py",    "desc": "強み・弱み・機会・脅威を体系化"},
            {"id": 9,  "name": "真因分析",               "icon": "🔎", "page": "pages/12_phase3_rootcause.py",  "desc": "課題の根本原因を特定・構造化"},
        ],
    },
    {
        "id": "phase5",
        "name": "戦略策定",
        "icon": "🗺️",
        "color": "#10b981",
        "steps": [
            {"id": 10, "name": "全社戦略仮説",           "icon": "🧭", "page": "pages/14_phase5_strategy.py",  "desc": "経営戦略の方向性・仮説を策定"},
            {"id": 11, "name": "ドメイン設定",           "icon": "🗺️", "page": "pages/domain_positioning.py",  "desc": "事業ドメイン・競争領域を定義"},
            {"id": 12, "name": "ポジショニングマップ",   "icon": "📍", "page": "pages/domain_positioning.py",  "desc": "競合との差異化ポジションを可視化"},
        ],
    },
    {
        "id": "phase6",
        "name": "機能別計画",
        "icon": "⚙️",
        "color": "#8b5cf6",
        "steps": [
            {"id": 13, "name": "機能別戦略策定",         "icon": "⚙️", "page": "pages/15_phase6_tactical.py",  "desc": "営業・製造・管理などの機能別戦略"},
            {"id": 14, "name": "機能別戦術策定",         "icon": "🛠️", "page": "pages/16_phase7_plan.py",      "desc": "各機能の具体的施策・アクションプラン"},
        ],
    },
    {
        "id": "phase7",
        "name": "数値計画",
        "icon": "💰",
        "color": "#f97316",
        "steps": [
            {"id": 15, "name": "売上計画策定",           "icon": "💰", "page": "pages/15_midterm_plan.py",      "desc": "売上目標・根拠・セグメント別計画"},
            {"id": 16, "name": "CF計画策定",             "icon": "💸", "page": "pages/17_financial_simulation.py", "desc": "キャッシュフロー計画・資金繰り"},
            {"id": 17, "name": "3か年数値計画",          "icon": "📅", "page": "pages/17_financial_simulation.py", "desc": "PL/BS/CF 3か年シミュレーション"},
        ],
    },
    {
        "id": "phase8",
        "name": "実行計画",
        "icon": "🚀",
        "color": "#06b6d4",
        "steps": [
            {"id": 18, "name": "スケジュール策定",       "icon": "📋", "page": "pages/09_execution.py",         "desc": "実行スケジュール・KPI・責任者設定"},
        ],
    },
]

ALL_STEPS = [step for phase in PHASES for step in phase["steps"]]
TOTAL_STEPS = len(ALL_STEPS)  # 18


# ------------------------------------------------------------------ #
#  Pipeline state helpers (Supabaseのclients.notesに保存)
# ------------------------------------------------------------------ #
def _load_pipeline_state(client_id: str) -> dict:
    """pipeline_steps dict を返す。{step_id: "done"|"in_progress"|"not_started"}"""
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        return notes.get("pipeline_steps", {})
    except Exception:
        return {}


def _save_step_status(client_id: str, step_id: int, status: str):
    """単一ステップのステータスを保存。"""
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        steps = notes.get("pipeline_steps", {})
        steps[str(step_id)] = status
        notes["pipeline_steps"] = steps
        sb.table("clients").update({"notes": json.dumps(notes, ensure_ascii=False)}).eq("id", client_id).execute()
    except Exception:
        pass


def _get_step_status(pipeline_steps: dict, step_id: int) -> str:
    return pipeline_steps.get(str(step_id), "not_started")


# ------------------------------------------------------------------ #
#  CSS additions for workspace
# ------------------------------------------------------------------ #
st.markdown("""
<style>
.main .block-container { max-width: 1280px; padding: 1.5rem 2.5rem 4rem; }

/* === Top bar === */
.ws-topbar {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 1.5rem;
}
.ws-project-name {
    font-size: 1.4rem; font-weight: 800; color: #111827; letter-spacing: -0.02em;
}
.ws-industry-badge {
    background: #eef2ff; color: #4f46e5;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    padding: 3px 10px; border-radius: 999px;
}

/* === Progress header === */
.ws-progress-wrap {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 14px;
    padding: 1.25rem 1.5rem; margin-bottom: 1.75rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    display: flex; align-items: center; gap: 1.5rem;
}
.ws-progress-left { flex: 1; }
.ws-progress-title { font-size: 0.78rem; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
.ws-progress-big { font-size: 2rem; font-weight: 800; color: #111827; margin-bottom: 6px; }
.ws-progress-bar-bg { background: #f3f4f6; border-radius: 999px; height: 8px; }
.ws-progress-bar-fill { background: linear-gradient(90deg, #6366f1, #a78bfa); height: 100%; border-radius: 999px; transition: width 0.5s ease; }
.ws-phase-counts { display: flex; gap: 1rem; flex-wrap: wrap; }
.ws-phase-count { text-align: center; }
.ws-phase-count-num { font-size: 1.1rem; font-weight: 700; color: #111827; }
.ws-phase-count-label { font-size: 0.7rem; color: #9ca3af; }

/* === Phase group === */
.phase-header {
    display: flex; align-items: center; gap: 8px;
    font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
    margin-bottom: 0.75rem; margin-top: 0.5rem;
}
.phase-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

/* === Step cards === */
.step-card {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
    padding: 1rem; transition: all 0.15s; position: relative;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    min-height: 120px;
}
.step-card:hover { border-color: #a5b4fc; box-shadow: 0 4px 14px rgba(79,70,229,0.1); transform: translateY(-1px); }
.step-card-done { background: #f0fdf4 !important; border-color: #86efac !important; }
.step-card-inprog { background: #eff6ff !important; border-color: #93c5fd !important; }

.step-num { font-size: 0.68rem; font-weight: 700; color: #9ca3af; margin-bottom: 4px; }
.step-icon { font-size: 1.2rem; margin-bottom: 4px; }
.step-name { font-size: 0.88rem; font-weight: 700; color: #111827; margin-bottom: 3px; line-height: 1.3; }
.step-desc { font-size: 0.73rem; color: #9ca3af; line-height: 1.4; margin-bottom: 8px; }

.step-badge-done    { background: #dcfce7; color: #15803d; font-size: 0.68rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; display: inline-block; margin-bottom: 6px; }
.step-badge-inprog  { background: #dbeafe; color: #1d4ed8; font-size: 0.68rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; display: inline-block; margin-bottom: 6px; }
.step-badge-notstart{ background: #f3f4f6; color: #6b7280; font-size: 0.68rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; display: inline-block; margin-bottom: 6px; }

.exec-board {
    background: #ffffff;
    border: 1px solid #dbe4ee;
    border-radius: 8px;
    padding: 1.15rem 1.25rem;
    margin: 1.25rem 0 1.5rem;
    box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
}
.exec-board-title {
    font-size: 0.8rem;
    font-weight: 800;
    color: #475569;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.45rem;
}
.exec-board-score {
    font-size: 2.15rem;
    font-weight: 850;
    color: #0f172a;
    line-height: 1;
}
.exec-board-status {
    display: inline-flex;
    border-radius: 8px;
    padding: 4px 9px;
    font-size: 0.78rem;
    font-weight: 800;
    margin-top: 8px;
}
.exec-board-success { background: #dcfce7; color: #166534; }
.exec-board-warning { background: #fef3c7; color: #92400e; }
.exec-board-danger { background: #fee2e2; color: #991b1b; }
.exec-board-copy {
    color: #334155;
    font-size: 0.9rem;
    line-height: 1.55;
}
.exec-board-list {
    margin: 0.4rem 0 0;
    padding-left: 1rem;
    color: #475569;
    font-size: 0.82rem;
    line-height: 1.55;
}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ #
#  Sidebar
# ------------------------------------------------------------------ #
def render_sidebar(client_id: str, client_name: str, pipeline_steps: dict):
    with st.sidebar:
        st.markdown("### ◆ Consulting OS")
        st.divider()

        # Project context
        st.markdown(f"**📁 {client_name}**")
        done = sum(1 for v in pipeline_steps.values() if v == "done")
        pct = int(done / TOTAL_STEPS * 100)
        st.progress(pct / 100, text=f"進捗 {done}/{TOTAL_STEPS} ({pct}%)")

        if st.button("← プロジェクト一覧", key="ws_back_home", use_container_width=True):
            st.switch_page("app.py")

        st.divider()
        st.markdown("**💬 AI チャット**")
        st.page_link("app.py", label="AI チャットを開く")

        st.divider()
        st.markdown("**📋 ステップ**")
        for phase in PHASES:
            st.caption(f"{phase['icon']} {phase['name']}")
            for step in phase["steps"]:
                status = _get_step_status(pipeline_steps, step["id"])
                icon = "✅" if status == "done" else ("🔵" if status == "in_progress" else "○")
                try:
                    st.page_link(step["page"], label=f"{icon} {step['id']}. {step['name']}")
                except Exception:
                    pass

        st.divider()
        if st.session_state.get("user"):
            st.caption(st.session_state.user.email)
        from core.auth import logout_user
        if st.button("ログアウト", key="ws_logout"):
            logout_user()


def render_executive_decision_board(pipeline_steps: dict):
    board = build_decision_board(pipeline_steps)
    status_cls = f"exec-board-{board.status_tone}"
    questions = "".join(f"<li>{escape(q)}</li>" for q in board.blocking_questions[:4])
    gates = "".join(f"<li>{escape(g)}</li>" for g in board.quality_gates[:4])
    differentiation = "".join(f"<li>{escape(s)}</li>" for s in board.differentiation_signals[:3])

    st.markdown(f"""
    <div class="exec-board">
        <div class="exec-board-title">社長の意思決定ボード</div>
        <div style="display:grid;grid-template-columns:0.9fr 2.2fr;gap:1.25rem;align-items:start;">
            <div>
                <div class="exec-board-score">{board.readiness_score}%</div>
                <div class="exec-board-status {status_cls}">{escape(board.status)}</div>
            </div>
            <div class="exec-board-copy">
                <strong>{escape(board.executive_summary)}</strong><br>
                次の一手: {escape(board.next_action)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("##### 未解決の経営論点")
        st.markdown(f'<ul class="exec-board-list">{questions}</ul>', unsafe_allow_html=True)
    with c2:
        st.markdown("##### 品質ゲート")
        st.markdown(f'<ul class="exec-board-list">{gates}</ul>', unsafe_allow_html=True)
    with c3:
        st.markdown("##### LLM代替されにくい強み")
        st.markdown(f'<ul class="exec-board-list">{differentiation}</ul>', unsafe_allow_html=True)


# ------------------------------------------------------------------ #
#  Main
# ------------------------------------------------------------------ #
def main():
    if not check_auth():
        st.warning("ログインしてください。")
        st.page_link("app.py", label="← ログインページへ")
        return

    client_id = st.session_state.get("client_id")
    client_name = st.session_state.get("client_name", "プロジェクト")

    if not client_id:
        st.info("プロジェクトが選択されていません。")
        if st.button("← プロジェクト一覧に戻る", type="primary"):
            st.switch_page("app.py")
        return

    # Load pipeline state (cache in session)
    cache_key = f"pipeline_{client_id}"
    if cache_key not in st.session_state or st.session_state.get("pipeline_reload"):
        st.session_state[cache_key] = _load_pipeline_state(client_id)
        st.session_state.pipeline_reload = False

    pipeline_steps = st.session_state[cache_key]

    # Sidebar
    render_sidebar(client_id, client_name, pipeline_steps)

    # Compute stats
    done_count = sum(1 for v in pipeline_steps.values() if v == "done")
    inprog_count = sum(1 for v in pipeline_steps.values() if v == "in_progress")
    pct = int(done_count / TOTAL_STEPS * 100)

    # ---- Project header ----
    # Get project details
    industry = ""
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("industry, location").eq("id", client_id).single().execute()
        if res.data:
            industry = res.data.get("industry", "")
    except Exception:
        pass

    col_title, col_actions = st.columns([4, 1])
    with col_title:
        st.markdown(f"""
        <div class="ws-topbar">
            <div class="ws-project-name">{client_name}</div>
            <div class="ws-industry-badge">{industry or '未設定'}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_actions:
        if st.button("← 一覧", key="ws_to_hub"):
            st.switch_page("app.py")

    # ---- Progress card ----
    p1, p2, p3, p4 = st.columns([3, 1, 1, 1])
    with p1:
        st.markdown(f"""
        <div style="margin-bottom:0.25rem;">
            <span style="font-size:0.78rem;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;">全体進捗</span>
        </div>
        <div style="font-size:2rem;font-weight:800;color:#111827;margin-bottom:8px;">{done_count} <span style="font-size:1rem;color:#9ca3af;font-weight:500;">/ {TOTAL_STEPS} ステップ完了</span></div>
        """, unsafe_allow_html=True)
        st.progress(pct / 100)
    with p2:
        st.metric("完了", done_count)
    with p3:
        st.metric("進行中", inprog_count)
    with p4:
        st.metric("未着手", TOTAL_STEPS - done_count - inprog_count)

    render_executive_decision_board(pipeline_steps)

    st.markdown("---")

    # ---- Pipeline grid ----
    # Render phases 2 per row
    phase_pairs = [PHASES[i:i+2] for i in range(0, len(PHASES), 2)]

    for pair in phase_pairs:
        row_cols = st.columns(len(pair), gap="large")
        for col_idx, phase in enumerate(pair):
            with row_cols[col_idx]:
                # Phase header
                st.markdown(
                    f'<div class="phase-header">'
                    f'<div class="phase-dot" style="background:{phase["color"]}"></div>'
                    f'{phase["icon"]} {phase["name"]}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                for step in phase["steps"]:
                    status = _get_step_status(pipeline_steps, step["id"])
                    card_cls = (
                        "step-card-done" if status == "done"
                        else "step-card-inprog" if status == "in_progress"
                        else ""
                    )
                    badge_cls = (
                        "step-badge-done" if status == "done"
                        else "step-badge-inprog" if status == "in_progress"
                        else "step-badge-notstart"
                    )
                    badge_txt = (
                        "✅ 完了" if status == "done"
                        else "🔵 進行中" if status == "in_progress"
                        else "○ 未着手"
                    )

                    with st.container():
                        st.markdown(
                            f'<div class="step-card {card_cls}">'
                            f'<div class="step-num">STEP {step["id"]}</div>'
                            f'<div class="step-icon">{step["icon"]}</div>'
                            f'<div class="step-name">{step["name"]}</div>'
                            f'<div class="step-desc">{step["desc"]}</div>'
                            f'<span class="{badge_cls}">{badge_txt}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                        # Buttons
                        bc1, bc2, bc3 = st.columns([2, 1, 1])
                        with bc1:
                            try:
                                st.page_link(
                                    step["page"],
                                    label=f"→ 開く",
                                    use_container_width=True,
                                )
                            except Exception:
                                if st.button(f"→ 開く", key=f"open_step_{step['id']}", use_container_width=True):
                                    pass
                        with bc2:
                            if st.button(
                                "✅",
                                key=f"done_{step['id']}",
                                help="完了にする",
                                use_container_width=True,
                            ):
                                _save_step_status(client_id, step["id"], "done")
                                st.session_state.pipeline_reload = True
                                st.rerun()
                        with bc3:
                            if st.button(
                                "↩",
                                key=f"reset_{step['id']}",
                                help="未着手に戻す",
                                use_container_width=True,
                            ):
                                _save_step_status(client_id, step["id"], "not_started")
                                st.session_state.pipeline_reload = True
                                st.rerun()

                    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

    # ---- Quick actions ----
    st.markdown("---")
    st.markdown("#### クイックアクション")
    qa1, qa2, qa3, qa4, qa5 = st.columns(5)
    with qa1:
        st.page_link("pages/02_upload.py", label="📥 ファイルアップロード")
    with qa2:
        st.page_link("pages/04_swot_analysis.py", label="⚔️ SWOT分析")
    with qa3:
        st.page_link("pages/15_midterm_plan.py", label="📄 中期経営計画")
    with qa4:
        st.page_link("pages/09_execution.py", label="📋 実行管理")
    with qa5:
        st.page_link("pages/deliverable_export.py", label="📤 成果物エクスポート")


main()
