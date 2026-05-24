"""
STEP 6: 内部環境分析登録
STEP 5 で確定した調査項目に対して、ヒアリング結果・社内文書を登録する。
調査項目ごとにエビデンスをひも付け、カバレッジを可視化する。
"""
import json
import io
import pandas as pd
import streamlit as st
from core.auth import check_auth
from core.style_utils import load_custom_css

st.set_page_config(
    page_title="STEP 6: 内部環境分析登録 — Consulting OS",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_custom_css()


# ── DB helpers ───────────────────────────────────────────────────────────────

def _load_survey_items(client_id: str) -> list[dict]:
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        return notes.get("internal_survey_items", {}).get("items", [])
    except Exception:
        return []


def _load_findings(client_id: str) -> dict:
    """調査結果（テキストメモ）を clients.notes から読む。"""
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        return notes.get("internal_findings", {})
    except Exception:
        return {}


def _save_findings(client_id: str, findings: dict, mark_done: bool = False):
    try:
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("notes").eq("id", client_id).single().execute()
        notes = json.loads(res.data.get("notes") or "{}")
        notes["internal_findings"] = findings
        if mark_done:
            steps = notes.get("pipeline_steps", {})
            steps["6"] = "done"
            notes["pipeline_steps"] = steps
            st.session_state[f"pipeline_{client_id}"] = steps
        sb.table("clients").update({"notes": json.dumps(notes, ensure_ascii=False)}).eq("id", client_id).execute()
    except Exception as e:
        st.error(f"保存エラー: {e}")


def _save_uploaded_docs(client_id: str, uploaded_files: list, item_id: str):
    """アップロードされた文書を DatasetRepo に保存し、調査項目 ID をタグとして持たせる。"""
    try:
        from core.repos.dataset_repo import DatasetRepo
        repo = DatasetRepo()

        cur_v = repo.get_current_dataset_version(client_id, "internal_docs")
        existing = []
        if cur_v and cur_v.get("normalized_json"):
            prev = cur_v["normalized_json"]
            existing = prev if isinstance(prev, list) else [prev]

        new_docs = []
        for f in uploaded_files:
            text_content = ""
            try:
                if f.name.endswith(".pdf"):
                    import pypdf
                    reader = pypdf.PdfReader(f)
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            text_content += extracted + "\n\n"
                elif f.name.endswith(".txt"):
                    text_content = f.read().decode("utf-8", errors="replace")
                elif f.name.endswith(".csv"):
                    try:
                        df = pd.read_csv(f)
                    except UnicodeDecodeError:
                        f.seek(0)
                        df = pd.read_csv(f, encoding="shift_jis")
                    import numpy as np
                    df = df.replace([np.inf, -np.inf], float("nan")).where(pd.notnull(df), None)
                    text_content = df.to_markdown(index=False)
                elif f.name.endswith(".docx"):
                    import docx
                    doc = docx.Document(f)
                    text_content = "\n".join(p.text for p in doc.paragraphs)
                else:
                    text_content = f.read().decode("utf-8", errors="replace")
            except Exception as e:
                st.warning(f"{f.name} の読み込みエラー: {e}")
                continue

            new_docs.append({
                "filename":    f.name,
                "content":     text_content,
                "type":        "internal_finding_doc",
                "survey_item_id": item_id,
                "uploaded_at": pd.Timestamp.now().isoformat(),
            })

        if new_docs:
            all_docs = existing + new_docs
            q_json = {
                "filename": f"{len(all_docs)} files (internal docs)",
                "type": "internal_document_batch",
                "count": len(all_docs),
            }
            repo.save_dataset_version(
                client_id=client_id,
                dataset_type="internal_docs",
                normalized_json=all_docs,
                quality_json=q_json,
                source_type="upload_doc",
                created_by=st.session_state.get("user", type("u", (), {"id": None})()).id,
            )
            return len(new_docs)
    except Exception as e:
        st.error(f"ドキュメント保存エラー: {e}")
    return 0


def _get_doc_count_by_item(client_id: str) -> dict[str, int]:
    """調査項目 ID ごとのアップロード済みドキュメント数を返す。"""
    try:
        from core.repos.dataset_repo import DatasetRepo
        repo = DatasetRepo()
        cur_v = repo.get_current_dataset_version(client_id, "internal_docs")
        if not cur_v or not cur_v.get("normalized_json"):
            return {}
        docs = cur_v["normalized_json"]
        if not isinstance(docs, list):
            return {}
        counts: dict[str, int] = {}
        for d in docs:
            iid = d.get("survey_item_id", "__none__")
            counts[iid] = counts.get(iid, 0) + 1
        return counts
    except Exception:
        return {}


# ── カバレッジ計算 ───────────────────────────────────────────────────────────

def _coverage(items: list, findings: dict, doc_counts: dict) -> tuple[int, int]:
    """調査項目のうち「エビデンスあり」の数を返す。"""
    covered = 0
    for item in items:
        iid = item.get("id", "")
        has_text = bool(findings.get(iid, {}).get("finding", "").strip())
        has_docs = doc_counts.get(iid, 0) > 0
        if has_text or has_docs:
            covered += 1
    return covered, len(items)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    from core.sidebar import render_sidebar
    render_sidebar()

    if not check_auth():
        st.warning("ログインが必要です。")
        return

    client_id   = st.session_state.get("client_id")
    client_name = st.session_state.get("client_name", "プロジェクト")

    if not client_id:
        st.warning("プロジェクトが選択されていません。")
        if st.button("← プロジェクト一覧へ"):
            st.switch_page("app.py")
        return

    # ---- ヘッダー ----
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
        <div style="background:#d1fae5;color:#065f46;font-size:0.72rem;font-weight:700;
                    padding:3px 10px;border-radius:999px;letter-spacing:0.06em;">
            STEP 6 — 環境分析フェーズ
        </div>
        <div style="font-size:0.8rem;color:#9ca3af;">前: STEP 5 内部環境調査項目示唆</div>
    </div>
    """, unsafe_allow_html=True)
    st.title("📋 内部環境分析登録")
    st.markdown(
        "STEP 5 で確定した調査項目ごとに、ヒアリング結果・社内文書を登録します。\n"
        "テキストメモ または ファイルアップロードのどちらかで記録できます。"
    )

    items      = _load_survey_items(client_id)
    findings   = _load_findings(client_id)
    doc_counts = _get_doc_count_by_item(client_id)

    if not items:
        st.warning(
            "STEP 5 の調査項目がまだ登録されていません。\n"
            "先に STEP 5 で調査項目を確定してください。"
        )
        st.page_link("pages/05_internal_survey_items.py", label="← STEP 5 内部環境調査項目示唆")
        return

    # ---- カバレッジサマリー ----
    covered, total = _coverage(items, findings, doc_counts)
    pct = int(covered / total * 100) if total else 0
    high_items = [i for i in items if i.get("priority") == "high"]
    high_covered = sum(
        1 for i in high_items
        if findings.get(i.get("id",""), {}).get("finding","").strip()
        or doc_counts.get(i.get("id",""), 0) > 0
    )

    st.markdown(f"""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;
                padding:1rem 1.5rem;margin-bottom:1.5rem;
                display:flex;align-items:center;gap:2.5rem;">
        <div>
            <div style="font-size:1.8rem;font-weight:800;color:#111827;line-height:1;">{covered}
                <span style="font-size:0.9rem;color:#9ca3af;font-weight:500;">/ {total}</span>
            </div>
            <div style="font-size:0.72rem;color:#6b7280;">調査項目カバレッジ</div>
        </div>
        <div style="flex:1;">
            <div style="background:#e5e7eb;border-radius:999px;height:8px;">
                <div style="background:linear-gradient(90deg,#10b981,#059669);
                            width:{pct}%;height:100%;border-radius:999px;transition:width 0.4s;"></div>
            </div>
            <div style="font-size:0.72rem;color:#6b7280;margin-top:3px;">{pct}% カバー済み</div>
        </div>
        <div>
            <div style="font-size:1.8rem;font-weight:800;color:#dc2626;line-height:1;">{high_covered}
                <span style="font-size:0.9rem;color:#9ca3af;font-weight:500;">/ {len(high_items)}</span>
            </div>
            <div style="font-size:0.72rem;color:#6b7280;">最重要項目カバレッジ</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- 調査項目ごとに入力 ----
    save_needed = False

    # 優先度順にソート
    priority_order = {"high": 0, "medium": 1, "low": 2}
    sorted_items = sorted(items, key=lambda i: priority_order.get(i.get("priority", "low"), 2))

    for item in sorted_items:
        iid      = item.get("id", "")
        priority = item.get("priority", "medium")
        finding  = findings.get(iid, {})

        border_color = {"high": "#fca5a5", "medium": "#fcd34d", "low": "#d1d5db"}.get(priority, "#d1d5db")
        badge_color  = {"high": "#dc2626", "medium": "#d97706", "low": "#6b7280"}.get(priority, "#6b7280")
        badge_label  = {"high": "最重要",  "medium": "重要",    "low": "参考"  }.get(priority, "参考")

        has_evidence = bool(finding.get("finding", "").strip()) or doc_counts.get(iid, 0) > 0
        status_icon  = "✅" if has_evidence else "○"

        with st.container():
            st.markdown(f"""
            <div style="border-left:3px solid {border_color};padding-left:12px;margin-bottom:4px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                    <span style="background:{badge_color};color:#fff;font-size:0.65rem;
                                 font-weight:700;padding:2px 8px;border-radius:999px;">{badge_label}</span>
                    <span style="font-size:0.72rem;color:#6b7280;">{item.get('category','')}</span>
                    <span style="font-size:0.82rem;margin-left:auto;">{status_icon} {'調査済み' if has_evidence else '未記録'}</span>
                </div>
                <div style="font-size:0.95rem;font-weight:700;color:#111827;">{item.get('title','')}</div>
                <div style="font-size:0.8rem;color:#6b7280;">
                    調査目的: {item.get('description','')} ／ 必要資料: {item.get('evidence_type','')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            tab_text, tab_file = st.tabs([
                f"📝 テキストメモ{'  ✅' if finding.get('finding','').strip() else ''}",
                f"📁 ファイルアップロード{'  ✅' if doc_counts.get(iid, 0) > 0 else ''} ({doc_counts.get(iid, 0)}件)",
            ])

            with tab_text:
                new_finding = st.text_area(
                    "ヒアリング結果・調査メモ",
                    value=finding.get("finding", ""),
                    height=100,
                    key=f"finding_{iid}",
                    placeholder=(
                        "ヒアリング結果、調査で判明した事実、コンサルタントの所見などを記録してください。\n"
                        "例：営業担当者ごとに粗利率が大きく異なる（トップ担当者30%、最低担当者8%）。"
                        "商品ミックスの差が主因と思われる。"
                    ),
                )
                new_confidence = st.select_slider(
                    "情報の確度",
                    options=["低（推測）", "中（裏付け不十分）", "高（エビデンスあり）"],
                    value=finding.get("confidence", "中（裏付け不十分）"),
                    key=f"conf_{iid}",
                )
                if new_finding != finding.get("finding", "") or new_confidence != finding.get("confidence", "中（裏付け不十分）"):
                    findings[iid] = {
                        **finding,
                        "finding":    new_finding,
                        "confidence": new_confidence,
                    }
                    save_needed = True

            with tab_file:
                uploaded = st.file_uploader(
                    f"ファイルをアップロード",
                    type=["txt", "pdf", "csv", "docx"],
                    accept_multiple_files=True,
                    key=f"upload_{iid}",
                    label_visibility="collapsed",
                )
                if uploaded and st.button(f"保存する", key=f"save_docs_{iid}", type="secondary"):
                    n = _save_uploaded_docs(client_id, uploaded, iid)
                    if n > 0:
                        st.success(f"{n} 件のファイルを保存しました。")
                        st.rerun()

                if doc_counts.get(iid, 0) > 0:
                    st.caption(f"登録済み: {doc_counts[iid]} 件")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if save_needed:
        _save_findings(client_id, findings)

    # ---- 一括テキスト入力（自由記述） ----
    st.divider()
    with st.expander("📝 補足・総合所見（自由記述）"):
        overall = findings.get("__overall__", {}).get("finding", "")
        new_overall = st.text_area(
            "全体的な内部環境の所見・特記事項",
            value=overall,
            height=150,
            key="overall_finding",
            placeholder="調査全体を通じた特記事項、ヒアリングで感じた組織の雰囲気、未確認の仮説など",
        )
        if new_overall != overall:
            findings["__overall__"] = {"finding": new_overall}
            _save_findings(client_id, findings)

    # ---- ナビゲーション & 完了 ----
    st.divider()
    high_uncovered = [
        i for i in high_items
        if not findings.get(i.get("id",""), {}).get("finding","").strip()
        and doc_counts.get(i.get("id",""), 0) == 0
    ]

    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        st.page_link("pages/05_internal_survey_items.py", label="← STEP 5 調査項目示唆")
    with nav2:
        if high_uncovered:
            st.warning(f"最重要項目 {len(high_uncovered)} 件にエビデンスが未登録です")
        else:
            if st.button("✅ 内部環境分析登録を完了 → STEP 6 完了",
                         type="primary", use_container_width=True):
                _save_findings(client_id, findings, mark_done=True)
                st.success("STEP 6 完了！STEP 7（理念・ビジョン設定）へ進んでください。")
                st.rerun()
    with nav3:
        st.page_link("pages/vision_mission.py", label="STEP 7 理念・ビジョン設定 →")


main()
