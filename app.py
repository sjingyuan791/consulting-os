"""
Consulting OS — Project Hub
ログイン後にプロジェクト（クライアント）一覧を表示し、各プロジェクトへ誘導する。
"""
import streamlit as st
from html import escape
from core.auth import check_auth, login_user, logout_user
from core.executive_decision_board import board_from_project

st.set_page_config(
    page_title="Consulting OS",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ------------------------------------------------------------------ #
#  共通 CSS
# ------------------------------------------------------------------ #
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+JP:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Sans JP', -apple-system, sans-serif;
}

#MainMenu { visibility: hidden; }
footer { display: none; }
[data-testid="stHeader"] { display: none; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stToolbar"] { display: none; }

/* === Hub background === */
.main { background: #f8f9fc; }
.main .block-container {
    max-width: 1200px;
    padding: 2rem 3rem 4rem;
}

/* === Top nav bar === */
.hub-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2.5rem;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid #e5e7eb;
}
.hub-logo {
    font-size: 1.3rem;
    font-weight: 800;
    color: #111827;
    letter-spacing: -0.02em;
}
.hub-logo span { color: #4f46e5; }

/* === Project cards === */
.proj-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 1.5rem;
    cursor: pointer;
    transition: all 0.18s ease;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    height: 100%;
    position: relative;
}
.proj-card:hover {
    border-color: #a5b4fc;
    box-shadow: 0 6px 20px rgba(79,70,229,0.12);
    transform: translateY(-2px);
}
.proj-card-active {
    border-color: #4f46e5 !important;
    box-shadow: 0 6px 20px rgba(79,70,229,0.18) !important;
}
.proj-industry {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6366f1;
    margin-bottom: 6px;
}
.proj-name {
    font-size: 1.15rem;
    font-weight: 700;
    color: #111827;
    margin-bottom: 4px;
}
.proj-location {
    font-size: 0.82rem;
    color: #9ca3af;
    margin-bottom: 14px;
}
.proj-progress-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #6b7280;
    margin-bottom: 4px;
}
.proj-progress-bar-bg {
    background: #f3f4f6;
    border-radius: 999px;
    height: 6px;
    overflow: hidden;
    margin-bottom: 6px;
}
.proj-progress-bar-fill {
    background: linear-gradient(90deg, #6366f1, #818cf8);
    height: 100%;
    border-radius: 999px;
    transition: width 0.4s ease;
}
.proj-step-count {
    font-size: 0.75rem;
    color: #9ca3af;
}
.decision-strip {
    border-top: 1px solid #eef2f7;
    margin-top: 14px;
    padding-top: 12px;
}
.decision-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
}
.decision-label {
    font-size: 0.72rem;
    font-weight: 700;
    color: #6b7280;
}
.decision-score {
    font-size: 1.35rem;
    font-weight: 800;
    color: #111827;
}
.decision-status {
    display: inline-flex;
    align-items: center;
    border-radius: 8px;
    padding: 3px 8px;
    font-size: 0.72rem;
    font-weight: 700;
}
.decision-status-success { background: #dcfce7; color: #166534; }
.decision-status-warning { background: #fef3c7; color: #92400e; }
.decision-status-danger { background: #fee2e2; color: #991b1b; }
.decision-next {
    color: #4b5563;
    font-size: 0.78rem;
    line-height: 1.45;
}

/* === New project card === */
.proj-card-new {
    background: #fafbff;
    border: 2px dashed #c7d2fe;
    border-radius: 16px;
    padding: 1.5rem;
    cursor: pointer;
    transition: all 0.18s ease;
    min-height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
}
.proj-card-new:hover {
    border-color: #4f46e5;
    background: #eef2ff;
}

/* === Buttons (main) === */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.875rem;
    border: 1px solid #e5e7eb;
    background: #ffffff;
    color: #374151;
    padding: 8px 18px;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    border-color: #a5b4fc;
    color: #4f46e5;
    background: #eef2ff;
}
.stButton > button[kind="primary"] {
    background: #4f46e5 !important;
    color: #ffffff !important;
    border-color: #4f46e5 !important;
    box-shadow: 0 3px 8px rgba(79,70,229,0.3);
}
.stButton > button[kind="primary"]:hover {
    background: #4338ca !important;
    border-color: #4338ca !important;
    box-shadow: 0 6px 16px rgba(79,70,229,0.4);
}

/* === Login page === */
.login-wrap {
    display: flex; align-items: center; justify-content: center; min-height: 90vh;
}
.login-logo { font-size: 1.6rem; font-weight: 800; color: #111827; letter-spacing:-0.03em; }
.login-logo span { color: #4f46e5; }
.login-sub { font-size: 0.9rem; color: #6b7280; margin: 4px 0 2rem; }
.stForm {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 2.5rem !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.06);
}
div[data-testid="stForm"] .stButton > button[kind="primaryFormSubmit"],
div[data-testid="stForm"] .stButton > button[kind="primary"] {
    background: #4f46e5 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700;
    padding: 0.65rem 0;
    box-shadow: 0 4px 12px rgba(79,70,229,0.3);
}

/* === Section header === */
.section-header {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #9ca3af;
    margin: 0 0 1rem;
}

/* === Metric cards === */
[data-testid="stMetric"] {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
[data-testid="stMetricLabel"] { color: #6b7280; font-size: 0.78rem; font-weight: 600; }
[data-testid="stMetricValue"] { color: #111827; font-size: 1.75rem; font-weight: 800; }

/* === Form inputs === */
.stTextInput input, .stSelectbox > div > div {
    border-radius: 8px; border-color: #d1d5db; font-size: 0.9rem;
}
.stTextInput input:focus { border-color: #818cf8; box-shadow: 0 0 0 3px rgba(129,140,248,0.15); }

/* === Expander (create form) === */
[data-testid="stExpander"] {
    border: 1px solid #e5e7eb !important; border-radius: 12px !important; background: #fff;
}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ #
#  DB helpers
# ------------------------------------------------------------------ #
def _get_or_create_workspace(user_id: str) -> str:
    """ユーザーのデフォルトワークスペースを取得（なければ作成）。"""
    from core.supabase_client import get_supabase_client
    sb = get_supabase_client()
    res = sb.table("workspaces").select("id").eq("owner_user_id", user_id).limit(1).execute()
    if res.data:
        return res.data[0]["id"]
    # Create default workspace
    ins = sb.table("workspaces").insert({"owner_user_id": user_id, "name": "My Workspace"}).execute()
    return ins.data[0]["id"]


def _get_projects(user_id: str) -> list[dict]:
    from core.supabase_client import get_supabase_client
    sb = get_supabase_client()
    ws_res = sb.table("workspaces").select("id").eq("owner_user_id", user_id).execute()
    if not ws_res.data:
        return []
    ws_ids = [w["id"] for w in ws_res.data]
    try:
        cl_res = (
            sb.table("clients")
            .select("id, name, industry, location, notes, created_at")
            .in_("workspace_id", ws_ids)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:
        # notes カラムが未作成の場合はフォールバック
        cl_res = (
            sb.table("clients")
            .select("id, name, industry, location, created_at")
            .in_("workspace_id", ws_ids)
            .order("created_at", desc=True)
            .execute()
        )
    return cl_res.data or []


def _create_project(workspace_id: str, name: str, industry: str, location: str):
    from core.supabase_client import get_supabase_client
    import json
    sb = get_supabase_client()
    row = {"workspace_id": workspace_id, "name": name,
           "industry": industry, "location": location}
    try:
        row["notes"] = json.dumps({"pipeline_steps": {}})
        sb.table("clients").insert(row).execute()
    except Exception:
        row.pop("notes", None)
        sb.table("clients").insert(row).execute()


def _get_pipeline_progress(project: dict) -> tuple[int, int]:
    """完了ステップ数と全ステップ数を返す。"""
    board = board_from_project(project)
    return board.completed_steps, board.total_steps


# ------------------------------------------------------------------ #
#  Today's Actions helpers
# ------------------------------------------------------------------ #
_STEP_MAP: dict[int, tuple] = {
    1:  ("決算書アップロード",    "pages/02_upload.py"),
    2:  ("外部環境調査・登録",    "pages/external_environment.py"),
    3:  ("会社概要インプット",    "pages/10_phase1_intake.py"),
    4:  ("財務・事業分析",        "pages/11_phase2_roa.py"),
    5:  ("内部環境調査項目示唆",  "pages/05_internal_survey_items.py"),
    6:  ("内部環境分析登録",      "pages/06_internal_docs.py"),
    7:  ("理念・ビジョン設定",    "pages/vision_mission.py"),
    8:  ("SWOT分析",              "pages/04_swot_analysis.py"),
    9:  ("真因分析",              "pages/12_phase3_rootcause.py"),
    10: ("全社戦略仮説",          "pages/14_phase5_strategy.py"),
    11: ("ドメイン設定",          "pages/domain_positioning.py"),
    12: ("ポジショニングマップ",  "pages/domain_positioning.py"),
    13: ("機能別戦略策定",        "pages/15_phase6_tactical.py"),
    14: ("機能別戦術策定",        "pages/16_phase7_plan.py"),
    15: ("売上計画策定",          "pages/15_midterm_plan.py"),
    16: ("CF計画策定",            "pages/17_financial_simulation.py"),
    17: ("3か年数値計画",         "pages/17_financial_simulation.py"),
    18: ("スケジュール策定",      "pages/09_execution.py"),
}


def _get_next_step(pipeline_steps: dict) -> tuple | None:
    """Returns (step_id, step_name, page, status) for the highest-priority actionable step."""
    for step_id in range(1, 19):
        status = pipeline_steps.get(str(step_id), "not_started")
        if status in ("in_progress", "not_started"):
            name, page = _STEP_MAP.get(step_id, ("不明なステップ", ""))
            return (step_id, name, page, status)
    return None


def _build_action_items(projects: list[dict]) -> list[dict]:
    """Today's recommended actions across all active projects."""
    import json as _json
    actions = []
    for proj in projects:
        raw = proj.get("notes")
        notes: dict = {}
        if raw:
            try:
                notes = _json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                pass
        pipeline_steps = notes.get("pipeline_steps", {})
        done = sum(1 for v in pipeline_steps.values() if v == "done")
        if done >= 18:
            continue
        result = _get_next_step(pipeline_steps)
        if not result:
            continue
        step_id, step_name, page, status = result
        actions.append({
            "client_id":   proj["id"],
            "client_name": proj.get("name") or "未設定",
            "industry":    proj.get("industry") or "",
            "step_id":     step_id,
            "step_name":   step_name,
            "page":        page,
            "urgency":     status,
            "done":        done,
        })
    actions.sort(key=lambda x: (0 if x["urgency"] == "in_progress" else 1, x["step_id"]))
    return actions


# ------------------------------------------------------------------ #
#  Login Page
# ------------------------------------------------------------------ #
def _login_page():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown('<div class="login-logo">◆ Consulting<span>OS</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Strategic Intelligence Platform</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("メールアドレス", placeholder="you@example.com")
            password = st.text_input("パスワード", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("ログイン", type="primary", use_container_width=True)

            if submitted:
                if email and password:
                    resp = login_user(email, password)
                    if resp:
                        st.session_state.user = resp.user
                        if resp.session:
                            st.session_state.access_token = resp.session.access_token
                            st.session_state.refresh_token = resp.session.refresh_token
                        st.rerun()
                else:
                    st.warning("メールアドレスとパスワードを入力してください。")


# ------------------------------------------------------------------ #
#  Project Hub (main page after login)
# ------------------------------------------------------------------ #
def _project_hub():
    user = st.session_state.user
    projects = _get_projects(user.id)

    # Top navigation bar
    col_logo, col_user = st.columns([4, 1])
    with col_logo:
        st.markdown('<div class="hub-logo">◆ Consulting<span>OS</span></div>', unsafe_allow_html=True)
    with col_user:
        st.caption(user.email)
        if st.button("ログアウト", key="hub_logout"):
            logout_user()

    st.markdown("---")

    # Summary metrics
    total_projects = len(projects)
    active_projects = sum(1 for p in projects if _get_pipeline_progress(p)[0] > 0)
    boards = [board_from_project(p) for p in projects]
    decision_ready = sum(1 for b in boards if b.readiness_score >= 70)
    needs_data = sum(1 for b in boards if b.status == "データ不足")

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("プロジェクト総数", total_projects)
    with m2:
        st.metric("進行中", active_projects)
    with m3:
        st.metric("決裁候補", decision_ready)
    with m4:
        st.metric("データ不足", needs_data)
    with m5:
        avg_progress = (
            sum(b.readiness_score for b in boards) / total_projects
            if total_projects > 0 else 0
        )
        st.metric("平均決裁可能度", f"{avg_progress:.0f}%")

    if projects:
        most_ready = max(zip(projects, boards), key=lambda item: item[1].readiness_score)
        st.info(
            f"PMレビュー: 最も決裁に近い案件は「{most_ready[0].get('name', '未設定')}」です。"
            f"{most_ready[1].executive_summary}"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Today's Actions Dashboard
    action_items = _build_action_items(projects)
    if action_items:
        st.markdown('<div class="section-header">🎯 今日やること</div>', unsafe_allow_html=True)
        for item in action_items[:5]:
            is_active = item["urgency"] == "in_progress"
            left_border = "#3b82f6" if is_active else "#d1d5db"
            bg_color = "#eff6ff" if is_active else "#f9fafb"
            badge_html = (
                '<span style="background:#dbeafe;color:#1e40af;padding:1px 7px;'
                'border-radius:5px;font-size:0.68rem;font-weight:700;">進行中</span>'
                if is_active else
                '<span style="background:#f3f4f6;color:#6b7280;padding:1px 7px;'
                'border-radius:5px;font-size:0.68rem;font-weight:700;">次のステップ</span>'
            )
            col_info, col_btn = st.columns([8, 1])
            with col_info:
                st.markdown(f"""
                <div style="background:{bg_color};border-left:3px solid {left_border};
                            border-radius:8px;padding:0.65rem 1rem;line-height:1.5;margin-bottom:6px;">
                    <span style="font-size:0.88rem;font-weight:700;color:#111827;">
                        {escape(item['client_name'])}</span>
                    &nbsp;{badge_html}
                    <div style="font-size:0.78rem;color:#6b7280;margin-top:2px;">
                        STEP {item['step_id']}: {escape(item['step_name'])}
                        &nbsp;<span style="color:#9ca3af;">{item['done']}/18 完了</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col_btn:
                if st.button("着手 →", key=f"today_{item['client_id']}_{item['step_id']}",
                             use_container_width=True):
                    st.session_state.client_id = item["client_id"]
                    st.session_state.client_name = item["client_name"]
                    st.switch_page(item["page"])
        st.markdown("<br>", unsafe_allow_html=True)

    # Section header + new project button
    hdr_col, btn_col = st.columns([3, 1])
    with hdr_col:
        st.markdown('<div class="section-header">プロジェクト一覧</div>', unsafe_allow_html=True)
    with btn_col:
        if st.button("＋ 新規プロジェクト", type="primary", use_container_width=True, key="open_create"):
            st.session_state.show_create = True

    # Create new project form
    if st.session_state.get("show_create"):
        with st.expander("新規プロジェクト作成", expanded=True):
            with st.form("create_project_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    new_name = st.text_input("プロジェクト名（会社名）", placeholder="株式会社○○")
                with c2:
                    new_industry = st.text_input("業種", placeholder="製造業")
                with c3:
                    new_location = st.text_input("所在地", placeholder="東京都")

                fc1, fc2, _ = st.columns([1, 1, 2])
                with fc1:
                    submitted = st.form_submit_button("作成する", type="primary", use_container_width=True)
                with fc2:
                    if st.form_submit_button("キャンセル", use_container_width=True):
                        st.session_state.show_create = False
                        st.rerun()

                if submitted:
                    if new_name:
                        ws_id = _get_or_create_workspace(user.id)
                        _create_project(ws_id, new_name, new_industry, new_location)
                        st.session_state.show_create = False
                        st.success(f"✅ プロジェクト「{new_name}」を作成しました。")
                        st.rerun()
                    else:
                        st.warning("プロジェクト名を入力してください。")

    st.markdown("<br>", unsafe_allow_html=True)

    # Project grid
    if not projects:
        st.markdown("""
        <div style="text-align:center; padding: 4rem 0; color: #9ca3af;">
            <div style="font-size:3rem; margin-bottom:1rem;">📂</div>
            <div style="font-size:1.1rem; font-weight:600; color:#374151; margin-bottom:0.5rem;">
                プロジェクトがありません
            </div>
            <div style="font-size:0.875rem;">「＋ 新規プロジェクト」から最初のプロジェクトを作成してください。</div>
        </div>
        """, unsafe_allow_html=True)
        return

    COLS = 3
    rows = [projects[i:i + COLS] for i in range(0, len(projects), COLS)]

    for row in rows:
        cols = st.columns(COLS, gap="medium")
        for idx, proj in enumerate(row):
            with cols[idx]:
                done, total = _get_pipeline_progress(proj)
                pct = int(done / total * 100)
                is_active = st.session_state.get("client_id") == proj["id"]
                board = board_from_project(proj)
                tone_cls = f"decision-status-{board.status_tone}"
                project_name = escape(str(proj.get("name") or ""))
                industry = escape(str(proj.get("industry") or "未設定"))
                location = escape(str(proj.get("location") or "未設定"))
                next_decision = escape(board.next_decision)

                # Card HTML
                active_cls = "proj-card-active" if is_active else ""
                st.markdown(f"""
                <div class="proj-card {active_cls}">
                    <div class="proj-industry">{industry}</div>
                    <div class="proj-name">{project_name}</div>
                    <div class="proj-location">📍 {location}</div>
                    <div class="proj-progress-label">進捗 {done}/{total} ステップ</div>
                    <div class="proj-progress-bar-bg">
                        <div class="proj-progress-bar-fill" style="width:{pct}%"></div>
                    </div>
                    <div class="proj-step-count">{pct}% 完了</div>
                    <div class="decision-strip">
                        <div class="decision-row">
                            <div>
                                <div class="decision-label">決裁可能度</div>
                                <div class="decision-score">{board.readiness_score}%</div>
                            </div>
                            <span class="decision-status {tone_cls}">{board.status}</span>
                        </div>
                        <div class="decision-next">次の論点: {next_decision}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Action buttons (below card)
                b1, b2 = st.columns(2, gap="small")
                with b1:
                    if st.button(
                        "開く →",
                        key=f"open_{proj['id']}",
                        type="primary" if not is_active else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state.client_id = proj["id"]
                        st.session_state.client_name = proj["name"]
                        st.session_state.messages = []
                        st.switch_page("pages/01_project_workspace.py")
                with b2:
                    if st.button("編集", key=f"edit_{proj['id']}", use_container_width=True):
                        st.session_state.editing_project = proj["id"]
                        st.rerun()

        # Fill remaining columns in last row
        remaining = COLS - len(row)
        if remaining > 0:
            for _ in range(remaining):
                pass

    # Edit project modal
    if st.session_state.get("editing_project"):
        from core.supabase_client import get_supabase_client
        target = next((p for p in projects if p["id"] == st.session_state.editing_project), None)
        if target:
            with st.expander(f"編集: {target['name']}", expanded=True):
                with st.form("edit_project_form"):
                    e1, e2, e3 = st.columns(3)
                    with e1:
                        e_name = st.text_input("プロジェクト名", value=target.get("name", ""))
                    with e2:
                        e_ind = st.text_input("業種", value=target.get("industry", ""))
                    with e3:
                        e_loc = st.text_input("所在地", value=target.get("location", ""))
                    ec1, ec2, _ = st.columns([1, 1, 2])
                    with ec1:
                        if st.form_submit_button("保存", type="primary", use_container_width=True):
                            sb = get_supabase_client()
                            sb.table("clients").update({
                                "name": e_name,
                                "industry": e_ind,
                                "location": e_loc,
                            }).eq("id", target["id"]).execute()
                            st.session_state.editing_project = None
                            st.rerun()
                    with ec2:
                        if st.form_submit_button("閉じる", use_container_width=True):
                            st.session_state.editing_project = None
                            st.rerun()


# ------------------------------------------------------------------ #
#  Entry
# ------------------------------------------------------------------ #
if not check_auth():
    _login_page()
else:
    _project_hub()
