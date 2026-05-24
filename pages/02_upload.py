import streamlit as st
import pandas as pd
from core.auth import check_auth
from core.normalizers import clean_financial_df, clean_sales_df
from core.validators import validate_financial_data, validate_sales_data
from core.quality_gate import check_financial_quality, check_sales_quality
import io
import json
from core.style_utils import load_custom_css
from core.external_data import ExternalDataConnector, get_industry_stats, get_regional_potential
from core.supabase_client import get_supabase_client
from core.repos.dataset_repo import DatasetRepo

# --- Template Generators (No Change) ---
def create_financials_template_lite():
    columns = ["年度", "売上", "営業利益", "経常利益", "当期純利益", "総資産", "純資産", "流動資産", "流動負債", "現預金", "有利子負債"]
    data = [
        [2023, 1000, 100, 90, 60, 1000, 300, 600, 400, 100, 300],
        [2024, 1100, 110, 100, 70, 1100, 350, 650, 420, 120, 280],
        [2025, 1200, 120, 110, 80, 1200, 400, 700, 450, 150, 250]
    ]
    df = pd.DataFrame(data, columns=columns)
    return df.to_csv(index=False).encode("utf-8-sig")

def create_financials_template_pro():
    columns = [
        "年度", "売上", "売上原価", "販管費", "営業利益", "減価償却費", "支払利息", 
        "経常利益", "当期純利益", "総資産", "純資産", "流動資産", "流動負債", 
        "売掛金", "棚卸資産", "買掛金", "現預金", "有利子負債", 
        "営業CF", "投資CF", "財務CF", "設備投資額", "従業員数"
    ]
    data = [
        [2023, 1000, 600, 300, 100, 20, 10, 90, 60, 1000, 300, 600, 400, 150, 100, 80, 100, 300, 100, -50, -30, 50, 20],
        [2024, 1100, 660, 330, 110, 22, 10, 100, 70, 1100, 350, 650, 420, 160, 110, 85, 120, 280, 110, -55, -40, 55, 22],
        [2025, 1200, 720, 360, 120, 24, 10, 110, 80, 1200, 400, 700, 450, 170, 120, 90, 150, 250, 120, -60, -50, 60, 25]
    ]
    df = pd.DataFrame(data, columns=columns)
    return df.to_csv(index=False).encode("utf-8-sig")

def create_sales_template(industry: str):
    columns = ["年月", "顧客名", "商品・サービス名", "数量", "売上金額", "原価", "粗利"]
    extensions = {
        "Retail": ["店舗名", "来店数", "客単価"],
        "Manufacturing": ["工場", "ロット", "稼働率"],
        "Construction": ["現場名", "工期", "原価区分"],
        "SaaS": ["契約ID", "MRR", "チャーン率"]
    }
    if industry in extensions:
        columns.extend(extensions[industry])
        
    base_row = ["2024-04", "Demo Customer", "Service A", 1, 10000, 3000, 7000]
    ext_data = []
    if industry == "Retail": ext_data = ["渋谷店", 150, 2000]
    elif industry == "Manufacturing": ext_data = ["第1工場", "LOT-001", "85%"]
    elif industry == "Construction": ext_data = ["東京ビル", "6ヶ月", "材料費"]
    elif industry == "SaaS": ext_data = ["SUB-123", 50000, "0.5%"]
        
    row = base_row + ext_data
    df = pd.DataFrame([row], columns=columns)
    return df.to_csv(index=False).encode("utf-8-sig")

