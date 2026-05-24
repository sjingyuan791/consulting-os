"""
11_phase2_roa.py — STEP 4: 財務分析ワークスペース
コンサルタント向け多年度財務分析 (STEP 0-3 実装済み、STEP 4-11 準備中)
"""
import json
import streamlit as st
from core.auth import check_auth
from core.style_utils import load_custom_css

st.set_page_config(
    page_title="財務分析 — Consulting OS",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_custom_css()

# ------------------------------------------------------------------ #
#  定数定義
# ------------------------------------------------------------------ #

_PURPOSES = [
    "中期経営計画", "経営改善計画", "資金調達支援", "設備投資判断",
    "事業承継", "補助金計画", "赤字改善", "資金繰り改善",
    "成長戦略", "再生支援", "その他",
]
_PHASES = ["初期診断", "現状分析", "戦略策定前", "数値計画作成前", "実行管理", "モニタリング"]
_OUTPUT_PURPOSES = ["Word計画書", "PowerPoint", "社長説明", "金融機関説明", "内部検討", "支援機関報告", "その他"]
_DEPTHS = ["スピード診断", "標準分析", "詳細分析（計画書作成用）"]

_SOURCES = {
    "financial_statement": "決算書",
    "tax_return":          "法人税申告書",
    "trial_balance":       "試算表",
    "depreciation_schedule": "減価償却明細",
    "repayment_schedule":  "返済予定表",
    "hearing":             "ヒアリング",
    "sales_register":      "売上台帳",
    "invoice_data":        "請求書データ",
    "construction_ledger": "工事台帳",
    "pos_data":            "POSデータ",
    "accounting_sub_account": "勘定科目内訳書",
    "management_system":   "管理システム",
    "estimate":            "概算・推定",
    "unknown":             "不明",
}
_CONFIDENCES = {"high": "高", "medium": "中", "low": "低", "unknown": "不明"}
_STATUSES    = {"confirmed": "確認済", "unconfirmed": "未確認", "needs_review": "要確認", "provisional": "仮値"}

_DOC_TYPES = [
    "決算書", "法人税申告書", "勘定科目内訳書", "減価償却明細",
    "借入返済予定表", "試算表", "売上台帳", "工事台帳",
    "請求書データ", "資金繰り表", "ヒアリングメモ", "業界平均データ", "その他",
]

_PL_ITEMS = [
    ("revenue",          "売上高"),
    ("cogs",             "売上原価"),
    ("gross_profit",     "売上総利益"),
    ("sga",              "販売費及び一般管理費"),
    ("operating_profit", "営業利益"),
    ("non_op_income",    "営業外収益"),
    ("non_op_expense",   "営業外費用"),
    ("ordinary_profit",  "経常利益"),
    ("special_income",   "特別利益"),
    ("special_loss",     "特別損失"),
    ("pretax_profit",    "税引前当期純利益"),
    ("tax",              "法人税等"),
    ("net_profit",       "当期純利益"),
    ("depreciation",     "減価償却費"),
]

_BS_ITEMS = [
    ("cash",              "現預金"),
    ("receivables",       "売掛金・受取手形"),
    ("inventory",         "棚卸資産"),
    ("current_assets",    "流動資産合計"),
    ("fixed_assets",      "固定資産"),
    ("total_assets",      "資産合計"),
    ("payables",          "買掛金・支払手形"),
    ("current_liabilities","流動負債合計"),
    ("short_term_loans",  "短期借入金"),
    ("long_term_loans",   "長期借入金"),
    ("total_loans",       "借入金合計"),
    ("total_liabilities", "負債合計"),
    ("equity",            "純資産"),
]

_ANOMALY_TAGS = [
    "特別償却あり", "雑収入が大きい", "役員報酬が通常より低い",
    "売掛金が急増", "在庫が急増", "借入金が増加",
    "一時的な売上計上", "保険収入あり", "資産売却益あり",
    "修繕費が大きい", "広告費が異常", "その他",
]

_LOAN_STATUSES = {"confirmed": "確認済", "unconfirmed": "未確認", "needs_review": "要確認"}

_ADJ_CATEGORIES = ["役員報酬", "賞与・退職金", "保険料", "修繕費", "特別損益", "雑収入", "雑損失", "その他"]
_ADJ_DIRECTIONS = {
    "add_back":    "加算（足し戻す）",
    "exclude":     "減算（除外する）",
    "not_adjusted": "補正なし",
}
_ADOPTION_OPTS = {"adopted": "採用", "reference_only": "参考", "pending": "未決定", "rejected": "不採用"}

_SALES_ROUTES = {
    "direct": "直販", "distributor": "代理店", "ec": "EC・通販",
    "retail": "小売", "wholesale": "卸売", "other": "その他",
}
_STRATEGIC_TREATMENTS = {
    "grow": "拡大", "maintain": "維持", "optimize": "最適化",
    "reduce": "縮小検討", "exit": "撤退検討", "unknown": "未決定",
}
_MISSING_PRIORITIES  = {"high": "高", "medium": "中", "low": "低"}
_COLLECTION_METHODS  = {
    "hearing":          "ヒアリング",
    "document_request": "資料依頼",
    "data_processing":  "データ加工",
    "site_visit":       "現地調査",
    "system_export":    "システム出力",
}

# ------------------------------------------------------------------ #
#  DB ヘルパー
# ------------------------------------------------------------------ #

def _sb():
    from core.supabase_client import get_supabase_client
    return get_supabase_client()


def _load_sessions(client_id: str) -> list:
    try:
        res = _sb().table("fin_sessions").select("id, session_name, purpose, phase, status, created_at") \
            .eq("client_id", client_id).eq("status", "active") \
            .order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []


def _load_session(session_id: str) -> dict:
    try:
        res = _sb().table("fin_sessions").select("*").eq("id", session_id).single().execute()
        return res.data or {}
    except Exception:
        return {}


def _save_session(client_id: str, data: dict) -> str | None:
    try:
        res = _sb().table("fin_sessions").insert({**data, "client_id": client_id}).execute()
        return res.data[0]["id"] if res.data else None
    except Exception as e:
        st.error(f"セッション保存エラー: {e}")
        return None


def _update_session(session_id: str, data: dict):
    try:
        _sb().table("fin_sessions").update(data).eq("id", session_id).execute()
    except Exception as e:
        st.error(f"セッション更新エラー: {e}")


def _load_statements(session_id: str) -> list:
    try:
        res = _sb().table("fin_statements").select("*").eq("session_id", session_id) \
            .order("fiscal_year").execute()
        return res.data or []
    except Exception:
        return []


def _upsert_statement(session_id: str, client_id: str, fiscal_year: str, pl: dict, bs: dict, memos: list):
    try:
        _sb().table("fin_statements").upsert({
            "session_id": session_id,
            "client_id":  client_id,
            "fiscal_year": fiscal_year,
            "pl": json.dumps(pl, ensure_ascii=False),
            "bs": json.dumps(bs, ensure_ascii=False),
            "abnormal_memos": json.dumps(memos, ensure_ascii=False),
        }, on_conflict="session_id,fiscal_year").execute()
    except Exception as e:
        st.error(f"決算書保存エラー: {e}")


def _load_loans(session_id: str) -> list:
    try:
        res = _sb().table("fin_loans").select("*").eq("session_id", session_id) \
            .order("created_at").execute()
        return res.data or []
    except Exception:
        return []


def _save_loan(session_id: str, client_id: str, data: dict) -> bool:
    try:
        _sb().table("fin_loans").insert({**data, "session_id": session_id, "client_id": client_id}).execute()
        return True
    except Exception as e:
        st.error(f"借入保存エラー: {e}")
        return False


def _delete_loan(loan_id: str):
    try:
        _sb().table("fin_loans").delete().eq("id", loan_id).execute()
    except Exception as e:
        st.error(f"削除エラー: {e}")


def _load_adjustments(session_id: str, fiscal_year: str | None = None) -> list:
    try:
        q = _sb().table("fin_adjustments").select("*").eq("session_id", session_id)
        if fiscal_year:
            q = q.eq("fiscal_year", fiscal_year)
        return (q.order("created_at").execute()).data or []
    except Exception:
        return []


def _save_adjustment(session_id: str, client_id: str, data: dict) -> bool:
    try:
        _sb().table("fin_adjustments").insert(
            {**data, "session_id": session_id, "client_id": client_id}
        ).execute()
        return True
    except Exception as e:
        st.error(f"補正保存エラー: {e}")
        return False


def _delete_adjustment(adj_id: str):
    try:
        _sb().table("fin_adjustments").delete().eq("id", adj_id).execute()
    except Exception as e:
        st.error(f"削除エラー: {e}")


def _update_adjustment(adj_id: str, data: dict):
    try:
        _sb().table("fin_adjustments").update(data).eq("id", adj_id).execute()
    except Exception as e:
        st.error(f"補正更新エラー: {e}")


def _load_segments(session_id: str, fiscal_year: str | None = None) -> list:
    try:
        q = _sb().table("fin_segments").select("*").eq("session_id", session_id)
        if fiscal_year:
            q = q.eq("fiscal_year", fiscal_year)
        return (q.order("created_at").execute()).data or []
    except Exception:
        return []


def _save_segment(session_id: str, client_id: str, data: dict) -> bool:
    try:
        _sb().table("fin_segments").insert(
            {**data, "session_id": session_id, "client_id": client_id}
        ).execute()
        return True
    except Exception as e:
        st.error(f"セグメント保存エラー: {e}")
        return False


def _delete_segment(seg_id: str):
    try:
        _sb().table("fin_segments").delete().eq("id", seg_id).execute()
    except Exception as e:
        st.error(f"削除エラー: {e}")


def _load_analysis_results(session_id: str) -> list:
    try:
        res = _sb().table("fin_analysis_results").select("*").eq("session_id", session_id) \
            .order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []


def _save_analysis_result(session_id: str, client_id: str, data: dict) -> str | None:
    try:
        res = _sb().table("fin_analysis_results").insert(
            {**data, "session_id": session_id, "client_id": client_id}
        ).execute()
        return res.data[0]["id"] if res.data else None
    except Exception as e:
        st.error(f"AI結果保存エラー: {e}")
        return None


def _update_analysis_result(result_id: str, data: dict):
    try:
        _sb().table("fin_analysis_results").update(data).eq("id", result_id).execute()
    except Exception as e:
        st.error(f"AI結果更新エラー: {e}")


def _load_client_notes(client_id: str) -> dict:
    try:
        res = _sb().table("clients").select("notes").eq("id", client_id).single().execute()
        notes = (res.data or {}).get("notes") or {}
        if isinstance(notes, str):
            notes = json.loads(notes)
        return notes
    except Exception:
        return {}


def _update_client_notes(client_id: str, notes: dict):
    try:
        _sb().table("clients").update(
            {"notes": json.dumps(notes, ensure_ascii=False)}
        ).eq("id", client_id).execute()
    except Exception as e:
        st.error(f"notes更新エラー: {e}")


# ------------------------------------------------------------------ #
#  UI パーツ
# ------------------------------------------------------------------ #

def _field_row(label: str, key_prefix: str, default_val: float = 0.0, default_src: str = "unknown",
               default_conf: str = "unknown", default_status: str = "unconfirmed", default_note: str = "") -> dict:
    """PL/BS 1行分の入力UI（value + source + confidence + status + note）"""
    c_label, c_val, c_src, c_conf, c_stat, c_note = st.columns([2, 1.5, 1.5, 1, 1.2, 2.5])
    with c_label:
        st.markdown(f"<div style='padding-top:8px;font-size:0.82rem;font-weight:600'>{label}</div>",
                    unsafe_allow_html=True)
    with c_val:
        val = st.number_input("金額(百万円)", value=float(default_val), step=0.1,
                              key=f"{key_prefix}_val", label_visibility="collapsed", format="%.1f")
    with c_src:
        src_opts  = list(_SOURCES.keys())
        src_disp  = list(_SOURCES.values())
        src_idx   = src_opts.index(default_src) if default_src in src_opts else src_opts.index("unknown")
        src = st.selectbox("情報源", src_opts, index=src_idx,
                           format_func=lambda x: _SOURCES[x],
                           key=f"{key_prefix}_src", label_visibility="collapsed")
    with c_conf:
        conf_opts = list(_CONFIDENCES.keys())
        conf_idx  = conf_opts.index(default_conf) if default_conf in conf_opts else conf_opts.index("unknown")
        conf = st.selectbox("信頼度", conf_opts, index=conf_idx,
                            format_func=lambda x: _CONFIDENCES[x],
                            key=f"{key_prefix}_conf", label_visibility="collapsed")
    with c_stat:
        stat_opts = list(_STATUSES.keys())
        stat_idx  = stat_opts.index(default_status) if default_status in stat_opts else 0
        status = st.selectbox("状態", stat_opts, index=stat_idx,
                              format_func=lambda x: _STATUSES[x],
                              key=f"{key_prefix}_status", label_visibility="collapsed")
    with c_note:
        note = st.text_input("メモ", value=default_note,
                             key=f"{key_prefix}_note", label_visibility="collapsed",
                             placeholder="補足・根拠メモ")
    return {"value": val, "source": src, "confidence": conf, "status": status, "note": note}


def _field_header():
    c_label, c_val, c_src, c_conf, c_stat, c_note = st.columns([2, 1.5, 1.5, 1, 1.2, 2.5])
    with c_label: st.caption("項目")
    with c_val:   st.caption("金額（百万円）")
    with c_src:   st.caption("情報源")
    with c_conf:  st.caption("信頼度")
    with c_stat:  st.caption("確認状態")
    with c_note:  st.caption("メモ")


def _confidence_badge(conf: str) -> str:
    colors = {"high": ("#dcfce7","#15803d"), "medium": ("#fef3c7","#b45309"),
              "low": ("#fee2e2","#b91c1c"), "unknown": ("#f3f4f6","#6b7280")}
    bg, fg = colors.get(conf, colors["unknown"])
    label  = _CONFIDENCES.get(conf, conf)
    return (f'<span style="background:{bg};color:{fg};font-size:0.68rem;'
            f'font-weight:700;padding:1px 7px;border-radius:999px;">{label}</span>')


# ------------------------------------------------------------------ #
#  STEP 0: セッション設定
# ------------------------------------------------------------------ #

def render_step0(client_id: str, client_name: str):
    st.subheader("STEP 0: 案件・分析目的設定")
    st.caption("分析セッションを作成・管理します。1クライアントに複数セッションを持てます。")

    sessions = _load_sessions(client_id)

    # セッション選択
    sess_options = {s["id"]: f"{s['session_name']} ({s.get('purpose','')}) — {s['created_at'][:10]}"
                   for s in sessions}

    col_sel, col_new = st.columns([3, 1])
    with col_sel:
        if sess_options:
            selected_id = st.selectbox(
                "既存セッションを選択",
                list(sess_options.keys()),
                format_func=lambda x: sess_options[x],
                key="fin_session_select",
            )
            if st.button("このセッションを開く", key="open_session"):
                st.session_state["fin_session_id"] = selected_id
                st.success(f"セッションを読み込みました: {sess_options[selected_id]}")
                st.rerun()
        else:
            st.info("まだ分析セッションがありません。右の「＋ 新規セッション作成」から作成してください。")

    with col_new:
        if st.button("➕ 新規セッション作成", type="primary", use_container_width=True):
            st.session_state["fin_creating_new"] = True

    st.divider()

    if st.session_state.get("fin_creating_new"):
        st.markdown("#### 新規セッション設定")
        with st.form("new_session_form"):
            c1, c2 = st.columns(2)
            with c1:
                session_name = st.text_input("案件名 *", placeholder="例: 2025年度 経営改善計画")
                purpose = st.selectbox("支援目的 *", _PURPOSES)
                phase   = st.selectbox("分析フェーズ", _PHASES)
            with c2:
                consultant_name = st.text_input("担当コンサルタント")
                depth = st.selectbox("分析深度", _DEPTHS)
                output_purpose = st.multiselect("出力用途", _OUTPUT_PURPOSES)

            st.markdown("**対象期間（分析する年度を選択）**")
            year_cols = st.columns(5)
            import datetime
            current_year = datetime.datetime.now().year
            selected_years = []
            for i, col in enumerate(year_cols):
                yr = str(current_year - 2 + i)
                label = yr + ("（今期）" if i == 2 else "")
                if col.checkbox(label, value=(i <= 2), key=f"yr_{yr}"):
                    selected_years.append(yr)

            submitted = st.form_submit_button("✅ セッションを作成", type="primary")
            if submitted:
                if not session_name:
                    st.error("案件名を入力してください。")
                elif not selected_years:
                    st.error("対象年度を1つ以上選択してください。")
                else:
                    new_id = _save_session(client_id, {
                        "session_name":   session_name,
                        "purpose":        purpose,
                        "phase":          phase,
                        "target_periods": sorted(selected_years),
                        "output_purpose": output_purpose,
                        "analysis_depth": depth,
                        "consultant_name": consultant_name,
                    })
                    if new_id:
                        st.session_state["fin_session_id"] = new_id
                        st.session_state["fin_creating_new"] = False
                        st.success(f"✅ セッション「{session_name}」を作成しました。")
                        st.rerun()

    # 現在のセッション情報
    current_session_id = st.session_state.get("fin_session_id")
    if current_session_id:
        sess = _load_session(current_session_id)
        if sess:
            st.markdown("#### 現在のセッション")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("案件名", sess.get("session_name", "—"))
            m2.metric("支援目的", sess.get("purpose", "—"))
            m3.metric("フェーズ", sess.get("phase", "—"))
            m4.metric("対象年度", ", ".join(sess.get("target_periods") or []))


# ------------------------------------------------------------------ #
#  STEP 1: 資料登録
# ------------------------------------------------------------------ #

def render_step1(session_id: str, client_id: str):
    st.subheader("STEP 1: 資料登録・根拠管理")
    st.caption("分析に使用する資料を登録します。各データの情報源追跡に使います。")

    sess = _load_session(session_id)
    docs = sess.get("documents") or []
    if isinstance(docs, str):
        try:
            docs = json.loads(docs)
        except Exception:
            docs = []

    with st.expander("➕ 資料を追加", expanded=not docs):
        with st.form("add_doc_form"):
            c1, c2 = st.columns(2)
            with c1:
                doc_name  = st.text_input("資料名称", placeholder="例: 2024年3月期 決算書")
                doc_type  = st.selectbox("資料種別", _DOC_TYPES)
                period    = st.text_input("対象期間", placeholder="例: 2024年3月期")
            with c2:
                src       = st.selectbox("情報源", list(_SOURCES.keys()),
                                         format_func=lambda x: _SOURCES[x])
                conf      = st.selectbox("信頼度", list(_CONFIDENCES.keys()),
                                         format_func=lambda x: _CONFIDENCES[x])
                use_flag  = st.checkbox("分析に使用する", value=True)
                note      = st.text_area("メモ", height=60)

            if st.form_submit_button("📎 追加", type="primary"):
                if doc_name:
                    docs.append({
                        "document_name": doc_name,
                        "document_type": doc_type,
                        "target_period": period,
                        "source":        src,
                        "confidence":    conf,
                        "use_in_analysis": use_flag,
                        "note":          note,
                    })
                    _update_session(session_id, {"documents": json.dumps(docs, ensure_ascii=False)})
                    st.success(f"「{doc_name}」を登録しました。")
                    st.rerun()

    if not docs:
        st.info("資料が未登録です。上のフォームから追加してください。")
        return

    st.markdown(f"**登録済み資料: {len(docs)} 件**")
    for i, doc in enumerate(docs):
        conf_html = _confidence_badge(doc.get("confidence", "unknown"))
        use_badge = (
            '<span style="background:#dbeafe;color:#1d4ed8;font-size:0.68rem;'
            'font-weight:700;padding:1px 7px;border-radius:999px;">分析使用</span>'
            if doc.get("use_in_analysis")
            else '<span style="background:#f3f4f6;color:#6b7280;font-size:0.68rem;'
            'padding:1px 7px;border-radius:999px;">参考</span>'
        )
        with st.container():
            col_info, col_del = st.columns([8, 1])
            with col_info:
                st.markdown(
                    f'<div style="border:1px solid #e5e7eb;border-radius:8px;'
                    f'padding:8px 14px;margin-bottom:6px;">'
                    f'<b>{doc.get("document_name","")}</b> '
                    f'<span style="color:#6b7280;font-size:0.8rem;">— {doc.get("document_type","")}</span>'
                    f'&nbsp;&nbsp;{conf_html} {use_badge}<br>'
                    f'<span style="font-size:0.75rem;color:#9ca3af;">'
                    f'期間: {doc.get("target_period","—")} | 情報源: {_SOURCES.get(doc.get("source","unknown"),"不明")}'
                    f'{"| " + doc.get("note","") if doc.get("note") else ""}'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("🗑", key=f"del_doc_{i}", help="削除"):
                    docs.pop(i)
                    _update_session(session_id, {"documents": json.dumps(docs, ensure_ascii=False)})
                    st.rerun()


# ------------------------------------------------------------------ #
#  STEP 2: 決算書データ入力
# ------------------------------------------------------------------ #

def render_step2(session_id: str, client_id: str):
    st.subheader("STEP 2: 決算書データ入力・確認")
    st.caption("PL・BSを年度別に入力します。各値に情報源・信頼度・確認状態を記録します。")

    sess = _load_session(session_id)
    years = sorted(sess.get("target_periods") or [])
    if not years:
        st.warning("STEP 0 で対象年度を設定してください。")
        return

    statements = {s["fiscal_year"]: s for s in _load_statements(session_id)}

    year_tabs = st.tabs([f"📅 {y}年度" for y in years])

    for tab, year in zip(year_tabs, years):
        with tab:
            stmt = statements.get(year, {})
            pl_saved = stmt.get("pl") or {}
            bs_saved = stmt.get("bs") or {}
            memos_saved = stmt.get("abnormal_memos") or []
            if isinstance(pl_saved, str):
                pl_saved = json.loads(pl_saved)
            if isinstance(bs_saved, str):
                bs_saved = json.loads(bs_saved)
            if isinstance(memos_saved, str):
                memos_saved = json.loads(memos_saved)

            with st.form(f"stmt_form_{year}"):
                # ---- PL ----
                st.markdown("##### 📊 損益計算書（P/L）")
                _field_header()
                pl_data = {}
                for key, label in _PL_ITEMS:
                    saved_field = pl_saved.get(key, {})
                    if isinstance(saved_field, dict):
                        dv = saved_field.get("value", 0.0)
                        ds = saved_field.get("source", "unknown")
                        dc = saved_field.get("confidence", "unknown")
                        dst = saved_field.get("status", "unconfirmed")
                        dn = saved_field.get("note", "")
                    else:
                        dv, ds, dc, dst, dn = float(saved_field or 0), "unknown", "unknown", "unconfirmed", ""
                    pl_data[key] = _field_row(label, f"pl_{year}_{key}", dv, ds, dc, dst, dn)

                st.markdown("---")

                # ---- BS ----
                st.markdown("##### 🏦 貸借対照表（B/S）")
                _field_header()
                bs_data = {}
                for key, label in _BS_ITEMS:
                    saved_field = bs_saved.get(key, {})
                    if isinstance(saved_field, dict):
                        dv = saved_field.get("value", 0.0)
                        ds = saved_field.get("source", "unknown")
                        dc = saved_field.get("confidence", "unknown")
                        dst = saved_field.get("status", "unconfirmed")
                        dn = saved_field.get("note", "")
                    else:
                        dv, ds, dc, dst, dn = float(saved_field or 0), "unknown", "unknown", "unconfirmed", ""
                    bs_data[key] = _field_row(label, f"bs_{year}_{key}", dv, ds, dc, dst, dn)

                st.markdown("---")

                # ---- 異常値メモ ----
                st.markdown("##### ⚠️ 異常値・特記事項")
                anomaly_tags = st.multiselect(
                    "該当する特記事項（複数選択可）",
                    _ANOMALY_TAGS,
                    default=[m.get("tag") for m in memos_saved if isinstance(m, dict) and "tag" in m],
                    key=f"anomaly_{year}",
                )
                anomaly_note = st.text_area(
                    "詳細メモ",
                    value="\n".join(m.get("note", "") for m in memos_saved if isinstance(m, dict) and "note" in m),
                    height=80,
                    key=f"anomaly_note_{year}",
                    placeholder="特記事項の詳細・根拠を記述",
                )

                if st.form_submit_button(f"💾 {year}年度を保存", type="primary"):
                    memos = [{"tag": t} for t in anomaly_tags]
                    if anomaly_note.strip():
                        memos.append({"note": anomaly_note.strip()})
                    _upsert_statement(session_id, client_id, year, pl_data, bs_data, memos)
                    st.success(f"✅ {year}年度 PL/BS を保存しました。")
                    st.rerun()

            # ---- 入力済みサマリー ----
            if stmt:
                from core.financial_calculator import calc_pl_ratios
                try:
                    ratios = calc_pl_ratios(pl_saved)
                    revenue = ratios["revenue"]
                    if revenue > 0:
                        st.markdown("**入力済みサマリー**")
                        s1, s2, s3, s4 = st.columns(4)
                        s1.metric("売上高", f"{revenue:.1f}M")
                        s2.metric("粗利率", f"{ratios['gross_margin']:.1f}%")
                        s3.metric("営業利益率", f"{ratios['operating_margin']:.1f}%")
                        s4.metric("経常利益率", f"{ratios['ordinary_margin']:.1f}%")
                except Exception:
                    pass


# ------------------------------------------------------------------ #
#  STEP 3: 借入・返済情報
# ------------------------------------------------------------------ #

def render_step3(session_id: str, client_id: str):
    st.subheader("STEP 3: 借入・返済情報入力")
    st.caption("借入明細を登録します。年間返済額は簡易CF計算に使用されます。")

    loans = _load_loans(session_id)

    # 簡易CF バナー
    if loans:
        total_principal = sum(float(ln.get("annual_principal") or 0) for ln in loans)
        sess = _load_session(session_id)
        years = sorted(sess.get("target_periods") or [])
        stmts = {s["fiscal_year"]: s for s in _load_sessions(session_id) if False}  # placeholder
        try:
            from core.financial_calculator import calc_simple_cf, _v
            # 最新年度のPLから簡易CF計算
            all_stmts = {s["fiscal_year"]: s for s in __import__('json') and []}
        except Exception:
            pass

        st.markdown(
            f'<div style="background:#f0f9ff;border-left:4px solid #0ea5e9;'
            f'border-radius:6px;padding:10px 16px;margin-bottom:1rem;">'
            f'<b>年間返済額合計: {total_principal:.1f}M</b> — '
            f'STEP 2 の当期純利益・減価償却費と組み合わせると簡易CFが計算されます。'
            f'</div>',
            unsafe_allow_html=True,
        )

    # 既存借入一覧
    if loans:
        st.markdown(f"**登録済み借入: {len(loans)} 件**")
        for ln in loans:
            conf = _LOAN_STATUSES.get(ln.get("status", "unconfirmed"), "未確認")
            sched = "✅ あり" if ln.get("has_schedule") else "❌ なし（不足データ）"
            with st.expander(
                f"🏦 {ln.get('lender_name','—')} — "
                f"残高 {float(ln.get('balance',0)):.1f}M / 年返済 {float(ln.get('annual_principal',0)):.1f}M",
            ):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**残高**: {float(ln.get('balance',0)):.1f}M")
                c1.markdown(f"**年間元金返済**: {float(ln.get('annual_principal',0)):.1f}M")
                c1.markdown(f"**年間利息**: {float(ln.get('annual_interest',0)):.1f}M")
                c2.markdown(f"**残返済期間**: {ln.get('remaining_years','—')}年")
                c2.markdown(f"**資金使途**: {ln.get('purpose','—')}")
                c2.markdown(f"**担保・保証**: {ln.get('collateral','—')}")
                c3.markdown(f"**返済予定表**: {sched}")
                c3.markdown(f"**確認状態**: {conf}")
                if ln.get("note"):
                    c3.markdown(f"**メモ**: {ln['note']}")

                if st.button("🗑 削除", key=f"del_loan_{ln['id']}"):
                    _delete_loan(ln["id"])
                    st.rerun()

    st.markdown("---")

    # 新規追加フォーム
    with st.expander("➕ 借入を追加", expanded=not loans):
        with st.form("add_loan_form"):
            c1, c2 = st.columns(2)
            with c1:
                lender   = st.text_input("借入先 *", placeholder="例: ○○銀行 プロパー融資")
                balance  = st.number_input("借入残高（百万円）", min_value=0.0, step=0.1, format="%.1f")
                annual_p = st.number_input("年間元金返済額（百万円）", min_value=0.0, step=0.1, format="%.1f")
                annual_i = st.number_input("年間利息（百万円）", min_value=0.0, step=0.01, format="%.2f")
            with c2:
                remaining = st.number_input("残返済期間（年）", min_value=0.0, step=0.5, format="%.1f")
                purpose   = st.text_input("資金使途", placeholder="例: 運転資金、設備投資")
                collateral = st.text_input("担保・保証", placeholder="例: 信用保証協会保証")
                has_sched = st.checkbox("返済予定表あり")
                stat      = st.selectbox("確認状態", list(_LOAN_STATUSES.keys()),
                                         format_func=lambda x: _LOAN_STATUSES[x])
                note      = st.text_area("メモ", height=60)

            if st.form_submit_button("💾 借入を登録", type="primary"):
                if not lender:
                    st.error("借入先を入力してください。")
                else:
                    ok = _save_loan(session_id, client_id, {
                        "lender_name":     lender,
                        "balance":         balance,
                        "annual_principal": annual_p,
                        "annual_interest": annual_i,
                        "remaining_years": remaining,
                        "purpose":         purpose,
                        "collateral":      collateral,
                        "has_schedule":    has_sched,
                        "status":          stat,
                        "note":            note,
                    })
                    if ok:
                        if not has_sched:
                            st.warning("⚠️ 返済予定表なし → 不足データとして STEP 8 に記録することを推奨します。")
                        st.rerun()


# ------------------------------------------------------------------ #
#  STEP 4: 一時要因・平年化補正
# ------------------------------------------------------------------ #

def render_step4(session_id: str, client_id: str):
    st.subheader("STEP 4: 一時要因・平年化補正")
    st.caption("一時的・非経常的な収益・費用を特定し、実力ベースの利益（平年化補正後利益）を算出します。")

    sess       = _load_session(session_id)
    years      = sorted(sess.get("target_periods") or [])
    statements = {s["fiscal_year"]: s for s in _load_statements(session_id)}
    adjs_all   = _load_adjustments(session_id)

    year_tabs = st.tabs([f"📅 {y}年度" for y in years])

    for tab, year in zip(year_tabs, years):
        with tab:
            stmt = statements.get(year, {})
            adjs = [a for a in adjs_all if a.get("fiscal_year") == year]

            memos = stmt.get("abnormal_memos") or []
            if isinstance(memos, str):
                try:
                    memos = json.loads(memos)
                except Exception:
                    memos = []
            tags = [m.get("tag", "") for m in memos if isinstance(m, dict) and m.get("tag")]
            if tags:
                st.info(f"💡 STEP 2 の特記事項: {', '.join(tags)}")

            with st.expander("➕ 補正項目を追加", expanded=not adjs):
                with st.form(f"adj_form_{year}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        item_name = st.text_input("項目名 *", placeholder="例: 役員報酬の過小計上")
                        category  = st.selectbox("カテゴリ", _ADJ_CATEGORIES)
                        amount    = st.number_input("金額（百万円）", min_value=0.0, step=0.1, format="%.1f")
                    with c2:
                        direction = st.selectbox(
                            "補正方向 *", list(_ADJ_DIRECTIONS.keys()),
                            format_func=lambda x: _ADJ_DIRECTIONS[x],
                        )
                        source = st.selectbox(
                            "情報源", list(_SOURCES.keys()),
                            format_func=lambda x: _SOURCES[x],
                        )
                        conf   = st.selectbox(
                            "信頼度", list(_CONFIDENCES.keys()),
                            format_func=lambda x: _CONFIDENCES[x],
                        )
                        note   = st.text_area("根拠メモ", height=60)

                    if st.form_submit_button("💾 補正を追加", type="primary"):
                        if item_name:
                            if _save_adjustment(session_id, client_id, {
                                "fiscal_year":          year,
                                "item_name":            item_name,
                                "amount":               amount,
                                "category":             category,
                                "adjustment_direction": direction,
                                "source":               source,
                                "confidence":           conf,
                                "note":                 note,
                                "adoption_status":      "pending",
                            }):
                                st.rerun()

            if adjs:
                st.markdown(f"**補正項目: {len(adjs)} 件**")
                for adj in adjs:
                    dir_label = _ADJ_DIRECTIONS.get(adj.get("adjustment_direction", ""), "—")
                    col_info, col_adopt, col_del = st.columns([5, 2, 1])
                    with col_info:
                        st.markdown(
                            f'<div style="border:1px solid #e5e7eb;border-radius:6px;'
                            f'padding:8px 12px;margin-bottom:4px;">'
                            f'<b>{adj.get("item_name","")}</b> — {dir_label} '
                            f'<b>{float(adj.get("amount",0)):.1f}M</b><br>'
                            f'<span style="font-size:0.75rem;color:#6b7280;">'
                            f'{adj.get("category","")}'
                            f'{"  |  " + adj.get("note","") if adj.get("note") else ""}'
                            f'</span></div>',
                            unsafe_allow_html=True,
                        )
                    with col_adopt:
                        adopt_opts = list(_ADOPTION_OPTS.keys())
                        cur_adopt  = adj.get("adoption_status", "pending")
                        cur_idx    = adopt_opts.index(cur_adopt) if cur_adopt in adopt_opts else 2
                        new_adopt  = st.selectbox(
                            "採用", adopt_opts, index=cur_idx,
                            format_func=lambda x: _ADOPTION_OPTS[x],
                            key=f"adj_adopt_{adj['id']}",
                            label_visibility="collapsed",
                        )
                        if new_adopt != cur_adopt:
                            _update_adjustment(adj["id"], {"adoption_status": new_adopt})
                            st.rerun()
                    with col_del:
                        if st.button("🗑", key=f"del_adj_{adj['id']}"):
                            _delete_adjustment(adj["id"])
                            st.rerun()

                st.markdown("---")
                st.markdown("#### 📊 平年化補正後利益")
                pl_saved = stmt.get("pl") or {}
                if isinstance(pl_saved, str):
                    try:
                        pl_saved = json.loads(pl_saved)
                    except Exception:
                        pl_saved = {}
                if pl_saved:
                    from core.financial_calculator import calc_pl_ratios, calc_normalized_profit
                    ratios     = calc_pl_ratios(pl_saved)
                    ord_profit = ratios["ordinary_profit"]
                    norm       = calc_normalized_profit(ord_profit, adjs)
                    add_back   = norm["total_add_back"]
                    exclude    = norm["total_exclude"]
                    normalized = norm["normalized_profit"]

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("経常利益（公表値）", f"{ord_profit:.1f}M")
                    m2.metric("加算合計", f"+{add_back:.1f}M")
                    m3.metric("減算合計", f"-{exclude:.1f}M")
                    m4.metric("平年化補正後利益", f"{normalized:.1f}M",
                              delta=f"{normalized - ord_profit:+.1f}M" if (add_back or exclude) else None)


# ------------------------------------------------------------------ #
#  STEP 5: 売上構造分析
# ------------------------------------------------------------------ #

def render_step5(session_id: str, client_id: str):
    st.subheader("STEP 5: 売上構造分析")
    st.caption("売上をセグメント別に分解し、収益性・成長性・戦略的重要度を評価します。")

    sess     = _load_session(session_id)
    years    = sorted(sess.get("target_periods") or [])
    segs_all = _load_segments(session_id)

    year_tabs = st.tabs([f"📅 {y}年度" for y in years])

    for tab, year in zip(year_tabs, years):
        with tab:
            segs = [s for s in segs_all if s.get("fiscal_year") == year]

            with st.expander("➕ セグメントを追加", expanded=not segs):
                with st.form(f"seg_form_{year}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        seg_name  = st.text_input("セグメント名 *", placeholder="例: 既存顧客向け保守")
                        sales_amt = st.number_input("売上高（百万円）", min_value=0.0, step=0.1, format="%.1f")
                        gm_pct    = st.number_input("粗利率（%）", min_value=0.0, max_value=100.0, step=0.1, format="%.1f")
                    with c2:
                        order_cnt = st.number_input("受注件数", min_value=0, step=1)
                        avg_price = st.number_input("平均単価（百万円）", min_value=0.0, step=0.01, format="%.2f")
                        route     = st.selectbox("販売チャネル", list(_SALES_ROUTES.keys()),
                                                 format_func=lambda x: _SALES_ROUTES[x])
                    with c3:
                        strategic = st.selectbox("戦略的位置づけ", list(_STRATEGIC_TREATMENTS.keys()),
                                                 format_func=lambda x: _STRATEGIC_TREATMENTS[x])
                        data_src  = st.selectbox("情報源", list(_SOURCES.keys()),
                                                 format_func=lambda x: _SOURCES[x])
                        data_conf = st.selectbox("信頼度", list(_CONFIDENCES.keys()),
                                                 format_func=lambda x: _CONFIDENCES[x])
                        note      = st.text_area("メモ", height=60)

                    if st.form_submit_button("💾 セグメントを追加", type="primary"):
                        if seg_name:
                            if _save_segment(session_id, client_id, {
                                "fiscal_year":       year,
                                "segment_name":      seg_name,
                                "sales_amount":      sales_amt,
                                "gross_margin":      gm_pct,
                                "order_count":       order_cnt,
                                "average_unit_price": avg_price,
                                "sales_route":       route,
                                "strategic_treatment": strategic,
                                "data_source":       data_src,
                                "data_confidence":   data_conf,
                                "consultant_note":   note,
                            }):
                                st.rerun()

            if segs:
                total_sales = sum(float(s.get("sales_amount", 0)) for s in segs)
                st.markdown(f"**登録セグメント: {len(segs)} 件 / 合計売上: {total_sales:.1f}M**")

                import pandas as pd
                strat_colors = {
                    "grow": "#dcfce7", "maintain": "#dbeafe", "optimize": "#fef3c7",
                    "reduce": "#fee2e2", "exit": "#f3f4f6", "unknown": "#f9fafb",
                }
                rows = []
                for s in segs:
                    amt   = float(s.get("sales_amount", 0))
                    share = round(amt / total_sales * 100, 1) if total_sales else 0
                    rows.append({
                        "セグメント":  s.get("segment_name", "—"),
                        "売上(M)":    f"{amt:.1f}",
                        "構成比(%)":  f"{share:.1f}",
                        "粗利率(%)":  f"{float(s.get('gross_margin',0)):.1f}",
                        "チャネル":   _SALES_ROUTES.get(s.get("sales_route", ""), "—"),
                        "戦略":       _STRATEGIC_TREATMENTS.get(s.get("strategic_treatment", ""), "—"),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                try:
                    chart_data = pd.DataFrame({
                        "セグメント": [s.get("segment_name", "") for s in segs],
                        "売上":       [float(s.get("sales_amount", 0)) for s in segs],
                    })
                    st.bar_chart(chart_data, x="セグメント", y="売上", use_container_width=True)
                except Exception:
                    pass

                for s in segs:
                    amt   = float(s.get("sales_amount", 0))
                    share = round(amt / total_sales * 100, 1) if total_sales else 0
                    strat = _STRATEGIC_TREATMENTS.get(s.get("strategic_treatment", ""), "—")
                    bg    = strat_colors.get(s.get("strategic_treatment", ""), "#f9fafb")
                    col_info, col_del = st.columns([10, 1])
                    with col_info:
                        st.markdown(
                            f'<div style="border:1px solid #e5e7eb;border-radius:6px;'
                            f'padding:8px 14px;margin-bottom:4px;">'
                            f'<b>{s.get("segment_name","")}</b> '
                            f'<span style="background:{bg};font-size:0.68rem;font-weight:700;'
                            f'padding:1px 7px;border-radius:999px;">{strat}</span><br>'
                            f'売上: {amt:.1f}M ({share:.1f}%) | '
                            f'粗利率: {float(s.get("gross_margin",0)):.1f}% | '
                            f'件数: {s.get("order_count","—")}件 | '
                            f'単価: {float(s.get("average_unit_price",0)):.2f}M'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with col_del:
                        if st.button("🗑", key=f"del_seg_{s['id']}"):
                            _delete_segment(s["id"])
                            st.rerun()


# ------------------------------------------------------------------ #
#  STEP 6: 資金繰り・運転資金
# ------------------------------------------------------------------ #

def render_step6(session_id: str, client_id: str):
    st.subheader("STEP 6: 資金繰り・運転資金分析")
    st.caption("STEP 2（PL/BS）・STEP 3（借入）のデータから主要指標を自動計算します。")

    sess       = _load_session(session_id)
    years      = sorted(sess.get("target_periods") or [])
    statements = {s["fiscal_year"]: s for s in _load_statements(session_id)}
    loans      = _load_loans(session_id)
    adjs_all   = _load_adjustments(session_id)

    if not statements:
        st.warning("STEP 2 で決算書データを入力してください。")
        return

    from core.financial_calculator import calc_all
    import pandas as pd

    # Multi-year trend table
    trend_rows = []
    for year in years:
        stmt = statements.get(year)
        if not stmt:
            continue
        pl = stmt.get("pl") or {}
        bs = stmt.get("bs") or {}
        if isinstance(pl, str):
            try:
                pl = json.loads(pl)
            except Exception:
                pl = {}
        if isinstance(bs, str):
            try:
                bs = json.loads(bs)
            except Exception:
                bs = {}
        year_adjs = [a for a in adjs_all if a.get("fiscal_year") == year]
        try:
            calcs = calc_all(pl, bs, loans, year_adjs)
            trend_rows.append({
                "年度":          year,
                "売上高(M)":     f"{calcs['pl_ratios']['revenue']:.1f}",
                "経常利益(M)":   f"{calcs['pl_ratios']['ordinary_profit']:.1f}",
                "簡易CF(M)":     f"{calcs['simple_cf']['simple_cf']:.1f}",
                "CCC(日)":       f"{calcs['ccc']['ccc']:.1f}",
                "現預金月数":    f"{calcs['bs_ratios']['cash_months']:.1f}",
                "自己資本比率%": f"{calcs['bs_ratios']['equity_ratio']:.1f}",
                "BEP(M)":        f"{calcs['bep']['bep_standard']:.1f}",
            })
        except Exception:
            trend_rows.append({"年度": year, "売上高(M)": "—", "経常利益(M)": "—",
                                "簡易CF(M)": "—", "CCC(日)": "—", "現預金月数": "—",
                                "自己資本比率%": "—", "BEP(M)": "—"})

    if trend_rows:
        st.markdown("#### 📊 多年度トレンド（自動計算）")
        st.dataframe(pd.DataFrame(trend_rows), use_container_width=True, hide_index=True)

    # Detailed view for latest year
    if years:
        latest = years[-1]
        stmt   = statements.get(latest)
        if stmt:
            pl = stmt.get("pl") or {}
            bs = stmt.get("bs") or {}
            if isinstance(pl, str):
                try:
                    pl = json.loads(pl)
                except Exception:
                    pl = {}
            if isinstance(bs, str):
                try:
                    bs = json.loads(bs)
                except Exception:
                    bs = {}
            year_adjs = [a for a in adjs_all if a.get("fiscal_year") == latest]
            try:
                calcs = calc_all(pl, bs, loans, year_adjs)
                st.markdown(f"#### 🔍 直近年度（{latest}）詳細")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**簡易CF分解**")
                    cf = calcs["simple_cf"]
                    ok_icon = "✅" if cf["is_positive"] else "⚠️ マイナス"
                    st.markdown(
                        f'<div style="border:1px solid #e5e7eb;border-radius:8px;padding:12px;">'
                        f'当期純利益: {cf["net_profit"]:.1f}M<br>'
                        f'＋ 減価償却費: {cf["depreciation"]:.1f}M<br>'
                        f'－ 年間元金返済: {cf["total_annual_principal"]:.1f}M<br>'
                        f'<hr style="margin:6px 0;">'
                        f'<b>簡易CF: {cf["simple_cf"]:.1f}M</b> {ok_icon}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.markdown("**CCC（キャッシュ・コンバージョン・サイクル）**")
                    ccc = calcs["ccc"]
                    st.markdown(
                        f'<div style="border:1px solid #e5e7eb;border-radius:8px;padding:12px;">'
                        f'売掛金回収日数: {ccc["receivables_days"]:.1f}日<br>'
                        f'＋ 在庫日数: {ccc["inventory_days"]:.1f}日<br>'
                        f'－ 買掛金支払日数: {ccc["payables_days"]:.1f}日<br>'
                        f'<hr style="margin:6px 0;">'
                        f'<b>CCC: {ccc["ccc"]:.1f}日</b>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                col3, col4 = st.columns(2)
                with col3:
                    st.markdown("**損益分岐点（BEP）**")
                    bep = calcs["bep"]
                    rev = calcs["pl_ratios"]["revenue"]
                    bep_ratio = round(bep["bep_standard"] / rev * 100, 1) if rev else 0
                    st.markdown(
                        f'<div style="border:1px solid #e5e7eb;border-radius:8px;padding:12px;">'
                        f'粗利率: {bep["gross_margin_rate"]:.1f}%<br>'
                        f'固定費: {bep["fixed_costs"]:.1f}M<br>'
                        f'BEP（通常）: {bep["bep_standard"]:.1f}M<br>'
                        f'BEP（返済込）: {bep["bep_with_repay"]:.1f}M<br>'
                        f'<b>売上BEP比率: {bep_ratio:.1f}%</b>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with col4:
                    st.markdown("**ROAツリー**")
                    roa = calcs["roa_tree"]
                    st.markdown(
                        f'<div style="border:1px solid #e5e7eb;border-radius:8px;padding:12px;">'
                        f'ROA: {roa["roa"]:.2f}%<br>'
                        f'＝ 売上高利益率 ({roa["profit_margin"]:.2f}%)<br>'
                        f'　× 総資産回転率 ({roa["asset_turnover"]:.3f}回)<br>'
                        f'経常利益: {roa["ordinary_profit"]:.1f}M / 総資産: {roa["total_assets"]:.1f}M'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            except Exception as ex:
                st.warning(f"計算エラー: {ex}")

    # Cashflow notes
    st.markdown("---")
    st.markdown("#### 📝 資金繰り補足メモ")
    cf_data = sess.get("cashflow_data") or {}
    if isinstance(cf_data, str):
        try:
            cf_data = json.loads(cf_data)
        except Exception:
            cf_data = {}

    with st.form("cf_notes_form"):
        peak_note    = st.text_area("ピーク月・季節変動",   value=cf_data.get("peak_note", ""),
                                    height=60, placeholder="例: 3月・9月に売掛金が集中")
        shortage_note = st.text_area("資金ショートリスク",   value=cf_data.get("shortage_note", ""),
                                     height=60, placeholder="例: 賞与月翌月に現預金が最低水準")
        overdraft     = st.text_area("当座貸越・緊急調達枠", value=cf_data.get("overdraft", ""),
                                     height=60, placeholder="例: ○○銀行に3000万円の当座枠あり")
        if st.form_submit_button("💾 メモを保存", type="primary"):
            new_cf = {**cf_data, "peak_note": peak_note,
                      "shortage_note": shortage_note, "overdraft": overdraft}
            _update_session(session_id, {"cashflow_data": json.dumps(new_cf, ensure_ascii=False)})
            st.success("✅ メモを保存しました。")
            st.rerun()


# ------------------------------------------------------------------ #
#  STEP 7: 業界比較・ベンチマーク
# ------------------------------------------------------------------ #

def render_step7(session_id: str, client_id: str):
    st.subheader("STEP 7: 業界比較・ベンチマーク")
    st.caption("業界平均と対比して、強み・弱みを数値で可視化します。")

    sess           = _load_session(session_id)
    benchmark_data = sess.get("benchmark_data") or {}
    if isinstance(benchmark_data, str):
        try:
            benchmark_data = json.loads(benchmark_data)
        except Exception:
            benchmark_data = {}

    with st.form("benchmark_form"):
        st.markdown("**業界平均値を入力**")
        c1, c2 = st.columns(2)
        with c1:
            b_gm     = st.number_input("粗利率（%）",       value=float(benchmark_data.get("gross_margin", 0)),     step=0.1, format="%.1f")
            b_om     = st.number_input("営業利益率（%）",   value=float(benchmark_data.get("operating_margin", 0)), step=0.1, format="%.1f")
            b_roa    = st.number_input("ROA（%）",           value=float(benchmark_data.get("roa", 0)),              step=0.1, format="%.2f")
            b_source = st.text_input("データ出所",           value=benchmark_data.get("source", ""),
                                     placeholder="例: 業種別財務データ（中企庁 2024年版）")
        with c2:
            b_er   = st.number_input("自己資本比率（%）", value=float(benchmark_data.get("equity_ratio", 0)),  step=0.1, format="%.1f")
            b_cr   = st.number_input("流動比率（%）",     value=float(benchmark_data.get("current_ratio", 0)), step=0.1, format="%.1f")
            b_ccc  = st.number_input("CCC（日）",          value=float(benchmark_data.get("ccc", 0)),           step=1.0, format="%.0f")
            b_note = st.text_area("補足メモ",              value=benchmark_data.get("note", ""), height=60)

        if st.form_submit_button("💾 ベンチマークを保存", type="primary"):
            new_bench = {
                "gross_margin":     b_gm,
                "operating_margin": b_om,
                "roa":              b_roa,
                "equity_ratio":     b_er,
                "current_ratio":    b_cr,
                "ccc":              b_ccc,
                "source":           b_source,
                "note":             b_note,
            }
            _update_session(session_id, {"benchmark_data": json.dumps(new_bench, ensure_ascii=False)})
            st.success("✅ ベンチマークを保存しました。")
            st.rerun()

    # Comparison table
    if benchmark_data and any(float(benchmark_data.get(k, 0)) for k in ["gross_margin", "operating_margin", "roa"]):
        years = sorted(sess.get("target_periods") or [])
        if years:
            statements = {s["fiscal_year"]: s for s in _load_statements(session_id)}
            loans      = _load_loans(session_id)
            adjs_all   = _load_adjustments(session_id)
            latest     = years[-1]
            stmt       = statements.get(latest)
            if stmt:
                pl = stmt.get("pl") or {}
                bs = stmt.get("bs") or {}
                if isinstance(pl, str):
                    try:
                        pl = json.loads(pl)
                    except Exception:
                        pl = {}
                if isinstance(bs, str):
                    try:
                        bs = json.loads(bs)
                    except Exception:
                        bs = {}
                year_adjs = [a for a in adjs_all if a.get("fiscal_year") == latest]
                try:
                    from core.financial_calculator import calc_all
                    import pandas as pd
                    calcs = calc_all(pl, bs, loans, year_adjs)

                    st.markdown(f"#### 📊 {latest}年度 vs 業界平均")
                    benchmarks = [
                        ("粗利率",       calcs["pl_ratios"]["gross_margin"],      benchmark_data.get("gross_margin", 0),    "%",  False),
                        ("営業利益率",   calcs["pl_ratios"]["operating_margin"],  benchmark_data.get("operating_margin", 0), "%", False),
                        ("ROA",          calcs["roa_tree"]["roa"],                benchmark_data.get("roa", 0),             "%",  False),
                        ("自己資本比率", calcs["bs_ratios"]["equity_ratio"],      benchmark_data.get("equity_ratio", 0),    "%",  False),
                        ("流動比率",     calcs["bs_ratios"]["current_ratio"],     benchmark_data.get("current_ratio", 0),   "%",  False),
                        ("CCC",          calcs["ccc"]["ccc"],                     benchmark_data.get("ccc", 0),             "日", True),
                    ]
                    rows = []
                    for label, client_val, bench_val, unit, lower_better in benchmarks:
                        diff = client_val - float(bench_val)
                        if lower_better:
                            diff_label = "↓良" if diff < -5 else ("↑要改善" if diff > 5 else "→並")
                        else:
                            diff_label = "↑良" if diff > 1 else ("↓要改善" if diff < -1 else "→並")
                        rows.append({
                            "指標":    f"{label}（{unit}）",
                            "自社":    f"{client_val:.1f}",
                            "業界平均": f"{float(bench_val):.1f}",
                            "差異":    f"{diff:+.1f}",
                            "評価":    diff_label,
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                except Exception as ex:
                    st.warning(f"比較計算エラー: {ex}")


# ------------------------------------------------------------------ #
#  STEP 8: 分析精度・不足データ管理
# ------------------------------------------------------------------ #

def render_step8(session_id: str, client_id: str):
    st.subheader("STEP 8: 分析精度・不足データ管理")
    st.caption("分析に必要なデータの不足・未確認事項を記録し、収集方法を管理します。")

    sess         = _load_session(session_id)
    missing_data = sess.get("missing_data") or []
    if isinstance(missing_data, str):
        try:
            missing_data = json.loads(missing_data)
        except Exception:
            missing_data = []

    loans = _load_loans(session_id)
    no_schedule = [ln for ln in loans if not ln.get("has_schedule")]
    if no_schedule:
        st.warning(
            f"⚠️ 返済予定表なし: {len(no_schedule)} 件 "
            f"({', '.join(ln.get('lender_name','?') for ln in no_schedule)})"
        )

    years      = sorted(sess.get("target_periods") or [])
    statements = {s["fiscal_year"]: s for s in _load_statements(session_id)}
    low_conf_items = []
    for year in years:
        stmt = statements.get(year)
        if not stmt:
            continue
        for section in ["pl", "bs"]:
            data = stmt.get(section) or {}
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    data = {}
            for k, v in data.items():
                if isinstance(v, dict) and v.get("confidence") in ("low", "unknown"):
                    low_conf_items.append(f"{year}/{section.upper()}/{k}: {v.get('confidence','?')}")
    if low_conf_items:
        with st.expander(f"⚠️ 信頼度 低/不明 フィールド: {len(low_conf_items)} 件"):
            for item in low_conf_items[:20]:
                st.caption(f"• {item}")

    st.markdown("---")

    with st.expander("➕ 不足データを追加"):
        with st.form("missing_form"):
            c1, c2 = st.columns(2)
            with c1:
                data_name = st.text_input("不足データ名 *", placeholder="例: 売上台帳（月次）")
                reason    = st.text_area("必要理由", height=60)
                impact    = st.text_area("分析への影響", height=60)
            with c2:
                priority = st.selectbox("優先度", list(_MISSING_PRIORITIES.keys()),
                                        format_func=lambda x: _MISSING_PRIORITIES[x])
                method   = st.selectbox("収集方法", list(_COLLECTION_METHODS.keys()),
                                        format_func=lambda x: _COLLECTION_METHODS[x])
                status   = st.selectbox(
                    "収集状況", ["pending", "in_progress", "collected"],
                    format_func=lambda x: {"pending": "未対応", "in_progress": "対応中", "collected": "収集済"}[x],
                )

            if st.form_submit_button("➕ 追加", type="primary"):
                if data_name:
                    missing_data.append({
                        "data_name": data_name,
                        "reason":    reason,
                        "impact":    impact,
                        "priority":  priority,
                        "method":    method,
                        "status":    status,
                    })
                    _update_session(session_id, {"missing_data": json.dumps(missing_data, ensure_ascii=False)})
                    st.success(f"「{data_name}」を追加しました。")
                    st.rerun()

    if missing_data:
        st.markdown(f"**不足データ: {len(missing_data)} 件**")
        prio_bg = {"high": "#fee2e2", "medium": "#fef3c7", "low": "#f3f4f6"}
        for i, item in enumerate(missing_data):
            bg         = prio_bg.get(item.get("priority", "low"), "#f3f4f6")
            prio_label = _MISSING_PRIORITIES.get(item.get("priority", ""), "—")
            stat_label = {"pending": "未対応", "in_progress": "対応中", "collected": "✅ 収集済"}.get(
                item.get("status", ""), "—"
            )
            impact_html = (
                f'<br><span style="font-size:0.75rem;color:#6b7280;">影響: {item["impact"]}</span>'
                if item.get("impact") else ""
            )
            col_info, col_del = st.columns([10, 1])
            with col_info:
                st.markdown(
                    f'<div style="background:{bg};border-radius:6px;padding:8px 14px;margin-bottom:6px;">'
                    f'<b>[{prio_label}] {item.get("data_name","")}</b> — {stat_label}<br>'
                    f'<span style="font-size:0.78rem;">{item.get("reason","")}</span>'
                    f'{impact_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("🗑", key=f"del_missing_{i}"):
                    missing_data.pop(i)
                    _update_session(session_id, {"missing_data": json.dumps(missing_data, ensure_ascii=False)})
                    st.rerun()


# ------------------------------------------------------------------ #
#  STEP 9: AI財務診断 実行
# ------------------------------------------------------------------ #

def render_step9(session_id: str, client_id: str):
    st.subheader("STEP 9: AI財務診断 実行")
    st.caption("収集したデータをもとにGPT-4oで財務診断を実行します。")

    sess            = _load_session(session_id)
    years           = sorted(sess.get("target_periods") or [])
    statements_list = _load_statements(session_id)
    loans           = _load_loans(session_id)
    adjs_all        = _load_adjustments(session_id)
    segs_all        = _load_segments(session_id)
    results         = _load_analysis_results(session_id)

    st.markdown("#### 📋 データ準備状況")
    checks = [
        ("決算書データ",   len(statements_list) > 0),
        ("借入情報",       len(loans) > 0),
        ("平年化補正",     len(adjs_all) > 0),
        ("売上セグメント", len(segs_all) > 0),
    ]
    cols = st.columns(len(checks))
    for col, (label, ok) in zip(cols, checks):
        col.metric(label, "✅" if ok else "⚠️ 未入力")

    if not statements_list:
        st.warning("STEP 2 で決算書データを入力してください。")
        return

    st.markdown("---")

    if results:
        st.success(f"✅ 最新のAI診断: {results[0]['created_at'][:16]}")
        run_label = "🔄 再実行（上書き）"
        run_type  = "secondary"
    else:
        run_label = "🤖 AI財務診断を実行"
        run_type  = "primary"

    if st.button(run_label, type=run_type, key="run_fin_ai"):
        st.session_state["fin_ai_run"] = True

    if st.session_state.pop("fin_ai_run", False):
        with st.spinner("AI分析中... 30〜60秒かかります"):
            from core.financial_calculator import calc_all
            from core.pipeline.financial_analysis_engine import run_financial_analysis

            statements_data: dict = {}
            for stmt in statements_list:
                fy = stmt["fiscal_year"]
                pl = stmt.get("pl") or {}
                bs = stmt.get("bs") or {}
                if isinstance(pl, str):
                    try:
                        pl = json.loads(pl)
                    except Exception:
                        pl = {}
                if isinstance(bs, str):
                    try:
                        bs = json.loads(bs)
                    except Exception:
                        bs = {}
                year_adjs = [a for a in adjs_all if a.get("fiscal_year") == fy]
                try:
                    calcs = calc_all(pl, bs, loans, year_adjs)
                    statements_data[fy] = {
                        "pl": pl, "bs": bs,
                        "ratios": calcs,
                        "memos":  stmt.get("abnormal_memos") or [],
                    }
                except Exception:
                    statements_data[fy] = {"pl": pl, "bs": bs}

            input_data = {
                "company_name":   st.session_state.get("client_name", ""),
                "purpose":        sess.get("purpose", ""),
                "phase":          sess.get("phase", ""),
                "statements":     statements_data,
                "loans":          loans,
                "adjustments":    adjs_all,
                "segments":       segs_all,
                "benchmark":      sess.get("benchmark_data") or {},
                "cashflow_notes": sess.get("cashflow_data") or {},
                "missing_data":   sess.get("missing_data") or [],
            }

            try:
                result = run_financial_analysis(input_data)
                rid    = _save_analysis_result(session_id, client_id, {
                    "analysis_type":  "comprehensive",
                    "ai_output":      json.dumps(result, ensure_ascii=False),
                    "confidence":     "medium",
                    "adoption_status": "pending",
                })
                if rid:
                    st.success("✅ AI財務診断が完了しました。STEP 10 で結果を確認・採用判断してください。")
                    st.rerun()
            except Exception as e:
                st.error(f"AI実行エラー: {e}")


# ------------------------------------------------------------------ #
#  STEP 10: AI結果レビュー・採用判断
# ------------------------------------------------------------------ #

def render_step10(session_id: str, client_id: str):
    st.subheader("STEP 10: AI診断結果レビュー・採用判断")
    st.caption("AI財務診断の結果を確認し、各発見事項の採用/参考/不採用を判断します。")

    results = _load_analysis_results(session_id)
    if not results:
        st.info("STEP 9 でAI診断を実行してください。")
        return

    prio_bg = {"high": "#fee2e2", "medium": "#fef9e7", "low": "#f3f4f6"}

    for res in results:
        st.markdown(f"**実行日時**: {res['created_at'][:16]} | **タイプ**: {res.get('analysis_type','')}")

        ai_output = res.get("ai_output") or {}
        if isinstance(ai_output, str):
            try:
                ai_output = json.loads(ai_output)
            except Exception:
                ai_output = {}

        summary = ai_output.get("summary", "")
        if summary:
            st.info(f"**総括**: {summary}")

        strengths = ai_output.get("strengths", [])
        if strengths:
            st.markdown("**財務的強み:** " + " / ".join(strengths))

        key_issues = ai_output.get("key_issues", [])
        if key_issues:
            st.markdown("**主要課題:** " + " / ".join(key_issues))

        findings = ai_output.get("findings", [])
        if findings:
            st.markdown(f"#### 発見事項: {len(findings)} 件")
            for i, f in enumerate(findings):
                bg         = prio_bg.get(f.get("priority", ""), "#f3f4f6")
                prio       = f.get("priority", "medium")
                a_type     = f.get("analysis_type", "")
                col_info, col_adopt = st.columns([7, 2])
                with col_info:
                    hypo_html = (
                        f'<br><span style="font-size:0.72rem;color:#7c3aed;">内部分析仮説: '
                        f'{f.get("hypothesis_for_internal","")}</span>'
                        if f.get("hypothesis_for_internal") else ""
                    )
                    st.markdown(
                        f'<div style="background:{bg};border-radius:8px;'
                        f'padding:10px 14px;margin-bottom:6px;">'
                        f'<span style="font-size:0.68rem;font-weight:700;color:#6b7280;">'
                        f'[{prio.upper()} | {a_type}]</span><br>'
                        f'<b>{f.get("finding","")}</b><br>'
                        f'<span style="font-size:0.78rem;color:#374151;">'
                        f'根拠: {f.get("evidence","")}</span><br>'
                        f'<span style="font-size:0.75rem;color:#6b7280;">'
                        f'提言: {f.get("recommendation","")}</span>'
                        f'{hypo_html}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with col_adopt:
                    adopt_opts = list(_ADOPTION_OPTS.keys())
                    st.selectbox(
                        "採用", adopt_opts, index=2,
                        format_func=lambda x: _ADOPTION_OPTS[x],
                        key=f"finding_adopt_{res['id']}_{i}",
                        label_visibility="collapsed",
                    )

        st.markdown("---")
        with st.form(f"review_form_{res['id']}"):
            overall_adopt = st.selectbox(
                "この診断全体の採用ステータス",
                list(_ADOPTION_OPTS.keys()),
                index=list(_ADOPTION_OPTS.keys()).index(res.get("adoption_status", "pending")),
                format_func=lambda x: _ADOPTION_OPTS[x],
            )
            review_note = st.text_area("コンサルタントコメント",
                                       value=res.get("consultant_review", ""), height=80)
            revision    = st.text_area("修正・追記事項",
                                       value=res.get("revision_note", ""), height=60)
            if st.form_submit_button("💾 採用判断を保存", type="primary"):
                _update_analysis_result(res["id"], {
                    "adoption_status":   overall_adopt,
                    "consultant_review": review_note,
                    "revision_note":     revision,
                })
                st.success("✅ 採用判断を保存しました。")
                st.rerun()


# ------------------------------------------------------------------ #
#  STEP 11: パイプライン接続
# ------------------------------------------------------------------ #

def render_step11(session_id: str, client_id: str):
    st.subheader("STEP 11: 計画書・SWOT・数値計画へ接続")
    st.caption("分析結果を集約し、パイプラインの次ステップへ引き渡します。")

    sess            = _load_session(session_id)
    years           = sorted(sess.get("target_periods") or [])
    statements_list = _load_statements(session_id)
    loans           = _load_loans(session_id)
    adjs_all        = _load_adjustments(session_id)
    results         = _load_analysis_results(session_id)

    from core.financial_calculator import calc_all
    import pandas as pd

    year_summaries: dict = {}
    for stmt in statements_list:
        fy = stmt["fiscal_year"]
        pl = stmt.get("pl") or {}
        bs = stmt.get("bs") or {}
        if isinstance(pl, str):
            try:
                pl = json.loads(pl)
            except Exception:
                pl = {}
        if isinstance(bs, str):
            try:
                bs = json.loads(bs)
            except Exception:
                bs = {}
        year_adjs = [a for a in adjs_all if a.get("fiscal_year") == fy]
        try:
            calcs = calc_all(pl, bs, loans, year_adjs)
            year_summaries[fy] = {
                "revenue":           calcs["pl_ratios"]["revenue"],
                "ordinary_profit":   calcs["pl_ratios"]["ordinary_profit"],
                "gross_margin":      calcs["pl_ratios"]["gross_margin"],
                "operating_margin":  calcs["pl_ratios"]["operating_margin"],
                "net_margin":        calcs["pl_ratios"]["net_margin"],
                "simple_cf":         calcs["simple_cf"]["simple_cf"],
                "equity_ratio":      calcs["bs_ratios"]["equity_ratio"],
                "debt_ratio":        calcs["bs_ratios"]["debt_ratio"],
                "cash_months":       calcs["bs_ratios"]["cash_months"],
                "ccc":               calcs["ccc"]["ccc"],
                "roa":               calcs["roa_tree"]["roa"],
                "normalized_profit": calcs["normalized"]["normalized_profit"],
            }
        except Exception:
            pass

    ai_findings: list[str] = []
    for res in results:
        if res.get("adoption_status") in ("adopted", "pending"):
            ai_out = res.get("ai_output") or {}
            if isinstance(ai_out, str):
                try:
                    ai_out = json.loads(ai_out)
                except Exception:
                    ai_out = {}
            for f in ai_out.get("findings", []):
                if f.get("priority") == "high":
                    ai_findings.append(f.get("finding", ""))

    st.markdown("#### 📋 エクスポートプレビュー")
    if year_summaries:
        rows = []
        for fy, s in sorted(year_summaries.items()):
            rows.append({
                "年度":        fy,
                "売上高(M)":   f"{s['revenue']:.1f}",
                "経常利益(M)": f"{s['ordinary_profit']:.1f}",
                "粗利率%":     f"{s['gross_margin']:.1f}",
                "営業利益率%": f"{s['operating_margin']:.1f}",
                "簡易CF(M)":   f"{s['simple_cf']:.1f}",
                "ROA%":        f"{s['roa']:.2f}",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("STEP 2 の決算書データが必要です。")

    if ai_findings:
        st.markdown("**AI診断 高優先度発見事項（上位5件）:**")
        for f in ai_findings[:5]:
            st.markdown(f"• {f}")

    st.markdown("---")
    if st.button("🔗 財務分析をパイプラインへ接続（保存）", type="primary"):
        notes = _load_client_notes(client_id)
        notes["financial_summary"] = {
            "session_id":              session_id,
            "session_name":            sess.get("session_name", ""),
            "purpose":                 sess.get("purpose", ""),
            "year_summaries":          year_summaries,
            "total_annual_principal":  sum(float(ln.get("annual_principal", 0)) for ln in loans),
            "ai_high_priority_findings": ai_findings[:5],
            "benchmark":               sess.get("benchmark_data") or {},
        }
        pipeline_steps = notes.get("pipeline_steps", {})
        pipeline_steps["4"] = "done"
        notes["pipeline_steps"] = pipeline_steps
        _update_client_notes(client_id, notes)
        st.success("✅ 財務分析を `clients.notes` に保存し、STEP 4 を完了マークしました。")
        st.balloons()


# ------------------------------------------------------------------ #
#  サイドバー: ステップナビゲーション
# ------------------------------------------------------------------ #

_STEPS = {
    0:  "⚙️ 案件・分析目的設定",
    1:  "📎 資料登録・根拠管理",
    2:  "📊 決算書データ入力",
    3:  "🏦 借入・返済情報",
    4:  "🔧 一時要因・平年化補正",
    5:  "📈 売上構造分析",
    6:  "💧 資金繰り・運転資金",
    7:  "🏭 業界比較・ベンチマーク",
    8:  "⚠️ 分析精度・不足データ",
    9:  "🤖 AI分析実行",
    10: "✅ AI結果レビュー・採用判断",
    11: "🔗 計画書・SWOT・数値計画へ接続",
}
_IMPLEMENTED = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}


def render_sidebar_nav():
    st.sidebar.markdown("### 財務分析 ステップ")
    current = st.session_state.get("fin_step", 0)
    selected = st.sidebar.radio(
        "ステップ選択",
        list(_STEPS.keys()),
        format_func=lambda x: _STEPS[x] + ("" if x in _IMPLEMENTED else " 🔜"),
        index=current,
        key="fin_step_radio",
        label_visibility="collapsed",
    )
    st.session_state["fin_step"] = selected

    session_id = st.session_state.get("fin_session_id")
    if session_id:
        st.sidebar.markdown("---")
        st.sidebar.caption(f"セッション ID: `{session_id[:8]}...`")
        if st.sidebar.button("🔄 セッション変更", key="change_session"):
            st.session_state.pop("fin_session_id", None)
            st.session_state["fin_step"] = 0
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

    # STEP バッジ
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
        <div style="background:#dcfce7;color:#15803d;font-size:0.72rem;font-weight:700;
                    padding:3px 10px;border-radius:999px;">STEP 4</div>
        <div style="font-size:0.8rem;color:#9ca3af;">データ収集 → 分析フェーズ</div>
    </div>
    """, unsafe_allow_html=True)

    st.title("💹 STEP 4: 財務分析ワークスペース")
    st.markdown(f"**{client_name}** — コンサルタント向け多年度財務分析")

    step = render_sidebar_nav()
    session_id = st.session_state.get("fin_session_id")

    st.divider()

    # STEP 0 はセッション不要
    if step == 0:
        render_step0(client_id, client_name)
        return

    # STEP 1 以降はセッション必須
    if not session_id:
        st.warning("⚠️ まず **STEP 0** で分析セッションを作成または選択してください。")
        if st.button("← STEP 0 へ"):
            st.session_state["fin_step"] = 0
            st.rerun()
        return

    if step == 1:
        render_step1(session_id, client_id)
    elif step == 2:
        render_step2(session_id, client_id)
    elif step == 3:
        render_step3(session_id, client_id)
    elif step == 4:
        render_step4(session_id, client_id)
    elif step == 5:
        render_step5(session_id, client_id)
    elif step == 6:
        render_step6(session_id, client_id)
    elif step == 7:
        render_step7(session_id, client_id)
    elif step == 8:
        render_step8(session_id, client_id)
    elif step == 9:
        render_step9(session_id, client_id)
    elif step == 10:
        render_step10(session_id, client_id)
    elif step == 11:
        render_step11(session_id, client_id)


main()
