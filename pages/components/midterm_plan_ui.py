
import difflib
import streamlit as st
import json
from datetime import datetime
from core.midterm_plan_engine import MidtermPlanDocument, MidtermPlanSection, ChapterStatus

# --- Constants ---
SECTION_SHORT_LABELS = [
    "理念", "ビジョン", "外部環境", "内部環境", "根本原因",
    "SWOT", "Cross SWOT", "全社戦略", "事業戦略",
    "機能戦略", "施策", "KPI", "数値計画"
]

def _get_status_class(status: ChapterStatus) -> str:
    """Map chapter status to CSS class."""
    if status == ChapterStatus.LOCKED:
        return "locked"
    elif status == ChapterStatus.APPROVED:
        return "approved"  
    elif status == ChapterStatus.AI_GENERATED:
        return "ai"
    elif status == ChapterStatus.HUMAN_MODIFIED:
        return "modified"
    return "empty"

def _get_status_icon(status: ChapterStatus) -> str:
    """Map chapter status to emoji icon."""
    if status == ChapterStatus.LOCKED:
        return "🔒"
    elif status == ChapterStatus.APPROVED:
        return "✅"
    elif status == ChapterStatus.AI_GENERATED:
        return "🤖"
    elif status == ChapterStatus.HUMAN_MODIFIED:
        return "✏️"
    return "○"

def _get_status_label(status: ChapterStatus) -> str:
    """Map chapter status to Japanese label."""
    if status == ChapterStatus.LOCKED:
        return "ロック済"
    elif status == ChapterStatus.APPROVED:
        return "承認済"
    elif status == ChapterStatus.AI_GENERATED:
        return "AI生成"
    elif status == ChapterStatus.HUMAN_MODIFIED:
        return "編集中"
    return "未着手"

