"""
05_internal_survey_items.py — STEP 5-6: 内部環境分析ワークスペース
コンサルタント向け仮説検証型内部分析 (STEP 0-15)
"""
import json
import streamlit as st
from core.auth import check_auth
from core.style_utils import load_custom_css

st.set_page_config(
    page_title="内部環境分析 — Consulting OS",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_custom_css()

# ------------------------------------------------------------------ #
#  定数
# ------------------------------------------------------------------ #

_PURPOSES = [
    "中期経営計画", "経営改善計画", "資金調達支援", "設備投資判断",
    "事業承継", "補助金計画", "赤字改善", "資金繰り改善",
    "成長戦略", "再生支援", "その他",
]
_PHASES   = ["初期診断", "現状分析", "戦略策定前", "数値計画作成前", "実行管理", "モニタリング"]
_DEPTHS   = ["スピード診断", "標準分析", "詳細分析（計画書作成用）"]

_SOURCES = {
    "hearing":              "ヒアリング",
    "document":             "既存資料",
    "financial_analysis":   "財務分析結果",
    "external_analysis":    "外部環境分析結果",
    "sales_data":           "売上データ",
    "site_visit":           "現場確認",
    "consultant_observation": "コンサルタント観察",
    "ai_hypothesis":        "AI仮説",
    "unknown":              "不明",
}
_CONFIDENCES = {"high": "高（資料/複数確認済）", "medium": "中（ヒアリング）",
                "low": "低（推定・仮説）", "unknown": "不明"}
_STATUSES    = {"confirmed": "確認済", "unconfirmed": "未確認",
                "needs_review": "要確認", "provisional": "暫定"}
_CLASSIFICATIONS = {
    "strength":            "💪 強み",
    "weakness":            "⚠️ 弱み",
    "unused_asset":        "💎 未活用資産",
    "strategic_constraint":"🚧 戦略制約",
    "unclassified":        "未分類",
}
_SWOT_CANDIDATES = {"S": "S（強み）", "W": "W（弱み）", "neither": "接続なし"}

_DOMAINS = {
    "organization":    "🏢 組織・人事",
    "capability":      "🎓 技能・ノウハウ・承継",
    "marketing":       "📣 営業・マーケティング・顧客接点",
    "product":         "📦 商品・サービス・提供価値",
    "operation":       "⚙️ オペレーション・生産性",
    "cost_mgmt":       "💰 原価管理・採算管理・資金管理",
    "it":              "💻 IT・情報管理・業務管理",
    "customer_asset":  "🤝 顧客資産・施工履歴・信用資産",
}

_Q_CATEGORIES = {
    "opportunity_fit":            "外部機会を取りに行けるか",
    "threat_resilience":          "外部脅威を受けにくいか",
    "financial_cause":            "財務課題の原因",
    "sales_structure":            "売上構造の分解",
    "strength_to_profit_cashflow":"強みが利益/CFに転換されているか",
    "execution_capacity":         "戦略実行体制",
    "falsification":              "仮説の反証",
    "document_request":           "資料依頼",
}

_Q_PRIORITY_COLORS = {
    "high":   ("#fee2e2", "#dc2626", "最重要"),
    "medium": ("#fef3c7", "#d97706", "重要"),
    "low":    ("#f3f4f6", "#6b7280", "参考"),
}

_DOC_TYPES = [
    "ヒアリングメモ", "組織図", "役割分担表", "業務フロー", "売上台帳",
    "顧客台帳", "案件台帳", "工事台帳", "施工履歴", "見積書",
    "原価管理表", "資金繰り表", "HP・SNS・GBP情報", "営業資料",
    "提案資料", "写真・施工事例", "口コミ・レビュー", "業務管理ツール", "その他",
]

_ADOPTION_OPTS = {
    "adopted":       "✅ 採用",
    "reference_only":"👁 参考",
    "pending":       "⏳ 保留",
    "rejected":      "❌ 不採用",
}

# ------------------------------------------------------------------ #
#  DB ヘルパー
# ------------------------------------------------------------------ #

def _sb():
    from core.supabase_client import get_supabase_client
    return get_supabase_client()


def _load_notes(client_id: str) -> dict:
    try:
        res = _sb().table("clients").select("notes").eq("id", client_id).single().execute()
        raw = res.data.get("notes") or "{}"
        return json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        return {}


def _load_sessions(client_id: str) -> list:
    try:
        res = _sb().table("internal_sessions").select(
            "id, session_name, purpose, phase, status, created_at"
        ).eq("client_id", client_id).eq("status", "active").order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []


def _load_session(session_id: str) -> dict:
    try:
        res = _sb().table("internal_sessions").select("*").eq("id", session_id).single().execute()
        return res.data or {}
    except Exception:
        return {}


def _create_session(client_id: str, data: dict) -> str | None:
    try:
        res = _sb().table("internal_sessions").insert({**data, "client_id": client_id}).execute()
        return res.data[0]["id"] if res.data else None
    except Exception as e:
        st.error(f"セッション作成エラー: {e}")
        return None


def _update_session(session_id: str, data: dict):
    try:
        _sb().table("internal_sessions").update(data).eq("id", session_id).execute()
    except Exception as e:
        st.error(f"更新エラー: {e}")


def _load_items(session_id: str) -> list:
    try:
        res = _sb().table("internal_findings_items").select("*") \
            .eq("session_id", session_id).order("created_at").execute()
        return res.data or []
    except Exception:
        return []


def _load_items_by_domain(session_id: str, domain: str) -> list:
    try:
        res = _sb().table("internal_findings_items").select("*") \
            .eq("session_id", session_id).eq("domain", domain).order("created_at").execute()
        return res.data or []
    except Exception:
        return []


def _add_item(session_id: str, client_id: str, data: dict) -> bool:
    try:
        _sb().table("internal_findings_items").insert(
            {**data, "session_id": session_id, "client_id": client_id}
        ).execute()
        return True
    except Exception as e:
        st.error(f"追加エラー: {e}")
        return False


def _update_item(item_id: str, data: dict):
    try:
        _sb().table("internal_findings_items").update(data).eq("id", item_id).execute()
    except Exception as e:
        st.error(f"更新エラー: {e}")


def _delete_item(item_id: str):
    try:
        _sb().table("internal_findings_items").delete().eq("id", item_id).execute()
    except Exception as e:
        st.error(f"削除エラー: {e}")


# ------------------------------------------------------------------ #
#  UI パーツ
# ------------------------------------------------------------------ #

def _conf_badge(conf: str) -> str:
    colors = {
        "high":    ("#dcfce7", "#15803d"),
        "medium":  ("#fef3c7", "#b45309"),
        "low":     ("#fee2e2", "#b91c1c"),
        "unknown": ("#f3f4f6", "#6b7280"),
    }
    bg, fg = colors.get(conf, colors["unknown"])
    label = {"high": "高", "medium": "中", "low": "低", "unknown": "不明"}.get(conf, conf)
    return (f'<span style="background:{bg};color:{fg};font-size:0.68rem;'
            f'font-weight:700;padding:1px 7px;border-radius:999px;">{label}</span>')


def _class_badge(cls: str) -> str:
    colors = {
        "strength":             ("#dcfce7", "#15803d"),
        "weakness":             ("#fee2e2", "#b91c1c"),
        "unused_asset":         ("#f3e8ff", "#7c3aed"),
        "strategic_constraint": ("#fef3c7", "#b45309"),
        "unclassified":         ("#f3f4f6", "#6b7280"),
    }
    bg, fg = colors.get(cls, colors["unclassified"])
    label = _CLASSIFICATIONS.get(cls, cls)
    return (f'<span style="background:{bg};color:{fg};font-size:0.68rem;'
            f'font-weight:700;padding:2px 8px;border-radius:999px;">{label}</span>')


# ------------------------------------------------------------------ #
#  STEP 0: セッション設定
# ------------------------------------------------------------------ #

def render_step0(client_id: str, client_name: str):
    st.subheader("STEP 0: 内部環境分析の目的設定")
    st.caption("分析セッションを作成します。外部環境分析・財務分析との接続が前提です。")

    sessions = _load_sessions(client_id)
    sess_map = {s["id"]: f"{s['session_name']} ({s.get('purpose','')}) — {s['created_at'][:10]}"
                for s in sessions}

    col_sel, col_new = st.columns([3, 1])
    with col_sel:
        if sess_map:
            selected_id = st.selectbox("既存セッションを選択", list(sess_map.keys()),
                                       format_func=lambda x: sess_map[x], key="int_sess_sel")
            if st.button("このセッションを開く", key="int_open_sess"):
                st.session_state["int_session_id"] = selected_id
                st.success("セッションを読み込みました。")
                st.rerun()
        else:
            st.info("セッションがありません。「新規セッション作成」から始めてください。")
    with col_new:
        if st.button("➕ 新規作成", type="primary", use_container_width=True):
            st.session_state["int_creating"] = True

    st.divider()

    if st.session_state.get("int_creating"):
        st.markdown("#### 新規セッション")
        with st.form("int_new_sess"):
            c1, c2 = st.columns(2)
            with c1:
                sname   = st.text_input("案件名 *", placeholder="例: 2025年度 経営改善計画")
                purpose = st.selectbox("支援目的 *", _PURPOSES)
                phase   = st.selectbox("分析フェーズ", _PHASES)
                depth   = st.selectbox("分析深度", _DEPTHS)
            with c2:
                consultant = st.text_input("担当コンサルタント")
                hypo = st.text_area(
                    "今回検証したい戦略仮説",
                    height=100,
                    placeholder="例: 外構工事の直受け比率を高めることで粗利率を5pt改善できる",
                )
            submitted = st.form_submit_button("✅ セッション作成", type="primary")
            if submitted:
                if not sname:
                    st.error("案件名を入力してください。")
                else:
                    new_id = _create_session(client_id, {
                        "session_name":       sname,
                        "purpose":            purpose,
                        "phase":              phase,
                        "analysis_depth":     depth,
                        "consultant_name":    consultant,
                        "strategy_hypotheses": hypo,
                    })
                    if new_id:
                        st.session_state["int_session_id"] = new_id
                        st.session_state["int_creating"] = False
                        st.success(f"✅ セッション「{sname}」を作成しました。")
                        st.rerun()

    sid = st.session_state.get("int_session_id")
    if sid:
        sess = _load_session(sid)
        if sess:
            m1, m2, m3 = st.columns(3)
            m1.metric("案件名", sess.get("session_name", "—"))
            m2.metric("支援目的", sess.get("purpose", "—"))
            m3.metric("フェーズ", sess.get("phase", "—"))
            if sess.get("strategy_hypotheses"):
                st.info(f"**検証仮説:** {sess['strategy_hypotheses']}")


# ------------------------------------------------------------------ #
#  STEP 1: 外部/財務分析 読み込み
# ------------------------------------------------------------------ #

def render_step1(session_id: str, client_id: str):
    st.subheader("STEP 1: 外部環境分析・財務分析結果の読み込み")
    st.caption("clients.notes から外部環境/財務分析の結果を読み込み、内部分析の焦点を確認します。")

    notes   = _load_notes(client_id)
    ext_env = notes.get("external_env") or notes.get("external_environment") or {}
    fin_sum = notes.get("financial_summary") or {}

    has_ext = bool(ext_env)
    has_fin = bool(fin_sum)

    c1, c2 = st.columns(2)
    c1.metric("外部環境分析", "✅ 読み込み済み" if has_ext else "⚠️ 未完了", delta=None)
    c2.metric("財務分析",     "✅ 読み込み済み" if has_fin else "⚠️ 未完了", delta=None)

    if not has_ext:
        st.warning("外部環境分析（STEP 2-3）のデータが見つかりません。外部環境調査ページで「🔍 外部環境を戦略的に分析」を実行してから戻ってください。")
    if not has_fin:
        st.warning("財務分析（STEP 4）のデータが見つかりません。財務分析ワークスペースでデータを入力してください。")

    if has_ext:
        with st.expander("📊 外部環境分析サマリー", expanded=True):
            macro = ext_env.get("macro_summary", {})
            if isinstance(macro, dict):
                essence = macro.get("essence_of_environment", "")
                if essence:
                    st.markdown(
                        f'<div style="background:linear-gradient(135deg,#ede9fe,#dbeafe);'
                        f'border-left:5px solid #6366f1;border-radius:10px;'
                        f'padding:14px 18px;font-size:1.05rem;font-weight:700;color:#1e1b4b;">'
                        f'"{essence}"</div>',
                        unsafe_allow_html=True,
                    )
                tw = macro.get("tailwinds", [])
                hw = macro.get("headwinds", [])
                if tw or hw:
                    col_t, col_h = st.columns(2)
                    with col_t:
                        st.markdown("**追い風**")
                        for t in tw[:3]:
                            st.markdown(f"✅ {t}")
                    with col_h:
                        st.markdown("**向かい風**")
                        for h in hw[:3]:
                            st.markdown(f"⚠️ {h}")
            elif isinstance(macro, str):
                st.markdown(macro)

    if has_fin:
        with st.expander("💹 財務分析サマリー", expanded=True):
            if isinstance(fin_sum, dict):
                for k, v in list(fin_sum.items())[:8]:
                    st.markdown(f"- **{k}**: {v}")
            else:
                st.markdown(str(fin_sum))

    # セッションにサマリーを保存（AI質問生成に使う）
    if has_ext or has_fin:
        ext_summary = json.dumps(ext_env, ensure_ascii=False)[:1000] if has_ext else ""
        fin_summary = json.dumps(fin_sum, ensure_ascii=False)[:1000] if has_fin else ""
        sess = _load_session(session_id)
        if (sess.get("external_analysis_summary") != ext_summary or
                sess.get("financial_analysis_summary") != fin_summary):
            _update_session(session_id, {
                "external_analysis_summary": ext_summary,
                "financial_analysis_summary": fin_summary,
            })


# ------------------------------------------------------------------ #
#  STEP 2: AI質問生成
# ------------------------------------------------------------------ #

def render_step2(session_id: str, client_id: str):
    st.subheader("STEP 2: AI質問生成・仮説検証ヒアリング設計")
    st.caption("外部環境/財務分析の発見事項を踏まえ、仮説検証型のヒアリング質問をAIが生成します。")

    sess  = _load_session(session_id)
    notes = _load_notes(client_id)

    questions = sess.get("ai_questions") or []
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except Exception:
            questions = []

    # 生成ボタン
    col_gen, col_info = st.columns([1, 3])
    with col_gen:
        if st.button("🤖 質問を生成", type="primary"):
            ext_env = notes.get("external_env") or notes.get("external_environment") or {}
            fin_sum = notes.get("financial_summary") or {}
            try:
                from core.supabase_client import get_supabase_client
                sb = get_supabase_client()
                cl = sb.table("clients").select("name, industry, location").eq("id", client_id).single().execute()
                company_info = cl.data or {}
            except Exception:
                company_info = {}

            with st.spinner("仮説検証質問を生成中（30〜60秒）..."):
                try:
                    from core.pipeline.internal_env_engine import generate_interview_questions
                    result = generate_interview_questions({
                        "company_info":       company_info,
                        "external_analysis":  ext_env,
                        "financial_summary":  fin_sum,
                        "strategy_hypotheses": sess.get("strategy_hypotheses", ""),
                        "purpose":            sess.get("purpose", ""),
                    })
                    _update_session(session_id, {
                        "ai_questions": json.dumps(result, ensure_ascii=False)
                    })
                    st.success(f"✅ {len(result['questions'])}問の質問を生成しました。")
                    st.rerun()
                except Exception as e:
                    st.error(f"生成エラー: {type(e).__name__}: {e}")
    with col_info:
        if not questions:
            st.info("「🤖 質問を生成」を押してください。STEP 1 で外部/財務データを読み込んだ後が最適です。")

    if not questions:
        return

    # 分析サマリー
    if isinstance(questions, dict):
        summary   = questions.get("analysis_summary", "")
        missing   = questions.get("missing_inputs", [])
        q_list    = questions.get("questions", [])
    else:
        summary, missing, q_list = "", [], questions

    if summary:
        st.markdown(
            f'<div style="background:#f0f9ff;border-left:4px solid #0ea5e9;'
            f'border-radius:6px;padding:10px 16px;margin-bottom:1rem;">'
            f'<b>分析の焦点:</b> {summary}</div>',
            unsafe_allow_html=True,
        )

    # 質問フィルター
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        filter_priority = st.selectbox("優先度フィルター", ["すべて", "high", "medium", "low"],
                                       key="q_filter_pri")
    with filter_col2:
        filter_cat = st.selectbox("カテゴリフィルター",
                                  ["すべて"] + list(_Q_CATEGORIES.keys()),
                                  format_func=lambda x: _Q_CATEGORIES.get(x, x) if x != "すべて" else x,
                                  key="q_filter_cat")

    st.markdown(f"**質問リスト: {len(q_list)}問**")

    updated_questions = list(q_list)
    for i, q in enumerate(updated_questions):
        priority = q.get("priority", "medium")
        cat      = q.get("question_category", "")
        if filter_priority != "すべて" and priority != filter_priority:
            continue
        if filter_cat != "すべて" and cat != filter_cat:
            continue

        pri_bg, pri_fg, pri_label = _Q_PRIORITY_COLORS.get(priority, _Q_PRIORITY_COLORS["medium"])
        domain_label = _DOMAINS.get(q.get("domain", ""), q.get("domain", ""))

        with st.expander(
            f"[{pri_label}] {q.get('question','')[:60]}{'...' if len(q.get('question','')) > 60 else ''}",
            expanded=(priority == "high"),
        ):
            st.markdown(
                f'<div style="background:{pri_bg};border-radius:8px;padding:10px 14px;margin-bottom:8px;">'
                f'<b>{q.get("question","")}</b></div>',
                unsafe_allow_html=True,
            )
            detail_col1, detail_col2 = st.columns(2)
            with detail_col1:
                st.markdown(f"**目的:** {q.get('purpose','')}")
                st.markdown(f"**紐づく発見:** {q.get('linked_finding','')}")
                st.markdown(f"**検証仮説:** {q.get('hypothesis_to_test','')}")
                st.markdown(f"**対象者:** {q.get('target_person','')}")
            with detail_col2:
                st.markdown(f"**期待するエビデンス:** {q.get('expected_evidence','')}")
                if q.get("follow_up_if_yes"):
                    st.markdown(f"**YESの場合:** {q['follow_up_if_yes']}")
                if q.get("follow_up_if_no"):
                    st.markdown(f"**NOの場合:** {q['follow_up_if_no']}")
                if q.get("required_data"):
                    st.markdown(f"**追加データ:** {q['required_data']}")

            st.markdown(
                f'<span style="font-size:0.72rem;color:#6b7280;">'
                f'カテゴリ: {_Q_CATEGORIES.get(cat,cat)} | ドメイン: {domain_label}</span>',
                unsafe_allow_html=True,
            )

            # 採用可否
            adopt_opts = list(_ADOPTION_OPTS.keys())
            current_adopt = q.get("adoption_status", "pending")
            new_adopt = st.radio(
                "採用可否",
                adopt_opts,
                index=adopt_opts.index(current_adopt) if current_adopt in adopt_opts else 2,
                format_func=lambda x: _ADOPTION_OPTS[x],
                horizontal=True,
                key=f"q_adopt_{i}",
            )
            if new_adopt != current_adopt:
                updated_questions[i] = {**q, "adoption_status": new_adopt}
                qs_data = {"questions": updated_questions, "missing_inputs": missing,
                           "analysis_summary": summary}
                _update_session(session_id, {"ai_questions": json.dumps(qs_data, ensure_ascii=False)})

    # 不足データ
    if missing:
        with st.expander(f"⚠️ 不足データ ({len(missing)}件)"):
            for m in missing:
                pri_bg, pri_fg, _ = _Q_PRIORITY_COLORS.get(m.get("priority","medium"), _Q_PRIORITY_COLORS["medium"])
                st.markdown(
                    f'<div style="background:{pri_bg};border-radius:6px;padding:8px 12px;margin-bottom:6px;">'
                    f'<b>{m.get("data_name","")}</b> — {m.get("reason","")}<br>'
                    f'<span style="font-size:0.75rem;color:#6b7280;">'
                    f'収集方法: {m.get("collection_method","")} | 分析への影響: {m.get("impact_on_analysis","")}'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )


# ------------------------------------------------------------------ #
#  STEP 3: 資料登録
# ------------------------------------------------------------------ #

def render_step3(session_id: str):
    st.subheader("STEP 3: 資料・ヒアリングソース登録")

    sess = _load_session(session_id)
    docs = sess.get("documents") or []
    if isinstance(docs, str):
        try:
            docs = json.loads(docs)
        except Exception:
            docs = []

    with st.expander("➕ 資料を追加", expanded=not docs):
        with st.form("int_doc_form"):
            c1, c2 = st.columns(2)
            with c1:
                dname = st.text_input("資料名称 *", placeholder="例: 2025年1月 ヒアリングメモ")
                dtype = st.selectbox("資料種別", _DOC_TYPES)
                period = st.text_input("対象期間")
            with c2:
                src  = st.selectbox("情報源", list(_SOURCES.keys()), format_func=lambda x: _SOURCES[x])
                conf = st.selectbox("信頼度", list(_CONFIDENCES.keys()), format_func=lambda x: _CONFIDENCES[x])
                use_flag = st.checkbox("分析に使用する", value=True)
                note = st.text_area("メモ", height=60)
            if st.form_submit_button("📎 追加", type="primary"):
                if dname:
                    docs.append({"document_name": dname, "document_type": dtype,
                                 "target_period": period, "source": src,
                                 "confidence": conf, "use_in_analysis": use_flag, "note": note})
                    _update_session(session_id, {"documents": json.dumps(docs, ensure_ascii=False)})
                    st.success(f"「{dname}」を登録しました。")
                    st.rerun()

    if docs:
        st.markdown(f"**登録済み資料: {len(docs)}件**")
        for i, doc in enumerate(docs):
            col_d, col_del = st.columns([8, 1])
            with col_d:
                st.markdown(
                    f'<div style="border:1px solid #e5e7eb;border-radius:8px;padding:8px 14px;margin-bottom:4px;">'
                    f'<b>{doc.get("document_name","")}</b> — {doc.get("document_type","")}'
                    f' {_conf_badge(doc.get("confidence","unknown"))}<br>'
                    f'<span style="font-size:0.75rem;color:#9ca3af;">'
                    f'期間: {doc.get("target_period","—")} | 情報源: {_SOURCES.get(doc.get("source",""),"不明")}'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("🗑", key=f"int_del_doc_{i}"):
                    docs.pop(i)
                    _update_session(session_id, {"documents": json.dumps(docs, ensure_ascii=False)})
                    st.rerun()


# ------------------------------------------------------------------ #
#  STEP 4-11: 8ドメイン発見事項入力ワークスペース
# ------------------------------------------------------------------ #

def render_domain_workspace(session_id: str, client_id: str):
    st.subheader("STEP 4-11: 8ドメイン発見事項入力ワークスペース")
    st.caption("各ドメインの発見事項を登録します。分類（強み/弱み/未活用資産/戦略制約）はSTEP 12でも変更できます。")

    domain_tabs = st.tabs(list(_DOMAINS.values()))

    for tab, (domain_key, domain_label) in zip(domain_tabs, _DOMAINS.items()):
        with tab:
            items = _load_items_by_domain(session_id, domain_key)
            st.markdown(f"**{domain_label} — 登録済み発見事項: {len(items)}件**")

            # 追加フォーム
            with st.expander("➕ 発見事項を追加", expanded=not items):
                with st.form(f"add_item_{domain_key}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        iname = st.text_input("発見事項名 *",
                                              placeholder="例: 後継者への見積判断未移管")
                        desc  = st.text_area("詳細・説明", height=80,
                                             placeholder="具体的な内容・事実を記述")
                        cls   = st.selectbox("分類", list(_CLASSIFICATIONS.keys()),
                                             format_func=lambda x: _CLASSIFICATIONS[x])
                    with c2:
                        src   = st.selectbox("情報源", list(_SOURCES.keys()),
                                             format_func=lambda x: _SOURCES[x],
                                             key=f"src_{domain_key}")
                        conf  = st.selectbox("信頼度", list(_CONFIDENCES.keys()),
                                             format_func=lambda x: _CONFIDENCES[x],
                                             key=f"conf_{domain_key}")
                        stat  = st.selectbox("確認状態", list(_STATUSES.keys()),
                                             format_func=lambda x: _STATUSES[x],
                                             key=f"stat_{domain_key}")
                        swot  = st.selectbox("SWOTへの接続", list(_SWOT_CANDIDATES.keys()),
                                             format_func=lambda x: _SWOT_CANDIDATES[x],
                                             key=f"swot_{domain_key}")
                    evidence = st.text_area("根拠・エビデンス", height=60,
                                            placeholder="ヒアリング内容、資料名、データ等")
                    c3, c4 = st.columns(2)
                    with c3:
                        imp_profit = st.selectbox("利益への影響",
                                                  ["high","medium","low","unknown"],
                                                  format_func=lambda x: {"high":"大","medium":"中","low":"小","unknown":"不明"}[x],
                                                  key=f"profit_{domain_key}")
                    with c4:
                        imp_strat = st.text_input("戦略への意味",
                                                  placeholder="例: 成長機会を取れない制約になっている")
                    note = st.text_input("メモ", placeholder="補足")

                    if st.form_submit_button(f"✅ 追加", type="primary"):
                        if iname:
                            ok = _add_item(session_id, client_id, {
                                "domain":          domain_key,
                                "item_name":       iname,
                                "description":     desc,
                                "classification":  cls,
                                "source":          src,
                                "confidence":      conf,
                                "status":          stat,
                                "swot_candidate":  swot,
                                "evidence":        evidence,
                                "impact_on_profit": imp_profit,
                                "impact_on_strategy": imp_strat,
                                "note":            note,
                                "adoption_status": "pending",
                            })
                            if ok:
                                st.rerun()

            # 既存アイテム一覧
            for item in items:
                cls = item.get("classification", "unclassified")
                conf = item.get("confidence", "unknown")
                col_item, col_edit = st.columns([7, 1])
                with col_item:
                    st.markdown(
                        f'<div style="border:1px solid #e5e7eb;border-radius:8px;'
                        f'padding:8px 14px;margin-bottom:6px;">'
                        f'{_class_badge(cls)} {_conf_badge(conf)}'
                        f'&nbsp;<b>{item.get("item_name","")}</b><br>'
                        f'<span style="font-size:0.8rem;color:#374151;">'
                        f'{item.get("description","")}</span><br>'
                        f'<span style="font-size:0.72rem;color:#9ca3af;">'
                        f'情報源: {_SOURCES.get(item.get("source",""),"不明")} | '
                        f'状態: {_STATUSES.get(item.get("status",""),"不明")} | '
                        f'SWOT: {_SWOT_CANDIDATES.get(item.get("swot_candidate","neither"),"")}'
                        f'</span></div>',
                        unsafe_allow_html=True,
                    )
                with col_edit:
                    if st.button("🗑", key=f"del_item_{item['id']}"):
                        _delete_item(item["id"])
                        st.rerun()

                # 分類変更
                with st.expander(f"✏️ 分類変更: {item.get('item_name','')}", expanded=False):
                    new_cls = st.selectbox(
                        "分類",
                        list(_CLASSIFICATIONS.keys()),
                        index=list(_CLASSIFICATIONS.keys()).index(cls) if cls in _CLASSIFICATIONS else 4,
                        format_func=lambda x: _CLASSIFICATIONS[x],
                        key=f"cls_change_{item['id']}",
                    )
                    new_adopt = st.selectbox(
                        "採用可否",
                        list(_ADOPTION_OPTS.keys()),
                        index=list(_ADOPTION_OPTS.keys()).index(item.get("adoption_status","pending")),
                        format_func=lambda x: _ADOPTION_OPTS[x],
                        key=f"adopt_change_{item['id']}",
                    )
                    if st.button("保存", key=f"save_cls_{item['id']}"):
                        _update_item(item["id"], {"classification": new_cls, "adoption_status": new_adopt})
                        st.rerun()


# ------------------------------------------------------------------ #
#  STEP 12: 4分類構造整理
# ------------------------------------------------------------------ #

def render_step12(session_id: str):
    st.subheader("STEP 12: 内部環境の構造整理")
    st.caption("登録済みの発見事項を4分類で整理します。SWOT接続候補も確認できます。")

    all_items = _load_items(session_id)
    if not all_items:
        st.info("STEP 4-11 で発見事項を登録してください。")
        return

    for cls_key, cls_label in _CLASSIFICATIONS.items():
        if cls_key == "unclassified":
            continue
        items_in_cls = [i for i in all_items if i.get("classification") == cls_key]
        if not items_in_cls:
            continue

        colors = {
            "strength":             "#dcfce7",
            "weakness":             "#fee2e2",
            "unused_asset":         "#f3e8ff",
            "strategic_constraint": "#fef3c7",
        }
        bg = colors.get(cls_key, "#f9fafb")

        st.markdown(
            f'<div style="background:{bg};border-radius:10px;padding:8px 14px;'
            f'margin-bottom:4px;font-weight:700;">{cls_label} — {len(items_in_cls)}件</div>',
            unsafe_allow_html=True,
        )
        for item in items_in_cls:
            adopt = item.get("adoption_status", "pending")
            swot  = _SWOT_CANDIDATES.get(item.get("swot_candidate","neither"),"")
            conf  = item.get("confidence","unknown")
            st.markdown(
                f'<div style="border-left:3px solid #e5e7eb;padding:6px 14px;margin:2px 0 4px 8px;">'
                f'{_conf_badge(conf)}&nbsp;'
                f'<b>{item.get("item_name","")}</b>'
                f'<span style="font-size:0.72rem;color:#9ca3af;"> | {swot} | '
                f'{_ADOPTION_OPTS.get(adopt,adopt)}</span><br>'
                f'<span style="font-size:0.78rem;color:#374151;">{item.get("description","")}</span><br>'
                f'<span style="font-size:0.72rem;color:#6b7280;">'
                f'ドメイン: {_DOMAINS.get(item.get("domain",""),"")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    unclassified = [i for i in all_items if i.get("classification", "unclassified") == "unclassified"]
    if unclassified:
        st.warning(f"⚠️ 未分類の発見事項: {len(unclassified)}件（STEP 4-11 で分類してください）")


# ------------------------------------------------------------------ #
#  STEP 15: SWOT・パイプライン接続
# ------------------------------------------------------------------ #

def render_step15(session_id: str, client_id: str):
    st.subheader("STEP 15: SWOT・クロスSWOT・重点施策への接続")
    st.caption("採用済みの発見事項を clients.notes['internal_findings'] に書き込み、SWOT・戦略設計と接続します。")

    all_items = _load_items(session_id)
    adopted   = [i for i in all_items if i.get("adoption_status") == "adopted"]
    strengths  = [i for i in adopted if i.get("classification") == "strength"]
    weaknesses = [i for i in adopted if i.get("classification") == "weakness"]
    unused     = [i for i in adopted if i.get("classification") == "unused_asset"]
    constraints = [i for i in adopted if i.get("classification") == "strategic_constraint"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💪 強み（採用）",   len(strengths))
    m2.metric("⚠️ 弱み（採用）",   len(weaknesses))
    m3.metric("💎 未活用資産",      len(unused))
    m4.metric("🚧 戦略制約",        len(constraints))

    if not adopted:
        st.warning("採用済みの発見事項がありません。STEP 4-11 で各アイテムの採用可否を「✅ 採用」に設定してください。")
        return

    st.markdown("---")
    st.markdown("**SWOT接続対象（採用済みのみ）**")

    def _items_to_list(items: list) -> list:
        return [{"item": i.get("item_name",""), "description": i.get("description",""),
                 "evidence": i.get("evidence",""), "confidence": i.get("confidence","unknown"),
                 "domain": i.get("domain",""), "impact_on_strategy": i.get("impact_on_strategy","")}
                for i in items]

    internal_findings = {
        "strengths":            _items_to_list(strengths),
        "weaknesses":           _items_to_list(weaknesses),
        "unused_assets":        _items_to_list(unused),
        "strategic_constraints": _items_to_list(constraints),
        "session_id":           session_id,
        "total_items":          len(adopted),
    }

    with st.expander("📋 書き込み内容プレビュー"):
        st.json(internal_findings)

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("🔗 パイプラインに接続（STEP 5・6 完了）", type="primary", use_container_width=True):
            try:
                notes = _load_notes(client_id)
                notes["internal_findings"] = internal_findings
                steps = notes.get("pipeline_steps", {})
                steps["5"] = "done"
                steps["6"] = "done"
                notes["pipeline_steps"] = steps
                _sb().table("clients").update({
                    "notes": json.dumps(notes, ensure_ascii=False)
                }).eq("id", client_id).execute()
                st.session_state[f"pipeline_{client_id}"] = steps
                st.success("✅ internal_findings を保存しました。STEP 5・6 完了。SWOT分析・戦略設計に自動連携されます。")
                st.balloons()
            except Exception as e:
                st.error(f"保存エラー: {e}")


# ------------------------------------------------------------------ #
#  サイドバーナビゲーション
# ------------------------------------------------------------------ #

_STEPS = {
    0:  "⚙️ 目的設定",
    1:  "📥 外部/財務データ読み込み",
    2:  "🤖 AI質問生成",
    3:  "📎 資料登録",
    4:  "🏢 組織・人事",
    5:  "🎓 技能・ノウハウ・承継",
    6:  "📣 営業・マーケティング",
    7:  "📦 商品・サービス",
    8:  "⚙️ オペレーション",
    9:  "💰 原価・採算・資金管理",
    10: "💻 IT・情報管理",
    11: "🤝 顧客資産・信用資産",
    12: "🗂 構造整理（4分類）",
    13: "🤖 AI分析実行",
    14: "✅ AI結果レビュー",
    15: "🔗 SWOT・パイプライン接続",
}
_DOMAIN_STEPS = set(range(4, 12))


def render_sidebar_nav():
    st.sidebar.markdown("### 内部環境分析 ステップ")
    current = st.session_state.get("int_step", 0)
    selected = st.sidebar.radio(
        "ステップ選択",
        list(_STEPS.keys()),
        format_func=lambda x: _STEPS[x] + ("" if x not in {13, 14} else " 🔜"),
        index=current,
        key="int_step_radio",
        label_visibility="collapsed",
    )
    st.session_state["int_step"] = selected

    sid = st.session_state.get("int_session_id")
    if sid:
        st.sidebar.markdown("---")
        st.sidebar.caption(f"セッション: `{sid[:8]}...`")
        if st.sidebar.button("🔄 セッション変更"):
            st.session_state.pop("int_session_id", None)
            st.session_state["int_step"] = 0
            st.rerun()
    return selected


# ------------------------------------------------------------------ #
#  Main
# ------------------------------------------------------------------ #

def main():
    from core.sidebar import render_sidebar
    render_sidebar()

    if not check_auth():
        st.warning("ログインが必要です。")
        return

    client_id   = st.session_state.get("client_id")
    client_name = st.session_state.get("client_name", "プロジェクト")

    if not client_id:
        st.warning("⚠️ プロジェクトを選択してください。")
        if st.button("← プロジェクト一覧へ"):
            st.switch_page("app.py")
        return

    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
        <div style="background:#f3e8ff;color:#7c3aed;font-size:0.72rem;font-weight:700;
                    padding:3px 10px;border-radius:999px;">STEP 5-6</div>
        <div style="font-size:0.8rem;color:#9ca3af;">内部環境分析フェーズ</div>
    </div>
    """, unsafe_allow_html=True)

    st.title("🔍 内部環境分析ワークスペース")
    st.markdown(f"**{client_name}** — 仮説検証型内部分析")

    step = render_sidebar_nav()
    session_id = st.session_state.get("int_session_id")
    st.divider()

    if step == 0:
        render_step0(client_id, client_name)
        return

    if not session_id:
        st.warning("⚠️ まず **STEP 0** でセッションを作成または選択してください。")
        if st.button("← STEP 0 へ"):
            st.session_state["int_step"] = 0
            st.rerun()
        return

    if step == 1:
        render_step1(session_id, client_id)
    elif step == 2:
        render_step2(session_id, client_id)
    elif step == 3:
        render_step3(session_id)
    elif step in _DOMAIN_STEPS:
        render_domain_workspace(session_id, client_id)
    elif step == 12:
        render_step12(session_id)
    elif step in (13, 14):
        st.subheader(_STEPS[step])
        st.info("🚧 このステップは現在実装中です。")
    elif step == 15:
        render_step15(session_id, client_id)


main()