# --- UI Components ---
def render_health_card(title, score, icon, status_text):
    """Renders a health summary card."""
    color = "var(--success-color)" if score >= 80 else "var(--warning-color)" if score >= 50 else "var(--error-color)"
    st.markdown(f"""
        <div style="background: white; border: 1px solid var(--border-color); border-radius: 12px; padding: 16px; display: flex; align-items: center; gap: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <div style="width: 48px; height: 48px; border-radius: 50%; background: {color}20; display: flex; align-items: center; justify-content: center; font-size: 24px;">
                {icon}
            </div>
            <div style="flex: 1;">
                <div style="font-size: 0.8rem; color: var(--secondary-color); font-weight: 600; text-transform: uppercase;">{title}</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: var(--primary-color); line-height: 1.2;">
                    {score}<span style="font-size: 0.9rem; color: var(--secondary-color); font-weight: 500;">/100</span>
                </div>
            </div>
             <div style="text-align: right;">
                <div style="font-size: 0.8rem; color: {color}; font-weight: 700; background: {color}10; padding: 4px 10px; border-radius: 20px;">
                    {status_text}
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

def app():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()
    
    if not check_auth():
        st.warning("Please login.")
        return
        
    if not st.session_state.get("client_id"):
        st.warning("Please select a client from the Home page first.")
        return

    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
        <div style="background:#ede9fe;color:#5b21b6;font-size:0.72rem;font-weight:700;
                    padding:3px 10px;border-radius:999px;letter-spacing:0.06em;">
            STEP 1 — データ収集フェーズ
        </div>
        <div style="font-size:0.8rem;color:#9ca3af;">財務データ（PL/BS）の登録がメイン作業です</div>
    </div>
    """, unsafe_allow_html=True)
    st.title("📥 データ登録コックピット")
    st.caption("STEP 1: 決算書（財務データ）のアップロードを優先してください。内部・外部データの追加登録も可能です。")
    
    repo = DatasetRepo()
    client_id = st.session_state.client_id
    
    # --- 1. Health Dashboard ---
    # Fetch current scores (Mock logic for demo, ideally fetch last check result)
    # We try to get version info to determine "Active" status
    v_fin = repo.get_current_dataset_version(client_id, "financial")
    v_int = repo.get_current_dataset_version(client_id, "internal") # Sales
    v_ext = repo.get_current_dataset_version(client_id, "external") # General External
    
    # Calculate pseudo-scores
    s_fin = v_fin['quality_json'].get('quality_score', 0) if v_fin and v_fin.get('quality_json') else 0
    s_int = v_int['quality_json'].get('quality_score', 0) if v_int and v_int.get('quality_json') else 0
    s_ext = 80 if v_ext else 0 # External data usually doesn't have a score, assume good if present
    
    c1, c2, c3 = st.columns(3)
    with c1:
        render_health_card("Financial Health", s_fin, "💰", "Ready" if s_fin > 0 else "Missing")
    with c2:
        render_health_card("Internal Data", s_int, "🏢", "Ready" if s_int > 0 else "Missing")
    with c3:
        render_health_card("Market Context", s_ext, "🌍", "Ready" if s_ext > 0 else "Missing")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- 2. Main Workflow Tabs ---
    tab1, tab2, tab3 = st.tabs([
        "1. Financials (PL/BS)", 
        "2. Internal (Sales/Docs)", 
        "3. External (Market)"
    ])
    
    # === Tab 1: Financials ===
    with tab1:
        st.markdown("### 📊 Financial Data Ingestion")
        st.caption("企業の基礎体力を診断するための財務データ（PL/BS）を登録します。")
        
        # Current Data Status
        if v_fin:
             fname = v_fin.get("quality_json", {}).get("filename", "Unknown")
             vdate = v_fin.get("created_at", "")[:10]
             st.success(f"✅ Active Data: **{fname}** (Version {v_fin['version']} / {vdate})")
        
        c_left, c_right = st.columns([1, 1], gap="large")
        
        with c_left:
            st.subheader("Step 1: Download Template")
            with st.container(border=True):
                st.markdown("**Select Template Type**")
                t_type = st.radio("Type", ["Lite (簡易版)", "Pro (詳細版)"], horizontal=True, label_visibility="collapsed")
                
                if "Lite" in t_type:
                    st.download_button("Download CSV", create_financials_template_lite(), "financials_lite.csv", "text/csv", use_container_width=True)
                    st.caption("最低限の指標のみ (売上、利益、資産など)")
                else:
                    st.download_button("Download CSV", create_financials_template_pro(), "financials_pro.csv", "text/csv", use_container_width=True)
                    st.caption("CFや販管費を含む詳細分析用")

        with c_right:
            st.subheader("Step 2: Upload & Validate")
            f_files = st.file_uploader("Upload CSV/Excel", type=["xlsx", "csv"], key="fin_up", accept_multiple_files=True)
            
            if f_files:
                # Processing Logic for Multiple Files
                processed_data = []
                scores = []
                has_error = False
                
                # Container for preview
                with st.expander("Preview & Validation", expanded=True):
                    for f in f_files:
                        try:
                            # 1. Read File
                            if f.name.endswith('.csv'): df = pd.read_csv(f)
                            else: df = pd.read_excel(f)
                            
                            # 2. Attempt Normalization (but keep raw if it looks like a supporting doc)
                            # We run quality check on the *raw* df first to see if it Matches Template?
                            # actually clean_financial_df forces columns. 
                            
                            df_clean = clean_financial_df(df)
                            q_res = check_financial_quality(df_clean)
                            
                            is_template = q_res['quality_score'] >= 40 # Loose threshold
                            
                            # Sanitization helper
                            def sanitize_df(d):
                                # Replace Inf/-Inf with None
                                import numpy as np
                                d = d.replace([np.inf, -np.inf], np.nan)
                                # Replace NaN with None (which becomes null in JSON)
                                return d.where(pd.notnull(d), None)

                            if is_template:
                                df_to_save = sanitize_df(df_clean)
                            else:
                                df_to_save = sanitize_df(df)

                            file_obj = {
                                "filename": f.name,
                                "type": "financial_standard" if is_template else "support_document",
                                "records": df_to_save.to_dict('records'),
                                "uploaded_at": pd.Timestamp.now().isoformat()
                            }
                            processed_data.append(file_obj)
                            
                            # UI Feedback Row
                            c_p1, c_p2 = st.columns([2, 1])
                            with c_p1:
                                st.caption(f"📄 **{f.name}**")
                            with c_p2:
                                if is_template:
                                    st.metric("Score", f"{q_res['quality_score']}", delta="Template Match" if q_res['quality_score']>80 else None)
                                else:
                                    st.caption("Raw Data (Support)")
                                    
                            scores.append(f"{f.name}: {q_res['quality_score']}")

                        except Exception as e:
                            st.error(f"Error processing {f.name}: {e}")
                            has_error = True

                if processed_data and not has_error:
                    if st.button("Save All Files", type="primary", use_container_width=True):
                        # Save logic for List of Files
                        q_json = {
                            "filename": f"{len(processed_data)} files uploaded",
                            "file_list": [d["filename"] for d in processed_data],
                            "quality_score": 100, # Composite score (placeholder)
                            "scores": scores
                        }
                        
                        version = repo.save_dataset_version(
                            client_id, "financial", processed_data, q_json, "upload_multi",
                            created_by=st.session_state.user.id
                        )
                        if version:
                            st.success(f"Successfully saved {len(processed_data)} files!")
                            import time
                            time.sleep(1)
                            st.rerun()

            st.markdown("---")
            render_file_list_table("financial", client_id)

    # === Tab 2: Internal ===
    with tab2:
        st.markdown("### 🏢 Internal Data Ingestion")
        st.caption("売上明細や社内文書を統合します。")
        
        # Sub-tabs for Sales vs Specs
        sub_t1, sub_t2 = st.tabs(["Sales Transactions", "Documents & Specs"])
        
        with sub_t1:
             st.subheader("Sales Data Analysis")
             col_t1, col_t2 = st.columns([1, 2])
             with col_t1:
                 industry = st.selectbox("Industry Template", ["Retail", "Manufacturing", "Construction", "SaaS"])
                 st.download_button("Download Template", create_sales_template(industry), f"sales_{industry}.csv", "text/csv", use_container_width=True)
             
             s_files = st.file_uploader("Upload Sales Data", type=["xlsx", "csv"], key="sale_up", accept_multiple_files=True)
             
             if s_files:
                 processed_sales = []
                 s_scores = []
                 s_has_error = False

                 with st.expander("Preview & Validation (Sales)", expanded=True):
                    for f in s_files:
                        try:
                            if f.name.endswith('.csv'): df_s = pd.read_csv(f)
                            else: df_s = pd.read_excel(f)
                            
                            df_s_clean = clean_sales_df(df_s)
                            q_res = check_sales_quality(df_s_clean)
                            
                            # Sanitization helper (Inline)
                            def sanitize_df(d):
                                import numpy as np
                                d = d.replace([np.inf, -np.inf], np.nan)
                                return d.where(pd.notnull(d), None)

                            file_obj = {
                                "filename": f.name,
                                "type": "sales_transaction",
                                "records": sanitize_df(df_s_clean).to_dict('records'),
                                "uploaded_at": pd.Timestamp.now().isoformat()
                            }
                            processed_sales.append(file_obj)
                            s_scores.append(f"{f.name}: {q_res['quality_score']}")

                            # UI Row
                            c_s1, c_s2 = st.columns([2, 1])
                            with c_s1:
                                st.caption(f"🛒 **{f.name}**")
                                st.dataframe(df_s_clean.head(3), use_container_width=True)
                            with c_s2:
                                st.metric("Quality", f"{q_res['quality_score']}/100")
                                if q_res['critical_flags']:
                                    st.error(f"Issues: {len(q_res['critical_flags'])}")

                        except Exception as e:
                            st.error(f"Error processing {f.name}: {e}")
                            s_has_error = True

                 if processed_sales and not s_has_error:
                     if st.button("Save Sales Data", type="primary"):
                         q_json = {
                             "filename": f"{len(processed_sales)} sales files",
                             "file_list": [d["filename"] for d in processed_sales],
                             "quality_score": 100,
                             "scores": s_scores
                         }
                         repo.save_dataset_version(
                             client_id, "internal", processed_sales, q_json, "upload_multi", 
                             created_by=st.session_state.user.id
                        )
                         st.success(f"Saved {len(processed_sales)} sales files!")
                         import time
                         time.sleep(1)
                         st.rerun()

             st.markdown("---")
             render_file_list_table("internal", client_id)

        with sub_t2:
            st.subheader("Unstructured Data (Docs)")
            st.info("PDF, Word, or Text files.")
            i_docs = st.file_uploader("Drop documents here", type=["txt", "pdf", "docx", "json", "csv"], accept_multiple_files=True, key="int_docs")
            if i_docs and st.button("Ingest Documents", key="ingest_int"):
                st.info("データ解析・保存を開始します...")
                processed_count = 0
                error_files = []

                # Prepare batch list
                cur_v = repo.get_current_dataset_version(client_id, "internal_docs")
                existing_docs = []
                if cur_v and cur_v.get("normalized_json"):
                    prev_data = cur_v.get("normalized_json")
                    if isinstance(prev_data, list):
                        existing_docs = prev_data
                    elif isinstance(prev_data, dict):
                        existing_docs = [prev_data]

                for f in i_docs:
                    try:
                        text_content = ""
                        # 1. Extract Text
                        if f.name.endswith(".pdf"):
                            import pypdf
                            reader = pypdf.PdfReader(f)
                            for page in reader.pages:
                                extracted = page.extract_text()
                                if extracted:
                                    text_content += extracted + "\n\n"
                        elif f.name.endswith(".txt"):
                            text_content = f.read().decode("utf-8")
                        elif f.name.endswith(".json"):
                            import json
                            data = json.load(f)
                            text_content = json.dumps(data, indent=2, ensure_ascii=False)
                        elif f.name.endswith(".csv"):
                            # CSV to Markdown
                            try:
                                df_temp = pd.read_csv(f)
                            except UnicodeDecodeError:
                                f.seek(0)
                                df_temp = pd.read_csv(f, encoding="shift_jis")
                            
                            # Sanitize
                            import numpy as np
                            df_temp = df_temp.replace([np.inf, -np.inf], np.nan)
                            df_temp = df_temp.where(pd.notnull(df_temp), None)
                            
                            text_content = f"### {f.name}\n\n" + df_temp.to_markdown(index=False)
                        else:
                            st.warning(f"未対応のファイル形式です: {f.name}")
                            continue

                        # 2. Construct Payload
                        if isinstance(text_content, str):
                            new_doc = {
                                "filename": f.name,
                                "content": text_content,
                                "type": "internal_doc_text",
                                "uploaded_at": pd.Timestamp.now().isoformat()
                            }
                        else:
                            new_doc = text_content
                            if isinstance(new_doc, dict):
                                new_doc["uploaded_at"] = pd.Timestamp.now().isoformat()
                        
                        existing_docs.append(new_doc)
                        processed_count += 1
                        
                    except Exception as e:
                        st.error(f"{f.name} の処理中にエラーが発生しました: {e}")
                        error_files.append(f.name)
                
                # 3. Save Batch
                if processed_count > 0:
                    q_json = {
                        "filename": f"Batch Upload ({processed_count} files)",
                        "type": "internal_document_batch",
                        "source": "upload_unstructured",
                        "count": len(existing_docs),
                        "error_files": error_files
                    }
                    
                    version = repo.save_dataset_version(
                        client_id=client_id,
                        dataset_type="internal_docs",
                        normalized_json=existing_docs,
                        quality_json=q_json,
                        source_type="upload_doc",
                        created_by=st.session_state.user.id if "user" in st.session_state else None
                    )
                    
                    st.success(f"{processed_count} 件のドキュメントを保存しました。(Dataset: internal_docs)")
                    import time
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("処理されたファイルはありませんでした。")
            
            st.markdown("---")
            render_file_list_table("internal_docs", client_id)

    # === Tab 3: External ===
    with tab3:
        st.markdown("### 🌍 External Environment")
        st.caption("市場データや統計情報を取得します。")
        
        # Hero Section for Auto-Fetch
        with st.container(border=True):
            c_hero1, c_hero2 = st.columns([2, 1])
            with c_hero1:
                st.markdown("#### ⚡ Auto-Fetch Intelligence")
                st.markdown("クライアントの属性（業種・所在地）に基づいて、政府統計(e-Stat)および地域経済データを自動取得します。")
            with c_hero2:
                # Current Client Info
                try:
                    sb = get_supabase_client()
                    c_res = sb.table("clients").select("*").eq("id", client_id).single().execute()
                    c_ind = c_res.data.get("industry", "Unset") if c_res.data else "Unset"
                    c_loc = c_res.data.get("location", "Unset") if c_res.data else "Unset"
                except:
                    c_ind, c_loc = "Unknown", "Unknown"
                
                st.caption(f"Target: {c_ind} / {c_loc}")
                if st.button("Run Auto-Fetch", type="primary", use_container_width=True):
                    with st.spinner("Fetching data from Government APIs..."):
                        try:
                            # Verify API Logic
                            conn = ExternalDataConnector()
                            stats = conn.get_industry_statistics(c_ind)
                            reg = conn.get_regional_market_potential(c_loc, c_ind)
                            
                            # Construct payload
                            data = {
                                "industry_stats": stats.dict() if stats else None,
                                "regional": reg,
                                "meta": {"fetched_at": pd.Timestamp.now().isoformat()}
                            }
                            repo.save_dataset_version(client_id, "external", data, {"source":"auto-fetch"}, "api", created_by=st.session_state.user.id)
                            st.success("Intelligence Acquired!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fetch failed: {e}")
        
        st.divider()
        st.markdown("#### Manual Upload")
        e_docs = st.file_uploader("Upload Report (PDF/JSON)", type=["json", "pdf", "txt"], accept_multiple_files=True, key="ext_docs")
        if e_docs and st.button("Ingest Reports"):
            st.info("データ解析・保存を開始します...")
            processed_count = 0
            
            # Prepare batch list
            cur_v = repo.get_current_dataset_version(st.session_state.client_id, "external_docs")
            existing_docs = []
            if cur_v and cur_v.get("normalized_json"):
                prev_data = cur_v.get("normalized_json")
                if isinstance(prev_data, list):
                    existing_docs = prev_data
                elif isinstance(prev_data, dict):
                    existing_docs = [prev_data]
            
            error_files = []

            for f in e_docs:
                try:
                    text_content = ""
                    # 1. Extract Text
                    if f.name.endswith(".pdf"):
                        import pypdf
                        reader = pypdf.PdfReader(f)
                        for page in reader.pages:
                            extracted = page.extract_text()
                            if extracted:
                                text_content += extracted + "\n\n"
                    elif f.name.endswith(".txt"):
                        text_content = f.read().decode("utf-8")
                    elif f.name.endswith(".json"):
                        import json
                        data = json.load(f)
                        text_content = json.dumps(data, indent=2, ensure_ascii=False)
                    elif f.name.endswith(".csv"):
                        # CSV to Markdown
                        try:
                            df_temp = pd.read_csv(f)
                        except UnicodeDecodeError:
                            f.seek(0)
                            df_temp = pd.read_csv(f, encoding="shift_jis")
                        
                        # Sanitize just in case
                        import numpy as np
                        df_temp = df_temp.replace([np.inf, -np.inf], np.nan)
                        df_temp = df_temp.where(pd.notnull(df_temp), None)
                        
                        text_content = f"### {f.name}\n\n" + df_temp.to_markdown(index=False)
                    else:
                        st.warning(f"未対応のファイル形式です: {f.name}")
                        continue

                    # 2. Construct Payload
                    if isinstance(text_content, str):
                        new_doc = {
                            "filename": f.name,
                            "content": text_content,
                            "type": "external_document_text",
                            "uploaded_at": pd.Timestamp.now().isoformat()
                        }
                    else:
                        new_doc = text_content
                        if isinstance(new_doc, dict):
                            new_doc["uploaded_at"] = pd.Timestamp.now().isoformat()
                    
                    existing_docs.append(new_doc)
                    processed_count += 1
                    
                except Exception as e:
                    st.error(f"{f.name} の処理中にエラーが発生しました: {e}")
                    error_files.append(f.name)
            
            # 3. Save Batch
            if processed_count > 0:
                q_json = {
                    "filename": f"Batch Upload ({processed_count} files)",
                    "type": "external_document_batch",
                    "source": "upload_unstructured",
                    "count": len(existing_docs),
                    "error_files": error_files
                }
                
                version = repo.save_dataset_version(
                    client_id=st.session_state.client_id,
                    dataset_type="external_docs",
                    normalized_json=existing_docs,
                    quality_json=q_json,
                    source_type="upload_doc",
                    created_by=st.session_state.user.id if "user" in st.session_state else None
                )
                
                st.success(f"{processed_count} 件のドキュメントを保存しました。(Dataset: external_docs)")
                st.info("※次回の分析実行時に、この情報が参照されます。")
                import time
                time.sleep(1)
                st.rerun()
            else:
                st.warning("処理されたファイルはありませんでした。")
        
        st.markdown("---")
        render_file_list_table("external_docs", client_id)
        render_file_list_table("external", client_id) # APIs

def render_file_list_table(dataset_type: str, client_id: str):
    """Refined file list table."""
    repo = DatasetRepo()
    cur_v = repo.get_current_dataset_version(client_id, dataset_type)
    
    if not cur_v or not cur_v.get("normalized_json"):
        st.info(f"No {dataset_type} files uploaded.")
        return

    data = cur_v.get("normalized_json")
    if isinstance(data, dict): data = [data]
    
    rows = []
    for item in data:
        # Handle Auto-Fetch Structure (nested in meta)
        if "meta" in item and "source" in item["meta"]:
            m = item["meta"]
            fname = f"Auto-Fetch ({m.get('target_industry', '?')}/{m.get('target_location', '?')})"
            ftype = "External API (e-Stat)"
            fdate = m.get("fetched_at", "")
        # Handle Standard Structure
        else:
            fname = item.get("filename", item.get("name", "Unknown"))
            ftype = item.get("type", "Unknown")
            fdate = item.get("uploaded_at", "")

        rows.append({
            "File": fname,
            "Type": ftype,
            "Date": fdate[:16]
        })
    
    st.markdown(f"**Uploaded Files ({dataset_type})**")
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

if __name__ == "__main__":
    app()