def render_section_header(section: MidtermPlanSection):
    """Render the header for the current section editor."""
    status = section.chapter_state.status
    icon = _get_status_icon(status)
    label = _get_status_label(status)
    status_cls = _get_status_class(status)
    
    st.markdown(f"""
    <div class="section-header" style="display:flex; justify-content:space-between; align_items:center; margin-bottom:1rem; padding-bottom:0.5rem; border-bottom:1px solid #e2e8f0;">
        <div style="font-size:1.5rem; font-weight:700; color:#1e293b;">
            §{section.section_id} {section.section_title}
        </div>
        <div class="status-badge {status_cls}" style="padding:4px 12px; border-radius:9999px; font-size:0.875rem; font-weight:500; display:flex; align-items:center; gap:4px;">
            {icon} {label}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_chapter_nav(doc: MidtermPlanDocument, current_id: int):
    """Render interactive chapter navigation using buttons."""
    
    # CSS to style buttons as rounded pills (better aesthetic)
    st.markdown("""
    <style>
    /* Scoped roughly to buttons in this area if possible, but global for now */
    div.stButton > button {
        border-radius: 20px;
        height: 40px;
        font-weight: bold;
    }
    .nav-label {
        font-size: 0.7rem;
        color: var(--secondary-color);
        text-align: center;
        margin-top: -8px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .nav-label.active {
        color: var(--primary-accent);
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 14 Steps (13 Sections + QA)
    cols = st.columns(14, gap="small")
    
    # Sections 1-13
    for i, section in enumerate(doc.sections):
        sid = section.section_id
        is_active = (sid == current_id)
        
        # Determine status char/icon for button label (optional) or just Number
        # User wants "Circle" + "Button". Number is cleanest.
        btn_label = str(sid)
        
        with cols[i]:
            # Use Primary type for active, Secondary for others
            if st.button(
                btn_label, 
                key=f"nav_btn_{sid}", 
                type="primary" if is_active else "secondary", 
                use_container_width=True,
                help=f"§{sid} {section.section_title}"
            ):
                st.session_state["midterm_current_section"] = sid
                st.rerun()
            
            # Label below
            short = SECTION_SHORT_LABELS[i] if i < len(SECTION_SHORT_LABELS) else f"§{sid}"
            active_cls = "active" if is_active else ""
            st.markdown(f'<div class="nav-label {active_cls}" title="{short}">{short}</div>', unsafe_allow_html=True)

    # Step 14: QA
    with cols[13]:
        is_active = (current_id == 14)
        if st.button(
            "QA",
            key="nav_btn_qa",
            type="primary" if is_active else "secondary",
            use_container_width=True,
            help="§14 品質チェック"
        ):
            st.session_state["midterm_current_section"] = 14
            st.rerun()
        
        active_cls = "active" if is_active else ""
        st.markdown(f'<div class="nav-label {active_cls}">品質QA</div>', unsafe_allow_html=True)

def render_audit_log(section: MidtermPlanSection):
    """Render audit metadata (Decision Audit) in an expander."""
    meta = section.generation_metadata
    if not meta:
        return

    with st.expander("🔍 生成監査ログ (Decision Audit)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.caption("使用モデル")
            st.info(meta.model_name or "Unknown")
            if meta.usage:
                st.caption("トークン使用量")
                st.json(meta.usage, expanded=False)
        with col2:
            st.caption("生成日時")
            st.text(meta.generated_at)
            st.caption("システムフィンガープリント")
            st.code(meta.system_fingerprint or "N/A")
        
        # Prompt Snapshot
        st.caption("プロンプト・スナップショット")
        with st.popover("プロンプトを表示"):
            try:
                # Pretty print JSON string if possible
                prompt_json = json.loads(meta.prompt_snapshot)
                st.json(prompt_json)
            except:
                st.code(meta.prompt_snapshot, language="json")

def render_stats_dashboard(doc: MidtermPlanDocument):
    """Render mini stats dashboard at the top."""
    total = len(doc.sections)
    locked = sum(1 for s in doc.sections if s.chapter_state.status == ChapterStatus.LOCKED)
    ai_gen = sum(1 for s in doc.sections if s.chapter_state.status == ChapterStatus.AI_GENERATED)
    modified = sum(1 for s in doc.sections if s.chapter_state.status == ChapterStatus.HUMAN_MODIFIED)
    has_content = sum(1 for s in doc.sections if s.narrative)
    progress_pct = int((locked / total) * 100) if total > 0 else 0
    
    # Last saved timestamp
    last_saved = st.session_state.get("midterm_last_saved", None)
    saved_str = f'<span style="color:#059669;font-weight:600;">💾 {last_saved}</span>' if last_saved else '<span style="color:#94A3B8;">未保存</span>'
    
    st.markdown(f"""
    <style>
    .stats-container {{
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 12px 24px;
        margin-bottom: 16px;
    }}
    .stat-box {{
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        min-width: 80px;
    }}
    .stat-val {{
        font-size: 1.4rem;
        font-weight: 800;
        line-height: 1;
        margin-bottom: 4px;
    }}
    .stat-lbl {{
        font-size: 0.75rem;
        color: #64748B;
        font-weight: 500;
    }}
    .stat-divider {{
        width: 1px;
        height: 30px;
        background-color: #E2E8F0;
    }}
    </style>
    
    <div class="stats-container">
        <div class="stat-box">
            <div class="stat-val" style="color:#0F172A;">{has_content}<span style="font-size:0.9rem;color:#94A3B8;font-weight:500;">/{total}</span></div>
            <div class="stat-lbl">作成済み</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-box">
            <div class="stat-val" style="color:#7C3AED;">{ai_gen}</div>
            <div class="stat-lbl">AI生成</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-box">
            <div class="stat-val" style="color:#2563EB;">{modified}</div>
            <div class="stat-lbl">編集中</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-box">
            <div class="stat-val" style="color:#059669;">{locked}</div>
            <div class="stat-lbl">ロック済</div>
        </div>
        <div class="stat-divider" style="margin-left: auto; margin-right: 16px;"></div>
        <div style="font-size: 0.85rem;">
            {saved_str}
        </div>
    </div>
    <div style="width:100%; background:#F1F5F9; height:6px; border-radius:3px; margin-bottom:24px; overflow:hidden;">
        <div style="width:{progress_pct}%; background:linear-gradient(90deg, #4F46E5, #818CF8); height:100%; border-radius:3px; transition: width 0.5s ease;"></div>
    </div>
    """, unsafe_allow_html=True)


def _escape_html(text: str) -> str:
    """HTML特殊文字をエスケープ"""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def render_diff_view(original: str, current: str) -> None:
    """
    AI生成原文(original)と現在テキスト(current)の差分をHTMLで表示。
    行単位のdiff。削除行=赤背景、追加行=緑背景。
    """
    if not original:
        st.info("AI生成スナップショットがありません。初回AI生成後に差分が表示されます。")
        return
    if original == current:
        st.success("変更なし（AI生成テキストと同一です）")
        return

    original_lines = original.splitlines(keepends=True)
    current_lines = current.splitlines(keepends=True)

    matcher = difflib.SequenceMatcher(None, original_lines, current_lines, autojunk=False)
    opcodes = matcher.get_opcodes()

    html_parts = [
        '<div style="font-family:monospace;font-size:0.82rem;line-height:1.6;'
        'background:#0F172A;padding:16px;border-radius:8px;overflow-x:auto;white-space:pre-wrap;">'
    ]

    deleted_count = 0
    added_count = 0

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for line in original_lines[i1:i2]:
                html_parts.append(f'<span style="color:#94A3B8;">{_escape_html(line)}</span>')
        elif tag == "delete":
            for line in original_lines[i1:i2]:
                html_parts.append(
                    f'<span style="background:#7F1D1D;color:#FCA5A5;'
                    f'text-decoration:line-through;">{_escape_html(line)}</span>'
                )
                deleted_count += 1
        elif tag == "insert":
            for line in current_lines[j1:j2]:
                html_parts.append(
                    f'<span style="background:#14532D;color:#86EFAC;">{_escape_html(line)}</span>'
                )
                added_count += 1
        elif tag == "replace":
            for line in original_lines[i1:i2]:
                html_parts.append(
                    f'<span style="background:#7F1D1D;color:#FCA5A5;'
                    f'text-decoration:line-through;">{_escape_html(line)}</span>'
                )
                deleted_count += 1
            for line in current_lines[j1:j2]:
                html_parts.append(
                    f'<span style="background:#14532D;color:#86EFAC;">{_escape_html(line)}</span>'
                )
                added_count += 1

    html_parts.append("</div>")

    st.caption(f"削除: {deleted_count}行　追加: {added_count}行")
    st.markdown("".join(html_parts), unsafe_allow_html=True)
